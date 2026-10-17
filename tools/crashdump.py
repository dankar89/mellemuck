"""Read a Windows crash dump of our ScummVM build: the faulting module, the
scummvm.exe functions found on the crashing thread's stack, and the strings it
points to (a failed assert's expression and file name).

	~/.venvs/mulle/bin/python tools/crashdump.py DUMP [UNSTRIPPED_EXE]

DUMP is e.g. /mnt/c/Users/<user>/AppData/Local/CrashDumps/scummvm.exe.<pid>.dmp.
UNSTRIPPED_EXE defaults to ~/src/scummvm-win/scummvm.exe; it must be the build
that crashed (the package's scummvm.exe is its stripped copy), so analyse a dump
before the next Windows build. Stack scanning is heuristic: stale values show up
too, the frames nearest the top are the most telling. See docs/tooling.md.
"""

import bisect
import os
import struct
import subprocess
import sys

from minidump.minidumpfile import MinidumpFile

IMAGE_BASE = 0x140000000


def sections(exe):
	"""{name: (rva, file offset, size)} from objdump -h."""
	out = subprocess.run(["x86_64-w64-mingw32-objdump", "-h", exe], capture_output=True, text=True).stdout
	result = {}
	for line in out.splitlines():
		parts = line.split()
		if len(parts) >= 6 and parts[1].startswith("."):
			size, vma, foff = int(parts[2], 16), int(parts[3], 16), int(parts[5], 16)
			result[parts[1]] = (vma - IMAGE_BASE, foff, size)
	return result


def symbols(exe):
	"""Sorted [(rva, name)] of the code symbols."""
	out = subprocess.run(["x86_64-w64-mingw32-nm", "-C", "--defined-only", exe], capture_output=True, text=True).stdout
	syms = []
	for line in out.splitlines():
		parts = line.split(" ", 2)
		if len(parts) == 3 and parts[1] in "tT":
			syms.append((int(parts[0], 16) - IMAGE_BASE, parts[2]))
	syms.sort()
	return syms


def string_at(pe, sec, rva):
	"""An ASCII or UTF-16 string at rva in section sec, or None."""
	srva, foff, size = sec
	if not srva <= rva < srva + size:
		return None
	raw = pe[foff + rva - srva:foff + rva - srva + 400]
	wide = raw.decode("utf-16-le", "replace").split("\0")[0]
	if len(wide) >= 6 and all(32 <= ord(c) < 127 for c in wide):
		return "W " + wide
	narrow = raw.split(b"\0")[0]
	if len(narrow) >= 6 and all(32 <= c < 127 for c in narrow):
		return narrow.decode()
	return None


def main():
	dump = sys.argv[1]
	exe = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/src/scummvm-win/scummvm.exe")
	mf = MinidumpFile.parse(dump)
	reader = mf.get_reader()
	mods = sorted((m.baseaddress, m.size, m.name.split("\\")[-1]) for m in mf.modules.modules)
	exe_base = [b for b, s, n in mods if n.lower() == "scummvm.exe"][0]
	secs = sections(exe)
	text, rdata = secs[".text"], secs[".rdata"]
	syms = symbols(exe)
	addrs = [s[0] for s in syms]
	pe = open(exe, "rb").read()

	rec = mf.exception.exception_records[0]
	print("exception", rec.ExceptionRecord.ExceptionCode, "thread", rec.ThreadId)
	for t in mf.threads.threads:
		if t.ThreadId != rec.ThreadId:
			continue
		rsp = t.ContextObject.Rsp
		data = reader.read(rsp, t.Stack.StartOfMemoryRange + t.Stack.DataSize - rsp)
		shown = 0
		for off in range(0, len(data) - 7, 8):
			v = struct.unpack("<Q", data[off:off + 8])[0]
			for base, size, name in mods:
				if not base <= v < base + size:
					continue
				rva = v - base
				if name.lower() != "scummvm.exe":
					print("%#06x %s+%#x" % (off, name, rva))
				elif text[0] <= rva < text[0] + text[2]:
					i = bisect.bisect_right(addrs, rva) - 1
					print("%#06x %s +%#x" % (off, syms[i][1][:140], rva - syms[i][0]))
				else:
					s = string_at(pe, rdata, rva)
					if s:
						print("%#06x string: %s" % (off, s))
				shown += 1
				break
			if shown >= 80:
				return


if __name__ == "__main__":
	main()
