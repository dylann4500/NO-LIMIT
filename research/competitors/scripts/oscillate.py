"""Do teams oscillate between rounds (e.g. fold more, then less, then more)?
usage: python -I oscillate.py KEYFILE r2/agg2.json r3/agg2.json ...   (KEYFILE: 'agg2' metrics or 'agg' for postflop fold-to-bet)
Tests, per metric, over teams present in every round:
  - size of round-to-round changes vs measurement noise (binomial SE)
  - share of consecutive changes that flip sign (pure noise around a fixed rate -> ~67%; trend -> <50%)
  - lag-1 correlation of consecutive changes (pure noise -> -0.5)
  - out-of-sample prediction of the next round: 'same as last round' vs 'oscillation' (last - k*last change) vs 'mean of all previous'"""
import json, math, sys, statistics as S

mode = sys.argv[1]; files = sys.argv[2:]
R = [json.load(open(f)) for f in files]
METRICS = {"agg2": {"pre fold vs 1 raise": ("face1_fold", "face1"), "open % unopened": ("open", "unop"),
                    "flop first-in bet %": ("ff_bet", "ff_opp"), "VPIP": ("vpip", "hands")},
           "agg": {"postflop fold to bet": ("fold_bet", "face_bet"), "call jam": ("call_jam", "face_jam")}}[mode]
names = [{s: A["name"].get(s, s) for s in A["st"]} for A in R]
by = []
for A, nm in zip(R, names):
    d = {}
    for s, c in A["st"].items():
        if len(A["pts"].get(s, [])) >= 30: d[nm[s]] = c
    by.append(d)
teams = sorted(set.intersection(*[set(d) for d in by]) - {"avalon"})
print(f"{len(teams)} teams present in all {len(files)} rounds")
for lab, (num, den) in METRICS.items():
    vals, ses = {}, {}
    for t in teams:
        v = []; e = []
        for d in by:
            n = d[t].get(den, 0); k = d[t].get(num, 0)
            if n < 100: break
            p = k / n; v.append(p); e.append(math.sqrt(p * (1 - p) / n))
        if len(v) == len(files): vals[t] = v; ses[t] = e
    if len(vals) < 10: print(lab, "too few"); continue
    ch = [abs(v[i + 1] - v[i]) for v in vals.values() for i in range(len(v) - 1)]
    noise = [math.sqrt(e[i] ** 2 + e[i + 1] ** 2) for e in ses.values() for i in range(len(e) - 1)]
    flips = tot = 0; xs = []; ys = []
    for v in vals.values():
        d = [v[i + 1] - v[i] for i in range(len(v) - 1)]
        for i in range(len(d) - 1):
            if abs(d[i]) > 0 and abs(d[i + 1]) > 0:
                tot += 1; flips += (d[i] > 0) != (d[i + 1] > 0)
            xs.append(d[i]); ys.append(d[i + 1])
    mx, my = S.mean(xs), S.mean(ys)
    corr = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    # prediction of round t+1 (t>=2) from rounds <= t
    err = {"same as last": [], "oscillate k=0.5": [], "oscillate k=1": [], "mean of previous": []}
    for v in vals.values():
        for t in range(1, len(v) - 1):
            last, prev = v[t], v[t - 1]; actual = v[t + 1]
            err["same as last"].append((actual - last) ** 2)
            err["oscillate k=0.5"].append((actual - (last - 0.5 * (last - prev))) ** 2)
            err["oscillate k=1"].append((actual - prev) ** 2)
            err["mean of previous"].append((actual - S.mean(v[:t + 1])) ** 2)
    print(f"\n== {lab}: {len(vals)} teams")
    print(f"  median |change| per round {S.median(ch)*100:.1f} pts  vs median noise SE of a change {S.median(noise)*100:.1f} pts")
    print(f"  sign flips of consecutive changes: {flips/tot:.0%} (n={tot}); pure noise ~67%, no structure 50%")
    print(f"  lag-1 corr of consecutive changes: {corr:+.2f} (pure noise -0.50)")
    print("  next-round prediction, median abs error (pts): " + "  ".join(f"{k} {math.sqrt(S.median(v))*100:.2f}" for k, v in err.items()))
    fld = []
    for d in by:
        k = sum(c.get(num, 0) for c in d.values()); n = sum(c.get(den, 0) for c in d.values()); fld.append(k / max(1, n))
    print("  field aggregate by round: " + " -> ".join(f"{x:.1%}" for x in fld))
