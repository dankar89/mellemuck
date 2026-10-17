"""Play back the player's input from a ScummVM log with PLAY lines (play log,
scummvm.ini play_log=true) in the test harness (tools/harness.sh, already
started and at the right place).

	~/.venvs/mulle/bin/python tools/replay_playlog.py LOG [--from SECONDS] [--to SECONDS]
		[--movie NAME] [--speed X] [--dry-run]

--movie starts at the first event in that movie (e.g. 05.DXR), --from/--to at
times from the log (the PLAY line's seconds). Events keep their relative timing
(divided by --speed). Mouse positions are game coordinates, as the harness uses.
The game must already be in the same state (e.g. the same save, the same scene):
timing differs between machines, so replay a scene, not a whole session.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time

LINE = re.compile(r"PLAY (\d+)\.(\d+) (\w+) (\S+)(?: frame (\d+))? (.*)")
# ScummVM key codes (common/keyboard.h) to X key names for xdotool
KEYS = {8: "BackSpace", 9: "Tab", 13: "Return", 27: "Escape", 32: "space", 127: "Delete",
	273: "Up", 274: "Down", 275: "Right", 276: "Left", 277: "Insert", 278: "Home", 279: "End",
	280: "Prior", 281: "Next", 303: "Shift_R", 304: "Shift_L", 305: "Control_R", 306: "Control_L",
	307: "Alt_R", 308: "Alt_L"}


def events(path):
	for line in open(path, errors="replace"):
		i = line.find("PLAY ")
		if i < 0:
			continue
		m = LINE.match(line[i:].strip())
		if m:
			secs = int(m.group(1)) + int(m.group(2)) / 1000
			yield secs, m.group(3), m.group(4), m.group(6)


def xkey(code):
	if code in KEYS:
		return KEYS[code]
	if 32 < code < 127:
		return chr(code)
	if 282 <= code <= 293:
		return "F%d" % (code - 281)
	return None


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("log")
	ap.add_argument("--from", dest="start", type=float, default=0)
	ap.add_argument("--to", dest="end", type=float, default=1e12)
	ap.add_argument("--movie")
	ap.add_argument("--speed", type=float, default=1.0)
	ap.add_argument("--dry-run", action="store_true")
	a = ap.parse_args()

	evs = [e for e in events(a.log) if a.start <= e[0] <= a.end]
	if a.movie:
		first = next((i for i, e in enumerate(evs) if e[2].lower() == a.movie.lower()), None)
		if first is None:
			sys.exit("no events in movie %s" % a.movie)
		evs = evs[first:]
	if not evs:
		sys.exit("no events")

	display = os.environ.get("DISPLAY", ":99")
	env = dict(os.environ, DISPLAY=display)
	xdotool = shutil.which("xdotool")
	if not xdotool:
		# unpacked without root, as tools/harness.sh does
		xtools = os.path.expanduser("~/.local/opt/xtools")
		xdotool = os.path.join(xtools, "usr/bin/xdotool")
		env["LD_LIBRARY_PATH"] = os.path.join(xtools, "usr/lib/x86_64-linux-gnu") + ":" + env.get("LD_LIBRARY_PATH", "")
	window = None
	if not a.dry_run:
		window = subprocess.run([xdotool, "search", "--onlyvisible", "--class", "scummvm"],
			capture_output=True, text=True, env=env).stdout.split()[:1]
		if not window:
			sys.exit("no ScummVM window on %s (start the harness first)" % display)
		window = window[0]

	t0, w0 = evs[0][0], time.time()
	for secs, what, movie, detail in evs:
		delay = (secs - t0) / a.speed - (time.time() - w0)
		if delay > 0:
			time.sleep(delay)
		cmd = None
		m = re.search(r"at (-?\d+),(-?\d+)", detail)
		if what in ("move", "down", "up", "rdown", "rup") and m:
			x, y = m.group(1), m.group(2)
			cmd = ["mousemove", "--window", window or "W", x, y]
			if what in ("down", "up", "rdown", "rup"):
				cmd += ["mouse" + ("down" if what.endswith("down") else "up"), "3" if what.startswith("r") else "1"]
		elif what in ("keydown", "keyup"):
			k = re.search(r"key (\d+)", detail)
			name = xkey(int(k.group(1))) if k else None
			if name:
				cmd = [what, "--window", window or "W", name]
		print("%8.3f %-7s %-8s %s" % (secs, what, movie, detail))
		if cmd and not a.dry_run:
			subprocess.run([xdotool] + cmd, env=env)


if __name__ == "__main__":
	main()
