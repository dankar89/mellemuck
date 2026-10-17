# The launcher

One launcher for all Mulle Meck games: it finds the player's game files,
starts our ScummVM build, makes the HD art on their machine and (planned)
copies everything to a Steam Deck. Decisions in [decisions](decisions.md)
(2026-10-14): Python with pygame-ce, no game engine; pictures from the
player's own disc; GPU upscaling only, with progress; no clutter, icons
instead of text, nothing that needs reading to understand.

## Running it

- Players: `Mulle Meck.exe` in the package (`dist/windows/MulleMeck`),
  built by `tools/build-launcher-windows.sh`: Python's embeddable 3.12
  distribution in `runtime/` with pygame-ce, numpy, Pillow and paramiko from
  win_amd64 wheels (tests and pygame's examples removed; no scipy since
  2026-10-14: `tools/morph.py` does the HD tools' mask operations with numpy,
  pixel for pixel the same, user: "this is getting big"); the launcher, the HD tools
  and the icons in `runtime/app/` (on the path through `python312._pth`, as
  the embedded Python ignores PYTHONPATH). `Mulle Meck.exe` is a small
  MinGW program (`launcher/starter.c`, icon `launcher/icon.ico`) that runs
  `runtime\pythonw.exe -m launcher --root <its folder>` without a console
  and passes its arguments on; output goes to `launcher.log`. No Python on
  the player's machine; the embedded one has no tkinter, so the folder
  dialog on Windows is PowerShell's `FolderBrowserDialog`.
- Straight into a game, e.g. for a shortcut: `"Mulle Meck.exe" --play
  bygger-bilar` (no separate exe per game; the user asked, we agreed one is
  enough).
- Fullscreen by default, games and launcher alike: the launcher writes
  `fullscreen=true` into `scummvm.ini` when it is missing and follows that
  setting itself, so the pause menu's Helskärm / Visa i fönster decides
  both. `--window` forces a window.
- Developing: `~/.venvs/mulle/bin/python -m launcher --root dist/windows/MulleMeck --window`
  (WSLg window; mouse and keyboard only, controllers do not reach WSL).
  From Windows: `launcher-preview-wsl.bat` in the project root.
- Testing the Windows package from WSL without opening a window:
  `SDL_VIDEODRIVER=dummy WSLENV=SDL_VIDEODRIVER/u ./runtime/python.exe -m
  launcher --root "$(wslpath -w .)" --shot "...\\x.png"` (or the same with
  `./Mulle\ Meck.exe`).
- Look without a display: `SDL_VIDEODRIVER=dummy ... -m launcher --root ...
  --shot out.png [--focus N] [--input pad|keyboard|mouse] [--ask-quit]`
  renders one screen (after the library scan) and quits.
- `--size 1280x800` (the Steam Deck's screen) with `--window`; F11 toggles
  fullscreen.

## The folder it runs in (ROOT)

```
ROOT/
  games/<id>/          the player's disc files (copied in by the launcher)
  games/<id>/HD/       HD art made on this machine (index.txt + PNGs)
  cache/<id>/          cover and backdrop pictures (cover.png, cover-hd.png ...)
  saves/  scummvm.ini  data/ (Fredoka)  scummvm(.exe)
```

Game ids: `bygger-bilar`, `bygger-batar`, `bygger-flygplan`, `bygger-hus`,
`upptacker-rymden` (`launcher/catalog.py`, with the file that identifies each
disc, where its Director files are, the card and backdrop bitmaps, and
whether our ScummVM plays it). Only Bygger bilar is playable now; the others
show an hourglass. All five discs are in the Windows package folder
([game-bygger-batar](game-bygger-batar.md)); the pictures
of the later ones are 16/32-bit (decoded by `bitmap_rgb()`).

## Games

Bygger bilar and (since 2026-10-14) Bygger båtar are playable, both with the
HD button; Bygg hus is playable (2026-10-14 night), with the HD button since
2026-10-15 (`hd_minutes` 30-50, about 1.5 GB; the package needs a rebuild
for it); Upptäck rymden shows an hourglass; Bygg flygplan is hidden. A game whose HD art the HD job cannot make has no HD button
(`GameInfo.hd`). The Steam Deck button is for the whole launcher, not one
game: one copy sends every game found here (user asked, 2026-10-14).

### Games with an installer (Bygg hus)

Bygg hus's program `MulleHus.exe` and player database `Data.cst` are only
inside `Setup.exe` on its disc. `GameInfo.installer` names them;
`discs.install()` unpacks them into `games/bygger-hus/` with
`tools/msi_extract.py` (standard library only, 0.15 s): once, while the game
is brought in, and before playing if they are missing (a copy brought in
before this existed). Files already there, also one folder down
(`Data/Data.cst`, as an installed copy has it), are left alone; ScummVM finds
`Data.cst` in the root or in `Data/`.

What a player may point at:
- the disc, an ISO or zip of it: recognised by `Movies/HouseData.cxt`, the
  two files unpacked;
- a folder with an installed copy and the disc's `Movies/` together: used as
  it is;
- an installed copy alone (`C:\Program Files\Levande Böcker\Bygg hus med
  Mulle Meck\`: `MulleHus.exe`, `Data\Data.cst`, `Help\`, `Xtras\`, no
  `Movies/`): not a game, the movies are only on the disc. (The marker was
  `MulleHus_hjalp.htm` before, which an installed copy has too.) Its
  `Data\Data.cst` holds the player's old players and progress: carrying it
  over is possible, not built.

## Code (`launcher/`)

- `catalog.py`: the games. Bygger bilar's cover is cast `10`, member
  `10b006v0` (the "Bygg bilar med MULLE MECK" title screen); its backdrop
  `10b004v0` (Mulle and Buffa at sunset).
- `library.py`: per game, found or not (the marker file, any case), HD
  progress (the share of `HD/index.txt`'s files on disk), pictures (the HD
  file if there, else decoded from the disc with `tools/director.py`;
  cached). Runs in a thread at start (9 s from WSL on the Windows package,
  most of it checking 1,583 HD files over /mnt/c).
- `ui.py`: the screen. Carousel (focused card 47 % of the height, 4:3,
  neighbours 70 % and dimmed, eased), blurred darkened backdrop of the
  focused game (cross-fade), its name, round buttons, one word for the
  button in use, position dots, a quit button in the corner.
  - Buttons: found and playable: play (yellow, main) and HD. Not found:
    find files (no need to point at a game already there). Not playable
    yet: a grey hourglass. See Navigation below.
  - Still there? Checked at start, when the window gets the focus back and
    before playing; a game whose files went shows the find-files button.
  - Find files: the system's folder dialog (tkinter on Windows; zenity or
    kdialog on Linux). The folder (or one below it) must hold the game's
    marker file; it is copied into `games/<id>/` with a progress ring on
    the card, so a Steam Deck copy can take it from there. A wrong folder
    shows a red cross.
  - Play: `scummvm(.exe)` next to the launcher (or `MULLE_SCUMMVM`, or the
    Linux build in `~/src/scummvm` when developing) with the same options as
    the package's .bat, absolute paths.
- Style as the pause menu (game-menu.cpp): Fredoka SemiBold, paper
  `#FFF3D6`, yellow `#FFC531`, ink `#4A2E17`; anti-aliased shapes drawn 4x
  with PIL and scaled down; icons from Lucide (`third_party/lucide/`, ISC
  licence), recoloured SVGs (`pygame.image.load_sized_svg`).

## Finding a game (`launcher/discs.py`)

"Hitta spelet" first looks by itself: drives (C: skipped; discs, mounted
images, USB sticks; on Linux /media, /run/media, /mnt), then Downloads,
Desktop and Documents (also under OneDrive), two folders deep, each place
walked once. Only if that finds nothing does the file dialog open, titled
with what it takes ("en skivavbild (.iso), en zip-fil eller en fil från
skivan eller mappen", filter "Mulle Meck-spel (.iso, .zip, .exe)"); the
button's word has a line "iso · zip · cd · mapp" under it (the user: make
the formats clear).

- Recognised by the game's marker file anywhere up to two folders down:
  folders and discs, ISO images (read without unpacking, Joliet names), zips
  with the disc's files, and zips with an ISO inside. A picked file: its folder or the one above, including
  images next to it. Plain images before zips.
- A disc of another game goes to that game (and the carousel moves to it).
- Brought in through `games/<id>.incoming`, then renamed, so a stop leaves
  no half game that looks found; HD art already made for it is kept.
- Measured on Windows: the search finds all four of the user's games in
  2.5 s (27 s from WSL); unpacking an image runs at disk speed.
- Bygg flygplan is hidden (`hidden=True` in catalog.py, user: "lets hide
  bygger flygplan until we have figured out how to remaster it"); its disc
  is not recognised either.

## Copy to Steam Deck (`launcher/deck.py`, `launcher/deckpanel.py`)

A button with a gamepad icon next to the quit button (only on a PC with the
Linux package: `linux/` in the Windows package, or the Linux package itself;
not on a Deck). Its panel works in steps (user, 2026-10-14: verify the
connection before choosing where, browse the Deck):

1. **Connect**: the Deck's address (default `steamdeck`, `.local` tried
   too; an IP works) and, the first time, the `deck` user's password, then
   Anslut. A password login installs the launcher's own SSH key on the Deck
   (RSA, in the user's settings folder: `%APPDATA%\MulleMeck\deck_key` or
   `~/.config/mulle-meck/deck_key`, never in the package, which may be
   shared), as the user's own deck_push script does with ssh-copy-id; with
   that key the panel connects by itself next time.
2. **Choose where**: places with their free space (home, `~/Games`, mounted
   microSD cards and USB drives under /run/media), the current folder with
   ".." and its folders (scrolling list), "Mulle Meck hamnar i ..." (a
   `Mulle Meck` folder there, or the folder itself if it is one) and
   "Behövs ... · ledigt ..." (red if it does not fit). Kopiera hit / Tillbaka.
   The last place is remembered (`launcher.json`, with the address; never
   the password).
3. **Copy**: one tar stream of what is new or changed. The saves only when
   the Deck has no saves at all, the settings only when it has none (user,
   2026-10-14: "will it overwrite all my saves if I copy it over to the deck
   again?": no; and since then a PC-only slot no longer turns up among the
   Deck's own either). Not what a Deck does not need (`NOT_ON_DECK_LIBS`,
   `NOT_ON_DECK_DIRS`: numpy, paramiko and its crypto libraries, the
   upscaler, about 180 MB). The package's own folders on the Deck
   (`runtime/`, `app/`) are made to match the build: what is not in it any
   more is deleted (`PACKAGE_DIRS`; Python's `__pycache__` stays; games,
   pictures, saves and settings are never touched). The user's Deck went
   from 154 to 95 MB of runtime that way (2026-10-14). Then **Steam's library**: the user's
   the user's own `steam_shortcut.py` (`launcher/steam_shortcut.py`), run
   on the Deck: the Steam client's own API on its debugging port (Decky
   Loader turns it on), found by name so it is updated rather than added
   twice, with artwork. Without the port, SteamOS's `steamos-add-to-steam`
   (first copy only); failing that the done screen says how to add it by
   hand. Also a desktop menu entry.
4. **Artwork** (`launcher/steamart.py`): made on the PC from the first
   playable game's own pictures (HD when made), sent along in
   `cache/steam/`: `library_600x900.png` (the title card on the blurred
   backdrop), `header_920x430.png`, `main_1232x706.png` (the backdrop).

- Text fields edit properly: cursor with the arrows, Home/End, Ctrl+arrows
  by words, a mouse click; Backspace/Delete (Ctrl: a word); Ctrl+V.
- Errors, short: "Hittar inte Steam Deck", the SSH steps when the Deck
  answers but SSH is off (`passwd`, then `sudo systemctl enable --now sshd`,
  in Konsole, in desktop mode), "Fel lösenord", "Skriv Steam Decks
  lösenord" (no key yet).
- The panel can be closed during a copy; its ring then shows on the corner
  button.
- Tested against a local sshd in WSL on port 2222 with a key
  (`MULLE_DECK_PORT`, `MULLE_DECK_USER`, `MULLE_DECK_KEY`; a non-root sshd
  logs in only as its own user and only with keys, so the password login
  and the key install were not run): connect, places, browsing into a
  folder, the copy, the Steam step falling back to "by hand" (no Steam
  there); from the packaged Windows Python too (the copied launcher then
  starts on the Linux side). On the user's Deck (2026-10-14): the copy, the
  Steam entry by the debugging port, the launcher and the game in game mode.
- On the Deck the launcher has no HD button (`can_make_hd()`: numpy and the
  upscaler are not there); the game shows the HD art copied from the PC.
- Steam's "Exit game" ends the launcher with a signal: it stops the HD job
  and exits quietly (no traceback); ScummVM saves and quits on the same
  signal ([scummvm](scummvm.md) 61).
- A game's output on the Deck, crashes included, is in Steam's
  `console-linux.txt` ([tooling](tooling.md), Linux and Steam Deck crashes).

## The Linux package (`tools/build-linux.sh`, `dist/linux/MulleMeck`)

For Linux PCs and the Steam Deck (265 MB; what a Deck gets of it, 109 MB):
`scummvm` (release build, Director
only, from `~/src/scummvm-linux`; needs only the system's SDL2, libpng, zlib,
FreeType and glibc 2.38+, all on SteamOS), `runtime/` (python-build-standalone
3.12.10, stripped, with pygame-ce, numpy, Pillow, paramiko; symlinks
replaced by copies, as the Windows launcher reads it from the Windows drive),
`app/` (launcher, HD tools, icons, the Linux `realesrgan-ncnn-vulkan` and the
three models), `data/`, and the start script `Mulle Meck`. Left out of the
runtime: Python's headers, man pages and terminfo, Tcl/Tk, lib2to3,
pydoc_data, and `libpython3.12.so`, a second copy of the `.so.1.0` that
python3 runs with (symlinks become copies), 63 MB in all.

Sizes (2026-10-14, without games and HD art): the Windows package 310 MB
(runtime 173, `linux/` 109, scummvm.exe 27), down from about 620 MB; the
Linux package 265 MB (375 before); a Deck's install 109 MB (375). The HD tools pick
the Linux upscaler on Linux and the Windows one on Windows and in WSL
(`alpha_upscale.esrgan_binary()`).

## The HD job (`launcher/hdjob.py`)

The HD button starts `python -m launcher.hdjob GAME_DIR WORK_DIR` in the
background (`HDJob` in ui.py; the console `python.exe` without a window, so
its lines come through a pipe). It writes the full `HD/index.txt` first, then
each image as soon as its upscale is ready (temporary name, renamed), so the
game uses what is done and draws the rest from the original art. Lines:
`PHASE extract|upscale`, `PROGRESS done total`, `DONE`, `ERROR text`. Work
files (originals, 4x cache; 818 MB for Bygger bilar) in `cache/<id>/hd-work`,
deleted when complete; they make a stopped job resume where it was.

- The button has four states (2026-10-14, the user: "there is no
  indication that it will generate it and that it might take a while",
  "what is the purpose of the hd-bilder button once hd images are
  generated? should it become a toggle?", "the image generation progress
  number should be shown on the toggle/button"):
  - not made: "Gör HD-bilder". Pressing opens a question first
    (`hdpanel.py`, same look and controls as the Steam Deck panel): what it
    does, about how long (`GameInfo.hd_minutes`: Bygger båtar took 27 min
    on the user's RTX 4070 laptop, 2026-10-14, so 25-40; Bygger bilar,
    with 61 % of the pixels, 15-30), that it
    can be paused and that finished images show in the game at once;
    Starta / Inte nu.
  - making: the percentage inside a ring that fills, a turning arc;
    "Gör HD-bilder 35 %". Pressing pauses (kills the job and the upscaler:
    `taskkill /T` on Windows, the process group elsewhere).
  - paused: a pause badge, "HD-bilder pausade 35 %"; pressing goes on.
  - made: an on/off switch for the game's HD art, "HD på" / "HD av" (the
    button greyed when off), kept in `launcher.json` `hd_off` and written
    to `scummvm.ini` `[scummvm] hd_art` before each start. F6 in the game
    switches it too (hd.cpp writes the same key); after the game the
    launcher takes that back into `hd_off`, so neither undoes the other.
  It is not a switch from the start: before the art is made there is
  nothing to switch to. A red cross if the job failed (no Vulkan graphics
  card, a driver reset).
- Playing while it runs works: Play pauses the job (both want the graphics
  card; a game and the upscaler together risk the driver reset of
  docs/upscaling.md) and resumes it when the game ends; the images done so
  far show in the game. Quitting the launcher stops it; the next press
  carries on.
- `MULLE_HD_LIMIT=N` limits a job to N bitmaps (tests).
- Tested: 12 images from the UI on Linux (start, extract, progress, done,
  work folder removed), pause at 35 % and resume to done (45 images, 68 s),
  6 images with the packaged Python on Windows (33 s), images equal to the
  dev pipeline's within GPU noise.
- The pipeline changes for it: `upscale_game.run_recipe(..., on_cached)`,
  `compose()` per entry, `save_atomic()`, `hd_rel()`;
  `extract_assets.extract()`; `alpha_upscale` without console windows and
  without PowerShell outside Windows.
- Packaged: `realesrgan-ncnn-vulkan.exe` (MIT), `vcomp140.dll` and the three
  models of our recipe (79 MB): `realesrgan-x4plus` and
  `realesrgan-x4plus-anime` (BSD-3, Real-ESRGAN), `ultrasharp-4x`
  (4x-UltraSharp by Kim2091, from Upscayl's model set; as far as we know
  CC BY-NC-SA 4.0, to check before sharing), plus `tools/data` (palettes).

## Starting a game on a Steam Deck

`start_game()` starts ScummVM with `SDL_ENABLE_SCREEN_KEYBOARD=0` (SteamOS's
SDL opened Steam's keyboard as soon as the game's window was there, and the
keyboard took the controller) and sets `scummvm.ini` `screen_keyboard=steam`
on SteamOS (`none` elsewhere): a click on a name field opens the keyboard
([scummvm](scummvm.md) 73). The launcher's own HD button is a switch on
the Deck whenever the game has HD art (`hd_switch()`), since the Deck cannot
make it.

## Navigation

No shortcuts (the user: buttons should be reached by navigating, also the
close button). Three rows: the quit button (top corner), the games, the
buttons under the focused game. Up/down change row, left/right move in a row
(in the games row: another game), A/Enter presses, B/Escape goes back to the
games; the mouse moves the focus and clicks. Focus is a white outline (a
frame round the card, a ring round a button, outside the HD progress ring).
The quit button quits at once: a quit question was tried and dropped ("just
ugly and confusing"); B and Escape never quit.

## Next

1. Text fields with a controller only (an on-screen keyboard), if wanted.
