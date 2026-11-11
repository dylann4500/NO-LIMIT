"""Cross-entropy tuner for the candidate's parameters over a mixture of field guesses.

Maximises the mean z-score across (field, payout) pairs, so the result is not fit to one guess.
Common random seeds across candidates reduce comparison noise.
"""
import json, math, random, sys, time
from multiprocessing import Pool
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import play_table, points_for
from field import ARCHETYPES, FIELDS
from hero import Hero, DEFAULT
import os
if os.environ.get("TUNE_TABLE"):
    from strength import HeroTable as Hero  # tune the lookup-model bot instead
from run import PAYOUTS

SEARCH = {
    "open_a": (0.02, 0.2), "open_b": (0.1, 0.8), "hu_open": (0.3, 1.0), "hu_jam": (0.3, 1.0),
    "sh_widen": (0.0, 5.0), "sh_range": (0.0, 2.0), "jam_scale": (0.4, 1.3),
    "call_open": (0.03, 0.25), "threebet": (0.015, 0.12), "fourbet": (0.01, 0.06),
    "open_size": (2.0, 4.0), "threebet_mult": (2.5, 4.0), "steal_fold_bonus": (0.0, 0.8),
    "jam_m": (5.0, 25.0), "jam_slope": (0.0, 0.2), "call_jam": (0.03, 0.25),
    "call_jam_short": (0.0, 0.05),
    "range_unraised": (0.3, 1.0), "range_bet": (0.1, 0.6), "range_raise": (0.03, 0.3),
    "value_eq": (0.55, 0.85), "bluff_freq": (0.0, 0.5), "bet_frac": (0.33, 1.2), "call_margin": (-0.03, 0.15),
    "raise_eq": (0.7, 0.95), "bully": (0.0, 1.0), "cbet_pfr": (0.0, 0.6), "cap_tight": (0.0, 0.2), "eqcall_margin": (-0.05, 0.2), "vwidth_mult": (0.4, 2.5), "commit_spr": (0.5, 3.0), "icm_margin": (0.0, 0.15),
}
V3_KEYS = {"bully", "cbet_pfr", "cap_tight", "eqcall_margin", "vwidth_mult"}
# TUNE_BASE=1 keeps the optional features out of the search, so their value can be measured separately.
KEYS = [k for k in SEARCH if not (os.environ.get("TUNE_BASE") and k in V3_KEYS)]


def _eval_one(a):
    params, fields, payouts, tables, seed = a
    rng = random.Random(seed)
    random.seed(seed)
    tot = {(f, p): 0.0 for f in fields for p in payouts}
    for f in fields:
        names = list(FIELDS[f])
        w = [FIELDS[f][k] for k in names]
        for _ in range(tables):
            seats = rng.choices(names, w, k=7)
            bots = [ARCHETYPES[s]() for s in seats]
            pos = rng.randrange(8)
            bots.insert(pos, Hero(**params))
            e, nh, s = play_table(bots)
            for p in payouts:
                tot[(f, p)] += points_for(e, s, PAYOUTS[p])[pos]
    return {k: v / tables for k, v in tot.items()}


def cem(fields, payouts, gens=8, pop=40, elite=8, tables=30, procs=10, start=None, seed=1, budget_s=None, log=print):
    rng = random.Random(seed)
    mu = {k: (start or DEFAULT)[k] for k in KEYS}
    sig = {k: (SEARCH[k][1] - SEARCH[k][0]) * 0.25 for k in KEYS}
    t0 = time.time()
    hist = []
    pool = Pool(procs)
    for g in range(gens):
        cands = [dict(mu)]
        for _ in range(pop - 1):
            c = {}
            for k in KEYS:
                lo, hi = SEARCH[k]
                c[k] = min(hi, max(lo, rng.gauss(mu[k], sig[k])))
            cands.append(c)
        gseed = rng.randrange(10 ** 9)
        res = pool.map(_eval_one, [(c, fields, payouts, tables, gseed) for c in cands], chunksize=1)
        # Normalise each (field, payout) cell by that cell's spread across this population.
        keys = list(res[0])
        scores = [0.0] * len(cands)
        for k in keys:
            vals = [r[k] for r in res]
            m = sum(vals) / len(vals)
            sd = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals)) or 1.0
            for i, v in enumerate(vals):
                scores[i] += (v - m) / sd / len(keys)
        order = sorted(range(len(cands)), key=lambda i: -scores[i])[:elite]
        for k in KEYS:
            vals = [cands[i][k] for i in order]
            nm = sum(vals) / elite
            sd = math.sqrt(sum((v - nm) ** 2 for v in vals) / elite)
            mu[k] = 0.7 * nm + 0.3 * mu[k]
            sig[k] = max((SEARCH[k][1] - SEARCH[k][0]) * 0.03, 0.8 * sd + 0.2 * sig[k])
        log(f"gen {g} t={time.time()-t0:.0f}s best_z={scores[order[0]]:.2f} mean_elite_top3={sum(res[i].get((fields[0], payouts[0]), 0) for i in order)/elite:.2f}")
        hist.append(dict(mu))
        if budget_s and time.time() - t0 > budget_s:
            break
    pool.close()
    return mu, hist


if __name__ == "__main__":
    name = sys.argv[1]
    payouts = sys.argv[2].split(",")
    fields = sys.argv[3].split(",")
    gens = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    tables = int(sys.argv[5]) if len(sys.argv) > 5 else 40
    procs = int(sys.argv[6]) if len(sys.argv) > 6 else 10
    start = dict(DEFAULT)
    if os.environ.get("START_JSON"):
        start.update(json.load(open(os.environ["START_JSON"]))["mu"])
    mu, hist = cem(fields, payouts, gens=gens, tables=tables, procs=procs, start=start)
    json.dump({"mu": mu, "hist": hist}, open(f"tuned_{name}.json", "w"), indent=1)
    print(json.dumps(mu, indent=1))
