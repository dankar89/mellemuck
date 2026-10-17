#!/usr/bin/env bash
# Test flow for Bygger bilar: junk-pile flow (wheels dropped on the door), back
# into the garage, then drag the wheels from the floor onto the chassis.
# Screenshots: runs/latest/07-garage.png, 08-mounted.png.
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
"$D/bilar-junkpile.sh" "$@" >/dev/null || exit 1
S="${SLOW:-1}"
$H move 35 200; sleep 1; $H click 35 200; sleep $(( 14 * S ))
$H shot 07-garage || exit 1
source <(sed -n '/^XTOOLS=/,/^}/p' "$H" | sed '/^start_xvfb/,$d'); export DISPLAY="${DISP:-:99}"
w=$(xdotool search --onlyvisible --class scummvm | head -1)
# Game coordinates; the window is 3x with HD art (HD=1).
k=$(sed -n 's/^SCALE=//p' "${RUN_DIR:-$D/../../runs/latest}/.state" 2>/dev/null); k=${k:-1}
xdotool mousemove --window "$w" $((185 * k)) $((430 * k)) sleep 0.3 mousedown 1 sleep 0.4
for i in $(seq 1 15); do xdotool mousemove --window "$w" $(((185 + i * 13) * k)) $(((430 - i * 10) * k)) sleep 0.08; done
sleep 1.2; xdotool mouseup 1; sleep 4
$H shot 08-mounted
