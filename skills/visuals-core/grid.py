"""Write a still with a labelled coordinate grid, so you (or Claude) can read off points for the effect flags.
  python grid.py --in clip.mp4 --t 3.2 --out grid.jpg [--size 1080x1920] [--step 100] [--crop y0,y1]
"""
import argparse, os, sys
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vfx

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--t", type=float, default=0.0)
ap.add_argument("--out", required=True); ap.add_argument("--size", default="1080x1920")
ap.add_argument("--step", type=int, default=100); ap.add_argument("--crop", help="only rows y0,y1 (for a closer look)")
a = ap.parse_args()
vfx.need()
img = vfx.grab(a.inp, a.t, vfx.size_of(a.size))
h, w = img.shape[:2]
for y in range(0, h, a.step):
    cv2.line(img, (0, y), (w, y), (0, 0, 255), 1); cv2.putText(img, str(y), (4, y - 4), 0, 0.8, (0, 0, 255), 2)
for x in range(0, w, a.step):
    cv2.line(img, (x, 0), (x, h), (255, 0, 0), 1); cv2.putText(img, str(x), (x + 3, 28), 0, 0.8, (255, 0, 0), 2)
if a.crop:
    y0, y1 = (int(v) for v in a.crop.split(",")); img = img[y0:y1]
cv2.imwrite(a.out, img); print("wrote", a.out)
