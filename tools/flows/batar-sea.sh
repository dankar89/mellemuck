#!/usr/bin/env bash
# Test flow for Bygger båtar: an existing player with a finished boat logs in,
# takes the boat from the boatyard to the quay on its cradle and casts off
# (the mooring rope) to the sea, movie 05. Then use `harness.sh lingo` (our
# build's test hook) and keys, e.g.
#   harness.sh lingo 'put the loc of the boat of gDir, the currentMap of the world of gMulleGlobals'
#   batar-sea.sh SAVEDIR PLAYER
# SAVEDIR holds the player's garygadget2-* files (e.g. copied from the Deck).
# Runs with the package's game folder and its HD art (HD=1: the window is 3x,
# coordinates stay game coordinates). Screenshots in $RUN_DIR (default
# runs/batar-sea): 01-login.png, 02-boatyard.png, 03-sea.png.
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
ROOT="$(cd "$D/../.." && pwd)"
SAVES="${1:?save folder}"; PLAYER="${2:?player name}"
export GAME_DIR="${GAME_DIR:-$ROOT/dist/windows/MulleMeck/games/bygger-batar}"
export RUN_DIR="${RUN_DIR:-$ROOT/runs/batar-sea}"
export HD="${HD:-1}" HD_PATH="${HD_PATH:-$GAME_DIR/HD}"
LOG="$RUN_DIR/scummvm.log"
$H stop >/dev/null
rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR/saves"
cp "$SAVES"/garygadget2-* "$RUN_DIR/saves/"
$H start >/dev/null
sleep 30
$H shot 01-login || exit 1
$H type "$PLAYER"; sleep 0.5; $H key Return
for i in $(seq 12); do
	sleep 5
	grep -q '01.dxr frame' "$LOG" 2>/dev/null && break
done
sleep 8
$H shot 02-boatyard || exit 1
# The cradle to the quay, then the mooring rope; slow clicks (the scenes poll
# the mouse once a frame).
for i in 1 2 3; do
	$H drag 523 324 523 325; sleep 6
	grep -q '04.dxr frame' "$LOG" && break
done
sleep 6
for i in 1 2 3 4; do
	$H drag 482 357 482 358; sleep 6
	grep -q '05.dxr frame' "$LOG" && break
done
sleep 10
$H shot 03-sea
