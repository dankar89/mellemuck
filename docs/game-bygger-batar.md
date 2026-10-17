# Mulle Meck bygger båtar

Swedish: *Bygg båtar med Mulle Meck*; German: *Schiffe bauen mit Willy*.
ScummVM game id `garygadget2`. Work started 2026-10-14 (user: "try our hands
at adding bygger båtar?"): it starts, logs a player in, reaches the boatyard,
saves and loads. Status below.

## Our copy

- The disc image `MULLEBAT (Windows).iso`, extracted (256 MB).
- Director 6.0 (`0x4C7`), like Bygger bilar.

## Status in our ScummVM (2026-10-14)

- **Detection**: the Swedish Windows disc (`Mullebat.exe`, 1,515,691 bytes,
  tail-MD5 `5e0c81ac9c9f8d9617a59ccdd29936a2`, Director 6.0) added to
  `detection_tables.h`.
- **Start**: the projector's first movie is Levande Böcker's start menu
  `LBProfil` (Start, help, web links, register, quit). It checks for an
  installation on the hard disk (`LBFamily.ini`, `Data/Data.cst` copied) and
  says "'Bygg båtar med Mulle Meck' är inte installerat. Installationsprogrammet
  kommer att startas." Its Start button goes to `Movies/10` (`Stringtable1` in
  `LBprofil.cxt`: `setaProp App1, #Dir, "movies" & delim & "10"`). The quirk
  `quirkMulleMeckBatar` makes `Movies/10.dxr` the first movie (unless
  `--start-movie` says otherwise); the logo movie `LBstart` is skipped with it
  (it needs `gSystem` from the start menu).
- **Login** (`11`): needed [scummvm](scummvm.md) 64: the shared cast's
  `KeyHandlers` movie script has `on keyDown systemKeys()` (F11 help, Alt+Q)
  without `pass`, and ScummVM let it keep every key, so the name field took
  no typing. Return logs in ("Entered a new name") and goes to the boatyard.
- **Objects run every frame**: the shared `LoopHandler` sets `#loopMe` on
  each object it runs (`setProp`); `Weather` does not declare it ([scummvm](scummvm.md) 65).
- **Saves**: players are numbered: `UsersDB` is `[1, 2, ...]`, each player's
  record is `User<id>DB` in `data` with the name as `#userName`
  (`Users.login(name)`). The quirk's save support uses the id as the player
  (`string(the userId of the user of gMulleGlobals)`), and loading logs in by
  the name read from `User<id>DB`, then goes to `01`. The sound object stops
  with `stopAll` (Bygger bilar: `stopAllEffects`). Autosaves, saving and loading
  through the pause menu: tested (`tools/flows/batar-login.sh`, then the menu).
- **Pointer**: sprite 115 (`CursorHandler`, `cursor(200)`), as in Bygger
  bilar. Dragged parts: `#DragPart` 90 in `02`, 100 in `03`, 98 in `04`.
- **Launcher**: playable since 2026-10-14 (the user: "add it to the launcher
  so I can play it"), with the HD button since later that night (the user:
  "how can we make bygger båtar HD?"). The extraction needed palette cast
  members (`LBSTART`'s 71 bitmaps use member 98) and a 32-bit bitmap
  (`tools/director.py`, `tools/extract_assets.py`). It finds 5,225 bitmaps:
  5,222 to upscale, 74.8 megapixels, 3,510 under 64 px (mostly the 2,800
  boat frames in `BLS`...`SAIL`, the boat at sea from every angle). Bygger
  bilar is 1,578 images, 45.5 MP, 30-45 min on the user's RTX 4070 laptop,
  so expect about 50-75 min. Tested: 12 images through the HD job (9 s on
  the GPU), the engine loads them ("HD art: 12 images") in HD. The full run
  is the user's (the HD button; ask before running it here).
- **The user's first play** (Steam Deck, 2026-10-14): picked a hull and
  rudder on the blueprint, went to the quay, the yard and the shelves; the
  shelf arrow broke the scene (fix 67), a load then left nothing clickable,
  and the progress file was saved with empty databases, so the next start
  would have failed (fix 68). Both fixed and replayed: blueprint (small
  hull, small rudder) -> boatyard -> cradle -> quay (the hull in the water)
  -> the shed on the right -> yard (cabinets 1-6) -> cabinet 1 -> shelves 1,
  2, 3, 2 -> load -> the blueprint clicks again.
- The way around: boatyard `01` -> the cradle (once a hull is chosen) ->
  quay `04` -> the right edge (625,245) -> yard `03` -> a cabinet -> its
  shelf in `02`; the sign at the top left (124,40) has the up/down arrows.
- The scenes' hotspots are polled by the game's `MouseHandler` once per
  frame: the harness's 2 ms click is missed; tests use `harness.sh drag X Y
  X Y+1` (a slow click), as a player's click is ~100 ms.
- Tried: the boatyard (`01`), the blueprint (`15`, from the drawing on the
  table, back with the corner button), the toolbox (Skrota båten, Titta på
  diplom, Avsluta spelet). Not yet: getting parts, building, the quay, the
  sea (the reviews' trouble spot), destinations, sound (the harness has none).
- **Going to sea** (2026-10-14, the user's boat: hull, mushroom cabin,
  outboard motor): from the boatyard the cradle (523,324) takes it to the
  quay (`04`); the mooring rope on the bollard (482,357) casts off and loads
  the sea, `05` (a map with the shore, a dashboard: compass, speed, fuel,
  the drive selector, the fish). `05`'s `BoatBase.init` used `setaProp`'s
  value, which stopped ScummVM ([scummvm](scummvm.md) 74). Starting `05` on
  its own runs a test mode (`b_alert(CheatBoat!)`): test the sea from a
  real save instead (log in, pause menu Ladda, the autosave).
- Sailing ([scummvm](scummvm.md) 76, [driving](driving.md) "The boat"):
  `05` keeps the boat in Dir's `boat` (BoatBase: `direction` 1-16 as the
  car's, `internalDirection` in hundredths, not wrapped, `loc` x100,
  `speed`); its kind in `boat.ancestor.type` (#Motor, #Sail, #Oar), the
  motor's throttle in `ancestor.motorSpeed` (-20..100). Keys: KeyPoll (arrow
  keys, polled each frame; needs "KeyPoll" in `availableXtras`), else only
  the keyDown handler (Left/Right; "-", ".", "<", "z" for speed). Up/Down:
  the motor's throttle, the oars' strokes, the sail's sheet; Shift/Ctrl too.
  The boat's pictures: `Boat0000` + (direction mod 16) + 80 * side tilt + 16
  * front/back tilt (DisplayBoat), the sail `Segel0000` the same way by its
  own angle (Sail), channels 42 and 43.
- The sea's world (`CDdata.cxt`, `#WorldId: "Da Hood"`): 10 x 11 maps
  (ids 1-110, a few 0), the start map point(2, 6) (id 52) at
  point(520, 190) heading 4; west of it only (1, 6). Crossing an edge:
  `BoatBase.checkBorders` (the depth checker's topology 316 x 198 at half
  scale, 4 cells of border) puts the boat 12 px inside the other side and
  calls `Dir.changeMap`; where no map is, Mulle says `05d051v0` and the
  boat is held 10 px from the edge. The harbour by the start takes the boat
  back to the quay (`04`) when it sails into it.
- **Where things are at sea** (`CDdata.cxt`: `mapNDB` lists a map's
  objects as `[objectId, loc, optional]`, `objectNDB` says what an object
  is; map id N is grid point ((N-1) mod 10 + 1, (N-1) div 10 + 1)).
  Destinations (`#dest`, movie in `#DirResource`; Mulle says `#Sounds[1]`
  in the outer radius, the movie starts in the inner one when he is done):
  77 map (1,6) (423,100), 76 (3,7) (253,89), 79 (5,6) (210,173), 88 (8,5)
  (285,170), 78 (3,4) (169,195), 80 (1,3) (342,284), 85 (3,1) (552,305), 86
  (9,2) (319,176) (only with a compass on board), 81 (3,8) (562,164), 84
  (1,10) (204,189), 83 (7,10) (144,263), 87 (10,10) (286,54). Random ones
  (`#rdest`, placed per trip by `World.randomizeDestinations` from
  `RandomDestinationsListDa Hood`): 70 on map 35 or 66, 71 on 44 or 77, the
  pickups (Bible, swim ring, doctor's bag; `#custom "Pickup"`) on 24, 32,
  43, 51, 53, 62, 75, 93. Others: the race (`"Racing"`, map 42), petrol
  stations (`"Gas"`, 66 and 84), the bridges (42: 62, 72, 91), river mouths,
  the maelstrom, `"NoMotor"` zones (maps 86, 87, 96, 97, 106, 107). The harbour by
  the start is object 3 (`#dest` to `04`) on map 52.
  `tools/flows/batar-dests.sh` puts the boat at each destination in turn.
- **Tested 2026-10-16** (our build, HD, the user's motor boat, by
  `batar-dests.sh`): 77, 76 (the boat show), 79, 88, 78, 80, 85, 81, 84,
  87, 70, 71 each play and give the boat back at sea beside the
  destination. `#NotGivenMissions` + `#NoDisplay` hides 70 until mission
  15 is given, 71 until 14; the first trip of a player gives one
  of the two at random (`Dir.loadWorld`), so one of them is missing. The
  broken-boat, capsize and hunger endings go home to the quay after
  Mulle's line (`batar-events.sh`; out of fuel: see 2026-10-17). Not
  reached, by the game's rules: 86 (shown only with a compass on board),
  83 (inside a `"NoMotor"` zone, object 40 with a 350 px radius at the
  edges of maps 86-107: a motor boat is put back where it entered and
  Mulle says so; sail or row there). Mulle gets hungry after ~4 minutes
  at sea (the fish plate on the dashboard) and, without a fishing rod,
  goes home to the quay: also the game's rule.
- **West from the start is land** (2026-10-16, the user: "still having
  trouble moving left with the gamepad"; the Deck log and the virtual pad):
  the boat starts at (520,190) east of the boatyard's peninsula, with the
  harbour (object 3, back to the quay) just north-west of it and the
  peninsula's tip down to about y 320. Straight west goes into the harbour
  (home) or onto the land (the crashes wear the boat out: towed home).
  Map (1,6) and the rest of the west are reached round the tip: south
  first, then west (virtual pad: south 8 s, then west: (3,7), (2,7), (1,7)).
  The stick steering itself works (heading 12 and full throttle when held
  west). While the player waits, the wind carries the boat east (into map
  (3,6) within ~15 s on the user's save). A mouse click at sea (the Deck's
  trackpad or R2 in Steam's layout) switches the boat to mouse steering
  (`Dir.mouse`: `steerMethod` #mouse, steers toward the pointer, throttle
  while the button is down) until a steering key arrives.
- **Tested 2026-10-17** (our build, HD, a test player's boat and save copies with
  its parts changed; virtual pad):
  * Sail: the dashboard's buttons switch motor and sail (sprites 65-67, one
    per possible power; `changeType`). The stick sails S, E, N at speed
    150-160; into the wind (W with the wind blowing east) the speed is 2
    and the boat drifts back: `Sail.getForce` gives nothing within two
    headings of the wind (game physics). A click on a button also switches
    to mouse steering: the boat then heads for the pointer, here upwind,
    and sits still until the wind carries it on (looked like a bug; it is
    not).
  * A sail-only boat (outboard 853 taken out of the save) is shown on the
    map with its sail and only the sail button; the reviews' "not shown at
    all" does not happen here.
  * Oars: one stroke per press of Up (`OarBoatAncestor`), the mouse rows on
    while held. The pad rowed once and stopped: fixed ([scummvm](scummvm.md)
    118), it rows on, also against the wind.
  * Out of fuel (`BoatBase.OutOfFuel`): a boat with another power switches
    to it (the test boat to the sail) and sails on; only a motor-only boat is towed
    home. 2026-10-16's "fuel: home" for the test boat was the harbour (the
    flow held Up from the start); `batar-events.sh` now calls `OutOfFuel`.
  * Fishing (hunger with `#Fishingrod` in the inventory): Mulle's line
    (`05d045v0` the first time, then `05d120v0`), a picture, sailing on;
    twice in a row.
  * Petrol station (map 66, object 47 `"Gas"`): only for a boat that uses
    fuel; the inner radius stops the boat, plays `31e001v0`, fills the tank
    (500 -> 22500) and gives the boat back.
  * The race (map 42, (2,5), object 2 `"Racing"`; shown once mission 16 is
    given or done): enter the goal (425,75) from the east (`#EnterDir` 12,
    within 3 headings), leave it west (a lap), enter from the east again:
    the time (3:90 with placing) goes on the board with the name, under
    15 s gives medal 2 (`#Medals`). The board's fields were never drawn
    ([scummvm](scummvm.md) 119), and an Ä in a name was not (120).
  * The board's best times on a fresh install are two names from a
    previous owner: `Data/data.cst` of our disc image holds `CustomRacingDB`
    and the two fields (members 22-24) from them (the script's own
    defaults are "MIA M" and "FIGGE F"). The game saves them with the rest
    of `data.cst` (casttext).
  * The maelstrom (object 46, `ObjectMaelstromScript`: circles the boat
    inside its outer radius) is on no map: unused.
- Propulsion rules (`checkCurrentlyOKPowers`): sail needs a rudder and a
  steering part; the motor needs both too unless it is an outboard, and a
  tank. So a boat with sail and outboard but no rudder can't switch to sail
  (Mulle says `05d055v0`): a rule, not the reviews' "sail never works" bug.
- The wind drifts the boat every frame (`BoatBase.loop`: `90 * #Drift *
  wind velocity / 100 / 100`; with the user's boat 18 a frame against the
  motor's 2 at a low throttle): a motor boat must keep its throttle up to go
  against it (fix 116: our gamepad code took a keyboard throttle away).
- At sea the shared CursorHandler's sprite 115 (no sprite in `05`'s score)
  was drawn as a white box beside the arrow: fixed ([scummvm](scummvm.md)
  75); the sea's pointer is the glove now.

## Scenes (from the scripts)

| Movie | Scene |
|---|---|
| `01` | Boatyard: the boat on its cradle, Mulle, Buffa; hotspots: the cradle (drag to `#Quay`), the drawing on the table (frame `Blueprint`), the metal and wood stores (drop targets), the toolbox (bottom right) |
| `02` | Shelves (`#ShelfNr`, `#JunkStart` 6, `#DragPart` 90) |
| `03` | Yard (`GoQuay`, `GoShelf1-3`, a gift, `#DragPart` 100) |
| `04` | Quay: radio, Figge, the photo book and camera, wind meter, `#DragPart` 98 |
| `05` | At sea: map, boat, sail, fog, fuel, medals (`MapDisplay`, `RecalcBoatProps`, `KPHBH`) |
| `06` | Photo album (export/import a boat, like Bygger bilar's 06) |
| `08` | Diploma (`PrintBH`) |
| `10` | Start: `Inits` (globals), then `11` |
| `11` | Login (name field, list of players) |
| `13`, `14` | File dialogs (movies in a window) |
| `15` | Blueprint: hulls, rudders, depth |
| `70`-`88` | Destinations |
| `LB*` | Levande Böcker: start menu, logo, demo, web dialogs |

## Disc layout differences from Bygger bilar

- Projector `MULLEBAT.EXE` sits in the disc root (1,515,691 bytes, tail-MD5
  `5e0c81ac9c9f8d9617a59ccdd29936a2`). **Not in ScummVM's detection table**;
  only the Norwegian `Mullebat.exe` (1,522,688 bytes) and German/Dutch builds
  are. Needs a one-line detection entry.
- `SOUND/`: 307 external WAV files (Bygger bilar keeps sounds inside the casts).
- `MOVIES/12M001V0.SMK`: a Smacker video (ScummVM can play Smacker).
- `DIRECTX/DX6SWE.EXE`: DirectX 6 installer.
- `BLS/BLW/BMS/BMW/BSS/BSW/SAIL.CXT`: seven casts of exactly 400 small bitmaps
  each (2,800 total), probably the boat drawn at many angles for sailing.
- `LB*.DXR`: Levande Böcker promo, web and profile movies.

## Assets (rough count, before a proper extraction)

5,289 bitmaps, 75.6 megapixels: 62 full-screen backgrounds, 35 sea-map tiles,
593 large and 1,055 medium sprites, 3,541 small ones (mostly the boat
frames), 3 1-bit masks.

## The other discs (looked at 2026-10-14)

Unpacked into `dist/windows/MulleMeck/games/<id>/` for the launcher
(`tools/iso_extract.py`, which now reads Joliet names; all four discs have
them, and their plain ISO 9660 names are 8.3 upper case).

- **Bygg båtar** (`MULLEBAT (Windows).iso`, 267 MB): laid out like Bygger
  bilar (`Movies`, `Data`, `Xtras`, `Mullebat.exe`), Director 6, 8-bit. No
  full-screen title with the logo (`08`'s `Title` is the diploma's); the
  launcher's card is the boat show `76b001v1`, its backdrop `78b001v1`.
- **Bygg flygplan** (2000, 687 MB): everything in InstallShield cabinets
  (`data1.cab` with `Start_Mulle.exe` 5,233,140 bytes, `MulleMeck.exe`,
  `gtDirect3D.dll`, `UdsPack.dll`, `Cc.dll`) and the data in `data.up` (499
  MB) and `map.up` (83 MB), packed "UDSP" archives (WAVs, Swedish texts). Not
  a Director game, or only a Director start menu: `MulleMeck.exe` has no
  Director data. ScummVM's Swedish `Start_Mulle.exe` (6,143,474 bytes,
  Director 8.5) must be another release. SafeDisc (`secdrv.sys`). Cabinets
  list with `unshield` (local copy, docs/tooling.md).
- **Bygg hus** (2002, 657 MB): Director 8.5 movies straight in `Movies/`
  (`00.cxt`, `00_Pic.cxt`, `01.dxr` ... `59.dxr`), 16-bit art; the program
  (`MulleHus.exe`, which ScummVM's detection wants) comes from the
  installer. Card: the cut-away house `24b013v0`; backdrop `55b001v0`.
- **Upptäck rymden** (2004, 446 MB): the game in `ToHD/` (`MulleRymd.exe`,
  `Data`, `Movies` with `Graphics.cxt`, `Xtras`, `Plugins`), 16- and 32-bit
  art. SafeDisc too, which does not matter: ScummVM does not run the
  program. Not in ScummVM's detection (only the Dutch and German ones).
  Card: the rocket by Earth `SpaceTravel_b010v0`; backdrop `Station_b001v2`.
  First try in our ScummVM (2026-10-14): `MulleRymd.exe` is a Director 9
  projector (`v9.0.0r383`, 3,341,981 bytes, tail-MD5
  `cae8beb617ac89dbf68103435e0ed521`), its movies Director 8.5 (config
  version `0x073a`), 800x600, 16-bit. Only fallback detection ("Macromedia
  Director Game (D8.00)"). It stops on a white screen at the projector's
  frame 1 with no Lingo error. Xtras it opens that ScummVM lacks: Font
  Asset, MacroMix, NetFile, Flash Asset. `MulleRymd.ini`: `StartupSettings`
  with `#Next:"LBMenu"`, search paths under `@INSTALL\`, `#SoundSystem:#Bass`
  (a BASS sound Xtra), `#VST` data files (`Data.vst`).

## Other Mulle Meck games in ScummVM's tables

`garygadget3` *Bygg flygplan med Mulle Meck*, `garygadget4` *Bygg hus med
Mulle Meck*, `garygadget5` *Upptäck rymden med Mulle Meck*. Norwegian
*Bygg fly med Mulle Mekk* and *Bygg biler med Mulle Mekk* are detected too
(ScummVM bug #13213).

## Player reports: reviews of the original game

Passed on by the user, 2026-10-14. Both are about the original game on
modern Windows, not ScummVM, but they say where to look first.

- *Sången, 2026-07-20, "Buggig nostalgi"* (Swedish, summarised): fine until
  sailing out on open water. There, **no sound at all** (back in harbour
  each time): wind, sea chart, radio and Mulle's comments were gone. Worse,
  **the boat froze every time the radio started at sea, the boat capsized,
  or Mulle was about to comment**; "return to the shipyard" always worked.
  Not workable: **no sail and none of the bigger engines worked**. With a
  sail fitted the game would not let you switch to it, and **a boat with
  only sails was not shown on the map at all**. They meant to try
  reinstalling or another release of the game.
- *RichieBoy89, 2025-10-24, "Funkar hyffsat"*: works fairly well on Windows
  10 32-bit, except **sound stuttering in cutscenes and when the radio
  skips**. One **script error** in a long session (had to restart). Their
  tips for the original: compatibility mode 640x480, 8-bit (256) colour,
  disable fullscreen optimisations.

What this suggests for us:
- The sea part leans on sound: the 307 external WAVs in `SOUND/`, the
  radio, Mulle's comments. "Freezes when a sound should start" looks like
  scripts waiting for a sound to finish or start (cf. Bygger bilar fix 44,
  looping sounds never "done", and 32, `the size of member` of sounds).
  Check that the external sounds load (paths, case) and that `soundBusy`
  and friends behave.
- Test every propulsion: sails, small and big engines, switching between
  them, and a sails-only boat on the sea map. If it fails in ScummVM too,
  decide whether it is a bug of the original (then a game quirk) or of the
  disc image (compare with the other variant).
- Stuttering sound in cutscenes was the original on modern Windows; check
  ours, but no evidence it carries over.
