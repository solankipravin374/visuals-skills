---
name: visuals-core
description: Shared tools and the shooting guide for the /visuals effect skills (orbit, zooming, words-from-behind, icon-on-palm, zig-zag-graph, paper, thanos-snap, share-comment). Use it to plan or film a laptop-on-a-desk reel for these effects, to measure coordinates (grid.py), to build the laptop mask (mask.py), or to stitch the rendered effect clips together.
---

# visuals-core

The engine under the 8 `/visuals` skills. Each effect skill is a Python script that turns a few seconds of your own
footage into a finished effect clip (MP4 with the original audio). This folder holds what they share:

- `vfx.py`: ffmpeg video I/O, laptop/screen/hand masks, easing and springs, RGBA compositing, sticker text
- `grid.py`: writes a still with a labelled pixel grid, so you can read off coordinates for flags like `--target`
- `mask.py`: builds `laptop_mask.png`, the cut-out every "behind the lid" effect uses, plus a red check overlay

**Requirements:** Python 3.9+, `pip install opencv-python numpy pillow`, and `ffmpeg` on PATH. SVG logos are drawn
with headless Chrome/Edge if installed (or `pip install cairosvg`); PNG always works.

**Keep the folders side by side.** Every effect script imports `../visuals-core/vfx.py`, so install all 9 folders
into the same skills directory.

## The workflow (same for every effect)

1. **Find the moment.** Ask the user for the clip and the rough time of each beat, or scrub it with ffmpeg stills.
   Times are in seconds of the source clip.
2. **Measure.** Run `grid.py` on a still from the beat and read coordinates off the grid. Look at the image; do not guess.
   ```bash
   python <skills>/visuals-core/grid.py --in clip.mp4 --t 30.9 --out grid.jpg
   python <skills>/visuals-core/mask.py --in clip.mp4 --t 30.9 --out laptop_mask.png   # hand-free frame
   ```
   Open `laptop_mask_check.jpg`: the red area must cover the whole laptop and nothing else. If it spills onto a dark
   table, raise `--min-y` or lower `--v-max`.
3. **Preview.** Every effect takes `--preview 0.3,1.0,2.0` (effect-local seconds) and writes PNG stills in seconds
   instead of a video. Look at them and adjust flags.
4. **Render.** Drop `--preview`, set `--out effect.mp4`. Output is 1080x1920 30 fps H.264 + the clip's audio.
5. **Stitch.** Concatenate in your editor, or:
   ```bash
   printf "file 'orbit.mp4'\nfile 'zoom.mp4'\n" > list.txt
   ffmpeg -f concat -safe 0 -i list.txt -c copy reel.mp4
   ```

## Flags every effect has

| flag | meaning |
|---|---|
| `--in`, `--start`, `--dur`, `--out` | source clip, effect start (s), effect length (s), output |
| `--size 1080x1920`, `--fps 30` | output format (portrait by default) |
| `--mask laptop_mask.png` | the laptop cut-out (auto-detected if omitted) |
| `--preview t1,t2,...` | write stills at these effect-local times instead of rendering |
| `--gamma 0.86` | brighten dark footage (lifts the mids; 1.0 = off) |
| `--wb 1.045,0.995,1` | white-balance gains B,G,R (this example cools a yellow wall) |
| `--no-audio` | do not copy the source audio |

## Shooting guide (what makes these effects possible)

1. **Locked-off camera.** Phone on a tripod, vertical, never touched. The hand and lid tricks key against a still frame.
2. **Framing.** Laptop in the lower ~55% of the frame, plain wall above it: orbit, words, graph and the sticker live there.
3. **Even front light**, exposure and focus locked (long-press AE/AF lock). 4K if you can: `/zooming` dives deeper.
4. **Big screen text.** Zoom the app in (Ctrl/Cmd `+`), dark or light mode, notifications off.
5. **Hand-free moments.** Hold still with hands off the laptop for 2-3 s now and then. Those frames are the
   `--ref-time` the hand effects key against.
6. **Clean plate** for `/thanos-snap`: after the take, lift the laptop out and record 5 s of the empty desk without
   moving the phone.
7. Per beat: say the line, type the slash command slowly, Enter, then do the action:

| effect | what to do on camera |
|---|---|
| `/orbit` | hands off the keyboard, hold still 3-4 s |
| `/zooming` | hands still 4 s (choose a target on screen: an icon, a mascot's eye) |
| `/words-from-behind` | hands still 3 s |
| `/icon-on-palm` | raise an open palm, flat and facing up, beside the laptop; hold 4 s, move it only slightly |
| `/zig-zag-graph` | one index finger draws a rising zig-zag left to right above the laptop (~2 s) |
| `/paper` | hands on the keyboard, mostly still, 3-4 s |
| `/thanos-snap` | hand up beside the laptop, one clear snap, hold 1 s, then hands out of frame |
| `/share-comment` | 4 s of the empty desk (or use the clean plate as the background) |

Full guide with the reasons behind each rule: `docs/SHOOTING.md` in the repository.
