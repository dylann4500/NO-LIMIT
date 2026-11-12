import sys, os, math, json, pickle; sys.path.insert(0, '.')
import numpy as np
from collections import defaultdict
from q3a import mh, bh, pz, MET
BR = ["690def26", "de7ac5d3", "188fa79b", "516b7309", "b009537f", "3425f351"]
D = {f: pickle.load(open(f"out2/bos_{f}.pkl", "rb")) for f in BR}
ME = D[BR[0]]["av"]
def run(labs, late=None):
    cells = defaultdict(list)
    for l in labs:
        for (t, m, s), v in D[l]["Q3"].items():
            if late is not None and s[-1] != late: continue
            cells[(t, m)].append(v)
    return {k: mh(v) for k, v in cells.items()}
pooled = run(BR); odd = run(BR[0::2]); even = run(BR[1::2]); early = run(BR, False); late = run(BR, True)
print(f"## Boston Q3a: how each team acts against {ME} (the friend's team) vs others, matched situations, pooled R1-R6")
print("| decision | teams | median effect (pp) | IQR | share |z|>2 | odd/even-round reliability r | SD of team effects (pp) |"); print("|---|---|---|---|---|---|---|")
out = []
for m in MET:
    rs = [(t, r) for (t, mm), r in pooled.items() if mm == m and r and t != ME and r[2] >= 150]
    if not rs: continue
    d = np.array([r[1] for _, r in rs]) * 100; z = np.array([r[0] for _, r in rs]); med = np.median(d)
    xs = np.array([(odd[(t, m)][1], even[(t, m)][1]) for t, _ in rs if odd.get((t, m)) and even.get((t, m))])
    print(f"| {m} | {len(rs)} | {med:+.1f} | {np.percentile(d,25):+.1f}..{np.percentile(d,75):+.1f} | {np.mean(np.abs(z)>2):.0%} | {np.corrcoef(xs[:,0], xs[:,1])[0,1]:+.2f} | {100*np.std(xs.mean(1)):.1f} |")
    for t, r in rs:
        se = abs(r[1] * 100 / r[0]) if r[0] else 1e9
        out.append(dict(team=t, metric=m, eff=r[1] * 100, n=r[2], p_av=r[3], p_oth=r[4], med=med, zdev=(r[1] * 100 - med) / se,
                        odd=odd.get((t, m)), even=even.get((t, m)), early=early.get((t, m)), late=late.get((t, m))))
q = bh([pz(o["zdev"]) for o in out])
print("\n| team | decision | n vs friend | rate vs friend | matched rate vs others | effect (pp) | field median | z vs field | first half of table | second half |"); print("|---|---|---|---|---|---|---|---|---|---|")
for o, qq in sorted(zip(out, q), key=lambda x: -abs(x[0]["zdev"])):
    if qq < 0.01 and abs(o["eff"] - o["med"]) >= 5 and o["odd"] and o["even"] and (o["odd"][1] * 100 - o["med"]) * (o["even"][1] * 100 - o["med"]) > 0:
        f = lambda r: f"{100*r[1]:+.1f}" if r else "-"
        print(f"| {o['team']} | {o['metric']} | {o['n']} | {100*o['p_av']:.1f} | {100*o['p_oth']:.1f} | {o['eff']:+.1f} | {o['med']:+.1f} | {o['zdev']:+.1f} | {f(o['early'])} | {f(o['late'])} |")
