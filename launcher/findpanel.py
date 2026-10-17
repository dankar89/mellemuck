"""Where a game's files come from, the player's choice (user, 2026-10-17: "I
think the automatic search should be optional"; "what if we wanna change to
another version"): "Leta åt mig" searches the usual places (discs.find_all)
and lists every copy found to pick from; "Välj själv" opens the file dialog
at once. Also for a game already there ("Byt spelfiler"): the new files
replace the old, the saves (saves/) and HD art (kept by discs.bring_in) stay.
Same look and controls as the HD panel: arrows/D-pad move, A/Enter press,
B/Escape back or close; the mouse too.
"""
import threading
from pathlib import Path

import pygame

from . import discs
from .deckpanel import BACK_FILL, GREEN, INK, PAPER, ROW, SOFT_INK, WHITE, wrap

SHOWN = 4  # copies listed at most


def describe(src):
	"""What a copy is called and where it is, for the list."""
	if src.kind == "drive":
		return f"Skivan i {str(src.path).rstrip(chr(92) + '/')}", ""
	path = src.path if src.kind in ("iso", "zip", "zip-iso") else (src.path / src.prefix if src.prefix else src.path)
	where = path.parent
	try:
		where = where.relative_to(Path.home())
	except ValueError:
		pass
	return path.name, str(where)


class FindPanel:
	def __init__(self, launcher, game, replacing=False):
		self.app, self.game, self.replacing = launcher, game, replacing
		self.state = "ask"  # ask, searching, results
		self.found = []
		self.focus = 0
		self.items = []  # (kind, rect) for the mouse

	def targets(self):
		if self.state == "ask":
			return ["search", "pick", "cancel"]
		if self.state == "searching":
			return ["cancel"]
		return [f"src{i}" for i in range(min(len(self.found), SHOWN))] + ["pick", "back"]

	def close(self):
		self.app.panel = None

	def search(self):
		self.state, self.focus = "searching", 0
		root = self.app.root / "games"

		def work():
			try:
				# Stops as soon as the panel is cancelled or closed.
				found = discs.find_all(self.game.info.id, exclude=root, stop=lambda: self.state != "searching")
			except Exception as e:
				print(f"launcher: search: {e}")
				found = []
			if self.state == "searching":  # not closed meanwhile
				self.found, self.state, self.focus = found, "results", 0
		threading.Thread(target=work, daemon=True).start()

	def press(self, kind):
		if kind == "search":
			self.search()
		elif kind == "pick":
			self.close()
			self.app.pick_and_bring(self.game)
		elif kind == "back":
			self.state, self.focus = "ask", 0
		elif kind == "cancel":
			self.state = "closed"
			self.close()
		elif kind.startswith("src"):
			self.close()
			self.app.bring(self.game, self.found[int(kind[3:])])

	def back(self):
		if self.state == "results":
			self.press("back")
		else:
			self.press("cancel")

	def handle(self, e):
		targets = self.targets()
		t = e.type
		if t == pygame.KEYDOWN:
			if e.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_TAB):
				self.focus = (self.focus + 1) % len(targets)
			elif e.key in (pygame.K_LEFT, pygame.K_UP):
				self.focus = (self.focus - 1) % len(targets)
			elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
				self.press(targets[self.focus])
			elif e.key == pygame.K_ESCAPE:
				self.back()
		elif t == pygame.CONTROLLERBUTTONDOWN:
			b = e.button
			if b in (pygame.CONTROLLER_BUTTON_DPAD_RIGHT, pygame.CONTROLLER_BUTTON_DPAD_DOWN):
				self.focus = (self.focus + 1) % len(targets)
			elif b in (pygame.CONTROLLER_BUTTON_DPAD_LEFT, pygame.CONTROLLER_BUTTON_DPAD_UP):
				self.focus = (self.focus - 1) % len(targets)
			elif b == pygame.CONTROLLER_BUTTON_A:
				self.press(targets[self.focus])
			elif b in (pygame.CONTROLLER_BUTTON_B, pygame.CONTROLLER_BUTTON_BACK):
				self.back()
		elif t == pygame.MOUSEMOTION:
			for k, rect in self.items:
				if rect.collidepoint(e.pos) and k in targets:
					self.focus = targets.index(k)
		elif t == pygame.MOUSEBUTTONDOWN and e.button == 1:
			for k, rect in self.items:
				if rect.collidepoint(e.pos):
					self.press(k)
					return

	def text_lines(self):
		title = self.game.info.title
		if self.state == "ask":
			first = (f"Vill du använda en annan kopia av {title}? De nya filerna ersätter de gamla; "
				"sparningar och HD-bilder finns kvar." if self.replacing else
				f"Mulle Meck behöver din kopia av {title}: skivan, en skivavbild (.iso) eller en zip-fil.")
			return [first, "Ska vi leta efter den på skivor och i Hämtade filer, Skrivbordet och Dokument, "
				"eller vill du välja filen själv?"]
		if self.state == "searching":
			return ["Letar på skivor och i dina mappar ..."]
		if not self.found:
			return ["Hittade ingen kopia. Välj filen själv i stället."]
		n = len(self.found)
		more = f" (de {SHOWN} första visas)" if n > SHOWN else ""
		return [f"Hittade {n} {'kopia' if n == 1 else 'kopior'}{more}. Vilken vill du använda?"]

	def draw(self, screen, assets, spin):
		W, H = screen.get_size()
		veil = pygame.Surface((W, H), pygame.SRCALPHA)
		veil.fill((10, 6, 2, 200))
		screen.blit(veil, (0, 0))
		# Room for the list of copies only when there is one.
		pw, ph = int(H * 1.05), int(H * (0.8 if self.state == "results" and self.found else 0.56))
		panel = pygame.Rect(0, 0, min(pw, W - int(H * 0.06)), ph)
		panel.center = (W // 2, H // 2)
		pygame.draw.rect(screen, PAPER, panel, border_radius=int(H * 0.03))
		self.items = []
		targets = self.targets()
		self.focus = min(self.focus, len(targets) - 1)

		ic = assets.icon("arrow-right-left" if self.replacing else "folder-open", H * 0.06, INK, stroke=2)
		word = "Byt spelfiler för" if self.replacing else "Hitta"
		title = assets.text(f"{word} {self.game.info.title}", H * 0.04, INK, shadow=False)
		total = ic.get_width() + H * 0.02 + title.get_width()
		x = panel.centerx - total / 2
		ty = panel.top + H * 0.065
		screen.blit(ic, ic.get_rect(midleft=(x, ty)))
		screen.blit(title, title.get_rect(midleft=(x + ic.get_width() + H * 0.02, ty)))

		y = ty + H * 0.065
		size = H * 0.029
		for line in self.text_lines():
			for part in wrap(assets, line, size, panel.width * 0.86):
				t = assets.text(part, size, INK, shadow=False)
				screen.blit(t, t.get_rect(midtop=(panel.centerx, y)))
				y += t.get_height()
			y += H * 0.016

		if self.state == "searching":
			d = H * 0.12
			arc = pygame.transform.rotate(assets.arc(d, H * 0.012, 70, INK), -spin)
			screen.blit(arc, arc.get_rect(center=(panel.centerx, y + d * 0.7)))

		# The copies found: one row each, the file's name and where it is.
		if self.state == "results":
			rw, rh = int(panel.width * 0.84), int(H * 0.078)
			for i, src in enumerate(self.found[:SHOWN]):
				rect = pygame.Rect(0, 0, rw, rh)
				rect.midtop = (panel.centerx, int(y))
				kind = f"src{i}"
				if targets[self.focus] == kind:
					pygame.draw.rect(screen, INK, rect.inflate(H * 0.012, H * 0.012), border_radius=int(H * 0.02))
				pygame.draw.rect(screen, ROW, rect, border_radius=int(H * 0.016))
				name, where = describe(src)
				t = assets.text(name, H * 0.026, INK, shadow=False)
				screen.blit(t, t.get_rect(topleft=(rect.left + H * 0.025, rect.top + H * 0.01)))
				if where:
					t2 = assets.text(where, H * 0.019, SOFT_INK, shadow=False)
					screen.blit(t2, t2.get_rect(topleft=(rect.left + H * 0.025, rect.top + H * 0.044)))
				self.items.append((kind, rect))
				y += rh + H * 0.014

		if self.state == "ask":
			row = [("search", "hard-drive", "Leta åt mig", GREEN), ("pick", "folder-open", "Välj själv", BACK_FILL),
				("cancel", "x", "Avbryt", BACK_FILL)]
		elif self.state == "searching":
			row = [("cancel", "x", "Avbryt", BACK_FILL)]
		else:
			row = [("pick", "folder-open", "Välj själv", GREEN if not self.found else BACK_FILL),
				("back", "undo-2", "Tillbaka", BACK_FILL)]
		bw, bh, gap = int(H * 0.25), int(H * 0.072), int(H * 0.025)
		bx = panel.centerx - (len(row) * bw + (len(row) - 1) * gap) // 2
		by = panel.bottom - int(H * 0.05) - bh
		for kind, icon, label, fill in row:
			rect = pygame.Rect(bx, by, bw, bh)
			if targets[self.focus] == kind:
				pygame.draw.rect(screen, INK, rect.inflate(H * 0.014, H * 0.014), border_radius=rect.height)
			pygame.draw.rect(screen, fill, rect, border_radius=rect.height // 2)
			fg = WHITE if fill == GREEN else INK
			ic = assets.icon(icon, rect.height * 0.45, fg, stroke=2.5)
			t = assets.text(label, H * 0.029, fg, shadow=False)
			wsum = ic.get_width() + H * 0.012 + t.get_width()
			cx = rect.centerx - wsum / 2
			screen.blit(ic, ic.get_rect(midleft=(cx, rect.centery)))
			screen.blit(t, t.get_rect(midleft=(cx + ic.get_width() + H * 0.012, rect.centery)))
			self.items.append((kind, rect))
			bx += bw + gap
