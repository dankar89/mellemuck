#!/usr/bin/env bash
# Test flow for Bygg hus: a new player logs in, the intro is skipped with
# clicks, and Mulle's first-visit tutorial on the building site (movie 04)
# plays out, so the build book and the toolbar take clicks.
#   hus-site.sh [PLAYER] [extra scummvm args]
# GAME_DIR needs MulleHus.exe and Data.cst next to the disc's files (the
# launcher unpacks them from Setup.exe; default ~/games/mulle-hus). Screenshots
# in $RUN_DIR (default runs/hus-site): 01-login.png, 02-site.png, 03-ready.png.
# Beside another session use your own DISP and a renamed SCUMMVM copy.
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
ROOT="$(cd "$D/../.." && pwd)"
PLAYER="${1:-Testa}"; shift || true
export GAME_DIR="${GAME_DIR:-$HOME/games/mulle-hus}"
export RUN_DIR="${RUN_DIR:-$ROOT/runs/hus-site}"
LOG="$RUN_DIR/scummvm.log"
$H stop >/dev/null
[[ "${KEEP:-0}" == 1 ]] || rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR/saves"
$H start "$@" >/dev/null
sleep 12
$H shot 01-login || exit 1
$H type "$PLAYER"; sleep 0.5; $H key Return
# The intro (01) skips on a click; the site is movie 04.
for i in $(seq 1 20); do
	sleep 5
	grep -q '04.dxr frame' "$LOG" 2>/dev/null && break
	$H click 400 300
done
grep -q '04.dxr frame' "$LOG" || $H move 400 300
sleep 4
$H shot 02-site || exit 1
# The tutorial (two minutes or more) explains each button; clicks wait until
# it ends. Ready: a click on the room button (the cube) opens the build book,
# whose page is white where the grass was. Moving away closes it again.
book_open() {
	"$H" shot _book >/dev/null
	~/.venvs/mulle/bin/python -c 'import sys
from PIL import Image
r, g, b = Image.open(sys.argv[1]).convert("RGB").getpixel((150, 520))
print(1 if min(r, g, b) > 235 else 0)' "$RUN_DIR/_book.png"
}
sleep 60
for i in $(seq 1 40); do
	$H move 22 308; sleep 0.3; $H click 22 308; sleep 2
	[[ $(book_open) == 1 ]] && break
	sleep 4
done
$H move 400 200; sleep 2
rm -f "$RUN_DIR/_book.png"
$H shot 03-ready
