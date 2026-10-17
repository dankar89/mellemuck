# Tooling and environment

Machine: Windows 11 + WSL2 Ubuntu 24.04, RTX 4070 Laptop GPU (8 GB), 16 cores.
No passwordless sudo: packages needing root are installed by the user.
Windows `.exe` tools run from WSL through interop and get the GPU; Linux-side
GPU access exists only through CUDA (no Vulkan driver in WSL).

## Locations

| What | Where |
|---|---|
| Game discs (ISOs, community extras) | the player's own copies (never in the repo) |
| Extracted discs | `~/games/mulle-bilar`, `~/games/mulle-batar` |
| ScummVM source + build | `~/src/scummvm` |
| Python venv (numpy, Pillow, SciPy) | `~/.venvs/mulle` |
| Real-ESRGAN, ProjectorRays (Windows exes) | `third_party/` |
| Extracted / generated assets | `build/<game>/` |
| Decompiled Lingo | `research/lingo-<game>/` |

## Scripts (`tools/`)

| Script | Purpose |
|---|---|
| `director.py` | Director 6 reader: chunks, cast members, bitmaps, palettes, cast libraries, score inks |
| `extract_assets.py GAME_DIR OUT_DIR` | All bitmaps to PNG + `manifest.json` |
| `upscale_game.py BUILD_DIR [--only CAST]` | Whole HD set from the manifest; model pass cached in `up4x/` |
| `review_page.py BUILD_DIR` | Writes `review.html`: original/HD toggle (T; open with `#original` to start in original mode), backgrounds, filters, zoom; originals with the game's transparency go to `orig_ink/` |
| `review_server.py BUILD_DIR [--port 8765]` | Serves the review page at http://localhost:8765/review.html; flags (⚑ / F) are saved to `BUILD_DIR/review-flags.json` |
| `qa_check.py BUILD_DIR` | Compares every HD image with its original; random/worst contact sheets in `qa/` |
| `alpha_upscale.py IN OUT --ink ...` | Halo-free sprite upscaling for a folder (functions reused by `upscale_game.py`) |
| `morph.py` | The mask operations the HD tools need (dilate, erode, connected-to-border, nearest pixel) with numpy alone, the same results as scipy's ndimage (no scipy in the players' packages since 2026-10-14) |
| `upscale-compare.sh` | Run several models over sample images |
| `flows/hus-site.sh [PLAYER]` | Bygg hus: new player, intro skipped, waits out Mulle's tutorial on the building site until the room button opens the build book (`GAME_DIR` default `~/games/mulle-hus`, which needs `MulleHus.exe` and `Data.cst`) |
| `flows/hus-goto.sh SAVEDIR MOVIE ['lingo' ...]` | Bygg hus: an existing player (first login name of the save) logs in, the site, then the Lingo lines (`harness.sh lingo`), then `go(1, MOVIE)`: for destinations one drives to, e.g. `hus-goto.sh runs/hus-play/saves 70 'addGivenMission(the pUserObj of gSystemObj, 39)'` |
| `flows/hus-sweep.sh SAVEDIR MOVIE... [-- 'lingo' ...]` | Bygg hus: visits scenes one after another; a screenshot and the counted log lines (warnings, errors, the game's `put`s) of each in `$RUN_DIR/sweep-NN.*`; closes an alert with Return. Found most of fixes 104-114 |
| `flows/hus-album.sh SAVEDIR` | Bygg hus: an existing player with a photo taken on the site goes to the album with the camera and puts the photo in (the name under it can then be typed) |
| `flows/batar-login.sh [PLAYER]` | Bygger båtar: start, log a player in, boatyard (screenshots in `runs/batar-login`) |
| `flows/batar-sea.sh SAVEDIR PLAYER` | Bygger båtar: a player with a finished boat logs in, cradle to the quay, the rope: at sea (`05`), in HD with the package's game folder; then `harness.sh lingo`, e.g. `put the loc of the boat of gDir, the currentMap of the world of gMulleGlobals` |
| `flows/batar-dests.sh SAVEDIR PLAYER [MOVIE ...]` | Bygger båtar: sails out, then puts the boat beside each destination (deep water outside its outer radius, then inside its inner one, from the depth map), waits for the movie and the sea again; `results.txt` one line each. Keeps Mulle fed (he goes home hungry after ~4 min) |
| `flows/batar-events.sh SAVEDIR PLAYER [EVENT ...]` | Bygger båtar: the endings at sea that wait on one of Mulle's lines (out of fuel, broken boat, capsize, hunger), each forced with Lingo; waits for the quay and casts off again. Out of fuel with a sail or oars on board switches to them (reported, no quay). `ROD=1` gives the player a fishing rod (hunger: Mulle fishes, sails on) |
| `harness.sh` | Run ScummVM on a hidden X screen; click, `dblclick`, drag, `press`/`move`/`release` (a held button), `keydown`/`keyup`, type, screenshot; `PAD=1`/`PAD=2` one or two virtual controllers (`pad`, `pad2`); `lingo CODE` runs Lingo in the game (our build, [scummvm](scummvm.md) 99); `XVFB_SIZE=2400x1800` for Bygg hus in HD |
| `roads.py GAME_DIR OUT_DIR [--map N ...]` | Bygger bilar's road network from the terrain grids, drawn over each map and the world, plus JSON ([driving](driving.md)) |
| `flows/bilar-new-player.sh` | Test flow: boot, create a player, skip the intro, screenshots |
| `flows/bilar-junkpile.sh` | Test flow: new player, junk pile, drag wheels onto the door |
| `flows/bilar-mount-wheels.sh` | Test flow: junk-pile flow, back to the garage, drag wheels onto the chassis |
| `flows/bilar-piles.sh` | Test flow: new player, walk the junk piles 1-2-3-4-3-2 with each pile's signposts |
| `flows/bilar-user-save.sh SAVEDIR PLAYER` | Test flow with the user's own progress (e.g. the Windows package's saves): log in, garage, pile; `STOP=garage` stays in the garage |
| `score_dump.py MOVIE [CHANNELS] [--frames A-B] [--main]` | A movie's markers and how sprite channels (and with `--main` the tempo/transition/palette channels) change per frame |
| `casttext_edit.py sub FILE OLD NEW` / `drop FILE NAME...` | Edits a saved cast (`*.casttext`, e.g. a player's boat parts) keeping the members' header lengths right; a wrong length makes the game load an older backup without a word |
| `build-release.sh VERSION` | Release archives for players from the packages: `dist/release/MulleMeck-Windows.zip` and `-Linux.tar.gz` (names without version, so `releases/latest/download/...` links stay right), with `release/LÄS MIG.txt` (version filled in), `LICENSER.txt`, `licenser/` and the ScummVM patch in `källkod/`. Leaves out games, saves, HD, `launcher.json` (the Deck's address), logs; writes a fresh `scummvm.ini`; fails on any disc file or personal path/address |
| `lingo_audit.py [LINGO_DIR] [SCUMMVM_DIRECTOR_DIR]` | Lists builtins, commands and `the` names the game's scripts use that our ScummVM lacks or stubs (static: misses wrong argument types and behaviour) |
| `replay_playlog.py LOG [--movie M] [--from S] [--to S] [--speed X] [--dry-run]` | Plays back the PLAY lines of a ScummVM log (play log) in the running harness |
| `crashdump.py DUMP [EXE]` | Read a Windows crash dump: faulting module, scummvm.exe functions and assert strings on the stack (see "Windows crash dumps") |
| `flows/bilar-garage-wander.sh` | Robustness test: hover the whole garage and click hotspots, report the step that crashes |
| `iso_extract.py IMAGE OUT_DIR` | Extract a game disc image (plain ISO9660) |
| `msi_extract.py SETUP OUT_DIR [NAME ...]` | Unpack files from an MSI or a Wise `setup.exe` with one inside (OLE compound file, MSZIP cabinet; standard library only, used by the launcher for Bygg hus) |
| `scummvm-regress.sh [--no-flows]` | Regression check: ScummVM's Lingo tests vs unmodified ScummVM, plus our flows. Beside another session: `REGRESS_OUT=... SCUMMVM=<copy> DISP=:95 RUN_DIR=...` |
| `build-windows.sh` | Rebuild the standalone Windows ScummVM into `dist/windows/MulleMeck/` (fails with "Permission denied" while the game runs on Windows: close it first) |
| `build-mingw-deps.sh` | Build static zlib, libpng and FreeType for the Windows build into `~/.local/opt/mingw-deps` (sources in `~/.cache/mingw-deps-build`) |
| `play-bilar.sh [--check]` | Start the Linux build in WSL with window and sound via WSLg |

## ScummVM build

```
cd ~/src/scummvm
./configure --disable-all-engines --enable-engine=director --disable-detection-full --enable-debug
make -j16        # ~40 s
```

Needs `libsdl2-dev` (installed). Config used by the harness:
`scummvm.ini` in the project root, with `enable_unsupported_game_warning=false`.

## Windows build (standalone, no WSL needed to run)

The game data is platform-neutral Director files; only the player is built
per platform. The Windows `scummvm.exe` is cross-compiled from the same
source with MinGW (`sudo apt install mingw-w64`) and SDL2's MinGW package
(`third_party/sdl2-mingw/`, copied to `~/.local/opt/sdl2-mingw` with the
`prefix=` line of `bin/sdl2-config` and `lib/pkgconfig/sdl2.pc` fixed):

```
mkdir -p ~/src/scummvm-win && cd ~/src/scummvm-win
D=$HOME/.local/opt/mingw-deps
PATH=$D/bin:$PATH ~/src/scummvm/configure --host=x86_64-w64-mingw32 --disable-all-engines \
    --enable-engine=director --disable-detection-full --enable-release --disable-imgui \
    --with-sdl-prefix=$HOME/.local/opt/sdl2-mingw \
    --with-zlib-prefix=$D --with-png-prefix=$D --with-freetype2-prefix=$D
make -j16
```

zlib, libpng and FreeType (HD art needs PNG, the engine-drawn menu
FreeType) are static libraries from `tools/build-mingw-deps.sh` in
`~/.local/opt/mingw-deps` (configured 2026-10-13). Gotchas:
- There is no pkg-config here, and FreeType no longer installs
  `freetype-config`; configure finds FreeType through a small hand-written
  `~/.local/opt/mingw-deps/bin/freetype-config` (answers `--cflags` and
  `--libs` with `-lfreetype -lpng16 -lz`).
- With FreeType on, configure also enables ImGui (the developer debugger):
  `--disable-imgui` for the player build.
- With FreeType on, the exe embeds ScummVM's font packs, including the
  38 MB `fonts-cjk.dat` (20 -> 63 MB). `tools/build-windows.sh` leaves it out
  with `make DIST_FILES_ENGINEDATA_BASE_BIG=` (exe 27 MB).

Fonts: `third_party/fonts/Fredoka-SemiBold.ttf` (OFL, `OFL.txt` next to it)
is a static weight-600 instance cut from Google Fonts' variable
`Fredoka[wdth,wght].ttf` with
`python -m fontTools.varLib.instancer Fredoka-variable.ttf wght=600 wdth=100`,
because ScummVM's TTF loader uses a variable font's default instance.

After the first setup, `tools/build-windows.sh` rebuilds and refreshes the
package folder. libgcc/libstdc++ are linked statically; the exe needs only
Windows system DLLs plus `SDL2.dll`, shipped next to it.
Package folder: `dist/windows/MulleMeck/` with `scummvm.exe`, `SDL2.dll`,
`scummvm.ini`, `Mulle Meck bygger bilar.bat` (relative paths, so the folder
can be moved), `README.txt`, `data/` (the pause menu's font and its OFL
licence, copied by `build-windows.sh`), `saves/`, and `games/bygger-bilar/`
(DATA, MOVIES, XTRAS from the user's disc, FileIO in XTRAS). Never share it
with `games/` included.

Data files for the engine (the menu font) are found through SearchMan.
ScummVM on Windows does **not** search the exe's folder (only the current
directory, as a last resort), so the .bat passes `--extrapath="%~dp0data"`;
`tools/harness.sh` and `tools/play-bilar.sh` pass
`--extrapath=third_party/fonts`.

For quick tests from WSL, `play-bygger-bilar-wsl.bat` in the project root starts
the Linux build through WSLg (`tools/play-bilar.sh`).

## Headless testing (`tools/harness.sh`)

Xvfb + xdotool were unpacked without root (`apt-get download` + `dpkg -x`)
into `~/.local/opt/xtools`. Xvfb insists on `/usr/bin/xkbcomp` and WSLg owns
`/tmp/.X11-unix`, so it runs inside a user namespace with an overlay mount
over `/usr/bin` and a tmpfs over `/tmp/.X11-unix`; clients connect through
the abstract socket. Coordinates are relative to the ScummVM window.

Bygg hus (2026-10-15): scenes behind driving or missions are reached with
`harness.sh lingo` (`hus-goto.sh`, `hus-sweep.sh`); the game's objects are
read the same way, e.g. `harness.sh lingo $'global gDirObj\nreturn the
m_loc of the m_oDawg of gDirObj'` (the answer is the log's `test Lingo: ->`
line). The snippets go through ScummVM's own compiler: `the x of y`,
`getPixel(img, x, y)`, `set x = ...`; dot syntax gives VOID. The file is
written whole (temporary name, renamed): read half-written, a snippet ran as
`global gDirObj` alone and the next line errored.

## Decompiling scripts

```
third_party/projectorrays/projectorrays.exe decompile <movies dir> -o <out dir> --dump-scripts
```

ProjectorRays 0.2.0 (Windows build). Takes about a second per game.

## Gotchas

- Two sessions at once: `harness.sh` defaults to display `:99`, and its
  `stop` kills every ScummVM started from `~/src/scummvm` (and the flows
  call it). Give each session its own `DISP=` and, for the second one, a
  renamed copy of the binary (`SCUMMVM=/path/scummvm-hus`) stopped with its
  own `pkill` (2026-10-14: one session typed into the other's window).
- Hearing a headless run: `SDL_AUDIODRIVER=disk SDL_DISKAUDIOFILE=out.raw`
  writes ScummVM's output (44.1 kHz stereo s16le) to a file; measure its
  loudness per second with numpy.
- Wise/MSI installers (Bygg hus `Setup.exe`): Windows 7-Zip
  (`/mnt/c/Program Files/7-Zip/7z.exe`) extracts the `.WISE` section and
  the MSI carved from it (OLE magic `d0 cf 11 e0`).

- Some builds cannot write into `/mnt/c` (FreeType: `could not open
  objs/ftexport.sym for writing`); build third-party code under `~/.cache`.
- Headless screenshots do not show the mouse pointer since it is drawn by
  the OS ([scummvm](scummvm.md) 21-22; Mulle's pointer sprite is no longer
  drawn on the stage either). The harness's `scummvm.ini` therefore has
  `system_cursor=false` (since 2026-10-13): ScummVM draws the pointer into
  the frame and screenshots show it. The Windows package keeps the OS
  pointer.
- Two harness runs at once collide: `harness.sh stop` kills every ScummVM
  started with the project's `scummvm.ini`, also one on another `DISP`
  (e.g. the regression check's flows killed a manual run).
- `harness.sh stop` kills only its own run's ScummVM (the pid in the run's
  `.state`) and the Xvfb on its `DISP`; before 2026-10-14 it killed every
  dev-build ScummVM, also another session's. For a test beside another
  session: `SCUMMVM=<a copy of the binary> DISP=:95` (a copy: a rebuild
  does not change it under the running test; `cp` fails with "Text file
  busy" while it runs: stop first).
- **Two Claude sessions in one ScummVM tree** (2026-10-14: a Bygg hus session
  edited `~/src/scummvm` while this one built packages): every build takes
  the other session's unfinished edits (a temporary `PROBE` line broke the
  Linux package build; the Windows build ran while it changed
  `lingo-soundobj`, `lingo-builtins`, `module.mk`), the patch refresh takes
  them too, and a regression check run before them says nothing about them.
  Check `git status` file times before building; better, one tree per
  session (e.g. a copy for the other game, our patch applied). The same
  goes for `launcher/` and `tools/`: a new tool the launcher imports must be
  in the build scripts' tool lists (`msi_extract` was not, and the packaged
  launcher could not start).

- **Many small images in a row reset the GPU driver: the PC freezes and output
  is corrupted.** In the full Bygger bilar runs (2026-10-12) the laptop froze
  repeatedly and Windows logged `nvlddmkm` event 153 ("Error occurred on
  GPUID: 100") every ~20 s while Real-ESRGAN processed hundreds of small
  sprites. Outputs came back as stripes, noise or black, while the exe still
  exited 0. What we measured:
  - 81 full-size backgrounds (2 minutes of heavy work): no errors.
  - Short test runs of a few images: no errors.
  - 20 small sprites, even with `-t 128 -j 1:1:1`: 3 errors. So it is not
    long dispatches (classic TDR); smaller tiles do not help.
  - The same sprites packed onto 1024x1024 sheets: no errors, and much
    faster (60 sprites in 10 s).

  `upscale_game.py` therefore packs small sprites onto sheets (each with a
  12 px margin of its own replicated edge pixels), runs 4 sheets per exe call
  with 2 s pauses, checks the Windows log after each call and stops at the
  first `nvlddmkm` event, and validates every cut-out against its input (mean
  difference < 25; good outputs measure 3–15). Do not raise `TdrDelay`. Long
  GPU jobs on this machine need the user's OK (they use the PC meanwhile).
  Check the log with:
  `Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=(Get-Date).AddHours(-1)} | ? ProviderName -eq nvlddmkm`

- `pkill -f <pattern>` kills the calling shell when the pattern appears in its
  own command line; use a bracket trick like `MOVIE[S]`.
- Windows exes resolve relative paths from their own working directory; pass
  absolute paths or `cd` first (`upscale-compare.sh` does both).

- `harness.sh stop` waits until its ScummVM is gone (2026-10-15): copying a
  rebuilt binary over the renamed copy right after a stop failed with "Text
  file busy" and the next test ran the old build. Check with
  `pgrep -af <copy>` when results look unchanged.
- `harness.sh stop` (and so every flow, which starts with one) kills **every**
  ScummVM started as `~/src/scummvm/scummvm`, whatever its display
  (2026-10-16: a båtar flow killed the regression's junk-pile flow, which
  then "failed"). Beside anything else, run a renamed copy
  (`SCUMMVM=runs/bin/scummvm-x`) on your own `DISP`, and stop it yourself
  (`pkill -f 'runs/bin/scummvm-[x]'`, `pkill -f 'Xvf[b] :97 '`).
- `pkill -f 'Xvfb :96'` matches the shell running it (its command line holds
  the pattern) and kills your own command: write `pkill -f 'Xvf[b] :96'`.
- `scummvm-regress.sh` with a relative `REGRESS_OUT` writes the patched
  run's log nowhere (the script changes directory) and reports every
  baseline line as missing: give it an absolute path.
- Bygg hus in HD is 2400x1800, larger than the harness's default X screen
  (1920x1440): the window shrank, the clicks (scaled by 3) missed and the
  login failed. `XVFB_SIZE=2400x1800`.
- No gdb in WSL here (2026-10-15).

## Windows crash dumps

When the Windows build dies without a Lingo error in the log:

- `powershell.exe Get-WinEvent -FilterHashtable @{LogName='Application';
  StartTime=(Get-Date).AddHours(-3)}` (filter on scummvm) gives the
  exception code and module. `0x40000015` in `msvcrt.dll` is `abort()`,
  i.e. a failed `assert` (its message goes to stderr, invisible in a GUI
  program).
- Windows keeps a dump in `C:\Users\<user>\AppData\Local\CrashDumps\scummvm.exe.<pid>.dmp`
  (pid in hex in the event).
- `~/.venvs/mulle/bin/python tools/crashdump.py DUMP` prints the crashing
  thread's stack: functions in `scummvm.exe` (from `x86_64-w64-mingw32-nm -C`
  of the **unstripped** `~/src/scummvm-win/scummvm.exe`, image base
  0x140000000; the dist exe is the stripped copy of the same build, same
  RVAs), other modules, and strings the stack points to. MinGW's assert
  passes UTF-16 strings, so a failed assert shows its expression and file.
  Uses the `minidump` package (installed in the venv 2026-10-13). First use:
  [scummvm](scummvm.md) fix 28.
- Rebuilding `~/src/scummvm-win` overwrites the unstripped exe, so analyse a
  dump before the next Windows build (or keep a copy of the exe).

## Linux and Steam Deck crashes and logs

- Our Linux builds print a backtrace on a crash (`posix-main.cpp`,
  `crashHandler()`, 2026-10-14): `ScummVM crashed, signal 11` and lines like
  `scummvm(+0x22824d)`. Map them with the **unstripped** build that crashed:
  `addr2line -f -C -i -p -e ~/src/scummvm/scummvm 0x22824d ...` (the dev
  build has line numbers; the release build in `~/src/scummvm-linux` gives
  function names only). The package's `scummvm` is the stripped copy, same
  offsets.
- On a Steam Deck, Steam keeps everything the game prints (the launcher's
  and ScummVM's output, the play log, Lingo errors, the crash backtrace) in
  `~/.local/share/Steam/logs/console-linux.txt`, for every run, with times.
  ScummVM's own `~/.cache/scummvm/logs/scummvm.log` holds only the last run
  (rewritten at each start). Search it with `grep -a` (binary bytes).
- `journalctl` on the Deck has the kernel's line for a segfault (`scummvm[pid]:
  segfault at ... in scummvm[offset,...]`: the offset works with addr2line)
  and `coredumpctl list` the crashes; `~/.local/share/Steam/logs/controller.txt`
  says which Steam Input template a game got per controller ("Loaded Config
  for ... App ID <shortcut id>, Controller N: .../templates/...").
- Reaching the Deck from WSL: `ssh -i <copy of %APPDATA%\MulleMeck\deck_key,
  chmod 600> deck@<address>` (the launcher installed that key).
  Before touching the install, check nothing runs there with a bracket
  pattern (`pgrep -f "scummv[m]"`): a plain `pgrep -f` over SSH matches the
  `bash -c` line carrying it.

## Finding what a scene draws

- `--debugflags=screenshot` makes the Director engine save the stage surface
  of every frame as `./dumps/<movie>-MovieScript-<n>.png` (from where
  ScummVM runs; delete afterwards, it writes hundreds). If the stage surface
  is right but the window is wrong, the problem is after rendering; if the
  surface is wrong, it is in the sprites.
- `--debugflags=images --debuglevel=2` logs palette changes and fades (a
  palette summary at level 3); level 7 logs every channel the renderer
  visits; level 8 logs every blit but is far too slow to reach a later
  scene.
- `--debugflags=loading --debuglevel=2` prints every sprite's span
  (`SpriteInfo: startFrame, endFrame`) and behaviours with their parameters
  (`initializerParams`) as frames load: the quickest way to see which
  behaviour sits on a channel and what it waits for. `score_dump.py` shows
  only members and positions.
- A scene that runs too fast or stalls: `--debugflags=events
  --debuglevel=1` logs `Current frame: N, time: ms` every frame (compress
  with awk to the frame changes); level 5 adds `renderFrame() finished in N
  millis`, which exposes blocking fades and transitions (fix 45).
  `--debugflags=lingoexec --debuglevel=3` adds every `go` (`func_goto`) and
  handler call: grep back from a `go` to find the behaviour that sent it.

## Catching problems early

- `tools/lingo_audit.py` (2026-10-13, user's idea): what the scripts call
  vs. what ScummVM implements. Its first run found `the marker` (fix 36) and
  showed what is still stubbed: PrintOMatic (printing the diploma, `08`),
  `charPosToLoc`. Two handlers the scripts call exist nowhere
  (`makeOKToContinue` in the intro's text entry, `nejj`): dead code in the
  original too. Re-run it after merging upstream ScummVM.
- The audit cannot see builtins that exist but treat a type differently
  from Director. Points and rects are the usual suspects (they are lists in
  Lingo): `listp`, `duplicate`, `getPos`... (fixes 19, 33, 40).
- A movie can be started on its own: `tools/harness.sh start
  --start-movie=MOVIES/85.DXR` (folder needed). Bygger bilar's shared
  `prepareMovie` then creates the globals and logs in a default player,
  and destination movies run in their "testing" mode (looping to `start`
  at the end).
- Gamepad actions without a gamepad (none under Xvfb, `/dev/uinput` is
  root-only): `HD=1 PADKEYS=1 tools/harness.sh start ...` runs a configured
  target `mulle-pad` (keymap settings live in the game's config section,
  which `--auto-detect` makes up) whose driving keymap also binds J/L/I/K
  to the left stick and Z/X to A/B. Hold them with
  `xdotool keydown/keyup --window ...`.
- Better since 2026-10-14: a virtual controller through SDL itself. `PAD=1
  tools/harness.sh start ...` (or any flow, e.g. `PAD=1 STOP=garage HD=1
  RUN_DIR=runs/pad tools/flows/bilar-user-save.sh ...`), then
  `tools/harness.sh pad a down` / `pad a up` / `pad leftx 20000` /
  `pad leftx 0` / `pad start down`. Our ScummVM build attaches it when
  `SCUMMVM_TEST_PAD` names a command file ([scummvm](scummvm.md), Testing
  our changes). The stick moves the pointer at ScummVM's virtual-mouse
  speed; for exact spots, move with `harness.sh move` while a pad button is
  held. The play log shows the pad's buttons (`PLAY ... pad ... A down`).
- HD art in the harness: `HD=1 tools/harness.sh start ...` (and
  `HD_SPRITES=true|false` to set `hd_sprites`) uses
  `build/bilar/hd` (a copy of scummvm.ini with `hd_path` in `$RUN_DIR`),
  OpenGL (Mesa; the software renderer has only 16-bit colour) and a 3x
  window; `click`/`move`/`drag` still take game coordinates, `shot` saves
  1920x1440. The junk pile flow scales its own xdotool drag. Use a fresh
  `RUN_DIR`: leftover saves of another player in `runs/latest` make
  `--start-movie` runs fail with `getaProp did not return value`.
  The mount-wheels flow often misses: the wheels land somewhere different
  on the garage floor each time (classic too).
- `scummvm-regress.sh` with flows sometimes reports extra Lingo-test
  warnings (`Label Zoom not found`, a second `No labels set`); a rerun with
  `--no-flows` is clean. Flaky, not a regression.
- Start at a frame with `@`: `--start-movie=MOVIES/92.DXR@58` opens 92 at
  its `JustDoIt` marker (in testing mode a destination's `Dir` takes
  `the frame` as its marker). Frame numbers of markers: `score_dump.py`.
- The user's Windows log (`C:\Users\<user>\AppData\Roaming\ScummVM\Logs\scummvm.log`,
  readable from WSL) now has the play log: grep `PLAY ` for what they did
  before a problem.

## Launcher

- `pygame-ce` 2.5.8 (SDL 2.32.10) in `~/.venvs/mulle` for the launcher
  ([launcher](launcher.md)); its SVG loader draws the Lucide icons
  (`third_party/lucide/`, fetched from `unpkg.com/lucide-static@0.469.0`).
- `import pygame._sdl2.controller` explicitly: `pygame._sdl2` is not loaded
  by `import pygame`.
- Windows has only the Microsoft Store placeholder `python.exe`; do not
  run it (it may open the Store). Packaging will use the embeddable zip.
- `unshield` 1.5.1 (InstallShield cabinets, e.g. Bygg flygplan's) unpacked
  without root into `~/.local/opt/unshield` (`apt-get download unshield
  libunshield0`, `dpkg -x`); run with
  `LD_LIBRARY_PATH=~/.local/opt/unshield/usr/lib/x86_64-linux-gnu`.
- `tools/iso_extract.py` reads Joliet names (needed for the 2000+ discs).
- Windows processes started from WSL cannot follow symlinks WSL made on
  /mnt/c: copy files for Windows-side tests.

## Linux build and package

- `~/src/scummvm-linux`: release build of `~/src/scummvm` for Linux players
  and the Steam Deck: `configure --disable-all-engines --enable-engine=director
  --disable-detection-full --enable-release --disable-imgui --disable-debug`
  and every optional library off (`--disable-libcurl --disable-cloud
  --disable-sdlnet --disable-enet --disable-fluidsynth --disable-fluidlite
  --disable-mad --disable-vorbis --disable-ogg --disable-tremor --disable-flac
  --disable-theoradec --disable-vpx --disable-faad --disable-discord
  --disable-tts --disable-fribidi --disable-gif --disable-jpeg --disable-lua
  --disable-sparkle --disable-readline --disable-gtk --disable-libunity
  --disable-alsa --disable-seq-midi --disable-sndio --disable-timidity
  --disable-sonivox`). Direct needs: SDL2, libpng16, zlib, FreeType,
  libstdc++ (base GLIBCXX_3.4 only), glibc 2.38. The dev build in
  `~/src/scummvm` stays -O0 with debugging.
- `tools/build-linux.sh` packages it (docs/launcher.md); then
  `tools/build-launcher-windows.sh` copies it into the Windows package as
  `linux/` for the Steam Deck copy, without what a Deck does not need
  (`launcher/deck.py` `NOT_ON_DECK_*`: numpy, paramiko and its crypto
  libraries, the upscaler).
- A stand-in Steam Deck for tests: `/usr/sbin/sshd -f CONFIG` as a normal
  user on 127.0.0.1:2222 with its own host key, `AuthorizedKeysFile` a test
  key, `UsePAM no`, `PasswordAuthentication no`, `StrictModes no`,
  `Subsystem sftp internal-sftp`. Windows reaches it as 127.0.0.1:2222
  (WSL's localhost forwarding).
- `tools/build-windows.sh` and `tools/build-launcher-windows.sh` check with
  PowerShell's Get-Process that nothing from `dist\windows\MulleMeck` runs
  (the launcher's pythonw holds its .pyd files; a rebuild then failed
  halfway, 2026-10-14).

## Fonts (`third_party/fonts/`)

Fredoka SemiBold (the pause menu and launcher, OFL) and the Liberation
Serif/Sans/Mono families (2.1.5, SIL OFL, from github.com/liberationfonts;
stand-ins for Times New Roman, Arial, Courier New in Director 7+ games,
[scummvm](scummvm.md) 93). The harness passes this folder as
`--extrapath`; the package builds copy them into `data/`.
