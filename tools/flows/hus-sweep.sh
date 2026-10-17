#!/usr/bin/env bash
# Bygg hus: visits scenes one after another (harness.sh lingo go) and keeps a
# screenshot and the log lines of each, to find what ScummVM still lacks.
#   hus-sweep.sh SAVEDIR MOVIE... [-- 'lingo line' ...]
# e.g. hus-sweep.sh runs/hus-play/saves 05 06 07 50 51
# Per scene: $RUN_DIR/sweep-NN.png and sweep-NN.log (warnings, errors and the
# game's own put lines, repeats counted). An alert box is closed with Return.
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
ROOT="$(cd "$D/../.." && pwd)"
SAVES="${1:?save folder}"; shift
MOVIES=(); while [[ $# -gt 0 && "$1" != "--" ]]; do MOVIES+=("$1"); shift; done
[[ "${1:-}" == "--" ]] && shift
export RUN_DIR="${RUN_DIR:-$ROOT/runs/hus-sweep}"
LOG="$RUN_DIR/scummvm.log"
WAIT=5 "$D/hus-goto.sh" "$SAVES" 04 "$@" >/dev/null 2>&1
for m in "${MOVIES[@]}"; do
	n=$(wc -l <"$LOG")
	$H lingo "go(1, \"$m\")"
	for i in $(seq 1 20); do sleep 1; tail -n +$n "$LOG" | grep -q "$m.dxr frame" && break; done
	sleep "${SCENE_WAIT:-20}"
	$H shot "sweep-$m"
	tail -n +$n "$LOG" | grep -a -v '^PLAY\|preLoadMember\|INCORRECT\|^000000\|kParentScript\|test Lingo\|Start save\|End save\|did not return value\|image 9 not found\|bit depth is 0' \
		| sed 's/0x[0-9a-f]*/0x/g' | sort | uniq -c | sort -rn >"$RUN_DIR/sweep-$m.log"
	grep -q 'b_alert' "$RUN_DIR/sweep-$m.log" && $H key Return
	echo "== $m: $(wc -l <"$RUN_DIR/sweep-$m.log") distinct lines"
done
