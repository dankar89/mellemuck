#!/usr/bin/env bash
# Test flow for Bygger bilar: boot, create player "Test", skip the intro.
#   bilar-new-player.sh [extra scummvm args, e.g. --debugflags=lingoexec --debuglevel=3]
# Screenshots land in runs/latest/. Timings are generous for a cold start;
# SLOW=2 (or more) multiplies the waits, e.g. when tracing slows the game down.
set -uo pipefail
S="${SLOW:-1}"
w() { sleep $(( $1 * S )); }
H="$(dirname "$0")/../harness.sh"
$H stop >/dev/null
rm -rf "${RUN_DIR:-$(dirname "$0")/../../runs/latest}"  # also its saves: a fresh player each run
$H start "$@" >/dev/null
w 36
$H shot 01-login || exit 1
$H click 190 75; sleep 0.5; $H type "Test"; sleep 0.5; $H key Return
w 10
$H shot 02-title || exit 1
$H click 320 240
w 12
$H shot 03-after-intro || exit 1
