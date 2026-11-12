"""Within-table drift: (a) last third vs first third of a table, strata = players-left bucket x own stack-in-bb bucket
(no blind-level control); (b) adjacent thirds within the same blind level; (c) second half vs first half of each blind level."""
import sys, math, json, pickle; sys.path.insert(0, '.')
import numpy as np
from collections import defaultdict
from common import *
from q3a import bh, pz
OUT = sys.argv[1] if len(sys.argv) > 1 else "out2"
KIND = sys.argv[2] if len(sys.argv) > 2 else "bay"
LABS = sys.argv[3].split(",") if len(sys.argv) > 3 else SCORED
W_ = os.path.dirname(os.path.abspath(__file__))
def ld(l):
    fid = LAB[l] if KIND == "bay" else l
    return pickle.load(open(f"{W_}/{OUT}/{KIND}_{fid}.pkl", "rb"))
def mh2(cells):
    """cells: list of (n_a,k_a,n_b,k_b) per stratum. b minus a. returns z, effect, n_b"""
    num = var = ws = ds = 0.0; nb = 0
    for n0, k0, n1, k1 in cells:
        if n0 < 1 or n1 < 1: continue
        N = n0 + n1; K = k0 + k1
        num += k1 - n1 * K / N
        if N > 1: var += n0 * n1 * K * (N - K) / (N * N * (N - 1))
        w = n0 * n1 / N; ws += w; ds += w * (k1 / n1 - k0 / n0); nb += min(n0, n1)
    if var <= 0: return None
    return num / math.sqrt(var), ds / ws, nb
def designs(T):
    """T: {(team, metric, third, lvl, half, plb, stkb): (n,k)} -> per (team, metric, design) cell lists"""
    a = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0])); b = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0])); c = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    for (t, m, th, lvl, half, plb, stkb), (n, k) in T.items():
        if th in (0, 2):
            x = a[(t, m)][(plb, stkb)]; x[th] += n; x[th + 1] += k
        # adjacent thirds within level: strata (lvl, plb, stkb, pair)
        for pair, (lo, hi) in enumerate(((0, 1), (1, 2))):
            if th == lo: x = b[(t, m)][(lvl, plb, stkb, pair)]; x[0] += n; x[1] += k
            if th == hi: x = b[(t, m)][(lvl, plb, stkb, pair)]; x[2] += n; x[3] += k
        x = c[(t, m)][(lvl, plb, stkb, th)]; x[2 * half] += n; x[2 * half + 1] += k
    return a, b, c
def run():
    per = {}
    for l in LABS:
        d = ld(l); a, b, c = designs(d["T"])
        for nm, dd in (("a", a), ("b", b), ("c", c)):
            for key, cells in dd.items():
                per[(l, nm) + key] = mh2(list(cells.values()))
        print(l, flush=True)
    pickle.dump(per, open(f"out/q4_{KIND}.pkl", "wb"))
if __name__ == "__main__":
    run()
