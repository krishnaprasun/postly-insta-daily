"""
Artwork prompts for the daily Instagram post.

The model does NOT produce the finished post. It produces ONE artwork element —
the subject, on a plain white background — which imaging.py cuts out and drops
into the Postly brand template (logo, two-tone Hindi headline, blessing line,
app-promo footer).

Two reasons it works this way:
  * Gemini garbles Devanagari conjuncts, so all text is drawn by us.
  * The brand template has a fixed layout and palette. Letting the model invent
    the whole composition produced good images that looked like someone else's
    brand — the reference creatives are a specific, repeatable template.
"""
from __future__ import annotations

SYSTEM_INSTRUCTION = """You are producing ONE isolated artwork element for an Indian brand's
social template. You are NOT designing a finished post.

BACKGROUND (critical): pure plain WHITE (#FFFFFF), completely empty. No scene, no room, no floor,
no gradient, no texture, no border, no vignette, no shadow cast onto the background. The subject
must sit on clean white like a product cutout, so it can be composited onto a template.

ABSOLUTE RULE — NO TEXT OF ANY KIND. No letters, words, numbers, calligraphy, captions, logos,
watermarks or signatures in any script. Not even decorative or blurred lettering. Artwork with
text is rejected and regenerated.

FRAMING: compose SQUARE, 1:1. A wide letterbox composition leaves the subject short and stranded
when it is placed into a side column of the template.

SUBJECT: one clear, beautifully rendered focal subject, centred, filling most of the frame with a
comfortable margin of white around it. Rich detail, premium finish, believable lighting and depth.
Think a high-end festival illustration, not flat clipart and not a stock greeting card.

CULTURAL ACCURACY: depict deities, rituals, attire, instruments, flowers and motifs correctly and
respectfully for the specific occasion. Never mix iconography across religions. Never place a deity
in a casual, demeaning or commercial pose.

PEOPLE: NEVER depict a real, named public figure's face or likeness. For a person-centred occasion
use symbolic imagery instead — a charkha, khadi, a lit lamp, their field of work, national symbols,
flowers. Ordinary unnamed people are fine when the occasion calls for it.

TRIBUTES: for a punyatithi / shraddhanjali the mood is restrained — white flowers, a single lit
lamp, muted tones, quiet space. No celebration, no bright festive colour, no fireworks."""


# Four art directions. All render on white; they differ in how the subject is treated,
# so the day's four variants are genuinely different choices.
VARIANTS = [
    ("Photographic",
     "STYLE: photorealistic, cinematic studio lighting, shallow depth of field, real textures and "
     "materials. Product-photography finish on pure white."),
    ("Illustrated",
     "STYLE: rich hand-illustrated digital painting, warm saffron/gold/maroon palette, painterly "
     "detail and soft glow. Isolated on pure white."),
    ("Ornate",
     "STYLE: intricate decorative treatment — mandala/rangoli geometry, gold filigree, marigold and "
     "diya detailing, deep jewel tones with metallic accents. Isolated on pure white."),
    ("Minimal",
     "STYLE: bold minimal graphic treatment, one strong symbolic motif, flat contemporary shapes, "
     "restrained palette with a single accent colour. Generous white space."),
]


def variant(i: int):
    """(name, style line) for variant i."""
    return VARIANTS[i % len(VARIANTS)]


def build_prompt(brief: dict, style: str) -> str:
    """Compose the per-variant artwork prompt from the creative brief."""
    b = brief
    bits = [
        f"OCCASION: {b.get('occasion_en', '')}",
        f"WHAT IT MARKS: {b.get('context', '')}",
        f"SUBJECT TO DRAW: {b.get('visual_concept', '')}",
        f"MOTIFS TO INCLUDE: {b.get('motifs', '')}",
        f"MOOD: {b.get('mood', '')}",
        f"COLOUR DIRECTION: {b.get('palette', '')}",
    ]
    if b.get("avoid"):
        bits.append(f"MUST AVOID: {b['avoid']}")
    if b.get("tone") in ("tribute", "tribute_somber", "remembrance"):
        bits.append("THIS IS A TRIBUTE — restrained and somber, absolutely no celebration.")
    bits.append(style)
    bits.append("Remember: the background must be pure empty WHITE, and there must be NO text "
                "anywhere in the image.")
    return "\n".join(bits)
