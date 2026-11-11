"""Heads-up jam-or-fold Nash charts by fictitious play. Output: for each of 169 hand classes, the largest stack
in big blinds at which the small blind jams, and at which the big blind calls a jam. Variant-aware via pk."""
import json, os, random, sys, time
from itertools import combinations
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk

RK = "23456789TJQKA"


def _class(a, b):
    ra, rb = a >> 2, b >> 2
    if ra < rb:
        ra, rb = rb, ra
    if ra == rb:
        return RK[ra] * 2
    return RK[ra] + RK[rb] + ("s" if (a & 3) == (b & 3) else "o")


CLS = {}
for ab in combinations(pk.DECK, 2):
    CLS.setdefault(_class(*ab), []).append(list(ab))
NAMES = sorted(CLS, key=lambda c: pk.pct(CLS[c][0]))


def _pair(a):
    i, j, n, seed = a
    rng = random.Random(seed)
    A, B = CLS[NAMES[i]], CLS[NAMES[j]]
    valid = [(x, y) for x in A for y in B if not set(x) & set(y)]
    if not valid:
        return i, j, 0.5, 0
    w = 0.0
    for _ in range(n):
        x, y = rng.choice(valid)
        rest = [c for c in pk.DECK if c not in x and c not in y]
        b = rng.sample(rest, 5)
        v1, v2 = pk.showdown(x, b), pk.showdown(y, b)
        w += 1.0 if v1 > v2 else 0.5 if v1 == v2 else 0.0
    return i, j, w / n, len(valid)


def matrix(n=800, procs=8):
    m = len(NAMES)
    jobs = [(i, j, n, i * 1000 + j) for i in range(m) for j in range(i, m)]
    E, W = np.full((m, m), 0.5), np.zeros((m, m))
    with Pool(procs) as p:
        for i, j, e, c in p.imap_unordered(_pair, jobs, chunksize=64):
            E[i, j], E[j, i] = e, 1 - e
            W[i, j] = W[j, i] = c
    return E, W


def solve(E, W, S, iters=3000):
    """Fictitious play at stack S big blinds. Blinds 0.5 and 1. Returns jam and call frequencies."""
    m = len(NAMES)
    combos = np.array([len(CLS[n]) for n in NAMES], float)
    x, y = np.ones(m) * 0.5, np.ones(m) * 0.5
    for t in range(1, iters + 1):
        # SB best response to y: value of jamming with i, weighted by non-conflicting villain combos.
        wy = W * y
        tot = W.sum(1)
        pcall = wy.sum(1) / np.maximum(tot, 1)
        eqc = ((E * wy).sum(1)) / np.maximum(wy.sum(1), 1e-9)
        evj = (1 - pcall) * 1.0 + pcall * (eqc * 2 * S - S)
        bx = (evj > -0.5).astype(float)
        # BB best response to x.
        wx = W * x
        eqv = ((E * wx).sum(1)) / np.maximum(wx.sum(1), 1e-9)
        by = (eqv * 2 * S - S > -1.0).astype(float)
        a = 1.0 / (t + 1)
        x += a * (bx - x)
        y += a * (by - y)
    return x, y, combos


if __name__ == "__main__":
    t0 = time.time()
    E, W = matrix()
    print(f"equity matrix {time.time()-t0:.0f}s; AA vs 72o {E[NAMES.index('AA'), NAMES.index('72o')]:.3f}; AKs vs QQ {E[NAMES.index('AKs'), NAMES.index('QQ')]:.3f}")
    depths = [1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 25, 30, 40]
    jam, call = {n: 0.0 for n in NAMES}, {n: 0.0 for n in NAMES}
    summary = []
    for S in depths:
        x, y, c = solve(E, W, S)
        summary.append((S, float((x * c).sum() / c.sum()), float((y * c).sum() / c.sum())))
        for i, n in enumerate(NAMES):
            if x[i] > 0.5:
                jam[n] = S
            if y[i] > 0.5:
                call[n] = S
    json.dump({"depths": depths, "jam": jam, "call": call, "summary": summary, "variant": pk.VARIANT}, open(f"nash_hu_{pk.VARIANT}.json", "w"), indent=0)
    print("S  jam%  call%")
    for S, a, b in summary:
        print(f"{S:4} {a:6.1%} {b:6.1%}")
    print("72o jam up to", jam["72o"], " call up to", call["72o"])
    print("A2o jam", jam["A2o"], "call", call["A2o"], "| K7s jam", jam["K7s"], "call", call["K7s"], "| 22 jam", jam["22"], "call", call["22"])
    print(f"total {time.time()-t0:.0f}s")
