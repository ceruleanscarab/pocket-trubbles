#!/usr/bin/env python3
"""draw_cthulhu_icons.py - the Cthulhu theme's icons (THEME_CTHULHU, the Android
app), into assets/icons_cthulhu/.

The Trubbles' script (draw_trubble_icons.py) draws every icon from a handful of
helpers - the Trubble, the moss, the crates, the bots, the mites, the crystals,
the fungus, the fern, the credit chip. This swaps those helpers for the theme's
(a little Cthulhu, kelp, sunken ruins, a glass slug, a kelp crab, pale
isopods, glyph stones, elder coral, a tentacled coin) and runs the same
draw_all(), so every icon keeps its name, size and composition. The icons
draw_all() does not make (the hand-drawn stat icons) are copied over first,
unchanged.

    python3 tools/draw_cthulhu_icons.py && python3 tools/gen_icons.py --theme cthulhu

Only the standard library.
"""
import math, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import draw_trubble_icons as T  # noqa: E402
from draw_trubble_icons import rgb, mix  # noqa: E402

SRC = os.path.join(T.ROOT, "assets", "icons")
OUT = os.path.join(T.ROOT, "assets", "icons_cthulhu")
GREEN = 0x5e9e6e


def cthulhu(cv, cx, cy, r, fur, look=0.0, asleep=False, feet=True):
    """the Trubble's slot: a round head leaning green, bat wings behind it,
    face tentacles below the eyes, slit pupils looking `look`"""
    skin = mix(rgb(fur) if isinstance(fur, int) else fur, rgb(GREEN), 0.6)
    dark, lite = mix(skin, (0, 0, 0), 0.4), mix(skin, (255, 255, 255), 0.35)
    wing = mix(dark, (0, 0, 0), 0.25)
    for s in (-1, 1):                                    # wings
        bx, by = cx + s * r * 0.65, cy - r * 0.05
        cv.poly([(bx, by), (bx + s * r * 0.95, by - r * 0.95), (bx + s * r * 0.85, by - r * 0.1), (bx + s * r * 0.45, by + r * 0.15)], wing)
    if feet:
        for s in (-1, 1):
            cv.ellipse(cx + s * r * 0.42, cy + r * 1.05, max(1.2, r * 0.28), max(0.8, r * 0.16), mix(skin, (26, 36, 24), 0.65))
    cv.disc(cx, cy, r, skin)
    cv.ellipse(cx - r * 0.3, cy - r * 0.4, r * 0.45, r * 0.32, lite, 150)
    n = 3 if r < 5 else 5                                # face tentacles
    for k in range(n):
        u = (k - (n - 1) / 2) / ((n - 1) / 2)
        x0, y0 = cx + look * r * 0.15 + u * r * 0.45, cy + r * 0.35
        for i in range(1, 4):
            t = i / 3
            cv.disc(x0 + u * t * r * 0.15 + math.sin(k * 1.7 + t * 3) * r * 0.08, y0 + t * r * 0.75,
                    max(0.6, r * 0.14 * (1 - 0.5 * t)), mix(skin, dark, 0.55))
    ex, gap, ey = look * r * 0.2, max(1.5, r * 0.34), cy - r * 0.1
    er = max(1.0, r * 0.25)
    for s in (-1, 1):
        x = cx + ex + s * gap
        if asleep:
            cv.line(x - er, ey + 0.5, x + er, ey + 0.5, (16, 24, 15))
            continue
        cv.ellipse(x, ey, er, er * 1.1, rgb(0xe8f2a8))
        cv.ellipse(x + look * er * 0.3, ey, max(0.5, er * 0.3), max(0.8, er * 0.85), (12, 16, 10))


def kelp(cv, x, y_bot, h, c=0x6f7a36, puff=0xc0a54c):
    """the moss's slot: a kelp stalk with a golden float bladder"""
    cv.line(x, y_bot, x, y_bot - h, rgb(c))
    cv.line(x + 1, y_bot, x + 1, y_bot - h + 1, mix(rgb(c), (0, 0, 0), 0.25))
    cv.ellipse(x + 0.5, y_bot - h, 1.4, 2.0, rgb(puff))


def ruins(cv, ox, oy, s):
    """the crates' slot: tumbled blocks, an arch of alternating voussoirs, moss"""
    st, dk, lt, moss_ = rgb(0x6e7b69), rgb(0x384236), rgb(0x93a08d), rgb(0x3e6b3a)
    cv.rect(ox, oy + 9 * s, ox + 9 * s, oy + 22 * s, st)
    cv.rect(ox + 19 * s, oy + 4 * s, ox + 28 * s, oy + 22 * s, st)
    cv.rect(ox + 8 * s, oy + 12 * s, ox + 20 * s, oy + 22 * s, mix(st, (255, 255, 255), 0.08))
    cv.poly([(ox + 1 * s, oy + 9 * s), (ox + 8 * s, oy + 6 * s), (ox + 8 * s, oy + 9 * s)], dk)   # a capstone, askew
    cv.rect(ox + 20 * s, oy + 1 * s, ox + 26 * s, oy + 4 * s, rgb(0x56624f))
    for y in (oy + 14 * s, oy + 18 * s):                 # the courses
        cv.line(ox, y, ox + 9 * s, y, dk); cv.line(ox + 19 * s, y - 3, ox + 28 * s, y - 3, dk)
    cv.rect(ox + 11 * s, oy + 16 * s, ox + 17 * s, oy + 22 * s, (4, 8, 7))   # the dark under the arch
    for k in range(9):                                   # the voussoirs
        a = math.pi * (k + 0.5) / 9
        cv.disc(ox + 14 * s - math.cos(a) * 4 * s, oy + 16 * s - math.sin(a) * 3.5 * s, 1.2 * s, lt if k % 2 else dk)
    for x in range(int(ox), int(ox + 28 * s), 3):        # moss along the foot
        cv.put(x, oy + 21 * s, moss_); cv.put(x + 1, oy + 20 * s, moss_)


def slug_side(cv, cx, by, r):
    """the cleaning bot's slot side on: a lilac glass slug, its eye-stalks up"""
    body, dk, lt, band = rgb(0xae9fbb), rgb(0x5a4b69), rgb(0xd9cde3), rgb(0xf0e6c8)
    cv.ellipse(cx, by - r * 0.35, r, r * 0.42, body)
    cv.rect(cx - r - 1, by, cx + r + 1, by + 2, (0, 0, 0), 0)
    cv.ellipse(cx - r * 0.25, by - r * 0.55, r * 0.5, r * 0.18, lt, 200)
    cv.line(cx - r + 2, by - r * 0.2, cx + r - 2, by - r * 0.2, band)
    cv.line(cx - r + 1, by, cx + r - 1, by, dk)
    for s in (0.45, 0.75):                               # eye-stalks
        x = cx + r * s
        cv.line(x, by - r * 0.6, x + 1, by - r * 1.2, body)
        cv.disc(x + 1, by - r * 1.25, 1.1, rgb(0x9dff7a))


def slug_disc(cv, cx, cy, r):
    """the cleaning bot on the glass: the slug's sole, seen through it"""
    body, dk = rgb(0xae9fbb), rgb(0x5a4b69)
    cv.ellipse(cx, cy, r * 0.75, r, dk)
    cv.ellipse(cx - 0.4, cy - 0.4, r * 0.75 - 1, r - 1, body)
    for k in range(5):                                   # the ripples of its foot
        y = cy - r * 0.6 + k * r * 0.3
        cv.line(cx - r * 0.45, y, cx + r * 0.45, y, mix(body, dk, 0.5))
    cv.disc(cx, cy - r * 0.8, max(1, r * 0.13), rgb(0x9dff7a))


def crab(cv, cx, by, r):
    """the mowing bot's slot: a red kelp crab, claws up"""
    shell, dk, lt, claw = rgb(0xb8432c), rgb(0x8a2a1e), rgb(0xe0735a), rgb(0xd8c7a8)
    for s in (-1, 1):                                    # legs
        for k in range(3):
            x = cx + s * r * (0.35 + k * 0.22)
            cv.line(x, by - r * 0.25, x + s * r * 0.25, by, dk)
    cv.ellipse(cx, by - r * 0.4, r * 0.85, r * 0.45, shell)
    cv.ellipse(cx - r * 0.25, by - r * 0.6, r * 0.35, r * 0.15, lt, 200)
    for s in (-1, 1):                                    # claws
        cx2, cy2 = cx + s * r * 0.95, by - r * 0.95
        cv.line(cx + s * r * 0.6, by - r * 0.55, cx2, cy2, dk)
        cv.disc(cx2, cy2, max(1.5, r * 0.25), claw)
        cv.put(cx2 + s * 1, cy2 - 2, (0, 0, 0), 0)
    for s in (-1, 1):                                    # eyes on stalks
        cv.put(cx + s * 2, by - r * 0.95, (20, 10, 8))


def isopod(cv, x, y, c=0xa9a2b4):
    """the mite's slot: a pale isopod, its plates banded"""
    c = rgb(c)
    for k in (-1, 0, 1):
        cv.put(x + k * 2 - 1, y + 2, rgb(0x6e6878)); cv.put(x + k * 2, y + 2, rgb(0x6e6878))
    cv.ellipse(x, y, 2.8, 1.7, c)
    for k in (-1, 1):
        cv.put(x + k, y - 1, rgb(0xcfc9d8)); cv.put(x + k, y, mix(c, (0, 0, 0), 0.3))
    cv.put(x + 3, y - 1, (10, 8, 14))
    cv.put(x + 4, y - 2, rgb(0xbdb6c8))


def glyph_stones(cv, ox, by, s, cols=(0x9fe07a, 0x5f8f6a, 0xc9f58a)):
    """the crystals' slot: standing stones, glyphs glowing in them"""
    rock, rk = rgb(0x464b48), rgb(0x2a2e2c)
    cv.ellipse(ox + 14 * s, by - 2 * s, 13 * s, 3.5 * s, rock)
    glow = rgb(cols[0])
    for x0, w, h, c in ((ox + 4 * s, 5 * s, 13 * s, cols[1]), (ox + 10 * s, 6 * s, 19 * s, cols[1]),
                        (ox + 18 * s, 5 * s, 15 * s, cols[1]), (ox + 23 * s, 4 * s, 9 * s, cols[1])):
        c = rgb(c)
        cv.poly([(x0, by - 3 * s), (x0 + 0.5, by - h + 1 * s), (x0 + w / 2, by - h), (x0 + w - 0.5, by - h + 1.5 * s), (x0 + w, by - 3 * s)], mix(c, rk, 0.35))
        cv.line(x0 + 1, by - 4 * s, x0 + 1, by - h + 2 * s, mix(c, (255, 255, 255), 0.25))
        gx, gy = x0 + w / 2, by - h * 0.6                # a glyph: a stroke and two twigs
        cv.line(gx, gy - 2 * s, gx, gy + 2 * s, glow)
        cv.put(gx - 1, gy - 1 * s, glow); cv.put(gx + 1, gy - 1 * s, glow)
    cv.put(ox + 6 * s, by - 2, rgb(0xc9f58a)); cv.put(ox + 21 * s, by - 1, rgb(0xc9f58a))


def elder_coral(cv, ox, by, s, c=0x4fb8a8):
    """the fungus's slot: the same branching growth, a sea-teal by default"""
    T_fungus(cv, ox, by, s, c)


def tall_kelp(cv, ox, by, s):
    """the fern's slot: tall wavy kelp blades with bladders"""
    g1, g2, bl = rgb(0x55743a), rgb(0x44602f), rgb(0xc0a54c)
    for k, (x, h) in enumerate(((7, 22), (12, 27), (17, 24), (22, 19))):
        c = g1 if k % 2 == 0 else g2
        prev = None
        for i in range(0, h * s, 1):
            px, py = ox + x * s + math.sin(i * 0.35 + k) * 1.5, by - 3 * s - i
            cv.put(px, py, c); cv.put(px + 1, py, c)
            if i % 7 == 6:
                cv.ellipse(px + 1.5, py, 1.2, 1.6, bl)
    cv.ellipse(ox + 14 * s, by - 2 * s, 11 * s, 2.5 * s, rgb(0x4f5c48))


def coin(cv, cx, cy, r):
    """the credit chip's slot: a gold coin with a tentacled face struck on it"""
    gold, dk, lt = rgb(0xf2c33a), rgb(0xa8741a), rgb(0xffe9a0)
    cv.disc(cx, cy, r, dk)
    cv.disc(cx - r * 0.06, cy - r * 0.06, r * 0.9, gold)
    cv.ellipse(cx - r * 0.3, cy - r * 0.35, r * 0.4, r * 0.25, lt, 170)
    cv.disc(cx, cy - r * 0.08, r * 0.42, dk)             # the struck head
    cv.disc(cx - r * 0.04, cy - r * 0.12, r * 0.38, mix(gold, lt, 0.3))
    for s in (-1, 1):
        cv.disc(cx + s * r * 0.15, cy - r * 0.15, max(0.6, r * 0.08), dk)
    for k in (-1, 0, 1):                                 # its tentacles
        cv.line(cx + k * r * 0.18, cy + r * 0.12, cx + k * r * 0.22, cy + r * 0.5, dk)
    n = max(10, int(r * 2.4))
    for k in range(n):                                   # the milled rim
        a = k * 2 * math.pi / n
        cv.put(cx + math.cos(a) * (r - 0.7), cy + math.sin(a) * (r - 0.7), lt if k % 2 else dk)


T_fungus = T.fungus


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(SRC):                            # the icons draw_all() does not draw, unchanged
        if f.endswith(".png"):
            shutil.copyfile(os.path.join(SRC, f), os.path.join(OUT, f))
    T.OUT = OUT
    T.trubble, T.moss, T.crates, T.bot_side, T.bot_disc = cthulhu, kelp, ruins, slug_side, slug_disc
    T.mower, T.mite, T.crystals, T.fungus, T.fern, T.chip = crab, isopod, glyph_stones, elder_coral, tall_kelp, coin
    T.draw_all()
    print("drew the Cthulhu theme's icons into", OUT)


if __name__ == "__main__":
    main()
