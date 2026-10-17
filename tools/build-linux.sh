#!/usr/bin/env bash
# Package Mulle Meck for Linux and the Steam Deck into dist/linux/MulleMeck/:
#   scummvm      our ScummVM, release build with only the Director engine; it
#                uses the system's SDL2, libpng, zlib and FreeType (all part of
#                SteamOS) and needs glibc 2.38+
#   runtime/     a portable Python 3.12 (python-build-standalone) with pygame-ce,
#                numpy, Pillow and paramiko
#   app/         the launcher, the HD tools, the icons and the Linux upscaler
#   data/        the menu font
#   Mulle Meck   the start script
# The games, HD art, saves and settings are not part of the package: the
# launcher's "copy to Steam Deck" sends them from the PC (docs/launcher.md).
# Downloads are cached in third_party/python-linux/. First-time setup of the
# ScummVM build folder: docs/tooling.md (Linux build).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="${BUILD:-$HOME/src/scummvm-linux}"
DIST="$ROOT/dist/linux/MulleMeck"
PL="$ROOT/third_party/python-linux"
PYTAG=20250409
PYVER=3.12.10
PYTGZ="$PL/cpython-$PYVER+$PYTAG-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
ESRZIP="$PL/realesrgan-ncnn-vulkan-20220424-ubuntu.zip"

[[ -f "$BUILD/config.mk" ]] || { echo "build-linux: $BUILD is not configured (see docs/tooling.md)" >&2; exit 1; }
make -C "$BUILD" -j"$(nproc)" >"$BUILD/build.log" 2>&1 || { tail -20 "$BUILD/build.log"; exit 1; }

mkdir -p "$DIST" "$PL"
strip -o "$DIST/scummvm" "$BUILD/scummvm"
mkdir -p "$DIST/data"
cp "$ROOT/third_party/fonts/Fredoka-SemiBold.ttf" "$ROOT/third_party/fonts/OFL.txt" "$DIST/data/"
# Stand-ins for the Windows fonts Director 7+ games name (Times New Roman, Arial,
# Courier New): Liberation, metric-compatible, SIL OFL (DirectorEngine::addFontSubstitutes()).
cp "$ROOT"/third_party/fonts/Liberation*.ttf "$ROOT/third_party/fonts/Liberation-LICENSE.txt" "$DIST/data/"

# Python
[[ -f "$PYTGZ" ]] || curl -sfL -o "$PYTGZ" \
	"https://github.com/astral-sh/python-build-standalone/releases/download/$PYTAG/$(basename "$PYTGZ" | sed 's/+/%2B/')"
rm -rf "$DIST/runtime" "$DIST/python"
tar -xzf "$PYTGZ" -C "$DIST"
mv "$DIST/python" "$DIST/runtime"
# No symlinks: the package lives on the Windows drive, and the Windows
# launcher reads it to send it to a Steam Deck (it cannot follow WSL's links).
find "$DIST/runtime" -type l | while read -r link; do
	target="$(readlink -f "$link")"
	rm "$link"
	if [[ -d "$target" ]]; then cp -r "$target" "$link"; else cp "$target" "$link"; fi
done
PY="$DIST/runtime/bin/python3"
# -s: not the build machine's own user site-packages (~/.local), or pip finds
# a library there, skips it, and the package lacks it (Pillow did, 2026-10-14:
# the Deck's launcher could not start).
"$PY" -s -m pip install -q --disable-pip-version-check --no-warn-script-location pygame-ce numpy pillow paramiko
# Only what the launcher and the HD tools use (as for Windows).
SP="$DIST/runtime/lib/python3.12/site-packages"
find "$DIST/runtime" -type d \( -name tests -o -name __pycache__ -o -name test \) -prune -exec rm -rf {} +
rm -rf "$SP/pygame/examples" "$SP/pygame/docs" "$SP"/pip "$SP"/pip-* "$DIST/runtime/lib/python3.12/idlelib" \
	"$DIST/runtime/lib/python3.12/tkinter" "$DIST/runtime/lib/python3.12/ensurepip"
# Nor what only building against Python, tkinter or a terminal needs (63 MB):
# libpython3.12.so is a second copy of the .so.1.0 python3 runs with (the
# symlinks became copies above).
RL="$DIST/runtime/lib"
rm -rf "$RL/libpython3.12.so" "$RL/pkgconfig" "$RL"/tcl8* "$RL"/tk8* "$RL"/Tix* "$RL"/itcl* "$RL"/thread2* \
	"$DIST/runtime/include" "$DIST/runtime/share" "$RL/python3.12/lib2to3" "$RL/python3.12/pydoc_data" \
	"$RL/python3.12/turtledemo"

# The launcher, the HD tools and their data, the icons.
rm -rf "$DIST/app"
mkdir -p "$DIST/app/launcher" "$DIST/app/tools" "$DIST/app/third_party/lucide"
cp "$ROOT"/launcher/*.py "$ROOT/launcher/icon.png" "$DIST/app/launcher/"
for t in director extract_assets upscale_game alpha_upscale morph hd_index iso_extract msi_extract; do
	cp "$ROOT/tools/$t.py" "$DIST/app/tools/"
done
cp -r "$ROOT/tools/data" "$DIST/app/tools/"
cp "$ROOT"/third_party/lucide/*.svg "$ROOT/third_party/lucide/LICENSE" "$DIST/app/third_party/lucide/"

# The upscaler (Linux build, MIT) and the three models of our recipe; the
# models are the same files as on Windows.
[[ -f "$ESRZIP" ]] || curl -sfL -o "$ESRZIP" \
	"https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/$(basename "$ESRZIP")"
ESR="$DIST/app/third_party/realesrgan-ncnn-vulkan"
mkdir -p "$ESR/models"
unzip -q -o -j "$ESRZIP" realesrgan-ncnn-vulkan -d "$ESR"
chmod +x "$ESR/realesrgan-ncnn-vulkan"
for m in ultrasharp-4x realesrgan-x4plus realesrgan-x4plus-anime; do
	cp "$ROOT/third_party/realesrgan-ncnn-vulkan/models/$m.param" "$ROOT/third_party/realesrgan-ncnn-vulkan/models/$m.bin" "$ESR/models/"
done

# Every library from the package itself, as on a machine without them.
PYTHONNOUSERSITE=1 PYTHONPATH="$DIST/app" "$PY" -s -c "import PIL.Image, pygame, numpy, paramiko, launcher.ui, launcher.hdjob" \
	|| { echo "build-linux: the package is missing a library" >&2; exit 1; }

# The start script.
cat > "$DIST/Mulle Meck" <<'SH'
#!/bin/sh
# Starts the Mulle Meck launcher from the folder this script is in.
HERE="$(cd "$(dirname "$0")" && pwd)"
# -s and PYTHONNOUSERSITE: only the package's own libraries, never the system user's.
PYTHONNOUSERSITE=1 PYTHONPATH="$HERE/app" exec "$HERE/runtime/bin/python3" -s -m launcher --root "$HERE" "$@"
SH
chmod +x "$DIST/Mulle Meck" "$DIST/scummvm"

echo "built: $DIST ($(du -sh "$DIST" | cut -f1))"
