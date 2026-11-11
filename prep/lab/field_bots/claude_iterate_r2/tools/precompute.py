"""Offline: preflop tables -> ../preflop.json. Classes ordered by strength; eq vs n random opps; eq vs top-p% ranges (HU)."""
import eval7, json, os, random, sys
R = '23456789TJQKA'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'preflop.json')
classes = []
for i in range(12, -1, -1):
    for j in range(i, -1, -1):
        if i == j: classes.append(R[i] * 2)
        else:
            classes.append(R[i] + R[j] + 's'); classes.append(R[i] + R[j] + 'o')
def combos(c):
    S = 'shdc'
    if len(c) == 2: return [(c[0] + S[a], c[1] + S[b]) for a in range(4) for b in range(a + 1, 4)]
    if c[2] == 's': return [(c[0] + s, c[1] + s) for s in S]
    return [(c[0] + a, c[1] + b) for a in S for b in S if a != b]
deck = [r + s for r in R for s in 'shdc']
CD = {c: eval7.Card(c) for c in deck}
rng = random.Random(7)
def eq_multi(c, n, iters):
    h = combos(c)[0]; rest = [CD[x] for x in deck if x not in h]; hc = [CD[h[0]], CD[h[1]]]
    tot = 0.0
    for _ in range(iters):
        s = rng.sample(rest, 5 + 2 * n)
        b = s[:5]; me = eval7.evaluate(hc + b); best = 0; cnt = 0
        for k in range(n):
            v = eval7.evaluate(s[5 + 2 * k:7 + 2 * k] + b)
            if v > best: best, cnt = v, 1
            elif v == best: cnt += 1
        if me > best: tot += 1
        elif me == best: tot += 1.0 / (cnt + 1)
    return tot / iters
full = eval7.HandRange(','.join(classes))
eqr = {}
for c in classes:
    hc = [CD[x] for x in combos(c)[0]]
    e1 = eval7.py_hand_vs_range_monte_carlo(hc, full, [], 30000)
    eqr[c] = [e1] + [eq_multi(c, n, int(sys.argv[1]) if len(sys.argv) > 1 else 3000) for n in range(2, 8)]
    print(c, [round(x, 3) for x in eqr[c]], flush=True)
# strength order: blend of HU and 4-way equity (normalised by fair share)
score = {c: 0.5 * eqr[c][0] / 0.5 + 0.5 * eqr[c][3] / 0.2 for c in classes}
order = sorted(classes, key=lambda c: -score[c])
ncomb = {c: len(combos(c)) for c in classes}
cum, pct = 0, {}
for c in order:
    pct[c] = (cum + ncomb[c] / 2) / 1326.0; cum += ncomb[c]
BUCKETS = [2, 4, 6, 9, 12, 16, 20, 25, 30, 40, 50, 65, 80, 100]
def top_range(p):
    out, cum = [], 0
    for c in order:
        if cum >= p / 100 * 1326 and out: break
        out.append(c); cum += ncomb[c]
    return out
eqtop = {c: [] for c in classes}
for p in BUCKETS:
    hr = eval7.HandRange(','.join(top_range(p)))
    for c in classes:
        hc = [CD[x] for x in combos(c)[0]]
        eqtop[c].append(eval7.py_hand_vs_range_monte_carlo(hc, hr, [], 8000))
json.dump({'order': order, 'pct': pct, 'eqr': eqr, 'buckets': BUCKETS, 'eqtop': eqtop}, open(OUT, 'w'))
print('wrote', OUT)
