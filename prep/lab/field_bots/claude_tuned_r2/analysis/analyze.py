"""Round-1 hand history analysis: where did claude_tuned win/lose chips, and how does the field play?"""
import gzip, json, collections, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "claude_tuned", "round1", "hand_history.jsonl.gz")
H = [json.loads(l) for l in gzip.open(PATH, "rt")]
ME = "claude_tuned"


def end_stack(h, s):
    for k, seat, amt, c in h["events"]:
        if k == "stack" and seat == s:
            return amt
    return None


def classify(h):
    me = h["seat"]
    ev = h["events"]
    street = 0
    nraise = 0
    mine = []
    allin_me = False
    st0 = h["stacks"][str(me)]
    for k, s, a, c in ev:
        if k == "board":
            street += 1
            continue
        if k == "raise" and street == 0:
            nraise += 1
        if s == me and k in ("fold", "check", "call", "raise"):
            mine.append((street, k, a, nraise))
    return mine


def pf_tag(h, mine):
    pf = [m for m in mine if m[0] == 0]
    if not pf:
        return "walk/none"
    first = pf[0]
    st0 = h["stacks"][str(h["seat"])]
    tag = None
    k, nr = first[1], first[3]
    if k == "fold":
        return "fold"
    if k == "check":
        tag = "bb_check"
    elif k == "call":
        tag = "limp" if nr == 0 else ("call_raise" if nr == 1 else "call_3bet+")
    elif k == "raise":
        amt = first[2]
        if amt >= st0 * 0.95:
            tag = "shove_open" if nr == 1 else "reshove"
        else:
            tag = "open" if nr == 1 else ("3bet" if nr == 2 else "4bet+")
    # later preflop actions
    for m in pf[1:]:
        if m[1] == "fold":
            tag += ">fold"
            break
        if m[1] == "call":
            tag += ">call"
        if m[1] == "raise":
            tag += ">raise"
    return tag


rows = []
for h in H:
    me = str(h["seat"])
    if me not in h["stacks"]:
        continue
    st0 = h["stacks"][me]
    st1 = end_stack(h, h["seat"])
    if st1 is None:
        continue
    bb = h["blinds"][1]
    mine = classify(h)
    sd = any(k == "show" and s == h["seat"] for k, s, a, c in h["events"])
    maxstreet = max([m[0] for m in mine] or [0])
    rows.append(dict(h=h, net=st1 - st0, netbb=(st1 - st0) / bb, tag=pf_tag(h, mine), sd=sd, mine=mine,
                     bust=(st1 == 0), stbb=st0 / bb, maxstreet=maxstreet, nplayers=len(h["stacks"])))

print("hands", len(rows), "total net bb %.0f" % sum(r["netbb"] for r in rows))
agg = collections.defaultdict(lambda: [0, 0.0, 0, 0])
for r in rows:
    a = agg[r["tag"]]
    a[0] += 1; a[1] += r["netbb"]; a[2] += r["bust"]; a[3] += r["sd"]
print("\n%-28s %6s %9s %8s %5s %5s" % ("preflop line", "n", "net bb", "bb/hand", "bust", "sd"))
for t, a in sorted(agg.items(), key=lambda kv: kv[1][1]):
    print("%-28s %6d %9.0f %8.2f %5d %5d" % (t, a[0], a[1], a[1] / a[0], a[2], a[3]))

# by stack depth
print("\nby stack depth (bb at hand start)")
bins = [(0, 8), (8, 13), (13, 20), (20, 35), (35, 60), (60, 1e9)]
for lo, hi in bins:
    rr = [r for r in rows if lo <= r["stbb"] < hi]
    if rr:
        print("  %4.0f-%-6.0f n=%5d net bb %8.0f  bb/hand %6.2f busts %d" % (lo, hi, len(rr), sum(r["netbb"] for r in rr), sum(r["netbb"] for r in rr) / len(rr), sum(r["bust"] for r in rr)))

# busts: line that busted us
print("\nbust lines:", collections.Counter(r["tag"] + ("/post" if r["maxstreet"] > 0 else "") for r in rows if r["bust"]).most_common(12))

# postflop: our actions when reaching the flop, net
post = [r for r in rows if r["maxstreet"] > 0]
print("\nsaw flop: n=%d net bb %.0f; showdown n=%d net %.0f; non-sd n=%d net %.0f" % (
    len(post), sum(r["netbb"] for r in post), sum(r["sd"] for r in post), sum(r["netbb"] for r in post if r["sd"]),
    sum(1 for r in post if not r["sd"]), sum(r["netbb"] for r in post if not r["sd"])))
# postflop lines: last action of ours
pl = collections.defaultdict(lambda: [0, 0.0])
for r in post:
    seq = "".join({"fold": "F", "check": "x", "call": "C", "raise": "R"}[m[1]] for m in r["mine"] if m[0] > 0)
    key = seq[:4]
    pl[key][0] += 1; pl[key][1] += r["netbb"]
print("postflop action strings (ours, flop on):")
for k, v in sorted(pl.items(), key=lambda kv: kv[1][1])[:12]:
    print("   %-6s n=%5d net %8.0f  avg %6.2f" % (k, v[0], v[1], v[1] / v[0]))
for k, v in sorted(pl.items(), key=lambda kv: -kv[1][1])[:6]:
    print("   %-6s n=%5d net %8.0f  avg %6.2f" % (k, v[0], v[1], v[1] / v[0]))
