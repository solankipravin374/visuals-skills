"""/icon-on-palm - a character drops onto your open palm, lands with a squash, then hops and glows while it follows
your hand.

  python icon_on_palm.py --in clip.mp4 --start 62.9 --dur 3.7 --out palm.mp4 --ref-time 60.8 --fingers left
  python icon_on_palm.py ... --icon my_mascot.png

The hand is found by difference against a hand-free frame (--ref-time), so the camera must not move.
"""
import math, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visuals-core"))
import vfx

ap = vfx.common_args(__doc__)
ap.add_argument("--ref-time", type=float, required=True, help="source time of a frame with NO hand in it")
ap.add_argument("--fingers", choices=["left", "right", "up"], default="left", help="which way the open fingers point")
ap.add_argument("--icon", help="PNG/SVG character (default: the built-in pixel robot)")
ap.add_argument("--icon-height", type=int, default=150, help="character height, px at 1080 wide")
ap.add_argument("--glow", default="#FF9E6E", help="glow colour")
ap.add_argument("--land", type=float, default=0.78, help="local time it lands")
ap.add_argument("--hop", type=float, default=0.56, help="seconds per hop")
ap.add_argument("--offset", default="-30,26", help="nudge from the tracked palm point, x,y px")
ap.add_argument("--thr", type=int, default=30, help="hand difference threshold (raise if the mask picks up noise)")
a = vfx.parse(ap)

W, H = vfx.size_of(a.size); U = W / 1080
OX, OY = (v * U for v in vfx.pt(a.offset))

def robot(u):
    """Built-in pixel robot (body, eyes, antenna, arms, feet), u px per cell."""
    O, D, L = (87, 119, 217, 255), (16, 17, 26, 255), (122, 160, 240, 255)
    rects = [(1, 2, 8, 6, O), (-1, 4, 2, 1.6, O), (9, 4, 2, 1.6, O), (2.2, 8, 1.6, 1.6, O), (6.2, 8, 1.6, 1.6, O),
             (4.6, 0.6, 0.8, 1.4, O), (4.2, 0, 1.6, 1.0, L), (2.6, 3.6, 1.2, 1.6, D), (6.2, 3.6, 1.2, 1.6, D), (3.6, 6.4, 2.8, 0.6, D), (3.0, 5.8, 0.6, 0.6, D), (6.4, 5.8, 0.6, 0.6, D)]
    img = np.zeros((int(9.8 * u) + 2, int(12.2 * u) + 2, 4), np.uint8)
    for x, y, w, h, c in rects:
        cv2.rectangle(img, (int((x + 1) * u), int(y * u)), (int((x + 1 + w) * u) - 1, int((y + h) * u) - 1), c, -1)
    return img

ICON = (vfx.load_rgba(a.icon, int(a.icon_height * U)) if a.icon else robot(a.icon_height * U / 9.8)).astype(np.float32)
GC = vfx.hexc(a.glow)
p = int(40 * U)
GLOW = cv2.copyMakeBorder(ICON, p, p, p, p, cv2.BORDER_CONSTANT, value=0)
GLOW[..., :3] = GC; GLOW[..., 3] = np.clip(cv2.GaussianBlur(GLOW[..., 3], (0, 0), 14 * U) * 1.6, 0, 255)

def ellipse(w, h, color, alpha, blur):
    e = np.zeros((int(h * 3), int(w * 1.6), 4), np.float32)
    cv2.ellipse(e, (e.shape[1] // 2, e.shape[0] // 2), (int(w / 2), int(h / 2)), 0, 0, 360, tuple(float(c) for c in color) + (255.0 * alpha,), -1, cv2.LINE_AA)
    e[..., 3] = cv2.GaussianBlur(e[..., 3], (0, 0), blur); return e
POOL = ellipse(300 * U, 140 * U, GC, 0.35, 30 * U)
SHAD = ellipse(140 * U, 26 * U, (10, 25, 60), 0.35, 5 * U)

# ---- pass 1: track the palm over the whole effect (half resolution is plenty) ----------------------------
hw, hh = W // 2, H // 2
ref = vfx.grab(a.inp, a.ref_time, (hw, hh))
track = []
for fr in vfx.decode(a.inp, a.start, int(round(a.dur * a.fps)), (hw, hh), a.fps):
    m = vfx.hand_mask(fr, ref, a.thr, min_area=800)
    ys, xs = np.where(m > 0)
    if len(xs) < 800: track.append(None); continue
    x0, x1 = xs.min(), xs.max()
    if a.fingers == "left": sel = xs < x0 + 0.55 * (x1 - x0)
    elif a.fingers == "right": sel = xs > x1 - 0.55 * (x1 - x0)
    else: sel = ys > np.percentile(ys, 35)
    track.append((xs[sel].mean() * 2, np.percentile(ys[sel], 25) * 2))
print(f"tracked the palm in {sum(t is not None for t in track)}/{len(track)} frames")

def palm(i, w=5):
    pts = [track[j] for j in range(max(0, i - w), min(len(track), i + w + 1)) if track[j] is not None]
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None

def render(frame, t, i):
    out = frame.astype(np.float32)
    pp = palm(min(i, len(track) - 1))
    if pp is None or t < a.land - 0.2: return out
    land = vfx.spring(t - a.land, 9, 140)
    tj = max(0.0, t - a.land - 0.45)
    ph = (tj / a.hop) % 1
    hop = math.sin(ph * math.pi) * 78 * U if tj > 0 else 0.0
    squash = max(0.0, 1 - min(ph, 1 - ph) * 9) if tj > 0 else 0.0
    fade = 1 - vfx.ramp(t, a.dur - 0.22, a.dur - 0.02)
    cx, feet = pp[0] + OX, pp[1] + OY
    y = feet - hop - (1 - land) * 700 * U
    pool = out.copy(); vfx.over(pool, POOL, cx, feet, 1.0)
    out = out + np.clip(pool - out, 0, None) * land * fade          # screen-like warm light on the palm
    vfx.over(out, SHAD, cx, feet, 1 - hop / (160 * U), 0, land * fade)
    g = 0.75 + 0.25 * math.sin(t * 9)
    sx, sy = 1 + 0.14 * squash, 1 - 0.16 * squash
    icon = cv2.resize(ICON, (int(ICON.shape[1] * sx), int(ICON.shape[0] * sy)), interpolation=cv2.INTER_LINEAR)
    glow = cv2.resize(GLOW, (int(GLOW.shape[1] * sx), int(GLOW.shape[0] * sy)), interpolation=cv2.INTER_LINEAR)
    vfx.over(out, glow, cx, y + p * sy, 1.0, 0, g * fade, anchor=(0.5, 1.0))
    vfx.over(out, icon, cx, y, 1.0, 0, fade, anchor=(0.5, 1.0))
    for k in range(6):                                              # sparkles drifting up
        an = k * 1.05 + t * 1.6; kk = (t * 0.9 + k / 6) % 1
        sx_ = cx + math.cos(an) * (90 + 60 * kk) * U; sy_ = feet - (70 + kk * 170) * U + math.sin(an) * 20 * U
        s = int(7 * U); col = (77, 225, 255) if k % 2 else (184, 210, 255)
        al = land * (1 - kk) * 0.95 * fade
        ov = out.copy()
        cv2.fillConvexPoly(ov, np.int32([[sx_, sy_ - s], [sx_ + s, sy_], [sx_, sy_ + s], [sx_ - s, sy_]]), col, cv2.LINE_AA)
        out = out * (1 - al) + ov * al
    return out

vfx.run(a, render)
