"""What the launcher knows about each game on this machine: found or not, how
far its HD art is, and its pictures.

HD progress comes from the game's HD folder: index.txt lists every HD image
the engine can use, and the share of them on disk is the progress. The engine
draws any image without an HD file from the original art, so a half-made set
plays fine.
"""
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from .catalog import GAMES, GameInfo

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def find_file(root, rel):
	"""root/rel with any case in each part (discs are upper case, Linux is not
	forgiving), or None."""
	path = Path(root)
	for part in Path(rel).parts:
		if not path.is_dir():
			return None
		match = next((p for p in path.iterdir() if p.name.lower() == part.lower()), None)
		if match is None:
			return None
		path = match
	return path


@dataclass
class HDStatus:
	done: int = 0
	total: int = 0

	@property
	def started(self):
		return self.done > 0

	@property
	def complete(self):
		return self.total > 0 and self.done >= self.total

	@property
	def fraction(self):
		return self.done / self.total if self.total else 0.0


def read_hd_status(hd_dir):
	index = Path(hd_dir) / "index.txt"
	if not index.exists():
		return HDStatus()
	files = []
	for line in index.read_text(encoding="utf-8", errors="replace").splitlines():
		if not line or line.startswith("#"):
			continue
		files += [item.split("=", 1)[1] for item in line.split("\t")[3:] if "=" in item]
	done = sum(1 for f in files if (Path(hd_dir) / f).exists())
	return HDStatus(done, len(files))


@dataclass
class Game:
	info: GameInfo
	root: Path
	found: bool = False
	hd: HDStatus = field(default_factory=HDStatus)
	cover: Image.Image | None = None
	backdrop: Image.Image | None = None

	@property
	def folder(self):
		return self.root / "games" / self.info.id

	@property
	def hd_dir(self):
		return self.folder / "HD"

	def refresh(self, hd=True):
		"""What is on disk now. hd=False leaves the HD progress (counting the
		HD files is the slow part) for a second pass."""
		self.found = find_file(self.folder, self.info.marker) is not None
		if self.found:
			self.cover = self.picture("cover", self.info.cover)
			self.backdrop = self.picture("backdrop", self.info.backdrop)
		else:
			self.cover = self.backdrop = None
		if hd:
			self.hd = read_hd_status(self.hd_dir) if self.found else HDStatus()

	def picture(self, which, member):
		"""A bitmap of the player's disc, the HD one when it exists. Cached in
		cache/<id>/."""
		if member is None:
			return None
		cast, name = member
		hd = self.hd_file(cast, name)
		cache = self.root / "cache" / self.info.id / f"{which}-{cast}-{name}{'-hd' if hd else ''}.png"
		if cache.exists():
			return Image.open(cache).convert("RGB")
		try:
			data = find_file(self.folder, self.info.data) if self.info.data else self.folder
			img = Image.open(hd).convert("RGB") if hd else extract_bitmap(data, cast, name)
		except Exception as e:  # a damaged or unexpected disc: the plain card it is
			print(f"launcher: no {which} for {self.info.id}: {e}", file=sys.stderr)
			return None
		if img is not None:
			cache.parent.mkdir(parents=True, exist_ok=True)
			img.save(cache)
		return img

	def hd_file(self, cast, name):
		index = self.hd_dir / "index.txt"
		if not index.exists():
			return None
		for line in index.read_text(encoding="utf-8", errors="replace").splitlines():
			parts = line.split("\t")
			if len(parts) < 4 or parts[0] != cast:
				continue
			for item in parts[3:]:
				variant, _, rel = item.partition("=")
				if variant == "copy" and f"_{name}." in rel and (self.hd_dir / rel).exists():
					return self.hd_dir / rel
		return None


def extract_bitmap(game_dir, cast, name):
	"""The bitmap called name in cast file <cast> of the disc, as RGB (any
	bit depth)."""
	if game_dir is None:
		return None
	if str(TOOLS) not in sys.path:
		sys.path.insert(0, str(TOOLS))
	from director import DirectorFile, cast_files, parse_cast_member

	movies = find_file(game_dir, "MOVIES")
	files = cast_files(movies) if movies else {}
	data = find_file(game_dir, "DATA")
	if data:
		for p in data.iterdir():
			if p.suffix.upper() == ".CST":
				files.setdefault(p.stem.upper(), p)
	path = files.get(cast.upper())
	if path is None:
		return None
	f = DirectorFile(path)
	keys = f.keys()
	first = next((lib["min"] for lib in f.cast_libs() if not lib["path"]), 1)
	for res in f.cast_resources(first).values():
		info = parse_cast_member(f.chunk(res))
		if info["type"] != "bitmap" or info["name"] != name:
			continue
		rgb = f.bitmap_rgb(res, info, keys)
		return Image.fromarray(rgb) if rgb is not None else None
	return None


def scan(root):
	"""Every game in the catalog, with what is known about it here. Reading the
	HD folders and discs takes a moment, so it runs in a thread; the games fill
	in when ready (Game.found etc.)."""
	games = [Game(info, Path(root)) for info in GAMES]

	def work():
		for g in games:
			g.refresh(hd=False)
		for g in games:
			g.hd = read_hd_status(g.hd_dir) if g.found else HDStatus()

	thread = threading.Thread(target=work, daemon=True)
	thread.start()
	return games, thread
