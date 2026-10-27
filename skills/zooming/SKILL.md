---
name: zooming
description: Video effect - an exponential camera push into one point on a screen (an icon, a mascot's eye), through into a tunnel of flying code, then a pull back out. Use when the user types /zooming or wants a "zoom into the screen / into the eye" transition in their footage.
---

# /zooming

The camera dives into a single point on the laptop screen, faster and faster, the pixels give way to a dark tunnel
of glowing code lines (with an optional spinning icon in the middle), it holds there, then pulls all the way back
out to the wide shot. Default timing fits ~3.6 s (1.15 s in, hold, 1.15 s out).

**Needs:** a locked-off clip, ideally 4K (the push renders from the source's full resolution, so 4K stays sharp much
deeper). Requires the `visuals-core` folder next to this one.

## Steps

1. Pick the target with `python ../visuals-core/grid.py --in clip.mp4 --t <start> --out grid.jpg`, then
   `--crop` around the screen for precision. Dark targets (an eye, a pupil) make the best dive.
2. Preview the push, the blend and the tunnel, then render:
   ```bash
   python zooming.py --in clip.mp4 --start 46.2 --dur 3.6 --out preview --preview 0.4,0.6,0.8,1.2,3.0 \
       --target 894.6,1170.2 --center-icon logo.svg
   python zooming.py --in clip.mp4 --start 46.2 --dur 3.6 --out zoom.mp4 --target 894.6,1170.2 --center-icon logo.svg
   ```

## Flags

| flag | default | meaning |
|---|---|---|
| `--target x,y` | required | point to dive into (output pixels) |
| `--push` | 1.15 | seconds to push in, and to pull out |
| `--max-zoom` | 2400 | zoom factor at the deepest point |
| `--tunnel-from` | 60 | zoom factor where the tunnel starts fading in (fully in at 10x) |
| `--code file.txt` | built-in | one code line per text line, shown in the tunnel |
| `--center-icon` | none | PNG/SVG spinning in the tunnel centre |
| `--glow` | `#D97757` | glow colour behind the centre icon |

## Check before delivering

- At ~0.6 s the target is still recognisable and sharp (a 1080p source goes soft earlier; lower `--tunnel-from`).
- The pull-out lands exactly on the original wide shot.
- Put your own lines in `--code` (the reel's commands, your repo name) for a personal touch.
