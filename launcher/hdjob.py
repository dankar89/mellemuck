"""The HD art for one game, made on this machine (the launcher's HD button).

  python -m launcher.hdjob GAME_DIR WORK_DIR [--limit N] [--keep]

GAME_DIR is games/<id>/ with the disc's files. The HD art goes into
GAME_DIR/HD image by image as it is done: the index lists every image from the
start, and the engine draws any image not there yet from the original art, so
the game can be played at any point (and after a stop or a crash). WORK_DIR
keeps the extracted originals and the 4x upscales, so a stopped job carries
on where it was; it is removed once the set is complete (--keep keeps it).
--limit N does only the first N bitmaps (for tests).

The steps are our dev pipeline's (docs/upscaling.md): extract_assets,
Real-ESRGAN per recipe on packed sheets, the alpha composition per ink.

Lines for the launcher on stdout:
  PHASE extract | PHASE upscale | PROGRESS <done> <total> | DONE | ERROR <text>
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import extract_assets  # noqa: E402
from upscale_game import RECIPES, compose, flat_name, hd_rel, run_recipe  # noqa: E402

SCALE = 3


def say(*parts):
	print(*parts, flush=True)


def write_index(hd, entries):
	"""The engine's index (engines/director/hd.cpp) for every image, done or not."""
	lines = ["# HD art index: cast, member, category, variant=file (relative to this folder)"]
	for e in entries:
		files = [f"{v}={hd_rel(e, v).as_posix()}" for v in sorted(e["variants"])]
		lines.append("\t".join([e["cast"], str(e["member"]), e["category"]] + files))
	hd.mkdir(parents=True, exist_ok=True)
	tmp = hd / "index.txt.tmp"
	tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
	tmp.replace(hd / "index.txt")


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("game", type=Path)
	ap.add_argument("work", type=Path)
	ap.add_argument("--limit", type=int)
	ap.add_argument("--keep", action="store_true")
	args = ap.parse_args()
	game, work, hd = args.game, args.work, args.game / "HD"

	manifest_path = work / "manifest.json"
	if not manifest_path.exists():
		say("PHASE extract")
		work.mkdir(parents=True, exist_ok=True)
		extract_assets.extract(game, work)
	manifest = json.loads(manifest_path.read_text())
	entries = [e for e in manifest if e["category"] in RECIPES and e["variants"]]
	if args.limit:
		entries = entries[:args.limit]
	write_index(hd, entries)

	total = sum(len(e["variants"]) for e in entries)
	complete = lambda e: all((hd / hd_rel(e, v)).exists() for v in e["variants"])
	pending = {flat_name(e): e for e in entries if not complete(e)}
	done = total - sum(len(e["variants"]) for e in pending.values())
	say("PROGRESS", done, total)

	def on_cached(names):
		nonlocal done
		for n in names:
			e = pending.pop(n, None)
			if e is not None:
				compose(work, e, SCALE, hd)
				done += len(e["variants"])
		say("PROGRESS", done, total)

	# Upscaled before a stop but not composed yet.
	on_cached([n for n, e in list(pending.items()) if (work / "up4x" / e["category"] / n).exists()])
	say("PHASE upscale")
	for category in RECIPES:
		run_recipe(work, category, [e for e in pending.values() if e["category"] == category], on_cached)
	if pending:
		raise SystemExit(f"{len(pending)} images not done")
	say("DONE")
	if not args.keep:
		shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
	try:
		main()
	except (SystemExit, Exception) as e:
		if isinstance(e, SystemExit) and e.code in (None, 0):
			raise
		text = e.code if isinstance(e, SystemExit) else f"{type(e).__name__}: {e}"
		if isinstance(e, subprocess.CalledProcessError):
			text = "the upscaler failed (no Vulkan graphics card?)"
		say("ERROR", text)
		sys.exit(1)
