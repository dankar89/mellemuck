#!/usr/bin/env bash
# Test flow for Bygg hus: an existing player (with a house and a photo taken
# on the site) logs in, goes from the building site to the photo album (12)
# with the camera, and puts the photo in the album with the left red arrow,
# which makes the name under it editable.
#   hus-album.sh SAVEDIR [PLAYER_Y]
# SAVEDIR holds a garygadget4-Data.cst.casttext with that player (e.g. the
# one from runs/hus-play: Kalle, the first name on the login list). PLAYER_Y
# is the name's row on the login list (default 268, the first name).
# Screenshots in $RUN_DIR (default runs/hus-album): 01-login.png,
# 02-site.png, 03-album.png, 04-photo.png. Beside another session use your
# own DISP and a renamed SCUMMVM copy.
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
ROOT="$(cd "$D/../.." && pwd)"
SAVES="${1:?save folder}"; PLAYER_Y="${2:-268}"
export GAME_DIR="${GAME_DIR:-$HOME/games/mulle-hus}"
export RUN_DIR="${RUN_DIR:-$ROOT/runs/hus-album}"
LOG="$RUN_DIR/scummvm.log"
$H stop >/dev/null
rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR/saves"
cp "$SAVES"/garygadget4-Data.cst.casttext "$RUN_DIR/saves/"
$H start >/dev/null
sleep 12
$H shot 01-login || exit 1
# The name list takes clicks only once the login has settled: retry.
for i in $(seq 1 6); do
	$H dblclick 545 "$PLAYER_Y"; sleep 4
	grep -q '0[14].dxr frame' "$LOG" 2>/dev/null && break
done
# The intro (01) skips on a click; the site is movie 04.
for i in $(seq 1 20); do
	sleep 5
	grep -q '04.dxr frame' "$LOG" 2>/dev/null && break
	$H click 400 300
done
sleep 6
$H shot 02-site || exit 1
# The camera on the site's right edge takes the photo and opens the album.
for i in $(seq 1 10); do
	$H move 718 275; sleep 0.5; $H click 718 275; sleep 5
	grep -q '12.dxr frame' "$LOG" && break
done
sleep 4
$H shot 03-album
# The left page's red arrow puts the photo in.
$H move 95 547; sleep 1; $H click 95 547; sleep 3
$H move 400 60; sleep 1
$H shot 04-photo
