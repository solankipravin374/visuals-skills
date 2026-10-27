---
name: words-from-behind
description: Video effect - a title (e.g. "Directed by Claude Code") rises from behind a laptop lid, steps forward in front of it, then sinks back behind. Use when the user types /words-from-behind or wants text emerging from behind an object in their footage.
---

# /words-from-behind

Two lines of title text start hidden behind the laptop lid, rise up over it with a little overshoot, step forward
(they grow and pass in front of the lid with a soft shadow), hold, then sink back down behind the lid. ~3.1 s.

**Needs:** a locked-off clip with the lid visible against the wall. Requires `visuals-core` next to this folder.

## Steps

1. Ask for the two lines (top small line, big line). Default: "Directed by" / "Claude Code".
2. Make or check the mask: `python ../visuals-core/mask.py --in clip.mp4 --t <hand-free time> --out laptop_mask.png`.
3. Preview and render:
   ```bash
   python words_from_behind.py --in clip.mp4 --start 74.8 --dur 3.1 --out preview --preview 0.06,0.5,1.2,2.95 \
       --line1 "Directed by" --line2 "Claude Code" --mask laptop_mask.png
   python words_from_behind.py --in clip.mp4 --start 74.8 --dur 3.1 --out words.mp4 --line1 ... --line2 ... --mask laptop_mask.png
   ```

## Flags

| flag | default | meaning |
|---|---|---|
| `--line1`, `--line2` | "Directed by", "Claude Code" | small top line ('' to skip) and big line |
| `--color1`, `--color2`, `--shadow` | ink, orange, ink | text colours (big line has a stacked shadow) |
| `--size2` | 122 | big line size in px at 1080 wide |
| `--font` | bold system font | any TTF/OTF |
| `--peak`, `--forward` | 185 / 290 px above the lid top | y positions of the rise and the step forward |
| `--back-at` | dur - 0.68 | when it starts sinking back |

## Check before delivering

- At 0.06 s and at the very end only the top of the text peeks over the lid. The lid must cut it cleanly.
- The big line fits inside the frame width; shorten it or lower `--size2`.
