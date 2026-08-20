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

_ISLAMIC = """ISLAMIC OCCASIONS (Eid, Milad-un-Nabi, Muharram, Ramzan): never depict the Prophet
or any human religious figure. Do NOT render Arabic calligraphy either — it is text, it comes out
malformed, and it trips the no-text rule. Build the image from ARCHITECTURE AND OBJECTS instead:
a mosque dome and minarets against dusk, a lit crescent moon and star, hanging metal lanterns
(fanoos), an ornate carved arch or jali screen, geometric girih tilework, dates, roses, a prayer
mat, strings of lights. Deep emerald green, teal, ivory and gold. Serene and reverent, festive
without frivolity."""

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

BACKGROUND (critical, this is the single most important instruction): SEAMLESS PURE WHITE
(#FFFFFF) filling every pixel that is not the subject itself.

Think e-commerce packshot on an infinite white sweep. Specifically FORBIDDEN:
  - any surface the subject rests on — no table, no cloth, no plate, no cushion, no ground
  - any room, wall, window, sky, backdrop or setting
  - any gradient, tint, texture, paper grain, vignette or coloured light on the background
  - any drop shadow, contact shadow or reflection falling onto the background
  - any border, frame, edge or corner decoration
The subject FLOATS on empty white. If the concept normally implies a setting, drop the setting
entirely and render only the object itself. A background that is off-white, cream, grey or
softly lit counts as a FAILURE.

FRAMING: compose SQUARE, 1:1. A wide letterbox composition leaves the subject short and stranded
when it is placed into a side column.

SUBJECT: one clear, beautifully rendered focal subject, centred, filling most of the frame with a
comfortable margin of white around it. Rich detail, premium finish, believable lighting and depth.

{no_text}

{people}

{culture}

{islamic}"""

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

{culture}

{islamic}"""


VARIANTS = [
    {"name": "Ivory botanical", "mode": "subject", "theme": "ivory-botanical",
     "angle": "SUBJECT ANGLE: ONE physical object you could hold or place on a table — the single "
              "most evocative object of this occasion, rendered large and detailed.",
     "direction": "STYLE: photorealistic, clean daylight, crisp real textures, premium "
                  "product-photography finish on pure white. Fresh and airy."},
    {"name": "Scene card", "mode": "scene", "theme": "scene-card", "zone": "LEFT HALF",
     "opposite": "right half",
     "angle": "SUBJECT ANGLE: a PLACE — the setting where this occasion actually happens, with "
              "architecture and depth receding behind the subject.",
     "direction": "STYLE: photorealistic and cinematic — soft depth of field, warm golden hour "
                  "light, foliage or florals framing the top-right, a real Indian setting with "
                  "genuine depth behind the subject."},
    {"name": "Royal maroon", "mode": "subject", "theme": "royal-maroon",
     "angle": "SUBJECT ANGLE: an ORNAMENT or emblem of the occasion — a decorative crafted piece, "
              "medallion, lamp or vessel, treated like a jewellery photograph.",
     "direction": "STYLE: opulent and jewel-like — heavy gold filigree, intricate metalwork, "
                  "gemstone accents, dramatic rim lighting and deep shadow. Regal and ornate, "
                  "isolated on pure white."},
    {"name": "Painted scene", "mode": "scene", "theme": "scene-wash", "zone": "BOTTOM HALF",
     "opposite": "top half",
     "angle": "SUBJECT ANGLE: a NIGHT SCENE with atmosphere — sky, lamps, distant silhouettes, "
              "people or life in the middle distance. Mood over object.",
     "direction": "STYLE: rich hand-painted illustration at night or dusk — luminous lamps and "
                  "moonlight, decorative border motifs, deep blues and violets with warm lamp "
                  "glow. Keep the upper-centre clear of detail: a logo sits there."},
    {"name": "Saffron graphic", "mode": "subject", "theme": "saffron-sunburst",
     "angle": "SUBJECT ANGLE: a SYMBOL reduced to its simplest recognisable shape — one bold "
              "silhouette, no ornament, readable at a glance.",
     "direction": "STYLE: bold flat-graphic vector treatment — clean geometric shapes, strong "
                  "silhouette, minimal detail, confident poster art. High contrast, few colours, "
                  "isolated on pure white."},
    # ── second set: what "regenerate five different" serves ──
    {"name": "Midnight teal", "mode": "subject", "theme": "midnight-teal",
     "angle": "SUBJECT ANGLE: an offering or ritual item arranged for the occasion — what a "
              "person actually holds, lights or gives that day.",
     "direction": "STYLE: photorealistic, low-key lighting, a single warm light source raking "
                  "across the subject, deep shadow. Isolated on pure white."},
    {"name": "Blush rose", "mode": "subject", "theme": "blush-rose",
     "angle": "SUBJECT ANGLE: FLOWERS and soft natural material tied to the occasion — a garland, "
              "petals, a bloom, fabric.",
     "direction": "STYLE: soft daylight, delicate and airy, gentle shadows, fine texture. "
                  "Isolated on pure white."},
    {"name": "Paper craft", "mode": "subject", "theme": "paper-craft",
     "angle": "SUBJECT ANGLE: the occasion built from LAYERED PAPER — a paper-cut diorama of its "
              "most recognisable shape.",
     "direction": "STYLE: layered paper-craft illustration, visible cut edges and soft drop "
                  "shadows between layers, warm muted palette. Isolated on pure white."},
    {"name": "Emerald clean", "mode": "subject", "theme": "emerald-clean",
     "angle": "SUBJECT ANGLE: a single ICON of the occasion, drawn simply and centred, no scene.",
     "direction": "STYLE: clean modern 3D render, smooth matte surfaces, soft studio light, "
                  "restrained palette. Isolated on pure white."},
    {"name": "Violet dusk", "mode": "scene", "theme": "violet-dusk", "zone": "BOTTOM HALF",
     "opposite": "top half",
     "angle": "SUBJECT ANGLE: the sky and the horizon at dusk, with the occasion's silhouette "
              "against it.",
     "direction": "STYLE: painterly dusk illustration, violet and rose sky, silhouettes, drifting "
                  "light. Keep the upper-centre clear of detail: a logo sits there."},
    {"name": "Sky ivory", "mode": "subject", "theme": "sky-ivory",
     "angle": "SUBJECT ANGLE: something in MOTION or in the air for this occasion — a kite, birds, "
              "smoke, water, cloth caught mid-air.",
     "direction": "STYLE: bright airy photography, pale cool daylight, lots of white space, crisp "
                  "edges. Isolated on pure white."},
    {"name": "Charcoal gold", "mode": "subject", "theme": "charcoal-gold",
     "angle": "SUBJECT ANGLE: a fine line-art emblem of the occasion, as if engraved.",
     "direction": "STYLE: delicate gold line engraving on nothing — thin metallic strokes, no "
                  "fill, jewellery-catalogue precision. Isolated on pure white."},
    {"name": "Frosted scene", "mode": "scene", "theme": "scene-frost", "zone": "LEFT HALF",
     "opposite": "right half",
     "angle": "SUBJECT ANGLE: hands and human detail — the occasion as people actually perform it, "
              "close in.",
     "direction": "STYLE: warm documentary photography, natural light, shallow focus, real texture "
                  "and imperfection."},
    # ── third set ──
    {"name": "Ivory close-up", "mode": "subject", "theme": "ivory-botanical",
     "angle": "SUBJECT ANGLE: an extreme CLOSE-UP of one detail — texture, grain, weave, flame.",
     "direction": "STYLE: macro photography, exquisite detail, shallow depth. Isolated on white."},
    {"name": "Maroon still life", "mode": "subject", "theme": "royal-maroon",
     "angle": "SUBJECT ANGLE: a STILL LIFE — several related objects of the occasion arranged "
              "together like a painting.",
     "direction": "STYLE: old-master still life lighting, deep shadow, rich colour. Isolated on white."},
    {"name": "Saffron pattern", "mode": "subject", "theme": "saffron-sunburst",
     "angle": "SUBJECT ANGLE: a bold folk-art motif of the occasion, drawn in a regional Indian "
              "craft idiom (Madhubani, Warli, Pattachitra, Gond).",
     "direction": "STYLE: traditional Indian folk illustration, flat colour, confident linework. "
                  "Isolated on pure white."},
    {"name": "Teal architecture", "mode": "subject", "theme": "midnight-teal",
     "angle": "SUBJECT ANGLE: ARCHITECTURE of the occasion — a dome, arch, gateway or shrine, "
              "rendered as a single object.",
     "direction": "STYLE: architectural render, dramatic uplighting, fine ornament. Isolated on white."},
    {"name": "Card scene warm", "mode": "scene", "theme": "scene-card", "zone": "LEFT HALF",
     "opposite": "right half",
     "angle": "SUBJECT ANGLE: a table or threshold prepared for the occasion, seen from just above.",
     "direction": "STYLE: warm overhead photography, natural light, real props and texture."},
]



def variant(i: int) -> dict:
    v = dict(VARIANTS[i % len(VARIANTS)])
    v["idx"] = i
    return v


def pool_size() -> int:
    return len(VARIANTS)


def system_for(v: dict, allow_likeness: bool = False) -> str:
    people = _PEOPLE_ALLOWED if allow_likeness else _PEOPLE_SYMBOLIC
    if v["mode"] == "scene":
        return SCENE_SYSTEM.format(no_text=_NO_TEXT, people=people, culture=_CULTURE,
                                   islamic=_ISLAMIC,
                                   zone=v.get("zone", "LEFT HALF"),
                                   opposite=v.get("opposite", "right half"))
    return SUBJECT_SYSTEM.format(no_text=_NO_TEXT, people=people, culture=_CULTURE,
                                 islamic=_ISLAMIC)


# For a person, the object angles fight the portrait: asked for "ONE physical
# object" AND "a dignified portrait of Rajiv Gandhi", the model resolves the
# conflict by putting the face INSIDE an object — a framed tablet, a jewelled
# medallion, a vector emblem. These angles are portrait-shaped instead.
PERSON_ANGLES = [
    "FRAMING: a formal portrait, head and shoulders, plain and dignified. No frame, no medallion, "
    "no object around them — just the person.",
    "FRAMING: the person in their working world — at a desk, among people, in the building or "
    "landscape they are associated with. Environmental portrait, three-quarter length.",
    "FRAMING: NO FACE AT ALL. Their emblem and belongings only — the objects that stand for their "
    "life and work, arranged as a still life.",
    "FRAMING: the person small against a large national setting at dusk — architecture, sky, "
    "distance. Atmosphere over likeness.",
    "FRAMING: a bold poster portrait, high-contrast and graphic, in the visual language of a "
    "political poster. Strong silhouette, few colours.",
]


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
    if b.get("show_person"):
        # index is carried on the variant so the person angles stay in step
        bits.append(PERSON_ANGLES[v.get("idx", 0) % len(PERSON_ANGLES)])
        bits.append("Do NOT enclose the face in a frame, tablet, screen, medallion or ornamental "
                    "disc — a former head of government rendered as a jewelled icon reads as "
                    "religious, not civic. No forehead tilak or devotional marks unless the person "
                    "actually wore them. No circuit-board or technology motifs unless the brief "
                    "explicitly asks for them.")
    elif v.get("angle"):
        bits.append(v["angle"] + " Do NOT default to a geometric medallion or mandala unless this "
                    "angle calls for it — five near-identical patterned discs is a failed set.")
    bits.append(v["direction"])
    if v["mode"] == "scene":
        bits.append(f"Keep the {v.get('zone', 'LEFT HALF')} calm for type. NO text in the image.")
    else:
        bits.append("Background must be pure empty WHITE. NO text anywhere in the image.")
    return "\n".join(bits)
