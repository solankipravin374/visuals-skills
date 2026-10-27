"""/words-from-behind - a title rises from BEHIND the laptop lid, steps forward in front of it, then sinks back behind.

  python words_from_behind.py --in clip.mp4 --start 74.8 --dur 3.1 --out words.mp4 \
      --line1 "Directed by" --line2 "Claude Code"

Needs a locked-off camera (the lid is cut from the live frame with one static mask).
"""
import os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visuals-core"))
import vfx

ap = vfx.common_args(__doc__)
ap.add_argument("--line1", default="Directed by", help="small top line ('' to skip)")
ap.add_argument("--line2", default="Claude Code", help="big line")
ap.add_argument("--color1", default="#1C1A17"); ap.add_argument("--color2", default="#D97757")
ap.add_argument("--shadow", default="#1C1A17", help="stacked shadow colour of the big line")
ap.add_argument("--size2", type=int, default=122, help="big line font size (px at 1080 wide)")
ap.add_argument("--font", help="TTF/OTF for both lines (default: a bold system font)")
ap.add_argument("--peak", type=float, help="y the title rises to (default: 210 px above the lid top)")
ap.add_argument("--forward", type=float, help="y once it steps forward (default: 290 px above the lid top)")
ap.add_argument("--back-at", type=float, help="local time it starts sinking back (default dur - 0.68)")
ap.add_argument("--mask-ref", type=float, help="source time of a hand-free frame for the mask (default --start)")
a = vfx.parse(ap)

W, H = vfx.size_of(a.size); U = W / 1080
ref = vfx.grab(a.inp, a.mask_ref if a.mask_ref is not None else a.start, (W, H))
mask = vfx.get_mask(a, ref)
LID_TOP = vfx.bbox(mask)[1]
LID = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), 0.8)[..., None]

big = vfx.text_rgba(a.line2, vfx.font(a.size2 * U, a.font), a.color2, stack_shadow=(int(4 * U), int(4 * U), 2, a.shadow))
rows = [big]
if a.line1:
    small = vfx.text_rgba(a.line1.upper(), vfx.font(a.size2 * 0.48 * U, a.font), a.color1)
    rows = [small, big]
TW = max(r.shape[1] for r in rows); TH = sum(r.shape[0] for r in rows)
TITLE = np.zeros((TH, TW, 4), np.uint8); y = 0
for r in rows:
    x = (TW - r.shape[1]) // 2; TITLE[y:y + r.shape[0], x:x + r.shape[1]] = r; y += r.shape[0]
SHADOW = vfx.shadow_rgba(TITLE, blur=22 * U, opacity=0.28, dy=int(26 * U))

START_Y = LID_TOP + 185 * U                       # hidden behind the lid
PEAK = a.peak if a.peak is not None else LID_TOP - 185 * U
FWD = a.forward if a.forward is not None else LID_TOP - 290 * U
BACK = a.back_at if a.back_at is not None else a.dur - 0.68
END_Y = LID_TOP + 205 * U

def render(frame, t, i):
    base = frame.astype(np.float32); out = base.copy()
    rise = vfx.ease_out_back(t / 0.62, 1.4)
    fwd = vfx.ease_out_cubic((t - 0.6) / 0.4)
    ret = vfx.ease_in_cubic((t - BACK) / 0.6)
    yc = START_Y + (PEAK - START_Y) * rise + (FWD - PEAK) * fwd + (END_Y - FWD) * ret
    sc = 0.85 + 0.30 * fwd - 0.30 * ret
    in_front = fwd > 0.5 and ret < 0.4
    if in_front:
        vfx.over(out, SHADOW, W / 2, yc, sc)
        vfx.over(out, TITLE, W / 2, yc, sc)
    else:
        vfx.over(out, TITLE, W / 2, yc, sc)
        out = out * (1 - LID) + base * LID           # lid in front of the title
    return out

vfx.run(a, render)
