"""Draftomatic — template article generator. Stdlib only, no network, no LLM."""
import datetime
import random
import re

MIN_WORDS, MAX_WORDS = 600, 1000

# Varied phrasing pools: variation i picks pool[i % len] so "regenerate" truly rewrites.
INTROS = [
    "If you own a home, {kw} is one of those jobs you know you should stay on top of, and yet it keeps sliding to "
    "the bottom of the list. That is exactly why {biz} put this guide together: we handle {ind} work every day, and "
    "we wrote down the questions homeowners ask us most, so you get answers before you pick up the phone.",
    "Most homeowners meet {ind} problems the same way: something looks off on a Saturday morning, and by the time "
    "you get around to it, the job has grown. {biz} built this guide to break that cycle. Here is what {kw} really "
    "involves, what it should cost, and when to call a crew instead of a hardware store.",
    "Ask our crew at {biz} what surprises new clients most about {kw}, and you will hear the same thing: how much "
    "the outcome depends on doing small things early. This guide is the short version of what we tell every "
    "homeowner before the first visit.",
]
COSTS = [
    "Pricing for {kw} depends on four things: the size of the property, the condition it is in when we start, the "
    "materials involved, and how quickly you need it done. {biz} quotes every job up front, so the number you "
    "approve is the number you pay. When you compare bids, make sure each one covers the same scope; a cheaper "
    "quote that skips steps usually costs more in the end.",
    "What does {kw} cost? Honest answer: it depends on scope, access, materials, and timing. What should never "
    "depend is transparency. {biz} writes the full price into the scope before work starts, and change orders only "
    "happen when you approve them in writing. That single policy saves homeowners more money than any discount.",
    "Budget talk, plainly: small {ind} jobs are usually billed at a flat rate, larger projects by the day with "
    "materials itemized. {biz} recommends getting two or three bids, checking that each one names the same tasks, "
    "and weighing the guarantee as heavily as the price.",
]
MISTAKES = [
    "The most common mistake we see is waiting too long. Small {ind} problems compound: a minor issue in spring "
    "becomes an expensive repair by fall. The second is hiring on price alone. Ask any provider whether they are "
    "licensed and insured, what the quote includes, and whether they guarantee the work. {biz} answers all three "
    "in writing before we start.",
    "Three mistakes account for most of the emergency calls we get at {biz}: deferring small fixes, buying the "
    "cheapest bid, and skipping the written scope. A ten-minute phone script (license, insurance, guarantee, "
    "exclusions) filters out most of the providers who create those emergencies.",
]
DIY = [
    "Some {kw} tasks are genuinely safe to DIY, and we will tell you when they are. The line is usually equipment "
    "and risk. If a job needs specialized machinery, takes a full crew a day or more, or has any safety exposure, "
    "hire it out. Our rule of thumb at {biz}: if you have to buy a tool you will use twice a year, the pro visit "
    "is already cheaper.",
    "The DIY question is about time and risk, not skill. Homeowners routinely handle the light, low-risk end of "
    "{kw} themselves, and that is fine. Where {biz} draws the line: anything above shoulder height, anything "
    "needing rented machinery, and anything where a mistake damages the property. Those pay for themselves.",
]
PROCESS = [
    "Working with {biz} is deliberately boring. You request a visit, we confirm a two-hour arrival window, and you "
    "get a written scope with the price before anyone touches a tool. Crews check in when they arrive and when "
    "they leave, photos are included in the wrap-up note, and follow-ups are scheduled automatically so nothing "
    "slips through.",
    "Our process at {biz} is built for people with no time to babysit a project. One request form, one confirmation "
    "text, one written scope. You approve the plan from your phone; the crew handles the rest and sends photo "
    "proof when the job is done. Most clients never rearrange a single workday.",
]
SEASONS = [
    "{ind_t} needs change with the season. Spring is for cleanup and catching winter damage early, summer is "
    "maintenance mode, fall is preparation, and winter is when small problems get expensive. Homeowners who book a "
    "standing seasonal slot with {biz} spend less over the year than the ones who call only when something breaks.",
    "Timing is the cheapest lever in {ind_t}. A one-hour spring check catches what a full-day fall repair would "
    "have cost. {biz} schedules seasonal visits automatically for autopilot clients, which is also why their "
    "annual spend runs lower than on-call clients.",
]
FAQS = [
    "<strong>How far ahead should I book?</strong> Two to three weeks is comfortable; we hold emergency slots "
    "daily. <strong>Do you guarantee work?</strong> Yes, {biz} stands behind every job in writing. <strong>Do I "
    "need to be home?</strong> No; we text photo updates instead. <strong>What areas do you serve?</strong> The "
    "metro area and surrounding suburbs; the request form confirms your address instantly.",
    "<strong>What does a first visit include?</strong> A walk-through, photos, and a written scope with pricing; "
    "no obligation. <strong>Are you licensed and insured?</strong> Yes, certificates come with every quote from "
    "{biz}. <strong>Can I schedule recurring visits?</strong> Yes; recurring clients get priority slots and a "
    "standing seasonal plan.",
]
CONCLUSIONS = [
    "A well-maintained property is not about finding one magical weekend a year; it is about a short, repeatable "
    "routine. {biz} built this guide so you could get that routine in one read. Book a visit, approve the scope, "
    "and get your {kw} handled by a crew that does it every day.",
    "The takeaway from {biz} is simple: small, scheduled attention beats big, panicked repairs. Pick a date, get "
    "the written scope, and let the routine do the work. Your weekends are worth more than the difference between "
    "a rushed DIY job and professional work that lasts.",
]


def _slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "article"


def _fill(pools, key, variation, **ctx):
    pool = pools[key]
    return pool[variation % len(pool)].format(**ctx)


def generate(topic, connected, variation=0):
    rng = random.Random(f"{topic.get('keyword')}|{topic.get('title')}|{variation}")
    biz = connected.get("name") or "Peak Lawn & Landscape"
    industry = connected.get("industry") or "home service"
    title = topic.get("title") or "Your guide"
    kw = topic.get("keyword") or industry
    v = variation
    ctx = dict(biz=biz, ind=industry, ind_t=industry.capitalize(), kw=kw)

    h2s = ["What the work involves", "What drives cost", "Mistakes to avoid", "DIY vs hiring a pro",
           "Our process, step by step", "Seasonal timing", "FAQ"]
    h2s_v = [rng.choice(["About", "Understanding", "Inside"]) + " " + h2s[0]] + h2s[1:]
    if v % 2 == 1:
        h2s_v = h2s_v[::-1]  # section order variation, keeps intro/conclusion at ends

    paras = [
        _fill(INTROS, None, v, **ctx) if False else INTROS[v % len(INTROS)].format(**ctx),
        f"Most people are surprised by how much goes into professional {industry} work. A typical visit includes an "
        f"on-site assessment, a written scope, and a schedule that fits around your week. {biz} crews show up with "
        f"the right equipment, protect the work area, and walk the property with you when the job is done. The goal "
        f"is simple: the work is done once, done right, and you did not have to rearrange your life for it. "
        + (f"Typical scope items include the {kw} itself plus the prep and cleanup around it, so you are not left "
           f"with a half-touched project." if v % 2 else
           f"Every visit ends the same way: photos, a short summary, and a clear answer on what (if anything) needs "
           f"a follow-up."),
        COSTS[v % len(COSTS)].format(**ctx),
        DIY[v % len(DIY)].format(**ctx) if v % 2 else MISTAKES[v % len(MISTAKES)].format(**ctx),
        (MISTAKES[v % len(MISTAKES)].format(**ctx) if v % 2 else DIY[v % len(DIY)].format(**ctx)),
        PROCESS[v % len(PROCESS)].format(**ctx),
        SEASONS[v % len(SEASONS)].format(**ctx),
        FAQS[v % len(FAQS)].format(**ctx),
        CONCLUSIONS[v % len(CONCLUSIONS)].format(**ctx),
    ]
    heads = h2s_v[:7]
    parts = [f"<p>{paras[0]}</p>"]
    for h2, p in zip(heads, paras[1:8]):
        parts.append(f"<h2>{h2}</h2><p>{p}</p>")
    parts.append(f"<p>{paras[8]}</p>")
    body = "\n".join(parts)
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    if words > MAX_WORDS:  # band enforcement: trim last sentence-ish chunk
        while words > MAX_WORDS and len(parts) > 2:
            parts.pop()
            body = "\n".join(parts)
            words = len(re.sub(r"<[^>]+>", " ", body).split())
    if words < MIN_WORDS:
        extra = (f" A final note from the crew at {biz}: the homeowners who are happiest with {kw} are the ones who "
                 f"treat it like any other part of the house, on a schedule instead of on an emergency basis. If it "
                 f"has been more than a year since the last look, that is the sign to book one. The visit is short, "
                 f"the scope is written, and the follow-up plan costs nothing to set up.") * 2
        body += f"<p>{extra}</p>"
        words = len(re.sub(r"<[^>]+>", " ", body).split())

    art = {
        "id": int(datetime.datetime.utcnow().timestamp() * 1000) + variation,  # ms precision: fast generate loops can't collide
        "title": title,
        "slug": _slugify(title),
        "meta_title": f"{title} | {biz}",
        "meta_description": (f"A practical {industry} guide from {biz}: what {kw} involves, what it costs, and how "
                             f"to avoid the mistakes that turn small jobs into big repairs."),
        "body_html": body,
        "word_count": words,
        "keyword": kw,
        "variation": variation,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    return art


def body_word_count(html):
    return len(re.sub(r"<[^>]+>", " ", html).split())