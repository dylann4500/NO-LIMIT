"""Exposure choice split by whether a kept card pairs the flop (showdown hands; avalon also all hands).

usage: python -I expo.py HANDS.jsonl.gz
"""
import collections
import gzip
import json
import sys

RANKS = {r: i for i, r in enumerate("23456789TJQKA", start=2)}
WANT = {"2 Curry", "thepastaway", "Lemonade", "Team 82", "avalon", "Team 123"}


def rk(c):
    return RANKS[c[0]]


def main(path):
    C = collections.defaultdict(collections.Counter)
    with gzip.open(path, "rt") as fh:
        head = json.loads(fh.readline())
        names = {e["entry_id"]: e["team_name"] for e in head["entries"]}
        you = head["you"]
        t = None
        for line in fh:
            o = json.loads(line)
            if "hands" in o:
                t = o
                continue
            own = o["you"]
            kept_priv = {pe["hand"]: pe["cards"] for pe in own.get("private_events") or [] if pe.get("kind") == "kept"}
            seats, fill = t["seats"], t["fillers"]
            for h in t["hands"]:
                flop, exp, shown = None, {}, {}
                for e in h["events"]:
                    k = e["kind"]
                    if k == "board" and flop is None:
                        flop = e["cards"]
                    elif k == "reveal":
                        exp[e["seat"]] = e["cards"][0]
                    elif k == "show":
                        shown[e["seat"]] = e["cards"]
                if not flop:
                    continue
                fr = {rk(x) for x in flop}
                fs = collections.Counter(x[1] for x in flop)
                for s, ex in exp.items():
                    if fill[s]:
                        continue
                    nm = names.get(seats[s], "?")
                    srcs = []
                    if s in shown and len(shown[s]) == 2:
                        srcs.append(("sd", shown[s]))
                    if seats[s] == you and h["hand"] in kept_priv:
                        srcs.append(("all", kept_priv[h["hand"]]))
                    for tag, kept in srcs:
                        oth = [x for x in kept if x != ex]
                        if len(oth) != 1:
                            continue
                        ot = oth[0]
                        key = nm if nm in WANT else "FIELD"
                        c = C[(key, tag)]
                        pe, po = rk(ex) in fr, rk(ot) in fr
                        if not pe and not po and rk(ex) != rk(ot):
                            c["np_n"] += 1
                            c["np_low"] += rk(ex) < rk(ot)
                        if pe != po:
                            c["one_n"] += 1
                            c["one_pairing"] += pe
                        if rk(ex) == rk(ot):
                            c["pp"] += 1
                        # flush-suit card: exactly one kept card matches a suit with 2+ on flop
                        se, so = fs[ex[1]] >= 2, fs[ot[1]] >= 2
                        if se != so:
                            c["fl_n"] += 1
                            c["fl_suit"] += se
    print(path.split("/")[-1])
    print(f"{'team':<14}{'src':>4}{'expLow|noPair':>14}{'n':>7}{'expPairing|1pairs':>18}{'n':>7}{'expFlushSuit|1':>15}{'n':>7}")
    for (k, tag), c in sorted(C.items()):
        print(f"{k:<14}{tag:>4}{100 * c['np_low'] / max(1, c['np_n']):>14.1f}{c['np_n']:>7}"
              f"{100 * c['one_pairing'] / max(1, c['one_n']):>18.1f}{c['one_n']:>7}"
              f"{100 * c['fl_suit'] / max(1, c['fl_n']):>15.1f}{c['fl_n']:>7}")


if __name__ == "__main__":
    main(sys.argv[1])
