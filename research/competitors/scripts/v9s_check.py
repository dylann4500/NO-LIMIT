"""v9s sanity: our HU SB first-in (2 alive) and BB vs a single CO/BTN/SB open (5-8 alive). Action mix + ICM points vs the fold counterfactual.\nusage: python -I v9s_check.py HANDS OUT.json"""

import collections, functools, gzip, itertools, json, random, sys
from multiprocessing import Pool
import eval7

PAY = [50, 30, 20]
R = "23456789TJQKA"


def icm(stacks):
    idx = tuple(i for i, s in enumerate(stacks) if s > 0); pr = (PAY + [0] * 8)[:len(idx)]

    @functools.lru_cache(None)
    def rec(rem, place):
        res = [0.0] * len(stacks)
        if place >= len(pr) or not rem: return tuple(res)
        T = sum(stacks[i] for i in rem)
        for i in rem:
            p = stacks[i] / T; res[i] += p * pr[place]
            sub = rec(tuple(j for j in rem if j != i), place + 1)
            for j in range(len(stacks)): res[j] += p * sub[j]
        return tuple(res)
    return rec(idx, 0)


TWO = None  # 2-card class -> HU equity vs random 2 cards


def two_key(a, b):
    ra, rb = R.index(a[0]), R.index(b[0])
    if ra < rb: ra, rb, a, b = rb, ra, b, a
    return (ra, rb, a[1] == b[1] and ra != rb)


def build_two(n=600, seed=1):
    rnd = random.Random(seed); deck = [r + s for r in R for s in "shdc"]; out = {}
    for ra in range(13):
        for rb in range(ra + 1):
            for suited in ((False, True) if ra != rb else (False,)):
                a = R[ra] + "s"; b = R[rb] + ("s" if suited else "h")
                rest = [c for c in deck if c not in (a, b)]; w = 0.0
                for _ in range(n):
                    smp = rnd.sample(rest, 7); opp = smp[:2]; board = smp[2:]
                    h1 = eval7.evaluate([eval7.Card(c) for c in [a, b] + board])
                    h2 = eval7.evaluate([eval7.Card(c) for c in opp + board])
                    w += 1 if h1 > h2 else (0.5 if h1 == h2 else 0)
                out[(ra, rb, suited)] = w / n
    return out


def strength3(c3):
    return max(TWO[two_key(a, b)] for a, b in itertools.combinations(c3, 2))


def init(two):
    global TWO
    TWO = two




def init2(two, cuts):
    global TWO, CUTS
    TWO = two; CUTS = cuts


CUTS = None


def band(q):
    # percentile band of our 3-card strength: top25 / 25-50 / 50-75 / 75-100
    if q >= CUTS[0]: return "top25"
    if q >= CUTS[1]: return "25-50"
    if q >= CUTS[2]: return "50-75"
    return "75-100"


def qual_bb(c3):
    r = [c[0] for c in c3]
    return "A" in r or sum(1 for x in r if x in "TJQK A") >= 2


def qual_open(c3):
    r = [c[0] for c in c3]
    return "A" in r or sum(1 for x in r if x in "TJQKA") >= 2


def proc(args):
    tl, yl = args
    t = json.loads(tl); y = json.loads(yl).get("you")
    if "hands" not in t or not y: return []
    me = y["seat"]; seats = t["seats"]; N = len(seats); out = []
    for hi, h in enumerate(t["hands"]):
        sb_ = h["stacks_before"]; bb = h["blinds"][1]
        if sb_[me] <= 0: continue
        c3 = y["cards"][hi] if hi < len(y["cards"]) else None
        if not c3: continue
        live = [i for i in range(N) if sb_[i] > 0]; n = len(live); btn = h["button"]
        blv = [(e["seat"], e["amount"]) for e in h["events"] if e["kind"] == "blind"]
        sbs = next((x for x, a in blv if a == h["blinds"][0]), blv[0][0] if blv else None)
        bbs = next((x for x, a in blv if a == h["blinds"][1] and x != sbs), None)
        if bbs is None and len(blv) > 1: bbs = [x for x, a in blv if x != sbs][0]
        order = sorted(live, key=lambda i: (i - btn - 1) % N); co = order[-2] if n >= 4 else None
        def pos(i):
            if i == sbs: return "SB"
            if i == bbs: return "BB"
            if i == btn: return "BTN"
            if i == co: return "CO"
            return "EP"
        tot = collections.Counter(); raises = 0; opener = None; callers = 0
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board": break
            if k == "blind": tot[s] += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if s == me:
                spot = None
                if n == 2 and raises == 0 and me == sbs:
                    eff = min(sb_) if False else min(sb_[i] for i in live) / bb
                    spot = "HU_SB_firstin"
                elif n >= 5 and me == bbs and raises == 1 and opener is not None and callers == 0 and pos(opener) in ("CO", "BTN", "SB"):
                    spot = "BB_vs_late_open"
                if spot:
                    eff = min(sb_[me], max(sb_[i] for i in live if i != me)) / bb
                    act = "fold" if k == "fold" else ("call" if k == "call" else ("check" if k == "check" else ("jam" if e["amount"] >= sb_[me] else "raise")))
                    # fold counterfactual: pot goes to the other player (HU) / the opener
                    winner = opener if spot == "BB_vs_late_open" else [i for i in live if i != me][0]
                    cf = [sb_[i] - tot.get(i, 0) for i in range(N)]
                    cf[winner] = sb_[winner] + sum(v for i, v in tot.items() if i != winner)
                    d = h["equity_after"][me] - icm(cf)[me]
                    out.append((spot, act, band(strength3(c3)), qual_bb(c3), round(eff, 1), d))
                break
            if raises == 0 and k == "raise" and e["amount"] < sb_[s]: opener = s
            if raises == 0 and k == "raise" and e["amount"] >= sb_[s]: opener = None
            if raises >= 1 and k == "call": callers += 1
            if k == "call": tot[s] += e["amount"]
            if k == "raise": tot[s] = e["amount"]; raises += 1
    return out


def main():
    two = build_two(); init2(two, None)
    deck = [r + s for r in R for s in "shdc"]
    allh = sorted(strength3(c) for c in itertools.combinations(deck, 3))
    cuts = [allh[int(q * len(allh))] for q in (0.75, 0.50, 0.25)]
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    pairs = [(lines[i], lines[i + 1]) for i in range(0, len(lines) - 1) if lines[i].startswith('{"variant"')]
    with Pool(8, initializer=init2, initargs=(two, cuts)) as p:
        res = [x for r in p.map(proc, pairs, chunksize=16) for x in r]
    json.dump({"ntab": len(pairs), "rows": res}, open(sys.argv[2], "w"))
    print(len(pairs), "tables", len(res), "spots")


if __name__ == "__main__":
    main()
