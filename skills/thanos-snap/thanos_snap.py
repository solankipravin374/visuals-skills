"""/thanos-snap - snap your fingers and the laptop crumbles into drifting ash, wave by wave from the snap, and it
stays gone (the shot settles on the clean plate).

  python plate.py --in clip.mp4 --t 90.8 --plate empty_table.jpg --out plate.png      # once
  python thanos_snap.py --in clip.mp4 --start 91.5 --dur 3.4 --out thanos.mp4 --plate plate.png \
      --snap-time 0.72 --ref-time 90.8

--ref-time: a frame with the laptop in place (its colours are what turns to dust; the hand is keyed against it).
"""
import os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visuals-core"))
import vfx

ap = vfx.common_args(__doc__)
ap.add_argument("--plate", required=True, help="clean plate from plate.py")
ap.add_argument("--snap-time", type=float, required=True, help="local time of the snap")
ap.add_argument("--ref-time", type=float, required=True, help="source time of a frame with the laptop, hand not over it")
ap.add_argument("--origin", help="x,y where the dissolve starts (default: top-right corner of the laptop)")
ap.add_argument("--spread", type=float, default=1.55, help="seconds for the wave to cross the laptop")
ap.add_argument("--ash", default="#3C322C", help="ash colour")
ap.add_argument("--settle", type=float, default=0.5, help="final crossfade onto the clean plate, seconds (0 = off)")
ap.add_argument("--thr", type=int, default=34, help="hand difference threshold")
a = vfx.parse(ap)

W, H = vfx.size_of(a.size)
ref = vfx.grab(a.inp, a.ref_time, (W, H))
LAP = vfx.get_mask(a, ref)
PLATE = cv2.resize(cv2.imread(a.plate), (W, H)).astype(np.float32)
x0, y0, x1, y1 = vfx.bbox(LAP)
OX, OY = vfx.pt(a.origin) if a.origin else (x1, y0)
SNAP = a.snap_time
rng = np.random.default_rng(11)
REF = ref.astype(np.float32)
MASK = cv2.GaussianBlur(LAP, (0, 0), 1.5).astype(np.float32) / 255
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
noise = cv2.resize(rng.random((H // 20, W // 20)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
noise2 = cv2.resize(rng.random((H // 10, W // 10)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
grain = rng.random((H, W)).astype(np.float32)
dist = np.hypot(xx - OX, (yy - OY) * 1.1)
st = dist / dist[LAP > 0].max() * 0.70 + noise * 0.16 + noise2 * 0.04 + grain * 0.10   # coherent wave, granular edge
st = (st - st[LAP > 0].min()) / (st[LAP > 0].max() - st[LAP > 0].min())
START = SNAP + 0.12 + st * a.spread                     # per-pixel time it turns to dust
B = max(2, round(3 * W / 1080))
ys, xs = np.where(LAP[::B, ::B] > 0); ys = ys * B + 1; xs = xs * B + 1
P0 = np.stack([xs, ys], 1).astype(np.float32); COL = REF[ys, xs]; T0 = START[ys, xs]; n = len(xs)
U = W / 1080
dirx = np.sign(OX - (x0 + x1) / 2) or 1.0              # ash drifts away from the snapping hand
V = np.stack([rng.normal(-120 * dirx, 50, n), rng.normal(-75, 45, n)], 1).astype(np.float32) * U
ACC = np.stack([rng.normal(-230 * dirx, 80, n), rng.normal(-120, 60, n)], 1).astype(np.float32) * U
LIFE = rng.uniform(1.0, 1.8, n).astype(np.float32); PH = rng.uniform(0, 6.28, n).astype(np.float32)
SIZE = rng.choice([1, 2, 2, 3], n)
ASH = vfx.hexc(a.ash)

def render(frame, t, i):
    fr = frame.astype(np.float32)
    gone = (t >= START).astype(np.float32)[..., None]                               # per pixel: already dust?
    fringe = np.clip(1 - (START - t) / 0.20, 0, 1) * (t < START) * MASK            # charred edge before it lets go
    lap = REF * (1 - 0.55 * fringe[..., None]) + ASH * 0.55 * fringe[..., None]
    kb = vfx.ease((t - SNAP - 0.05) / 0.9)
    outside = fr * (1 - kb) + PLATE * kb                                              # whole background onto the plate, no seams
    lap = lap * (1 - gone) + PLATE * gone                                             # swap only the laptop layer, so its soft
    base = outside * (1 - MASK[..., None]) + lap * MASK[..., None]                   # edge never leaves a dark outline
    tau = t - T0; alive = (tau > 0) & (tau < LIFE)
    if alive.any():
        T = tau[alive][:, None]
        pos = P0[alive] + V[alive] * T + 0.5 * ACC[alive] * T * T
        pos[:, 0] += 14 * U * np.sin(PH[alive] + T[:, 0] * 7) * T[:, 0]
        pos[:, 1] += 10 * U * np.cos(PH[alive] * 1.3 + T[:, 0] * 5) * T[:, 0]
        life = T[:, 0] / LIFE[alive]
        alpha = np.clip(1 - life, 0, 1) ** 0.8
        mk = np.clip(life * 1.3 + 0.45, 0, 1)[:, None]
        c = COL[alive] * (1 - mk) + ASH * mk
        sz = np.maximum(1, np.round(SIZE[alive] * (1 - 0.6 * life))).astype(int)
        acc = np.zeros((H, W, 3), np.float32); aa = np.zeros((H, W), np.float32)
        px = pos[:, 0].astype(int); py = pos[:, 1].astype(int)
        for dy in range(3):
            for dx in range(3):
                sel = sz > max(dx, dy)
                x = px[sel] + dx; y = py[sel] + dy
                ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
                al = alpha[sel][ok]
                np.add.at(aa, (y[ok], x[ok]), al); np.add.at(acc, (y[ok], x[ok]), c[sel][ok] * al[:, None])
        A = np.clip(aa, 0, 1)
        base = base * (1 - A[..., None]) + acc / np.maximum(aa, 1e-6)[..., None] * A[..., None]
    hm = vfx.hand_mask(frame, ref, a.thr)
    if hm.any():
        hm = cv2.erode(hm, np.ones((7, 7), np.uint8))                                 # mask runs a few px wide: no halo
        h = cv2.GaussianBlur(hm, (0, 0), 1.6).astype(np.float32)[..., None] / 255
        base = base * (1 - h) + fr * h
    if a.settle > 0 and t > a.dur - a.settle:
        k = (t - (a.dur - a.settle)) / a.settle; base = base * (1 - k) + PLATE * k
    return base

vfx.run(a, render)
