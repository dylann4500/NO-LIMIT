"""Build-time Monte Carlo for 3-card preflop strength (Bay Area variant).

For every canonical 3-card class (suit isomorphism), deal a flop, both players keep the best
2 of 3 on it (made hand), run out, compare. Pass 1: equity vs a random 3-card hand -> pct
(fraction of all 22,100 starting hands at least as strong). Pass 2: equity vs villains drawn
from the top-w of that ranking for w in WIDTHS.
Writes tables_bayarea.json next to this file. Not imported by the bot.
"""

import itertools
import json
import multiprocessing as mp
import os
import random
import sys

import eval7

RANKS = "23456789TJQKA"
SUITS = "shdc"
DECK = [r + s for r in RANKS for s in SUITS]
PERMS = list(itertools.permutations(SUITS))
WIDTHS = [0.05, 0.10, 0.20, 0.35, 0.50, 1.0]
PAIRS = ((0, 1), (0, 2), (1, 2))


def canon(cards):
    best = None
    for p in PERMS:
        m = dict(zip(SUITS, p))
        k = tuple(sorted((c[0] + m[c[1]] for c in cards),
                         key=lambda c: (RANKS.index(c[0]), c[1]), reverse=True))
        if best is None or k < best:
            best = k
    return best


def best_keep(c3, flop):
    best = -1
    bk = None
    for i, j in PAIRS:
        v = eval7.evaluate([c3[i], c3[j]] + flop)
        if v > best:
            best, bk = v, [c3[i], c3[j]]
    return bk


def sim(args):
    key, n, seed, villains = args  # villains: None (random) or list of 3-card str tuples
    rng = random.Random(seed)
    hero = [eval7.Card(c) for c in key]
    hs = set(key)
    rest = [c for c in DECK if c not in hs]
    restc = {c: eval7.Card(c) for c in rest}
    vil_pool = None
    if villains is not None:
        vil_pool = [v for v in villains if not (hs & set(v))]
    win = 0.0
    for _ in range(n):
        if vil_pool is None:
            s = rng.sample(rest, 8)
            vil = [restc[c] for c in s[:3]]
            other = s[3:]
        else:
            v = vil_pool[rng.randrange(len(vil_pool))]
            vil = [restc[c] for c in v]
            vs = set(v)
            other = rng.sample([c for c in rest if c not in vs], 5)
        flop = [restc[c] for c in other[:3]]
        tr = [restc[c] for c in other[3:5]]
        hk = best_keep(hero, flop)
        vk = best_keep(vil, flop)
        a = eval7.evaluate(hk + flop + tr)
        b = eval7.evaluate(vk + flop + tr)
        win += 1.0 if a > b else 0.5 if a == b else 0.0
    return key, win / n


def main():
    n1 = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    n2 = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    classes = {}
    for combo in itertools.combinations(DECK, 3):
        k = canon(combo)
        classes.setdefault(k, []).append(combo)
    keys = sorted(classes)
    print("classes", len(keys), file=sys.stderr)
    with mp.Pool(os.cpu_count()) as pool:
        eq1 = dict(pool.map(sim, [(k, n1, i, None) for i, k in enumerate(keys)], chunksize=8))
        # Percentile: fraction of all combos with equity >= this class's.
        order = sorted(keys, key=lambda k: -eq1[k])
        total = sum(len(classes[k]) for k in keys)
        pct = {}
        cum = 0
        for k in order:
            cum += len(classes[k])
            pct[k] = cum / total
        ranked_combos = [c for k in order for c in classes[k]]
        eqw = {k: [] for k in keys}
        for w in WIDTHS:
            if w >= 1.0:
                for k in keys:
                    eqw[k].append(eq1[k])
                continue
            top = ranked_combos[: max(50, int(w * total))]
            res = dict(pool.map(sim, [(k, n2, 10_000 + i, top) for i, k in enumerate(keys)],
                                chunksize=8))
            for k in keys:
                eqw[k].append(res[k])
            print("width", w, "done", file=sys.stderr)
    out = {
        "widths": WIDTHS,
        "classes": {"".join(k): [round(pct[k], 5), [round(x, 4) for x in eqw[k]]] for k in keys},
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables_bayarea.json")
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("wrote", path, os.path.getsize(path), file=sys.stderr)
    for k in order[:10] + order[len(order) // 2: len(order) // 2 + 5] + order[-5:]:
        print("".join(k), round(eq1[k], 3), round(pct[k], 4), file=sys.stderr)


if __name__ == "__main__":
    main()
