# Mulle Meck bygger bilar (1997)

Swedish: *Bygg bilar med Mulle Meck*; English: *Building Cars with Gary Gadget*;
German: *Autos bauen mit Willy Werkel*. Levande Böcker / ELD Interaktiv, 1997.
ScummVM game id `garygadget1`.

## Our copy

- `Mulle-Meck_Bygger-Bilar_Svenska/`: a community
  release. Swedish version merged with the Danish 32-bit build so it runs on
  64-bit Windows. Includes the manual, map, website plugin parts, the source
  art extracted by SuperDOS (`Extramaterial/Källfiler`, 883 PNGs + 515 WAVs)
  and ProjectorRays-unprotected `.dir`/`.cst` files.
- Disc extracted to `~/games/mulle-bilar` (ISO9660, no Joliet needed).

## Disc layout

| Path | What |
|---|---|
| `DATA/MULLE32.EXE` | Stock Director 6.0 Windows projector (1,512,594 bytes, ScummVM tail-MD5 `a559c8b9d3bce8dd94d168d74509506d`) |
| `DATA/MULLE16.EXE` | 16-bit projector |
| `DATA/FILEIO.X32`, `FILEIO16.X16` | FileIO Xtra (saving). The installer copies it into `Xtras/`. |
| `DATA/DATA.CST` | Save-game cast, written back to disk by the game |
| `XTRAS/KEYPOLL.X32`, `PMATIC.X32` | KeyPoll (keyboard) and PrintOMatic (printing the diploma) Xtras |
| `MOVIES/*.DXR`, `*.CXT` | The game: 25 movies + shared casts |
| `SETUP.EXE` etc. | InstallShield; installs to `C:\Levande\MulleBil`; the game needs the disc mounted |

## Movies (scenes)

Names from the release README (some unverified, marked ?):

| File | Scene |
|---|---|
| `00.CXT` | Shared cast: Mulle, Buffa the dog, entering/leaving |
| `CDDATA.CXT` | Shared cast: letters, car parts, maps (1,390 members) |
| `LBSTART.DXR` | Levande Böcker intro logo |
| `UNLOAD.DXR` | Loading screen |
| `TEMPPLUG.CXT` | ? (tiny) |
| `02` | Junk pile (skrothögen) |
| `03` | Inside the garage |
| `04` | Yard |
| `05` | Driving (map) |
| `06` | Photo album of the player's cars (the camera on the tripod in the garage) |
| `08` | Print diploma |
| `10` | Intro |
| `12` | Quit |
| `13` | File dialog for exporting/importing a car (`.car`), a movie in a window over `06` |
| `18` | Credits? |
| `82` | Stuck in the mud |
| `83` | Tree in the road |
| `84` | Grunka |
| `85` | Salka |
| `86`–`92` | Mia Minardi, Gaston Garcon, Sture Stortand, Viola Vallmark, Doris Digital, Ludde Labb, Figge Ferrum |
| `93` | End of the road |
| `94` | Car show |
| `66.dxr` (website plugin) | Figge's scrapyard minigame; `Plugin.cst`, `bil1-10.cst` add parts |

Movies reference casts as libraries: 1 internal, 2 `00`, 3 `data`
(`DATA/DATA.CST`), 4 `CDdata`.

## Assets

From `tools/extract_assets.py` (output `build/bilar/`, manifest
`build/bilar/manifest.json`):

- **1,620 bitmaps** (4 more members have no pixel data), 45.5 megapixels. All
  8-bit ones use the Mac system palette.
- 82 backgrounds (54 full screens, 28 driving-map tiles of 632x396; a few
  backgrounds are 720x540, larger than the screen), ~1,500 sprites, 42 1-bit masks.
- 588 sounds, 329 scripts.
- Inks seen in the scores: copy 77 members, matte 111, background transparent
  107, both copy and matte 5. **1,320 bitmaps never appear in any score**; the
  scripts place them at runtime, so their ink depends on the channel they go
  into.
- Junkyard (`02`): channels 2–5 are copy (background layers), channels 10 and
  up are a pool of placeholder sprites with **background transparent** ink
  that the scripts fill with car parts. So car parts lose *all* pure white,
  including enclosed holes (e.g. inside the hammock frame `20b199v1`).
- Runtime-filled sprite slots are almost all **background transparent**:
  the part pools, the yard's cursor-behaviour slots, Mulle's slot and Buffa's
  slot (garage channel 7, driven by `BuffaBH`). Matte is used only for the
  cursor (`C_standard`) and a few overlay slots (channel 119 in 02/03).
- **Art convention:** pure white means see-through; white that must stay
  visible is painted off-white (Buffa's snout, eyes). So the pure white
  between Buffa's legs in frames like `00/13` is a hole. The extractor gives
  every runtime-only bitmap the background-transparent variant
  (`RUNTIME_INK` in `tools/extract_assets.py`); the user caught the dog when
  both variants were still produced.
- Member naming: `NNxMMMvV`, e.g. `20b199v1`: `NN` scene/group, `x` kind
  (`a`, `b`, `n` seen), `MMM` id, `vV` variant/view. Car parts are `20b…` in
  `CDDATA`. Not unique across casts.

## Scripts

All 329 scripts decompiled with ProjectorRays into
`research/lingo-bilar/<movie>/casts/**.ls` (readable Lingo; `.lasm` is
bytecode listing). Object-oriented: parent scripts such as `GeneralAncestor`
with `puppetSprite(index, 1)`. This is the reference for how the game behaves.

### Mouse pointer

The game hides the real cursor (`cursor(200)`, when `CustomCursorActive`
of `gMulleGlobals`, always 1) and draws its own: **sprite 115** with
`CursorSpriteBH`, moved to the mouse in `exitFrame`. Hotspots carry
`CursorBH` with `whichCustomCursor` (`#left`, `#right`, `#Grab`, `#click`,
`#Back`, `#Standard`) and swap 115's member on `mouseEnter`/`mouseLeave`
(`C_Standard` 19x32, `C_Left`, `C_Right`, `C_Click`, `C_Grab`, `C_MoveLeft`,
`C_MoveRight`, `C_MoveIn`, `C_Back`; matte ink). Driving (`05`) instead uses
real cast-member cursors over the map (`05CursorBH`, `cursor([member,
mask])`) and parks 115 on `Dummy`.

### Garage (`03`): building the car

- `spriteList` of `Dir`: `CarStart` 10 (car layers), `JunkStart` 46 (floor
  parts, `FloorPartBH`, drawn by `DrawJunkBH.drawJunk`), `drag` 100
  (`DragPartBH`), `fButton` 101, `cheatStart` 102, `Mulle` 6, `Buffa` 7.
- Grabbing (`FloorPartBH.mouseDown` or a car part) calls
  `PartsCommon.grabbedPart`: removes the part from the floor or car, builds
  the snap rects and starts `DragPartBH`. A `SafeDragScript` screen object
  (rect -1000..2000) reports the mouse up to `DragPartBH.report`, which
  blanks the drag sprite and calls `letGoOfPart` (car, door to the junk
  pile, or the floor, where the part falls to `floorLocV`).
- Snap rects (`generateSnapRects`): for each free morph of the part (wheels
  have one per axle), an 80x80 box around the centre of its use view on the
  car: `rect/2 - regPoint + carOffset + getOffset(part) + snap offset`.
  While the mouse is in one, `showUseView` draws the part on the car layers
  and the drag sprite shows `Dummy`.
- Examples with the user's chassis 1: fender 23 snaps over the rear wheel
  (mouse about 440-500, 220-280); the tyres (morphs 141/142) at four spots
  around the axles.

### Sounds and cue points

- The `Sound` parent script (shared cast `00`) plays everything through
  `puppetSound` on channels 1 (`#BG`, `#TRANS`), 2 and 3 (`#EFFECT`,
  `#OPEFFECT`). `finished` and `purge` free a channel when `soundBusy` is
  false, or for effects after `90 + the size of member * ticksPerSec /
  11025` ticks (ticksPerSec 63 on Windows), stopping the sound.
- Speech members are D6 `sndH`/`sndS` sounds, 22050 Hz 16-bit, most with
  cue points: `Talk`/`Silence` drive the talking animation
  (`SpriteAnimBH.spritecuePassed`), `toNextFrame` advances scenes (yard
  `04`, destinations 82-94, intro `10`).
- Rolling out: the garage door (`GaragePortBH`) needs wheels and a seat
  (car comfort > 0; the wicker body 127 covers the seat point `#a11`), then
  `go("garage")` plays the door scene (03 frames 40-41, waits for the
  transition sound) and `go(1, "04")`.

### Driving (`05`) and destinations

- Click the road in the yard to drive (`carClickBH`, `go("05")`). While
  `nrOfBuiltCars < 4` a show-off plays first (arrow keys on a plate, the
  car driving a demo); a click ends it. Arrow keys come from the KeyPoll
  Xtra (`bgAllKeys`, Windows virtual key codes), plus Shift/Ctrl/mouse.
- The driving maps (the "overworld") are 28 bitmaps of 632x396 in
  `CDDATA.CXT` (`30bNNNv0`, e.g. member 644 `30b016v0` for map 16), drawn
  at the top of the screen above the dashboard. They count as backgrounds
  for the HD art. Of the game's 82 backgrounds, 48 are full 640x480
  screens, 4 are 720x540 (larger than the stage), 2 odd sizes, 28 maps.
- **Driving controls (original)** (`05`: `KeyHandlers`, `KeyStuff`,
  `Dir.keyDown/keyUp`, `CarDriving`): the car has 16 headings (direction
  1-16, 16 = up, 4 = right, 8 = down, 12 = left; `directionList` holds the
  unit vectors x100) and the movie runs at 12 fps. Two modes:
  - Keys (`keySteer` 1): Left/Right (keyDown events, keyCode 123/124) set
    `Steering` -1/+1 until released; the heading turns by the car's
    `#Steering` stat per frame. Up/Shift/mouse button and Down/Ctrl/right
    button (polled with KeyPoll `bgAllKeys`, Windows codes 38/40) set
    `acceleration` +1/-1; releasing sets it to 0, which **keeps the speed**
    (cruise): Up "sets" the speed, Down brakes, then reverses.
  - Mouse (`keySteer` 0, while the left button is held): `mouseSteer`
    turns the car one step per frame towards the pointer (shortest way)
    and accelerates; top speed is 75% of key mode.
  - The car can turn on the spot at speed 0. Hits: `makeTheBestOfHit`
    slides along or stops and nudges the heading.
  - Quirk: the movie's `keyUp` handler calls `keyUp(gDir)` without the key,
    and Dir's `keyUp` then ends the steering, so releasing *any* key (also
    Up) stops a held Left/Right turn.
- **Road driving (our build, [scummvm](scummvm.md) 72, [driving](driving.md)):**
  the stick, the mouse held on the map or A drives along the roads, a
  click on a road drives there; F7 shows the road graph.
- **Driving with a gamepad (our build, [scummvm](scummvm.md) 48; with
  `road_driving=false` since 72):** left
  stick = the direction on screen the car should go (it turns there and
  waits facing a blocked edge), A or right trigger = gas (like Up), B or
  left trigger = brake/reverse (like Down), D-pad = arrow keys.
- Terrain: each map has two text members (`30tNNNv0`, `30tNNNv0-2`), each
  316 x 99 characters, together the 632x396 map at half resolution
  (cell = (pixel - 4) / 2). Byte 0 road, 16 rough ground, 240 and up
  blocked; `Wheels.quickCheck` reads the cell under and in front of the car.
  World "Da Hood" starts on map (4,3) = id 16 at (300,250).
- Leaving the map: `CarDriving` calls `checkBorders`, which returns a
  point such as `point(-1, 0)`; if the world has a map there it changes
  maps, otherwise the car steps back and stops.
- Destinations (82-94) are separate movies with markers like start,
  Prata (talk), Pause, Tillbaka, Leave. The frame script holds each marker
  with `go(the frame)`; `SpriteAnimBH` behaviours move on with `go(#next)`
  after their sound (`#sound`), animation or path (`#Path`). The shared
  `DestToEndBH` goes to `Leave` (or back to `start` in testing mode), which
  plays the engine sound and returns to `05`.
- Destination scenes also have an `ASoundBH` sprite across the whole
  scene (92: channel 15, frames 6-96) playing a looping background sound
  (`92e002v0`, `#BG`) with `WaitForSound: #GoNextFrame`; as looping sounds
  never finish, it never advances anything ([scummvm](scummvm.md) 44).
- 92 is Figge Ferrum: with the dog in the car's cache (`#Dog`) it plays
  `JustDoIt` (58) - Jajamenssan (63) - Granntack (72) - Thing (83) - Mulle
  tack (88), completes the mission, swaps `#Dog` for `#ExtraTank: 20` and
  fills the tank; without it `CantDoIt`, afterwards `Done`. The characters'
  sprites exist only on each marker's frame, so a playhead that does not
  hold makes them flash.
- **Loading screen:** every movie's frames 1-4 show sprite 118 and, in
  119, a picture of the scene the player comes from (set in the shared
  `prepareMovie` from `the WhereFrom`, e.g. `00b008v0` from driving).
  Frame 2 carries a palette instruction to the system palette at speed 0
  that must be a no-op ([scummvm](scummvm.md) 45).

### Junk pile (`02`)

- Six piles, each a pair of markers: `jN` (entry frame, 1/11/.../51) and
  `PileN` (2/12/.../52, loops back to itself in `PileBH.exitFrame`).
  The garage door does `go("j" & myLastPile, "02")`, so the movie opens at
  the last visited pile; the signposts do `go("PileN")`.
- Each pile has its own sprite spans: `PileBH` (with `whichPile`), the part
  pool (channels 12-65, `PartBH`), Mulle and Buffa. `spriteList` of `Dir`:
  `drag` 105, `JunkStart` 12, `DoorStart` 10, `fDialog` 114, `Mulle` 102,
  `Buffa` 103, `leftSign` 83, `rightSign` 82.
- **Mulle is two sprites:** body in channel 101 (matte, plain) and head in
  102 (`SpriteAnimBH` + `MulleJunkBH`, background transparent). The head's
  `SpriteAnimBH` remembers its position from `beginSprite` (`myLoc`) and sets
  it every frame. Piles 1-3 have him on the left (member 209/226), 4-6 on the
  right, mirrored (210/246).
- Picking up: `PartBH.mouseDown` -> `sendSprite(120, #grabPart)`;
  `PileBH.prepareFrame` moves the drag sprite (105, `DragPartBH`) once the
  mouse leaves a 4x4 box; `DragPartBH.mouseUp` -> `PileBH.releasePart`, which
  checks the signposts, the pile's rects and the door's `trackRect`.
- `Dir.new` (in `prepareMovie`) calls `activate(me, 1)`, which sends
  `#activate` to all sprites. In Director that reaches nobody yet; ScummVM
  handled it wrongly ([scummvm](scummvm.md) 23-24).
- The part pool and `PileBH` placeholders look the same in every pile, so
  only the span boundaries tell the piles apart ([scummvm](scummvm.md) 25).
- Signpost positions differ per pile (pile 4: left 55,365, right 460,350;
  pile 3: left 180,350, right 540,390). `tools/flows/bilar-piles.sh` clicks
  fixed spots and misses in pile 3.

### Album (`06`) and its file dialog (`13`)

- The camera on the tripod in the garage (619,73) opens the album (label
  `Save`; the label `Load` is the import mode, `WhereFrom` "07"). The way
  back is **STÄNG** (bottom right, 572,435); there is no key for it. The
  user called it "the camera scene" and got stuck in it on the Steam Deck
  (2026-10-14), in the file dialog below.
- **EXPORTERA** (the disk, 520,434) runs `Dir.openWindow`: it switches off
  every album sprite (`activateScreen(me, 0)`), lists the `.car` files
  (`FileStuff.checkFolder`, FileIO in `the carPath`), and opens the movie
  `13` in a window "Choose" of 336x278 at 132,81 (`titleVisible` 0). That
  window has the folder, a scrolling list, a name field ("MinBil"), **OK**
  (434,307 on the stage) and a round **back** button (425,341).
  `dialogueResult(gDir, #Cancel / #NewFile / #ChoseFile)` closes it
  (`closeWindow`: `tell myMIAW cleanUp()`, `close(myMIAW)`) and switches the
  album back on. The album's `Dir.kill` (on leaving) closes it too.
- In ScummVM the window was invisible (white in 8-bit, missing in HD), its
  buttons missed by 17 pixels, the second EXPORTERA crashed, and loading a
  save with the window open crashed ([scummvm](scummvm.md) 56-60). Export
  works now: the car goes to the save folder as `garygadget1-<name>.car.txt`.
- Movie `13` uses the shared cast `00`, so the shared `stopMovie`
  (`set gDir to kill(gDir)`) is also the dialog's: a stopMovie in the window
  kills the album's director object. Director evidently never sent one
  there.
- The garage's loading picture on sprite 119 (`00b020v0` when coming from
  the album) stays on sprite 119 in the album at (-160,-110) with a
  foreColor/backColor that makes ScummVM draw only its black and white
  pixels (nothing shows). HD drew it in full until [scummvm](scummvm.md) 60.

## Saving

- All progress lives as Lingo list literals (plain text) in text members of
  the `data` cast library, `DATA/DATA.CST`: `PartsDB`, `ExternalPartsDB`,
  `UsersDB` (player profiles), one `User<id>DB` per player (their car, parts,
  progress), `WorldsDB`, `mapsDB`, `ObjectsDB`, `MissionsDB`, plus custom
  racing records. A fresh disc copy has `UsersDB = []` and no user members.
- `MulleGlobals.save` (cast `00`, ParentScript 8) writes those texts back and
  calls `save(castLib "data")`, rewriting the whole cast file next to the
  game. It runs when the globals object is killed (quitting) and from the
  directors of scenes 06 (album) and 10 (intro/player selection). If the
  `User<id>DB` member is missing it alerts "Game not saved!".
- Scene 06 can export and import a single car as a `.car` text file (8.3
  name, Lingo list) through FileIO's file dialog (`ZZDataOnDiskBH`).
- `DBsToFile` (cast `00`, MovieScript 59) is a developer tool that dumps the
  parts/objects/missions/maps databases to `20t…v0.txt`-style text files.
- `tools/director.py` reads these members (text is in the member's `STXT`
  chunk, found through `KEY*`), so original saves can be imported.
- In our ScummVM build the progress goes to
  `saves/garygadget1-data.cst.casttext` (plain text, 9 backups) and is restored
  at startup. See [scummvm](scummvm.md) fixes 17-18. ScummVM save slots
  are per player (fix 53): a save holds only that player's `User<id>DB`,
  and loading puts back only that. Only `UsersDB` and the logged-in
  player's `User<id>DB` ever change (`MulleGlobals.save`); `Users.login`
  creates a new player's member from `UserNewTemplateDB` (at most 6
  players), `deleteUser` erases it.
  Autosaves happen on each new scene and on a slow timer, only when the
  texts changed (fix 52); the scenes' own state is not saved, a load always
  continues in the garage.
- Logging in as an existing player: click the name in the list (it is copied
  to the name sign), then press Enter.
- **Every scene's `Dir` lives from `prepareMovie` to `stopMovie`** (shared
  MovieScript 7 in `00`): prepareMovie creates `gDir` (`new(script "Dir")`,
  prints "A new ancestor"), stopMovie kills it. Frame scripts call
  `loop(gDir)`; if gDir is gone that call fails and the playhead runs on
  (in the garage to frame 10, whose script goes to the junk pile). So a
  restart that "goes" to the scene already playing must reload the movie
  ([scummvm](scummvm.md) 50).
- **The game sets `the exitLock`**: quitting goes through its own routine
  (which saves). ScummVM then asks "The game prevents quitting..." when
  the window is closed; our pause menu asks instead and autosaves
  ([scummvm](scummvm.md) 49).

## ScummVM status

See [scummvm](scummvm.md) for our fixes; as of 2026-10-12 the game runs to the
garage without errors. Original findings with unpatched master `c420cad105`:

- Detected as `director:garygadget1` (Windows/Swedish), support level
  *unstable*. No game-specific quirks or patches exist.
- Startup fails with `Xtra not found: fileio`: ScummVM, like Director 6, only
  auto-loads Xtras from an `Xtras/` folder. Workaround then: copy
  `DATA/FILEIO.X32` into `XTRAS/` (mimics the installer). Fixed in the
  engine since 2026-10-17 ([scummvm](scummvm.md) 122): a copy straight from
  the disc starts.
- Then the Levande Böcker logo plays correctly (dissolve transition included),
  followed by a Lingo failure: `cb_theassign: no me object` ->
  `b_sort can not handle argument of type VOID` -> `b_count` error. Many
  `Unhandled kParentScript` warnings.
- `--start-movie=MOVIES/02.DXR` jumps into a scene. `-u` with a `dumps/`
  folder dumps raw resources (not readable Lingo).
