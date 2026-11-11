"""Chip result (BB) of our postflop lines, split by made-hand class at the time of the bet."""
import json, gzip, collections, sys
import eval7
P = sys.argv[1] if len(sys.argv) > 1 else "lab/field_bots/claude_default_d/round1/hand_history.jsonl.gz"
C = {r + s: eval7.Card(r + s) for r in "23456789TJQKA" for s in "shdc"}
out = collections.defaultdict(lambda: [0, 0.0])
for l in gzip.open(P, "rt"):
    h = json.loads(l)
    me = h["seat"]; bb = h["blinds"][1]
    if str(me) not in h["stacks"]: continue
    s0 = h["stacks"][str(me)]; s1 = None
    board = []; street = 0; pf_aggr = None; first = {}; curbet = 0
    for k, s, a, c in h["events"]:
        if k == "board": board += c; street += 1; curbet = 0; continue
        if k == "stack" and s == me: s1 = a
        if k == "raise" and street == 0: pf_aggr = s
        if street >= 1 and s == me and k in ("raise", "check", "call", "fold") and street not in first:
            ht = eval7.handtype(eval7.evaluate([C[x] for x in h["hole"] + board]))
            first[street] = (k if not (k == "raise" and curbet > 0) else "raise_vs_bet", ht, pf_aggr == me)
        if k == "raise": curbet = a
    if s1 is None or 1 not in first: continue
    d = (s1 - s0) / bb
    k, ht, aggr = first[1]
    hc = ht if ht in ("High Card", "Pair") else "Two Pair+"
    out[("flop", k, "aggr" if aggr else "notaggr", hc)][0] += 1
    out[("flop", k, "aggr" if aggr else "notaggr", hc)][1] += d
for key in sorted(out, key=lambda x: out[x][1]):
    n, v = out[key]
    print("%-55s n=%5d total %8.0f  per %6.2f" % (key, n, v, v / n))
