---
name: orbit
description: Video effect - logos fly out of a laptop screen, circle the lid on a tilted ring (the back half passes behind the lid) and get sucked back into the screen with a flash. Use when the user types /orbit or wants icons/logos orbiting a laptop, phone or object in their footage.
---

# /orbit

Logos pop out of the screen, orbit the laptop lid on a tilted 3D ring, the half of the ring behind the lid is hidden
by the real lid, then everything spirals back into the screen with a flash. Default timing fits ~2.9 s.

**Needs:** a locked-off clip with hands off the laptop, and 3-6 logo files (PNG with transparency, or SVG).
Requires the `visuals-core` folder next to this one (see its SKILL.md for setup and the shared flags).

## Steps

1. Ask for the clip, the effect start time and the logos. No logos? Ask which brands; free SVGs are in the npm
   package `@lobehub/icons-static-svg` (`npm pack @lobehub/icons-static-svg`, then use `icons/*.svg`). Brand logos
   are trademarks of their owners: fine for commentary, not for implying endorsement.
2. Check the mask on a hand-free frame: `python ../visuals-core/mask.py --in clip.mp4 --t <hand-free time> --out laptop_mask.png`.
3. Preview, look at the stills, adjust, render:
   ```bash
   python orbit.py --in clip.mp4 --start 26.0 --dur 2.9 --out preview --preview 0.3,1.0,1.6,2.4,2.74 \
       --logos chatgpt.svg,perplexity.svg,claude.svg,cursor.svg,gemini.svg --mask laptop_mask.png
   python orbit.py --in clip.mp4 --start 26.0 --dur 2.9 --out orbit.mp4 --logos ... --mask laptop_mask.png
   ```

## Flags

| flag | default | meaning |
|---|---|---|
| `--logos` | required | comma list of logo files |
| `--center x,y` | lid centre, ~124 px below the lid top | ring centre |
| `--into x,y` | screen centre | where logos come from and return to |
| `--rx`, `--ry` | 42% of width, 0.35 x rx | ring radii |
| `--tilt` | -7 | ring tilt in degrees |
| `--badge` | 164 | badge diameter in px |
| `--spin` | 0.42 | revolutions per second |
| `--ring-ref` | `--start` | source time of a hand-free frame for the auto mask |

## Check before delivering

- At ~1.6 s at least one badge is partly hidden behind the top edge of the lid. If badges float in front of the lid
  all the time, the mask is missing the lid: rebuild it.
- Badges should not cover a talking face or captions: move `--center` or shrink `--rx`.
- The suck-in (last 0.8 s) ends on a flash over the screen centre.
