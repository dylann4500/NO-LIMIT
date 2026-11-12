import sys, json, time, numpy as np, collections
sys.path.insert(0, '.')
from lib import *
rng = np.random.default_rng(1)
t0 = time.time()
R = {k: Round(k) for k in range(1, 7)}; V = Vocab(R.values()); TOP = R[1].TOP
L = 20
# fix LMS3: merge min-raise into raise
for Rk in R.values():
    m = (V.fam[Rk.g] == "LMS3") & (Rk.val == 1); Rk.val = Rk.val.copy(); Rk.val[m] = 2
    Rk.tteam = Rk.team[Rk.seat]
    # fixed avalon train subsample (1100 seats)
    av = np.flatnonzero(Rk.team == AV); keep = rng.choice(av, 1100, replace=False)
    tm = np.ones(Rk.n, bool); tm[av] = False; tm[keep] = True; Rk.trainseat = tm
names = np.array(V.names)
isent = np.array([n.startswith("LMS entry") for n in names])
ispre = np.array([n.startswith("FQ pf_") for n in names])
FAMS = {
    "ALL": np.isin(V.fam, ["SZ", "FQ", "VAR", "LMS", "OTH"]),
    "SZ sizes": V.fam == "SZ",
    "FQ frequencies": V.fam == "FQ",
    "VAR expose": V.fam == "VAR",
    "LMS limp/minraise/shove": V.fam == "LMS",
    "OTH showdown hands": V.fam == "OTH",
    "NOSIZE (FQ+VAR+OTH+limp/shove)": np.isin(V.fam, ["FQ", "VAR", "OTH", "LMS3"]) | ((V.fam == "LMS") & ~isent),
    "FQ+LMS3 only": np.isin(V.fam, ["FQ", "LMS3"]) | ((V.fam == "LMS") & ~isent),
    "SZ+preflop FQ (Part 4 scorer)": (V.fam == "SZ") | ispre,
}
ALPHA = 10.0

def profiles(Rk, val=None, fam=None, alpha=ALPHA):
    val = Rk.val if val is None else val
    lab = np.where(Rk.trainseat[Rk.seat], Rk.tteam, -1)
    if fam is not None: lab = np.where(fam[Rk.g], lab, -1)
    return log_profiles(counts(Rk.g, val, lab, L, V), V, alpha=alpha)

def evalpair(Rtr, Rte, fam, vtr=None, vte=None, alpha=ALPHA, Ns=NS, seatmask=None, ret_scores=False):
    cols, LP, LU = profiles(Rtr, vtr, fam, alpha)
    vte = Rte.val if vte is None else vte
    out = {}
    for N in Ns:
        m = fam[Rte.g] & (Rte.hid < N)
        if seatmask is not None: m &= seatmask[Rte.seat]
        S = score(Rte.g, vte, Rte.seat, Rte.n, cols, LP, LU, m)
        S += rng.random(S.shape) * 1e-9
        out[N] = S
    return out

def recall(S, team):
    pred = S.argmax(1)
    return np.array([np.mean(pred[team == t] == t) for t in range(L)])

res = {}
if __name__ == "__main__":
    # alpha tuning R1->R2
    for a in (2, 10, 50):
        S = evalpair(R[1], R[2], FAMS["ALL"], alpha=a, Ns=(20, 10**6))
        print("alpha", a, {N: round(recall(S[N], R[2].team).mean() * 100, 1) for N in S}, flush=True)
    tab = collections.defaultdict(list); avtab = collections.defaultdict(list)
    for lagname, pairs in (("lag1", [(k, k + 1) for k in range(1, 6)]), ("lag2", [(k, k + 2) for k in range(1, 5)]), ("same", [(k, k) for k in range(1, 7)])):
        for fn, fam in FAMS.items():
            if lagname != "lag1" and fn not in ("ALL", "SZ sizes", "NOSIZE (FQ+VAR+OTH+limp/shove)"): continue
            for (a, b) in pairs:
                if a == b:
                    # split by table parity: train on even tables, test on odd
                    Rk = R[a]; par = Rk.table % 2 == 0
                    save = Rk.trainseat; Rk.trainseat = par
                    S = evalpair(Rk, Rk, fam, seatmask=~par)
                    Rk.trainseat = save
                    tm = np.where(~par, Rk.team, -1)
                else:
                    S = evalpair(R[a], R[b], fam); tm = R[b].team
                for N in NS:
                    rc = recall(S[N], tm)
                    tab[(lagname, fn, N)].append(rc.mean()); avtab[(lagname, fn, N)].append(rc)
            print(time.time() - t0, lagname, fn, " ".join(f"{np.mean(tab[(lagname, fn, N)]) * 100:5.1f}" for N in NS), flush=True)
    out = {}
    for (lg, fn, N), v in tab.items():
        out[f"{lg}|{fn}|{N}"] = {"mean": float(np.mean(v)), "sd_pairs": float(np.std(v, ddof=1)), "pairs": [float(x) for x in v],
                                 "per_team": np.mean(avtab[(lg, fn, N)], 0).tolist()}
    json.dump({"TOP": TOP, "res": out}, open("res_recog.json", "w"), indent=0)
    for lg in ("lag1", "lag2", "same"):
        print(f"\n{lg}: macro top-1 over 20 teams, mean over round pairs (sd across pairs)")
        print(f"{'family':36s}" + "".join(f"{x:>12s}" for x in NLAB))
        for fn in FAMS:
            if f"{lg}|{fn}|5" not in out: continue
            print(f"{fn:36s}" + "".join(f"{out[f'{lg}|{fn}|{N}']['mean'] * 100:7.1f}({out[f'{lg}|{fn}|{N}']['sd_pairs'] * 100:3.1f})" for N in NS))
    print("\nper-team recall lag1 ALL / SZ / NOSIZE at N=20 and all")
    for i, t in enumerate(TOP):
        print(f"{t:20s}" + " ".join(f"{out[f'lag1|{fn}|{N}']['per_team'][i] * 100:5.0f}" for fn in ("ALL", "SZ sizes", "NOSIZE (FQ+VAR+OTH+limp/shove)", "FQ frequencies") for N in (20, 10**6)))
