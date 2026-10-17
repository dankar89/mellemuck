"""Print a Director 6 movie's markers and how chosen sprite channels change
from frame to frame (member, position, size, ink).

	~/.venvs/mulle/bin/python tools/score_dump.py MOVIE.DXR [CHANNELS] [--frames A-B]

CHANNELS is a comma list of sprite channels (default: all non-empty ones in the
frame range). Example: tools/score_dump.py research/bilar-movies/05.DXR 1,20,50,115
"""

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import director as D  # noqa: E402


def frames(df):
	"""Yield (frame number, frame buffer) for every frame of the score."""
	d = df.chunk(df.find("VWSC")[0])
	_, _, list_start = struct.unpack(">IiI", d[:12])
	_, list_size, _ = struct.unpack(">III", d[list_start:list_start + 12])
	index_start = list_start + 12
	frame_data = index_start + list_size * 4
	off0 = struct.unpack(">I", d[index_start:index_start + 4])[0]
	p = frame_data + off0
	stream_end = p + struct.unpack(">I", d[p:p + 4])[0]
	num_channels = struct.unpack(">H", d[p + 16:p + 18])[0]
	p += 20
	buf = bytearray(D.MAIN_CHANNELS_SIZE + num_channels * D.SPRITE_CHANNEL_SIZE)
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
		yield frame, bytes(buf), num_channels


def markers(df):
	"""{frame: name} from the VWLB chunk (see docs/director-format.md)."""
	res = df.find("VWLB")
	if not res:
		return {}
	d = df.chunk(res[0])
	n = struct.unpack(">H", d[:2])[0]
	entries = [struct.unpack(">HH", d[2 + i * 4:6 + i * 4]) for i in range(n)]
	text_len = struct.unpack(">I", d[2 + n * 4:6 + n * 4])[0]
	text = d[6 + n * 4:6 + n * 4 + text_len]
	offsets = [e[1] for e in entries] + [text_len]
	return {entries[i][0]: text[offsets[i]:offsets[i + 1]].decode("mac_roman") for i in range(n)}


def sprite(buf, ch):
	s = D.MAIN_CHANNELS_SIZE + (ch - 1) * D.SPRITE_CHANNEL_SIZE
	rec = buf[s:s + D.SPRITE_CHANNEL_SIZE]
	lib, member = struct.unpack(">hH", rec[4:8])
	y, x, h, w = struct.unpack(">hhhh", rec[12:20])
	return (lib, member, x, y, w, h, rec[1] & 0x3F)


def main_channels(buf):
	"""The D6 main channels, 24 bytes each (see ScummVM Frame::readMainChannelsD6)."""
	script = struct.unpack(">hH", buf[0:4])
	tempo_cue, tempo = struct.unpack(">HB", buf[28:31])
	trans = struct.unpack(">hH", buf[48:52])
	pal_lib, pal_member, speed, flags = struct.unpack(">hhBB", buf[120:126])
	fade = buf[132]
	return "script %d,%d tempo %d cue %d trans %d,%d palette %d,%d speed %d flags %#x fade %#x" % (
		script[0], script[1], tempo, tempo_cue, trans[0], trans[1], pal_lib, pal_member, speed, flags, fade)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("movie")
	ap.add_argument("channels", nargs="?")
	ap.add_argument("--frames", default="1-99999")
	ap.add_argument("--main", action="store_true", help="also print the main channels (script, tempo, transition, palette) when they change")
	a = ap.parse_args()
	first, last = (int(v) for v in a.frames.split("-"))
	df = D.DirectorFile(a.movie)
	labels = markers(df)
	print("markers:", ", ".join("%d %s" % (f, n) for f, n in sorted(labels.items())))
	wanted = [int(c) for c in a.channels.split(",")] if a.channels else None
	prev = {}
	for frame, buf, num_channels in frames(df):
		if frame < first:
			continue
		if frame > last:
			break
		if frame in labels:
			print("== marker %s (frame %d)" % (labels[frame], frame))
		if a.main:
			mc = main_channels(buf)
			if prev.get("main") != mc:
				print("  frame %d main: %s" % (frame, mc))
				prev["main"] = mc
		for ch in wanted or range(1, num_channels + 1):
			cur = sprite(buf, ch)
			if prev.get(ch) != cur and (wanted or cur[1] or prev.get(ch, (0, 0))[1]):
				lib, member, x, y, w, h, ink = cur
				print("  frame %d ch %d: lib %d member %d loc %d,%d size %dx%d ink %d" % (frame, ch, lib, member, x, y, w, h, ink))
				prev[ch] = cur


if __name__ == "__main__":
	main()
