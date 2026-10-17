#!/usr/bin/env bash
# Drive ScummVM headlessly on a virtual X screen so the game can be tested
# without a human at the controls.
#
#   harness.sh start [extra scummvm args]   start Xvfb + ScummVM (window-relative 1:1 game coords)
#   harness.sh click X Y                     left click at game coordinates
#   harness.sh dblclick X Y                  double click at game coordinates
#   harness.sh drag X1 Y1 X2 Y2              press at X1,Y1, move, release at X2,Y2
#   harness.sh move X Y                      move the mouse only
#   harness.sh press X Y / release           hold the left button / let go
#   harness.sh key KEY                       xdotool key name, e.g. Escape, Return
#   harness.sh keydown KEY / keyup KEY       hold a key / let go
#   harness.sh type TEXT                     type text into the focused game window
#   harness.sh pad BUTTON down|up            press/release on the test gamepad (PAD=1)
#   harness.sh pad2 BUTTON down|up           the same on the second one (PAD=2: two pads)
#   harness.sh pad AXIS VALUE                move a stick or trigger (leftx, lefty, ...)
#   harness.sh lingo CODE                    run Lingo in the game between scripts (our build), e.g. 'go(1, "70")'
#   harness.sh shot NAME                     screenshot to $RUN_DIR/NAME.png
#   harness.sh wait SECONDS                  let the game run
#   harness.sh log [N]                       tail the ScummVM log
#   harness.sh stop                          kill ScummVM + Xvfb
#
# HD=1 harness.sh start ...  runs with the HD art (build/bilar/hd, see
# docs/scummvm.md 46): the window is 3x, coordinates stay game coordinates.
# HD_SPRITES=true|false sets hd_sprites (HD art for sprites too).
# HD_PATH=dir uses another HD folder (e.g. a half-finished one).
# INI="key=value ..." sets scummvm.ini keys for this run (e.g. screen_keyboard=steam).
# PADKEYS=1 (with HD=1) binds keys to the gamepad's driving controls, as no
# gamepad exists here: J/L/I/K the left stick, Z = A (gas), X = B (brake).
# PAD=1 attaches a virtual game controller through SDL instead (our ScummVM
# build, SCUMMVM_TEST_PAD), driven with "harness.sh pad": SDL's names, e.g.
# "pad a down", "pad lefty -32767", "pad start up" (docs/tooling.md).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCUMMVM="${SCUMMVM:-$HOME/src/scummvm/scummvm}"
GAME_DIR="${GAME_DIR:-$HOME/games/mulle-bilar}"
RUN_DIR="${RUN_DIR:-$ROOT/runs/latest}"
DISP="${DISP:-:99}"
STATE="$RUN_DIR/.state"

# Xvfb/xdotool may be unpacked without root into ~/.local/opt/xtools
# (apt-get download + dpkg -x). Xvfb then needs xkbcomp at /usr/bin, which we
# provide via a private overlay mount in a user namespace.
XTOOLS="$HOME/.local/opt/xtools"
if ! command -v xdotool >/dev/null && [[ -x "$XTOOLS/usr/bin/xdotool" ]]; then
	export LD_LIBRARY_PATH="$XTOOLS/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
	xdotool() { "$XTOOLS/usr/bin/xdotool" "$@"; }
fi
start_xvfb() {
	# XVFB_SIZE: Bygg hus in HD (800x600 x3) needs 2400x1800
	local args=("$DISP" -screen 0 "${XVFB_SIZE:-1920x1440}x24" -nolisten tcp)
	if command -v Xvfb >/dev/null && command -v xkbcomp >/dev/null; then
		Xvfb "${args[@]}"
	else
		# /tmp/.X11-unix belongs to WSLg; clients reach us via the abstract socket.
		unshare -rm sh -c "mount -t overlay overlay -o lowerdir=$XTOOLS/usr/bin:/usr/bin /usr/bin \
			&& mount -t tmpfs tmpfs /tmp/.X11-unix && exec /usr/bin/Xvfb ${args[*]}"
	fi
}

export DISPLAY="$DISP"
# Keep SDL on X11 (Xvfb), not the WSLg Wayland compositor.
export SDL_VIDEODRIVER=x11
unset WAYLAND_DISPLAY
# No sound card under Xvfb; ScummVM still needs a mixer.
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-dummy}"

# All coordinates are relative to the ScummVM window, i.e. game coordinates
# (times 3 on screen with HD art).
wid() { xdotool search --onlyvisible --class scummvm | head -1; }
SCALE=$(sed -n 's/^SCALE=//p' "$STATE" 2>/dev/null || true)
SCALE=${SCALE:-1}
sc() { echo $(( $1 * SCALE )); }
# The window at the screen's corner (with HD it becomes 3x late, sometimes
# after start gave up waiting; clicks near its right edge then missed).
placed() {
	local w; w=$(wid)
	if [[ "${SCALE:-1}" != 1 ]] && ! xdotool getwindowgeometry "$w" | grep -q "Position: 0,0"; then
		xdotool windowmove "$w" 0 0; sleep 0.2
	fi
	echo "$w"
}

cmd="${1:-}"; shift || true
case "$cmd" in
start)
	mkdir -p "$RUN_DIR"
	# Skip the "not yet fully supported" dialog for unstable games.
	if ! grep -q '^enable_unsupported_game_warning' "$ROOT/scummvm.ini" 2>/dev/null; then
		{ echo "[scummvm]"; echo "enable_unsupported_game_warning=false"; } >>"$ROOT/scummvm.ini"
	fi
	cfg="$ROOT/scummvm.ini"
	scale=1
	gfx=()
	if [[ "${HD:-0}" == 1 ]]; then
		cfg="$RUN_DIR/scummvm-hd.ini"
		cp "$ROOT/scummvm.ini" "$cfg"
		sed -i "/^\[scummvm\]/a hd_path=${HD_PATH:-$ROOT/build/bilar/hd}" "$cfg"
		[[ -z "${HD_SPRITES:-}" ]] || sed -i "/^\[scummvm\]/a hd_sprites=$HD_SPRITES" "$cfg"
		scale=3
		# OpenGL (Mesa) as on Windows: full colour screen and 3x pointer; the
		# software renderer offers only 16-bit colour.
		gfx=(--gfx-mode=opengl)
	fi
	mkdir -p "$RUN_DIR/saves"
	# INI="key=value ..." adds settings to [scummvm] (a copy of the config).
	if [[ -n "${INI:-}" ]]; then
		[[ "$cfg" == "$RUN_DIR/"* ]] || { cp "$cfg" "$RUN_DIR/scummvm-run.ini"; cfg="$RUN_DIR/scummvm-run.ini"; }
		for kv in $INI; do sed -i "/^\[scummvm\]/a $kv" "$cfg"; done
	fi
	if [[ "${PAD:-0}" == 1 || "${PAD:-0}" == 2 ]]; then
		: >"$RUN_DIR/pad.txt"
		export SCUMMVM_TEST_PAD="$RUN_DIR/pad.txt"
		# PAD=2: a second pad too (pad2 ...), as a Steam Deck with another pad.
		[[ "${PAD}" == 2 ]] && : >"$RUN_DIR/pad2.txt" && export SCUMMVM_TEST_PAD2="$RUN_DIR/pad2.txt"
	fi
	# Lingo run between scripts (harness.sh lingo CODE), docs/tooling.md.
	: >"$RUN_DIR/lingo.txt"
	export SCUMMVM_TEST_LINGO="$RUN_DIR/lingo.txt"
	start_xvfb >"$RUN_DIR/xvfb.log" 2>&1 &
	echo "XVFB=$!" >"$STATE"
	echo "SCALE=$scale" >>"$STATE"
	for _ in $(seq 50); do xdotool getdisplaygeometry >/dev/null 2>&1 && break; sleep 0.1; done
	game=(--path="$GAME_DIR" --auto-detect)
	if [[ "${PADKEYS:-0}" == 1 ]]; then
		# Keymap settings live in the game's config section, which
		# --auto-detect makes up on the fly: run a configured target instead.
		k=keymap_director-garygadget-driving
		cat >>"$cfg" <<-INI

		[mulle-pad]
		gameid=garygadget1
		engineid=director
		path=$GAME_DIR
		language=se
		platform=windows
		${k}_STEERLEFT=j JOY_LEFT_STICK_X-
		${k}_STEERRIGHT=l JOY_LEFT_STICK_X+
		${k}_STEERUP=i JOY_LEFT_STICK_Y-
		${k}_STEERDOWN=k JOY_LEFT_STICK_Y+
		${k}_GAS=z JOY_A JOY_RIGHT_TRIGGER
		${k}_BRAKE=x JOY_B JOY_LEFT_TRIGGER
		INI
		game=(mulle-pad)
	fi
	"$SCUMMVM" --config="$cfg" --extrapath="$ROOT/third_party/fonts" \
		--scaler=normal --scale-factor=1 --no-aspect-ratio --savepath="$RUN_DIR/saves" \
		"${gfx[@]}" "$@" "${game[@]}" >"$RUN_DIR/scummvm.log" 2>&1 &
	echo "SCUMMVM=$!" >>"$STATE"
	if [[ $scale != 1 ]]; then
		# SDL keeps the window where the first, 640x480 screen was centred:
		# once it is 3x, move it onto the screen so screenshots get all of it.
		for _ in $(seq 200); do
			w=$(wid)
			if [[ -n "$w" ]] && xdotool getwindowgeometry "$w" | grep -q "Geometry: $((640 * scale))x"; then
				xdotool windowmove "$w" 0 0
				break
			fi
			sleep 0.1
		done
	fi
	echo "started; log: $RUN_DIR/scummvm.log"
	;;
click) w=$(placed); xdotool mousemove --window "$w" "$(sc "$1")" "$(sc "$2")" sleep 0.05 click 1 ;;
dblclick) w=$(placed); xdotool mousemove --window "$w" "$(sc "$1")" "$(sc "$2")" sleep 0.05 click --repeat 2 --delay 120 1 ;;
move)  xdotool mousemove --window "$(placed)" "$(sc "$1")" "$(sc "$2")" ;;
drag)
	w=$(placed)
	xdotool mousemove --window "$w" "$(sc "$1")" "$(sc "$2")" sleep 0.1 mousedown 1 sleep 0.2
	for i in 1 2 3 4 5 6 7 8; do
		xdotool mousemove --window "$w" "$(sc $(( $1 + ($3 - $1) * i / 8 )))" "$(sc $(( $2 + ($4 - $2) * i / 8 )))" sleep 0.05
	done
	xdotool sleep 0.2 mouseup 1
	;;
press)
	# Hold the left button at X Y (let go with "release"; "move" moves it held).
	xdotool mousemove --window "$(placed)" "$(sc "$1")" "$(sc "$2")" sleep 0.1 mousedown 1
	;;
release) xdotool mouseup 1 ;;
key)  xdotool key --window "$(wid)" "$1" ;;
keydown) xdotool keydown --window "$(wid)" "$1" ;;
keyup) xdotool keyup --window "$(wid)" "$1" ;;
type) xdotool type --delay 80 --window "$(wid)" "$1" ;;
pad)  printf '%s\n' "$*" >>"$RUN_DIR/pad.txt" ;;
lingo)
	# The game empties the file when it has read it: wait for the last one,
	# or a second call right after would replace it unread (5 s at most).
	for _ in $(seq 50); do [[ -s "$RUN_DIR/lingo.txt" ]] || break; sleep 0.1; done
	printf '%s\n' "$*" >"$RUN_DIR/lingo.tmp" && mv -f "$RUN_DIR/lingo.tmp" "$RUN_DIR/lingo.txt" ;;  # whole, never half-written
pad2) printf '%s\n' "$*" >>"$RUN_DIR/pad2.txt" ;;
shot)
	w=$(wid)
	[[ -n "$w" ]] || { echo "no ScummVM window (crashed?)"; exit 1; }
	# SDL may put a 3x (HD) window partly off the screen: move it back first.
	if [[ "$SCALE" != 1 ]] && ! xdotool getwindowgeometry "$w" | grep -q "Position: 0,0"; then
		xdotool windowmove "$w" 0 0
		sleep 1.5
	fi
	import -window "$w" "$RUN_DIR/$1.png" && echo "$RUN_DIR/$1.png"
	;;
wait) sleep "$1" ;;
log)  tail -n "${1:-40}" "$RUN_DIR/scummvm.log" ;;
stop)
	# This run's ScummVM (its pid in $STATE) and the X screen on $DISP; only
	# without a state file every ScummVM of the dev build. (Two sessions share
	# this machine: a stop killed the other's game, 2026-10-14.) Xvfb by
	# command line: $! of the backgrounded start_xvfb is a subshell.
	pid=$(sed -n 's/^SCUMMVM=//p' "$STATE" 2>/dev/null || true)
	if [[ -n "$pid" ]]; then
		kill "$pid" 2>/dev/null || true
		# Gone before returning, so a copied-over binary is not "busy"
		for _ in $(seq 50); do kill -0 "$pid" 2>/dev/null || break; sleep 0.1; done
	else
		pkill -f "src/scummvm/scumm[v]m --config=" 2>/dev/null || true
	fi
	pkill -f "Xvf[b] $DISP " 2>/dev/null || true
	rm -f "$STATE"
	echo stopped
	;;
*) sed -n '2,17p' "$0"; exit 1 ;;
esac
