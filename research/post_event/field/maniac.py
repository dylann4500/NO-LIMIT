"""R6: do high fold-to-3-bet teams lose more points at tables with thepastaway (60% 3-bettor)?

usage: python -I maniac.py OUTDIR [ROUND] [TEAMNAME]
Groups teams (>=100 shared tables) by fold-to-3-bet tercile; compares their points at tables
where TEAMNAME sat vs all their shared tables. Also avalon's F3B percentile.
"""
import collections, math, os, pickle, sys
OUT = sys.argv[1]; R = int(sys.argv[2]) if len(sys.argv) > 2 else 6
TEAM = sys.argv[3] if len(sys.argv) > 3 else "thepastaway"
d = pickle.load(open(os.path.join(OUT, f"r{R}.pkl"), "rb"))
names = d["names"]; you = d["you"]
tid = [e for e, n in names.items() if n == TEAM][0]
allp = collections.defaultdict(list); withp = collections.defaultdict(list)
for it, tb, nh, alive, me, srows in d["rows"]:
    present = any(x[0] == tid for x in srows)
    for x in srows:
        e = x[0]
        if e in ("FILLER", tid):
            continue
        allp[e].append(x[1])
        if present:
            withp[e].append(x[1])
C = d["C"]
f3b = {e: C[e].get("f3b", 0) / C[e]["f3b_opp"] for e in allp if len(allp[e]) >= 100 and C.get(e, {}).get("f3b_opp", 0) >= 200}
order = sorted(f3b, key=f3b.get)
m = lambda v: sum(v) / len(v)
k = len(order) // 3
print(f"R{R} vs {TEAM}: teams with F3B data {len(order)}; avalon F3B {100 * f3b.get(you, float('nan')):.1f}% "
      f"(rank {order.index(you) + 1 if you in order else '-'} of {len(order)} from lowest)")
for lab, grp in (("low F3B", order[:k]), ("mid F3B", order[k:2 * k]), ("high F3B", order[2 * k:])):
    diffs = []; n = 0
    for e in grp:
        if e == you:
            continue
        w = withp[e]
        if not w:
            continue
        diffs.extend([p - m(allp[e]) for p in w]); n += 1
    sd = math.sqrt(sum((x - m(diffs)) ** 2 for x in diffs) / len(diffs))
    print(f"  {lab:<9} F3B {100 * f3b[grp[0]]:.0f}-{100 * f3b[grp[-1]]:.0f}%  teams {n}  seat-tables with {TEAM} {len(diffs)}  "
          f"pts diff {m(diffs):+.2f} ± {sd / math.sqrt(len(diffs)):.2f}")
