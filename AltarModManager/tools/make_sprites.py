"""Generates every sprite used by the Altar Core mod and the manager app.

Run:  python make_sprites.py

Writes
  mods/altar_core/resources/gfx/items/collectibles/<key>.png        pedestal/HUD icon (frame 0)
  mods/altar_core/resources/gfx/items/collectibles/altar/<key>_N.png animation frames 0-5
  mods/altar_core/resources/gfx/altar/*                             UI sprites, VFX strips, anm2 files
  AltarModManager/assets/*                                          app logo and item previews
"""
import colorsys
import math
import os
import random

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MANAGER = os.path.dirname(HERE)
GAME = os.path.dirname(MANAGER)
MOD = os.path.join(GAME, "mods", "altar_core")
ITEM_DIR = os.path.join(MOD, "resources", "gfx", "items", "collectibles")
FRAME_DIR = os.path.join(ITEM_DIR, "altar")
UI_DIR = os.path.join(MOD, "resources", "gfx", "altar")
APP_DIR = os.path.join(MANAGER, "assets")

FRAMES = 6
OUTLINE = (20, 10, 24, 255)
TAU = math.pi * 2


# ---------------------------------------------------------------- helpers

def canvas(w=32, h=None):
    return Image.new("RGBA", (w, h or w), (0, 0, 0, 0))


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def put(img, x, y, c):
    x, y = int(x), int(y)
    if 0 <= x < img.width and 0 <= y < img.height:
        if len(c) == 3:
            c = c + (255,)
        if c[3] < 255:
            base = img.getpixel((x, y))
            if base[3]:
                a = c[3] / 255
                c = tuple(int(base[i] * (1 - a) + c[i] * a) for i in range(3)) + (255,)
        img.putpixel((x, y), c)


def opaque(img, x, y):
    return 0 <= x < img.width and 0 <= y < img.height and img.getpixel((x, y))[3] > 0


def fill(img, test, color):
    """test(x, y) -> truthy; color(x, y) -> rgb. Samples pixel centres."""
    for y in range(img.height):
        for x in range(img.width):
            if test(x + 0.5, y + 0.5):
                put(img, x, y, color(x + 0.5, y + 0.5))


def outline(img, color=OUTLINE):
    src = img.copy()
    for y in range(img.height):
        for x in range(img.width):
            if src.getpixel((x, y))[3]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if opaque(src, x + dx, y + dy):
                    img.putpixel((x, y), color)
                    break
    return img


def sphere(cx, cy, r, light, dark):
    def col(x, y):
        nx, ny = (x - cx) / r, (y - cy) / r
        l = clamp(0.55 - nx * 0.45 - ny * 0.55)
        return lerp(dark, light, l)
    return col


def vgrad(y0, y1, top, bottom):
    return lambda x, y: lerp(top, bottom, (y - y0) / max(1, y1 - y0))


def circle(cx, cy, r):
    return lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def ellipse(cx, cy, rx, ry):
    return lambda x, y: ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def ring(cx, cy, r0, r1, sy=1.0):
    return lambda x, y: r0 * r0 <= (x - cx) ** 2 + ((y - cy) / sy) ** 2 <= r1 * r1


def rect(x0, y0, x1, y1):
    return lambda x, y: x0 <= x < x1 and y0 <= y < y1


def poly(pts):
    def test(x, y):
        inside = False
        j = len(pts) - 1
        for i in range(len(pts)):
            xi, yi = pts[i]
            xj, yj = pts[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
                inside = not inside
            j = i
        return inside
    return test


def heart(cx, cy, s):
    def test(x, y):
        u, v = (x - cx) / s, -(y - cy) / s + 0.25
        return (u * u + v * v - 1) ** 3 - u * u * v ** 3 <= 0
    return test


def lobe_heart(cx, cy, r):
    """Chunky two-lobe heart that stays readable at 16px."""
    left, right = circle(cx - r * 0.5, cy, r * 0.58), circle(cx + r * 0.5, cy, r * 0.58)
    tip = poly([(cx - r * 1.06, cy + r * 0.15), (cx + r * 1.06, cy + r * 0.15), (cx, cy + r * 1.15)])
    return lambda x, y: left(x, y) or right(x, y) or tip(x, y)


def star(cx, cy, r1, r2, n, rot=0.0):
    pts = []
    for i in range(n * 2):
        a = rot + i * math.pi / n - math.pi / 2
        r = r1 if i % 2 == 0 else r2
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return poly(pts)


def teardrop(cx, cy, r):
    body = circle(cx, cy, r)
    tip = poly([(cx - r * 0.9, cy - r * 0.35), (cx, cy - r * 2.3), (cx + r * 0.9, cy - r * 0.35)])
    return lambda x, y: body(x, y) or tip(x, y)


def hue(h, s=0.8, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def line(img, x0, y0, x1, y1, c):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n + 1):
        t = i / max(1, n)
        put(img, round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c)


def gargantua(img, cx, cy, r, t, disk=2.3, tilt=0.28, alpha=1.0, hot=(255, 236, 200), warm=(255, 140, 40), cool=(150, 30, 20)):
    """Interstellar-style black hole: shadow, photon ring, lensed arc and a tilted
    accretion disk with Doppler beaming (left side brighter). t rotates the disk."""
    w, h = img.size
    for y in range(h):
        for x in range(w):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(dx, dy)
            ang = math.atan2(dy, dx)
            col = None
            a = 0
            # disk plane (flattened ellipse)
            dd = math.hypot(dx, dy / tilt)
            in_disk = r * 1.25 < dd < r * disk
            streak = 0.55 + 0.45 * math.sin(math.atan2(dy / tilt, dx) * 5 - t * math.tau + dd * 0.6)
            doppler = clamp(0.75 - dx / (r * disk) * 0.6, 0.25, 1.3)
            heat = clamp((dd - r * 1.25) / (r * (disk - 1.25)))
            # lensed light from the far side of the disk wraps over and under the shadow
            lens = r * 1.08 < d < r * 1.55 and abs(dy) > r * 0.25
            if lens and not (in_disk and dy > 0):
                k = clamp(1 - (d - r * 1.08) / (r * 0.47)) * (0.75 if dy > 0 else 1)
                k *= 0.6 + 0.4 * math.sin(ang * 4 + t * math.tau)
                col = lerp(warm, hot, k)
                a = clamp(k * 1.4)
            if d < r * 1.08 and d >= r * 0.98:
                col, a = (255, 250, 240), 1.0
            if d < r * 0.98:
                col, a = (0, 0, 0), 1.0
            # the near half of the disk passes in front of the shadow
            if in_disk and (dy > 0 or d > r * 1.08):
                k = clamp(streak * doppler * (1.15 - heat))
                dc = lerp(lerp(cool, warm, k), hot, clamp(k * 1.4 - 0.4))
                ka = clamp((1 - heat) * 1.3) * clamp(streak + 0.25)
                if col is None:
                    col, a = dc, ka
                else:
                    col, a = lerp(col, dc, ka), max(a, ka)
            if col is not None and a > 0.04:
                put(img, x, y, col + (int(255 * a * alpha),))
    return img


# ---------------------------------------------------------------- animation pass

def animate(img, t, glow):
    """Isaac-style finish: rim light, rim shadow, soft shine sweep and a dark outline.

    `glow` tints the rim light so every item keeps its own colour identity.
    """
    body = img.copy()
    w, h = body.size
    for y in range(h):
        for x in range(w):
            c = body.getpixel((x, y))
            if not c[3]:
                continue
            up_left = opaque(body, x - 1, y) and opaque(body, x, y - 1)
            down_right = opaque(body, x + 1, y) and opaque(body, x, y + 1)
            rgb = c[:3]
            if not up_left:
                rgb = lerp(rgb, lerp(glow, (255, 255, 255), 0.5), 0.45)
            elif not down_right:
                rgb = lerp(rgb, (25, 10, 20), 0.45)
            img.putpixel((x, y), rgb + (255,))
    # one soft diagonal shine per loop
    p = -14 + t * 80
    for y in range(h):
        for x in range(w):
            if body.getpixel((x, y))[3] and abs((x + y) - p) < 1.6:
                c = img.getpixel((x, y))
                img.putpixel((x, y), lerp(c[:3], (255, 255, 255), 0.35) + (255,))
    return outline(img, (12, 6, 10, 255))


# ---------------------------------------------------------------- item art (t = 0..1 loop phase)

def cosmic_overclock(t):
    img = canvas()
    for i in range(4):
        p = 9 + i * 4
        for k in range(3):
            for (x, y) in ((p, 5 + k), (p, 24 + k), (5 + k, p), (24 + k, p)):
                put(img, x, y, (200, 200, 215))
    fill(img, rect(8, 8, 24, 24), lambda x, y: lerp((70, 30, 140), (20, 10, 50), ((x - 8) + (y - 8)) / 30))
    core = hue(t)
    fill(img, star(16, 16, 7.5, 2.2, 4, t * math.pi / 2), lambda x, y: lerp((255, 255, 255), core, math.hypot(x - 16, y - 16) / 7))
    return img, (0, 240, 255)


def black_hole_core(t):
    img = canvas()
    gargantua(img, 16, 16, 5.6, t, disk=2.6, tilt=0.3)
    return img, (255, 170, 80)


def midas_engine(t):
    img = canvas()
    rot = t * TAU / 8
    def test(x, y):
        dx, dy = x - 16, y - 16
        r = math.hypot(dx, dy)
        teeth = 11.5 if math.cos((math.atan2(dy, dx) + rot) * 8) > 0.25 else 9.5
        return 3.5 < r < teeth
    fill(img, test, lambda x, y: lerp((255, 240, 140), (190, 110, 10), (x + y) / 32))
    fill(img, circle(16, 16, 3), lambda x, y: (255, 210, 60))
    return img, (255, 210, 60)


def glitched_crown(t):
    img = canvas()
    base = canvas()
    spikes = [(6, 8), (11, 12), (16, 7), (21, 12), (26, 8)]
    def test(x, y):
        if not (5 <= x < 27 and y < 25):
            return False
        return y >= min(sy + abs(x - sx) * 2 for sx, sy in spikes) and y >= 8
    fill(base, test, vgrad(8, 24, (255, 235, 120), (210, 120, 20)))
    fill(base, rect(5, 20, 27, 22), lambda x, y: (170, 40, 220))
    for gx in (10, 16, 22):
        put(base, gx, 17, (255, 60, 90))
    split = 1 + int(2 * abs(math.sin(t * TAU)))
    for ox, tint in ((-split, (255, 0, 60)), (split, (0, 230, 255))):
        for y in range(32):
            for x in range(32):
                if base.getpixel((x, y))[3]:
                    put(img, x + ox, y, tint + (150,))
    img.alpha_composite(base)
    return img, (0, 230, 255)


def shatter_drive(t):
    img = canvas()
    pts = [(16, 3), (25, 14), (16, 29), (7, 14)]
    fill(img, poly(pts), lambda x, y: lerp((150, 245, 255), (30, 80, 200), (x - 6) / 20 + (0.2 if y > 14 else 0)))
    rng = random.Random(7)
    x, y = 16, 5
    while y < 27:
        put(img, x, y, (255, 255, 255))
        y += 1
        x = max(11, min(21, x + rng.choice((-1, 0, 1))))
    return img, (120, 220, 255)


def debug_die(t):
    img = canvas()
    fill(img, lambda x, y: 6 <= x < 27 and 6 <= y < 27 and not (min(x - 6, 27 - x) < 2 and min(y - 6, 27 - y) < 2),
         vgrad(6, 26, (245, 245, 255), (170, 170, 200)))
    pip = hue(0.38 + t * 0.3, 0.8, 0.9)
    for px, py in ((11, 11), (16, 16), (21, 21), (21, 11), (11, 21)):
        fill(img, circle(px, py, 1.8), lambda x, y: pip)
    row = 8 + int(t * 16)
    for x in range(6, 27):
        if img.getpixel((x, row))[3]:
            put(img, x + 2, row, (255, 0, 200, 200))
    return img, (60, 255, 140)


def supernova_heart(t):
    img = canvas()
    fill(img, heart(16, 17, 11), sphere(13, 12, 14, (255, 150, 90), (150, 10, 30)))
    core = 3 + 1.5 * math.sin(t * TAU)
    fill(img, circle(16, 16, core), lambda x, y: lerp((255, 255, 255), (255, 220, 120), math.hypot(x - 16, y - 16) / core))
    return img, (255, 140, 60)


def quantum_tears(t):
    img = canvas()
    for i in range(3):
        a = i * TAU / 3 + t * TAU / 3
        cx, cy = 16 + math.cos(a) * 7, 19 + math.sin(a) * 6
        fill(img, teardrop(cx, cy, 4.2), sphere(cx - 1, cy - 2, 6, (210, 255, 255), (20, 120, 220)))
    return img, (80, 220, 255)


def phoenix_feather(t):
    img = canvas()
    # curved shaft from bottom-left to top-right; vanes sampled along it
    def shaft(s):
        return 7 + s * 17 + math.sin(s * 3.1) * 2.5, 27 - s * 23
    flick = math.sin(t * TAU)
    for i in range(80):
        s = i / 79
        sx, sy = shaft(s)
        width = 7.2 * math.sin(clamp(s * 1.05) * math.pi) ** 0.8
        notch = 1 if int(s * 9 + t * 2) % 3 == 0 else 0
        for side in (-1, 1):
            for k in range(int(width) - notch):
                px_ = sx + side * k * 0.75 + k * 0.45
                py_ = sy + side * k * 0.55 - k * 0.35
                heat = clamp(s + 0.12 * flick)
                c = lerp((210, 30, 20), (255, 150, 30), heat * 1.3)
                c = lerp(c, (255, 240, 140), clamp((heat - 0.6) * 2.5))
                put(img, px_, py_, c)
    for i in range(60):
        sx, sy = shaft(i / 59)
        put(img, sx, sy, (255, 245, 210))
    for k in range(3):
        ex = 9 + ((t * 20 + k * 7) % 14)
        put(img, ex, 26 - ((t * 30 + k * 11) % 20), (255, 210, 90, 220))
    return img, (255, 130, 40)


def storm_core(t):
    img = canvas()
    fill(img, circle(16, 16, 11), sphere(12, 11, 13, (120, 140, 255), (20, 20, 90)))
    bolt = [(18, 6), (11, 17), (16, 17), (13, 27), (22, 14), (17, 14), (20, 6)]
    flick = (255, 255, 160) if int(t * FRAMES) % 2 == 0 else (255, 230, 60)
    fill(img, poly(bolt), lambda x, y: flick)
    return img, (255, 240, 80)


def vampire_fang(t):
    img = canvas()
    fill(img, poly([(9, 5), (23, 5), (21, 14), (17, 28), (15, 28), (11, 14)]), vgrad(5, 28, (255, 255, 245), (200, 190, 180)))
    drip = 22 + int(t * 7)
    fill(img, lambda x, y: (15 <= x < 18 and 24 <= y < drip) or ((x - 16.5) ** 2 + (y - drip) ** 2 < 2.5),
         lambda x, y: (220, 10, 40))
    return img, (230, 20, 60)


def frost_nova(t):
    img = canvas()
    rot = t * TAU / 6
    for i in range(6):
        a = rot + i * TAU / 6
        x1, y1 = 16 + math.cos(a) * 12, 16 + math.sin(a) * 12
        for w in (-0.6, 0, 0.6):
            line(img, 16 + w, 16, x1 + w, y1, (190, 240, 255))
        for s in (0.5, 0.75):
            bx, by = 16 + math.cos(a) * 12 * s, 16 + math.sin(a) * 12 * s
            for b in (-0.7, 0.7):
                line(img, bx, by, bx + math.cos(a + b) * 4, by + math.sin(a + b) * 4, (120, 200, 255))
    fill(img, circle(16, 16, 3.5), lambda x, y: (255, 255, 255))
    return img, (140, 220, 255)


def inferno_halo(t):
    img = canvas()
    for i in range(7):
        fx = 6 + i * 3.4
        h = 6 + 4 * abs(math.sin(t * TAU + i * 1.3))
        fill(img, poly([(fx - 2.5, 19), (fx, 19 - h), (fx + 2.5, 19)]),
             vgrad(19 - h, 19, (255, 240, 120), (255, 80, 10)))
    fill(img, ring(16, 21, 8, 12, 0.45), vgrad(16, 26, (255, 230, 120), (230, 120, 10)))
    return img, (255, 120, 20)


def titan_blood(t):
    img = canvas()
    fill(img, rect(13, 3, 19, 10), lambda x, y: (200, 200, 220))
    fill(img, rect(12, 2, 20, 5), lambda x, y: (120, 80, 50))
    fill(img, circle(16, 19, 10), lambda x, y: (220, 230, 255) if y < 14 else (0, 0, 0))
    fill(img, lambda x, y: circle(16, 19, 9)(x, y) and y >= 14, sphere(13, 15, 12, (255, 70, 80), (110, 0, 20)))
    for i in range(3):
        by = 27 - ((t * 12 + i * 4) % 12)
        put(img, 12 + i * 4, by, (255, 160, 170))
    return img, (255, 40, 60)


def mirror_shard(t):
    img = canvas()
    fill(img, poly([(8, 27), (13, 4), (25, 10), (21, 28)]), lambda x, y: lerp((230, 240, 255), (110, 130, 170), (x + y) / 50))
    p = 6 + t * 26
    fill(img, lambda x, y: poly([(8, 27), (13, 4), (25, 10), (21, 28)])(x, y) and abs(x - y * 0.4 - p + 6) < 1.4,
         lambda x, y: (255, 255, 255))
    return img, (200, 220, 255)


def fourfold_clover(t):
    img = canvas()
    sway = math.sin(t * TAU) * 1
    for ox, oy in ((-5, -5), (5, -5), (-5, 5), (5, 5)):
        fill(img, circle(16 + ox + sway, 14 + oy, 5.3),
             sphere(14 + ox, 12 + oy, 7, (150, 255, 140), (20, 120, 40)))
    line(img, 16 + sway, 16, 20, 29, (240, 200, 60))
    return img, (110, 255, 120)


def bullet_hell(t):
    img = canvas()
    for i in range(3):
        x0 = 6 + i * 7
        off = int(2 * math.sin(t * TAU + i))
        fill(img, rect(x0, 13 + off, x0 + 5, 27 + off), lambda x, y: lerp((255, 220, 120), (170, 100, 20), (x - x0) / 5))
        fill(img, ellipse(x0 + 2.5, 13 + off, 2.5, 6), lambda x, y: lerp((220, 220, 230), (120, 120, 140), (x - x0) / 5))
    return img, (255, 200, 80)


def colossus_tears(t):
    img = canvas()
    s = 9 + 0.8 * math.sin(t * TAU)
    fill(img, teardrop(16, 19, s), sphere(13, 15, 13, (220, 245, 255), (20, 70, 200)))
    return img, (90, 160, 255)


def toxic_core(t):
    img = canvas()
    fill(img, circle(16, 16, 11), sphere(12, 11, 13, (200, 255, 110), (20, 90, 20)))
    for i in range(4):
        a = i * 1.7 + t * TAU
        bx, by = 16 + math.cos(a) * 5, 16 + math.sin(a) * 5
        fill(img, circle(bx, by, 1.6), lambda x, y: (60, 140, 30))
    fill(img, lambda x, y: (x - 16) ** 2 + (y - 16) ** 2 < 4, lambda x, y: (240, 255, 200))
    return img, (130, 255, 60)


def satellite_beam(t):
    img = canvas()
    fill(img, rect(3, 12, 11, 18), lambda x, y: (60, 90, 200) if (int(x) + int(y)) % 2 else (90, 130, 240))
    fill(img, rect(21, 12, 29, 18), lambda x, y: (60, 90, 200) if (int(x) + int(y)) % 2 else (90, 130, 240))
    fill(img, rect(11, 14, 21, 16), lambda x, y: (160, 160, 180))
    fill(img, circle(16, 15, 5), sphere(14, 13, 7, (240, 240, 250), (100, 100, 120)))
    if int(t * FRAMES) % 3 != 2:
        fill(img, rect(15, 20, 18, 30), vgrad(20, 30, (255, 120, 120), (255, 0, 40)))
    return img, (255, 60, 80)


def chronos_gear(t):
    img = canvas()
    def test(x, y):
        dx, dy = x - 16, y - 16
        r = math.hypot(dx, dy)
        return r < (13 if math.cos(math.atan2(dy, dx) * 12) > 0.3 else 11.5)
    fill(img, test, lambda x, y: (190, 140, 60))
    fill(img, circle(16, 16, 10), lambda x, y: (250, 240, 215))
    a1, a2 = t * TAU - math.pi / 2, t * TAU / 12 * 6 - math.pi / 2
    line(img, 16, 16, 16 + math.cos(a1) * 8, 16 + math.sin(a1) * 8, (40, 30, 30))
    line(img, 16, 16, 16 + math.cos(a2) * 5, 16 + math.sin(a2) * 5, (180, 30, 30))
    put(img, 16, 16, (40, 30, 30))
    return img, (255, 220, 120)


def blast_heart(t):
    img = canvas()
    fill(img, circle(15, 18, 10), sphere(12, 14, 12, (110, 110, 130), (15, 15, 25)))
    fill(img, heart(15, 18, 5), lambda x, y: (230, 30, 60))
    line(img, 20, 10, 24, 5, (190, 160, 110))
    spark = (255, 255, 160) if int(t * FRAMES) % 2 else (255, 150, 30)
    fill(img, star(25, 4, 3.5, 1.2, 4, t * 2), lambda x, y: spark)
    return img, (255, 120, 40)


def phantom_step(t):
    img = canvas()
    ph = t * TAU
    def test(x, y):
        if y < 15:
            return circle(16, 15, 10)(x, y)
        wave = 27 + 2 * math.sin(x * 0.9 + ph)
        return 6 <= x <= 26 and y < wave
    fill(img, test, vgrad(5, 29, (250, 245, 255), (170, 150, 230)))
    for ex in (12, 20):
        fill(img, ellipse(ex, 15, 1.6, 2.6), lambda x, y: (40, 20, 70))
    return img, (200, 170, 255)


def chaos_prism(t):
    img = canvas()
    tri = [(16, 4), (28, 26), (4, 26)]
    fill(img, poly(tri), lambda x, y: lerp(hue(t + (x + y) / 64, 0.6, 1), (255, 255, 255), 0.25))
    for i in range(5):
        c = hue(t + i / 5)
        line(img, 24, 17 + i, 31, 15 + i * 2, c)
    return img, hue(t)


def overcharger(t):
    img = canvas()
    fill(img, rect(9, 5, 23, 29), lambda x, y: (60, 60, 75))
    fill(img, rect(13, 2, 19, 5), lambda x, y: (160, 160, 175))
    level = 1 + int(t * 4) % 5
    for i in range(level):
        y0 = 25 - i * 5
        fill(img, rect(11, y0, 21, y0 + 3), lambda x, y: lerp((150, 255, 120), (40, 200, 60), (x - 11) / 10))
    return img, (110, 255, 90)


def ascension_sigil(t):
    img = canvas()
    fill(img, ring(16, 16, 10.5, 13), lambda x, y: lerp((255, 240, 160), (210, 140, 20), (x + y) / 32))
    fill(img, star(16, 16, 9.5, 4, 5, t * TAU / 5), lambda x, y: lerp((255, 255, 230), (255, 190, 40), math.hypot(x - 16, y - 16) / 9))
    return img, (255, 210, 80)


def nuke_button(t):
    img = canvas()
    fill(img, ellipse(16, 22, 13, 6), lambda x, y: (120, 120, 135))
    fill(img, rect(3, 18, 29, 22), lambda x, y: (90, 90, 105))
    press = int(t * FRAMES) % 3 == 0
    top = 13 if not press else 15
    fill(img, ellipse(16, top + 5, 9, 4), lambda x, y: (150, 0, 20))
    fill(img, ellipse(16, top, 9, 5), sphere(13, top - 2, 9, (255, 110, 110), (190, 0, 30)))
    fill(img, star(16, top, 3, 1.2, 3), lambda x, y: (255, 230, 60))
    return img, (255, 60, 60)


def wormhole_key(t):
    img = canvas()
    fill(img, rect(15, 13, 18, 29), lambda x, y: (220, 190, 90))
    fill(img, rect(18, 22, 22, 24), lambda x, y: (220, 190, 90))
    fill(img, rect(18, 26, 21, 28), lambda x, y: (220, 190, 90))
    def swirl(x, y):
        dx, dy = x - 16, y - 9
        r = math.hypot(dx, dy)
        a = math.atan2(dy, dx) + r * 0.5 - t * TAU
        return lerp((255, 200, 255), (70, 0, 140), (math.sin(a * 2) + 1) / 2 * 0.7 + r / 24)
    fill(img, circle(16, 9, 7), swirl)
    return img, (190, 90, 255)


def balance_glove(t):
    img = canvas()
    gold = lambda x, y: lerp((255, 232, 130), (196, 128, 24), (y - 4) / 26 + (x - 6) / 60)
    # cuff
    fill(img, rect(10, 24, 24, 30), lambda x, y: (120, 70, 140))
    fill(img, rect(10, 24, 24, 25), lambda x, y: (200, 150, 230))
    # palm
    fill(img, lambda x, y: rect(9, 13, 25, 25)(x, y) or circle(17, 23, 7.5)(x, y) and y < 25, gold)
    # four fingers, rounded tips, slightly fanned
    for i, (fx, top) in enumerate(((10.5, 7), (14.5, 4.5), (18.5, 5), (22.5, 8))):
        fill(img, lambda x, y, fx=fx, top=top: (abs(x - fx) < 1.8 and top + 1.5 < y < 15) or (x - fx) ** 2 + (y - top - 1.5) ** 2 < 3.4, gold)
        line(img, fx + 2, top + 3, fx + 2, 14, (150, 90, 15))
    # thumb
    fill(img, lambda x, y: ((x - 7) * 0.8 + (y - 18) * 0.6) ** 2 / 9 + ((x - 7) * -0.6 + (y - 18) * 0.8) ** 2 / 3.2 < 1, gold)
    # six gems across the knuckles cycle their glow
    for i, h in enumerate((0.0, 0.12, 0.3, 0.55, 0.72, 0.85)):
        c = hue(h, 0.75, 0.75 + 0.25 * math.sin(t * TAU + i))
        gx = 10.5 + i * 2.6
        fill(img, circle(gx, 18.5, 1.2), lambda x, y, c=c: c)
    return img, (255, 215, 90)


def seraph_bell(t):
    img = canvas()
    flap = 2 * math.sin(t * TAU)
    for sgn in (-1, 1):
        fill(img, ellipse(16 + sgn * 10, 12 - flap * 0.5, 6, 3.4 + flap * 0.3), lambda x, y: (250, 250, 255))
    fill(img, poly([(11, 8), (21, 8), (24, 22), (8, 22)]), vgrad(6, 24, (255, 240, 150), (210, 140, 30)))
    fill(img, ellipse(16, 8, 5, 3), lambda x, y: (255, 240, 150))
    fill(img, ellipse(16, 22, 9, 2), lambda x, y: (200, 130, 20))
    fill(img, circle(16 + flap, 25, 2), lambda x, y: (160, 100, 20))
    return img, (255, 240, 170)


def treasure_geyser(t):
    img = canvas()
    fill(img, rect(5, 18, 27, 29), vgrad(18, 29, (170, 100, 50), (100, 50, 20)))
    fill(img, rect(5, 18, 27, 20), lambda x, y: (230, 190, 60))
    fill(img, rect(14, 21, 18, 25), lambda x, y: (240, 200, 70))
    for i in range(5):
        ph = (t + i / 5) % 1
        cx = 16 + (i - 2) * 3 * ph * 1.6
        cy = 17 - ph * 14 + ph * ph * 4
        fill(img, ellipse(cx, cy, 2.2, 2.2), sphere(cx - 0.5, cy - 0.5, 2.5, (255, 245, 150), (200, 140, 10)))
    return img, (255, 220, 60)


def event_horizon(t):
    img = canvas()
    # a shard of void held in a cracked golden frame
    fill(img, ring(16, 16, 12, 14.2), lambda x, y: lerp((255, 225, 120), (170, 100, 20), (x + y) / 32))
    fill(img, circle(16, 16, 12), lambda x, y: (18, 8, 30))
    gargantua(img, 16, 16, 4.4, t, disk=2.5, tilt=0.26, hot=(240, 230, 255), warm=(180, 110, 255), cool=(70, 20, 140))
    for k in range(5):
        a = k * TAU / 5 + t * TAU / 5
        put(img, 16 + math.cos(a) * 10, 16 + math.sin(a) * 10, (255, 255, 255, 200))
    return img, (190, 130, 255)


# ---- Fallen Sky items (v1.1): Oblivion's star-and-void look

def fallen_star(t):
    img = canvas()
    for i in range(40):  # tail streaking in from the top-left
        s = i / 39
        x, y, w = 4 + s * 15, 3 + s * 15, 0.6 + s * 2.4
        c = lerp((110, 80, 255), (255, 250, 220), s) + (int(90 + 165 * s),)
        for k in range(-int(w), int(w) + 1):
            put(img, x + k * 0.7, y - k * 0.7, c)
    wob = math.sin(t * TAU) * 0.15
    fill(img, star(20, 20, 8.5, 3.6, 5, wob), lambda x, y: lerp((255, 255, 235), (255, 185, 50), math.hypot(x - 20, y - 20) / 8.5))
    fill(img, circle(20, 20, 2.2), lambda x, y: (255, 255, 255))
    for k in range(3):
        ph = (t + k / 3) % 1
        put(img, 25 + ph * 4 - k * 9, 6 + k * 4 + ph * 3, (255, 255, 255, int(255 * (1 - ph))))
    return img, (255, 220, 120)


def still_sky(t):
    img = canvas()
    gold = lambda x, y: lerp((255, 230, 140), (170, 110, 30), (y - 3) / 26)
    fill(img, rect(7, 3, 25, 6), gold)
    fill(img, rect(7, 26, 25, 29), gold)
    fill(img, poly([(9, 6), (23, 6), (17.5, 16), (23, 26), (9, 26), (14.5, 16)]), lambda x, y: (36, 44, 104))
    fill(img, poly([(10.5, 7), (21.5, 7), (16.6, 15), (15.4, 15)]), lambda x, y: lerp((70, 80, 190), (20, 20, 70), (y - 7) / 8))
    fill(img, poly([(10.5, 25), (21.5, 25), (18.5, 20.5), (13.5, 20.5)]), lambda x, y: lerp((210, 180, 255), (255, 240, 170), (y - 20) / 5))
    for k in range(4):  # starlight grains hanging mid-fall: time has stopped
        put(img, 16, 15.5 + k * 1.3, (255, 250, 220, 255 - k * 40))
    for i, (sx, sy) in enumerate(((13, 9), (18, 8), (16, 11), (19, 11), (12, 8))):
        a = 0.5 + 0.5 * math.sin((t + i / 5) * TAU)
        put(img, sx, sy, (255, 255, 255, int(90 + 165 * a)))
    return img, (170, 190, 255)


def oblivion_eye(t):
    img = canvas()
    fill(img, ellipse(16, 16, 13.5, 7.8), lambda x, y: lerp((240, 228, 255), (130, 90, 200), math.hypot(x - 16, (y - 16) * 1.6) / 14))
    gargantua(img, 16, 16, 3.6, t, disk=2.2, tilt=0.26, hot=(240, 230, 255), warm=(180, 110, 255), cool=(70, 20, 140))
    blink = 1 if 0.45 < t < 0.6 else 0
    for x in range(4, 29):  # heavy upper lid
        top = 16 - 7.8 * math.sqrt(max(0, 1 - ((x - 16) / 13.5) ** 2))
        for k in range(2 + blink * 5):
            put(img, x, top + k, (60, 20, 90))
    for k in range(5):
        a = math.pi + 0.35 + k * 0.6
        line(img, 16 + math.cos(a) * 12, 16 + math.sin(a) * 6.5, 16 + math.cos(a) * 15, 16 + math.sin(a) * 10, (60, 20, 90))
    return img, (190, 130, 255)


def seraph_wings(t):
    img = canvas()
    flap = math.sin(t * TAU)
    for sgn in (-1, 1):
        for i in range(4):
            cx = 16 + sgn * (5 + i * 2.6)
            cy = 16 + i * 1.6 - flap * (1.6 - i * 0.35)
            fill(img, ellipse(cx, cy, 3 + i * 0.4, 7.5 - i), lambda x, y, i=i: lerp((255, 255, 255), (185, 195, 240), i / 4))
    fill(img, ring(16, 6, 3.4, 5, 0.45), lambda x, y: (255, 225, 110))
    fill(img, ellipse(16, 17, 2.2, 4.5), lambda x, y: (255, 248, 225))
    return img, (240, 240, 255)


def nebula_heart(t):
    img = canvas()

    def col(x, y):
        n = math.sin(x * 0.45 + t * TAU) + math.cos(y * 0.5 - t * TAU) + math.sin((x + y) * 0.3)
        c = lerp((255, 90, 190), (90, 60, 230), (n + 3) / 6)
        return lerp(c, (60, 200, 255), clamp((x - 16) / 20 + 0.1))
    fill(img, lobe_heart(16, 13, 11), col)
    for sx, sy, ph in ((11, 11, 0), (20, 12, 0.33), (15, 19, 0.66), (18, 8, 0.5), (9, 15, 0.2)):
        a = 0.5 + 0.5 * math.sin((t + ph) * TAU)
        put(img, sx, sy, (255, 255, 255, int(110 + 145 * a)))
    return img, (255, 120, 220)


def comet_tail(t):
    img = canvas()
    for i in range(60):
        s = i / 59
        x = 22 - s * 18
        y = 22 - s * 18 + math.sin(s * 6 + t * TAU) * 1.3
        w = 4.6 * (1 - s) + 0.5
        c = lerp((190, 245, 255), (40, 80, 220), s) + (int(255 * (1 - s * 0.6)),)
        for dx in range(-int(w), int(w) + 1):
            for dy in range(-int(w), int(w) + 1):
                if dx * dx + dy * dy <= w * w:
                    put(img, x + dx, y + dy, c)
    fill(img, circle(22, 22, 4.8), sphere(21, 21, 5, (245, 255, 255), (70, 170, 255)))
    return img, (120, 200, 255)


def rift_shard(t):
    img = canvas()
    fill(img, poly([(16, 2), (23.5, 12), (20, 29.5), (10.5, 25), (8.5, 11)]),
         lambda x, y: lerp((125, 75, 210), (28, 10, 60), (x - 8) / 16 + (y - 2) / 70))
    glow = lerp((255, 110, 255), (255, 255, 255), 0.5 + 0.5 * math.sin(t * TAU))
    crack = [(15, 4), (17.5, 10), (14, 15), (18.5, 20), (15, 27)]
    for a, b in zip(crack, crack[1:]):
        line(img, a[0], a[1], b[0], b[1], glow)
        line(img, a[0] + 1, a[1], b[0] + 1, b[1], lerp(glow, (160, 60, 220), 0.5))
    for k in range(3):
        ph = (t + k / 3) % 1
        put(img, 25 + k, 8 + ph * 16, (255, 180, 255, int(255 * (1 - ph))))
    return img, (220, 110, 255)


def dying_star(t):
    img = canvas()
    pulse = 0.5 + 0.5 * math.sin(t * TAU)
    for k in range(12):
        a = k * TAU / 12 + t * TAU / 12
        r1 = 10 + (3 if k % 2 == 0 else 1) + pulse * 1.5
        line(img, 16 + math.cos(a) * 7, 16 + math.sin(a) * 7, 16 + math.cos(a) * r1, 16 + math.sin(a) * r1,
             lerp((255, 200, 80), (255, 80, 30), k % 2))
    fill(img, circle(16, 16, 7.8 + pulse * 0.6), sphere(14, 14, 9, (255, 250, 210), (215, 45, 20)))
    fill(img, circle(16, 16, 2.8 + pulse), lambda x, y: (255, 255, 240))
    return img, (255, 120, 40)


ITEMS = [
    "cosmic_overclock", "black_hole_core", "midas_engine", "glitched_crown", "shatter_drive", "debug_die",
    "supernova_heart", "quantum_tears", "phoenix_feather", "storm_core", "vampire_fang", "frost_nova",
    "inferno_halo", "titan_blood", "mirror_shard", "fourfold_clover", "bullet_hell", "colossus_tears",
    "toxic_core", "satellite_beam", "chronos_gear", "blast_heart", "phantom_step", "chaos_prism",
    "overcharger", "ascension_sigil", "nuke_button", "wormhole_key", "balance_glove", "seraph_bell",
    "treasure_geyser", "event_horizon",
    "fallen_star", "still_sky", "oblivion_eye", "seraph_wings", "nebula_heart", "comet_tail", "rift_shard", "dying_star",
]


def item_frames(key):
    fn = globals()[key]
    frames = []
    for i in range(FRAMES):
        t = i / FRAMES
        img, glow = fn(t)
        frames.append(animate(img, t, glow))
    return frames


# ---------------------------------------------------------------- VFX strips

def bh_tear_strip(n=8, s=32):
    strip = canvas(s * n, s)
    for i in range(n):
        img = canvas(s)
        gargantua(img, s / 2, s / 2, 4.2, i / n, disk=2.9, tilt=0.32)
        strip.alpha_composite(img, (i * s, 0))
    return strip


def singularity_strip(n=14, s=96):
    """Tear impact: the hole swells, flares, then collapses with a shockwave."""
    strip = canvas(s * n, s)
    for i in range(n):
        t = i / (n - 1)
        img = canvas(s)
        c = s / 2
        r = 3 + 11 * math.sin(min(1, t * 1.4) * math.pi * 0.5) * (1 - max(0, t - 0.65) / 0.35)
        fade = 1 if t < 0.8 else (1 - t) / 0.2
        wave = 8 + t * 40
        for y in range(s):
            for x in range(s):
                d = math.hypot(x + 0.5 - c, y + 0.5 - c)
                if abs(d - wave) < 1.6 * (1 - t) + 0.4:
                    put(img, x, y, (255, 200, 140, int(150 * (1 - t))))
        if r > 1:
            gargantua(img, c, c, r, t * 2, disk=2.4, tilt=0.3, alpha=fade)
        strip.alpha_composite(img, (i * s, 0))
    return strip


def horizon_strip(n=12, s=128):
    """Event Horizon effect: a big, slowly spinning black hole with a gravity halo."""
    strip = canvas(s * n, s)
    for i in range(n):
        t = i / n
        img = canvas(s)
        c = s / 2
        for y in range(s):
            for x in range(s):
                d = math.hypot(x + 0.5 - c, y + 0.5 - c)
                if 20 < d < 60:
                    k = (1 - (d - 20) / 40) * (0.5 + 0.5 * math.sin(math.atan2(y - c, x - c) * 3 - d * 0.25 + t * TAU))
                    if k > 0.35:
                        put(img, x, y, (120, 60, 200, int(70 * k)))
        gargantua(img, c, c, 15, t, disk=2.5, tilt=0.27)
        strip.alpha_composite(img, (i * s, 0))
    return strip


# ---------------------------------------------------------------- small UI icons (16x16)

def heart_icon(top, bottom, extra=None):
    img = canvas(16)
    fill(img, lobe_heart(8, 6, 6), vgrad(2, 13, top, bottom))
    put(img, 4, 4, (255, 255, 255))
    if extra:
        extra(img)
    return outline(img)


def icon_coin():
    img = canvas(16)
    fill(img, circle(8, 8, 6), sphere(6, 6, 8, (255, 245, 150), (200, 130, 10)))
    fill(img, rect(7, 5, 9, 11), lambda x, y: (190, 120, 10))
    return outline(img)


def icon_bomb():
    img = canvas(16)
    fill(img, circle(7, 9, 5.5), sphere(5, 7, 7, (120, 120, 140), (20, 20, 30)))
    line(img, 10, 4, 13, 1, (220, 180, 90))
    put(img, 13, 1, (255, 230, 80))
    return outline(img)


def icon_key():
    img = canvas(16)
    fill(img, ring(5, 5, 1.5, 4), lambda x, y: (220, 200, 210))
    line(img, 8, 8, 14, 14, (220, 200, 210))
    line(img, 8, 9, 13, 14, (220, 200, 210))
    put(img, 12, 14, (220, 200, 210))
    put(img, 14, 12, (220, 200, 210))
    return outline(img)


def icon_card():
    img = canvas(16)
    fill(img, rect(4, 2, 12, 14), vgrad(2, 14, (250, 240, 220), (200, 180, 150)))
    fill(img, star(8, 8, 3, 1.2, 4), lambda x, y: (200, 40, 60))
    return outline(img)


def icon_pill():
    img = canvas(16)
    fill(img, ellipse(8, 8, 6, 3.5), lambda x, y: (240, 240, 250) if x < 8 else (80, 160, 255))
    return outline(img)


def icon_trinket():
    img = canvas(16)
    fill(img, ring(8, 9, 2.5, 5), lambda x, y: (220, 180, 70))
    fill(img, star(8, 3.5, 2.5, 1, 4), lambda x, y: (120, 230, 255))
    return outline(img)


def icon_chest():
    img = canvas(16)
    fill(img, rect(2, 6, 14, 14), vgrad(6, 14, (180, 110, 50), (110, 60, 20)))
    fill(img, rect(2, 6, 14, 8), lambda x, y: (230, 190, 60))
    fill(img, rect(7, 8, 9, 11), lambda x, y: (240, 210, 80))
    return outline(img)


def icon_battery():
    img = canvas(16)
    fill(img, rect(5, 3, 11, 15), lambda x, y: (60, 60, 75))
    fill(img, rect(7, 1, 9, 3), lambda x, y: (160, 160, 175))
    fill(img, rect(6, 6, 10, 14), lambda x, y: (100, 255, 100))
    return outline(img)


def icon_stat(color):
    img = canvas(16)
    fill(img, poly([(8, 2), (14, 9), (10, 9), (10, 14), (6, 14), (6, 9), (2, 9)]), vgrad(2, 14, lerp(color, (255, 255, 255), 0.4), color))
    return outline(img)


def container_extra(img):
    hole = lobe_heart(8, 6.5, 3)
    for y in range(16):
        for x in range(16):
            if hole(x + 0.5, y + 0.5):
                img.putpixel((x, y), (0, 0, 0, 0))


def broken_extra(img):
    line(img, 8, 3, 6, 8, (20, 10, 24))
    line(img, 6, 8, 9, 12, (20, 10, 24))


UI_ICONS = {
    "heart_container": lambda: heart_icon((120, 120, 140), (40, 40, 55), container_extra),
    "heart_red": lambda: heart_icon((255, 90, 100), (170, 10, 30)),
    "heart_soul": lambda: heart_icon((170, 200, 255), (60, 90, 200)),
    "heart_black": lambda: heart_icon((90, 80, 100), (20, 15, 30)),
    "heart_bone": lambda: heart_icon((250, 245, 230), (190, 180, 160)),
    "heart_rotten": lambda: heart_icon((170, 160, 90), (100, 90, 40)),
    "heart_golden": lambda: heart_icon((255, 240, 130), (220, 150, 20)),
    "heart_eternal": lambda: heart_icon((255, 255, 255), (210, 210, 230)),
    "heart_broken": lambda: heart_icon((110, 100, 110), (60, 50, 60), broken_extra),
    "coin": icon_coin, "bomb": icon_bomb, "key": icon_key, "card": icon_card, "pill": icon_pill,
    "trinket": icon_trinket, "chest": icon_chest, "battery": icon_battery,
    "stat_damage": lambda: icon_stat((255, 80, 80)), "stat_tears": lambda: icon_stat((80, 170, 255)),
    "stat_speed": lambda: icon_stat((255, 220, 70)), "stat_range": lambda: icon_stat((120, 255, 140)),
    "stat_shotspeed": lambda: icon_stat((200, 120, 255)), "stat_luck": lambda: icon_stat((90, 230, 120)),
}


def icon_tab(kind):
    img = canvas(16)
    if kind == "mods":
        fill(img, poly([(8, 1), (14, 5), (14, 11), (8, 15), (2, 11), (2, 5)]), lambda x, y: lerp((210, 160, 255), (110, 50, 200), (x + y) / 26))
    elif kind == "items":
        fill(img, rect(2, 6, 14, 14), vgrad(6, 14, (200, 130, 60), (120, 60, 20)))
        fill(img, rect(2, 5, 14, 8), lambda x, y: (240, 200, 70))
        fill(img, rect(7, 7, 9, 10), lambda x, y: (255, 230, 120))
    elif kind == "give":
        fill(img, lobe_heart(8, 6, 6), vgrad(2, 13, (255, 100, 110), (170, 10, 30)))
    elif kind == "combos":
        fill(img, poly([(10, 1), (3, 9), (7, 9), (5, 15), (13, 6), (9, 6), (11, 1)]), lambda x, y: (255, 230, 80))
    elif kind == "warp":
        fill(img, ring(8, 8, 2.5, 6.5), lambda x, y: hue(math.atan2(y - 8, x - 8) / TAU + 0.6, 0.6, 1))
    elif kind == "player":
        fill(img, circle(8, 6, 4.5), lambda x, y: (250, 215, 190))
        fill(img, ellipse(8, 14, 5, 3), lambda x, y: (250, 215, 190))
        put(img, 6, 6, (30, 20, 30)); put(img, 10, 6, (30, 20, 30))
    elif kind == "debug":
        fill(img, ellipse(8, 9, 4, 5), lambda x, y: (120, 230, 120))
        for yy in (6, 9, 12):
            line(img, 2, yy, 14, yy, (60, 140, 60))
        fill(img, circle(8, 4, 2.5), lambda x, y: (90, 200, 90))
    elif kind == "console":
        fill(img, rect(1, 3, 15, 13), lambda x, y: (40, 34, 60))
        line(img, 3, 6, 5, 8, (120, 255, 140)); line(img, 5, 8, 3, 10, (120, 255, 140))
        line(img, 7, 10, 11, 10, (200, 200, 220))
    elif kind == "settings":
        fill(img, lambda x, y: 2.5 < math.hypot(x - 8, y - 8) < (6.8 if math.cos(math.atan2(y - 8, x - 8) * 6) > 0 else 5.4),
             lambda x, y: (190, 190, 210))
    return outline(img)


def app_icon(size=256):
    """Smooth (non pixel-art) app icon: an amethyst gem on a dark altar slab."""
    from PIL import ImageDraw, ImageFilter
    S = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = S * 0.04
    d.rounded_rectangle((pad, pad, S - pad, S - pad), radius=S * 0.22, fill=(22, 14, 38, 255))
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((S * 0.18, S * 0.12, S * 0.82, S * 0.76), fill=(150, 80, 255, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.08))
    img.alpha_composite(glow)
    # altar slab
    d.polygon([(S * 0.2, S * 0.74), (S * 0.8, S * 0.74), (S * 0.72, S * 0.86), (S * 0.28, S * 0.86)], fill=(70, 58, 92, 255))
    d.polygon([(S * 0.16, S * 0.68), (S * 0.84, S * 0.68), (S * 0.8, S * 0.74), (S * 0.2, S * 0.74)], fill=(120, 104, 150, 255))
    # gem facets
    cx, top, mid, bot, wdt = S * 0.5, S * 0.16, S * 0.38, S * 0.68, S * 0.26
    facets = [
        ([(cx, top), (cx - wdt, mid), (cx, mid)], (215, 170, 255)),
        ([(cx, top), (cx + wdt, mid), (cx, mid)], (165, 95, 250)),
        ([(cx - wdt, mid), (cx, bot), (cx, mid)], (120, 50, 215)),
        ([(cx + wdt, mid), (cx, bot), (cx, mid)], (80, 25, 165)),
    ]
    for pts, col in facets:
        d.polygon(pts, fill=col + (255,))
    d.polygon([(cx - wdt * 0.45, mid - S * 0.02), (cx, top + S * 0.05), (cx + wdt * 0.15, mid - S * 0.04)], fill=(245, 230, 255, 200))
    d.line([(cx, top), (cx - wdt, mid), (cx, bot), (cx + wdt, mid), (cx, top)], fill=(40, 10, 80, 255), width=int(S * 0.012))
    return img.resize((size, size), Image.LANCZOS)


def installer_banner(w=640, h=150):
    from PIL import ImageDraw, ImageFilter
    img = Image.new("RGBA", (w, h), (18, 12, 30, 255))
    d = ImageDraw.Draw(img)
    for x in range(w):
        c = lerp((40, 20, 75), (18, 12, 30), x / w)
        d.line([(x, 0), (x, h)], fill=c + (255,))
    rng = random.Random(3)
    for _ in range(90):
        x, y = rng.randrange(w), rng.randrange(h)
        a = rng.randrange(60, 200)
        d.point((x, y), fill=(220, 200, 255, a))
    hole = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
    gargantua(hole, 110, 110, 30, 0.1, disk=2.6, tilt=0.26)
    hole = hole.filter(ImageFilter.GaussianBlur(0.6))
    img.alpha_composite(hole, (w - 250, -35))
    return img


def altar_gem(size=24):
    img = canvas(size)
    c = (size - 1) / 2
    rad = size * 0.42
    for y in range(size):
        for x in range(size):
            dx, dy = x - c, y - c
            ax, ay = abs(dx), abs(dy)
            if ax <= rad * 0.866 and ax * 0.577 + ay <= rad:
                facet = (dx > 0) * 1 + (dy > 0) * 2
                col = [(200, 140, 255), (150, 80, 240), (110, 40, 200), (70, 20, 150)][facet]
                if ax * 0.577 + ay > rad * 0.75 or ax > rad * 0.866 * 0.8:
                    col = lerp(col, (40, 10, 90), 0.5)
                if ax * 0.577 + ay < rad * 0.35:
                    col = lerp(col, (240, 220, 255), 0.6)
                put(img, x, y, col)
    put(img, int(c - rad * 0.4), int(c - rad * 0.45), (255, 255, 255))
    return outline(img)


# ---------------------------------------------------------------- anm2

FRAME_ATTRS = ('XScale="100" YScale="100" Delay="{d}" Visible="true" RedTint="255" GreenTint="255" BlueTint="255" '
               'AlphaTint="255" RedOffset="0" GreenOffset="0" BlueOffset="0" Rotation="0" Interpolated="false"')


def write_anm2(path, sheet, w, h, frames=1, delay=1, loop=True, anim="Idle", center=False):
    px, py = (w // 2, h // 2) if center else (0, 0)
    layer_frames = "\n".join(
        f'          <Frame XPosition="0" YPosition="0" XPivot="{px}" YPivot="{py}" XCrop="{i * w}" YCrop="0" '
        f'Width="{w}" Height="{h}" ' + FRAME_ATTRS.format(d=delay) + "/>"
        for i in range(frames))
    xml = f"""<AnimatedActor>
  <Info CreatedBy="Altar" CreatedOn="30/10/2026" Version="1" Fps="30"/>
  <Content>
    <Spritesheets>
      <Spritesheet Path="{sheet}" Id="0"/>
    </Spritesheets>
    <Layers>
      <Layer Name="main" Id="0" SpritesheetId="0"/>
    </Layers>
    <Nulls/>
    <Events/>
  </Content>
  <Animations DefaultAnimation="{anim}">
    <Animation Name="{anim}" FrameNum="{frames * delay}" Loop="{'true' if loop else 'false'}">
      <RootAnimation>
        <Frame XPosition="0" YPosition="0" Delay="{frames * delay}" {FRAME_ATTRS.split('Delay="{d}" ')[0]}{FRAME_ATTRS.split('Delay="{d}" ')[1]}/>
      </RootAnimation>
      <LayerAnimations>
        <LayerAnimation LayerId="0" Visible="true">
{layer_frames}
        </LayerAnimation>
      </LayerAnimations>
      <NullAnimations/>
      <Triggers/>
    </Animation>
  </Animations>
</AnimatedActor>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)


# ---------------------------------------------------------------- main

def main():
    for d in (ITEM_DIR, FRAME_DIR, UI_DIR, APP_DIR):
        os.makedirs(d, exist_ok=True)

    preview = canvas(32 * 8 * 2, 32 * 5 * 2)
    for idx, key in enumerate(ITEMS):
        frames = item_frames(key)
        frames[0].save(os.path.join(ITEM_DIR, key + ".png"))
        for i, fr in enumerate(frames):
            fr.save(os.path.join(FRAME_DIR, f"{key}_{i}.png"))
        frames[0].resize((64, 64), Image.NEAREST).save(os.path.join(APP_DIR, "item_" + key + ".png"))
        preview.alpha_composite(frames[0].resize((64, 64), Image.NEAREST), ((idx % 8) * 64, (idx // 8) * 64))
    preview.save(os.path.join(APP_DIR, "items_preview.png"))

    bh_tear_strip().save(os.path.join(UI_DIR, "bh_tear.png"))
    write_anm2(os.path.join(UI_DIR, "bh_tear.anm2"), "bh_tear.png", 32, 32, frames=8, delay=2, anim="Spin", center=True)
    singularity_strip().save(os.path.join(UI_DIR, "singularity.png"))
    write_anm2(os.path.join(UI_DIR, "singularity.anm2"), "singularity.png", 96, 96, frames=14, delay=2, loop=False,
               anim="Burst", center=True)
    horizon_strip().save(os.path.join(UI_DIR, "horizon.png"))
    write_anm2(os.path.join(UI_DIR, "horizon.anm2"), "horizon.png", 128, 128, frames=12, delay=3, anim="Idle", center=True)
    for kind in ("mods", "items", "give", "combos", "warp", "player", "debug", "console", "settings"):
        icon_tab(kind).save(os.path.join(UI_DIR, "ic_tab_" + kind + ".png"))
    # your own icon art wins: drop a square PNG at AltarModManager/icon_in/icon.png
    custom = os.path.join(MANAGER, "icon_in", "icon.png")
    big = Image.open(custom).convert("RGBA").resize((256, 256), Image.LANCZOS) if os.path.isfile(custom) else app_icon(256)
    big.save(os.path.join(APP_DIR, "app_icon.png"))
    big.save(os.path.join(APP_DIR, "altar.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    big.resize((96, 96), Image.LANCZOS).save(os.path.join(APP_DIR, "logo.png"))
    installer_banner().save(os.path.join(APP_DIR, "banner.png"))

    for name, fn in UI_ICONS.items():
        fn().save(os.path.join(UI_DIR, "ic_" + name + ".png"))
    write_anm2(os.path.join(UI_DIR, "altar_icon16.anm2"), "ic_coin.png", 16, 16)

    altar_gem(24).save(os.path.join(UI_DIR, "altar_button.png"))
    Image.new("RGBA", (4, 4), (255, 255, 255, 255)).save(os.path.join(UI_DIR, "altar_pixel.png"))
    write_anm2(os.path.join(UI_DIR, "altar_pixel.anm2"), "altar_pixel.png", 4, 4)
    # 256px frame for boss/character portraits loaded from the game at runtime
    write_anm2(os.path.join(UI_DIR, "altar_portrait.anm2"), "altar_pixel.png", 256, 256)
    write_anm2(os.path.join(UI_DIR, "altar_button.anm2"), "altar_button.png", 24, 24)
    write_anm2(os.path.join(UI_DIR, "altar_icon.anm2"), "../items/collectibles/cosmic_overclock.png", 32, 32)
    big.resize((48, 48), Image.LANCZOS).save(os.path.join(MOD, "thumb.png"))
    big.resize((32, 32), Image.LANCZOS).save(os.path.join(APP_DIR, "icon.png"))
    print(f"wrote {len(ITEMS)} items x {FRAMES} frames, VFX and {len(UI_ICONS)} UI icons")


if __name__ == "__main__":
    main()
