"""Offline builder for tables.json (run once; agent.py only reads the JSON).

tables.json:
  classes : 169 hand-class names ("AA", "AKs", "AKo", ...), index = class id
  order   : class ids sorted best -> worst
  cum     : for each class id, fraction of the 1326 combos ranked at or above it (its percentile)
  grid    : range widths (fractions of combos) for the equity matrix
  eq      : eq[class][g] = all-in equity of the class vs the top grid[g] of hands (heads-up)
"""
import json, os, random, time
import eval7
from eval7 import Card

R = "23456789TJQKA"
S = "shdc"
random.seed(7)


def classes():
    out = []
    for i in range(12, -1, -1):
        for j in range(12, -1, -1):
            a, b = R[i], R[j]
            if i == j:
                out.append(a + b)
            elif i > j:
                out.append(a + b + "s")
                out.append(a + b + "o")
    return out


CL = classes()
assert len(CL) == 169


def combos(c):
    a, b = c[0], c[1]
    res = []
    if len(c) == 2:
        for x in range(4):
            for y in range(x + 1, 4):
                res.append((a + S[x], b + S[y]))
    elif c[2] == "s":
        for x in range(4):
            res.append((a + S[x], b + S[x]))
    else:
        for x in range(4):
            for y in range(4):
                if x != y:
                    res.append((a + S[x], b + S[y]))
    return res


COMBOS = {c: combos(c) for c in CL}
REP = {c: [Card(x) for x in COMBOS[c][0]] for c in CL}


def range_list(order, width):
    n = max(1, int(round(width * 1326)))
    out = []
    for c in order:
        for (x, y) in COMBOS[c]:
            out.append(((Card(x), Card(y)), 1.0))
        if len(out) >= n:
            break
    return out


def eq_vs(c, rl, it):
    return eval7.py_hand_vs_range_monte_carlo(REP[c], rl, [], it)


def main():
    t0 = time.time()
    full = range_list(CL, 1.0)
    e_rand = {c: eq_vs(c, full, 60000) for c in CL}
    order0 = sorted(CL, key=lambda c: -e_rand[c])
    r15 = range_list(order0, 0.15)
    e15 = {c: eq_vs(c, r15, 40000) for c in CL}
    score = {c: 0.5 * e_rand[c] + 0.5 * e15[c] for c in CL}
    order = sorted(CL, key=lambda c: -score[c])
    cum, tot = {}, 0
    for c in order:
        tot += len(COMBOS[c])
        cum[c] = tot / 1326.0
    grid = [0.01, 0.02, 0.03, 0.045, 0.06, 0.08, 0.10, 0.13, 0.16, 0.20, 0.25, 0.30, 0.36, 0.43, 0.50, 0.60, 0.72, 0.85, 1.0]
    rls = [range_list(order, g) for g in grid]
    eq = []
    for c in CL:
        eq.append([round(eq_vs(c, rl, 40000), 4) for rl in rls])
    out = {"classes": CL, "order": [CL.index(c) for c in order], "cum": [round(cum[c], 5) for c in CL],
           "grid": grid, "eq": eq}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("done", time.time() - t0)
    print(" ".join(order[:60]))


if __name__ == "__main__":
    main()
