"""Practice vs adjacent scored rounds: per team, which bot did the practice round play?"""
import sys, math, json; sys.path.insert(0, '.')
from common import *
import numpy as np
from q1 import CORE
R = api_results(); S = standings(); rank = {t: r for r, t, _ in S}
TRI = [("P4", "P3", "R1"), ("P6", "R2", "R3"), ("P7", "R3", "R4"), ("P8", "R4", "R5"), ("P9", "R5", "R6")]
def rates(l, t):
    A = load(l)["A"]; o = {}
    for m in CORE:
        n, k = rate(A, t, m)
        if n: o[m] = (n, k)
    return o
def chi(a, b, minn=30):
    """sum z^2 and count across metrics comparing counts a vs b"""
    s = 0.0; c = 0; mx = 0.0
    for m in a:
        if m not in b: continue
        n1, k1 = a[m]; n2, k2 = b[m]
        if n1 < minn or n2 < minn: continue
        p = (k1 + k2) / (n1 + n2)
        if p <= 0 or p >= 1: continue
        z = (k1 / n1 - k2 / n2) / math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)); s += z * z; c += 1; mx = max(mx, abs(k1 / n1 - k2 / n2))
    return s, c, mx
def llr(pr, a, b):
    """log-likelihood of practice counts under next-round rates minus under prev-round rates"""
    s = 0.0
    for m, (n, k) in pr.items():
        if m not in a or m not in b or a[m][0] < 200 or b[m][0] < 200: continue
        pa = (a[m][1] + 1) / (a[m][0] + 2); pb = (b[m][1] + 1) / (b[m][0] + 2)
        s += k * math.log(pb / pa) + (n - k) * math.log((1 - pb) / (1 - pa))
    return s
out = []
print("## Q5 per practice round: which bot did each team play?")
print("| practice → scored | teams | unchanged prev=practice=next | changed before practice (practice = next) | changed after practice (practice = prev) | practice differs from both (experiment or two changes) | unclear |")
print("|---|---|---|---|---|---|---|")
for P, prev, nxt in TRI:
    cnt = dict(same=0, eq_next=0, eq_prev=0, neither=0, unclear=0); n = 0
    for t in load(P)["teams"]:
        if t == "avalon" or R[P][t]["forfeited"] or R[nxt][t]["forfeited"] or R[prev][t]["forfeited"]: continue
        p, a, b = rates(P, t), rates(prev, t), rates(nxt, t)
        if "open" not in p or p["open"][0] < 300: continue
        n += 1
        sab, cab, mxab = chi(a, b); spa, cpa, mxpa = chi(p, a); spb, cpb, mxpb = chi(p, b)
        # thresholds: chi-square mean per metric; null ~1 (overdispersion measured separately)
        dab = sab / max(cab, 1); dpa = spa / max(cpa, 1); dpb = spb / max(cpb, 1)
        L = llr(p, a, b)
        changed = dab > 6 and mxab > 0.03   # prev vs next differ clearly (large samples)
        fit_a = dpa < 2.5; fit_b = dpb < 2.5
        if not changed:
            c = "same" if (fit_a and fit_b) else ("neither" if (dpa > 4 and dpb > 4) else "unclear")
        else:
            if L > 10 and fit_b: c = "eq_next"
            elif L < -10 and fit_a: c = "eq_prev"
            elif dpa > 4 and dpb > 4: c = "neither"
            else: c = "unclear"
        cnt[c] += 1
        out.append(dict(P=P, team=t, cls=c, dab=dab, dpa=dpa, dpb=dpb, L=L, mxab=mxab, mxpa=mxpa, mxpb=mxpb, rank=rank[t],
                        sp=R[P][t]["avg"], sn=R[nxt][t]["avg"], sprev=R[prev][t]["avg"], ntab=load(P)["PT"].get(t, (0,))[0]))
    print(f"| {P} → {nxt} (prev {prev}) | {n} | {cnt['same']} | {cnt['eq_next']} | {cnt['eq_prev']} | {cnt['neither']} | {cnt['unclear']} |")
json.dump(out, open("out/q5.json", "w"))
for tier, lo, hi in (("top 20", 1, 20), ("21-60", 21, 60), ("61+", 61, 200)):
    xs = [o for o in out if lo <= o["rank"] <= hi and o["P"] != "P4"]
    c = {k: sum(o["cls"] == k for o in xs) for k in ("same", "eq_next", "eq_prev", "neither", "unclear")}
    print(f"tier {tier} (P6-P9 pooled, n={len(xs)}):", c)
print("\n'neither' cases (practice bot matches neither adjacent scored round), top-60 teams:")
for o in sorted(out, key=lambda o: (o["P"], o["rank"])):
    if o["cls"] == "neither" and o["rank"] <= 60:
        print(f"  {o['P']} {o['team']} (rank {o['rank']}): mean z² vs prev {o['dpa']:.1f}, vs next {o['dpb']:.1f}, prev-vs-next {o['dab']:.1f}; scores prev/practice/next {o['sprev']:.1f}/{o['sp']:.1f}/{o['sn']:.1f}")
# score-based: practice vs following scored, all teams, official results
print("\n## practice score vs following scored score (official results, all active teams)")
print("| practice → scored | n | corr | SD of (practice − scored) | expected SD from sampling noise alone | excess SD | mean abs diff | avalon: practice − scored (our bot) |")
print("|---|---|---|---|---|---|---|---|")
allp = [l for l, _ in ORDER if l.startswith("P")]
nxt_of = {"P1": "R1", "P2": "R1", "P3": "R1", "P4": "R1", "P5": "R2", "P6": "R3", "P7": "R4", "P8": "R5", "P9": "R6"}
bots = {"P1": "m10", "P2": "v3", "P3": "v3b", "P4": "v4", "P5": "v5?", "P6": "v6", "P7": "v7", "P8": "v8b", "P9": "v10", "R1": "v3b", "R2": "v5r", "R3": "v6", "R4": "v7", "R5": "v9s", "R6": "v10"}
for P in allp:
    N = nxt_of[P]
    ts = [t for t in R[P] if not R[P][t]["forfeited"] and not R[N][t]["forfeited"]]
    a = np.array([R[P][t]["avg"] for t in ts]); b = np.array([R[N][t]["avg"] for t in ts])
    se = np.array([math.hypot(R[P][t]["moe"] / 1.96, R[N][t]["moe"] / 1.96) for t in ts])
    d = a - b; ex = math.sqrt(max(d.var() - (se ** 2).mean(), 0))
    print(f"| {P} → {N} | {len(ts)} | {np.corrcoef(a,b)[0,1]:.2f} | {d.std():.2f} | {math.sqrt((se**2).mean()):.2f} | {ex:.2f} | {np.abs(d).mean():.2f} | {R[P]['avalon']['avg']-R[N]['avalon']['avg']:+.2f} ({bots[P]} vs {bots[N]}) |")
# among behaviourally unchanged teams: is practice score biased relative to the scored round?
print("\n## teams whose bot was the same in prev scored, practice and next scored (behaviourally): practice − next scored score")
for P, prev, nxt in TRI:
    xs = [o for o in out if o["P"] == P and o["cls"] == "same"]
    if not xs: continue
    d = np.array([o["sp"] - o["sn"] for o in xs]); se = np.array([math.hypot(R[P][o["team"]]["moe"] / 1.96, R[nxt][o["team"]]["moe"] / 1.96) for o in xs])
    w = np.array([o["sn"] for o in xs])
    hi = d[w >= np.median(w)]; lo = d[w < np.median(w)]
    print(f"  {P}→{nxt}: n={len(xs)} mean diff {d.mean():+.2f} ± {d.std()/math.sqrt(len(d)):.2f}; SD {d.std():.2f} vs noise {math.sqrt((se**2).mean()):.2f}; stronger half {hi.mean():+.2f}, weaker half {lo.mean():+.2f}; slope of diff on scored score {np.polyfit(w, d, 1)[0]:+.3f}")
