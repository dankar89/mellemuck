#!/usr/bin/env bash
# Run every upscaling model over a folder of sample images so they can be compared.
#
#   upscale-compare.sh [INPUT_DIR] [OUT_DIR]
#
# Each model writes 4x output to OUT_DIR/<model>/, then a 3x copy (Lanczos
# downscale, the target 1920x1440 for full screens) to OUT_DIR/<model>-3x/.
# Plain nearest-neighbour and Lanczos 3x baselines are written alongside.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IN="$(realpath "${1:-$ROOT/upscale-test/input}")"
OUT="$(realpath -m "${2:-$ROOT/upscale-test/out}")"
ESRGAN_DIR="$ROOT/third_party/realesrgan-ncnn-vulkan"
MODELS=(${MODELS:-realesrgan-x4plus realesrgan-x4plus-anime realesr-animevideov3-x4 ultrasharp-4x remacri-4x high-fidelity-4x})

mkdir -p "$OUT/nearest-3x" "$OUT/lanczos-3x"
for f in "$IN"/*.png; do
	n=$(basename "$f")
	convert "$f" -filter point -resize 300% "$OUT/nearest-3x/$n"
	convert "$f" -filter lanczos -resize 300% "$OUT/lanczos-3x/$n"
done

for m in "${MODELS[@]}"; do
	mkdir -p "$OUT/$m" "$OUT/$m-3x"
	start=$(date +%s)
	# The Windows build runs through WSL interop; it resolves relative paths from the cwd.
	(cd "$ESRGAN_DIR" && ./realesrgan-ncnn-vulkan.exe -i "$(realpath --relative-to="$ESRGAN_DIR" "$IN")" \
		-o "$(realpath --relative-to="$ESRGAN_DIR" "$OUT/$m")" -n "$m" -f png >/dev/null 2>&1)
	for f in "$OUT/$m"/*.png; do
		convert "$f" -filter lanczos -resize 75% "$OUT/$m-3x/$(basename "$f")"
	done
	echo "$m: $(( $(date +%s) - start ))s"
done
