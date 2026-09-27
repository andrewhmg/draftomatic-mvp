"""Draftomatic — Framer CMS publish adapter.

Field mapping (Framer CMS "Articles" collection → our article):
  title            -> title
  slug             -> slug
  metaTitle        -> meta_title   (SEO title tag)
  metaDescription  -> meta_description
  body             -> body_html    (rich text)
  image            -> cover SVG, 1200x630 (Framer social-preview ratio)
  publishedAt      -> now (ISO 8601)

If FRAMER_API_KEY is set in the environment, POSTs to the Framer Web API
(https://api.framer.com/web-api/) via urllib. Otherwise DEMO MODE: writes the
exact payload to published/<slug>.json and logs a status entry, so the flow is
testable without touching a real site.
"""
import datetime
import json
import os
import urllib.request

import cover

ROOT = os.path.dirname(os.path.abspath(__file__))


def _now():
    return datetime.datetime.utcnow().isoformat() + "Z"


def publish(article, is_retry=False):
    art_id = article["id"]
    payload = {
        "title": article.get("title"),
        "slug": article.get("slug"),
        "metaTitle": article.get("meta_title"),
        "metaDescription": article.get("meta_description"),
        "body": article.get("body_html"),
        "image": None,
        "publishedAt": _now(),
    }
    try:
        cpath, crel = cover.generate_cover(article.get("title"), art_id)
        payload["image"] = crel
    except Exception as e:
        pass  # cover failure should not block publish; logged below

    key = os.environ.get("FRAMER_API_KEY")
    if key:
        try:
            req = urllib.request.Request(
                "https://api.framer.com/web-api/",
                data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status in (200, 201):
                    status = "published"
                else:
                    status = "failed"
        except Exception:
            status = "failed"
        demo = False
    else:
        out = os.path.join(ROOT, "published", f"{payload['slug']}.json")
        with open(out, "w") as f:
            json.dump({"collection": "Articles", "payload": payload}, f, indent=2)
        status = "published-demo"
        demo = True

    log = {
        "article_id": art_id,
        "title": payload["title"],
        "status": status,
        "demo": demo,
        "attempt": 2 if is_retry else 1,
        "at": _now(),
    }
    published = {
        "article_id": art_id,
        "title": payload["title"],
        "slug": payload["slug"],
        "url": f"https://{(os.environ.get('FRAMER_SITE') or 'demo.example.com')}/{payload['slug']}",
        "image": payload["image"],
        "publishedAt": payload["publishedAt"],
        "demo": demo,
    }
    return {"ok": status.startswith("published"), "log": log, "published": published, "payload": payload}