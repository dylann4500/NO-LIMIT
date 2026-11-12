import sys, json, numpy as np, collections, pickle
sys.path.insert(0, '.')
from recog import *
NF = (2, 3, 5, 8, 10, 15, 20, 30, 40, 60)
print("avalon hands per table: mean %.1f median %d; other top-20: mean %.1f" % (R[6].nh[R[6].team == AV].mean(), np.median(R[6].nh[R[6].team == AV]), R[6].nh[R[6].team != AV].mean()))
print("table length (hands, any seat live) approx = max hid+1: median", int(np.median([R[6].hid[R[6].off[i]:R[6].off[i + 1]].max() + 1 for i in np.flatnonzero(R[6].team == AV)[:3000] if R[6].off[i + 1] > R[6].off[i]])))
print("\nHOW EARLY (lag-1 profiles, mean of 5 round pairs): avalon seats called avalon / other teams' seats called avalon / precision with a 1-in-20 prior / share with NB posterior>=0.9")
for fn in ("ALL", "SZ sizes", "NOSIZE (FQ+VAR+OTH+limp/shove)"):
    fam = FAMS[fn]; acc = collections.defaultdict(list)
    for k in range(1, 6):
        S = evalpair(R[k], R[k + 1], fam, Ns=NF); tm = R[k + 1].team
        for N in NF:
            pred = S[N].argmax(1); tp = np.mean(pred[tm == AV] == AV); fp = np.mean([np.mean(pred[tm == t] == AV) for t in range(L) if t != AV])
            Z = S[N] - S[N].max(1, keepdims=True); P = np.exp(Z); P /= P.sum(1, keepdims=True)
            conf = np.mean(P[tm == AV, AV] >= 0.9); fconf = np.mean([np.mean(P[tm == t, AV] >= 0.9) for t in range(L) if t != AV])
            ntok = np.bincount(R[k + 1].seat[fam[R[k + 1].g] & (R[k + 1].hid < N)], minlength=R[k + 1].n)[tm == AV].mean()
            acc[N].append((tp, fp, conf, fconf, ntok))
    print(fn)
    for N in NF:
        tp, fp, conf, fconf, ntok = np.mean(acc[N], 0)
        print(f"  after {N:3d} hands: found {100 * tp:5.1f}%  false {100 * fp:5.2f}%  precision {100 * tp / (tp + 19 * fp):4.0f}% | posterior>=0.9: {100 * conf:5.1f}% of our seats, {100 * fconf:5.2f}% of others' (precision {100 * conf / max(1e-9, conf + 19 * fconf):3.0f}%) | tokens seen {ntok:5.1f}")
# feature information: per-hand LLR avalon vs mixture of others, lag-1
print("\nWHICH FEATURES GIVE US AWAY: mean log2-likelihood ratio (avalon profile vs equal mixture of the other 19), bits per 100 hands of ours, lag-1 profiles, mean over pairs")
grp = np.array([" ".join(n.split()[:2]) if not n.startswith("FQ p") else " ".join(n.split()[:2]) for n in names])
ug = sorted(set(grp)); gi = np.array([ug.index(x) for x in grp])
tot = np.zeros(len(ug)); occ = np.zeros(len(ug)); near = collections.defaultdict(lambda: np.zeros(L))
for k in range(1, 6):
    cols, LP, LU = profiles(R[k], None, FAMS["ALL"] | (V.fam == "LMS3"))
    Rt = R[k + 1]; m = Rt.tteam == AV
    key = Rt.g[m] * 4096 + Rt.val[m]; pos = np.searchsorted(cols, key); pos[pos >= len(cols)] = 0; hit = cols[pos] == key
    lp = np.where(hit[None, :], LP[:, pos], LU[:, Rt.g[m]])  # [L, ntok]
    oth = [t for t in range(L) if t != AV]
    mix = np.log(np.exp(lp[oth]).mean(0))
    llr = (lp[AV] - mix) / np.log(2)
    hands = Rt.nh[Rt.team == AV].sum()
    tot += np.bincount(gi[Rt.g[m]], weights=llr, minlength=len(ug)) / hands * 100 / 5
    occ += np.bincount(gi[Rt.g[m]], minlength=len(ug)) / hands * 100 / 5
    for fn in ("SZ sizes", "FQ frequencies", "NOSIZE (FQ+VAR+OTH+limp/shove)", "ALL"):
        fm = FAMS[fn][Rt.g[m]]
        near[fn] += ((lp[AV][None, :] - lp)[:, fm].sum(1) / np.log(2) / hands * 100) / 5
o = np.argsort(-tot)
for i in o[:22]: print(f"  {ug[i]:24s} {tot[i]:7.1f} bits/100 hands   ({occ[i]:5.1f} occurrences/100 hands, {tot[i] / max(occ[i], 1e-9):.2f} bits each)")
fam_of = np.array([g.split()[0] for g in ug])
for f in ("SZ", "FQ", "LMS", "VAR", "OTH"): print(f"  family {f}: {tot[fam_of == f].sum():.1f} bits/100 hands")
print("\nNEAREST TEAMS to avalon (bits per 100 of our hands separating us from that team's profile; small = confusable)")
for fn, v in near.items():
    o = np.argsort(v); o = [i for i in o if i != AV][:5]
    print(f"  {fn:32s} " + ", ".join(f"{TOP[i]} {v[i]:.0f}" for i in o))
