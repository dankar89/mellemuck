#!/usr/bin/env bash
# Rebuild the standalone Windows ScummVM (cross-compiled with MinGW from the
# same source as the Linux build) and refresh dist/windows/MulleMeck/.
# First-time setup is described in docs/tooling.md (Windows build).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="${BUILD:-$HOME/src/scummvm-win}"
SDL="${SDL:-$HOME/.local/opt/sdl2-mingw}"
DIST="$ROOT/dist/windows/MulleMeck"

# Not while the package runs on Windows (its files are in use: a rebuild would
# delete half of them and then fail).
running="$(powershell.exe -NoProfile -Command "(Get-Process | Where-Object { \$_.Path -like '*\\dist\\windows\\MulleMeck\\*' } | Select-Object -ExpandProperty Name) -join ' '" 2>/dev/null | tr -d '\r')"
if [[ -n "$running" ]]; then
	echo "$(basename "$0"): close Mulle Meck on Windows first (running: $running)" >&2
	exit 1
fi

[[ -f "$BUILD/config.mk" ]] || { echo "build-windows: $BUILD is not configured (see docs/tooling.md)" >&2; exit 1; }
# Leave out ScummVM's CJK font pack (38 MB, embedded since FreeType is on;
# Mulle needs none of it).
BIG_RH="$BUILD/dists/scummvm_rc_engine_data_big.rh"
[[ -s "$BIG_RH" ]] && rm -f "$BIG_RH"
make -C "$BUILD" -j"$(nproc)" DIST_FILES_ENGINEDATA_BASE_BIG= >"$BUILD/build.log" 2>&1 || { tail -20 "$BUILD/build.log"; exit 1; }

mkdir -p "$DIST"
x86_64-w64-mingw32-strip -o "$DIST/scummvm.exe" "$BUILD/scummvm.exe"
cp "$SDL/bin/SDL2.dll" "$DIST/"
# The pause menu's font (OFL), found through --extrapath="%~dp0data" in the .bat.
mkdir -p "$DIST/data"
cp "$ROOT/third_party/fonts/Fredoka-SemiBold.ttf" "$ROOT/third_party/fonts/OFL.txt" "$DIST/data/"
# Stand-ins for the Windows fonts Director 7+ games name (Times New Roman, Arial,
# Courier New): Liberation, metric-compatible, SIL OFL (DirectorEngine::addFontSubstitutes()).
cp "$ROOT"/third_party/fonts/Liberation*.ttf "$ROOT/third_party/fonts/Liberation-LICENSE.txt" "$DIST/data/"
echo "built: $DIST/scummvm.exe ($(du -h "$DIST/scummvm.exe" | cut -f1))"
