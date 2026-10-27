"""/orbit - logos fly out of the screen, circle the laptop lid on a tilted ring (the back half passes BEHIND the lid),
then get sucked back into the screen with a flash.

  python orbit.py --in clip.mp4 --start 26.0 --dur 2.9 --out orbit.mp4 \
      --logos chatgpt.png,perplexity.png,claude.svg,cursor.png,gemini.png

Needs a locked-off camera: the lid is cut out from the live frame with one static mask.
"""
import math, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visuals-core"))
import vfx

ap = vfx.common_args(__doc__)
ap.add_argument("--logos", required=True, help="comma list of logo files (PNG with alpha, or SVG)")
ap.add_argument("--center", help="ring centre x,y (default: lid centre, a little below the lid top)")
ap.add_argument("--into", help="point the logos come from / go back into, x,y (default: screen centre)")
ap.add_argument("--rx", type=float, help="ring radius x (default 42%% of the width)")
ap.add_argument("--ry", type=float, help="ring radius y (default 0.35 * rx)")
ap.add_argument("--tilt", type=float, default=-7.0, help="ring tilt, degrees")
ap.add_argument("--badge", type=int, default=164, help="logo badge diameter, px")
ap.add_argument("--spin", type=float, default=0.42, help="revolutions per second")
ap.add_argument("--ring-ref", type=float, help="source time of a hand-free frame for the mask (default --start)")
a = vfx.parse(ap)

W, H = vfx.size_of(a.size)
ref = vfx.grab(a.inp, a.ring_ref if a.ring_ref is not None else a.start, (W, H))
mask = vfx.get_mask(a, ref)
x0, y0, x1, y1 = vfx.bbox(mask)
scr = vfx.screen_mask(ref, mask)
if scr.any():
    sx0, sy0, sx1, sy1 = vfx.bbox(scr); S = ((sx0 + sx1) / 2, (sy0 + sy1) / 2)
else:
    S = ((x0 + x1) / 2, y0 + 0.25 * (y1 - y0))
O = vfx.pt(a.center) if a.center else ((x0 + x1) / 2, y0 + 0.115 * W)
S = vfx.pt(a.into) if a.into else S
RX = a.rx or 0.42 * W; RY = a.ry or 0.35 * RX
TILT = math.radians(a.tilt)
LID = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), 0.8)[..., None]

# badges: white disc + logo, soft shadow under it
B = a.badge
badges = []
for p in a.logos.split(","):
    logo = vfx.load_rgba(p.strip(), int(B * 0.6))
    if logo.shape[1] > B * 0.6: logo = cv2.resize(logo, (int(B * 0.6), int(logo.shape[0] * B * 0.6 / logo.shape[1])), interpolation=cv2.INTER_AREA)
    disc = np.zeros((B, B, 4), np.float32)
    cv2.circle(disc, (B // 2, B // 2), B // 2 - 1, (255, 255, 255, 255), -1, cv2.LINE_AA)
    vfx.over(disc[..., :3], logo, B / 2, B / 2)                     # logo onto the disc colour, disc alpha stays
    badges.append(disc)
n = len(badges)
SH = vfx.shadow_rgba(badges[0], blur=18, opacity=0.30, dy=14)

fl = np.zeros((600, 840, 4), np.float32)
yy, xx = np.mgrid[0:600, 0:840]
rr = np.sqrt(((xx - 420) / 420) ** 2 + ((yy - 300) / 300) ** 2)
fl[..., 0] = 230; fl[..., 1] = 240; fl[..., 2] = 255; fl[..., 3] = np.clip(1 - rr, 0, 1) ** 1.5 * 255

T_SUCK = (a.dur - 0.78, a.dur - 0.18)
T_FLASH = a.dur - 0.16

def ring_pts(th):
    x, y = RX * np.cos(th), RY * np.sin(th)
    return O[0] + x * math.cos(TILT) - y * math.sin(TILT), O[1] + x * math.sin(TILT) + y * math.cos(TILT)

def draw_ring(dst, front, alpha):
    if alpha <= 0.01: return
    th = np.linspace(0, 2 * np.pi, int(2 * np.pi * RX / 18), endpoint=False)
    sel = (np.sin(th) > 0) == front
    ov = dst.copy()
    for x, y in zip(*ring_pts(th[sel])):
        cv2.circle(ov, (int(x), int(y)), 3 if front else 2, (255, 255, 255), -1, cv2.LINE_AA)
    dst[:] = dst * (1 - 0.75 * alpha) + ov * (0.75 * alpha)

def render(frame, t, i):
    base = frame.astype(np.float32); out = base.copy()
    pop = vfx.spring(t, 14, 120); suck = vfx.ramp(t, *T_SUCK)
    r = pop * (1 - suck)
    spin = t * 2 * math.pi * a.spin + suck * suck * 5.5
    items = []
    for k in range(n):
        th = k / n * 2 * math.pi + spin
        rx_, ry_ = ring_pts(th)
        px, py = S[0] + (rx_ - S[0]) * r, S[1] + (ry_ - S[1]) * r
        depth = (math.sin(th) + 1) / 2
        front = math.sin(th) > 0 or r < 0.55
        sc = (0.72 + 0.42 * depth) * max(r, 1e-3) ** 0.6
        items.append((depth, front, px, py, sc, k))
    for layer_front in (False, True):
        if layer_front: out = out * (1 - LID) + base * LID          # the lid (and any hand on it) occludes the back half
        draw_ring(out, layer_front, r * (1 - suck))
        for depth, front, px, py, sc, k in sorted(items):
            if front != layer_front: continue
            vfx.over(out, SH, px, py + 6, sc)
            b = badges[k] if front else np.dstack([badges[k][..., :3] * (0.85 + 0.15 * depth), badges[k][..., 3]])
            vfx.over(out, b, px, py, sc)
    f = max(0.0, 1 - abs(t - T_FLASH) / 0.16)
    if f > 0: vfx.over(out, fl, S[0], S[1], 1.0, 0, f)
    return out

vfx.run(a, render)
