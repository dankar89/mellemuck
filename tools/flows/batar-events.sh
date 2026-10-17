#!/usr/bin/env bash
# Test flow for Bygger båtar's endings at sea, each of which waits for one of
# Mulle's lines to finish (MulleSez's mulleFinished callback) and then goes
# back to the quay (04): out of fuel (tow home; a boat with a sail or oars
# switches to them instead), a broken boat (crash), a
# capsize, hunger (with a fishing rod: a pause and back to sailing; without:
# home). Sails out with batar-sea.sh, then per event: forces it with Lingo,
# waits for 04 (or, for the fishing break, for the boat to move again), casts
# off again. One line per event in $RUN_DIR/results.txt.
#   batar-events.sh SAVEDIR PLAYER [EVENT ...]   (fuel crash capsize hunger)
# ROD=1 gives the player a fishing rod first (hunger: Mulle fishes).
# Beside another session use your own DISP and a renamed SCUMMVM copy.
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
ROOT="$(cd "$D/../.." && pwd)"
SAVES="${1:?save folder}"; PLAYER="${2:?player name}"; shift 2
export RUN_DIR="${RUN_DIR:-$ROOT/runs/batar-events}"
LOG="$RUN_DIR/scummvm.log"
EVENTS=(fuel crash capsize hunger)
[[ $# -gt 0 ]] && EVENTS=("$@")

lines() { wc -l <"$LOG"; }  # tail -n +N counts empty lines too
wait_log() {  # from line $1, pattern $2, at most $3 s
	local i
	for ((i = 0; i < $3; i += 2)); do
		tail -n +"$1" "$LOG" | grep -ac "$2" >/dev/null && return 0  # not -q: tail gets SIGPIPE, pipefail fails it
		sleep 2
	done
	return 1
}
lingo_val() {
	local n; n=$(lines)
	$H lingo "put \"VAL\", $1" >/dev/null
	sleep 1.5
	tail -n +"$n" "$LOG" | grep -a '^-- "VAL"' | tail -1 | sed 's/^-- "VAL" //'
}
at_sea() {  # waits until the player has the boat
	local i
	for i in $(seq 20); do
		[[ $(lingo_val "the programControlsBoat of the boat of gDir") == 0 ]] && return 0
		sleep 2
	done
	return 1
}
cast_off() {  # from the quay back to sea
	local n i; n=$(lines)
	sleep 6
	for i in 1 2 3 4; do
		$H drag 482 357 482 358; sleep 6
		wait_log "$n" "05.dxr frame [0-9]* new scene" 2 && break
	done
	sleep 8
	at_sea
}

"$D/batar-sea.sh" "$SAVES" "$PLAYER" >/dev/null || exit 1
at_sea || { echo "never got the boat at sea" | tee "$RUN_DIR/results.txt"; exit 1; }
results=()
for ev in "${EVENTS[@]}"; do
	n=$(lines)
	case $ev in
	fuel)
		# What BoatBase does when the tank runs dry (not by driving: from the
		# start, Up runs into the harbour, which also goes home). A boat with
		# another power (sail, oars) switches to it; only motor alone is towed.
		$H lingo 'set the fuel of the boat of gDir to 0
OutOfFuel(the boat of gDir)' >/dev/null ;;
	crash)
		# Durability 0: the next hit breaks the boat. Land: the start map's
		# top left.
		$H lingo 'set the Durability of the boat of gDir to 0' >/dev/null; sleep 0.7
		$H lingo 'setShowCoordinate(the boat of gDir, point(150, 60))' >/dev/null ;;
	capsize)
		# What BoatBase.loop does when the boat leans over 30 degrees.
		$H lingo 'say(the mulleTalkObject of gDir, #Capsize, 1, the boat of gDir, #Q, #GoHomeCapsize)' >/dev/null; sleep 0.7
		$H lingo 'waitToGoHome(the boat of gDir)' >/dev/null ;;
	hunger)
		[[ ${ROD:-} ]] && { $H lingo 'setInInventory(the user of gMulleGlobals, #Fishingrod, [:])' >/dev/null; sleep 0.7; }
		rod=$(lingo_val "isInInventory(the user of gMulleGlobals, #Fishingrod)")
		$H lingo 'set the mulleHunger of the boat of gDir to 1' >/dev/null ;;
	esac
	sleep 3
	$H shot "$ev-1" >/dev/null
	if [[ $ev == fuel ]] && type=$(lingo_val "getType(the boat of gDir)") && [[ $type != "#Motor" ]]; then
		results+=("fuel: switched to $type (another power on board), sailing on")
		continue
	fi
	if [[ $ev == hunger && $rod == 1 ]]; then
		sleep 20
		$H shot "$ev-2" >/dev/null
		if at_sea; then results+=("hunger (fishing rod): fished, sailing again")
		else results+=("hunger (fishing rod): NOT sailing again"); fi
		continue
	fi
	if wait_log "$n" "04.dxr frame [0-9]* new scene" 90; then
		$H shot "$ev-2" >/dev/null
		results+=("$ev: home at the quay")
		cast_off || { results+=("could not cast off again"); break; }
	else
		$H shot "$ev-stuck" >/dev/null
		results+=("$ev: NOT home after 90 s: $(tail -n +"$n" "$LOG" | grep -a 'autosave' | tail -1)")
		break
	fi
done
printf '%s\n' "${results[@]}" | tee "$RUN_DIR/results.txt"
