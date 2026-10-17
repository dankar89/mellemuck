# Road driving (Bygger bilar's map)

The user, 2026-10-14: "driving is very annoying ... what if we made a road
network, where we could like click on the road and mulle drove there
following the road? ... Just move the cursor or stick in the direction you
wanna go, and mulle moves there, along the roads"; "we would have to build a
tool for finding the roads though, and a debug view to show the roads in game
to find errors". Chosen (decisions.md): both ways (a direction follows the
roads, a click drives there), the game's own speed, fuel, terrain and
destinations kept, the car's own art turned smoothly.

Built in our ScummVM (`engines/director/roads.cpp/.h`, [scummvm](scummvm.md)
72) and drawn by `tools/roads.py`.

## The roads in the game's data

- Each driving map (28 in world "Da Hood", ids 1-30 without 25 and 29) has a
  terrain grid: two text members in `CDDATA.CXT`, `30tNNNv0` and
  `30tNNNv0-2`, 316 x 99 bytes each, together 316 x 198 cells of 2 x 2
  pixels; cell (x, y) covers stage pixels (4 + 2x, 4 + 2y). The game reads
  them with `charToNum(char ...)` (`Wheels.quickCheck`).
- A byte: below 240 drivable, 240 blocked. High nibble the ground (0 road,
  1 holes: needs durability, 2 mud: needs grip), low nibble the height (hills:
  steep ones need strength).
- **The drivable cells are exactly the painted roads** (also yards and
  driveways). A road can look painted but be blocked: map 7's lower road
  is not connected to the upper one (cells 102-120 blocked); it is reached
  from map 13.
- The world (`worldDa HoodDB`): `#map` is a grid of map ids, rows top to
  bottom (6 x 5), start map point(4, 3) = 16 at (300, 250). Row 5 repeats
  maps (26, 26, 27, 28, 28, 30).
- Crossing a map edge keeps the other coordinate (the car arrives at x 12 or
  631, y 12 or 395). Most roads line up within a few cells at the edges; some
  do not (12 -> 18: 26 cells apart; 22 -> 28; 1 -> 7 half), and there the
  map has a `#Correct` object (object 31) by the edge that puts the arriving
  car on the road (`Dir.goThroughObjects`, within its radius, 80 by
  default). So the road driver needs no links between maps: it finds the car
  on the new map's roads.
- Objects on a map (`mapNDB` `#objects`): destinations (`#dest`,
  `#rdest`: random), `#custom` ones (cows, goats, ferry, gas, bridges, hills,
  stop signs, teleports) and `#Correct`. A destination starts when the car
  comes near (its `#InnerRadius`); for the last metres the game drives the
  car itself (`programControl`).

## The graph (`RoadGraph::build`, `tools/roads.py`)

1. Drivable mask; the map's edge cells repeated 12 cells outwards, so roads
   leaving the map keep their centre line to the edge.
2. Zhang-Suen thinning to one-cell lines, then "tidy": drop cells whose
   neighbours are one run of three or more (staircase corners, 2 x 2 blocks).
3. Nodes: cells with one run of neighbours (ends) or three or more
   (junctions; touching junction cells are one node). Each node also owns the
   line cells round it; what is left falls apart into pieces of line, each an
   edge between the nodes it touches (path: shortest way through the piece).
   Nodes whose cells touch get a direct edge. (A walking tracer lost a road
   on map 14; pieces without the owned cells still met diagonally beside a
   junction: both fixed this way.)
4. Prune, until nothing changes: loops under 30 cells (round a speck in the
   road), edges under 7 cells (one junction traced as two nodes: joined at
   the middle), dead ends under 14 cells (the road's ragged edge), not
   those within 6 cells of the map's edge (exits); then join the two edges
   of a node left with two (not loops).
5. Stage pixels: cell centre (5 + 2x, 5 + 2y), each point averaged with up
   to 4 cells either side (the ends stay on their nodes): the cells' stair
   steps gone, the aim moves along a smooth line (the user: "we can smooth
   the movement along the path a bit").

Result: 1-14 nodes per map, 8 ms per map in the -O0 build, made when the map
is first driven and kept by the terrain's hash. The engine logs
`RoadDriver: map <hash>: N nodes, M edges, E ends (X exits)`; the same counts
as `tools/roads.py` on maps 11, 16, 17 and 23 (both follow the same rules).

## The driver (`RoadDriver`)

It holds the game's keys, as our gamepad driving did ([scummvm](scummvm.md)
48): Left/Right until the car points at the aim (within 0.6 of a heading),
Up for gas, Down to brake. So speed, fuel, hills, holes, mud, crashes, map
changes and destinations are the game's own.

- **Direction** (left stick; the mouse held on the map: towards the
  pointer; A alone: the way the car points). The car's edge and the way
  along it are chosen by the direction; at the next junction the branch
  whose first 24 px point nearest the direction. The branch is chosen anew
  while the junction is over 30 px away, kept nearer (it would flip as the
  car turns), unless the direction changes a lot. Map exits: the aim goes
  on past the edge, the game changes maps. Dead ends: it stops there.
- **Turning round**: only when the direction points back against the way
  (dot < -0.5) *and* the player moved it since the way was chosen (dot with
  that direction < 0.9). The first rule alone turned the car in a road that
  bends back; with "moved more than 90 degrees" a wrong turn could not be
  undone (seen: map 17's junction, the stick passing "right" on its way to
  "down-right" took the road up).
- **Click** anywhere on the map (press and release within 0.4 s, under 12
  px apart; user, 2026-10-14: "you should be able to click anywhere and
  have the car drive to the closest road point. otherwise its too hard to
  go to drive to the edge and to another screen or to any house"). Where
  to (`clickTarget()`), in this order:
  1. Within 40 px of the map's edge, with a road leaving on that side within
     160 px: off the map through it. In the next map the car goes on 48 px
     along the road and stops (the user: "when clicking on the edge and
     transitioning to another screen, the car keeps moving ... It should
     move a little bit into the other screen, just so that we can easily
     move back"). A route that leaves the map by chance brakes there.
  2. On a road (within 12 px): that place.
  3. Within 70 px of a place to go (Dir's `objects`: `#dest`, `#rdest`, and
     `#custom` Gas, Racing, Ferry; their `myLoc`): the road point nearest
     the place, so the game starts it (a house: its destination).
  4. Else the nearest road point, however far.
  Then Dijkstra over the nodes from both ends of the car's edge; the car
  follows the plan and stops there ("there": stopped within 8 px; closer it
  overshot, braked, and inched back and forth). Off the plan (a hit, a
  ferry): planned again.
- **Aim**: 16 px + 2.5 x the speed (pixels a frame) ahead along the plan,
  at most 60. Gas while the aim is within 2.5 headings; brake when it is 4
  or more off at speed, and in time for the end: stopping distance from the
  car's `#break` (`quickCarProps`). At speed 0 the car turns on the spot
  first.
- **Stop**: letting go (stick, mouse, A) or B brakes until the car stands.
  Releasing Up alone keeps the speed in this game (cruise).
- **From the brake to the gas**: Down is let go first, Up pressed only once
  the car's `acceleration` is back to 0. The game's idle handler
  (`KeyHandlers.myidle`) handles Up before Down's release, and that release
  sets the acceleration to 0: with both at once Up stayed held and the car
  stood still (it looked "stuck" short of a clicked spot).
- **Stuck** (gas, speed 0, not moving for 1.5 s: a hill too steep for the
  car): it lets go of the gas until the direction changes.
- The keyboard's arrows are the player's own driving (they cancel ours);
  the right button still brakes (the game's own). Presses below the map
  (the dashboard, the toolbox menu) go to the game. A press the driver took
  is hidden from Lingo's `the mouseDown` (`lingo-the.cpp`), or the game's
  own mouse steering would start too.
- scummvm.ini `road_driving=false`: the stick points the car as before (48).

## The car turned smoothly (HD)

The car's sprite shows member `CarPic` + heading + (2 + slope) x 16
(`DisplayCar.display`): 16 headings x 5 slopes of tiny pre-rendered cars
(about 20 x 28 px). On a winding road the car switches between two headings
all the time. With HD: `RoadDriver::watchCar` keeps the car's heading
(where it went over the last 4 frames when moving, else its fine
`internalDirection`; at most 1.2 headings of change a frame), and
`HDArt::carImage` draws the HD picture of the nearest heading turned by the
rest (at most 11 degrees), round the registration point, bilinear. The area
round the car (12 stage px) is composed with it, also where it was last
drawn. The car's HD pictures lose the light grey their edges have
(`carClean`: light, colourless pixels within 3 HD pixels of the outside; the
originals' anti-aliasing towards white, which background transparent ink
keeps and which showed as specks over the map). Tyres and a grey part on the
roof stay (they are the art).

## The car glides (HD)

The game moves the car 12 times a second, 6-13 px at a time (18-40 on the
3x screen). HD draws about every 10-20 ms, so `HDArt::updateGlide()` draws
the car moving from where it was shown to the game's newest place over one
game frame's time (measured between the game's moves), and the heading
likewise; jumps over 40 px (another map) are not glided. The car is shown up
to one game frame (83 ms) late; the game's own logic uses its real place.
Measured headless: drawn every ~21 ms, ~1 px a step, instead of 5 px every
110 ms. Debug: `--debugflags=images --debuglevel=5` logs each drawn place.

## The boat (Bygger båtar's sea)

The same smooth picture and glide, and the stick steering, for the boat
([scummvm](scummvm.md) 76): the stick points the boat; a motor or rowing
boat goes while it points that way (Up held) and a motor boat's throttle
comes down to 0 when the stick is let go; a sail boat is steered (A and B
work the sheet). No roads at sea. The sail turns with the hull.

## Debug view and tools

- **F7** while driving (HD): the graph over the map (white lines, red
  junctions, yellow dead ends, blue exits), the car's plan (green), its aim
  (magenta) and its place on the road (cyan).
- `tools/roads.py GAME_DIR OUT_DIR [--map N ...] [--scale S]`: per map
  `map-NNN.png` (road cells tinted: red road, orange holes, purple mud; the
  graph as in F7), `world.png` (all maps in the world's grid) and
  `roads.json`. Generated from the disc: `build/bilar/roads/`, never shared.
- Logs (`--debugflags=events`): level 1 the graph per map, clicks, "there",
  "stuck"; level 2 turning round; level 3 every steering change and the
  graph's nodes and edges.
- Harness: `tools/harness.sh start --start-movie=MOVIES/05.DXR` (HD=1 PAD=1)
  drives map 16 at once; `pad leftx 30000` / `pad lefty ...` the stick,
  `click`, `press X Y` + `move` + `release` a held mouse, `keydown Up` /
  `keyup Up` the keyboard, `key F7`.

## Tested (2026-10-14, harness, HD, virtual pad)

Stick right along map 16's road to map 17 and stop on release; a wrong turn
at map 17's junction undone by pointing down; down onto map 23; click on
map 23's far road (2 steps) and on Figge Ferrum's driveway on map 16 (two
junctions, 4 steps; destination 92 started); a click after coming back from
a destination; the mouse held on the map (drives towards it, crosses to map
17, stops on release); A alone; B; the keyboard arrows; the toolbox menu
opens and closes and driving goes on after; the car turned smoothly.

Then (after the user's first tries): clicks by the right and left edges
(off the map, 48 px into the next, stop; and back), a click near a road
(drives to the nearest road point, "there"), a click on Figge Ferrum's
house (to its yard), the glide (above).

## Open

- The user tried an early build (edge clicks made the car roll on); the
  fixes above are not yet tried by the user, nor on the Steam Deck.
- The speed limits and brake points are first guesses; tune from play.
- Routes stay on the map the car is on; a click on a road part reached only
  through another map does nothing.
- Classic (non-HD) mode has no debug view and no smooth car.
