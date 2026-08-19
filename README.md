# Postly — daily Instagram post system

Every morning this picks the Indian occasion worth posting about, generates 4
square variants with the Hindi headline already on them, and sends you one link.
You pick one. Nothing reaches Instagram until you do.

```
07:00 IST   calendar → occasion → creative brief → 4 variants → review link
you         open link, pick one, hit post (or download + post by hand)
```

## Why the calendar, not the model

Asked directly what falls on 19 Aug 2026, the text model answered "Raksha Bandhan
and Janmashtami". The real dates are **28 Aug** and **4 Sep**. Lunar-calendar
dates are exactly where an LLM is least reliable, and a wrong-day festival post
is the worst failure this system could have.

So the split in `events.py` is deliberate and should not be undone:

* **`data/calendar/postly_calendar_clean.csv` is the only source of dates.** It's
  the human-QA'd calendar from the Creative Tool, with Priority/Tier/Tone/
  Sensitivity/Lock/QA-flag columns.
* **The LLM only ranks** the day's already-verified occasions for Instagram
  suitability. It is never asked when something falls.

Coverage today is **2026-05-01 → 2028-04-30**. Past the end, runs fail loudly
rather than guessing — refresh with `python refresh_calendar.py`.

### What gets picked, and what doesn't

Film and TV anniversaries are dropped outright. Person-based occasions are
restricted to **Indian leaders** — the calendar's `National Icon` and `Politics`
categories only, which cuts ~10,000 long-tail Figure rows (Padma Shri awardees,
actors, sportspeople, foreign luminaries) that exist for in-app status content.

The `Politics` category still mixes Indian statesmen with foreign politicians
(Mike Pence, João de Castro) and carries no marker separating them, so
`events.verify_leaders()` asks the model one narrow question per person — Indian?
deceased? a leader? — and drops the rest. That is a checkable fact about a named
person, not a date question.

### Quiet days

Roughly a third of dates carry nothing a mainstream audience marks. Those days
get honest generic content instead of a dressed-up obscure anniversary: half the
variants are the **weekday's deity** (Somwar–Shiv, Mangalwar–Hanuman, Budhwar–
Ganesh …) and half are a **good-morning** post, so there is still a real choice.
The run is flagged, and **Skip today** is one click.

## Four themes, so the day's options are actually different

Early on, all four variants shared one cream canvas and read as the same post
four times — useless for choosing. Each variant now gets its own ground, palette
and decoration (`themes.py`), and asks the model for a different *kind* of image
(`prompts.py`):

Five templates a day, each with its own ground **and palette**:

| # | template | ground | type colours | the model returns |
|---|---|---|---|---|
| 1 | Ivory botanical | cream, leaf corners, gold mandala | green + gold | subject on white |
| 2 | Scene card | its backdrop, full-bleed | teal + gold on a white card | scene, left half calm |
| 3 | Royal maroon | deep maroon→plum, gold bokeh | gold + cream | subject on white |
| 4 | Painted scene | its backdrop under an indigo wash | amber + white | night scene, bottom calm |
| 5 | Saffron graphic | saffron sunburst rays | white + deep maroon | flat vector subject |

The variant index selects the theme, so a quiet day that splits five slots across
two generic briefs must pass explicit non-overlapping indices — otherwise both
briefs render on themes 1 and 2 and the day's options collide.

On scene themes the logo is drawn white over a soft top scrim — a navy wordmark
on an arbitrary photographic backdrop is unreadable, and which backdrop comes
back is not knowable in advance. Cutouts get their alpha eroded before landing on
a dark ground, or the white rim from the keyed background shows as a halo.

**Punyatithi is muted; Jayanti is not.** A death anniversary overrides both the
ground and the type colours. A birth anniversary stays festive — greying it out
reads as mourning on the wrong day — while the copy stays respectful either way
(`जयंती पर शत्-शत् नमन`, never "Happy Birthday"). The decision is made in
`brief.py` from the occasion itself, not from the model's tone word, which says
"remembrance" for both.

## Portraits of leaders

A Gandhi Jayanti post without Gandhi is a weaker post, so the blanket ban on
depicting real people is now scoped: the model may render a faithful, dignified
likeness of a **deceased** Indian national figure, and is told to fall back to
their strongest symbol (charkha, khadi, a lit lamp) rather than ship an
inaccurate face. Living people remain off-limits — the calendar's
`[LIVING - VERIFY BEFORE PUBLISH]` flag hard-blocks `show_person`. Every likeness
post is flagged **check before posting**, because likeness fidelity is the one
thing here a machine cannot verify.

## Good-morning posts carry a quote

A good-morning creative without a line worth reading is wallpaper. `quote_hi`
holds a short Hindi suvichar for generic posts, rendered where the blessing line
normally sits. It stays empty for real occasions.

## The template, and why the model draws no text

The post is a fixed Postly brand template — cream ground, logo lockup, two-tone
green/gold Devanagari headline, ornament, blessing line, app-promo footer — built
in `brandkit.py` + `imaging.py` to match the reference creatives.

The model supplies exactly **one** thing: a subject isolated on white. Everything
else is drawn deterministically. Two reasons:

* Gemini garbles Devanagari conjuncts often enough to matter. All text is shaped
  by CoreText (macOS) or Noto+raqm (Linux), so it is correct 100% of the time.
* Letting the model compose the whole post produced good images that looked like
  someone else's brand. The references are a specific, repeatable template.

The headline and the line under it are printed together and **read as one
sentence** (`रक्षा बंधन` + `की हार्दिक शुभकामनाएं!`), so `brief.py` enforces that
they join grammatically, and strips the stutter when a name already ends in the
suffix's first word (`गांधी जयंती` + `जयंती पर नमन`).

**Artwork treatment adapts.** If the model honoured the white background, the
subject is flood-cut out and floated on the canvas. If it returned a full scene
instead — common for contextual subjects like a cup of chai — cutting would tear
ragged holes, so it is framed as a rounded photo card instead. `notes.art` records
which happened.

Tributes switch the whole palette to muted navy/grey: no green, no gold, no
festive ornament.

If shaping isn't available on the host, variants **fail** rather than shipping
artwork with no message on it. Check `/healthz` → `devanagari_shaping`.

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pip install pyobjc-framework-Cocoa      # macOS only, for Devanagari shaping
cp .env.example .env                              # fill in LITELLM_* at minimum
.venv/bin/python app.py                           # http://127.0.0.1:8000
```

Generate a specific day without waiting for the scheduler:

```bash
.venv/bin/python daily.py 2026-08-28 --force
```

See what today would pick, without spending image credits:

```bash
curl -s localhost:8000/preview | python -m json.tool
```

## Layout

| file | what it does |
|---|---|
| `events.py` | verified occasions from the calendar; LLM ranks them |
| `brief.py` | occasion → headline, visual direction, Hindi + English captions |
| `prompts.py` | image system instruction + the 4 art directions |
| `gen.py` | generates variants in parallel, vision-checks each for stray text |
| `imaging.py` | 1080×1080 crop, gradient scrim, shaped Hindi overlay |
| `publisher.py` | CDN hosting + Instagram Graph API (off until configured) |
| `daily.py` | one day's run end to end |
| `app.py` | review UI + the 07:00 IST scheduler |

## Tone safety

The calendar marks tributes and possibly-living figures, and `brief.py` enforces
the rules: a Jayanti of someone deceased gets *"जयंती पर शत्-शत् नमन"*, never
"Happy Birthday"; a Punyatithi gets *"विनम्र श्रद्धांजलि"* and never a
celebratory word. Rows flagged `[LIVING - VERIFY BEFORE PUBLISH]` are **demoted
below clean options** — greeting a living person's Jayanti is a public mistake —
and anything needing a look shows a **Check before posting** banner on the review
page.

Quiet days (no widely-marked occasion) are labelled as such, with a **Skip today**
button, rather than dressed up as an event.

## Turning on Instagram auto-posting

Currently **off**: the account isn't set up for API publishing yet. Until it is,
approve → **Download** → **Copy caption** → post from the phone. Those are logged
as `manual` so the history stays honest.

To switch it on, the account owner needs to:

1. Convert the Instagram account to **Business or Creator** and link it to a
   Facebook Page.
2. Create a Meta app with `instagram_basic`, `instagram_content_publish` and
   `pages_read_engagement`.
3. Generate a **long-lived page access token** (~60 days — it expires, and a
   post will start failing when it does).
4. Get the **Instagram Business account id** —
   `GET /{page-id}?fields=instagram_business_account`. This is not the @handle.

Then set `IG_USER_ID`, `IG_ACCESS_TOKEN`, `IG_PUBLISH_ENABLED=true` and confirm
`/healthz` → `instagram.ready` is `true`. No code change needed.

Instagram fetches a **public URL** rather than a file upload, which is why
`publisher.host()` puts the JPEG on the Postly CDN first. That part is already
configured and working.

## Deploy

Docker → Render (`render.yaml`). Needs a **persistent disk at `/data`** — the
SQLite DB and generated JPEGs live there and a deploy without it loses history.
Set the env vars listed in `render.yaml`, then check `/healthz`.

The Dockerfile installs `libraqm0` + `fonts-noto-devanagari` for shaping. **This
was not verified on Linux** — no Docker on the machine this was built on — so
check `/healthz` → `devanagari_shaping` is `true` on the first deploy before
trusting a run.
