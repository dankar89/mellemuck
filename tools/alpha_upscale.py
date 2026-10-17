"""Upscale sprites that use white as their transparent colour, without halos.

Director's matte ink treats white pixels connected to the image border as
transparent. Keying white out of an upscaled sprite leaves a light halo: the
upscaler blends the white background into the edge pixels. Cutting the mask
before upscaling avoids the halo but gives staircase edges, because the
original mask is pixel-sharp. So we combine both:

  1. upscale the sprite as-is, on its white background, so the model draws
     smooth outlines,
  2. use Director's original matte (scaled up) to split the result into
     solid inside, clear outside, and an edge band of about one original pixel,
  3. inside the band, treat pixels that connect to the outside through
     near-white pixels as background, solve them (and the anti-aliased pixels
     next to them) as a mix of the nearest art colour and white; that gives
     their alpha, and their colour is the art colour, so no light fringe
     remains. Everything else, e.g. pale paint just inside an outline, stays
     solid.

Which white counts as transparent depends on the sprite's Director ink:
matte removes only border-connected white (enclosed white such as eyes stays),
background transparent removes all pure white (holes in car parts).

Usage:
  alpha_upscale.py IN_DIR OUT_DIR [--ink matte|bgtrans|copy] [--model M] [--scale 3]
                   [--preblur SIGMA] [--naive]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import morph  # noqa: E402  (numpy only: scipy was too big for the players' packages)

ROOT = Path(__file__).resolve().parent.parent
ESRGAN_DIR = ROOT / "third_party" / "realesrgan-ncnn-vulkan"

# Edge-band pixels at or above WHITE_HI are fully transparent, at or below
# WHITE_LO fully opaque; in between alpha ramps linearly.
WHITE_LO, WHITE_HI = 150 / 255, 245 / 255
# Edge pixels whose lightest channel is at most this are treated as unmixed foreground.
SOLID_MAX = 0.3
# Edge pixels whose lightest channel is at least this count as background (white).
BG_MIN = 0.85


def ink_mask(rgb, ink):
	"""Opaque mask for a Director ink. Copy: everything; background transparent: all
	pure white is see-through; matte: only white connected to the border is."""
	if ink == "copy":
		return np.ones(rgb.shape[:2], dtype=bool)
	if ink == "bgtrans":
		return ~np.all(rgb == 255, axis=2)
	return matte_mask(rgb)


def matte_mask(rgb, white_min=255):
	"""Opaque mask using Director's matte rule: border-connected white is transparent."""
	white = rgb.min(axis=2) >= white_min
	return ~morph.from_border(white)


# Real-ESRGAN's defaults (auto tile size, 1:2:2 threads). This is the setting that
# ran the full-size backgrounds without GPU driver resets; smaller tiles did not
# prevent the resets seen with many small images (docs/tooling.md, Gotchas).
TILE = 0
THREADS = "1:2:2"


# On Windows, console programs started from the windowless launcher would each
# flash a console window.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def esrgan_binary():
	"""The upscaler for this system: the Windows build on Windows and in WSL
	(our development setup: WSL has no Vulkan driver for the GPU, the Windows
	program runs through interop), the Linux build elsewhere (Linux PCs, the
	Steam Deck)."""
	import platform
	if sys.platform == "win32" or "microsoft" in platform.uname().release.lower():
		return ESRGAN_DIR / "realesrgan-ncnn-vulkan.exe"
	return ESRGAN_DIR / "realesrgan-ncnn-vulkan"


def esrgan(in_dir, out_dir, model):
	rel = lambda p: os.path.relpath(p, ESRGAN_DIR)
	# The Windows build runs via WSL interop and resolves relative paths from its cwd.
	subprocess.run([str(esrgan_binary()), "-i", rel(in_dir), "-o", rel(out_dir),
		"-n", model, "-f", "png", "-t", str(TILE), "-j", THREADS],
		cwd=ESRGAN_DIR, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)


def driver_reset_marker():
	"""Record id of the newest NVIDIA driver event (nvlddmkm) in the Windows System log, or 0
	(also without Windows)."""
	try:
		out = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
			"(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='nvlddmkm'} -MaxEvents 1 "
			"-ErrorAction SilentlyContinue).RecordId"], capture_output=True, text=True, creationflags=NO_WINDOW)
	except FileNotFoundError:
		return 0
	return int(out.stdout.strip() or 0)


def compose(up, opaque, scale):
	"""Build RGBA from the white-background upscale `up` (float 0..1) and the original mask.

	Only pixels that connect to the transparent outside through background-like
	(very light) pixels count as background, so a dark outline acts as a wall:
	light art just inside it (pale chrome, white paint) stays solid. Background
	pixels and the anti-aliased pixels right next to them are modelled as
	up = a*F + (1-a)*white, F being the colour of the nearest art pixel (usually
	the dark outline); solving for a gives soft edges, and the colour is F, so no
	light rim remains.
	"""
	band_r = scale + 1
	big = np.kron(opaque, np.ones((scale, scale), dtype=bool))
	inside = morph.erode(big, band_r, border_value=True)
	outside = ~morph.dilate(big, band_r)
	band = ~inside & ~outside

	lightest = up.min(axis=2)
	dark = lightest <= SOLID_MAX
	# Background reachable from the outside without crossing art.
	exterior = morph.reachable(outside | (band & (lightest >= BG_MIN)), outside)
	# Anti-aliased pixels between that background and the art.
	edge = band & ~exterior & ~dark & morph.dilate(exterior)
	art = ~exterior & ~edge
	# The nearest art pixel, for every pixel that is not outside (those get
	# alpha 0 anyway). A radius of 4 * band_r + 4 gave the same pixels as
	# ndimage's unbounded search on 120 sprites (10 differed at 2 * band_r + 2).
	iy, ix = morph.nearest(art, ~outside, 4 * band_r + 4)
	fg = up[iy, ix]

	ink = 1 - fg
	den = (ink * ink).sum(axis=2)
	alpha_fg = ((1 - up) * ink).sum(axis=2) / np.maximum(den, 1e-4)
	# Light foregrounds (F close to white) make the solve unstable; fall back to whiteness.
	alpha_white = 1 - np.clip((lightest - WHITE_LO) / (WHITE_HI - WHITE_LO), 0, 1)
	alpha = np.clip(np.where(den > 0.05, alpha_fg, alpha_white), 0, 1)
	alpha[alpha < 0.04] = 0
	alpha = np.where(art, 1.0, np.where(outside, 0.0, alpha))

	color = np.where(art[..., None], up, fg)
	color[outside] = 0
	return np.dstack([color, alpha])


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("in_dir", type=Path)
	ap.add_argument("out_dir", type=Path)
	ap.add_argument("--model", default="realesrgan-x4plus")
	ap.add_argument("--ink", choices=("matte", "bgtrans", "copy"), default="matte",
		help="Director ink the sprite is drawn with; decides which white is transparent")
	ap.add_argument("--scale", type=int, default=3, help="final scale; models run at 4x then resample")
	ap.add_argument("--preblur", type=float, default=0, help="gaussian sigma to soften dithering first")
	ap.add_argument("--naive", action="store_true", help="also write the halo-prone upscale-then-key version")
	args = ap.parse_args()

	args.out_dir.mkdir(parents=True, exist_ok=True)
	work = Path(tempfile.mkdtemp(prefix="alpha_", dir=args.out_dir))
	(work / "in").mkdir()
	(work / "up").mkdir()

	mattes = {}
	for f in sorted(args.in_dir.glob("*.png")):
		img = Image.open(f).convert("RGB")
		mattes[f.name] = ink_mask(np.asarray(img), args.ink)
		if args.preblur:
			img = img.filter(ImageFilter.GaussianBlur(args.preblur))
		img.save(work / "in" / f.name)

	esrgan(work / "in", work / "up", args.model)

	for name, opaque in mattes.items():
		h, w = opaque.shape
		up_img = Image.open(work / "up" / name).convert("RGB").resize((w * args.scale, h * args.scale), Image.LANCZOS)
		up = np.asarray(up_img).astype(np.float32) / 255
		rgba = compose(up, opaque, args.scale)
		Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").save(args.out_dir / name)
		if args.naive:
			# Key out near-white after upscaling, the way a naive pipeline would.
			keyed = matte_mask(np.asarray(up_img), white_min=240)
			naive = np.dstack([np.asarray(up_img), np.where(keyed, 255, 0).astype(np.uint8)])
			Image.fromarray(naive, "RGBA").save(args.out_dir / f"{Path(name).stem}.naive.png")
	shutil.rmtree(work)
	print(f"{len(mattes)} sprites -> {args.out_dir}")


if __name__ == "__main__":
	sys.exit(main())
