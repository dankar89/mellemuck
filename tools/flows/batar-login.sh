#!/usr/bin/env bash
# Test flow for Bygger båtar: start (the quirk skips Levande Böcker's start
# menu), type a player's name on the login screen, Return, and wait for the
# boatyard (movie 01).
#   batar-login.sh [PLAYER] [extra scummvm args]
# GAME_DIR defaults to the launcher's copy of the disc. Screenshots in
# $RUN_DIR (default runs/batar-login): 01-login.png, 02-boatyard.png.
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
ROOT="$(cd "$D/../.." && pwd)"
PLAYER="${1:-Testa}"; shift || true
export GAME_DIR="${GAME_DIR:-$ROOT/dist/windows/MulleMeck/games/bygger-batar}"
export RUN_DIR="${RUN_DIR:-$ROOT/runs/batar-login}"
S="${SLOW:-1}"
w() { sleep $(( $1 * S )); }
$H stop >/dev/null
[[ "${KEEP:-0}" == 1 ]] || rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR/saves"
$H start "$@" >/dev/null
w 30
$H shot 01-login || exit 1
$H type "$PLAYER"; sleep 0.5; $H key Return
w 20
$H shot 02-boatyard || exit 1
