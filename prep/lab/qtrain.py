"""Learns Q overrides on top of a tuned rule, from hand-level utility, in the blended field."""
import json, os, random, sys, time
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import play_table
from field import ARCHETYPES, FIELDS
from mtune import BLEND_FIELDS
import methods


def work(a):
    params, qfile, tables, seed, eps, nmin, delta = a
    random.seed(seed)
    out = {}
    for t in range(tables):
        f = BLEND_FIELDS[t % len(BLEND_FIELDS)]
        names = list(FIELDS[f]); w = [FIELDS[f][k] for k in names]
        bots = [ARCHETYPES[x]() for x in random.choices(names, w, k=7)]
        h = methods.HeroQ(qfile=qfile, eps=eps, nmin=nmin, delta=delta, collect=True, **params)
        bots.insert(random.randrange(8), h)
        play_table(bots)
        for k, row in h.out.items():
            o = out.setdefault(k, [[0.0, 0] for _ in range(5)])
            for i in range(5):
                o[i][0] += row[i][0]; o[i][1] += row[i][1]
    return out


if __name__ == "__main__":
    params = json.load(open(sys.argv[1]))["mu"]
    iters, tables, name = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    tot, qfile = {}, None
    t0 = time.time()
    with Pool(10) as p:
        for it in range(iters):
            res = p.map(work, [(params, qfile, tables // 10, it * 100 + i, 0.1, 300, 0.05) for i in range(10)])
            for k in tot:
                for i in range(5):
                    tot[k][i][0] *= 0.85; tot[k][i][1] *= 0.85
            for r in res:
                for k, row in r.items():
                    o = tot.setdefault(k, [[0.0, 0.0] for _ in range(5)])
                    for i in range(5):
                        o[i][0] += row[i][0]; o[i][1] += row[i][1]
            q = {k: [[(c[0] / c[1] if c[1] else 0.0), int(c[1])] for c in row] for k, row in tot.items()}
            qfile = f"q_{name}.json"
            json.dump(q, open(qfile, "w"))
            methods._QCACHE.clear()
            print(f"iter {it} t={time.time()-t0:.0f}s keys={len(q)}", flush=True)
