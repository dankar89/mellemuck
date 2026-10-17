# Our ScummVM build (Director engine fixes)

Approach (A) from [decisions](decisions.md): the original game scripts run
unchanged on ScummVM's Director engine, and we fix where ScummVM's
reimplementation of Director 6 is incomplete or differs from the real thing.
The game itself is not changed; the bugs are in the player.

- Source: `~/src/scummvm`, branch `mulle` (based on master `c420cad105`,
  2026-10-12). Build: see [tooling](tooling.md#scummvm-build).
- All changes as one patch: `patches/scummvm-mulle.patch`
  (`git diff c420cad105 > patches/scummvm-mulle.patch` after each change: our changes are commits on the branch `mulle` on top of that upstream commit).
- Test flow: `tools/flows/bilar-new-player.sh` boots the game headless,
  creates player "Test", skips the intro and screenshots each step into
  `runs/latest/` (`SLOW=2` when tracing with
  `--debugflags=lingoexec --debuglevel=3`).

## Testing our changes

`tools/scummvm-regress.sh` runs ScummVM's own Lingo test suite
(`engines/director/lingo/tests`, target `directortest`) and compares it with
the same run on unmodified ScummVM (`~/src/scummvm-base`, a git worktree of
the base commit), then runs our Bygger bilar flows. Unmodified ScummVM already
fails 6 assertions (in the chunk and another test); ours must fail exactly
those and produce the same kinds of warnings. Run it after every change.
`macros.lingo` branches on `Random(5)`, so a few of its warnings ("Label Zoom
not found", "undefined handler 'check'", "No labels set") come and go
between runs on either build: noise, not a regression.

Controller input without a controller: `PAD=1 tools/harness.sh start` sets
`SCUMMVM_TEST_PAD`, which makes our build attach an SDL virtual game
controller at start-up (`sdl2-events.cpp`, `attachTestPad()`). It goes
through SDL, ScummVM's keymapper and the virtual mouse like a real one
("Using game controller: Virtual Controller"). `tools/harness.sh pad a down`,
`pad a up`, `pad lefty -20000`, `pad start down` etc. append lines to
`$RUN_DIR/pad.txt`, read every 10 ms (SDL's button and axis names). Without
a controller, ScummVM leaves the `JOY_*` inputs out of the keymaps entirely,
so keys bound to pad actions (`PADKEYS=1`) were the only way before.
`PAD=2` attaches a second one too (`SCUMMVM_TEST_PAD2`, driven with
`harness.sh pad2 ...`), as a Steam Deck with another pad connected (55).

## Debugging tools (from the ScummVM wiki's Director page)

The wiki (wiki.scummvm.org/index.php/Director) is behind bot protection that
blocks automated fetching; the user pasted it on 2026-10-12. Useful parts:

- Debug flags: `--debugflags=lingoexec` (with `-d5` shows every instruction),
  `lingostrict` (drop into the debugger on a Lingo error instead of carrying
  on), `loading`, `sound`, `xobj`, `slow`, `fast`.
- Debugger console (Ctrl+Alt+D): `bt`, `stack`, `var`, `channels [frame]`,
  `cast`, `markers`, `print <lingo>`, `repl`, breakpoints on functions
  (`bpset`), variables (`bpvar`), `the` entities (`bpentity`), events
  (`bpevent`), frames and movies.
- Visual debugger with Score, Cast and Channels windows: OpenGL graphics mode
  and `--debugflags=imgui`.
- `--start-movie=NAME@FRAME` starts at a movie and frame.
- `./configure --enable-asan` for memory-leak checks; ScummVM aims for none.
- File-format references: Team Earthquake's "A Tour of the Adobe Director File
  Format" and Shockwave docs, OpenShockwave / Earthquake Project repos, Archive
  Team's Shockwave page.

## Progress (Bygger bilar)

| Date | Reaches |
|---|---|
| 2026-10-12 start | Levande Böcker logo, then a Lingo error |
| 2026-10-12 | Login, new player, title screen, **garage** with Mulle, Buffa and the chassis, no errors |
| 2026-10-12 | Car building in the garage (drag parts off and back on), garage <-> junk pile, piles navigation, **collecting a part**: drag wheels from the pile onto the door, they appear on the garage floor |
| 2026-10-12 | Mouse pointer visible, characters animate (fixes 14-15); Windows build in `dist/windows/MulleMeck` |
| 2026-10-12 | Hover-over-Mulle crash fixed (16); progress saved and restored, autosave every 30 s with 9 backups (17-18) |
| 2026-10-12 evening | Junk-pile walking fixed (19); save slots and pause menu on Escape/F5/Start (20); OS mouse pointer against lag (21) |
| 2026-10-13 | Pause menu confirmed by the user on Windows; Mulle's pointer sprite shown as the real cursor (22); junk pile entered at another pile than 1 works: Mulle's head on his body, parts can be collected, walking between piles lays out each pile's parts (23-25, reproduced with the user's own save) |
| 2026-10-13 afternoon | **Building the car**: parts snap onto the car (fender, wheels), come off again, and dropped parts leave no image behind (26-27, with the user's save) |
| 2026-10-13 late afternoon | Crash on Windows while dragging a part guarded (28, cause still unknown); dragged parts follow the mouse smoothly (29) |
| 2026-10-13 evening | **The car rolls out to the yard** (31); `cuePassed` works (30); Mulle's speech no longer cut off (32) |
| 2026-10-13 evening | **Driving**: click the road, the show-off with the arrow keys, then the map with the car, accelerating and steering (33-35, with the user's car) |
| 2026-10-13 evening | Destination 85 (the dog) plays through; driving off the map edge changes maps (38-40) |
| 2026-10-13 evening | Terrain collisions while driving; input no longer runs inside scripts (41-43) |
| 2026-10-13 evening | Destination cutscenes hold on each speech (92, returning the dog); loading screens no longer stall 8 s (44-45) |
| 2026-10-13 night | **HD art (plan step 2)**: HD backgrounds in every scene at 1920x1440, F6 switches to the original art (46) |
| 2026-10-13 night | **HD art (plan step 3)**: HD sprites too (characters, dogs, car parts, the car on the map), default on (46-47) |
| 2026-10-13 night | **Gamepad driving**: the stick points the car, A gas, B brake/reverse (48) |
| 2026-10-13 late night | **Our pause menu**, drawn by the engine, controller first, scaled to the window (49); loading a save in the garage works (50) |
| 2026-10-14 | A lost controller release no longer leaves a part stuck to the pointer (51, "NOT FOUND!"); autosaves per scene, only when something changed, older ones in slots 1-2 (52); saves per player (53); autosave on leaving a scene, a cut-off progress file falls back to a backup (54); a virtual controller for headless tests |
| 2026-10-14 night | Sprites with a runtime ink use the other HD variants (70); every bilar scene checked for what is still classic |
| 2026-10-14 night | HD no longer shows another scene's pictures after a scene change (69; the car show's announcer had the fuel needle) |
| 2026-10-14 night | Bygger båtar from the user's Deck play: changing shelf works (67); a restart no longer fails on the saved progress (68) |
| 2026-10-14 evening | **Bygger båtar** starts (detection, start menu skipped), logs a player in (64), runs its loop objects (65), saves and loads per player (66); boatyard, blueprint and toolbox work |
| 2026-10-14 afternoon | From the user's Steam Deck play: every controller works at once (55); the album's file dialog shows and works, also in HD, and loading a save with it open no longer crashes (56-60); Steam's "Exit game" saves and quits at once (61) |

## Fixes

Each one is a general Director 6 behaviour, not a Mulle-specific hack, unless
marked otherwise. File paths are under `engines/director/`.

1. **`go(#next)` / `go(#previous)` ran the rest of the handler too early**
   (`lingo/lingo-funcs.cpp`). `go to frame` freezes the calling script and
   resumes it after the new frame is entered; `go(#next)` did not, so code
   after it ran before the target frame's behaviours existed. Mulle's intro
   does `go(#next)` then `sendSprite(22, #setText, ...)`.
2. **`the scriptInstanceList of sprite` was a stub** returning an empty list
   (`lingo/lingo-the.cpp`). Now returns the sprite's behaviour instances
   (read-only copy; Mulle only reads it).
3. **`beginSprite` was sent while other sprites' behaviours were still
   missing** (`lingo/lingo-events.cpp`, `createScriptInstances`). Director
   creates all new behaviours first, then sends `beginSprite`.
4. **`new(#type, castLib X)` / `new(#type, member N of castLib X)` was not
   implemented** (`lingo/lingo-code.cpp`, `createNewCastMember`). Implemented by
   duplicating an existing member of the type and clearing name and text,
   because ScummVM has no blank member constructors. Limitation: a member of
   that type must already be loaded. Mulle creates a save member per player.
5. **Setting `the name` of a member without an info record failed**
   (`cast.cpp`, `castmember/castmember.cpp`): new `getOrCreateCastMemberInfo`.
6. **A call whose first argument is a built-in object went to the current
   object's own handler** (`lingo/lingo-code.cpp`). `save(castLib "data")`
   inside MulleGlobals' own `save` handler (compiled as `localcall`) recursed
   forever. Messages to castLib/member/sprite/field references now go to the
   builtin of that name when one exists.
7. **`go` killed the old frame's behaviours immediately**, running their
   `endSprite` nested inside the calling script, which could destroy the
   caller's own context (`lingo/lingo-funcs.cpp`). The regular frame update
   already kills them after the script is frozen, so the early kill is gone.
8. **Freezing inside a nested execution broke native callers**
   (`lingo/lingo.cpp`, `lingo.h`). `sendSprite()` runs a handler in a nested
   `execute()` and expects a result; if that handler calls `go`, the freeze
   left an empty stack (assertion). Only the outermost execution freezes now.
9. **A behaviour's own `new` handler was never run** when instantiating it
   (`lingo/lingo-events.cpp`, `createScriptInstance`), leaving an empty stack.
   Mulle's `DrawCar` has `on new me, theUseChassisLoc ... return me`.
10. **D6 behaviour handlers were registered as global handlers**
    (`lingo/lingo-bytecode.cpp`). `sendSprite` to a sprite without the
    behaviour then ran another sprite's behaviour handler without `me`. Since
    D6, score-script handlers are only reached through their sprite; older
    versions keep the old behaviour.

11. **`the X of sprite N` for a non-built-in property returned nothing**
    (`lingo/lingo-the.cpp`). Since D6 it reaches the first behaviour on the
    sprite with that property (get and set). The junk pile checks drops on the
    door with `the trackRect of sprite(DoorStart)`.
12. **Rollover events went to the topmost sprite with any behaviour**
    (`events.cpp`, `score.cpp`). A dragged part in a high channel blocked
    `mouseEnter` on the door beneath it, so parts could not be dropped on the
    door. Since D6 rollover events go to the topmost sprite whose behaviours
    handle `mouseEnter`/`mouseLeave`/`mouseWithin` (ScummVM's own TODO said to
    check individual events).
13. **Behaviour parameters were lost when behaviours were created from inside
    a running script** (`lingo/lingo-events.cpp`, `createScriptInstance`).
    `sendSprite` to a sprite without instances creates them on the spot; the
    parameter evaluation then ran an unbounded `execute()` that continued with
    the caller's script, and the junk pile door lost its destination
    (`[#mediaName: "movie03"]`). The evaluation now runs only its own frame and
    is shielded from a pending `go` freeze.

14. **`enterFrame`/`exitFrame` never reached sprite behaviours**
    (`score.cpp`, `lingo/lingo-events.cpp`). Since D6 they are broadcast to
    every sprite's behaviours (like `prepareFrame`), then the frame script.
    Without this, Mulle's mouse pointer (a sprite moved to the mouse in its
    behaviour's `exitFrame`) stayed off-screen and character animations were
    frozen.
15. **Any sprite with a behaviour caught mouse clicks** (`sprite.cpp`,
    `respondsToMouse`, ScummVM's own TODO). Since D6 only sprites whose
    behaviours have mouse handlers take mouse events. Mulle's pointer sprite
    follows the mouse and has none, so clicks reach what is underneath.

16. **Inverted rects crashed ScummVM** (`lingo/lingo-builtins.cpp`,
    `lingoRect`). Director accepts rects with right < left or bottom < top and
    treats them as empty; `Common::Rect`'s constructor asserts (also in release
    builds). Mulle's garage door uses `rect(70, 25, 45, 100)` while the mouse is
    over Mulle, so hovering over him crashed the game (reported by the user on
    the Windows build). `inside`, `intersect` and `inflate` now build rects
    field by field.

17. **`save castLib` did nothing** (`lingo/lingo-builtins.cpp` `b_save`,
    `cast.cpp`). Now the cast's text members are written to
    `<target>-<cast file>.casttext` in the save folder (readable text:
    `member <id> <name len> <text len>`, name, text) with 9 rotating backups
    (`.bak1` newest), and applied on top of the original file whenever that cast
    loads (`Cast::loadSavedTextMembers`, which also recreates members the game
    made at runtime, like one per player). First attempt used ScummVM's
    `RIFXArchive::writeToFile` to rewrite `DATA.CST`; for an external cast it
    wrote member names from the wrong cast and truncated `CASt` chunks, so the
    text format replaced it.
18. **Autosave** (`savestate.cpp` `runAutosave`, called from the main loop in
    `director.cpp`). Every `autosave_period` seconds (ScummVM's standard
    setting; our packaged `scummvm.ini` sets 30) the engine writes ScummVM's
    autosave slot 0 through `saveGameState` (see 20), which first runs the
    game's own save routine. Runs only when no script is executing; a script
    frozen by `go` does not block it. ScummVM's own autosave timer is turned
    off (`canSaveAutosaveCurrently` false): it runs from event polling, also
    in the middle of scripts, and backs off for minutes when it cannot save.
    Snippets are compiled each time: anonymous scripts are reference counted
    and freed after the call, so a cached one crashed the second autosave.

19. **List functions refused points** (`lingo/lingo-builtins.cpp`). In
    Director points and rects work as small linear lists; `getAt`, `count` and
    `setAt` already allowed them, `getPos`, `getOne` and `getLast` now do too.
    Mulle's `SpriteAnimBH` calls `getPos(theLoc, -4711)`; walking between junk
    piles opened the debugger (reported by the user on Windows).

20. **Save slots and pause menu** (new `savestate.cpp`, `game-menu.cpp/.h`;
    `game-quirks.cpp` `quirkMulleMeckSaves`; `metaengine.cpp`). ScummVM's
    Director engine had no save states. A game quirk fills
    `DirectorEngine::SaveSupport`: the cast holding the progress (`data`),
    Lingo to sync it (`save(gMulleGlobals)`), to read the current player's
    name, and to restart after loading (log that player in, go to the
    garage; no player: the login screen). A save file is
    `DIRECTOR-PROGRESS 1`, `user <len>`, the name, then the cast's text
    members in the casttext format of 17; ScummVM appends its header
    (description, date, play time, thumbnail). Loading writes the members
    into the cast and the casttext file, then runs the restart Lingo. Saving
    and loading are allowed only when no script is executing. `hasFeature`
    reports save/load support only for titles with the quirk.
    The pause menu (`GameMenuDialog`, Swedish: Fortsätt spela, Spara spel,
    Ladda spel, ScummVM-meny, Avsluta) replaces the engine's main menu
    dialog, so Ctrl+F5 and the controller's Start (global keymap) open it.
    `garygadget` targets get their own game keymap
    (`director-garygadget`): left click = mouse left / JOY_A, right click =
    mouse right / JOY_B, game menu = Escape / F5 sending `EVENT_MAINMENU`. The
    default engine keymap sent F5 on as a key and mapped Escape to "Skip", so
    neither opened the menu. No partial matches, so Alt+Escape still
    reaches the game. The ScummVM GUI dialog was replaced by our own menu
    drawn by the engine (49).
21. **Mouse pointer drawn by the OS** (`backends/graphics/sdl/sdl-graphics.*`,
    `backends/graphics/surfacesdl/surfacesdl-graphics.*`). The user found the
    mouse laggy; mulle.js in a browser felt smooth. Measured: the engine loop
    runs about 90 times a second with about 1 ms of work, so the lag was the
    pointer itself: ScummVM paints it into each frame, so it trails the real
    mouse by a frame or two (vsync, compositor). The game's cursor image
    (the `cursor` command with cast-member cursors; not a sprite) is now
    handed to SDL as a colour cursor (`SDL_CreateColorCursor`) scaled to the
    window, and the frame-drawn cursor is skipped. Outside the game area
    the normal arrow shows; a hidden game cursor hides it. Rebuilt on cursor,
    palette and window-size changes. Only in the default SurfaceSDL renderer
    (OpenGL mode still draws it). Off with `system_cursor=false` in
    `scummvm.ini`. Headless screenshots cannot show an OS pointer.
    **On its own this did nothing for Bygger bilar** (user, 2026-10-13: "it
    shows the ingame pointer still. and its still janky"): Mulle's pointer
    is not a cursor but a sprite, see 22.
22. **The game's pointer sprite becomes the real cursor** (`score.cpp`
    `findCursorSprite`/`showCursorSprite`/`updateCursorSprite`, `window.cpp`,
    `game-quirks.cpp` `quirkMulleMeckBilar`; Mulle-specific through a quirk).
    Bygger bilar hides the cursor with `cursor(200)` and draws its own:
    sprite 115, which `CursorSpriteBH` moves to the mouse in `exitFrame`, so
    it moves only at the game's frame rate. Hover behaviours (`CursorBH`)
    swap its member (`C_Standard`, `C_Left`, `C_Right`, `C_Click`, `C_Grab`,
    `C_MoveLeft`/`Right`/`In`, `C_Back`). The quirk sets
    `DirectorEngine::_cursorSpriteChannel = 115`. While the default cursor
    is hidden (`kMacCursorOff`) and that channel shows a bitmap, its image
    becomes the cursor (`CursorMan`, so with 21 the OS pointer) and the
    stage skips drawing the channel. The image is made by drawing the sprite
    with its own ink twice, on two different backgrounds: pixels equal in
    both are the pointer, the rest transparent, so matte edges and white
    inside the glove come out as on the stage. Hotspot = the sprite's loc
    minus its bbox origin (`C_Standard` 19x32, hotspot 5,1, the fingertip).
    CLUT8 cursors use the screen palette (`replaceCursorPalette(nullptr, 0,
    0)`), so palette changes follow. Rebuilt only when member, ink, colours,
    size or widget change (checked before each render and on mouse events).
    When the game shows a real cursor (the driving map in 05 uses
    `cursor([member, mask])`), the sprite is drawn as usual. Dragged parts
    still follow the mouse at the frame rate, so they trail the pointer.
23. **Behaviours were created during `prepareMovie`, for frame 1**
    (`lingo/lingo-events.cpp`, `Score::createScriptInstances`). Upstream's
    `sendSprite`/`sendAllSprites` create missing behaviour instances on the
    spot. The junk pile's `Dir` object is made in `prepareMovie` and sends
    `#activate` to all sprites, while the score still holds frame 1, even
    though the garage opens the movie at the last pile's marker
    (`go "j4", "02"`). So every sprite got pile 1's behaviours (`PileBH`
    with `whichPile` 1, Mulle's head with pile 1's position, parts with
    pile 1's spans) and, being puppets by then, kept them after the jump.
    The user saw Mulle's head separated from his body and could not pick up
    parts (pile 1's parts were laid out over pile 4, and `PileBH` worked on
    pile 1's lists). Only showed up when the last visited pile was not 1,
    so the new-player flows never caught it. Now no instances are created
    before the score starts playing, as in Director.
24. **An unhandled `sendSprite`/`sendAllSprites` message called the sender's
    own handler** (`lingo/lingo-builtins.cpp`). When no behaviour handles the
    message it goes on to a movie-level handler, found with
    `Lingo::getHandler()`, which looks in the calling script first. `Dir`'s
    `activate` method sends `#activate` to all sprites; with no behaviours
    yet (23) it called itself without its object, forever. The fallback now
    looks only at movie scripts (`Movie::getHandler`).
25. **A channel entering another sprite span kept the old sprite**
    (`channel.cpp` `isDirty`, `score.cpp` `updateCurrentFrame`). ScummVM
    replaces a channel's sprite on a frame change only when it looks
    different (member, position, ink...) and never for puppets. The old
    sprite keeps its span and behaviour list; the old instances are killed
    when the span ends, so the channel has no behaviours at all. In the junk
    pile every pile's `PileBH` and part pool sit on identical placeholder
    sprites, and the parts are auto-puppets (set from Lingo). Walking from
    pile 4 to pile 3 left pile 3 without `PileBH`: no parts were laid out
    and the signposts did nothing. Since D6: a different span (start/end
    frame from the sprite details) counts as a change, and auto-puppet
    changes are dropped when the channel enters another span (Director
    keeps Lingo's changes only to the end of the span; explicit
    `puppetSprite` still survives).
26. **`the rect` and `the regPoint` of a bitmap member were in paint-window
    coordinates** (`castmember/bitmap.cpp`). A D6 bitmap stores its rect
    where it sat in the paint window and its reg point in the same space;
    most of Bygger bilar's car part images are stored at their place on the
    stage (`20b001v2`: rect 152,241 356x108, reg 320,240). Director reports
    the rect from the bitmap's own corner, `rect(0, 0, 356, 108)`, and the
    reg point relative to it, `point(168, -1)`; ScummVM gave the stored
    values. `PartsCommon.generateSnapRects` computes every snap target as
    the rect's centre minus the regPoint, so the targets were ~100 px off
    and no part could be put on the car (the user, 2026-10-13, and the old
    "wheels do not snap" note). Since D6 both are relative (also when
    setting the regPoint); internally ScummVM keeps the stored values.
27. **`the spriteNum of me` was the sprite of the current event**
    (`lingo/lingo-object.cpp`, `lingo-events.cpp`). Behaviours that do not
    declare `spriteNum` got `_currentSpriteNum`, which is only right while
    the behaviour handles its own sprite's event. The garage's
    `DragPartBH.report` is called by a screen object on mouse up and sets
    `the member of sprite (the spriteNum of me)` to `Dummy`: it blanked
    some other sprite and the dragged part's image stayed on the stage
    (duplicate images, reported by the user). Each behaviour instance now
    remembers its channel. 51 of Bygger bilar's scripts use
    `the spriteNum of me`.
28. **A handler run by `sendSprite`/`sendAllSprites` that returned no value
    crashed the game** (`lingo/lingo-builtins.cpp`, `executeForResult`).
    The builtin runs the handler and pops its result; a handler cut short
    (frozen by a `go`, which swaps the Lingo state out, or aborted by a Lingo
    error) leaves nothing, and `Lingo::pop()` asserted on the empty stack.
    The user's Windows build died a second after picking up a part in the
    garage (2026-10-13 14:43); found from the Windows crash dump (see
    [tooling](tooling.md)): `_wassert("_state->stack.size() != 0",
    lingo-code.cpp)` from `callBehaviorHandler` <- `b_sendSprite`, during a
    `mouseEnter`. Not reproduced headless. Now such a call returns VOID and
    logs `Handler 'X' returned no result (frozen by a go or aborted)`, so
    the next occurrence names the handler in the log.
29. **Dragged parts follow the mouse between frames** (`score.cpp`
    `followMouse`, `window.cpp`, quirk `_dragSpriteChannels`;
    Mulle-specific). The game moves the dragged part to the mouse once per
    frame (about 13 per second), so next to the smooth pointer (22) it was
    janky (user). After every engine step (about 90 a second), if the
    movie's drag sprite (`02`: 105, `03`/`04`: 100) sits where the mouse
    was at the previous step, the game is dragging it, and it is moved to
    the mouse and the stage redrawn. A part the game has not yet attached
    to the mouse (the junk pile waits until it leaves a 4x4 box) stays.
30. **`cuePassed` was never delivered** (`lingo/lingo-events.cpp`
    `Movie::processCuePassed`, `registerEvent`, `Lingo::processEvent`;
    `sound.cpp`). ScummVM read the cue points (`cupt`) and noticed them
    passing, but `registerEvent` had no case for the event ("Unhandled event
    cuePassed") and handlers got no arguments. Now it goes to the frame
    script, then the movie scripts, with Director's arguments: the channel
    as a symbol (`#sound1`...), the cue number from 1, and its name. A new
    sound starts again from its first cue point (`lastCuePointIndex` was
    never reset). Bygger bilar uses cues everywhere: Mulle's talking
    animation (`Talk`/`Silence` via `spritecuePassed`), the yard and the
    destinations (`toNextFrame` -> `go(the frame + 1)`), the intro.
31. **Movie scripts were not searched in cast order**
    (`lingo/lingo-events.cpp` `resolveScriptEvent`, `lingo-bytecode.cpp`
    handler registration). `scriptContexts` is a hash map, so an event went
    to whichever movie script with that handler came first in hash order,
    and a call reached whichever was compiled first. The yard (`04`) has
    `on startMovie` in members 12 (the setup) and 212
    (`startMovie(gDir)`, dead code in Director): ScummVM ran 212, whose call
    found 212 again, recursing forever. The user's car never reached the
    yard ("the game hangs"). Now the lowest member number wins for both.
32. **`the size of member` of a D6 sound was its cast record**
    (`castmember/sound.cpp`). For sounds stored as `sndH`/`sndS` (all of
    Bygger bilar's) the size stayed at the `CASt` record's few bytes.
    The game's `Sound.purge` stops an effect once it has played longer than
    `90 + size * ticksPerSec / 11025` ticks, so every line Mulle said was
    cut off after about 1.4 s (user: "cutof sounds when mulle talks"). Now
    it is the sample data size (a 4.9 s line: 214 KB, about 21 s of
    timeout).
33. **`duplicate()` of a point or rect returned nothing**
    (`lingo/lingo-builtins.cpp` `b_duplicateList`, `lingo.cpp`
    `Datum::clone`). Calls with a point go to the list builtin, which only
    accepted lists, pushed nothing, and the Lingo error opened the debugger
    ("Builtin 'duplicate' did not return value", user, when clicking the
    road to drive). It now copies anything; points and rects are copied
    for real (`clone` used to share their list).
34. **KeyPoll Xtra: `bgAllKeys` was a stub returning 0**
    (`lingo/xtras/k/keypoll.cpp`, `events.cpp`). The driving scene reads the
    arrow keys with `getPos(bgAllKeys(), 38)` (Windows virtual key codes;
    Mac key codes on the Mac): a Lingo error as soon as the drive started.
    `DirectorEngine::_keysDown` now tracks held keys from the event loop and
    `bgAllKeys`/`bgOneKey` answer from it (`bgOneKey` used to poll and
    swallow the game's key events). `platformKeyCode()` maps to the
    platform's codes.
35. **An empty bitmap in a stretched sprite covered the stage in white**
    (`castmember/bitmap.cpp` `createWidget`). The shared cast's `Dummy` is
    a 0x0 bitmap; the driving scene sets it into channel 118, whose score
    sprite is a stretched 657x485 full-screen shape. ScummVM stretched the
    empty picture into a white 657x485 surface with copy ink: the drive ran
    behind a white screen. A bitmap without pixels now gets no widget and
    draws nothing, as in Director. Found with the `screenshot` debug flag
    (the stage surface itself was one colour) and a temporary log of every
    blit.
36. **`the marker` was unknown** (`lingo/lingo-bytecode.cpp`
    `cb_v4theentitynamepush`). Bygger bilar's `WaitBH` and `ASoundBH` (yard,
    intro) do `go(the marker + 1)`; ScummVM pushed VOID, so the game jumped
    to frame 1 instead of the frame after the current marker. Now it is
    `marker(0)`. Found by `tools/lingo_audit.py` before anyone hit it.
37. **Play log** (`events.cpp` `logPlayEvent`; on with `play_log=true` in
    `scummvm.ini`, set in the Windows package and the harness). Every click,
    release and key, and the mouse position at most four times a second,
    as `PLAY <seconds> <what> <movie> frame <n> ...` lines in the ScummVM
    log, with the sprite and member under the mouse for clicks. The user
    suggested it; `tools/replay_playlog.py` plays a stretch of it back in
    the harness. Replaying a drive does not reach the same place: driving depends
    on frame timing.
38. **The score's last sprite-detail entry was lost** (`score.cpp`
    `loadFrames`, D6). The detail list has `listSize` offsets (one per
    entry plus the end), ScummVM read only `numEntries`, so the last entry
    had no end and read as empty. In six of Bygger bilar's movies that entry
    is a behaviour's parameters (08, 18, 82, 84, 85, 87); in destination 85
    (Salka the dog) the car animation started without them and the game
    stopped with "Builtin 'getaProp' did not return value" (user).
39. **`go(the frame)` cancelled a pending jump** (`lingo/lingo-funcs.cpp`
    `func_goto`, D6). Mulle holds each scene on its marker with the frame
    script's `go(the frame)` and moves on with a behaviour's `go(#next)` in
    the same exitFrame round (behaviours run first). The last go won, so the
    scene stayed. Since D6 a `go` to the current frame keeps a pending jump
    elsewhere, as scripts after a go see the new frame in Director.
40. **`listp()` was FALSE for points and rects**
    (`lingo/lingo-builtins.cpp`). Director: TRUE for lists, points and
    rects. Two hangs: the destinations' animations only build their path
    `if listp(toLoc)` (a point), and driving checks `if listp(checkBorders(...))`
    (a point at the map's edge): the car drove off the map instead of
    changing maps or stopping (user: "When driving off the screen, nothing
    really happens"). Points and rects behave as lists in many places
    (fixes 19, 33, 40); suspect this first when a list function misbehaves.
41. **Input was delivered in the middle of running scripts** (`events.cpp`
    `processSysEvents`). `Lingo::execute()` polls events every hundred
    instructions to keep the window alive, and that ran the handlers of
    clicks and keys inside the running script. Director delivers input only
    between handlers. With the user's quick clicks a door's `go` ran in the
    middle of the garage's start-up: `checkEquipment` (via `sendSprite`)
    returned no result and the game stopped ("Builtin 'sendSprite' popped
    extra 2 values", and probably the 14:43 crash behind fix 28). Input
    arriving while Lingo runs is now queued (`_deferredInput`, mouse moves
    coalesced) and delivered afterwards; the mouse position and buttons
    (`the mouseDown`), held keys (KeyPoll) and the play log follow at once.
42. **Text members stopped at the first NUL byte** (`stxt.cpp`). The
    driving map's terrain is kept as text (`30tNNNv0` and `30tNNNv0-2`, 316
    columns x 99 rows each; byte 0 road, 16 rough, 240+ blocked; read with
    `charToNum(char N of ...)` in `Wheels.quickCheck`). Read with
    `readString(0, len)`, everything after the first 0 byte was missing, so
    every lookup found 0 (road): the car drove through lakes and forests
    (user). All `strLen` bytes are kept now; the text is split by style in
    one piece, not character by character.
43. **U+0000 vanished when encoding to UTF-8** (`common/str-enc.cpp`,
    shared ScummVM code). `String::encodeUTF8` appended each character as a
    C string, so NUL characters were dropped and `the text of member` lost
    the terrain's road cells: the grid shifted and the car could not move at
    all. NUL is appended explicitly now. Also in `common/str-base.cpp`: the
    "Adding \\0 to String" warning fires once per run (per character it slowed
    the driving scene to a crawl).
44. **Looping sounds stopped being "busy" after one pass** (`sound.cpp`
    `isChannelActive`, a ScummVM "WORKAROUND HACK" of unknown origin; now
    skipped for D6). In Director a looping sound stays busy until stopped.
    Mulle's destinations put an `ASoundBH` on a sprite over the whole scene
    (92: channel 15, frames 6-96) that plays a looping background sound
    with `WaitForSound: #GoNextFrame`, which therefore never fires. With the
    hack, `finished()` turned TRUE after the first loop (6.6 s in 92) and it
    did `go(the frame + 1)` every frame: the playhead ran through every
    speech hold, so sprites that exist only on their marker frame flashed
    and each speech was cut after a frame (user: "the cutscene like
    fastforwarded", returning the dog to Figge, movie 92).
45. **A palette "fade" to the colours already showing took 8 seconds**
    (`score.cpp` `renderPrePaletteCycle`). Every Mulle movie shows a loading
    screen on frames 1-4 (sprite 118 and the previous scene's picture in
    119); frame 2 sets the system palette with speed 0, which ScummVM
    plays as the slowest fade (494 steps, 8.2 s), blocking on the old
    screen while the new scene's sounds already played (user: "I hear the
    audio from the next scene way before the loading screen disappear").
    The fade was not seen as a no-op because a new movie starts without a
    last palette, and the score names the same built-in palette as both
    castLib -1 and 0. Now a normal fade is skipped when the target's colours
    equal the screen's, and palette IDs are compared with built-in
    palettes normalised to castLib -1 (`paletteKey`). Loading frames take
    0.35 s now.

46. **HD art: backgrounds (plan step 2)** (new `hd.cpp`/`hd.h`, hooks in
    `director.cpp`, `graphics.cpp`, `window.cpp`, `events.cpp`, `movie.cpp`,
    `score.cpp`, `transitions.cpp`, `metaengine.cpp`; 2026-10-13). When an
    HD folder exists (`hd_path` in scummvm.ini, else `HD` in the game
    folder, with `index.txt` from `tools/hd_index.py`), the screen is
    1920x1440 full colour (3x the stage) for the whole session, so switching
    art is instant and the window never changes size. Without it nothing
    changes.
    - The classic 8-bit stage is still rendered as before (scripts,
      transitions and switching back rely on it). After each render
      `HDArt::compose()` rebuilds the same dirty rects on the 3x surface,
      bottom to top: a sprite with HD art (bitmap, ink copy/matte/bgtrans,
      matching variant in the index) is blended from its PNG, scaled to its
      bbox x3 (stretched sprites work); a run of sprites without HD art is
      drawn with ScummVM's ink code onto two scratch stages, one white and
      one black, and the pixels that agree are scaled up 3x (the same trick
      as the pointer in fix 22, exact for every ink). Sprites with trails
      fall back to the scaled classic stage for that rect.
    - `DirectorEngine::draw()` presents the HD surface instead of the window
      manager's output; `syncPalette()` triggers a full recompose instead of
      setting the system palette (the screen has none); transitions show
      the classic stage scaled up while they run (`setPassthrough`), then
      recompose. Mouse events and `Window::getMousePos()` divide by 3. The
      pointer sprite (fix 22) becomes a 3x full-colour cursor; other
      cursors (Mac arrow, watch) stay small for now.
    - Settings: `hd_art` (show HD art, default true, **F6** toggles and saves
      it), `hd_sprites` (also non-background bitmaps; default true since
      plan step 3), `hd_cache_mb` (decoded images kept, LRU, default
      1024; everything decoded would be ~1.6 GB).
    - Limits now: movies in a window (MIAW) are not drawn in HD; Mac cursors
      are tiny; images load on first use (a 1920x1440 PNG takes ~400 ms in
      the -O0 Linux build, far less in the -O2 Windows build); the HD
      surface goes through `blendBlitFrom` (needs RGBA32: OpenGL offers it,
      the software renderer only 16-bit, `present()` converts then).
    - Tested headless (`HD=1` harness, OpenGL on Mesa): 92's cutscene
      timing unchanged, F6 back and forth, login/title/garage/junk pile
      with HD backgrounds, dragging wheels to the door, driving on the HD
      map tile (92 ms per frame, same as classic).

47. **`ManagedSurface::blendBlitFrom` clipped right and bottom by the
    source's size** (`graphics/managed_surface.cpp`, shared ScummVM code).
    `srcRect.bottom -= (destRect.bottom - src.h)` should subtract what sticks
    out of the *destination* (`h`); with the source's height, a sprite
    reaching past the bottom (or right) of the target lost its whole source
    rect and was not drawn. HD sprites are drawn into sub-surfaces of the
    dirty rect, so Mulle's head vanished above the rect edge after dragging
    a part over it (HD step 3). Worth reporting upstream.

48. **Gamepad driving** (`metaengine.cpp` keymap `director-garygadget-driving`,
    `events.cpp` `updateDrivePad()`, quirk `_drivingMovie = "05.DXR"`;
    2026-10-13, the user's design, see [decisions](decisions.md)). While
    Dir's `mode` is `#Driving`, the driving keymap replaces the normal one:
    the left stick's half-axes arrive as joystick axis events (axis numbers
    `kDriveAxisLeft`...) instead of moving ScummVM's virtual mouse (a game
    keymap's exact match beats the global one), A/right trigger and
    B/left trigger are engine actions, the D-pad sends arrow keys. The
    engine turns that into the game's own input, as a player would: it holds
    Left or Right until the car's heading (`direction` of Dir's
    `carDriving`, read from Lingo) is within 0.6 of a heading of the stick,
    and holds Up/Down for A/B. The game (speeds, terrain, hits, fuel) is
    untouched. Details that mattered:
    - Hits: the game stops the car or turns it a heading away
      (`makeTheBestOfHit`). Steering straight back fought it (the car jiggled
      or got stuck); not steering let the nudges add up (the car turned away
      from the stick). Now: like the game's `mouseSteer`, no steering on the
      frame after a `#stop`/`#Turn` hit while within 1.6 headings of the stick,
      and a head-on `#stop` with the stick still pointing there releases the
      gas ("blocked") until the stick moves 1.5 headings or A is pressed again:
      the car waits at the edge, facing the stick.
    - Any key release ends the steering (Dir.keyUp gets no key, see
      [game-bygger-bilar](game-bygger-bilar.md)); the pad presses its direction
      again after every other key release (`padKeyReleased`).
    - Synthetic keys go through `_deferredInput`, so they reach the scripts
      between handlers like real ones, and show in the play log.
    Tested headless with keys bound to the pad actions (`PADKEYS=1`, no
    gamepad under Xvfb): turn on the spot, drive north and east along the
    roads, wait at a blocked edge, brake and reverse; keyboard driving
    unchanged.

49. **Pause menu drawn by the engine, controller first** (`game-menu.cpp/.h`
    rewritten; `DirectorEngine::runDialog()` override; keymap
    `director-garygadget-menu`; 2026-10-13, design in
    [decisions](decisions.md)). Replaces fix 20's ScummVM dialog, which was
    tiny in big windows (user: "make the pause menu a bit bigger. its hard to
    read on larger resolutions"). How it works:
    - Plugged in without touching ScummVM's shared code: `Engine::
      openMainMenuDialog()` (Start, Escape, F5, Ctrl+F5) calls the virtual
      `runDialog(*_mainMenuDialog)`; our override runs `GameMenu::run()`
      instead and leaves ScummVM's `MainMenuDialog` for "Fler
      inställningar". Loading still goes through `setGameToLoadSlot()`, so
      Engine loads the slot after the menu closes.
    - Drawn on the overlay (window resolution: 1920x1440 in HD, the whole
      window with OpenGL) into a 32-bit `ManagedSurface`, converted to the
      overlay format (16-bit in the SDL surface renderer) and copied in one
      piece. Layout in 640x480 units scaled by `min(ow/640, oh/480)`; the
      text is Fredoka loaded at the pixel size (`loadTTFFont`, found through
      SearchMan, i.e. `--extrapath`; else ScummVM's FreeSansBold, else the
      GUI font). Rounded boxes with smooth edges from a signed distance.
      The background is the game screen (`lockScreen()`, CLUT8 with
      `grabPalette`) averaged down to 160 rows and grown again bilinearly,
      dimmed to ~40%. `ManagedSurface::scale(..., true)` did not smooth
      (blocky result), hence our own.
    - Pages: main (Fortsätt, Spara, Ladda, Helskärm/Visa i fönster, Fler
      inställningar, Avsluta), save (slots 3-8 as picture cards), load
      (slots 0-2 autosaves, then 3-8), confirm (overwrite, quit). Cards read
      `querySaveMetaInfos()`: thumbnail and "idag 14:05"/"igår"/"3 okt".
      After saving: back to the main page with a "Sparat!" toast.
    - Input: the menu keymap (D-pad, left stick, arrows move; A, Enter,
      Space select; B, Escape, Backspace back; F5 close) is enabled and the
      game's two keymaps disabled while it is open; the mouse is unmapped
      and arrives as is (hover focuses, click selects, right click back).
      Start arrives as `EVENT_MAINMENU` (the engine is paused, so ScummVM
      does not reopen) and closes. Focus moves to the nearest item in the
      pressed direction, wrapping; held directions repeat (400 ms, then
      110 ms). The button that closed the menu is waited for (up to 0.5 s)
      before the game keymap returns, or its release reached the game (a
      stray Return keyup, or for A a mouse-up).
    - Keys and pad controls held when the menu opens are released for the
      game first (`releaseHeldInput()`: queued keyups, `DrivePad` reset), as
      their releases go to the menu.
    - Opens between scripts: ScummVM opens its menu from event polling,
      which also runs inside Lingo (`Lingo::execute()`), and saving needs a
      moment between scripts. A request while Lingo runs is pending until the
      main loop (`openPendingMenu()`); a script that runs over a second gets
      the menu in the middle, with Spara/Ladda greyed out.
    - Quitting: the game sets `the exitLock`, so ScummVM's quit asked "the
      game prevents quitting..." in a tiny dialog and Avsluta did nothing.
      Avsluta (after "Vill du sluta spela?") autosaves, clears the exitLock
      and quits; closing the window or Alt+F4 while the lock is on opens
      our menu on that question (`processEventQUIT()`, `_menuAskQuit`), and
      "Nej" goes straight back to the game.
    - Fullscreen: toggled with a GFX transaction and written to the config
      (Alt+Enter does not persist it).
    - ScummVM's own menu (Fler inställningar) gets a transient `gui_scale`
      so its GUI is laid out for about 480 rows, unless the player set a GUI
      scale; leaving it returns to the game.
    Tested headless in HD (OpenGL, 1920x1440) and classic (640x480, 16-bit
    overlay): open/close with Escape, F5, reopen; save to an empty slot and
    over a used one; load by keyboard and mouse; quit from the menu (saves,
    exits) and Ctrl+Q (asks; no returns). Not testable here: a real
    controller (no gamepad under Xvfb).
50. **Loading a save in the garage left it broken** (`window.cpp`
    `_reloadSameMovie`, set by `loadGameStream()`). The load restarts with
    `go(1, "03")`. ScummVM skips reloading when the next movie is the one
    playing (`Window::loadNextMovie()`: "next movie is the same as current
    movie, skipping load") and only jumps to the frame, but `stopMovie` has
    already run, and the game's `stopMovie` kills `gDir` (prepareMovie
    creates it). Frame 2's `loop(gDir)` then failed ("Call to undefined
    handler 'loop'"), the playhead ran on to frame 10, whose script goes to
    the junk pile: an empty garage, then the pile. A load now always reloads
    the movie (prepareMovie, startMovie); other same-movie `go`s keep
    ScummVM's shortcut. Verified: load in the garage stays in the garage
    with the same car.

51. **A lost button release left a part stuck to the pointer**
    (`processSysEvents()`, `_leftButtonDown`; 2026-10-14). The user's log,
    playing with an Xbox 360 controller on Windows, had a press (A) on a part
    with no release before the next press, and once a release with no press.
    In the garage the part stayed on the pointer, and the next press landed
    on the car's preview of the part (`showUseView`): the game took it for a
    part on the car and its `deletePart` showed `alert("NOT FOUND!")` (Car
    parent script, 00 cast). Our event path does not lose them: with the
    virtual controller (below), long drags with the stick and quick taps
    always gave pairs. So the loss is upstream (SDL's Windows joystick
    drivers, RAWINPUT by default in SDL 2.32, or the window losing focus:
    SDL drops presses, not releases, while unfocused). The engine now
    releases the left button first when a press arrives while it is still
    down (logged `up ... (added: the release was lost)`), so the part drops
    where the pointer is and the press then picks up what is there:
    verified with the user's save, pressing again over the car's preview
    gives no alert. `releaseHeldInput()` (the pause menu opening) lets go of
    the button too. To find the cause, the play log now also has the
    controller's buttons as SDL sends them, before the keymapper (`PLAY ...
    pad ... A down`, a `PadLog` event mapper that maps nothing), and window
    focus changes (`unfocused`, `focused`).
    The `WARNING: handler X did not return value` lines in the same log are
    ScummVM noting handlers the game calls as functions without `return`;
    harmless (the value is VOID, as in Director).
52. **Autosaves: per scene, only when something changed, older ones kept**
    (`runAutosave()`, `writeAutosave()`, `keepOlderAutosave()` in
    `savestate.cpp`; 2026-10-14, the user's rules in
    [decisions](decisions.md)). Before: slot 0 every 30 s, whatever happened.
    - When: on leaving a scene (`autosaveLeavingScene()`, called by
      `Window::step()` before the old movie stops, the scene still showing;
      user: "what if the game crashes when entering/exiting a scene?":
      loading the next scene is where crashes have been), 3 s after coming
      to the next one (the delay lets the thumbnail show the scene, not the
      loading screen; usually "unchanged" after the leaving save), and
      in a long scene every `autosave_period` as a safety net (the package
      sets 120 s, the harness 20 s), never while the mouse button is held (a
      part being dragged). Avsluta saves the same way.
    - Only when the game changed: the save data (the game's own sync, then
      the data cast's text members, sorted by id, so equal progress gives
      equal bytes) is made in memory and compared with slot 0's data (the
      file up to ScummVM's appended header); equal: nothing is written.
      Verified: idling in the garage skips every timer save, moving a part
      saves at the next one, walking to the junk pile and back logs "new
      scene: unchanged".
    - Only with a player logged in (`currentPlayerName()`), whose name is
      the description; a save from the login scene would only open the
      player selection.
    - Older autosaves: before slot 0 is overwritten, it is copied
      (`copySavefile`) into the older or empty one of slots 1-2 when the
      newer of them is at least 5 minutes older (header times, minute
      resolution) and neither holds the same data (after loading one of
      them). The previous session's last autosave is kept too. Slots 1-2
      holding a game the player saved (not an autosave, possible through
      ScummVM's own save dialog) are left alone. The load page shows the
      newer of slots 1-2 first, "Tidigare" only on autosaves. Verified with
      `autosave_period=20`: slot 1 at the second save, slot 2 five minutes
      later (09:59 and 10:04).
    - Each autosave is in the play log: `PLAY ... autosave 03.DXR frame 2
      new scene: saved, the last one kept in slot 1`, `timer: unchanged`,
      `leaving the scene: saved`. Verified: a part moved and the scene left
      at once gives "leaving the scene: saved", then "new scene: unchanged".
    - Slots are per player since fix 53: "slot 0" above is the player's
      first slot.

53. **Saves per player** (`playerSlotBase()`, `SaveSupport::playerMember`,
    `Cast::readTextMember()`, `saveTextMembers(onlyName)`; 2026-10-14, user:
    "yes, make saves per player"). Before, a save held the whole data cast,
    so loading one put every player back to that moment. The game keeps
    each player's progress in one text member, `User<id>DB`
    ([game-bygger-bilar](game-bygger-bilar.md), Saving); the quirk sets
    `playerMember = "User{user}DB"`.
    - Slots: blocks of 10 per player (ScummVM's 0-99, so 10 player names
      over time; the game allows 6 at once). In a block, +0 is the latest
      autosave, +1-2 older ones, +3-8 the player's own. A block belongs to
      the player named in the save data of its lowest save (`user` line,
      compared ignoring case like the game's Lingo); a player without saves
      takes the first empty block at their first save or autosave. No free
      block: autosaves are skipped (logged) and Spara says it failed. The
      user's old saves (slots 0-1, both one player's) become that player's block.
    - A save holds only the player's member. Loading reads that member by
      name (ids can differ after players are deleted and added), lets the
      game write whoever plays now into the cast first, sets the text and
      restarts as before; the other players' members are not touched. Older
      saves with the whole cast load the same way (only the player's member
      is taken).
    - The pause menu shows the logged-in player's block; Spara and Ladda
      are greyed out before a player has logged in. ScummVM's own menu no
      longer saves or loads (`hasFeature()` false for both; its buttons
      answer "use in-game interface"), as it would put saves in any slot.
    Verified headless: player A's saves went to slots 0, 1, 3; a new player
    B got 10 and 13 and B's load page showed only B's autosave; then
    A moved a part (tank at 200,460) and loaded slot 3: A's
    record equals the save again (tank at 522,460) and B's record is
    unchanged.

54. **A cut-off progress file is skipped for its newest whole backup**
    (`Cast::loadSavedTextMembers()`, `completeTextMembers()`; 2026-10-14).
    ScummVM writes save files in place (`DefaultSaveFileManager::
    openForSaving()` uses `createWriteStream(false)`; upstream turned atomic
    writes off in 2025, commit 28285eac0b, after save failures on Windows,
    bugs #15700/#16269), so a crash or power cut while writing leaves a
    cut-off file. The game's progress (`.casttext`) is read whole at start;
    a cut-off one restored a cut-off player record. Now the save and its 9
    backups are checked in turn (magic, every member's name and text of the
    given length, nothing after) and the first whole one is used, with a
    warning. Verified: the casttext cut to 2000 of 4647 bytes, the game
    starts from `.bak1` with the player's car intact. A cut-off ScummVM slot
    only shows as empty in the menu (its header at the end is missing); the
    older autosaves and the player's own saves are separate files.

55. **Every game controller at once** (`backends/events/sdl/sdl2-events.cpp`,
    `openOtherControllers()`, `axisFromOther()`; 2026-10-14). ScummVM opened
    one controller, `joystick_num` (0). On the user's Steam Deck with an
    8BitDo pad connected, SDL listed the 8BitDo's virtual pad first ("Using
    game controller: 8BitDo Ultimate 2C"), so the Deck's own controls did
    nothing; the user switched Steam Input to keyboard and mouse, and then
    could drive only by dragging the mouse. Now every game controller is
    opened (added and removed ones too), the first as before, the others
    "Also using game controller: ...". A stick resting near the centre on
    one pad (a few hundred either way) does not cancel a stick held over on
    another: an axis belongs to the pad that has it off centre (8000) until
    it comes back. Only that joystick's own SDL_JOY* events are read for a
    plain joystick (game controllers send them too). Tested with two virtual
    pads (`PAD=2`, `harness.sh pad2 ...`): the second pad's stick moves the
    pointer, its A clicks; the first pad's jitter leaves the held stick
    alone; the first pad works too.
56. **A window without a border drew white over its content**
    (`graphics/macgui/macwindow.cpp` `drawBorder()`; upstream bug). With no
    border loaded, the border surface stayed as created, colour 0, and
    `draw()` blits it over the window with green as the transparent colour:
    in 8-bit, colour 0 is white, so the whole window was white. Bygger
    bilar's file dialog (movie `13` in a window over the album,
    [game](game-bygger-bilar.md)) showed as an empty white box with every
    album button switched off: the user was stuck. Now the surface is
    cleared to the transparent colour.
57. **Clicks in a movie in a window missed by its border** (`events.cpp`
    `Window::processWMEvent()`; upstream bug). MacWindow gives the mouse
    relative to the window's outer edge; the movie's sprites are relative
    to its content (17 pixels in for the file dialog), so its OK and back
    buttons were missed. Mouse events are now moved by the border.
58. **Opening a closed window again with its own movie** (`window.cpp`
    `ensureMovieIsLoaded()`). `set the fileName of window` with the movie
    the window had stopped it first: a stopMovie in the window, which ran
    the shared cast's `stopMovie` (`set gDir to kill(gDir)`) and killed the
    album's director object while the album was open; the next statement
    hit 0 and the movie then failed to load ("Archive::openFile(): Error
    opening file"), a null movie, a crash. Director evidently does not send
    it (the second export works in the original). A closed, non-stage
    window now reloads its own movie afresh without a stopMovie (fresh
    list and name field); a window whose movie cannot load no longer
    crashes.
59. **Saving and loading ran in whichever window was current**
    (`savestate.cpp` `StageScope`). The main loop polls events with the last
    window stepped as the current one, so with the file dialog open a load
    from the pause menu ran its restart (`go` to the garage) in the dialog:
    the dialog stopped its movie, "Call to undefined handler 'cleanUp'",
    then a crash in `Lingo::processEvents` on the deleted movie. That was
    the user's "loading a saved state seemed to restart the whole game" on
    the Steam Deck: the game crashed back to the launcher, and Play started
    it from the beginning. Saving likewise looked for the progress cast in
    the dialog's movie. All save and load work now runs on the stage.
60. **HD: movies in a window, and sprites the classic drawing hides**
    (`hd.cpp`/`hd.h`; 2026-10-14). HD presented only the stage, so a movie
    in a window was not drawn at all. Each such window now gets its own 3x
    layer, composed from its sprites like the stage (HD art where there is
    some) and shown over the stage at its place (`present()`: the dirty
    area of the stage, then the windows on top, in a second surface).
    Rendering the window's movie composes its layer (`Window::render` for
    any window, not only the stage). Also, as the classic drawing does:
    a sprite's blend (fade) is applied (invisible sprites skipped, partly
    faded ones mixed in), and a sprite recoloured by its foreColor/backColor
    (ScummVM then draws only its black and white pixels) is drawn the
    classic way, not with its HD image: the garage's loading picture stayed
    on sprite 119 in the album that way, and HD showed it in the album's
    corner. The file dialog in HD: its own HD art, buttons work.
61. **A terminate signal saves and quits without asking**
    (`sdl2-events.cpp`, `events.cpp` `processEventQUIT()`). SDL_QUIT that
    does not follow a window close (within a second) is a signal, e.g.
    Steam's "Exit game" on a Steam Deck; it sets the transient
    `quit_from_system`, and the engine autosaves (if no script runs),
    clears the exit lock and quits, instead of asking "Vill du sluta
    spela?" in a menu nobody answers (Steam then kills the game). Tested:
    SIGTERM, "autosave ... quitting", gone in 0.2 s. Closing the window
    still asks.
62. **A crash prints a backtrace on Linux** (`posix-main.cpp`
    `crashHandler()`). See [tooling](tooling.md), Linux and Steam Deck
    crashes.
63. **The play log names the window an event is for** (`logPlayEvent()`):
    the window under the pointer (a movie in a window, or the stage), not
    the last one stepped; clicks on the album after the dialog closed were
    logged as the dialog's.

64. **An editable field takes the keys its own scripts pass on**
    (`lingo-events.cpp` `processEvents()`, `Movie::processInputEvent()`,
    `Lingo::_keyPassedToField`; 2026-10-14, Bygger båtar). A key goes to
    the field's sprite scripts, its cast member script, the frame and the
    movie scripts; ScummVM typed it into the field only if the last handler
    passed it. Bygger båtar's shared movie script has `on keyDown
    systemKeys()` (help, Alt+Q) without `pass`, so its login field took no
    typing, while the game works in Director. Now a key that gets past the
    field's own scripts (they pass it, or have no keyDown) is typed into the
    field; the frame and movie handlers still run (F11, Alt+Q keep working).
65. **`setProp`/`setaProp` create a property on a script instance**
    (`lingo-builtins.cpp` `setObjectPropCreating()`). ScummVM dropped the
    value when the object did not declare the property (and had no
    ancestor), against its own comment that objects take new properties.
    Bygger båtar's `LoopHandler` sets `#loopMe` on every object it runs and
    reads it each frame; its `Weather` object has no such property ("has no
    property 'loopMe'" every frame).
66. **Bygger båtar, Swedish** (`detection_tables.h`, `game-quirks.cpp`
    `quirkMulleMeckBatar`, `DirectorEngine::setDefaultStartMovie()`):
    detection, start at `Movies/10.dxr` (skipping Levande Böcker's start
    menu and its install check), save support for numbered players, the
    pointer sprite and dragged parts. See [game-bygger-batar](game-bygger-batar.md).

67. **A `go` to the movie that is playing loads it afresh** (`window.cpp`
    `Window::step()`; 2026-10-14, the user stuck in Bygger båtar's shelves).
    ScummVM jumped to the frame when the next movie was the current one,
    after `stopMovie` had already run. Bygger båtar changes shelf with
    `go("NewShelf")`, whose frame script does `go(1, "02")` from `02`: the
    shared `stopMovie` killed the scene's director object and no
    `prepareMovie`/`startMovie` made a new one; the scene then took no
    clicks ("Invalid object: 0" from the mouse handlers). Fix 50 did this
    for loads only; now any switch that stopped the movie reloads it (the
    flag `_reloadSameMovie`). Verified: shelves 1 -> 2 -> 3 -> 2 in båtar.
68. **The saved progress had empty members** (`Cast::saveTextMembers()`,
    `applyTextMembers()`; 2026-10-14). The cast's text members were written
    without loading them, and ScummVM reads members from the disc when first
    used: in Bygger båtar `PartsDB`, `WorldsDB`, `mapsDB`, the hull and
    rudder tables were saved empty, and the next start failed at once on
    `count()` of a number (the debugger opened). Saving now loads each
    member first. Restoring keeps the disc's text where a save has an empty
    one, which repairs files saved before (the user's Deck had one).

69. **HD showed another movie's pictures after a scene change** (`hd.cpp`
    `castStem()`, `imageFor()`; 2026-10-14, the user on the Deck: "in
    cutscenes it often uses the wrong sprites for animations ... the
    anouncer had some of his animation frame replaced with the pin from the
    fuel dasboard"). The HD lookup caches which cast file each cast library
    is, per movie, keyed by the movie's address. A new movie is often
    allocated where the last one was (seen: the album 06 -> the garage 03),
    and the cache then kept the old movie's own cast: at the car show (94,
    reached from the driving map 05), the announcer's frames, members 32-42
    of 94's cast, got the HD images of 05's members 32-42, the fuel gauge's
    needle. The cache now also checks the movie's file. And as a safety net
    an HD image is only drawn if its file is named for the member (the name
    as `tools/extract_assets.py` writes it: `safe()`, "GÅ-1" -> "G_-1");
    otherwise the original is drawn, with a warning once ("HDArt: ... is
    another one's"). Checked: no such warning in any scene run alone or
    across scene changes.

70. **HD for sprites the scripts give another ink** (`hd.cpp`
    `imageFor()`, `noteClassic()`; 2026-10-14, the user: "some textures are
    not HD in bilar yet?"). The HD variants come from the inks in the
    scores; a sprite placed with another ink at runtime found no file and
    was drawn the classic way. Now matte and background transparent stand in
    for each other (they differ only in enclosed white), and copy ink uses a
    transparent variant drawn over a white box of its size (the same
    picture). Found with a new debug line (`--debugflags=images
    --debuglevel=1`: "HDArt: classic: <movie> member ... : <why>", once per
    member), run over every Bygger bilar scene: what is left classic is text
    (name fields), shapes (flat click areas) and sprites that draw nothing
    either way (no widget). Mulle's pointer as a stage sprite (matte only)
    and the bird in 83 (copy) are HD now.

71. **HD cursors** (`hd.cpp` `cursorChanged()`, `setMemberCursor()`,
    `setArrowCursor()`; hooks in `score.cpp` where a sprite's or the
    default cursor changes and in `window.cpp` where the watch goes up while
    a movie loads; `game-quirks.cpp` `_pointerArt`, `_drivingArrows`;
    2026-10-14, the user: "in 'Bilar' there is a small white ugly cursor. I
    think its a loading cursor ... also the white arrow cursor when driving
    is ugly. Can we replace it with our own?"). Bygger bilar draws its own
    pointer as a stage sprite (Mulle's glove, member `C_standard`), but
    whenever a script sets a system cursor (the arrow, the watch while a
    movie loads, the crosshair and crossbar the yard uses for its hands,
    `cursor 2/3`) ScummVM drew its own small 1-bit cursor. With HD on,
    those now show a cast member's HD image instead (per game:
    `_pointerArt`, cursor type -> member name: arrow and watch -> the glove,
    crosshair/crossbar -> `C_Grab`), hotspot at the member's registration
    point, 3x. The driving map's arrows (`cursor [member, mask]` from 16
    pairs counted from `05n002v0`, 1-bit, 16 headings) become our own:
    white with a dark outline, anti-aliased from 4x4 samples per pixel,
    54 px, drawn in code once per heading. A cursor made from a bitmap
    member (`cursor(member)`) uses the member's HD image too. With HD off
    everything is as the game draws it. Checked: the glove HD in the
    garage and while scenes load, the arrow on the driving map while the
    mouse is held (`--debugflags=images --debuglevel=2`:
    "HDArt::setMemberCursor(): ... HD").

72. **Road driving and the smooth car** (new `roads.cpp/.h`; hooks in
    `events.cpp` `updateDrivePad()` and `processSysEvents()`,
    `lingo-the.cpp` `the mouseDown`, `hd.cpp` `compose()`/`present()`
    `drivingCar()`/`carImage()`/`carClean()`, `metaengine.cpp` F7,
    `director.cpp`; 2026-10-14, the user: "driving is very annoying ...
    Just move the cursor or stick in the direction you wanna go, and mulle
    moves there, along the roads"). The road network is built from each
    map's terrain grid as the game loaded it (`Wheels.Topology`); a driver
    follows it by holding the game's own keys: a direction (stick, the
    mouse held on the map, A) follows the roads and takes the branch nearest
    the direction, a click drives there the shortest way and stops. Presses
    on the map are the driver's and hidden from `the mouseDown`; the arrow
    keys stay the player's. With HD the car's picture turns smoothly (the
    nearest of its 16 headings turned by the rest) and loses its light grey
    edge. F7 shows the graph, the plan and the aim. `road_driving=false`
    turns it off. All of it in [driving](driving.md). Regression check
    clean (`runs/regress-roads.txt`).

Fixes 73-84 (2026-10-14 night, **Bygg hus**, Director 8.5; see
[game-bygger-hus](game-bygger-hus.md)). These are general D8.5 support;
most are gated on version 850+ (or 700+) so the D6 games are untouched.

73. **D7+ scores have up to 1000 sprite channels** (`score.cpp`
    `loadFrames()`, `frame.cpp` `readChannelD7()`): frames version 13 kept
    D6's 120 channels (crash on the first frame), and `readChannelD7` kept
    the channel number in a byte (channel 1000, the pointer, wrapped and
    overran the record). The D7 sprite record's 12 padding bytes (36-47)
    may also be updated on their own or partly (`readSpriteDataD7`).
74. **`LctX`**: D8.5 files name the script context `LctX`, not `Lctx`
    (`cast.cpp`); without it no Lingo was compiled at all (the screen still
    showed, so it looked alive). D8.5 bytecode (`lingo-bytecode.cpp`,
    as lingodec): handler records have 4 more bytes (stack height),
    variable/constant indices are plain (multiplier 1, not 8; also in
    `findVarV4`), new opcodes 0x6d pushchunkvarref, 0x6e/0x6f pushint,
    0x70 getchainedprop (`obj.prop`), and 4-byte-argument opcodes
    (0xc0+: pushint32, pushfloat32).
75. **D8.5 dot syntax compiles to calls** (`lingo-builtins.cpp`):
    `s.char[a..b]` is `getProp(s, #char, a, b)`; `getPropRef`,
    `setProp(obj, #line, i, v)`, `count(obj, #chunk)`, `setContents*`,
    `delete`, `hilite`; `list[#prop]` is `getAt`/`setAt` with a symbol;
    `list.count` is a property read (`lingo-the.cpp`); `obj.handler(#x)`.
    The method-call path keeps variable references for the chunk calls
    (`LC::call`).
76. **vList Xtra cast members** (new `lingo/xtras-cast/vlistxtra.cpp`): the
    game's player records and house grid. `content` get/set (copies),
    `new(#vList)`, decoding the disc's XMED (zlib blocks of a binary Lingo
    value; format in `tools/vlist.py`), saved in the `.casttext` save as
    `vlist` records holding a Lingo literal (own parser, no Lingo run).
77. **`sound(n)` channel objects** (new `lingo/lingo-soundobj.cpp`):
    `.volume`, `.pan`, `play/queue/setPlayList/stop/isBusy/fade*`.
78. **Amplitude Xtra** (new `lingo/xtras/a/amplitude.cpp`): lip sync;
    `ampValue` is not the real loudness yet but a level that changes every
    80 ms while the channel plays. Quirk-opened Xtras (`_startXtras`:
    FileIO, Amplitude, PrintOMatic), as the installer's `Xtras/` is not on
    the disc. `vList_register`, `ampRegister` are no-ops.
79. **Windows texts decoded as Shift JIS** (`util.cpp`
    `detectFontEncoding()`): a font ID in the Mac's Japanese range
    (16384-16895) made Windows text members Shift JIS; ignored now for
    Windows games that are not Japanese.
80. **D8.5 sounds** (`castmember/sound.cpp`, `cast.cpp`): the D6/D7
    `sndH`/`sndS` reader and loop flag now cover D8.5 (verified by
    capturing audio with `SDL_AUDIODRIVER=disk`).
81. **Typing in a field a behavior reads on keyUp** (`castmember/text.cpp`):
    `the text` takes the active editable widget's content first (typing
    reached the member only at the next draw, and the keyUp handler wrote
    the old text back).
82. **D7+: a behavior without the event's handler passes it on**
    (`lingo-events.cpp` `processEvents()`): the name field's keyUp-only
    behavior swallowed every keyDown, so nothing was typed.
83. **`the lastChannel`, `keyPressed()`, `quickTimeVersion()`** (7.0).
84. **Bygg hus quirk** (`game-quirks.cpp` `quirkMulleMeckHus`): start at
    `Movies/02.dxr`, FileIO as Xtra, the Xtras above, pointer sprite 1000;
    detection entry with `GF_TRUECOLOR` (16-bit art).
85. **`the mouseLoc`, `sprite(n).pointToLine(point)`** (`lingo-the.cpp`,
    `lingo-builtins.cpp`; also `pointToChar`, `pointToWord`, `pointToItem`,
    all D7): Bygg hus's login list (a scrolling field, `ScrollFieldBH`) picks
    the name under the pointer with them. Without them a click on a player's
    name did nothing (only new players could start). Now a double click on a
    name, or a click and Return, logs that player in. `-1` when the point is
    not over the sprite's text, as in Director.
86. **D8 image and colour objects** (new `lingo/lingo-imageobj.cpp`):
    `image(w, h, depth)`, `member.image` (a reference: changing it changes
    the member, which redraws), `member.image = img`, `(the stage).image` (a
    copy), and on images `getPixel` (a colour, or with `#integer` the raw
    value: x555 for 16-bit, `0xRRGGBB` for 32-bit, the index for 8-bit),
    `setPixel`, `fill` (rect or oval), `copyPixels` (rect or quad, ink 0/8/36,
    `#maskImage` + `#maskOffset` in source coordinates, `#blendLevel`),
    `duplicate`, `crop`, `trimWhiteSpace`, `createMask` (dark is drawn),
    `createMatte`; `rgb()`, `paletteIndex()` (equal by value in `=`); the D8
    builtins `bitAnd/bitOr/bitXor/bitNot`, `the milliseconds`. 16-bit pixels
    read as 5 bits times 8 (white is 248), as Director does; Bygg hus's mouse
    masks test for both 255 and 248. Bygg hus builds every wall strip and
    floor tile of the house this way (`IsoObj Parent`: new bitmap members in
    `BuildData`, pixels copied from `HouseData`'s texture sheets).
87. **Timeout objects** (new `lingo/lingo-timeoutobj.cpp`, fired from
    `Score::update()`): `timeout("name").new(period, #handler, target)`,
    `.forget()`, `.period`, `.persistent`, `.target`; not persistent ones end
    with their movie. Bygg hus: Mulle explains a build book button after
    1.2-2.5 s on it.
88. **A sprite's behaviors are one shared list** (`channel.h/.cpp`
    `ScriptInstanceList`): `sprite(n).scriptInstanceList` returns the list
    itself, so `.add(obj)` attaches a behavior, and setting it works (was a
    stub). Behaviors attached so get the frame events
    (`Movie::broadcastEvent`), the mouse (`Channel::scriptsTakeMouse()` in the
    hit test, only for lists a script changed so a pointer sprite whose
    behaviors ignore the mouse still lets clicks through), and their
    `spriteNum`. Bygg hus's build book gives each part on its page its drag
    behavior this way; without it parts could not be picked up. (A missing
    pair of braces here once stopped every behavior getting events: the
    resolve code's `if` has two statements now.)

89. **D7+ `flipH`/`flipV` drawn** (`Sprite::flipAroundRegistration()`,
    `BitmapCastMember::createWidget()`; was stored only): the box is
    mirrored around the registration point and the pixels mirrored in the
    widget. Only for D7+ movies (D6 scores may use those thickness bits for
    other things). Bygg hus draws the walls along one axis as flipped copies
    of the other's: without it a room's four walls stood parallel. Not yet:
    the hit test's matte and HD sprites are not flipped.
90. **`sprite(n).spriteNum` is n** (`Lingo::getObjectProp()`, `the
    spriteNum of sprite`; was a stub returning 0, or a behavior's property):
    Bygg hus empties its build book sprites' behavior lists, then asks
    `sprite(SP.spriteNum - 10)`, which went to sprite -10.

91. **Bygg hus saves** (`game-quirks.cpp` `quirkMulleMeckHusSaves()`,
    `savestate.cpp`, `Cast::readTextMember()`; 2026-10-15): the pause
    menu's Spara/Ladda, autosaves and Avsluta work, per player. Players are
    vList members `User<id>DB` in the `Data` cast (`gSystemObj.pUsersObj`,
    `.pUserObj`); the game saves on every scene change (`stopMovie`:
    `save(gSystemObj)`, which packs each house in the player record). The
    sync does the same in the middle of a scene: the house being built
    (`gIsoObj.pWorldDataArray`) into the player as the door does, the save,
    then the scene's own house unpacked again as its `prepareMovie` left it.
    The player is `the pUserId of the pUserObj of gSystemObj` (an integer
    once logged in). A load sets the player's vList content
    (`readTextMember` now also returns vList records), logs them in again
    and goes to the building site (04). The snippets are compiled by
    ScummVM's own Lingo compiler: write `the x of y`, not `y.x` (dot
    syntax gave VOID and "undefined handler"). Verified headless: autosaves
    while building (unchanged when nothing happens), Spara to slot 3, Avsluta
    quits, a restart shows the room, Ladda brings it back.

92. **D8.5 internal casts' font maps** (`Cast::loadCast()`): a D8.5 movie
    keeps its internal cast's `Fmap` under the cast library's resource
    (65536 + 1024), not the movie's 1024, so it was never read and every
    font id in it (Bygg hus's login: 32774, Times New Roman) was "not
    found" and fell back to Geneva. Each cast has its own map (ids 0x8001
    up); the shared casts' maps were read already.
93. **TrueType stand-ins for the Windows fonts** (`DirectorEngine::
    addFontSubstitutes()`, new `MacFontManager::addTTFSubstitute()`; D7+
    only): Times New Roman, Arial, Verdana, Trebuchet MS, Courier New, and
    the Mac names Director's cross-platform map (`FXmp`) turns them into
    (Times, Helvetica, Courier), are drawn with the Liberation fonts (SIL
    OFL, metric-compatible) at the size asked for, when no bitmap font of
    that size exists. Files in `third_party/fonts/`, copied into the
    package's `data/` (found through `--extrapath`). Bygg hus's login names
    are Times New Roman 18 bold: they were a small bitmap font.
    Embedded fonts (Font Asset Xtra, e.g. Bygg hus's `GiffordsHand *` in
    `00.cxt`) are still not drawn: their data is a PFR1 font in the member's
    `XMED` child. PFR1 is not the PFR FreeType reads: the character table is
    delta-encoded, and the glyph programs use other curve commands
    (dirplayer-rs, GPL-3.0, decodes them in about 3,000 lines of Rust,
    `vm-rust/src/director/chunks/pfr1/`; LibreShockwave, AGPL-3.0, converts
    them to TrueType). Not ported.

94. **`erase` takes the member away at once** (`LB::b_erase()`): ScummVM
    only flagged it and removed it at the next frame if a sprite showed it.
    Bygg hus erases its house's wall pictures and makes new ones with the
    same names on every change; the flagged old ones won the name lookup
    (lowest number), the sprites got them, and they vanished at the next
    frame: changing a wall texture or adding a roof left only the changed
    wall. Script members are still flagged (one may be running). Bygger
    bilar and båtar erase players' members the same way.
95. **`member.editable` on D8 text members** (`TextXtraCastMember`, stored
    only): Bygg hus's album (12) set it in its init, which stopped there
    ("no property 'editable'"): the album stayed empty.
96. **The saved cast keeps pictures a script made** (`Cast::
    saveTextMembers()`/`applyTextMembers()`, "bitmap" records:
    `serializeBitmapMember()`, `restoreBitmapMember()` in
    `lingo-imageobj.cpp`; `BitmapCastMember::_scriptImage`). The game saves
    its `Data` cast on every scene change and the next movie reads it back;
    ScummVM's saved cast held only text and vList members, so the camera's
    `tempHousePic` (the stage copied on the building site) was gone in the
    album, and photos put in the album would not survive a restart. Records:
    w, h, bytes per pixel, depth, pixel format, regPoint, palette, rows.
    Not in per-player saves (photos are album members of their own).
97. **D8 text members were white on black** (`TextXtraCastMember::
    createWidget()`, the colours swapped): the album's empty name boxes were
    solid black. Their authored font and size are still not read (12 pt
    system font).

98. **D7+ text members take typing** (`TextXtraCastMember`: `takesTyping()`,
    `updateFromWidget()`, editable widget; new `CastMember::takesTyping()`
    used by `channel.cpp` and `events.cpp` where only `kCastText` was;
    `lingo.cpp` `varAssign()`/`evalChunkRef()` use a member's text field;
    2026-10-15). The album (12) names a photo in `leftName`/`rightName`
    (text members): `editable = 1`, the player types, Return's keyUp deletes
    the last char (the RETURN) and saves. Setting `editable` remakes the
    widget; `the text` reads the typing from the active widget (as 81);
    text a script sets wins over older typing until the widget is made again
    (`_scriptText`: the RETURN came back otherwise). `hilite` is stored.
    Verified: "Huset" typed, shown, saved in the player's `#Album`.
99. **Test hook: Lingo from a file** (`score.cpp` `runTestLingo()`):
    `SCUMMVM_TEST_LINGO=<file>`; Lingo written into it runs between scripts
    and the file is emptied (`harness.sh lingo CODE`). Reaches scenes a test
    cannot click to: `addGivenMission(the pUserObj of gSystemObj, 39)` then
    `go(1, "70")`. Results in the log (`test Lingo: -> ...`). ScummVM's own
    compiler: `the x of y`, `getPixel(img, x, y)`, not dot syntax.
100. **D8 bytecode `swap` (0x21) and `atan(a, b)`** (`lingo-bytecode.cpp`,
    `LB::b_atan()`): `put x into s.char[a..b]` compiles to getPropRef, swap,
    setContents; without it 33,000 "STUB: opcode 0x21" and
    "assignment to non-variable" a second in 70. Two-argument atan is
    atan2 (70's `rotatePoint`).
101. **D7+ points and rects keep fractions** (`b_point()`, `b_rect()`
    `pointCoord()`; printed with decimals): Bygg hus's digging dog moves 0.2
    squares a tick and is drawn at `(loc - point(0.5, 0.5)) * 44`;
    `point(0.5, 0.5)` was `point(0, 0)` and the dog stood half a square off,
    under the dirt. D6 and older still round.
102. **D7+ `getPos`/`getOne`/`deleteOne` compare lists by contents**
    (`LC::eqDataStrict()`): the dog keeps the held arrows as `[1, 1]` lists
    made afresh each tick; by identity none was ever found: 13,000 copies,
    and a released key stayed held. Before D7 still by identity (ScummVM's
    tests).
103. **`keyPressed(code)` is whether the key is held now** (`b_keyPressed()`
    over `_keysDown`, Director key codes or a character): it answered "was it
    the last key pressed", so a released arrow stayed down.
104. **`member(x).prop[i]` and `sprite(n).prop[i]`** (`b_getProp()`, 3-4
    arguments): read the property as `obj.prop` does, then the item (the
    crane: `member("21b014v0").rect[4]`); it took only lists and broke the
    stack ("getProp popped extra 1 values", debugger) entering 69.
105. **D7+ mask ink with 8-bit masks** (`Channel::getMask()`): dark is drawn,
    light clear, cut at half grey (Director blends the greys). Made once per
    picture and box (`_maskFrom`, `_maskVersion`, `BitmapCastMember::
    _imageVersion`; made every frame, it slowed 69 to 2-3 frames a second).
    A sprite with mask ink is redrawn when a script paints its mask (the
    member after its own; `bitmapChanged()`). The mud in 69 was solid brown
    blocks over the scene; the scoop's bites now show.
106. **D7+ `sprite(n).rotation`** (new `kTheRotation`, `Sprite::_rotation`,
    `rotateAroundRegistration()`, `isRotated()`; `bitmap.cpp`
    `rotateSurface()`; autopuppet `kAPRotation`): clockwise around the
    registration point, the box turned in `getBbox()`, the picture drawn
    unturned (and flipped) then turned, nearest pixel, white outside (the
    users' inks drop it). The cranes' booms and the scoop's jaws (69), the
    glass globe's handles (64). Hit tests use the turned box. Not in HD
    (drawn classic).
107. **Colour objects equal by value** (`Datum::equalTo()`):
    `paletteIndex(0) = paletteIndex(0)` was false (objects were compared as
    strings, which hold their addresses), so the scoop never found the mud's
    surface in its mask. The check in the OBJECT case was never reached.
108. **1-bit pictures are 0 and 1 to Lingo** (`m_imageGetPixel()`,
    `m_imageSetPixel()`): kept as 0x00/0xff, `getPixel` gave
    `paletteIndex(255)` for black; the scoop bites where its 1-bit bite
    shape is `paletteIndex(1)`.
109. **`sprite(a).intersects(b)`, `.within(b)`** (D7 functions over
    `c_intersects`/`c_within`; the keywords still win for older games): the
    crane tools test what they touch so (64 stopped on it).
110. **`member.comments`** (`kTheComments`, cast info entry 20): Bygg hus
    keeps each sea map's water depth grid there (10's DepthChecker).
111. **Keypoll Xtra for Bygg hus** (`quirkMulleMeckHus`): the car and boat
    worlds (09, 10) poll arrows with `bgAllKeys`.
112. **D7+ 32-bit alpha** (`BITDDecoder::_alpha`, `BitmapCastMember::_alpha`,
    `getAlphaMask()`, used by `Channel::getMask()` for copy and background
    transparent inks): the picture stays opaque; the alpha plane, when it has
    both clear and opaque pixels, is a draw mask (half or more drawn, not
    blended; not for turned or flipped sprites). The world maps' car and boat
    stood in black boxes.
113. **D7+ film loops** (`FilmLoopCastMember::load()`): their score is an
    `SCVW` child as in D4-D6, read with the D7 frame format; sprites and
    sounds name the loop's own cast library as castLib -1. 62 and 63 (the
    waterfall). Some "Unknown castLib -1" lookups remain in 62 (harmless).
114. **Matte ink on D7+ text members** (`Channel::getMask()`): only the
    letters, from the drawn widget (the album's page numbers stood in white
    boxes).
115. **HD art for true-colour movies** (`hd.cpp` `screenColor()`): the
    classic layers are drawn in the window manager's format, so Bygg hus
    (32-bit, 16-bit art) gets HD too; its screen is 2400x1800. A member a
    script painted (`_scriptImage`: the dirt, maze, mud masks, the photos)
    or a turned sprite is drawn classic; D7+ flipped sprites get their HD
    image mirrored.
116. **Bygger båtar: a throttle set with the keys stays** (`events.cpp`
    `updateDrivePad()`, `DrivePad::stickThrottle`; 2026-10-15, the user on
    the Deck: "It appears you cant go west in bygger båtar?"). Fix 76 held
    Down whenever the stick was not pointed and a motor boat's throttle was
    above 0, to bring it down once the stick is let go. On the Deck Steam
    sends the controls as arrow keys, so the stick never pointed: each time
    Up was let go, Down took the throttle back to 0 (KeyPoll then saw Up
    and Down together while Up was held). The sea's wind drifts the boat
    (`loop`: `90 * #Drift * wind / 100 / 100` a frame, 18 east against 2
    west at a low throttle), so the boat drifted east whatever its heading.
    Now only a throttle the stick opened is brought down; it ends at 0 or
    when A is held. Tested (`flows/batar-sea.sh` with the Deck's save):
    keys west, throttle 100 stays after Up is let go, the boat crosses onto
    map (1,6); the stick west, then let go: 100 down to 0.
117. **The stick's halves: one side at a time** (`events.cpp`, the
    `EVENT_JOYAXIS_MOTION` case; 2026-10-15, the user: "using a motor boat,
    I was not able to turn towards west even"). The driving keymap binds the
    left stick as four half axes (`JOY_LEFT_STICK_X-`/`X+`, ...), and the
    keymapper (`keymap.cpp`) sends a half its 0 only on a reading of exactly
    0 (both halves then). A stick flicked from one side to the other without
    a 0 reading (easy on the Deck) left the other half at its last value:
    right held at full and left pushed full gave x = 0, so the stick
    pointed nowhere (or north/south with a little up or down), and the boat
    or car could not be pointed west. Now a half that moves sets the other
    to 0. Reproduced and tested with the virtual pad (`pad leftx 32767`,
    then `pad leftx -32767`): heading 4 stayed 4 before, now turns to 12.
    The Deck's log also shows Left and Right swapping directly while the
    stick pointed nearly opposite the boat (the shorter way flips with the
    stick's wobble); not changed, as the boat turns about 9 headings a
    second and got past it in every test.
118. **Bygger båtar: the stick rows on** (`events.cpp` `updateDrivePad()`;
    2026-10-17, found testing without the user). Oars row a stroke per
    press of Up (Down: backwards): `OarBoatAncestor.steer` starts one
    (`Oar` = 25) only while `Oar` is 0, the loop counts it down to 1, and
    only a key poll without Up/Down puts it back to 0. The pad held Up while
    the stick pointed, so an oar boat rowed once and then drifted (speed
    147, then 2). Now, for an oar boat in key steering, Up (Down) is let go
    when `Oar` is 1 (-1) and pressed again once the game has set it to 0:
    a player tapping the key. Tested with the virtual pad (scratchpad
    `sail3.sh`, a save with oars only): the boat rows on while the stick is
    held, also west against the wind. Motor and sail boats unchanged.
119. **A field sprite Lingo fills is drawn; `the rect of member` of a field
    can be set** (`Sprite::setCast()`, `TextCastMember::setField()`;
    2026-10-17). Bygger båtar's race board (`ObjectRacingScript`) puts its
    time fields into empty channels with `set the member of sprite`; a text
    member kept the sprite's old size (the score's), here 0x0, so the times
    were never drawn. Now a sprite with no size takes the member's. The
    script also sizes new fields with `set the rect of member` (read-only
    before, a warning): it now sets a field's box. Tested: the board shows
    the times (scratchpad `race5.sh`, `race6.sh`).
120. **TrueType stand-ins in Director 6 Windows games; Mac Roman bytes
    mapped** (`DirectorEngine::addFontSubstitutes()`,
    `MacFontManager::generateTTFFont()`; 2026-10-17). Fix 93's Liberation
    stand-ins are now used by D6 Windows movies too (Bygger båtar's race
    board is Helvetica 20, `Arial` once the game's font map is applied;
    no bitmap of that size, and the scaled bitmap had no Ä). Still only
    where no bitmap font of the size exists. And `MacText` hands a font
    whose encoding is one byte wide (Mac Roman) its text as bytes in that
    encoding (`MacFontRun::plainByteMode()`), which a TrueType font reads as
    Latin-1: Mac Roman's Ä (0x80) had no glyph, so "PRÄST" (a name
    on the race board) was drawn "PRST". A stand-in for such a font is now loaded with that encoding's
    byte-to-Unicode table (`loadTTFFont`'s `mapping`). Tested on the race
    board ("PRÄST"); Bygg hus's Times New Roman login names with å, ä, ö go
    the same way (not tried). Visible elsewhere: the login screens of
    Bygger bilar and båtar ask for Times 24 (the name list `ScrollField`,
    the typing `EnterField`), which was a small fallback bitmap and is now
    Liberation Serif 24, as Times New Roman on Windows (`runs/font-*`).
121. **Typing å, ä, ö into fields** (`MacText::processEvent()`,
    `insertChar()` takes a Unicode character; 2026-10-17). An editable
    field took only ASCII 0x20-0x7F, so a player named "Åsa" or "Björn"
    became "sa" or "Bjrn" on every login screen (SDL hands those letters
    over as text input: key code 0, `kbd.ascii` the character). Now
    characters from 0xA0 up are inserted too. Tested on båtar's login with
    xdotool (scratchpad `typeao2.sh`): "åsa Böö" is drawn in the field,
    logs in, is saved, and the boatyard autosaves. (xdotool on Xvfb sent
    Å as å, probably its way of typing a letter the keymap lacks; capitals
    from a real keyboard not tried.)
122. **Bygger bilar from a copy straight off the disc** (`game-quirks.cpp`
    `quirkMulleMeckBilar()`, `Window::loadInitialMovie()`; 2026-10-17, the
    user testing 0.1.1: "Xtra not found: fileio", from `getCDPath` in the
    start script, over and over). The disc keeps `FILEIO.X32` in `DATA/`;
    its installer copied it to `XTRAS/`, the only place Xtras load from, and
    our development copy had it there by hand. The quirk now lists FileIO
    as a start Xtra (as an Xtra, `_fileIOType`), and start Xtras are now
    opened at every start, right after the Xtras folder; before, only with
    a start movie (`loadStartMovieXLibs()`), which Bygg hus has and Bygger
    bilar, started from its projector, does not. Tested: fresh copies of
    all three games, made by the launcher's own `discs.bring_in()` from the
    disc images, start to their first screen without Lingo errors
    (before: bilar 300-400 "Xtra not found").

### Director 7-8.5 gaps (2026-10-14, `tools/lingo_audit.py research/lingo-hus`)

Found by the audit; image objects, colours, timeouts, bit operations and
`the milliseconds` are done since (86-88), the rest of what Bygg hus's
scenes need since 98-115 (2026-10-15, found by visiting every scene,
`tools/flows/hus-sweep.sh`). Still open:
- `image.draw()` (lines; Bygg hus's maze code has it but draws its walls
  with `copyPixels`), `charPosToLoc` (stub).
- Rotation in HD and in the hit test's matte; skew; alpha blending (alpha
  is a cut-out, 112); 2- and 4-bit bitmaps in the HD set.
- Embedded fonts (Font Asset Xtra, PFR1 data): see 93.
- Not needed: SetupDlg's installer calls, NetLingo, PrintOMatic.
Upptäck rymden adds a D9 projector and the Flash Asset, Font Asset,
MacroMix and NetFile Xtras.

73. **Steam Deck: the keyboard and two pads** (`events.cpp`
    `openScreenKeyboard()`, `updateScreenKeyboard()`, `editableFieldRect()`;
    `hd.cpp` keyboard badge; `backends/events/sdl/sdl2-events.cpp`
    `axisFromOther()`, `logPadAxis()`; 2026-10-14, the user on the Deck:
    "when starting bygger bilar it opens the steamdeck keyboard. Also, cant
    select anything in the start menu using the gamepad controller mapping.
    Cant control mouse pointer"; "allow moving the mouse pointer with the
    stick to the input field and click it"; "The same issue is for the Båtar
    game").
    - The keyboard: SteamOS's SDL2 is sdl2-compat over SDL3 (3.2.18);
      SDL2 starts text input when the window opens, and SDL3 then opens
      Steam's keyboard (`steam://open/keyboard...`), which takes the
      controls while open. The launcher now starts games with
      `SDL_ENABLE_SCREEN_KEYBOARD=0` (text input stays on, for å, ä, ö;
      the keyboard is not shown by itself) and sets `screen_keyboard=steam`
      on SteamOS. With that, a click on an editable text field (the
      login's name field in both games) opens Steam's keyboard by the same
      URL SDL3 uses, placed clear of the field, and `steam://close/keyboard`
      closes it when no field is left. In HD a keyboard badge stands beside
      the field.
    - The pointer ran to the right edge: two pads (the Deck's own and an
      8BitDo, both Steam virtual pads); fix 55 let the other pad's small
      stick values through once the first pad's stick was back in the
      middle, so a stick resting a little off centre (past the pointer's
      3000 dead zone) moved it. Now an axis belongs to the pad that last
      pushed it past 8000; small values from the other pad, and from
      everyone before any push, are left out. Tested with two virtual pads
      (`PAD=2`): a resting 4000 on pad 2 moves nothing, either pad takes
      over when pushed.
    - The log (stdout, the Deck's Steam console log) names each pad with
      its number and vendor:product, its buttons (`pad N button a down`)
      and its axes passing 3000 and 8000 (`pad N axis leftx 30000`): each
      button came twice on the Deck, to be explained from the next log.

74. **A command's value used gives VOID, not a stop** (`lingo-code.cpp`
    `LC::call()`; 2026-10-14, the user: "found a bug with Båtar. It crashes
    when I tried to go out with the boat"). Casting off at the quay (04, the
    rope at 482,357) loads the sea (05), whose `BoatBase.init` has `set
    tmpDriv to setaProp(tmpAllDriv, argType, ...)` (a slip in the original:
    `tmpDriv` is never used). ScummVM stopped with "Builtin 'setaProp' did not
    return value" and opened its debugger: the game froze (on the Deck it
    looked like a crash). Director gives VOID there; so does our build now,
    for any builtin, with a warning once per name. Reproduced and checked
    with the user's own save from the Deck (log in as the player, load the
    autosave, cradle to the quay, the rope): the sea loads.

75. **A pointer sprite a scene does not have stays hidden; båtar's arrow is
    the glove** (`score.cpp` `isStrayCursorSprite()`, `_cursorChannelSeen`;
    `window.cpp`, `hd.cpp` compose; `game-quirks.cpp` båtar `_pointerArt`;
    2026-10-14, seen at sea while fixing 74). Bygger båtar's shared
    CursorHandler (a global, from cast 00) sets sprite 115's member and place
    in every scene. At sea (`05`) channel 115 has no sprite in the score and
    the scene shows the system arrow (`cursor(-1)`); ScummVM auto-puppeted
    the channel and drew the glove there as a white box with the hand cut
    out, following the mouse beside the arrow. Director shows nothing in a
    channel without a sprite unless `puppetSprite`d; now the pointer channel
    is not drawn (nor used as the pointer) in a scene whose score never had
    a sprite in it. Which scenes: every Bygger bilar scene with the glove has
    it in its score (only 12, LBSTART, UNLOAD do not); in båtar 05, the
    destinations (70-88, which hide the pointer with `cursor(200)`: no
    pointer, as meant), 10, 13, showboat and the LB movies do not. And
    båtar's system arrow and watch show its glove (`00b001v0`, HD) as
    Bygger bilar's do (71): at sea the arrow was tiny on the 3x screen.
    Checked: the login, boatyard and quay keep their gloves, the sea shows
    the glove; regression check clean (`runs/regress-sea.txt`).

76. **Bygger båtar's boat: smooth, and with a gamepad** (`game-quirks.cpp`
    båtar `_drivingMovie`/`_drivingVehicle`/`_vehicleArt`/`_skipXtras`;
    `events.cpp` `updateDrivePad()`; `hd.cpp` `findVehicle()`,
    `vehicleImage()`; `roads.cpp` `watchCar()`; `lingo-code.cpp`
    `chunkRef()`; `resource.cpp` `loadXtrasFromPath()`; 2026-10-15, the user:
    "Steering the boat works. But can we make is smooth like we did for the
    car steering? ... and make it work with a gamepad ... The boat can just
    move in the direction of the gamepad stick").
    - The car's code made general: a game names Dir's vehicle property
      (`carDriving`, `boat`) and its pictures (`VehicleArt`: first member,
      count, the heading of the first, attached or not). The boat: 400
      pictures from `Boat0000` (heading 16 first, `+ 80 * side + 16 *
      front/back` tilt); its sail, `Segel0000` the same way by the sail's own
      angle, attached: shifted and turned by as much as the hull. The
      heading shown is `internalDirection` / 100; the boat glides between
      frames as the car does. Road driving stays Bygger bilar's
      (`_roadDriving`).
    - The gamepad: the stick points the boat (Left/Right held as for the car)
      and, for a motor or rowing boat, holds Up while it points within 2.5
      headings of the stick; let go, a motor boat's throttle is brought down
      to 0 with Down (not into reverse). A and B are the game's Up/Down (the
      throttle, the oars, the sail's sheet). A sail boat: the stick steers.
    - Why the keys did not work either: båtar's `MulleGlobals.new` lists the
      Xtras by name and ends with `delete char -30003 of availableXtras` (the
      RETURN after the last name). ScummVM took a chunk number below 1
      (other than -30000, "the last") for the whole string and deleted it
      all: the sea then found no KeyPoll Xtra, polled no arrow keys, and a
      released key left `#Release` in the motor's speedChange, which compares
      as > 0 here: the motor ran up to full by itself. Now -30001..-30009
      count as "the last" too. With the list right, the sea also tried its
      DirectSound sound object (our DirectSound Xtra is a stub: an alert
      "DirectSound installed!?"); båtar's DSOUND_R.X32 is not loaded
      (`_skipXtras`), so the game uses its normal sound as it did.
    - Tested with the user's boat (motor): stick right, throttle 0 -> 100, the
      boat goes right and onto the next map; let go, throttle back to 0, no
      reverse; stick down, the boat turns smoothly. Sail and oar boats not
      tried. Regression check clean (`runs/regress-boat.txt`).

(Until fix 122 `DATA/FILEIO.X32` had to be copied into `XTRAS/` by hand;
that is why the development copy never showed the problem.)

## Known open issues

- An empty text field draws solid black (login name field).
- `value()` logs syntax errors for a player record (one `]` too many) and for
  Mulle's animation table (stray `333` after the list). Both are quirks of the
  original data; ScummVM trims the garbage and parses the rest, as Director
  does. Not a bug.
- Sound untested (headless runs use the dummy audio driver).
- ScummVM's `RIFXArchive::writeToFile` mis-writes external casts (see fix 17);
  worth reporting upstream.
- ScummVM's debug log numbers channels `i + 1`: its "channel 17" is sprite 16.
- `Sprite::getShape(): kCastMemberSprite has no cast defined` warnings flood
  the log in the junk pile.
- The casttext backups skip `.bak2` (seen: `.bak1`, `.bak3`, `.bak4`);
  suspect `renameSavefile`/`exists` caching in `writeSavedTextMembers`.
- Since the save changes, the Lingo tests log one `File::open: node does
  not exist!` warning fewer than unmodified ScummVM; the assertions are
  the same (6 known failures).
