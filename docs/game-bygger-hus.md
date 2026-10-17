# Bygg hus med Mulle Meck (2002)

Director 8.5 (movies `v851`, file version 0x73a), 800x600, 16-bit art,
Swedish Windows disc (unpacked in
`dist/windows/MulleMeck/games/bygger-hus/`). First worked on 2026-10-14
night; ScummVM fixes 73-84 in [scummvm](scummvm.md).

## What is on the disc and what the installer adds

- The disc has `Movies/` (`00.cxt` shared cast, `00_Pic`, `00_Snd`,
  `01.dxr` ... `74.dxr`, data casts `HouseData`, `IsoData`, `BuildData`,
  `BoatData`, `Temp`), `Help/`, `QuickTime/`, `Setup.exe`, `Autoplay.exe`.
- **The program and the player database come only from the installer.**
  `Setup.exe` is a Wise for Windows Installer: its `.WISE` PE section holds
  an MSI (OLE file at offset 3,532,370 of the section). 7-Zip lists and
  extracts both (`7z x Setup.exe .WISE`, carve from the OLE magic, `7z x`
  the MSI). Out of it: `MulleHus.exe` (3,760,882 bytes, the projector
  ScummVM's Swedish detection entry wants), `Data.cst` (7,760 bytes, the
  `Data` cast: `HousePartsDB`, `ElementsDB`, `RoomsDB`, `RoofsDB`,
  `CardsDB`, `ExternalDB`, `UsersDB`), and the Xtras (`Amplitude.x32`,
  `FileIo.x32`, `vList.x32`, `PMatic.x32`, `keypoll.x323`, ...). The test
  folder `~/games/mulle-hus` = symlinks to the disc + those two files in
  the root (ScummVM finds `Data.cst` there).
- `tools/msi_extract.py` does the same without 7-Zip (the launcher uses
  it): finds the OLE file anywhere in the exe, reads it as a compound file,
  takes the stream that starts with `MSCF` (`Cabs.w1.cab`) and unpacks its
  MSZIP blocks (each a raw deflate stream with the previous 32 KB as
  dictionary). Cabinet names are the File table's keys, so some carry a
  number (`Mullehus.ico1`, `bo.jpg2`); `MulleHus.exe` and `Data.cst` do not.
- The installed layout (MSI Directory/File tables): `Program Files\Levande
  Böcker\Bygg hus med Mulle Meck\` with `MulleHus.exe`, `Mullehus.ico`,
  `MulleHus_hjalp.htm/.txt`, `Data\Data.cst`, `Help\` (the HTML help) and
  `Xtras\`. No movies: the game runs them from the CD. An old install's
  `Data\Data.cst` is the player's own players and progress.
- The projector's own movies (carved from the exe, mmap offsets are
  absolute: rebase them for ProjectorRays): `StartCD` (install check:
  registry `App Paths\MulleHus.exe`, `Data\Data.cst` on the hard disk, the
  CD by `Help\MulleHusHelp.htm`; then `LbMenuChild`), `LbMenuChild`
  (Levande Böcker's menu; Start goes to `Movies/02`). Decompiled in
  `research/lingo-hus-exe/pr/`; the disc's movies in `research/lingo-hus/`.
  ScummVM's `--dump-scripts` writes broken 1.6 GB files for these
  projector members: don't use it here.

## The game

- `02` login (name boards; Return or click Mulle). An existing player: a
  double click on the name, or a click (puts it in the entry field) and
  Return. `01` intro (a QuickTime movie, `01m001v0.mov`, plays; a click
  skips it; ends in `04`).
- `04` the building site. The first visit plays Mulle's tutorial (two
  minutes or more; clicks wait until it ends): he points a blinking yellow
  ring at each button. Left: the build book's four modes (roof, rooms,
  walls, floors; a click opens the book with that page). Bottom toolbar:
  door (in/out view), demolish, crowbar, floor up/down. The book's parts
  get their drag behaviors at runtime (`scriptInstanceList.add`); a room is
  dragged from the book onto the grid and dropped. Walls are made at
  runtime: 21x112 strips copied diagonally out of a 315x210 (`316`) wall
  texture sheet into new members of the `BuildData` cast. A new room's
  default walls (`23b002v1`) are a patchwork of old wallpapers, by design.
  Floor textures (630x209 sheets) are cut with the `TileMask` mask. Shed
  door -> `05`, album -> `11`, camera -> `12` (copies the stage).
- Globals: `gSystemObj` (users, loop objects, `pGotoMovie`/`pGoToMode`),
  `gSoundObj`, `gDirObj` (each movie's `Dir Parent`), `gCursorObj`
  (pointer sprite in `the lastChannel`, 1000).
- Players: `UsersDB` lists ids; each player is a vList member
  `User<id>DB` in the `Data` cast, created with `newMember(#vList, ...)`,
  saved with `save(castLib("data"))`. Our save: `garygadget4-Data.cst.casttext`.
- The house grid template is the vList member `worldTemplate` in `IsoData`
  (15x15 tiles per floor: floor, three object levels, four walls).
- Sounds: `sndH` + `sndS`, 16-bit mono 22,050 Hz big-endian PCM. Speech
  `NNdNNNv0` plays once, effects `NNeNNNv0` often loop.

## Status (2026-10-14 night)

Headless with `/tmp/.../scratchpad/hus.sh`-style isolation (own display
`:97`, renamed binary): login with a new name works (saved), the intro plays
through to the building site, speech plays. Not done: playing the building
site, saves through the pause menu (the shared save Lingo is Bygger bilar's
`gMulleGlobals`; hus needs `gSystemObj` versions), real lip-sync amplitude,
HD (16/32-bit art).

Launcher (2026-10-14 night): playable, no HD button; marker
`Movies/HouseData.cxt`; `MulleHus.exe` and `Data.cst` unpacked from
`Setup.exe` by the launcher ([launcher](launcher.md)). Started the way the
launcher starts it (`--path` to the game folder, `--auto-detect`), headless:
login, intro, building site. `Data.cst` in `Data/` works the same.

## Status (2026-10-15 morning)

ScummVM fixes 85-88 ([scummvm](scummvm.md)): existing players log in, the
site's build book opens, a room can be dragged onto the plot and is built
(walls drawn from the texture sheet). Test flow `tools/flows/hus-site.sh`
(new player, intro skipped, waits until the room button opens the book).
Then (89-90): the room stands as a box (flipped walls), a floor texture
dragged onto it changes its floor, the roof book opens and a roof can be
dropped (it stayed where it was dropped, above and left of the room; the
room view then showed the floors without walls: not known whether that is
how the game works, check against the original). Not tried yet: the walls
book, the toolbar tools, the shed (05), album (11), camera (12), the
minigames (21, 70), saving the house.

Saves (2026-10-15, [scummvm](scummvm.md) 91): the pause menu and autosaves
work per player; the house built on the site survives a restart and a load.

Playing on (2026-10-15, [scummvm](scummvm.md) 92-97): wall textures, the
roof (it lands on the room), the in/out view (front walls cut away), floor
up; the shed (05) and shelf 1 (06: furniture is dragged between shelves);
the camera on the site takes a photo of the house that the album (12) puts
in a frame with its red arrow. The login names are Times New Roman 18 bold
(Liberation Serif). Still to try: the album's naming (typing into a D8 text
member is not supported), the toolbox crate, the other shelves, the
minigames (21, 70), the mail and level reports.

## The scenes (2026-10-15)

| Movie | What |
|---|---|
| 02 | login; 01 intro (QuickTime) |
| 04 | building site (build book, toolbar, camera, album button) |
| 05 | the shed: shelves 1-5 (-> 06), yards, poster |
| 06 | a shelf (`pGoToMode` picks which); parts dragged between shelves |
| 07 | the yard with the car: mailbox, quay, World (-> 09), doors |
| 08 | the quay with the boat: World (-> 10) |
| 09 / 10 | driving / sailing on the world map (Keypoll arrows; 10's water depth grid is in each map member's `comments`) |
| 11 | album with the cards and camera tabs; 12 the photo album |
| 24 | a picture book (Prev/Next/Abort) |
| 50-74 | destinations; 21.cxt is the shared cast of the cranes (hook, scoop, claw), the glass globe and the lighthouse, used by 51, 53, 57, 64, 69 |

Missions are numbered; a destination offers its task only when the mission
is given (`addGivenMission(gSystemObj.pUserObj, n)`), e.g. 70's digging
game (39), 69's scoop crane (38), 64's glass globe (31). Destinations draw
the vehicle the player came in (`#Vehicle` in the player record, `#Car` or
`#boat`); 69 and 64 need the boat.

- **70, the digging game**: Buffa digs through a random maze (17x9 squares
  of 44 px) with the arrow keys (`keyPressed(123..126)` every tick) to the
  water tank, past a buried part. The dirt is 16 picture sprites that get
  white oval holes (`copyPixels` with a mask), the maze's pipe walls an
  8-bit picture made with quad `copyPixels` (rotated crossings).
- **69, the scoop crane**: the control panel's buttons are held down
  (boom up/down, in/out, scoop up/down, open/close). The boom's parts and
  the scoop's jaws turn (`rotation`); the mud is a picture with mask ink
  whose 8-bit mask the scoop bites into (`setPixel`), dropped mud lands on
  the barge's mask.
- **64**: the same crane with a hook; the glass dome breaks if the hook
  comes down on it (that is the game).
- **66** has no 00_Pic/00_Snd cast linked, and its Mulle animation asks for
  `00a001v0`: an alert "Animation Error (setAnimFirstFrame)" (likely the
  disc's own; not checked against the original).

## Status (2026-10-15 afternoon)

ScummVM 98-115 ([scummvm](scummvm.md)): the album's names can be typed and
are saved; 70's digging game plays to the end (tank found, part given,
mission 39 done); 69's crane digs mud; every scene from 05 to 74 opens
without a Lingo error (`tools/flows/hus-sweep.sh`), with the world maps'
vehicles in alpha and the film loops of 62/63. Tested headless by jumping
to scenes (`tools/flows/hus-goto.sh`, `harness.sh lingo`), not by playing
through; the mailbox (no mail yet), the toolbox items dragged into scenes,
the lighthouse (57, 51) and Viola's dig (53) were not tried.

HD (2026-10-15, [upscaling](upscaling.md)): 4,033 bitmaps, 136 million
pixels (three times Bygger bilar's), mostly 16-bit; the screen is
2400x1800. What scripts paint (the house's walls and floors, the dirt, the
photos) stays classic, scaled up.
