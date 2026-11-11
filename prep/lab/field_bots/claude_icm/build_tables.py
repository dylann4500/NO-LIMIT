"""Offline builder for preflop.json (not imported by the bot).
Computes a 169-class preflop ranking and heads-up all-in equity of every class vs the top-X% ranges."""
import json, os, eval7

RANKS = "23456789TJQKA"
SUITS = "cdhs"
GRID = [2, 3, 5, 7, 10, 13, 16, 20, 25, 30, 35, 40, 50, 60, 70, 85, 100]


def classes():
    out = []
    for i in range(12, -1, -1):
        for j in range(i, -1, -1):
            if i == j:
                out.append(RANKS[i] * 2)
            else:
                out.append(RANKS[i] + RANKS[j] + "s")
                out.append(RANKS[i] + RANKS[j] + "o")
    return out


def combos(cl):
    a, b = cl[0], cl[1]
    res = []
    if a == b:
        for x in range(4):
            for y in range(x + 1, 4):
                res.append((a + SUITS[x], b + SUITS[y]))
    elif cl[2] == "s":
        for s in SUITS:
            res.append((a + s, b + s))
    else:
        for s in SUITS:
            for t in SUITS:
                if s != t:
                    res.append((a + s, b + t))
    return res


CL = classes()
CB = {c: [(eval7.Card(x), eval7.Card(y)) for x, y in combos(c)] for c in CL}


def top_range(order, pct):
    want = 1326 * pct / 100.0
    hands, n = [], 0
    for c in order:
        if n >= want:
            break
        w = min(1.0, (want - n) / len(CB[c]))
        for cc in CB[c]:
            hands.append((cc, w))
        n += len(CB[c])
    hr = eval7.HandRange("AA")
    hr.hands = hands
    return hr


def eq_vs(cl, hr, iters):
    tot = 0.0
    cbs = CB[cl]
    # use a few representative combos (suit patterns matter little)
    reps = cbs[:: max(1, len(cbs) // 3)][:3]
    for h in reps:
        tot += eval7.py_hand_vs_range_monte_carlo(list(h), hr, [], iters)
    return tot / len(reps)


def main():
    rnd = top_range(CL, 100)
    e100 = {c: eq_vs(c, rnd, 20000) for c in CL}
    order0 = sorted(CL, key=lambda c: -e100[c])
    t20 = top_range(order0, 20)
    e20 = {c: eq_vs(c, t20, 20000) for c in CL}
    # final ordering: blend of raw strength (vs random) and playability vs good ranges
    score = {c: 0.5 * e100[c] + 0.5 * e20[c] for c in CL}
    order = sorted(CL, key=lambda c: -score[c])
    table = {}
    for p in GRID:
        hr = top_range(order, p)
        table[p] = [round(eq_vs(c, hr, 12000), 4) for c in CL]
        print("grid", p, flush=True)
    out = {"classes": CL, "order": order, "grid": GRID, "eq": [table[p] for p in GRID]}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "preflop.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("top 20:", order[:20])
    print("ranks of some:", {c: order.index(c) for c in ["72o", "T9s", "A2o", "K9o", "22", "AKo", "Q8s", "54s"]})


if __name__ == "__main__":
    main()
