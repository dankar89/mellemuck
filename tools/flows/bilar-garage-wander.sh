#!/usr/bin/env bash
# Robustness test for the garage: sweep the mouse over the whole screen, then
# click a series of hotspots, checking after every step that ScummVM is alive.
# Prints the step that crashed, if any. Screenshot per click in runs/latest/.
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
"$D/bilar-new-player.sh" "$@" >/dev/null || exit 1
alive() { pgrep -f "${SCUMMVM:-src/scummvm/scummvm} --config" >/dev/null; }
for y in 40 120 200 280 360 440; do
	for x in 40 140 240 340 440 540 620; do
		$H move $x $y; sleep 0.4
		alive || { echo "CRASH while hovering at $x,$y"; exit 1; }
	done
done
n=10
for spot in "mulle 90 200" "buffa 590 210" "toolbox 620 420" "phone 135 80" "radio 275 95" \
	"moose 340 40" "camera 610 90" "window 220 30" "battery 228 265" "engine 320 280" "mulle 90 200"; do
	set -- $spot
	$H click "$2" "$3"; sleep 3
	alive || { echo "CRASH after clicking $1 at $2,$3"; exit 1; }
	$H shot "$n-$1" >/dev/null; n=$((n + 1))
done
echo "no crash"
