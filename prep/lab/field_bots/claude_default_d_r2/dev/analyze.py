"""Round-1 hand-history analysis: where did our chips go?"""
import json, gzip, collections, sys
P = sys.argv[1] if len(sys.argv) > 1 else "lab/field_bots/claude_default_d/round1/hand_history.jsonl.gz"
ME = "claude_default_d"
tot = collections.defaultdict(float); cnt = collections.Counter()
busts = []
by_opp = collections.defaultdict(float)
allin_pf = []
lines = collections.defaultdict(lambda: [0, 0.0])
for l in gzip.open(P, "rt"):
    h = json.loads(l)
    me = h["seat"]; st = h["stacks"]; bb = h["blinds"][1]
    if str(me) not in st: continue
    s0 = st[str(me)]
    s1 = None
    street = 0
    my_acts = []
    shows = {}
    invested_pf_allin = False
    winners = {}
    pot_contrib = collections.Counter()
    for k, s, a, c in h["events"]:
        if k == "board": street += 1
        elif k == "stack" and s == me: s1 = a
        elif k == "show": shows[s] = c
        elif k == "win": winners[s] = winners.get(s, 0) + a
        elif k in ("fold", "check", "call", "raise") and s == me:
            my_acts.append((street, k, a))
    if s1 is None: continue
    d = (s1 - s0) / bb
    lvl = (h["hand"] - 1) // 20
    tot["lvl%d" % lvl] += d
    nplayers = len(st)
    tot["n%d" % nplayers] += d
    # line classification
    if not my_acts:
        key = "no_action"
    else:
        last = my_acts[-1]
        went_sd = me in shows
        maxst = max(a[0] for a in my_acts)
        vol = any(k in ("call", "raise") for _, k, _ in my_acts)
        if not vol and last[1] == "fold" and last[0] == 0:
            key = "pf_fold_noinvest"
        elif went_sd:
            key = "showdown_%s_st%d" % ("win" if d > 0 else "lose", maxst)
        elif last[1] == "fold":
            key = "fold_st%d" % last[0]
        else:
            key = "won_uncontested_st%d" % last[0]
    lines[key][0] += 1; lines[key][1] += d
    if s1 == 0 and s0 > 0:
        opp = {int(k): v for k, v in shows.items() if int(k) != me}
        busts.append((h["table"], h["hand"], nplayers, round(s0 / bb, 1), h["hole"], [(k, a, c) for k, s, a, c in h["events"] if s == me and k in ("call", "raise")], opp, street))
print("chip delta (BB) by level:", {k: round(v) for k, v in sorted(tot.items()) if k.startswith("lvl")})
print("by players at table:", {k: round(v) for k, v in sorted(tot.items()) if k.startswith("n")})
print("lines (count, total BB, BB/hand):")
for k, (n, v) in sorted(lines.items(), key=lambda x: x[1][1]):
    print("  %-26s %6d %9.0f %7.2f" % (k, n, v, v / max(1, n)))
print("busts:", len(busts))
bl = collections.Counter((b[2], b[7]) for b in busts)
print("busts by (players, street reached):", sorted(bl.items()))
for b in busts[:40]:
    print(b)
