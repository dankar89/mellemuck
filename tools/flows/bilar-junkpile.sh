#!/usr/bin/env bash
# Test flow for Bygger bilar: new player -> garage -> junk pile, then drag the
# wheels (lying on the pile at about 430,190) onto the door to the garage.
# Screenshots: runs/latest/04-pile.png, 05-dragging.png, 06-dropped.png.
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
"$D/bilar-new-player.sh" "$@" >/dev/null || exit 1
S="${SLOW:-1}"
$H move 515 100; sleep 1; $H click 515 100; sleep $(( 12 * S ))
$H shot 04-pile || exit 1
source <(sed -n '/^XTOOLS=/,/^}/p' "$H" | sed '/^start_xvfb/,$d'); export DISPLAY="${DISP:-:99}"
w=$(xdotool search --onlyvisible --class scummvm | head -1)
# Game coordinates; the window is 3x with HD art (HD=1).
k=$(sed -n 's/^SCALE=//p' "${RUN_DIR:-$D/../../runs/latest}/.state" 2>/dev/null); k=${k:-1}
# Slow drag so the game sees the pointer pass over the door.
xdotool mousemove --window "$w" $((430 * k)) $((190 * k)) sleep 0.3 mousedown 1 sleep 0.4
for i in $(seq 1 20); do xdotool mousemove --window "$w" $(((430 - i * 19) * k)) $(((190 + i) * k)) sleep 0.08; done
sleep 1.5; $H shot 05-dragging
xdotool mouseup 1; sleep 4; $H shot 06-dropped
