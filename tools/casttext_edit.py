"""Edit a saved cast (`<target>-<cast>.casttext`, our ScummVM's `save castLib`)
for tests, keeping each member's header length right (a wrong one makes the
file "incomplete": the game quietly loads an older backup instead).

	casttext_edit.py sub FILE OLD NEW     replace OLD by NEW in the members' text
	casttext_edit.py drop FILE NAME...    drop the named members

E.g. a player's boat without its outboard:
	casttext_edit.py sub saves/garygadget2-data.cst.casttext \
		'[731, 827, 853, 784, 984, 992]' '[731, 827, 784, 984, 992]'
Delete the file's .bak* copies too, or a mistake falls back to them unseen.
"""
import sys


def members(data):
	"""(header line, [(kind, id, name, text)]) of a .casttext file."""
	head, rest = data.split(b"\n", 1)
	out = []
	while rest:
		hdr, rest = rest.split(b"\n", 1)
		kind, mid, nlen, tlen = hdr.split(b" ")[:4]
		nlen, tlen = int(nlen), int(tlen)
		name, rest = rest[:nlen], rest[nlen + 1:]
		text, rest = rest[:tlen], rest[tlen + 1:]
		out.append((kind, mid, name, text))
	return head, out


def write(path, head, items):
	with open(path, "wb") as f:
		f.write(head + b"\n")
		for kind, mid, name, text in items:
			f.write(b"%s %s %d %d\n%s\n%s\n" % (kind, mid, len(name), len(text), name, text))


def main():
	if len(sys.argv) < 4 or sys.argv[1] not in ("sub", "drop"):
		sys.exit(__doc__)
	cmd, path = sys.argv[1], sys.argv[2]
	head, items = members(open(path, "rb").read())
	if cmd == "sub":
		if len(sys.argv) != 5:
			sys.exit(__doc__)
		old, new = sys.argv[3].encode("utf-8"), sys.argv[4].encode("utf-8")
		n = sum(old in t for _, _, _, t in items)
		items = [(k, m, nm, t.replace(old, new)) for k, m, nm, t in items]
		print(f"{n} members changed")
	else:
		names = {n.encode("utf-8") for n in sys.argv[3:]}
		kept = [it for it in items if it[2] not in names]
		print(f"{len(items) - len(kept)} members dropped")
		items = kept
	write(path, head, items)


if __name__ == "__main__":
	main()
