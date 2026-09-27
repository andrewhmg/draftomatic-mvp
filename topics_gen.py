"""Draftomatic — topic generator (stdlib only). Deterministic templates per industry."""
import random

BASE_ANGLES = [
    "how it works, what to expect",
    "pricing explained: what drives cost",
    "mistakes homeowners make (and how to avoid them)",
    "seasonal tips from our crew",
    "before-and-after story",
    "DIY vs hiring a pro",
    "what to look for when choosing a provider",
    "our process step by step",
    "questions to ask before you book",
    "signs it's time to call a pro",
    "maintenance checklist you can follow",
    "how we keep projects on time and on budget",
]


def generate(industry, business_name, n=12):
    rng = random.Random(f"{industry}|{business_name}")
    topics = []
    for i, angle in enumerate(BASE_ANGLES[:n]):
        title = f"{angle.split(',')[0].split(':')[0].capitalize()} — {business_name} guide"
        kw = f"{industry} {['tips', 'cost', 'guide', 'checklist', 'help'][i % 5]}"
        topics.append({
            "id": i + 1,
            "title": f"{angle.split(':')[0].capitalize()} for {industry} homeowners",
            "angle": angle,
            "keyword": kw,
            "priority": i + 1,
            "approved": False,
        })
    return topics