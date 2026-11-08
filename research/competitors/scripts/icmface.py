"""Our heads-up all-in calls with <=5 alive: actual ICM points after the hand minus ICM points had we folded
(jammer takes everything committed so far). equity_after was verified = Malmuth-Harville ICM (max diff 1e-4).
usage: python -I icmcall.py HANDS.jsonl.gz OUT.json"""
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


def proc(args):
    tl, yl = args
    t = json.loads(tl); y = json.loads(yl).get("you")
    if "hands" not in t or not y: return []
    me = y["seat"]; N = len(t["seats"]); out = []
    global FOLDS
    FOLDS = []
    for hi, h in enumerate(t["hands"]):
        sb_ = h["stacks_before"]
        if sb_[me] <= 0: continue
        alive = sum(1 for s in sb_ if s > 0)
        if alive > 5: continue
        tot = collections.Counter(); con = collections.Counter(); street = 0; folded = set(); last_raiser = None
        dec = None
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board": street += 1; con = collections.Counter(); continue
            if k == "blind": tot[s] += e["amount"]; con[s] += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if s == me and dec is None and k == "fold" and last_raiser is not None and last_raiser != me and tot[last_raiser] >= sb_[last_raiser]:
                FOLDS.append((alive, street, strength3(y["cards"][hi]) if hi < len(y["cards"]) and y["cards"][hi] else None, sb_[last_raiser] >= sb_[me]))
                break
            if s == me and dec is None and k in ("call", "raise") and last_raiser is not None and last_raiser != me:
                j = last_raiser
                jam_allin = tot[j] >= sb_[j]
                after = tot[me] + (e["amount"] if k == "call" else e["amount"] - con[me])
                me_allin = after >= sb_[me]
                if (jam_allin or me_allin) and (k == "call" or me_allin):
                    dec = (j, dict(tot), street, k if (k == 'call' or jam_allin) else 'rejam')
            if k == "call": tot[s] += e["amount"]; con[s] += e["amount"]
            if k == "raise":
                d = e["amount"] - con[s]; tot[s] += d; con[s] = e["amount"]; last_raiser = s
            if k == "fold": folded.add(s)
        if dec is None: continue
        j, tot0, st, kind = dec
        live_end = [i for i in range(N) if sb_[i] > 0 and i not in folded]
        if sorted(live_end) != sorted([me, j]): continue  # heads-up pots only
        cf = [sb_[i] - tot0.get(i, 0) for i in range(N)]
        cf[j] = sb_[j] + sum(v for i, v in tot0.items() if i != j)
        fold_pts = icm(cf)[me]
        stk = [sb_[i] - tot0.get(i, 0) for i in range(N)]; pot = sum(tot0.values())
        to_call = max(0, tot0.get(j, 0) - tot0.get(me, 0)); ce = min(to_call, stk[me]); excess = to_call - ce
        w_ = list(stk); w_[me] = stk[me] + pot - excess; w_[j] = stk[j] + excess
        l_ = list(stk); l_[me] = stk[me] - ce; l_[j] = stk[j] + pot + ce
        uf, uw, ul = fold_pts, icm(w_)[me], icm(l_)[me]
        thr = (uf - ul) / (uw - ul) if uw - ul > 1e-9 else None
        odds = ce / max(1, pot - excess + ce)
        d = h["equity_after"][me] - fold_pts
        c3 = y["cards"][hi] if hi < len(y["cards"]) else None
        strg = strength3(c3) if c3 else None
        covered = sb_[j] - 0 >= sb_[me]  # jammer covers us -> calling risks our bust
        out.append(("CALL",) + (alive, st, strg, covered, round(min(sb_[me], sb_[j]) / h["blinds"][1], 1), d, kind, thr, odds))
    return out + [("FOLD",) + f for f in FOLDS]


FOLDS = []


def main():
    two = build_two()
    deck = [r + s for r in R for s in "shdc"]
    TWO_ = two
    init(two)
    allh = sorted(strength3(c) for c in itertools.combinations(deck, 3))
    cut = lambda q: allh[int(q * len(allh))]
    thr = {"top10": cut(0.90), "10-25": cut(0.75), "25-45": cut(0.55)}
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    pairs = [(lines[i], lines[i + 1]) for i in range(0, len(lines) - 1) if lines[i].startswith('{"variant"')]
    with Pool(8, initializer=init, initargs=(two,)) as p:
        res = [x for r in p.map(proc, pairs, chunksize=32) for x in r]
    json.dump({"thr": thr, "rows": res, "pct": [allh[int(q*len(allh))] for q in (0.75,0.5,0.25)]}, open(sys.argv[2], "w"))
    print(len(pairs), "tables", len(res), "HU all-in calls with <=5 alive; thresholds", thr)


if __name__ == "__main__":
    main()
