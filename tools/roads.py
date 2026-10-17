"""The road network of Bygger bilar's driving maps, from the game's own
terrain grids (user, 2026-10-14: "we would have to build a tool for finding
the roads though, and a debug view to show the roads in game to find
errors"; docs/driving.md).

  roads.py GAME_DIR OUT_DIR [--map N ...] [--scale S]

GAME_DIR is the game's folder (with MOVIES/CDDATA.CXT). OUT_DIR gets one
overlay per map (map-NNN.png: the road cells, the centre lines, the
junctions and dead ends, the exits to the next map), the whole world on one
sheet (world.png) and the graph as JSON (roads.json).

Each map's terrain is two text members, `30tNNNv0` and `30tNNNv0-2`, 316 x
99 bytes each: a 316 x 198 grid of 2 x 2 pixel cells, cell (x, y) at pixel
(4 + 2x, 4 + 2y) of the 632 x 396 map. A byte below 240 is drivable (high
nibble: 0 road, 1 holes, 2 mud; low nibble: height), 240 and up blocked.
The drivable cells are exactly the painted roads.

The centre lines: the drivable cells thinned to one cell (Zhang-Suen), then
traced into edges between nodes (junctions and ends); short spurs that the
road's ragged edges leave are pruned. The engine builds the same graph
itself from the same data (engines/director/roads.cpp); this tool is for
looking at it.
"""
import argparse
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from director import DirectorFile  # noqa: E402

W, H = 316, 198  # cells
OFFSET = 4  # pixels: cell (x, y) is at pixel (OFFSET + 2x, OFFSET + 2y)
BLOCKED = 240
# Spurs shorter than this (cells) are road edges, not roads.
SPUR = 14
# Loops shorter than this (cells) go round a speck in the road; edges
# shorter than JOIN join their two nodes.
LOOP = 30
JOIN = 7
# Path points are averaged with up to this many cells either side (the ends
# stay on their nodes), as the engine does.
SMOOTH = 4
# Ends this close to the map's edge (cells) lead to the next map. The game
# changes maps when the car's front is 3 cells from the edge (Wheels.checkBorders).
EXIT_MARGIN = 6


class Game:
	"""CDDATA.CXT's text members and bitmaps by name."""

	def __init__(self, game_dir):
		path = next(p for p in Path(game_dir).rglob("*") if p.name.upper() == "CDDATA.CXT")
		self.file = DirectorFile(path)
		self.keys = self.file.keys()
		self.res = self.file.cast_resources()
		self.members = self.file.cast_members()
		self.by_name = {m["name"]: n for n, m in self.members.items()}

	def text(self, name):
		d = self.file.chunk(self.keys[(self.res[self.by_name[name]], "STXT")])
		off, length = struct.unpack(">II", d[:8])
		return d[off:off + length]

	def terrain(self, map_id):
		data = self.text(f"30t{map_id:03d}v0") + self.text(f"30t{map_id:03d}v0-2")
		return np.frombuffer(data, dtype=np.uint8).reshape(H, W)

	def world(self, name="Da Hood"):
		"""The world's grid of map ids, rows top to bottom (worldNameDB)."""
		text = self.text(f"world{name}DB").decode("latin1")
		start = text.index("#map:") + len("#map:")
		depth, end = 0, start
		for i in range(start, len(text)):
			depth += {"[": 1, "]": -1}.get(text[i], 0)
			if depth == 0 and text[i] == "]":
				end = i + 1
				break
		return json.loads(text[start:end])

	def map_image(self, map_id):
		"""The map's bitmap as RGB."""
		n = self.by_name[f"30b{map_id:03d}v0"]
		return Image.fromarray(self.file.bitmap_rgb(self.res[n], self.members[n], self.keys), "RGB")


def zhang_suen(mask):
	"""Thins a mask to one-cell lines (Zhang & Suen 1984)."""
	m = mask.astype(np.uint8).copy()
	while True:
		changed = False
		for step in (0, 1):
			p = np.pad(m, 1)
			n = [p[:-2, 1:-1], p[:-2, 2:], p[1:-1, 2:], p[2:, 2:], p[2:, 1:-1], p[2:, :-2], p[1:-1, :-2], p[:-2, :-2]]
			b = sum(x.astype(np.int32) for x in n)
			a = sum(((n[i] == 0) & (n[(i + 1) % 8] == 1)).astype(np.int32) for i in range(8))
			p2, p4, p6, p8 = n[0], n[2], n[4], n[6]
			if step == 0:
				c = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
			else:
				c = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
			kill = (m == 1) & (b >= 2) & (b <= 6) & (a == 1) & c
			if kill.any():
				m[kill] = 0
				changed = True
		if not changed:
			return m.astype(bool)


NEIGHBOURS = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]  # (dy, dx) clockwise from north


def ring(sk, y, x):
	return [bool(sk[y + dy, x + dx]) if 0 <= y + dy < sk.shape[0] and 0 <= x + dx < sk.shape[1] else False
		for dy, dx in NEIGHBOURS]


def arcs(r):
	"""Number of runs of set neighbours around a cell."""
	if all(r):
		return 1
	return sum(1 for i in range(8) if r[i] and not r[i - 1])


def tidy(sk):
	"""Removes cells the lines do not need: a cell whose neighbours form one
	run of three or more (a corner of a staircase or a 2 x 2 block)."""
	sk = sk.copy()
	again = True
	while again:
		again = False
		for y, x in zip(*np.nonzero(sk)):
			r = ring(sk, y, x)
			if sum(r) >= 3 and arcs(r) == 1:
				# Only if the neighbours stay connected without it.
				sk[y, x] = False
				again = True
	return sk


class Graph:
	"""Nodes (cell positions) and edges (cell paths between two nodes)."""

	def __init__(self):
		self.nodes = []  # [x, y]
		self.edges = []  # {"a": node, "b": node, "path": [[x, y], ...]} (path from a to b, both ends included)

	def degree(self, n):
		return sum((e["a"] == n) + (e["b"] == n) for e in self.edges)

	def to_json(self):
		return {"nodes": self.nodes, "edges": self.edges}


def trace(sk):
	"""The skeleton as a graph. Nodes: cells with one neighbour run (ends) or
	three or more (junctions; junction cells next to each other are one node).
	Without the node cells the skeleton falls apart into pieces of line; each
	piece is the edge between the nodes it touches, its path the shortest way
	through it from one to the other."""
	h, w = sk.shape

	def around(c):
		y, x = c
		for dy, dx in NEIGHBOURS:
			if 0 <= y + dy < h and 0 <= x + dx < w and sk[y + dy, x + dx]:
				yield (y + dy, x + dx)

	kind = {}
	for y, x in zip(*np.nonzero(sk)):
		a = arcs(ring(sk, y, x))
		if a != 2:
			kind[(y, x)] = a
	g = Graph()
	node_of = {}
	for cell in kind:
		if cell in node_of:
			continue
		group, todo = [cell], [cell]
		node_of[cell] = len(g.nodes)
		while todo:
			c0 = todo.pop()
			for c in around(c0):
				if c in kind and c not in node_of and kind[c] >= 3 and kind[cell] >= 3:
					node_of[c] = len(g.nodes)
					group.append(c)
					todo.append(c)
		g.nodes.append([sum(c[1] for c in group) / len(group), sum(c[0] for c in group) / len(group)])

	# Each node also owns the line cells around it: without them two pieces
	# of line still meet diagonally beside a junction.
	owner = dict(node_of)
	for c0, n in node_of.items():
		for c in around(c0):
			owner.setdefault(c, n)
	# Nodes whose cells touch are joined directly (a junction traced as a few
	# nodes close together; prune() makes them one).
	direct = set()
	for c0, n in owner.items():
		for c in around(c0):
			m = owner.get(c)
			if m is not None and m != n:
				direct.add((min(n, m), max(n, m), min(c0, c)))
	direct = {(a, b): c for a, b, c in sorted(direct, reverse=True)}
	direct = [(a, b, c) for (a, b), c in direct.items()]

	def centre(n):
		return cell_of(g.nodes[n])

	for a, b, c in sorted(direct):
		g.edges.append({"a": a, "b": b, "path": [centre(a), [int(c[1]), int(c[0])], centre(b)]})

	seen = set()
	for start in zip(*np.nonzero(sk)):
		if start in owner or start in seen:
			continue
		# One piece of line, and the nodes it touches (by their cells).
		piece, todo, touch = {start}, [start], {}
		seen.add(start)
		while todo:
			c0 = todo.pop()
			for c in around(c0):
				if c in owner:
					touch.setdefault(owner[c], set()).add(c0)
				elif c not in seen:
					seen.add(c)
					piece.add(c)
					todo.append(c)
		nodes = sorted(touch)
		if not nodes:
			# A ring with no junction: one node on it.
			cell = min(piece)
			g.nodes.append([float(cell[1]), float(cell[0])])
			n = len(g.nodes) - 1
			ring_path = [cell]
			prev = {cell: None}
			# Walk round it.
			cur = cell
			while True:
				nxt = next((c for c in around(cur) if c in piece and c not in prev), None)
				if nxt is None:
					break
				prev[nxt] = cur
				ring_path.append(nxt)
				cur = nxt
			g.edges.append({"a": n, "b": n, "path": [[int(c[1]), int(c[0])] for c in ring_path + [cell]]})
			continue
		if len(nodes) > 2:
			print(f"warning: a piece of line touches {len(nodes)} nodes near cell {int(start[1])},{int(start[0])}", file=sys.stderr)

		def shortest(a_cells, b_cells, same):
			"""The way through the piece from a cell next to one node to a cell
			next to the other (for a loop: back to the same node, the long way)."""
			prev = {c: None for c in sorted(a_cells)}
			queue = sorted(a_cells)
			for c in queue:
				if c in b_cells and (not same or prev[c] is not None and len(queue) > 2):
					path = [c]
					while prev[path[-1]] is not None:
						path.append(prev[path[-1]])
					return path[::-1]
				for n in around(c):
					if n in piece and n not in prev and not (same and n in a_cells and c in a_cells):
						prev[n] = c
						queue.append(n)
			return None

		if len(nodes) == 1:
			n = nodes[0]
			ends = sorted(touch[n])
			if len(ends) >= 2:
				path = shortest({ends[0]}, set(ends[1:]), False)
				if path:
					g.edges.append({"a": n, "b": n, "path": [centre(n)] + [[int(c[1]), int(c[0])] for c in path] + [centre(n)]})
			continue
		for i in range(len(nodes)):
			for k in range(i + 1, len(nodes)):
				a, b = nodes[i], nodes[k]
				path = shortest(touch[a], touch[b], False)
				if path:
					g.edges.append({"a": a, "b": b, "path": [centre(a)] + [[int(c[1]), int(c[0])] for c in path] + [centre(b)]})
	return g


def cell_of(p):
	"""The cell a node is in (rounded as the engine does: half up)."""
	return [int(math.floor(p[0] + 0.5)), int(math.floor(p[1] + 0.5))]


def smooth(path, k=SMOOTH):
	"""The path's stair steps averaged out (the engine's smoothing)."""
	n = len(path)
	out = []
	for i in range(n):
		r = min(k, i, n - 1 - i)
		pts = path[i - r:i + r + 1]
		out.append([sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)])
	return out


def path_length(path):
	return sum(((path[i][0] - path[i - 1][0]) ** 2 + (path[i][1] - path[i - 1][1]) ** 2) ** 0.5 for i in range(1, len(path)))


def at_edge(p, margin=EXIT_MARGIN):
	x, y = p
	return x < margin or y < margin or x >= W - margin or y >= H - margin


def prune(g, spur=SPUR):
	"""Drops short dead ends (not those at the map's edge), small loops and
	edges of a few cells (one junction traced as two), and joins the edges of
	nodes left with two."""
	while True:
		changed = False
		for i, e in enumerate(g.edges):
			length = path_length(e["path"])
			if e["a"] == e["b"] and length < LOOP:
				g.edges.pop(i)
				changed = True
				break
			if e["a"] != e["b"] and length < JOIN:
				# One node where the two were; its edges start there.
				keep, gone = e["a"], e["b"]
				g.edges.pop(i)
				ka, kb = g.nodes[keep], g.nodes[gone]
				g.nodes[keep] = [(ka[0] + kb[0]) / 2, (ka[1] + kb[1]) / 2]
				at = cell_of(g.nodes[keep])
				for f in g.edges:
					if f["a"] == gone:
						f["a"] = keep
						f["path"] = [at] + f["path"]
					if f["b"] == gone:
						f["b"] = keep
						f["path"] = f["path"] + [at]
				changed = True
				break
		if changed:
			continue
		for i, e in enumerate(g.edges):
			for end, other in (("a", "b"), ("b", "a")):
				n = e[end]
				if g.degree(n) == 1 and g.degree(e[other]) >= 3 and path_length(e["path"]) < spur \
						and not at_edge(g.nodes[n]):
					g.edges.pop(i)
					changed = True
					break
			if changed:
				break
		if changed:
			continue
		# Merge through nodes with exactly two edges.
		for n in range(len(g.nodes)):
			es = [e for e in g.edges if e["a"] == n or e["b"] == n]
			if len(es) == 2 and es[0]["a"] != es[0]["b"] and es[1]["a"] != es[1]["b"]:
				e1, e2 = es
				p1 = e1["path"] if e1["b"] == n else e1["path"][::-1]
				a = e1["a"] if e1["b"] == n else e1["b"]
				p2 = e2["path"] if e2["a"] == n else e2["path"][::-1]
				b = e2["b"] if e2["a"] == n else e2["a"]
				g.edges.remove(e1)
				g.edges.remove(e2)
				g.edges.append({"a": a, "b": b, "path": p1 + p2[1:]})
				changed = True
				break
		if not changed:
			break
	# Renumber the nodes still used.
	used = sorted({e["a"] for e in g.edges} | {e["b"] for e in g.edges})
	new = {n: i for i, n in enumerate(used)}
	g.nodes = [g.nodes[n] for n in used]
	for e in g.edges:
		e["a"], e["b"] = new[e["a"]], new[e["b"]]
	return g


def road_graph(terrain):
	"""The centre-line graph of one map's terrain grid."""
	mask = terrain < BLOCKED
	# Roads that leave the map go on: the edge cells are repeated outwards so
	# their centre lines run to the edge instead of turning away from it.
	pad = 12
	big = np.pad(mask, pad, mode="edge")
	sk = zhang_suen(big)[pad:-pad, pad:-pad]
	sk = tidy(sk)
	g = trace(sk)
	return prune(g)


def draw(img, terrain, g, scale):
	"""The map with its road cells tinted, the centre lines, nodes (red
	junctions, yellow ends, blue exits)."""
	big = img.resize((img.width * scale, img.height * scale), Image.NEAREST).convert("RGBA")
	tint = np.zeros((H, W, 4), dtype=np.uint8)
	kind = terrain // 16
	drivable = terrain < BLOCKED
	tint[drivable & (kind == 0)] = (255, 60, 40, 70)
	tint[drivable & (kind == 1)] = (255, 170, 0, 110)
	tint[drivable & (kind == 2)] = (170, 40, 255, 110)
	t = Image.fromarray(tint, "RGBA").resize((W * 2 * scale, H * 2 * scale), Image.NEAREST)
	layer = Image.new("RGBA", big.size)
	layer.paste(t, (OFFSET * scale, OFFSET * scale))
	big = Image.alpha_composite(big, layer)
	d = ImageDraw.Draw(big)

	def px(p):
		return ((OFFSET + 2 * p[0] + 1) * scale, (OFFSET + 2 * p[1] + 1) * scale)

	for e in g.edges:
		d.line([px(p) for p in smooth(e["path"])], fill=(255, 255, 255, 255), width=max(2, scale))
	for i, n in enumerate(g.nodes):
		deg = g.degree(i)
		col = (40, 120, 255) if at_edge(n) and deg == 1 else (255, 220, 0) if deg == 1 else (230, 0, 0)
		r = 3 * scale
		x, y = px(n)
		d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=(0, 0, 0))
	return big


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("game", type=Path)
	ap.add_argument("out", type=Path)
	ap.add_argument("--map", type=int, nargs="*")
	ap.add_argument("--scale", type=int, default=2)
	args = ap.parse_args()
	game = Game(args.game)
	world = game.world()
	ids = sorted({m for row in world for m in row})
	if args.map:
		ids = [m for m in ids if m in args.map]
	args.out.mkdir(parents=True, exist_ok=True)
	graphs, images = {}, {}
	for m in ids:
		terrain = game.terrain(m)
		g = road_graph(terrain)
		graphs[m] = g
		images[m] = draw(game.map_image(m), terrain, g, args.scale)
		images[m].convert("RGB").save(args.out / f"map-{m:03d}.png")
		ends = sum(1 for i in range(len(g.nodes)) if g.degree(i) == 1)
		print(f"map {m}: {len(g.nodes)} nodes, {len(g.edges)} edges, {ends} ends")
	(args.out / "roads.json").write_text(json.dumps({str(m): g.to_json() for m, g in graphs.items()}))
	if not args.map:
		w, h = images[ids[0]].size
		sheet = Image.new("RGB", (w * len(world[0]) // 2, h * len(world) // 2))
		for r, row in enumerate(world):
			for c, m in enumerate(row):
				sheet.paste(images[m].convert("RGB").resize((w // 2, h // 2), Image.LANCZOS), (c * w // 2, r * h // 2))
		sheet.save(args.out / "world.png")


if __name__ == "__main__":
	main()
