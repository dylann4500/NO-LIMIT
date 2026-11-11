"""For each of our postflop calls: pot odds taken vs how often the hand was eventually won (real field data)."""
import json, gzip, collections, sys
import eval7
P = sys.argv[1] if len(sys.argv) > 1 else "lab/field_bots/claude_default_d/round1/hand_history.jsonl.gz"
C = {r + s: eval7.Card(r + s) for r in "23456789TJQKA" for s in "shdc"}
agg = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0])  # n, sum req, wins, chips EV of call (bb)
for l in gzip.open(P, "rt"):
    h = json.loads(l)
    me = h["seat"]; bb = h["blinds"][1]
    if str(me) not in h["stacks"]: continue
    board = []; street = 0; pot = 0; contrib = collections.Counter(); calls = []
    won = 0
    for k, s, a, c in h["events"]:
        if k == "board": board += c; street += 1; contrib = collections.Counter(); continue
        if k in ("blind", "ante"): pot += a; contrib[s] += a
        elif k == "call":
            if s == me and street >= 1:
                ht = eval7.handtype(eval7.evaluate([C[x] for x in h["hole"] + board]))
                hc = ht if ht in ("High Card", "Pair", "Two Pair") else "Trips+"
                calls.append((street, hc, a, pot))
            pot += a; contrib[s] += a
        elif k == "raise":
            pot += a - contrib[s]; contrib[s] = a
        elif k == "win" and s == me: won += a
    final_pot = pot
    for st, hc, a, p in calls:
        req = a / float(p + a)
        key = (("flop", "turn", "river")[st - 1], hc)
        g = agg[key]; g[0] += 1; g[1] += req; g[2] += 1 if won > 0 else 0
for k in sorted(agg):
    n, r, w, _ = agg[k]
    print("%-22s n=%4d  avg pot-odds needed %.2f   hand won %.2f" % (k, n, r / n, w / n))
