"""Our late-position (CO/BTN/SB) first-in decisions by our 3-card strength: open rate, forward bb of opens.\nusage: python -I lateopen.py HANDS OUT.json"""

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




def init2(two):
    global TWO
    TWO = two


def proc(args):
    tl, yl = args
    t = json.loads(tl); y = json.loads(yl).get("you")
    if "hands" not in t or not y: return []
    me = y["seat"]; N = len(t["seats"]); out = []
    for hi, h in enumerate(t["hands"]):
        sb_, sa = h["stacks_before"], h["stacks_after"]; bb = h["blinds"][1]
        if sb_[me] <= 0: continue
        live = [i for i in range(N) if sb_[i] > 0]; n = len(live); btn = h["button"]
        bl = [e["seat"] for e in h["events"] if e["kind"] == "blind"]
        sbs = bl[0] if bl else None
        order = sorted(live, key=lambda i: (i - btn - 1) % N); co = order[-2] if n >= 4 else None
        late = (me in (co, btn, sbs)) if n >= 3 else False
        if not late: continue
        tot = collections.Counter(); raises = 0
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board": break
            if k == "blind": tot[s] += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if raises > 0: break
            if s == me:
                if k == "check": break
                c3 = y["cards"][hi] if hi < len(y["cards"]) else None
                if not c3: break
                act = "fold" if k == "fold" else ("limp" if k == "call" else ("jam" if e["amount"] >= sb_[me] else "raise"))
                fwd = (sa[me] - sb_[me] + tot[me]) / bb
                dp = h["equity_after"][me] - h["equity_before"][me]
                out.append((n, strength3(c3), act, fwd, dp, sb_[me] / bb))
                break
            if k == "call": tot[s] += e["amount"]
            if k == "raise": tot[s] = e["amount"]; raises += 1
    return out


def main():
    two = build_two(); init2(two)
    deck = [r + s for r in R for s in "shdc"]
    allh = sorted(strength3(c) for c in itertools.combinations(deck, 3))
    qs = [0.9, 0.75, 0.55, 0.40, 0.25]
    thr = [allh[int(q * len(allh))] for q in qs]
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    pairs = [(lines[i], lines[i + 1]) for i in range(0, len(lines) - 1) if lines[i].startswith('{"variant"')]
    with Pool(8, initializer=init2, initargs=(two,)) as p:
        res = [x for r in p.map(proc, pairs, chunksize=32) for x in r]
    json.dump({"thr": thr, "qs": qs, "rows": res}, open(sys.argv[2], "w"))
    print(len(res), "late-position first-in spots")


if __name__ == "__main__":
    main()
