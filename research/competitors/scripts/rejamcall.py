"""Facing a re-jam over OUR open: call/fold by our 3-card strength; forward bb and ICM call-minus-fold.\nusage: python -I rejamcall.py HANDS OUT.json freq_entry_ids_csv"""

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



FREQ = set()


def init2(two, freq):
    global TWO, FREQ
    TWO = two; FREQ = set(freq)


def proc(args):
    tl, yl = args
    t = json.loads(tl); y = json.loads(yl).get("you")
    if "hands" not in t or not y: return []
    me = y["seat"]; seats = t["seats"]; N = len(seats); out = []
    for hi, h in enumerate(t["hands"]):
        sb_, sa = h["stacks_before"], h["stacks_after"]; bb = h["blinds"][1]
        if sb_[me] <= 0: continue
        alive = sum(1 for s in sb_ if s > 0)
        tot = collections.Counter(); raises = 0; opened = False; jam = None
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board": break
            if k == "blind": tot[s] += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if jam is not None and s == me and k in ("fold", "call", "raise"):
                j = jam
                cf = [sb_[i] - tot.get(i, 0) for i in range(N)]
                cf[j] = sb_[j] + sum(v for i, v in tot.items() if i != j)
                d = (h["equity_after"][me] - icm(cf)[me]) if k != "fold" else 0.0
                fwd = (sa[me] - sb_[me] + tot[me]) / bb
                c3 = y["cards"][hi] if hi < len(y["cards"]) else None
                out.append((seats[j] in FREQ, strength3(c3) if c3 else None, k, fwd, d, alive, sb_[j] >= sb_[me], min(sb_[me], sb_[j]) / bb))
                break
            if opened and raises == 1 and s != me and k == "raise" and e["amount"] >= sb_[s]:
                jam = s
            elif opened and raises >= 1 and s != me and k == "raise":
                break  # someone else 3-bet without jamming: not our spot
            if s == me and raises == 0 and k == "raise" and e["amount"] < sb_[me]: opened = True
            if k == "call": tot[s] += e["amount"]
            if k == "raise": tot[s] = e["amount"]; raises += 1
    return out


def main():
    two = build_two(); init2(two, [])
    deck = [r + s for r in R for s in "shdc"]
    allh = sorted(strength3(c) for c in itertools.combinations(deck, 3))
    cut = lambda q: allh[int(q * len(allh))]
    thr = {"top10": cut(0.90), "10-25": cut(0.75), "25-45": cut(0.55)}
    freq = [x for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else []
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    pairs = [(lines[i], lines[i + 1]) for i in range(0, len(lines) - 1) if lines[i].startswith('{"variant"')]
    with Pool(8, initializer=init2, initargs=(two, freq)) as p:
        res = [x for r in p.map(proc, pairs, chunksize=32) for x in r]
    json.dump({"thr": thr, "rows": res}, open(sys.argv[2], "w"))
    print(len(res), "spots where we opened and faced a re-jam")


if __name__ == "__main__":
    main()
