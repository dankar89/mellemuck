"""Upscale every bitmap of an extracted game (see extract_assets.py) into the HD art set.

  upscale_game.py BUILD_DIR [--only CAST] [--scale 3]

Reads BUILD_DIR/manifest.json and writes BUILD_DIR/hd/<CAST>/<member>_<name>.<variant>.png,
one file per transparency variant the bitmap needs (copy, matte, bgtrans). The
Real-ESRGAN pass runs once per recipe and is cached in BUILD_DIR/up4x/, so
re-running only redoes the cheap compositing step. Adds an "hd" map
{variant: path} to each manifest entry.
"""
import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from alpha_upscale import compose as compose_alpha, driver_reset_marker, esrgan, ink_mask  # noqa: E402

# category -> (model, gaussian pre-blur sigma at original size); see docs/upscaling.md
RECIPES = {
	"background": ("ultrasharp-4x", 0.7),
	"painted": ("realesrgan-x4plus", 0.0),
	"lineart": ("realesrgan-x4plus-anime", 0.0),
}


def flat_name(entry):
	return f"{entry['cast']}__{Path(entry['file']).name}"


def looks_right(src, out):
	"""The 4x output (array), shrunk back, must resemble its input (array). Corrupted
	Real-ESRGAN output (stripes/noise/black) comes back with exit code 0."""
	b = Image.fromarray(out).resize((src.shape[1], src.shape[0]), Image.BOX)
	return float(np.abs(np.asarray(b).astype(np.float32) - src.astype(np.float32)).mean()) < MAX_DRIFT


# Mean absolute difference (0-255) between input and downscaled output; good
# outputs measured 3-15, corrupted ones far above 30.
MAX_DRIFT = 25
# Hundreds of small images in a row reset this laptop's GPU driver (nvlddmkm
# event 153, desktop freezes), while large images run cleanly. So small sprites
# are packed onto sheets, each with a margin of its own replicated edge pixels so
# neighbours cannot influence it, upscaled as one image and cut apart again.
SHEET = 1024
MARGIN = 12
SHEETS_PER_RUN = 4
PAUSE = 2  # seconds between runs, so the GPU (which also drives the display) gets a break


def pack(sizes):
	"""Shelf-pack {name: (w, h)} into sheets. Returns [{name: (x, y)}]; (x, y) is the
	sprite's top-left inside its sheet, margins excluded."""
	sheets, cur, x, y, shelf = [], {}, 0, 0, 0
	for name, (w, h) in sorted(sizes.items(), key=lambda kv: -kv[1][1]):
		bw, bh = w + 2 * MARGIN, h + 2 * MARGIN
		if bw > SHEET or bh > SHEET:
			sheets.append({name: (MARGIN, MARGIN)})  # too big to share a sheet
			continue
		if x + bw > SHEET:
			x, y, shelf = 0, y + shelf, 0
		if y + bh > SHEET:
			sheets.append(cur)
			cur, x, y, shelf = {}, 0, 0, 0
		cur[name] = (x + MARGIN, y + MARGIN)
		x, shelf = x + bw, max(shelf, bh)
	if cur:
		sheets.append(cur)
	return sheets


def run_recipe(build, category, entries, on_cached=None):
	"""Real-ESRGAN for one category, into the 4x cache. on_cached(names) is
	called after each run with the cache names it finished, so a caller can
	compose those right away (the launcher's HD job)."""
	model, blur = RECIPES[category]
	cache = build / "up4x" / category
	todo = [e for e in entries if not (cache / flat_name(e)).exists()]
	if not todo:
		return
	cache.mkdir(parents=True, exist_ok=True)
	stage = build / "up4x" / f"_stage_{category}"
	shutil.rmtree(stage, ignore_errors=True)
	stage.mkdir(parents=True)

	inputs = {}
	for e in todo:
		img = Image.open(build / e["file"]).convert("RGB")
		# The blur takes out the 8-bit palette's dither; 16/32-bit art (Bygg
		# hus) has none.
		if blur and e.get("bpp", 8) <= 8:
			img = img.filter(ImageFilter.GaussianBlur(blur))
		inputs[flat_name(e)] = np.asarray(img)

	start = time.time()
	reset_baseline = driver_reset_marker()
	pending = list(inputs)
	for attempt in range(2):
		sheets = pack({n: (inputs[n].shape[1], inputs[n].shape[0]) for n in pending})
		failed = []
		for i in range(0, len(sheets), SHEETS_PER_RUN):
			run_in, run_out = stage / "in", stage / "out"
			for d in (run_in, run_out):
				shutil.rmtree(d, ignore_errors=True)
				d.mkdir()
			group = sheets[i:i + SHEETS_PER_RUN]
			for k, placement in enumerate(group):
				w = max(x + inputs[n].shape[1] + MARGIN for n, (x, y) in placement.items())
				h = max(y + inputs[n].shape[0] + MARGIN for n, (x, y) in placement.items())
				canvas = np.full((h, w, 3), 255, np.uint8)
				for n, (x, y) in placement.items():
					padded = np.pad(inputs[n], ((MARGIN, MARGIN), (MARGIN, MARGIN), (0, 0)), mode="edge")
					ph, pw = padded.shape[:2]
					canvas[y - MARGIN:y - MARGIN + ph, x - MARGIN:x - MARGIN + pw] = padded
				Image.fromarray(canvas).save(run_in / f"sheet{k}.png")
			esrgan(run_in, run_out, model)
			if driver_reset_marker() != reset_baseline:
				shutil.rmtree(stage)
				raise SystemExit("GPU driver reset detected (nvlddmkm in the Windows System log); stopped.")
			finished = []
			for k, placement in enumerate(group):
				out_path = run_out / f"sheet{k}.png"
				sheet = np.asarray(Image.open(out_path).convert("RGB")) if out_path.exists() else None
				for n, (x, y) in placement.items():
					h, w = inputs[n].shape[:2]
					crop = sheet[4 * y:4 * (y + h), 4 * x:4 * (x + w)] if sheet is not None else None
					if crop is not None and crop.shape[:2] == (4 * h, 4 * w) and looks_right(inputs[n], crop):
						save_atomic(Image.fromarray(crop), cache / n)
						finished.append(n)
					else:
						failed.append(n)
			if on_cached and finished:
				on_cached(finished)
			time.sleep(PAUSE)
		pending = failed
		if not pending:
			break
		print(f"  {category}: {len(pending)} corrupted outputs, retrying", flush=True)
	shutil.rmtree(stage)
	if pending:
		raise SystemExit(f"{category}: still corrupted after retry: {pending[:10]}")
	print(f"  {category}: {len(todo)} images with {model} in {time.time() - start:.0f}s", flush=True)


def save_atomic(img, path):
	"""Written under a temporary name and renamed: a stop or crash never leaves
	a cut-off image (the engine reads HD images as they appear)."""
	tmp = path.with_name(path.name + ".tmp")
	img.save(tmp, format="PNG")
	os.replace(tmp, path)


def hd_rel(entry, variant):
	"""An HD image's path relative to the HD folder."""
	return Path(entry["cast"]) / f"{Path(entry['file']).stem}.{variant}.png"


def compose(build, e, scale, out_dir):
	"""The HD images of manifest entry e (one per variant) from its cached 4x
	upscale, into out_dir. Returns {variant: path relative to out_dir}."""
	orig = np.asarray(Image.open(build / e["file"]).convert("RGB"))
	h, w = orig.shape[:2]
	size = (w * scale, h * scale)
	up_img = Image.open(build / "up4x" / e["category"] / flat_name(e)).convert("RGB").resize(size, Image.LANCZOS)
	up = np.asarray(up_img).astype(np.float32) / 255
	out = {}
	for variant in e["variants"]:
		rel = hd_rel(e, variant)
		(out_dir / rel).parent.mkdir(parents=True, exist_ok=True)
		if variant == "copy":
			save_atomic(up_img, out_dir / rel)
		else:
			# A picture with an alpha channel is drawn by it, whatever the ink
			mask = np.asarray(Image.open(build / e["alpha"])) >= 128 if e.get("alpha") else ink_mask(orig, variant)
			rgba = compose_alpha(up, mask, scale)
			save_atomic(Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA"), out_dir / rel)
		out[variant] = rel.as_posix()
	return out


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("build", type=Path)
	ap.add_argument("--only", help="limit to one cast file stem, e.g. CDDATA")
	ap.add_argument("--scale", type=int, default=3)
	ap.add_argument("--limit", type=int, help="process at most this many bitmaps (for a test run)")
	args = ap.parse_args()

	manifest_path = args.build / "manifest.json"
	manifest = json.loads(manifest_path.read_text())
	work = [e for e in manifest if e["category"] in RECIPES and (not args.only or e["cast"] == args.only)]
	if args.limit:
		cached = lambda e: (args.build / "up4x" / e["category"] / flat_name(e)).exists()
		work = [e for e in work if not cached(e)][:args.limit]

	for category in RECIPES:
		run_recipe(args.build, category, [e for e in work if e["category"] == category])

	written = 0
	for e in work:
		e["hd"] = {v: f"hd/{rel}" for v, rel in compose(args.build, e, args.scale, args.build / "hd").items()}
		written += len(e["hd"])

	manifest_path.write_text(json.dumps(manifest, indent=1))
	print(f"{written} HD images for {len(work)} bitmaps -> {args.build / 'hd'}")


if __name__ == "__main__":
	main()
