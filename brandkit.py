"""
Postly brand kit: palette, fonts, logo, and the repeated pieces of the post
template (header lockup, ornament dividers, app-promo footer, artwork cutout).

Colours and layout are taken from the reference creatives: white/cream ground,
vivid green + gold two-tone Devanagari headline, navy body text, and the
"Download Now / Postly App" footer bar.
"""
from __future__ import annotations

import functools
import io
import os
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import hinditext

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

# ── palette ─────────────────────────────────────────────────────────────────
GREEN = (32, 167, 93)
GREEN_DK = (18, 122, 66)
GOLD = (232, 160, 23)
GOLD_DK = (196, 126, 10)
NAVY = (26, 28, 46)
INK = (58, 62, 82)
MUTED = (120, 126, 145)
CREAM = (253, 252, 247)
WHITE = (255, 255, 255)

# tribute palette — no festive green/gold on a remembrance post
T_DARK = (52, 56, 72)
T_ACC = (122, 130, 152)

FEATURES = ["1000+ Templates", "Easy to Use", "HD Quality", "1 Click Share"]
PROMO_LINE1 = "Apne Status ko"
PROMO_LINE2 = "Aur Bhi Khaas Banaye"
PROMO_LINE3 = "Postly App Ke Saath!"
TAGLINE = "Apna Status, Apni Pehchaan"

_LATIN_BOLD = [
    os.environ.get("LATIN_FONT_BOLD", ""),
    "/System/Library/Fonts/Supplemental/Futura.ttc",
    "/System/Library/Fonts/Avenir Next.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]
_LATIN_REG = [
    os.environ.get("LATIN_FONT", ""),
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]


def latin(size: int, bold: bool = True):
    for p in (_LATIN_BOLD if bold else _LATIN_REG):
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


# ── Devanagari ──────────────────────────────────────────────────────────────
@functools.lru_cache(maxsize=2048)
def _hindi_png(text: str, size: int, color, bold: bool):
    return hinditext.render_hindi(text, font_size=size, color=color, bold=bold)


def hindi(text: str, size: int, color=NAVY, bold: bool = True) -> Optional[Image.Image]:
    """Shaped Devanagari as an RGBA image.

    Cached: fitting type to a box re-renders the same words at several sizes, and
    word-wrap measures each candidate line repeatedly, so one post asked for the
    same render dozens of times. Shaping is the slowest step in compositing.
    """
    png = _hindi_png(text, int(size), tuple(color), bool(bold))
    if not png:
        return None
    return Image.open(io.BytesIO(png)).convert("RGBA")


def shaping_available() -> bool:
    """Can this host actually draw Devanagari, or only .notdef boxes?

    Compares the SHAPE of real Devanagari against a private-use control string
    that no font defines. If both come out as the same boxes, the font has no
    Devanagari and every post would ship unreadable.

    Width alone is not enough — the first version of this compared widths and a
    four-glyph tofu run happens to measure about the same as a shaped conjunct,
    so it failed a healthy Linux build. Shape comparison is unambiguous.
    """
    real = hindi("क्षत्रिय", 48)
    if real is None or real.width < 6 or real.height < 6:
        return False
    control = hindi("\ue000\ue001\ue002\ue003", 48)
    if control is None or control.width < 6 or control.height < 6:
        return True                    # undefined glyphs draw nothing: font is fine
    a = real.split()[3].resize((64, 32))
    b = control.split()[3].resize((64, 32))
    pa, pb = list(a.getdata()), list(b.getdata())
    diff = sum(abs(x - y) for x, y in zip(pa, pb)) / (len(pa) * 255.0)
    return diff > 0.06                 # identical shapes => tofu


def _shade(c, f: float):
    """Lighten (f>1) or darken (f<1) a colour, clamped."""
    return tuple(max(0, min(255, int(v * f))) for v in c)


def styled_hindi(text: str, size: int, color, bold: bool = True,
                 gradient: bool = True, outline: bool = True,
                 shadow_alpha: int = 58) -> Optional[Image.Image]:
    """Display-weight Devanagari: gradient fill, outline and a soft drop shadow.

    Flat single-colour type is what made the headline read as a caption rather
    than as designed lettering. The reference creatives set the occasion name in
    graduated colour with depth behind it; this is that treatment, applied to
    correctly shaped Devanagari.
    """
    base = hindi(text, size, (255, 255, 255), bold)
    if base is None:
        return None
    a = base.split()[3]
    w, h = base.size
    pad = max(6, size // 10)
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))

    if shadow_alpha:
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", base.size, (0, 0, 0, shadow_alpha)),
                 (pad, pad + max(2, size // 22)), a)
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(max(2, size / 34))))

    if outline:
        ow = max(1, size // 52)
        grown = a
        for _ in range(ow):
            grown = grown.filter(ImageFilter.MaxFilter(3))
        ol = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ol.paste(Image.new("RGBA", base.size, (*_shade(color, 0.62), 255)), (pad, pad), grown)
        canvas.alpha_composite(ol)

    if gradient:
        g = Image.new("RGB", (1, h))
        top, bot = _shade(color, 1.32), _shade(color, 0.68)
        for y in range(h):
            t = y / max(1, h - 1)
            g.putpixel((0, y), tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
        fill = g.resize((w, h)).convert("RGBA")
    else:
        fill = Image.new("RGBA", base.size, (*color, 255))
    face = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    face.paste(fill, (pad, pad), a)
    canvas.alpha_composite(face)

    bbox = canvas.split()[3].getbbox()
    return canvas.crop(bbox) if bbox else canvas


def fit(text: str, size: int, max_w: int, color=NAVY, bold: bool = True,
        styled: bool = False) -> Optional[Image.Image]:
    """Render Devanagari at `size`, scaled down if it would exceed max_w."""
    im = styled_hindi(text, size, color, bold) if styled else hindi(text, size, color, bold)
    if im is None:
        return None
    if im.width > max_w:
        r = max_w / im.width
        im = im.resize((max_w, max(1, int(im.height * r))), Image.LANCZOS)
    return im


def wrap(text: str, size: int, max_w: int, color=NAVY, bold: bool = True,
         max_lines: int = 2) -> List[Image.Image]:
    """Word-wrap Devanagari by measuring real shaped renders."""
    words = text.split()
    if not words:
        return []
    lines, cur = [], []
    for w in words:
        im = hindi(" ".join(cur + [w]), size, color, bold)
        if im is None:
            return []
        if im.width <= max_w or not cur:
            cur.append(w)
        else:
            done = hindi(" ".join(cur), size, color, bold)
            if done:
                lines.append(done)
            cur = [w]
            if len(lines) >= max_lines:
                cur = []
                break
    if cur and len(lines) < max_lines:
        im = hindi(" ".join(cur), size, color, bold)
        if im:
            lines.append(im)
    out = []
    for im in lines[:max_lines]:
        if im.width > max_w:
            r = max_w / im.width
            im = im.resize((max_w, max(1, int(im.height * r))), Image.LANCZOS)
        out.append(im)
    return out


def split_headline(occasion_hi: str) -> Tuple[str, str]:
    """Split the occasion name into the green part and the gold part.

    The references set the first word large in green and the rest in gold
    ("नाग" / "पंचमी"). One-word names stay entirely green.
    """
    parts = occasion_hi.split()
    if len(parts) <= 1:
        return occasion_hi.strip(), ""
    if len(parts) == 2:
        return parts[0], parts[1]
    return " ".join(parts[:-1]), parts[-1]


# ── logo ────────────────────────────────────────────────────────────────────
def logo(height: int, color=NAVY) -> Optional[Image.Image]:
    """The Postly wordmark recoloured. The shipped asset is a white-on-transparent
    mask, so it is repainted rather than used as-is."""
    p = ASSETS / "postly_logo.png"
    if not p.exists():
        return None
    im = Image.open(p).convert("RGBA")
    r = height / im.height
    im = im.resize((max(1, int(im.width * r)), height), Image.LANCZOS)
    solid = Image.new("RGBA", im.size, (*color, 255))
    solid.putalpha(im.split()[3])
    return solid


def app_icon(size: int) -> Optional[Image.Image]:
    p = ASSETS / "postly_app_icon.png"
    if not p.exists():
        return None
    im = Image.open(p).convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1],
                                           radius=int(size * 0.24), fill=255)
    im.putalpha(mask)
    return im


# ── shapes ──────────────────────────────────────────────────────────────────
def pill(size: Tuple[int, int], color, radius: Optional[int] = None,
         outline=None, width: int = 2) -> Image.Image:
    w, h = size
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    r = radius if radius is not None else h // 2
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], radius=r,
                                         fill=(*color, 255),
                                         outline=(*outline, 255) if outline else None,
                                         width=width)
    return im


def shadow(im: Image.Image, blur: int = 12, alpha: int = 46,
           offset: Tuple[int, int] = (0, 4)) -> Image.Image:
    """Soft drop shadow behind an RGBA element; returns a larger canvas."""
    pad = blur * 3
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.split()[3].point(lambda a: int(a * alpha / 255)))
    sh = Image.new("RGBA", im.size, (0, 0, 0, alpha)) if False else sh
    out.alpha_composite(sh, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out


def crest(draw: ImageDraw.ImageDraw, cx: int, y: int, size: int, color=GOLD) -> None:
    """A small decorative crest sitting above the greeting line.

    The reference creatives open with a motif before the type starts; without it
    the text block begins abruptly and the layout reads unfinished.
    """
    s2 = size
    draw.polygon([(cx, y - s2), (cx + s2 * 0.34, y), (cx, y + s2), (cx - s2 * 0.34, y)],
                 fill=(*color, 230))
    for dx in (-1, 1):
        draw.arc([cx + dx * s2 * 0.30 - s2 * 0.95, y - s2 * 0.62,
                  cx + dx * s2 * 0.30 + s2 * 0.95, y + s2 * 0.62],
                 start=200 if dx > 0 else 340, end=340 if dx > 0 else 200,
                 fill=(*color, 190), width=3)
    for dx in (-1, 1):
        draw.ellipse([cx + dx * s2 * 1.25 - 4, y - 4, cx + dx * s2 * 1.25 + 4, y + 4],
                     fill=(*color, 200))


def sprig(size: int, leaf=(74, 148, 86), berry=GOLD, seed: int = 0) -> Image.Image:
    """A small leaf-and-berry cluster, drawn to sit ON the lettering.

    The reference creatives tuck a leaf into the occasion name so the type and
    the artwork read as one drawing rather than two stacked layers. This is that
    ornament, procedural so it can be tinted per theme.
    """
    import math
    import random
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    rnd = random.Random(seed)
    cx, cy = size * 0.5, size * 0.55
    # a curving stem
    pts = [(cx - size * 0.34 + i * size * 0.09,
            cy + math.sin(i * 0.8) * size * 0.10) for i in range(8)]
    d.line(pts, fill=(*_shade(leaf, 0.75), 235), width=max(2, size // 26), joint="curve")
    for i, (x, y) in enumerate(pts[1:7]):
        ang = -0.9 if i % 2 == 0 else 0.9
        L, W = size * rnd.uniform(0.26, 0.36), size * rnd.uniform(0.11, 0.15)
        poly = []
        for t in range(13):
            u = t / 12
            poly.append(((u - 0.5) * L, math.sin(math.pi * u) * W / 2))
        for t in range(12, -1, -1):
            u = t / 12
            poly.append(((u - 0.5) * L, -math.sin(math.pi * u) * W / 2))
        ca, sa = math.cos(ang), math.sin(ang)
        d.polygon([(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in poly],
                  fill=(*leaf, 240))
    for x, y in (pts[2], pts[5]):
        r = size * 0.055
        d.ellipse([x - r, y - r * 1.6, x + r, y + r * 0.4], fill=(*berry, 245))
    return im


def ornament(draw: ImageDraw.ImageDraw, cx: int, y: int, w: int, color=GOLD) -> None:
    """The small diamond-and-rule divider used between text blocks."""
    half = w // 2
    draw.line([(cx - half, y), (cx - 14, y)], fill=(*color, 150), width=2)
    draw.line([(cx + 14, y), (cx + half, y)], fill=(*color, 150), width=2)
    for dx, s in ((0, 7), (-11, 4), (11, 4)):
        draw.polygon([(cx + dx, y - s), (cx + dx + s, y), (cx + dx, y + s), (cx + dx - s, y)],
                     fill=(*color, 210))


# ── artwork cutout ──────────────────────────────────────────────────────────
def _flat_white(art: Image.Image, lum_min: int, chroma_max: int, clean: int = 5) -> Image.Image:
    """Mask of flat near-white pixels — the render background, not white subject parts.

    A white kurta or a pearl is white but SHADED: within one region its
    luminance varies and its darker pixels break the mask up. The rendered
    background is flat. Eroding then dilating keeps large flat fields and
    deletes the speckle that shading produces, so the subject survives.
    """
    r, g, b = art.convert("RGB").split()
    lum = art.convert("L")
    mx = ImageChops.lighter(ImageChops.lighter(r, g), b)
    mn = ImageChops.darker(ImageChops.darker(r, g), b)
    chroma = ImageChops.subtract(mx, mn)
    bright = lum.point(lambda v: 255 if v >= lum_min else 0)
    neutral = chroma.point(lambda v: 255 if v <= chroma_max else 0)
    mask = ImageChops.multiply(bright, neutral)
    if clean:
        mask = mask.filter(ImageFilter.MinFilter(clean))   # erode: kill speckle
        mask = mask.filter(ImageFilter.MaxFilter(clean))   # dilate: restore area
    return mask


def _drop_shadow_islands(art: Image.Image, alpha: Image.Image,
                         max_frac: float = 0.06) -> Image.Image:
    """Delete small detached pale islands — the contact shadow the model drew.

    The model is told not to cast a shadow onto the background and mostly obeys,
    but when it does the blob averages ~228 luminance: too dark for a whiteness
    threshold to catch without also eating the shaded folds of a white kurta.

    Structure separates them instead. The shadow is a SEPARATE island from the
    subject, small, pale and colourless; the subject is one big coloured mass.
    Islands are labelled at quarter resolution (fast, and the decision is about
    whole blobs, not edges), and only small pale neutral ones are dropped.
    """
    import numpy as np

    w, h = alpha.size
    sw, sh = max(64, w // 4), max(64, h // 4)
    small = alpha.resize((sw, sh), Image.NEAREST).point(lambda v: 255 if v > 128 else 0)
    rgb = np.asarray(art.convert("RGB").resize((sw, sh), Image.BILINEAR)).astype(np.int16)

    work = small.copy()
    labels = {}
    label = 2
    for y in range(0, sh, 2):
        for x in range(0, sw, 2):
            if work.getpixel((x, y)) == 255 and label < 250:
                ImageDraw.floodfill(work, (x, y), label, thresh=0)
                labels[label] = True
                label += 1
    if len(labels) < 2:
        return alpha

    arr = np.asarray(work)
    areas = {lab: int((arr == lab).sum()) for lab in labels}
    biggest = max(areas.values()) if areas else 0
    if not biggest:
        return alpha

    drop = np.zeros((sh, sw), dtype=bool)
    for lab, area in areas.items():
        if area >= biggest * max_frac:
            continue
        sel = arr == lab
        if not sel.any():
            continue
        px = rgb[sel]
        lum = px.mean(axis=1).mean()
        chroma = (px.max(axis=1) - px.min(axis=1)).mean()
        if lum > 200 and chroma < 24:          # pale and colourless => shadow
            drop |= sel
    if not drop.any():
        return alpha

    dropmask = Image.fromarray((drop * 255).astype("uint8"), "L").resize(
        (w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))
    return ImageChops.subtract(alpha, dropmask)


def cutout(art: Image.Image, tolerance: int = 26) -> Image.Image:
    """Drop the white background the model was asked to render on.

    Two passes, because either alone is wrong:

    1. Flood inward from the edges. This handles the surrounding background
       without touching white inside the subject.
    2. Remove ENCLOSED flat-white regions too. A rakhi is a loop and a garland
       is a ring — the background shows through the middle, and a border flood
       can never reach it. Those islands survived as white blobs, which is
       invisible on a cream canvas and glaring on a maroon one.

    Pass 2 keys on flatness rather than brightness so white cloth and pearls,
    which are shaded, are kept.
    """
    art = art.convert("RGB")
    w, h = art.size
    lum = art.convert("L")

    marker = lum.copy()
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
             (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2),
             (w // 4, 0), (3 * w // 4, 0), (w // 4, h - 1), (3 * w // 4, h - 1)]
    for sx, sy in seeds:
        try:
            if marker.getpixel((sx, sy)) >= 200:
                ImageDraw.floodfill(marker, (sx, sy), 1, thresh=tolerance)
        except Exception:  # noqa: BLE001
            continue
    exterior = marker.point(lambda p: 0 if p <= 1 else 255)

    enclosed = _flat_white(art, lum_min=236, chroma_max=14, clean=5)
    keep = ImageChops.subtract(exterior, enclosed)

    edge = Image.new("L", (w, h), 0)
    pad = max(6, int(min(w, h) * 0.02))
    ImageDraw.Draw(edge).rectangle([pad, pad, w - 1 - pad, h - 1 - pad], fill=255)
    edge = edge.filter(ImageFilter.GaussianBlur(pad * 0.8))
    alpha = ImageChops.multiply(keep, edge).filter(ImageFilter.GaussianBlur(1.2))
    try:
        alpha = _drop_shadow_islands(art, alpha)
    except Exception as exc:  # noqa: BLE001
        print(f"[cutout] island pass skipped: {exc}", flush=True)

    out = art.convert("RGBA")
    out.putalpha(alpha)
    return out


def is_white_bg(art: Image.Image, min_frac: float = 0.70) -> bool:
    """Is this artwork actually isolated on white, as the prompt asked?

    The model honours the white-background instruction most of the time, but for
    contextual subjects it sometimes renders a full scene. Cutting a scene tears
    ragged holes in it, so the border is sampled first and the caller picks
    between a cutout and a shaped frame.
    """
    lum = art.convert("L")
    w, h = lum.size
    step = max(1, min(w, h) // 120)
    pts = []
    for x in range(0, w, step):
        pts.append(lum.getpixel((x, 0)))
        pts.append(lum.getpixel((x, h - 1)))
    for y in range(0, h, step):
        pts.append(lum.getpixel((0, y)))
        pts.append(lum.getpixel((w - 1, y)))
    if not pts:
        return False
    return sum(1 for v in pts if v >= 235) / len(pts) >= min_frac


def _framed(art: Image.Image, mask: Image.Image, ring, ring_w: int,
            outline_path) -> Image.Image:
    """Apply a shaped mask plus a decorative ring, on a transparent canvas."""
    im = art.convert("RGBA")
    im.putalpha(mask.filter(ImageFilter.GaussianBlur(0.8)))
    pad = ring_w * 3
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    out.alpha_composite(im, (pad, pad))
    if ring and ring_w:
        d = ImageDraw.Draw(out, "RGBA")
        outline_path(d, pad, ring, ring_w)
    return out


def medallion(art: Image.Image, ring=GOLD, ring_w: int = 9) -> Image.Image:
    """Circular medallion treatment.

    Used when the model ignored the white-background instruction. A rounded
    rectangle reads as a photo box pasted onto the design; a medallion reads as
    a deliberate frame and sits far better on an ornamented canvas.
    """
    side = min(art.size)
    art = art.convert("RGB").crop(((art.width - side) // 2, (art.height - side) // 2,
                                   (art.width - side) // 2 + side,
                                   (art.height - side) // 2 + side))
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, side - 1, side - 1], fill=255)

    def ring_path(d, pad, col, w):
        d.ellipse([pad - w // 2, pad - w // 2, pad + side + w // 2, pad + side + w // 2],
                  outline=(*col, 255), width=w)
        d.ellipse([pad - w * 2, pad - w * 2, pad + side + w * 2, pad + side + w * 2],
                  outline=(*col, 110), width=2)
    return _framed(art, mask, ring, ring_w, ring_path)


def arch(art: Image.Image, ring=GOLD, ring_w: int = 9) -> Image.Image:
    """Temple-arch treatment — rounded top, straight base."""
    w, h = art.size
    tgt_w = int(h * 0.78)
    if w > tgt_w:
        art = art.crop(((w - tgt_w) // 2, 0, (w - tgt_w) // 2 + tgt_w, h))
    w, h = art.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    r = w // 2
    d.pieslice([0, 0, w - 1, w - 1], 180, 360, fill=255)
    d.rectangle([0, r, w - 1, h - 1], fill=255)

    def ring_path(dd, pad, col, rw):
        dd.arc([pad - rw // 2, pad - rw // 2, pad + w + rw // 2, pad + w + rw // 2],
               180, 360, fill=(*col, 255), width=rw)
        dd.line([(pad - rw // 2, pad + r), (pad - rw // 2, pad + h)], fill=(*col, 255), width=rw)
        dd.line([(pad + w + rw // 2, pad + r), (pad + w + rw // 2, pad + h)],
                fill=(*col, 255), width=rw)
    return _framed(art, mask, ring, ring_w, ring_path)


def defringe(im: Image.Image, px: int = 2) -> Image.Image:
    """Erode a cutout's alpha slightly.

    A flood cutout leaves a rim of near-white pixels from the original
    background. Invisible on a cream canvas, an obvious halo on a dark one — so
    the edge is pulled in before compositing onto dark themes.
    """
    a = im.split()[3]
    for _ in range(max(1, px)):
        a = a.filter(ImageFilter.MinFilter(3))
    a = a.filter(ImageFilter.GaussianBlur(0.8))
    out = im.copy()
    out.putalpha(a)
    return out


def trim(im: Image.Image) -> Image.Image:
    bbox = im.split()[3].getbbox()
    return im.crop(bbox) if bbox else im


def scale_to(im: Image.Image, max_w: int, max_h: int) -> Image.Image:
    r = min(max_w / im.width, max_h / im.height)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
