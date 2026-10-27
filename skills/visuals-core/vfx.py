"""Shared helpers for the /visuals effect skills.

Video in/out through ffmpeg pipes, laptop + hand masks, easing and springs, RGBA compositing, sticker-style text.
Every effect script imports this file:  sys.path.insert(0, <skills>/visuals-core);  import vfx
Coordinates are always output pixels (default 1080x1920 portrait), origin top-left.
"""
import argparse, math, os, shutil, subprocess, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---- setup ---------------------------------------------------------------------------------------------
def need(tool="ffmpeg"):
    if not shutil.which(tool):
        sys.exit(f"'{tool}' was not found on PATH. Install ffmpeg (https://ffmpeg.org/download.html) and try again.")

def size_of(s):
    w, h = s.lower().split("x"); return int(w), int(h)

def pt(s):
    """'540,960' -> (540.0, 960.0)"""
    return tuple(float(v) for v in s.split(","))

def pts(s):
    """'10,20;30,40' -> [(10,20),(30,40)]"""
    return [pt(p) for p in s.split(";") if p.strip()]

def hexc(h):
    """'#RRGGBB' -> BGR float32"""
    h = h.lstrip("#"); return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.float32)

def common_args(desc):
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--in", dest="inp", required=True, help="source video (any format ffmpeg reads)")
    ap.add_argument("--start", type=float, default=0.0, help="effect start time in the source, seconds")
    ap.add_argument("--dur", type=float, required=True, help="effect length, seconds")
    ap.add_argument("--out", required=True, help="output .mp4 (or a folder of stills with --preview)")
    ap.add_argument("--size", default="1080x1920", help="output size WxH (default 1080x1920)")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--mask", help="laptop mask PNG (white = laptop). Default: auto-detected (see mask.py)")
    ap.add_argument("--preview", help="comma list of effect-local times; writes PNG stills instead of a video")
    ap.add_argument("--no-audio", action="store_true", help="do not copy the source audio")
    ap.add_argument("--gamma", type=float, default=1.0, help="brighten dark footage: 0.86 lifts mids (1.0 = off)")
    ap.add_argument("--wb", default="1,1,1", help="white-balance gains B,G,R, e.g. 1.045,0.995,1 cools a yellow cast")
    return ap

GRADE = None

def parse(ap):
    """Parse args and switch on the optional grade for every decoded frame (refs, masks and the effect alike)."""
    global GRADE
    a = ap.parse_args()
    gains = [float(v) for v in a.wb.split(",")]
    if a.gamma != 1.0 or gains != [1.0, 1.0, 1.0]:
        x = np.arange(256) / 255.0
        GRADE = [np.clip((np.clip(x * g, 0, 1) ** a.gamma) * 255 + 0.5, 0, 255).astype(np.uint8) for g in gains]
    return a

def graded(img):
    if GRADE is None: return img
    return cv2.merge([cv2.LUT(c, l) for c, l in zip(cv2.split(img), GRADE)])

# ---- decoding / encoding -------------------------------------------------------------------------------
def decode(path, start, n, size=None, fps=30.0):
    """Yield n BGR frames from `start` (seconds). size=None keeps the native resolution."""
    vf = f"fps={fps}" + (f",scale={size[0]}:{size[1]}:flags=area" if size else "")
    if size is None:
        h, w = grab(path, start).shape[:2]
    else:
        w, h = size
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.4f}", "-i", path, "-an", "-vf", vf, "-frames:v", str(n),
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=w * h * 3 * 2)
    last = None
    for _ in range(n):
        buf = p.stdout.read(w * h * 3)
        if len(buf) == w * h * 3:
            last = graded(np.frombuffer(buf, np.uint8).reshape(h, w, 3))
        if last is None: break
        yield last
    p.stdout.close(); p.wait()

def grab(path, t, size=None):
    """One frame at time t (seconds)."""
    vf = ["-vf", f"scale={size[0]}:{size[1]}:flags=area"] if size else []
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", path, "-frames:v", "1", *vf,
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    img = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)
    if img is None: sys.exit(f"could not read a frame at {t:.2f}s from {path}")
    return graded(img)

class Writer:
    def __init__(self, path, size, fps):
        self.path, self.tmp = path, path + ".video.mp4"
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{size[0]}x{size[1]}",
                                   "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                                   "-pix_fmt", "yuv420p", self.tmp], stdin=subprocess.PIPE)
    def write(self, img):
        self.p.stdin.write(np.ascontiguousarray(img, np.uint8).tobytes())
    def close(self, src=None, start=0.0, dur=None):
        self.p.stdin.close(); self.p.wait()
        if src:
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.tmp, "-ss", f"{start:.4f}", "-t", f"{dur:.4f}", "-i", src,
                                "-map", "0:v", "-map", "1:a?", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                                "-movflags", "+faststart", self.path])
            if r.returncode == 0: os.remove(self.tmp); return
        os.replace(self.tmp, self.path)

def run(args, render, native=False):
    """Drive an effect: render(frame, t_local, index) -> BGR frame (uint8 or float).
    native=True hands render() the full-resolution source frame (for zooms)."""
    need()
    size = size_of(args.size)
    if args.preview:
        os.makedirs(args.out, exist_ok=True)
        for t in [float(v) for v in args.preview.split(",")]:
            fr = grab(args.inp, args.start + t, None if native else size)
            img = render(fr, t, int(round(t * args.fps)))
            p = os.path.join(args.out, f"preview_{t:05.2f}s.png"); cv2.imwrite(p, to8(img)); print("wrote", p)
        return
    n = int(round(args.dur * args.fps))
    w = Writer(args.out, size, args.fps)
    for i, fr in enumerate(decode(args.inp, args.start, n, None if native else size, args.fps)):
        w.write(to8(render(fr, i / args.fps, i)))
        if i % 15 == 0: print(f"  frame {i + 1}/{n}", flush=True)
    w.close(None if args.no_audio else args.inp, args.start, args.dur)
    print("wrote", args.out)

def to8(img):
    return img if img.dtype == np.uint8 else np.clip(img, 0, 255).astype(np.uint8)

# ---- masks ------------------------------------------------------------------------------------------------
def laptop_mask(frame, v_max=95, min_y=None):
    """Dark laptop body (plus the screen and stickers it encloses). Works for a dark laptop on a lighter wall/table.
    min_y: ignore everything above this row (default 35% of the height)."""
    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    dark = (hsv[..., 2] < v_max).astype(np.uint8) * 255
    dark[: int(min_y if min_y is not None else 0.35 * h)] = 0
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(dark)
    if n <= 1: sys.exit("no dark laptop found - pass --mask, or tune --v-max in mask.py")
    m = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8) * 255
    pad = cv2.copyMakeBorder(m, 0, 40, 0, 0, cv2.BORDER_CONSTANT, value=255)   # close the bottom so the screen counts as a hole
    ff = pad.copy(); cv2.floodFill(ff, np.zeros((pad.shape[0] + 2, w + 2), np.uint8), (w // 2, 2), 255)
    m = (pad | ~ff)[:h]
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))

def get_mask(args, frame):
    if args.mask:
        m = cv2.imread(args.mask, cv2.IMREAD_GRAYSCALE)
        if m is None: sys.exit(f"cannot read mask {args.mask}")
        return cv2.resize(m, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)
    return laptop_mask(frame)

def bbox(mask):
    ys, xs = np.where(mask > 0)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())

def screen_mask(frame, laptop, thr=150):
    """Bright screen inside the laptop: convex hull of the biggest bright blob."""
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    b = ((g > thr) & (laptop > 0)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(b)
    if n <= 1: return np.zeros_like(b)
    blob = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    out = np.zeros_like(b); cv2.fillConvexPoly(out, cv2.convexHull(cv2.findNonZero(blob)), 255)
    return out

def hand_mask(frame, ref, thr=30, keep=1, min_area=1500):
    """Hand = pixels that differ from a hand-free reference frame (needs a locked-off camera)."""
    d = np.abs(frame.astype(np.int16) - ref.astype(np.int16)).max(2).astype(np.uint8)
    m = (cv2.GaussianBlur(d, (7, 7), 0) > thr).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n <= 1: return np.zeros_like(m)
    order = 1 + np.argsort(-st[1:, cv2.CC_STAT_AREA])[:keep]
    m = np.isin(lab, order[st[order, cv2.CC_STAT_AREA] > min_area]).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    # fill small holes (skin that happens to match the background), keep real gaps between fingers
    n, lab, st, _ = cv2.connectedComponentsWithStats(255 - m)
    h, w = m.shape
    for i in range(1, n):
        x, y, bw, bh, ar = st[i]
        if ar < 0.002 * h * w and x > 0 and y > 0 and x + bw < w and y + bh < h: m[lab == i] = 255
    return m

# ---- easing ------------------------------------------------------------------------------------------------
def clamp(v, a=0.0, b=1.0): return min(b, max(a, v))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def ramp(t, a, b): return ease((t - a) / (b - a))
def ease_out_back(x, s=1.6): x = clamp(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2
def ease_in_cubic(x): x = clamp(x); return x ** 3
def ease_out_cubic(x): x = clamp(x); return 1 - (1 - x) ** 3

def spring(t, damping=12.0, stiffness=180.0, mass=1.0):
    """Damped spring from 0 to 1 (same physics as Remotion's spring()); t in seconds, 0 before t=0."""
    if t <= 0: return 0.0
    w0 = math.sqrt(stiffness / mass); z = damping / (2 * math.sqrt(stiffness * mass))
    if z < 1:
        wd = w0 * math.sqrt(1 - z * z)
        return 1 - math.exp(-z * w0 * t) * (math.cos(wd * t) + z * w0 / wd * math.sin(wd * t))
    return 1 - math.exp(-w0 * t) * (1 + w0 * t)

# ---- compositing -------------------------------------------------------------------------------------------
def over(dst, rgba, cx, cy, scale=1.0, rot=0.0, alpha=1.0, anchor=(0.5, 0.5)):
    """Composite an RGBA image (uint8 or float 0-255) onto float BGR dst. (cx, cy) = where the anchor lands."""
    if alpha <= 0 or scale <= 0.001: return dst
    h, w = rgba.shape[:2]
    ax, ay = anchor[0] * w, anchor[1] * h
    M = cv2.getRotationMatrix2D((ax, ay), rot, scale); M[0, 2] += cx - ax; M[1, 2] += cy - ay
    H, W = dst.shape[:2]
    corners = cv2.transform(np.float32([[[0, 0]], [[w, 0]], [[0, h]], [[w, h]]]), M).reshape(-1, 2)
    x0, y0 = np.floor(corners.min(0)).astype(int) - 2; x1, y1 = np.ceil(corners.max(0)).astype(int) + 2
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x0 >= x1 or y0 >= y1: return dst
    M[0, 2] -= x0; M[1, 2] -= y0
    warped = cv2.warpAffine(rgba.astype(np.float32), M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    a = warped[..., 3:4] / 255.0 * alpha
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + warped[..., :3] * a
    return dst

def shadow_rgba(rgba, blur=14, opacity=0.35, dx=0, dy=12):
    """RGBA drop shadow of an RGBA sprite, padded so the blur fits."""
    p = int(blur * 3 + max(abs(dx), abs(dy)))
    a = cv2.copyMakeBorder(rgba[..., 3].astype(np.float32), p, p, p, p, cv2.BORDER_CONSTANT, value=0)
    a = cv2.GaussianBlur(np.roll(np.roll(a, dy, 0), dx, 1), (0, 0), blur) * opacity
    out = np.zeros(a.shape + (4,), np.float32); out[..., 3] = a
    return out

def load_rgba(path, height=None):
    """PNG/JPG/WebP (keeps alpha) or SVG (needs `pip install cairosvg`, or rsvg-convert / ImageMagick on PATH)."""
    if path.lower().endswith(".svg"):
        png = None
        try:
            import cairosvg
            png = cairosvg.svg2png(url=path, output_height=height or 512)
        except ImportError:
            for tool, cmd in (("rsvg-convert", ["rsvg-convert", "-h", str(height or 512), path]),
                              ("magick", ["magick", "-background", "none", "-density", "384", path, "png:-"])):
                if shutil.which(tool): png = subprocess.run(cmd, capture_output=True).stdout; break
        img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED) if png else _svg_via_browser(path, height or 512)
        if img is None: sys.exit(f"cannot rasterise {path}: install Chrome/Edge or `pip install cairosvg`, or convert it to PNG")
    else:
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None: sys.exit(f"cannot read image {path}")
    if img.ndim == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    if img.shape[2] == 3: img = np.dstack([img, np.full(img.shape[:2], 255, np.uint8)])
    if height:
        img = cv2.resize(img, (max(1, round(img.shape[1] * height / img.shape[0])), height), interpolation=cv2.INTER_AREA)
    return img

BROWSERS = ["C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]

def _svg_via_browser(path, height):
    """Rasterise an SVG with headless Chrome/Edge (transparent background), cropped to its alpha."""
    exe = next((b for b in BROWSERS if os.path.exists(b)), None) or next(
        (shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge") if shutil.which(n)), None)
    if not exe: return None
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        html = os.path.join(d, "s.html"); shot = os.path.join(d, "s.png")
        uri = pathlib.Path(os.path.abspath(path)).as_uri()
        open(html, "w").write(f'<html><body style="margin:0;background:transparent"><img src="{uri}" style="height:{height}px"></body></html>')
        subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
                        f"--window-size={height * 4},{height}", f"--screenshot={shot}", pathlib.Path(html).as_uri()],
                       capture_output=True, timeout=60)
        img = cv2.imread(shot, cv2.IMREAD_UNCHANGED)
    if img is None or img.shape[2] != 4 or img[..., 3].max() == 0: return None
    ys, xs = np.where(img[..., 3] > 0)
    return img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

# ---- text + stickers -----------------------------------------------------------------------------------------
FONT_CANDIDATES = {
    True: ["C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Black.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"],
    False: ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf"],
}

MONO_CANDIDATES = ["C:/Windows/Fonts/consolab.ttf", "C:/Windows/Fonts/consola.ttf", "/System/Library/Fonts/Menlo.ttc",
                   "/System/Library/Fonts/Monaco.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                   "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf"]

def mono(size, path=None):
    for p in ([path] if path else []) + MONO_CANDIDATES:
        if p and os.path.exists(p): return ImageFont.truetype(p, int(size))
    return font(size)

def font(size, path=None, bold=True):
    for p in ([path] if path else []) + FONT_CANDIDATES[bold]:
        if p and os.path.exists(p): return ImageFont.truetype(p, int(size))
    return ImageFont.load_default(size=int(size))

def rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def text_rgba(text, fnt, color="#1C1A17", stroke=0, stroke_color="#1C1A17", stack_shadow=None):
    """Tight RGBA of one line. stack_shadow=(dx, dy, n, color) draws a stacked offset shadow (sticker lettering)."""
    l, t, r, b = fnt.getbbox(text, stroke_width=stroke)
    pad = 6 + (stack_shadow[0] * stack_shadow[2] if stack_shadow else 0)
    img = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if stack_shadow:
        dx, dy, n, c = stack_shadow
        for k in range(n, 0, -1): d.text((pad - l + dx * k, pad - t + dy * k), text, font=fnt, fill=rgb(c) + (255,))
    d.text((pad - l, pad - t), text, font=fnt, fill=rgb(color) + (255,), stroke_width=stroke, stroke_fill=rgb(stroke_color) + (255,))
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)

def sticker(rows, bg="#FBF8F1", ink="#1C1A17", pad=(46, 28), radius=40, border=6, shadow=(10, 12), gap=6):
    """Neo-brutalist sticker card. rows = [(text, size, color, bold, highlight_hex_or_None, font_path_or_None)].
    Returns a BGRA numpy image (card + solid offset shadow)."""
    parts = []
    for text, sz, color, bold, hl, fp in rows:
        f = font(sz, fp, bold); l, t, r, b = f.getbbox(text); parts.append((text, f, color, hl, r - l, b - t, l, t))
    W = max(p[4] for p in parts) + 2 * pad[0]; H = sum(p[5] for p in parts) + gap * (len(parts) - 1) + 2 * pad[1]
    sx, sy = shadow
    img = Image.new("RGBA", (W + sx + border, H + sy + border), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((sx, sy, W + sx - 1, H + sy - 1), radius, fill=rgb(ink) + (255,))
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius, fill=rgb(bg) + (255,), outline=rgb(ink) + (255,), width=border)
    y = pad[1]
    for text, f, color, hl, tw, th, l, t in parts:
        x = (W - tw) // 2
        if hl: d.rounded_rectangle((x - 10, y - 4, x + tw + 10, y + th + 8), 8, fill=rgb(hl) + (255,))
        d.text((x - l, y - t), text, font=f, fill=rgb(color) + (255,)); y += th + gap
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)

def pill(text, size=54, bg="#D97757", fg="#FFFFFF", ink="#1C1A17", font_path=None):
    f = font(size, font_path, True); l, t, r, b = f.getbbox(text)
    W, H = r - l + 72, b - t + 36
    img = Image.new("RGBA", (W + 14, H + 15), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 9, W + 7, H + 8), H // 2, fill=rgb(ink) + (255,))
    d.rounded_rectangle((0, 0, W - 1, H - 1), H // 2, fill=rgb(bg) + (255,), outline=rgb(ink) + (255,), width=6)
    d.text((36 - l, 18 - t), text, font=f, fill=rgb(fg) + (255,))
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)
