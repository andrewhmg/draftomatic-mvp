# Draftomatic — MVP (IS 581 Week 4)

Autopilot blog for Framer small-business sites: connect a site, approve an AI-generated
content plan, and drafts get written, covered, and published on a weekly schedule with
zero manual work (~5 min/week of owner time — the value prop).

Built to the Week 3 MVP Description scope, unchanged: **Connect → Plan → Generate →
Publish**, plus Trust controls (preview, autopilot toggle, pause, status log).

## Run it (no dependencies, Python stdlib only)

```bash
cd mvp-build
python3 server.py          # binds 127.0.0.1:8765 (falls forward if busy)
open http://127.0.0.1:8765
```

Demo data (fake landscaping company "Peak Lawn & Landscape") auto-seeds on first run so
the flow works without a real Framer site. `data/state.json` holds all state; delete it
for a factory reset.

## The 4 screens

| Screen | URL | What to show |
|---|---|---|
| Connect | `/` | sign-up form → connect site → industry auto-detected |
| Topics | `/topics` | 12 ranked topics w/ keywords; approve all / edit / add / delete |
| Preview | `/preview` | full draft: meta, 1200×630 cover, 600–1,000-word body; approve→publish, regenerate |
| Dashboard | `/dashboard` | autopilot toggle, published posts, status log w/ retry |

## API (all JSON)

`GET /api/health` · `GET /api/state` · `POST /api/connect` · `GET /api/topics` ·
`POST /api/topics/generate|approve|edit|delete|add` · `POST /api/generate` ·
`POST /api/regenerate` · `GET /api/article/<id>` · `POST /api/publish` ·
`POST /api/publish/retry` · `GET /api/statuslog` · `POST /api/autopilot`

## Publishing to a real Framer site

`framer.py` builds the Framer CMS payload (title, slug, metaTitle, metaDescription,
body, image, publishedAt — mapping table documented in the module docstring) and, when
`FRAMER_API_KEY` is set in the environment, POSTs it to the Framer Web API via urllib.
Without a key it runs in **demo mode**: the exact payload is written to
`published/<slug>.json` and logged, so the whole flow is testable with no credentials.
Failures are logged with attempt number and retried from the dashboard.

## Architecture

```
server.py    stdlib http.server, JSON API + static screens     (no framework)
store.py     JSON persistence, atomic writes, read-modify-write lock
content.py   template article generator (600–1,000 words, SEO meta, variation seed)
topics_gen.py industry-keyword topic generator (12 ranked topics)
cover.py     1200×630 SVG cover generator (Framer social-preview ratio)
framer.py    Framer CMS publish adapter (live key or demo mode)
static/      4 screens, shared nav + style.css
```

## Files

- `screens/` — the four verified screenshots (used in the submission doc)
- `SPEC.md` / `STATE.json` — build plan and per-part verification log
- `SUBMISSION-NOTES.md` — what's demo vs. real, every claim checked
- `~/Downloads/Draftomatic MVP (Week 4).docx` — the submission document