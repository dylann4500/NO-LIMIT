"""Heads-up win rate from equal stacks, and finish distribution in the typical field."""
import random, sys, json, math
from multiprocessing import Pool
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import engine
from engine import play_table, points_for, SCHEDULE_DEFAULT
from field import ARCHETYPES, FIELDS
from hero import Hero

# Endgames start at a mid-tournament blind level.
SCHED = SCHEDULE_DEFAULT[3:]

def hu(a):
    opp, params, n, seed = a
    random.seed(seed)
    w = 0
    for i in range(n):
        h = Hero(**params)
        v = ARCHETYPES[opp]()
        bots = [h, v] if i % 2 else [v, h]
        me = 0 if i % 2 else 1
        e, nh, s = play_table(bots, SCHED)
        if me in s and (len(s) == 1 or s[me] > s[1 - me]):
            w += 1
    return w

def dist(a):
    fld, params, n, seed = a
    random.seed(seed)
    names = list(FIELDS[fld]); wt = [FIELDS[fld][k] for k in names]
    c = [0.0] * 8
    for _ in range(n):
        pos = random.randrange(8)
        bots = [ARCHETYPES[s]() for s in random.choices(names, wt, k=7)]
        bots.insert(pos, Hero(**params))
        e, nh, s = play_table(bots)
        for k in range(8):
            pay = [0.0] * 8
            pay[k] = 1.0
            c[k] += points_for(e, s, pay)[pos]
    return c

if __name__ == "__main__":
    params = json.load(open(sys.argv[1]))["mu"] if len(sys.argv) > 1 and sys.argv[1] != "-" else {}
    with Pool(10) as p:
        print("heads-up win% (mid blinds):")
        for o in ["fold", "random", "station", "maniac", "jam20", "jam08", "tag", "nit", "lag", "mc", "shortfold"]:
            r = sum(p.map(hu, [(o, params, 100, s) for s in range(10)]))
            print(f"  vs {o:10} {r/10:5.1f}%", flush=True)
        for fld in ["typical", "strong", "aggro"]:
            rs = p.map(dist, [(fld, params, 300, s) for s in range(10)])
            t = [sum(r[k] for r in rs) / 30.0 for k in range(8)]
            print(f"finish % {fld:8}: " + " ".join(f"{i+1}:{v:4.1f}" for i, v in enumerate(t)), flush=True)
