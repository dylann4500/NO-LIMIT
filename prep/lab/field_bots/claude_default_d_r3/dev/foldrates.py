"""How often does this field fold to our postflop bets, by street and by whether we were the preflop aggressor?"""
import json, gzip, collections, sys
P = sys.argv[1] if len(sys.argv) > 1 else "lab/field_bots/claude_default_d/round1/hand_history.jsonl.gz"
res = collections.defaultdict(lambda: [0, 0])   # key -> [bets, all folded]
field = collections.defaultdict(lambda: [0, 0])  # opponent fold-to-bet when facing any bet (not ours)
lead = collections.defaultdict(lambda: [0, 0, 0.0])
for l in gzip.open(P, "rt"):
    h = json.loads(l)
    me = h["seat"]; bb = h["blinds"][1]
    street = 0; pf_aggr = None; curbet = 0
    pending = None  # our bet awaiting responses: [street, responders folded?, any call]
    ev = h["events"]
    for i, (k, s, a, c) in enumerate(ev):
        if k == "board":
            if pending: res[pending[0]][0] += 1; res[pending[0]][1] += 0 if pending[2] else 1; pending = None
            street += 1; curbet = 0; continue
        if k == "raise" and street == 0: pf_aggr = s
        if street == 0 or k not in ("fold", "call", "raise", "check"): 
            if k == "win" and pending:
                res[pending[0]][0] += 1; res[pending[0]][1] += 0 if pending[2] else 1; pending = None
            continue
        if s == me and k == "raise":
            if pending: res[pending[0]][0] += 1; res[pending[0]][1] += 0 if pending[2] else 1
            key = (street, "aggr" if pf_aggr == me else ("lead_vs_pfr" if pf_aggr is not None else "nopfr"), "bet" if curbet == 0 else "raise")
            pending = [key, 0, False]
            curbet = a; continue
        if s != me and pending and k in ("call", "raise"):
            pending[2] = True
        if s != me and k in ("fold", "call", "raise") and curbet > 0:
            field[street][0] += 1; field[street][1] += (k == "fold")
        if k == "raise": curbet = a
for k in sorted(res):
    n, f = res[k]
    print("our %-40s n=%5d  everyone folded %.2f" % (k, n, f / max(1, n)))
print("field fold-to-bet by street (all responses to bets):", {k: round(v[1] / max(1, v[0]), 2) for k, v in sorted(field.items())})
