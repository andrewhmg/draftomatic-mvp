"""Draftomatic MVP — JSON persistence. Stdlib only."""
import json, os, threading

_LOCK = threading.Lock()


def _path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "state.json")


def load():
    try:
        with open(_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"connected": None, "topics": [], "articles": [], "published": [],
                "statuslog": [], "autopilot": True, "paused": False}


def save(state):
    p = _path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, p)  # atomic write


def update(fn):
    """Read-modify-write under a lock; fn mutates the state dict in place."""
    with _LOCK:
        s = load()
        fn(s)
        save(s)
        return s