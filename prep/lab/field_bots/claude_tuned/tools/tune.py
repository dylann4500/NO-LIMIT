"""Parameter evaluation and search on the own simulator.

usage:
  tune.py eval  [--tables N] [--params file.json]          mean points of a param set in the mixed field
  tune.py search [--tables N] [--rounds R]                  coordinate search from the current params
"""
import argparse
import json
import math
import os
import random
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim  # noqa: E402
import opponents as O  # noqa: E402
import agent as A  # noqa: E402

FIELD = [("tag", 3.0), ("lag", 1.5), ("station", 1.0), ("nit", 1.0), ("pusher", 1.5), ("maniac", 0.5),
         ("mirror", 2.5), ("flaky", 1.5), ("minr", 0.3), ("cof", 0.4)]

# (name, mode, step, lo, hi): mode "mul" scales by (1 +/- step), "add" shifts by +/- step
SPACE = [
    ("open_ep", "mul", 0.25, 0.04, 0.4), ("open_mp", "mul", 0.25, 0.05, 0.5), ("open_co", "mul", 0.25, 0.08, 0.7),
    ("open_btn", "mul", 0.25, 0.1, 0.9), ("open_sb", "mul", 0.25, 0.1, 1.0), ("open_bb", "add", 0.4, 2.0, 4.0),
    ("iso_pct", "mul", 0.3, 0.03, 0.4), ("limp_pct", "mul", 0.3, 0.0, 0.7), ("bb_raise_pct", "mul", 0.4, 0.01, 0.3),
    ("steal_adapt", "add", 0.4, 0.0, 2.0),
    ("shove_bb", "add", 3.0, 6.0, 25.0), ("sc_base", "mul", 0.25, 0.04, 0.6), ("sc_exp", "add", 0.25, 0.0, 1.5),
    ("bb_call_mult", "add", 0.3, 0.8, 2.5), ("adapt", "add", 0.3, 0.0, 1.5), ("shove_margin", "add", 0.3, -1.0, 2.0),
    ("ai_call_margin", "add", 0.3, -1.0, 2.0), ("sv_base", "mul", 0.25, 0.08, 0.8), ("behind_pen", "add", 0.15, 0.0, 1.0),
    ("pfr_prior", "mul", 0.25, 0.06, 0.5), ("rng_mult", "mul", 0.2, 0.5, 2.5), ("rr_mult", "mul", 0.25, 0.1, 0.8),
    ("tb_eq", "add", 0.03, 0.5, 0.75), ("tb_mult", "add", 0.5, 2.2, 4.5), ("fb_eq", "add", 0.03, 0.45, 0.7),
    ("call_margin", "add", 0.03, -0.05, 0.2), ("mw", "add", 0.2, 0.3, 1.2), ("reshove_bb", "add", 5.0, 10.0, 45.0),
    ("call_3b_frac", "mul", 0.25, 0.1, 0.9), ("commit_frac", "add", 0.08, 0.2, 0.7),
    ("vb1", "add", 0.04, 0.45, 0.85), ("vb2", "add", 0.04, 0.45, 0.85), ("vb3", "add", 0.04, 0.45, 0.9),
    ("bs1", "add", 0.15, 0.25, 1.3), ("bs2", "add", 0.15, 0.25, 1.3), ("bs3", "add", 0.15, 0.25, 1.5),
    ("bf1", "mul", 0.2, 0.15, 1.0), ("bf2", "mul", 0.2, 0.15, 1.0), ("bf3", "mul", 0.2, 0.15, 1.0),
    ("bs_exp", "add", 0.2, 0.0, 1.0), ("af_adapt", "add", 0.3, 0.0, 1.5), ("raise_f", "mul", 0.2, 0.2, 1.0),
    ("cm1", "add", 0.03, -0.15, 0.2), ("cm2", "add", 0.03, -0.15, 0.2), ("cm3", "add", 0.03, -0.15, 0.2),
    ("rz1", "add", 0.04, 0.6, 0.97), ("rz2", "add", 0.04, 0.6, 0.97), ("rz3", "add", 0.04, 0.6, 0.97),
    ("rz_frac", "add", 0.25, 0.4, 2.0), ("cbet", "add", 0.15, 0.0, 1.0),
    ("bl1", "add", 0.06, 0.0, 0.6), ("bl2", "add", 0.06, 0.0, 0.6), ("bl3", "add", 0.05, 0.0, 0.6),
    ("bl_max3", "add", 0.08, 0.05, 0.6), ("fold_adapt", "add", 0.4, 0.0, 2.0), ("jam_spr", "add", 0.25, 0.0, 2.0),
    ("fold_tax", "add", 0.4, 0.0, 3.0),
]


def variant(base, name, mode, step, lo, hi, sign):
    v = base[name]
    nv = v * (1 + sign * step) if mode == "mul" else v + sign * step
    nv = max(lo, min(hi, nv))
    if abs(nv - v) < 1e-9:
        return None
    d = dict(base)
    d[name] = round(nv, 4)
    return d
WORKERS = 14
FIELDS = {
    "mix": FIELD,
    "self": [("mirror", 1.0)],
    "tag": [("tag", 3.0), ("flaky", 2.0), ("pusher", 1.0), ("nit", 1.0)],
    "loose": [("lag", 2.0), ("station", 2.0), ("maniac", 1.0), ("minr", 0.5), ("tag", 1.0)],
    "weak": [("cof", 1.0), ("minr", 1.0), ("flaky", 1.0), ("station", 1.0)],
}


def pick(rng, field):
    tot = sum(w for _, w in field)
    r = rng.uniform(0, tot)
    for name, w in field:
        r -= w
        if r <= 0:
            return name
    return field[-1][0]


def run_chunk(args):
    cand_list, base, seeds, k_cand, field = args
    out = []
    lat = []
    fails = 0
    dec = 0
    ex = []
    for sd in seeds:
        rng = random.Random(sd)
        seats = list(range(8))
        rng.shuffle(seats)
        cseats = set(seats[:k_cand])
        names = [None] * 8
        for i in range(8):
            if i not in cseats:
                names[i] = pick(rng, field)
        opp_seed = rng.randrange(10 ** 9)
        row = []
        for cand in cand_list:
            orng = random.Random(opp_seed)
            bots = []
            for i in range(8):
                if i in cseats:
                    bots.append(A.Agent(cand))
                elif names[i] == "mirror":
                    bots.append(A.Agent(base))
                else:
                    bots.append(O.ARCH[names[i]](orng))
            st = sim.Stats()
            random.seed(sd * 31 + 7)
            pts, hands = sim.play_table(bots, random.Random(sd + 1), track=cseats, stats=st, deal_seed=sd)
            row.append(sum(pts[i] for i in cseats) / k_cand)
            lat.extend(st.lat)
            fails += st.fails
            dec += st.decisions
            ex.extend(st.fail_ex[:2])
        out.append(row)
    lat.sort()
    return out, (lat[len(lat) // 2] if lat else 0, lat[int(len(lat) * 0.99)] if lat else 0, lat[-1] if lat else 0), fails, dec, ex[:3]


def perturbed(base, signs, scale=1.0):
    d = dict(base)
    for (name, mode, step, lo, hi), sg in zip(SPACE, signs):
        if sg == 0:
            continue
        v = base[name]
        nv = v * (1 + sg * step * scale) if mode == "mul" else v + sg * step * scale
        d[name] = max(lo, min(hi, nv))
    return d


def run_grad_chunk(args):
    base, seeds, k_cand, field, scale = args
    rows = []
    for sd in seeds:
        rng = random.Random(sd)
        seats = list(range(8))
        rng.shuffle(seats)
        cseats = seats[:k_cand]
        names = [None] * 8
        bots = [None] * 8
        signs = {}
        for i in range(8):
            if i in cseats:
                sg = [rng.choice((-1, 1)) for _ in SPACE]
                signs[i] = sg
                bots[i] = A.Agent(perturbed(base, sg, scale))
            else:
                names[i] = pick(rng, field)
        orng = random.Random(rng.randrange(10 ** 9))
        for i in range(8):
            if bots[i] is None:
                bots[i] = A.Agent(base) if names[i] == "mirror" else O.ARCH[names[i]](orng)
        random.seed(sd * 31 + 7)
        pts, hands = sim.play_table(bots, random.Random(sd + 1), deal_seed=sd)
        for i in cseats:
            rows.append(([bots[i].P[x[0]] for x in SPACE], pts[i]))
    return rows


def coded(base, vals):
    out = []
    for (name, mode, step, lo, hi), v in zip(SPACE, vals):
        b = base[name]
        out.append((v - b) / (step * b) if mode == "mul" and b else (v - b) / step)
    return out


def collect(base, n_tables, seed, k_cand, pool, field=FIELD, scale=1.0):
    seeds = [seed * 100003 + t for t in range(n_tables)]
    chunks = [seeds[i::WORKERS * 3] for i in range(WORKERS * 3)]
    res = pool.map(run_grad_chunk, [(base, ch, k_cand, field, scale) for ch in chunks if ch])
    return [r for ch in res for r in ch]


def regress(base, rows):
    import numpy as np
    X = np.array([[1.0] + coded(base, vals) for vals, _ in rows])
    y = np.array([p for _, p in rows])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = resid @ resid / (len(y) - X.shape[1])
    cov = s2 * np.linalg.inv(X.T @ X)
    return beta, np.sqrt(np.diag(cov))


def grad(base, n_tables, seed, k_cand, pool, field=FIELD, scale=1.0):
    import numpy as np
    seeds = [seed * 100003 + t for t in range(n_tables)]
    chunks = [seeds[i::WORKERS * 3] for i in range(WORKERS * 3)]
    res = pool.map(run_grad_chunk, [(base, ch, k_cand, field, scale) for ch in chunks if ch])
    rows = [r for ch in res for r in ch]
    X = np.array([[1.0] + coded(base, vals) for vals, _ in rows])
    y = np.array([p for _, p in rows])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = resid @ resid / (len(y) - X.shape[1])
    cov = s2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    return beta, se, len(y)


def evaluate(cand_list, base, n_tables, seed=1, k_cand=2, field=FIELD, pool=None):
    seeds = [seed * 100003 + t for t in range(n_tables)]
    chunks = [seeds[i::WORKERS * 2] for i in range(WORKERS * 2)]
    args = [(cand_list, base, ch, k_cand, field) for ch in chunks if ch]
    res = pool.map(run_chunk, args)
    rows = []
    lats = []
    fails = dec = 0
    ex = []
    for r, l, f, d, e in res:
        rows.extend(r)
        lats.append(l)
        fails += f
        dec += d
        ex.extend(e)
    n = len(rows)
    k = len(cand_list)
    means = [sum(r[j] for r in rows) / n for j in range(k)]
    # paired SE vs the first entry
    ses = []
    for j in range(k):
        d = [r[j] - r[0] for r in rows]
        m = sum(d) / n
        sd = math.sqrt(max(0.0, sum((x - m) ** 2 for x in d) / max(1, n - 1)) / n)
        ses.append(sd)
    sd0 = math.sqrt(sum((r[0] - means[0]) ** 2 for r in rows) / max(1, n - 1) / n)
    return means, ses, sd0, {"p50_us": max(l[0] for l in lats) / 1e3, "p99_us": max(l[1] for l in lats) / 1e3,
                             "max_us": max(l[2] for l in lats) / 1e3, "fails": fails, "decisions": dec, "ex": ex[:3]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode")
    ap.add_argument("--tables", type=int, default=280)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--params", default=None)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--only", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--z", type=float, default=1.5)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--move", type=float, default=1.0)
    ap.add_argument("--window", type=int, default=3)
    ap.add_argument("--other", default=None)
    ap.add_argument("--fields", default="mix,self,tag,loose,weak")
    ap.add_argument("--maxmove", type=int, default=8)
    a = ap.parse_args()
    base = dict(A.P0)
    if a.params:
        base.update(json.load(open(a.params)))
    with Pool(WORKERS) as pool:
        t = time.time()
        if a.mode == "eval":
            means, ses, sd0, info = evaluate([base], base, a.tables, a.seed, a.k, pool=pool)
            print(json.dumps({"mean": means[0], "se": sd0, "info": info, "secs": time.time() - t}))
        elif a.mode == "compare":
            other = dict(A.P0)
            if a.other:
                other.update(json.load(open(a.other)))
            for fname in a.fields.split(","):
                means, ses, sd0, info = evaluate([other, base], other, a.tables, a.seed, a.k, field=FIELDS[fname], pool=pool)
                print("%-6s other=%.2f  params=%.2f  diff=%+.2f ± %.2f  (%.0fs)" % (
                    fname, means[0], means[1], means[1] - means[0], ses[1], time.time() - t), flush=True)
        elif a.mode == "agrad":
            out = a.out or os.path.join(HERE, "tuned.json")
            log = open(os.path.join(HERE, "agrad_log.txt"), "a")
            hist = []
            for it in range(a.rounds):
                hist.append(collect(base, a.tables, a.seed + 1000 * it, a.k, pool, scale=a.scale))
                hist = hist[-a.window:]
                rows = [r for h in hist for r in h]
                beta, se = regress(base, rows)
                lines = ["iter %d  n=%d  intercept=%.2f  (%.0fs)" % (it, len(rows), beta[0], time.time() - t)]
                moved = []
                ranked = sorted(range(len(SPACE)), key=lambda j: -abs(beta[j + 1] / se[j + 1]))
                for j in ranked:
                    name, mode, step, lo, hi = SPACE[j]
                    b, e = beta[j + 1], se[j + 1]
                    tag = ""
                    if abs(b) > a.z * e:
                        v = variant(base, name, mode, step * a.move, lo, hi, 1 if b > 0 else -1)
                        if v is not None:
                            moved.append((name, v[name]))
                            tag = " -> %.4f" % v[name]
                    if abs(b) > 1.5 * e or tag:
                        lines.append("  %-14s %8.4f  beta=%+.3f se=%.3f t=%+.1f%s" % (name, base[name], b, e, b / e, tag))
                for name, new in moved[:a.maxmove]:
                    base[name] = new
                json.dump({k: base[k] for k in A.P0}, open(out, "w"), indent=1)
                txt = "\n".join(lines)
                print(txt, flush=True)
                log.write(txt + "\n")
                log.flush()
        elif a.mode == "grad":
            out = a.out or os.path.join(HERE, "tuned.json")
            log = open(os.path.join(HERE, "grad_log.txt"), "a")
            for it in range(a.rounds):
                beta, se, n = grad(base, a.tables, a.seed + 1000 * it, a.k, pool, scale=a.scale)
                lines = ["iter %d  n=%d  intercept=%.2f  (%.0fs)" % (it, n, beta[0], time.time() - t)]
                moved = []
                ranked = sorted(range(len(SPACE)), key=lambda j: -abs(beta[j + 1] / se[j + 1]))
                for j in ranked:
                    name, mode, step, lo, hi = SPACE[j]
                    b, e = beta[j + 1], se[j + 1]
                    tag = ""
                    if abs(b) > a.z * e:
                        v = variant(base, name, mode, step * a.move, lo, hi, 1 if b > 0 else -1)
                        if v is not None:
                            moved.append((name, base[name], v[name]))
                            tag = " -> %.4f" % v[name]
                    lines.append("  %-14s %8.4f  beta=%+.3f se=%.3f t=%+.1f%s" % (name, base[name], b, e, b / e, tag))
                for name, old, new in moved:
                    base[name] = new
                json.dump({k: base[k] for k in A.P0}, open(out, "w"), indent=1)
                txt = "\n".join(lines)
                print(txt, flush=True)
                log.write(txt + "\n")
                log.flush()
        elif a.mode == "search":
            out = a.out or os.path.join(HERE, "tuned.json")
            names = [x[0] for x in SPACE]
            if a.only:
                names = a.only.split(",")
            spec = {x[0]: x for x in SPACE}
            log = open(os.path.join(HERE, "search_log.txt"), "a")
            seed = a.seed
            for rnd in range(a.rounds):
                order = names[:]
                random.Random(seed + rnd).shuffle(order)
                for name in order:
                    _, mode, step, lo, hi = spec[name]
                    vs = [variant(base, name, mode, step, lo, hi, s) for s in (+1, -1)]
                    cl = [base] + [v for v in vs if v is not None]
                    seed += 1
                    means, ses, sd0, info = evaluate(cl, base, a.tables, seed, a.k, pool=pool)
                    j = max(range(len(cl)), key=lambda i: means[i])
                    msg = "r%d %-14s base=%.3f  %s  -> " % (rnd, name, base[name], " ".join(
                        "%.3f:%.2f(+%.2f±%.2f)" % (c[name], m, m - means[0], s) for c, m, s in zip(cl[1:], means[1:], ses[1:])))
                    if j != 0 and means[j] - means[0] > a.z * ses[j]:
                        base = cl[j]
                        msg += "ACCEPT %.4f" % base[name]
                        json.dump({k: base[k] for k in A.P0}, open(out, "w"), indent=1)
                    else:
                        msg += "keep"
                    msg += "  [base %.2f, %.0fs]" % (means[0], time.time() - t)
                    print(msg, flush=True)
                    log.write(msg + "\n")
                    log.flush()


if __name__ == "__main__":
    main()
