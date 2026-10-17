"""Check an HD art set against the originals and write contact sheets for review.

  qa_check.py BUILD_DIR

For every HD image: shrink it back to the original size and measure the mean
colour difference to the original over the pixels the game draws opaque. Lists
the worst images and writes BUILD_DIR/qa/random.png and BUILD_DIR/qa/worst.png
(sprites on a dark background, labelled), plus BUILD_DIR/qa/report.json.
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from alpha_upscale import ink_mask  # noqa: E402

TILE = 240
DARK = (40, 44, 52, 255)


def drift(build, e, variant, path):
	orig = np.asarray(Image.open(build / e["file"]).convert("RGB")).astype(np.float32)
	hd = Image.open(build / path).convert("RGBA").resize((e["width"], e["height"]), Image.BOX)
	hd = np.asarray(hd).astype(np.float32)
	opaque = ink_mask(orig.astype(np.uint8), variant)
	if not opaque.any():
		return 0.0, 0.0
	colour = float(np.abs(hd[..., :3] - orig)[opaque].mean())
	alpha_err = float(np.abs(hd[..., 3] / 255 - opaque).mean())
	return colour, alpha_err


def sheet(build, items, out, title):
	cols = 6
	rows = (len(items) + cols - 1) // cols
	img = Image.new("RGB", (cols * (TILE + 4), rows * (TILE + 18) + 20), (12, 12, 12))
	d = ImageDraw.Draw(img)
	d.text((4, 4), title, fill=(255, 255, 255))
	for i, (e, v, p, c, a) in enumerate(items):
		sp = Image.open(build / p).convert("RGBA")
		sp.thumbnail((TILE, TILE), Image.LANCZOS)
		t = Image.new("RGBA", (TILE, TILE), DARK)
		t.alpha_composite(sp, ((TILE - sp.width) // 2, (TILE - sp.height) // 2))
		x, y = (i % cols) * (TILE + 4), 20 + (i // cols) * (TILE + 18)
		img.paste(t.convert("RGB"), (x, y))
		d.text((x + 2, y + TILE + 3), f"{e['cast']}/{e['name'] or e['member']} {v} d{c:.0f}", fill=(220, 220, 120))
	img.save(out)


def main():
	build = Path(sys.argv[1])
	manifest = json.loads((build / "manifest.json").read_text())
	rows = []
	for e in manifest:
		for v, p in e.get("hd", {}).items():
			c, a = drift(build, e, v, p)
			rows.append((e, v, p, c, a))
	rows.sort(key=lambda r: -r[3])
	(build / "qa").mkdir(exist_ok=True)
	colours = np.array([r[3] for r in rows])
	print(f"{len(rows)} HD images; colour drift median {np.median(colours):.1f}, "
		f"95th pct {np.percentile(colours, 95):.1f}, max {colours.max():.1f}")
	print("worst:")
	for e, v, p, c, a in rows[:12]:
		print(f"  {c:5.1f}  alpha {a:.3f}  {p}")
	random.seed(1)
	sheet(build, random.sample(rows, min(36, len(rows))), build / "qa" / "random.png", "Random sample")
	sheet(build, rows[:36], build / "qa" / "worst.png", "Largest colour drift")
	(build / "qa" / "report.json").write_text(json.dumps(
		[{"file": p, "variant": v, "colour_drift": round(c, 2), "alpha_error": round(a, 4)} for e, v, p, c, a in rows], indent=1))


if __name__ == "__main__":
	main()
