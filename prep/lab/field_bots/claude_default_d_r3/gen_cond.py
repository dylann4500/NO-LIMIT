"""Offline calibration of postflop range conditioning (writes cond.json; the agent only reads it).

Question answered: if hero has equity E against a villain's whole range on this board, what is hero's
equity against the strongest b-fraction of that range (ranked by each villain combo's equity vs a
random hand on this board, i.e. how strength-driven bots choose to bet or call)?

Table: cond[street][bi][ei] = mean equity vs top-b subset, for b = BS[bi], E bin ei (20 bins).
usage: .venv/bin/python lab/field_bots/claude_default_d/gen_cond.py
"""
import json, os, random
from multiprocessing import Pool

import eval7

DECK = [r + s for r in "23456789TJQKA" for s in "shdc"]
C = {c: eval7.Card(c) for c in DECK}
ALL = [(a, b) for i, a in enumerate(DECK) for b in DECK[i + 1:]]
BS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
NE = 20


def one_board(args):
    seed, street = args
    rng = random.Random(seed)
    nb = {1: 3, 2: 4, 3: 5}[street]
    board = rng.sample(DECK, nb)
    bc = [C[x] for x in board]
    live = [h for h in ALL if h[0] not in board and h[1] not in board]
    rnd = [((C[a], C[b]), 1.0) for a, b in live]
    rng.shuffle(rnd)
    rnd = rnd[:250]
    # strength of each villain combo = equity vs random hand
    strength = []
    for a, b in live:
        e = eval7.py_hand_vs_range_monte_carlo([C[a], C[b]], rnd, bc, 250)
        strength.append((e, a, b))
    strength.sort(reverse=True)
    full = [((C[a], C[b]), 1.0) for _, a, b in strength]
    rng.shuffle(full)
    subs = []
    for bfrac in BS:
        k = max(10, int(len(strength) * bfrac))
        sub = [((C[a], C[b]), 1.0) for _, a, b in strength[:k]]
        rng.shuffle(sub)
        subs.append(sub)
    out = []
    heroes = rng.sample(live, 40)
    for a, b in heroes:
        hc = [C[a], C[b]]
        ef = eval7.py_hand_vs_range_monte_carlo(hc, full, bc, 1500)
        row = [ef]
        for sub in subs:
            row.append(eval7.py_hand_vs_range_monte_carlo(hc, sub, bc, 1000))
        out.append(row)
    return street, out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    jobs = [(1000 * st + i, st) for st in (1, 2, 3) for i in range(160)]
    with Pool(8) as p:
        res = p.map(one_board, jobs)
    acc = {st: [[[0.0, 0] for _ in range(NE)] for _ in BS] for st in (1, 2, 3)}
    for st, rows in res:
        for row in rows:
            ef = row[0]
            ei = min(NE - 1, int(ef * NE))
            for bi in range(len(BS)):
                cell = acc[st][bi][ei]
                cell[0] += row[1 + bi]
                cell[1] += 1
    table = {}
    for st in (1, 2, 3):
        t = []
        for bi in range(len(BS)):
            r = []
            for ei in range(NE):
                s, n = acc[st][bi][ei]
                mid = (ei + 0.5) / NE
                # shrink thin cells toward the identity
                r.append(round((s + 2 * mid) / (n + 2) if n < 30 else s / n, 4))
            # enforce monotone non-decreasing in E
            for ei in range(1, NE):
                if r[ei] < r[ei - 1]:
                    r[ei] = r[ei - 1]
            t.append(r)
        table[str(st)] = t
    with open(os.path.join(here, "cond.json"), "w") as f:
        json.dump({"bs": BS, "ne": NE, "cond": table}, f)
    for st in (1, 2, 3):
        print("street", st)
        for bi, bf in enumerate(BS):
            print("  b=%.1f" % bf, " ".join("%.2f" % x for x in table[str(st)][bi]))


if __name__ == "__main__":
    main()
