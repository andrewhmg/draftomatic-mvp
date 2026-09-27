"""Draftomatic MVP — stdlib HTTP server (http.server). Port 8765."""
import json, os, re, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import store

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")

ROUTES = {}  # (method, compiled_regex) -> handler(state, body, match) -> dict


def route(method, pattern):
    def deco(fn):
        ROUTES[(method, re.compile("^" + pattern + "$"))] = fn
        return fn
    return deco


def store_now():
    import datetime
    return datetime.datetime.utcnow().isoformat() + "Z"


# ---------- Connect ----------
@route("POST", r"/api/connect")
def api_connect(s, body, m):
    name = (body.get("name") or "").strip() or "My Business"
    url = (body.get("url") or "").strip()
    email = (body.get("email") or "").strip()
    industry = detect_industry(url, name)

    def fn(st):
        st["connected"] = {"name": name, "url": url, "industry": industry,
                           "email": email, "connected_at": store_now()}
    store.update(fn)
    return {"ok": True, "industry": industry, "name": name}


def detect_industry(url, name):
    text = ""
    if url:
        try:
            import urllib.request
            req = urllib.request.Request(url if url.startswith("http") else "https://" + url,
                                         headers={"User-Agent": "Mozilla/5.0 Draftomatic/0.1"})
            with urllib.request.urlopen(req, timeout=5) as r:
                text = r.read(20000).decode("utf-8", "ignore").lower()
        except Exception:
            text = ""
    if not text:
        # no live page: the NAME the owner typed is the strongest signal — check it alone first
        name_scores = {ind: sum(1 for k in kws if k in name.lower()) for ind, kws in INDUSTRIES.items()}
        best_name = max(name_scores, key=name_scores.get)
        if name_scores[best_name] > 0:
            return best_name
        # otherwise fall back to the seed company's content sample (demo mode)
        try:
            with open(os.path.join(ROOT, "data", "seed.json")) as f:
                text = " " + json.load(f).get("site_content_sample", "").lower()
        except FileNotFoundError:
            text = " " + name.lower()
    scores = {ind: sum(1 for k in kws if k in text) for ind, kws in INDUSTRIES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


INDUSTRIES = {
    "landscaping": ["landscap", "lawn", "mowing", "irrigation", "tree care", "sod", "mulch", "snow removal"],
    "restaurant": ["restaurant", "menu", "kitchen", "dining", "chef", "catering"],
    "dental": ["dental", "dentist", "teeth", "orthodont"],
    "hvac": ["hvac", "heating", "cooling", "furnace", "air conditioning", "plumb"],
    "fitness": ["gym", "fitness", "training", "yoga", "pilates"],
    "realestate": ["real estate", "realtor", "homes for sale", "listings"],
    "salon": ["salon", "hair", "nails", "spa", "barber"],
}


# ---------- Plan (topics) ----------
@route("GET", r"/api/topics")
def api_topics(s, body, m):
    return {"topics": s.get("topics", [])}


@route("POST", r"/api/topics/generate")
def api_topics_generate(s, body, m):
    import topics_gen
    conn = s.get("connected") or {}
    gen = topics_gen.generate(conn.get("industry", "general"), conn.get("name", "your business"))
    store.update(lambda st: st.update({"topics": gen, "topics_approved": False}))
    return {"ok": True, "count": len(gen)}


@route("POST", r"/api/topics/approve")
def api_topics_approve(s, body, m):
    ids = body.get("ids")
    count = {"n": 0}

    def fn(st):
        for t in st["topics"]:
            t["approved"] = True if ids is None else (t["id"] in ids)
        st["topics"] = [t for t in st["topics"] if t.get("approved")]
        st["topics_approved"] = True
        count["n"] = len(st["topics"])
    store.update(fn)
    return {"ok": True, "approved": count["n"]}


@route("POST", r"/api/topics/edit")
def api_topics_edit(s, body, m):
    tid = body.get("id")

    def fn(st):
        for t in st["topics"]:
            if t["id"] == tid:
                for k in ("title", "angle", "keyword"):
                    if k in body:
                        t[k] = body[k]
                if "approved" in body:  # topics-screen checkbox toggle
                    t["approved"] = bool(body["approved"])
    store.update(fn)
    return {"ok": True}


@route("POST", r"/api/topics/delete")
def api_topics_delete(s, body, m):
    tid = body.get("id")
    store.update(lambda st: st.update({"topics": [t for t in st["topics"] if t["id"] != tid]}))
    return {"ok": True}


@route("POST", r"/api/topics/add")
def api_topics_add(s, body, m):
    def fn(st):
        n = max([t["id"] for t in st["topics"]] + [0]) + 1
        st["topics"].append({"id": n, "title": body.get("title", "Untitled topic"),
                             "angle": body.get("angle", ""), "keyword": body.get("keyword", ""),
                             "approved": True, "priority": len(st["topics"]) + 1})
    store.update(fn)
    return {"ok": True}


# ---------- Generate ----------
@route("POST", r"/api/generate")
def api_generate(s, body, m):
    import content
    tid = body.get("topic_id")
    topic = next((t for t in s.get("topics", []) if t["id"] == tid), None)
    if not topic:
        return {"ok": False, "error": "topic not found"}
    art = content.generate(topic, s.get("connected") or {})

    def fn(st):
        art["topic_id"] = tid
        st["articles"].append(art)
    store.update(fn)
    _persist_article(art)
    return {"ok": True, "article_id": art["id"], "words": art["word_count"]}


def _persist_article(art, remove_id=None):
    """Persist a generated article to data/articles/<id>.json (SPEC P3).

    Writable root follows store.data_root() (Vercel: /tmp)."""
    d = os.path.join(store.data_root(), "data", "articles")
    os.makedirs(d, exist_ok=True)
    if remove_id is not None and remove_id != art["id"]:
        try:
            os.remove(os.path.join(d, f"{remove_id}.json"))
        except OSError:
            pass
    with open(os.path.join(d, f"{art['id']}.json"), "w") as f:
        json.dump(art, f, indent=2)


@route("POST", r"/api/regenerate")
def api_regenerate(s, body, m):
    import content
    aid = body.get("article_id")
    idx = next((i for i, a in enumerate(s.get("articles", [])) if a["id"] == aid), None)
    if idx is None:
        return {"ok": False, "error": "article not found"}
    old = s["articles"][idx]
    topic = next((t for t in s.get("topics", []) if t["id"] == old.get("topic_id")), None)
    art = content.generate(topic or {"title": old.get("title", "Article"), "angle": "", "keyword": old.get("keyword", "")},
                           s.get("connected") or {}, variation=old.get("variation", 0) + 1)

    def fn(st):
        art["topic_id"] = st["articles"][idx].get("topic_id")
        art["id"] = st["articles"][idx]["id"]  # keep the SAME id on regenerate: screen URLs/statuslog stay valid
        st["articles"][idx] = art
    store.update(fn)
    _persist_article(art, remove_id=None)  # id unchanged -> same file overwritten
    return {"ok": True, "article_id": art["id"], "words": art["word_count"]}


@route("GET", r"/api/article/(\d+)")
def api_article(s, body, m):
    aid = int(m.group(1))
    art = next((a for a in s.get("articles", []) if a["id"] == aid), None)
    if not art:
        return {"ok": False, "error": "not found"}
    art = dict(art)
    if not art.get("cover"):  # preview cover on demand (idempotent file write)
        try:
            import cover
            _, art["cover"] = cover.generate_cover(art.get("title"), aid)
        except Exception:
            pass
    return art


# ---------- Publish ----------
def _publish_art(s, art, is_retry):
    import framer
    res = framer.publish(art, is_retry=is_retry)
    art_id = art["id"]  # captured before mutation; dedupe below replaces older publish entries

    def fn(st):
        st["statuslog"].append(res["log"])
        if res["ok"]:
            st["published"] = [p for p in st["published"] if p["article_id"] != art_id]  # republish replaces, no dupes
            st["published"].append(res["published"])
    store.update(fn)
    return res


@route("POST", r"/api/publish")
def api_publish(s, body, m):
    art = next((a for a in s.get("articles", []) if a["id"] == body.get("article_id")), None)
    if not art:
        return {"ok": False, "error": "article not found"}
    res = _publish_art(s, art, is_retry=False)
    return {"ok": res["ok"], "status": res["log"]["status"]}


@route("POST", r"/api/publish/retry")
def api_retry(s, body, m):
    art = next((a for a in s.get("articles", []) if a["id"] == body.get("article_id")), None)
    if not art:
        return {"ok": False, "error": "article not found"}
    res = _publish_art(s, art, is_retry=True)
    return {"ok": res["ok"], "status": res["log"]["status"]}


@route("GET", r"/api/statuslog")
def api_statuslog(s, body, m):
    return {"statuslog": s.get("statuslog", [])}


# ---------- Trust / dashboard ----------
@route("POST", r"/api/autopilot")
def api_autopilot(s, body, m):
    on = bool(body.get("on", True))

    def fn(st):
        st["autopilot"] = on
        st["paused"] = not on
    store.update(fn)
    return {"ok": True, "autopilot": on, "paused": not on}


@route("GET", r"/api/state")
def api_state(s, body, m):
    return {k: s.get(k) for k in ("connected", "topics", "articles", "published",
                                  "statuslog", "autopilot", "paused", "topics_approved")}


@route("GET", r"/api/health")
def api_health(s, body, m):
    return {"ok": True, "service": "draftomatic", "time": store_now()}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # quiet

    def _send(self, code, ctype, payload):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        for (meth, rx), fn in ROUTES.items():
            if meth == "GET":
                m = rx.match(path)
                if m:
                    self._send(200, "application/json", json.dumps(fn(store.load(), {}, m)).encode())
                    return
        safe = path.lstrip("/") or "index.html"
        fpath = None
        covers_root = os.path.join(store.data_root(), "covers")  # writable root (Vercel: /tmp)
        for base, prefix in ((STATIC, ""), (covers_root, "covers/")):  # covers/ served for preview images
            rel = safe
            if prefix:
                if not rel.startswith(prefix):
                    continue
                rel = rel[len(prefix):]
            cand = os.path.normpath(os.path.join(base, rel))
            if not cand.startswith(base):
                continue  # path traversal guard
            if not os.path.isfile(cand):
                alt = os.path.normpath(os.path.join(base, rel + ".html"))
                if os.path.isfile(alt):
                    cand = alt
            if os.path.isfile(cand):
                fpath = cand
                break
        if not fpath or not fpath.startswith((STATIC, covers_root)) or not os.path.isfile(fpath):
            self._send(404, "text/html", b"<h1>404</h1>")
            return
        ext = fpath.rsplit(".", 1)[-1].lower()  # extension of the FILE (pretty URLs like /topics have none)
        ctype = {"html": "text/html", "css": "text/css", "js": "text/javascript",
                 "svg": "image/svg+xml"}.get(ext, "application/octet-stream")
        with open(fpath, "rb") as f:
            self._send(200, ctype, f.read())

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}
        for (meth, rx), fn in ROUTES.items():
            if meth == "POST":
                m = rx.match(path)
                if m:
                    self._send(200, "application/json", json.dumps(fn(store.load(), body, m)).encode())
                    return
        self._send(404, "application/json", b'{"ok": false, "error": "no route"}')


HTTPD = None  # module-level handle so a caller can shutdown() cleanly


def shutdown():
    global HTTPD
    if HTTPD is not None:
        HTTPD.shutdown()
        HTTPD.server_close()
        HTTPD = None


def main():
    for sub in ("data/articles", "covers", "published", "screens"):
        os.makedirs(os.path.join(ROOT, sub), exist_ok=True)
    global HTTPD
    port = int(os.environ.get("PORT", "8765"))
    for p in range(port, port + 20):  # fall forward if a stale thread holds the port
        try:
            HTTPD = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    if HTTPD is None:
        raise RuntimeError("no free port in 8765-8784")
    print(f"Draftomatic listening on http://127.0.0.1:{HTTPD.server_address[1]}", flush=True)
    HTTPD.serve_forever()


if __name__ == "__main__":
    main()