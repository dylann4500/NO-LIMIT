import sys, pickle, numpy as np, collections
sys.path.insert(0, '.')
from lib import *
R = {k: Round(k) for k in range(1, 7)}; V = Vocab(R.values()); TOP = R[1].TOP
names = np.array(V.names)
out = pickle.load(open("ledger.pkl", "rb"))
def rate(Rk, pred, succ):
    gs = np.array([pred(n) for n in names]); m = gs[Rk.g]
    t = Rk.team[Rk.seat][m]; ok = np.isin(Rk.val[m], succ)
    n = np.bincount(t, minlength=20); s = np.bincount(t, weights=ok, minlength=20)
    return s / np.maximum(n, 1), n / np.bincount(Rk.team, minlength=20)
TEND = [("open when folded to (deep)", lambda n: n.startswith("FQ pf_unopened") and n[-2:] in ("d2", "d3", "d4"), [2]),
        ("3-bet vs an open", lambda n: n.startswith("FQ pf_face_open"), [2]),
        ("fold to 3-bet (not all-in)", lambda n: n == "FQ pf_face_3b", [0]),
        ("fold to 3-bet jam", lambda n: n == "FQ pf_face_3bjam", [0]),
        ("BB fold to late steal", lambda n: n == "FQ pf_bb_vs_steal", [0]),
        ("call/raise a preflop all-in", lambda n: n.startswith("FQ pf_face_jam"), [1, 2]),
        ("c-bet flop", lambda n: n == "FQ cbet", [1]),
        ("bet when first, HU flop", lambda n: n.startswith("FQ post_first s1") and n.endswith("hu1"), [2]),
        ("fold to bet HU flop", lambda n: n.startswith("FQ post_face s1") and " hu1 " in n, [0]),
        ("fold to bet HU turn", lambda n: n.startswith("FQ post_face s2") and " hu1 " in n, [0]),
        ("fold to bet HU river", lambda n: n.startswith("FQ post_face s3") and " hu1 " in n, [0]),
        ("raise a bet HU flop", lambda n: n.startswith("FQ post_face s1") and " hu1 " in n, [2]),
        ("fold to raise after betting", lambda n: n.startswith("FQ post_face_r"), [0])]
T = {}
for k in R:
    for nm, p, s in TEND: T[(k, nm)] = rate(R[k], p, s)
sel = [2, 1, 0, 3, 9, 10]
print("TENDENCIES (% ; chances per table in brackets for avalon R6). 'top20' = mean of the other 19, sd across them")
print(f"{'':30s}" + "".join(f"{'av R' + str(k):>8s}" for k in (1, 2, 3, 4, 5, 6)) + f"{'[n/tbl]':>8s}{'top20 R6':>10s}{'sd':>5s}" + "".join(f"{TOP[t][:9] + ' R6':>13s}" for t in sel[1:]) + f"{'top20 lag-1 drift':>18s}")
for nm, p, s in TEND:
    f6, n6 = T[(6, nm)]; oth = [j for j in range(20) if j != 2]
    drift = np.mean([np.abs(T[(k + 1, nm)][0][oth] - T[(k, nm)][0][oth]).mean() for k in range(1, 6)])
    print(f"{nm:30s}" + "".join(f"{100 * T[(k, nm)][0][2]:8.1f}" for k in range(1, 7)) + f"{n6[2]:8.1f}{100 * f6[oth].mean():10.1f}{100 * f6[oth].std():5.1f}" + "".join(f"{100 * f6[t]:13.1f}" for t in sel[1:]) + f"{100 * drift:18.1f}")
# threshold (flip) model
def ev(f, P, B): return f * P - (1 - f) * B
def value(k, Ttrue, belief_rows=None, label=None):
    """points per opponent per table for an opponent whose bluff decisions follow belief (rows of another team) vs default (average finalist)"""
    tot = 0; det = []
    for i, r in enumerate(out[(k, Ttrue)]):
        P, B, n = r["P"], r["B"], r["opp"] / 7
        slope = r["bound"] / max(1e-12, abs(r["fT"] - r["f0"]) * (P + B) * r["opp"])
        evT = ev(r["fT"], P, B); ev0 = ev(r["f0"], P, B)
        fb = r["fT"] if belief_rows is None else belief_rows[i]["fT"]
        evb = ev(fb, P, B)
        g = (evT if evb > 0 else 0) - (evT if ev0 > 0 else 0)
        tot += g * n * slope; det.append((r["kind"].split("(")[0], evT / P, ev0 / P, g * n * slope))
    return tot, det
print("\nFLIP MODEL (zero-equity bluff, wins pot P when target folds, loses B otherwise; default policy bluffs only where it profits against the average finalist).")
print("Value per recognising opponent per table, points; and EV of the bluff in pots vs target / vs average finalist")
for Tt in (2, 1, 0, 3):
    for k in (1, 3, 6):
        tot, det = value(k, Tt)
        print(f"  {TOP[Tt]:16s} R{k}: {tot:6.2f} pts | " + "; ".join(f"{d[0].strip()}: {d[1]:+.2f}/{d[2]:+.2f} -> {d[3]:.2f}" for d in det))
print("\nAll top-20: flip-model value per opponent per table (points), mean R1-R6 and R6, next to linear bound mean")
for Tt in range(20):
    v = [value(k, Tt)[0] for k in R]; b = [sum(r['bound'] for r in out[(k, Tt)]) / 7 for k in R]
    print(f"  {TOP[Tt]:20s} flip mean {np.mean(v):5.2f}  R6 {v[-1]:5.2f} | linear bound mean {np.mean(b):5.2f}  R6 {b[-1]:5.2f}")
print("\nMISIDENTIFICATION: opponent believes our seat is team X and applies X's best response to us (avalon R6 truth). Its gain vs default play, points per table (negative = the counter loses to us)")
res = []
for X in range(20):
    if X == 2: continue
    tot, det = value(6, 2, out[(6, X)])
    res.append((tot, TOP[X], det))
for tot, nm, det in sorted(res): print(f"  believed {nm:20s} {tot:+6.2f} | " + "; ".join(f"{d[0].strip()[:18]}: {d[3]:+.2f}" for d in det))
print(f"  believed avalon (correct)    {value(6, 2)[0]:+6.2f}")
