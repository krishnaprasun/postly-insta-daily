"""
Correct Devanagari (Hindi) text -> transparent PNG using macOS CoreText (pyobjc).
PIL can't shape Devanagari here (raqm off); CoreText does proper conjunct/matra shaping.
Used to overlay a figure's NAME deterministically (the image model refuses real person names).
"""
from __future__ import annotations
import io, math, os
from pathlib import Path

# Devanagari font for the Linux/Pillow fallback (Render). Override with $DEVANAGARI_FONT.
_FONT_CANDIDATES = [
    os.environ.get("DEVANAGARI_FONT", ""),
    str(Path(__file__).resolve().parent / "fonts" / "NotoSansDevanagari-Bold.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
]


def _font_path() -> str | None:
    for p in _FONT_CANDIDATES:
        if p and os.path.exists(p):
            return p
    return None


def _render_pil(text, font_size, color, pad):
    """Linux/cross-platform path: Pillow + raqm (libraqm) shapes Devanagari correctly."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        fp = _font_path()
        if not fp:
            return None
        try:
            font = ImageFont.truetype(fp, font_size, layout_engine=ImageFont.Layout.RAQM)
        except Exception:
            font = ImageFont.truetype(fp, font_size)  # raqm missing → still better than nothing
        tmp = Image.new("RGBA", (8, 8))
        l, t, r, b = ImageDraw.Draw(tmp).textbbox((0, 0), text, font=font)
        w, h = (r - l) + pad * 2, (b - t) + pad * 2
        im = Image.new("RGBA", (max(2, w), max(2, h)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((pad - l, pad - t), text, font=font, fill=(*color, 255))
        bbox = im.split()[3].getbbox()
        if bbox:
            im = im.crop(bbox)
        out = io.BytesIO(); im.save(out, "PNG"); return out.getvalue()
    except Exception:
        return None


def render_hindi(text: str, font_size: int = 64, color=(255, 255, 255),
                 font_name: str = "Kohinoor Devanagari", bold: bool = True,
                 pad: int = 10) -> bytes | None:
    """Render `text` as a tightly-cropped RGBA PNG (transparent bg). Returns PNG bytes.
    macOS → CoreText (best shaping). Other OS (Render/Linux) → Pillow+raqm fallback."""
    try:
        from AppKit import (NSAttributedString, NSFont, NSColor, NSBitmapImageRep,
                            NSGraphicsContext, NSFontManager, NSDeviceRGBColorSpace)
        from Foundation import NSMakePoint
    except Exception:
        return _render_pil(text, font_size, color, pad)
    fm = NSFontManager.sharedFontManager()
    font = NSFont.fontWithName_size_(font_name, font_size)
    if font is None:
        font = NSFont.fontWithName_size_("Devanagari Sangam MN", font_size) \
            or NSFont.systemFontOfSize_(font_size)
    if bold and font is not None:
        b = fm.convertFont_toHaveTrait_(font, 2)  # NSBoldFontMask
        if b is not None:
            font = b
    r, g, bl = [c / 255.0 for c in color]
    col = NSColor.colorWithDeviceRed_green_blue_alpha_(r, g, bl, 1.0)
    attrs = {"NSFont": font, "NSColor": col}
    s = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
    sz = s.size()
    w = int(math.ceil(sz.width)) + pad * 2
    h = int(math.ceil(sz.height)) + pad * 2
    if w < 2 or h < 2:
        return None
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, w, h, 8, 4, True, False, NSDeviceRGBColorSpace, 0, 0)
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(ctx)
    s.drawAtPoint_(NSMakePoint(pad, pad))
    NSGraphicsContext.restoreGraphicsState()
    png = rep.representationUsingType_properties_(4, None)  # 4 = NSBitmapImageFileTypePNG
    data = bytes(png)
    # tight-crop transparent margins via PIL
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        bbox = im.split()[3].getbbox()
        if bbox:
            im = im.crop(bbox)
        out = io.BytesIO(); im.save(out, "PNG"); return out.getvalue()
    except Exception:
        return data
