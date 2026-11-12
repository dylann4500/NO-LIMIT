import sys, math, json; sys.path.insert(0, '.')
from common import *
import numpy as np
M = [("open","open (first in)"),("open_l1","open, level 1 full table"),("3bet","re-raise (3-bet)"),("3betjam","re-raise all-in"),("f3b","fold to re-raise"),
     ("4bet","4-bet"),("jam","shove (per hand dealt)"),("openjam_short","open-shove under 15bb"),("calljam","call a shove"),("bbfold","BB fold to open"),
     ("vpip","VPIP"),("pfr","PFR"),("cbet","c-bet flop"),
     ("btc1","bet when checked to, flop"),("btc2","... turn"),("btc3","... river"),("fold1","fold to bet, flop"),("fold2","... turn"),("fold3","... river"),
     ("xraise1","raise a flop bet"),("explow","expose lower kept card (showdowns)"),("exp_hi","exposed card T+"),("exp_pair","exposed card pairs flop")]
R = api_results(); S = standings()
active = [t for t in R["R1"] if not any(R[l][t]["forfeited"] for l in SCORED)]
rank = {t: r for r, t, _ in S}
top20 = [t for r, t, _ in S if r <= 20]
print("active in all six rounds:", len(active), "top20:", len(top20))
D = {l: load(l) for l in SCORED}
def tr(l, t, m, minn=30):
    n, k = rate(D[l]["A"], t, m)
    return k / n if n >= minn else None
X = {m: np.array([[tr(l, t, m) if tr(l, t, m) is not None else np.nan for l in SCORED] for t in active]) for m, _ in M}
it = [active.index(t) for t in top20]
io = [i for i, t in enumerate(active) if t != "avalon"]
it_noav = [i for i in it if active[i] != "avalon"]
print("\n## Q2a field mean (team-equal weight, n=%d active teams excl. avalon) and top-20 mean (excl. avalon, n=%d), by scored round" % (len(io), len(it_noav)))
print("| tendency | group | R1 | R2 | R3 | R4 | R5 | R6 | R1→R6 |")
print("|---|---|---|---|---|---|---|---|---|")
FA = {}
for m, lab in M:
    for g, ix in (("field", io), ("top 20", it_noav)):
        v = np.nanmean(X[m][ix], axis=0); FA[(m, g)] = v
        # se of mean across teams
        print(f"| {lab} | {g} | " + " | ".join(f"{100*x:.1f}" for x in v) + f" | {100*(v[5]-v[0]):+.1f} |")
# forecast test
print("\n## Q2c forecast errors (percentage points), target rounds R3..R6")
def fc(series):
    """series: array (..., 6). returns abs errors persist, trend, damped for targets idx 2..5"""
    ep, et, ed = [], [], []
    for j in range(2, 6):
        a, b, c = series[..., j - 2], series[..., j - 1], series[..., j]
        ep.append(np.abs(c - b)); et.append(np.abs(c - (2 * b - a))); ed.append(np.abs(c - (b + 0.5 * (b - a))))
    return np.array(ep), np.array(et), np.array(ed)
rows = []
print("| tendency | field: same-as-last | field: trend | field: half-trend | top20: same | top20: trend | top20: half | team-level: same | team: trend | team: half |")
print("|---|---|---|---|---|---|---|---|---|---|")
agg = {k: [] for k in range(9)}
for m, lab in M:
    vals = []
    for g in ("field", "top 20"):
        ep, et, ed = fc(FA[(m, g)])
        vals += [ep.mean(), et.mean(), ed.mean()]
    ep, et, ed = fc(X[m][io])
    vals += [np.nanmean(ep), np.nanmean(et), np.nanmean(ed)]
    for i, v in enumerate(vals): agg[i].append(v)
    print(f"| {lab} | " + " | ".join(f"{100*v:.2f}" for v in vals) + " |")
print("| **mean over tendencies** | " + " | ".join(f"**{100*np.mean(agg[i]):.2f}**" for i in range(9)) + " |")
# how often does trend beat persistence at field level
wins = sum(1 for m, _ in M for g in ("field", "top 20") for j in range(2, 6)
           if abs(FA[(m, g)][j] - (2 * FA[(m, g)][j - 1] - FA[(m, g)][j - 2])) < abs(FA[(m, g)][j] - FA[(m, g)][j - 1]))
print(f"\ntrend beats same-as-last in {wins} of {len(M)*2*4} (tendency, group, round) forecasts")
# sign persistence of field moves
for g in ("field", "top 20"):
    same = tot = 0; corr_x = []; corr_y = []
    for m, _ in M:
        d = np.diff(FA[(m, g)])
        for j in range(1, 5):
            tot += 1; same += (d[j] * d[j - 1] > 0); corr_x.append(d[j - 1]); corr_y.append(d[j])
    print(g, f"consecutive moves in same direction: {same}/{tot}; correlation of consecutive changes r={np.corrcoef(corr_x, corr_y)[0,1]:.2f}")
# by-transition: does direction persist excluding R1->R2
json.dump({f"{m}|{g}": list(map(float, v)) for (m, g), v in FA.items()}, open("out/q2_field.json", "w"))
# best response at team level
print("\n## Q2b team-level best-response checks: corr(experienced signal in round n, team's change n→n+1), pooled over 5 transitions")
E_ = {l: D[l]["EXP"] for l in SCORED}
def ex(l, t, m, minn=50):
    v = E_[l].get((t, m))
    return v[1] / v[0] if v and v[0] >= minn else np.nan
tests = [("f3b_vs_me", "3bet", "+", "opponents folded to my re-raises → I re-raise more"),
         ("3bet_vs_me", "f3b", "-", "I was re-raised more → I fold to re-raises less"),
         ("3bet_vs_me", "4bet", "+", "I was re-raised more → I 4-bet more"),
         ("fold1_vs_me", "btc1", "+", "opponents folded to my flop bets → I bet flop more"),
         ("fold2_vs_me", "btc2", "+", "opponents folded to my turn bets → I bet turn more"),
         ("calljam_vs_me", "jam", "-", "my shoves got called more → I shove less"),
         ("bbfold_vs_me", "open", "+", "BBs folded to my opens → I open more")]
print("| signal in round n | response n→n+1 | expected sign | r (all active) | n | r (top 20) | n | r among changers (|Δ|>2pp) | n |")
print("|---|---|---|---|---|---|---|---|---|")
for sig, resp, sign, desc in tests:
    xs, ys, xt, yt = [], [], [], []
    for j in range(5):
        # signal relative to the round's field mean
        sv = np.array([ex(SCORED[j], t, sig) for t in active]); sv = sv - np.nanmean(sv)
        dv = X[resp][:, j + 1] - X[resp][:, j]
        for i in io:
            if not (np.isnan(sv[i]) or np.isnan(dv[i])):
                xs.append(sv[i]); ys.append(dv[i])
                if i in it: xt.append(sv[i]); yt.append(dv[i])
    xs, ys = np.array(xs), np.array(ys)
    ch = np.abs(ys) > 0.02
    r = lambda a, b: np.corrcoef(a, b)[0, 1] if len(a) > 5 else float("nan")
    print(f"| {sig} | Δ{resp} | {sign} | {r(xs,ys):+.2f} | {len(xs)} | {r(xt,yt):+.2f} | {len(xt)} | {r(xs[ch],ys[ch]):+.2f} | {ch.sum()} |")
# mean reversion control: corr(level, change)
print("\nreference: corr(own level in round n, own change n→n+1) [regression to the mean / convergence]:")
for m in ("3bet", "f3b", "btc1", "fold1", "jam", "open"):
    xs = np.concatenate([X[m][io, j] - np.nanmean(X[m][io, j]) for j in range(5)]); ys = np.concatenate([X[m][io, j + 1] - X[m][io, j] for j in range(5)])
    ok = ~(np.isnan(xs) | np.isnan(ys)); print(f"  {m}: r={np.corrcoef(xs[ok], ys[ok])[0,1]:+.2f}")
# spread of the field over rounds (convergence?)
print("\nspread across teams (SD, pp) by round:")
for m in ("open", "3bet", "f3b", "jam", "btc1", "fold1", "fold2", "explow"):
    print(f"  {m}: " + " ".join(f"{100*np.nanstd(X[m][io, j]):.1f}" for j in range(6)) + "   top20: " + " ".join(f"{100*np.nanstd(X[m][it_noav, j]):.1f}" for j in range(6)))
print("\n## Q2b' same checks controlling for the team's own level (regression to the mean): standardized coefficient of the signal in Δresp ~ own level + signal + transition dummies")
print("| signal | response | expected | beta (std) | t | n | top-20 beta | t | n |")
print("|---|---|---|---|---|---|---|---|---|")
def ols(Xm, y):
    b, *_ = np.linalg.lstsq(Xm, y, rcond=None); r = y - Xm @ b; s2 = r @ r / (len(y) - Xm.shape[1]); cov = s2 * np.linalg.inv(Xm.T @ Xm)
    return b, np.sqrt(np.diag(cov))
for sig, resp, sign, desc in tests:
    outs = []
    for sub in (io, it_noav):
        rows_ = []
        for j in range(5):
            sv = np.array([ex(SCORED[j], t, sig) for t in active]); lv = X[resp][:, j]; dv = X[resp][:, j + 1] - X[resp][:, j]
            for i in sub:
                if not (np.isnan(sv[i]) or np.isnan(dv[i]) or np.isnan(lv[i])): rows_.append((j, sv[i], lv[i], dv[i]))
        a = np.array(rows_); z = lambda v: (v - v.mean()) / v.std()
        dm = np.column_stack([(a[:, 0] == j).astype(float) for j in range(5)])
        b, se = ols(np.column_stack([z(a[:, 1]), z(a[:, 2]), dm]), z(a[:, 3]))
        outs += [f"{b[0]:+.2f}", f"{b[0]/se[0]:+.1f}", str(len(a))]
    print(f"| {sig} | Δ{resp} | {sign} | " + " | ".join(outs) + " |")
