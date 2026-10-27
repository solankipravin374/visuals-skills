# Shooting guide for the /visuals effects

Each effect needs something specific from the footage. Get these right and every effect works with its defaults.

## Setup (once)

1. **Phone on a tripod, vertical (9:16). Never touch it again until you finish.**
   Why: the lid occlusion (`/orbit`, `/words-from-behind`), the hand tracking (`/icon-on-palm`, `/paper`,
   `/thanos-snap`) and the clean plate all compare frames against each other. One bump and they misalign.
2. **Framing:** laptop open, screen toward the camera at a slight angle, in the **lower ~55%** of the frame. Keep
   the **top ~40% empty** with a plain wall. Orbit, the words, the graph, the paper scenery and the sticker all go there.
3. **Light:** bright and even from the front (window or lamp behind the phone). No strong backlight.
4. **Lock exposure and focus** (long-press the screen → AE/AF lock). **4K 30 fps** if possible: `/zooming` renders
   from full resolution and dives much deeper in 4K.
5. **Screen:** brightness ~50%, one app (Claude Desktop, a terminal, anything) zoomed in so the text is big,
   notifications off.
6. **Hands:** sleeves up, nothing the same colour as the desk. A dark laptop on a lighter desk/wall is ideal for the
   automatic mask.

## While recording

For each beat: **say the line → type the slash command slowly → Enter → do the action → 1 s pause.**
Every few beats, **rest both hands off the laptop for 2-3 s**. Those still frames become the `--ref-time` the
hand effects key against.

| effect | do this on camera | hold |
|---|---|---|
| `/orbit` | hands off the keyboard, resting below it | 3-4 s |
| `/zooming` | hands still; know which on-screen point to dive into | 4 s |
| `/words-from-behind` | hands still | 3 s |
| `/icon-on-palm` | open palm, flat, facing up, beside the laptop; move it only slightly | 4 s |
| `/zig-zag-graph` | index finger draws a rising zig-zag left → right above the laptop, slowly (~2 s) | +1 s at the end |
| `/paper` | hands on the keyboard, mostly still | 3-4 s |
| `/thanos-snap` | hand up beside the laptop, one clear snap, hold, then hands out of frame | 1 s + 3 s |
| `/share-comment` | empty desk (or use the clean plate) | 4 s |

## Clean plate (for /thanos-snap)

Right after the take: **lift the laptop out of frame, keep your hands out, record 5 s of the empty desk.** Do not
move the phone. Leave no marker on the desk, or plan to `--patch` it out. `plate.py` lines the plate up and
colour-matches it even if the phone shifted slightly.

## Common problems

| symptom | cause | fix |
|---|---|---|
| logos or words float in front of the lid | the mask misses part of the lid | rebuild with `mask.py`, check `*_check.jpg` |
| icon jumps around, or the paper hand has holes | camera moved, or the ref frame contains a hand | pick a different `--ref-time`; raise `--thr` |
| lighter rectangle after the snap | plate exposure differs | re-shoot the plate with exposure locked, or re-run `plate.py` |
| zoom goes soft early | 1080p source | shoot 4K, or lower `--tunnel-from` |
| everything looks dull | dim room | `--gamma 0.86` (and `--wb` for a colour cast) |
