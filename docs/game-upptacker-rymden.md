# Upptäck rymden med Mulle Meck (2004)

Looked at 2026-10-15 (user: "do saves then upptäck rymden"). Earlier notes
on the disc in [game-bygger-batar](game-bygger-batar.md) ("The other
discs"). Scripts decompiled with ProjectorRays into `research/lingo-rymden/`
(254 scripts; the movies are Director 8.5, the projector Director 9).

## The disc

- The game is in `ToHD/`: `MulleRymd.exe` (D9 projector), `MulleRymd.ini`
  (`StartupSettings`: next movie `LBMenu`, search paths `@INSTALL\Movies`,
  `@CD\Movies`, saves and `.vst` vList files in `@INSTALL\Data\`, sound
  system `#Bass`, ExitLock), `Movies/` (287 MB), `Sound/` (84 MB), `Data/`
  (`Mulle.vst`), `Xtras/`, empty `Plugins/`. `Movies/` on the disc root has
  `outro_a001v0.swf` (40 MB). SafeDisc (`SECDRV.SYS`), which does not matter
  when the program itself is not run.
- Xtras: Flash Asset/Agent, Shockwave 3D Asset, Havok, Font Asset/Xtra,
  Text Asset/TextXtra, vList, FileIo, FileXtra4, BASS, DSound, MacroMix,
  Mix Services, NetFile/NetLingo/INetURL, SWA*, MPEG 3, Amplitude, Mui
  Dialog, budapi.

## What the movies hold (`tools/director.py`, Xtra members by name)

- **Flash** (55 members in `Graphics.cxt`, 3 in `MulleScripts.cxt`, 10
  `.swf` files): every character animation at the destinations (Fiona, Sam,
  Boris, Daisy, Doris, Erik, Figge, Gordon, Viola, Winkel, GoG, the robot,
  the moon concert, the station interior), the space travel sequences
  (`SpaceTravel_a002v0`-`a010v0`), the rocket, the intro and the outro. The
  scripts drive them: `goToFrame`, `.frame`, `tellTarget`,
  `setFlashProperty`, `frameCount`, `rewind`.
- **Shockwave 3D**: `Houston.dxr` (mission control: a 3D solar system
  navigator, `CSolarSystem`, `CPlanetGfx`, `COrbitGfx`, `CStarrySky`,
  `CNavigator`, `CCamMover`, `C3DMarker`, `CText3D`: how the player picks
  where to fly), `asteroids.cxt` (a 3D minigame with **Havok** physics),
  `Destination.dxr` and `Graphics.cxt` (a `world`/`3D` member each).
- **Text Asset** members for all text (227 in `Language.cxt`), Font Asset
  fonts (10 in `Graphics.cxt`), vector shapes (`parabol.cxt` beams and
  lines, the car's `RoadShape`, `LbMenu`).
- Plain bitmaps: `Graphics.cxt` (975), the planet driving maps
  (`MapEarthCar` 500, Moon, Mars, Mercury, Europa), `car.cxt`: the car
  driving on the planets is 2D.

## Status in our ScummVM

Starts (fallback detection, D8.5 movies) and runs the projector's first
script, which stops on an alert "Ini file missing!": it reads `the
applicationName` (not in ScummVM) to find `MulleRymd.ini`. Text Asset,
Font Asset and the others are "Unimplemented xlib". That part is small.

The size of the job is Flash and Shockwave 3D: ScummVM has neither. Without
Flash no character animates and the space travel shows nothing; without 3D
mission control (choosing a destination) and the asteroids game do not
exist. Parked on the user's word (2026-10-15). Ideas for later:
- Flash: render each `.swf`/Flash member to frames on the player's machine
  (like the HD job; e.g. with Ruffle) and play those as bitmaps, with the
  frame calls the scripts make mapped onto them. Interactive Flash
  (`tellTarget`, variables) needs more.
- 3D: a W3D (Shockwave 3D) reader and a small renderer for what Houston and
  the asteroids game use (models, textures, camera, a few lights), and
  enough of Havok for the asteroids.
