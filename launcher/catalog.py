"""The Mulle Meck games the launcher knows about.

Each game lives in games/<id>/ next to the launcher: the files of the
player's own disc, and in HD/ the HD art made on their machine. The cover and
backdrop are bitmaps from the disc (cast file stem, member name), so the
carousel shows the player's own copy; games not found yet get a plain card.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class GameInfo:
	id: str  # folder under games/
	title: str
	icon: str  # Lucide icon on the plain card
	color: tuple  # plain card colour
	marker: str  # a file that identifies the disc, relative to its root (any case)
	cover: tuple | None  # the card's picture: (cast stem, member name)
	backdrop: tuple | None  # blurred behind the carousel
	playable: bool  # runs in our ScummVM build
	data: str = ""  # where the Director files are on the disc (MOVIES/, DATA/), if not its root
	hidden: bool = False  # not shown (nor its disc recognised) yet
	hd: bool = True  # the HD job can make its art (tools/extract_assets.py reads its disc)
	# About how long the HD job takes on a good graphics card. Measured on the
	# user's RTX 4070 laptop (2026-10-14): Bygger båtar 27 min for 74.8
	# megapixels; Bygger bilar (45.5) scaled from that.
	hd_minutes: tuple | None = None
	# Files the game needs that are only inside its installer on the disc:
	# (the installer, (file names)), unpacked once into games/<id>/ by discs.install().
	installer: tuple | None = None


# The pictures: Bygger bilar's title screen; the others have no full-screen
# title (theirs is a video or drawn in pieces), so a scene that says what the
# game is about. The Swedish discs we know (docs/game-bygger-batar.md):
# Bygg båtar is laid out like Bygger bilar (Director 6); Bygg hus has its
# Director 8.5 files in Movies/ (its program comes from the installer); in
# Upptäck rymden the game is in ToHD/; this Bygg flygplan (2000) is not a
# Director game (a 3D engine with its data packed in data.up/map.up).
ALL_GAMES = [
	GameInfo("bygger-bilar", "Bygg bilar", "car", (206, 72, 54), "DATA/MULLE32.EXE",
		("10", "10b006v0"), ("10", "10b004v0"), True, hd_minutes=(15, 30)),
	# Playable and with HD since 2026-10-14 (user: "add it to the launcher so
	# I can play it", "how can we make bygger båtar HD?"): the extractor reads
	# palette members and direct-colour bitmaps now.
	GameInfo("bygger-batar", "Bygg båtar", "sailboat", (44, 118, 186), "MULLEBAT.EXE",
		("76", "76b001v1"), ("78", "78b001v1"), True, hd_minutes=(25, 40)),
	# Hidden until we know how to remaster it (user, 2026-10-14).
	GameInfo("bygger-flygplan", "Bygg flygplan", "plane", (66, 150, 204), "data.up",
		None, None, False, hidden=True),
	# Playable since 2026-10-14 (Director 8.5; user: "lets try getting either
	# mulle meck bygger hus eller upptäck rymden working through the
	# launcher"). Its program and player database come only from Setup.exe (a
	# Wise installer with an MSI inside; docs/game-bygger-hus.md). An installed
	# copy (Program Files) has those but no Movies/ (they stay on the disc), so
	# the marker is a file only the disc has; a folder with both works too.
	# HD since 2026-10-15 (user: "do HD images for bygger hus"): the extractor
	# reads Director 8.5 casts and scores; about three times Bygger bilar's
	# pixels (800x600 art, 2400x1800 in HD).
	GameInfo("bygger-hus", "Bygg hus", "house", (64, 142, 78), "Movies/HouseData.cxt",
		("24", "24b013v0"), ("55", "55b001v0"), True, hd_minutes=(30, 50),
		installer=("Setup.exe", ("MulleHus.exe", "Data.cst"))),
	GameInfo("upptacker-rymden", "Upptäck rymden", "rocket", (104, 78, 168), "ToHD/MulleRymd.exe",
		("Graphics", "SpaceTravel_b010v0"), ("Graphics", "Station_b001v2"), False, data="ToHD"),
]

GAMES = [g for g in ALL_GAMES if not g.hidden]
