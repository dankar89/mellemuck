# HD art: upscaling findings

Goal: an optional HD art set (toggle in game, see [decisions](decisions.md)).
Target scale 3x: full screens become 1920x1440. Free, local upscaling on the
RTX 4070 laptop GPU.

## Tools

- Real-ESRGAN ncnn-vulkan, Windows build, run from WSL through interop
  (WSL has no GPU Vulkan driver; the Windows exe uses the GPU directly):
  `third_party/realesrgan-ncnn-vulkan/`. About 6 s per 640x480 image at 4x,
  roughly 10–15 minutes for a whole game per model.
- Extra models in ncnn format from the Upscayl repo
  (`resources/models`): `ultrasharp-4x`, `remacri-4x`, `high-fidelity-4x`,
  `digital-art-4x` (same file size as Real-ESRGAN's anime model, likely the same).
- Comparison script: `tools/upscale-compare.sh`; results in
  `upscale-test/compare/`.

## The source art

Hand-painted watercolour reduced to the fixed Mac system palette, so it is
**heavily dithered** (fine checkerboard noise). This decides everything:

- Sharpening models (UltraSharp, Remacri) amplify the dither into crunchy
  texture.
- Smoothing models (Real-ESRGAN x4plus, anime) remove it but turn foliage
  into smooth blobs.
- A light Gaussian blur first (sigma 0.7 px at original size) removes most of
  the dither so detail-keeping models work. Selective blur did not remove it.

## Best recipe per category (as of 2026-10-12)

| Category | Recipe | Why |
|---|---|---|
| Backgrounds, map tiles | blur 0.7 + `ultrasharp-4x` | keeps watercolour texture and line detail; slight grain remains |
| Painted sprites, car parts | `realesrgan-x4plus` | crisp, clean edges, shading kept |
| Line art (characters) | `realesrgan-x4plus-anime` | very clean outlines |
| 1-bit masks | not upscaled | regenerate from the sprite |

Categories come from the extractor: backgrounds by size, line art vs painted
by **flatness** (share of pixels equal to their right neighbour; line art
~0.7, car parts median 0.28 and never above 0.57; threshold 0.60).

All models run at 4x, then Lanczos down to 3x.

## Transparency without halos (`tools/alpha_upscale.py`)

Sprites use white as their transparent colour. What failed:

1. Upscale, then key out white: light halo, because the model blends the
   white background into the edges.
2. Cut the mask first, upscale colour (with edge colours bled outwards) and
   mask separately: no halo, but staircase edges, because the model treats
   the binary mask like pixel art and does not smooth it. The mask also
   drifts off the outline and nicks it.
3. Alpha from "whiteness" of edge pixels with a linear ramp: smooth, but
   leaves light specks where outline meets white (user spotted them on
   Mulle's shirt). The ramp overestimates alpha for grey mixes.
4. Solving *every* edge-band pixel as a mix of the nearest solid colour and
   white: no specks, but pale paint just inside a dark outline (the chrome on
   fender `20b019v1`) was read as "white mixed with outline", became partly
   transparent, and notched the outline. Found in the full-run QA.

What works:

- Upscale the sprite on its white background (the model draws smooth outlines).
- Scale up the original 1x mask (nearest) and split into *inside* (eroded by
  scale+1 px, alpha 1), *outside* (dilated, alpha 0) and an edge band.
- In the band, **background** is only what connects to the outside through
  near-white pixels (min channel >= 0.85); a dark outline is a wall, so pale
  art inside it stays solid. Background pixels and the one-pixel ring of
  anti-aliased pixels next to them are solved as a mix of the nearest art
  colour F and white: `up = a*F + (1-a)*white`, least squares over RGB;
  colour = F. Fall back to a whiteness ramp when F is nearly white. Alpha
  below 0.04 -> 0. Everything else in the band keeps alpha 1 and its own colour.
- Light-grey pixels the original art has along an edge that touches the
  bitmap border (e.g. the Levande Böcker logo's top row, values 221–238) are
  not background by Director's rules and are kept. They are faithful, and
  invisible on the white screen that logo is shown on.

QA: `tools/qa_check.py BUILD_DIR` compares every HD image, shrunk back, with
its original (median colour difference ~13 because the dither is gone;
outliers are tiny or thin sprites) and writes random/worst contact sheets.

## Which white is transparent: the sprite's ink

See [director-format](director-format.md#inks-how-a-sprite-is-drawn).
`alpha_upscale.py --ink matte|bgtrans|copy`. The extractor's manifest lists
the variants each bitmap needs: the inks the scores use, or for the
runtime-only bitmaps `bgtrans` (see the art convention in
[game-bygger-bilar](game-bygger-bilar.md#assets)). Bygger bilar: 1,583 HD
images for 1,578 bitmaps. The engine picks the variant matching the
sprite's ink at runtime, like the original.

## Full pipeline

```
tools/extract_assets.py ~/games/mulle-bilar build/bilar   # 1,620 PNGs + manifest, ~30 s
tools/upscale_game.py build/bilar                          # HD set in build/bilar/hd/
tools/review_page.py build/bilar                           # build/bilar/review.html
tools/hd_index.py build/bilar                              # hd/index.txt for the engine
```

The engine reads `hd/index.txt` (cast, member, category, `variant=file`)
and finds the folder through `hd_path` in scummvm.ini or as `HD` in the game
folder ([scummvm](scummvm.md) 46). For the Windows package, copy
`build/bilar/hd` to `dist/windows/MulleMeck/games/bygger-bilar/HD` (502 MB,
local only like the game data).

Member numbers follow the movie's cast table: internal casts can start at 2
([director-format](director-format.md)). Until 2026-10-13 the extractor
numbered from 1; the 88 affected images (movies 13, 18, 88, 92) were
renumbered by renaming their cached 4x upscales (`up4x/`) and recomposing,
no GPU run. 10 of them changed variant (their ink usage had been read from
the neighbouring member).

Output names: `hd/<CAST>/<member>_<name>.<variant>.png`, variant `copy`
(opaque), `matte` or `bgtrans`. The manifest's `hd` field maps variant to file.

## Bygg hus (Director 8.5, 2026-10-15)

- `extract_assets.py` reads its `Movies/` (`.dxr`/`.cxt`): 4,033 bitmaps,
  136 million pixels at 1x (Bygger bilar 45), 16-bit mostly (2,995), 8-bit
  446, 32-bit 394, 1-bit 198. The scores' inks come from D7 records
  (`director.py` `score_sprites()`: 48-byte sprite records, the six main
  channels in 288 bytes, read from the score header). 3,519 bitmaps are
  placed only by scripts (Mulle's animations etc.): `bgtrans`, as before.
- Five 2- and 4-bit bitmaps (black full screens, one sea map) are left out:
  the engine draws them from the original.
- No pre-blur for 16/32-bit art (`upscale_game.py`): the blur is for the
  8-bit palette's dither, which this art does not have. Backgrounds with
  ultrasharp-4x and no blur keep the watercolour paper and sharpen the pen
  lines (checked on 55b001v0).
- 32-bit pictures with an alpha channel (173: the world maps' car and boat,
  `mullecar1`, `boat.pict.02` ...): the upscaler gets them over white, and
  their mask is the alpha (`<file>.alpha.png`, manifest `alpha`), whatever
  the ink, so never an opaque `copy` variant. The engine draws such pictures
  by their alpha in classic mode too ([scummvm](scummvm.md) 112).
- Enclosed white is checked at every depth now (it was 8-bit only).
- Speed (RTX 4070 laptop, 2026-10-15): backgrounds 11 min (100 images),
  painted 20 min (3,177), line art a minute, then the CPU compose; about 45
  minutes in all. The set: 3,819 images, 1.4 GB.
- Bitmaps of 8x8 pixels or less are category `speck`, not upscaled: two
  4x4 black/grey dots (62, 63) failed `looks_right()` twice, which stops the
  whole run (it guards against a GPU gone bad) before anything is composed.
- The HD screen is 2400x1800 (3x of 800x600). What scripts paint at run time
  (the house's walls and floors cut from texture sheets, the dirt, the
  photos) has no HD image and is drawn classic, scaled up.

## Open issues

- Real-ESRGAN x4plus raises saturation slightly; colour-match to the original.
- Animation frames: not yet checked for frame-to-frame flicker.
- Tiny images (<64 px) upscale poorly; consider pixel-art scalers or redraws.
- Widescreen: 82 backgrounds need outpainting (not started).

## Paid options considered (prices October 2026, for reference)

Faithful API upscaling (SeedVR2 ~$0.001–0.0025/MP) costs a few dollars per
game. Generative 4K redraws of the 82 key images (Nano Banana Pro $0.24/image)
plus FLUX.2 Pro outpainting (~$0.05–0.10/try) come to roughly $60–125 per
game. The user chose free local upscaling for now.
