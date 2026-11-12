import sys, math, json, pickle, os; sys.path.insert(0, '.')
import numpy as np
os.environ["OUTDIR"] = "out2"
from common import *
import q1
from q1b import feats
BR = ["690def26", "de7ac5d3", "188fa79b", "516b7309", "b009537f", "3425f351"]   # scored R1..R6 (order inferred by seriation)
BP = [("1ad66b85", 0, 1), ("4e7ebfdb", 2, 3), ("9b809569", 3, 4)]                 # practice files and the scored rounds either side
PRE = ["1c9f9286", "5fe45583", "61812d38", "dc16f7e0"]
D = {f: load(f, "bos") for f in BR + [p for p, _, _ in BP] + PRE}
HI = {id(d): q1.build_hist_index(d) for d in D.values()}
q1.CORE = q1.CORE + ["bid_any", "bid_big"]; q1.SIZES = ["open0", "open", "3bet", "bet1", "bet2", "bet3", "bidfrac"]
ME = D[BR[0]]["av"]
print("friend's team:", ME, "| tables per scored file:", [D[f]["ntab"] for f in BR])
teams = sorted(set.intersection(*[set(D[f]["PT"]) for f in BR]) - {ME})
print("teams seen in all six scored files:", len(teams), "; median tables per team per round:", int(np.median([D[BR[0]]["PT"][t][0] for t in teams])))
def cmp(a, pa, b, pb, t):
    r, tvs = q1.compare(D[a], pa, D[b], pb, t, HI); s = q1.summarize(r, tvs)
    if s: s["rates"] = {m: (v[0], v[1], v[2], v[3], v[4]) for m, v in r.items()}
    return s
print("\n## Boston Q1: bot changes between consecutive scored rounds")
nullc = {}
for f in BR:
    c = [feats(s)["cls"] for t in teams if (s := cmp(f, 0, f, 1, t))]
    nullc[f] = sum(x != "unchanged" for x in c) / len(c)
print("null check (odd vs even tables of the same file) share flagged changed:", {f[:4]: round(v, 3) for f, v in nullc.items()})
def pts(f, t):
    p = D[f]["PT"][t]; m = p[1] / p[0]; return m, math.sqrt(max(p[4] / p[0] - m * m, 0) / p[0])
rows = []
print("| transition | teams | unchanged | tweak | jump | rewrite-scale | median RMS change among changers (pp) |")
print("|---|---|---|---|---|---|---|")
for i in range(5):
    a, b = BR[i], BR[i + 1]; cl = {}
    for t in teams:
        s = cmp(a, None, b, None, t)
        if s:
            f = feats(s); cl[t] = f
            rows.append(dict(tr=i, team=t, **f, prev=pts(a, t)[0], d=pts(b, t)[0] - pts(a, t)[0]))
    n = {k: sum(v["cls"] == k for v in cl.values()) for k in ("unchanged", "tweak", "jump", "rewrite")}
    print(f"| R{i+1}→R{i+2} | {len(cl)} | {n['unchanged']} | {n['tweak']} | {n['jump']} | {n['rewrite']} | {100*np.median([v['rmsx'] for v in cl.values() if v['cls']!='unchanged']):.1f} |")
# strength tiers from mean points over 6 rounds (weights 1,2,3,5,8,13), estimated from friend's tables
wts = [1, 2, 3, 5, 8, 13]
tot = {t: sum(w * pts(f, t)[0] for w, f in zip(wts, BR)) for t in teams}
order = sorted(teams, key=lambda t: -tot[t]); rk = {t: i + 1 for i, t in enumerate(order)}
print("\nby estimated final standing (weighted points at the friend's tables; noisy, SE ~1 point per team-round):")
for nm, lo, hi in (("1-20", 1, 20), ("21-60", 21, 60), ("61-120", 61, 120), ("121+", 121, 999)):
    x = [r for r in rows if lo <= rk[r["team"]] <= hi]
    print(f"| {nm} | {len(x)} | " + " | ".join(f"{sum(r['cls']==k for r in x)/len(x):.0%}" for k in ("unchanged", "tweak", "jump", "rewrite")) + f" | {100*np.mean([r['rmsx'] for r in x]):.1f} |")
d = np.array([r["d"] for r in rows]); prev = np.array([r["prev"] for r in rows]); sl, ic = np.polyfit(prev, d, 1); res = d - (sl * prev + ic)
print(f"\ndid changes help (Δ points at the friend's tables; SE of one Δ ≈ 1.4, so only group means are meaningful); regression slope on previous score {sl:.2f}")
for k in ("unchanged", "tweak", "jump", "rewrite"):
    ix = np.array([r["cls"] == k for r in rows])
    if ix.sum(): print(f"| {k} | {ix.sum()} | mean Δ {d[ix].mean():+.2f} | adjusted {res[ix].mean():+.2f} ± {res[ix].std()/math.sqrt(ix.sum()):.2f} | SD {d[ix].std():.2f} |")
rm = np.array([r["rmsx"] for r in rows]); print(f"corr(size of change, |Δscore|) = {np.corrcoef(rm, np.abs(d))[0,1]:+.2f}; corr(size, adjusted Δ) = {np.corrcoef(rm, res)[0,1]:+.2f}")
nch = {}
for r in rows: nch.setdefault(r["team"], []).append(r["cls"] != "unchanged")
k = np.array([sum(v) for v in nch.values()]); print("gaps (of 5) in which a team changed:", {i: int((k == i).sum()) for i in range(6)})
# Q2
print("\n## Boston Q2: field mean and top-20 mean by scored round (teams equal weight)")
M = ["open", "open_l1", "3bet", "3betjam", "f3b", "4bet", "jam", "openjam_short", "calljam", "bbfold", "vpip", "pfr", "cbet", "btc1", "btc2", "btc3", "fold1", "fold2", "fold3", "xraise1", "bid_any", "bid_big"]
def tr(f, t, m):
    n, kk = rate(D[f]["A"], t, m); return kk / n if n >= 30 else np.nan
X = {m: np.array([[tr(f, t, m) for f in BR] for t in teams]) for m in M}
top = [teams.index(t) for t in order[:20]]
FA = {}
print("| tendency | group | R1 | R2 | R3 | R4 | R5 | R6 | R1→R6 |"); print("|---|---|---|---|---|---|---|---|---|")
for m in M:
    for g, ix in (("field", list(range(len(teams)))), ("top 20", top)):
        v = np.nanmean(X[m][ix], axis=0); FA[(m, g)] = v
        print(f"| {m} | {g} | " + " | ".join(f"{100*x:.1f}" for x in v) + f" | {100*(v[5]-v[0]):+.1f} |")
def fc(s):
    ep, et, ed = [], [], []
    for j in range(2, 6):
        a, b, c = s[..., j - 2], s[..., j - 1], s[..., j]; ep.append(np.abs(c - b)); et.append(np.abs(c - (2 * b - a))); ed.append(np.abs(c - (b + .5 * (b - a))))
    return np.nanmean(ep), np.nanmean(et), np.nanmean(ed)
for g in ("field", "top 20"):
    e = np.array([fc(FA[(m, g)]) for m in M]); wins = sum(1 for m in M for j in range(2, 6) if abs(FA[(m, g)][j] - (2 * FA[(m, g)][j-1] - FA[(m, g)][j-2])) < abs(FA[(m, g)][j] - FA[(m, g)][j-1]))
    print(f"forecast error ({g}; mean over {len(M)} tendencies, pp): same-as-last {100*e[:,0].mean():.2f}, trend {100*e[:,1].mean():.2f}, half-trend {100*e[:,2].mean():.2f}; trend wins {wins}/{len(M)*4}")
e = np.array([fc(X[m]) for m in M]); print(f"forecast error (team level): same-as-last {100*e[:,0].mean():.2f}, trend {100*e[:,1].mean():.2f}, half-trend {100*e[:,2].mean():.2f}")
# Q5
print("\n## Boston Q5: practice files vs the scored rounds either side")
def chi(a, b, minn=30):
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
    s = 0.0
    for m, (n, k) in pr.items():
        if m not in a or m not in b or a[m][0] < 200 or b[m][0] < 200: continue
        pa = (a[m][1] + 1) / (a[m][0] + 2); pb = (b[m][1] + 1) / (b[m][0] + 2)
        s += k * math.log(pb / pa) + (n - k) * math.log((1 - pb) / (1 - pa))
    return s
def rates_(f, t):
    o = {}
    for m in q1.CORE:
        n, kk = rate(D[f]["A"], t, m)
        if n: o[m] = (n, kk)
    return o
print("| practice (tables) | between | teams | same bot in all three | practice = next | practice = previous | differs from both | practice-only experiment | unclear | fixed-bot shift practice − next | practice − prev |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for P, i, j in BP:
    a_, b_ = BR[i], BR[j]; cnt = {k: 0 for k in "ABCDEF"}; dn = []; dp = []
    for t in teams:
        if t not in D[P]["PT"]: continue
        p, a, b = rates_(P, t), rates_(a_, t), rates_(b_, t)
        if "open" not in p or p["open"][0] < 300: continue
        sab, cab, _ = chi(a, b); spa, cpa, _ = chi(p, a); spb, cpb, _ = chi(p, b)
        dab, dpa, dpb = sab / max(cab, 1), spa / max(cpa, 1), spb / max(cpb, 1); L = llr(p, a, b)
        s = cmp(a_, None, b_, None, t); unchanged = s and feats(s)["cls"] == "unchanged"
        if unchanged: c = "A" if (dpa < 3.5 and dpb < 3.5) else ("E" if (dpa > 6 and dpb > 6) else "F")
        elif dpb < 3.5 and (dpa >= 3.5 or L > 10): c = "B"
        elif dpa < 3.5 and (dpb >= 3.5 or L < -10): c = "C"
        elif dpa > 6 and dpb > 6: c = "D"
        else: c = "F"
        cnt[c] += 1
        if c in "AB": dn.append(pts(P, t)[0] - pts(b_, t)[0])
        if c in "AC": dp.append(pts(P, t)[0] - pts(a_, t)[0])
    n = sum(cnt.values())
    f = lambda v: f"{np.mean(v):+.2f} ± {np.std(v)/math.sqrt(len(v)):.2f} (n={len(v)})" if len(v) > 3 else "-"
    print(f"| {P[:8]} ({D[P]['ntab']}) | R{i+1}–R{j+1} | {n} | " + " | ".join(str(cnt[k]) for k in "ABCDEF") + f" | {f(dn)} | {f(dp)} |")
json.dump(dict(order=order[:40], rk=rk), open("out/boston_rank.json", "w"))
