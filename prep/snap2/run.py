"""Parallel tournament runner. Each table: `hero_spec` at one seat, seven field bots."""
import math, random, sys, time, json
from multiprocessing import Pool
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import play_table, points_for, SCHEDULE_DEFAULT
from field import ARCHETYPES, FIELDS
from hero import Hero

# Guesses at the point table. The real one is announced at kickoff, so test across all of these.
PAYOUTS = {
    "top3": [50, 30, 20, 0, 0, 0, 0, 0],
    "top4": [45, 25, 18, 12, 0, 0, 0, 0],
    "steep": [100, 50, 30, 20, 10, 5, 2, 0],
    "linear": [7, 6, 5, 4, 3, 2, 1, 0],
    "wta": [100, 0, 0, 0, 0, 0, 0, 0],
}


def make(spec):
    if isinstance(spec, dict):
        return Hero(**spec)
    return ARCHETYPES[spec]()


def _work(a):
    heroes, field, payout_names, tables, seed, schedule = a
    random.seed(seed)
    names = list(FIELDS[field])
    weights = [FIELDS[field][k] for k in names]
    out = {h: {p: [0.0, 0.0] for p in payout_names} for h in heroes}
    hands = 0
    for t in range(tables):
        for h, spec in heroes.items():
            seats = random.choices(names, weights, k=7)
            bots = [make(s) for s in seats]
            pos = random.randrange(8)
            bots.insert(pos, make(spec))
            elim, nh, surv = play_table(bots, schedule)
            hands += nh
            for pn in payout_names:
                v = points_for(elim, surv, PAYOUTS[pn])[pos]
                c = out[h][pn]
                c[0] += v
                c[1] += v * v
    return out, hands


def evaluate(heroes, field="typical", payouts=("top3", "linear", "steep"), tables=2000, procs=10, seed=7, schedule=SCHEDULE_DEFAULT):
    """Returns {hero: {payout: (mean, stderr)}}."""
    per = max(1, tables // procs)
    jobs = [(heroes, field, list(payouts), per, seed * 1000 + i, schedule) for i in range(procs)]
    with Pool(procs) as pool:
        res = pool.map(_work, jobs)
    tot = per * procs
    final = {}
    for h in heroes:
        final[h] = {}
        for p in payouts:
            s = sum(r[0][h][p][0] for r in res)
            s2 = sum(r[0][h][p][1] for r in res)
            mean = s / tot
            var = max(0.0, s2 / tot - mean * mean)
            final[h][p] = (mean, math.sqrt(var / tot))
    return final, sum(r[1] for r in res)


if __name__ == "__main__":
    t0 = time.time()
    heroes = {k: k for k in ARCHETYPES}
    heroes["HERO"] = {}
    res, hands = evaluate(heroes, tables=int(sys.argv[1]) if len(sys.argv) > 1 else 300)
    dt = time.time() - t0
    print(f"{hands} hands in {dt:.1f}s = {hands/dt:.0f} hands/s")
    fair = {p: sum(v) / 8 for p, v in PAYOUTS.items()}
    for h, r in sorted(res.items(), key=lambda x: -x[1]["top3"][0]):
        print(h.ljust(10), "  ".join(f"{p}:{m:6.2f}±{s:4.2f} (fair {fair[p]:.1f})" for p, (m, s) in r.items()))
