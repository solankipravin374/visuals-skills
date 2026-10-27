"""Prepare the clean plate for /thanos-snap: the same table/wall WITHOUT the laptop, lined up with your clip.

  python plate.py --in clip.mp4 --t 90.8 --plate empty_table.jpg --out plate.png [--mask laptop_mask.png]
  python plate.py ... --plate empty_table.mov --plate-t 2.0 --patch 370,1395,570,1550,180

Shoot the plate right after the take: same camera spot, laptop removed. It does not have to be pixel-perfect -
SIFT features on the wall line it up (homography), then the colour is matched (Lab mean/std + a per-row gain).
--patch x0,y0,x1,y1,dx covers a leftover marker by copying the strip dx pixels to its left (feathered).
"""
import argparse, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visuals-core"))
import vfx

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--in", dest="inp", required=True, help="your clip")
ap.add_argument("--t", type=float, required=True, help="clip time with the laptop in place and no hand in shot")
ap.add_argument("--plate", required=True, help="clean plate photo or video")
ap.add_argument("--plate-t", type=float, default=1.0, help="time to grab if --plate is a video")
ap.add_argument("--out", required=True); ap.add_argument("--size", default="1080x1920")
ap.add_argument("--mask", help="laptop mask PNG (default: auto)")
ap.add_argument("--patch", action="append", default=[], help="x0,y0,x1,y1,dx (repeatable)")
ap.add_argument("--gamma", type=float, default=1.0, help="use the same --gamma as the effect")
ap.add_argument("--wb", default="1,1,1", help="use the same --wb as the effect")
a = vfx.parse(ap)
vfx.need()
W, H = vfx.size_of(a.size)
ref = vfx.grab(a.inp, a.t, (W, H))
if a.plate.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")):
    plate = cv2.imread(a.plate)
    if plate is None: sys.exit(f"cannot read {a.plate}")
    plate = vfx.graded(cv2.resize(plate, (W, H), interpolation=cv2.INTER_AREA))
else:
    plate = vfx.grab(a.plate, a.plate_t, (W, H))
lap = cv2.resize(cv2.imread(a.mask, 0), (W, H), interpolation=cv2.INTER_NEAREST) if a.mask else vfx.laptop_mask(ref)
keep = (cv2.dilate(lap, np.ones((41, 41), np.uint8)) == 0).astype(np.uint8) * 255   # wall/table the laptop never covers

# ---- align: SIFT on the uncovered area, RANSAC homography -------------------------------------------------
sift = cv2.SIFT_create(6000)
k1, d1 = sift.detectAndCompute(cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY), None)
k2, d2 = sift.detectAndCompute(cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY), keep)
good = [m for m, n in cv2.BFMatcher().knnMatch(d1, d2, k=2) if m.distance < 0.75 * n.distance]
if len(good) < 12: sys.exit(f"only {len(good)} feature matches - the plate needs visible wall/table texture shared with the clip")
Hm, inl = cv2.findHomography(np.float32([k1[m.queryIdx].pt for m in good]), np.float32([k2[m.trainIdx].pt for m in good]), cv2.RANSAC, 4.0)
print(f"aligned with {int(inl.sum())}/{len(good)} inlier matches")
pw = cv2.warpPerspective(plate, Hm, (W, H), borderMode=cv2.BORDER_REPLICATE)

# ---- colour: Lab mean/std on the uncovered area, then a per-row gain (tone drifts with height) -----------------
A = cv2.cvtColor(pw, cv2.COLOR_BGR2LAB).astype(np.float32); B = cv2.cvtColor(ref, cv2.COLOR_BGR2LAB).astype(np.float32)
sel = keep > 0
for c in range(3):
    A[..., c] = (A[..., c] - A[..., c][sel].mean()) / (A[..., c][sel].std() + 1e-6) * B[..., c][sel].std() + B[..., c][sel].mean()
pm = cv2.cvtColor(np.clip(A, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
for p in a.patch:
    x0, y0, x1, y1, dx = (int(float(v)) for v in p.split(","))
    w = x1 - x0; src = pm[y0:y1, x0 - dx:x1 - dx].astype(np.float32); dst = pm[y0:y1, x0:x1].astype(np.float32)
    f = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / 18.0, 0, 1)[None, :, None]
    pm[y0:y1, x0:x1] = (dst * (1 - f) + src * f).astype(np.uint8)
wf = cv2.GaussianBlur(ref, (0, 0), 3).astype(np.float32); pf = cv2.GaussianBlur(pm, (0, 0), 3).astype(np.float32)
G = np.full((H, 3), np.nan, np.float32)
for y in range(H):
    v = sel[y]
    if v.sum() > 40: G[y] = (wf[y, v].mean(0) + 1) / (pf[y, v].mean(0) + 1)
ok = ~np.isnan(G[:, 0]); idx = np.arange(H)
for c in range(3): G[:, c] = np.interp(idx, idx[ok], G[ok, c])
G = np.stack([np.convolve(np.pad(G[:, c], 60, mode="edge"), np.ones(121) / 121, "valid") for c in range(3)], 1)
out = np.clip(pm.astype(np.float32) * G[:, None, :], 0, 255).astype(np.uint8)
cv2.imwrite(a.out, out)
chk = os.path.splitext(a.out)[0] + "_seam_check.jpg"
cv2.imwrite(chk, np.where(lap[..., None] > 0, out, ref))
print(f"wrote {a.out} and {chk} (laptop area replaced by the plate: look for seams)")
