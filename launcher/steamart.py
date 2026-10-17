"""Steam library artwork for the "Mulle Meck" entry on a Steam Deck, made on
this machine from the player's own pictures (a game's title screen and its
backdrop, HD when made), so nothing from the discs is shipped. Steam's sizes,
as the user's other launcher: library_600x900.png the portrait
tile, header_920x430.png the wide one, main_1232x706.png the banner on the
game's page. deck.py sends them along and steam_shortcut.py sets them.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SIZES = {"library_600x900.png": (600, 900), "header_920x430.png": (920, 430), "main_1232x706.png": (1232, 706)}


def cover_fit(img, w, h):
	s = max(w / img.width, h / img.height)
	big = img.resize((max(w, round(img.width * s)), max(h, round(img.height * s))), Image.LANCZOS)
	x, y = (big.width - w) // 2, (big.height - h) // 2
	return big.crop((x, y, x + w, y + h))


def card(img, w, h, radius):
	"""The title screen as a rounded card with a soft shadow, on transparency."""
	pad = max(8, h // 12)
	out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
	mask = Image.new("L", (w * 4, h * 4), 0)
	ImageDraw.Draw(mask).rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1), radius * 4, fill=255)
	mask = mask.resize((w, h), Image.LANCZOS)
	shadow = Image.new("L", out.size, 0)
	shadow.paste(mask, (pad, pad + pad // 3))
	shadow = shadow.filter(ImageFilter.GaussianBlur(pad * 0.45)).point(lambda v: int(v * 0.6))
	out.putalpha(shadow)
	face = cover_fit(img, w, h).convert("RGBA")
	face.putalpha(mask)
	out.alpha_composite(face, (pad, pad))
	return out


def make(root, games):
	"""Writes the artwork into root/cache/steam from the first playable game
	found here with its pictures. Returns the folder, or None."""
	game = next((g for g in games if g.found and g.info.playable and g.cover is not None and g.backdrop is not None), None)
	if game is None:
		return None
	out = Path(root) / "cache" / "steam"
	out.mkdir(parents=True, exist_ok=True)
	title, back = game.cover.convert("RGB"), game.backdrop.convert("RGB")
	for name, (w, h) in SIZES.items():
		img = cover_fit(back, w, h).convert("RGBA")
		if name != "main_1232x706.png":  # the banner is the scene alone; the tiles show the title on it
			img = img.filter(ImageFilter.GaussianBlur(max(w, h) / 160))
			cw = int(w * 0.86) if w < h else int(h * 0.84 * 4 / 3)
			ch = cw * 3 // 4
			c = card(title, cw, ch, max(6, ch // 20))
			y = (h - c.height) // 2 - (int(h * 0.08) if w < h else 0)
			img.alpha_composite(c, ((w - c.width) // 2, y))
		img.convert("RGB").save(out / name)
	return out
