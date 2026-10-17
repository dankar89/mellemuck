#!/usr/bin/env bash
# Test flow for Bygger bilar: new player -> junk pile, then walk through the
# piles with the signposts (right x3, left x2), checking ScummVM survives each.
# Look at the screenshots too: each pile should show its own parts and Mulle
# whole (piles 4-6 have him on the right).
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
"$D/bilar-new-player.sh" "$@" >/dev/null || exit 1
S="${SLOW:-1}"
alive() { pgrep -f "${SCUMMVM:-src/scummvm/scummvm} --config" >/dev/null; }
$H move 515 100; sleep 1; $H click 515 100; sleep $(( 12 * S ))
$H shot 04-pile || exit 1
n=5
# Signposts sit in different places in each pile: 1->2->3->4, then 4->3->2.
for step in "right 570 383" "right 570 383" "right 540 390" "left 55 365" "left 180 350"; do
	set -- $step
	$H move "$2" "$3"; sleep 0.5; $H click "$2" "$3"; sleep $(( 8 * S ))
	alive || { echo "CRASH after sign $1 (step $n)"; exit 1; }
	$H shot "0$n-$1" >/dev/null; n=$((n + 1))
done
grep -q "Debugger started" "$D/../../runs/latest/scummvm.log" && { echo "LINGO ERROR (debugger opened)"; exit 1; }
echo "no crash"
