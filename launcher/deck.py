"""Copying Mulle Meck to a Steam Deck over the network (the launcher's Steam
Deck button, on Windows and Linux PCs).

First a connection (Session): the Deck's address and, the first time, the
password of its "deck" user; that installs the launcher's own SSH key on the
Deck (kept in the user's settings folder, never in the package), so later
copies need no password. Then the user picks where on the Deck (browsing its
folders: home, Games, the microSD card, with the free space), and DeckCopy
sends everything from this machine: the Linux package (linux/ next to the
Windows package, or this folder when the launcher runs on Linux), the games
found here with their HD art, the pictures, and only if the Deck has none yet
the saves and settings. What is already there with the same size and time is
skipped. Last it puts Mulle Meck in Steam's library with its artwork, through
the Steam client's own API on its debugging port (steam_shortcut.py, from the
user's other projects; Decky Loader turns the port on), or SteamOS's
steamos-add-to-steam without it.

SteamOS has SSH, off until the user sets a password and starts it once
(HELP["nossh"]).
"""
import os
import posixpath
import shlex
import socket
import stat
import sys
import tarfile
import threading
from pathlib import Path

DEFAULT_HOST = "steamdeck"
USER = "deck"
INSTALL_NAME = "Mulle Meck"  # the folder made in the place the user picks
STEAM_NAME = "Mulle Meck"

# What the user sees when something fails: short, in Swedish. Lines starting
# with "$ " are commands to type (drawn in a box).
HELP = {
	"unreachable": "Hittar inte Steam Deck.\nÄr den på och i samma nätverk?",
	"nossh": "Slå på SSH på Steam Deck, en gång:\n"
		"Skrivbordsläge, öppna Konsole och skriv\n"
		"$ passwd\n"
		"(välj ett lösenord) och sedan\n"
		"$ sudo systemctl enable --now sshd",
	"auth": "Fel lösenord.",
	"password": "Skriv Steam Decks lösenord (första gången).",
	"other": "Det gick inte att kopiera.",
}

# Programs in the Linux package, executable on the Deck (the package is read
# from the Windows drive, which keeps no Unix modes).
EXECUTABLE = ("scummvm", "Mulle Meck")


# What a Steam Deck does without (user, 2026-10-14: make the launcher
# smaller): it gets the HD art from the PC, so no upscaler and no image maths
# (numpy), and it copies nothing on (no SSH client: paramiko and its crypto
# libraries). About 180 MB of the Linux package. The Deck's launcher hides the
# HD button without them (ui.can_make_hd()).
NOT_ON_DECK_LIBS = {"numpy", "scipy", "paramiko", "cryptography", "nacl", "pynacl", "bcrypt", "cffi",
	"_cffi_backend", "pycparser", "invoke"}
NOT_ON_DECK_DIRS = ("app/third_party/realesrgan-ncnn-vulkan",)
SITE_PACKAGES = "runtime/lib/python3.12/site-packages"
# The folders of the install that are the package's alone (a copy makes them
# match it); games/, cache/, saves/ and the settings are left alone.
PACKAGE_DIRS = ("runtime", "app")


def needed_on_deck(rel):
	"""False for a file (or folder) of the Linux package that a Steam Deck
	does not need; rel is relative to the package, with "/"."""
	if any(rel == d or rel.startswith(d + "/") for d in NOT_ON_DECK_DIRS):
		return False
	if rel.startswith(SITE_PACKAGES + "/"):
		name = rel[len(SITE_PACKAGES) + 1:].split("/")[0]
		return name.split("-")[0].split(".")[0].lower() not in NOT_ON_DECK_LIBS
	return True


def not_needed_on_deck(paths):
	"""The top folders and files (relative paths) among paths that a Steam
	Deck does not need: what to delete from an install made with them."""
	out = set()
	for rel in paths:
		if needed_on_deck(rel):
			continue
		top = next((d for d in NOT_ON_DECK_DIRS if rel == d or rel.startswith(d + "/")), None)
		if top is None:
			top = SITE_PACKAGES + "/" + rel[len(SITE_PACKAGES) + 1:].split("/")[0]
		out.add(top)
	return sorted(out)


def linux_package(root):
	"""The Linux package to send: root/linux (the Windows package carries it),
	or root itself when this is the Linux package."""
	root = Path(root)
	if (root / "linux" / "runtime").is_dir():
		return root / "linux"
	if sys.platform.startswith("linux") and (root / "runtime" / "bin").is_dir():
		return root
	return None


def on_steamos():
	try:
		return "steamos" in Path("/etc/os-release").read_text().lower()
	except OSError:
		return False


def settings_dir():
	"""The user's own settings folder (not the package's: that may be shared)."""
	if sys.platform == "win32":
		return Path(os.environ.get("APPDATA", Path.home())) / "MulleMeck"
	return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "mulle-meck"


class DeckError(Exception):
	"""kind: a key of HELP."""

	def __init__(self, kind, text=""):
		super().__init__(text or kind)
		self.kind = kind


class Session:
	"""A connection to the Deck."""

	def __init__(self, host, user=USER, port=22, key_file=None):
		self.host, self.user, self.port = host.strip(), user, port
		self.key_file = Path(key_file) if key_file else settings_dir() / "deck_key"
		self.client = None
		self.home = f"/home/{user}"

	def key(self, create=False):
		import paramiko
		if self.key_file.exists():
			for kind in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
				try:
					return kind.from_private_key_file(str(self.key_file))
				except paramiko.SSHException:
					continue
			return None
		if not create:
			return None
		key = paramiko.RSAKey.generate(3072)
		self.key_file.parent.mkdir(parents=True, exist_ok=True)
		key.write_private_key_file(str(self.key_file))
		return key

	def connect(self, password=""):
		"""Our key first; else the password, which then installs our key. Raises
		DeckError."""
		import paramiko
		hosts = [self.host] if "." in self.host or ":" in self.host else [self.host, self.host + ".local"]
		error = None
		for host in hosts:
			for attempt in ("key", "password"):
				pkey = self.key() if attempt == "key" else None
				if attempt == "key" and pkey is None:
					continue
				if attempt == "password" and not password:
					error = error or DeckError("password")
					continue
				client = paramiko.SSHClient()
				client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # a Deck on the home network
				try:
					client.connect(host, port=self.port, username=self.user, pkey=pkey,
						password=password if attempt == "password" else None, timeout=8, banner_timeout=8,
						auth_timeout=10, allow_agent=False, look_for_keys=False)
				except paramiko.AuthenticationException:
					error = DeckError("auth" if attempt == "password" else "password")
					continue
				except (paramiko.ssh_exception.NoValidConnectionsError, ConnectionRefusedError):
					error = DeckError("nossh")  # it answers, but nothing listens for SSH
					break
				except (socket.gaierror, socket.timeout, OSError, paramiko.SSHException) as e:
					if error is None or error.kind == "password":
						error = DeckError("unreachable", str(e))
					break
				self.client = client
				self.host = host
				if attempt == "password":
					self.install_key()
				self.home = self.run("printf %s \"$HOME\"")[1].strip() or self.home
				return
		raise error or DeckError("unreachable")

	def install_key(self):
		"""So that the next copy needs no password (as ssh-copy-id does)."""
		key = self.key(create=True)
		line = f"{key.get_name()} {key.get_base64()} mulle-meck-launcher"
		self.run("mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && "
			f"(grep -qxF {shlex.quote(line)} ~/.ssh/authorized_keys || echo {shlex.quote(line)} >> ~/.ssh/authorized_keys) && "
			"chmod 600 ~/.ssh/authorized_keys")

	def run(self, command, stdin=None, timeout=60):
		"""(exit status, stdout, stderr) of a shell command on the Deck."""
		channel = self.client.get_transport().open_session()
		channel.settimeout(timeout)
		channel.exec_command(command)
		if stdin is not None:
			channel.sendall(stdin)
		channel.shutdown_write()
		out = channel.makefile("rb").read()
		err = channel.makefile_stderr("rb").read()
		return channel.recv_exit_status(), out.decode(errors="replace"), err.decode(errors="replace")

	def places(self):
		"""Where Mulle Meck can go: [(kind, label, path, free bytes)]: the
		home folder, its Games folder, then microSD cards and USB drives."""
		home = self.home
		mounts = self.run("for d in /run/media/*/* /run/media/*; do [ -d \"$d\" ] && "
			"mountpoint -q \"$d\" && echo \"$d\"; done 2>/dev/null")[1].split("\n")
		out = [("home", "Hem", home), ("games", "Spel", posixpath.join(home, "Games"))]
		for m in sorted(set(x.strip() for x in mounts if x.strip())):
			out.append(("card", posixpath.basename(m) or m, m))
		return [(k, label, path, self.free(path)) for k, label, path in out]

	def free(self, path):
		"""Free bytes where path is (or would be), or None."""
		status, out, _ = self.run(f"p={shlex.quote(path)}; while [ ! -e \"$p\" ]; do p=$(dirname \"$p\"); done; "
			"df -B1 --output=avail \"$p\" | tail -1")
		try:
			return int(out.strip()) if status == 0 else None
		except ValueError:
			return None

	def folders(self, path):
		"""The folders in path, sorted, hidden ones left out; [] if none or missing."""
		status, out, _ = self.run(f"cd {shlex.quote(path)} 2>/dev/null && for d in */; do "
			"[ -d \"$d\" ] && echo \"${d%/}\"; done")
		return sorted((x for x in out.split("\n") if x and x != "*"), key=str.lower) if status == 0 else []

	def close(self):
		if self.client:
			self.client.close()
			self.client = None


def files_to_send(root, games):
	"""(local path, path in the install folder, only for a first install: the
	saves when the Deck has none, the settings when it has none)."""
	root = Path(root)
	out = []
	package = linux_package(root)
	skip_top = {"games", "saves", "cache", "linux", "scummvm.ini", "launcher.log", "launcher.json"}
	for p in sorted(package.rglob("*")):
		rel = p.relative_to(package)
		if p.is_file() and rel.parts[0] not in skip_top and "__pycache__" not in rel.parts and needed_on_deck(rel.as_posix()):
			out.append((p, rel.as_posix(), False))
	for g in games:
		for p in sorted(g.folder.rglob("*")):
			if p.is_file():
				out.append((p, (Path("games") / g.info.id / p.relative_to(g.folder)).as_posix(), False))
		pics = root / "cache" / g.info.id
		if pics.is_dir():
			out += [(p, (Path("cache") / g.info.id / p.name).as_posix(), False) for p in pics.glob("*.png")]
	art = root / "cache" / "steam"
	if art.is_dir():
		out += [(p, f"cache/steam/{p.name}", False) for p in art.glob("*.png")]
	# The player's saves and settings only for a first install: never over the Deck's own.
	saves = root / "saves"
	if saves.is_dir():
		out += [(p, (Path("saves") / p.relative_to(saves)).as_posix(), True) for p in sorted(saves.rglob("*")) if p.is_file()]
	if (root / "scummvm.ini").exists():
		out.append((root / "scummvm.ini", "scummvm.ini", True))
	return out


class DeckCopy:
	"""One copy through a connected Session, in a thread. state: copying,
	steam, done, failed, cancelled; progress 0..1; steam: added, updated,
	fallback or manual (how it got into Steam's library). cancel() stops it at
	once; what got there stays, and the next copy sends only the rest."""

	def __init__(self, session, root, games, dest):
		self.session, self.root, self.games, self.dest = session, Path(root), games, dest.rstrip("/")
		self.state, self.error, self.progress, self.steam = "copying", None, 0.0, None
		self.first = True
		self.cancelled = False
		self.channel = None
		threading.Thread(target=self.run, daemon=True).start()

	def run(self):
		try:
			self.copy()
			self.state = "steam"
			self.add_to_steam()
			self.state = "done"
		except Exception as e:
			if self.cancelled:
				self.state = "cancelled"
				return
			print(f"launcher: Steam Deck copy: {e}", file=sys.stderr)
			self.error, self.state = "other", "failed"

	def copy(self):
		"""What is new or changed goes in one tar stream to "tar -x" on the Deck:
		thousands of small files (Python's) cost a round trip or five each over
		SFTP. A copy cut off leaves a file of the wrong size, sent again next
		time."""
		transport = self.session.client.get_transport()
		transport.default_window_size = 1 << 27
		transport.packetizer.REKEY_BYTES = transport.packetizer.REKEY_PACKETS = 1 << 40
		sftp = self.session.client.open_sftp()
		there = remote_files(sftp, self.dest)
		sftp.close()
		self.first = "Mulle Meck" not in there
		# Saves go only to a Deck with none: a slot made on the PC must not turn
		# up among the Deck's own (user, 2026-10-14: "will it overwrite all my
		# saves if I copy it over to the deck again?").
		deck_saves = any(r.startswith("saves/") for r in there)
		files = files_to_send(self.root, self.games)
		plan = []
		for local, rel, only_if_missing in files:
			st = local.stat()
			have = there.get(rel)
			if only_if_missing and (have or (deck_saves and rel.startswith("saves/"))):
				continue
			if have and have[0] == st.st_size and abs(have[1] - int(st.st_mtime)) <= 2:
				continue
			plan.append((local, rel, st))
		total = sum(st.st_size for _, _, st in plan) or 1
		if plan:
			channel = self.channel = transport.open_session()
			channel.exec_command(f"mkdir -p {shlex.quote(self.dest)} && tar -xf - -C {shlex.quote(self.dest)}")
			out = _ChannelWriter(channel, lambda n: setattr(self, "progress", min(1.0, n / total)))
			with tarfile.open(fileobj=out, mode="w|", format=tarfile.PAX_FORMAT) as tar:
				for local, rel, st in plan:
					if self.cancelled:
						raise RuntimeError("cancelled")
					info = tarfile.TarInfo(rel)
					info.size, info.mtime = st.st_size, int(st.st_mtime)
					info.mode = 0o755 if rel in EXECUTABLE or rel.startswith("runtime/bin/") else 0o644
					info.uname = info.gname = self.session.user
					with open(local, "rb") as f:
						tar.addfile(info, f)
			channel.shutdown_write()
			status = channel.recv_exit_status()
			if status != 0:
				raise OSError(f"tar on the Deck: {status} {channel.recv_stderr(4096).decode(errors='replace')}")
		# The package's own folders mirror this build: what an earlier copy
		# left there and the package no longer has goes (libraries a Deck does
		# not need, files a newer build leaves out). Python's caches stay.
		sent = {rel for _, rel, _ in files}
		stale = [r for r in there if r.split("/")[0] in PACKAGE_DIRS and r not in sent
			and "__pycache__" not in r.split("/")]
		if stale:
			self.session.run(f"cd {shlex.quote(self.dest)} && xargs -0 rm -f -- && "
				f"find {' '.join(PACKAGE_DIRS)} -depth -type d -empty -delete 2>/dev/null; true",
				stdin="\0".join(stale).encode() + b"\0")
		self.progress = 1.0

	def add_to_steam(self):
		"""Steam's library, as the user's own deck_push script does: the Steam
		client's own API on its debugging port (Decky Loader), found by name so
		it is updated rather than added twice, with the artwork. Without the
		port: SteamOS's steamos-add-to-steam (the first time only, it cannot
		tell an entry is there). Also a menu entry for desktop mode."""
		s, q = self.session, shlex.quote
		start = posixpath.join(self.dest, "Mulle Meck")
		icon = posixpath.join(self.dest, "app", "launcher", "icon.png")
		entry = ("[Desktop Entry]\nType=Application\nName=Mulle Meck\n"
			f"Exec=\"{start}\"\nIcon={icon}\nCategories=Game;\nTerminal=false\n")
		s.run("mkdir -p ~/.local/share/applications && cat > ~/.local/share/applications/mulle-meck.desktop",
			stdin=entry.encode())
		script = Path(__file__).with_name("steam_shortcut.py").read_bytes()
		art = posixpath.join(self.dest, "cache", "steam")
		status, out, err = s.run(f"python3 - --name {q(STEAM_NAME)} --exe {q(start)} --dir {q(self.dest)} "
			f"--art {q(art)}", stdin=script, timeout=90)
		if status == 0:
			self.steam = "added" if "Added to" in out else "updated"
			return
		print(f"launcher: Steam entry via the debugging port: {err.strip()[-300:]}", file=sys.stderr)
		if self.first and s.run("command -v steamos-add-to-steam")[0] == 0:
			self.steam = "fallback" if s.run(f"steamos-add-to-steam {q(start)}")[0] == 0 else "manual"
		else:
			self.steam = "manual"

	def cancel(self):
		"""Stops the copy now (closing the stream mid-file is fine: a file cut
		short has the wrong size and goes again next time)."""
		if self.state != "copying":
			return
		self.cancelled = True
		if self.channel is not None:
			self.channel.close()


def remote_files(sftp, dest):
	"""{relative path: (size, mtime)} already in the install folder."""
	out = {}

	def walk(path, rel):
		try:
			entries = sftp.listdir_attr(path)
		except IOError:
			return
		for a in entries:
			r = posixpath.join(rel, a.filename) if rel else a.filename
			if stat.S_ISDIR(a.st_mode):
				walk(posixpath.join(path, a.filename), r)
			else:
				out[r] = (a.st_size, a.st_mtime)

	walk(dest, "")
	return out


class _ChannelWriter:
	"""A file-like writer for tarfile onto an SSH channel, counting bytes."""

	def __init__(self, channel, progress):
		self.channel, self.progress, self.sent = channel, progress, 0

	def write(self, data):
		self.channel.sendall(data)
		self.sent += len(data)
		self.progress(self.sent)
		return len(data)

	def flush(self):
		pass
