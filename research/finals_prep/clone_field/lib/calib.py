"""Calibration helpers.
  calib.py cdf FIELD QLOGDIR             -> FIELD/cdf.json (strength quantile maps from clone logs)
  calib.py compare FIELD SIM.pkl [...]   -> real (fitted) vs simulated clone frequencies
  calib.py adj FIELD SIM.pkl             -> FIELD/adj.json (cell frequencies corrected so simulated match fitted)
"""
import collections, glob, json, math, os, pickle, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fitlib

KEYS = ["vpip", "pfr", "open", "openjam", "limp", "3bet", "fold_to_open", "fold_to_3bet", "4bet", "call_allin",
        "flop_bet", "flop_fold_to_bet", "flop_raise", "turn_bet", "turn_fold_to_bet", "turn_raise",
        "river_bet", "river_fold_to_bet", "river_raise", "sawflop", "wtsd", "wsd",
        "sdagg_w0", "sdagg_w1", "sdagg_w2", "sdagg_w3", "sdcall_w", "ex_low", "hands_alive_per_table"]


def pooled(acc, teams):
    g = fitlib.new_acc()
    for t in teams:
        if t in acc["stats"]:
            fitlib.merge(g, {"cells": {"*": acc["cells"].get(t, {})}, "sizes": {},
                             "stats": {"*": acc["stats"][t]}})
    return g


def cmd_cdf(field, qdir):
    d = collections.defaultdict(list)
    for fn in glob.glob(os.path.join(qdir, "q_*.txt")):
        for ln in open(fn):
            p = ln.split()
            if len(p) == 2:
                d[p[0]].append(float(p[1]))
    out = {}
    for k, v in d.items():
        v.sort()
        m = 400
        out[k] = [round(v[min(len(v) - 1, int((i + 0.5) / m * len(v)))], 4) for i in range(m)]
        print(k, len(v), "median raw q", out[k][m // 2])
    json.dump(out, open(os.path.join(field, "cdf.json"), "w"))


def load_field(field):
    f = json.load(open(os.path.join(field, "field.json")))
    real = pickle.load(open(os.path.join(field, "acc.pkl"), "rb"))
    return f, real


def cmd_compare(field, simp, quiet=False):
    f, real = load_field(field)
    sim = pickle.load(open(simp, "rb"))["acc"]
    teams = [e["team"] for e in f["entries"]]
    # pooled, weighting teams as the sim met them is implicit in the sim; real pooled = all rows
    rp = fitlib.style(pooled(real, teams), "*")
    sp = fitlib.style(pooled(sim, teams), "*")
    rs = {t: fitlib.style(real, t) for t in teams}
    ss = {t: fitlib.style(sim, t) for t in teams if t in sim["stats"]}
    print(f"{'stat':22s} {'real':>7s} {'sim':>7s}   per-team: corr   MAE   (n teams)")
    for k in KEYS:
        xs = [(rs[t][k], ss[t][k]) for t in ss if not (math.isnan(rs[t][k]) or math.isnan(ss[t][k]))]
        n = len(xs)
        mx = sum(x for x, _ in xs) / n
        my = sum(y for _, y in xs) / n
        vx = sum((x - mx) ** 2 for x, _ in xs)
        vy = sum((y - my) ** 2 for _, y in xs)
        cov = sum((x - mx) * (y - my) for x, y in xs)
        corr = cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else float("nan")
        mae = sum(abs(x - y) for x, y in xs) / n
        print(f"{k:22s} {rp[k]:7.3f} {sp[k]:7.3f}            {corr:5.2f} {mae:6.3f}  ({n})")
    # cell-level error, weighted by simulated decisions
    num = den = 0.0
    bykind = collections.defaultdict(lambda: [0.0, 0.0])
    for t in ss:
        P = json.load(open(os.path.join(field, [e for e in f["entries"] if e["team"] == t][0]["folder"], "params.json")))
        for key, c in sim["cells"][t].items():
            n = sum(c)
            tgt = P["cells"].get(key)
            if not tgt or n < 30:
                continue
            err = sum(abs(c[i] / n - tgt[i]) for i in range(4)) / 2
            num += err * n
            den += n
            bykind[key[0]][0] += err * n
            bykind[key[0]][1] += n
    print("cell-level total-variation error (decision-weighted, team cells with n>=30): %.3f" % (num / max(1, den)),
          {k: round(v[0] / v[1], 3) for k, v in sorted(bykind.items())})
    print("clone points/table in sim: sd across teams %.2f; real sd %.2f; corr(real pts, sim pts) %.2f" % pts_corr(rs, ss))


def pts_corr(rs, ss):
    xs = [(rs[t]["pts"], ss[t]["pts"]) for t in ss if ss[t]["tables"] >= 50]
    n = len(xs)
    mx = sum(x for x, _ in xs) / n
    my = sum(y for _, y in xs) / n
    vx = sum((x - mx) ** 2 for x, _ in xs) / n
    vy = sum((y - my) ** 2 for _, y in xs) / n
    cov = sum((x - mx) * (y - my) for x, y in xs) / n
    return vy ** 0.5, vx ** 0.5, cov / math.sqrt(vx * vy)


def cmd_adj(field, simp):
    f, real = load_field(field)
    sim = pickle.load(open(simp, "rb"))["acc"]
    prev = {}
    ap = os.path.join(field, "adj.json")
    if os.path.exists(ap):
        prev = json.load(open(ap))
    teams = [e for e in f["entries"]]
    P = {e["team"]: json.load(open(os.path.join(field, e["folder"], "params.json")))["cells"] for e in teams}
    # pooled delta per cell: decision-weighted target vs simulated
    tsum = collections.defaultdict(lambda: [0.0] * 4)
    ssum = collections.defaultdict(lambda: [0.0] * 4)
    for t, cells in sim["cells"].items():
        if t not in P:
            continue
        for key, c in cells.items():
            n = sum(c)
            tgt = P[t].get(key)
            if not tgt:
                continue
            for i in range(4):
                tsum[key][i] += tgt[i] * n
                ssum[key][i] += c[i]
    out = {}
    for t in P:
        cur_all = prev.get(t, {})
        o = {}
        for key, tgt in P[t].items():
            cur = cur_all.get(key, tgt)
            n_all = sum(ssum[key]) if key in ssum else 0
            pd = [(tsum[key][i] - ssum[key][i]) / n_all for i in range(4)] if n_all >= 200 else [0.0] * 4
            c = sim["cells"].get(t, {}).get(key)
            n = sum(c) if c else 0
            w = n / (n + 60.0)
            v = []
            for i in range(4):
                td = (tgt[i] - c[i] / n) if n else pd[i]
                d = w * td + (1 - w) * pd[i]
                v.append(min(1.0, max(0.0, cur[i] + d)))
            # keep impossible actions impossible, renormalise
            v = [0.0 if tgt[i] == 0 and cur[i] == 0 else v[i] for i in range(4)]
            s = sum(v) or 1.0
            o[key] = [round(x / s, 4) for x in v]
        out[t] = o
    json.dump(out, open(ap, "w"))
    print("wrote", ap)


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "cdf":
        cmd_cdf(sys.argv[2], sys.argv[3])
    elif c == "compare":
        cmd_compare(sys.argv[2], sys.argv[3])
    elif c == "adj":
        cmd_adj(sys.argv[2], sys.argv[3])
