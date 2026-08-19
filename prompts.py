"""
Artwork prompts.

Each variant asks the model for a DIFFERENT KIND of image, because four renders
of the same brief on the same canvas produced four posts that read as one post.
Two modes:

  * "subject" — one isolated subject on pure white, cut out and floated on a
    decorated brand canvas.
  * "scene"   — a full designed backdrop with depth (foliage, temple, bokeh,
    fabric), used full-bleed with the type laid over it.

Text is never drawn by the model; imaging.py shapes all Devanagari.
"""
from __future__ import annotations

_NO_TEXT = """ABSOLUTE RULE — NO TEXT OF ANY KIND. No letters, words, numbers, calligraphy, captions,
logos, watermarks or signatures in any script. Not even decorative or blurred lettering. Artwork
containing text is rejected and regenerated."""

_CULTURE = """CULTURAL ACCURACY: depict deities, rituals, attire, instruments, flowers and motifs
correctly and respectfully for the specific occasion. Never mix iconography across religions.
Never place a deity in a casual, demeaning or commercial pose.

TRIBUTES: for a punyatithi / shraddhanjali the mood is restrained — white flowers, a single lit
lamp, muted tones, quiet space. No celebration, no bright festive colour, no fireworks."""

# Real people: allowed, deliberately, for DECEASED Indian national figures — a
# Gandhi Jayanti post without Gandhi is a worse post. Living people are still
# off-limits, and the review page flags likeness posts for a human look.
_PEOPLE_ALLOWED = """THE PERSON: this occasion honours a specific deceased Indian national figure.
Depict them faithfully and with dignity — a recognisable, respectful portrait in their well-known
appearance, attire and era. Get the recognisable details right (spectacles, headwear, khadi, staff,
posture). Dignified expression, never caricature, never a cartoon, never a celebratory party
setting. If you cannot render a faithful likeness, draw their strongest symbol instead
(charkha, khadi, a lit lamp, their emblem) rather than an inaccurate face."""

_PEOPLE_SYMBOLIC = """PEOPLE: never depict a real, named public figure's face or likeness. Use
symbolic imagery instead — an emblem, a charkha, khadi, a lit lamp, their field of work, national
symbols, flowers. Ordinary unnamed people are fine when the occasion calls for it."""

SUBJECT_SYSTEM = """You are producing ONE isolated artwork element for an Indian brand's social
template. You are NOT designing a finished post.

BACKGROUND (critical): pure plain WHITE (#FFFFFF), completely empty. No scene, no room, no floor,
no gradient, no texture, no border, no vignette, no shadow cast onto the background. The subject
must sit on clean white like a product cutout, so it can be composited onto a template.

FRAMING: compose SQUARE, 1:1. A wide letterbox composition leaves the subject short and stranded
when it is placed into a side column.

SUBJECT: one clear, beautifully rendered focal subject, centred, filling most of the frame with a
comfortable margin of white around it. Rich detail, premium finish, believable lighting and depth.

{no_text}

{people}

{culture}"""

SCENE_SYSTEM = """You are producing a full BACKDROP image for an Indian brand's Instagram post.
Square 1:1. The brand lays its logo and Hindi headline over this image afterwards.

COMPOSITION FOR TYPE: the {zone} of the frame must stay visually CALM — soft gradient, wash,
bokeh, plain wall, sky or fabric. No faces, no key detail, no busy pattern there, because type
goes on top of it. Put the hero subject in the opposite {opposite}.

DEPTH AND RICHNESS: this is a designed backdrop, not an empty background. Build real atmosphere —
layered depth, foliage or florals framing an edge, warm practical light, a soft architectural or
devotional setting, delicate particles or bokeh. Premium editorial finish, never flat clipart.

{no_text}

{people}

{culture}"""


VARIANTS = [
    {"name": "Floral cutout", "mode": "subject", "theme": "floral-cream",
     "direction": "STYLE: photorealistic, warm natural light, rich real textures, premium "
                  "product-photography finish on pure white."},
    {"name": "Scene card", "mode": "scene", "theme": "scene-card", "zone": "LEFT HALF",
     "opposite": "right half",
     "direction": "STYLE: photorealistic and cinematic — soft depth of field, warm golden light, "
                  "foliage or florals framing the top-right, a devotional or festive Indian "
                  "setting with real depth behind the subject."},
    {"name": "Deep festive", "mode": "subject", "theme": "deep-festive",
     "direction": "STYLE: ornate and jewel-like — gold filigree, intricate detailing, marigold and "
                  "diya accents, deep saturated colour, dramatic rim lighting on pure white."},
    {"name": "Painted scene", "mode": "scene", "theme": "scene-wash", "zone": "BOTTOM HALF",
     "opposite": "top half",
     "direction": "STYLE: rich hand-painted illustration — luminous traditional Indian palette, "
                  "decorative border motifs, mandala or rangoli geometry worked into the setting, "
                  "painterly glow and ornament."},
]


def variant(i: int) -> dict:
    return VARIANTS[i % len(VARIANTS)]


def system_for(v: dict, allow_likeness: bool = False) -> str:
    people = _PEOPLE_ALLOWED if allow_likeness else _PEOPLE_SYMBOLIC
    if v["mode"] == "scene":
        return SCENE_SYSTEM.format(no_text=_NO_TEXT, people=people, culture=_CULTURE,
                                   zone=v.get("zone", "LEFT HALF"),
                                   opposite=v.get("opposite", "right half"))
    return SUBJECT_SYSTEM.format(no_text=_NO_TEXT, people=people, culture=_CULTURE)


def build_prompt(brief: dict, v: dict) -> str:
    b = brief
    subject = b.get("portrait_concept") if b.get("show_person") else b.get("visual_concept")
    bits = [
        f"OCCASION: {b.get('occasion_en', '')}",
        f"WHAT IT MARKS: {b.get('context', '')}",
        f"{'SCENE TO BUILD' if v['mode'] == 'scene' else 'SUBJECT TO DRAW'}: {subject or ''}",
        f"MOTIFS TO INCLUDE: {b.get('motifs', '')}",
        f"MOOD: {b.get('mood', '')}",
        f"COLOUR DIRECTION: {b.get('palette', '')}",
    ]
    if b.get("show_person") and b.get("person_name_en"):
        bits.append(f"THE PERSON TO DEPICT: {b['person_name_en']} — faithful, dignified likeness.")
    if b.get("avoid"):
        bits.append(f"MUST AVOID: {b['avoid']}")
    if b.get("tone") in ("tribute", "tribute_somber", "remembrance"):
        bits.append("THIS IS A TRIBUTE — restrained and somber, absolutely no celebration.")
    bits.append(v["direction"])
    if v["mode"] == "scene":
        bits.append(f"Keep the {v.get('zone', 'LEFT HALF')} calm for type. NO text in the image.")
    else:
        bits.append("Background must be pure empty WHITE. NO text anywhere in the image.")
    return "\n".join(bits)
