"""Write the HD art index our ScummVM build reads (engines/director/hd.cpp).

	~/.venvs/mulle/bin/python tools/hd_index.py [BUILD_DIR]

BUILD_DIR (default build/bilar) holds manifest.json and hd/ from
extract_assets.py and upscale_game.py. Writes BUILD_DIR/hd/index.txt, one line
per bitmap with HD art, tab-separated:

	CAST  MEMBER  CATEGORY  variant=file ...

CAST is the cast file's name without extension (05, 00, CDDATA), MEMBER its
number as Lingo sees it, variant one of copy, matte, bgtrans (the ink the
sprite is drawn with), file relative to hd/. The engine finds the folder
through `hd_path` in scummvm.ini or as `HD` in the game folder.
"""

import json
import sys
from pathlib import Path


def main():
	build = Path(sys.argv[1] if len(sys.argv) > 1 else "build/bilar")
	manifest = json.loads((build / "manifest.json").read_text())
	lines = ["# HD art index: cast, member, category, variant=file (relative to this folder)"]
	for e in manifest:
		hd = e.get("hd")
		if not hd:
			continue
		files = ["%s=%s" % (variant, Path(path).relative_to("hd").as_posix()) for variant, path in sorted(hd.items())]
		lines.append("\t".join([e["cast"], str(e["member"]), e["category"]] + files))
	(build / "hd" / "index.txt").write_text("\n".join(lines) + "\n")
	print("%d bitmaps -> %s" % (len(lines) - 1, build / "hd" / "index.txt"))


if __name__ == "__main__":
	main()
