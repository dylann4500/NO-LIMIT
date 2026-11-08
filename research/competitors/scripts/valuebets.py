"""Our first-in turn/river decisions (no bet yet on the street): bet (by size) vs check, forward bb,
split by our hand class x street x HU/MW x opponents' visible-card class. Also called-bet diagnostics per caller team.
usage: python -I valuebets.py HANDS.jsonl.gz OUT.json"""
import collections, gzip, json, sys
from multiprocessing import Pool
import eval7

R = "23456789TJQKA"
STRONG = {"Two Pair", "Trips", "Straight", "Flush", "Full House", "Quads", "Straight Flush"}


def rk(c): return R.index(c[0])


def connect(card, board):
    if card is None: return "na"
    r = rk(card); br = [rk(b) for b in board]
    if r in br: return "pair"
    if sum(1 for b in board if b[1] == card[1]) >= 2: return "conn"
    rs = set(br)
    for lo in range(-1, 9):
        win = set(range(lo, lo + 5))
        rr = r if not (lo == -1 and r == 12) else -1
        bb_ = {x if not (lo == -1 and x == 12) else -1 for x in rs}
        if rr in win and len(bb_ & win) >= 2: return "conn"
    return "miss"


def hand_class(kept, board):
    k = [rk(c) for c in kept]; B = [rk(c) for c in board]
    full = eval7.evaluate([eval7.Card(c) for c in kept + board])
    ht = eval7.handtype(full)
    if ht in STRONG:
        bo = eval7.evaluate([eval7.Card(c) for c in board]) if len(board) == 5 else None
        uses = k[0] == k[1] or k[0] in B or k[1] in B
        if (bo is None or full > bo) and (ht != "Two Pair" or (k[0] in B and k[1] in B) or (k[0] == k[1] and k[0] in B) or (uses and len(set(B)) < len(B))):
            return "2pair+"
    top = max(B)
    if k[0] == k[1]:
        return "overpair" if k[0] > top else "midpair"
    if top in k:
        kick = k[1] if k[0] == top else k[0]
        return "TP_good" if kick >= R.index("J") else "TP_weak"
    if k[0] in B or k[1] in B: return "midpair"
    return "nopair"


YOU = None


def init(y):
    global YOU
    YOU = y


def proc(args):
    tl, yl = args
    t = json.loads(tl); y = json.loads(yl).get("you")
    if "hands" not in t or not y: return {}, {}
    me = y["seat"]; seats = t["seats"]; N = len(seats)
    kept = {p["hand"]: p["cards"] for p in y.get("private_events", []) if p["kind"] == "kept"}
    out = collections.defaultdict(lambda: [0, 0.0, 0.0, 0, 0.0])  # n, sum, sumsq, n_called, sum_called
    callers = collections.defaultdict(lambda: [0, 0.0, 0])  # (team, street) -> n called, sum fwd, n we won showdown
    for h in t["hands"]:
        sb_, sa = h["stacks_before"], h["stacks_after"]; bb = h["blinds"][1]
        if sb_[me] <= 0: continue
        kp = kept.get(h["hand"])
        if not kp: continue
        live = [i for i in range(N) if sb_[i] > 0]
        street = 0; board = []; vis = {}; folded = set(); tot = collections.Counter(); con = collections.Counter()
        pot = 0; street_pot = 0; bet_on = False; pending = None
        evs = h["events"]
        for idx, e in enumerate(evs):
            k, s = e["kind"], e.get("seat")
            if k == "board":
                board = board + e["cards"]; street += 1; bet_on = False; con = collections.Counter(); street_pot = pot; continue
            if k == "reveal": vis[s] = e["cards"][0]; continue
            if k == "blind": tot[s] += e["amount"]; con[s] += e["amount"]; pot += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if s == me and street >= 2 and not bet_on and sb_[me] - tot[me] > 0:
                active = [i for i in live if i not in folded]
                opps = [i for i in active if i != me]
                cl = [connect(vis.get(o), board) for o in opps]
                vc = "pair" if "pair" in cl else ("conn" if "conn" in cl else "miss")
                hm = "HU" if len(opps) == 1 else "MW"
                hc = hand_class(kp, board)
                fwd = (sa[me] - sb_[me] + tot[me]) / bb
                if k == "raise":
                    frac = (e["amount"] - con[me]) / max(1, street_pot)
                    sz = "<=0.5" if frac <= 0.5 else ("0.5-0.8" if frac <= 0.8 else ">0.8")
                    act = "bet" + sz
                    # was it called? next actions on this street by others
                    called = False; caller = None
                    for x in evs[idx + 1:]:
                        if x["kind"] == "board": break
                        if x.get("seat") != me and x["kind"] in ("call", "raise"):
                            called = True; caller = x["seat"]; break
                else:
                    act = "check"; called = False; caller = None
                for a in (act, "bet" if act != "check" else "check"):
                    o = out[(street, hm, hc, vc, a)]; o[0] += 1; o[1] += fwd; o[2] += fwd * fwd
                    if called: o[3] += 1; o[4] += fwd
                if called and hm == "HU":
                    shows = any(x["kind"] == "show" for x in evs)
                    c = callers[(seats[caller], street, hc)]; c[0] += 1; c[1] += fwd; c[2] += 1 if (shows and sa[me] > sb_[me]) else 0
            if k == "call": tot[s] += e["amount"]; con[s] += e["amount"]; pot += e["amount"]
            if k == "raise":
                d = e["amount"] - con[s]; tot[s] += d; con[s] = e["amount"]; pot += d
                if street > 0: bet_on = True
            if k == "fold": folded.add(s)
    return {"|".join(map(str, k)): v for k, v in out.items()}, {"|".join(map(str, k)): v for k, v in callers.items()}


def main():
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    pairs = [(lines[i], lines[i + 1]) for i in range(0, len(lines) - 1) if lines[i].startswith('{"variant"')]
    with Pool(8, initializer=init, initargs=(head["you"],)) as p:
        res = p.map(proc, pairs, chunksize=32)
    tot = collections.defaultdict(lambda: [0, 0.0, 0.0, 0, 0.0]); cal = collections.defaultdict(lambda: [0, 0.0, 0])
    for a, b in res:
        for k, v in a.items():
            o = tot[k]
            for i in range(5): o[i] += v[i]
        for k, v in b.items():
            o = cal[k]
            for i in range(3): o[i] += v[i]
    json.dump({"ntab": len(pairs), "cells": tot, "callers": cal,
               "name": {e["entry_id"]: e["team_name"] for e in head["entries"]}}, open(sys.argv[2], "w"))
    print(len(pairs), "tables")


if __name__ == "__main__":
    main()
