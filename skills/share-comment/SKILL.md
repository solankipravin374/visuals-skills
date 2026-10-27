---
name: share-comment
description: Video effect - the end-card call to action, a sticker that drops in from the top and bounces ("COMMENT 'VISUALS' to get all 8 effect skills") with a follow pill popping in under it. Use when the user types /share-comment or wants a comment-keyword CTA sticker at the end of a reel.
---

# /share-comment

A white sticker with an ink border and a solid offset shadow falls from above the frame, overshoots and settles at
a slight tilt with a wobble. It reads COMMENT / "KEYWORD" / a subline with a yellow highlight. A second later a
"Follow @you" pill springs in underneath. ~2.5-4.5 s.

**Needs:** any clip for the background (or a still such as the clean plate). Requires `visuals-core`.

## Steps

1. Ask for the comment keyword, the subline, the follow handle, and whether to use the video or a still behind it.
2. Preview and render:
   ```bash
   python share_comment.py --in clip.mp4 --start 113.0 --dur 4.5 --out preview --preview 0.2,0.6,1.4 \
       --keyword VISUALS --sub "to get all 8 effect skills" --highlight "8 effect skills" --follow "Follow @aiwithpravin"
   python share_comment.py --in clip.mp4 --start 113.0 --dur 4.5 --out cta.mp4 --bg plate.png --keyword VISUALS ...
   ```

## Flags

| flag | default | meaning |
|---|---|---|
| `--keyword`, `--top` | VISUALS, COMMENT | the big keyword and the line above it |
| `--sub`, `--highlight` | "to get all 8 effect skills", "8 effect skills" | subline and its highlighted part |
| `--follow` | none | follow pill text |
| `--bg` | the video | still image background |
| `--accent`, `--ink` | `#D97757`, `#1C1A17` | keyword/pill colour, border and text colour |
| `--y` | 29% of height | sticker top |
| `--font` | bold system font | sticker font |

## Check before delivering

- Keep the sticker inside Instagram's safe zone: below y=230 and above y=1440 on 1080x1920, and clear of the right 230 px of icons.
  The default `--y` does this.
- The keyword in the sticker must match the keyword your auto-DM tool listens for.
