"""Offline: approximate Nash push/fold strategies for an unopened pot, solved by fictitious play.

Model (chip EV, units of big blinds): the pusher has `n` players left to act behind; each may call with
its own calling range (the last two behind are SB/BB with 0.5 and 1 posted; when n == 1 the pusher is the SB
facing the BB). Only the first caller is modelled (multiway all-ins ignored). Dead money D = 1.5bb.
Output (appended to push_tables.npz): push[n-1, k, cls] = push probability at stack S_GRID[k].
"""
import os
import numpy as np
from build_tables import COMBOS

HERE = os.path.dirname(os.path.abspath(__file__))
S_GRID = np.array([1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 11, 12, 13, 14, 15,
                   16, 17, 18, 19, 20, 22, 25, 30], dtype=float)


def solve(eq, W, n, S, D=1.5, iters=600):
    if n == 1:
        bp, bc = 0.5, [1.0]
    else:
        bp, bc = 0.0, [0.0] * (n - 2) + [0.5, 1.0]
    Wn = W / W.sum()
    vr = eq @ Wn
    p = (vr > np.quantile(vr, 0.6)).astype(float)
    c = np.array([(vr > np.quantile(vr, 0.85)).astype(float) for _ in range(n)])
    for t in range(iters):
        lr = 1.0 / (t + 2)
        # callers' best responses vs current push range
        rw = p * W
        if rw.sum() > 0:
            eq_vs_p = eq @ rw / rw.sum()
        else:
            eq_vs_p = vr
        for i in range(n):
            ev = eq_vs_p * (D + 2 * S - bp - bc[i]) - (S - bc[i])
            c[i] += lr * ((ev > 0).astype(float) - c[i])
        # pusher best response vs callers
        ev = np.zeros(169)
        nf = 1.0
        for i in range(n):
            cw = c[i] * W
            pc = cw.sum() / W.sum()
            if pc > 0:
                eqc = eq @ cw / cw.sum()
                ev += nf * pc * (eqc * (D + 2 * S - bp - bc[i]) - (S - bp))
            nf *= (1 - pc)
        ev += nf * D
        p += lr * ((ev > 0).astype(float) - p)
    return p, c


if __name__ == "__main__":
    d = np.load(os.path.join(HERE, "pf_tables.npz"))
    eq = d["eq"].astype(float)
    W = np.array([len(x) for x in COMBOS], float)
    push = np.zeros((7, len(S_GRID), 169), dtype=np.float32)
    for n in range(1, 8):
        for k, S in enumerate(S_GRID):
            p, c = solve(eq, W, n, S)
            push[n - 1, k] = p
        print(n, [round(float((push[n - 1, k] * W).sum() / 1326), 3) for k in range(0, len(S_GRID), 4)])
    np.savez_compressed(os.path.join(HERE, "push_tables.npz"), push=push, s_grid=S_GRID.astype(np.float32))
