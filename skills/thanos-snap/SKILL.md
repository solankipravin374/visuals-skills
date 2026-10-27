---
name: thanos-snap
description: Video effect - snap your fingers and the laptop crumbles into drifting ash, wave by wave from the snap, while your hand stays in front; the laptop stays gone and the shot settles on a clean plate of the empty desk. Use when the user types /thanos-snap (or /thanos-finger) or wants an object to disintegrate into dust after a snap.
---

# /thanos-snap

After the snap a dissolve wave spreads across the laptop from the snapping hand. Each pixel chars, lets go and
becomes an ash particle that drifts up and away with a little turbulence. The background behind is revealed from a
clean plate, the real hand stays composited on top, and the shot ends on the empty desk. ~3.4 s.

**Needs:**
1. A locked-off clip with one clear snap near the laptop.
2. A **clean plate**: the same shot without the laptop. Lift the laptop out after the take, and keep the phone still.
3. A frame with the laptop in place and the hand not over it (`--ref-time`). Its colours are what turn to dust.

Requires `visuals-core` next to this folder.

## Steps

1. Align and colour-match the plate to the clip (once):
   ```bash
   python plate.py --in clip.mp4 --t 90.8 --plate empty_desk.jpg --out plate.png --mask laptop_mask.png
   ```
   Open `plate_seam_check.jpg`: the laptop area is filled from the plate, and wall marks should line up. A video plate
   works too (`--plate empty.mov --plate-t 2`). Cover a leftover marker with `--patch x0,y0,x1,y1,dx`.
2. Find the snap frame (local time from `--start`) and preview:
   ```bash
   python thanos_snap.py --in clip.mp4 --start 91.5 --dur 3.4 --out preview --preview 0.6,1.1,1.5,2.0,3.3 \
       --plate plate.png --snap-time 0.72 --ref-time 90.8 --mask laptop_mask.png
   ```
3. Render without `--preview`, with `--out thanos.mp4`. Add the real snap sound in the edit if the audio is quiet.

## Flags

| flag | default | meaning |
|---|---|---|
| `--plate` | required | output of plate.py |
| `--snap-time` | required | local time of the snap |
| `--ref-time` | required | frame with the laptop, hand not over it |
| `--origin x,y` | top-right of the laptop | where the wave starts (put it at the snapping hand) |
| `--spread` | 1.55 | seconds for the wave to cross the laptop |
| `--ash` | `#3C322C` | ash colour |
| `--settle` | 0.5 | final crossfade onto the plate (0 = off) |
| `--thr` | 34 | hand-difference threshold |

## Check before delivering

- No outline of the laptop is left on the wall after the dust. If a lighter rectangle shows, re-run plate.py from a
  closer `--t`, or check that the plate was shot with the same exposure.
- The hand stays solid in front of the dust, with no halo. A halo means the ref frame has a different screen state, so pick another.
