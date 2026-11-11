"""Offline generator for preflop.json (run once; the agent only reads the JSON).

usage: .venv/bin/python lab/field_bots/claude_default_d/gen_tables.py

Produces, for the 169 starting-hand classes:
  classes   : class names ("AA", "AKs", "AKo", ...), index order used everywhere
  combos    : number of combos per class (6 / 4 / 12)
  hu        : 169x169 heads-up all-in equity matrix (row hero vs column villain class)
  multi     : equity vs k random hands, k = 1..7
"""
import json, os, random, sys
from multiprocessing import Pool

import eval7

RANKS = "23456789TJQKA"
SUITS = "shdc"
CARD = {r + s: eval7.Card(r + s) for r in RANKS for s in SUITS}


def class_list():
    out = []
    for i in range(12, -1, -1):
        for j in range(12, -1, -1):
            a, b = RANKS[i], RANKS[j]
            if i == j:
                out.append(a + b)
            elif i > j:
                out.append(a + b + "s")
                out.append(a + b + "o")
    return out


CLASSES = class_list()


def combos_of(cls):
    a, b = cls[0], cls[1]
    res = []
    if len(cls) == 2:
        for x in range(4):
            for y in range(x + 1, 4):
                res.append((a + SUITS[x], b + SUITS[y]))
    elif cls[2] == "s":
        for x in range(4):
            res.append((a + SUITS[x], b + SUITS[x]))
    else:
        for x in range(4):
            for y in range(4):
                if x != y:
                    res.append((a + SUITS[x], b + SUITS[y]))
    return res


def hu_row(i):
    hero_cls = CLASSES[i]
    reps = combos_of(hero_cls)
    random.seed(1000 + i)
    reps = random.sample(reps, min(4, len(reps)))
    row = []
    for j, vc in enumerate(CLASSES):
        vlist = [((CARD[x], CARD[y]), 1.0) for x, y in combos_of(vc)]
        tot = 0.0
        n = 0
        for h in reps:
            hc = [CARD[h[0]], CARD[h[1]]]
            # eval7 skips conflicting villain combos; if every villain combo conflicts, skip rep
            live = [v for v in vlist if str(v[0][0]) not in h and str(v[0][1]) not in h]
            if not live:
                continue
            tot += eval7.py_hand_vs_range_monte_carlo(hc, live, [], 4000)
            n += 1
        row.append(round(tot / n, 4) if n else 0.5)
    return row


def multi_row(i):
    rng = random.Random(7 + i)
    cls = CLASSES[i]
    reps = combos_of(cls)
    out = []
    for k in range(1, 8):
        iters = 6000
        wins = 0.0
        for it in range(iters):
            h = reps[it % len(reps)]
            deck = [c for c in CARD if c not in h]
            draw = rng.sample(deck, 5 + 2 * k)
            board = [CARD[c] for c in draw[:5]]
            hv = eval7.evaluate([CARD[h[0]], CARD[h[1]]] + board)
            best = 0
            nbest = 0
            for o in range(k):
                ov = eval7.evaluate([CARD[draw[5 + 2 * o]], CARD[draw[6 + 2 * o]]] + board)
                if ov > best:
                    best, nbest = ov, 1
                elif ov == best:
                    nbest += 1
            if hv > best:
                wins += 1.0
            elif hv == best:
                wins += 1.0 / (nbest + 1)
        out.append(round(wins / iters, 4))
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with Pool(14) as p:
        hu = p.map(hu_row, range(169))
        multi = p.map(multi_row, range(169))
    combos = [len(combos_of(c)) for c in CLASSES]
    with open(os.path.join(here, "preflop.json"), "w") as f:
        json.dump({"classes": CLASSES, "combos": combos, "hu": hu, "multi": multi}, f, separators=(",", ":"))
    print("wrote", len(CLASSES))


if __name__ == "__main__":
    main()
