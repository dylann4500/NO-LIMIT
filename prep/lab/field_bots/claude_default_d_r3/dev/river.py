"""Results of hands by our action on the turn/river (what kind of decision lost chips)."""
import json, gzip, collections, sys
import eval7
P = sys.argv[1] if len(sys.argv) > 1 else "lab/field_bots/claude_default_d/round1/hand_history.jsonl.gz"
C = {r + s: eval7.Card(r + s) for r in "23456789TJQKA" for s in "shdc"}
out = collections.defaultdict(lambda: [0, 0.0])
lvl0 = collections.defaultdict(lambda: [0, 0.0])
for l in gzip.open(P, "rt"):
    h = json.loads(l)
    me = h["seat"]; bb = h["blinds"][1]
    if str(me) not in h["stacks"]: continue
    s0 = h["stacks"][str(me)]; s1 = None
    board = []; street = 0; acts = collections.defaultdict(list); curbet = 0; facing_size = {}
    pot = 0
    for k, s, a, c in h["events"]:
        if k == "board": board += c; street += 1; curbet = 0; continue
        if k == "stack" and s == me: s1 = a
        if k in ("blind", "ante", "call"): pot += a or 0
        if s == me and k in ("raise", "check", "call", "fold"):
            kk = k
            if k == "raise": kk = "bet" if curbet == 0 else "raise"
            acts[street].append(kk)
            if k == "call": facing_size[street] = facing_size.get(street, 0)
        if k == "raise": curbet = a
    if s1 is None: continue
    d = (s1 - s0) / bb
    for st in (2, 3):
        if acts.get(st):
            b = board[:3 + st - 1] if st == 2 else board[:5]
            ht = eval7.handtype(eval7.evaluate([C[x] for x in h["hole"] + b]))
            hc = ht if ht in ("High Card", "Pair", "Two Pair") else "Trips+"
            key = ("turn" if st == 2 else "river", "/".join(acts[st]), hc)
            out[key][0] += 1; out[key][1] += d
    if h["hand"] <= 20:
        k0 = "pf:" + "/".join(acts.get(0, ["-"])) + (" post" if any(acts.get(x) for x in (1, 2, 3)) else "")
        lvl0[k0][0] += 1; lvl0[k0][1] += d
for key in sorted(out, key=lambda x: out[x][1])[:22]:
    n, v = out[key]
    print("%-45s n=%5d total %8.0f per %6.2f" % (key, n, v, v / n))
print("--- level 0 by preflop line")
for key in sorted(lvl0, key=lambda x: lvl0[x][1])[:12]:
    n, v = lvl0[key]
    print("%-45s n=%5d total %8.0f per %6.2f" % (key, n, v, v / n))
