import sys, pickle, collections, numpy as np, json
sys.path.insert(0, '.')
from lib import *
R = {k: Round(k) for k in range(1, 7)}; V = Vocab(R.values()); TOP = R[1].TOP
names = np.array(V.names)
def rate(Rk, pred, succ=0):
    gs = np.array([pred(n) for n in names]); m = gs[Rk.g]
    t = Rk.team[Rk.seat][m]; ok = Rk.val[m] == succ
    n = np.bincount(t, minlength=20); s = np.bincount(t, weights=ok, minlength=20)
    return s / np.maximum(n, 1), n
KIN = ["3-bet our open (fold to non-all-in 3-bet)", "bet flop HU (fold to flop bet)", "bet turn HU (fold to turn bet)", "bet river HU (fold to river bet)", "steal our BB from BTN/SB (BB fold to steal)"]
PRED = [lambda n: n == "FQ pf_face_3b", lambda n: n.startswith("FQ post_face s1") and " hu1 " in n, lambda n: n.startswith("FQ post_face s2") and " hu1 " in n,
        lambda n: n.startswith("FQ post_face s3") and " hu1 " in n, lambda n: n == "FQ pf_bb_vs_steal"]
# ICM slope
S = collections.Counter()
for k in R: S.update(R[k].d["slope"])
slope = {a: S[(a, 1, 0)] / S[(a, 1, 1)] for a in range(2, 9) if S[(a, 1, 1)]}
print("points per chip (stack 0.5-1.5x average) by players alive:", {a: round(v * 1000, 2) for a, v in slope.items()}, "x1e-3;  small / big stacks at 8 alive:", [round(1000 * S[(8, b, 0)] / S[(8, b, 1)], 2) for b in (0, 1, 2)])
out = {}
other_rates = collections.defaultdict(list)
for k in R:
    led = R[k].d["led"]; seats = np.bincount(R[k].team, minlength=20)
    rates = [rate(R[k], p) for p in PRED]
    for T in range(20):
        tot = 0; tot10 = 0; tot20 = 0; rows = []
        for kind in range(5):
            f, n = rates[kind]; f0 = np.mean([f[j] for j in range(20) if j != T]); fT = f[T]
            N = sum(led.get((T, kind, a, tb, 0), 0) for a in range(2, 9) for tb in range(3))
            pot = sum(led.get((T, kind, a, tb, 1), 0) for a in range(2, 9) for tb in range(3)); bet = sum(led.get((T, kind, a, tb, 2), 0) for a in range(2, 9) for tb in range(3))
            pts = np.zeros(3)
            for a in range(2, 9):
                for tb in range(3):
                    pts[tb] += (led.get((T, kind, a, tb, 1), 0) + led.get((T, kind, a, tb, 2), 0)) * slope.get(a, 0)
            pts = pts / seats[T]  # (P+B) in points per target-table
            bound = abs(fT - f0) * pts
            P, B = pot / max(N, 1), bet / max(N, 1)
            rows.append(dict(kind=KIN[kind], fT=fT, f0=f0, nresp=int(n[T]) / seats[T], opp=N / seats[T], P=P, B=B, be=B / (P + B), bound=bound.sum(), b10=bound[1:].sum(), b20=bound[2]))
        out[(k, T)] = rows
def show(T, ks=range(1, 7)):
    print(f"\n=== target {TOP[T]}: upper bound on what ALL opponents together gain per table by knowing the seat (points/table); per opponent = /7")
    for k in ks:
        rows = out[(k, T)]
        print(f" R{k}: total bound {sum(r['bound'] for r in rows):.2f} pts/table all opponents = {sum(r['bound'] for r in rows) / 7:.3f} per opponent; if only usable after hand 10: {sum(r['b10'] for r in rows) / 7:.3f}; after hand 20: {sum(r['b20'] for r in rows) / 7:.3f}")
        for r in rows:
            print(f"    {r['kind']:46s} target {100 * r['fT']:5.1f}% vs avg finalist {100 * r['f0']:5.1f}% | break-even fold {100 * r['be']:4.0f}% | chances/table {r['opp']:5.1f} (target responds {r['nresp']:.1f}x/table) | pot+risk {r['P'] + r['B']:6.0f} chips | bound {r['bound']:.3f}")
for T in (2, 1, 0, 3): show(T, (1, 3, 6))
print("\nAll top-20, R6 and mean R1-6: bound per opponent per table (points)")
for T in range(20):
    print(f"  {TOP[T]:20s} R6 {sum(r['bound'] for r in out[(6, T)]) / 7:.3f}   mean {np.mean([sum(r['bound'] for r in out[(k, T)]) for k in R]) / 7:.3f}")
pickle.dump(out, open("ledger.pkl", "wb"))
