# Draftomatic MVP — Build Spec (IS 581 Week 4: MVP Development)

Frozen decisions — build this, do not redesign it. All work happens in this directory (`/Users/andrewhogge/Documents/School/IS581/mvp-build/`).

## What we're building
Draftomatic = autopilot blog for Framer small-business sites (Week 3 MVP Description, submitted for continuity). Critical path: **Connect → Plan → Generate → Publish**, plus Trust controls. Core assumption the MVP tests: small-business owners will let AI publish with minimal review (auto-approve toggle defaults ON).

## Assignment target (Canvas course 36486, assignment 1460871)
- Due 2026-09-27T05:59Z = tonight 23:59 MDT. 5 points, `online_upload`.
- **5 pts** = functional MVP ready for testing (minimum features fine).
- **4 pts fallback** = "Partially Implemented MVP" doc: what's completed + screenshots + remaining steps & 1–2 week timeline. P7 always builds this doc too, so a submission exists no matter what.
- Submission artifact goes in `~/Downloads`. NEVER submit to Canvas — Andrew submits himself. Canvas is READ-ONLY.

## Architecture (frozen, stdlib-only — no pip installs, server runs with plain `python3 server.py`)
- `server.py` — stdlib `http.server` app, port 8765.
  - Pages: `GET /` → static/index.html, `/topics` → topics.html, `/preview` → preview.html, `/dashboard` → dashboard.html
  - API (all JSON): `GET /api/health`, `GET /api/state`, `POST /api/connect`, `GET /api/topics`, `POST /api/topics/approve`, `POST /api/topics/edit`, `POST /api/generate`, `POST /api/regenerate`, `GET /api/article/<id>`, `POST /api/approve`, `POST /api/publish`, `GET /api/statuslog`, `POST /api/autopilot`
- `store.py` — JSON persistence in `data/state.json`, atomic write (tmp file + rename). Helpers `load()/save()/update(fn)`.
- `content.py` — template-based article generator (no network, no LLM): headline, slug, meta title, meta description, body 600–1,000 words built from varied sentence/section templates parameterized by industry + keyword. Must enforce a ≥600-word check and a `regenerate` variation seed.
- `cover.py` — cover image generator: 1200×630 SVG (gradient + article title), saved to `covers/<slug>.svg`.
- `framer.py` — publish adapter. Builds Framer CMS payload `{title, slug, metaTitle, metaDescription, body(html), image, publishedAt}` with a documented field-mapping table. If env `FRAMER_API_KEY` is set, POST via urllib to the Framer Web API; otherwise **demo mode**: write payload JSON to `published/`, append entry to `data/statuslog.json` (status: published-demo / failed, with retry support).
- `static/` — `style.css` + 4 screens with shared nav: index (sign up / connect site), topics (approve list), preview (draft + approve/publish + regenerate), dashboard (published posts, status log, autopilot toggle, pause).

## Demo data (seed on first run)
Fake landscaping company **"Peak Lawn & Landscape"** (`data/seed.json`) so the demo never depends on a real Framer site. `/api/connect` takes any URL/name: tries a live scrape (urllib, 5s timeout) for industry detection, else falls back to demo content. Industry = keyword-match table → drives topic generation.

## Parts (execute strictly in order — one per cron tick)
Every part ends with: real verification (commands run, outputs shown), `STATE.json` updated (status + one-line note + log line), and the background server killed before ending.

### P0 — Scaffold
`server.py` with all routes returning stub-but-valid JSON, `store.py`, `data/state.json`, `static/` 4 screens + nav + style.css, seed loader.
**Accept:** `python3 server.py` runs; `curl localhost:8765/api/health` → ok; all 4 pages return 200 and render nav.

### P1 — Connect stage
`/api/connect` (POST name+url+email): persists site, industry detection (scrape → keyword table → demo fallback), signup fields stored. First-run auto-seeds Peak Lawn so screens are never empty. Connect screen wired.
**Accept:** POST /api/connect returns detected industry; state persists across server restart; UI screen shows connected state.

### P2 — Plan stage
Topic generator: ≥10 topics (title + angle + target keyword + SEO priority rank) derived from industry + business name. One-tap approve-all + per-topic select + edit/delete/add. Topics screen wired.
**Accept:** `curl /api/topics` → ≥8 topics with keywords; approve persists; screen shows approve controls.

### P3 — Generate stage
`/api/generate` from an approved topic → full article (headline, slug, meta title/description, body 600–1,000 words, readable sections). `/api/regenerate` re-rolls variation. Persist under `data/articles/`.
**Accept:** curl check: generated article body ≥600 words; all fields present; regenerate produces a different body.

### P4 — Publish stage
`/api/publish` → builds Framer payload with field mapping, generates cover SVG, writes `published/<slug>.json` + status log entry (published-demo), retry on failure. `framer.py` adapter with `FRAMER_API_KEY` hook + field-mapping table documented.
**Accept:** publish produces payload file + cover SVG + status-log entry; a forced-failure path logs failed + retry works.

### P5 — Trust stage + dashboard
Preview screen renders full draft (body, meta, image) with Approve→Publish and Regenerate. Autopilot toggle (auto-approve on schedule) + pause, persisted. Dashboard: published posts list, status log, next scheduled.
**Accept:** end-to-end via curl: connect → approve topics → generate → publish → dashboard lists it; autopilot toggle persists.

### P6 — End-to-end verify + screenshots
Walk all 4 screens with Chrome headless screenshots (`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --headless --screenshot=<path> --window-size=1440,900 <url>` — browser_exec/Safari profile does NOT work on this Mac), fix any bugs found, rerun smoke test.
**Accept:** 4 screenshots in `screens/`, all flows verified working.

### P7 — Submission package
`README.md` (run instructions + FRAMER_API_KEY hookup), `SUBMISSION-NOTES.md` (every claim checked, what's demo vs real), shot list for Andrew's 2-min screen recording, and **`~/Downloads/Draftomatic MVP (Week 4).docx`** — Partially-Implemented-MVP fallback doc: what's completed (with the `screens/` screenshots embedded), remaining steps + 1–2 week timeline (Framer live-key hookup, digest email). Build the docx with python-docx under `/usr/bin/python3` and verify by reading it back.
**Accept:** docx exists in ~/Downloads, verified via python-docx; notes present.

## After all parts done
- GET `https://byu.instructure.com/api/v1/courses/36486/assignments/1460871?include[]=submission` (Bearer token at `~/.hermes/canvas_token`). If still unsubmitted → idle ticks reply one line: "MVP READY — Andrew submits from ~/Downloads + records walkthrough." If submitted/graded → reply "DONE — cron can be removed."

## Deadline guard
After 22:00 MDT, if P6 isn't done, finish P7 first so the fallback doc exists. Minimality beats completeness: if a part fails twice, shrink it.

## Hard rules
- NEVER submit anything to Canvas (no /submissions POSTs, no uploads). Andrew submits himself, always.
- Never touch files outside `mvp-build/` except the docx in `~/Downloads`.
- No pip installs, no credential requests, no questions — decide, log in STATE.json, move on.