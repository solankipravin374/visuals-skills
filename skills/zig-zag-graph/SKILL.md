---
name: zig-zag-graph
description: Video effect - a glowing up-trend zig-zag line draws itself across the frame (timed to a finger sweep), ending in an arrow and a springy "+300%" tag. Use when the user types /zig-zag-graph or wants a growth chart drawn over their footage.
---

# /zig-zag-graph

A thick green line with a glow and a soft area fill draws itself left to right, node by node, ending in an arrow
head; then a "+300%" sticker springs in above it. Time `--draw` to the user's finger sweep and it looks like they
drew it in the air. ~3.3 s.

**Needs:** any clip (locked-off is best). Requires `visuals-core` next to this folder.

## Steps

1. Find when the finger starts and stops sweeping (local seconds from `--start`) and use them as `--draw start,end`.
2. Optional: trace the finger path with `grid.py` stills at a few moments and pass them as `--nodes`, so the line
   follows the real finger. Otherwise the auto zig-zag fills `--box`.
3. Preview and render:
   ```bash
   python zig_zag_graph.py --in clip.mp4 --start 79.9 --dur 3.3 --out preview --preview 0.8,1.4,2.0,2.8 --draw 0.35,1.85
   python zig_zag_graph.py --in clip.mp4 --start 79.9 --dur 3.3 --out zig.mp4 --draw 0.35,1.85 --label "+300%"
   ```

## Flags

| flag | default | meaning |
|---|---|---|
| `--nodes "x,y;x,y;..."` | auto | the line's points, left to right |
| `--box x0,y0,x1,y1`, `--points` | middle of frame, 8 | area and node count of the auto zig-zag |
| `--draw start,end` | 0.35,1.85 | when the line draws (ease in-out) |
| `--label` | "+300%" | tag text ('' for none) |
| `--color` | `#22C55E` | line and tag colour |
| `--font` | bold system font | tag font |

## Check before delivering

- The line head stays just behind the fingertip while drawing (nudge `--draw`).
- Never present the label as a real metric the user did not give you. "+300%" is a visual; if the reel claims a
  number, use the user's real one.
