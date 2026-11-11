"""E8: does the exact ICM price beat the plain candidate? Compared per point table."""
import math, random, sys, json
from multiprocessing import Pool
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import play_table, points_for
from field import ARCHETYPES, FIELDS
from hero import Hero
from hero2 import HeroICM
from run import PAYOUTS


def work(a):
    fld, pn, tables, seed, params = a
    rng = random.Random(seed)
    random.seed(seed)
    names = list(FIELDS[fld])
    w = [FIELDS[fld][k] for k in names]
    res = {"plain": [0.0, 0.0], "icm": [0.0, 0.0]}
    for _ in range(tables):
        for label in res:
            seats = rng.choices(names, w, k=7)
            pos = rng.randrange(8)
            h = Hero(**params) if label == "plain" else HeroICM(payouts=PAYOUTS[pn], **params)
            bots = [ARCHETYPES[s]() for s in seats]
            bots.insert(pos, h)
            e, nh, s = play_table(bots)
            v = points_for(e, s, PAYOUTS[pn])[pos]
            res[label][0] += v
            res[label][1] += v * v
    return res


if __name__ == "__main__":
    params = json.load(open(sys.argv[1]))["mu"] if len(sys.argv) > 1 else {}
    N, procs = 5000, 10
    with Pool(procs) as pool:
        for fld in ["typical", "strong", "aggro", "passive"]:
            for pn in ["top3", "linear", "steep", "wta"]:
                rs = pool.map(work, [(fld, pn, N // procs, 100 + i, params) for i in range(procs)])
                row = []
                for k in ("plain", "icm"):
                    s = sum(r[k][0] for r in rs)
                    s2 = sum(r[k][1] for r in rs)
                    m = s / N
                    se = math.sqrt(max(0, s2 / N - m * m) / N)
                    row.append(f"{k}={m:7.2f}±{se:4.2f}")
                print(f"{fld:8} {pn:7} " + "  ".join(row), flush=True)
