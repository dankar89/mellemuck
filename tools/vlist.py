"""Reader for vList Xtra cast members (Bygg hus med Mulle Meck, Director 8.5).

The vList Xtra (GUID 823b9e92-a5d6-11d4-bf88-0050e490321a) stores a Lingo
value in a cast member: `member("worldTemplate").content`. The member's XMED
chunk is a series of blocks, each [u32 compressed length][zlib data] and
0-5 bytes of leftover memory, whose outputs (96 KB each, the last shorter)
join into one big-endian stream:

	16 bytes   the Xtra's GUID
	u32        7 (format version?)
	u32        number of symbols
	u32        1
	symbols    each [00 00 01 03][u32 length incl. NUL][name NUL]
	value      one typed value, then zero padding

Typed values (u32 type first): 0 void, 1 integer, 2 symbol (1-based index
into the table), 7 list [count, depth, values], 10 property list
[count, depth, (key value)*]; depth is the nesting level (1 = outermost).
Run: vlist.py FILE.cxt [member name]  (prints the value as Lingo).
"""
import struct
import sys
import zlib

GUID = bytes.fromhex("823b9e92a5d611d4bf880050e490321a")


def unpack_xmed(x):
	out, p = b"", 0
	while p + 6 <= len(x) and x[p + 4:p + 6] == b"\x78\x9c":
		n = struct.unpack(">I", x[p:p + 4])[0]
		out += zlib.decompress(x[p + 4:p + 4 + n])
		# 0-5 bytes of leftover memory follow; the next block's length
		# starts with 00 00 (blocks are small) and its zlib data with 78 9c.
		e = p + 4 + n
		p = next((q for q in range(e, min(e + 8, len(x) - 5)) if x[q:q + 2] == b"\0\0" and x[q + 4:q + 6] == b"\x78\x9c"), len(x))
	return out


class Reader:
	def __init__(self, d):
		self.d, self.p = d, 0

	def u32(self):
		v = struct.unpack(">I", self.d[self.p:self.p + 4])[0]
		self.p += 4
		return v

	def i32(self):
		v = struct.unpack(">i", self.d[self.p:self.p + 4])[0]
		self.p += 4
		return v


class Symbol(str):
	def __repr__(self):
		return "#" + self


def decode(d):
	if d[:16] != GUID:
		raise ValueError("not a vList stream")
	r = Reader(d)
	r.p = 16
	version, nsym, one = r.u32(), r.u32(), r.u32()
	syms = []
	for _ in range(nsym):
		tag = r.d[r.p:r.p + 4]
		if tag != b"\0\0\1\3":
			raise ValueError(f"symbol record {tag.hex()} at {r.p}")
		r.p += 4
		n = r.u32()
		syms.append(Symbol(r.d[r.p:r.p + n].rstrip(b"\0").decode("latin1")))
		r.p += n

	def value():
		t = r.u32()
		if t == 0:
			return None
		if t == 1:
			return r.i32()
		if t == 2:
			return syms[r.u32() - 1]
		if t == 7:
			n, _depth = r.u32(), r.u32()
			return [value() for _ in range(n)]
		if t == 10:
			n, _depth = r.u32(), r.u32()
			out = []
			for _ in range(n):
				k = value()
				out.append((k, value()))
			return dict(out) if len({k for k, _ in out}) == n else out
		raise ValueError(f"unknown vList type {t} at {r.p - 4}")

	v = value()
	if any(r.d[r.p:]):
		raise ValueError(f"data after the value at {r.p}")
	return v


def lingo(v):
	if v is None:
		return "VOID"
	if isinstance(v, Symbol):
		return "#" + v
	if isinstance(v, int):
		return str(v)
	if isinstance(v, dict):
		return "[" + ", ".join(f"{lingo(k)}: {lingo(x)}" for k, x in v.items()) + "]" if v else "[:]"
	return "[" + ", ".join(lingo(x) for x in v) + "]"


if __name__ == "__main__":
	sys.path.insert(0, __file__.rsplit("/", 1)[0])
	from director import DirectorFile, parse_cast_member
	f = DirectorFile(sys.argv[1])
	keys = f.keys()
	for num, res in sorted(f.cast_resources().items()):
		xmed = keys.get((res, "XMED"))
		name = parse_cast_member(f.chunk(res))["name"]
		if xmed is None or GUID not in f.chunk(res) or (len(sys.argv) > 2 and name != sys.argv[2]):
			continue
		raw = unpack_xmed(f.chunk(xmed))
		if raw[:16] != GUID:
			continue
		print(f"{num} {name}: {lingo(decode(raw))}")
