"""
Canvas themes.

Four renders of one brief on one cream canvas produced four posts that looked
identical in a feed. Each variant now gets its own ground, palette and
decoration, so the day's options are a real choice rather than four takes on the
same card.

A theme supplies: the painted background, the ink colours for type, and whether
the canvas is dark (which flips the logo, footer and body text).
"""
from __future__ import annotations

import math
import random
from typing import Dict

from PIL import Image, ImageDraw, ImageFilter

import brandkit as bk

PX = 1080


# ── helpers ─────────────────────────────────────────────────────────────────
def _vgrad(top, bottom, size=(PX, PX)) -> Image.Image:
    """Vertical gradient."""
    w, h = size
    base = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        base.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return base.resize((w, h))


def _radial_glow(im: Image.Image, cx: float, cy: float, radius: float, color, strength: int):
    """Soft light bloom, drawn as a blurred disc."""
    glow = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(glow)
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=strength)
    glow = glow.filter(ImageFilter.GaussianBlur(radius * 0.55))
    layer = Image.new("RGB", im.size, color)
    return Image.composite(layer, im, glow)


def _mandala(d: ImageDraw.ImageDraw, cx: int, cy: int, r0: int, rings: int, color, alpha: int,
             petals: int = 16):
    for k in range(rings):
        r = r0 + k * 26
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*color, alpha), width=2)
    for i in range(petals):
        a = 2 * math.pi * i / petals
        r = r0 + rings * 26
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=(*color, alpha), width=2)


def _leaf(d: ImageDraw.ImageDraw, x, y, w, h, ang, color, alpha):
    """A simple pointed leaf, drawn as a rotated lens shape."""
    pts = []
    for t in range(0, 21):
        u = t / 20
        dx = (u - 0.5) * w
        dy = math.sin(math.pi * u) * h / 2
        pts.append((dx, dy))
    for t in range(20, -1, -1):
        u = t / 20
        dx = (u - 0.5) * w
        dy = -math.sin(math.pi * u) * h / 2
        pts.append((dx, dy))
    ca, sa = math.cos(ang), math.sin(ang)
    d.polygon([(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in pts],
              fill=(*color, alpha))


def _foliage(im: Image.Image, corner: str, color, alpha: int, n: int = 22, seed: int = 0):
    """A botanical cluster in one corner — the greenery of the reference creatives."""
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    rnd = random.Random(seed)
    ox, oy = {"tl": (0, 0), "tr": (PX, 0), "bl": (0, PX), "br": (PX, PX)}[corner]
    for _ in range(n):
        r = rnd.uniform(40, 330)
        a = rnd.uniform(0, math.pi / 2)
        sx = -1 if ox else 1
        sy = -1 if oy else 1
        x = ox + sx * math.cos(a) * r
        y = oy + sy * math.sin(a) * r
        _leaf(d, x, y, rnd.uniform(48, 120), rnd.uniform(20, 46),
              rnd.uniform(0, math.pi), color, int(alpha * rnd.uniform(0.5, 1.0)))
    layer = layer.filter(ImageFilter.GaussianBlur(0.6))
    out = im.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def _bokeh(im: Image.Image, color, n: int = 34, seed: int = 3):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = rnd.uniform(0, PX), rnd.uniform(0, PX)
        r = rnd.uniform(8, 46)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*color, rnd.randint(18, 60)))
    layer = layer.filter(ImageFilter.GaussianBlur(7))
    out = im.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


# ── the themes ──────────────────────────────────────────────────────────────
def _floral_cream(tribute: bool) -> Image.Image:
    if tribute:
        im = _vgrad((252, 252, 253), (238, 239, 243))
        im = _foliage(im, "tr", (150, 158, 175), 40, 18, seed=11)
        im = _foliage(im, "bl", (150, 158, 175), 28, 12, seed=12)
    else:
        im = _vgrad((255, 253, 244), (250, 244, 228))
        im = _radial_glow(im, PX * 0.78, PX * 0.16, PX * 0.5, (255, 246, 214), 90)
        im = _foliage(im, "tr", (74, 148, 86), 62, 26, seed=5)
        im = _foliage(im, "bl", (96, 162, 104), 40, 16, seed=6)
        d = ImageDraw.Draw(im, "RGBA")
        _mandala(d, 90, PX - 90, 120, 5, bk.GOLD, 26)
    return im


def _deep_festive(tribute: bool) -> Image.Image:
    if tribute:
        im = _vgrad((38, 40, 52), (22, 23, 32))
        im = _bokeh(im, (190, 196, 214), 22, seed=9)
    else:
        im = _vgrad((86, 22, 40), (28, 14, 34))
        im = _radial_glow(im, PX * 0.5, PX * 0.30, PX * 0.62, (196, 96, 60), 120)
        im = _bokeh(im, (255, 206, 120), 40, seed=2)
        d = ImageDraw.Draw(im, "RGBA")
        _mandala(d, PX // 2, PX // 2, 300, 4, bk.GOLD, 22, petals=24)
    return im


THEMES: Dict[str, Dict] = {
    "floral-cream": {
        "paint": _floral_cream, "dark": False, "kind": "subject",
        "acc1": bk.GREEN, "acc2": bk.GOLD, "ink": bk.NAVY, "body": bk.INK,
        "orn": bk.GOLD, "bar": bk.GREEN,
    },
    "deep-festive": {
        "paint": _deep_festive, "dark": True, "kind": "subject",
        "acc1": (255, 205, 108), "acc2": (255, 255, 255), "ink": (255, 250, 238),
        "body": (238, 228, 210), "orn": (255, 205, 108), "bar": bk.GOLD,
    },
    # scene themes paint nothing — the model's backdrop is the background
    "scene-card": {
        "paint": None, "dark": False, "kind": "scene", "panel": "left",
        "acc1": bk.GREEN, "acc2": bk.GOLD, "ink": bk.NAVY, "body": bk.INK,
        "orn": bk.GOLD, "bar": bk.GREEN,
    },
    "scene-wash": {
        "paint": None, "dark": True, "kind": "scene", "panel": "full",
        "acc1": (255, 208, 112), "acc2": (255, 255, 255), "ink": (255, 252, 245),
        "body": (240, 234, 222), "orn": (255, 208, 112), "bar": bk.GOLD,
    },
}


def theme(name: str) -> Dict:
    return THEMES.get(name, THEMES["floral-cream"])


def for_tribute(th: Dict) -> Dict:
    """Mute a theme's type colours for a remembrance post.

    The background painters already switch to a restrained ground, but the ink
    colours are per-theme constants — without this a punyatithi could go out set
    in festive green and gold.
    """
    t = dict(th)
    if th["dark"]:
        t.update({"acc1": (226, 230, 240), "acc2": (176, 184, 202),
                  "ink": (238, 240, 246), "body": (206, 212, 226),
                  "orn": (150, 158, 178), "bar": (74, 80, 98)})
    else:
        t.update({"acc1": bk.T_DARK, "acc2": bk.T_ACC, "ink": bk.NAVY,
                  "body": bk.INK, "orn": bk.T_ACC, "bar": bk.T_DARK})
    return t


def background(name: str, tribute: bool) -> Image.Image:
    t = theme(name)
    if t["paint"] is None:
        return Image.new("RGB", (PX, PX), bk.CREAM)
    return t["paint"](tribute)
