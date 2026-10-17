#!/usr/bin/env bash
# Test flow for Bygg hus: an existing player logs in, reaches the building
# site, runs the given Lingo lines (harness.sh lingo, our build's test hook)
# and then goes to MOVIE. For scenes a test cannot click its way to, such as
# the destinations one drives or sails to.
#   hus-goto.sh SAVEDIR MOVIE ['lingo line' ...]
# e.g. hus-goto.sh runs/hus-play/saves 70 \
#        'addGivenMission(the pUserObj of gSystemObj, 39)'
# SAVEDIR holds a garygadget4-Data.cst.casttext whose first login name is the
# player (PLAYER_Y=268 is that name's row). Screenshots in $RUN_DIR (default
# runs/hus-goto): 01-site.png, 02-movie.png. Beside another session use your
# own DISP and a renamed SCUMMVM copy.
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
ROOT="$(cd "$D/../.." && pwd)"
SAVES="${1:?save folder}"; MOVIE="${2:?movie, e.g. 70}"; shift 2
export GAME_DIR="${GAME_DIR:-$HOME/games/mulle-hus}"
export RUN_DIR="${RUN_DIR:-$ROOT/runs/hus-goto}"
LOG="$RUN_DIR/scummvm.log"
$H stop >/dev/null
rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR/saves"
cp "$SAVES"/garygadget4-Data.cst.casttext "$RUN_DIR/saves/"
$H start >/dev/null
sleep 12
# The name list takes clicks only once the login has settled: retry.
for i in $(seq 1 6); do
	$H dblclick 545 "${PLAYER_Y:-268}"; sleep 4
	grep -q '0[14].dxr frame' "$LOG" 2>/dev/null && break
done
for i in $(seq 1 20); do
	sleep 5
	grep -q '04.dxr frame' "$LOG" 2>/dev/null && break
	$H click 400 300
done
sleep 5
$H shot 01-site || exit 1
for code in "$@"; do
	$H lingo "$code"; sleep 1
done
$H lingo "go(1, \"$MOVIE\")"
for i in $(seq 1 30); do
	sleep 1
	grep -q "$MOVIE.dxr frame" "$LOG" && break
done
sleep "${WAIT:-20}"
$H shot 02-movie
