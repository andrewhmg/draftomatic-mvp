"""Draftomatic — Ollama LLM backend for topic + article generation. Stdlib only.

Talks to the local Ollama OpenAI-compatible endpoint (ollama-launch proxy).
glm-5.3-flash:cloud is a reasoning model: its thinking arrives in a separate
`reasoning` field on /v1, so `content` is clean — but guard the parse anyway
(strip code fences, retry once on bad JSON). Template engines in content.py /
topics_gen.py remain the fallback whenever the LLM path errors out.

Env:
  DRAFTO_DISABLE_LLM=1  -> force template mode (offline tests, template-only demos)
  OLLAMA_URL            -> override endpoint (default http://127.0.0.1:11434/v1)
  OLLAMA_MODEL          -> override model   (default glm-5.3-flash:cloud)
"""
import json
import os
import re
import urllib.request

URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/v1/chat/completions")
MODEL = os.environ.get("OLLAMA_MODEL", "glm-5.3-flash:cloud")
TIMEOUT = 240  # full article took 35s in probe; leave headroom for queueing behind other calls


class LLMError(Exception):
    pass


def enabled():
    """LLM on unless disabled, or on Vercel (serverless can't reach localhost Ollama
    — a 240s hang per request there would be worse than the template fallback)."""
    return not os.environ.get("DRAFTO_DISABLE_LLM") and not os.environ.get("VERCEL")


def _chat(messages, max_tokens=24000):
    payload = json.dumps({"model": MODEL, "messages": messages,
                          "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        d = json.loads(r.read().decode("utf-8", "ignore"))
    content = (d["choices"][0]["message"] or {}).get("content") or ""
    return content


def _parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S | re.M).strip()
    m = re.search(r"\{.*\}", t, flags=re.S)  # tolerate preamble before the object
    if not m:
        raise LLMError("no JSON object in model output")
    return json.loads(m.group(0))


def _ask_json(system, user, max_tokens=24000):
    """One LLM call whose content must parse as JSON. Retries once on bad JSON."""
    last_err = None
    for attempt in (1, 2):
        suffix = "" if attempt == 1 else ("\n\nIMPORTANT: your previous reply was not valid JSON. "
                                          "Output the raw JSON object only — no prose, no markdown fences.")
        try:
            return _parse_json(_chat([{"role": "system", "content": system},
                                      {"role": "user", "content": user + suffix}],
                                     max_tokens=max_tokens))
        except (LLMError, json.JSONDecodeError, KeyError, IndexError, OSError) as e:
            last_err = e
    raise LLMError(f"LLM JSON call failed twice: {last_err}")


# ---------- Topics ----------

def generate_topics(industry, business_name, n=12):
    sys_p = "You are an SEO content strategist for small-business blogs. Output ONLY valid JSON."
    user_p = (
        f'Business: "{business_name}" — a {industry} business.\n'
        f"Propose {n} blog post topics its customers would actually search for.\n"
        'Return ONLY valid JSON: {"topics": [{"title": "...", "angle": "one-line angle", '
        '"keyword": "target seo keyword (2-4 words)"}]} with exactly '
        f"{n} entries, no duplicates."
    )
    d = _ask_json(sys_p, user_p, max_tokens=4000)
    out, seen = [], set()
    for t in d.get("topics", []):
        title = str(t.get("title") or "").strip()
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        out.append({"title": title[:120],
                    "angle": str(t.get("angle") or "")[:160],
                    "keyword": str(t.get("keyword") or industry)[:60]})
        if len(out) >= n:
            break
    if len(out) < 6:
        raise LLMError(f"LLM returned only {len(out)} usable topics")
    return out


# ---------- Articles ----------

def generate_article(topic, connected, variation=0):
    """Returns the article dict (same shape content.generate makes) + generator tag.

    Raises LLMError on failure — caller falls back to the template engine."""
    import datetime

    from content import _slugify, body_word_count

    biz = connected.get("name") or "Peak Lawn & Landscape"
    industry = connected.get("industry") or "home service"
    title = topic.get("title") or "Your guide"
    kw = topic.get("keyword") or industry
    fresh = ("" if not variation else
             f'\nNote: a previous draft of this topic used the headline "{topic.get("last_headline", title)}". '
             "Take a clearly different angle and headline this time.")

    sys_p = "You are a ghostwriter for small-business blogs. Output ONLY valid JSON with no markdown fences."
    user_p = (
        f'Blog article for "{biz}" (a {industry} business).\n'
        f'Topic: "{title}". Target keyword: "{kw}".{fresh}\n'
        "Return ONLY valid JSON with exactly these keys:\n"
        ' "headline" (catchy, <=70 chars), "slug" (lowercase-hyphens, <=60 chars),\n'
        ' "meta_title" (<=60 chars), "meta_description" (<=155 chars),\n'
        ' "intro" (one paragraph, 60-90 words),\n'
        ' "sections" (array of 5-6 objects, each {"h2": "section heading", "text": '
        "one practical 80-130 word paragraph}),\n"
        ' "conclusion" (one paragraph, 50-80 words, soft call to action mentioning '
        f'"{biz}").\n'
        f"Total body 650-850 words. Concrete, specific advice for the business's customers; "
        "no fluff, no repetition, never mention being an AI or a model."
    )
    d = _ask_json(sys_p, user_p)

    sections = d.get("sections") or []
    if not isinstance(sections, list) or len(sections) < 3:
        raise LLMError("model returned too few sections")
    parts = [f"<p>{d['intro']}</p>"]
    for s in sections:
        h = re.sub(r"<[^>]+>", "", str(s.get("h2") or "")).strip() or "More detail"
        p = re.sub(r"<[^>]+>", "", str(s.get("text") or "")).strip()
        if p:
            parts.append(f"<h2>{h}</h2><p>{p}</p>")
    parts.append(f"<p>{d['conclusion']}</p>")
    body = "\n".join(parts)
    words = body_word_count(body)

    art = {
        "id": int(datetime.datetime.utcnow().timestamp() * 1000) + variation,
        "title": str(d.get("headline") or title),
        "slug": _slugify(d.get("slug") or title),
        "meta_title": str(d.get("meta_title") or title)[:60],
        "meta_description": str(d.get("meta_description") or "")[:155],
        "body_html": body,
        "word_count": words,
        "keyword": kw,
        "variation": variation,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "generator": "AI (glm via Ollama, local)",
    }
    return art