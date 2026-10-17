# Macromedia Director 6 file format notes

What we have verified while reading the Mulle Meck discs. All Mulle Meck PC
games found so far are Director 6.0 (`DRCF` version `0x4C7`). The reader in
`tools/director.py` implements everything below; layouts follow ScummVM's
Director engine (`~/src/scummvm/engines/director/`), which is the best
reference when something new turns up.

## Containers

- Movies are `.DXR` (protected) / `.DIR`; casts are `.CXT` (protected) / `.CST`.
  ProjectorRays turns protected files into editable `.dir`/`.cst` and
  decompiles the scripts (see [tooling](tooling.md)).
- Magic `RIFX` = big-endian (Mac-authored), `XFIR` = little-endian. Both occur
  on the same disc. Codec after the size: `MV93`/`39VM` for movies,
  `MC95`/`59CM` for casts.
- The `imap` chunk starts at offset 12; the `mmap` offset is the u32 at file
  offset 24. `mmap`: u16 header length, u16 entry length (20), i32 max,
  i32 used, then entries `fourcc, u32 length, u32 offset, u16 flags, u16, i32 next`.
  A chunk's **resource id is its index in the mmap**.
- **Endianness trap:** `mmap` and `KEY*` follow the file's endianness, but the
  payloads of `CASt`, `CAS*`, `VWSC`, `MCsL` and `DRCF` are big-endian in
  every file.

## Version

`DRCF` payload, big-endian u16 at offset 36. `0x4C7` -> Director 6.0.
Mapping (from ScummVM `humanVersion`): `>=0x4C2` 6, `>=0x4B1` 5, `>=0x45B` 4.

## Casts and members

- `CAS*`: array of big-endian u32 resource ids. Index *i* is cast member
  `minMember + i`; 0 means an empty slot.
- `CASt` (D5+): u32 type, u32 info length, u32 specific-data length, then the
  info block, then the specific data. Types: 1 bitmap, 2 film loop, 3 text,
  4 palette, 6 sound, 8 shape, 11 script, 15 transition.
- Info block: u32 offset to a string list; there, u16 (count-1), count u32
  offsets, then the strings. String 0 is script text, string 1 the **name**
  (Pascal string).
- **Member names are not unique across cast files.** Scene `02.DXR` has its own
  `00a001v0` that differs from the shared one in `00.CXT`. Always key members
  by (cast file, member number).
- `KEY*`: u16, u16, u32 max, u32 used, then 12-byte entries
  `u32 child id, u32 parent id, fourcc`. This is how a bitmap `CASt` finds its
  `BITD` pixel data.

## Bitmaps

Bitmap specific data (D6), big-endian:

| Offset | Field |
|---|---|
| 0 | u16 pitch; `0x8000` = extended record, row bytes = `pitch & 0x3FFF` |
| 2 | rect: top, left, bottom, right (i16) |
| 18 | registration point y, x (i16) |
| 23 | bit depth (8 or 1 in Mulle) |
| 24 | palette cast library (i16) |
| 26 | palette id (i16): `0` = Mac system palette; built-in id is value - 1 |

`BITD`: if its length equals `pitch * height` it is raw, otherwise run-length
coded: control byte `c`; if `c & 0x80`, repeat the next byte
`((c ^ 0xFF) & 0xFF) + 2` times, else copy the next `c + 1` bytes. 8-bit pixels
are palette indices (row stride = pitch); 1-bit pixels are bits, 1 = black.

**16 and 32 bits** (the later Mulle games, Director 8.5+: Bygg hus,
Upptäck rymden): RLE-packed `BITD` keeps each byte of a pixel in its own
plane per row: 16-bit rows are all high bytes then all low bytes (width each),
the colour RGB555; 32-bit rows are A, R, G, B planes. Unpacked (length =
width x height x bytes) the bytes are interleaved per pixel instead. Same as
ScummVM's `BITDDecoder`; `tools/director.py` `bitmap_rgb()` decodes all depths.

**The A plane is real alpha in D7+** (Bygg hus's world maps draw the car and
boat in transparent black: alpha 0 around them). `director.py`
`bitmap_alpha()`; the engine keeps it beside the opaque picture
([scummvm](scummvm.md) 112). An all-0 or all-255 plane says nothing.
Bygg hus also has five 2- and 4-bit bitmaps (black full screens).

**Palettes:** Bygger bilar has no custom palettes (`CLUT`); every 8-bit image
uses the built-in **Mac system palette** (index 0 white, 255 black). The
built-ins are in `tools/data/director-palettes.json` (taken from ScummVM's
`graphics-data.h`). Decoding with it reproduces the community-extracted PNGs
pixel for pixel. The fixed 6x6x6 cube palette is why the watercolour art is
heavily dithered.

## Cast libraries (`MCsL`)

Lists the casts a movie uses: name, the authoring path
(e.g. `C:\dok\Mulle\MvNoProt\CDdata.cst` -> file `CDDATA.CXT`), and member
range. Library 1 is the movie's internal cast.

- **The member range's start is the first member number.** A movie's
  internal cast does not always start at 1: in Bygger bilar 13, 18, 88 and
  92 it starts at 2, so the first `CAS*` entry is member 2 (92's background
  is `member 2`). External cast files (`.CXT`/`.CST`, no `MCsL`) start at 1.
  Numbering from 1 put every member of those four movies one too low
  (fixed in `extract_assets.py`, 2026-10-13).

## Score (`VWSC`, D6)

- Header: u32 length, i32 `-3`, u32 list start (12). At the list start:
  u32 entries, u32 list size, u32 max data length, then the offset table;
  entry data begins at `list start + 12 + 4 * list size`.
- Entry 0 is the frame stream: u32 size, u32 frame-1 offset (20), u32 frame
  count (**0 in these files: read frames until the stream ends**), u16 frames
  version (11), u16 sprite record size (24), u16 channel count (126), u16.
- Each frame: u16 frame size, then delta records `u16 size, u16 offset, bytes`
  patched into a running frame buffer.
- Because frames are deltas, a frame may rewrite only part of a field: in
  Bygger bilar frame 2 changes only the palette's cast library (-1 to 0),
  the member stays -1. Built-in palettes (negative member numbers, -1 the
  Mac system palette) are the same whatever cast library is named.
- Main channels: tempo at 28 (u16 cue/value at 28, u8 tempo at 30): 246
  means "value is fps" (Mulle: 12 fps), 247 a delay in seconds, 248 wait
  for a click, 254/255 wait for sound 2/1 (value = cue point). Palette at
  120 (i16 cast library, i16 member, u8 speed, u8 flags: `0x80` cycling,
  `0x60` 0 normal / `0x40` to white / `0x60` to black, `0x04` over time).
- Frame buffer: 144 bytes of main channels (script, tempo, transition, sound,
  palette), then 24 bytes per sprite channel: +0 sprite type, +1 ink
  (`& 0x3F`; `0x40` trails, `0x80` stretch), +2 fore colour, +3 back colour,
  +4 cast library (i16), +6 member (u16), +12 y, +14 x, +16 height, +18 width.
- Bitmap header: the stored rect (top, left, bottom, right) is where the
  image sat in the paint window, often its place on the stage, and the reg
  point is in the same space. Lingo's `the rect of member` is
  `rect(0, 0, w, h)` and `the regPoint` is relative to the image's corner
  (regX - left, regY - top); scripts compute positions from those
  ([scummvm](scummvm.md) 26).
- Markers (`VWLB`): u16 count, then `count` entries of (u16 frame, u16 offset
  into the text), then u32 text length and the names (Mac Roman, not
  separated: a name runs to the next offset). Bygger bilar's junk pile `02`:
  `j1`=1, `Pile1`=2, `j2`=11, `Pile2`=12 ... `j6`=51, `Pile6`=52, `End`=61.

## Score, Director 7+ (Bygg hus, D8.5)

- The frame stream header is the same 20 bytes; frames version 13, sprite
  record size **48**, channel count **1006** (six main channels and 1000
  sprite channels). The main channels take **288** bytes (6 x 48), then
  48 bytes per sprite channel. The first 8 bytes of a sprite record are as
  in D6 (type, ink, fore, back, cast library i16, member u16).
- Film loops (D7+) keep their score as an `SCVW` child of the member, read
  like the movie's; their sprites and sounds name the loop's own cast
  library as **-1**.
- Cast member info entry 20 is the member's **comments** (Lingo
  `member.comments`); Bygg hus stores each sea map's water depth grid there.
- "Text" members (the Text Asset Xtra, cast type Xtra) hold their text in an
  `XMED` child (an ASCII-hex Hermes-Paige document); scripts make them
  editable for typing (`member.editable`).

## Runtime: when behaviours exist

- `prepareMovie` runs before any behaviour is instantiated, so
  `sendSprite`/`sendAllSprites` from it reach no sprite. The first behaviours
  start (`beginSprite`) with the first frame played.
- A movie opened at a marker (`go "j4", "02"`) starts at that marker; frame 1
  is never played and its sprites never begin. Mulle relies on both: the
  junk pile's `prepareMovie` sends `#activate` to all sprites, and every
  pile is its own marker with its own sprite spans (see
  [game-bygger-bilar](game-bygger-bilar.md)).
- A behaviour instance lives for its sprite span; leaving the span (also by
  a jump) sends `endSprite`, entering a new span creates new instances and
  sends `beginSprite`. Behaviours keep state such as a remembered position
  (`SpriteAnimBH`'s `myLoc`), so an instance from the wrong span shows up as
  sprites in the wrong place.
- Consecutive spans can hold identical-looking sprites (same placeholder
  member, same spot) with different behaviours or parameters; the span
  boundaries (start/end frame in the sprite details) are what tell them
  apart, not the sprite's look.
- Several movie scripts may define the same handler (an event or a call);
  the lowest cast member wins. Bygger bilar's yard relies on it (two
  `startMovie` handlers, the second would recurse).
- `cuePassed channel, number, name`: sent when a sound passes a cue point
  (`cupt` chunk of the sound member: count, then per cue a time in ms and a
  32-byte name); channel is a symbol like `#sound1`, number counts from 1.
  Sound-channel cues go to the frame script, then the movie scripts.
- A bitmap member can be empty (0x0, e.g. Bygger bilar's `Dummy`); it draws
  nothing, also in a stretched sprite. Changing a stretched sprite's member
  keeps the sprite's size.
- Text members (`STXT`) may contain NUL bytes; Lingo strings keep them
  (`length`, `char N of`, `charToNum`). Bygger bilar stores its driving
  terrain that way.
- Input (clicks, keys) reaches scripts only between handlers, never in the
  middle of one; `the mouseDown`/`the mouseH` change at once.
- `the size of member` of a sound is its sample data (`sndS`), not the
  cast record; games use it to estimate how long a sound plays.
- `the spriteNum of me` in a behaviour is its own channel, wherever the
  handler is called from (also from another object's handler).
- `soundBusy(n)` stays TRUE for a looping sound until it is stopped; it
  does not turn FALSE after a pass. Mulle "waits for the end" of looping
  background sounds, i.e. forever ([scummvm](scummvm.md) 44).
- A palette channel "fade" to the palette already on screen is a no-op;
  Mulle's loading frames have one at speed 0 (the slowest, ~8 s if
  played) ([scummvm](scummvm.md) 45).
- Setting a sprite property from Lingo ("auto-puppet", D6) lasts until the
  end of the sprite's span; the next span starts from the score again. Only
  `puppetSprite(n, TRUE)` keeps a channel under Lingo's control across spans.

## Inks (how a sprite is drawn)

| Value | Ink | Effect on a white-backed sprite |
|---|---|---|
| 0 | copy | opaque, white is drawn |
| 8 | matte | white **connected to the bitmap border** is transparent (flood fill); enclosed white stays |
| 36 | background transparent | **every** pixel of the background colour (white) is transparent |

Others exist (1 transparent, 3 ghost, 32 blend, 37/39 lightest/darkest...) but
Bygger bilar's scores only use copy, matte and background transparent.

The game scripts never set ink. It is fixed per score channel, and the
scripts swap members into those channels at runtime (`puppetSprite`), so a
member placed by code inherits the channel's ink.

## Palettes of bitmaps (`clut_id`)

An 8-bit bitmap's specific data ends with the palette it uses: cast library
and id. Negative ids (and 0) are Director's built-in palettes
(`tools/director.py` `palette()`: 0 Mac system, -100 Windows system, ...).
A positive id is a palette **cast member** of the same cast (Bygger båtar's
`LBSTART` logo: member 98). Its colours are in the member's `CLUT` chunk
(through `KEY*`): three big-endian 16-bit words per colour (R, G, B), the
high byte the 8-bit value, usually 256 colours (`DirectorFile.member_palette()`).
16- and 32-bit bitmaps have no palette (`bitmap_rgb()`); the HD extractor
takes their colour where it compares palette indices (2026-10-14).
