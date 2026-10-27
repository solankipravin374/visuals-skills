"""/zooming - an exponential push into one point on the screen (e.g. a mascot's eye), through into a tunnel of flying
code, hold, then pull all the way back out.

  python zooming.py --in clip.mp4 --start 46.2 --dur 3.6 --out zoom.mp4 --target 894.6,1170.2 \
      --center-icon claude.svg

Renders from the source's full resolution, so a 4K phone clip stays sharp much deeper than a 1080p one.
"""
import math, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visuals-core"))
import vfx

ap = vfx.common_args(__doc__)
ap.add_argument("--target", required=True, help="x,y (output pixels) to dive into")
ap.add_argument("--push", type=float, default=1.15, help="seconds to push in (and to pull out)")
ap.add_argument("--max-zoom", type=float, default=2400.0, help="zoom factor at the deepest point")
ap.add_argument("--tunnel-from", type=float, default=60.0, help="zoom factor where the code tunnel starts fading in (fully in at 10x that)")
ap.add_argument("--code", help="text file, one code line per line (default: built-in lines)")
ap.add_argument("--center-icon", help="PNG/SVG spinning in the middle of the tunnel")
ap.add_argument("--glow", default="#D97757", help="glow colour of the centre icon")
a = vfx.parse(ap)

W, H = vfx.size_of(a.size)
U = W / 1080
TX, TY = vfx.pt(a.target)
CODE = [l.rstrip("\n") for l in open(a.code, encoding="utf-8")] if a.code else [
    "skill.run('/zooming')", "const eye = mascot.focus()", "await zoom({ into: 'pupil' })", "export const magic = () => {}",
    "if (frame > 30) dive()", "for (const line of story)", "render(reel, { fps: 30 })", "git commit -m 'visuals'",
    "npm run effects", "return <Orbit icons={5} />", "dust.from(laptop)", "paper.cut(frame)", "graph.up('+300%')",
    "yield* imagine()", "0101 1101 0110", "useCurrentFrame()", "spring({ damping: 12 })", "skills.load('/visuals')",
    "while (curious) watch()", "<Directed by='you' />"]
COLS = ["#D97757", "#F5E9DA", "#7CE3A6", "#9CC7FF"]
F = vfx.mono(40 * U)
SPR = []
for i in range(34):
    c = COLS[i % 4]
    pd = int(40 * U)                                       # room for the glow blur, or it clips into a box
    t = cv2.copyMakeBorder(vfx.text_rgba(CODE[i % len(CODE)], F, c), pd, pd, pd, pd, cv2.BORDER_CONSTANT, value=0).astype(np.float32)
    g = np.zeros_like(t); g[..., :3] = vfx.hexc(c); g[..., 3] = cv2.GaussianBlur(t[..., 3], (0, 0), 12 * U) * 0.9
    SPR.append((g, t))
ICON = None
if a.center_icon:
    ICON = vfx.load_rgba(a.center_icon, int(190 * U)).astype(np.float32)
    gl = np.zeros((int(420 * U), int(420 * U), 4), np.float32); r = gl.shape[0] // 2
    yy, xx = np.mgrid[0:gl.shape[0], 0:gl.shape[1]]
    gl[..., :3] = vfx.hexc(a.glow); gl[..., 3] = np.clip(1 - np.hypot(xx - r, yy - r) / r, 0, 1) ** 2 * 230
    GLOW = gl
LOG_MAX = math.log(a.max_zoom)

def cam(t):
    if t < a.push: k = vfx.ease(t / a.push)
    elif t < a.dur - a.push: k = 1.0
    else: k = 1 - vfx.ease((t - (a.dur - a.push)) / a.push)
    s = math.exp(LOG_MAX * k ** 1.6)
    w = min(1.0, (s - 1) / 3.0)                           # drift the centre onto the target as the push starts
    return W / 2 + (TX - W / 2) * w, H / 2 + (TY - H / 2) * w, s

def warp(img, cx, cy, s):
    nh, nw = img.shape[:2]
    f = s * W / nw                                         # native px -> output px
    if f < 1:                                              # downscale first for a clean (alias-free) wide shot
        small = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        M = np.float32([[1, 0, W / 2 - cx * s], [0, 1, H / 2 - cy * s]])
        return cv2.warpAffine(small, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    M = np.float32([[f, 0, W / 2 - cx * s], [0, f, H / 2 - cy * s]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def tunnel(t):
    out = np.zeros((H, W, 3), np.float32); out[:] = (8, 9, 11)
    ov = out.copy()
    for i in range(26):
        ang = i * 0.2417 * 2 * math.pi; k = (t * 2.2 + i * 0.137) % 1
        r0 = (120 + k * 380) * U; r1 = r0 + (260 + k * 700) * U
        p0 = (int(W / 2 + math.cos(ang) * r0), int(H / 2 + math.sin(ang) * r0))
        p1 = (int(W / 2 + math.cos(ang) * r1), int(H / 2 + math.sin(ang) * r1))
        a_ = (1 - k) * 0.45
        cv2.line(ov, p0, p1, (220 * a_ + 8, 236 * a_ + 9, 255 * a_ + 11), max(1, int(3 * U)), cv2.LINE_AA)
    out = np.maximum(out, ov)
    for i, (g, s_) in enumerate(SPR):
        seed = (i * 9301 + 49297) % 233280 / 233280
        ang = i * 2.39996 + seed * 0.6
        zc = (t * 1.35 + i / 34) % 1
        z = 1.6 - 1.5 * zc; R = 210 * U / z
        x, y = W / 2 + math.cos(ang) * R, H / 2 + math.sin(ang) * R * 1.35
        al = vfx.clamp(zc * 3) * vfx.clamp((1 - zc) * 4)
        vfx.over(out, g, x, y, 0.5 / z, 0, al); vfx.over(out, s_, x, y, 0.5 / z, 0, al)
    if ICON is not None:
        vfx.over(out, GLOW, W / 2, H / 2, 1 + 0.08 * math.sin(t * 14))
        vfx.over(out, ICON, W / 2, H / 2, 1 + 0.08 * math.sin(t * 14), -t * 90)
    return out

def render(frame, t, i):
    cx, cy, s = cam(t)
    inside = vfx.ease(math.log(s / a.tunnel_from) / math.log(10))
    if inside >= 1: return tunnel(t)
    img = warp(frame, cx, cy, min(s, a.tunnel_from * 10)).astype(np.float32)
    if inside > 0: img = img * (1 - inside) + tunnel(t) * inside
    return img

vfx.run(a, render, native=True)
