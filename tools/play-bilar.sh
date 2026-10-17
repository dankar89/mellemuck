#!/usr/bin/env bash
# Play Bygger bilar on our ScummVM build: a window with sound on the Windows
# desktop through WSLg.
#
#   play-bilar.sh [--check] [extra ScummVM options, e.g. --fullscreen]
#
# --check only verifies the setup and prints the command.
# From Windows, double-click play-bygger-bilar.bat in the project folder.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCUMMVM="${SCUMMVM:-$HOME/src/scummvm/scummvm}"
GAME_DIR="${GAME_DIR:-$HOME/games/mulle-bilar}"
CONFIG="$ROOT/play/scummvm.ini"
SAVES="$ROOT/play/saves/bilar"

fail() { echo "play-bilar: $*" >&2; exit 1; }

[[ -x "$SCUMMVM" ]] || fail "ScummVM build not found at $SCUMMVM (see docs/tooling.md, ScummVM build)"
[[ -f "$GAME_DIR/DATA/MULLE32.EXE" ]] || fail "game files not found in $GAME_DIR (extract the disc with tools/iso_extract.py)"
# Director only loads Xtras from Xtras/; the original installer put FileIO there.
[[ -f "$GAME_DIR/XTRAS/FILEIO.X32" ]] || cp "$GAME_DIR/DATA/FILEIO.X32" "$GAME_DIR/XTRAS/"

mkdir -p "$SAVES"
if [[ ! -f "$CONFIG" ]]; then
	# Our build knowingly runs a game ScummVM marks as unstable; skip that warning.
	printf '[scummvm]\nenable_unsupported_game_warning=false\nautosave_period=30\n' >"$CONFIG"
fi

cmd=("$SCUMMVM" --config="$CONFIG" --path="$GAME_DIR" --auto-detect --savepath="$SAVES" --extrapath="$ROOT/third_party/fonts" --scale-factor=2)

if [[ "${1:-}" == "--check" ]]; then
	echo "ok: ${cmd[*]}"
	exit 0
fi

# Use WSLg's display and sound, also when started from Windows via wsl.exe or
# from a shell set up for the headless test harness.
unset SDL_VIDEODRIVER SDL_AUDIODRIVER
export DISPLAY="${DISPLAY:-:0}"
export PULSE_SERVER="${PULSE_SERVER:-unix:/mnt/wslg/PulseServer}"
exec "${cmd[@]}" "$@"
