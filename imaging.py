"""
Compose the finished 1080x1080 post.

Each variant gets its own THEME (themes.py) so the day's four options look
genuinely different in a feed rather than four takes on one cream card:

  floral-cream  light botanical canvas, subject cut out and floated
  deep-festive  dark jewel canvas with gold bokeh, subject floated
  scene-card    the model's full backdrop, type on a translucent card
  scene-wash    the model's full backdrop under a colour wash, type centred

All Devanagari is shaped here, never drawn by the model.
"""
from __future__ import annotations

import io
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter

import brandkit as bk
import prompts
import themes

PX = 1080
MARGIN = 62


def shaping_available() -> bool:
    return bk.shaping_available()


def to_square(img_bytes: bytes, px: int = PX, pad_white: bool = True) -> Image.Image:
    """Fit artwork to a square. Cutouts are padded (never cropped, or a rakhi
    loses its tassels); scene backdrops are cropped to fill the frame."""
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    if pad_white:
        r = min(px / im.width, px / im.height)
        im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
        sq = Image.new("RGB", (px, px), (255, 255, 255))
        sq.paste(im, ((px - im.width) // 2, (px - im.height) // 2))
        return sq
    r = max(px / im.width, px / im.height)
    im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
    return im.crop(((im.width - px) // 2, (im.height - px) // 2,
                    (im.width - px) // 2 + px, (im.height - px) // 2 + px))


def _crop_active(sq: Image.Image) -> Image.Image:
    lum = sq.convert("L")
    inv = lum.point(lambda v: 0 if v >= 250 else 255)
    bbox = inv.getbbox()
    return sq.crop(bbox) if bbox else sq


def _is_muted(brief: Dict) -> bool:
    """Muted palette = death anniversary only. brief.py decides this from the
    occasion itself; the model's tone word says "remembrance" for a Jayanti too,
    which would wrongly grey out a birth anniversary."""
    if "muted" in brief:
        return bool(brief["muted"])
    return str(brief.get("tone", "")).lower() in ("tribute", "tribute_somber", "shraddhanjali")


# ── header / footer ─────────────────────────────────────────────────────────
def _header(canvas, th: Dict, centered: bool = False, scrim: bool = False) -> int:
    """Logo lockup. On a photographic backdrop the logo is white over a soft top
    scrim — a navy wordmark on an arbitrary scene is unreadable, and which scene
    the model returns is not knowable in advance."""
    if scrim:
        layer = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
        d0 = ImageDraw.Draw(layer, "RGBA")
        band = 200
        for y in range(band):
            d0.line([(0, y), (PX, y)], fill=(10, 8, 18, int(130 * (1 - y / band) ** 1.4)))
        canvas.alpha_composite(layer)
    col = (255, 255, 255) if (th["dark"] or scrim) else bk.NAVY
    sub = (238, 235, 230) if (th["dark"] or scrim) else bk.MUTED
    lg = bk.logo(56, col)
    d = ImageDraw.Draw(canvas)
    f = bk.latin(19, bold=False)
    if not lg:
        return 50
    x = (PX - lg.width) // 2 if centered else MARGIN
    canvas.alpha_composite(lg, (x, 50))
    tw = d.textlength(bk.TAGLINE, font=f)
    tx = (PX - tw) / 2 if centered else MARGIN + 2
    d.text((tx, 50 + lg.height + 8), bk.TAGLINE, font=f, fill=(*sub, 235))
    return 50 + lg.height + 8 + 26


def _footer_top(compact: bool = False) -> int:
    """Where the footer starts, without drawing it.

    Lets a layout lay its own panel down BEFORE the footer, so the panel does not
    end up painted over the feature bar and dim it.
    """
    bar_y = PX - MARGIN - 62
    return bar_y - 18 if compact else bar_y - 12 - 78 - 18


def _footer(canvas, th: Dict, compact: bool = False) -> int:
    d = ImageDraw.Draw(canvas)
    bar_h, inner = 62, PX - MARGIN * 2
    bar_y = PX - MARGIN - bar_h
    bar_col = th["bar"]

    dl_w = int(inner * 0.34)
    feat_w = inner - dl_w - 12
    canvas.alpha_composite(bk.pill((feat_w, bar_h), bar_col, radius=bar_h // 2), (MARGIN, bar_y))

    fb, fr = bk.latin(17, bold=True), bk.latin(16, bold=False)
    on_bar = (26, 20, 8) if bar_col == bk.GOLD else (255, 255, 255)
    gap = feat_w / len(bk.FEATURES)
    for i, label in enumerate(bk.FEATURES):
        cx = MARGIN + gap * i + gap / 2
        tw = d.textlength(label, font=fr)
        d.text((cx - tw / 2, bar_y + bar_h / 2 - 10), label, font=fr, fill=(*on_bar, 240))
        if i:
            d.line([(MARGIN + gap * i, bar_y + 16), (MARGIN + gap * i, bar_y + bar_h - 16)],
                   fill=(*on_bar, 80), width=1)

    dx = MARGIN + feat_w + 12
    canvas.alpha_composite(bk.pill((dl_w, bar_h), bk.WHITE, radius=bar_h // 2,
                                   outline=bar_col, width=2), (dx, bar_y))
    t1, t2 = "Download Now", "Postly App"
    d.text((dx + dl_w / 2 - d.textlength(t1, font=fr) / 2, bar_y + 12), t1, font=fr,
           fill=(*bk.MUTED, 255))
    d.text((dx + dl_w / 2 - d.textlength(t2, font=fb) / 2, bar_y + 32), t2, font=fb,
           fill=(*(bk.GOLD_DK if bar_col == bk.GOLD else bar_col), 255))

    if compact:
        return bar_y - 18

    card_h = 78
    card_y = bar_y - 12 - card_h
    card_w = int(inner * 0.66)
    card = bk.pill((card_w, card_h), bk.WHITE, radius=card_h // 2)
    canvas.alpha_composite(bk.shadow(card, blur=10, alpha=34), (MARGIN - 30, card_y - 30))
    ic = bk.app_icon(card_h - 22)
    if ic:
        canvas.alpha_composite(ic, (MARGIN + 12, card_y + 11))
    tx = MARGIN + 12 + (card_h - 22) + 16
    d.text((tx, card_y + 12), bk.PROMO_LINE1, font=bk.latin(16, bold=False), fill=(*bk.MUTED, 255))
    d.text((tx, card_y + 32), bk.PROMO_LINE2, font=bk.latin(19, bold=True), fill=(*bk.NAVY, 255))
    d.text((tx, card_y + 54), bk.PROMO_LINE3, font=bk.latin(16, bold=True),
           fill=(*(bk.GOLD_DK if th["bar"] == bk.GOLD else th["bar"]), 255))
    return card_y - 18


# ── the Hindi text block ────────────────────────────────────────────────────
def _text_block(brief: Dict, th: Dict, max_w: int, scale: float = 1.0,
                center: bool = True) -> Optional[Image.Image]:
    def S(v):
        return max(14, int(v * scale))

    # Fit to a slightly narrower box than the column. A line exactly as wide as
    # the column sits flush against it and its outline gets shaved, which reads
    # as the headline being cut off.
    inner = max_w - max(6, int(max_w * 0.04))

    rows: List[Tuple[Image.Image, int]] = []
    pre = (brief.get("prefix_hi") or "").strip()
    occ = (brief.get("occasion_hi") or "").strip()
    suf = (brief.get("suffix_hi") or "").strip()
    # a good-morning post carries a quote; everything else a one-line blessing
    body_text = (brief.get("quote_hi") or brief.get("blessing_hi") or "").strip()

    if pre:
        im = bk.fit(pre, S(38), inner, th["ink"])
        if im:
            rows.append((im, S(14)))

    # The occasion name gets display treatment — gradient, outline, depth. Flat
    # type made the hero line read as a caption instead of as lettering.
    a, b = bk.split_headline(occ)
    if a:
        im = bk.fit(a, S(126), inner, th["acc1"], styled=True)
        if im is None:
            return None
        rows.append((im, S(2) if b else S(14)))
    if b:
        im = bk.fit(b, S(104), inner, th["acc2"], styled=True)
        if im:
            rows.append((im, S(14)))
    if suf:
        for im in bk.wrap(suf, S(42), inner, th["ink"], max_lines=2):
            rows.append((im, S(8)))
        if rows:
            rows[-1] = (rows[-1][0], S(22))
    if not rows:
        return None

    crest_h = S(46)
    orn_h = S(48) if body_text else 0
    body_imgs = bk.wrap(body_text, S(29), inner, th["body"], bold=False, max_lines=4) \
        if body_text else []

    total_h = crest_h + sum(im.height + g for im, g in rows) + orn_h + \
        sum(im.height + S(8) for im in body_imgs)
    block = Image.new("RGBA", (max_w, max(1, total_h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(block, "RGBA")

    y = 0
    bk.ornament(d, max_w // 2 if center else min(max_w // 2, 190), y + S(18),
                int(max_w * 0.30), th["orn"])
    y += crest_h
    for im, g in rows:
        block.alpha_composite(im, ((max_w - im.width) // 2 if center else 0, y))
        y += im.height + g
    if body_imgs:
        bk.ornament(d, max_w // 2 if center else min(max_w // 2, 190), y + S(20),
                    int(max_w * 0.42), th["orn"])
        y += orn_h
        for im in body_imgs:
            block.alpha_composite(im, ((max_w - im.width) // 2 if center else 0, y))
            y += im.height + S(8)

    bbox = block.split()[3].getbbox()
    return block.crop((0, 0, max_w, bbox[3])) if bbox else block


def _fit_block(brief: Dict, th: Dict, max_w: int, max_h: int, center: bool = True,
               cap: float = 1.35) -> Optional[Image.Image]:
    """Largest text block that still fits the space.

    A fixed scale was leaving a third of the frame empty on short copy and
    crowding long copy. Type should fill the column it is given.
    """
    lo, hi, best = 0.45, cap, None
    for _ in range(7):
        mid = (lo + hi) / 2
        blk = _text_block(brief, th, max_w, scale=mid, center=center)
        if blk is None:
            return None
        if blk.height <= max_h:
            best = blk
            lo = mid
        else:
            hi = mid
    return best or _text_block(brief, th, max_w, scale=0.5, center=center)


def _ground_shadow(canvas, x: int, y: int, w: int, dark: bool):
    """Contact shadow so a cutout sits on the canvas instead of floating."""
    pad = 60
    sh = Image.new("RGBA", (w + pad * 2, 130), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([pad, 30, pad + w, 100],
                               fill=(0, 0, 0, 92 if not dark else 130))
    sh = sh.filter(ImageFilter.GaussianBlur(26))
    canvas.alpha_composite(sh, (x - pad, y - 78))


def _halo(canvas, blk: Image.Image, x: int, y: int, dark: bool, strength: int = 190):
    """A soft glow that follows the LETTERS, so type stays legible over artwork.

    This was a large ellipse behind the text block. Because the tint is lighter
    than the ground, the ellipse's own edge showed as a pale vertical line
    running down the frame and across the subject's face. A mask grown from the
    text's own alpha has no such boundary — it fades out a few pixels past the
    glyphs, wherever they happen to be.
    """
    a = blk.split()[3]
    grow = a
    for _ in range(5):
        grow = grow.filter(ImageFilter.MaxFilter(5))
    grow = grow.filter(ImageFilter.GaussianBlur(16))
    grow = grow.point(lambda v: min(255, int(v * (strength / 255.0) * 2.1)))

    pad = 60
    field = Image.new("RGBA", (blk.width + pad * 2, blk.height + pad * 2), (0, 0, 0, 0))
    tint = (8, 6, 14) if dark else (255, 254, 250)
    solid = Image.new("RGBA", grow.size, (*tint, 255))
    solid.putalpha(grow)
    field.alpha_composite(solid, (pad, pad))
    canvas.alpha_composite(field.filter(ImageFilter.GaussianBlur(6)), (x - pad, y - pad))


# ── subject layouts (cutout floated on a painted canvas) ────────────────────
def _layout_hero(canvas, art, brief, th, mirror=False):
    trimmed = bk.trim(art)
    if trimmed.width / max(1, trimmed.height) > 1.5:
        return _layout_banner(canvas, art, brief, th)
    top = _header(canvas, th)
    bottom = _footer(canvas, th, compact=True)

    # Art runs from just under the header to the footer and bleeds off the side,
    # so the frame reads full instead of leaving a third of it empty.
    # The artwork is deliberately oversized and pushed INTO the text column, so
    # the two halves interlock instead of sitting side by side. The halo below
    # keeps the words readable where the picture passes behind them.
    art_h = int((bottom - top) * 1.10)
    a = bk.scale_to(trimmed, int(PX * 0.66), art_h)
    overlap = int(a.width * 0.16)
    ax = (PX - MARGIN + 30 - a.width + overlap) if not mirror else (MARGIN - 30 - overlap)
    ay = bottom - a.height + 8
    _ground_shadow(canvas, ax + int(a.width * 0.14), bottom + 4, int(a.width * 0.72), th["dark"])
    canvas.alpha_composite(a, (ax, ay))

    # Column width must come from where the art ACTUALLY landed. Deriving it from
    # a nominal 50% while the art bleeds to 56% overlapped the two.
    if not mirror:
        bx = MARGIN
        col_w = max(240, ax - 16 - MARGIN)
    else:
        bx = ax + a.width + 16
        col_w = max(240, PX - MARGIN - bx)
    blk = _fit_block(brief, th, col_w, bottom - top - 20, center=True)
    if blk is None:
        return False
    by = top + max(0, int((bottom - top - blk.height) * 0.42))
    _halo(canvas, blk, bx, by, th["dark"])
    canvas.alpha_composite(blk, (bx, by))

    # Foliage drawn in FRONT of both halves, crossing the seam where the artwork
    # meets the words. Small procedural sprigs were tried first and read as blobs
    # at this scale; large soft leaves overlapping both layers is what actually
    # makes the two halves look like one drawing.
    if not _is_muted(brief):
        # Skipped on a punyatithi: fresh green foliage across a remembrance post
        # is the wrong register entirely.
        _foreground_foliage(canvas, bx + col_w, by, th, mirror)
    return True


def _foreground_foliage(canvas, seam_x: int, y: int, th: Dict, mirror: bool):
    import math
    import random
    leaf_col = (58, 122, 68) if not th["dark"] else (150, 196, 150)
    layer = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    rnd = random.Random(11)
    for _ in range(9):
        ox = seam_x + rnd.uniform(-PX * 0.10, PX * 0.06) * (-1 if mirror else 1)
        oy = y + rnd.uniform(-PX * 0.10, PX * 0.30)
        L, W = PX * rnd.uniform(0.10, 0.17), PX * rnd.uniform(0.030, 0.048)
        ang = rnd.uniform(-1.5, 1.5)
        poly = []
        for t in range(15):
            u = t / 14
            poly.append(((u - 0.5) * L, math.sin(math.pi * u) * W / 2))
        for t in range(14, -1, -1):
            u = t / 14
            poly.append(((u - 0.5) * L, -math.sin(math.pi * u) * W / 2))
        ca, sa = math.cos(ang), math.sin(ang)
        d.polygon([(ox + px * ca - py * sa, oy + px * sa + py * ca) for px, py in poly],
                  fill=(*leaf_col, rnd.randint(58, 104)))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.1)))


def _layout_banner(canvas, art, brief, th):
    top = _header(canvas, th, centered=True)
    bottom = _footer(canvas, th, compact=True)
    # Wide artwork lands here. Let it run nearly edge to edge and let the type
    # take the rest — the earlier split left both the art and the type undersized.
    a = bk.scale_to(bk.trim(art), int(PX * 0.92), int((bottom - top) * 0.46))
    canvas.alpha_composite(a, ((PX - a.width) // 2, bottom - a.height + 4))
    _ground_shadow(canvas, (PX - a.width) // 2 + int(a.width * 0.14), bottom + 6,
                   int(a.width * 0.72), th["dark"])
    avail = bottom - a.height - top - 10
    blk = _fit_block(brief, th, PX - MARGIN * 2 - 20, avail, center=True, cap=1.7)
    if blk is None:
        return False
    canvas.alpha_composite(blk, ((PX - blk.width) // 2, top + max(0, (avail - blk.height) // 2)))
    return True


# ── scene layouts (the model's backdrop IS the background) ──────────────────
def _layout_scene_card(canvas, brief, th):
    """Backdrop full-bleed, type on a translucent card over the calm half."""
    top = _header(canvas, th, scrim=True)
    bottom = _footer(canvas, th, compact=True)

    card_w = int(PX * 0.54)
    card_x = MARGIN
    blk = _fit_block(brief, th, card_w - 56, int((bottom - top) * 0.86), center=True)
    if blk is None:
        return False
    card_h = blk.height + 76
    card_y = top + max(0, int((bottom - top - card_h) * 0.42))

    card = bk.pill((card_w, card_h), (255, 255, 255), radius=34)
    card.putalpha(card.split()[3].point(lambda a: int(a * 0.90)))
    canvas.alpha_composite(bk.shadow(card, blur=16, alpha=52), (card_x - 48, card_y - 48))
    canvas.alpha_composite(blk, (card_x + 28, card_y + 38))
    return True


def _layout_scene_wash(canvas, brief, th):
    """Backdrop with a frosted panel across the lower third, type inside it.

    A full-image wash muddied the artwork and still left type sitting on top of
    the subject. A defined panel keeps the picture clean above and gives the
    words their own ground, which is what the type needs to be readable.
    """
    wr, wg, wb = th.get("wash", (14, 10, 24))
    top = _header(canvas, th, centered=True, scrim=True)
    bottom = _footer_top(compact=True)          # footer is drawn last, on top

    blk = _fit_block(brief, th, PX - MARGIN * 2 - 70, int(PX * 0.40), center=True)
    if blk is None:
        return False

    pad = int(PX * 0.045)
    panel_h = blk.height + pad * 2
    panel_y = bottom - panel_h - int(PX * 0.015)
    fade = int(PX * 0.10)

    layer = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    for y in range(max(0, panel_y - fade), PX):
        if y < panel_y:                       # soft top edge into the artwork
            a = int(212 * ((y - (panel_y - fade)) / fade) ** 1.5)
        else:
            a = 212
        d.line([(0, y), (PX, y)], fill=(wr, wg, wb, a))
    canvas.alpha_composite(layer)
    canvas.alpha_composite(blk, ((PX - blk.width) // 2, panel_y + pad))
    _footer(canvas, th, compact=True)           # drawn over the panel, stays crisp
    return True


# ── entry point ─────────────────────────────────────────────────────────────
def layout_name(i: int) -> str:
    return prompts.variant(i)["theme"]


def compose(art_bytes: bytes, brief: Dict, variant: int = 0) -> Tuple[bytes, Dict]:
    v = prompts.variant(variant)
    if brief.get("political") and v["theme"] == "saffron-sunburst":
        v = dict(v, theme="sky-ivory")     # neutral ground for a political figure
    # Each design gets its own complete write-up — greeting line, lead-in and
    # closing line — so the five are five choices, not one post five times.
    tv = brief.get("text_variants") or []
    if tv:
        t = tv[variant % len(tv)]
        brief = dict(brief)
        brief["prefix_hi"] = t.get("prefix", brief.get("prefix_hi", ""))
        brief["suffix_hi"] = t.get("suffix") or brief.get("suffix_hi", "")
        brief["blessing_hi"] = t.get("blessing") or brief.get("blessing_hi", "")
    else:
        bv = brief.get("blessing_variants") or []
        if bv:
            brief = dict(brief)
            brief["blessing_hi"] = bv[variant % len(bv)]
    th = themes.theme(v["theme"])
    tribute = _is_muted(brief)
    if tribute:
        th = themes.for_tribute(th)
    mode = ""

    if th["kind"] == "scene":
        canvas = to_square(art_bytes, pad_white=False).convert("RGBA")
        if tribute:                       # drain the colour out of a tribute backdrop
            canvas = Image.blend(canvas, canvas.convert("L").convert("RGBA"), 0.55)
        ok = (_layout_scene_card(canvas, brief, th) if th.get("panel") == "left"
              else _layout_scene_wash(canvas, brief, th))
        mode = "scene"
    else:
        canvas = themes.background(v["theme"], tribute).convert("RGBA")
        sq = to_square(art_bytes, pad_white=True)
        if bk.is_white_bg(sq):
            art, mode = bk.cutout(sq), "cutout"
            if th["dark"]:
                art = bk.defringe(art)
        else:
            # The model returned a scene rather than an isolated subject. Flood
            # cutting would shred its edges and a rounded rectangle reads as a
            # photo box pasted on the design, so it gets the theme's own frame.
            src = _crop_active(sq)
            if th.get("frame") == "arch":
                art, mode = bk.arch(src, ring=th["orn"]), "arch"
            else:
                art, mode = bk.medallion(src, ring=th["orn"]), "medallion"
        ok = _layout_hero(canvas, art, brief, th, mirror=bool(th.get("mirror")))

    notes = {"shaping": bool(ok), "theme": v["theme"], "mode": v["mode"],
             "art": mode, "tribute": tribute}
    out = io.BytesIO()
    canvas.convert("RGB").save(out, "JPEG", quality=93, optimize=True)
    return out.getvalue(), notes
