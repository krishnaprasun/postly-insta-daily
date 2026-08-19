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

## Why the model draws no text

Gemini garbles Devanagari conjuncts often enough to matter. So the image model
produces **artwork only**, with a deliberately calm bottom band, and `imaging.py`
overlays the headline using proper CoreText/Noto shaping. Text is correct 100% of
the time and consistent across the grid.

If shaping isn't available on the host, variants **fail** rather than shipping
bare artwork with no message on it. Check `/healthz` → `devanagari_shaping`.

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
