"""Check which Lingo builtins, commands and `the` properties a game's scripts
use against what our ScummVM implements, to find gaps before playing into them.

	~/.venvs/mulle/bin/python tools/lingo_audit.py [LINGO_DIR] [SCUMMVM_DIRECTOR_DIR]

LINGO_DIR is the decompiled scripts (default research/lingo-bilar, *.ls from
ProjectorRays); SCUMMVM_DIRECTOR_DIR is engines/director of our ScummVM source
(default ~/src/scummvm/engines/director).

Reports, most used first:
  MISSING  called like a function or command, but neither a game handler nor
           a ScummVM builtin (or Xtra/XLib function)
  STUB     a ScummVM builtin whose implementation is (partly) a stub
  XTRA-STUB a function only an Xtra/XLib provides, stubbed there
  LIST-ONLY a builtin that refuses points and rects (lists in Lingo):
           listp, duplicate and getPos did, and each broke the game
  the-STUB a `the` entity whose get or set is a stub in ScummVM
Static only: it cannot see argument types (e.g. duplicate() of a point) or
wrong behaviour, so run the game too. See docs/tooling.md.
"""

import collections
import glob
import os
import re
import sys

LINGO_KEYWORDS = {
	"if", "then", "else", "end", "repeat", "while", "with", "in", "to", "down", "case", "of", "otherwise",
	"set", "put", "into", "after", "before", "global", "property", "on", "return", "exit", "next", "me",
	"and", "or", "not", "the", "field", "char", "word", "line", "item", "sprite", "member", "castLib",
	"cast", "window", "menu", "menuItem", "tell", "TRUE", "FALSE", "EMPTY", "VOID", "RETURN", "SPACE",
	"QUOTE", "TAB", "BACKSPACE", "ENTER", "PI", "contains", "starts", "mod", "new", "nothing", "go",
	"play", "done", "loop", "previous", "movie", "frame", "marker", "point", "rect", "list", "script",
	"xtra", "sound", "number", "string", "integer", "float", "symbol", "value", "pass", "halt", "abort",
}


def scummvm_tables(src):
	"""(builtins {name: [function names]}, stubbed functions, the entities, entity stubs, fields)."""
	builtins = collections.defaultdict(list)	# name -> [(function, source file)]
	files = [os.path.join(src, "lingo/lingo-builtins.cpp"), os.path.join(src, "lingo/lingo-funcs.cpp")]
	files += glob.glob(os.path.join(src, "lingo/xtras/**/*.cpp"), recursive=True)
	files += glob.glob(os.path.join(src, "lingo/xlibs/**/*.cpp"), recursive=True)
	entry = re.compile(r'\{\s*"([^"]+)",\s*([A-Za-z_:]+)\s*,')
	stubbed = set()
	list_only = set()	# builtins that refuse points and rects (Lingo treats them as lists)
	for path in files:
		text = open(path, errors="replace").read()
		for name, func in entry.findall(text):
			builtins[name.lower()].append((func.split("::")[-1], os.path.relpath(path, src)))
		# Function bodies that report a stub, and stub macros.
		for m in re.finditer(r"void\s+(?:\w+::)?(\w+)\(int nargs\)\s*\{(.*?)\n\}", text, re.S):
			if "STUB" in m.group(2):
				stubbed.add(m.group(1))
			body = m.group(2)
			if re.search(r"TYPECHECK2\(\w+, ARRAY, PARRAY\)|type == ARRAY \|\| \w+\.type == PARRAY\)", body) and "POINT" not in body:
				list_only.add(m.group(1))
		for m in re.finditer(r"XOBJSTUB(?:NV)?\((?:\w+::)?(\w+)", text):
			stubbed.add(m.group(1))
	the = open(os.path.join(src, "lingo/lingo-the.cpp"), errors="replace").read()
	entities = {n.lower(): k for k, n in re.findall(r'\{\s*(kThe\w+),\s*"([^"]+)"', the.split("TheEntityField fields")[0])}
	entity_stubs = set(re.findall(r"(?:get|set)TheEntitySTUB\((kThe\w+)\)", the))
	fields = {n.lower() for n in re.findall(r'\{\s*kThe\w+,\s*"([^"]+)",\s*kThe\w+', the)}
	return builtins, stubbed, entities, entity_stubs, fields, list_only


def scan_scripts(lingo_dir):
	"""Handlers the game defines, and the names it calls / `the` names it uses, with where."""
	handlers = set()
	calls = collections.defaultdict(collections.Counter)
	thes = collections.defaultdict(collections.Counter)
	call_re = re.compile(r'(?<![\w#".])([A-Za-z_]\w*)\s*\(')
	cmd_re = re.compile(r'^\s*([A-Za-z_]\w*)(?:\s+(?![=(])|$)')
	the_re = re.compile(r'\bthe\s+([A-Za-z_]\w*)(\s+(?:of|char|word|item|line)\b)?', re.I)
	for path in glob.glob(os.path.join(lingo_dir, "**/*.ls"), recursive=True):
		where = os.path.relpath(path, lingo_dir)
		for line in open(path, errors="replace"):
			code = line.split("--")[0]
			m = re.match(r'\s*on\s+(\w+)', code)
			if m:
				handlers.add(m.group(1).lower())
				continue
			stripped = re.sub(r'"[^"]*"', '""', code)
			for name in call_re.findall(stripped):
				calls[name.lower()][where] += 1
			m = cmd_re.match(stripped)
			if m and m.group(1).lower() not in LINGO_KEYWORDS:
				calls[m.group(1).lower()][where] += 1
			for name, of in the_re.findall(stripped):
				thes[(name.lower(), bool(of))][where] += 1
	return handlers, calls, thes


def show(rows, title):
	print("\n== %s (%d)" % (title, len(rows)))
	for name, uses, note in sorted(rows, key=lambda r: -sum(r[1].values())):
		total = sum(uses.values())
		top = ", ".join("%s (%d)" % (os.path.dirname(w).split("/")[0] + "/" + os.path.basename(w)[:40], c)
			for w, c in uses.most_common(2))
		print("  %-24s %4d uses  %s  %s" % (name, total, note, top))


def main():
	lingo_dir = sys.argv[1] if len(sys.argv) > 1 else "research/lingo-bilar"
	src = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/src/scummvm/engines/director")
	builtins, stubbed, entities, entity_stubs, fields, list_only = scummvm_tables(src)
	handlers, calls, thes = scan_scripts(lingo_dir)

	missing, stubs, xtra_stubs, lists = [], [], [], []
	for name, uses in calls.items():
		if name in handlers or name in LINGO_KEYWORDS:
			continue
		if name not in builtins:
			missing.append((name, uses, ""))
			continue
		core = [(f, path) for f, path in builtins[name] if "/xtras/" not in path and "/xlibs/" not in path]
		if any(f in list_only for f, path in core):
			lists.append((name, uses, "(" + ", ".join(sorted({f for f, p in core if f in list_only})) + ")"))
		if core:
			# A builtin of the language: only its own implementation counts.
			if any(f in stubbed for f, path in core):
				stubs.append((name, uses, "(" + ", ".join(sorted({f for f, p in core})) + ")"))
		else:
			bad = sorted({"%s in %s" % (f, os.path.basename(path)) for f, path in builtins[name] if f in stubbed})
			if bad:
				xtra_stubs.append((name, uses, "(" + "; ".join(bad) + ")"))

	the_missing, the_stubs = [], []
	for (name, of), uses in thes.items():
		if of:
			# `the x of obj` is mostly the game's own objects' properties, and
			# `the last char` a chunk expression: not checked.
			continue
		if name not in entities and name not in fields:
			the_missing.append((name, uses, ""))
		elif entities.get(name) in entity_stubs:
			the_stubs.append((name, uses, "(" + entities[name] + ")"))

	print("Lingo audit of %s against %s" % (lingo_dir, src))
	print("%d game handlers, %d called names, %d `the` names" % (len(handlers), len(calls), len(thes)))
	show(missing, "MISSING: called, but neither a game handler nor a ScummVM builtin")
	show(stubs, "STUB: ScummVM builtin is (partly) a stub")
	show(xtra_stubs, "XTRA-STUB: only an Xtra/XLib provides it, and that method is a stub")
	show(lists, "LIST-ONLY: ScummVM refuses points/rects here; check the game never passes one")
	show(the_stubs, "the-STUB: `the` entity stubbed in ScummVM")
	show(the_missing, "the-MISSING: `the` name ScummVM does not know")


if __name__ == "__main__":
	main()
