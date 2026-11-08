"""Decompose OUR showdown results: by when the money went in (preflop all-in / postflop all-in / no all-in),
by who bet last (we were the last aggressor or the caller), by heads-up showdown opponent team.
usage: python -I sdsplit.py HANDS.jsonl.gz OUT.json"""
import collections, gzip, json, sys
from multiprocessing import Pool

YOU = None


def init(y):
    global YOU
    YOU = y


def proc(line):
    t = json.loads(line)
    if "hands" not in t or YOU not in t.get("seats", []): return None
    seats = t["seats"]; me = seats.index(YOU); N = len(seats)
    cat = collections.defaultdict(lambda: [0, 0.0]); opp = collections.defaultdict(lambda: [0, 0.0])
    for h in t["hands"]:
        sb_, sa = h["stacks_before"], h["stacks_after"]; bb = h["blinds"][1]
        if sb_[me] <= 0: continue
        if not any(e["kind"] == "show" for e in h["events"]): continue
        folded = set(); tot = collections.Counter(); con = collections.Counter(); street = 0
        allin_street = None; last_aggr = None
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board": street += 1; con = collections.Counter(); continue
            if k == "blind": tot[s] += e["amount"]; con[s] += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if k == "fold": folded.add(s)
            if k == "call": tot[s] += e["amount"]; con[s] += e["amount"]
            if k == "raise":
                d = e["amount"] - con[s]; tot[s] += d; con[s] = e["amount"]; last_aggr = (s, street)
            if allin_street is None and k in ("call", "raise") and tot[s] >= sb_[s]: allin_street = street
        if me in folded: continue
        live = [i for i in range(N) if sb_[i] > 0 and i not in folded]
        d = (sa[me] - sb_[me]) / bb
        when = "allin_pre" if allin_street == 0 else ("allin_post" if allin_street is not None else "no_allin")
        role = "we_last_aggr" if last_aggr and last_aggr[0] == me else ("opp_last_aggr" if last_aggr else "no_aggr")
        hu = "HU" if len(live) == 2 else "MW"
        for key in (when, f"{when}|{role}", f"{when}|{hu}"):
            c = cat[key]; c[0] += 1; c[1] += d
        if hu == "HU":
            o = [i for i in live if i != me][0]; c = opp[seats[o]]; c[0] += 1; c[1] += d
    return dict(cat), dict(opp)


def main():
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    with Pool(8, initializer=init, initargs=(head["you"],)) as p:
        res = [r for r in p.map(proc, lines, chunksize=32) if r]
    cat = collections.defaultdict(lambda: [0, 0.0]); opp = collections.defaultdict(lambda: [0, 0.0])
    for C, O in res:
        for k, v in C.items(): cat[k][0] += v[0]; cat[k][1] += v[1]
        for k, v in O.items(): opp[k][0] += v[0]; opp[k][1] += v[1]
    json.dump({"ntab": len(res), "cat": cat, "opp": opp, "name": {e["entry_id"]: e["team_name"] for e in head["entries"]}},
              open(sys.argv[2], "w"))
    print(len(res), "tables")


if __name__ == "__main__":
    main()
