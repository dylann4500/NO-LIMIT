"""Seat-level in-table response, pass 3 (adds the faced seat's stack bucket and covers flag; 3-bet test fits both
histories jointly). Per team per round logistic regression; see q3b.py for the idea."""
import sys, math, json, pickle, os; sys.path.insert(0, '.')
import numpy as np
from common import *
from q3b import irls, onehot, team_type_rates
OUT = sys.argv[1] if len(sys.argv) > 1 else "out3b"
KIND = sys.argv[2] if len(sys.argv) > 2 else "bay"
LABS = sys.argv[3].split(",") if len(sys.argv) > 3 else SCORED
W_ = os.path.dirname(os.path.abspath(__file__))
def ld(l):
    fid = LAB[l] if KIND == "bay" else l
    return pickle.load(open(f"{W_}/{OUT}/{KIND}_{fid}.pkl", "rb"))
# kind: (ncols, [(name, type metric, n col, k col, min n)], categorical cols, has table-others placebo)
SPEC = {
 "tb":    (22, [("f3b_hist", "f3b", 3, 4, 1), ("open_hist", "open", 19, 14, 5)], [7, 8, 9, 10, 11, 16, 20, 21]),
 "steal": (16, [("bbfold_hist", "bbfold", 3, 4, 1)], [7, 8, 9, 10, 14, 15]),
 "btc":   (18, [("fold_hist", "foldpost", 3, 4, 2)], [7, 8, 9, 10, 11, 14, 15, 16, 17]),
 "fb":    (19, [("bet_hist", "betpost", 3, 4, 3)], [7, 8, 9, 10, 11, 14, 15, 16, 17, 18]),
 "cj":    (16, [("jam_hist", "jam", 3, 4, 5)], [7, 8, 9, 10, 11, 14, 15]),
}
def run():
    res = []
    for l in LABS:
        d = ld(l); teams = d["teams"]; types = team_type_rates(d)
        for kind, (nc, hs, cats) in SPEC.items():
            R = np.frombuffer(d["REC"][kind], dtype=np.int16).reshape(-1, nc)
            R = R[(R[:, 0] >= 0) & (R[:, 1] >= 0)]
            good = np.ones(len(R), bool); devs = []; trs = []
            for nm, tmet, cn, ck, mn in hs:
                tr = types[tmet][R[:, 1]]; hn = R[:, cn].astype(float); hk = R[:, ck].astype(float)
                good &= ~np.isnan(tr) & (hn >= mn)
                devs.append((hk + 4.0 * np.nan_to_num(tr)) / (hn + 4.0) - np.nan_to_num(tr)); trs.append(tr)
            on = R[:, 5].astype(float); ok = R[:, 6].astype(float); f = np.nanmean(types[hs[0][1]]); odev = (ok + 8 * f) / (on + 8) - f
            R = R[good]; devs = [x[good] for x in devs]; trs = [x[good] for x in trs]; odev = odev[good]
            order = np.argsort(R[:, 0], kind="stable"); R = R[order]; devs = [x[order] for x in devs]; trs = [x[order] for x in trs]; odev = odev[order]
            bounds = np.flatnonzero(np.diff(R[:, 0])) + 1; starts = np.r_[0, bounds]; ends = np.r_[bounds, len(R)]
            for a, b in zip(starts, ends):
                if b - a < 1500: continue
                r = R[a:b]; y = r[:, 2].astype(float)
                if y.mean() < 0.005 or y.mean() > 0.995: continue
                cols = [np.ones(b - a)] + [x[a:b] for x in devs] + [x[a:b] - x[a:b].mean() for x in trs] + [odev[a:b]]
                for c in cats: cols += onehot(r[:, c])
                bb, se = irls(np.column_stack(cols), y)
                if bb is None: continue
                p = y.mean(); nh = len(hs)
                for i, (nm, *_ ) in enumerate(hs):
                    res.append(dict(round=l, team=teams[r[0, 0]], test=kind + ":" + nm, n=int(b - a), p=float(p), b=float(bb[1 + i]), se=float(se[1 + i]),
                                    b_type=float(bb[1 + nh + i]), se_type=float(se[1 + nh + i]), b_o=float(bb[1 + 2 * nh]), se_o=float(se[1 + 2 * nh])))
        print(l, len(res), flush=True)
    json.dump(res, open(f"out/q3b2_{KIND}.json", "w"))
if __name__ == "__main__":
    run()
