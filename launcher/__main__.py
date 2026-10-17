"""Mulle Meck launcher.

  python -m launcher [--root DIR] [--window [--size 1280x800]]
                     [--shot FILE [--focus N]]
  python -m launcher --play GAME_ID   (straight into a game, e.g. bygger-bilar)

ROOT is the folder with the games (games/<id>/), ScummVM and its settings;
by default the folder the launcher runs from. Fullscreen like the games
(ScummVM's fullscreen setting, default on); --window for a window. --shot renders one screen to a
PNG and quits (for checking the look without a display:
SDL_VIDEODRIVER=dummy).
"""
import argparse
import signal
import sys
from pathlib import Path

from .ui import Launcher


def interrupted(*_):
	raise KeyboardInterrupt


def main():
	ap = argparse.ArgumentParser(prog="launcher")
	here = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
	ap.add_argument("--root", type=Path, default=here)
	ap.add_argument("--size", default="1280x800")
	ap.add_argument("--window", action="store_true", help="a window, whatever the fullscreen setting")
	ap.add_argument("--shot", type=Path)
	ap.add_argument("--focus", type=int, default=0)
	ap.add_argument("--input", choices=("pad", "keyboard", "mouse"), default="mouse")
	ap.add_argument("--play", metavar="GAME_ID", help="start this game without the carousel")
	args = ap.parse_args()
	if sys.stderr is None:  # pythonw (the packaged launcher): no console, so a log
		sys.stderr = sys.stdout = open(args.root / "launcher.log", "w", encoding="utf-8", buffering=1)
	if args.play:
		# Straight into one game: its starter next to the launcher ("Bygg
		# bilar.exe"), a shortcut, a Steam entry. A game not found here yet
		# (the starter used before "Hitta spelet") opens the launcher on it.
		from . import discs
		from .catalog import GAMES
		from .library import Game, find_file
		from .ui import start_game
		info = next((g for g in GAMES if g.id == args.play), None)
		game = Game(info, args.root.resolve()) if info else None
		if (game and info.playable and find_file(game.folder, info.marker) is not None
				and discs.install(info, game.folder)):
			sys.exit(start_game(args.root, game).wait())
		if info:
			args.focus = GAMES.index(info)
	w, h = (int(v) for v in args.size.lower().split("x"))
	from .ui import fullscreen_setting
	fullscreen = not (args.window or args.shot) and fullscreen_setting(args.root)
	app = Launcher(args.root, (w, h), fullscreen)
	app.focus = args.focus
	app.pos = float(args.focus)
	app.input = args.input
	# Steam's "Exit game" (a Steam Deck) and Ctrl+C end the launcher with a
	# signal: stop the HD job and go, without a traceback. The game gets the
	# same signal and saves on its own way out.
	signal.signal(signal.SIGTERM, interrupted)
	try:
		app.run(shot=args.shot, frames=90 if args.shot else None)
	except KeyboardInterrupt:
		if app.job:
			app.job.stop()
		sys.exit(0)


if __name__ == "__main__":
	main()
