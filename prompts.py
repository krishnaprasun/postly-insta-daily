"""
Image prompts for the daily Instagram post.

KEY DESIGN CHOICE — the image model draws NO TEXT.
Gemini garbles Devanagari conjuncts often enough that a festival post can go out
misspelled. So the model produces artwork only, with a deliberately calm lower
band, and imaging.py overlays the Hindi headline with CoreText/Noto shaping. The
text is then correct 100% of the time and typographically consistent across the
grid, which also makes the feed look like one brand rather than 365 one-offs.
"""
from __future__ import annotations

SYSTEM_INSTRUCTION = """You are a senior art director producing artwork for an Indian consumer
brand's INSTAGRAM feed post. Square 1:1 composition.

ABSOLUTE RULE — NO TEXT OF ANY KIND. Do not draw letters, words, numbers, captions, logos,
watermarks, signatures or calligraphy in ANY script (Devanagari, Latin, or other). Not even
decorative or blurred lettering. All text is added afterwards by the design system. Artwork that
contains text is rejected and regenerated. Do not draw any UI, frame, border ribbon meant to hold
text, or empty speech bubble.

COMPOSITION FOR TEXT OVERLAY: keep the BOTTOM 35% of the square visually calm — no faces, no key
subject detail, no busy pattern there. A gradient, sky, water, soft bokeh, fabric, rangoli edge or
plain colour wash is ideal. The headline is placed there later, so detail in that band gets covered.
Put the hero subject in the upper two-thirds.

QUALITY: premium, modern, editorial-grade Indian design. Rich but harmonious colour. Real depth and
lighting, not flat clipart. Think a well-funded brand's festival post, not a stock greeting card.

CULTURAL ACCURACY: depict deities, rituals, attire, instruments and motifs correctly and
respectfully for the specific occasion. Never mix iconography across religions. Never place a deity
in a demeaning, casual or commercial pose.

PEOPLE: you may show ordinary people celebrating (faces are fine). NEVER depict a real, named public
figure's face — for a person-centred occasion, use symbolic imagery (their emblem, a khadi/charkha,
flowers, a lit diya, their field of work) instead of their likeness.

TRIBUTES: for a punyatithi / shraddhanjali / remembrance occasion the mood must be restrained and
somber — muted palette, white flowers, a single lit lamp, quiet space. No celebration, no confetti,
no bright festive colour, no fireworks."""


# Four distinct art directions so the day's variants are genuinely different
# choices rather than four renders of the same idea.
VARIANTS = [
    ("Illustrated",
     "ART DIRECTION: rich hand-illustrated style, warm traditional Indian palette (saffron, deep "
     "maroon, gold). Ornamental but not cluttered. Hero subject large in the upper two-thirds, "
     "soft glow, calm gradient wash across the bottom band."),
    ("Photographic",
     "ART DIRECTION: photorealistic, cinematic depth of field, natural warm light, authentic Indian "
     "setting and real textures. Shallow focus so the bottom band falls into soft bokeh."),
    ("Minimal modern",
     "ART DIRECTION: bold minimal graphic design, lots of negative space, a single strong symbolic "
     "motif, flat contemporary palette with one accent colour. Clean and premium, gallery-poster "
     "feel. Bottom band left as plain colour."),
    ("Ornate festive",
     "ART DIRECTION: intricate decorative composition — mandala/rangoli geometry, gold filigree, "
     "diyas or marigold detailing, deep jewel tones (emerald, indigo, ruby) with metallic accents. "
     "Dense ornament above, fading to a calm dark wash across the bottom band."),
]


def variant(i: int):
    """(name, art-direction line) for variant i."""
    return VARIANTS[i % len(VARIANTS)]


def build_prompt(brief: dict, art_direction: str) -> str:
    """Compose the per-variant user prompt from the creative brief."""
    b = brief
    bits = [
        f"OCCASION: {b.get('occasion_en', '')}",
        f"WHAT IT MARKS: {b.get('context', '')}",
        f"MOOD: {b.get('mood', '')}",
        f"VISUAL CONCEPT: {b.get('visual_concept', '')}",
        f"KEY MOTIFS TO INCLUDE: {b.get('motifs', '')}",
        f"COLOUR DIRECTION: {b.get('palette', '')}",
    ]
    if b.get("avoid"):
        bits.append(f"MUST AVOID: {b['avoid']}")
    if b.get("tone") in ("tribute_somber",):
        bits.append("THIS IS A TRIBUTE — restrained and somber, absolutely no celebration.")
    bits.append(art_direction)
    bits.append("Remember: NO TEXT anywhere in the image. Keep the bottom 35% calm and uncluttered.")
    return "\n".join(bits)
