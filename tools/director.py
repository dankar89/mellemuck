"""Minimal reader for Macromedia Director 6 movie (.DXR/.DIR) and cast (.CXT/.CST) files.

Covers what the asset pipeline needs: the chunk map, cast members (names,
bitmap geometry), cast-library mapping (MCsL) and the score (VWSC) with the
ink each sprite is drawn with. Layouts follow ScummVM's Director engine.
"""
import struct
from collections import Counter, defaultdict
from pathlib import Path

INKS = {0: "copy", 1: "transparent", 2: "reverse", 3: "ghost", 4: "notCopy", 5: "notTrans",
	6: "notReverse", 7: "notGhost", 8: "matte", 9: "mask", 32: "blend", 33: "addPin", 34: "add",
	35: "subPin", 36: "backgroundTransparent", 37: "lightest", 38: "subtract", 39: "darkest"}
CAST_TYPES = {1: "bitmap", 2: "filmloop", 3: "text", 4: "palette", 5: "picture", 6: "sound",
	7: "button", 8: "shape", 9: "movie", 10: "digitalVideo", 11: "script", 12: "richText", 15: "transition"}

MAIN_CHANNELS_SIZE = 144  # D6 score: script/tempo/transition/sound/palette channels
SPRITE_CHANNEL_SIZE = 24
MAIN_CHANNELS_SIZE_D7 = 288  # Director 7+ (frames version 13)
SPRITE_CHANNEL_SIZE_D7 = 48


class DirectorFile:
	def __init__(self, path):
		self.path = Path(path)
		self.data = self.path.read_bytes()
		self.big_endian = self.data[:4] == b"RIFX"
		if self.data[:4] not in (b"RIFX", b"XFIR"):
			raise ValueError(f"{path}: not a Director file")
		e = ">" if self.big_endian else "<"
		mmap_off = struct.unpack(e + "I", self.data[24:28])[0]
		hdr = self.data[mmap_off + 8:]
		hlen, elen, _, used = struct.unpack(e + "HHii", hdr[:12])
		self.chunks = []  # index = resource id
		for k in range(used):
			ent = hdr[hlen + k * elen: hlen + (k + 1) * elen]
			tag = ent[:4] if self.big_endian else ent[:4][::-1]
			length, off = struct.unpack(e + "II", ent[4:12])
			self.chunks.append((tag.decode("latin1"), length, off))

	def chunk(self, idx):
		_, length, off = self.chunks[idx]
		return self.data[off + 8: off + 8 + length]

	def find(self, tag):
		return [i for i, c in enumerate(self.chunks) if c[0] == tag]

	def keys(self):
		"""KEY* table: {(parent resource id, tag): child resource id}, e.g. a CASt's BITD."""
		e = ">" if self.big_endian else "<"
		d = self.chunk(self.find("KEY*")[0])
		_, _, _, used = struct.unpack(e + "HHII", d[:12])
		out = {}
		for k in range(used):
			child, parent, tag = struct.unpack(e + "II4s", d[12 + 12 * k: 24 + 12 * k])
			out[(parent, (tag if self.big_endian else tag[::-1]).decode("latin1"))] = child
		return out

	def cast_resources(self, min_member=1):
		"""{member number: CASt resource id}."""
		out = {}
		for cas in self.find("CAS*"):
			ids = struct.unpack(f">{len(self.chunk(cas)) // 4}I", self.chunk(cas))
			for i, res in enumerate(ids):
				if 0 < res < len(self.chunks) and self.chunks[res][0] == "CASt":
					out[min_member + i] = res
		return out

	def bitmap_indices(self, cast_res, info, keys=None):
		"""Decode a bitmap member's BITD into a (height, width) array of palette indices
		(8-bit) or 0/1 values (1-bit, 1 = black). Returns None if it has no pixel data."""
		import numpy as np
		keys = keys if keys is not None else self.keys()
		bitd = keys.get((cast_res, "BITD"))
		if bitd is None:
			return None
		raw = self.chunk(bitd)
		w, h, bpp, pitch = info["width"], info["height"], info["bpp"], info["pitch"]
		if len(raw) != pitch * h:
			raw = unpack_rle(raw, pitch * h)
		buf = np.frombuffer(raw[:pitch * h].ljust(pitch * h, b"\0"), dtype=np.uint8).reshape(h, pitch)
		if bpp == 8:
			return buf[:, :w]
		if bpp == 1:
			return np.unpackbits(buf, axis=1)[:, :w]
		raise NotImplementedError(f"{bpp}-bit bitmaps")

	def bitmap_rgb(self, cast_res, info, keys=None):
		"""A bitmap member as an RGB array, any bit depth: 8-bit through its
		palette, 16-bit (RGB555) and 32-bit (ARGB, alpha dropped) as stored. The
		later Mulle games (Bygg hus, Upptäck rymden; Director 8.5+) use 16 and 32
		bits. RLE-packed rows keep each byte of a pixel in its own plane (16-bit:
		high bytes, then low bytes; 32-bit: A, R, G, B); unpacked ones
		interleave them, as in ScummVM's BITDDecoder. None without pixel data."""
		import numpy as np
		bpp = info["bpp"]
		if bpp in (1, 8):
			idx = self.bitmap_indices(cast_res, info, keys)
			if idx is None:
				return None
			if bpp == 1:
				return np.where(idx[..., None] == 1, 0, 255).astype(np.uint8).repeat(3, axis=2)
			clut = info.get("clut_id", 0)
			table = self.member_palette(clut, keys) if clut > 0 else palette(clut)
			return table[idx].astype(np.uint8)
		keys = keys if keys is not None else self.keys()
		bitd = keys.get((cast_res, "BITD"))
		if bitd is None or bpp not in (16, 32):
			return None
		raw = self.chunk(bitd)
		w, h = info["width"], info["height"]
		size = w * h * bpp // 8
		packed = len(raw) != size
		if packed:
			raw = unpack_rle(raw, size)
		buf = np.frombuffer(raw[:size].ljust(size, b"\0"), dtype=np.uint8)
		if bpp == 16:
			rows = buf.reshape(h, 2, w) if packed else buf.reshape(h, w, 2).transpose(0, 2, 1)
			c = rows[:, 0, :].astype(np.uint16) << 8 | rows[:, 1, :]
			rgb = np.stack([(c >> 10) & 31, (c >> 5) & 31, c & 31], axis=2).astype(np.uint16)
			return ((rgb * 255 + 15) // 31).astype(np.uint8)
		rows = buf.reshape(h, 4, w) if packed else buf.reshape(h, w, 4).transpose(0, 2, 1)
		return np.stack([rows[:, 1, :], rows[:, 2, :], rows[:, 3, :]], axis=2)

	def bitmap_alpha(self, cast_res, info, keys=None):
		"""A 32-bit bitmap's alpha plane (height, width), or None (other depths,
		no pixel data). Bygg hus draws its world maps' car and boat in alpha."""
		import numpy as np
		if info["bpp"] != 32:
			return None
		keys = keys if keys is not None else self.keys()
		bitd = keys.get((cast_res, "BITD"))
		if bitd is None:
			return None
		raw = self.chunk(bitd)
		w, h = info["width"], info["height"]
		size = w * h * 4
		packed = len(raw) != size
		if packed:
			raw = unpack_rle(raw, size)
		buf = np.frombuffer(raw[:size].ljust(size, b"\0"), dtype=np.uint8)
		rows = buf.reshape(h, 4, w) if packed else buf.reshape(h, w, 4).transpose(0, 2, 1)
		return rows[:, 0, :].copy()

	def member_palette(self, member, keys=None):
		"""RGB table (256, 3) of a palette cast member of this file (a bitmap's
		clut_id > 0, e.g. Bygger båtar's LBSTART uses member 98): its CLUT chunk,
		three big-endian 16-bit words per colour, the high byte the 8-bit value."""
		import numpy as np
		keys = keys if keys is not None else self.keys()
		try:
			first = next((lib["min"] for lib in self.cast_libs() if not lib["path"]), 1)
		except Exception:
			first = 1
		res = self.cast_resources(first).get(member)
		clut = keys.get((res, "CLUT")) if res is not None else None
		if clut is None:
			raise KeyError(f"palette member {member} not found in {self.path}")
		raw = self.chunk(clut)
		n = min(256, len(raw) // 6)
		words = np.frombuffer(raw[:n * 6], dtype=">u2").reshape(n, 3)
		table = np.zeros((256, 3), dtype=np.uint8)
		table[:n] = (words >> 8).astype(np.uint8)
		return table

	def cast_members(self, min_member=1):
		"""{member number: info dict} for the (single) cast stored in this file."""
		out = {}
		for cas in self.find("CAS*"):
			ids = struct.unpack(f">{len(self.chunk(cas)) // 4}I", self.chunk(cas))
			for i, res in enumerate(ids):
				if res == 0 or res >= len(self.chunks) or self.chunks[res][0] != "CASt":
					continue
				out[min_member + i] = parse_cast_member(self.chunk(res))
		return out

	def cast_libs(self):
		"""Cast libraries a movie uses: [{lib, name, path, min, max}] (MCsL)."""
		res = self.find("MCsL")
		if not res:
			return [{"lib": 1, "name": "Internal", "path": "", "min": 1, "max": 0}]
		d = self.chunk(res[0])
		data_off, _, count, per = struct.unpack(">IHHH", d[:10])
		ntab = struct.unpack(">H", d[data_off:data_off + 2])[0]
		offs = struct.unpack(f">{ntab}I", d[data_off + 2:data_off + 2 + 4 * ntab])
		items_len = struct.unpack(">I", d[data_off + 2 + 4 * ntab:data_off + 6 + 4 * ntab])[0]
		base = data_off + 6 + 4 * ntab

		def item(idx):
			start = offs[idx] if idx < ntab else items_len
			end = offs[idx + 1] if idx + 1 < ntab else items_len
			return d[base + start: base + end]

		def pascal(b):
			return b[1:1 + b[0]].decode("latin1") if b else ""

		libs = []
		for i in range(count):
			b = i * per
			rng = item(b + 4) if per >= 4 else b""
			mn, mx = struct.unpack(">HH", rng[:4]) if len(rng) >= 4 else (1, 0)
			libs.append({"lib": i + 1, "name": pascal(item(b + 1)), "path": pascal(item(b + 2)) if per >= 2 else "",
				"min": mn, "max": mx})
		return libs

	def score_sprites(self):
		"""Yield (frame, channel, castLib, member, ink) for every non-empty sprite in the score."""
		res = self.find("VWSC")
		if not res:
			return
		d = self.chunk(res[0])
		_, _, list_start = struct.unpack(">IiI", d[:12])
		_, list_size, _ = struct.unpack(">III", d[list_start:list_start + 12])
		index_start = list_start + 12
		frame_data = index_start + list_size * 4
		off0 = struct.unpack(">I", d[index_start:index_start + 4])[0]
		p = frame_data + off0
		stream_end = p + struct.unpack(">I", d[p:p + 4])[0]
		# The frame count field is 0 in these files; frames run to the end of the stream.
		record, num_channels = struct.unpack(">HH", d[p + 14:p + 18])
		main, rec = MAIN_CHANNELS_SIZE, SPRITE_CHANNEL_SIZE
		if record == SPRITE_CHANNEL_SIZE_D7:
			# Director 7+ (Bygg hus): 48-byte records; the count includes the
			# six main channels, which take 288 bytes.
			main, rec = MAIN_CHANNELS_SIZE_D7, SPRITE_CHANNEL_SIZE_D7
			num_channels -= MAIN_CHANNELS_SIZE_D7 // SPRITE_CHANNEL_SIZE_D7
		p += 20
		buf = bytearray(main + num_channels * rec)
		frame = 0
		while p + 2 <= stream_end:
			frame += 1
			size = struct.unpack(">H", d[p:p + 2])[0]
			if size == 0:
				break
			end = p + size
			p += 2
			while p < end:
				csize, coff = struct.unpack(">HH", d[p:p + 4])
				buf[coff:coff + csize] = d[p + 4:p + 4 + csize]
				p += 4 + csize
			for ch in range(num_channels):
				s = main + ch * rec
				ink = buf[s + 1] & 0x3F
				lib, member = struct.unpack(">hH", buf[s + 4:s + 8])
				if member:
					yield frame, ch + 1, lib, member, ink


def parse_cast_member(c):
	ctype, info_size, data_size = struct.unpack(">III", c[:12])
	info = c[12:12 + info_size]
	spec = c[12 + info_size: 12 + info_size + data_size]
	m = {"type": CAST_TYPES.get(ctype, str(ctype)), "name": info_name(info)}
	if ctype == 1 and len(spec) >= 22:
		pitch = struct.unpack(">H", spec[:2])[0]
		top, left, bottom, right = struct.unpack(">hhhh", spec[2:10])
		reg_y, reg_x = struct.unpack(">hh", spec[18:22])
		bpp = spec[23] if (pitch & 0x8000) and len(spec) > 23 else 1
		m.update(width=right - left, height=bottom - top, left=left, top=top, reg_x=reg_x, reg_y=reg_y,
			bpp=bpp, pitch=pitch & 0x3FFF)
		if (pitch & 0x8000) and len(spec) >= 28:
			m["clut_lib"], m["clut_id"] = struct.unpack(">hh", spec[24:28])
	return m


def unpack_rle(raw, size):
	"""Director BITD run-length scheme (PackBits-like, as in ScummVM's BITDDecoder)."""
	out = bytearray()
	i = 0
	while i < len(raw) and len(out) < size:
		c = raw[i]
		i += 1
		if c & 0x80:
			out += bytes([raw[i]]) * (((c ^ 0xFF) & 0xFF) + 2)
			i += 1
		else:
			out += raw[i:i + c + 1]
			i += c + 1
	return bytes(out)


_PALETTES = None


def palette(clut_id):
	"""RGB table (256, 3) for a built-in palette id as stored in bitmap members
	(0 = Mac system, -100 = Windows system, ... i.e. Director's id + 1)."""
	import json
	import numpy as np
	global _PALETTES
	if _PALETTES is None:
		_PALETTES = json.loads((Path(__file__).parent / "data" / "director-palettes.json").read_text())
	names = {0: "macPalette", -1: "rainbowPalette", -2: "grayscalePalette", -3: "pastelsPalette",
		-4: "vividPalette", -5: "ntscPalette", -6: "metallicPalette", -100: "winPalette", -101: "winD5Palette"}
	return np.array(_PALETTES[names[clut_id]], dtype=np.uint8).reshape(256, 3)


def info_name(info):
	"""Cast member name: second string of the member's info list (first is script text)."""
	if len(info) < 20:
		return ""
	data_off = struct.unpack(">I", info[:4])[0]
	if data_off + 2 > len(info):
		return ""
	count = struct.unpack(">H", info[data_off:data_off + 2])[0] + 1
	offs = struct.unpack(f">{count}I", info[data_off + 2:data_off + 2 + 4 * count])
	strings = info[data_off + 2 + 4 * count:]
	if count < 3 or offs[2] <= offs[1]:
		return ""
	s = strings[offs[1]:offs[2]]
	return s[1:1 + s[0]].decode("latin1") if s else ""


def ink_usage(movie_dir):
	"""Map (cast file stem, member number) -> Counter of inks across every movie's score.

	Member names are not unique across cast files (scene 02 has its own 00a001v0),
	so members are keyed by number within their cast file.
	"""
	movie_dir = Path(movie_dir)
	files = cast_files(movie_dir)
	usage = defaultdict(Counter)
	for stem, path in sorted(files.items()):
		if path.suffix.upper() not in (".DXR", ".DIR"):
			continue
		movie = DirectorFile(path)
		libs = {}
		for lib in movie.cast_libs():
			src = stem if not lib["path"] else lib_stem(lib["path"])
			if src in files:
				libs[lib["lib"]] = src
		for _, ch, lib, member, ink in movie.score_sprites():
			if lib in libs:
				usage[(libs[lib], member)][ink] += 1
	return usage


def cast_files(movie_dir):
	"""{STEM: path} for every movie and cast file in a directory."""
	return {p.stem.upper(): p for p in Path(movie_dir).iterdir()
		if p.suffix.upper() in (".DXR", ".DIR", ".CXT", ".CST")}


def lib_stem(path):
	"""Cast-library path as stored by the authoring machine -> file stem, e.g.
	'C:\\dok\\Mulle\\MvNoProt\\CDdata.cst' -> 'CDDATA'."""
	return Path(path.replace("\\", "/").replace(":", "/")).stem.upper()
