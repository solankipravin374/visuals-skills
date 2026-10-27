"""/zig-zag-graph - a glowing up-trend line draws itself across the frame (time it to your finger sweep), then a
"+300%" tag springs in at the top.

  python zig_zag_graph.py --in clip.mp4 --start 79.9 --dur 3.3 --out zig.mp4 --draw 0.35,1.85 --label "+300%"
  python zig_zag_graph.py ... --nodes "160,1330;280,1185;385,1262;505,1080;615,1150;735,945;835,1012;945,752"
"""
import math, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visuals-core"))
import vfx

ap = vfx.common_args(__doc__)
ap.add_argument("--nodes", help="x,y;x,y;... points of the line (default: an auto zig-zag inside --box)")
ap.add_argument("--box", help="x0,y0,x1,y1 area for the auto zig-zag (default: middle of the frame)")
ap.add_argument("--points", type=int, default=8, help="node count for the auto zig-zag")
ap.add_argument("--draw", default="0.35,1.85", help="local start,end time of the line drawing")
ap.add_argument("--label", default="+300%", help="tag text ('' for none)")
ap.add_argument("--color", default="#22C55E")
ap.add_argument("--font", help="TTF/OTF for the tag")
a = vfx.parse(ap)

W, H = vfx.size_of(a.size); U = W / 1080
if a.nodes:
    NODES = vfx.pts(a.nodes)
else:
    x0, y0, x1, y1 = vfx.pt(a.box) if a.box else (0.15 * W, 0.39 * H, 0.875 * W, 0.695 * H)
    n = a.points
    NODES = []
    for k in range(n):
        f = k / (n - 1)
        zig = 0 if k in (0, n - 1) else (0.15 if k % 2 else -0.05) * (y1 - y0)   # odd points dip, even points lift
        y = y1 - (y1 - y0) * f ** 1.15 + zig
        NODES.append((x0 + (x1 - x0) * f, y))
T0, T1 = vfx.pt(a.draw)
C = vfx.hexc(a.color)
seg = [math.hypot(NODES[i][0] - NODES[i - 1][0], NODES[i][1] - NODES[i - 1][1]) for i in range(1, len(NODES))]
TOTAL = sum(seg)
FLOOR = max(p[1] for p in NODES) + 60 * U
TAG = vfx.sticker([(a.label, 92 * U, "#FFFFFF", True, None, a.font)], bg=a.color, pad=(int(30 * U), int(10 * U)),
                  radius=int(26 * U), border=max(2, int(5 * U)), shadow=(int(8 * U), int(9 * U))) if a.label else None

def partial(p):
    rem = p * TOTAL; out = [NODES[0]]
    for i in range(1, len(NODES)):
        if rem <= 0: break
        k = min(1.0, rem / seg[i - 1])
        out.append((NODES[i - 1][0] + (NODES[i][0] - NODES[i - 1][0]) * k, NODES[i - 1][1] + (NODES[i][1] - NODES[i - 1][1]) * k))
        rem -= seg[i - 1]
    return out

def render(frame, t, i):
    out = frame.astype(np.float32)
    if t < T0 - 0.02: return out
    p = 0.5 - 0.5 * math.cos(math.pi * vfx.clamp((t - T0) / (T1 - T0)))     # ease in-out sine
    pts = partial(p); P = np.int32([[round(x), round(y)] for x, y in pts])
    # area under the line, fading down
    area = np.zeros((H, W), np.float32)
    cv2.fillPoly(area, [np.int32(list(P) + [[P[-1][0], FLOOR], [P[0][0], FLOOR]])], 1.0, cv2.LINE_AA)
    grad = np.clip((FLOOR - np.arange(H, dtype=np.float32)) / (FLOOR - min(y for _, y in NODES) + 1), 0, 1)[:, None]
    a_ = area * grad * 0.35
    out = out * (1 - a_[..., None]) + C * a_[..., None]
    # glow, body, highlight
    glow = np.zeros((H, W), np.float32); cv2.polylines(glow, [P], False, 1.0, int(22 * U), cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), 9 * U) * 0.85
    out = out * (1 - glow[..., None]) + C * glow[..., None]
    cv2.polylines(out, [P], False, tuple(float(c) for c in C), int(13 * U), cv2.LINE_AA)
    cv2.polylines(out, [P], False, (244, 255, 239), max(1, int(4 * U)), cv2.LINE_AA)
    for x, y in NODES[:len(pts) - 1]:
        cv2.circle(out, (int(x), int(y)), int(10 * U), (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(out, (int(x), int(y)), int(10 * U), tuple(float(c) for c in C), max(1, int(5 * U)), cv2.LINE_AA)
    done = p >= 0.999
    hx, hy = pts[-1]
    if not done:
        r = int((16 + 3 * math.sin(t * 20)) * U)
        cv2.circle(out, (int(hx), int(hy)), r, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(out, (int(hx), int(hy)), r, tuple(float(c) for c in C), max(1, int(6 * U)), cv2.LINE_AA)
    else:                                                                    # arrow head
        (ax, ay), (bx, by) = NODES[-2], NODES[-1]
        ang = math.atan2(by - ay, bx - ax); L = 44 * U
        for s in (2.5, -2.5):
            cv2.line(out, (int(bx), int(by)), (int(bx + L * math.cos(ang + s)), int(by + L * math.sin(ang + s))),
                     tuple(float(c) for c in C), int(13 * U), cv2.LINE_AA)
        if TAG is not None:
            lab = vfx.spring(t - T1 - 0.01, 10, 160)
            vfx.over(out, TAG, bx - 40 * U, by - 70 * U, lab, 6 - (1 - lab) * 10, 1.0, anchor=(0.8, 1.0))
    return out

vfx.run(a, render)
