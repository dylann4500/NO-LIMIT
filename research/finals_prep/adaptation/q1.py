import sys, math, json; sys.path.insert(0, '.')
from common import *
import numpy as np
CORE = ["open","open_l1","limp","openjam_short","3bet","3betjam","coldcall","bbfold","f3b","4bet","calljam","jam","vpip","pfr",
        "cbet","btc1","btc2","btc3","fold1","fold2","fold3","xraise1","exp_hi","exp_pair","explow"]
SIZES = ["open0","open","3bet","bet1","bet2","bet3","exprank"]
def hist(d, team, kind, par=None):
    h = {}
    for (t, k, p, b), c in d["SZ"].items():
        if t == team and k == kind and (par is None or p == par): h[b] = h.get(b, 0) + c
    return h
def build_hist_index(d):
    idx = {}
    for (t, k, p, b), c in d["SZ"].items():
        idx.setdefault((t, k, p), {})[b] = c
    return idx
def tv(h1, h2):
    n1, n2 = sum(h1.values()), sum(h2.values())
    if n1 < 300 or n2 < 300: return None
    return 0.5 * sum(abs(h1.get(b, 0) / n1 - h2.get(b, 0) / n2) for b in set(h1) | set(h2))
def merge(h1, h2):
    o = dict(h1)
    for b, c in h2.items(): o[b] = o.get(b, 0) + c
    return o
def compare(dA, pa, dB, pb, team, HI):
    """dA with parity selection pa (None=both) vs dB/pb. returns dict of per-metric (pa, pb, z) and TVs."""
    res = {}
    for m in CORE:
        n1, k1 = rate(dA["A"], team, m, pa); n2, k2 = rate(dB["A"], team, m, pb)
        if n1 < 40 or n2 < 40: continue
        p1, p2 = k1 / n1, k2 / n2; p = (k1 + k2) / (n1 + n2)
        se = math.sqrt(max(p * (1 - p), 1e-6) * (1 / n1 + 1 / n2))
        res[m] = (p1, p2, (p2 - p1) / se, n1, n2)
    tvs = {}
    for kind in SIZES:
        def hh(d, par):
            ix = HI[id(d)]
            if par is None: return merge(ix.get((team, kind, 0), {}), ix.get((team, kind, 1), {}))
            return ix.get((team, kind, par), {})
        x = tv(hh(dA, pa), hh(dB, pb))
        if x is not None: tvs[kind] = x
    return res, tvs
def summarize(res, tvs):
    if not res: return None
    z = np.array([v[2] for v in res.values()]); dp = np.array([abs(v[1] - v[0]) for v in res.values()])
    return dict(meanz2=float(np.mean(z ** 2)), maxz=float(np.max(np.abs(z))), maxdp=float(dp.max()), meandp=float(dp.mean()),
                maxtv=max(tvs.values()) if tvs else 0.0, n=len(z), top=sorted(((abs(v[1]-v[0]), m, round(v[0],3), round(v[1],3)) for m, v in res.items()), reverse=True)[:3],
                tvs={k: round(v, 3) for k, v in tvs.items()})
if __name__ == "__main__":
    labs = [l for l, _ in ORDER if l != "P5"]
    D = {l: load(l) for l in labs}
    HI = {id(d): build_hist_index(d) for d in D.values()}
    teams = D["R6"]["teams"]
    out = {}
    # null: parity split within each file ; adjacent pairs
    for l in labs:
        for t in teams:
            r, tvs = compare(D[l], 0, D[l], 1, t, HI)
            s = summarize(r, tvs)
            if s:
                s["rates"] = {m: (round(v[0], 4), round(v[1], 4), round(v[2], 2), v[3], v[4]) for m, v in r.items()}
                out[f"{l}|{l}|{t}"] = s
    pairs = [(labs[i], labs[j]) for i in range(len(labs)) for j in range(i + 1, len(labs))]
    for a, b in pairs:
        for t in teams:
            r, tvs = compare(D[a], None, D[b], None, t, HI)
            s = summarize(r, tvs)
            if s:
                s["rates"] = {m: (round(v[0], 4), round(v[1], 4), round(v[2], 2), v[3], v[4]) for m, v in r.items()}
                out[f"{a}|{b}|{t}"] = s
    json.dump(out, open("out/q1_pairs.json", "w"))
    print(len(out))
