#!/usr/bin/env python3
"""Draftomatic MVP — automated test suite.

Boots the app on a scratch port with a COPY of the state, runs the full
acceptance flow (health, pages, connect, topics, generate, regenerate,
publish, retry, autopilot), then restores your state and shuts down.

Run:  python3 test_draftomatic.py        (exit 0 = all pass)
      python3 test_draftomatic.py -v    (list every check)
No dependencies beyond the Python stdlib.
"""
import glob
import json
import os
import py_compile
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

VERBOSE = "-v" in sys.argv

_results = []


def check(name, cond, detail=""):
    _results.append((name, bool(cond), detail))
    if VERBOSE:
        print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  --> {str(detail)[:160]}"))


def api(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def page_ok(base, path):
    try:
        return urllib.request.urlopen(base + path, timeout=5).status == 200
    except Exception:
        return False


def main():
    print("=" * 56)
    print("Draftomatic MVP test suite")
    print("=" * 56)

    # ---- 0. static checks: modules compile ----
    for f in ("server.py", "store.py", "content.py", "cover.py", "framer.py", "topics_gen.py"):
        try:
            py_compile.compile(os.path.join(ROOT, f), doraise=True)
            check(f"compiles: {f}", True)
        except Exception as e:
            check(f"compiles: {f}", False, e)
            print(f"COMPILE FAIL in {f}: {e}")
            return finish()  # cannot continue meaningfully

    # ---- boot on a scratch port with a state COPY ----
    for mod in ("server", "content", "store", "cover", "framer", "topics_gen"):
        sys.modules.pop(mod, None)
    import server as srvmod

    os.environ["PORT"] = "8795"
    state_backup = "/tmp/draftomatic-test-state-backup.json"
    had_state = os.path.exists("data/state.json")
    if had_state:
        shutil.copy("data/state.json", state_backup)
    for d in ("published", "covers"):
        for x in glob.glob(os.path.join(d, "*")):
            os.remove(x)

    t = threading.Thread(target=srvmod.main, daemon=True)
    t.start()
    for _ in range(30):
        time.sleep(0.2)
        if srvmod.HTTPD:
            break
    if not srvmod.HTTPD:
        check("server boots", False, "no HTTPD after 6s")
        return finish()
    BASE = f"http://127.0.0.1:{srvmod.HTTPD.server_address[1]}"
    check("server boots", True, BASE)

    try:
        # ---- P0: health + pages ----
        h = api(BASE, "GET", "/api/health")
        check("health ok", h.get("ok") is True, h)
        for pg in ("/", "/topics", "/preview", "/dashboard", "/style.css"):
            check(f"page {pg} -> 200", page_ok(BASE, pg))

        # ---- P1: connect + industry detection ----
        c = api(BASE, "POST", "/api/connect",
                {"name": "Peak Lawn & Landscape", "url": "", "email": "owner@peaklawn.demo"})
        check("connect detects landscaping", c.get("industry") == "landscaping", c)
        st = api(BASE, "GET", "/api/state")
        check("connected state persists", (st.get("connected") or {}).get("name") == "Peak Lawn & Landscape")
        c2 = api(BASE, "POST", "/api/connect", {"name": "Bright Smile Dental", "url": "", "email": "x@y.z"})
        check("connect detects dental", c2.get("industry") == "dental", c2)
        api(BASE, "POST", "/api/connect", {"name": "Peak Lawn & Landscape", "url": "", "email": "owner@peaklawn.demo"})

        # ---- P2: topics ----
        api(BASE, "POST", "/api/topics/generate", {})
        tps = api(BASE, "GET", "/api/topics")["topics"]
        check("topics >= 10", len(tps) >= 10, len(tps))
        check("topics have keywords+priority", all(t.get("keyword") and t.get("priority") for t in tps))
        some = [tps[0]["id"], tps[1]["id"]]
        api(BASE, "POST", "/api/topics/approve", {"ids": some})
        t2 = api(BASE, "GET", "/api/topics")["topics"]
        check("subset approve keeps only chosen", len(t2) == 2 and all(x["approved"] for x in t2), t2)
        api(BASE, "POST", "/api/topics/edit", {"id": t2[0]["id"], "title": "Edited title"})
        t3 = api(BASE, "GET", "/api/topics")["topics"]
        check("topic edit persists", any(x["title"] == "Edited title" for x in t3))
        api(BASE, "POST", "/api/topics/add", {"title": "Manual topic"})
        t4 = api(BASE, "GET", "/api/topics")["topics"]
        check("topic add works", len(t4) == 3 and any(x["title"] == "Manual topic" for x in t4))
        api(BASE, "POST", "/api/topics/approve", {})  # approve-all
        t5 = api(BASE, "GET", "/api/topics")["topics"]
        check("approve-all", len(t5) == 3 and all(x["approved"] for x in t5))

        # ---- P3: generate + regenerate ----
        g = api(BASE, "POST", "/api/generate", {"topic_id": t5[0]["id"]})
        check("generate ok", g.get("ok") is True, g)
        check("body 600-1000 words", 600 <= g.get("words", 0) <= 1000, g.get("words"))
        aid = g["article_id"]
        a1 = api(BASE, "GET", f"/api/article/{aid}")
        check("article fields complete", all(k in a1 for k in
              ("title", "slug", "meta_title", "meta_description", "body_html", "word_count")))
        check("cover attached", (a1.get("cover") or "").startswith("/covers/"), a1.get("cover"))
        check("cover file exists", os.path.isfile(os.path.join(ROOT, a1["cover"].lstrip("/"))))
        rg = api(BASE, "POST", "/api/regenerate", {"article_id": aid})
        check("regenerate ok", rg.get("ok") is True, rg)
        a2 = api(BASE, "GET", f"/api/article/{aid}")
        check("same id after regenerate", a2.get("id") == aid)
        check("regenerate changes body", a1["body_html"] != a2["body_html"])
        check("regenerated body in band", 600 <= a2["word_count"] <= 1000, a2["word_count"])
        check("article persisted to data/articles",
              os.path.isfile(os.path.join(ROOT, "data", "articles", f"{aid}.json")))

        # ---- P4: publish + retry + statuslog ----
        p = api(BASE, "POST", "/api/publish", {"article_id": aid})
        check("publish ok", p.get("ok") is True and p.get("status") == "published-demo", p)
        pub_files = glob.glob("published/*.json")
        check("payload file written", len(pub_files) >= 1, pub_files)
        payload = json.load(open(pub_files[0]))["payload"]
        check("payload has Framer field mapping",
              all(k in payload for k in ("title", "slug", "metaTitle", "metaDescription", "body", "image", "publishedAt")),
              sorted(payload.keys()))
        sl = api(BASE, "GET", "/api/statuslog")["statuslog"]
        check("statuslog entry", any(x.get("status") == "published-demo" for x in sl))
        p2 = api(BASE, "POST", "/api/publish", {"article_id": aid})  # republish
        pubs = [x for x in api(BASE, "GET", "/api/state")["published"] if x["article_id"] == aid]
        check("republish dedupes (no dupes)", len(pubs) == 1, len(pubs))

        # forced-failure path: FRAMER_API_KEY with a bogus key must fail + log
        env_key = os.environ.get("FRAMER_API_KEY")
        os.environ["FRAMER_API_KEY"] = "bogus-key-for-test"
        for mod in ("framer",):
            sys.modules.pop(mod, None)
        pf = api(BASE, "POST", "/api/publish/retry", {"article_id": aid})
        check("publish with bad key -> failed", pf.get("ok") is False and pf.get("status") == "failed", pf)
        sl2 = api(BASE, "GET", "/api/statuslog")["statuslog"]
        check("failure logged with attempt#", any(x.get("status") == "failed" and x.get("attempt") == 2 for x in sl2))
        if env_key is None:
            os.environ.pop("FRAMER_API_KEY")
        else:
            os.environ["FRAMER_API_KEY"] = env_key

        # ---- P5: trust / autopilot / dashboard state ----
        au = api(BASE, "POST", "/api/autopilot", {"on": False})
        check("autopilot pause", au.get("autopilot") is False and au.get("paused") is True, au)
        au2 = api(BASE, "POST", "/api/autopilot", {"on": True})
        check("autopilot resume", au2.get("autopilot") is True and au2.get("paused") is False, au2)
        final = api(BASE, "GET", "/api/state")
        check("state endpoint complete", all(k in final for k in
              ("connected", "topics", "articles", "published", "statuslog", "autopilot", "paused")))
    finally:
        srvmod.shutdown()
        if had_state:
            shutil.copy(state_backup, "data/state.json")
            os.remove(state_backup)

    return finish()


def finish():
    ok = sum(1 for _, o, _ in _results if o)
    print("-" * 56)
    print(f"RESULT: {ok}/{len(_results)} checks passed" + ("  — ALL GOOD" if ok == len(_results) else "  — FAILURES ABOVE"))
    return 0 if ok == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())