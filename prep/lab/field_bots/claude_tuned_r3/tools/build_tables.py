"""Offline: build preflop tables for agent.py (equity vs top-x% ranges, equity vs k random hands, hand ordering).
Writes ../pf_tables.json (read by agent.py at import)."""
import eval7, json, random, os, sys
from multiprocessing import Pool

R = "AKQJT98765432"
HERE = os.path.dirname(os.path.abspath(__file__))
BUCKETS = [0.03, 0.05, 0.08, 0.11, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 1.0]
KMAX = 7


def classes():
    out = []
    for i, a in enumerate(R):
        for j, b in enumerate(R):
            if i == j:
                out.append((a + b, 6))
            elif i < j:
                out.append((a + b + "s", 4))
                out.append((a + b + "o", 12))
    return out


CL = classes()


def rep(name):
    a, b = name[0], name[1]
    if len(name) == 2:
        return [eval7.Card(a + "s"), eval7.Card(b + "h")]
    if name[2] == "s":
        return [eval7.Card(a + "s"), eval7.Card(b + "s")]
    return [eval7.Card(a + "s"), eval7.Card(b + "h")]


def multi_job(args):
    idx, n = args
    name = CL[idx][0]
    me = rep(name)
    deck = [c for c in eval7.Deck().cards if c not in me]
    rng = random.Random(1000 + idx)
    tot = [0.0] * (KMAX + 1)
    for _ in range(n):
        s = rng.sample(deck, 5 + 2 * KMAX)
        board = s[:5]
        mv = eval7.evaluate(me + board)
        best_other = -1
        ties = 0
        for k in range(1, KMAX + 1):
            o = s[5 + 2 * (k - 1): 7 + 2 * (k - 1)]
            v = eval7.evaluate(o + board)
            if v > best_other:
                best_other, ties = v, 1
            elif v == best_other:
                ties += 1
            if mv > best_other:
                tot[k] += 1.0
            elif mv == best_other:
                tot[k] += 1.0 / (ties + 1)
    return [t / n for t in tot[1:]]


def range_job(args):
    idx, ranges, iters = args
    me = rep(CL[idx][0])
    out = []
    for rs in ranges:
        hr = eval7.HandRange(rs)
        out.append(eval7.py_hand_vs_range_monte_carlo(me, hr, [], iters))
    return out


def main():
    nmulti = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    with Pool(14) as pool:
        multi = pool.map(multi_job, [(i, nmulti) for i in range(len(CL))])
        # ordering: blend of heads-up and 4-way strength (relative to fair share)
        score = [m[0] * 2 + m[2] * 4 + m[4] * 6 * 0.5 for m in multi]
        order = sorted(range(len(CL)), key=lambda i: -score[i])
        total = 1326.0
        cum = 0.0
        pct = [0.0] * len(CL)
        start = [0.0] * len(CL)
        for i in order:
            start[i] = cum / total
            pct[i] = (cum + CL[i][1] / 2.0) / total
            cum += CL[i][1]
        ranges = []
        for b in BUCKETS:
            names = [CL[i][0] for i in order if start[i] < b - 1e-9]
            ranges.append(",".join(names))
        rng_eq = pool.map(range_job, [(i, ranges, 30000) for i in range(len(CL))])
    data = {"classes": [c[0] for c in CL], "pct": [round(p, 4) for p in pct], "buckets": BUCKETS,
            "eq_top": [[round(e, 4) for e in row] for row in rng_eq],
            "eq_multi": [[round(e, 4) for e in m] for m in multi],
            "order": [CL[i][0] for i in order]}
    with open(os.path.join(os.path.dirname(HERE), "pf_tables.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))
    for i in order[:25]:
        print(CL[i][0], round(pct[i], 3), [round(x, 3) for x in multi[i][:4]])
    print("...")
    for i in order[-5:]:
        print(CL[i][0], round(pct[i], 3), [round(x, 3) for x in multi[i][:4]])


if __name__ == "__main__":
    main()
