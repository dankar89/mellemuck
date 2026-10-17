"""Extract every bitmap from a Mulle Meck game disc (Director 6, or 8.5 for Bygg hus) into PNGs plus a manifest.

  extract_assets.py GAME_DIR OUT_DIR

GAME_DIR is the extracted disc (with MOVIES/ and DATA/). Writes
  OUT_DIR/orig/<CAST>/<member>_<name>.png   original pixels, white kept
  OUT_DIR/manifest.json                     one entry per bitmap

Each manifest entry records the cast file, member number, name, size,
registration point, bit depth, palette, the inks the scores draw it with, and
a category that selects the upscaling recipe:
  background  full-screen art and map tiles, drawn opaque
  lineart     flat-coloured outlined art (characters), Real-ESRGAN anime model
  painted     dithered painted sprites (car parts, props)
  mask        1-bit bitmaps; not upscaled, regenerated from their sprite
  speck       8x8 pixels or smaller; not upscaled
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from director import INKS, DirectorFile, cast_files, ink_usage, palette, parse_cast_member  # noqa: E402
import morph  # noqa: E402

# Fraction of opaque pixels equal to their right-hand neighbour. Flat-filled
# line art scores high; dithered painted art scores low.
LINEART_FLATNESS = 0.60
TINY = 64
SPECK = 8  # bitmaps this small (both sides) get no HD image
# Ink for bitmaps that never appear in a score (placed by scripts at runtime).
RUNTIME_INK = "bgtrans"


def safe(name):
	return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


def flatness(idx, opaque):
	same = (idx[:, 1:] == idx[:, :-1]) & opaque[:, 1:] & opaque[:, :-1]
	n = (opaque[:, 1:] & opaque[:, :-1]).sum()
	return float(same.sum() / n) if n else 1.0


def has_enclosed_white(rgb):
	"""True if pure white exists that the matte flood fill would keep (matte != background transparent)."""
	white = np.all(rgb == 255, axis=2)
	return bool((white & ~morph.from_border(white)).any())


def variants(inks, category, enclosed):
	"""Which transparency variants the HD set needs for this bitmap."""
	if category == "background":
		return ["copy"]
	need = set()
	for ink in inks:
		if ink == "matte":
			need.add("matte")
		elif ink == "backgroundTransparent":
			need.add("bgtrans")
		else:
			need.add("copy")
	if not need:
		# Only placed at runtime by the scripts. In Bygger bilar the slots they
		# fill (part pools, Mulle, Buffa) are background transparent, and the
		# artists paint white that must stay visible off-white (snouts, eyes),
		# so pure white is always a hole. See docs/game-bygger-bilar.md.
		need = {RUNTIME_INK}
	if not enclosed and {"matte", "bgtrans"} <= need:
		need.discard("bgtrans")  # identical without enclosed white
	return sorted(need)


def main():
	manifest = extract(Path(sys.argv[1]), Path(sys.argv[2]))
	print("categories:", dict(Counter(m["category"] for m in manifest)))
	print("variants:", dict(Counter("+".join(m["variants"]) for m in manifest)))
	print("inks seen:", dict(Counter("+".join(m["inks"]) or "(runtime only)" for m in manifest)))
	print("palettes:", dict(Counter(str(m["palette"]) for m in manifest)))


def find_dir(root, name):
	"""root/name in any case (discs are upper case; Linux minds the case)."""
	return next((p for p in Path(root).iterdir() if p.is_dir() and p.name.upper() == name), Path(root) / name)


def extract(game_dir, out_dir):
	"""Every bitmap of the disc in game_dir into out_dir; returns the manifest."""
	game_dir, out_dir = Path(game_dir), Path(out_dir)
	files = cast_files(find_dir(game_dir, "MOVIES"))
	for p in find_dir(game_dir, "DATA").glob("*"):
		if p.suffix.upper() == ".CST":
			files.setdefault(p.stem.upper(), p)
	usage = ink_usage(find_dir(game_dir, "MOVIES"))

	manifest = []
	for stem, path in sorted(files.items()):
		f = DirectorFile(path)
		keys = f.keys()
		# A movie's internal cast does not always start at member 1 (13, 18, 88
		# and 92 start at 2); its first number is in the MCsL table. Numbering
		# from 1 put every member one too low, and its ink variants came from
		# its neighbour's inks.
		first = next((lib["min"] for lib in f.cast_libs() if not lib["path"]), 1)
		for num, res in sorted(f.cast_resources(first).items()):
			info = parse_cast_member(f.chunk(res))
			if info["type"] != "bitmap" or info["width"] <= 0 or info["height"] <= 0:
				continue
			if info["bpp"] in (2, 4):
				# Bygg hus has five (black full screens): left to the original art
				continue
			if info["bpp"] in (16, 32):
				# Direct colour (Bygger båtar has one; the later games use them
				# throughout): the colour itself stands in for the palette index
				# where only equality matters (flatness).
				rgb = f.bitmap_rgb(res, info, keys)
				if rgb is None:
					continue
				idx = (rgb[..., 0].astype(np.int32) << 16) | (rgb[..., 1].astype(np.int32) << 8) | rgb[..., 2]
				pal = None
			else:
				idx = f.bitmap_indices(res, info, keys)
				if idx is None:
					continue
			if info["bpp"] in (16, 32):
				pass
			elif info["bpp"] == 1:
				rgb = np.where(idx[..., None] == 1, 0, 255).astype(np.uint8).repeat(3, axis=2)
				pal = None
			else:
				pal = info.get("clut_id", 0)
				rgb = (f.member_palette(pal, keys) if pal > 0 else palette(pal))[idx]
			rel = Path("orig") / stem / f"{num:04d}_{safe(info['name']) or 'unnamed'}.png"
			(out_dir / rel).parent.mkdir(parents=True, exist_ok=True)
			# A 32-bit picture with an alpha channel (Director 7+) is drawn
			# with it, whatever the ink: the upscaler gets it over white, as
			# the other sprites, and its mask is the alpha (docs/upscaling.md).
			alpha = f.bitmap_alpha(res, info, keys) if info["bpp"] == 32 else None
			alpha_rel = None
			if alpha is not None and (alpha < 255).any() and (alpha > 0).any():
				a = alpha[..., None].astype(np.float32) / 255
				rgb = (rgb * a + 255 * (1 - a) + 0.5).astype(np.uint8)
				alpha_rel = rel.with_suffix(".alpha.png")
				Image.fromarray(alpha).save(out_dir / alpha_rel)
			Image.fromarray(rgb).save(out_dir / rel)

			inks = sorted({INKS.get(i, str(i)) for i in usage.get((stem, num), {})})
			h, w = idx.shape
			if info["bpp"] == 1:
				category = "mask"
			elif w <= SPECK and h <= SPECK:
				# A few pixels (Bygg hus's 4x4 dots): nothing to gain, and the
				# upscale cannot pass looks_right(); drawn from the original
				category = "speck"
			elif (w >= 600 and h >= 380) and set(inks) <= {"copy"}:
				category = "background"
			else:
				opaque = ~np.all(rgb == 255, axis=2)
				category = "lineart" if flatness(idx, opaque) >= LINEART_FLATNESS else "painted"
			enclosed = info["bpp"] in (8, 16, 32) and not alpha_rel and has_enclosed_white(rgb)
			manifest.append({
				"cast": stem, "member": num, "name": info["name"], "file": rel.as_posix(),
				"width": w, "height": h, "reg_x": info["reg_x"], "reg_y": info["reg_y"],
				"bpp": info["bpp"], "palette": pal, "inks": inks, "category": category,
				"tiny": max(w, h) < TINY, "enclosed_white": enclosed,
				"variants": [] if category in ("mask", "speck") else variants(inks, category, enclosed),
			})
			if alpha_rel:
				# Drawn by its alpha with any ink, so never as an opaque copy
				entry = manifest[-1]
				entry["alpha"] = alpha_rel.as_posix()
				if entry["category"] == "background":
					entry["category"] = "painted"
				entry["variants"] = sorted({"bgtrans" if v == "copy" else v for v in entry["variants"]})

	(out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
	print(f"{len(manifest)} bitmaps -> {out_dir}")
	return manifest


if __name__ == "__main__":
	main()
