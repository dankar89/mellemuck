"""The HD button's question before a game's HD art is made (user, 2026-10-14:
"the launcher should be more clear what happens when clicking the
'HD-bilder' there is no indication that it will generate it and that it
might take a while"): what it does, about how long it takes, that it can be
paused, then Starta or Inte nu. Same look and controls as the Steam Deck
panel (deckpanel.py): left/right or up/down move, A/Enter press, B/Escape
close; the mouse too.
"""
import pygame

from .deckpanel import BACK_FILL, GREEN, INK, PAPER, WHITE, wrap


class HDPanel:
	def __init__(self, launcher, game):
		self.app, self.game = launcher, game
		self.focus = 0
		self.items = []  # (kind, rect) for the mouse

	def targets(self):
		return ["start", "cancel"]

	def close(self):
		self.app.panel = None

	def press(self, kind):
		self.close()
		if kind == "start":
			self.app.start_hd(self.game)

	def handle(self, e):
		targets = self.targets()
		t = e.type
		if t == pygame.KEYDOWN:
			if e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
				self.focus = (self.focus + 1) % len(targets)
			elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
				self.press(targets[self.focus])
			elif e.key == pygame.K_ESCAPE:
				self.close()
		elif t == pygame.CONTROLLERBUTTONDOWN:
			b = e.button
			if b in (pygame.CONTROLLER_BUTTON_DPAD_LEFT, pygame.CONTROLLER_BUTTON_DPAD_RIGHT,
					pygame.CONTROLLER_BUTTON_DPAD_UP, pygame.CONTROLLER_BUTTON_DPAD_DOWN):
				self.focus = (self.focus + 1) % len(targets)
			elif b == pygame.CONTROLLER_BUTTON_A:
				self.press(targets[self.focus])
			elif b in (pygame.CONTROLLER_BUTTON_B, pygame.CONTROLLER_BUTTON_BACK):
				self.close()
		elif t == pygame.MOUSEMOTION:
			for k, rect in self.items:
				if rect.collidepoint(e.pos):
					self.focus = targets.index(k)
		elif t == pygame.MOUSEBUTTONDOWN and e.button == 1:
			for k, rect in self.items:
				if rect.collidepoint(e.pos):
					self.press(k)
					return

	def lines(self):
		info = self.game.info
		lo, hi = info.hd_minutes or (30, 60)
		return [
			"Datorns grafikkort ritar om spelets bilder skarpare, i tre gånger så hög upplösning.",
			f"Det tar ungefär {lo}–{hi} minuter med ett bra grafikkort, längre med ett enklare.",
			"Du kan pausa och fortsätta när du vill. Medan du spelar väntar det, "
			"och bilderna som är klara syns i spelet direkt.",
		]

	def draw(self, screen, assets, spin):
		W, H = screen.get_size()
		veil = pygame.Surface((W, H), pygame.SRCALPHA)
		veil.fill((10, 6, 2, 200))
		screen.blit(veil, (0, 0))
		pw, ph = int(H * 0.95), int(H * 0.66)
		panel = pygame.Rect(0, 0, min(pw, W - int(H * 0.06)), ph)
		panel.center = (W // 2, H // 2)
		pygame.draw.rect(screen, PAPER, panel, border_radius=int(H * 0.03))
		self.items = []

		ic = assets.icon("image-up", H * 0.065, INK, stroke=2)
		title = assets.text(f"HD-bilder för {self.game.info.title}", H * 0.04, INK, shadow=False)
		total = ic.get_width() + H * 0.02 + title.get_width()
		x = panel.centerx - total / 2
		ty = panel.top + H * 0.07
		screen.blit(ic, ic.get_rect(midleft=(x, ty)))
		screen.blit(title, title.get_rect(midleft=(x + ic.get_width() + H * 0.02, ty)))

		y = ty + H * 0.07
		size = H * 0.03
		for line in self.lines():
			for part in wrap(assets, line, size, panel.width * 0.84):
				t = assets.text(part, size, INK, shadow=False)
				screen.blit(t, t.get_rect(midtop=(panel.centerx, y)))
				y += t.get_height()
			y += H * 0.018

		bw, bh, gap = int(H * 0.25), int(H * 0.072), int(H * 0.03)
		row = [("start", "play", "Starta", GREEN), ("cancel", "x", "Inte nu", BACK_FILL)]
		bx = panel.centerx - (len(row) * bw + (len(row) - 1) * gap) // 2
		by = panel.bottom - int(H * 0.05) - bh
		for i, (kind, icon, word, fill) in enumerate(row):
			rect = pygame.Rect(bx, by, bw, bh)
			if self.focus == i:
				pygame.draw.rect(screen, INK, rect.inflate(H * 0.014, H * 0.014), border_radius=rect.height)
			pygame.draw.rect(screen, fill, rect, border_radius=rect.height // 2)
			fg = WHITE if fill == GREEN else INK
			ic = assets.icon(icon, rect.height * 0.45, fg, stroke=2.5)
			t = assets.text(word, H * 0.03, fg, shadow=False)
			wsum = ic.get_width() + H * 0.012 + t.get_width()
			cx = rect.centerx - wsum / 2
			screen.blit(ic, ic.get_rect(midleft=(cx, rect.centery)))
			screen.blit(t, t.get_rect(midleft=(cx + ic.get_width() + H * 0.012, rect.centery)))
			self.items.append((kind, rect))
			bx += bw + gap
