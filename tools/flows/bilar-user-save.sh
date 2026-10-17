#!/usr/bin/env bash
# Test flow for Bygger bilar with the progress from another save folder (e.g. the
# Windows package's), to reproduce what the user sees: copy the game's own
# progress file, log in as that player and go to the junk pile.
#   bilar-user-save.sh SAVEDIR PLAYER [extra scummvm args]
# Screenshots: $RUN_DIR (default runs/user-save) 01-login.png ... 04-pile.png.
# STOP=garage ends in the garage (e.g. to test building the car).
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
SAVES="$1"; PLAYER="$2"; shift 2
export RUN_DIR="${RUN_DIR:-$(cd "$D/../.." && pwd)/runs/user-save}"
S="${SLOW:-1}"
w() { sleep $(( $1 * S )); }
$H stop >/dev/null
rm -rf "$RUN_DIR"; mkdir -p "$RUN_DIR/saves"
cp "$SAVES/garygadget1-data.cst.casttext" "$RUN_DIR/saves/"
$H start "$@" >/dev/null
w 36
$H shot 01-login || exit 1
$H click 190 75; sleep 0.5; $H type "$PLAYER"; sleep 0.5; $H key Return
w 12
$H shot 02-after-login || exit 1
$H click 320 240
w 12
$H shot 03-garage || exit 1
[[ "${STOP:-}" == garage ]] && exit 0
$H move 515 100; sleep 1; $H click 515 100; w 12
$H shot 04-pile || exit 1
