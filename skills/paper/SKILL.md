---
name: paper
description: Video effect - a torn-paper wipe turns the real laptop, its screen and your hand into a layered paper-craft diorama (flat colour sheets, thick shadows, stop-motion boil) while a sky, sun, clouds on strings, mountains, hills and trees pop up behind the lid, then it tears back to video. Use when the user types /paper or wants a paper cut-out / papercraft look on their laptop footage.
---

# /paper

A jagged torn-paper edge sweeps across the frame. Behind it the scene is rebuilt as cut paper:
- **The laptop:** a navy lid, a cream screen whose text lines become paper strips, coloured UI chips, key caps, a trackpad and stickers.
- **Your hand:** a two-layer skin-tone sheet that follows it.
- **The scenery:** the sun and clouds drop in on strings, and mountains with snow caps, layered hills and two trees pop up from behind the lid like a pop-up book. Paper puffs rise along the bottom edge.

Every sheet gets a flat colour, a fibre texture, a lit cut edge and a soft drop shadow. The edges boil at 12 fps like stop-motion. Then the paper tears away again. About 2.9 s.

**Needs:** a locked-off clip of a dark laptop on a desk with a plain wall above, hand(s) mostly still on the keyboard,
and a frame from the same shot where the hand is off the laptop (`--ref-time`). Requires `visuals-core`.

## Steps

1. Zero-config first. The laptop, screen, text strips, colour chips, keys and stickers are all detected:
   ```bash
   python paper.py --in clip.mp4 --start 34.4 --dur 2.9 --out preview --preview 0.35,1.0,1.5 --ref-time 30.9
   ```
2. Polish with measurements from `python ../visuals-core/grid.py --in clip.mp4 --t 30.9 --out grid.jpg`
   (use `--crop y0,y1` for the keyboard). Look at the grid image and read the values:
   - `--keyboard-rows rows.json`: a clean full keyboard. One row per keyboard row: `[bottom_y, left_x, right_x, key_height, [unit widths]]`. Use `0.25` for a gap. `examples/rows.json` in the repo is a laptop with a number pad.
   - `--trackpad "x,y;x,y;x,y;x,y"`: the 4 corners.
   - `--cards "[[x0,y0,x1,y1,r],...]"`: app panels that should pop off the screen as white cards.
   - `--hot x0,y0,x1,y1`: text inside this box turns into orange strips. Use it for the user's typed prompt.
   - `--sidebar-x 357` (tinted sidebar sheet), `--webcam x,y`, `--hinge-y`.
3. Render the final:
   ```bash
   python paper.py --in clip.mp4 --start 34.4 --dur 2.9 --out paper.mp4 --ref-time 30.9 --keyboard-rows rows.json \
       --trackpad "266,1702;600,1698;632,1888;243,1892" --cards "[[385,1180,918,1326,16]]" --hot 385,1180,918,1326
   ```
   About 2-3 s per frame. A 3 s effect takes 3-4 minutes, so render it in the background.

## Flags

| flag | default | meaning |
|---|---|---|
| `--ref-time` | required | hand-free frame: the paper laptop is built from it and the hand is keyed against it |
| `--hinge-y` | screen bottom + 60 | where the lid meets the deck |
| `--keyboard-rows` | auto (key bottom edges) | JSON file or inline JSON, see above |
| `--trackpad`, `--cards`, `--hot`, `--sidebar-x`, `--webcam` | off | optional detail layers |
| `--tear-in`, `--tear-out` | 0.10,0.50 / dur-0.60,dur-0.18 | the torn-paper wipes |
| `--thr` | 30 | hand-difference threshold |

Colours live in the `PAL` dict at the top of `paper.py`; change it to restyle the scene (e.g. a sunset sky).

## Check before delivering

- **The hand reads as one clean paper shape.** If it has holes or picks up shadows, adjust `--thr` or choose a better `--ref-time`.
- **No grey specks on the screen.** Any that show are tiny dark UI bits; they are dropped when smaller than about 160 px².
- **The scenery peeks over the lid top.** If the laptop fills the frame, there is no room for it. Reframe the shot or accept a laptop-only diorama.
