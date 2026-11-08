"""Facing a single non-jam open (no cold callers): fold/call/3bet(non-jam)/jam per team, by players alive, opener position, IP/OOP.\nForward bb and whole-hand points. Also opener response to 3-bets, 3-bettor response to 4-bets, shown 3-bet hands, our top-15% spots.\nusage: python -I threebet.py HANDS OUT.json"""

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



YOU = None


def init2(two, you):
    global TWO, YOU
    TWO = two; YOU = you


def nb(n): return "8-6" if n >= 6 else ("5-4" if n >= 4 else "3-2")


def proc(args):
    tl, yl = args
    t = json.loads(tl); y = json.loads(yl).get("you")
    if "hands" not in t or not y: return {}, []
    seats = t["seats"]; N = len(seats); me = y["seat"]
    out = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0])  # n, sum fwd bb, sumsq, sum dpts
    shown = []
    for hi, h in enumerate(t["hands"]):
        sb_, sa = h["stacks_before"], h["stacks_after"]; bb = h["blinds"][1]
        live = [i for i in range(N) if sb_[i] > 0]; n = len(live); btn = h["button"]
        bl = [e["seat"] for e in h["events"] if e["kind"] == "blind"]
        sbs = bl[0] if bl else None; bbs = bl[1] if len(bl) > 1 else None
        order = sorted(live, key=lambda i: (i - btn - 1) % N)   # postflop order: SB first ... BTN last
        co = order[-2] if n >= 4 else None
        def pos(i):
            if i == sbs: return "SB"
            if i == bbs: return "BB"
            if i == btn: return "BTN"
            if i == co: return "CO"
            return "EP"
        shows = {e["seat"]: e["cards"] for e in h["events"] if e["kind"] == "show"}
        tot = collections.Counter(); raises = 0; opener = None; callers = 0; tb = None; spot = None
        evs = h["events"]
        for idx, e in enumerate(evs):
            k, s = e["kind"], e.get("seat")
            if k == "board": break
            if k == "blind": tot[s] += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if raises == 1 and opener is not None and s != opener and callers == 0 and spot is None:
                act = "fold" if k == "fold" else ("call" if k == "call" else ("jam" if e["amount"] >= sb_[s] else "3bet"))
                ip = order.index(s) > order.index(opener)
                fwd = (sa[s] - sb_[s] + tot[s]) / bb
                dp = h["equity_after"][s] - h["equity_before"][s]
                key = [seats[s], nb(n), pos(opener), "IP" if ip else "OOP"]
                for kk in (tuple(key + [act]), tuple(key[:2] + ["*", "*", act]), tuple(key[:1] + ["*", "*", "*", act])):
                    o = out[kk]; o[0] += 1; o[1] += fwd; o[2] += fwd * fwd; o[3] += dp
                if s == me and hi < len(y["cards"]) and y["cards"][hi]:
                    q = strength3(y["cards"][hi])
                    qb = "top5" if q >= TOP15[0] else ("5-10" if q >= TOP15[1] else ("10-15" if q >= TOP15[2] else ("15-25" if q >= TOP15[3] else "rest")))
                    for kk in (("US", qb, nb(n), "IP" if ip else "OOP", act), ("US", qb, "*", "*", act)):
                        o = out[kk]; o[0] += 1; o[1] += fwd; o[2] += fwd * fwd; o[3] += dp
                if act == "3bet":
                    spot = (s, idx)
                    if s in shows and len(shows[s]) == 2: shown.append((seats[s], shows[s]))
                else:
                    spot = ("done",)
                if act != "3bet": pass
            elif spot and spot[0] != "done" and s == opener and raises == 2:
                # opener's response to the 3-bet
                ra = "fold" if k == "fold" else ("call" if k == "call" else "4bet")
                o = out[(seats[spot[0]], "*", "*", "*", "opener_" + ra)]; o[0] += 1
            elif spot and spot[0] != "done" and s == spot[0] and raises == 3:
                ra = "fold" if k == "fold" else ("call" if k == "call" else "5bet")
                fwd = (sa[s] - sb_[s] + tot[s]) / bb
                o = out[(seats[s], "*", "*", "*", "vs4bet_" + ra)]; o[0] += 1; o[1] += fwd
                spot = ("done",)
            if raises == 0 and k == "raise" and e["amount"] < sb_[s]: opener = s
            if raises >= 1 and k == "call" and s != opener and spot is None: callers += 1
            if k == "call": tot[s] += e["amount"]
            if k == "raise": tot[s] = e["amount"]; raises += 1
    return {"|".join(k): v for k, v in out.items()}, shown


TOP15 = None


def main():
    global TOP15
    two = build_two()
    init2(two, None)
    deck = [r + s for r in R for s in "shdc"]
    allh = sorted(strength3(c) for c in itertools.combinations(deck, 3))
    TOP15 = [allh[int(q * len(allh))] for q in (0.95, 0.90, 0.85, 0.75)]
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    pairs = [(lines[i], lines[i + 1]) for i in range(0, len(lines) - 1) if lines[i].startswith('{"variant"')]
    with Pool(8, initializer=init3, initargs=(two, TOP15)) as p:
        res = p.map(proc, pairs, chunksize=32)
    tot = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0]); shown = []
    for a, b in res:
        for k, v in a.items():
            o = tot[k]
            for i in range(4): o[i] += v[i]
        shown += b
    json.dump({"name": {e["entry_id"]: e["team_name"] for e in head["entries"]}, "you": head["you"], "ntab": len(pairs),
               "cells": tot, "shown": shown}, open(sys.argv[2], "w"))
    print(len(pairs), "tables", len(shown), "shown 3-bet hands")


def init3(two, top15):
    global TWO, TOP15
    TWO = two; TOP15 = top15


if __name__ == "__main__":
    main()
