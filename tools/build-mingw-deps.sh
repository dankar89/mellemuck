#!/usr/bin/env bash
# Build the static MinGW libraries the Windows ScummVM build uses beyond SDL2:
# zlib, libpng (HD art) and FreeType (menu text). Installs into
# ~/.local/opt/mingw-deps; sources are downloaded to ~/.cache/mingw-deps-build/.
#
#   build-mingw-deps.sh        build what is missing
#
# Then configure ~/src/scummvm-win with
#   --with-zlib-prefix=$HOME/.local/opt/mingw-deps --with-png-prefix=... --with-freetype2-prefix=...
# (tools/build-windows.sh passes these; see docs/tooling.md, Windows build).
set -euo pipefail
trap 'echo "build-mingw-deps: failed (line $LINENO)" >&2' ERR

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="$HOME/.local/opt/mingw-deps"
# On the Linux side: FreeType's build cannot write objs/ftexport.sym on /mnt/c.
WORK="$HOME/.cache/mingw-deps-build"
HOST=x86_64-w64-mingw32
JOBS=$(nproc)

ZLIB=zlib-1.3.1
PNG=libpng-1.6.43
FREETYPE=freetype-2.13.2

fetch() {	# fetch NAME URL
	[[ -f "$WORK/$1.tar.gz" ]] || curl -fsSL -o "$WORK/$1.tar.gz" "$2"
	rm -rf "$WORK/$1" && tar -xzf "$WORK/$1.tar.gz" -C "$WORK"
}

mkdir -p "$WORK" "$PREFIX"

if [[ ! -f "$PREFIX/lib/libz.a" ]]; then
	fetch $ZLIB "https://zlib.net/fossils/$ZLIB.tar.gz"
	(cd "$WORK/$ZLIB" && make -f win32/Makefile.gcc PREFIX=$HOST- -j"$JOBS" libz.a >/dev/null \
		&& make -f win32/Makefile.gcc install PREFIX=$HOST- SHARED_MODE=0 \
			INCLUDE_PATH="$PREFIX/include" LIBRARY_PATH="$PREFIX/lib" BINARY_PATH="$PREFIX/bin" >/dev/null)
	echo "built $ZLIB"
fi

if [[ ! -f "$PREFIX/lib/libpng.a" ]]; then
	fetch $PNG "https://download.sourceforge.net/libpng/$PNG.tar.gz"
	(cd "$WORK/$PNG" && CPPFLAGS="-I$PREFIX/include" LDFLAGS="-L$PREFIX/lib" \
		./configure --host=$HOST --prefix="$PREFIX" --enable-static --disable-shared >/dev/null \
		&& make -j"$JOBS" >/dev/null && make install >/dev/null)
	echo "built $PNG"
fi

if [[ ! -f "$PREFIX/lib/libfreetype.a" ]]; then
	fetch $FREETYPE "https://download.savannah.gnu.org/releases/freetype/$FREETYPE.tar.gz"
	(cd "$WORK/$FREETYPE" && ZLIB_CFLAGS="-I$PREFIX/include" ZLIB_LIBS="-L$PREFIX/lib -lz" \
		./configure --host=$HOST --prefix="$PREFIX" --enable-static --disable-shared \
			--with-zlib=yes --with-png=no --with-bzip2=no --with-brotli=no --with-harfbuzz=no >/dev/null \
		&& make -j"$JOBS" >/dev/null && make install >/dev/null)
	echo "built $FREETYPE"
fi

ls "$PREFIX/lib"
