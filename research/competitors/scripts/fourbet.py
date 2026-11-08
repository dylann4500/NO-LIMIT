"""4-bet check (our non-jam 3-bet facing a 4-bet; value of a 5-bet jam that is always called, ignoring fold equity) -- adapted from E4 check: estimated ICM value of CALLING re-jams over our open, incl. spots we folded.\nJammer range = its shown kept 2 cards at showdowns of its re-jams (unbiased: all-ins always show).\nusage: python -I e4check.py HANDS OUT.json"""

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
    """phase 1: our non-jam 3-bets facing the opener's 4-bet + shown 4-bet hands (anyone's)."""
    tl, yl = args
    t = json.loads(tl); y = json.loads(yl).get("you")
    if "hands" not in t or not y: return [], []
    me = y["seat"]; seats = t["seats"]; N = len(seats); spots = []; shown = []
    for hi, h in enumerate(t["hands"]):
        sb_ = h["stacks_before"]; bb = h["blinds"][1]
        if sb_[me] <= 0: continue
        shows = {e["seat"]: e["cards"] for e in h["events"] if e["kind"] == "show"}
        tot = collections.Counter(); raises = 0; opener = None; tbet = None; fourb = None; done = False
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board": break
            if k == "blind": tot[s] += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if raises == 1 and opener is not None and s != opener and k == "raise" and e["amount"] < sb_[s] and tbet is None:
                tbet = s
            elif raises == 2 and tbet is not None and s == opener and k == "raise" and fourb is None:
                fourb = s
                if s in shows and len(shows[s]) == 2: shown.append((seats[s], shows[s]))
            elif fourb is not None and tbet == me and s == me and not done and k in ("fold", "call", "raise"):
                c3 = y["cards"][hi] if hi < len(y["cards"]) else None
                if c3:
                    spots.append({"team": seats[fourb], "c3": c3, "sb": list(sb_), "tot": dict(tot), "me": me, "j": fourb, "k": k,
                                  "eff": min(sb_[me], sb_[fourb]) / bb, "s3": strength3(c3)})
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
    sb_ = sp["sb"]; N = len(sb_); me, j = sp["me"], sp["j"]; tot = {int(a): b for a, b in sp["tot"].items()}
    E = min(sb_[me], sb_[j]); dead = sum(v for i, v in tot.items() if i not in (me, j))
    base = [sb_[i] - tot.get(i, 0) for i in range(N)]
    f = list(base); f[j] = sb_[j] + sum(v for i, v in tot.items() if i != j)
    w_ = list(base); w_[me] = sb_[me] + E + dead; w_[j] = sb_[j] - E
    l_ = list(base); l_[me] = sb_[me] - E; l_[j] = sb_[j] + E + dead
    uf, uw, ul = icm(f)[me], icm(w_)[me], icm(l_)[me]
    p = equity(sp["c3"], sp["team"])
    return p * uw + (1 - p) * ul - uf, p


def main():
    two = build_two(); init2(two, [])
    deck = [r + s for r in R for s in "shdc"]
    allh = sorted(strength3(c) for c in itertools.combinations(deck, 3))
    T5 = allh[int(0.95 * len(allh))]
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
    spots = [s for s in spots]
    with Pool(8, initializer=init3, initargs=(ranges,)) as p:
        evs = p.map(ev_spot, spots, chunksize=16)
    b = lambda x: "top5" if x >= T5 else ("top10" if x >= thr["top10"] else ("10-25" if x >= thr["10-25"] else "25+"))
    rows = [(False, b(s["s3"]), s["k"], 0.0, ev, eq, s["eff"]) for s, (ev, eq) in zip(spots, evs)]
    json.dump({"rows": rows, "nrange": {nm.get(k, k): len(v) for k, v in ranges.items()}}, open(sys.argv[2], "w"))
    print(len(spots), "spots;", len(shown), "shown re-jam hands; teams with own range:", len(ranges) - 1)


if __name__ == "__main__":
    main()
