"""Draftomatic — append-only event metrics (stdlib only).

Every tester action lands as one JSON line in data/metrics.jsonl. The
/api/metrics endpoint aggregates them into per-session funnels — connect event
starts a session — so the validated-learning report cites real collected data
instead of recollection.

Env: DRAFTO_DISABLE_LLM irrelevant here; metrics are always on.
"""
import datetime
import json
import os
import threading

_LOCK = threading.Lock()


def _path():
    if os.environ.get("DRAFTO_METRICS_PATH"):  # test isolation: suite points this at a temp file
        return os.environ["DRAFTO_METRICS_PATH"]
    import store
    return os.path.join(store.data_root(), "data", "metrics.jsonl")


def log(event, **fields):
    rec = {"ts": datetime.datetime.utcnow().isoformat() + "Z", "event": event}
    rec.update({k: v for k, v in fields.items() if v is not None})
    with _LOCK:
        try:
            os.makedirs(os.path.dirname(_path()), exist_ok=True)
            with open(_path(), "a") as f:
                f.write(json.dumps(rec) + "\n")
        except OSError:
            pass  # metrics must never break a request (read-only FS etc.)
    return rec


def read_all():
    try:
        with open(_path()) as f:
            return [json.loads(line) for line in f if line.strip()]
    except (OSError, json.JSONDecodeError):
        return []


def summary():
    """Aggregate sessions: a 'connect' event starts one. Returns headline numbers
    plus per-session funnel rows for the report."""
    events = read_all()
    sessions = []
    cur = None
    for e in events:
        if e["event"] == "connect":
            cur = {"started": e["ts"], "industry": e.get("industry"), "has_url": e.get("has_url"),
                   "topics_generated": 0, "drafts": 0, "first_draft_seconds": None,
                   "words_total": 0, "regenerations": 0, "publishes": 0,
                   "failed_publishes": 0, "autopilot_final": None}
            sessions.append(cur)
        elif cur is None:
            continue  # pre-connect events (shouldn't happen) are ignored
        ev = e["event"]
        if ev == "topics_generated":
            cur["topics_generated"] = e.get("count") or 0
        elif ev == "article_generated":
            cur["drafts"] += 1
            cur["words_total"] += e.get("words") or 0
            if cur["first_draft_seconds"] is None:
                cur["first_draft_seconds"] = e.get("seconds")
        elif ev == "article_regenerated":
            cur["regenerations"] += 1
        elif ev == "publish":
            if e.get("ok"):
                cur["publishes"] += 1
            else:
                cur["failed_publishes"] += 1
        elif ev == "autopilot":
            cur["autopilot_final"] = bool(e.get("on"))
    totals = {
        "sessions": len(sessions),
        "drafts_generated": sum(s["drafts"] for s in sessions),
        "avg_words": (sum(s["words_total"] for s in sessions) // max(1, sum(s["drafts"] for s in sessions))) or 0,
        "publishes": sum(s["publishes"] for s in sessions),
        "autopilot_left_on": sum(1 for s in sessions if s["autopilot_final"] is True),
        "autopilot_turned_off": sum(1 for s in sessions if s["autopilot_final"] is False),
    }
    return {"sessions": sessions, "totals": totals, "raw_event_count": len(events)}