"""Make the laptop mask every "behind the lid" effect uses, plus a red overlay to check it.
  python mask.py --in clip.mp4 --t 2.0 --out laptop_mask.png [--size 1080x1920] [--v-max 95] [--min-y 700]
Pick a time where no hand covers the laptop. White = laptop (body + screen + stickers).
"""
import argparse, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vfx

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--t", type=float, default=0.0)
ap.add_argument("--out", required=True); ap.add_argument("--size", default="1080x1920")
ap.add_argument("--v-max", type=int, default=95, help="max HSV value (brightness) of laptop-body pixels")
ap.add_argument("--min-y", type=int, help="ignore everything above this row (default 35%% of the height)")
a = ap.parse_args()
vfx.need()
img = vfx.grab(a.inp, a.t, vfx.size_of(a.size))
m = vfx.laptop_mask(img, a.v_max, a.min_y)
cv2.imwrite(a.out, m)
chk = img.copy(); chk[m > 0] = (chk[m > 0] * 0.5 + np.array([0, 0, 255]) * 0.5).astype(np.uint8)
x0, y0, x1, y1 = vfx.bbox(m)
cv2.rectangle(chk, (x0, y0), (x1, y1), (0, 255, 255), 2)
p = os.path.splitext(a.out)[0] + "_check.jpg"; cv2.imwrite(p, chk)
print(f"wrote {a.out} and {p}; laptop bbox x {x0}-{x1}, y {y0}-{y1} (lid top = {y0})")
