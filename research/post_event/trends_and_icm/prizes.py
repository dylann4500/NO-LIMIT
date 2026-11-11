"""What do prize_* events mark? usage: python -I prizes.py HANDS.gz NTABLES"""
import gzip, json, sys, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval7
f = gzip.open(sys.argv[1], "rt"); f.readline(); N = int(sys.argv[2]); c = collections.Counter(); nt = 0
for line in f:
    if line.startswith('{"you"'): continue
    t = json.loads(line); nt += 1
    for h in t["hands"]:
        ev = h["events"]; kinds = [e["kind"] for e in ev]
        streets = kinds.count("board"); sd = "show" in kinds
        bl = [e for e in ev if e["kind"] == "prize_the_empty_bluffer"]
        if streets >= 1 and not sd:
            # did the winner bet/raise on the last street played? 
            last_aggr = None; st = 0
            for e in ev:
                if e["kind"] == "board": st += 1
                if e["kind"] == "raise" and st >= 1: last_aggr = e["seat"]
            c[("postflop_no_showdown", "bluffer" if bl else "none", "winner_bet_postflop" if last_aggr is not None else "no_postflop_bet")] += 1
        elif streets == 0 and not sd:
            c[("preflop_end", "bluffer" if bl else "none")] += 1
        elif sd:
            c[("showdown", "bluffer" if bl else "none")] += 1
    if nt >= N: break
for k, v in sorted(c.items()): print(k, v)
