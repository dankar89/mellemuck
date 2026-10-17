#!/usr/bin/env bash
# Bygger båtar from a new player to the shelves: login (batar-login.sh), the
# blueprint (small hull and rudder), back to the boatyard, the cradle to the
# quay, the yard, cabinet 1 (movie 02). The game polls the mouse once per
# frame, so clicks are slow ones (press, 1 px, release).
#   batar-shelves.sh [PLAYER]     screenshots in $RUN_DIR (runs/batar-shelves)
set -uo pipefail
D="$(dirname "$0")"; H="$D/../harness.sh"
ROOT="$(cd "$D/../.." && pwd)"
export RUN_DIR="${RUN_DIR:-$ROOT/runs/batar-shelves}"
"$D/batar-login.sh" "${1:-Testa}" >/dev/null || exit 1
c() { $H drag "$1" "$2" "$1" $(( $2 + 1 )) >/dev/null; sleep "$3"; }
c 141 355 15     # the drawing on the table: the blueprint (15)
c 322 227 3      # small hull
c 181 241 3      # small rudder
c 604 451 15     # back to the boatyard
$H shot 03-hull >/dev/null
c 523 324 18     # the cradle: the quay (04)
$H shot 04-quay >/dev/null
c 625 245 16     # the shed: the yard (03)
$H shot 05-yard >/dev/null
c 160 200 16     # cabinet 1: the shelves (02)
$H shot 06-shelf1 || exit 1
