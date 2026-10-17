#!/usr/bin/env bash
# Regression check for our ScummVM changes:
#  1. ScummVM's own Lingo test suite (engines/director/lingo/tests), compared with
#     the same run on unmodified ScummVM (~/src/scummvm-base, a git worktree of the
#     commit our branch is based on). Any new failing assertion or new kind of
#     warning is reported.
#  2. Our Bygger bilar test flows (new player, junk pile, garage wander).
#
#   scummvm-regress.sh [--no-flows]
#
# Beside another session on this machine: REGRESS_OUT=runs/regress-mine
# SCUMMVM=<a copy of the patched binary> DISP=:95 (own results, binary and X
# screen; the baseline is copied from runs/regress).
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PATCHED="$HOME/src/scummvm"
BASE="$HOME/src/scummvm-base"
OUT="${REGRESS_OUT:-$ROOT/runs/regress}"
mkdir -p "$OUT"
for f in base.warnings base.asserts; do
	[[ -f "$OUT/$f" || ! -f "$ROOT/runs/regress/$f" ]] || cp "$ROOT/runs/regress/$f" "$OUT/"
done
PATCHED_BIN="${SCUMMVM:-$PATCHED/scummvm}"

run_tests() {  # $1 = scummvm source/build dir, $2 = output name, $3 = binary (default $1/scummvm)
	(cd "$1" && SDL_VIDEODRIVER=offscreen SDL_AUDIODRIVER=dummy timeout 600 "${3:-./scummvm}" \
		--config="$OUT/$2.ini" -d11 -p engines/director/lingo/tests/ directortest >"$OUT/$2.log" 2>&1)
	grep "WARNING" "$OUT/$2.log" | sed -E 's/0x[0-9a-f]+/0x?/g; s/[0-9]+/N/g' | sort | uniq -c | sort -k2 >"$OUT/$2.warnings"
	grep "BUILDBOT: LB::b_scummvmassert" "$OUT/$2.log" >"$OUT/$2.asserts" || true
}

status=0
[[ -f "$OUT/base.warnings" ]] || { echo "baseline: running unmodified ScummVM's Lingo tests"; run_tests "$BASE" base; }
echo "patched: running Lingo tests"
run_tests "$PATCHED" patched "$PATCHED_BIN"
if ! diff -q "$OUT/base.asserts" "$OUT/patched.asserts" >/dev/null; then
	echo "LINGO TESTS: assertion results differ from unmodified ScummVM:"; diff "$OUT/base.asserts" "$OUT/patched.asserts"; status=1
else
	echo "lingo tests: same assertions as unmodified ScummVM ($(wc -l <"$OUT/base.asserts") known failures)"
fi
if ! diff -q "$OUT/base.warnings" "$OUT/patched.warnings" >/dev/null; then
	echo "lingo tests: warnings differ (check these):"; diff "$OUT/base.warnings" "$OUT/patched.warnings"
fi

if [[ "${1:-}" != "--no-flows" ]]; then
	for flow in bilar-junkpile bilar-garage-wander; do
		result=$("$ROOT/tools/flows/$flow.sh" 2>&1 | tail -1)
		if pgrep -f "${SCUMMVM:-src/scummvm/scummvm} --config" >/dev/null; then
			echo "flow $flow: ok ${result}"
		else
			echo "FLOW $flow: ScummVM is not running at the end: ${result}"; status=1
		fi
		"$ROOT/tools/harness.sh" stop >/dev/null
	done
fi
exit $status
