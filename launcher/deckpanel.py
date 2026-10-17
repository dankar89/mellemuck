"""The "copy to Steam Deck" panel (deck.py does the work).

Steps (user, 2026-10-14: verify the connection before choosing where; browse
the Deck): connect (the Deck's address and, the first time, its password;
with the launcher's key from an earlier copy it connects by itself), choose
where (places with their free space: home, Games, microSD cards; then the
folders, ".." to go up; the copy goes into a "Mulle Meck" folder there, or
into the one the user is in), then the copy and Steam's library, and a tick
or a red cross with what to do.

Text fields edit like text fields: the cursor moves with the arrows, Home,
End and the mouse; Backspace and Delete; Ctrl+V pastes. Focus moves with
up/down (Tab), the D-pad or the mouse; Enter or A presses; Escape or B goes a
step back. A copy goes on if the panel is closed, its ring on the corner
button. The address and the place are remembered in launcher.json; the
password never is (after the first copy the launcher's key is used).
"""
import json
import math
import os
import posixpath
import shlex
import sys
import threading

import pygame

from . import deck, steamart

INK = (74, 46, 23)
SOFT_INK = (120, 92, 60)
PAPER = (255, 243, 214)
YELLOW = (255, 197, 49)
GREEN = (61, 170, 74)
RED = (217, 68, 58)
WHITE = (255, 255, 255)
FIELD = (255, 251, 240)
ROW = (247, 232, 200)
BACK_FILL = (242, 212, 155)

ROWS_SHOWN = 6


def size_text(n):
	if n is None:
		return "?"
	gb = n / 1e9
	return f"{gb:.1f} GB".replace(".", ",") if gb >= 1 else f"{n / 1e6:.0f} MB"


class TextField:
	def __init__(self, text="", secret=False):
		self.text, self.pos, self.secret = text, len(text), secret

	def shown(self):
		return "•" * len(self.text) if self.secret else self.text

	def insert(self, s):
		s = s.replace("\n", "").replace("\r", "")
		self.text = self.text[:self.pos] + s + self.text[self.pos:]
		self.pos += len(s)

	def key(self, e):
		"""A key event on the focused field. True if it used it."""
		ctrl = e.mod & pygame.KMOD_CTRL
		if e.key == pygame.K_LEFT:
			self.pos = self.word_left() if ctrl else max(0, self.pos - 1)
		elif e.key == pygame.K_RIGHT:
			self.pos = self.word_right() if ctrl else min(len(self.text), self.pos + 1)
		elif e.key == pygame.K_HOME:
			self.pos = 0
		elif e.key == pygame.K_END:
			self.pos = len(self.text)
		elif e.key == pygame.K_BACKSPACE:
			start = self.word_left() if ctrl else max(0, self.pos - 1)
			self.text, self.pos = self.text[:start] + self.text[self.pos:], start
		elif e.key == pygame.K_DELETE:
			end = self.word_right() if ctrl else min(len(self.text), self.pos + 1)
			self.text = self.text[:self.pos] + self.text[end:]
		elif e.key == pygame.K_v and ctrl:
			self.insert(paste())
		else:
			return False
		return True

	def word_left(self):
		p = self.pos
		while p > 0 and self.text[p - 1] in " /.":
			p -= 1
		while p > 0 and self.text[p - 1] not in " /.":
			p -= 1
		return p

	def word_right(self):
		p, n = self.pos, len(self.text)
		while p < n and self.text[p] in " /.":
			p += 1
		while p < n and self.text[p] not in " /.":
			p += 1
		return p

	def click(self, x, font):
		"""Put the cursor at x pixels from the text's start."""
		shown = self.shown()
		best, best_d = 0, abs(x)
		for i in range(1, len(shown) + 1):
			d = abs(font.size(shown[:i])[0] - x)
			if d < best_d:
				best, best_d = i, d
		self.pos = best


def paste():
	try:
		if hasattr(pygame.scrap, "get_text"):
			return pygame.scrap.get_text() or ""
	except pygame.error:
		pass
	return ""


class DeckPanel:
	def __init__(self, launcher):
		self.app = launcher
		settings = self.load()
		self.host = TextField(settings.get("deck_host", deck.DEFAULT_HOST))
		self.password = TextField(secret=True)
		self.place = settings.get("deck_place")  # the folder last browsed to
		self.step = "connect"  # connect, connecting, choose, copy
		self.error = None
		self.session = None
		self.focus = 1 if self.host.text else 0
		self.items = []  # (target, rect) for the mouse
		self.shift = {}  # how far each text field's text is scrolled
		self.places, self.path, self.folders, self.row, self.scroll = [], "", [], 0, 0
		self.area = "list"  # in choose: places, list, buttons
		self.place_i = self.button_i = 0
		self.free, self.needed = None, None
		self.busy = False
		self.copy = launcher.deck_copy if launcher.deck_copy and launcher.deck_copy.state in ("copying", "steam") else None
		if self.copy:
			self.step = "copy"
		elif self.host.text and self.new_session().key():
			self.connect()  # an earlier copy left our key on the Deck: no password needed
		pygame.key.start_text_input()

	# Settings -------------------------------------------------------------

	def settings_path(self):
		return self.app.root / "launcher.json"

	def load(self):
		try:
			return json.loads(self.settings_path().read_text(encoding="utf-8"))
		except (OSError, ValueError):
			return {}

	def save(self):
		s = self.load()
		s.update(deck_host=self.host.text.strip(), deck_place=self.path)
		try:
			self.settings_path().write_text(json.dumps(s, indent=1), encoding="utf-8")
		except OSError:
			pass

	# Work in the background -----------------------------------------------

	def work(self, fn):
		def run():
			self.busy = True
			try:
				fn()
			except deck.DeckError as e:
				self.error, self.step = e.kind, "connect"
			except Exception as e:
				print(f"launcher: Steam Deck: {e}", file=sys.stderr)
				self.error, self.step = "other", "connect"
			finally:
				self.busy = False
		threading.Thread(target=run, daemon=True).start()

	def new_session(self):
		env = os.environ  # tests: a stand-in server (MULLE_DECK_PORT, _USER, _KEY)
		return deck.Session(self.host.text, user=env.get("MULLE_DECK_USER", deck.USER),
			port=int(env.get("MULLE_DECK_PORT", 22)), key_file=env.get("MULLE_DECK_KEY"))

	def connect(self):
		self.step, self.error = "connecting", None
		session = self.new_session()

		def go():
			session.connect(self.password.text)
			self.session = session
			self.places = session.places()
			self.open(self.place or self.places[1][2])
			self.needed = sum(p.stat().st_size for p, _, _ in deck.files_to_send(self.app.root, self.found()))
			self.step, self.area = "choose", "list"
			self.save()
		self.work(go)

	def found(self):
		return [g for g in self.app.games if g.found]

	def open(self, path):
		"""Show path's folders (the nearest existing folder if it is gone)."""
		s = self.session
		while path not in ("", "/") and s.run(f"test -d {shlex.quote(path)}")[0] != 0:
			path = posixpath.dirname(path)
		path = path or s.home
		folders, free = s.folders(path), s.free(path)
		# All at once: the screen is drawn meanwhile.
		self.path, self.folders, self.free, self.row, self.scroll = path, folders, free, 0, 0

	def dest(self):
		"""Where the copy goes: a Mulle Meck folder here, or this one if it is one."""
		if posixpath.basename(self.path) == deck.INSTALL_NAME:
			return self.path
		return posixpath.join(self.path, deck.INSTALL_NAME)

	def start_copy(self):
		self.save()
		steamart.make(self.app.root, self.app.games)
		self.copy = deck.DeckCopy(self.session, self.app.root, self.found(), self.dest())
		self.app.deck_copy = self.copy
		self.step, self.focus = "copy", 0

	# Focus targets ---------------------------------------------------------

	def targets(self):
		"""The focusable things in the current step, in order (connect and copy)."""
		if self.step == "connect":
			return ["host", "password", "connect", "close"]
		if self.step == "connecting":
			return ["close"]
		if self.step == "copy":
			if self.copy.state == "copying":
				return ["hide", "cancel"]
			if self.copy.state == "steam":
				return ["hide"]
			if self.copy.state == "done":
				return ["ok"]
			return ["retry", "close"]
		return []

	def close(self):
		pygame.key.stop_text_input()
		self.app.panel = None

	def back(self):
		if self.step == "choose":
			self.step, self.focus = "connect", 1
		else:
			self.close()

	def field(self, name):
		return {"host": self.host, "password": self.password}.get(name)

	def press(self, kind):
		if kind == "connect":
			if self.host.text.strip():
				self.connect()
		elif kind in ("close", "hide", "ok"):
			self.close()
		elif kind == "back":
			self.back()
		elif kind == "cancel":
			self.copy.cancel()
		elif kind == "retry":
			self.step, self.copy = "choose", None
		elif kind in ("host", "password"):
			self.focus += 1
		elif kind == "copyhere":
			self.start_copy()
		elif kind == "up":
			self.work(lambda: self.open(posixpath.dirname(self.path) or "/"))
		elif kind and kind.startswith("place:"):
			path = self.places[int(kind[6:])][2]
			self.work(lambda: self.open(path))
		elif kind and kind.startswith("folder:"):
			path = posixpath.join(self.path, kind[7:])
			self.work(lambda: self.open(path))

	# Input ------------------------------------------------------------------

	def choose_rows(self):
		"""The folder list: going up first (unless at the top), then the folders."""
		rows = [] if self.path in ("/", "") else ["up"]
		return rows + ["folder:" + f for f in self.folders]

	def handle(self, e):
		if self.busy:
			return
		if self.step == "choose":
			return self.handle_choose(e)
		targets = self.targets()
		self.focus = max(0, min(self.focus, len(targets) - 1))
		kind = targets[self.focus] if targets else None
		f = self.field(kind)
		t = e.type
		if t == pygame.KEYDOWN:
			if f and f.key(e):
				return
			if e.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
				d = -1 if e.key == pygame.K_UP or (e.key == pygame.K_TAB and e.mod & pygame.KMOD_SHIFT) else 1
				self.focus = (self.focus + d) % len(targets)
			elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
				self.focus = (self.focus + (1 if e.key == pygame.K_RIGHT else -1)) % len(targets)
			elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
				self.press("connect" if f else kind)
			elif e.key == pygame.K_ESCAPE:
				self.back()
		elif t == pygame.TEXTINPUT and f:
			f.insert(e.text)
		elif t == pygame.CONTROLLERBUTTONDOWN:
			b = e.button
			if b in (pygame.CONTROLLER_BUTTON_DPAD_UP, pygame.CONTROLLER_BUTTON_DPAD_LEFT):
				self.focus = (self.focus - 1) % len(targets)
			elif b in (pygame.CONTROLLER_BUTTON_DPAD_DOWN, pygame.CONTROLLER_BUTTON_DPAD_RIGHT):
				self.focus = (self.focus + 1) % len(targets)
			elif b == pygame.CONTROLLER_BUTTON_A:
				self.press(kind)
			elif b in (pygame.CONTROLLER_BUTTON_B, pygame.CONTROLLER_BUTTON_BACK):
				self.back()
		elif t == pygame.MOUSEMOTION:
			for k, rect in self.items:
				if rect.collidepoint(e.pos) and k in targets and not self.field(k):
					self.focus = targets.index(k)
		elif t == pygame.MOUSEBUTTONDOWN and e.button == 1:
			for k, rect in self.items:
				if rect.collidepoint(e.pos) and k in targets:
					self.focus = targets.index(k)
					if self.field(k):
						inner = rect.inflate(-rect.height * 0.6, 0)
						self.field(k).click(e.pos[0] - inner.left + self.shift.get(k, 0), self.app.assets.font(self.font_size()))
					else:
						self.press(k)
					return

	def handle_choose(self, e):
		rows = self.choose_rows()
		t = e.type
		move = None
		if t == pygame.KEYDOWN:
			move = {pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)}.get(e.key)
			if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
				self.press(self.choose_focus())
			elif e.key == pygame.K_BACKSPACE and self.path not in ("/", ""):
				self.press("up")
			elif e.key == pygame.K_ESCAPE:
				self.back()
			elif e.key == pygame.K_TAB:
				self.area = {"places": "list", "list": "buttons", "buttons": "places"}[self.area]
		elif t == pygame.CONTROLLERBUTTONDOWN:
			move = {pygame.CONTROLLER_BUTTON_DPAD_UP: (0, -1), pygame.CONTROLLER_BUTTON_DPAD_DOWN: (0, 1),
				pygame.CONTROLLER_BUTTON_DPAD_LEFT: (-1, 0), pygame.CONTROLLER_BUTTON_DPAD_RIGHT: (1, 0)}.get(e.button)
			if e.button == pygame.CONTROLLER_BUTTON_A:
				self.press(self.choose_focus())
			elif e.button in (pygame.CONTROLLER_BUTTON_B, pygame.CONTROLLER_BUTTON_BACK):
				self.back()
		elif t == pygame.MOUSEWHEEL:
			self.scroll = max(0, min(max(0, len(rows) - ROWS_SHOWN), self.scroll - e.y))
		elif t in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
			for k, rect in self.items:
				if rect.collidepoint(e.pos):
					self.focus_kind(k)
					if t == pygame.MOUSEBUTTONDOWN and e.button == 1:
						self.press(k)
					return
		if move:
			dx, dy = move
			if self.area == "places":
				if dx:
					self.place_i = max(0, min(len(self.places) - 1, self.place_i + dx))
				elif dy > 0:
					self.area = "list" if rows else "buttons"
			elif self.area == "list":
				if dy < 0 and self.row == 0:
					self.area = "places"
				elif dy > 0 and self.row >= len(rows) - 1:
					self.area = "buttons"
				elif dy:
					self.row = max(0, min(len(rows) - 1, self.row + dy))
				self.scroll = max(min(self.scroll, self.row), self.row - ROWS_SHOWN + 1)
			elif self.area == "buttons":
				if dx:
					self.button_i = max(0, min(1, self.button_i + dx))
				elif dy < 0:
					self.area = "list" if rows else "places"

	def choose_focus(self):
		rows = self.choose_rows()
		if self.area == "places":
			return f"place:{self.place_i}"
		if self.area == "list":
			return rows[min(self.row, len(rows) - 1)] if rows else None
		return ("copyhere", "back")[self.button_i]

	def focus_kind(self, k):
		rows = self.choose_rows()
		if k.startswith("place:"):
			self.area, self.place_i = "places", int(k[6:])
		elif k in rows:
			self.area, self.row = "list", rows.index(k)
		elif k in ("copyhere", "back"):
			self.area, self.button_i = "buttons", ("copyhere", "back").index(k)

	def font_size(self):
		return self.app.screen.get_height() * 0.032

	# Drawing --------------------------------------------------------------

	def draw(self, screen, assets, spin):
		W, H = screen.get_size()
		veil = pygame.Surface((W, H), pygame.SRCALPHA)
		veil.fill((10, 6, 2, 200))
		screen.blit(veil, (0, 0))
		pw, ph = int(H * 0.9), int(H * 0.86)
		panel = pygame.Rect(0, 0, pw, ph)
		panel.center = (W // 2, H // 2)
		pygame.draw.rect(screen, PAPER, panel, border_radius=int(H * 0.03))
		self.items, self.shift = [], {}
		self.assets, self.spin, self.H = assets, spin, H

		ic = assets.icon("gamepad-2", H * 0.065, INK, stroke=2)
		title = assets.text("Kopiera till Steam Deck", H * 0.04, INK, shadow=False)
		total = ic.get_width() + H * 0.02 + title.get_width()
		x = panel.centerx - total / 2
		ty = panel.top + H * 0.06
		screen.blit(ic, ic.get_rect(midleft=(x, ty)))
		screen.blit(title, title.get_rect(midleft=(x + ic.get_width() + H * 0.02, ty)))

		if self.step in ("connect", "connecting"):
			self.draw_connect(screen, panel)
		elif self.step == "choose":
			self.draw_choose(screen, panel)
		else:
			self.draw_copy(screen, panel)
		if self.busy and self.step == "choose":
			arc = pygame.transform.rotate(assets.arc(H * 0.05, H * 0.008, 80, INK), -spin)
			screen.blit(arc, arc.get_rect(center=(panel.right - H * 0.06, ty)))

	def spinner(self, screen, center, d, text=None, progress=None):
		a, H = self.assets, self.H
		ring = a.ring(d, H * 0.016, progress or 0.0, YELLOW, track=(74, 46, 23, 50))
		screen.blit(ring, ring.get_rect(center=center))
		arc = pygame.transform.rotate(a.arc(d, H * 0.016, 70, INK), -self.spin)
		screen.blit(arc, arc.get_rect(center=center))
		if text:
			t = a.text(text, H * 0.04, INK, shadow=False)
			screen.blit(t, t.get_rect(center=center))

	def button(self, screen, kind, rect, icon, word, fill, focused):
		a, H = self.assets, self.H
		if focused:
			pygame.draw.rect(screen, INK, rect.inflate(H * 0.014, H * 0.014), border_radius=rect.height)
		pygame.draw.rect(screen, fill, rect, border_radius=rect.height // 2)
		fg = WHITE if fill == GREEN else INK
		ic = a.icon(icon, rect.height * 0.45, fg, stroke=2.5)
		t = a.text(word, H * 0.03, fg, shadow=False)
		wsum = ic.get_width() + H * 0.012 + t.get_width()
		cx = rect.centerx - wsum / 2
		screen.blit(ic, ic.get_rect(midleft=(cx, rect.centery)))
		screen.blit(t, t.get_rect(midleft=(cx + ic.get_width() + H * 0.012, rect.centery)))
		self.items.append((kind, rect))

	def buttons(self, screen, panel, row, focused):
		H = self.H
		bw, bh, gap = int(H * 0.25), int(H * 0.072), int(H * 0.03)
		x = panel.centerx - (len(row) * bw + (len(row) - 1) * gap) // 2
		y = panel.bottom - int(H * 0.045) - bh
		for kind, icon, word, fill in row:
			self.button(screen, kind, pygame.Rect(x, y, bw, bh), icon, word, fill, focused == kind)
			x += bw + gap

	def draw_connect(self, screen, panel):
		a, H = self.assets, self.H
		targets = self.targets()
		focused = targets[min(self.focus, len(targets) - 1)]
		if self.step == "connecting":
			self.spinner(screen, (panel.centerx, panel.top + int(panel.height * 0.43)), H * 0.2)
			t = a.text("Ansluter till " + self.host.text.strip(), H * 0.03, INK, shadow=False)
			screen.blit(t, t.get_rect(midtop=(panel.centerx, panel.top + int(panel.height * 0.6))))
			self.buttons(screen, panel, [("close", "undo-2", "Tillbaka", BACK_FILL)], focused)
			return
		fw, fh = int(panel.width * 0.8), int(H * 0.068)
		y = panel.top + int(H * 0.13)
		for name, label, field in (("host", "Steam Decks adress", self.host), ("password", "Lösenord", self.password)):
			lab = a.text(label, H * 0.026, SOFT_INK, shadow=False)
			screen.blit(lab, (panel.centerx - fw // 2, y))
			y += lab.get_height() + H * 0.006
			box = pygame.Rect(panel.centerx - fw // 2, y, fw, fh)
			self.text_field(screen, name, box, field, focused == name)
			self.items.append((name, box))
			y += fh + H * 0.022
		if self.error:
			c = a.circle(H * 0.05, RED)
			cr = c.get_rect(midtop=(panel.centerx, y))
			screen.blit(c, cr)
			xi = a.icon("x", H * 0.03, WHITE, stroke=3)
			screen.blit(xi, xi.get_rect(center=cr.center))
			self.help(screen, panel, deck.HELP.get(self.error, deck.HELP["other"]).split("\n"), cr.bottom + H * 0.01)
		self.buttons(screen, panel, [("connect", "link", "Anslut", YELLOW), ("close", "undo-2", "Tillbaka", BACK_FILL)],
			focused)

	def text_field(self, screen, name, box, field, focused):
		a, H = self.assets, self.H
		pygame.draw.rect(screen, FIELD, box, border_radius=int(box.height * 0.3))
		pygame.draw.rect(screen, YELLOW if focused else (220, 200, 160), box, width=max(2, int(H * 0.005)),
			border_radius=int(box.height * 0.3))
		font = a.font(self.font_size())
		shown = field.shown()
		inner = box.inflate(-box.height * 0.6, 0)
		before = font.size(shown[:field.pos])[0]
		shift = max(0, before - inner.width + 4)  # keep the cursor in view
		self.shift[name] = shift
		screen.set_clip(inner)
		t = font.render(shown, True, INK)
		screen.blit(t, t.get_rect(midleft=(inner.left - shift, box.centery)))
		if focused and (pygame.time.get_ticks() // 500) % 2 == 0:
			cx = inner.left - shift + before
			pygame.draw.line(screen, INK, (cx, box.top + box.height * 0.22), (cx, box.bottom - box.height * 0.22), 2)
		screen.set_clip(None)

	def help(self, screen, panel, lines, y):
		a, H = self.assets, self.H
		for line in lines:
			if line.startswith("$ "):
				t = a.text(line[2:], H * 0.025, WHITE, shadow=False)
				box = t.get_rect(midtop=(panel.centerx, y)).inflate(H * 0.03, H * 0.01)
				pygame.draw.rect(screen, INK, box, border_radius=int(H * 0.012))
				screen.blit(t, t.get_rect(center=box.center))
				y = box.bottom + H * 0.007
				continue
			for part in wrap(a, line, H * 0.025, panel.width * 0.88):
				t = a.text(part, H * 0.025, INK, shadow=False)
				screen.blit(t, t.get_rect(midtop=(panel.centerx, y)))
				y += t.get_height() + H * 0.002
		return y

	def draw_choose(self, screen, panel):
		a, H = self.assets, self.H
		focus = self.choose_focus()
		# Places: home, Games, cards, each with its free space.
		n = max(1, len(self.places))
		gap = int(H * 0.02)
		cw = int(min(H * 0.24, (panel.width * 0.9 - (n - 1) * gap) / n))
		chh = int(H * 0.1)
		x = panel.centerx - (n * cw + (n - 1) * gap) // 2
		y = panel.top + int(H * 0.11)
		for i, (kind, label, path, free) in enumerate(self.places):
			rect = pygame.Rect(x, y, cw, chh)
			here = self.path == path or (kind != "home" and self.path.startswith(path.rstrip("/") + "/"))
			if focus == f"place:{i}":
				pygame.draw.rect(screen, INK, rect.inflate(H * 0.012, H * 0.012), border_radius=int(H * 0.025))
			pygame.draw.rect(screen, YELLOW if here else ROW, rect, border_radius=int(H * 0.02))
			icon = {"home": "house", "games": "gamepad-2", "card": "hard-drive"}[kind]
			ic = a.icon(icon, H * 0.034, INK, stroke=2.2)
			screen.blit(ic, ic.get_rect(midleft=(rect.left + H * 0.015, rect.top + chh * 0.34)))
			t = a.text(label[:12], H * 0.026, INK, shadow=False)
			screen.blit(t, t.get_rect(midleft=(rect.left + H * 0.058, rect.top + chh * 0.34)))
			f = a.text(size_text(free) + " ledigt", H * 0.021, SOFT_INK, shadow=False)
			screen.blit(f, f.get_rect(midleft=(rect.left + H * 0.015, rect.top + chh * 0.74)))
			self.items.append((f"place:{i}", rect))
			x += cw + gap

		# Where we are, and its folders.
		y += chh + int(H * 0.02)
		lw = int(panel.width * 0.86)
		lx = panel.centerx - lw // 2
		p = a.text(fit(a, self.path, H * 0.025, lw), H * 0.025, SOFT_INK, shadow=False)
		screen.blit(p, (lx, y))
		y += p.get_height() + int(H * 0.008)
		rows = self.choose_rows()
		rh = int(H * 0.05)
		self.scroll = max(0, min(self.scroll, max(0, len(rows) - ROWS_SHOWN)))
		for j, kind in enumerate(rows[self.scroll:self.scroll + ROWS_SHOWN]):
			rect = pygame.Rect(lx, y + j * (rh + 4), lw, rh)
			pygame.draw.rect(screen, YELLOW if focus == kind else ROW, rect, border_radius=int(rh * 0.3))
			name = ".." if kind == "up" else kind[7:]
			ic = a.icon("corner-left-up" if kind == "up" else "folder", rh * 0.55, INK, stroke=2.2)
			screen.blit(ic, ic.get_rect(midleft=(rect.left + rh * 0.3, rect.centery)))
			t = a.text(name, H * 0.026, INK, shadow=False)
			screen.blit(t, t.get_rect(midleft=(rect.left + rh * 1.1, rect.centery)))
			self.items.append((kind, rect))
		if not rows:
			t = a.text("Inga mappar här", H * 0.025, SOFT_INK, shadow=False)
			screen.blit(t, t.get_rect(midtop=(panel.centerx, y + H * 0.01)))
		if len(rows) > ROWS_SHOWN:
			more = a.text(f"{self.scroll + 1}-{min(len(rows), self.scroll + ROWS_SHOWN)} av {len(rows)}", H * 0.02,
				SOFT_INK, shadow=False)
			screen.blit(more, more.get_rect(topright=(lx + lw, y + ROWS_SHOWN * (rh + 4))))

		# Where the copy goes, and whether it fits.
		y = panel.bottom - int(H * 0.045) - int(H * 0.072) - int(H * 0.08)
		t = a.text(fit(a, f"Mulle Meck hamnar i {self.dest()}", H * 0.024, panel.width * 0.9), H * 0.024, INK, shadow=False)
		screen.blit(t, t.get_rect(midtop=(panel.centerx, y)))
		fits = self.needed is None or self.free is None or self.needed < self.free
		need = a.text(f"Behövs {size_text(self.needed)} · ledigt {size_text(self.free)}", H * 0.022,
			INK if fits else RED, shadow=False)
		screen.blit(need, need.get_rect(midtop=(panel.centerx, y + t.get_height() + H * 0.004)))
		self.buttons(screen, panel, [("copyhere", "send", "Kopiera hit", YELLOW), ("back", "undo-2", "Tillbaka", BACK_FILL)],
			focus)

	def draw_copy(self, screen, panel):
		a, H = self.assets, self.H
		state = self.copy.state
		mid = (panel.centerx, panel.top + int(panel.height * 0.43))
		targets = self.targets()
		focused = targets[min(self.focus, len(targets) - 1)]
		if state == "cancelled":
			# Back to choosing (still connected); what got there stays.
			self.step, self.copy = "choose", None
			self.app.deck_copy = None
			return self.draw_choose(screen, panel)
		# "I bakgrunden" closes the panel and the copy goes on, its ring on the
		# corner button; "Avbryt" stops it.
		background = ("hide", "minimize-2", "I bakgrunden", BACK_FILL)
		if state == "copying":
			self.spinner(screen, mid, H * 0.22, f"{math.floor(self.copy.progress * 100)} %", self.copy.progress)
			self.buttons(screen, panel, [background, ("cancel", "x", "Avbryt", BACK_FILL)], focused)
		elif state == "steam":
			self.spinner(screen, mid, H * 0.22, None, 1.0)
			ic = a.icon("library", H * 0.07, INK, stroke=2)
			screen.blit(ic, ic.get_rect(center=mid))
			self.buttons(screen, panel, [background], focused)
		elif state == "done":
			c = a.circle(H * 0.18, GREEN)
			cr = c.get_rect(center=(mid[0], mid[1] - H * 0.04))
			screen.blit(c, cr)
			ic = a.icon("check", H * 0.1, WHITE, stroke=3)
			screen.blit(ic, ic.get_rect(center=cr.center))
			if self.copy.steam in ("added", "updated", "fallback"):
				line = "Finns i Steams bibliotek som Mulle Meck."
			else:
				line = "Lägg till i Steam: skrivbordsläget, menyn, Mulle Meck, Lägg till i Steam."
			y = cr.bottom + H * 0.03
			lib = a.icon("library", H * 0.04, INK, stroke=2)
			screen.blit(lib, lib.get_rect(midtop=(panel.centerx, y)))
			y += lib.get_height() + H * 0.01
			for part in wrap(a, line, H * 0.026, panel.width * 0.8):
				t = a.text(part, H * 0.026, INK, shadow=False)
				screen.blit(t, t.get_rect(midtop=(panel.centerx, y)))
				y += t.get_height()
			self.buttons(screen, panel, [("ok", "check", "Klart", GREEN)], focused)
		else:
			c = a.circle(H * 0.12, RED)
			screen.blit(c, c.get_rect(center=mid))
			ic = a.icon("x", H * 0.07, WHITE, stroke=3)
			screen.blit(ic, ic.get_rect(center=mid))
			self.help(screen, panel, [deck.HELP["other"]], mid[1] + H * 0.09)
			self.buttons(screen, panel, [("retry", "send", "Igen", YELLOW), ("close", "undo-2", "Tillbaka", BACK_FILL)],
				focused)


def fit(assets, text, size, width):
	"""text, its start cut off with an ellipsis if it is wider than width (a
	path's end is what matters)."""
	font = assets.font(size)
	if font.size(text)[0] <= width:
		return text
	while text and font.size("\u2026" + text)[0] > width:
		text = text[1:]
	return "\u2026" + text


def wrap(assets, text, size, width):
	"""Lines of text that fit width."""
	words, lines, line = text.split(" "), [], ""
	for w in words:
		test = f"{line} {w}".strip()
		if line and assets.font(size).size(test)[0] > width:
			lines.append(line)
			line = w
		else:
			line = test
	return lines + [line] if line else lines
