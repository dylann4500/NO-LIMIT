"""vs-avalon test: Mantel-Haenszel within situation strata, per team x metric, per round and pooled."""
import sys, math, json; sys.path.insert(0, '.')
from common import *
import numpy as np
from collections import defaultdict
MET = ["steal", "3bet", "f3b", "calljam", "btc", "foldbet"]
def mh(cells):
    """cells: iterable of (n0,k0,n1,k1). returns z, weighted risk difference (pp), n_av, raw p_av, standardized p_other"""
    num = var = wsum = dsum = 0.0; nav = kav = 0; exp_oth = 0.0
    for n0, k0, n1, k1 in cells:
        if n0 == 0 or n1 == 0: continue
        N = n0 + n1; K = k0 + k1
        num += k1 - n1 * K / N
        if N > 1: var += n0 * n1 * K * (N - K) / (N * N * (N - 1))
        w = n0 * n1 / N; wsum += w; dsum += w * (k1 / n1 - k0 / n0)
        nav += n1; kav += k1; exp_oth += n1 * k0 / n0
    if var <= 0 or nav == 0: return None
    return num / math.sqrt(var), dsum / wsum, nav, kav / nav, exp_oth / nav
def run(labs, keyfilter=None):
    """returns {(team, metric): mh result} pooling strata across labs (round kept as a stratum)"""
    cells = defaultdict(list)
    for l in labs:
        for (t, m, s), v in load(l)["Q3"].items():
            if keyfilter and not keyfilter(m, s): continue
            cells[(t, m)].append(v)
    return {k: mh(v) for k, v in cells.items()}
def bh(p):
    p = np.asarray(p); o = np.argsort(p); q = np.empty(len(p)); prev = 1.0
    for rnk, i in enumerate(o[::-1]):
        r = len(p) - rnk; prev = min(prev, p[i] * len(p) / r); q[i] = prev
    return q
from math import erfc
pz = lambda z: erfc(abs(z) / math.sqrt(2))
if __name__ == "__main__":
    S = standings(); rank = {t: r for r, t, _ in S}
    pooled = run(SCORED)
    per = {l: run([l]) for l in SCORED}
    odd = run(["R1", "R3", "R5"]); even = run(["R2", "R4", "R6"])
    out = []
    print("## Q3a field-wide: how the whole field acts against avalon vs against others in matched situations (pooled R1-R6)")
    print("| decision | teams | median effect (pp) | IQR | share of teams with |z|>2 | field-pooled effect (pp) | by round: R1..R6 median effect |")
    print("|---|---|---|---|---|---|---|")
    for m in MET:
        rs = [(t, r) for (t, mm), r in pooled.items() if mm == m and r and t != "avalon" and r[2] >= 200]
        d = np.array([r[1] for _, r in rs]) * 100; z = np.array([r[0] for _, r in rs])
        byr = []
        for l in SCORED:
            dd = [r[1] * 100 for (t, mm), r in per[l].items() if mm == m and r and t != "avalon" and r[2] >= 100]
            byr.append(np.median(dd))
        print(f"| {m} | {len(rs)} | {np.median(d):+.1f} | {np.percentile(d,25):+.1f}..{np.percentile(d,75):+.1f} | {np.mean(np.abs(z)>2):.0%} | {np.average(d, weights=[r[2] for _, r in rs]):+.1f} | " + " ".join(f"{x:+.1f}" for x in byr) + " |")
        med = np.median(d); mad = np.median(np.abs(d - med)) * 1.4826
        for (t, r) in rs:
            out.append(dict(team=t, metric=m, z=r[0], eff=r[1] * 100, n=r[2], p_av=r[3], p_oth=r[4], dev=(r[1] * 100 - med), field_med=med, mad=mad,
                            odd=(odd.get((t, m)) or [None, None])[1], even=(even.get((t, m)) or [None, None])[1],
                            byround=[(per[l].get((t, m)) or [None, None])[1] for l in SCORED],
                            zround=[(per[l].get((t, m)) or [None, None])[0] for l in SCORED]))
    # team-specific: deviation from the field's common effect; se of team effect approx eff/z
    for o in out:
        se = abs(o["eff"] / o["z"]) if o["z"] else float("inf")
        o["se"] = se; o["zdev"] = o["dev"] / se if se > 0 else 0.0; o["p"] = pz(o["zdev"])
    q = bh([o["p"] for o in out])
    for o, qq in zip(out, q): o["q"] = float(qq)
    json.dump(out, open("out/q3a.json", "w"))
    sig = [o for o in out if o["q"] < 0.01]
    print(f"\ntests: {len(out)}; BH q<0.01 for a team effect different from the field's common effect: {len(sig)}; q<0.05: {sum(o['q']<0.05 for o in out)}")
    # replication: odd vs even rounds sign and size
    rep = [o for o in sig if o["odd"] is not None and o["even"] is not None and (o["odd"] * 100 - o["field_med"]) * (o["even"] * 100 - o["field_med"]) > 0]
    print(f"of those, same sign of deviation in odd rounds and even rounds: {len(rep)}")
    big = sorted([o for o in rep if abs(o["dev"]) >= 5], key=lambda o: -abs(o["zdev"]))
    print(f"replicated and |deviation| >= 5pp: {len(big)}")
    print("\n| team | final rank | decision | n vs avalon | rate vs avalon | matched rate vs others | effect (pp) | field median effect | z vs field | q | effect by round R1..R6 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for o in big[:45]:
        br = " ".join("." if x is None else f"{100*x:+.0f}" for x in o["byround"])
        print(f"| {o['team']} | {rank.get(o['team'])} | {o['metric']} | {o['n']} | {100*o['p_av']:.1f} | {100*o['p_oth']:.1f} | {o['eff']:+.1f} | {o['field_med']:+.1f} | {o['zdev']:+.1f} | {o['q']:.1g} | {br} |")
    # correlation between odd and even deviations across all teams per metric (is team heterogeneity real?)
    print("\nreliability of team-specific effects (corr of odd-round vs even-round effect across teams):")
    for m in MET:
        xs = [(o["odd"], o["even"]) for o in out if o["metric"] == m and o["odd"] is not None and o["even"] is not None]
        a = np.array(xs); print(f"  {m}: r={np.corrcoef(a[:,0], a[:,1])[0,1]:+.2f} (n={len(a)}), SD of team effects {100*np.std(a.mean(1)):.1f}pp")
