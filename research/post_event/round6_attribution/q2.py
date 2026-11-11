"""Q2: is our postflop fold-to-bet over-folding? Heads-up first bets of a street (exactly 2 live players, target not all-in).
Per target team: fold/call/raise rates by bet size, pure-bluff break-even fold rate alpha = b/(P+b),
bettor's chip return R/P (R = bettor's stack after the hand - stack before the bet; R/P = 1 when the target folds),
target's ICM value of the facing decision vs folding (d_t), stab rate after the target checks first,
and the showdown strength of bettors who were called (class at the time of the bet).
usage: python -I q2.py r6 [r5]"""
import collections, pickle, sys
import numpy as np
import pandas as pd

LEADERS = ["2 Curry", "thepastaway", "Lemonade", "Team 82", "Team 123", "pocket rockets"]
SIZES = ["<.4", ".4-.6", ".6-.85", ".85-1.2", ">1.2"]


def agg(FA, FR, ids, street, sizeb=None):
    n = f = c = r = 0; v = np.zeros(8)
    for t in ids:
        for sb in ([sizeb] if sizeb else SIZES):
            f += FA.get((t, street, sb, "fold"), 0); c += FA.get((t, street, sb, "call"), 0); r += FA.get((t, street, sb, "raise"), 0)
            x = FR.get((t, street, sb))
            if x:
                v += np.array(x)
    n = f + c + r
    if n == 0:
        return None
    m = v[1] / v[0]; sd = np.sqrt(max(0, v[2] / v[0] - m * m))
    md = v[5] / v[0]; sdd = np.sqrt(max(0, v[6] / v[0] - md * md))
    return dict(n=n, fold=f / n, call=c / n, raise_=r / n, alpha=v[4] / v[0], RP=m, RP_ci=1.96 * sd / np.sqrt(v[0]),
                Rbb=v[3] / v[0], dT=md, dT_ci=1.96 * sdd / np.sqrt(v[0]))


def main():
    for prefix in sys.argv[1:]:
        F = pickle.load(open(prefix + "_field.pkl", "rb"))
        names = F["names"]; you = F["you"]; FA = F["FA"]; FR = F["FR"]; SD = F["SD"]; FS = F["FS"]
        byname = {v: k for k, v in names.items()}
        lead = [byname[n] for n in LEADERS if n in byname]
        missing = [n for n in LEADERS if n not in byname]
        allt = sorted({k[0] for k in FA})
        field = [t for t in allt if t != you]
        groups = [("avalon (us)", [you]), ("6 leaders pooled", lead)] + [(names[t], [t]) for t in lead] + [("field excl. us", field)]
        print(f"\n######## {prefix}: {F['ntables']} tables; leaders found {len(lead)} missing {missing}")
        for st in (1, 2, 3):
            print(f"\n== street {st} ('FTR'[{st-1}]) HU first bet: target response, bettor return R/P (1.0 = target always folds), target ICM value vs folding dT")
            for nm, ids in groups:
                a = agg(FA, FR, ids, st)
                if a:
                    print(f"  {nm[:18]:18s} n={a['n']:7d} fold {a['fold']:5.1%} call {a['call']:5.1%} raise {a['raise_']:5.1%} | alpha {a['alpha']:.3f} | "
                          f"bettor R/P {a['RP']:+.3f}±{a['RP_ci']:.3f} ({a['Rbb']:+.2f}bb) | target dT {a['dT']:+.3f}±{a['dT_ci']:.3f} pts")
            print(f"  -- by bet size (fold% / alpha / bettor R/P):")
            for sb in SIZES:
                line = f"    size {sb:8s}"
                for nm, ids in [groups[0], groups[1], groups[-1]]:
                    a = agg(FA, FR, ids, st, sb)
                    if a:
                        line += f" | {nm[:10]:10s} n={a['n']:6d} fold {a['fold']:5.1%} a={a['alpha']:.2f} R/P {a['RP']:+.2f}±{a['RP_ci']:.2f} dT {a['dT']:+.2f}"
                print(line)
        # stab rate after the target checks first HU
        print("\n== opponents' stab rate after the target checks first (HU):")
        for st in (1, 2, 3):
            line = f"  street {st}:"
            for nm, ids in [groups[0], groups[1], groups[-1]]:
                s = sum(FS.get((t, st, "stab"), 0) for t in ids); cb = sum(FS.get((t, st, "checkback"), 0) for t in ids)
                if s + cb:
                    line += f"  {nm[:12]}: {s/(s+cb):5.1%} (n={s+cb})"
            print(line)
        # bettor showdown strength when called (class at time of bet)
        print("\n== bettors called HU and reaching showdown: bettor's hand class at the bet (all bettors)")
        for st in (1, 2):
            for us in (1, 0):
                c = collections.Counter()
                for (b, s, cl, u), n in SD.items():
                    if s == st and u == us:
                        c[cl] += n
                tot = sum(c.values())
                print(f"  street {st} caller={'us' if us else 'others'} n={tot}: " + " ".join(f"{k} {c[k]/tot:5.1%}" for k in ["air", "fd", "weak", "top", "over", "strong"]))
        # weight by our HU folds per villain
        try:
            d = pd.read_pickle(prefix + "_dec.pkl")
        except FileNotFoundError:
            continue
        for st, lab in ((1, "F_fold"), (2, "T_fold")):
            fo = d[(d.label == lab) & (d.nopp == 1)]
            pool = collections.Counter()
            per = collections.defaultdict(collections.Counter)
            for (b, s, cl, u), n in SD.items():
                if s == st:
                    per[b][cl] += n; pool[cl] += n
            ptot = sum(pool.values())
            W = collections.Counter(); nv = 0
            for v, k in fo["agg"].value_counts().items():
                c = per.get(v)
                tot = sum(c.values()) if c else 0
                src = c if tot >= 30 else pool; T = tot if tot >= 30 else ptot
                for cl in ["air", "fd", "weak", "top", "over", "strong"]:
                    W[cl] += k * src[cl] / T
                nv += k
            print(f"\n== our HU {lab} n={len(fo)}: our folded hand classes: " + " ".join(f"{k} {v/len(fo):5.1%}" for k, v in fo['hcls'].value_counts().items()))
            print(f"   villains' called-bet showdown range (same villain, same street, weighted by our folds): " +
                  " ".join(f"{cl} {W[cl]/nv:5.1%}" for cl in ["air", "fd", "weak", "top", "over", "strong"]))
            print(f"   villain exposed card pairs board in {(fo.vexp==1).mean():.1%} of these folds; median pot odds {fo.odds.median():.3f}; "
                  f"median bet/pot {pd.to_numeric(fo.betfrac, errors='coerce').median():.2f}")
            for vx in (0, 1):
                g = fo[fo.vexp == vx]
                print(f"     vexp={vx}: n={len(g)} classes " + " ".join(f"{k} {v/len(g):5.1%}" for k, v in g['hcls'].value_counts().items()))
            # our fold rate HU facing a first bet by hand class (from our rows, facing & HU)
            fac = d[(d.street == st) & (d.facing == 1) & (d.nopp == 1) & (d.checked.isin([0, 1]))]
            tab = fac.groupby(["vexp", "hcls"])["act"].apply(lambda s: pd.Series({"n": len(s), "fold%": (s == "fold").mean()})).unstack()
            print("   our fold% facing HU bets by villain-exposed-pairs x our class:"); print(tab.round(3).to_string())


if __name__ == "__main__":
    main()
