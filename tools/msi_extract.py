"""Unpacks files from an MSI installer, also one inside a Wise setup.exe.

Bygg hus med Mulle Meck has its program (MulleHus.exe) and its player
database (Data.cst) only inside Setup.exe: a Wise for Windows Installer whose
.WISE section holds an MSI. An MSI is an OLE compound file; its files are in
a cabinet (MSCF) stored as one of its streams, compressed with MSZIP. Only
the standard library is used, so the launcher's embedded Python can run it.

	msi_extract.py Setup.exe OUTDIR [NAME ...]
"""
import struct
import sys
import zlib
from pathlib import Path

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
FREE, END = 0xFFFFFFFF, 0xFFFFFFFE


def find_ole(data):
	"""The compound file in data: an .msi itself, or the one carried in a
	Wise setup.exe (anywhere in it)."""
	at = data.find(OLE_MAGIC)
	if at < 0:
		raise ValueError("no MSI (OLE compound file) found")
	return data[at:]


def ole_streams(ole):
	"""{name: bytes} of every stream in a compound file. Names are as stored
	(MSI encodes its table names; cabinets are found by content)."""
	sector_shift, mini_shift = struct.unpack_from("<HH", ole, 0x1E)
	ssize, msize = 1 << sector_shift, 1 << mini_shift
	(n_fat, dir_start, _, mini_cutoff, minifat_start, n_minifat,
		difat_start, n_difat) = struct.unpack_from("<IIIIIIII", ole, 0x2C)

	def sector(i):
		off = (i + 1) * ssize
		return ole[off:off + ssize]

	difat = list(struct.unpack_from("<109I", ole, 0x4C))
	i = difat_start
	for _ in range(n_difat):
		if i in (FREE, END):
			break
		s = sector(i)
		difat += struct.unpack_from(f"<{ssize // 4 - 1}I", s)
		i = struct.unpack_from("<I", s, ssize - 4)[0]
	fat = []
	for i in difat[:n_fat]:
		fat += struct.unpack(f"<{ssize // 4}I", sector(i))

	def chain(start, table):
		out, i, seen = [], start, set()
		while i not in (FREE, END) and i < len(table) and i not in seen:
			seen.add(i)
			out.append(i)
			i = table[i]
		return out

	def read(start, size):
		return b"".join(sector(i) for i in chain(start, fat))[:size]

	dir_data = read(dir_start, 1 << 62)
	entries = []
	for off in range(0, len(dir_data) - 127, 128):
		name_len, kind = struct.unpack_from("<HB", dir_data, off + 0x40)
		name = dir_data[off:off + max(name_len - 2, 0)].decode("utf-16-le", "replace")
		start, size = struct.unpack_from("<II", dir_data, off + 0x74)
		entries.append((name, kind, start, size))
	root = next(e for e in entries if e[1] == 5)
	ministream = read(root[2], root[3])
	minifat = []
	for i in chain(minifat_start, fat)[:n_minifat]:
		minifat += struct.unpack(f"<{ssize // 4}I", sector(i))

	streams = {}
	for name, kind, start, size in entries:
		if kind != 2:
			continue
		if size < mini_cutoff:
			streams[name] = b"".join(ministream[i * msize:(i + 1) * msize] for i in chain(start, minifat))[:size]
		else:
			streams[name] = read(start, size)
	return streams


def cab_files(cab):
	"""{name: bytes} of a cabinet's files (MSZIP or stored folders)."""
	if cab[:4] != b"MSCF":
		raise ValueError("not a cabinet")
	(cb_cab, off_files, n_folders, n_files, flags) = (
		struct.unpack_from("<I", cab, 8)[0], struct.unpack_from("<I", cab, 16)[0],
		*struct.unpack_from("<HHH", cab, 26))
	pos = 36
	cb_header_res = cb_folder_res = cb_data_res = 0
	if flags & 4:  # reserve fields present
		cb_header_res, cb_folder_res, cb_data_res = struct.unpack_from("<HBB", cab, pos)
		pos += 4 + cb_header_res
	if flags & 1:  # previous cabinet named: skip the two strings
		for _ in range(2):
			pos = cab.index(b"\0", pos) + 1
	if flags & 2:
		for _ in range(2):
			pos = cab.index(b"\0", pos) + 1
	folders = []
	for _ in range(n_folders):
		data_off, n_data, comp = struct.unpack_from("<IHH", cab, pos)
		folders.append((data_off, n_data, comp))
		pos += 8 + cb_folder_res

	unpacked = []
	for data_off, n_data, comp in folders:
		kind, out, p, window = comp & 0xF, bytearray(), data_off, b""
		for _ in range(n_data):
			_, cb_data, cb_uncomp = struct.unpack_from("<IHH", cab, p)
			p += 8 + cb_data_res
			block = cab[p:p + cb_data]
			p += cb_data
			if kind == 0:
				out += block
			elif kind == 1:
				if block[:2] != b"CK":
					raise ValueError("bad MSZIP block")
				# Each block is its own deflate stream that may refer back to
				# the previous block's last 32 KB.
				d = zlib.decompressobj(-15, zdict=window) if window else zlib.decompressobj(-15)
				chunk = d.decompress(block[2:]) + d.flush()
				out += chunk
				window = bytes(out[-32768:])
			else:
				raise ValueError(f"cabinet compression {kind} (only MSZIP is read)")
		unpacked.append(bytes(out))

	files, pos = {}, off_files
	for _ in range(n_files):
		size, off, folder, _, _, attribs = struct.unpack_from("<IIHHHH", cab, pos)
		end = cab.index(b"\0", pos + 16)
		name = cab[pos + 16:end].decode("utf-8" if attribs & 0x80 else "cp1252")
		pos = end + 1
		if folder < len(unpacked):
			files[name] = unpacked[folder][off:off + size]
	return files


def installer_files(path):
	"""{name: bytes} of every file in the installer's cabinets."""
	streams = ole_streams(find_ole(Path(path).read_bytes()))
	out = {}
	for data in streams.values():
		if data[:4] == b"MSCF":
			out.update(cab_files(data))
	return out


def extract(path, outdir, names=None):
	"""Writes the installer's files (or only names, matched without case) to
	outdir; returns the paths written."""
	files = installer_files(path)
	want = {n.lower() for n in names} if names else None
	outdir = Path(outdir)
	outdir.mkdir(parents=True, exist_ok=True)
	written = []
	for name, data in files.items():
		if want is not None and name.lower() not in want:
			continue
		target = outdir / name
		tmp = target.with_name(target.name + ".tmp")
		tmp.write_bytes(data)
		tmp.replace(target)
		written.append(target)
	return written


if __name__ == "__main__":
	if len(sys.argv) < 3:
		sys.exit(__doc__)
	for p in extract(sys.argv[1], sys.argv[2], sys.argv[3:] or None):
		print(p, p.stat().st_size)
