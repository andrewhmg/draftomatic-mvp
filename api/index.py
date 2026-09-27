"""Draftomatic on Vercel — ASGI adapter over the stdlib route table.

Maps ASGI (scope, receive, send) requests onto the same ROUTES table that
server.py's http.server handler uses, so one codebase serves both:
  locally:  python3 server.py          (http.server on 127.0.0.1:8765)
  Vercel:   api/index.py (this file)   (serverless, /api/* routes)

State on Vercel is per-instance ephemeral (/tmp), so it is seeded at boot:
 - data/state.json is copied from data/state-seed.json if missing
 - covers are generated on demand (same as local)
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
sys.path.insert(0, ROOT)
os.chdir(ROOT)

# seed demo state on cold start
DATA = os.path.join(ROOT, "data")
STATE = os.path.join(DATA, "state.json")
SEED = os.path.join(DATA, "state-seed.json")
if not os.path.exists(STATE) and os.path.exists(SEED):
    shutil.copy(SEED, STATE)

import server as appmod  # noqa: E402  (imports store, registers ROUTES)

STATIC_TYPES = {"html": "text/html; charset=utf-8", "css": "text/css; charset=utf-8",
                "js": "text/javascript; charset=utf-8", "svg": "image/svg+xml"}


async def read_body(receive):
    chunks = []
    while True:
        msg = await receive()
        chunks.append(msg.get("body", b""))
        if not msg.get("more_body"):
            break
    return b"".join(chunks)


async def send_json(send, obj, status=200):
    payload = json.dumps(obj).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8"),
                            (b"content-length", str(len(payload)).encode())]})
    await send({"type": "http.response.body", "body": payload})


async def send_static(send, relpath):
    safe = os.path.normpath(os.path.join(ROOT, "static", relpath))
    alt = safe + ".html"
    if not os.path.isfile(safe) and os.path.isfile(alt):
        safe = alt
    covers_root = os.path.join(ROOT, "covers")
    if relpath.startswith("covers/") or not os.path.isfile(safe):
        cand = os.path.join(covers_root, os.path.basename(relpath))
        if os.path.isfile(cand):
            safe = cand
    if not (safe.startswith(ROOT) and os.path.isfile(safe)):
        await send({"type": "http.response.start", "status": 404,
                    "headers": [(b"content-type", b"text/html")]})
        await send({"type": "http.response.body", "body": b"<h1>404</h1>"})
        return
    ext = safe.rsplit(".", 1)[-1].lower()
    ctype = STATIC_TYPES.get(ext, "application/octet-stream")
    with open(safe, "rb") as f:
        body = f.read()
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", ctype.encode()),
                            (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


async def app(scope, receive, send):
    if scope["type"] != "http":  # ignore lifecycle pings
        return
    path = scope["path"]
    method = scope["method"]

    if method == "GET" and not path.startswith("/api/"):
        await send_static(send, path.lstrip("/") or "index.html")
        return

    m = None
    handler = None
    for (meth, rx), fn in appmod.ROUTES.items():
        if meth == method:
            m = rx.match(path)
            if m:
                handler = fn
                break
    if handler is None:
        await send_json(send, {"ok": False, "error": "no route"}, 404)
        return

    body = {}
    if method == "POST":
        raw = await read_body(receive)
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            body = {}
    state = appmod.store.load()
    result = handler(state, body, m)
    await send_json(send, result)