"""
Turn a verified calendar occasion into a creative brief + Instagram captions.

One LLM call produces everything the rest of the run needs: the Hindi headline
that gets overlaid on the artwork, the visual direction for the image model, and
both the Hindi and English captions with hashtags.

Tone correctness is the point of this module. The calendar already tells us
whether the occasion is a festival, a jayanti or a punyatithi; the prompt turns
that into the right words, so a remembrance never reads "Happy".
"""
from __future__ import annotations

import json
import re
from typing import Dict

import config
import llm

BRIEF_SYS = """You are a creative director for an Indian consumer brand's Instagram handle.
You write Hindi that is natural, correctly spelled and idiomatic — never machine-literal.
Answer with RAW JSON only: no markdown fences, no commentary."""

TONE_RULES = """TONE RULES (these are not negotiable):
- Festival / religious occasion -> warm, celebratory, devotional as appropriate to that faith.
- National day -> dignified and patriotic, not jingoistic.
- Jayanti (birth anniversary of someone DECEASED) -> remembrance and respect
  ("जयंती पर शत्-शत् नमन"). NEVER "Happy Birthday", NEVER "जन्मदिन मुबारक".
- Punyatithi / Shraddhanjali (death anniversary) -> somber tribute
  ("विनम्र श्रद्धांजलि"). NEVER any celebratory word, NEVER "शुभकामनाएं".
- Observance / awareness day -> light, useful, human.
Never use the word "Happy" or "शुभकामनाएं" for a tribute or remembrance occasion."""


GENERIC_RULES = """
THIS IS GENERIC DAILY CONTENT, not an event announcement. Phrase it as an everyday post:
- Good morning: occasion_hi is "सुप्रभात", prefix_hi is EMPTY, and suffix_hi is a day-wish such as
  "आपका दिन मंगलमय हो!" — never "की हार्दिक शुभकामनाएं" (you do not congratulate someone on a morning).
- Weekday deity: occasion_hi is ONLY the deity's name in Hindi ("श्री गणेश", "हनुमान जी",
  "शनि देव", "माँ लक्ष्मी"), prefix_hi is EMPTY or a short day word ("आज है"), and suffix_hi is a
  blessing that grammatically follows that name — "की कृपा आप पर बनी रहे". Never put day words
  like "शनिवार का आशीर्वाद" in occasion_hi: it will not join with the suffix.
"""


def _prompt(ev: Dict) -> str:
    warn = ""
    if ev.get("warnings"):
        warn = "\nCALENDAR WARNINGS: " + " | ".join(ev["warnings"])
    return f"""Build the creative brief for ONE Instagram post.

OCCASION: {ev.get('event', '')}
DATE: {ev.get('date', '')}
TYPE: {ev.get('type', '')}   CATEGORY: {ev.get('category', '')}
CURATED TONE: {ev.get('tone', '')}   OCCASION KIND: {ev.get('occasion', '')}
AUDIENCE: {ev.get('audience', '')}
EDITORIAL HOOK (from the calendar): {ev.get('hook', '')}
BACKGROUND NOTES: {ev.get('notes', '')[:400]}
DEITY (if any): {ev.get('deity', '')}{warn}

{TONE_RULES}
{GENERIC_RULES if ev.get('_generic') else ''}

The post is built from a FIXED brand template. You are filling in its slots, not designing a
layout. The template stacks, centred:

    <prefix>            small          e.g.  आप सभी को
    <occasion>          HUGE, two-tone e.g.  नाग पंचमी
    <suffix>            medium         e.g.  की हार्दिक शुभकामनाएं!
    ---- ornament ----
    <blessing>          small, 1-2 lines

The artwork is generated separately as a cutout on white, so describe a SINGLE SUBJECT, not a
scene and not a layout.

Return RAW JSON with exactly these keys:
{{
  "occasion_en": "<occasion name in English>",
  "occasion_hi": "<ONLY the name, in HINDI, 1-3 words. e.g. 'नाग पंचमी', 'रक्षा बंधन',
                   'जय श्री गणेश'. For a person, their NAME in Devanagari. It must NOT contain
                   blessing or greeting words — no कृपा, no शुभकामनाएं, no नमन, no आशीर्वाद —
                   those belong in suffix_hi, and repeating them reads as a duplication
                   ('शनिदेव कृपा' + 'की कृपा आप पर बनी रहे').>",
  "prefix_hi": "<short lead-in line, usually 'आप सभी को'. EMPTY STRING for a tribute.>",
  "suffix_hi": "<the line that follows the name. Festival: 'की हार्दिक शुभकामनाएं!'.
                 Jayanti of someone deceased: 'जयंती पर शत्-शत् नमन'.
                 Punyatithi: 'पुण्यतिथि पर विनम्र श्रद्धांजलि'. MAX 5 words.

                 HARD RULE: occasion_hi and suffix_hi are printed one under the other and are
                 READ AS ONE SENTENCE. They must be grammatical when joined.
                   good:  'रक्षा बंधन' + 'की हार्दिक शुभकामनाएं!'
                   good:  'शनि देव'    + 'की कृपा आप पर बनी रहे'
                   BAD:   'शनिवार का आशीर्वाद' + 'की कृपा आप पर बनी रहे'  (ungrammatical)
                   BAD:   'सुप्रभात' + 'की हार्दिक शुभकामनाएं!'            (nonsense)
                 Read the two aloud together before answering. If they do not join cleanly,
                 change occasion_hi to a plain name so that they do.>",
  "blessing_hi": "<one warm closing line in Hindi, MAX 14 words. For a tribute, a line of
                   remembrance instead — never a blessing for prosperity.>",
  "quote_hi": "<ONLY for a good-morning or generic motivational post: a short Hindi quote or
                suvichar, 1-2 lines, MAX 20 words, that a person would actually forward. Real
                sentiment, not a fortune cookie. EMPTY STRING for every other kind of occasion.>",
  "show_person": <true ONLY if this occasion honours a specific DECEASED public figure whose
                  portrait belongs on the post (a national leader's jayanti/punyatithi).
                  false for festivals, observances, and for anyone still living.>,
  "person_name_en": "<that person's full name in English, for the illustrator. Empty otherwise.>",
  "portrait_concept": "<if show_person: 2-3 sentences describing a dignified portrait. LEAD WITH
                        THE IDENTIFYING FEATURES a person would recognise them by — headwear
                        (Tilak's red pagdi, Nehru's cap, Ambedkar's suit and spectacles), facial
                        hair (Tilak's thick white moustache), spectacles, build, age, and the era's
                        clothing. A generic old man in a dhoti is a failed portrait. Then the
                        setting and symbols around them. Empty otherwise.>",
  "context": "<one line: what this occasion actually marks>",
  "mood": "<3-6 adjectives for the artwork's emotional register>",
  "visual_concept": "<2-3 sentences describing ONE subject to draw, isolated on white:
                      what it is, its materials, how it is lit. Concrete and visual.>",
  "motifs": "<comma-separated concrete objects/symbols in that subject>",
  "palette": "<the colour direction in a short phrase>",
  "avoid": "<what must not appear — wrong iconography, clichés, anything disrespectful>",
  "caption_hi": "<Instagram caption in HINDI, 2-4 short lines, warm and human, may use 1-3 emoji.
                  No hashtags here.>",
  "caption_en": "<the English caption, 2-4 short lines. Not a literal translation — write it
                  natively for an English-reading Indian audience. May use 1-3 emoji. No hashtags.>",
  "hashtags": ["<8-12 relevant hashtags, mixed Hindi-transliterated and English, no # symbol>"],
  "tone": "<one of: festive|devotional|patriotic|remembrance|tribute|awareness|love>",
  "needs_human_check": <true if anything about this occasion is uncertain or sensitive, else false>,
  "check_reason": "<why, if needs_human_check is true, else empty string>"
}}"""


def _fallback(ev: Dict) -> Dict:
    """Deterministic brief so a failed LLM call never blocks the day's run."""
    name = ev.get("event", "आज का दिन")
    tribute = ev.get("tone") == "tribute_somber" or "punyatithi" in name.lower()
    return {
        "occasion_en": name,
        "occasion_hi": "",
        "prefix_hi": "" if tribute else "आप सभी को",
        "suffix_hi": "विनम्र श्रद्धांजलि" if tribute else "की हार्दिक शुभकामनाएं!",
        "blessing_hi": "",
        "quote_hi": "",
        "show_person": False,
        "person_name_en": "",
        "portrait_concept": "",
        "muted": tribute,
        "context": ev.get("notes", "")[:160],
        "mood": "restrained, respectful" if tribute else "warm, festive",
        "visual_concept": f"A respectful symbolic composition for {name}.",
        "motifs": "diya, marigold" if not tribute else "white flowers, single lamp",
        "palette": "muted greys and white" if tribute else "saffron and gold",
        "avoid": "text, celebration" if tribute else "text",
        "caption_hi": name,
        "caption_en": name,
        "hashtags": ["india", "festival"] if not tribute else ["shraddhanjali"],
        "tone": "tribute" if tribute else "festive",
        "needs_human_check": True,
        "check_reason": "Brief was generated by the offline fallback, not the model — review copy.",
        "_fallback": True,
    }


def build(ev: Dict) -> Dict:
    """Creative brief + captions for a calendar occasion. Never raises."""
    if not getattr(llm, "ENABLED", False):
        return _fallback(ev)
    try:
        raw = llm.text(_prompt(ev), system=BRIEF_SYS, timeout=90)
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return _fallback(ev)
        b = json.loads(m.group(0))
    except Exception as exc:  # noqa: BLE001
        print(f"[brief] failed, using fallback: {exc}", flush=True)
        return _fallback(ev)

    tags = b.get("hashtags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace("#", "").split() if t.strip()]
    b["hashtags"] = [str(t).lstrip("#").strip()[:40] for t in tags if str(t).strip()][:12]

    for k in ("occasion_hi", "prefix_hi", "suffix_hi", "blessing_hi", "quote_hi",
              "caption_hi", "caption_en", "occasion_en", "person_name_en", "portrait_concept"):
        b[k] = str(b.get(k, "")).strip()

    # Palette decision, made deterministically from the OCCASION rather than from
    # the model's tone word. A Punyatithi (death anniversary) is muted. A Jayanti
    # is a celebration of the person's birth and stays festive — greying it out
    # reads as mourning on the wrong day. The copy stays respectful either way.
    name = (ev.get("event", "") + " " + ev.get("occasion", "") + " " +
            ev.get("category", "") + " " + ev.get("type", "")).lower()
    is_punya = any(k in name for k in
                   ("punyatithi", "punya tithi", "death anniversary", "shraddhanjali",
                    "shraddhanjali", "barsi", "smriti diwas"))
    is_jayanti = ("jayanti" in name or "birth anniversary" in name) and not is_punya
    b["muted"] = bool(is_punya or (ev.get("tone") == "tribute_somber" and not is_jayanti))

    # A likeness only goes out for someone the calendar agrees is no longer living;
    # an AI portrait of a living person on a "jayanti" post is the wrong image AND
    # the wrong framing.
    living = (ev.get("warnings") and any("LIVING" in w for w in ev["warnings"]))
    b["show_person"] = bool(b.get("show_person")) and not living and bool(b.get("portrait_concept"))
    if b["show_person"]:
        b["needs_human_check"] = True
        b["likeness_of"] = b.get("person_name_en", "")
        b["check_reason"] = ((b.get("check_reason", "") + " | ") if b.get("check_reason") else "") + \
            "Generated likeness of a real person — check the portrait actually looks like them."
    b["needs_human_check"] = bool(b.get("needs_human_check")) or bool(ev.get("warnings"))
    if ev.get("warnings") and not b.get("check_reason"):
        b["check_reason"] = " | ".join(ev["warnings"])

    # Safety net for the one-sentence rule. The model keeps the occasion word in
    # BOTH halves — "गांधी जयंती" + "की जयंती पर शत्-शत् नमन" prints as a stutter.
    # Any occasion word the suffix already carries is dropped from the name.
    for kw in ("जयंती", "पुण्यतिथि", "जन्मदिन", "दिवस", "पर्व"):
        if kw in b["occasion_hi"] and kw in b["suffix_hi"]:
            b["occasion_hi"] = " ".join(w for w in b["occasion_hi"].split() if w != kw)
    occ_words = b["occasion_hi"].split()
    suf_words = b["suffix_hi"].split()
    if len(occ_words) > 1 and suf_words and occ_words[-1] == suf_words[0]:
        b["occasion_hi"] = " ".join(occ_words[:-1])
    b["occasion_hi"] = b["occasion_hi"].strip()

    # occasion_hi is the hero of the template — without it there is no post
    if not b["occasion_hi"]:
        b["occasion_hi"] = (ev.get("event", "") or "").split("(")[0].strip()
    if not b["suffix_hi"]:
        b["suffix_hi"] = _fallback(ev)["suffix_hi"]
    return b


def caption_text(brief: Dict, lang: str = "hi") -> str:
    """Final caption as it would be posted: body + hashtag block."""
    body = brief.get("caption_hi" if lang == "hi" else "caption_en", "")
    tags = " ".join("#" + t.replace(" ", "") for t in brief.get("hashtags", []))
    handle = config.BRAND_HANDLE
    parts = [body.strip()]
    if tags:
        parts.append(tags)
    if handle:
        parts.append(handle)
    return "\n\n".join(p for p in parts if p)
