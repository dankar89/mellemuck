"""Finding a game's files on this machine and bringing them into games/<id>/.

A game can come as a disc in a drive (or a mounted image), a disc image
(.iso), a zip (with the disc's files, or with an .iso inside), or a folder with a copy of the disc. Each
is recognised by the game's marker file (catalog.py), wherever it sits in it.

search() looks in the usual places without asking anything: drives, then the
user's Downloads, Desktop and Documents, two folders deep. The launcher opens
a file dialog only when that finds nothing.
"""
import os
import shutil
import string
import sys
import zipfile
from pathlib import Path, PurePosixPath

from .catalog import GAMES

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
	sys.path.insert(0, str(TOOLS))
import iso_extract  # noqa: E402
import msi_extract  # noqa: E402

MAX_DEPTH = 2


def games_in(paths):
	"""{game: prefix} for every game whose marker is among paths (lower case,
	'/'-separated, relative to the source); prefix is the folder inside the
	source that holds the disc (where the marker's root is)."""
	out = {}
	for game in GAMES:
		marker = game.marker.lower()
		for p in paths:
			if p == marker or p.endswith("/" + marker):
				prefix = p[:len(p) - len(marker)].rstrip("/")
				if prefix.count("/") < MAX_DEPTH:
					out[game] = prefix
					break
	return out


def game_in(paths):
	"""(game, prefix) for the first game in paths, or (None, None)."""
	return next(iter(games_in(paths).items()), (None, None))


def iso_paths(iso):
	with open(iso, "rb") as f:
		lba, size, joliet = iso_extract.volume_root(f)
		out = []

		def walk(lba, size, prefix, depth):
			for name, elba, esz, is_dir in iso_extract.entries(f, lba, size, joliet):
				p = f"{prefix}{name}".lower()
				out.append(p)
				if is_dir and depth < 4:
					walk(elba, esz, p + "/", depth + 1)

		walk(lba, size, "", 0)
		return out


def dir_paths(folder, depth=MAX_DEPTH + 1):
	out = []
	base = Path(folder)
	for root, dirs, files in os.walk(base):
		rel = Path(root).relative_to(base)
		if len(rel.parts) >= depth:
			dirs[:] = []
		for name in files:
			out.append((rel / name).as_posix().lower())
	return out


class Source:
	"""Somewhere a game's files are: kind is drive, folder, iso, zip or zip-iso
	(an .iso inside a zip)."""

	def __init__(self, kind, path, game, prefix="", member=None):
		self.kind, self.path, self.game, self.prefix, self.member = kind, Path(path), game, prefix, member

	def __repr__(self):
		return f"Source({self.kind}, {self.path}, {self.game.id}, {self.prefix!r})"


def identify(path, around=True):
	"""The Source a file or folder holds, or None. For any other file (one
	picked in the dialog), around=True looks at its folder and the one above."""
	path = Path(path)
	try:
		if path.is_dir():
			game, prefix = game_in(dir_paths(path))
			if game:
				return Source("folder", path, game, prefix)
			# A disc image or zip right in it (a download's folder).
			for f in sorted(path.iterdir()):
				if f.is_file() and f.suffix.lower() in (".iso", ".zip"):
					found = identify(f, around=False)
					if found:
						return found
			return None
		suffix = path.suffix.lower()
		if suffix == ".iso":
			game, prefix = game_in(iso_paths(path))
			return Source("iso", path, game, prefix) if game else None
		if suffix == ".zip":
			with zipfile.ZipFile(path) as z:
				names = [n.lower().rstrip("/") for n in z.namelist()]
				game, prefix = game_in(names)
				if game:
					return Source("zip", path, game, prefix)
				isos = [n for n in z.namelist() if n.lower().endswith(".iso")]
			for member in isos[:3]:
				# An image inside: look at its contents without unpacking all of it.
				with zipfile.ZipFile(path) as z, z.open(member) as f:
					inner = _ZipIso(f)
					game, prefix = game_in(inner.paths())
				if game:
					return Source("zip-iso", path, game, prefix, member)
			return None
		if path.is_file() and around:
			# Any file on a disc or in a copy of it (or next to the image): its
			# folder, or the one above for a file in a subfolder of the disc.
			for folder in (path.parent, path.parent.parent):
				found = identify(folder, around=False)
				if found:
					return found
	except (OSError, ValueError, zipfile.BadZipFile):
		return None
	return None


class _ZipIso:
	"""Reads an ISO's directory tree from inside a zip (seekable member)."""

	def __init__(self, f):
		self.f = f

	def paths(self):
		lba, size, joliet = iso_extract.volume_root(self.f)
		out = []

		def walk(lba, size, prefix, depth):
			for name, elba, esz, is_dir in iso_extract.entries(self.f, lba, size, joliet):
				p = f"{prefix}{name}".lower()
				out.append(p)
				if is_dir and depth < 4:
					walk(elba, esz, p + "/", depth + 1)

		walk(lba, size, "", 0)
		return out


def places():
	"""Where to look, in order: drives (discs, mounted images, USB sticks),
	then the user's own folders."""
	out = []
	if sys.platform == "win32":
		import ctypes
		for letter in string.ascii_uppercase[2:]:  # not A: and B:
			root = Path(f"{letter}:\\")
			# Not network drives (4): a slow or gone one would keep the search
			# waiting; nor letters with no drive (1).
			if letter != "C" and ctypes.windll.kernel32.GetDriveTypeW(str(root)) not in (0, 1, 4) and root.exists():
				out.append((root, 0))
	else:
		for base in (Path("/media"), Path("/run/media"), Path("/mnt")):
			if base.is_dir():
				out += [(p, 1) for p in base.iterdir() if p.is_dir()]
	home = Path.home()
	for base in (home, home / "OneDrive"):  # Windows may keep Desktop and Documents in OneDrive
		for name in ("Downloads", "Hämtade filer", "Desktop", "Skrivbord", "Documents", "Dokument"):
			if (base / name).is_dir():
				out.append((base / name, MAX_DEPTH))
	return out


# Folders never worth walking into.
SKIP = {"appdata", "node_modules", "$recycle.bin", "windows", "program files", "program files (x86)"}


def sources(stop=None):
	"""Every Source in the usual places, in search order: drives first; in each
	place a copied disc's folder, then plain images, then zips (they come in
	without unpacking twice). Each place is walked once, MAX_DEPTH folders deep
	for images and zips and two more for a copied disc's marker. stop(): True
	ends the search (the player cancelled)."""
	for place, depth in places():
		if stop and stop():
			return
		paths, images = [], []
		try:
			for root, dirs, files in os.walk(place):
				if stop and stop():
					return
				rel = Path(root).relative_to(place)
				level = len(rel.parts)
				dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in SKIP] if level < depth + 2 else []
				for name in files:
					p = (rel / name).as_posix()
					paths.append(p.lower())
					if level <= depth and name.lower().endswith((".iso", ".zip")):
						images.append(Path(root) / name)
		except OSError:
			continue
		for game, prefix in games_in(paths).items():
			yield Source("drive" if depth == 0 else "folder", place, game, prefix)
		for image in sorted(images, key=lambda p: p.suffix.lower() != ".iso"):
			if stop and stop():
				return
			src = identify(image, around=False)
			if src:
				yield src


def search(game_id=None):
	"""Sources found in the usual places: {game id: Source}, the first for each
	game. game_id: stop once that game is found."""
	found = {}
	for src in sources():
		found.setdefault(src.game.id, src)
		if game_id in found:
			break
	return found


def find_all(game_id, exclude=None, stop=None):
	"""Every copy of one game in the usual places (so the player can choose,
	e.g. between versions), not those under exclude (the launcher's own
	games/ folder)."""
	out = []
	for src in sources(stop):
		if src.game.id != game_id:
			continue
		where = src.path / src.prefix if src.kind in ("drive", "folder") and src.prefix else src.path
		if exclude is not None and Path(where).resolve().is_relative_to(Path(exclude).resolve()):
			continue
		out.append(src)
	return out


def bring_in(source, dest, progress=None):
	"""Copies or unpacks the game from source into dest (games/<id>/).
	progress(fraction). Into a temporary folder first, so a stop leaves no
	half game that looks found."""
	dest = Path(dest)
	tmp = dest.with_name(dest.name + ".incoming")
	shutil.rmtree(tmp, ignore_errors=True)
	tmp.mkdir(parents=True)
	report = (lambda done, total: progress(done / total if total else 0)) if progress else None
	if source.kind in ("folder", "drive"):
		_copy_tree(source.path / source.prefix if source.prefix else source.path, tmp, report)
	elif source.kind == "iso":
		iso_extract.extract_iso(source.path, tmp, report)
		_lift(tmp, source.prefix)
	elif source.kind == "zip":
		with zipfile.ZipFile(source.path) as z:
			members = [i for i in z.infolist() if not i.is_dir()]
			total = sum(i.file_size for i in members) or 1
			done = 0
			for info in members:
				name = PurePosixPath(info.filename)
				target = tmp.joinpath(*name.parts)
				target.parent.mkdir(parents=True, exist_ok=True)
				with z.open(info) as fi, open(target, "wb") as fo:
					while chunk := fi.read(1 << 20):
						fo.write(chunk)
						done += len(chunk)
						if report:
							report(done, total)
		_lift(tmp, source.prefix)
	elif source.kind == "zip-iso":
		iso = dest.with_name(dest.name + ".iso.tmp")
		with zipfile.ZipFile(source.path) as z, z.open(source.member) as fi, open(iso, "wb") as fo:
			size, done = z.getinfo(source.member).file_size, 0
			while chunk := fi.read(1 << 20):
				fo.write(chunk)
				done += len(chunk)
				if progress:
					progress(0.5 * done / size)
		iso_extract.extract_iso(iso, tmp, (lambda d, t: progress(0.5 + 0.5 * d / t)) if progress else None)
		iso.unlink()
		_lift(tmp, source.prefix)
	install(source.game, tmp)
	# The game's own folder may already hold HD art made here: keep it.
	if (dest / "HD").exists() and not (tmp / "HD").exists():
		shutil.move(str(dest / "HD"), str(tmp / "HD"))
	shutil.rmtree(dest, ignore_errors=True)
	tmp.rename(dest)


def install(game, folder):
	"""Unpacks the files the game has only inside its installer (catalog.py
	installer) into folder, once: nothing happens when they are there, also
	one folder down as an installed copy has them (Data/Data.cst; ScummVM
	finds them there). Returns True when the game has all it needs."""
	if not game.installer:
		return True
	setup_name, names = game.installer
	folder = Path(folder)

	def have():
		if not folder.is_dir():
			return set()
		files = list(folder.iterdir())
		files += [p for d in files if d.is_dir() for p in d.iterdir()]
		return {p.name.lower() for p in files if p.is_file()}

	missing = [n for n in names if n.lower() not in have()]
	if not missing:
		return True
	setup = next((p for p in folder.iterdir() if p.name.lower() == setup_name.lower()), None)
	if setup is None:
		return False
	try:
		msi_extract.extract(setup, folder, missing)
	except (OSError, ValueError, KeyError, StopIteration):
		return False
	return all(n.lower() in have() for n in names)


def _lift(tmp, prefix):
	"""When the disc's files sit in a folder inside the source, make that the top."""
	if not prefix:
		return
	# The source's names are in their own case; find the folder whatever its case.
	path = tmp
	for part in [p for p in prefix.split("/") if p]:
		path = next((c for c in path.iterdir() if c.name.lower() == part), path / part)
	inner = path
	keep = tmp.with_name(tmp.name + ".lift")
	inner.rename(keep)
	shutil.rmtree(tmp)
	keep.rename(tmp)


def _copy_tree(src, dst, report):
	files = [p for p in Path(src).rglob("*") if p.is_file()]
	total = sum(p.stat().st_size for p in files) or 1
	done = 0
	for p in files:
		target = dst / p.relative_to(src)
		target.parent.mkdir(parents=True, exist_ok=True)
		with open(p, "rb") as fi, open(target, "wb") as fo:
			while chunk := fi.read(1 << 20):
				fo.write(chunk)
				done += len(chunk)
				if report:
					report(done, total)
