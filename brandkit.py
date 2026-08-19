"""
Postly brand kit: palette, fonts, logo, and the repeated pieces of the post
template (header lockup, ornament dividers, app-promo footer, artwork cutout).

Colours and layout are taken from the reference creatives: white/cream ground,
vivid green + gold two-tone Devanagari headline, navy body text, and the
"Download Now / Postly App" footer bar.
"""
from __future__ import annotations

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
def hindi(text: str, size: int, color=NAVY, bold: bool = True) -> Optional[Image.Image]:
    png = hinditext.render_hindi(text, font_size=size, color=color, bold=bold)
    if not png:
        return None
    return Image.open(io.BytesIO(png)).convert("RGBA")


def shaping_available() -> bool:
    im = hindi("क्ष", 40)
    return im is not None and im.width > 4


def fit(text: str, size: int, max_w: int, color=NAVY, bold: bool = True) -> Optional[Image.Image]:
    """Render Devanagari at `size`, scaled down if it would exceed max_w."""
    im = hindi(text, size, color, bold)
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


def ornament(draw: ImageDraw.ImageDraw, cx: int, y: int, w: int, color=GOLD) -> None:
    """The small diamond-and-rule divider used between text blocks."""
    half = w // 2
    draw.line([(cx - half, y), (cx - 14, y)], fill=(*color, 150), width=2)
    draw.line([(cx + 14, y), (cx + half, y)], fill=(*color, 150), width=2)
    for dx, s in ((0, 7), (-11, 4), (11, 4)):
        draw.polygon([(cx + dx, y - s), (cx + dx + s, y), (cx + dx, y + s), (cx + dx - s, y)],
                     fill=(*color, 210))


# ── artwork cutout ──────────────────────────────────────────────────────────
def cutout(art: Image.Image, tolerance: int = 26) -> Image.Image:
    """Drop the background the model was asked to render on white.

    Flood-fills inward from the edges over the LUMINANCE image with a tolerance,
    rather than keying every light pixel. Two reasons:
      * keying by brightness would eat white flowers or a white kurta inside the
        subject,
      * the model's "white" background is often a soft off-white gradient with a
        contact shadow, which a hard threshold misses entirely — leaving a
        visible rectangle pasted on the cream canvas.
    Whatever the flood does not reach is kept, and the edge is feathered so a
    failed key degrades to a soft blend instead of a hard box.
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
            if marker.getpixel((sx, sy)) >= 200:      # only flood from light edges
                ImageDraw.floodfill(marker, (sx, sy), 1, thresh=tolerance)
        except Exception:  # noqa: BLE001
            continue

    alpha = marker.point(lambda p: 0 if p <= 1 else 255)

    # Feather the outer border so an unsuccessful key blends rather than boxes.
    edge = Image.new("L", (w, h), 0)
    pad = max(6, int(min(w, h) * 0.02))
    ImageDraw.Draw(edge).rectangle([pad, pad, w - 1 - pad, h - 1 - pad], fill=255)
    edge = edge.filter(ImageFilter.GaussianBlur(pad * 0.8))
    alpha = ImageChops.multiply(alpha, edge)
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.2))

    out = art.convert("RGBA")
    out.putalpha(alpha)
    return out


def is_white_bg(art: Image.Image, min_frac: float = 0.70) -> bool:
    """Is this artwork actually isolated on white, as the prompt asked?

    The model honours the white-background instruction most of the time, but for
    contextual photographic subjects (a chai cup) it often renders a full scene.
    Flood-cutting a scene tears ragged holes in it, which looks far worse than
    not cutting at all — so the border is sampled first and the caller picks a
    treatment.
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


def photo_card(art: Image.Image, radius: int = 34) -> Image.Image:
    """Treatment for artwork that came back as a full scene: a rounded photo card."""
    im = art.convert("RGBA")
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1],
                                           radius=radius, fill=255)
    im.putalpha(mask)
    return im


def trim(im: Image.Image) -> Image.Image:
    bbox = im.split()[3].getbbox()
    return im.crop(bbox) if bbox else im


def scale_to(im: Image.Image, max_w: int, max_h: int) -> Image.Image:
    r = min(max_w / im.width, max_h / im.height)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
