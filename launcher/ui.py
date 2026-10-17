"""The launcher's screen: a carousel of the Mulle Meck games.

The focused game sits large in the middle on a blurred picture from its disc,
its neighbours smaller on each side. Below it: its name and round icon
buttons (play, HD art with its progress ring; find the game files when they
are not there), with one word for what has focus. Everything is reached by
moving the focus (controller, arrow keys or mouse) and pressed with A, Enter
or a click: no shortcuts to learn (the user's wish).

Drawn in the pause menu's style (game-menu.cpp in our ScummVM): Fredoka,
paper and yellow buttons, brown ink.
"""
import io
import json
import math
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pygame
import pygame._sdl2.controller
from PIL import Image, ImageDraw, ImageFilter

from . import deck, discs, library
from .deckpanel import DeckPanel
from .hdpanel import HDPanel

PROJECT = Path(__file__).resolve().parent.parent
ICONS = PROJECT / "third_party" / "lucide"

INK = (74, 46, 23)
PAPER = (255, 243, 214)
YELLOW = (255, 197, 49)
GREEN = (61, 170, 74)
RED = (217, 68, 58)
WHITE = (255, 255, 255)
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def font_path(root):
	for p in (Path(root) / "data" / "Fredoka-SemiBold.ttf", PROJECT / "third_party" / "fonts" / "Fredoka-SemiBold.ttf"):
		if p.exists():
			return p
	return None


def to_surface(img):
	img = img.convert("RGBA")
	return pygame.image.frombytes(img.tobytes(), img.size, "RGBA").convert_alpha()


def rounded_mask(w, h, r, ss=4):
	"""Anti-aliased rounded rectangle as an L image."""
	m = Image.new("L", (w * ss, h * ss), 0)
	ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
	return m.resize((w, h), Image.LANCZOS)


def cover_fit(img, w, h):
	"""Scale and crop to fill w x h."""
	s = max(w / img.width, h / img.height)
	big = img.resize((max(w, round(img.width * s)), max(h, round(img.height * s))), Image.LANCZOS)
	x, y = (big.width - w) // 2, (big.height - h) // 2
	return big.crop((x, y, x + w, y + h))


class Assets:
	def __init__(self, root):
		self.font_file = font_path(root)
		self._fonts, self._icons, self._rings, self._circles = {}, {}, {}, {}

	def font(self, size):
		size = max(8, int(size))
		if size not in self._fonts:
			self._fonts[size] = pygame.font.Font(str(self.font_file) if self.font_file else None, size)
		return self._fonts[size]

	def text(self, s, size, color=WHITE, shadow=True):
		f = self.font(size)
		surf = f.render(s, True, color)
		if not shadow:
			return surf
		out = pygame.Surface((surf.get_width() + 4, surf.get_height() + 4), pygame.SRCALPHA)
		sh = f.render(s, True, (0, 0, 0))
		sh.set_alpha(110)
		out.blit(sh, (3, 3))
		out.blit(surf, (0, 0))
		return out

	def icon(self, name, size, color=INK, filled=False, stroke=2.25):
		key = (name, int(size), color, filled, stroke)
		if key not in self._icons:
			svg = (ICONS / f"{name}.svg").read_text()
			hexc = "#%02x%02x%02x" % color
			svg = svg.replace("currentColor", hexc).replace('stroke-width="2"', f'stroke-width="{stroke}"')
			if filled:
				svg = svg.replace('fill="none"', f'fill="{hexc}"')
			self._icons[key] = pygame.image.load_sized_svg(io.BytesIO(svg.encode()), (int(size), int(size)))
		return self._icons[key]

	def circle(self, d, color, alpha=255):
		key = (int(d), color, alpha)
		if key not in self._circles:
			ss = 4
			m = Image.new("L", (int(d) * ss, int(d) * ss), 0)
			ImageDraw.Draw(m).ellipse((0, 0, int(d) * ss - 1, int(d) * ss - 1), fill=alpha)
			m = m.resize((int(d), int(d)), Image.LANCZOS)
			img = Image.new("RGBA", m.size, color + (0,))
			img.putalpha(m)
			self._circles[key] = to_surface(img)
		return self._circles[key]

	def ring(self, d, width, fraction, color, track=(255, 255, 255, 70)):
		"""A progress ring, starting at the top, clockwise."""
		key = (int(d), int(width), round(fraction * 200), color, track)
		if key not in self._rings:
			ss = 4
			D, W = int(d) * ss, max(1, int(width * ss))
			img = Image.new("RGBA", (D, D), (0, 0, 0, 0))
			draw = ImageDraw.Draw(img)
			box = (W // 2, W // 2, D - W // 2 - 1, D - W // 2 - 1)
			draw.ellipse(box, outline=track, width=W)
			if fraction > 0:
				draw.arc(box, -90, -90 + 360 * min(1.0, fraction), fill=color + (255,), width=W)
			self._rings[key] = to_surface(img.resize((int(d), int(d)), Image.LANCZOS))
		return self._rings[key]


	def focus_ring(self, d, H):
		"""The focus mark of a round button: a white outline just outside it
		(outside the HD button's progress ring too)."""
		return self.ring(d + H * 0.05, max(2, H * 0.0055), 1.0, WHITE, track=(0, 0, 0, 0))

	def frame(self, w, h, r, width):
		"""A white rounded outline just outside a w x h card (the focus)."""
		key = ("frame", w, h, r, width)
		if key not in self._rings:
			ss, pad = 4, width + 2
			W, H = (w + 2 * pad) * ss, (h + 2 * pad) * ss
			m = Image.new("L", (W, H), 0)
			draw = ImageDraw.Draw(m)
			draw.rounded_rectangle((0, 0, W - 1, H - 1), (r + pad) * ss, fill=255)
			draw.rounded_rectangle((pad * ss, pad * ss, W - pad * ss - 1, H - pad * ss - 1), r * ss, fill=0)
			img = Image.new("RGBA", (W, H), WHITE + (0,))
			img.putalpha(m)
			self._rings[key] = to_surface(img.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS))
		return self._rings[key]

	def arc(self, d, width, degrees, color):
		"""A short arc at the top of a ring, turned to make a spinner."""
		key = ("arc", int(d), int(width), degrees, color)
		if key not in self._rings:
			ss = 4
			D, W = int(d) * ss, max(1, int(width * ss))
			img = Image.new("RGBA", (D, D), (0, 0, 0, 0))
			box = (W // 2, W // 2, D - W // 2 - 1, D - W // 2 - 1)
			ImageDraw.Draw(img).arc(box, -90, -90 + degrees, fill=color + (255,), width=W)
			self._rings[key] = to_surface(img.resize((int(d), int(d)), Image.LANCZOS))
		return self._rings[key]


class Card:
	"""A game's card at full size, with its shadow; scaled while drawn."""

	def __init__(self, game, assets, w, h):
		r = max(6, int(h * 0.05))
		if game.cover is not None:
			img = cover_fit(game.cover, w, h).convert("RGBA")
		else:
			img = self.plain(game, assets, w, h)
		img.putalpha(rounded_mask(w, h, r))
		self.image = to_surface(img)
		pad = int(h * 0.08)
		sh = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
		sh.paste(rounded_mask(w, h, r), (pad, pad + int(pad * 0.35)))
		sh = sh.filter(ImageFilter.GaussianBlur(pad * 0.45))
		shadow = Image.new("RGBA", sh.size, (0, 0, 0, 0))
		shadow.putalpha(sh.point(lambda v: int(v * 0.55)))
		self.shadow = to_surface(shadow)
		self.pad = pad

	@staticmethod
	def plain(game, assets, w, h):
		"""Before the game is found: its colour and its icon (the name is under
		the card)."""
		c = game.info.color
		top, bottom = tuple(min(255, int(v * 1.18 + 16)) for v in c), tuple(int(v * 0.72) for v in c)
		grad = Image.new("RGB", (1, h))
		for y in range(h):
			t = y / max(1, h - 1)
			grad.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
		img = grad.resize((w, h)).convert("RGBA")
		surf = pygame.image.frombytes(img.tobytes(), img.size, "RGBA")
		icon = assets.icon(game.info.icon, h * 0.42, WHITE, stroke=1.5)
		surf.blit(icon, icon.get_rect(center=(w // 2, h // 2)))
		return Image.frombytes("RGBA", (w, h), pygame.image.tobytes(surf, "RGBA"))




class Button:
	def __init__(self, kind, primary=False, enabled=True):
		self.kind, self.primary, self.enabled = kind, primary, enabled
		self.rect = pygame.Rect(0, 0, 0, 0)
		self.glow = 0.0  # focus, animated 0..1


class HDJob:
	"""launcher.hdjob for one game, in the background; its progress lines
	update the game's HD status as images are done."""

	def __init__(self, root, game):
		self.game = game
		self.state = "running"  # running, done, failed, stopped
		self.phase = "start"
		work = root / "cache" / game.info.id / "hd-work"
		kwargs = {"creationflags": NO_WINDOW} if sys.platform == "win32" else {"start_new_session": True}
		limit = ["--limit", os.environ["MULLE_HD_LIMIT"]] if os.environ.get("MULLE_HD_LIMIT") else []  # tests
		self.process = subprocess.Popen([str(job_python()), "-m", "launcher.hdjob", str(game.folder), str(work)] + limit,
			cwd=PROJECT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
			errors="replace", **kwargs)
		threading.Thread(target=self.read, daemon=True).start()

	def read(self):
		error = None
		for line in self.process.stdout:
			words = line.split()
			if not words:
				continue
			if words[0] == "PROGRESS" and len(words) == 3:
				self.game.hd = library.HDStatus(int(words[1]), int(words[2]))
			elif words[0] == "PHASE" and len(words) == 2:
				self.phase = words[1]
			elif words[0] == "DONE":
				self.state = "done"
			elif words[0] == "ERROR":
				error = line[6:].strip()
		self.process.wait()
		if self.state == "running":
			self.state = "failed" if self.process.returncode not in (0, -15, 1) or error else "stopped"
		if error and self.state != "stopped":
			print(f"launcher: HD job for {self.game.info.id}: {error}", file=sys.stderr)

	@property
	def running(self):
		return self.state == "running"

	def stop(self):
		"""Stops it with the upscaler it runs; it carries on from there next time."""
		if self.process.poll() is not None:
			return
		self.state = "stopped"
		if sys.platform == "win32":
			subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"], capture_output=True,
				creationflags=NO_WINDOW)
		else:
			try:
				os.killpg(self.process.pid, signal.SIGTERM)
			except OSError:
				pass


class Launcher:
	"""Focus moves between three rows: the quit button in the corner, the
	games, and the buttons under the focused game. Up and down change row,
	left and right move within it (in the games row: another game), A or Enter
	does what has focus (on a game: its main button), B or Escape goes back to
	the games. Only the quit button quits, at once (the user found a quit
	question ugly and confusing), so B or Escape never closes the launcher.
	The mouse moves the focus too."""

	def __init__(self, root, size=(1280, 800), fullscreen=False):
		self.root = Path(root).resolve()
		pygame.init()
		pygame.display.set_caption("Mulle Meck")
		icon = Path(__file__).with_name("icon.png")
		if icon.exists():
			pygame.display.set_icon(pygame.image.load(str(icon)))
		# Fullscreen at the desktop's resolution; everything scales with the height.
		self.screen = pygame.display.set_mode((0, 0) if fullscreen else size,
			pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
		self.assets = Assets(self.root)
		self.games, self._scan = library.scan(self.root)
		self.focus = 0  # the game in the middle
		self.pos = 0.0  # where the carousel is, animated towards focus
		self.area = "games"  # games, row, quit
		self.row_i = 0
		self.cards = {}
		self.can_make_hd = can_make_hd()
		self.backgrounds = {}
		self.bg_prev, self._bg_current, self.bg_alpha = None, None, 1.0
		self.buttons = []
		self.input = "mouse"
		self.controllers = {}
		self.toast, self.toast_until = None, 0
		self.game_process = None
		self.played = None  # the game game_process runs
		self.job = None  # one HD job at a time (one graphics card)
		self.resume_after_game = None
		self.copying = {}  # game id -> fraction copied in
		self.searching = set()  # game ids being looked for
		# The top corner: copy to Steam Deck (a PC with the Linux package, not
		# on a Deck itself) and quit.
		self.top = (["deck"] if deck.linux_package(self.root) and not deck.on_steamos() else []) + ["quit"]
		self.top_i = len(self.top) - 1
		self.top_rects = {}
		self.top_glow = {k: 0.0 for k in self.top}
		self.panel = None  # the Steam Deck panel when open
		self.deck_copy = None
		self.card_glow = 0.0
		self.card_rects = []
		self.spin = 0.0
		self.stick_until = 0
		self.clock = pygame.time.Clock()
		self.running = True
		pygame._sdl2.controller.init()
		for i in range(pygame._sdl2.controller.get_count()):
			self.open_controller(i)

	# Input --------------------------------------------------------------

	def open_controller(self, index):
		try:
			c = pygame._sdl2.controller.Controller(index)
			self.controllers[c.as_joystick().get_instance_id()] = c
		except pygame.error:
			pass

	def game(self):
		return self.games[self.focus]

	def enabled_row(self):
		return [i for i, b in enumerate(self.buttons_for(self.game())) if b.enabled]

	def navigate(self, dx, dy):
		row = self.enabled_row()
		if self.area == "games":
			if dx:
				self.focus = max(0, min(len(self.games) - 1, self.focus + dx))
			elif dy > 0 and row:
				self.area = "row"
				self.row_i = next((i for i in row if self.buttons_for(self.game())[i].primary), row[0])
			elif dy < 0:
				self.area = "top"
		elif self.area == "row":
			if dx and row:
				at = row.index(self.row_i) if self.row_i in row else 0
				self.row_i = row[max(0, min(len(row) - 1, at + dx))]
			elif dy < 0:
				self.area = "games"
		elif self.area == "top":
			if dx:
				self.top_i = max(0, min(len(self.top) - 1, self.top_i + dx))
			elif dy > 0:
				self.area = "games"

	def activate(self):
		if self.area == "top":
			if self.top[self.top_i] == "quit":
				self.running = False
			else:
				self.panel = DeckPanel(self)
		elif self.area == "games":
			b = next((b for b in self.buttons_for(self.game()) if b.primary and b.enabled), None)
			if b:
				self.do(b.kind)
		elif self.area == "row":
			buttons = self.buttons_for(self.game())
			if self.row_i < len(buttons) and buttons[self.row_i].enabled:
				self.do(buttons[self.row_i].kind)

	def back(self):
		self.area = "games"

	def handle(self, e):
		t = e.type
		if self.panel and t not in (pygame.QUIT, pygame.VIDEORESIZE, pygame.CONTROLLERDEVICEADDED):
			if t in (pygame.KEYDOWN, pygame.CONTROLLERBUTTONDOWN):
				self.input = "keyboard" if t == pygame.KEYDOWN else "pad"
			self.panel.handle(e)
			return
		if t == pygame.QUIT:
			self.running = False
		elif t == pygame.VIDEORESIZE:
			self.screen = pygame.display.set_mode(e.size, pygame.RESIZABLE)
		elif t == pygame.WINDOWFOCUSGAINED:
			self.recheck()
		elif t == pygame.CONTROLLERDEVICEADDED:
			self.open_controller(e.device_index)
		elif t == pygame.CONTROLLERBUTTONDOWN:
			self.input = "pad"
			b = e.button
			moves = {pygame.CONTROLLER_BUTTON_DPAD_LEFT: (-1, 0), pygame.CONTROLLER_BUTTON_DPAD_RIGHT: (1, 0),
				pygame.CONTROLLER_BUTTON_DPAD_UP: (0, -1), pygame.CONTROLLER_BUTTON_DPAD_DOWN: (0, 1)}
			if b in moves:
				self.navigate(*moves[b])
			elif b == pygame.CONTROLLER_BUTTON_A:
				self.activate()
			elif b == pygame.CONTROLLER_BUTTON_B:
				self.back()
		elif t == pygame.CONTROLLERAXISMOTION and e.axis in (pygame.CONTROLLER_AXIS_LEFTX, pygame.CONTROLLER_AXIS_LEFTY):
			if abs(e.value) > 20000:
				self.input = "pad"
				if time.time() > self.stick_until:
					d = 1 if e.value > 0 else -1
					self.navigate(d, 0) if e.axis == pygame.CONTROLLER_AXIS_LEFTX else self.navigate(0, d)
					self.stick_until = time.time() + 0.3
			elif abs(e.value) < 8000:
				self.stick_until = 0
		elif t == pygame.KEYDOWN:
			self.input = "keyboard"
			k = e.key
			moves = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}
			if k in moves:
				self.navigate(*moves[k])
			elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
				self.activate()
			elif k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
				self.back()
			elif k == pygame.K_F11:
				pygame.display.toggle_fullscreen()
		elif t == pygame.MOUSEMOTION:
			self.input = "mouse"
			self.point(e.pos)
		elif t == pygame.MOUSEBUTTONDOWN and e.button == 1:
			self.input = "mouse"
			if self.point(e.pos):
				self.activate()
			else:
				hit = next((i for i, r in self.card_rects if r.collidepoint(e.pos)), None)
				if hit is not None:
					self.focus, self.area = hit, "games"
		elif t == pygame.MOUSEWHEEL:
			self.navigate(-e.y if e.y else e.x, 0)

	def point(self, pos):
		"""Focus what is under the mouse. True if that is something to press."""
		for i, k in enumerate(self.top):
			if k in self.top_rects and self.top_rects[k].collidepoint(pos):
				self.area, self.top_i = "top", i
				return True
		for i, b in enumerate(self.buttons):
			if b.rect.collidepoint(pos) and b.enabled:
				self.area, self.row_i = "row", i
				return True
		focused = next((r for i, r in self.card_rects if i == self.focus), None)
		if focused and focused.collidepoint(pos):
			self.area = "games"
			return True
		return False

	# Actions ------------------------------------------------------------

	def do(self, kind):
		game = self.game()
		if kind == "play":
			self.play(game)
		elif kind == "folder":
			self.choose_files(game)
		elif kind == "hd":
			# Making: pause. Made: HD on or off for this game. Paused: go on.
			# Not started: first say what it does and how long it takes
			# (user, 2026-10-14).
			if self.job and self.job.running and self.job.game is game:
				self.job.stop()
			elif self.hd_switch(game):
				set_hd_on(self.root, game.info.id, not hd_on(self.root, game.info.id))
			elif not (self.job and self.job.running):
				if game.hd.started:
					self.start_hd(game)
				else:
					self.panel = HDPanel(self, game)

	def start_hd(self, game):
		if not (self.job and self.job.running):
			self.job = HDJob(self.root, game)

	def play(self, game):
		if self.game_process is not None:
			return
		# Still there? (The files may have gone since the launcher started.)
		if library.find_file(game.folder, game.info.marker) is None:
			self.recheck()
			self.show_toast("x")
			return
		# A copy brought in before the launcher could unpack the installer.
		if not discs.install(game.info, game.folder):
			self.show_toast("x")
			return
		# The game and the upscaler both want the graphics card: the HD job
		# waits for the game, then carries on.
		if self.job and self.job.running:
			self.job.stop()
			self.resume_after_game = self.job.game
		self.game_process = start_game(self.root, game)
		self.played = game

	def recheck(self):
		"""Are the games still where they were? (On start, on getting the focus
		back, before playing.) The HD progress of a running job comes from the job."""
		def work():
			for g in self.games:
				busy = self.job is not None and self.job.running and self.job.game is g
				g.refresh(hd=not busy)
		threading.Thread(target=work, daemon=True).start()

	def choose_files(self, game):
		"""Find the game: first by itself in the usual places (drives, Downloads,
		Desktop, Documents), then, if it is not there, in a file dialog. Disc
		images, zips, discs and copied folders all work (discs.py). The files go
		into games/<id>/, so a Steam Deck copy gets them too."""
		if game.info.id in self.copying or game.info.id in self.searching:
			return
		threading.Thread(target=self.find_game, args=(game,), daemon=True).start()

	def find_game(self, game):
		self.searching.add(game.info.id)
		try:
			source = discs.search(game.info.id).get(game.info.id)
		except Exception as e:
			print(f"launcher: search: {e}", file=sys.stderr)
			source = None
		self.searching.discard(game.info.id)
		if source is None:
			picked = pick_file()
			if not picked:
				return
			source = discs.identify(picked)
			if source is None:
				self.show_toast("x")
				return
		# A disc of another game goes to that one.
		target = next((g for g in self.games if g.info.id == source.game.id), game)
		if target is not game:
			self.focus = self.games.index(target)
		self.copying[target.info.id] = 0.0
		try:
			discs.bring_in(source, target.folder, lambda f: self.copying.__setitem__(target.info.id, f))
		except Exception as e:
			print(f"launcher: bringing in {source}: {e}", file=sys.stderr)
			self.show_toast("x")
		finally:
			self.copying.pop(target.info.id, None)
		self.cards = {k: v for k, v in self.cards.items() if k[0] != target.info.id}
		target.refresh()

	def show_toast(self, icon):
		self.toast, self.toast_until = icon, time.time() + 2.2

	# Layout and drawing -------------------------------------------------

	def background(self, game, size):
		key = (game.info.id, size, game.backdrop is not None)
		if key not in self.backgrounds:
			w, h = size
			if game.backdrop is not None:
				small = cover_fit(game.backdrop, max(1, w // 10), max(1, h // 10))
				img = small.filter(ImageFilter.GaussianBlur(2)).resize((w, h), Image.BICUBIC)
			else:
				c = game.info.color
				img = Image.new("RGB", (w, h), tuple(int(v * 0.55) for v in c))
			# Darker towards the bottom, so the white name and buttons read well.
			shade = Image.linear_gradient("L").resize((w, h)).point(lambda v: 40 + v * 0.42)
			black = Image.new("RGB", (w, h), (12, 8, 4))
			img = Image.composite(black, img, shade)
			self.backgrounds[key] = to_surface(img)
		return self.backgrounds[key]

	def card(self, game, w, h):
		key = (game.info.id, w, h, game.cover is not None)
		if key not in self.cards:
			self.cards[key] = Card(game, self.assets, w, h)
		return self.cards[key]

	def buttons_for(self, game):
		"""The row under the focused game. Found: play and HD; not found: find
		the files (no need to point at a game that is already there); not
		playable yet: an hourglass."""
		if not game.info.playable:
			return [Button("soon", primary=True, enabled=False)]
		if not game.found:
			return [Button("folder", primary=True)]
		# A game the HD job cannot make art for yet; a Steam Deck (it cannot
		# make HD art: it comes from the PC) without any for this game.
		if not game.info.hd or not (self.can_make_hd or game.hd.started):
			return [Button("play", primary=True)]
		return [Button("play", primary=True), Button("hd")]

	def hd_switch(self, game):
		"""The HD button switches the game's HD art on and off: when the art
		is all made, or on a machine that cannot make it (a Steam Deck: user,
		2026-10-14, "there is no 'HD-Bilder' toggle on the steam deck
		launcher?") whenever there is some."""
		return game.hd.complete or (not self.can_make_hd and game.hd.started)

	def job_for(self, game):
		return self.job if self.job and self.job.game is game else None

	def label(self, kind, game):
		if game.info.id in self.copying:
			return f"{round(self.copying[game.info.id] * 100)} %"
		if game.info.id in self.searching:
			return "Letar ..."
		if kind == "hd":
			job = self.job_for(game)
			if self.hd_switch(game):
				return "HD på" if hd_on(self.root, game.info.id) else "HD av"
			if job and job.running and job.phase in ("start", "extract"):
				return "Gör HD-bilder ..."
			if job and job.running:
				return f"Gör HD-bilder {math.floor(game.hd.fraction * 100)} %"
			if game.hd.started:
				return f"HD-bilder pausade {math.floor(game.hd.fraction * 100)} %"
			return "Gör HD-bilder"
		return {"play": "Spela", "folder": "Hitta spelet", "soon": "Kommer senare"}.get(kind)

	def draw(self, dt):
		W, H = self.screen.get_size()
		game = self.game()
		self.spin = (self.spin + dt * 300) % 360

		bg = self.background(game, (W, H))
		if self._bg_current is not bg:
			self.bg_prev, self._bg_current, self.bg_alpha = self._bg_current, bg, 0.0
		self.bg_alpha = min(1.0, self.bg_alpha + dt / 0.35)
		if self.bg_prev is not None and self.bg_alpha < 1:
			self.screen.blit(self.bg_prev, (0, 0))
			bg.set_alpha(int(255 * self.bg_alpha))
		self.screen.blit(bg, (0, 0))
		bg.set_alpha(None)

		# The carousel.
		self.pos += (self.focus - self.pos) * (1 - math.exp(-dt * 11))
		ch = int(H * 0.47)
		cw = ch * 4 // 3
		cy = int(H * 0.38)
		order = sorted(range(len(self.games)), key=lambda i: -abs(i - self.pos))
		self.card_rects = []
		ease = 1 - math.exp(-dt * 14)
		self.card_glow += ((1.0 if self.area == "games" else 0.0) - self.card_glow) * ease
		for i in order:
			t = i - self.pos
			a = abs(t)
			if a > 2.6:
				continue
			scale = 1 - 0.30 * min(a, 1) - 0.12 * max(0.0, min(a - 1, 1))
			x = W / 2 + math.copysign(min(a, 1) * cw * 0.92 + max(0.0, a - 1) * cw * 0.64, t)
			card = self.card(self.games[i], cw, ch)
			w, h = int(cw * scale), int(ch * scale)
			img = pygame.transform.smoothscale(card.image, (w, h)) if scale < 0.999 else card.image
			pad = int(card.pad * scale)
			shadow = pygame.transform.smoothscale(card.shadow, (w + 2 * pad, h + 2 * pad))
			dim = 1 - 0.42 * min(a, 1) - 0.35 * max(0.0, min(a - 1, 1))
			rect = img.get_rect(center=(int(x), cy))
			shadow.set_alpha(int(255 * dim))
			self.screen.blit(shadow, (rect.x - pad, rect.y - pad))
			if i == self.focus and a < 0.05 and self.card_glow > 0.02:
				frame = self.assets.frame(w, h, max(6, int(h * 0.05)), max(3, int(H * 0.006)))
				frame.set_alpha(int(240 * self.card_glow))
				self.screen.blit(frame, frame.get_rect(center=rect.center))
			if dim < 0.999:
				img = img.copy()
				img.fill((int(255 * dim),) * 3 + (255,), special_flags=pygame.BLEND_RGBA_MULT)
			self.screen.blit(img, rect)
			self.card_rects.append((i, rect))
			gid = self.games[i].info.id
			if gid in self.copying or gid in self.searching:
				d, width = min(w, h) * 0.3, max(3, h * 0.025)
				ring = self.assets.ring(d, width, self.copying.get(gid, 0.0), YELLOW)
				self.screen.blit(ring, ring.get_rect(center=rect.center))
				if gid in self.searching:
					arc = pygame.transform.rotate(self.assets.arc(d, width, 70, WHITE), -self.spin)
					self.screen.blit(arc, arc.get_rect(center=rect.center))

		# Name, buttons and the word for what has focus.
		top = cy + ch // 2 + int(H * 0.035)
		title = self.assets.text(game.info.title, H * 0.052)
		self.screen.blit(title, title.get_rect(midtop=(W // 2, top)))
		self.layout_buttons(game, W, top + int(H * 0.085), H)
		for i, b in enumerate(self.buttons):
			focused = self.area == "row" and i == self.row_i
			self.draw_button(b, game, focused, dt, H)
		kind = None
		if self.area == "row" and self.row_i < len(self.buttons):
			kind = self.buttons[self.row_i].kind
		elif self.area == "games":
			kind = next((b.kind for b in self.buttons if b.primary), None)
		word = self.label(kind, game) if kind else None
		if word and self.buttons:
			s = self.assets.text(word, H * 0.032, (255, 236, 200))
			bottom = max(b.rect.bottom for b in self.buttons)
			r = self.screen.blit(s, s.get_rect(midtop=(W // 2, bottom + int(H * 0.018))))
			# What "find the game" takes (the user: make the formats clear).
			if kind == "folder" and game.info.id not in self.copying and game.info.id not in self.searching:
				f = self.assets.text("iso  ·  zip  ·  cd  ·  mapp", H * 0.024, (230, 214, 186))
				self.screen.blit(f, f.get_rect(midtop=(W // 2, r.bottom + int(H * 0.004))))

		# Where in the row of games.
		n = len(self.games)
		gap = int(H * 0.026)
		x0 = W // 2 - (n - 1) * gap // 2
		for i in range(n):
			d = max(4, int(H * 0.009)) * (1.6 if i == self.focus else 1)
			c = self.assets.circle(d, WHITE, 235 if i == self.focus else 110)
			self.screen.blit(c, c.get_rect(center=(x0 + i * gap, int(H * 0.972))))

		# The top corner: Steam Deck, quit.
		d, gap = int(H * 0.06), int(H * 0.03)
		x = W - gap - d
		for i in reversed(range(len(self.top))):
			k = self.top[i]
			rect = pygame.Rect(x, gap, d, d)
			self.top_rects[k] = rect
			x -= d + gap
			on = self.area == "top" and self.top_i == i and not self.panel
			self.top_glow[k] += ((1.0 if on else 0.0) - self.top_glow[k]) * ease
			glow = self.top_glow[k]
			if glow > 0.02:
				ring = self.assets.focus_ring(d, H)
				ring.set_alpha(int(255 * glow))
				self.screen.blit(ring, ring.get_rect(center=rect.center))
			c = self.assets.circle(d, (255, 255, 255) if glow > 0.5 else (70, 60, 52), 255 if glow > 0.5 else 150)
			self.screen.blit(c, rect)
			ic = self.assets.icon("x" if k == "quit" else "gamepad-2", d * (0.5 if k == "quit" else 0.56),
				INK if glow > 0.5 else WHITE, stroke=2.5 if k == "quit" else 2.2)
			self.screen.blit(ic, ic.get_rect(center=rect.center))
			# A copy going on in the background: its ring round the Deck button.
			if k == "deck" and self.deck_copy and self.deck_copy.state in ("copying", "steam"):
				ring = self.assets.ring(d + H * 0.018, H * 0.006, self.deck_copy.progress, YELLOW)
				self.screen.blit(ring, ring.get_rect(center=rect.center))
		if self.area == "top" and not self.panel and self.top[self.top_i] == "deck":
			s = self.assets.text("Kopiera till Steam Deck", H * 0.028, (255, 236, 200))
			r = self.top_rects["deck"]
			self.screen.blit(s, s.get_rect(topright=(self.top_rects["quit"].right, r.bottom + int(H * 0.02))))

		if self.toast and time.time() < self.toast_until:
			d = H * 0.13
			c = self.assets.circle(d, RED)
			r = c.get_rect(center=(W // 2, cy))
			self.screen.blit(c, r)
			ic = self.assets.icon(self.toast, d * 0.55, WHITE, stroke=3)
			self.screen.blit(ic, ic.get_rect(center=r.center))

	def layout_buttons(self, game, W, y, H):
		wanted = self.buttons_for(game)
		if [(b.kind, b.primary, b.enabled) for b in wanted] != [(b.kind, b.primary, b.enabled) for b in self.buttons]:
			self.buttons = wanted
			self.row_i = min(self.row_i, len(wanted) - 1)
		d, dp, gap = int(H * 0.085), int(H * 0.105), int(H * 0.04)
		sizes = [dp if b.primary else d for b in self.buttons]
		x = W // 2 - (sum(sizes) + gap * (len(sizes) - 1)) // 2
		for b, s in zip(self.buttons, sizes):
			b.rect = pygame.Rect(x, y + (dp - s) // 2, s, s)
			x += s + gap

	def draw_button(self, b, game, focused, dt, H):
		b.glow += ((1.0 if focused else 0.0) - b.glow) * (1 - math.exp(-dt * 14))
		s = b.rect.width * (1 + 0.08 * b.glow)
		center = b.rect.center
		fill = YELLOW if b.primary and b.enabled else PAPER
		if not b.enabled:
			fill = (190, 182, 166)
		if b.glow > 0.02:
			ring = self.assets.focus_ring(b.rect.width, H)
			ring.set_alpha(int(255 * b.glow))
			self.screen.blit(ring, ring.get_rect(center=center))
		self.screen.blit(disc := self.assets.circle(s, fill, 250), disc.get_rect(center=center))
		ink = INK if b.enabled else (120, 108, 92)
		if b.kind == "play":
			ic = self.assets.icon("play", s * 0.44, ink, filled=True)
			self.screen.blit(ic, ic.get_rect(center=(center[0] + s * 0.03, center[1])))
		elif b.kind == "hd":
			self.draw_hd(game, s, center, ink, H)
		else:
			name = {"folder": "folder-open", "soon": "hourglass"}[b.kind]
			ic = self.assets.icon(name, s * 0.46, ink)
			self.screen.blit(ic, ic.get_rect(center=center))

	def draw_hd(self, game, s, center, ink, H):
		"""The HD button: "HD" in a ring that fills as the images are done; a
		turning arc while the job runs, a green tick when all are done, a red
		cross if the job failed (pressing again tries again)."""
		job = self.job_for(game)
		d, width = s + H * 0.018, H * 0.008
		switch = self.hd_switch(game)
		off = switch and not hd_on(self.root, game.info.id)
		color = (150, 138, 120) if off else GREEN if switch else YELLOW
		ring = self.assets.ring(d, width, game.hd.fraction, color)
		self.screen.blit(ring, ring.get_rect(center=center))
		if job and job.running:
			arc = pygame.transform.rotate(self.assets.arc(d, width, 70, WHITE), -self.spin)
			self.screen.blit(arc, arc.get_rect(center=center))
		elif game.hd.started and not switch:
			# Paused: the pause sign next to the ring.
			bd = s * 0.38
			c = self.assets.circle(bd, YELLOW)
			br = c.get_rect(center=(center[0] + s * 0.36, center[1] - s * 0.36))
			self.screen.blit(c, br)
			ic = self.assets.icon("pause", bd * 0.6, INK, stroke=3)
			self.screen.blit(ic, ic.get_rect(center=br.center))
		# While making or paused, the progress in the ring itself, so it shows
		# without the button having focus (user, 2026-10-14).
		if not switch and (game.hd.started or (job and job.running)):
			t = self.assets.text(f"{math.floor(game.hd.fraction * 100)}%", s * 0.27, ink, shadow=False)
		else:
			t = self.assets.text("HD", s * 0.36, (150, 138, 120) if off else ink, shadow=False)
		self.screen.blit(t, t.get_rect(center=(center[0], center[1] + s * 0.02)))
		badge = None
		if switch and not off:
			badge = (GREEN, "check")
		elif job and job.state == "failed":
			badge = (RED, "x")
		if badge:
			bd = s * 0.38
			c = self.assets.circle(bd, badge[0])
			br = c.get_rect(center=(center[0] + s * 0.36, center[1] - s * 0.36))
			self.screen.blit(c, br)
			ic = self.assets.icon(badge[1], bd * 0.64, WHITE, stroke=3.5)
			self.screen.blit(ic, ic.get_rect(center=br.center))

	# Main loop ------------------------------------------------------------

	def run(self, shot=None, frames=None):
		count = 0
		scanned = time.time()
		while self.running:
			dt = self.clock.tick(60) / 1000
			for e in pygame.event.get():
				self.handle(e)
			if self.game_process is not None and self.game_process.poll() is not None:
				self.game_process = None
				# F6 in the game switches HD too (hd.cpp toggleArt() writes
				# it to scummvm.ini): the HD button keeps what it was left at.
				shown = ini_get(self.root, "hd_art")
				if shown is not None and self.hd_switch(self.played):
					set_hd_on(self.root, self.played.info.id, shown == "true")
				self.recheck()
				if self.resume_after_game is not None and not self.resume_after_game.hd.complete:
					self.job = HDJob(self.root, self.resume_after_game)
				self.resume_after_game = None
			self.draw(dt)
			if self.panel:
				self.panel.draw(self.screen, self.assets, self.spin)
			pygame.display.flip()
			count += 1
			if self._scan.is_alive():
				scanned = time.time()
			elif shot and count >= frames and time.time() - scanned > 0.6:  # the cross-fade has finished
				pygame.image.save(self.screen, str(shot))
				break
			if self.game_process is not None:
				time.sleep(0.05)  # the game has the screen
		if self.job:
			self.job.stop()
		pygame.quit()


def can_make_hd():
	"""Whether HD art can be made here: the image maths (numpy) and the
	upscaler. The Steam Deck's copy has neither (deck.NOT_ON_DECK_LIBS); it
	gets the HD art with the copy from the PC."""
	import importlib.util
	esr = PROJECT / "third_party" / "realesrgan-ncnn-vulkan"
	return importlib.util.find_spec("numpy") is not None and esr.is_dir()


def job_python():
	"""The Python for the HD job: a console one (output to the launcher through
	a pipe), started without a window."""
	exe = Path(sys.executable)
	if exe.name.lower() == "pythonw.exe" and exe.with_name("python.exe").exists():
		return exe.with_name("python.exe")
	return exe


def scummvm(root):
	"""Our ScummVM build for this system: next to the launcher, or
	MULLE_SCUMMVM, or (developing) the Linux build in ~/src/scummvm."""
	candidates = [Path(root) / ("scummvm.exe" if sys.platform == "win32" else "scummvm")]
	if os.environ.get("MULLE_SCUMMVM"):
		candidates.insert(0, Path(os.environ["MULLE_SCUMMVM"]))
	if sys.platform != "win32":
		candidates.append(Path.home() / "src" / "scummvm" / "scummvm")
	return next((p for p in candidates if p.is_file()), None)


def fullscreen_setting(root):
	"""ScummVM's fullscreen setting ([scummvm] fullscreen in scummvm.ini),
	true when not set yet (user, 2026-10-14: "fullscreen mode for the games
	should be default"). The launcher follows it too. Written into the file
	when missing, so a fresh install starts the games fullscreen; the pause
	menu's Helskärm / Visa i fönster changes it."""
	ini = Path(root) / "scummvm.ini"
	lines = ini.read_text(encoding="utf-8", errors="replace").splitlines() if ini.exists() else []
	section = None
	for line in lines:
		t = line.strip()
		if t.startswith("[") and t.endswith("]"):
			section = t[1:-1].lower()
		elif section == "scummvm" and t.lower().startswith("fullscreen="):
			return t.split("=", 1)[1].strip().lower() in ("true", "1", "yes")
	at = next((i + 1 for i, line in enumerate(lines) if line.strip().lower() == "[scummvm]"), None)
	if at is None:
		lines = ["[scummvm]"] + lines
		at = 1
	lines.insert(at, "fullscreen=true")
	try:
		ini.write_text("\n".join(lines) + "\n", encoding="utf-8")
	except OSError:
		pass
	return True


def load_settings(root):
	"""The launcher's own settings (launcher.json; the Steam Deck panel keeps
	its address and place there too)."""
	try:
		return json.loads((Path(root) / "launcher.json").read_text(encoding="utf-8"))
	except (OSError, ValueError):
		return {}


def hd_on(root, game_id):
	"""Whether a game's HD art is shown (the HD button once the art is made;
	on unless switched off)."""
	return game_id not in load_settings(root).get("hd_off", [])


def set_hd_on(root, game_id, on):
	s = load_settings(root)
	off = set(s.get("hd_off", []))
	(off.discard if on else off.add)(game_id)
	s["hd_off"] = sorted(off)
	try:
		(Path(root) / "launcher.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
	except OSError:
		pass


def ini_get(root, key):
	"""[scummvm] key in scummvm.ini, or None."""
	ini = Path(root) / "scummvm.ini"
	section = None
	try:
		lines = ini.read_text(encoding="utf-8", errors="replace").splitlines()
	except OSError:
		return None
	for line in lines:
		t = line.strip()
		if t.startswith("[") and t.endswith("]"):
			section = t[1:-1].lower()
		elif section == "scummvm" and t.lower().startswith(key + "="):
			return t.split("=", 1)[1].strip().lower()
	return None


def ini_set(root, key, value):
	"""Sets [scummvm] key=value in scummvm.ini."""
	ini = Path(root) / "scummvm.ini"
	lines = ini.read_text(encoding="utf-8", errors="replace").splitlines() if ini.exists() else []
	section, done = None, False
	for i, line in enumerate(lines):
		t = line.strip()
		if t.startswith("[") and t.endswith("]"):
			section = t[1:-1].lower()
		elif section == "scummvm" and t.lower().startswith(key + "="):
			lines[i], done = f"{key}={value}", True
	if not done:
		at = next((i + 1 for i, line in enumerate(lines) if line.strip().lower() == "[scummvm]"), None)
		if at is None:
			lines, at = ["[scummvm]"] + lines, 1
		lines.insert(at, f"{key}={value}")
	try:
		ini.write_text("\n".join(lines) + "\n", encoding="utf-8")
	except OSError:
		pass


def start_game(root, game):
	"""Starts the game in our ScummVM build (the HD art is found as HD/ in the
	game's folder; shown or not as the HD button says). Returns the process,
	or None without ScummVM."""
	root = Path(root).resolve()
	ini_set(root, "hd_art", "true" if hd_on(root, game.info.id) else "false")
	# Steam's on-screen keyboard: opened by clicking a name field on SteamOS
	# (our ScummVM, screen_keyboard=steam), never by itself when the game
	# starts (SDL starts text input with the window; on a Steam Deck that
	# opened the keyboard, which then took the controls; user, 2026-10-14).
	ini_set(root, "screen_keyboard", "steam" if deck.on_steamos() else "none")
	exe = scummvm(root)
	if exe is None:
		return None
	(root / "saves").mkdir(exist_ok=True)
	fullscreen_setting(root)
	args = [str(exe), f"--config={root / 'scummvm.ini'}", f"--path={game.folder}", "--auto-detect",
		f"--savepath={root / 'saves'}", f"--extrapath={root / 'data'}", "--scale-factor=2"]
	return subprocess.Popen(args, cwd=root, env=dict(os.environ, SDL_ENABLE_SCREEN_KEYBOARD="0"))


# The file dialog says what it takes (the user: make the formats clear).
PICK_TITLE = "Hitta spelet: en skivavbild (.iso), en zip-fil eller en fil från skivan eller mappen"
PICK_FILTER_NAME = "Mulle Meck-spel (.iso, .zip, .exe)"


def pick_file():
	"""A disc image, zip or any file of the game, chosen in the system's own
	dialog, or None."""
	if sys.platform == "win32":
		# The packaged Python has no tkinter: Windows' own dialog through
		# PowerShell, its output as UTF-8 (names like "Upptäck rymden").
		script = ("[Console]::OutputEncoding = [Text.Encoding]::UTF8;"
			"Add-Type -AssemblyName System.Windows.Forms;"
			"$d = New-Object System.Windows.Forms.OpenFileDialog;"
			f"$d.Title = '{PICK_TITLE}';"
			f"$d.Filter = '{PICK_FILTER_NAME}|*.iso;*.zip;*.exe|Alla filer (*.*)|*.*';"
			"if ($d.ShowDialog() -eq 'OK') { $d.FileName }")
		out = subprocess.run(["powershell.exe", "-NoProfile", "-STA", "-Command", script], capture_output=True,
			encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
		return out.stdout.strip() or None
	if sys.platform.startswith("linux"):
		for cmd in (["zenity", "--file-selection", f"--title={PICK_TITLE}",
				f"--file-filter={PICK_FILTER_NAME} | *.iso *.ISO *.zip *.ZIP *.exe *.EXE", "--file-filter=* | *"],
				["kdialog", "--title", PICK_TITLE, "--getopenfilename", str(Path.home()),
				f"*.iso *.ISO *.zip *.ZIP *.exe *.EXE|{PICK_FILTER_NAME}"]):
			try:
				out = subprocess.run(cmd, capture_output=True, text=True)
			except FileNotFoundError:
				continue
			return out.stdout.strip() or None
	try:
		import tkinter
		from tkinter import filedialog
		tk = tkinter.Tk()
		tk.withdraw()
		name = filedialog.askopenfilename(title=PICK_TITLE,
			filetypes=[(PICK_FILTER_NAME, "*.iso *.zip *.exe"), ("Alla filer", "*")])
		tk.destroy()
		return name or None
	except Exception:
		return None
