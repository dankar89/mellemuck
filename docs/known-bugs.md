# Known bugs and annoyances

One entry per problem: symptom, where it was reported, cause (script and
handler once found, see `research/lingo-<game>/`), and how the new engine
handles it.

**Proposed policy (not yet confirmed by the user):** real bugs (crashes, lost
saves, softlocks, wrong behaviour) are always fixed. Changes to how the game
plays become settings, so the original behaviour stays available, like the
original/HD art toggle.

## Player and platform problems (all games)

These come from the 1997 Director projector and old Windows, not the game
logic. The new engine replaces the projector, so they go away.

| Symptom | Source | Status |
|---|---|---|
| Does not start or crashes on XP and later; users recommend Windows 98 compatibility mode and 256-colour mode | [SweClockers thread](https://www.sweclockers.com/forum/post/6827273) | Gone with the new engine |
| The game needs the disc image mounted to run | Release README | Gone: the engine reads extracted disc files |
| Swedish Bygger bilar build did not run on 64-bit Windows (community merged it with the Danish 32-bit build) | Release README | Gone with the new engine |

## Bygger bilar

| Symptom | Source | Status |
|---|---|---|
| Likely: progress lost or not saved when installed in a protected folder, because saving rewrites `DATA.CST` inside the game's own folder (`save(castLib "data")`) | Inferred from the scripts; not yet reproduced | New engine keeps saves in the user's profile folder |

## Bygger båtar

| Symptom | Source | Status |
|---|---|---|
| Crash when diving to the plane wreck to fetch an item | [SweClockers thread](https://www.sweclockers.com/forum/post/6509162) (the thread also mixes in another game; unverified) | Find the cause in the scripts when we get to this game |
