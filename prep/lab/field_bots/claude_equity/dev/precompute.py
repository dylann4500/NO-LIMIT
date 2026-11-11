"""Offline precompute for claude_equity: preflop hand ranking and HU equity tables vs top-p ranges.
Writes ../tables.json. Run: .venv/bin/python lab/field_bots/claude_equity/dev/precompute.py"""
import eval7, json, os, random, itertools, time
from eval7 import Card, evaluate

R = "23456789TJQKA"
S = "cdhs"
DECK = [Card(r + s) for r in R for s in S]
random.seed(7)


def classes():
    out = []
    for i in range(12, -1, -1):
        for j in range(i, -1, -1):
            if i == j:
                out.append(R[i] + R[j])
            else:
                out.append(R[i] + R[j] + "s")
                out.append(R[i] + R[j] + "o")
    return out


def combos(c):
    a, b = c[0], c[1]
    if a == b:
        return [(Card(a + s1), Card(b + s2)) for s1, s2 in itertools.combinations(S, 2)]
    if c[2] == "s":
        return [(Card(a + s), Card(b + s)) for s in S]
    return [(Card(a + s1), Card(b + s2)) for s1 in S for s2 in S if s1 != s2]


CL = classes()
CMB = {c: combos(c) for c in CL}


def eq_multi(hero, nopp, trials):
    """MC equity of hero vs nopp random hands (python loop)."""
    rest = [c for c in DECK if c not in hero]
    tot = 0.0
    for _ in range(trials):
        d = random.sample(rest, 5 + 2 * nopp)
        board = d[:5]
        hv = evaluate(list(hero) + board)
        best = 0
        ties = 0
        lost = False
        for k in range(nopp):
            v = evaluate(d[5 + 2 * k:7 + 2 * k] + board)
            if v > hv:
                lost = True
                break
            if v == hv:
                ties += 1
        if not lost:
            tot += 1.0 / (1 + ties)
    return tot / trials


t0 = time.time()
ALL = [((a, b), 1.0) for a, b in itertools.combinations(DECK, 2)]
eq1 = {}
for c in CL:
    h = list(CMB[c][0])
    lst = [x for x in ALL if x[0][0] not in h and x[0][1] not in h]
    random.shuffle(lst)
    eq1[c] = eval7.py_hand_vs_range_monte_carlo(h, lst, [], len(lst) * 40)
print("eq1 done", time.time() - t0)
eq3 = {c: eq_multi(CMB[c][0], 2, 6000) for c in CL}
print("eq3 done", time.time() - t0)
eqk = {}
for c in CL:
    eqk[c] = [round(eq1[c], 4)] + [round(eq_multi(CMB[c][1 % len(CMB[c])], k, 2500), 4) for k in range(2, 8)]
print("eqk done", time.time() - t0)
score = {c: eq1[c] + 0.6 * eq3[c] for c in CL}
order = sorted(CL, key=lambda c: -score[c])
# combo-weighted percentile (top of class)
cum, pct = 0, {}
for c in order:
    n = len(CMB[c])
    pct[c] = (cum + n / 2) / 1326.0
    cum += n
BUCKETS = [0.02, 0.035, 0.05, 0.075, 0.10, 0.13, 0.17, 0.22, 0.28, 0.35, 0.45, 0.6, 0.8, 1.0]
ranked = [cmb for c in order for cmb in CMB[c]]
eqb = {}
for c in CL:
    row = []
    for p in BUCKETS:
        top = ranked[:max(1, int(round(p * 1326)))]
        e, w = 0.0, 0
        reps = CMB[c][:2] if len(CMB[c]) > 1 else CMB[c]
        for h in reps:
            lst = [(x, 1.0) for x in top if x[0] not in h and x[1] not in h]
            random.shuffle(lst)
            it = max(20000, len(lst) * 30)
            it = (it // len(lst)) * len(lst)
            e += eval7.py_hand_vs_range_monte_carlo(list(h), lst, [], it)
            w += 1
        row.append(round(e / w, 4))
    eqb[c] = row
print("eqb done", time.time() - t0)
out = {"order": order, "pct": {c: round(pct[c], 5) for c in CL}, "buckets": BUCKETS, "eqb": eqb, "eqk": eqk}
path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tables.json")
with open(path, "w") as f:
    json.dump(out, f, separators=(",", ":"))
print("wrote", path, "top20:", order[:20], "bottom5:", order[-5:])
