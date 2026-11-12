import sys, json, numpy as np, collections
sys.path.insert(0, '.')
from lib import *
rng = np.random.default_rng(1)
R = {k: Round(k) for k in range(1, 7)}; V = Vocab(R.values()); TOP = R[1].TOP; L = 20
names = np.array(V.names); isent = np.array([n.startswith("LMS entry") for n in names])
for Rk in R.values():
    m = (V.fam[Rk.g] == "LMS3") & (Rk.val == 1); Rk.val = Rk.val.copy(); Rk.val[m] = 2
    Rk.tteam = Rk.team[Rk.seat]
    av = np.flatnonzero(Rk.team == AV); keep = rng.choice(av, 380, replace=False)
    tm = np.ones(Rk.n, bool); tm[av] = False; tm[keep] = True; Rk.trainseat = tm
FAMS = {"ALL": np.isin(V.fam, ["SZ", "FQ", "LMS", "OTH"]), "SZ sizes": V.fam == "SZ",
        "NOSIZE": np.isin(V.fam, ["FQ", "OTH", "LMS3"]) | ((V.fam == "LMS") & ~isent)}
NS2 = (5, 10, 20, 40, 80, 10**6)
def ev(a, b, fam, heldout=False):
    Ra, Rb = R[a], R[b]
    lab = np.where(Ra.trainseat[Ra.seat] & fam[Ra.g], Ra.tteam, -1); sm = None
    if heldout:
        par = Ra.table % 2 == 0; lab = np.where(par[Ra.seat] & fam[Ra.g], Ra.tteam, -1); sm = ~par
    cols, LP, LU = log_profiles(counts(Ra.g, Ra.val, lab, L, V), V)
    out = []
    for N in NS2:
        m = fam[Rb.g] & (Rb.hid < N)
        S = score(Rb.g, Rb.val, Rb.seat, Rb.n, cols, LP, LU, m) + rng.random((Rb.n, L)) * 1e-9
        pred = S.argmax(1); tm = Rb.team if sm is None else np.where(sm, Rb.team, -1)
        out.append(np.mean([np.mean(pred[tm == t] == t) for t in range(L)]))
    return out
M = np.zeros((6, 6))
res = collections.defaultdict(list); same = collections.defaultdict(list)
for fn, fam in FAMS.items():
    for a in range(1, 7):
        same[fn].append(ev(a, a, fam, True))
        for b in range(1, 7):
            if a == b: continue
            r = ev(a, b, fam); res[fn].append(r)
            if fn == "ALL": M[a - 1, b - 1] = r[2]
print("Boston (flop-auction variant), 20 candidates = 19 best teams at the friend's tables + the friend's team; ~370 seats per team per file")
print("file-to-file ALL-feature accuracy at 20 hands (row = profile file, col = test file); the six files are the six scored rounds in unknown order")
print(np.round(M * 100).astype(int))
print(f"{'':10s}" + "".join(f"{('all' if n > 999 else str(n)):>7s}" for n in NS2))
for fn in FAMS:
    a = np.array(res[fn]) * 100; s = np.array(same[fn]) * 100
    print(f"{fn:10s}" + "".join(f"{x:7.1f}" for x in a.mean(0)) + "   different round (mean of 30 ordered pairs; best pair at 20 hands %.1f, worst %.1f)" % (a[:, 2].max(), a[:, 2].min()))
    print(f"{fn:10s}" + "".join(f"{x:7.1f}" for x in s.mean(0)) + "   same round, held-out tables")
