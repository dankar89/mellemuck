#!/usr/bin/env bash
# Package the launcher for Windows into dist/windows/MulleMeck/: Python's
# embeddable distribution with the launcher, our HD tools and their libraries
# in runtime/, and "Mulle Meck.exe", a small starter compiled with MinGW. The
# player needs no Python. Downloads are cached in third_party/python-win/.
# See docs/launcher.md.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist/windows/MulleMeck"
PW="$ROOT/third_party/python-win"
PYVER=3.12.10
EMBED="$PW/python-$PYVER-embed-amd64.zip"
PY="$HOME/.venvs/mulle/bin/python"

# Not while the package runs on Windows (its files are in use: a rebuild would
# delete half of them and then fail).
running="$(powershell.exe -NoProfile -Command "(Get-Process | Where-Object { \$_.Path -like '*\\dist\\windows\\MulleMeck\\*' } | Select-Object -ExpandProperty Name) -join ' '" 2>/dev/null | tr -d '\r')"
if [[ -n "$running" ]]; then
	echo "$(basename "$0"): close Mulle Meck on Windows first (running: $running)" >&2
	exit 1
fi

mkdir -p "$PW"
[[ -f "$EMBED" ]] || curl -sfL -o "$EMBED" "https://www.python.org/ftp/python/$PYVER/python-$PYVER-embed-amd64.zip"
"$PY" -m pip download -q --only-binary=:all: --platform win_amd64 --python-version 3.12 --implementation cp \
	-d "$PW/wheels" pygame-ce numpy pillow paramiko
# No scipy since 2026-10-14 (tools/morph.py does its few mask operations):
# not from an older download either.
rm -f "$PW"/wheels/scipy-*.whl

RT="$DIST/runtime"
rm -rf "$RT"
mkdir -p "$RT/Lib/site-packages" "$RT/app"
unzip -q "$EMBED" -d "$RT"
for whl in "$PW"/wheels/*.whl; do
	unzip -q -o "$whl" -d "$RT/Lib/site-packages"
done
# No test suites or examples.
SP="$RT/Lib/site-packages"
find "$SP" -type d \( -name tests -o -name __pycache__ \) -prune -exec rm -rf {} +
rm -rf "$SP/pygame/examples" "$SP/pygame/docs"
# Where the embedded Python looks for modules (it ignores PYTHONPATH).
printf 'python312.zip\r\n.\r\nLib\\site-packages\r\napp\r\nimport site\r\n' > "$RT/python312._pth"

# The launcher and the HD tools it runs, with the icons it draws.
mkdir -p "$RT/app/launcher" "$RT/app/tools" "$RT/app/third_party/lucide"
cp "$ROOT"/launcher/*.py "$ROOT/launcher/icon.png" "$RT/app/launcher/"
for t in director extract_assets upscale_game alpha_upscale morph hd_index iso_extract msi_extract; do
	cp "$ROOT/tools/$t.py" "$RT/app/tools/"
done
cp -r "$ROOT/tools/data" "$RT/app/tools/"  # Director's palettes
cp "$ROOT"/third_party/lucide/*.svg "$ROOT/third_party/lucide/LICENSE" "$RT/app/third_party/lucide/"
# The upscaler for the HD button, with the three models our recipe uses
# (tools/upscale_game.py RECIPES): 79 MB.
ESR="$ROOT/third_party/realesrgan-ncnn-vulkan"
mkdir -p "$RT/app/third_party/realesrgan-ncnn-vulkan/models"
cp "$ESR/realesrgan-ncnn-vulkan.exe" "$ESR/vcomp140.dll" "$ESR/README_windows.md" "$RT/app/third_party/realesrgan-ncnn-vulkan/"
for m in ultrasharp-4x realesrgan-x4plus realesrgan-x4plus-anime; do
	cp "$ESR/models/$m.param" "$ESR/models/$m.bin" "$RT/app/third_party/realesrgan-ncnn-vulkan/models/"
done

# The starter, with the icon.
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
cp "$ROOT/launcher/icon.ico" "$BUILD/"
echo '1 ICON "icon.ico"' > "$BUILD/icon.rc"
x86_64-w64-mingw32-windres "$BUILD/icon.rc" -O coff -o "$BUILD/icon.o"
x86_64-w64-mingw32-gcc -O2 -municode -mwindows -o "$DIST/Mulle Meck.exe" "$ROOT/launcher/starter.c" "$BUILD/icon.o"
x86_64-w64-mingw32-strip "$DIST/Mulle Meck.exe"

# The Linux package (tools/build-linux.sh), which "copy to Steam Deck" sends,
# without what a Deck does not need (launcher/deck.py NOT_ON_DECK_*: numpy,
# the SSH libraries, the upscaler).
if [[ -d "$ROOT/dist/linux/MulleMeck/runtime" ]]; then
	rm -rf "$DIST/linux"
	cp -r "$ROOT/dist/linux/MulleMeck" "$DIST/linux"
	(cd "$DIST/linux" && find . -mindepth 1 | sed 's|^\./||' | PYTHONPATH="$ROOT" "$PY" -c "
import sys
from launcher.deck import not_needed_on_deck
print('\n'.join(not_needed_on_deck(l.strip() for l in sys.stdin)))" | while read -r p; do rm -rf -- "$p"; done)
else
	echo "note: no dist/linux/MulleMeck (tools/build-linux.sh): no Steam Deck copy in this package" >&2
fi

echo "built: $DIST/Mulle Meck.exe and runtime/ ($(du -sh "$RT" | cut -f1))"
