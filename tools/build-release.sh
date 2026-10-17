#!/usr/bin/env bash
# Release archives for players, from the packages (build them first:
# build-windows.sh, build-linux.sh, build-launcher-windows.sh):
#   dist/release/MulleMeck-Windows.zip   (with linux/ for the Steam Deck copy)
#   dist/release/MulleMeck-Linux.tar.gz
# No version in the names: the README's link .../releases/latest/download/
# MulleMeck-Windows.zip always gets the newest. The version is in LÄS MIG.
# Only the programs: never games/, saves/, HD art, the launcher's settings
# (launcher.json has the Deck's address) or logs. The settings file is a
# fresh one. A check at the end fails on anything from a game disc or with a
# personal detail of this machine.
#   tools/build-release.sh VERSION      e.g. tools/build-release.sh 0.1.0
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:?version, e.g. 0.1.0}"
WIN="$ROOT/dist/windows/MulleMeck"
LIN="$ROOT/dist/linux/MulleMeck"
OUT="$ROOT/dist/release"
STAGE="$OUT/stage"
PY="$HOME/.venvs/mulle/bin/python"

rm -rf "$STAGE"
mkdir -p "$STAGE/windows/MulleMeck" "$STAGE/linux/MulleMeck"

# The settings a first start needs (ScummVM's warning about Director games
# off, autosaves, fullscreen and HD on); the launcher adds the rest.
settings() {
	printf '[scummvm]\r\nenable_unsupported_game_warning=false\r\nplay_log=true\r\nautosave_period=120\r\nfullscreen=true\r\nhd_art=true\r\n' >"$1"
}

# Texts for the player, the licences and the ScummVM source.
texts() {
	sed "s/{VERSION}/$VERSION/" "$ROOT/release/LÄS MIG.txt" >"$1/LÄS MIG.txt"
	cp "$ROOT/release/LICENSER.txt" "$1/"
	cp -r "$ROOT/release/licenser" "$1/"
	mkdir -p "$1/källkod"
	cp "$ROOT/patches/scummvm-mulle.patch" "$1/källkod/"
	printf 'ScummVM med Mulle Meck-ändringarna:\nhttps://github.com/scummvm/scummvm, commit %s,\nmed scummvm-mulle.patch (git apply). Mer: https://github.com/dankar89/mellemuck\n' \
		"$(git -C "$HOME/src/scummvm" rev-parse --short=10 HEAD~1)" >"$1/källkod/README.txt"
}

W="$STAGE/windows/MulleMeck"
for f in "Mulle Meck.exe" scummvm.exe SDL2.dll data runtime linux; do
	cp -a "$WIN/$f" "$W/"
done
settings "$W/scummvm.ini"
texts "$W"
# Windows reads the texts best with CRLF.
for f in "$W/LÄS MIG.txt" "$W/LICENSER.txt"; do sed -i 's/\r\?$/\r/' "$f"; done

L="$STAGE/linux/MulleMeck"
cp -a "$LIN/." "$L/"
rm -rf "$L/games" "$L/saves" "$L/cache" "$L/launcher.json" "$L/launcher.log"
settings "$L/scummvm.ini"
sed -i 's/\r$//' "$L/scummvm.ini"
texts "$L"

# The check: nothing from a disc or made from one, no personal details.
fail=0
while IFS= read -r -d '' f; do
	echo "release: does not belong in a release: ${f#$STAGE/}" >&2
	fail=1
done < <(find "$STAGE" \( -iname '*.dxr' -o -iname '*.cxt' -o -iname '*.cst' -o -iname '*.dir' \
	-o -iname '*.cct' -o -iname '*.dcr' -o -iname '*.iso' -o -iname '*.casttext' -o -iname '*.x32' \
	-o -iname 'launcher.json' -o -iname '*.log' -o -iname 'garygadget*' \
	-o \( -type d \( -name games -o -name saves -o -name cache -o -name HD -o -name hd-work \) \) \) -print0)
# This machine's user name is read here, never written into the file.
if grep -r -l -I -i -E "192\\.168\\.|/mnt/c/Users/[a-z]|C:\\\\Users\\\\[a-z]|/home/$(id -un)/" "$STAGE" \
	--exclude-dir=Lib --exclude-dir=lib --exclude='*.patch' 2>/dev/null; then
	echo "release: personal details in the files above" >&2
	fail=1
fi
((fail == 0)) || exit 1

mkdir -p "$OUT"
rm -f "$OUT/MulleMeck-Windows.zip" "$OUT/MulleMeck-Linux.tar.gz"
# Python's zipfile: UTF-8 names (LÄS MIG.txt) flagged so Windows shows them right.
(cd "$STAGE/windows" && "$PY" - "$OUT/MulleMeck-Windows.zip" <<'EOF'
import os, sys, zipfile
with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
	for dirpath, dirnames, filenames in os.walk("MulleMeck"):
		dirnames.sort()
		for name in sorted(filenames):
			path = os.path.join(dirpath, name)
			info = zipfile.ZipInfo.from_file(path)
			# Keep the Linux programs executable for the Steam Deck copy.
			info.external_attr = (os.stat(path).st_mode & 0xFFFF) << 16
			info.compress_type = zipfile.ZIP_DEFLATED
			with open(path, "rb") as f:
				z.writestr(info, f.read(), compresslevel=9)
EOF
)
tar -C "$STAGE/linux" -czf "$OUT/MulleMeck-Linux.tar.gz" MulleMeck
rm -rf "$STAGE"
ls -l "$OUT"
