"""Hand-drawn flipbook animations for the OBLIVION story cutscene.

Run:  python make_story.py

Each of the 5 panels is a 16-frame flipbook (384x216 per frame, 4x4 grid sheet)
drawn here in code with the boss's own pixel sprites (Seraphiel is the boss before
the fall), ink lines that "boil" frame to frame, paper grain, and
moving parts (stars lighting up, tears rising, lights going out, the dark
swallowing her, the giant looming). Writes resources/gfx/altar/story/flipN.png
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

STAR_POS = [(random.Random(i).uniform(40, W - 40), random.Random(i + 50).uniform(30, H * 0.45)) for i in range(26)]


def scene1(f):
    """Before the basement, there was a sky: she lights the stars one by one."""
    t = f / FRAMES
    pg = Page(f, (16, 18, 44), (52, 44, 74), 1)
    for k, (sx, sy) in enumerate(STAR_POS):
        lit = 1.0 if k < 16 else clamp(t * 14 - (k - 16) * 1.3)
        lantern(pg, sx + math.sin(t * TAU + k) * 3, sy, 7 + (k % 3) * 2, lit, thread_top=0)
    hills(pg, H * 0.82, (34, 30, 46), 4)
    house(pg, W * 0.8, H * 0.84, 1.6, light=0.8 + 0.2 * math.sin(t * TAU * 2))
    pg.glow(W * 0.33, H * 0.5, 170, (255, 236, 190), 0.9)
    paste_sprite(pg, seraph(t), W * 0.33, H * 0.5 + math.sin(t * TAU) * 8, 2.3)
    return pg.finish()


def scene2(f):
    """One for every child who cried: tears rise as threads of light to her."""
    t = f / FRAMES
    pg = Page(f, (20, 16, 30), (44, 32, 30), 2)
    pg.shape([(0, H * 0.74), (W, H * 0.74), (W, H), (0, H)], (40, 30, 28, 255))
    for k in range(7):
        x = 40 + k * 120
        pg.line([(x, H * 0.74), (x + 30, H)], fill=(30, 22, 20, 255), width=3)
    center = (W * 0.5, H * 0.34)
    for k in range(7):
        kx, ky = W * (0.1 + k * 0.133), H * 0.94
        child(pg, kx, ky, 1.5, tear=(t * 3 + k * 0.3) % 1)
        rise = (t + k / 7) % 1
        x = kx + (center[0] - kx) * rise
        y = (ky - 40) + (center[1] + 40 - (ky - 40)) * rise
        pg.line([(kx, ky - 40), (x + math.sin(rise * 6) * 8, y)], fill=(255, 220, 150, 140), width=2, amp=0.6)
        pg.glow(x, y, 14, (255, 220, 140), 1.0)
    pg.glow(center[0], center[1], 150, (255, 236, 190), 1.0)
    paste_sprite(pg, seraph(t, charge=0.2), center[0], center[1] + math.sin(t * TAU) * 5, 1.9)
    return pg.finish()


def scene3(f):
    """The crying never stopped: the stars go out one by one and her light fades."""
    t = f / (FRAMES - 1)
    pg = Page(f, lerp((22, 22, 44), (10, 10, 14), t), lerp((40, 36, 56), (18, 18, 22), t), 3)
    for k, (sx, sy) in enumerate(STAR_POS):
        lit = clamp(1 - (t * 30 - k) / 3)
        lantern(pg, sx, sy + (1 - lit) * 20, 7 + (k % 3) * 2, lit, thread_top=0)
    rng = random.Random(33)
    for _ in range(80):  # falling ash
        x, y0 = rng.uniform(0, W), rng.uniform(0, H)
        y = (y0 + t * 160) % H
        pg.d.ellipse((x, y, x + 3, y + 3), fill=(150, 146, 156, 150))
    hills(pg, H * 0.88, (18, 18, 24), 7)
    if t < 0.7:
        pg.glow(W / 2, H * 0.6, 150 * (1 - t), (255, 236, 190), 1 - t)
    paste_sprite(pg, seraph(t * 2, dim=t * 0.85), W / 2, H * 0.6 + t * 30, 2.2)
    return pg.finish()


def scene4(f):
    """She swallows the dark to save the last light, and the dark swallows her."""
    t = f / (FRAMES - 1)
    pg = Page(f, lerp((26, 16, 40), (4, 2, 8), t), lerp((40, 20, 50), (10, 4, 14), t), 4)
    rng = random.Random(44)
    for k in range(60):  # light pulled toward her
        a = rng.uniform(0, TAU)
        d = rng.uniform(80, 340) * (1 - (t * 1.5 + k / 60) % 1)
        x, y = W / 2 + math.cos(a) * d, H * 0.5 + math.sin(a) * d * 0.6
        pg.line([(x, y), (x - math.cos(a) * 10, y - math.sin(a) * 6)], fill=(230, 200, 255, 200), width=2, amp=0.3)
    scale, cx, cy = 2.4, W / 2, H * 0.52
    angel_img = seraph(t, dim=t * 0.5)
    dark_img = figure(t, PALETTES["normal"])
    # cross-dissolve the angel into Oblivion
    mix = Image.blend(angel_img, dark_img, clamp((t - 0.25) / 0.55))
    paste_sprite(pg, mix, cx, cy, scale)
    hole = Image.new("RGBA", (200, 200))
    ms.gargantua(hole, 100, 100, 3 + 13 * t, t * 2, disk=2.7, tilt=0.28)
    paste_sprite(pg, hole, cx, cy - (64 - 32) * scale, 1.6)
    return pg.finish()


def scene5(f):
    """Now I am Oblivion: the giant looms over one small child with a candle."""
    t = f / FRAMES
    pg = Page(f, (8, 6, 14), (24, 16, 18), 5)
    paste_sprite(pg, figure(t, PALETTES["normal"]), W / 2, H * 0.42 + math.sin(t * TAU) * 6, 3.4)
    pg.shape([(0, H * 0.86), (W, H * 0.86), (W, H), (0, H)], (22, 16, 14, 255))
    flick = 0.8 + 0.2 * math.sin(t * TAU * 3)
    pg.glow(W / 2 + 22, H * 0.79, 90 * flick, (255, 180, 80), 1.2)
    child(pg, W / 2, H * 0.92, 2.0)
    pg.line([(W / 2 + 22, H * 0.86), (W / 2 + 22, H * 0.8)], fill=(240, 230, 210, 255), width=5)
    pg.shape([(W / 2 + 18, H * 0.8), (W / 2 + 22, H * 0.74 - flick * 6), (W / 2 + 26, H * 0.8)], (255, 200, 90, 255),
             width=2)
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


def main():
    os.makedirs(STORY, exist_ok=True)
    rows = (FRAMES + COLS - 1) // COLS
    for n, scene in enumerate(SCENES, 1):
        sheet = Image.new("RGBA", (PW * COLS, PH * rows))
        for f in range(FRAMES):
            sheet.alpha_composite(scene(f), ((f % COLS) * PW, (f // COLS) * PH))
        sheet.save(os.path.join(STORY, f"flip{n}.png"))
        write_anm2(os.path.join(STORY, f"flip{n}.anm2"), f"flip{n}.png")
        print(f"flipbook {n} written")


if __name__ == "__main__":
    main()
