"""/share-comment - the end card: a sticker drops in from the top and bounces ("COMMENT 'VISUALS' to get ..."), then
a follow pill pops in under it.

  python share_comment.py --in clip.mp4 --start 113.0 --dur 4.5 --out cta.mp4 --keyword VISUALS \
      --sub "to get all 8 effect skills" --highlight "8 effect skills" --follow "Follow @aiwithpravin"
  python share_comment.py --in clip.mp4 --start 113.0 --dur 4.5 --out cta.mp4 --bg plate.png ...   # still background

The background is your clip (or --bg image), the audio is the clip's audio from --start.
"""
import math, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visuals-core"))
import vfx

ap = vfx.common_args(__doc__)
ap.add_argument("--keyword", default="VISUALS"); ap.add_argument("--top", default="COMMENT")
ap.add_argument("--sub", default="to get all 8 effect skills"); ap.add_argument("--highlight", default="8 effect skills",
                help="part of --sub on a yellow highlight ('' for none)")
ap.add_argument("--follow", default="", help="pill text under the sticker, e.g. 'Follow @you' ('' for none)")
ap.add_argument("--bg", help="still image instead of the video background")
ap.add_argument("--accent", default="#D97757"); ap.add_argument("--ink", default="#1C1A17")
ap.add_argument("--y", type=float, help="sticker top y (default 29%% of the height)")
ap.add_argument("--font", help="TTF/OTF for the sticker")
a = vfx.parse(ap)

W, H = vfx.size_of(a.size); U = W / 1080
BG = cv2.resize(cv2.imread(a.bg), (W, H)).astype(np.float32) if a.bg else None
f_top, f_key, f_sub = vfx.font(64 * U, a.font), vfx.font(168 * U, a.font), vfx.font(50 * U, a.font, bold=False)
rows = [vfx.text_rgba(a.top, f_top, a.ink), vfx.text_rgba(f"“{a.keyword}”", f_key, a.accent, stack_shadow=(int(5 * U), int(5 * U), 1, a.ink))]
if a.sub:
    pre, hl, post = (a.sub.partition(a.highlight) if a.highlight and a.highlight in a.sub else (a.sub, "", ""))
    parts = [vfx.text_rgba(t, f_sub, a.ink) for t in (pre.rstrip(), hl, post.lstrip()) if t]
    if hl:
        i = [t for t in (pre.rstrip(), hl, post.lstrip()) if t].index(hl)
        p = parts[i]; pad = int(10 * U)
        bgc = np.zeros((p.shape[0], p.shape[1] + 2 * pad, 4), np.uint8); bgc[..., :3] = vfx.hexc("#FFE14D").astype(np.uint8); bgc[..., 3] = 255
        bgc[:, pad:pad + p.shape[1]] = (bgc[:, pad:pad + p.shape[1]] * (1 - p[..., 3:4] / 255) + p * (p[..., 3:4] / 255)).astype(np.uint8)
        bgc[..., 3] = 255; parts[i] = bgc
    gap = int(14 * U); hh = max(p.shape[0] for p in parts)
    line = np.zeros((hh, sum(p.shape[1] for p in parts) + gap * (len(parts) - 1), 4), np.uint8); x = 0
    for p in parts:
        line[(hh - p.shape[0]) // 2:(hh - p.shape[0]) // 2 + p.shape[0], x:x + p.shape[1]] = p; x += p.shape[1] + gap
    rows.append(line)
# assemble the card: cream body, ink border, solid offset shadow
padx, pady, bd, rad = int(54 * U), int(30 * U), max(2, int(7 * U)), int(44 * U)
CW = max(r.shape[1] for r in rows) + 2 * padx; CH = sum(r.shape[0] for r in rows) + 2 * pady + int(8 * U) * (len(rows) - 1)
sx, sy = int(12 * U), int(14 * U)
card = np.zeros((CH + sy, CW + sx, 4), np.uint8)
def rr(img, x0, y0, x1, y1, r, col):
    from PIL import Image, ImageDraw
    im = Image.fromarray(img); ImageDraw.Draw(im).rounded_rectangle((x0, y0, x1, y1), r, fill=col); img[:] = np.array(im)
rr(card, sx, sy, CW + sx - 1, CH + sy - 1, rad, tuple(int(v) for v in vfx.hexc(a.ink)) + (255,))
rr(card, 0, 0, CW - 1, CH - 1, rad, tuple(int(v) for v in vfx.hexc(a.ink)) + (255,))
rr(card, bd, bd, CW - 1 - bd, CH - 1 - bd, rad - bd, (255, 255, 255, 255))
y = pady
for r in rows:
    x = (CW - r.shape[1]) // 2; al = r[..., 3:4] / 255.0
    card[y:y + r.shape[0], x:x + r.shape[1], :3] = (card[y:y + r.shape[0], x:x + r.shape[1], :3] * (1 - al) + r[..., :3] * al).astype(np.uint8)
    y += r.shape[0] + int(8 * U)
CARD = card.astype(np.float32)
SOFT = vfx.shadow_rgba(card, blur=30 * U, opacity=0.18, dy=int(30 * U))
PILL = vfx.pill(a.follow, 54 * U, a.accent, "#FFFFFF", a.ink, a.font) if a.follow else None
TOP = a.y if a.y is not None else 0.29 * H

def render(frame, t, i):
    out = BG.copy() if BG is not None else frame.astype(np.float32)
    drop = vfx.spring(t - 0.05, 8, 95, 1.1)
    wob = math.sin(t * 7) * 3 * math.exp(-t * 1.6)
    cy = TOP + CARD.shape[0] / 2 + (1 - drop) * -1250 * U
    vfx.over(out, SOFT, W / 2, cy, 1.0, 4 - wob)
    vfx.over(out, CARD, W / 2, cy, 1.0, 4 - wob)
    if PILL is not None:
        f2 = vfx.spring(t - 1.05, 10, 170)
        vfx.over(out, PILL, W / 2, TOP + CARD.shape[0] + 110 * U, 0.6 + 0.4 * f2, -3, min(1.0, f2))
    return out

vfx.run(a, render)
