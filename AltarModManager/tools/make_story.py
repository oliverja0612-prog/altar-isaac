"""Hand-drawn flipbook animations for the OBLIVION story cutscene.

Run:  python make_story.py

Each of the 5 panels is a 16-frame flipbook (384x216 per frame, 4x4 grid sheet)
drawn in code, one per story line: Mom hearing the voice from above, the eye in the
light, Isaac falling through basement, womb and dark to the Void, Delirium coming apart,
and Isaac in the chest while everyone who isn't coming fades out. Writes resources/gfx/altar/story/flipN.png
and flipN.anm2; the cutscene plays them (ambient loops or synced to the voice).
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

import make_sprites as ms
from make_oblivion import PALETTES, figure

HERE = os.path.dirname(os.path.abspath(__file__))
STORY = os.path.join(ms.UI_DIR, "story")
PW, PH = 384, 216
SS = 2                      # supersampling: draw at 2x, downscale for clean lines
W, H = PW * SS, PH * SS
FRAMES, COLS = 16, 4
TAU = math.tau
INK = (24, 16, 22, 255)


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    t = clamp(t)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


# ---------------------------------------------------------------- drawing kit

class Page:
    """One flipbook frame: paper, wobbly ink, glows."""

    def __init__(self, frame, top, bottom, seed):
        self.f = frame
        self.rng = random.Random(seed * 100 + frame)   # per-frame randomness = line boil
        self.img = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(self.img)
        for y in range(H):
            d.line([(0, y), (W, y)], fill=lerp(top, bottom, y / H) + (255,))
        self.d = ImageDraw.Draw(self.img)

    def jit(self, pts, amp=1.6):
        return [(x + self.rng.uniform(-amp, amp), y + self.rng.uniform(-amp, amp)) for x, y in pts]

    def shape(self, pts, fill, ink=INK, width=3, amp=1.6):
        pts = self.jit(pts, amp)
        self.d.polygon(pts, fill=fill)
        if ink:
            self.d.line(pts + [pts[0]], fill=ink, width=width, joint="curve")

    def line(self, pts, fill=INK, width=3, amp=1.2):
        self.d.line(self.jit(pts, amp), fill=fill, width=width, joint="curve")

    def circle(self, x, y, r, fill, ink=INK, width=3):
        j = self.rng.uniform(-1, 1)
        self.d.ellipse((x - r + j, y - r - j, x + r - j, y + r + j), fill=fill, outline=ink, width=width if ink else 0)

    def glow(self, x, y, r, color, strength=1.0):
        layer = Image.new("RGBA", (W, H))
        ld = ImageDraw.Draw(layer)
        for k in range(8, 0, -1):
            rr = r * k / 8
            ld.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color + (int(22 * strength),))
        self.img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(r / 4)))
        self.d = ImageDraw.Draw(self.img)

    def finish(self):
        """Paper grain + vignette, then downscale."""
        img = self.img.resize((PW, PH), Image.LANCZOS)
        px = img.load()
        rng = self.rng
        for y in range(PH):
            for x in range(PW):
                r, g, b, a = px[x, y]
                n = rng.randint(-7, 7)
                dv = math.hypot((x - PW / 2) / (PW / 2), (y - PH / 2) / (PH / 2))
                v = 1 - clamp((dv - 0.55) / 0.6) * 0.7
                px[x, y] = (int(clamp((r + n) * v, 0, 255)), int(clamp((g + n) * v, 0, 255)),
                            int(clamp((b + n) * v, 0, 255)), 255)
        return img


def star_pts(cx, cy, r, points=4, inner=0.38, rot=0.0):
    pts = []
    for i in range(points * 2):
        a = rot + i * math.pi / points - math.pi / 2
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return pts


def lantern(pg, x, y, r, lit, thread_top=0):
    pg.line([(x, thread_top), (x, y - r)], fill=(150, 140, 160, 160), width=1, amp=0.4)
    if lit > 0.05:
        pg.glow(x, y, r * 4, (255, 210, 120), lit)
    col = lerp((70, 66, 80), (255, 226, 140), lit)
    pg.shape(star_pts(x, y, r), col + (255,), width=2)


def seraph(t, dim=0.0, charge=0.0):
    """Seraphiel as a pixel sprite: the boss's own design before the fall."""
    pal = {k: (lerp(v, lerp(v, (40, 40, 60), 0.75), dim) if isinstance(v, tuple) else v)
           for k, v in PALETTES["angel"].items()}
    return figure(t, pal, charge=charge, form=0)


def child(pg, x, y, s, tear=0.0):
    pg.shape([(x - 9 * s, y), (x + 9 * s, y), (x + 6 * s, y - 16 * s), (x - 6 * s, y - 16 * s)], (196, 170, 160, 255),
             width=2)
    pg.circle(x, y - 22 * s, 8 * s, (232, 204, 190, 255))
    if tear > 0:
        ty = y - 20 * s + tear * 6 * s
        pg.circle(x - 3 * s, ty, 1.8 * s, (150, 200, 255, 255), ink=None)


def house(pg, x, y, s, light=1.0):
    pg.shape([(x - 30 * s, y), (x + 30 * s, y), (x + 30 * s, y - 28 * s), (x - 30 * s, y - 28 * s)], (70, 60, 58, 255))
    pg.shape([(x - 36 * s, y - 28 * s), (x, y - 52 * s), (x + 36 * s, y - 28 * s)], (60, 44, 40, 255))
    win = lerp((40, 36, 40), (255, 210, 120), light)
    pg.shape([(x + 6 * s, y - 20 * s), (x + 18 * s, y - 20 * s), (x + 18 * s, y - 8 * s), (x + 6 * s, y - 8 * s)],
             win + (255,), width=2)
    if light > 0.1:
        pg.glow(x + 12 * s, y - 14 * s, 26 * s, (255, 200, 110), light * 0.7)


def hills(pg, y, col, seed):
    rng = random.Random(seed)
    pts = [(0, H)]
    for k in range(9):
        pts.append((k * W / 8, y + rng.uniform(-18, 18)))
    pts.append((W, H))
    pg.shape(pts, col + (255,), width=3)


def paste_sprite(pg, img, x, y, scale):
    big = img.resize((int(img.width * scale), int(img.height * scale)), Image.NEAREST)
    pg.img.alpha_composite(big, (int(x - big.width / 2), int(y - big.height / 2)))
    pg.d = ImageDraw.Draw(pg.img)


# ---------------------------------------------------------------- the five scenes
# One per intro line: Mom and the voice from above; the eye in the light; the fall
# through basement, womb and dark to the Void; Delirium falling apart; Isaac in the chest.

def light_layer(pg, pts, color, alpha, blur=18):
    """A soft translucent shape (beams, shafts), blended rather than painted over."""
    layer = Image.new("RGBA", (W, H))
    ImageDraw.Draw(layer).polygon(pts, fill=color + (int(alpha),))
    pg.img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    pg.d = ImageDraw.Draw(pg.img)


def mom(pg, x, y, s, lift=0.0):
    """Isaac's mom from behind, as the game shows her: a big figure in a red dress, hair up."""
    pg.shape([(x - 44 * s, y), (x + 44 * s, y), (x + 28 * s, y - 64 * s), (x - 28 * s, y - 64 * s)], (128, 40, 52, 255))
    pg.shape([(x - 30 * s, y - 60 * s), (x + 30 * s, y - 60 * s), (x + 20 * s, y - 92 * s), (x - 20 * s, y - 92 * s)],
             (116, 34, 46, 255))
    for side in (-1, 1):  # arms raised toward the light as it speaks
        pg.shape([(x + side * 22 * s, y - 86 * s), (x + side * 30 * s, y - 84 * s),
                  (x + side * (34 + 6 * lift) * s, y - (100 + 24 * lift) * s),
                  (x + side * (27 + 6 * lift) * s, y - (102 + 24 * lift) * s)], (116, 34, 46, 255), width=2)
    hy = y - 106 * s - lift * 3 * s
    pg.circle(x, hy, 16 * s, (92, 62, 50, 255))
    pg.circle(x + 3 * s, hy - 17 * s, 8 * s, (84, 56, 44, 255))


def tv(pg, x, y, s, flick):
    pg.shape([(x - 34 * s, y), (x + 34 * s, y), (x + 34 * s, y - 50 * s), (x - 34 * s, y - 50 * s)], (62, 50, 48, 255))
    scr = lerp((110, 130, 160), (225, 236, 255), flick)
    pg.shape([(x - 26 * s, y - 8 * s), (x + 20 * s, y - 8 * s), (x + 20 * s, y - 42 * s), (x - 26 * s, y - 42 * s)],
             scr + (255,), width=2)
    pg.line([(x - 3 * s, y - 38 * s), (x - 3 * s, y - 13 * s)], fill=(60, 70, 90, 255), width=3)  # a cross on the screen
    pg.line([(x - 13 * s, y - 30 * s), (x + 7 * s, y - 30 * s)], fill=(60, 70, 90, 255), width=3)
    pg.line([(x - 10 * s, y - 50 * s), (x - 22 * s, y - 70 * s)], fill=INK, width=2)
    pg.line([(x + 6 * s, y - 50 * s), (x + 18 * s, y - 72 * s)], fill=INK, width=2)
    pg.glow(x - 3 * s, y - 25 * s, 80 * s, (190, 210, 255), 0.5 + 0.5 * flick)


def scene1(f):
    """Your mother heard a voice from above. She thought it was God."""
    t = f / FRAMES
    pg = Page(f, (40, 30, 34), (24, 18, 20), 11)
    pg.shape([(0, H * 0.78), (W, H * 0.78), (W, H), (0, H)], (58, 40, 32, 255))  # floorboards
    for k in range(9):
        pg.line([(k * W / 8, H * 0.78), (k * W / 8 - 40, H)], fill=(40, 28, 22, 255), width=3)
    pg.shape([(W * 0.06, H * 0.2), (W * 0.2, H * 0.2), (W * 0.2, H * 0.5), (W * 0.06, H * 0.5)], (30, 26, 40, 255))  # window
    pulse = 0.75 + 0.25 * math.sin(t * TAU)
    cx = W * 0.62
    light_layer(pg, [(cx - 30, 0), (cx + 30, 0), (cx + 150, H * 0.82), (cx - 150, H * 0.82)], (255, 244, 210), 110 * pulse)
    pg.shape([(cx - 46, 0), (cx - 10, 26), (cx + 8, 8), (cx + 40, 30), (cx + 52, 0)], (255, 250, 230, 255), width=2)  # the crack
    pg.glow(cx, 10, 120, (255, 240, 200), pulse)
    rng = random.Random(5)
    for _ in range(40):  # dust turning in the beam
        x0, y0 = rng.uniform(-120, 120), rng.uniform(0, H * 0.8)
        y = (y0 + t * 40) % (H * 0.8)
        x = cx + x0 * (y / (H * 0.8)) + math.sin(t * TAU + y0) * 6
        pg.d.ellipse((x, y, x + 3, y + 3), fill=(255, 248, 220, 200))
    tv(pg, W * 0.24, H * 0.8, 1.7, 0.5 + 0.5 * math.sin(t * TAU * 3))
    mom(pg, cx, H * 0.9, 1.45, lift=0.5 + 0.5 * math.sin(t * TAU))
    return pg.finish()


def eye(pg, x, y, r, open_):
    """Her eye in the light: an almond, a violet iris, a pupil like a hole."""
    h = r * 0.55 * open_
    if h < 2:
        pg.line([(x - r, y), (x + r, y)], fill=INK, width=4)
        return
    top = [(x - r + 2 * r * k / 20, y - math.sin(math.pi * k / 20) * h) for k in range(1, 20)]
    bottom = [(x + r - 2 * r * k / 20, y + math.sin(math.pi * k / 20) * h) for k in range(1, 20)]
    pg.shape([(x - r, y)] + top + [(x + r, y)] + bottom, (250, 246, 255, 255), width=4)
    ir = min(h, r * 0.42)
    pg.circle(x, y, ir, (150, 90, 230, 255))
    pg.circle(x, y, ir * 0.45, (10, 4, 16, 255), ink=None)
    pg.d.ellipse((x - ir * 0.5, y - ir * 0.6, x - ir * 0.2, y - ir * 0.3), fill=(255, 255, 255, 255))


def scene2(f):
    """It wasn't. It was me."""
    t = f / FRAMES
    pg = Page(f, (10, 8, 16), (26, 18, 24), 12)
    cx, cy = W / 2, H * 0.36
    light_layer(pg, [(cx - 260, cy - 70), (cx + 260, cy - 70), (cx + 210, cy + 90), (cx - 210, cy + 90)], (255, 240, 220), 120)
    pg.glow(cx, cy, 300, (255, 236, 220), 0.9)
    rng = random.Random(9)
    for k in range(14):  # torn edges of the opening in the ceiling
        a = k / 14 * TAU
        r1 = 250 + rng.uniform(-20, 20)
        pg.line([(cx + math.cos(a) * r1, cy + math.sin(a) * r1 * 0.38),
                 (cx + math.cos(a) * (r1 + 60), cy + math.sin(a) * (r1 + 60) * 0.38)], fill=INK, width=4)
    blink = 0.08 if f in (9, 10) else 1.0
    eye(pg, cx + math.sin(t * TAU) * 6, cy, 170, blink)
    for k in range(5):  # light falling on the tiny figure below
        x = cx - 60 + k * 30
        pg.line([(x, cy + 70), (x + (k - 2) * 18, H * 0.9)], fill=(255, 240, 210, 90), width=2, amp=0.5)
    mom(pg, cx, H * 0.97, 0.55, lift=1.0)
    return pg.finish()


def falling_child(pg, x, y, s, t):
    rot = math.sin(t * TAU) * 0.4
    c, sn = math.cos(rot), math.sin(rot)
    body = [(-9, 0), (9, 0), (6, -16), (-6, -16)]
    pg.shape([(x + (px * c - py * sn) * s, y + (px * sn + py * c) * s) for px, py in body], (196, 170, 160, 255), width=2)
    hx, hy = x + 22 * sn * s, y - 22 * c * s
    pg.circle(hx, hy, 8 * s, (232, 204, 190, 255))
    for k in range(4):  # tears streaming upward as he falls
        pg.circle(hx - 4 * s + k * 2 * s, hy - (10 + k * 9) * s, (1.8 - k * 0.3) * s, (150, 200, 255, 255), ink=None)


def scene3(f):
    """I followed you down: basement, womb, dark, the Void. (Synced to the line.)"""
    t = f / (FRAMES - 1)
    pg = Page(f, (0, 0, 0), (0, 0, 0), 13)
    bands = [((88, 62, 44), (60, 42, 30)), ((150, 40, 44), (96, 20, 30)), ((24, 14, 26), (10, 6, 12)), ((4, 4, 6), (0, 0, 0))]
    scroll = t * 3 * H
    for k, (a, b) in enumerate(bands):
        top = k * H - scroll
        if top > H or top + H < 0:
            continue
        for y in range(max(0, int(top)), min(H, int(top + H))):
            pg.d.line([(0, y), (W, y)], fill=lerp(a, b, (y - top) / H) + (255,))
        if k == 0:  # basement: boards and the trapdoor above
            for j in range(10):
                pg.line([(0, top + j * H / 10), (W, top + j * H / 10)], fill=(50, 34, 24, 255), width=3)
            pg.shape([(W / 2 - 90, top), (W / 2 + 90, top), (W / 2 + 90, top + 30), (W / 2 - 90, top + 30)], (12, 8, 6, 255))
        elif k == 1:  # womb: soft walls and veins
            for side in (0, W):
                for j in range(6):
                    pg.circle(side, top + j * H / 6 + 30, 90, (120, 26, 36, 255))
            rng = random.Random(3)
            for _ in range(10):
                x0 = rng.uniform(80, W - 80)
                pg.line([(x0 + rng.uniform(-40, 40), top + rng.uniform(0, H)) for _ in range(4)], fill=(80, 10, 24, 255), width=3)
        elif k == 2:  # the dark: eyes watching as he passes
            rng = random.Random(4)
            for _ in range(12):
                ex, ey = rng.uniform(60, W - 60), top + rng.uniform(30, H - 30)
                pg.d.ellipse((ex - 8, ey - 3, ex + 8, ey + 3), fill=(200, 180, 220, 160))
        else:  # the Void: static
            rng = random.Random(f)
            for _ in range(160):
                x, y = rng.uniform(0, W), top + rng.uniform(0, H)
                if 0 <= y < H:
                    pg.d.rectangle((x, y, x + 2, y + 2), fill=(240, 240, 240, 255))
    # her hand following him down, a little closer each frame
    reach = H * (0.05 + 0.25 * t)
    pg.shape([(W / 2 - 110, 0), (W / 2 + 110, 0), (W / 2 + 40, reach), (W / 2 - 40, reach)], (20, 8, 30, 255), ink=None)
    for k in range(5):
        x0 = W / 2 - 40 + k * 20
        pg.line([(x0, reach - 6), (x0 + (k - 2) * 6, reach + 26)], fill=(20, 8, 30, 255), width=10, amp=0.5)
    falling_child(pg, W / 2 + math.sin(t * TAU) * 20, H * 0.62, 2.4, t)
    return pg.finish()


def scene4(f):
    """Delirium was only your fear: it falls apart, and she is what's left. (Synced.)"""
    t = f / (FRAMES - 1)
    pg = Page(f, (10, 10, 12), (2, 2, 4), 14)
    cx, cy = W / 2, H * 0.5
    if t > 0.2:  # Oblivion behind it, clearer as Delirium goes
        pg.glow(cx, cy, 200, (150, 90, 230), (t - 0.2) * 1.2)
        paste_sprite(pg, figure(t, PALETTES["normal"]), cx, cy - 10, 2.6)
        if t < 0.95:
            pg.img.alpha_composite(Image.new("RGBA", (W, H), (6, 6, 8, int(255 * clamp(1.1 - t * 1.2)))))
            pg.d = ImageDraw.Draw(pg.img)
    rng = random.Random(21)
    for k in range(46):  # Delirium: a white mass of faces, drifting apart
        a = rng.uniform(0, TAU)
        d0 = rng.uniform(0, 120)
        drift = t * rng.uniform(120, 320)
        x = cx + math.cos(a) * (d0 + drift)
        y = cy + math.sin(a) * (d0 + drift) * 0.7
        r = rng.uniform(20, 42) * clamp(1 - t * 1.1 + rng.uniform(-0.1, 0.2))
        if r < 3:
            continue
        pg.circle(x, y, r, (236, 236, 232, 255), width=3)
        if r > 16 and k % 3 == 0:  # some of them are faces
            pg.d.ellipse((x - r * 0.4, y - r * 0.2, x - r * 0.15, y + r * 0.05), fill=(30, 30, 30, 255))
            pg.d.ellipse((x + r * 0.15, y - r * 0.2, x + r * 0.4, y + r * 0.05), fill=(30, 30, 30, 255))
            pg.d.arc((x - r * 0.4, y, x + r * 0.4, y + r * 0.5), 200, 340, fill=(30, 30, 30, 255), width=3)
    return pg.finish()


def chest(pg, x, y, s, open_):
    pg.shape([(x - 60 * s, y), (x + 60 * s, y), (x + 60 * s, y - 44 * s), (x - 60 * s, y - 44 * s)], (110, 70, 40, 255))
    pg.line([(x - 60 * s, y - 22 * s), (x + 60 * s, y - 22 * s)], fill=(70, 44, 24, 255), width=3)
    lid = y - 44 * s
    pg.shape([(x - 62 * s, lid), (x + 62 * s, lid), (x + 58 * s, lid - (16 + 40 * open_) * s),
              (x - 58 * s, lid - (16 + 40 * open_) * s)], (124, 80, 46, 255))


def silhouette(pg, x, y, s, kind, a):
    """Someone who isn't coming, fading out: Mom, Dad, the light."""
    if a <= 0.02:
        return
    col = lerp((16, 12, 18), (120, 110, 130), a)
    if kind == "mom":
        pg.shape([(x - 26 * s, y), (x + 26 * s, y), (x + 14 * s, y - 50 * s), (x - 14 * s, y - 50 * s)], col + (255,), ink=None)
        pg.circle(x, y - 60 * s, 10 * s, col + (255,), ink=None)
    elif kind == "dad":
        pg.shape([(x - 14 * s, y), (x + 14 * s, y), (x + 14 * s, y - 62 * s), (x - 14 * s, y - 62 * s)], col + (255,), ink=None)
        pg.circle(x, y - 72 * s, 9 * s, col + (255,), ink=None)
    else:
        pg.glow(x, y - 40 * s, 70 * s, (255, 240, 200), a)
        bright = lerp((16, 12, 18), (255, 246, 220), a) + (255,)
        pg.line([(x, y - 70 * s), (x, y - 10 * s)], fill=bright, width=5)
        pg.line([(x - 18 * s, y - 52 * s), (x + 18 * s, y - 52 * s)], fill=bright, width=5)


def scene5(f):
    """No one is coming for you, Isaac. Not her. Not him. Not God. (Synced.)"""
    t = f / (FRAMES - 1)
    pg = Page(f, (8, 6, 14), (20, 14, 16), 15)
    paste_sprite(pg, figure(t, PALETTES["normal"]), W / 2, H * 0.3, 3.0)  # her, huge and patient above
    pg.img.alpha_composite(Image.new("RGBA", (W, H), (8, 6, 14, 120)))
    pg.d = ImageDraw.Draw(pg.img)
    for k, (kind, x) in enumerate((("mom", W * 0.14), ("dad", W * 0.86), ("light", W * 0.5))):
        silhouette(pg, x, H * 0.72, 1.4, kind, clamp(1 - (t * 3.2 - k * 0.9)))
    pg.shape([(0, H * 0.86), (W, H * 0.86), (W, H), (0, H)], (22, 16, 14, 255))
    chest(pg, W / 2, H * 0.97, 1.6, 0.4)
    pg.circle(W / 2, H * 0.97 - 76, 16, (232, 204, 190, 255))  # Isaac peeking over the rim
    for k in range(2):
        ty = H * 0.97 - 72 + ((t * 2 + k * 0.5) % 1) * 22
        pg.circle(W / 2 - 6 + k * 12, ty, 3, (150, 200, 255, 255), ink=None)
    return pg.finish()


SCENES = [scene1, scene2, scene3, scene4, scene5]


def write_anm2(path, sheet):
    attrs = ('XScale="100" YScale="100" Visible="true" RedTint="255" GreenTint="255" BlueTint="255" '
             'AlphaTint="255" RedOffset="0" GreenOffset="0" BlueOffset="0" Rotation="0" Interpolated="false"')
    frames = "\n".join(
        f'          <Frame XPosition="0" YPosition="0" XPivot="{PW // 2}" YPivot="{PH // 2}" '
        f'XCrop="{(i % COLS) * PW}" YCrop="{(i // COLS) * PH}" Width="{PW}" Height="{PH}" Delay="4" {attrs}/>'
        for i in range(FRAMES))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"""<AnimatedActor>
  <Info CreatedBy="Altar" CreatedOn="30/10/2026" Version="1" Fps="30"/>
  <Content>
    <Spritesheets>
      <Spritesheet Path="{sheet}" Id="0"/>
    </Spritesheets>
    <Layers>
      <Layer Name="page" Id="0" SpritesheetId="0"/>
    </Layers>
    <Nulls/>
    <Events/>
  </Content>
  <Animations DefaultAnimation="Play">
    <Animation Name="Play" FrameNum="{FRAMES * 4}" Loop="true">
      <RootAnimation>
        <Frame XPosition="0" YPosition="0" Delay="{FRAMES * 4}" {attrs}/>
      </RootAnimation>
      <LayerAnimations>
        <LayerAnimation LayerId="0" Visible="true">
{frames}
        </LayerAnimation>
      </LayerAnimations>
      <NullAnimations/>
      <Triggers/>
    </Animation>
  </Animations>
</AnimatedActor>
""")


STORY_IN = os.path.join(os.path.dirname(HERE), "story_in")


def painted(path):
    """Your own panel art (story_in/panelN.png) as a flipbook: a slow push-in, flickering
    light and fresh grain each frame, so a still image still feels alive. Panels that
    aren't 16:9 sit whole over a blurred, darkened copy of themselves instead of being cropped."""
    from PIL import ImageEnhance
    src = Image.open(path).convert("RGB")
    sw, sh = src.size
    cover = max(PW / sw, PH / sh) * 1.08
    back = src.resize((int(sw * cover) + 1, int(sh * cover) + 1), Image.LANCZOS)
    back = back.crop(((back.width - int(PW * 1.08)) // 2, (back.height - int(PH * 1.08)) // 2,
                      (back.width - int(PW * 1.08)) // 2 + int(PW * 1.08), (back.height - int(PH * 1.08)) // 2 + int(PH * 1.08)))
    back = ImageEnhance.Brightness(back.filter(ImageFilter.GaussianBlur(14))).enhance(0.45)
    fit = min(PW * 1.08 / sw, PH * 1.08 / sh)
    front = src.resize((int(sw * fit), int(sh * fit)), Image.LANCZOS)
    base = back.copy()
    base.paste(front, ((base.width - front.width) // 2, (base.height - front.height) // 2))

    def frame(f):
        t = f / (FRAMES - 1)
        z = 1.0 + 0.06 * t
        cw, ch = int(PW * 1.08 / z), int(PH * 1.08 / z)
        x0, y0 = (base.width - cw) // 2, (base.height - ch) // 2
        img = base.crop((x0, y0, x0 + cw, y0 + ch)).resize((PW, PH), Image.LANCZOS).convert("RGBA")
        rng = random.Random(f)
        flick = 0.94 + 0.06 * math.sin(f * 1.7)
        px = img.load()
        for y in range(PH):
            for x in range(PW):
                r, g, b, _ = px[x, y]
                n = rng.randint(-6, 6)
                px[x, y] = (int(clamp((r + n) * flick, 0, 255)), int(clamp((g + n) * flick, 0, 255)),
                            int(clamp((b + n) * flick, 0, 255)), 255)
        return img
    return frame


def main():
    os.makedirs(STORY, exist_ok=True)
    rows = (FRAMES + COLS - 1) // COLS
    for n, scene in enumerate(SCENES, 1):
        custom = os.path.join(STORY_IN, f"panel{n}.png")
        if os.path.isfile(custom):  # your own art wins over the drawn scene
            scene = painted(custom)
        sheet = Image.new("RGBA", (PW * COLS, PH * rows))
        for f in range(FRAMES):
            sheet.alpha_composite(scene(f), ((f % COLS) * PW, (f // COLS) * PH))
        sheet.save(os.path.join(STORY, f"flip{n}.png"))
        write_anm2(os.path.join(STORY, f"flip{n}.anm2"), f"flip{n}.png")
        print(f"flipbook {n} written")


if __name__ == "__main__":
    main()
