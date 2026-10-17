"""The few mask operations the HD tools need, with numpy alone (scipy's
ndimage was 45-55 MB of the players' packages for these five; user,
2026-10-14: make the launcher smaller). Same results as ndimage with its
default cross-shaped neighbourhood, nearest() included (its ties broken as
ndimage breaks them): checked on 120 of Bygger bilar's sprites, no pixel
differs (docs/launcher.md).
"""
import numpy as np


def _grow(m):
	out = m.copy()
	out[1:] |= m[:-1]
	out[:-1] |= m[1:]
	out[:, 1:] |= m[:, :-1]
	out[:, :-1] |= m[:, 1:]
	return out


def dilate(mask, iterations=1):
	"""ndimage.binary_dilation(mask, iterations=n): outside the image counts as False."""
	m = mask.astype(bool)
	for _ in range(iterations):
		m = _grow(m)
	return m


def erode(mask, iterations=1, border_value=True):
	"""ndimage.binary_erosion(mask, iterations=n, border_value=b)."""
	m = mask.astype(bool)
	for _ in range(iterations):
		p = np.pad(m, 1, constant_values=bool(border_value))
		m = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
	return m


def reachable(mask, seeds):
	"""The parts of mask connected (4-neighbours) to seeds: what
	ndimage.label(mask) plus "the labels under seeds" gives. Grows until
	nothing changes."""
	mask = mask.astype(bool)
	out = seeds.astype(bool) & mask
	while True:
		grown = _grow(out) & mask
		if (grown == out).all():
			return out
		out = grown


def from_border(mask):
	"""The parts of mask connected to the image's edge."""
	seeds = np.zeros_like(mask, dtype=bool)
	seeds[0], seeds[-1], seeds[:, 0], seeds[:, -1] = mask[0], mask[-1], mask[:, 0], mask[:, -1]
	return reachable(mask, seeds)


def nearest(feature, where, radius):
	"""(iy, ix): for each pixel in where, the nearest feature pixel (Euclidean)
	within radius; other pixels point at themselves. ndimage's
	distance_transform_edt(~feature, return_indices=True), for pixels known to
	be near a feature (the HD tools' edge band)."""
	h, w = feature.shape
	iy, ix = np.indices((h, w))
	ys, xs = np.nonzero(where & ~feature)
	if len(ys) == 0:
		return iy, ix
	r = int(radius)
	# Nearest first; between equally near ones, by dx then dy: that is the
	# pixel ndimage picks (matched on Bygger bilar's sprites: no difference).
	offs = [(dy * dy + dx * dx, dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
		if 0 < dy * dy + dx * dx <= r * r]
	offs.sort(key=lambda o: (o[0], o[2], o[1]))
	ty, tx = ys.copy(), xs.copy()
	left = np.ones(len(ys), dtype=bool)
	for _, dy, dx in offs:
		if not left.any():
			break
		cy, cx = ys + dy, xs + dx
		ok = left & (cy >= 0) & (cy < h) & (cx >= 0) & (cx < w)
		ok[ok] = feature[cy[ok], cx[ok]]
		ty[ok], tx[ok] = cy[ok], cx[ok]
		left &= ~ok
	iy[ys, xs], ix[ys, xs] = ty, tx
	return iy, ix
