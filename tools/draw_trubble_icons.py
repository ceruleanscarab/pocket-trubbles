#!/usr/bin/env python3
"""draw_trubble_icons.py - draw the Trubbles' icons as pixel art from code.

The re-skin (2026-10-09) of pocket-tank's fish and sea icons: the same file
names and sizes (so icons.h keeps every name), drawn here with a few
primitives - discs, polygons, lines, a dark outline pass - and one Trubble
sprite reused across the badges. Programmer art, meant to be replaced by an
artist's: re-run, then tools/gen_icons.py to bake them into common/icons.c.

    python3 tools/draw_trubble_icons.py && python3 tools/gen_icons.py

Only the standard library (the PNGs are written with zlib).
"""
import math, os, struct, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "icons")

OUTLINE = (20, 16, 26)


def rgb(h):
    return ((h >> 16) & 255, (h >> 8) & 255, h & 255)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [None] * (w * h)                    # None = transparent, else (r, g, b, a)

    def put(self, x, y, c, a=255):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            if a >= 255 or self.px[y * self.w + x] is None:
                self.px[y * self.w + x] = (*c, a)
            else:
                old = self.px[y * self.w + x]
                t = a / 255
                self.px[y * self.w + x] = (*mix(old[:3], c, t), max(old[3], a))

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y * self.w + x]
        return None

    def ellipse(self, cx, cy, rx, ry, c, a=255):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                if dx * dx + dy * dy <= 1.0:
                    self.put(x, y, c, a)

    def disc(self, cx, cy, r, c, a=255):
        self.ellipse(cx, cy, r, r, c, a)

    def rect(self, x0, y0, x1, y1, c, a=255):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.put(x, y, c, a)

    def poly(self, pts, c, a=255):
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            yc = y + 0.5
            xs = []
            for i in range(len(pts)):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    xs.append(x0 + (x1 - x0) * (yc - y0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(math.ceil(xs[i] - 0.5)), int(math.floor(xs[i + 1] - 0.5)) + 1):
                    self.put(x, y, c, a)

    def line(self, x0, y0, x1, y1, c, a=255):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / max(n, 1)
            self.put(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c, a)

    def outline(self, c=OUTLINE):
        """a 1 px dark rim round everything opaque (the icons' hard edge)"""
        add = []
        for y in range(self.h):
            for x in range(self.w):
                if self.get(x, y) is not None:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    p = self.get(x + dx, y + dy)
                    if p is not None and p[3] > 128 and p[:3] != c:
                        add.append((x, y))
                        break
        for x, y in add:
            self.put(x, y, c)

    def save(self, name):
        raw = b""
        for y in range(self.h):
            raw += b"\0"
            for x in range(self.w):
                p = self.px[y * self.w + x]
                raw += bytes(p) if p else b"\0\0\0\0"
        ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
        png = (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0))
               + ch(b"IDAT", zlib.compress(raw, 9)) + ch(b"IEND", b""))
        open(os.path.join(OUT, name), "wb").write(png)


# ---- the Trubble ----
def trubble(cv, cx, cy, r, fur, look=0.0, asleep=False, feet=True):
    """a fuzzy ball: tufts, a lit upper left, a shaded lower right, two big
    eyes looking `look` (-1 left .. 1 right), shut to lines asleep"""
    fur = rgb(fur) if isinstance(fur, int) else fur
    dark, lite = mix(fur, (0, 0, 0), 0.35), mix(fur, (255, 255, 255), 0.4)
    if feet:
        for s in (-1, 1):
            cv.ellipse(cx + s * r * 0.45, cy + r * 0.92, max(1.2, r * 0.32), max(0.8, r * 0.18), mix(fur, (40, 28, 24), 0.7))
    n = max(8, int(r * 2.2))
    for k in range(n):                                   # tufts round the rim
        a = k * 2 * math.pi / n + 0.3
        if math.sin(a) > 0.75 and feet:
            continue                                     # not under it
        tip = r + (1.6 if k % 2 else 1.0) * max(1, r / 6)
        w = math.pi / n * 0.9
        cv.poly([(cx + math.cos(a - w) * r * 0.9, cy + math.sin(a - w) * r * 0.9),
                 (cx + math.cos(a) * tip, cy + math.sin(a) * tip),
                 (cx + math.cos(a + w) * r * 0.9, cy + math.sin(a + w) * r * 0.9)], dark if k % 2 else fur)
    cv.disc(cx, cy, r, fur)
    cv.ellipse(cx + r * 0.15, cy + r * 0.5, r * 0.8, r * 0.38, dark, 120)
    cv.ellipse(cx - r * 0.3, cy - r * 0.35, r * 0.5, r * 0.38, lite, 150)
    ex, gap, ey = look * r * 0.2, max(1.5, r * 0.36), cy - r * 0.12
    er = max(1.0, r * 0.27)
    for s in (-1, 1):
        x = cx + ex + s * gap
        if asleep:
            cv.line(x - er, ey + 0.5, x + er, ey + 0.5, (36, 26, 34))
            continue
        cv.ellipse(x, ey, er, er * 1.15, (255, 255, 255))
        pr = max(0.6, er * 0.6)
        cv.ellipse(x + look * er * 0.3, ey + er * 0.12, pr, pr * 1.1, (20, 12, 18))
        if er >= 2:
            cv.put(int(x + look * er * 0.3 - pr * 0.4), int(ey - pr * 0.4), (255, 255, 255))


PINK, TEAL, LILAC, PEACH, SKY, MINT, SUN = 0xf2a0b8, 0x38c9b4, 0xb59cf0, 0xffb07a, 0x7ab8f0, 0x9ad8a0, 0xffd166


def note(cv, x, y, c):
    c = rgb(c)
    cv.ellipse(x, y, 1.8, 1.4, c)
    cv.line(x + 1, y, x + 1, y - 6, c)
    cv.line(x + 1, y - 6, x + 3, y - 5, c)


def heart(cv, x, y, s, c=0xff4d6d):
    c = rgb(c)
    cv.disc(x - s * 0.5, y, s * 0.6, c)
    cv.disc(x + s * 0.5, y, s * 0.6, c)
    cv.poly([(x - s * 1.05, y + s * 0.2), (x + s * 1.05, y + s * 0.2), (x, y + s * 1.4)], c)


def moss(cv, x, y_bot, h, c=0x6f9763, puff=0xa9c98c):
    cv.line(x, y_bot, x, y_bot - h, rgb(c))
    cv.line(x + 1, y_bot, x + 1, y_bot - h + 1, mix(rgb(c), (0, 0, 0), 0.25))
    cv.disc(x + 0.5, y_bot - h, 1.8, rgb(puff))


def chip(cv, cx, cy, r):
    """a credit: a gold coin with a Trubble's face struck on it"""
    gold, dk, lt = rgb(0xf2c33a), rgb(0xa8741a), rgb(0xffe9a0)
    cv.disc(cx, cy, r, dk)
    cv.disc(cx - r * 0.06, cy - r * 0.06, r * 0.9, gold)
    cv.ellipse(cx - r * 0.3, cy - r * 0.35, r * 0.4, r * 0.25, lt, 170)
    cv.disc(cx, cy + r * 0.05, r * 0.55, dk)                      # the struck face
    cv.disc(cx - r * 0.04, cy, r * 0.5, mix(gold, lt, 0.3))
    for s in (-1, 1):
        cv.disc(cx + s * r * 0.2, cy - r * 0.05, max(0.8, r * 0.1), dk)
    n = max(10, int(r * 2.4))
    for k in range(n):                                   # the milled rim
        a = k * 2 * math.pi / n
        cv.put(cx + math.cos(a) * (r - 0.7), cy + math.sin(a) * (r - 0.7), lt if k % 2 else dk)


def crates(cv, ox, oy, s):
    ol, olk, orng, hz = rgb(0x7f8a55), rgb(0x434b2b), rgb(0xe0803a), rgb(0xf2c33a)
    cv.rect(ox, oy + 10 * s, ox + 9 * s, oy + 22 * s, ol)
    cv.rect(ox + 19 * s, oy + 6 * s, ox + 28 * s, oy + 22 * s, ol)
    cv.rect(ox + 8 * s, oy + 12 * s, ox + 20 * s, oy + 22 * s, mix(ol, (255, 255, 255), 0.12))
    cv.rect(ox + 2 * s, oy + 4 * s, ox + 7 * s, oy + 9 * s, orng)
    cv.rect(ox + 21 * s, oy + 0 * s, ox + 27 * s, oy + 5 * s, orng)
    for (x0, y0, x1, y1) in ((ox, oy + 10 * s, ox + 9 * s, oy + 22 * s), (ox + 19 * s, oy + 6 * s, ox + 28 * s, oy + 22 * s)):
        cv.line(x0, (y0 + y1) // 2, x1, (y0 + y1) // 2, olk)
        cv.put(x0 + 1, y0 + 1, (200, 210, 160)); cv.put(x1 - 1, y0 + 1, (200, 210, 160))
    cv.rect(ox + 11 * s, oy + 15 * s, ox + 17 * s, oy + 22 * s, (7, 9, 12))   # the loading gap
    for k in range(ox + 10 * s, ox + 19 * s):
        cv.put(k, oy + 14 * s, hz if (k // 2) % 2 else (38, 38, 42))


def bot_side(cv, cx, by, r):
    """the cleaning bot side on: a steel dome, a yellow stripe, a lens, a
    green light, the brush skirt"""
    steel, dk, lt = rgb(0xb9c4cd), rgb(0x5b6672), rgb(0xe7edf2)
    for x in range(int(cx - r), int(cx + r) + 1):
        cv.put(x, by, rgb(0x4a535d) if x % 2 else rgb(0x22282e))
        cv.put(x, by - 1, rgb(0x4a535d) if (x + 1) % 2 else rgb(0x22282e))
    cv.ellipse(cx, by - 2, r, r * 0.62, steel)
    cv.rect(cx - r - 1, by - 2, cx + r + 1, by - 1, (0, 0, 0), 0)
    cv.ellipse(cx - r * 0.3, by - 2 - r * 0.35, r * 0.45, r * 0.22, lt, 200)
    cv.line(cx - r + 1, by - 3, cx + r - 1, by - 3, rgb(0xffcf6a))
    cv.disc(cx + r * 0.6, by - 2 - r * 0.25, max(1, r * 0.14), (12, 16, 20))
    cv.line(cx, by - 2 - r * 0.62, cx, by - 4 - r * 0.62, dk)
    cv.disc(cx, by - 5 - r * 0.62, 1.2, rgb(0x6dffb0))


def bot_disc(cv, cx, cy, r):
    steel, dk = rgb(0xb9c4cd), rgb(0x5b6672)
    cv.disc(cx, cy, r, dk)
    cv.disc(cx - 0.4, cy - 0.4, r - 1, steel)
    for k in range(int(2 * math.pi * (r * 0.68))):
        a = k / (r * 0.68)
        cv.put(cx + math.cos(a) * r * 0.68, cy + math.sin(a) * r * 0.68, rgb(0xffcf6a))
    cv.disc(cx, cy, r * 0.42, rgb(0x22282e))
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        cv.line(cx, cy, cx + math.cos(a) * r * 0.4, cy + math.sin(a) * r * 0.4, rgb(0x6b7480))
    cv.disc(cx, cy + r * 0.82, max(1, r * 0.13), (12, 16, 20))
    cv.disc(cx, cy - r * 0.82, max(1, r * 0.12), rgb(0x6dffb0))


def mower(cv, cx, by, r):
    org, dk, lt = rgb(0xe5822a), rgb(0xb4561a), rgb(0xffb661)
    cv.ellipse(cx, by - r * 0.55, r, r * 0.55, org)
    cv.rect(cx - r, by - r * 0.5, cx + r, by, (0, 0, 0), 0)
    cv.rect(cx - r * 0.95, by - r * 0.45, cx + r * 0.95, by - 1, dk)
    cv.ellipse(cx - r * 0.3, by - r * 0.75, r * 0.4, r * 0.18, lt, 200)
    for x in range(int(cx - r * 0.55), int(cx + r * 0.55) + 1, 2):
        cv.put(x, by, rgb(0x8996a2))
    for s in (-1, 1):
        cv.disc(cx + s * r * 0.72, by - 1, max(1.6, r * 0.3), rgb(0x1b2026))
        cv.put(cx + s * r * 0.72, by - 1, rgb(0x8996a2))
    cv.line(cx, by - r * 1.1, cx, by - r * 1.25, rgb(0x8996a2))
    cv.disc(cx, by - r * 1.35, 1.1, rgb(0xfff0d3))


def mite(cv, x, y, c=0xc49260):
    c = rgb(c)
    for k in (-1, 0, 1):
        cv.put(x + k * 2 - 1, y + 2, rgb(0x8a6a48)); cv.put(x + k * 2, y + 2, rgb(0x8a6a48))
    cv.ellipse(x, y, 2.6, 1.8, c)
    cv.put(x - 1, y - 1, rgb(0xe6bd88))
    cv.put(x + 2, y - 1, (18, 10, 6))
    cv.put(x + 3, y - 2, rgb(0xd9b892))


def crystals(cv, ox, by, s, cols=(0xb07cff, 0x7c5cff, 0x5fd8e8)):
    rock, rk = rgb(0x464b58), rgb(0x2a2e38)
    cv.ellipse(ox + 14 * s, by - 2 * s, 13 * s, 3.5 * s, rock)
    for x0, w, h, c in ((ox + 4 * s, 4 * s, 12 * s, cols[1]), (ox + 9 * s, 5 * s, 18 * s, cols[0]),
                        (ox + 16 * s, 4 * s, 14 * s, cols[1]), (ox + 21 * s, 5 * s, 9 * s, cols[2])):
        c = rgb(c)
        cv.poly([(x0, by - 3 * s), (x0, by - h + 2 * s), (x0 + w / 2, by - h), (x0 + w, by - h + 2 * s), (x0 + w, by - 3 * s)], c)
        cv.line(x0 + 1, by - 4 * s, x0 + 1, by - h + 2 * s, mix(c, (255, 255, 255), 0.6))
        cv.line(x0 + w - 1, by - 4 * s, x0 + w - 1, by - h + 2 * s, mix(c, (0, 0, 0), 0.35))
        cv.put(x0 + w / 2, by - h + 1, (255, 255, 255))
    cv.put(ox + 6 * s, by - 2, rgb(0x9fb3c8)); cv.put(ox + 19 * s, by - 1, rgb(0x9fb3c8))


def fungus(cv, ox, by, s, c=0xff8a3a):
    c = rgb(c)
    glow, tip = mix(c, (255, 255, 255), 0.45), mix(c, (255, 255, 255), 0.8)
    branches = [((16, 30), (16, 18)), ((16, 22), (9, 13)), ((16, 20), (24, 11)), ((9, 13), (6, 6)),
                ((9, 13), (12, 6)), ((24, 11), (21, 4)), ((24, 11), (28, 6)), ((16, 18), (17, 8))]
    for (x0, y0), (x1, y1) in branches:
        for d in (-1, 0, 1):
            cv.line(ox + (x0 + d * 0.5) * s, by - 30 * s + y0 * s, ox + (x1 + d * 0.5) * s, by - 30 * s + y1 * s, c)
        cv.line(ox + x0 * s - 1, by - 30 * s + y0 * s, ox + x1 * s - 1, by - 30 * s + y1 * s, glow)
    for _, (x1, y1) in branches:
        if (x1, y1) not in [b[0] for b in branches]:
            cv.disc(ox + x1 * s, by - 30 * s + y1 * s, 1.6 * s, tip)
            for dx, dy in ((-2, 0), (2, 0), (0, -2)):
                cv.put(ox + x1 * s + dx, by - 30 * s + y1 * s + dy, tip, 90)


def fern(cv, ox, by, s):
    g1, g2 = rgb(0x4f9a52), rgb(0x3e8546)
    for k, (x, h, lean) in enumerate(((8, 22, -3), (14, 27, 0), (20, 24, 3), (11, 17, -5), (18, 18, 5))):
        c = g1 if k % 2 == 0 else g2
        x0, y0, x1, y1 = ox + x * s, by - 3 * s, ox + (x + lean) * s, by - h * s
        cv.line(x0, y0, x1, y1, c)
        n = int((y0 - y1) / 2)
        for i in range(1, n):
            t = i / n
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            L = (1 - t) * 3.2 * s + 0.6
            cv.line(px, py, px - L, py - L * 0.5, c)
            cv.line(px, py, px + L, py - L * 0.5, c)
    cv.ellipse(ox + 14 * s, by - 2 * s, 11 * s, 2.5 * s, rgb(0x6d7a86))


def draw_all():
    # ---- traits (16 px) ----
    cv = Canvas(16, 16)                                   # bold: dashing, speed lines
    for y in (6, 9, 12):
        cv.line(0, y, 3, y, rgb(0x6db9ff))
    trubble(cv, 10, 9, 4.5, PEACH, look=1)
    cv.outline(); cv.save("icon_bold.png")
    cv = Canvas(16, 16)                                   # shy: peeking from the moss
    trubble(cv, 7, 10, 4.5, LILAC, look=-0.6, feet=False)
    for x, h in ((9, 11), (11, 13), (13, 10)):
        moss(cv, x, 15, h)
    cv.outline(); cv.save("icon_shy.png")
    cv = Canvas(16, 16)                                   # solo: one
    trubble(cv, 8, 8.5, 5, SKY)
    cv.outline(); cv.save("icon_solo.png")
    cv = Canvas(16, 16)                                   # social (cuddly): two, snug
    trubble(cv, 5, 9.5, 3.8, PINK, look=1)
    trubble(cv, 11, 9.5, 3.8, TEAL, look=-1)
    cv.outline(); cv.save("icon_social.png")
    cv = Canvas(16, 16)                                   # cautious: a half-lidded eye (the curious eye's partner)
    cv.ellipse(8, 9, 6, 4, (255, 255, 255))
    cv.disc(8, 9.5, 2.6, rgb(0x3a66c8)); cv.disc(8, 9.5, 1.3, (10, 14, 30))
    cv.rect(1, 4, 15, 8, rgb(0x5a7fd0))
    cv.line(2, 8, 14, 8, rgb(0x2a3f80))
    cv.outline(); cv.save("icon_cautious.png")

    # ---- badges (32 px) ----
    cv = Canvas(32, 32)                                   # first song
    trubble(cv, 12, 19, 8, MINT, look=0)
    note(cv, 21, 13, 0xffe28a); note(cv, 27, 7, 0xbfe8ff)
    cv.outline(); cv.save("ms_first_bubbles.png")
    cv = Canvas(32, 32)                                   # first roll
    for k, a in enumerate((2.6, 3.0, 3.4)):
        for t in range(10):
            ang = a + t * 0.12
            cv.put(16 + math.cos(ang) * (13 - k), 17 + math.sin(ang) * (11 - k), rgb(0x6db9ff), 220 - t * 18)
    trubble(cv, 18, 17, 8, PEACH, look=1)
    for x in (5, 8, 26):
        cv.disc(x, 28, 1.3, rgb(0x8a95a0), 200)
    cv.outline(); cv.save("ms_first_dart.png")
    cv = Canvas(32, 32)                                   # first cuddle
    trubble(cv, 10, 20, 7, PINK, look=1)
    trubble(cv, 22, 20, 7, TEAL, look=-1)
    heart(cv, 16, 4, 3.2)
    cv.outline(); cv.save("ms_first_follow.png")
    cv = Canvas(32, 32)                                   # first glass cleaning: a grimy pane, a clean swipe
    cv.rect(3, 4, 28, 27, rgb(0x2d4a58))
    for (x, y) in ((6, 8), (10, 22), (22, 7), (25, 20), (8, 15), (19, 24), (24, 13), (14, 6)):
        cv.ellipse(x, y, 2.2, 1.5, rgb(0x6b6455))
    cv.poly([(4, 24), (9, 27), (27, 9), (22, 5)], rgb(0x5a8ea6))
    for (x, y) in ((12, 13), (17, 17), (21, 11)):
        cv.put(x, y, (255, 255, 255)); cv.put(x + 1, y, (200, 230, 255))
    cv.rect(3, 3, 28, 3, rgb(0x8996a2)); cv.rect(3, 28, 28, 28, rgb(0x5b6672))
    cv.outline(); cv.save("ms_first_glass_cleaning.png")
    cv = Canvas(32, 32)                                   # first hold-approach: a fingertip, a Trubble looking up
    skin, sk2 = rgb(0xf3c4a0), rgb(0xd99c78)
    cv.poly([(19, 0), (27, 0), (26, 11), (20, 11)], skin)
    cv.ellipse(23, 11, 3.6, 2.6, skin); cv.line(20, 1, 20, 10, sk2)
    cv.ellipse(23, 9, 2, 1.4, rgb(0xffe6d6))                    # the nail
    trubble(cv, 11, 22, 7, SUN, look=0.8)
    cv.outline(); cv.save("ms_first_hold_approach.png")
    cv = Canvas(32, 32)                                   # first meal from you
    trubble(cv, 13, 18, 8.5, PEACH, look=1)
    cv.disc(25, 21, 2.6, rgb(0xffbd59)); cv.put(24, 20, rgb(0xffe9bd))
    for (x, y) in ((28, 25), (23, 26), (29, 18)):
        cv.put(x, y, rgb(0xffbd59))
    cv.outline(); cv.save("ms_first_meal.png")
    cv = Canvas(32, 32)                                   # first play session: two bouncing
    trubble(cv, 9, 10, 6, LILAC, look=1)
    trubble(cv, 22, 22, 6, MINT, look=-1)
    for t in range(9):
        cv.put(4 + t, 24 - int(6 * math.sin(t / 8 * math.pi)), rgb(0x6db9ff), 200)
        cv.put(19 + t, 10 - int(5 * math.sin(t / 8 * math.pi)), rgb(0x6db9ff), 200)
    cv.outline(); cv.save("ms_first_play_session.png")
    cv = Canvas(32, 32)                                   # first full night's sleep: the nest, the moon
    cv.disc(25, 7, 4.5, rgb(0xfff2b0))                   # the moon: a disc, its inner part carved out
    for y in range(32):
        for x in range(32):
            if (x + 0.5 - 27.4) ** 2 + (y + 0.5 - 5.4) ** 2 <= 14 and cv.get(x, y) is not None:
                cv.px[y * 32 + x] = None
    cv.ellipse(15, 27, 12, 4, rgb(0x5a4330))
    cv.ellipse(15, 25.5, 10, 2.2, rgb(0x2e2219))
    trubble(cv, 15, 20, 7, SKY, asleep=True, feet=False)
    cv.ellipse(15, 27.5, 11, 2.2, rgb(0x8a6a48))
    for x, y in ((5, 4), (12, 9), (8, 13)):
        cv.put(x, y, (220, 230, 255))
    cv.outline(); cv.save("ms_first_quiet_night.png")
    cv = Canvas(32, 32)                                   # first visit to the crystals
    crystals(cv, 13, 30, 0.7)
    trubble(cv, 8, 22, 6.5, PEACH, look=1)
    cv.outline(); cv.save("ms_first_reef.png")
    cv = Canvas(32, 32)                                   # first nap in the moss
    for x, h in ((3, 22), (7, 26), (25, 24), (29, 20)):
        moss(cv, x, 31, h)
    trubble(cv, 16, 22, 7.5, PINK, asleep=True)
    for x, h in ((11, 13), (21, 14)):
        moss(cv, x, 31, h)
    cv.outline(); cv.save("ms_first_seagrass.png")
    cv = Canvas(32, 32)                                   # a colony of ten mites
    for (x, y) in ((5, 6), (14, 4), (24, 7), (9, 13), (19, 12), (28, 15), (4, 21), (14, 20), (23, 22), (11, 28)):
        mite(cv, x, y)
    cv.outline(); cv.save("ms_full_school.png")
    cv = Canvas(32, 32)                                   # credits
    chip(cv, 16, 16, 13)
    cv.outline(); cv.save("ms_sand_dollar.png")
    cv = Canvas(32, 32)                                   # the pod changed someone: a turn of arrows round a Trubble
    for t in range(40):
        a = t / 40 * 2 * math.pi
        if (t // 10) % 2 == 0:
            cv.put(16 + math.cos(a) * 13, 16 + math.sin(a) * 13, rgb(0xffd166))
    for a in (0.0, math.pi):
        x, y = 16 + math.cos(a + 0.9) * 13, 16 + math.sin(a + 0.9) * 13
        cv.disc(x, y, 1.6, rgb(0xffd166))
    trubble(cv, 16, 16, 7, MINT)
    cv.disc(13, 18, 1.6, rgb(0xff7aa8)); cv.disc(20, 13, 1.4, rgb(0xff7aa8))   # new markings
    cv.outline(); cv.save("ms_tank_changed_someone.png")

    # ---- the shop ----
    cv = Canvas(32, 32); crates(cv, 2, 6, 1); cv.outline(); cv.save("shop_castle.png")
    cv = Canvas(32, 32); crystals(cv, 2, 30, 1); cv.outline(); cv.save("shop_cluster.png")
    cv = Canvas(32, 32); fungus(cv, 0, 31, 1); cv.ellipse(16, 30, 8, 2, rgb(0x6d7a86)); cv.outline(); cv.save("shop_coral.png")
    cv = Canvas(32, 32); fern(cv, 2, 31, 1); cv.outline(); cv.save("shop_plant.png")
    cv = Canvas(32, 32)
    for (x, y) in ((8, 9), (22, 7), (12, 20), (25, 19), (17, 27)):
        mite(cv, x, y)
    cv.outline(); cv.save("shop_shrimp.png")
    cv = Canvas(32, 32); bot_side(cv, 16, 24, 11); cv.outline(); cv.save("shop_snail.png")
    cv = Canvas(32, 32); mower(cv, 16, 25, 12); cv.outline(); cv.save("shop_urchin.png")
    cv = Canvas(16, 16); chip(cv, 8, 8, 6.5); cv.outline(); cv.save("shop_sand_dollar_16.png")
    cv = Canvas(64, 64); chip(cv, 32, 32, 28); cv.outline(); cv.save("shop_sand_dollar_64.png")
    cv = Canvas(24, 24); bot_disc(cv, 12, 12, 10); cv.outline(); cv.save("snail_glass.png")
    cv = Canvas(32, 32); bot_side(cv, 16, 24, 11); cv.outline(); cv.save("snail_upright.png")


if __name__ == "__main__":
    draw_all()
    print("drew the Trubbles' icons into", OUT)
