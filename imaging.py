"""
Compose the final 1080x1080 Instagram post: model artwork + overlaid text.

The image model returns text-free artwork with a calm bottom band (see prompts.py).
Here we square it, lay a gradient scrim over the bottom, and place the Hindi
headline, optional subline and the brand handle using properly shaped Devanagari.
"""
from __future__ import annotations

import io
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

import config
import hinditext

WHITE = (255, 255, 255)


# ── canvas ──────────────────────────────────────────────────────────────────
def to_square(img_bytes: bytes, px: Optional[int] = None) -> Image.Image:
    """Centre-crop to 1:1 and resize to px. Models drift off exact aspect ratio."""
    px = px or config.CANVAS_PX
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = im.size
    side = min(w, h)
    im = im.crop(((w - side) // 2, (h - side) // 2,
                  (w - side) // 2 + side, (h - side) // 2 + side))
    return im.resize((px, px), Image.LANCZOS)


def _scrim(im: Image.Image, start: float = 0.42, strength: int = 215) -> Image.Image:
    """Darken the bottom so overlaid text stays legible on any artwork."""
    px = im.size[0]
    grad = Image.new("L", (1, px), 0)
    top = int(px * start)
    for y in range(top, px):
        t = (y - top) / max(1, px - top)
        grad.putpixel((0, y), int(strength * (t ** 1.6)))
    mask = grad.resize(im.size)
    dark = Image.new("RGB", im.size, (8, 6, 14))
    return Image.composite(dark, im.convert("RGB"), mask)


# ── Devanagari text ─────────────────────────────────────────────────────────
def _render(text: str, size: int, color=WHITE, bold: bool = True) -> Optional[Image.Image]:
    png = hinditext.render_hindi(text, font_size=size, color=color, bold=bold)
    if not png:
        return None
    return Image.open(io.BytesIO(png)).convert("RGBA")


def shaping_available() -> bool:
    """True when Devanagari can be shaped correctly on this host.

    False means CoreText (macOS) and a Devanagari TTF (Linux) are both missing —
    the caller should surface that rather than ship mangled text.
    """
    im = _render("क्ष", 40)
    return im is not None and im.width > 4


def _wrap(text: str, size: int, max_w: int, max_lines: int = 2) -> List[Image.Image]:
    """Greedy word-wrap by measuring real shaped renders."""
    words = text.split()
    if not words:
        return []
    lines: List[Image.Image] = []
    cur: List[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        im = _render(trial, size)
        if im is None:
            return []
        if im.width <= max_w or not cur:
            cur.append(w)
            if im.width > max_w and len(cur) == 1:   # single word too wide
                lines.append(im); cur = []
        else:
            done = _render(" ".join(cur), size)
            if done:
                lines.append(done)
            cur = [w]
        if len(lines) >= max_lines:
            break
    if cur and len(lines) < max_lines:
        im = _render(" ".join(cur), size)
        if im:
            lines.append(im)
    # anything that still overflows gets scaled down rather than clipped
    out = []
    for im in lines[:max_lines]:
        if im.width > max_w:
            r = max_w / im.width
            im = im.resize((max_w, max(1, int(im.height * r))), Image.LANCZOS)
        out.append(im)
    return out


def _latin_font(size: int):
    for p in ("/System/Library/Fonts/Supplemental/Futura.ttc",
              "/System/Library/Fonts/HelveticaNeue.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


# ── composition ─────────────────────────────────────────────────────────────
def compose(art_bytes: bytes, headline: str, subline: str = "",
            handle: Optional[str] = None) -> Tuple[bytes, dict]:
    """Artwork + text -> final square JPEG bytes, plus a small QA dict."""
    px = config.CANVAS_PX
    im = to_square(art_bytes, px).convert("RGBA")
    im = _scrim(im).convert("RGBA")

    margin = int(px * 0.075)
    max_w = px - margin * 2
    notes = {"shaping": True, "headline_lines": 0}

    head_imgs = _wrap(headline, int(px * 0.082), max_w, max_lines=2)
    if not head_imgs:
        notes["shaping"] = False          # caller decides whether to ship this
    sub_imgs = _wrap(subline, int(px * 0.042), max_w, max_lines=1) if subline else []
    notes["headline_lines"] = len(head_imgs)

    gap = int(px * 0.018)
    block_h = sum(i.height for i in head_imgs) + gap * max(0, len(head_imgs) - 1)
    if sub_imgs:
        block_h += int(px * 0.028) + sum(i.height for i in sub_imgs)

    handle = config.BRAND_HANDLE if handle is None else handle
    handle_h = int(px * 0.030) if handle else 0
    bottom = px - margin - (handle_h + int(px * 0.022) if handle else 0)
    y = bottom - block_h

    for i, line in enumerate(head_imgs):
        im.alpha_composite(line, ((px - line.width) // 2, y))
        y += line.height + (gap if i < len(head_imgs) - 1 else 0)
    if sub_imgs:
        y += int(px * 0.028)
        for line in sub_imgs:
            faded = line.copy()
            faded.putalpha(faded.split()[3].point(lambda a: int(a * 0.86)))
            im.alpha_composite(faded, ((px - faded.width) // 2, y))
            y += line.height

    if handle:
        d = ImageDraw.Draw(im)
        f = _latin_font(handle_h)
        tw = d.textlength(handle, font=f)
        d.text(((px - tw) / 2, px - margin - handle_h),
               handle, font=f, fill=(255, 255, 255, 205))

    out = io.BytesIO()
    im.convert("RGB").save(out, "JPEG", quality=92, optimize=True)
    return out.getvalue(), notes
