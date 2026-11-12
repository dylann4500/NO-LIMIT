"""Seat-level in-table response tests. For each actor team (per round), logistic regression of the action on the
faced seat's in-table history (deviation from that seat's team norm), controlling the seat's team norm, the rest of
the table's history (placebo), blind level, players left, stack buckets and situation dummies."""
import sys, math, json, pickle; sys.path.insert(0, '.')
import numpy as np
from common import *
OUT = sys.argv[1] if len(sys.argv) > 1 else "out2"
KIND = sys.argv[2] if len(sys.argv) > 2 else "bay"
LABS = sys.argv[3].split(",") if len(sys.argv) > 3 else SCORED
W_ = os.path.dirname(os.path.abspath(__file__))
def ld(l):
    fid = LAB[l] if KIND == "bay" else l
    return pickle.load(open(f"{W_}/{OUT}/{KIND}_{fid}.pkl", "rb"))
# test: (record kind, ncols, type-rate metric for the faced seat's team, categorical extra cols, description, hist prior m)
TESTS = {
 "tb":    (20, "f3b",   [10, 11, 16, 18], "re-raise an opener who has folded to re-raises more often earlier at this table"),
 "tb_open": (20, "open", [10, 11, 16, 18], "re-raise an opener who has opened more often earlier at this table"),
 "steal": (14, "bbfold", [10, 11],        "open from SB/BTN more when the big blind has folded to opens earlier at this table"),
 "btc":   (16, "foldpost", [10, 11, 14, 15], "bet when checked to (heads-up) more against a seat that has folded to bets earlier at this table"),
 "fb":    (16, "betpost", [10, 11, 14, 15], "fold to a bet (heads-up) less against a seat that has bet more often earlier at this table"),
 "cj":    (14, "jam",   [10, 11],        "call a shove more from a seat that has shoved more often earlier at this table"),
}
def irls(X, y, it=25, ridge=1e-3):
    b = np.zeros(X.shape[1])
    for _ in range(it):
        eta = np.clip(X @ b, -30, 30); p = 1 / (1 + np.exp(-eta)); w = p * (1 - p) + 1e-9
        H = X.T @ (X * w[:, None]) + ridge * np.eye(X.shape[1]); g = X.T @ (y - p) - ridge * b
        try: step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError: return None, None
        b += step
        if np.abs(step).max() < 1e-7: break
    try: cov = np.linalg.inv(H)
    except np.linalg.LinAlgError: return None, None
    return b, np.sqrt(np.diag(cov))
def onehot(col):
    vals = np.unique(col)
    return [(col == v).astype(float) for v in vals[1:]]
def team_type_rates(d):
    """per team index: round-level rates used as the faced seat's 'type'"""
    A = d["A"]; teams = d["teams"]; out = {}
    for name, (num, den) in {"f3b": ("f3b", None), "open": ("open", None), "bbfold": ("bbfold", None), "jam": ("jam", None)}.items():
        v = np.full(len(teams), np.nan)
        for i, t in enumerate(teams):
            n, k = rate(A, t, num)
            if n >= 50: v[i] = k / n
        out[name] = v
    # postflop fold-to-bet (all streets), bet when no bet faced (all streets)
    for name, ms in (("foldpost", ["fold1", "fold2", "fold3"]), ("betpost", ["bet1", "bet2", "bet3"])):
        v = np.full(len(teams), np.nan)
        for i, t in enumerate(teams):
            n = k = 0
            for m in ms:
                a, b = rate(A, t, m); n += a; k += b
            if n >= 50: v[i] = k / n
        out[name] = v
    return out
def run():
    res = []
    for l in LABS:
        d = ld(l); teams = d["teams"]; types = team_type_rates(d)
        for test, (nc, tmet, cats) in ((k, v[:3]) for k, v in TESTS.items()):
            kind = "tb" if test == "tb_open" else test
            R = np.frombuffer(d["REC"][kind], dtype=np.int16).reshape(-1, nc)
            R = R[(R[:, 0] >= 0) & (R[:, 1] >= 0)]
            tr = types[tmet][R[:, 1]]
            if test == "tb_open":
                hn, hk = R[:, 19].astype(float), R[:, 14].astype(float)      # S open opps, S opens
                on = ok = None
            else:
                hn, hk = R[:, 3].astype(float), R[:, 4].astype(float)
                on, ok = R[:, 5].astype(float), R[:, 6].astype(float)
            good = ~np.isnan(tr) & (hn >= (5 if test in ("tb_open", "cj") else 1))
            R, tr, hn, hk = R[good], tr[good], hn[good], hk[good]
            m = 4.0
            dev = (hk + m * tr) / (hn + m) - tr          # shrunk in-table deviation of the faced seat from its team norm
            if on is not None:
                on, ok = on[good], ok[good]; f = np.nanmean(types[tmet])
                odev = (ok + 8 * f) / (on + 8) - f
            for ai in np.unique(R[:, 0]):
                sel = R[:, 0] == ai
                if sel.sum() < 1500: continue
                r = R[sel]; y = r[:, 2].astype(float)
                if y.mean() < 0.005 or y.mean() > 0.995: continue
                cols = [np.ones(sel.sum()), dev[sel], tr[sel] - tr[sel].mean()]
                names = ["c", "dev", "type"]
                if on is not None: cols.append(odev[sel]); names.append("odev")
                for c in [7, 8, 9] + cats:
                    cols += onehot(r[:, c])
                X = np.column_stack(cols)
                b, se = irls(X, y)
                if b is None: continue
                p = y.mean()
                res.append(dict(round=l, team=teams[ai], test=test, n=int(sel.sum()), p=float(p), b=float(b[1]), se=float(se[1]),
                                b_type=float(b[2]), se_type=float(se[2]), b_o=float(b[3]) if on is not None else None,
                                se_o=float(se[3]) if on is not None else None, sd_dev=float(dev[sel].std())))
        print(l, len(res), flush=True)
    json.dump(res, open(f"out/q3b_{KIND}.json", "w"))
if __name__ == "__main__":
    run()
