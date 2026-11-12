import sys, json, numpy as np, collections
sys.path.insert(0, '.')
import recog
from recog import *
rg = np.random.default_rng(7)
isSZ = V.fam == "SZ"
SETS = {"SZ": FAMS["SZ sizes"], "SZ+preFQ": FAMS["SZ+preflop FQ (Part 4 scorer)"], "ALL": FAMS["ALL"], "NOSIZE": FAMS["NOSIZE (FQ+VAR+OTH+limp/shove)"]}
NSS = (5, 10, 20, 40, 10**6)
gname = names
def team_dist(Rk, t):
    """dict g -> (vals, probs) for team t"""
    m = (Rk.tteam == t) & (isSZ[Rk.g] | isent[Rk.g])
    d = {}
    g = Rk.g[m]; v = Rk.val[m]
    for gg in np.unique(g):
        vv, c = np.unique(v[g == gg], return_counts=True); d[gg] = (vv, c / c.sum())
    return d
def modal_table(Rk):
    tab = {}
    acc = collections.defaultdict(lambda: collections.Counter())
    for t in range(L):
        if t == AV: continue
        for gg, (vv, p) in team_dist(Rk, t).items():
            for a, b in zip(vv, p): acc[gg][a] += b
    return {gg: c.most_common(1)[0][0] for gg, c in acc.items()}, acc
def band(name, mode, v):
    n = len(v)
    if mode == "wide":
        if name.startswith("SZ open"): return rg.integers(40, 53, n)
        if name.startswith("SZ bet"): return rg.integers(18, 31, n)
        if name == "SZ 3b": return rg.integers(28, 35, n)
        if name.startswith("SZ raise"): return rg.integers(10, 15, n)
        if name == "SZ gran pre": return rg.choice([0, 1, 2, 3, 4], n, p=[.1, .1, .1, .2, .5])
        if name == "SZ gran post": return rg.choice([0, 2, 3, 4], n, p=[.05, .05, .1, .8])
        if name.startswith("LMS entry"): return np.where((v == 1) | (v == 2), np.where(rg.random(n) < 1 / 13, 1, 2), v)
        return v
    if mode == "narrow":  # our own sizes +-1 unit (0.05bb / 0.025 pot / 0.1x)
        if name.startswith("SZ open") or name.startswith("SZ bet") or name == "SZ 3b": return v + rg.integers(-1, 2, n)
        if name == "SZ gran pre": return rg.choice([0, 1, 2, 3, 4], n, p=[.1, .1, .1, .2, .5])
        if name == "SZ gran post": return rg.choice([0, 2, 3, 4], n, p=[.05, .05, .1, .8])
        return v
def transform(Rk, mode, ref=None, X=None):
    val = Rk.val.copy()
    m = (Rk.tteam == AV) & (isSZ[Rk.g] | isent[Rk.g])
    idx = np.flatnonzero(m); g = Rk.g[idx]
    for gg in np.unique(g):
        ii = idx[g == gg]; nm = gname[gg]
        if mode == "modal":
            mt = ref
            if nm.startswith("LMS entry"):
                # consistent with the modal open size (use BTN table)
                mo = mt.get(V.gid["SZ open BTN"], 50)
                v = val[ii]; val[ii] = np.where((v == 1) | (v == 2), 1 if mo == 40 else 2, v)
            elif gg in mt: val[ii] = mt[gg]
        elif mode in ("wide", "narrow"):
            val[ii] = band(nm, mode, val[ii])
        elif mode == "copy":
            if gg in ref:
                vv, p = ref[gg]
                if nm.startswith("LMS entry"):
                    v = val[ii]; k = (vv == 1) | (vv == 2)
                    if k.any():
                        dr = rg.choice(vv[k], len(ii), p=p[k] / p[k].sum()); val[ii] = np.where((v == 1) | (v == 2), dr, v)
                else: val[ii] = rg.choice(vv, len(ii), p=p)
    return val
def run(label, mk_tr, mk_te, X=None, pairs=range(1, 6)):
    acc = collections.defaultdict(list)
    for k in pairs:
        vtr = mk_tr(R[k], k); vte = mk_te(R[k + 1], k)
        for sn, fam in SETS.items():
            S = evalpair(R[k], R[k + 1], fam, vtr=vtr, vte=vte, Ns=NSS)
            for N in NSS:
                pred = S[N].argmax(1); tm = R[k + 1].team
                pa = pred[tm == AV]
                lab = np.bincount(pa, minlength=L) / len(pa)
                fp = np.mean([np.mean(pred[tm == t] == AV) for t in range(L) if t != AV])
                rc = np.array([np.mean(pred[tm == t] == t) for t in range(L)])
                srt = np.sort(S[N][tm == AV], 1); top3 = np.mean((S[N][tm == AV] >= srt[:, [-3]])[:, AV])
                acc[(sn, N)].append(dict(lab=lab, fp=fp, rc=rc, top3=top3))
    out = {}
    print(f"\n### {label}")
    print(f"{'features':9s} {'N':>4s} | {'avalon found':>12s} {'top3':>5s} {'others called avalon':>20s} {'precision@1/20':>14s} | where avalon seats go (top 3 labels) | n teams >=5% | macro acc" + (f" | {TOP[X]} recall, avalon->{TOP[X]}" if X is not None else ""))
    for sn in SETS:
        for N in NSS:
            a = acc[(sn, N)]; lab = np.mean([x["lab"] for x in a], 0); fp = np.mean([x["fp"] for x in a]); rc = np.mean([x["rc"] for x in a], 0)
            sdv = np.std([x["lab"][AV] for x in a], ddof=1) if len(a) > 1 else 0
            o = np.argsort(-lab)[:3]
            prec = lab[AV] / max(1e-9, lab[AV] + 19 * fp)
            ex = f" | {100 * rc[X]:4.0f}% {100 * lab[X]:4.0f}%" if X is not None else ""
            print(f"{sn:9s} {('all' if N > 999 else str(N)):>4s} | {100 * lab[AV]:6.1f}±{100 * sdv:4.1f} {100 * np.mean([x['top3'] for x in a]):5.1f} {100 * fp:20.2f} {100 * prec:14.0f} | " + ", ".join(f"{TOP[i]} {100 * lab[i]:.0f}%" for i in o) + f" | {int((lab >= .05).sum())} | {100 * rc.mean():.1f}" + ex)
            out[f"{sn}|{N}"] = dict(av=float(lab[AV]), sd=float(sdv), fp=float(fp), lab=lab.tolist(), macro=float(rc.mean()), rc=rc.tolist())
    return out
real = lambda Rk, k: Rk.val
MT = {k: modal_table(R[k]) for k in range(1, 6)}
print("modal size per feature (pooled over the other 19, equal weight) by training round, and how many of the 19 use it for >=50% / >=20% of that action in R6")
for nm in ("SZ open EP", "SZ open CO", "SZ open BTN", "SZ open SB", "SZ 3b", "SZ bet s1", "SZ bet s2", "SZ bet s3", "SZ gran pre", "SZ gran post"):
    gg = V.gid[nm]; sc = 20 if "open" in nm else 10 if "3b" in nm else 40 if "bet" in nm else 1
    mv = MT[5][0].get(gg); sh = []
    for t in range(L):
        if t == AV: continue
        d = team_dist(R[6], t).get(gg)
        sh.append(float(d[1][d[0] == mv].sum()) if d is not None else 0)
    sh = np.array(sh)
    print(f"  {nm:14s} modal by round: " + " ".join(f"R{k}:{MT[k][0].get(gg, 0) / sc:g}" for k in range(1, 6)) + f" | R6 teams using R5-modal >=50%: {(sh >= .5).sum()}, >=20%: {(sh >= .2).sum()}, mean share {100 * sh.mean():.0f}%")
res = {}
res["baseline"] = run("S0 baseline: no masking (profile = previous round)", real, real)
res["modal_unaware"] = run("S1 modal sizes, first round of masking (recogniser's avalon profile is the old one)", real, lambda Rk, k: transform(Rk, "modal", MT[k][0]))
res["modal_aware"] = run("S2 modal sizes, later rounds (recogniser has a profile of masked avalon)", lambda Rk, k: transform(Rk, "modal", MT[k][0]), lambda Rk, k: transform(Rk, "modal", MT[k][0]))
res["wide_unaware"] = run("S3a randomised sizes in a wide band, first round", real, lambda Rk, k: transform(Rk, "wide"))
res["wide_aware"] = run("S3b randomised sizes in a wide band, later rounds (recogniser has the randomised profile)", lambda Rk, k: transform(Rk, "wide"), lambda Rk, k: transform(Rk, "wide"))
res["narrow_unaware"] = run("S3c our own sizes jittered by one step (0.05bb / 2.5% pot), first round", real, lambda Rk, k: transform(Rk, "narrow"))
res["narrow_aware"] = run("S3d our own sizes jittered by one step, later rounds", lambda Rk, k: transform(Rk, "narrow"), lambda Rk, k: transform(Rk, "narrow"))
for X in (1, 0, 9, 10):
    res[f"copy{X}_unaware"] = run(f"S4 copy {TOP[X]}'s sizes (its previous-round distribution), first round", real, lambda Rk, k: transform(Rk, "copy", team_dist(R[k], X)), X=X)
    res[f"copy{X}_aware"] = run(f"S4 copy {TOP[X]}'s sizes, later rounds (recogniser has the hybrid profile)", lambda Rk, k: transform(Rk, "copy", team_dist(R[k], X)), lambda Rk, k: transform(Rk, "copy", team_dist(R[k], X)), X=X)
json.dump(res, open("res_mask.json", "w"))
