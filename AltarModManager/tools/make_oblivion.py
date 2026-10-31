"""Generates the Oblivion boss sprite sheet, its anm2 and portrait.

Run:  python make_oblivion.py   (build.py runs it too)

Sheet rows (128x128 frames): Idle x8, Charge x6, Enraged x8, Death x16.
"""
import math
import os
import random

from PIL import Image

import make_sprites as ms
from make_sprites import TAU, canvas, clamp, gargantua, lerp, put

UI_DIR = ms.UI_DIR
S = 128
CX, CY = 64, 60

PALETTES = {
    # Form 0, Seraphiel before the fall: white robe, gold, silver hair
    "angel": dict(dark=(150, 140, 180), mid=(238, 236, 248), rim=(255, 240, 200), glow=(255, 236, 180),
                  bone=(255, 246, 222), bone_dark=(206, 172, 110), hot=(255, 255, 245), warm=(255, 210, 120),
                  cool=(160, 120, 60), feather=(255, 255, 255)),
    "normal": dict(dark=(16, 8, 30), mid=(54, 24, 96), rim=(176, 120, 255), glow=(205, 150, 255),
                   bone=(214, 206, 232), bone_dark=(120, 110, 150), hot=(255, 240, 215), warm=(255, 150, 60),
                   cool=(150, 40, 30)),
    "enraged": dict(dark=(30, 4, 8), mid=(112, 18, 28), rim=(255, 100, 60), glow=(255, 150, 70),
                    bone=(240, 214, 200), bone_dark=(150, 90, 80), hot=(255, 250, 230), warm=(255, 60, 30),
                    cool=(120, 0, 10)),
    # Form 2, the Hollow Seraph: void wings, cracked halo
    "seraph": dict(dark=(12, 6, 26), mid=(40, 20, 80), rim=(220, 200, 255), glow=(235, 225, 255),
                   bone=(245, 240, 255), bone_dark=(150, 140, 190), hot=(255, 255, 255), warm=(190, 140, 255),
                   cool=(60, 20, 120), feather=(250, 248, 255)),
    # Form 3, the Last Star: radiant gold and crimson
    "star": dict(dark=(60, 12, 8), mid=(170, 60, 30), rim=(255, 230, 150), glow=(255, 220, 140),
                 bone=(255, 246, 220), bone_dark=(210, 160, 90), hot=(255, 255, 240), warm=(255, 120, 40),
                 cool=(150, 10, 10), feather=(255, 244, 210)),
}


def disc(img, x, y, r, c):
    for yy in range(int(y - r - 1), int(y + r + 2)):
        for xx in range(int(x - r - 1), int(x + r + 2)):
            if (xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2 <= r * r:
                put(img, xx, yy, c)


def tendrils(img, t, pal, reach=1.0):
    roots = [((44, 56), -2.5), ((84, 56), -0.64), ((48, 80), -2.75), ((80, 80), -0.39)]
    for i, ((rx, ry), ang) in enumerate(roots):
        x, y = rx, ry
        length = 50 * reach
        steps = 40
        for k in range(steps):
            s = k / (steps - 1)
            a = ang + math.sin(s * 4.5 + t * TAU + i * 1.7) * 0.55 * s
            x += math.cos(a) * length / steps
            y += math.sin(a) * length / steps
            th = 5.5 * (1 - s) + 1.2
            disc(img, x, y, th, lerp(pal["mid"], pal["dark"], s * 0.8))
            disc(img, x - 0.8, y - th * 0.6, max(0.6, th * 0.35), lerp(pal["rim"], pal["mid"], s))
        disc(img, x, y, 1.6, pal["glow"])


def cloak(img, t, pal):
    for y in range(46, 124):
        k = (y - 46) / 74
        half = 16 + 26 * k ** 0.85
        for x in range(int(CX - half), int(CX + half) + 1):
            hem = 112 + 6 * math.sin(x * 0.33 + t * TAU) + (5 if (x // 5) % 2 else 0)
            if y > hem:
                continue
            u = (x - CX) / half
            col = lerp(pal["mid"], pal["dark"], k * 0.7 + abs(u) * 0.35)
            if abs(math.sin(u * 7 + 0.4)) < 0.12:  # cloth folds
                col = lerp(col, pal["dark"], 0.6)
            if u < -0.86:
                col = lerp(col, pal["rim"], 0.45)
            put(img, x, y, col)


def ribcage(img, t, pal, power=1.0):
    pulse = 0.6 + 0.4 * math.sin(t * TAU * 2)
    for y in range(60, 92):
        for x in range(54, 75):
            d = math.hypot((x - 64) / 4, (y - 76) / 13)
            if d < 1:
                put(img, x, y, lerp(pal["glow"], pal["hot"], (1 - d) * pulse * power))
    for i in range(4):
        ry = 64 + i * 7
        for side in (-1, 1):
            for k in range(13):
                x = 64 + side * (2 + k)
                y = ry + (k * k) * 0.05
                put(img, x, y, pal["bone"] if k < 10 else pal["bone_dark"])
                put(img, x, y + 1, pal["bone_dark"])


def pauldrons(img, pal):
    for side in (-1, 1):
        bx = 64 + side * 24
        ms.fill(img, ms.ellipse(bx, 52, 11, 7), lambda x, y: lerp(pal["bone"], pal["bone_dark"], (y - 45) / 14))
        for j, (dx, h) in enumerate(((0, 16), (side * 7, 12), (-side * 6, 9))):
            sx = bx + dx
            ms.fill(img, ms.poly([(sx - 3, 50), (sx + side * 4, 50 - h), (sx + 3, 50)]),
                    lambda x, y: lerp(pal["bone"], pal["bone_dark"], (50 - y) / 18))


def halo(img, t, pal, spin=1.0):
    rot = t * TAU / 12 * spin
    for i in range(12):
        a = rot + i * TAU / 12
        x0, y0 = CX + math.cos(a) * 18, 32 + math.sin(a) * 18
        x1, y1 = CX + math.cos(a) * 26, 32 + math.sin(a) * 26
        for k in range(10):
            f = k / 9
            disc(img, x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, 1.8 * (1 - f) + 0.5, lerp(pal["bone"], pal["glow"], f))
    for i in range(80):
        a = i * TAU / 80
        put(img, CX + math.cos(a) * 17, 32 + math.sin(a) * 17, pal["bone_dark"])


def head(img, t, pal, r=9.5, brightness=1.0):
    hot = lerp(pal["warm"], pal["hot"], brightness)
    gargantua(img, CX, 32, r, t, disk=2.5, tilt=0.3, hot=hot, warm=pal["warm"], cool=pal["cool"])


def aura(img, pal, strength):
    """Soft glow behind the figure, drawn first."""
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - CX, (y - 58) * 0.8)
            a = clamp(1 - d / 62) ** 2 * strength
            if a > 0.03:
                put(img, x, y, pal["glow"] + (int(150 * a),))


def wings(img, t, pal, pairs):
    """Feathered wings fanning out from the shoulders; pairs = 2 (seraph) or 3 (last star)."""
    flap = math.sin(t * TAU) * 0.12
    spreads = [(-1.15, 44), (-0.45, 50), (0.25, 40)][:pairs]
    for side in (-1, 1):
        for k, (base_ang, length) in enumerate(spreads):
            bx, by = CX + side * 14, 50
            # solid wing membrane under the feathers so it reads as one shape
            edge, tips = [], []
            for j in range(11):
                s = j / 10
                a = base_ang + flap * (1 + k * 0.4) - s * 0.5
                ex = bx + side * math.cos(a) * length * s
                ey = by + math.sin(a) * length * s
                flen = 9 + 12 * s
                edge.append((ex, ey))
                tips.append((ex + side * math.cos(a + 1.25) * flen * 0.5, ey + math.sin(a + 1.25) * flen))
            ms.fill(img, ms.poly([(bx, by)] + edge + tips[::-1]),
                    lambda x, y: lerp(pal["mid"], pal.get("feather", pal["bone"]), 0.25 + 0.35 * clamp(abs(x - bx) / length)))
            for j in range(11):
                s = j / 10
                # the wing's leading edge curves outward and up
                a = base_ang + flap * (1 + k * 0.4) - s * 0.5
                ex = bx + side * math.cos(a) * length * s
                ey = by + math.sin(a) * length * s
                flen = 9 + 12 * s
                fa = a + 1.25  # feathers hang below the edge
                for f in range(int(flen)):
                    q = f / flen
                    x = ex + side * math.cos(fa) * f * 0.5
                    y = ey + math.sin(fa) * f
                    col = lerp(pal["mid"], pal.get("feather", pal["bone"]), clamp(q * 1.3 * (0.4 + s)))
                    disc(img, x, y, 1.6 * (1 - q * 0.5), col)
                disc(img, ex, ey, 1.4, pal["rim"])


def angel_head(img, t, pal):
    """Seraphiel's face where Oblivion has her black hole: silver hair, closed eyes."""
    for y in range(14, 52):
        for x in range(CX - 14, CX + 15):
            if ((x - CX) / 13.5) ** 2 + ((y - 33) / 17) ** 2 <= 1:
                put(img, x, y, lerp((236, 236, 250), (170, 170, 200), (y - 14) / 38))
    disc(img, CX, 31, 9, (252, 232, 220))
    for dx in (-4, 3):  # closed eyes
        put(img, CX + dx, 31, (90, 60, 70))
        put(img, CX + dx + 1, 31, (90, 60, 70))
    put(img, CX - 5, 34, (255, 180, 180))
    put(img, CX + 5, 34, (255, 180, 180))
    for k in range(5):  # bangs
        put(img, CX - 6 + k * 3, 23, (220, 220, 240))


def chest_star(img, t, pal):
    pulse = 0.6 + 0.4 * math.sin(t * TAU * 2)
    for r in range(7, 0, -1):
        disc(img, CX, 74, r * pulse + 1, lerp(pal["glow"], pal["hot"], 1 - r / 7) + (int(90 + 20 * (7 - r)),))


def figure(t, pal, charge=0.0, jitter=(0, 0), form=1):
    img = canvas(S)
    if charge > 0 or form in (0, 3):
        aura(img, pal, max(charge, 0.45 if form == 3 else 0.35 if form == 0 else 0))
    body = canvas(S)
    if form >= 2 or form == 0:
        wings(body, t, pal, 3 if form == 3 else 2)
    halo(body, t, pal, spin=(1 + charge * 3) * (2 if form == 3 else 1))
    if form == 2:  # crack the halo: knock out a wedge
        for y in range(4, 60):
            for x in range(CX - 4, CX + 30):
                if 0 < (x - CX) * 0.6 - (y - 32) < 6:
                    body.putpixel((x, y), (0, 0, 0, 0))
    if form == 3:
        for i in range(120):  # second, larger halo ring
            a = i * TAU / 120 + t
            put(body, CX + math.cos(a) * 30, 32 + math.sin(a) * 30, pal["rim"])
    if form == 1:
        tendrils(body, t, pal)
    cloak(body, t, pal)
    pauldrons(body, pal)
    if form == 0:
        chest_star(body, t, pal)
        angel_head(body, t, pal)
    else:
        ribcage(body, t, pal, power=1 + charge + (form - 1) * 0.6)
        head(body, t, pal, r=9.5 + (form - 1) * 1.5, brightness=0.5 + charge * 0.5 + (form - 1) * 0.2)
    ms.outline(body, (8, 4, 10, 255))
    img.alpha_composite(body, jitter)
    if charge > 0:  # sparks streaming into the core
        rng = random.Random(int(t * 100))
        for _ in range(int(30 * charge)):
            a = rng.random() * TAU
            d = 30 + rng.random() * 30 * (1 - t)
            put(img, CX + math.cos(a) * d, 32 + math.sin(a) * d, pal["hot"] + (220,))
    return img


def death_frame(i, n):
    """Clean death: halo shatters, body pulses white, dissolves upward into glowing
    motes while rays grow from the core, then implodes to a point and a ring."""
    t = i / (n - 1)
    pal = PALETTES["star"]
    base = figure(0.3, pal, charge=0.4, form=3)
    img = canvas(S)
    rng = random.Random(9)

    # 1) light rays behind the body (clean wedges), growing then fading
    ray_k = clamp(t * 1.6) * clamp((1 - t) * 3)
    if ray_k > 0:
        rays = canvas(S)
        for k in range(12):
            a = k * TAU / 12 + t * 0.6
            for d in range(4, int(70 * ray_k)):
                w = 0.06 + d / 900
                for side in (-1, 0, 1):
                    put(rays, CX + math.cos(a + side * w) * d, 60 + math.sin(a + side * w) * d,
                        (255, 240, 210, int(150 * (1 - d / 70))))
        img.alpha_composite(rays)

    # 2) body: white pulses, then dissolves upward into motes (bottom first)
    flash = 0.5 + 0.5 * math.cos(t * TAU * 3) if t < 0.35 else 0.0
    dissolve = clamp((t - 0.25) / 0.45)
    shrink = clamp((t - 0.55) / 0.25)
    for y in range(S):
        for x in range(S):
            c = base.getpixel((x, y))
            if not c[3]:
                continue
            # each pixel gets a dissolve time: lower pixels go first, with a little noise
            td = (S - y) / S * 0.8 + rng.random() * 0.2
            col = lerp(c[:3], (255, 255, 255), flash * 0.7 + dissolve * 0.4)
            if dissolve < td:
                # pull everything toward the core as it collapses
                px_ = CX + (x - CX) * (1 - shrink * 0.85)
                py_ = 60 + (y - 60) * (1 - shrink * 0.85)
                put(img, px_, py_, col + (255,))
            else:
                age = (dissolve - td) * 3
                my = y - age * 40 - rng.random() * 6
                if age < 1 and my > 6:  # motes fade before they could stack at the frame edge
                    put(img, x + math.sin(y * 0.7 + age * 6) * 2, my, (255, 236, 200, int(255 * (1 - age) * min(1, my / 20))))

    # 3) halo shards fly outward and fade (first third)
    if t < 0.45:
        for k in range(12):
            a = k * TAU / 12 + 0.2
            d = 22 + t * 90
            fade = int(255 * (1 - t / 0.45))
            for f in range(5):
                put(img, CX + math.cos(a) * (d + f), 32 + math.sin(a) * (d + f) - t * 10, (255, 230, 160, fade))

    # 4) the core: black hole shrinks to a point
    if t < 0.85:
        r = 11 * (1 - clamp((t - 0.5) / 0.35)) + 1.5
        gargantua(img, CX, 32 + (60 - 32) * shrink, r, t * 3, disk=2.6, tilt=0.3,
                  hot=pal["hot"], warm=pal["warm"], cool=pal["cool"])

    # 5) implosion: clean expanding ring + fading flash disc
    if t > 0.78:
        k = (t - 0.78) / 0.22
        rad = 6 + k * 58
        for j in range(360):
            a = j * TAU / 360
            for w in (0, 1):
                put(img, CX + math.cos(a) * (rad + w), 60 + math.sin(a) * (rad + w) * 0.8,
                    (255, 250, 235, int(255 * (1 - k))))
        disc(img, CX, 60, 14 * (1 - k) + 2, (255, 255, 255, int(255 * (1 - k))))
    return img

def shake(i):
    return random.Random(i).randint(-1, 1), random.Random(i + 9).randint(-1, 1)


# name, frames, delay, loop, frame function. One row per animation; one pair per form.
ANIMS = [
    ("Idle1", 8, 3, True, lambda i: figure(i / 8, PALETTES["normal"])),
    ("Charge1", 6, 3, True, lambda i: figure(i / 6, PALETTES["normal"], charge=0.4 + i / 10)),
    ("Idle2", 8, 3, True, lambda i: figure(i / 8, PALETTES["seraph"], form=2)),
    ("Charge2", 6, 3, True, lambda i: figure(i / 6, PALETTES["seraph"], charge=0.4 + i / 10, form=2)),
    ("Idle3", 8, 2, True, lambda i: figure(i / 8, PALETTES["star"], charge=0.3, jitter=shake(i), form=3)),
    ("Charge3", 6, 2, True, lambda i: figure(i / 6, PALETTES["star"], charge=0.6 + i / 12, jitter=shake(i), form=3)),
    ("Death", 24, 3, False, lambda i: death_frame(i, 24)),
]

FORM_NAMES = ["Form I - Oblivion", "Form II - The Hollow Seraph", "Form III - The Last Star"]


# ---------------------------------------------------------------- the arena floor (338x182 = a 1x1 room)

AW, AH = 390, 234


def arena_frame(i, n=8):
    """Void floor laid over the boss room: starfield, faint tiles, cracks of light
    and a slowly turning sigil ring of runes around the centre."""
    t = i / n
    rng = random.Random(77)
    img = Image.new("RGBA", (AW, AH))
    cx, cy = AW / 2, AH / 2
    for y in range(AH):
        for x in range(AW):
            d = math.hypot((x - cx) / (AW / 2), (y - cy) / (AH / 2))
            c = lerp((26, 14, 46), (6, 4, 12), clamp(d))
            if x % 26 == 0 or y % 26 == 0:  # faint floor tiles
                c = lerp(c, (60, 40, 96), 0.25 * (1 - clamp(d)))
            img.putpixel((x, y), c + (int(255 * clamp(1.15 - d * 0.35)),))
    # outer band where the walls were: broken stone drifting in the void
    for _ in range(60):
        side = rng.randrange(4)
        if side < 2:
            x, y = rng.uniform(0, AW), (rng.uniform(2, 24) if side == 0 else rng.uniform(AH - 24, AH - 2))
        else:
            x, y = (rng.uniform(2, 24) if side == 2 else rng.uniform(AW - 24, AW - 2)), rng.uniform(0, AH)
        r = rng.uniform(2, 6)
        bob = math.sin(t * TAU + x * 0.1) * 1.5
        disc(img, x, y + bob, r, (44, 34, 60, 255))
        disc(img, x - r * 0.3, y + bob - r * 0.3, r * 0.5, (70, 58, 96, 255))
    for _ in range(140):  # twinkling stars
        x, y, ph = rng.randrange(AW), rng.randrange(AH), rng.random()
        a = 0.35 + 0.65 * abs(math.sin((t + ph) * math.pi))
        put(img, x, y, (230, 215, 255, int(200 * a)))
    for k in range(7):  # cracks of light running out from the sigil
        a = k * TAU / 7 + 0.3
        x, y = cx + math.cos(a) * 64, cy + math.sin(a) * 64 * 0.62
        for _ in range(26):
            x += math.cos(a) * 3
            y += math.sin(a) * 3 * 0.62
            a += rng.uniform(-0.35, 0.35)
            glow = 0.5 + 0.5 * math.sin(t * TAU + k)
            put(img, x, y, lerp((120, 70, 200), (255, 220, 160), glow) + (220,))
    # sigil: two rings, a six-point star, runes riding the outer ring
    for r, col in ((62, (210, 170, 255)), (52, (255, 210, 140))):
        for j in range(360):
            a = j * TAU / 360
            put(img, cx + math.cos(a) * r, cy + math.sin(a) * r * 0.62, col + (200,))
    pts = [(cx + math.cos(k * TAU / 6 + t * TAU / 6) * 52, cy + math.sin(k * TAU / 6 + t * TAU / 6) * 52 * 0.62)
           for k in range(6)]
    for k in range(6):
        x0, y0 = pts[k]
        x1, y1 = pts[(k + 2) % 6]
        for f in range(60):
            q = f / 59
            put(img, x0 + (x1 - x0) * q, y0 + (y1 - y0) * q, (255, 230, 180, 170))
    for k in range(16):
        a = k * TAU / 16 - t * TAU / 8
        rx, ry = cx + math.cos(a) * 57, cy + math.sin(a) * 57 * 0.62
        for dx, dy in ((0, -2), (0, -1), (0, 0), (0, 1), (-1, 0), (1, 0), (1, -2) if k % 2 else (-1, 2)):
            put(img, rx + dx, ry + dy, (255, 245, 220, 230))
    disc(img, cx, cy, 6, (0, 0, 0, 255))
    disc(img, cx, cy, 7.5, (200, 160, 255, 120))
    return img


def write_arena():
    n = 8
    strip = Image.new("RGBA", (AW * n, AH))
    for i in range(n):
        strip.alpha_composite(arena_frame(i, n), (i * AW, 0))
    strip.save(os.path.join(UI_DIR, "arena.png"))
    write_anm2(os.path.join(UI_DIR, "arena.anm2"), "arena.png", AW, AH,
               [("Idle", n, 6, True, None)], pivot=(AW // 2, AH // 2))




# ---------------------------------------------------------------- deep space (Form IV's arena)

def cosmic_frame(i, n=8):
    """Where she drags you after she falls: nebula, a turning galaxy, a ringed
    planet and a sky full of stars. Covers floor and walls like the void arena."""
    t = i / n
    rng = random.Random(99)
    img = Image.new("RGBA", (AW, AH))
    for y in range(AH):
        for x in range(AW):
            u, v = x / AW, y / AH
            n1 = math.sin(u * 7.1 + math.sin(v * 5.3) * 1.7) * math.cos(v * 6.2 - u * 2.1)
            n2 = math.sin((u + v) * 11.3 + math.cos(u * 9.1) * 2.0)
            k = clamp(0.5 + 0.35 * n1 + 0.2 * n2)
            c = lerp((3, 2, 12), (38, 14, 66), k)
            c = lerp(c, (18, 58, 120), clamp(n2 * 0.5 + 0.1) * 0.5)
            c = lerp(c, (150, 36, 118), clamp(n1 - 0.35) * 0.6)
            img.putpixel((x, y), c + (255,))
    # a spiral galaxy, slowly turning
    gx, gy = AW * 0.72, AH * 0.3
    for s in range(1100):
        r = (s / 1100) * 48
        a = r * 0.17 + (s % 2) * math.pi + t * TAU / 8
        x = gx + math.cos(a) * r + rng.uniform(-2, 2)
        y = gy + math.sin(a) * r * 0.45 + rng.uniform(-1, 1)
        put(img, x, y, lerp((255, 240, 220), (150, 120, 255), r / 48) + (int(210 * (1 - r / 62)),))
    for r in range(9, 0, -1):
        disc(img, gx, gy, r * 0.8, lerp((255, 250, 235), (190, 160, 255), r / 9) + (int(255 * (1 - r / 10)),))
    # a cold ringed planet low in the corner
    px_, py_, pr = AW * 0.17, AH * 0.8, 24
    for y in range(int(py_ - pr), int(py_ + pr) + 1):
        for x in range(int(px_ - pr), int(px_ + pr) + 1):
            d = math.hypot(x - px_, y - py_)
            if d <= pr:
                light = clamp(0.75 - ((x - px_) + (y - py_)) / (pr * 2.2))
                band = 0.08 * math.sin((y - py_) * 0.7)
                put(img, x, y, lerp((10, 20, 50), (110, 170, 230), clamp(light + band)) + (255,))
    for j in range(720):
        a = j * TAU / 720
        x, y = px_ + math.cos(a) * pr * 1.75, py_ + math.sin(a) * pr * 0.35
        if not (math.sin(a) < 0 and math.hypot(x - px_, y - py_) < pr):  # ring passes behind the top
            put(img, x, y, (200, 220, 255, 170))
    # stars, some large with cross glints, all twinkling
    for _ in range(460):
        x, y, ph = rng.randrange(AW), rng.randrange(AH), rng.random()
        tw = 0.3 + 0.7 * abs(math.sin((t + ph) * math.pi))
        col = rng.choice(((255, 255, 255), (200, 220, 255), (255, 230, 200), (230, 200, 255)))
        put(img, x, y, col + (int(230 * tw),))
        if rng.random() < 0.06:
            for k in (1, 2):
                for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
                    put(img, x + dx, y + dy, col + (int(150 * tw / k),))
    return img


def write_cosmic():
    n = 8
    strip = Image.new("RGBA", (AW * n, AH))
    for i in range(n):
        strip.alpha_composite(cosmic_frame(i, n), (i * AW, 0))
    strip.save(os.path.join(UI_DIR, "cosmic.png"))
    write_anm2(os.path.join(UI_DIR, "cosmic.anm2"), "cosmic.png", AW, AH,
               [("Idle", n, 8, True, None)], pivot=(AW // 2, AH // 2))


SG_W, SG_H, SG_N = 168, 104, 16


def sigil_frame(i):
    """The rune circle she draws on the floor before every attack: two rings, a hexagram
    and sixteen runes, turning in opposite directions; in perspective, white so it can
    be tinted per form. One loop turns the star by a sixth so it repeats seamlessly."""
    from PIL import ImageDraw
    k = 4  # supersample
    t = i / SG_N
    img = Image.new("RGBA", (SG_W * k, SG_H * k))
    d = ImageDraw.Draw(img)
    cx, cy = SG_W * k / 2, SG_H * k / 2

    def P(r, a):
        return (cx + math.cos(a) * r * k, cy + math.sin(a) * r * k * 0.6)

    def ring(r, w, alpha):
        pts = [P(r, j * TAU / 120) for j in range(121)]
        d.line(pts, fill=(255, 255, 255, alpha), width=w * k)

    ring(80, 2, 255)
    ring(73, 1, 200)
    ring(30, 2, 230)
    ring(22, 1, 160)
    star_rot = t * TAU / 6
    pts = [P(66, star_rot + j * TAU / 6) for j in range(6)]
    for j in range(6):
        d.line([pts[j], pts[(j + 2) % 6]], fill=(255, 255, 255, 220), width=2 * k)
    rune_rot = -t * TAU / 16
    for j in range(16):
        a = rune_rot + j * TAU / 16
        x, y = P(76.5, a)
        s = 3.2 * k
        shape = j % 4
        if shape == 0:
            d.line([(x, y - s), (x, y + s)], fill=(255, 255, 255, 240), width=k)
            d.line([(x - s * 0.7, y - s * 0.3), (x + s * 0.7, y - s * 0.3)], fill=(255, 255, 255, 240), width=k)
        elif shape == 1:
            d.polygon([(x, y - s), (x + s * 0.8, y + s * 0.6), (x - s * 0.8, y + s * 0.6)], outline=(255, 255, 255, 240), width=k)
        elif shape == 2:
            d.ellipse((x - s * 0.6, y - s * 0.6, x + s * 0.6, y + s * 0.6), outline=(255, 255, 255, 240), width=k)
            d.line([(x, y + s * 0.6), (x, y + s * 1.1)], fill=(255, 255, 255, 240), width=k)
        else:
            d.line([(x - s * 0.7, y - s), (x + s * 0.7, y + s)], fill=(255, 255, 255, 240), width=k)
            d.line([(x + s * 0.7, y - s), (x - s * 0.7, y + s)], fill=(255, 255, 255, 240), width=k)
    for j in range(6):  # small marks at the star's points
        x, y = P(66, star_rot + j * TAU / 6)
        d.ellipse((x - 2.5 * k, y - 2.5 * k, x + 2.5 * k, y + 2.5 * k), fill=(255, 255, 255, 255))
    img = img.resize((SG_W, SG_H), Image.LANCZOS)
    # a faint wash of light inside the outer ring
    wash = Image.new("RGBA", (SG_W, SG_H))
    for y in range(SG_H):
        for x in range(SG_W):
            dd = math.hypot((x - SG_W / 2) / 80, (y - SG_H / 2) / 48)
            if dd < 1:
                wash.putpixel((x, y), (255, 255, 255, int(40 * (1 - dd))))
    wash.alpha_composite(img)
    return wash


def write_sigil():
    strip = Image.new("RGBA", (SG_W * SG_N, SG_H))
    for i in range(SG_N):
        strip.alpha_composite(sigil_frame(i), (i * SG_W, 0))
    strip.save(os.path.join(UI_DIR, "sigil.png"))
    write_anm2(os.path.join(UI_DIR, "sigil.anm2"), "sigil.png", SG_W, SG_H, [("Spin", SG_N, 2, True, None)],
               pivot=(SG_W // 2, SG_H // 2))


def write_glow():
    """Soft white light (alpha falls off like a bloom) tinted in game for auras and glows."""
    g = 64
    img = Image.new("RGBA", (g, g))
    for y in range(g):
        for x in range(g):
            d = math.hypot(x - g / 2 + 0.5, y - g / 2 + 0.5) / (g / 2)
            a = clamp(1 - d) ** 2.2
            img.putpixel((x, y), (255, 255, 255, int(255 * a)))
    img.save(os.path.join(UI_DIR, "glow.png"))
    write_anm2(os.path.join(UI_DIR, "glow.anm2"), "glow.png", g, g, [("Idle", 1, 1, True, None)], pivot=(g // 2, g // 2))


def write_anm2(path, sheet, w, h, anims, pivot=None):
    frame_attrs = ('XScale="100" YScale="100" Visible="true" RedTint="255" GreenTint="255" BlueTint="255" '
                   'AlphaTint="255" RedOffset="0" GreenOffset="0" BlueOffset="0" Rotation="0" Interpolated="false"')
    out = [f"""<AnimatedActor>
  <Info CreatedBy="Altar" CreatedOn="30/10/2026" Version="1" Fps="30"/>
  <Content>
    <Spritesheets>
      <Spritesheet Path="{sheet}" Id="0"/>
    </Spritesheets>
    <Layers>
      <Layer Name="body" Id="0" SpritesheetId="0"/>
    </Layers>
    <Nulls/>
    <Events/>
  </Content>
  <Animations DefaultAnimation="{anims[0][0]}">"""]
    for row, (name, n, delay, loop, _) in enumerate(anims):
        frames = "\n".join(
            f'          <Frame XPosition="0" YPosition="0" XPivot="{(pivot or (w // 2, h // 2 + 20))[0]}" YPivot="{(pivot or (w // 2, h // 2 + 20))[1]}" XCrop="{i * w}" '
            f'YCrop="{row * h}" Width="{w}" Height="{h}" Delay="{delay}" {frame_attrs}/>' for i in range(n))
        out.append(f"""    <Animation Name="{name}" FrameNum="{n * delay}" Loop="{'true' if loop else 'false'}">
      <RootAnimation>
        <Frame XPosition="0" YPosition="0" Delay="{n * delay}" {frame_attrs}/>
      </RootAnimation>
      <LayerAnimations>
        <LayerAnimation LayerId="0" Visible="true">
{frames}
        </LayerAnimation>
      </LayerAnimations>
      <NullAnimations/>
      <Triggers/>
    </Animation>""")
    out.append("  </Animations>\n</AnimatedActor>\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def main():
    cols = max(a[1] for a in ANIMS)
    sheet = canvas(S * cols, S * len(ANIMS))
    for row, (name, n, _, _, fn) in enumerate(ANIMS):
        for i in range(n):
            sheet.alpha_composite(fn(i), (i * S, row * S))
    sheet.save(os.path.join(UI_DIR, "oblivion.png"))
    write_anm2(os.path.join(UI_DIR, "oblivion.anm2"), "oblivion.png", S, S, ANIMS)
    figure(0, PALETTES["normal"]).save(os.path.join(UI_DIR, "oblivion_portrait.png"))

    write_arena()
    write_cosmic()
    write_glow()
    write_sigil()


    # screenshot sheet of the three forms for the app / README
    shot = Image.new("RGBA", (3 * 300, 330), (20, 16, 26, 255))
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(shot)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 16)
    except OSError:
        font = None
    for k, (pal, name) in enumerate(zip(("normal", "seraph", "star"), FORM_NAMES)):
        fig = figure(0.15, PALETTES[pal], form=k + 1, charge=0.2 if k == 2 else 0).resize((256, 256), Image.NEAREST)
        shot.alpha_composite(fig, (k * 300 + 22, 40))
        d.text((k * 300 + 150 - d.textlength(name, font=font) / 2, 300), name, fill=(235, 225, 255), font=font)
    shot.save(os.path.join(ms.APP_DIR, "oblivion_forms.png"))
    print("oblivion sheet, forms and arena written")


if __name__ == "__main__":
    main()
