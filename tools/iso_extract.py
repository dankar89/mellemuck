"""Extract an ISO 9660 disc image, with its Joliet long names when it has them.

  iso_extract.py IMAGE.iso OUT_DIR

The Mulle Meck discs from 2000 on carry Joliet names (Start_Mulle.exe,
mixed case); the plain ISO 9660 tree only has 8.3 upper-case ones
(START_MU.EXE), which ScummVM's detection does not recognise. No Rock Ridge
or HFS needed. extract_iso() is also used by the launcher.
"""
import os
import struct
import sys

SECTOR = 2048


def volume_root(f):
	"""(lba, size, joliet) of the root directory: the Joliet tree if any."""
	plain = None
	for lba in range(16, 64):
		f.seek(lba * SECTOR)
		d = f.read(SECTOR)
		if d[1:6] != b"CD001":
			break
		root = d[156:190]
		where = (struct.unpack("<I", root[2:6])[0], struct.unpack("<I", root[10:14])[0])
		if d[0] == 2 and d[88:90] == b"%/" and d[90:91] in (b"@", b"C", b"E"):
			return where + (True,)
		if d[0] == 1 and plain is None:
			plain = where + (False,)
		if d[0] == 255:
			break
	if plain is None:
		raise ValueError("not an ISO 9660 image")
	return plain


def entries(f, lba, size, joliet):
	"""(name, lba, size, is_dir) in a directory."""
	f.seek(lba * SECTOR)
	data = f.read(size)
	i = 0
	while i < len(data):
		n = data[i]
		if n == 0:  # records do not cross sectors: go to the next one
			i = (i // SECTOR + 1) * SECTOR
			continue
		r = data[i:i + n]
		i += n
		raw = r[33:33 + r[32]]
		if raw in (b"\x00", b"\x01"):
			continue
		name = raw.decode("utf-16-be" if joliet else "latin1", errors="replace")
		name = name.split(";")[0].rstrip(".")
		if "/" in name or "\\" in name or name in ("", ".", ".."):
			raise ValueError(f"bad name {name!r}")
		yield name, struct.unpack("<I", r[2:6])[0], struct.unpack("<I", r[10:14])[0], bool(r[25] & 2)


def extract_iso(iso, out, progress=None):
	"""Every file of the image into out. progress(done_bytes, total_bytes) is
	called as it goes."""
	with open(iso, "rb") as f:
		lba, size, joliet = volume_root(f)
		files = []

		def walk(lba, size, dst):
			for name, elba, esz, is_dir in entries(f, lba, size, joliet):
				if is_dir:
					walk(elba, esz, os.path.join(dst, name))
				else:
					files.append((os.path.join(dst, name), elba, esz))

		walk(lba, size, out)
		total = sum(s for _, _, s in files) or 1
		done = 0
		for path, elba, esz in files:
			os.makedirs(os.path.dirname(path), exist_ok=True)
			f.seek(elba * SECTOR)
			left = esz
			with open(path, "wb") as o:
				while left:
					chunk = f.read(min(left, 1 << 20))
					if not chunk:
						break
					o.write(chunk)
					left -= len(chunk)
					done += len(chunk)
					if progress:
						progress(done, total)
	return len(files)


if __name__ == "__main__":
	n = extract_iso(sys.argv[1], sys.argv[2])
	print(f"{n} files -> {sys.argv[2]}")
