"""Draftomatic — cover image generator: 1200x630 SVG (Framer social-preview ratio). Stdlib only."""
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))

PALETTES = [
    ("#1b4332", "#2d6a4f"), ("#014f86", "#2a9d8f"), ("#3d348b", "#7678ed"),
    ("#7f5539", "#b08968"), ("#264653", "#e76f51"), ("#3a5a40", "#a3b18a"),
]


def generate_cover(title, article_id):
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "cover").lower()).strip("-")[:50] or "cover"
    c1, c2 = PALETTES[article_id % len(PALETTES)]
    t = (title or "Draftomatic").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    words = t.split()
    lines, cur = [], ""
    for w in words:  # word-boundary wrap, max ~26 chars/line, 4 lines
        if len(cur) + 1 + len(w) > 26 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
        if len(lines) == 4:
            break
    if cur and len(lines) < 4:
        lines.append(cur)
    tspans = "".join(
        f'<tspan x="80" y="{220 + i * 62}">{line}</tspan>' for i, line in enumerate(lines)
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>
  </linearGradient></defs>
  <rect width="1200" height="630" fill="url(#g)"/>
  <text x="80" y="120" font-family="Helvetica, Arial, sans-serif" font-size="30" letter-spacing="6" fill="#ffffff" opacity="0.85">DRAFTOMATIC</text>
  <text font-family="Georgia, serif" font-size="44" font-weight="bold" fill="#ffffff">{tspans}</text>
</svg>'''
    path = os.path.join(ROOT, "covers", f"{slug}.svg")
    with open(path, "w") as f:
        f.write(svg)
    rel = f"/covers/{slug}.svg"
    return path, rel