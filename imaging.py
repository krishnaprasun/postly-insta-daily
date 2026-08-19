"""
Compose the finished 1080x1080 post in the Postly brand template.

The model supplies one cutout artwork element on white (see prompts.py); every
other pixel — background, logo lockup, two-tone Devanagari headline, blessing
line, app-promo footer — is drawn here, so the brand stays identical day to day
and the Hindi is always correctly shaped.

Four layouts, chosen per variant so the day's options differ in structure and
not just in art style.
"""
from __future__ import annotations

import io
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter

import brandkit as bk
import config

PX = 1080
MARGIN = 62


def shaping_available() -> bool:
    return bk.shaping_available()


def to_square(img_bytes: bytes, px: int = PX) -> Image.Image:
    """Fit the artwork into a square on WHITE without cropping.

    The model returns whatever aspect it likes (often 16:9). Centre-cropping a
    cutout lops the subject's edges off — a rakhi loses its tassels — so it is
    padded instead. White padding is invisible: the cutout keys it out, and the
    canvas behind is white anyway.
    """
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    r = min(px / im.width, px / im.height)
    im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
    sq = Image.new("RGB", (px, px), (255, 255, 255))
    sq.paste(im, ((px - im.width) // 2, (px - im.height) // 2))
    return sq


def _crop_active(sq: Image.Image) -> Image.Image:
    """Drop the white letterbox padding to_square added, keeping the real photo."""
    lum = sq.convert("L")
    inv = lum.point(lambda v: 0 if v >= 250 else 255)
    bbox = inv.getbbox()
    return sq.crop(bbox) if bbox else sq


# ── palette per tone ────────────────────────────────────────────────────────
def _palette(brief: Dict) -> Dict:
    tribute = str(brief.get("tone", "")).lower() in (
        "tribute", "tribute_somber", "remembrance", "shraddhanjali")
    if tribute:
        return {"tribute": True, "acc1": bk.T_DARK, "acc2": bk.T_ACC,
                "body": bk.INK, "bar": bk.T_DARK, "orn": bk.T_ACC, "bg": (250, 250, 251)}
    return {"tribute": False, "acc1": bk.GREEN, "acc2": bk.GOLD,
            "body": bk.INK, "bar": bk.GREEN, "orn": bk.GOLD, "bg": bk.CREAM}


# ── background ──────────────────────────────────────────────────────────────
def _background(pal: Dict) -> Image.Image:
    im = Image.new("RGB", (PX, PX), pal["bg"])
    d = ImageDraw.Draw(im, "RGBA")
    # faint corner mandala arcs, echoing the reference creatives
    c = (*pal["orn"], 16)
    for r in range(150, 470, 26):
        d.ellipse([-r + 40, PX - r - 40, r + 40, PX + r - 40], outline=c, width=2)
    for r in range(120, 330, 24):
        d.ellipse([PX - r - 30, -r + 30, PX + r - 30, r + 30], outline=c, width=2)
    # soft warm wash at the top
    wash = Image.new("L", (1, PX), 0)
    for y in range(PX):
        wash.putpixel((0, y), max(0, int(26 * (1 - y / (PX * 0.55)))))
    im = Image.composite(Image.new("RGB", (PX, PX), (255, 252, 240)), im,
                         wash.resize((PX, PX)))
    return im


# ── header / footer ─────────────────────────────────────────────────────────
def _header(canvas: Image.Image, pal: Dict, centered: bool = False) -> int:
    """Draw the logo lockup. Returns the y where content may start."""
    lg = bk.logo(56, bk.NAVY)
    d = ImageDraw.Draw(canvas)
    f = bk.latin(19, bold=False)
    if lg:
        x = (PX - lg.width) // 2 if centered else MARGIN
        canvas.alpha_composite(lg, (x, 50))
        tw = d.textlength(bk.TAGLINE, font=f)
        tx = (PX - tw) / 2 if centered else MARGIN + 2
        d.text((tx, 50 + lg.height + 8), bk.TAGLINE, font=f, fill=(*bk.MUTED, 255))
        return 50 + lg.height + 8 + 26
    return 50


def _footer(canvas: Image.Image, pal: Dict, compact: bool = False) -> int:
    """Draw the app-promo footer. Returns the y where content must stop."""
    d = ImageDraw.Draw(canvas)
    bar_h = 62
    bar_y = PX - MARGIN - bar_h
    inner = PX - MARGIN * 2

    # green feature bar + white "Download Now" pill on the right
    dl_w = int(inner * 0.34)
    feat_w = inner - dl_w - 12
    bar = bk.pill((feat_w, bar_h), pal["bar"], radius=bar_h // 2)
    canvas.alpha_composite(bar, (MARGIN, bar_y))

    fb = bk.latin(17, bold=True)
    fr = bk.latin(16, bold=False)
    gap = feat_w / len(bk.FEATURES)
    for i, label in enumerate(bk.FEATURES):
        cx = MARGIN + gap * i + gap / 2
        tw = d.textlength(label, font=fr)
        d.text((cx - tw / 2, bar_y + bar_h / 2 - 10), label, font=fr, fill=(255, 255, 255, 235))
        if i:
            d.line([(MARGIN + gap * i, bar_y + 16), (MARGIN + gap * i, bar_y + bar_h - 16)],
                   fill=(255, 255, 255, 70), width=1)

    dl = bk.pill((dl_w, bar_h), bk.WHITE, radius=bar_h // 2, outline=pal["bar"], width=2)
    canvas.alpha_composite(dl, (MARGIN + feat_w + 12, bar_y))
    dx = MARGIN + feat_w + 12
    t1, t2 = "Download Now", "Postly App"
    w1 = d.textlength(t1, font=fr)
    w2 = d.textlength(t2, font=fb)
    d.text((dx + dl_w / 2 - w1 / 2, bar_y + 12), t1, font=fr, fill=(*bk.MUTED, 255))
    d.text((dx + dl_w / 2 - w2 / 2, bar_y + 32), t2, font=fb, fill=(*pal["bar"], 255))

    if compact:
        return bar_y - 18

    # promo card above the bar
    card_h = 78
    card_y = bar_y - 12 - card_h
    card_w = int(inner * 0.66)
    card = bk.pill((card_w, card_h), bk.WHITE, radius=card_h // 2)
    canvas.alpha_composite(bk.shadow(card, blur=10, alpha=30), (MARGIN - 30, card_y - 30))

    ic = bk.app_icon(card_h - 22)
    if ic:
        canvas.alpha_composite(ic, (MARGIN + 12, card_y + 11))
    tx = MARGIN + 12 + (card_h - 22) + 16
    d.text((tx, card_y + 12), bk.PROMO_LINE1, font=bk.latin(16, bold=False), fill=(*bk.MUTED, 255))
    d.text((tx, card_y + 32), bk.PROMO_LINE2, font=bk.latin(19, bold=True), fill=(*bk.NAVY, 255))
    d.text((tx, card_y + 54), bk.PROMO_LINE3, font=bk.latin(16, bold=True), fill=(*pal["bar"], 255))
    return card_y - 18


# ── the Hindi text block ────────────────────────────────────────────────────
def _text_block(brief: Dict, pal: Dict, max_w: int, scale: float = 1.0,
                center: bool = True) -> Optional[Image.Image]:
    """prefix / two-tone occasion / suffix / ornament / blessing, as one RGBA block."""
    def S(v):
        return max(14, int(v * scale))

    rows: List[Tuple[Image.Image, int]] = []      # (image, gap-after)
    pre = (brief.get("prefix_hi") or "").strip()
    occ = (brief.get("occasion_hi") or "").strip()
    suf = (brief.get("suffix_hi") or "").strip()
    bls = (brief.get("blessing_hi") or "").strip()

    if pre:
        im = bk.fit(pre, S(38), max_w, bk.NAVY)
        if im:
            rows.append((im, S(14)))

    a, b = bk.split_headline(occ)
    if a:
        im = bk.fit(a, S(126), max_w, pal["acc1"])
        if im is None:
            return None
        rows.append((im, S(4) if b else S(16)))
    if b:
        im = bk.fit(b, S(104), max_w, pal["acc2"])
        if im:
            rows.append((im, S(16)))
    if suf:
        for im in bk.wrap(suf, S(42), max_w, bk.NAVY, max_lines=2):
            rows.append((im, S(8)))
        if rows:
            rows[-1] = (rows[-1][0], S(22))
    if not rows:
        return None

    orn_h = S(48) if bls else 0
    bl_imgs = bk.wrap(bls, S(29), max_w, pal["body"], bold=False, max_lines=3) if bls else []

    total_h = sum(im.height + g for im, g in rows) + orn_h + \
        sum(im.height + S(6) for im in bl_imgs)
    block = Image.new("RGBA", (max_w, max(1, total_h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(block, "RGBA")

    y = 0
    for im, g in rows:
        x = (max_w - im.width) // 2 if center else 0
        block.alpha_composite(im, (x, y))
        y += im.height + g
    if bl_imgs:
        bk.ornament(d, max_w // 2 if center else min(max_w // 2, 190), y + S(20),
                    int(max_w * 0.42), pal["orn"])
        y += orn_h
        for im in bl_imgs:
            x = (max_w - im.width) // 2 if center else 0
            block.alpha_composite(im, (x, y))
            y += im.height + S(6)

    bbox = block.split()[3].getbbox()
    return block.crop((0, 0, max_w, bbox[3])) if bbox else block


# ── layouts ─────────────────────────────────────────────────────────────────
def _layout_hero(canvas, art, brief, pal, mirror: bool = False):
    """Artwork down one side, text column on the other.

    A very wide subject cannot fill a side column — it ends up small with a big
    empty band above it — so wide artwork is laid out as a bottom banner instead.
    """
    trimmed = bk.trim(art)
    if trimmed.width / max(1, trimmed.height) > 1.5:
        return _layout_banner(canvas, art, brief, pal)

    top = _header(canvas, pal)
    bottom = _footer(canvas, pal, compact=True)

    art_w, art_h = int(PX * 0.50), bottom - top - 6
    a = bk.scale_to(trimmed, art_w, art_h)
    ax = PX - MARGIN - a.width if not mirror else MARGIN
    canvas.alpha_composite(a, (ax, bottom - a.height))

    col_w = PX - MARGIN * 2 - art_w - 20
    blk = _text_block(brief, pal, col_w, scale=0.80, center=True)
    if blk is None:
        return False
    bx = MARGIN if not mirror else PX - MARGIN - col_w
    # optically centred — sitting dead-centre leaves the top of the frame empty
    by = top + max(0, int((bottom - top - blk.height) * 0.38))
    canvas.alpha_composite(blk, (bx, by))
    return True


def _layout_typographic(canvas, art, brief, pal):
    """Text-led, artwork as a soft watermark — the reference's second style."""
    top = _header(canvas, pal, centered=True)
    bottom = _footer(canvas, pal, compact=False)

    a = bk.scale_to(bk.trim(art), int(PX * 0.72), int((bottom - top) * 0.92))
    faint = a.copy()
    faint.putalpha(faint.split()[3].point(lambda v: int(v * 0.13)))
    canvas.alpha_composite(faint, ((PX - a.width) // 2, top + (bottom - top - a.height) // 2))

    blk = _text_block(brief, pal, PX - MARGIN * 2 - 60, scale=0.92, center=True)
    if blk is None:
        return False
    canvas.alpha_composite(blk, ((PX - blk.width) // 2,
                                 top + max(0, (bottom - top - blk.height) // 2)))
    return True


def _layout_banner(canvas, art, brief, pal):
    """Artwork as a large bottom element, text stacked above it."""
    top = _header(canvas, pal, centered=True)
    bottom = _footer(canvas, pal, compact=True)

    a = bk.scale_to(bk.trim(art), int(PX * 0.74), int((bottom - top) * 0.50))
    canvas.alpha_composite(a, ((PX - a.width) // 2, bottom - a.height))

    avail = bottom - a.height - top - 16
    blk = _text_block(brief, pal, PX - MARGIN * 2 - 40, scale=0.78, center=True)
    if blk is None:
        return False
    if blk.height > avail:
        r = avail / blk.height
        blk = blk.resize((max(1, int(blk.width * r)), max(1, int(blk.height * r))), Image.LANCZOS)
    canvas.alpha_composite(blk, ((PX - blk.width) // 2, top + max(0, (avail - blk.height) // 2)))
    return True


LAYOUTS = ["hero-right", "typographic", "banner", "hero-left"]


def layout_name(i: int) -> str:
    return LAYOUTS[i % len(LAYOUTS)]


# ── entry point ─────────────────────────────────────────────────────────────
def compose(art_bytes: bytes, brief: Dict, variant: int = 0) -> Tuple[bytes, Dict]:
    """Artwork + brief -> finished branded post. Returns (jpeg_bytes, notes)."""
    pal = _palette(brief)
    canvas = _background(pal).convert("RGBA")

    sq = to_square(art_bytes)
    if bk.is_white_bg(sq):
        art = bk.cutout(sq)
        mode = "cutout"
    else:
        # The model returned a full scene, not an isolated subject. Framing it as
        # a photo card reads as deliberate; flood-cutting it would shred the edges.
        art = bk.photo_card(_crop_active(sq))
        mode = "card"

    name = layout_name(variant)
    if name == "hero-right":
        ok = _layout_hero(canvas, art, brief, pal, mirror=False)
    elif name == "hero-left":
        ok = _layout_hero(canvas, art, brief, pal, mirror=True)
    elif name == "banner":
        ok = _layout_banner(canvas, art, brief, pal)
    else:
        ok = _layout_typographic(canvas, art, brief, pal)

    notes = {"shaping": bool(ok), "layout": name, "tribute": pal["tribute"], "art": mode}
    out = io.BytesIO()
    canvas.convert("RGB").save(out, "JPEG", quality=93, optimize=True)
    return out.getvalue(), notes
