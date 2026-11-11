"""Offline table builder (run once; agent.py only reads the output).

Writes pf_tables.npz next to this file:
  eq  : 169x169 heads-up all-in equity of class i vs class j (card removal handled, symmetrised)
  mw  : 169x3 equity vs 2, 3 and 5 random hands (used for the preflop hand ranking)
Class index: pairs 0..12 (22..AA), then suited (hi,lo), then offsuit (hi,lo) in the order of classes().
"""
import os, random, sys
from multiprocessing import Pool
import numpy as np
import eval7

R = "23456789TJQKA"
S = "shdc"
CARDS = [eval7.Card(r + s) for r in R for s in S]  # index = rank*4 + suit


def classes():
    out = [(r, r, "p") for r in range(13)]
    out += [(h, l, "s") for h in range(13) for l in range(h)]
    out += [(h, l, "o") for h in range(13) for l in range(h)]
    return out


CLS = classes()


def class_combos(c):
    h, l, t = c
    res = []
    if t == "p":
        for a in range(4):
            for b in range(a + 1, 4):
                res.append((h * 4 + a, h * 4 + b))
    elif t == "s":
        for a in range(4):
            res.append((h * 4 + a, l * 4 + a))
    else:
        for a in range(4):
            for b in range(4):
                if a != b:
                    res.append((h * 4 + a, l * 4 + b))
    return res


COMBOS = [class_combos(c) for c in CLS]


def row(i, iters=5000, reps=3):
    rnd = random.Random(1000 + i)
    heroes = COMBOS[i][:]
    rnd.shuffle(heroes)
    heroes = heroes[:reps]
    out = np.zeros(169)
    for j in range(169):
        tot = 0.0
        n = 0
        for hc in heroes:
            vr = [((CARDS[a], CARDS[b]), 1.0) for a, b in COMBOS[j] if a not in hc and b not in hc]
            if not vr:
                continue
            tot += eval7.py_hand_vs_range_monte_carlo([CARDS[hc[0]], CARDS[hc[1]]], vr, [], iters)
            n += 1
        out[j] = tot / n if n else 0.5
    return out


def multiway(i, samples=6000):
    rnd = random.Random(5000 + i)
    res = []
    for k in (2, 3, 5):
        win = 0.0
        hc = COMBOS[i][rnd.randrange(len(COMBOS[i]))]
        deck = [c for c in range(52) if c not in hc]
        hero = [CARDS[hc[0]], CARDS[hc[1]]]
        for _ in range(samples):
            d = rnd.sample(deck, 5 + 2 * k)
            board = [CARDS[x] for x in d[:5]]
            hv = eval7.evaluate(hero + board)
            best = 0
            ties = 1
            for v in range(k):
                vv = eval7.evaluate([CARDS[d[5 + 2 * v]], CARDS[d[6 + 2 * v]]] + board)
                if vv > best:
                    best = vv
                    ties = 1
                elif vv == best:
                    ties += 1
            if hv > best:
                win += 1
            elif hv == best:
                win += 1.0 / (ties + 1)
        res.append(win / samples)
    return res


if __name__ == "__main__":
    with Pool(14) as p:
        rows = p.map(row, range(169))
        mw = p.map(multiway, range(169))
    eq = np.array(rows)
    eq = (eq + (1 - eq.T)) / 2
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pf_tables.npz")
    np.savez_compressed(out, eq=eq.astype(np.float32), mw=np.array(mw, dtype=np.float32))
    print("saved", out, eq.shape)
