# Mulle Meck remaster

Modernising the late-90s Mulle Meck games (Macromedia Director 6) for modern
PCs and Steam Deck: gamepad, quality of life, widescreen, optional HD art.
Starting with *Bygger bilar*, then *Bygger båtar*.

**Read `docs/handover.md` first** (where the last session stopped and what
comes next), then `docs/README.md`, which indexes everything learned so far:
the Director file format, per-game notes, upscaling findings, decisions and
tooling. Update `docs/handover.md` before a session ends.

## Keep the docs current

When you learn something non-obvious (a file format detail, a game quirk, a
tool gotcha, a decision the user makes, a failed approach and why), write it
into the matching file in `docs/` in the same session. Record decisions with
the date in `docs/decisions.md`. Notes should be useful for remaking the other
Mulle Meck games too, so keep general Director knowledge in
`docs/director-format.md` and game-specific details in `docs/game-*.md`.

## Conventions

- Python tools run with `~/.venvs/mulle/bin/python`; indent with tabs.
- Windows `.exe` tools (Real-ESRGAN, ProjectorRays) run through WSL interop
  from `third_party/`.
- Generated assets go to `build/<game>/`; they are derived from the
  copyrighted games and are never committed or published.
- No passwordless sudo: ask the user to run `! sudo ...` for system packages.
