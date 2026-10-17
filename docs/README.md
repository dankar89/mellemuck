# Mulle Meck remaster: project knowledge

Everything we learn goes here, so it is not lost between sessions and can be
reused for the other Mulle Meck games.

| Document | Contents |
|---|---|
| handover.md | Where the last session stopped, work in progress, next steps (local working notes, not in the repo) |
| decisions.md | Goals, decisions with dates, open questions, prior art (local, not in the repo) |
| [director-format.md](director-format.md) | Director 6 file format: chunks, casts, bitmaps, palettes, score, inks. Shared by all Mulle games |
| [game-bygger-bilar.md](game-bygger-bilar.md) | Disc layout, scenes, assets, inks, scripts, ScummVM status |
| [game-bygger-batar.md](game-bygger-batar.md) | First notes on Bygger båtar; other Mulle titles |
| [game-bygger-hus.md](game-bygger-hus.md) | Bygg hus (Director 8.5): installer files, vList data, status |
| [game-upptacker-rymden.md](game-upptacker-rymden.md) | Upptäck rymden (Director 9): disc, Flash and Shockwave 3D use, status |
| [driving.md](driving.md) | Road driving in Bygger bilar: the roads in the terrain data, the graph, the driver, the smooth car, the F7 view, `tools/roads.py` |
| [launcher.md](launcher.md) | The launcher for all Mulle Meck games: layout, code, input, next steps |
| [upscaling.md](upscaling.md) | HD art: model comparisons, recipes, halo-free transparency |
| [known-bugs.md](known-bugs.md) | Bugs and annoyances in the originals: symptom, cause, fix |
| [scummvm.md](scummvm.md) | Our ScummVM build: every Director 6 fix with its reason, progress, open issues |
| [tooling.md](tooling.md) | Environment, tool locations, scripts, gotchas |

## Starting a new Mulle game

1. Extract the disc: `tools/iso_extract.py IMAGE.iso ~/games/<name>`.
2. Check the Director version (all known Mulle PC games are 6.0).
3. Decompile the scripts with ProjectorRays into `research/lingo-<name>/`.
4. Extract the art: `tools/extract_assets.py ~/games/<name> build/<name>`.
5. Write `docs/game-<name>.md` with what differs from Bygger bilar.
