"""E4 check: estimated ICM value of CALLING re-jams over our open, incl. spots we folded.\nJammer range = its shown kept 2 cards at showdowns of its re-jams (unbiased: all-ins always show).\nusage: python -I e4check.py HANDS OUT.json"""

import collections, functools, gzip, itertools, json, random, sys
from multiprocessing import Pool
import eval7, random

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
    """phase 1: our re-jam spots + shown hands of re-jammers (over anyone's open)."""
    tl, yl = args
    t = json.loads(tl); y = json.loads(yl).get("you")
    if "hands" not in t or not y: return [], []
    me = y["seat"]; seats = t["seats"]; N = len(seats); spots = []; shown = []
    for hi, h in enumerate(t["hands"]):
        sb_, sa = h["stacks_before"], h["stacks_after"]; bb = h["blinds"][1]
        if sb_[me] <= 0: continue
        shows = {e["seat"]: e["cards"] for e in h["events"] if e["kind"] == "show"}
        tot = collections.Counter(); raises = 0; opener = None; jam = None; done = False
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board": break
            if k == "blind": tot[s] += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if jam is None and raises == 1 and opener is not None and s != opener and k == "raise" and e["amount"] >= sb_[s]:
                jam = s
                if s in shows and len(shows[s]) == 2: shown.append((seats[s], shows[s]))
            if not done and jam is not None and opener == me and s == me and k in ("fold", "call"):
                stk = [sb_[i] - tot.get(i, 0) for i in range(N)]
                c3 = y["cards"][hi] if hi < len(y["cards"]) else None
                if c3:
                    d = (h["equity_after"][me] - icm([sb_[i] - tot.get(i, 0) if i != jam else sb_[jam] + sum(v for q, v in tot.items() if q != jam) for i in range(N)])[me]) if k == "call" else 0.0
                    spots.append({"team": seats[jam], "c3": c3, "stk": stk, "tot": dict(tot), "me": me, "j": jam, "k": k, "real": d,
                                  "eff": min(sb_[me], sb_[jam]) / bb, "s3": strength3(c3)})
                done = True
            if raises == 0 and k == "raise" and e["amount"] < sb_[s]: opener = s
            if k == "call": tot[s] += e["amount"]
            if k == "raise": tot[s] = e["amount"]; raises += 1
    return spots, shown


RANGES = {}


def init3(ranges):
    global RANGES
    RANGES = ranges


def equity(c3, team, n=300, seed=0):
    rng = random.Random(seed)
    rngs = RANGES.get(team) or RANGES["_pool"]
    deck = [r + s for r in R for s in "shdc"]
    mine = set(c3); w = 0.0; m = 0
    for _ in range(n):
        opp = rng.choice(rngs)
        if mine & set(opp): continue
        rest = [c for c in deck if c not in mine and c not in opp]
        b = rng.sample(rest, 5)
        flop = [eval7.Card(c) for c in b[:3]]
        best = max(itertools.combinations(c3, 2), key=lambda p: eval7.evaluate([eval7.Card(c) for c in p] + flop))
        h1 = eval7.evaluate([eval7.Card(c) for c in list(best) + b])
        h2 = eval7.evaluate([eval7.Card(c) for c in list(opp) + b])
        w += 1 if h1 > h2 else (0.5 if h1 == h2 else 0); m += 1
    return w / max(1, m)


def ev_spot(sp):
    N = len(sp["stk"]); stk = list(sp["stk"]); me, j = sp["me"], sp["j"]; tot = {int(a): b for a, b in sp["tot"].items()}
    pot = sum(tot.values()); to_call = max(0, tot.get(j, 0) - tot.get(me, 0)); ce = min(to_call, stk[me]); ex = to_call - ce
    f = list(stk); f[j] += pot
    w_ = list(stk); w_[me] = stk[me] + pot - ex; w_[j] = stk[j] + ex
    l_ = list(stk); l_[me] = stk[me] - ce; l_[j] = stk[j] + pot + ce
    uf, uw, ul = icm(f)[me], icm(w_)[me], icm(l_)[me]
    p = equity(sp["c3"], sp["team"])
    return p * uw + (1 - p) * ul - uf, p


def main():
    two = build_two(); init2(two, [])
    deck = [r + s for r in R for s in "shdc"]
    allh = sorted(strength3(c) for c in itertools.combinations(deck, 3))
    thr = {"top10": allh[int(0.9 * len(allh))], "10-25": allh[int(0.75 * len(allh))], "25-45": allh[int(0.55 * len(allh))]}
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    nm = {e["entry_id"]: e["team_name"] for e in head["entries"]}
    freq = {s for s, n in nm.items() if n in ("Lemonade", "AZ", "TeamBallHog", "sandylikesfrogs")}
    pairs = [(lines[i], lines[i + 1]) for i in range(0, len(lines) - 1) if lines[i].startswith('{"variant"')]
    with Pool(8, initializer=init2, initargs=(two, [])) as p:
        res = p.map(proc, pairs, chunksize=32)
    spots = [s for a, b in res for s in a]; shown = [x for a, b in res for x in b]
    ranges = collections.defaultdict(list)
    for team, cards in shown: ranges[team].append(cards); ranges["_pool"].append(cards)
    ranges = {k: v for k, v in ranges.items() if len(v) >= 40 or k == "_pool"}
    spots = [s for s in spots if s["s3"] >= thr["25-45"]]
    with Pool(8, initializer=init3, initargs=(ranges,)) as p:
        evs = p.map(ev_spot, spots, chunksize=16)
    b = lambda x: "top10" if x >= thr["top10"] else ("10-25" if x >= thr["10-25"] else "25-45")
    rows = [(s["team"] in freq, b(s["s3"]), s["k"], s["real"], ev, eq, s["eff"]) for s, (ev, eq) in zip(spots, evs)]
    json.dump({"rows": rows, "nrange": {nm.get(k, k): len(v) for k, v in ranges.items()}}, open(sys.argv[2], "w"))
    print(len(spots), "spots;", len(shown), "shown re-jam hands; teams with own range:", len(ranges) - 1)


if __name__ == "__main__":
    main()
