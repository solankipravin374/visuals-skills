"""/paper - the real laptop, its screen and your hand turn into a layered paper-craft diorama (flat colour sheets,
thick drop shadows, cut-edge rims, fibre texture, 12 fps stop-motion boil). A torn-paper wipe reveals it, the sky,
sun and clouds drop in on strings, mountains + hills + trees pop up from behind the lid, then it tears away again.

  python paper.py --in clip.mp4 --start 34.4 --dur 2.9 --out paper.mp4 --ref-time 30.9
  python paper.py ... --keyboard-rows rows.json --trackpad "266,1702;600,1698;632,1888;243,1892" \
                      --cards "[[385,1180,918,1326,16]]" --hot 385,1180,918,1326 --sidebar-x 357

--ref-time: a frame where the hand is NOT on the laptop. It is the source of the paper laptop and the reference the
hand is keyed against, so the camera must not move.
"""
import json, math, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visuals-core"))
import vfx

PAL = dict(
    sky_top="#2F6290", sky_bot="#A3D3E2", sun="#F6C343", sun_in="#FCE29A", sun_ring="#F0A63A", string="#F6F2EA",
    cloud="#FBF8F2", cloud_sh="#CFDCE8", mtn_l="#5C8AA8", mtn_d="#3E6A88", snow="#F5F2EC",
    hill1="#3C8A4F", hill2="#5DAA58", hill3="#84C267", tree="#2C7444", tree2="#45A158", trunk="#7A4E2D", ground="#9BCB69",
    lid="#22324A", screen="#FBF4E3", side="#F0E4CC", card="#FFFFFF", pill="#8F9DB1", pill_hot="#D97757", task="#3A4C66",
    deck="#2C3E56", key="#435C7E", pad="#364B68", skin="#B9774C", skin_hi="#D0915F", puff_back="#F2BC58", puff="#FBEAC8")

def rise(t, t0, t1, d):
    """offset that starts at d and settles to 0 with a little overshoot (pop-up book)"""
    return d * (1 - vfx.ease_out_back((t - t0) / (t1 - t0)))

def shift(m, dx, dy):
    if dx == 0 and dy == 0: return m
    h, w = m.shape[:2]
    return cv2.warpAffine(m, np.float32([[1, 0, dx], [0, 1, dy]]), (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

def lift(m, dx, dy):
    """move a scenery sheet; edge rows repeat so ground-anchored sheets never open a gap when they overshoot"""
    h, w = m.shape[:2]
    return cv2.warpAffine(m, np.float32([[1, 0, dx], [0, 1, dy]]), (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def rrect(img, x0, y0, x1, y1, r, v=255):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1); r = int(max(1, min(r, (x1 - x0) / 2, (y1 - y0) / 2)))
    cv2.rectangle(img, (x0 + r, y0), (x1 - r, y1), v, -1); cv2.rectangle(img, (x0, y0 + r), (x1, y1 - r), v, -1)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)): cv2.circle(img, (cx, cy), r, v, -1, cv2.LINE_AA)

class Group:
    """Layer stack with shadows: final = bg * D * (1 - A) + C. Each layer only touches its own bounding box."""
    def __init__(s, tex, U):
        s.T, s.U = tex, U
        H, W = tex.shape[:2]
        s.C = np.zeros((H, W, 3), np.float32); s.A = np.zeros((H, W), np.float32); s.D = np.ones((H, W), np.float32)
    def add(s, m, col, grad=0.10, sh=None, rim=2):
        x, y, w, h = cv2.boundingRect((m > 0.004).astype(np.uint8))
        if w == 0: return
        H, W = m.shape
        if sh: sh = (sh[0] * s.U, sh[1] * s.U, max(0.5, sh[2] * s.U), sh[3])
        rim = max(1, round(rim * s.U)) if rim else 0
        pad = rim + 2 + (int(abs(sh[0]) + abs(sh[1]) + 3 * sh[2]) if sh else 0)
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(W, x + w + pad), min(H, y + h + pad)
        R = (slice(y0, y1), slice(x0, x1)); mm = m[R]
        c = vfx.hexc(col) if isinstance(col, str) else col
        g = 1 + grad * (0.5 - np.clip((np.arange(y0, y1) - y) / max(1, h), 0, 1))
        cimg = c[None, None, :] * g[:, None, None] * s.T[R]
        if sh:
            f = 1 - sh[3] * cv2.GaussianBlur(shift(mm, sh[0], sh[1]), (0, 0), sh[2]) * (1 - mm)
            s.C[R] *= f[..., None]; s.D[R] *= f
        if rim:
            hi = np.clip(mm - shift(mm, rim, rim), 0, 1); lo = np.clip(mm - shift(mm, -rim, -rim), 0, 1)
            cimg = cimg * (1 + 0.22 * hi - 0.20 * lo)[..., None]
        s.C[R] = s.C[R] * (1 - mm[..., None]) + cimg * mm[..., None]; s.A[R] = s.A[R] * (1 - mm) + mm
    def over(s, bg):
        return bg * (s.D * (1 - s.A))[..., None] + s.C

class PaperWorld:
    def __init__(s, ref, laptop_mask, hinge_y=None, rows=None, trackpad=None, cards=None, hot=None, sidebar_x=None, webcam=None):
        H, W = ref.shape[:2]; s.W, s.H = W, H; U = s.U = W / 1080
        s.YY, s.XX = np.mgrid[0:H, 0:W].astype(np.float32)
        rng = np.random.default_rng(7)
        s.tex, s.boil = [], []
        for _ in range(3):                                   # 3 stop-motion phases, swapped every 2 frames
            n = cv2.GaussianBlur(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (0, 0), 1.0) * 0.6
            n += cv2.GaussianBlur(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (0, 0), 7) * 1.4
            fib = np.zeros((H // 2, W // 2), np.float32)
            for _ in range(1100):
                x, y = rng.integers(0, W // 2), rng.integers(0, H // 2); an = rng.uniform(0, np.pi); L = rng.integers(4, 15)
                cv2.line(fib, (x, y), (int(x + L * np.cos(an)), int(y + L * np.sin(an))), float(rng.uniform(0.5, 1.2)), 1)
            n += cv2.GaussianBlur(fib, (3, 3), 0) * 1.4
            s.tex.append(1 + 0.04 * cv2.resize(n, (W, H))[..., None])
            s.boil.append(cv2.resize(rng.uniform(-1, 1, (H // 24, W // 24)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC))
        lap = (laptop_mask > 127).astype(np.uint8)
        gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY); hsv = cv2.cvtColor(ref, cv2.COLOR_BGR2HSV)
        def soft(binm, sig=2.0): return cv2.GaussianBlur(binm.astype(np.float32) / max(1, binm.max()), (0, 0), sig * U)
        k3 = lambda n: np.ones((max(1, round(n * U)),) * 2, np.uint8)
        # ---- laptop ----------------------------------------------------------------------------------------
        screen = vfx.screen_mask(ref, lap)
        if not screen.any(): sys.exit("no bright screen found inside the laptop mask")
        screen = cv2.erode(screen, k3(5))
        sx0, sy0, sx1, sy1 = vfx.bbox(screen)
        s.horizon = vfx.bbox(lap)[1]
        hinge = int(hinge_y if hinge_y else sy1 + 60 * U)
        s.ground_y = hinge
        lid = lap.copy(); lid[hinge:] = 0
        deck = lap.copy(); deck[:hinge] = 0
        inner = cv2.erode(screen, k3(15))
        task = screen.copy(); task[:sy1 - int(36 * U)] = 0
        side = np.zeros((H, W), np.uint8)
        if sidebar_x: side[:, :int(sidebar_x)] = 255; side &= screen; side[sy1 - int(36 * U):] = 0
        # text -> paper strips: dark glyphs merged into words/lines, each drawn as a rounded pill
        txt = ((gray < 165) & (hsv[..., 1] < 70) & (inner > 0)).astype(np.uint8) * 255
        txt[sy1 - int(40 * U):] = 0
        txt = cv2.morphologyEx(txt, cv2.MORPH_CLOSE, np.ones((max(1, round(5 * U)), max(1, round(15 * U))), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(txt)
        pills, hotm = np.zeros((H, W), np.uint8), np.zeros((H, W), np.uint8)
        for i in range(1, n):
            x, y, w, h, ar = st[i]
            if w < 6 * U or h < 3 * U or ar < 12 * U * U or h > 40 * U: continue
            cy = y + h / 2; ph = min(max(h, 7 * U), 12 * U)
            tgt = hotm if (hot and hot[0] < x < hot[2] and hot[1] < cy < hot[3]) else pills
            rrect(tgt, x, cy - ph / 2, x + max(w, ph), cy + ph / 2, ph / 2)
        cardm = np.zeros((H, W), np.uint8)
        for c in (cards or []): rrect(cardm, *c)
        # coloured UI bits (icons, logos) -> small coloured chips
        s.chips = []
        col = ((hsv[..., 1] > 90) & (hsv[..., 2] > 80) & (screen > 0)).astype(np.uint8)
        col = cv2.morphologyEx(col, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(col)
        for i in range(1, n):
            x, y, w, h, ar = st[i]
            if ar < 14 * U * U or (ar < 160 * U * U and y < sy1 - 40 * U): continue   # drop cursors and specks
            m = (lab == i).astype(np.uint8)
            c = cv2.cvtColor(np.uint8([[ref[m > 0].mean(0)]]), cv2.COLOR_BGR2HSV)[0, 0].astype(np.float32)
            c[1] = min(255, c[1] * 1.15); c[2] = min(255, max(c[2], 170))
            hm = np.zeros((H, W), np.uint8); cv2.fillConvexPoly(hm, cv2.convexHull(cv2.findNonZero(m)), 255)
            s.chips.append((soft(cv2.dilate(hm, np.ones((3, 3), np.uint8)), 0.8), cv2.cvtColor(np.uint8([[c]]), cv2.COLOR_HSV2BGR)[0, 0].astype(np.float32)))
        # key caps: measured rows if given, else each key's bottom shadow edge (finds most keys on a dark keyboard)
        keys = np.zeros((H, W), np.uint8)
        if rows:
            for yb, xl, xr, kh, units in rows:
                u = (xr - xl) / sum(units); x = xl
                for w in units:
                    if w != 0.25: rrect(keys, x + 3 * U, yb - kh, x + w * u - 3 * U, yb, 5 * U)
                    x += w * u
        else:
            g = gray.astype(np.float32)
            ke = (((cv2.GaussianBlur(g, (0, 0), 9 * U) - g) > 2.5) & (deck > 0)).astype(np.uint8) * 255
            ke[:hinge + int(40 * U)] = 0; ke[hinge + int(0.13 * H):] = 0
            ke = cv2.morphologyEx(ke, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            n, lab, st, _ = cv2.connectedComponentsWithStats(ke)
            for i in range(1, n):
                x, y, w, h, ar = st[i]
                if 250 * U * U < ar < 9000 * U * U and 12 * U < w < 420 * U and h < 60 * U:
                    rrect(keys, x + 1, y + h - 2 - 22 * U, x + w - 2, y + h - 2, 5 * U)
        padm = np.zeros((H, W), np.uint8)
        if trackpad:
            cv2.fillConvexPoly(padm, np.int32(trackpad), 255)
            padm = (cv2.GaussianBlur(padm, (0, 0), 6 * U) > 127).astype(np.uint8) * 255
        s.stick = []
        sm = ((gray > 115) & (deck > 0)).astype(np.uint8); sm[:hinge + int(0.13 * H)] = 0
        n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(sm, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)))
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] < 1500 * U * U: continue
            m = (lab == i).astype(np.uint8)
            c = ref[m > 0].mean(0).astype(np.float32)
            c = c + (np.array([226, 233, 238], np.float32) - c) * (0.55 if c.max() - c.min() < 40 else 0.15)
            hm = np.zeros((H, W), np.uint8); cv2.fillConvexPoly(hm, cv2.convexHull(cv2.findNonZero(m)), 255)
            s.stick.append((soft(hm, 1.5), c))
        cam = np.zeros((H, W), np.uint8)
        if webcam: cv2.circle(cam, (int(webcam[0]), int(webcam[1])), int(6 * U), 255, -1, cv2.LINE_AA)
        s.lap = dict(lid=soft(lid, 2.5), deck=soft(deck, 2.5), screen=soft(screen, 1.5), side=soft(side, 1.0), task=soft(task, 1.0),
                     cards=soft(cardm, 1.2), pills=soft(pills, 0.7), hot=soft(hotm, 0.7), keys=soft(keys, 1.0), pad=soft(padm, 1.5),
                     cam=soft(cam, 0.8))
        s.lap_cache = {}
        # ---- scenery: placed relative to the lid top (horizon) and the frame width ----------------------------
        hz = s.horizon; X = lambda v: v * U; Y = lambda v: hz + v * U
        k = np.clip(s.YY / max(1, hz + 25 * U), 0, 1)[..., None]
        sky = vfx.hexc(PAL["sky_top"]) * (1 - k) + vfx.hexc(PAL["sky_bot"]) * k
        s.sky = [sky * t for t in s.tex]
        s.mtns = []
        for px, py, hw in ((150, -265, 260), (430, -330, 300), (735, -375, 290), (1000, -285, 250)):
            px, py, hw, base = X(px), Y(py), X(hw), Y(225)
            L = np.zeros((H, W), np.uint8); R = np.zeros((H, W), np.uint8); S = np.zeros((H, W), np.uint8)
            mid = px + 0.18 * (base - py)
            cv2.fillPoly(L, [np.int32([[px, py], [px - hw, base], [mid, base]])], 255)
            cv2.fillPoly(R, [np.int32([[px, py], [mid, base], [px + hw, base]])], 255)
            d = 62 * U; kx = hw / (base - py) * d
            cv2.fillPoly(S, [np.int32([[px, py], [px - kx, py + d], [px - kx * 0.45, py + d - 14 * U], [px, py + d + 8 * U],
                                       [px + kx * 0.5, py + d - 12 * U], [px + kx, py + d]])], 255)
            s.mtns.append((soft(L, 2.2), soft(R, 2.2), soft(S, 1.8)))
        xr = s.XX[0] / W * 2 * np.pi
        def hill(base, amp, ph, freq):
            top = Y(base) + amp[0] * U * np.sin(xr * freq[0] + ph) + amp[1] * U * np.sin(xr * freq[1] + ph * 1.7)
            return soft((s.YY > top[None, :]).astype(np.uint8), 2.0)
        s.hills = [hill(-85, (34, 14), 0.6, (1.3, 3.1)), hill(-30, (26, 11), 2.1, (1.7, 3.7)), hill(30, (18, 9), 4.0, (2.1, 4.3))]
        s.trees = []
        for tx, crowns in ((32, [(30, -225, 98), (-40, -160, 80), (100, -155, 74)]), (1046, [(1050, -185, 102), (980, -115, 72), (1115, -120, 82)])):
            tr = np.zeros((H, W), np.uint8); cv2.rectangle(tr, (int(X(tx - 13)), int(Y(-175))), (int(X(tx + 13)), int(hinge + 30 * U)), 255, -1)
            cr = np.zeros((H, W), np.uint8); hi = np.zeros((H, W), np.uint8)
            for cx, cy, r in crowns:
                cv2.circle(cr, (int(X(cx)), int(Y(cy))), int(X(r)), 255, -1, cv2.LINE_AA)
                cv2.circle(hi, (int(X(cx - r * 0.18)), int(Y(cy - r * 0.2))), int(X(r * 0.7)), 255, -1, cv2.LINE_AA)
            s.trees.append((soft(tr, 1.5), soft(cr, 2.0), soft(hi, 2.0)))
        gtop = hinge + 10 * U * np.sin(s.XX[0] / W * 9.0)
        s.ground = soft((s.YY > gtop[None, :]).astype(np.uint8), 2.0)
        def cloud(cx, cy, sc):
            cx, cy, sc = X(cx), Y(cy), sc * U
            m = np.zeros((H, W), np.uint8)
            for dx, dy, r in ((-112, 8, 60), (-48, -30, 80), (36, -44, 92), (112, -2, 66), (0, 12, 72)):
                cv2.circle(m, (int(cx + dx * sc), int(cy + dy * sc)), int(r * sc), 255, -1, cv2.LINE_AA)
            rrect(m, cx - 168 * sc, cy, cx + 172 * sc, cy + 62 * sc, 30 * sc)
            return soft(m, 2.0), (int(cx + 20 * sc), int(cy - 130 * sc))
        s.clouds = [cloud(230, -355, 1.0) + (0.48, 0.0), cloud(615, -235, 0.72) + (0.58, 1.9), cloud(965, -140, 0.6) + (0.66, 3.6)]
        s.SUN = (X(842), Y(-423))
        def puff(base, r0, seed):
            m = np.zeros((H, W), np.uint8); r = np.random.default_rng(seed); x = int(-40 * U)
            while x < W + 60 * U:
                rr = int(r.uniform(0.8, 1.25) * r0 * U); cv2.circle(m, (x, int(base + r.uniform(-12, 12) * U)), rr, 255, -1, cv2.LINE_AA); x += int(rr * 1.25)
            m[int(base):] = 255; return soft(m, 2.0)
        s.puffs = [puff(H - 35 * U, 62, 2), puff(H + 2 * U, 58, 5)]

    def cut(s, sf, k, amt=0.10):
        return np.clip((sf + s.boil[k] * amt - 0.5) * 6 + 0.5, 0, 1)

    def laptop(s, k):
        if k in s.lap_cache: return s.lap_cache[k]
        L = s.lap; G = Group(s.tex[k], s.U)
        for key, colr, amt, grad, sh, rim in (
                ("lid", "lid", 0.10, 0.10, (12, 18, 14, 0.45), 3), ("screen", "screen", 0.05, 0.06, (3, 5, 4, 0.35), 2),
                ("side", "side", 0.0, 0.04, (2, 3, 2, 0.18), 0), ("cards", "card", 0.03, 0.05, (4, 7, 6, 0.30), 2),
                ("pills", "pill", 0.0, 0.0, (1, 2, 1.5, 0.30), 1), ("hot", "pill_hot", 0.0, 0.0, (2, 3, 1.5, 0.35), 1),
                ("task", "task", 0.0, 0.05, (0, -3, 3, 0.25), 1)):
            m = s.cut(L[key], k, amt); G.add(m, PAL[colr], grad, sh, rim)
        for sf, c in s.chips:
            m = s.cut(sf, k, 0.0); G.add(m, c, 0.0, (1, 2, 1.5, 0.35), 1)
        m = s.cut(L["cam"], k, 0.0); G.add(m, "#121A26", 0.0, None, 0)
        m = s.cut(L["deck"], k); G.add(m, PAL["deck"], 0.12, (0, -8, 10, 0.40), 3)
        m = s.cut(L["keys"], k, 0.04); G.add(m, PAL["key"], 0.08, (2, 4, 2.5, 0.55), 2)
        m = s.cut(L["pad"], k, 0.05); G.add(m, PAL["pad"], 0.08, (-2, -3, 3, 0.35), 2)
        for sf, c in s.stick:
            m = s.cut(sf, k, 0.05); G.add(m, c, 0.08, (3, 5, 4, 0.35), 2)
        s.lap_cache[k] = G
        return G

    def string(s, G, x, y_end):
        if y_end <= 0: return
        m = np.zeros((s.H, s.W), np.float32)
        cv2.line(m, (int(x), -5), (int(x), int(y_end)), 1.0, max(1, round(2 * s.U)), cv2.LINE_AA)
        G.add(m * 0.85, PAL["string"], 0.0, (4, 0, 2, 0.22), 0)

    def __call__(s, f, lt, hand):
        U = s.U; k = (f // 2) % 3; T = s.tex[k]
        out = s.sky[k].copy()
        G = Group(T, U)
        # sun on its string, scalloped ring turning slowly
        cx, cy = s.SUN[0], s.SUN[1] - rise(lt, 0.40, 1.05, 640 * U)
        th = np.linspace(0, 2 * np.pi, 240, endpoint=False)
        ring = np.zeros((s.H, s.W), np.uint8)
        rr = (128 + 11 * np.cos(14 * th + lt * 0.9)) * U
        cv2.fillPoly(ring, [np.int32(np.stack([cx + rr * np.cos(th), cy + rr * np.sin(th)], 1))], 255)
        disc = np.zeros((s.H, s.W), np.uint8); cv2.circle(disc, (int(cx), int(cy)), int(96 * U), 255, -1, cv2.LINE_AA)
        inn = np.zeros((s.H, s.W), np.uint8); cv2.circle(inn, (int(cx - 14 * U), int(cy - 14 * U)), int(64 * U), 255, -1, cv2.LINE_AA)
        s.string(G, cx, cy - 135 * U)
        for msk, c, sh in ((ring, "sun_ring", (12, 18, 12, 0.30)), (disc, "sun", (4, 6, 5, 0.30)), (inn, "sun_in", (3, 4, 4, 0.22))):
            m = s.cut(cv2.GaussianBlur(msk.astype(np.float32) / 255, (0, 0), 1.6 * U), k, 0.05); G.add(m, PAL[c], 0.08, sh)
        # mountains (lit + shaded faces, snow caps), hills, trees, ground: each rises from behind the lid
        for i, (L_, R_, S_) in enumerate(s.mtns):
            dy = rise(lt, 0.28 + 0.05 * i, 0.82 + 0.05 * i, 520 * U)
            for sf, c, sh in ((L_, "mtn_l", (8, 10, 9, 0.30)), (R_, "mtn_d", (8, 10, 9, 0.30)), (S_, "snow", (2, 4, 3, 0.25))):
                m = s.cut(lift(sf, 0, dy), k); G.add(m, PAL[c], 0.10, sh)
        for i, (sf, c) in enumerate(zip(s.hills, ("hill1", "hill2", "hill3"))):
            dy = rise(lt, 0.36 + 0.06 * i, 0.88 + 0.06 * i, 340 * U)
            m = s.cut(lift(sf, 0, dy), k); G.add(m, PAL[c], 0.14, (6, 9, 9, 0.34))
        for i, (tr, cr, hi) in enumerate(s.trees):
            dy = rise(lt, 0.50 + 0.06 * i, 1.02 + 0.06 * i, 620 * U)
            for sf, c, sh in ((tr, "trunk", (6, 8, 6, 0.30)), (cr, "tree", (10, 14, 12, 0.35)), (hi, "tree2", (4, 6, 5, 0.25))):
                m = s.cut(lift(sf, 0, dy), k); G.add(m, PAL[c], 0.12, sh)
        m = s.cut(s.ground, k); G.add(m, PAL["ground"], 0.08, (4, 6, 6, 0.3))
        # clouds drop in on their strings, then bob
        for sf, (ax, ay), t0, ph in s.clouds:
            dy = -rise(lt, t0, t0 + 0.62, 760 * U) + 7 * U * math.sin(lt * 2 * math.pi * 0.55 + ph)
            s.string(G, ax, ay + dy)
            m = s.cut(lift(sf, 0, dy + 10 * U), k); G.add(m, PAL["cloud_sh"], 0.0, (10, 16, 13, 0.28))
            m = s.cut(lift(sf, 0, dy), k); G.add(m, PAL["cloud"], 0.10, (3, 5, 4, 0.20))
        out = G.over(out)
        out = s.laptop(k).over(out)
        # the hand: under-sheet + a lighter top sheet, floating above the keys
        if hand is not None and hand.any():
            hs = cv2.GaussianBlur(hand.astype(np.float32) / 255, (0, 0), 3.5 * U)
            m = np.clip((hs - 0.5) * 6 + 0.5, 0, 1)
            Hg = Group(T, U); Hg.add(m, PAL["skin"], 0.10, (16, 24, 15, 0.42), 3)
            dt = cv2.distanceTransform((hs > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
            top = cv2.GaussianBlur(shift((dt > 13 * U).astype(np.float32), -3 * U, -4 * U), (0, 0), 3.0 * U)
            mt = np.clip((top - 0.5) * 6 + 0.5, 0, 1) * m
            Hg.add(mt, PAL["skin_hi"], 0.10, (3, 5, 4, 0.25), 2)
            out = Hg.over(out)
        # foreground paper puffs rising at the bottom edge
        P = Group(T, U)
        for i, (sf, c) in enumerate(zip(s.puffs, ("puff_back", "puff"))):
            dy = rise(lt, 0.40 + 0.07 * i, 0.86 + 0.07 * i, 300 * U)
            m = s.cut(lift(sf, 8 * U * math.sin(lt * 1.7 + i * 2), dy), k); P.add(m, PAL[c], 0.06, (5, -9, 12, 0.32))
        out = P.over(out)
        vig = 1.03 - 0.07 * np.clip((s.XX - 0.35 * s.W) ** 2 / (0.83 * s.W) ** 2 + (s.YY - 0.36 * s.H) ** 2 / (0.78 * s.H) ** 2, 0, 1)
        return out * vig[..., None]

def torn_front(lt, t0, t1, W, H, reverse=False, seed=3):
    """Per-pixel coverage of a jagged diagonal tear sweeping across the frame, plus its white fibre band."""
    k = vfx.ease((lt - t0) / (t1 - t0))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rng = np.random.default_rng(seed)
    edge = (xx + 0.35 * yy) / (W + 0.35 * H)
    walk = np.cumsum(rng.normal(0, 1, H)).astype(np.float32)
    walk = cv2.GaussianBlur(walk[:, None], (0, 0), 6)[:, 0]; walk = (walk - walk.mean()) / (np.abs(walk).max() + 1e-6)
    fine = cv2.GaussianBlur(rng.normal(0, 1, (H, 1)).astype(np.float32), (0, 0), 1.2)[:, 0]
    jag = (0.035 * walk + 0.006 * fine)[:, None]
    pos = 1.08 - k * 1.16 if reverse else -0.08 + k * 1.16
    cov = (edge + jag < pos).astype(np.float32)
    band = np.exp(-((edge + jag - pos) ** 2) / (2 * 0.006 ** 2)) * (0 < k < 1)
    return cov, band

if __name__ == "__main__":
    ap = vfx.common_args(__doc__)
    ap.add_argument("--ref-time", type=float, required=True, help="source time of a frame with the hand OFF the laptop")
    ap.add_argument("--hinge-y", type=float, help="row where the lid meets the keyboard deck (default: screen bottom + 60)")
    ap.add_argument("--keyboard-rows", help="JSON (file or inline): [[bottom_y, left_x, right_x, key_h, [unit widths]], ...]; 0.25 = gap")
    ap.add_argument("--trackpad", help="x,y;x,y;x,y;x,y corners of the trackpad")
    ap.add_argument("--cards", help="JSON [[x0,y0,x1,y1,radius], ...] white UI cards that pop off the screen")
    ap.add_argument("--hot", help="x0,y0,x1,y1: text strips inside this box turn orange (e.g. your typed prompt)")
    ap.add_argument("--sidebar-x", type=float, help="x where an app sidebar ends (gets a tinted sheet)")
    ap.add_argument("--webcam", help="x,y of the webcam dot")
    ap.add_argument("--tear-in", default="0.10,0.50", help="local start,end of the tear that reveals the paper world")
    ap.add_argument("--tear-out", help="local start,end of the tear back to video (default: dur-0.60,dur-0.18)")
    ap.add_argument("--thr", type=int, default=30, help="hand difference threshold")
    a = vfx.parse(ap)
    W, H = vfx.size_of(a.size)
    J = lambda v: json.load(open(v)) if v and os.path.exists(v) else (json.loads(v) if v else None)
    ref = vfx.grab(a.inp, a.ref_time, (W, H))
    PW = PaperWorld(ref, vfx.get_mask(a, ref), a.hinge_y, J(a.keyboard_rows), vfx.pts(a.trackpad) if a.trackpad else None,
                    J(a.cards), vfx.pt(a.hot) if a.hot else None, a.sidebar_x, vfx.pt(a.webcam) if a.webcam else None)
    TIN = vfx.pt(a.tear_in); TOUT = vfx.pt(a.tear_out) if a.tear_out else (a.dur - 0.60, a.dur - 0.18)
    PAPER_WHITE = np.array([244, 248, 250], np.float32)

    def render(frame, t, i):
        img = frame.astype(np.float32)
        if t <= (TIN[1] + TOUT[0]) / 2: cov, band = torn_front(t, *TIN, W, H)
        else: cov, band = torn_front(t, *TOUT, W, H, reverse=True, seed=9)
        if cov.max() == 0: return img
        hm = vfx.hand_mask(frame, ref, a.thr)
        P = PW(i, t, hm if hm.any() else None)
        out = img * (1 - cov[..., None]) + P * cov[..., None]
        sh = cv2.GaussianBlur(cov, (0, 0), 9)
        out *= (1 - 0.25 * sh * (1 - cov))[..., None]                     # the paper sheet casts a shadow on the video
        return out * (1 - band[..., None]) + PAPER_WHITE * band[..., None]   # white torn-fibre edge

    vfx.run(a, render)
