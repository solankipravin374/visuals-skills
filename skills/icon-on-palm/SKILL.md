---
name: icon-on-palm
description: Video effect - a character or mascot drops onto your open palm, lands with a squash, then hops and glows while following your hand, with sparkles. Use when the user types /icon-on-palm or wants a mascot/icon standing on their hand in their footage.
---

# /icon-on-palm

A little character falls from above onto the user's open palm, lands with a squash-and-stretch bounce, then keeps
hopping and glowing while it tracks the hand; a warm light pools on the palm and sparkles drift up. ~3.7 s.

The default character is a built-in pixel robot. Pass `--icon` for a mascot or logo (PNG with transparency or SVG).

**Needs:** a locked-off clip where an open palm is held up (flat, facing up) and a hand-free frame from the same
shot. Requires `visuals-core` next to this folder.

## Steps

1. Find the palm moment and a frame with no hand in shot (`--ref-time`).
2. Note which way the fingers point (`--fingers left|right|up`); the palm point sits on the finger side of the hand.
3. Preview (the script tracks the palm over the whole effect first and prints how many frames it found), render:
   ```bash
   python icon_on_palm.py --in clip.mp4 --start 62.9 --dur 3.7 --out preview --preview 0.7,1.0,1.5,2.6 \
       --ref-time 60.8 --fingers left
   python icon_on_palm.py --in clip.mp4 --start 62.9 --dur 3.7 --out palm.mp4 --ref-time 60.8 --fingers left --icon mascot.png
   ```

## Flags

| flag | default | meaning |
|---|---|---|
| `--ref-time` | required | source time of a frame with NO hand |
| `--fingers` | left | which way the open fingers point |
| `--icon`, `--icon-height` | pixel robot, 150 | character file and height (px at 1080 wide) |
| `--glow` | `#FF9E6E` | glow and palm-light colour |
| `--land`, `--hop` | 0.78, 0.56 | landing time and seconds per hop |
| `--offset x,y` | -30,26 | nudge from the tracked palm point |
| `--thr` | 30 | hand-difference threshold; raise it if shadows get tracked |

## Check before delivering

- The tracker should find the hand in nearly every frame (it prints e.g. `108/111`). If not: the camera moved, or the
  ref frame has a hand or a different screen in it. Pick another `--ref-time`.
- The character's feet sit on the palm, not floating: adjust `--offset`.
- Using someone's mascot? Use one you own or have rights to.
