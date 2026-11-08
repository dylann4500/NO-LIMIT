"""Generate the README images in assets/readme/ (light and dark variants of each).

    python3 tools/readme_assets.py

results-{light,dark}.svg  points per table by round (numbers from the README results table / docs/STEERING.md)
variant-{light,dark}.svg  how flop_discard_reveal works, using a hand the v10 bot actually plays this way

Standard library only. Colors: GitHub's Primer text/border tokens, and a two-step blue
(practice recedes, scored stands out) checked for contrast against GitHub's light and dark backgrounds.
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "readme"
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

THEMES = {
    "light": dict(text="#1f2328", muted="#59636e", grid="#d1d9e0", axis="#818b98",
                  practice="#86b6ef", scored="#2a78d6", card_edge="#818b98", back="#2a78d6"),
    "dark": dict(text="#f0f6fc", muted="#9198a1", grid="#3d444d", axis="#656c76",
                 practice="#184f95", scored="#3987e5", card_edge="#3d444d", back="#3987e5"),
}

# (round, bot, points per table); None = not recorded
ROUNDS = [
    ("P1", "m10", 14.61), ("P2", "v3", 18.87), ("P3", "v3b", 19.02), ("P4", "v4", 9.17),
    ("S1 ×1", "v3b", 18.10), ("S2 ×2", "v5r", 16.73), ("S3 ×3", "v6", 19.05),
    ("S4 ×4", "v7", 18.26), ("S5 ×5", "v9s", 17.95), ("S6 ×6", "v10", None),
]
CALLOUTS = {"P1": "14.61 · first bot", "P4": "9.17 · rolled back", "S3 ×3": "19.05 · 3rd in round"}


def text(x, y, s, size=13, fill="#000", weight=400, anchor="start"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{s}</text>')


def bar(x, w, top, base, r, fill):
    """Bar with 4px rounded data end, square at the baseline."""
    return (f'<path d="M{x:.1f},{base:.1f} V{top + r:.1f} Q{x:.1f},{top:.1f} {x + r:.1f},{top:.1f} '
            f'H{x + w - r:.1f} Q{x + w:.1f},{top:.1f} {x + w:.1f},{top + r:.1f} V{base:.1f} Z" fill="{fill}"/>')


def svg(w, h, title, desc, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d" font-family="{FONT}">\n'
            f'<title id="t">{title}</title><desc id="d">{desc}</desc>\n' + "\n".join(body) + "\n</svg>\n")


def results(t):
    W, H = 940, 390
    left, right, top, base = 58, 920, 92, 292
    ymax = 20.0
    y = lambda v: base - (base - top) * v / ymax
    b = [text(left - 46, 30, "Points per table, by round", 17, t["text"], 600),
         text(left - 46, 52, "8-seat sit-and-gos paying 50/30/20 points. Final standing: 6th of 148.", 13, t["muted"])]
    # legend (top right)
    lx = right - 196
    for i, (name, key) in enumerate((("Practice", "practice"), ("Scored", "scored"))):
        x = lx + i * 100
        b.append(f'<rect x="{x}" y="20" width="12" height="12" rx="2" fill="{t[key]}"/>')
        b.append(text(x + 18, 31, name, 13, t["text"]))
    # grid + y labels
    for v in (0, 5, 10, 15, 20):
        yy = y(v)
        if v:
            b.append(f'<line x1="{left}" x2="{right}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{t["grid"]}" '
                     f'stroke-width="1" stroke-dasharray="3 4"/>')
        b.append(text(left - 10, yy + 4, str(v), 12, t["muted"], anchor="end"))
    # slots: 4 practice, gap, 6 scored
    gap = 44
    slot = (right - left - gap) / 10
    bw = 46
    centers = []
    for i, (rnd, bot, pts) in enumerate(ROUNDS):
        cx = left + slot * (i + 0.5) + (gap if i >= 4 else 0)
        centers.append(cx)
        fill = t["practice"] if i < 4 else t["scored"]
        if pts is None:
            b.append(text(cx, base - 24, "not", 11, t["muted"], anchor="middle"))
            b.append(text(cx, base - 10, "recorded", 11, t["muted"], anchor="middle"))
        else:
            b.append(bar(cx - bw / 2, bw, y(pts), base, 4, fill))
        if rnd in CALLOUTS:
            b.append(text(cx, y(pts) - 9, CALLOUTS[rnd], 12, t["text"], 600, "middle"))
        b.append(text(cx, base + 20, rnd, 12, t["text"], 600, "middle"))
        b.append(text(cx, base + 37, bot, 12, t["muted"], anchor="middle"))
    b.append(f'<line x1="{left}" x2="{right}" y1="{base}" y2="{base}" stroke="{t["axis"]}" stroke-width="1"/>')
    # group brackets
    for lo, hi, label in ((0, 3, "Practice rounds"), (4, 9, "Scored rounds (×weight)")):
        x1, x2, by = centers[lo] - bw / 2, centers[hi] + bw / 2, base + 52
        b.append(f'<path d="M{x1:.1f},{by - 5} V{by} H{x2:.1f} V{by - 5}" fill="none" stroke="{t["axis"]}" stroke-width="1"/>')
        b.append(text((x1 + x2) / 2, by + 20, label, 13, t["muted"], anchor="middle"))
    desc = "; ".join(f"{r} {bot}: {p if p is not None else 'not recorded'}" for r, bot, p in ROUNDS)
    return svg(W, H, "Points per table by round", desc, b)


def card(x, y, w, h, rank, suit, t, fade=False, label=None, dashed=False):
    red = suit in "♥♦"
    op = ' opacity="0.35"' if fade else ""
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    g = [f'<g{op}>',
         f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#ffffff" stroke="{t["card_edge"]}" stroke-width="1.5"{dash}/>',
         text(x + 8, y + 22, rank, 19, "#cf222e" if red else "#1f2328", 700),
         text(x + w / 2, y + h - 14, suit, 28, "#cf222e" if red else "#1f2328", 400, "middle")]
    if fade:
        g.append(f'<line x1="{x + 6}" y1="{y + h - 6}" x2="{x + w - 6}" y2="{y + 6}" stroke="#cf222e" stroke-width="2"/>')
    g.append("</g>")
    if label:
        g.append(text(x + w / 2, y + h + 22, label, 12, t["muted"], 600, "middle"))
    return "\n".join(g)


def back(x, y, w, h, t, label=None):
    g = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{t["back"]}"/>',
         f'<rect x="{x + 5}" y="{y + 5}" width="{w - 10}" height="{h - 10}" rx="3" fill="none" stroke="#ffffff" stroke-opacity="0.55" stroke-width="1"/>',
         text(x + w / 2, y + h / 2 + 9, "?", 26, "#ffffff", 700, "middle")]
    if label:
        g.append(text(x + w / 2, y + h + 22, label, 12, t["muted"], 600, "middle"))
    return "\n".join(g)


def arrow(x1, x2, yy, t):
    return (f'<line x1="{x1}" y1="{yy}" x2="{x2 - 8}" y2="{yy}" stroke="{t["axis"]}" stroke-width="2"/>'
            f'<path d="M{x2},{yy} l-10,-6 v12 z" fill="{t["axis"]}"/>')


def variant(t):
    W, H = 940, 262
    cw, ch, cg = 56, 78, 12
    cy = 104
    cols = [(20, "1 · Deal", "3 hole cards; normal preflop betting"),
            (340, "2 · Flop: discard 1, expose 1", "board  A♥ 8♣ 2♠"),
            (660, "3 · What opponents see", "every opponent is visible card + hidden card")]
    b = []
    for x, title, sub in cols:
        b.append(text(x + 130, 32, title, 15, t["text"], 600, "middle"))
        b.append(text(x + 130, 54, sub, 13, t["muted"], anchor="middle"))
    start = lambda x, n: x + (260 - (n * cw + (n - 1) * cg)) / 2
    s = start(20, 3)
    for i, (r, su) in enumerate((("A", "♠"), ("K", "♦"), ("7", "♣"))):
        b.append(card(s + i * (cw + cg), cy, cw, ch, r, su, t))
    s = start(340, 3)
    b.append(card(s, cy, cw, ch, "A", "♠", t, label="hidden", dashed=True))
    b.append(card(s + cw + cg, cy, cw, ch, "K", "♦", t, label="shown"))
    b.append(card(s + 2 * (cw + cg), cy, cw, ch, "7", "♣", t, fade=True, label="discarded"))
    s = start(660, 2)
    b.append(card(s, cy, cw, ch, "K", "♦", t, label="K♦"))
    b.append(back(s + cw + cg, cy, cw, ch, t, label="any unseen card"))
    b.append(arrow(288, 334, cy + ch / 2, t))
    b.append(arrow(608, 654, cy + ch / 2, t))
    b.append(text(W / 2, H - 22, "v10 keeps A♠ K♦ (best Monte Carlo equity), then shows the card that doesn't pair the board, so its top pair stays hidden.",
                  13, t["muted"], anchor="middle"))
    return svg(W, H, "How flop_discard_reveal works",
               "Dealt A spades, K diamonds, 7 clubs. On a flop of A hearts, 8 clubs, 2 spades the bot discards the 7, "
               "shows the K and hides the A. Opponents see the K plus one unknown card.", b)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for mode, t in THEMES.items():
        (OUT / f"results-{mode}.svg").write_text(results(t), encoding="utf-8")
        (OUT / f"variant-{mode}.svg").write_text(variant(t), encoding="utf-8")
    print("wrote", ", ".join(sorted(p.name for p in OUT.glob("*.svg"))))
