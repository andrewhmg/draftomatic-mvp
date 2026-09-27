# Draftomatic MVP — SUBMISSION NOTES (IS 581 Week 4)

Built 2026-09-26 from the Week 3 MVP Description (`~/Documents/School/IS581/mvp-user-flow.md`,
submitted as the Week 3 docx). Scope frozen: Connect → Plan → Generate → Publish + Trust.
Submission file: `~/Downloads/Draftomatic MVP (Week 4).docx`.

## What is real vs. demo (every claim checked)

REAL and working (verified by automated checks + live screenshots):
- 4-screen web app, stdlib-only Python server (`python3 server.py`, port 8765)
- Connect flow: sign-up fields + site URL → industry auto-detection (keyword table over
  scraped page text; falls back to the seed company when no live site is reachable)
- Topic planning: 12 SEO-ranked topics generated from the detected industry; approve-all,
  individual select, edit, delete, add-own
- Article generation: full draft per topic (headline, slug, meta title + description,
  600–1,000-word body in 7 sections), regenerate produces a genuinely different draft
- Publishing: Framer CMS payload with documented field mapping, 1200×630 SVG cover per
  article, status log with attempt numbers, failed-publish retry
- Trust/autopilot: preview-before-publish, autopilot toggle (auto-approve on schedule),
  pause; all state persists across server restarts (atomic JSON writes)

DEMO scaffolding (honest limits, stated in the doc):
- The connected site is a seed company ("Peak Lawn & Landscape"), not Andrew's real site
- Article text comes from a template engine, not an LLM (no API keys needed to run)
- Publish writes the exact Framer CMS payload to `published/<slug>.json` instead of
  calling Framer's API. The live-API path is implemented and used automatically when
  `FRAMER_API_KEY` is set; it is untested against a real Framer account

## Verification performed (2026-09-26)

- 20/20 automated API checks passed (health, pages 200, connect → landscaping detected,
  ≥10 topics, approve persists, generate ≥600 words, regenerate differs, publish →
  payload file + cover SVG + status log entry, autopilot toggle persists)
- All 4 screens screenshotted at 1440×900 (2× retina) and visually verified:
  `screens/01-connect.png` … `04-dashboard.png`
- State persistence verified across real server restarts

## Known quirks (documented for the record, not user-facing)

- On this Mac, headless Chrome completes exactly one clean page capture per process
  (exit 124 hang AFTER the screenshot file is written); worked around by launching one
  fresh process per shot
- `content.py` uses `.format()`-safe templates (no method calls in format strings)

## 2-minute walkthrough script (for Andrew's screen recording)

1. (0:00–0:20) Open `http://127.0.0.1:8765` — Connect screen. Type name/email, paste a
   Framer site URL (or leave blank for the demo company), hit Connect. Point at the
   detected-industry card.
2. (0:20–0:45) Topics screen: 12 ranked topics with target keywords. Approve all with
   one tap — drafts generate immediately.
3. (0:45–1:20) Preview: full 600+ word draft, meta tags, auto-generated 1200×630 cover.
   Hit Regenerate to show a different draft, then Approve & publish.
4. (1:20–1:50) Dashboard: published post listed, status log shows published-demo, flip
   the autopilot toggle off and on (the core assumption: owners leave it on).
5. (1:50–2:00) Close: "~5 minutes a week is the whole product. Connect → Plan →
   Generate → Publish, no manual work."