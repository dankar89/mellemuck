#!/usr/bin/env bash
# Test flow for Bygger båtar's destinations: sails out with batar-sea.sh, then
# for each destination puts the boat on its map (Lingo: changeMap), next to it
# and then inside its radius, as if it had sailed there; waits for the
# destination movie and for the sea (05) again. Screenshots every 10 s in
# $RUN_DIR/<movie>-NN.png; a line per destination at the end (reached, back at
# sea, or where it stuck).
#   batar-dests.sh SAVEDIR PLAYER [MOVIE ...]   (default: all of them)
# Beside another session use your own DISP and a renamed SCUMMVM copy
# (harness.sh stop kills every ~/src/scummvm/scummvm).
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
ROOT="$(cd "$D/../.." && pwd)"
SAVES="${1:?save folder}"; PLAYER="${2:?player name}"; shift 2
export RUN_DIR="${RUN_DIR:-$ROOT/runs/batar-dests}"
LOG="$RUN_DIR/scummvm.log"
# movie: map point, where the boat is put first (deep water outside the
# outer radius) and then (deep water inside the inner radius); from the game
# data (CDdata.cxt objectNDB/mapNDB and the depth map, docs/game-bygger-batar.md).
# Random destinations: one entry per map they can be on.
declare -A DEST=(
	[77]="1,6 386,166 402,134" [76]="3,7 190,130 222,114" [79]="5,6 142,206 174,190"
	[88]="8,5 358,150 322,158" [78]="3,4 134,262 150,230" [80]="1,3 370,354 354,322"
	[85]="3,1 482,278 514,294" [86]="9,2 402,258 378,230" [81]="3,8 574,242 574,202"
	[84]="1,10 134,162 166,178" [83]="7,10 210,318 186,290" [87]="10,10 354,86 322,70"
	[70:5,4]="5,4 374,254 350,226" [70:6,7]="6,7 210,158 178,142"
	[71:4,5]="4,5 434,242 418,210" [71:7,8]="7,8 154,90 182,114"
)
RDEST=([70]=10 [71]=11)  # their object ids
ORDER=(77 76 79 88 78 80 85 86 81 84 83 87 70 71)
[[ $# -gt 0 ]] && ORDER=("$@")

lines() { wc -l <"$LOG"; }  # tail -n +N counts empty lines too
# Waits until a line after line $1 of the log matches $2; $3 seconds at most.
wait_log() {
	local from=$1 pat=$2 t=$3 i
	for ((i = 0; i < t; i += 2)); do
		tail -n +"$from" "$LOG" | grep -ac "$pat" >/dev/null && return 0  # not -q: tail gets SIGPIPE, pipefail fails it
		sleep 2
	done
	return 1
}
lingo_val() {  # puts the value of $1 into the log and prints it
	local n; n=$(lines)
	$H lingo "put \"VAL\", $1" >/dev/null
	sleep 1.5
	tail -n +"$n" "$LOG" | grep -a '^-- "VAL"' | tail -1 | sed 's/^-- "VAL" //'
}

"$D/batar-sea.sh" "$SAVES" "$PLAYER" >/dev/null || exit 1
sleep 8
results=()
for m in "${ORDER[@]}"; do
	key=$m
	if [[ -n ${RDEST[$m]:-} ]]; then
		rd=$(lingo_val "getaProp(getRandomDestinations(the world of gMulleGlobals), ${RDEST[$m]})")
		key="$m:$(sed -E 's/point\(([0-9]+), ([0-9]+)\)/\1,\2/' <<<"$rd")"
		[[ -n ${DEST[$key]:-} ]] || { results+=("$m: not placed this trip ($rd)"); continue; }
	fi
	read -r map far near <<<"${DEST[$key]}"
	# Wait until the sea gives the boat back to the player; keep Mulle fed
	# (he goes home hungry after a few minutes).
	for i in $(seq 15); do
		[[ $(lingo_val "the programControlsBoat of the boat of gDir") == 0 ]] && break
		sleep 2
	done
	$H lingo 'set the mulleHunger of the boat of gDir to 10000' >/dev/null
	start=$(lines)
	$H lingo "setShowCoordinate(the boat of gDir, point($far))" >/dev/null
	sleep 0.5
	$H lingo "changeMap(gDir, point($map), #Absolute)" >/dev/null
	sleep 2
	$H lingo "setShowCoordinate(the boat of gDir, point($near))" >/dev/null
	if ! wait_log "$start" "autosave $m.dxr" 60; then
		$H shot "$m-notreached" >/dev/null
		results+=("$m: NOT reached (map $map, $near)")
		continue
	fi
	after=$(lines)
	back=0
	for ((i = 1; i <= 30; i++)); do
		$H shot "$(printf '%s-%02d' "$m" $i)" >/dev/null
		if wait_log "$after" "autosave 05.dxr frame [0-9]* new scene" 10; then back=1; break; fi
	done
	if ((back)); then
		results+=("$m: reached, back at sea")
	else
		results+=("$m: reached, NOT back at sea after 5 min: $(tail -n +"$start" "$LOG" | grep -a 'autosave' | tail -1)")
		break
	fi
	sleep 6
done
printf '%s\n' "${results[@]}" | tee "$RUN_DIR/results.txt"
