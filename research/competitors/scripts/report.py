"""usage: python -I report.py OUTDIR/agg.json [TOPN]  -> prints comparison tables"""
import collections, json, math, statistics as S, sys

A = json.load(open(sys.argv[1]))
TOPN = int(sys.argv[2]) if len(sys.argv) > 2 else 6
you, name, pts, st, sizes = A["you"], A["name"], A["pts"], A["st"], A["sizes"]
nm = lambda s: ("US" if s == you else name.get(s, s[:8]))[:14]
rows = sorted(((S.mean(v), s) for s, v in pts.items() if len(v) >= 30), reverse=True)
rank = {s: i + 1 for i, (_, s) in enumerate(rows)}
r = lambda a, b: a / b if b else float("nan")


def ci(v):
    m = S.mean(v); se = S.pstdev(v) / math.sqrt(len(v)); return m, 1.96 * se


# maniacs: jam >= 30% of hands
maniac = {s for s in st if r(st[s].get("jam", 0), st[s].get("hands", 0)) >= 0.30 and len(pts.get(s, [])) >= 30}
top = [s for _, s in rows[:TOPN]]
show = top + ([you] if you not in top else [])
field = [s for _, s in rows if s not in maniac]

print(f"tables={len(A['tables'])} teams={len(rows)} maniacs={len(maniac)}: {sorted(nm(s) for s in maniac)}")
print("\n== POINTS (95% CI) and places ==")
for s in show:
    v = pts[s]; m, h = ci(v); c = collections.Counter(round(x) for x in v)
    print(f"{rank[s]:3d} {nm(s):14s} {m:5.2f}±{h:4.2f} n={len(v):5d} 1st {c[50]/len(v):4.0%} 2nd {c[30]/len(v):4.0%} 3rd {c[20]/len(v):4.0%}")


def g(s, k):
    return st[s].get(k, 0)


def agg(group, k):
    return sum(g(s, k) for s in group)


def statline(get):
    hd = ["VPIP", "PFR", "open%", "openJam%", "3bet%", "3betJam/3b", "cbetHU", "cbetMW", "barrelT", "barrelR",
          "foldToBet", "foldToCbet", "raiseVsBet"]
    vals = [r(get("vpip"), get("hands")), r(get("pfr"), get("hands")),
            r(get("open_raise") + get("open_jam"), get("unopened")), r(get("open_jam"), get("unopened")),
            r(get("threebet"), get("face_open")), r(get("threebet_jam"), get("threebet")),
            r(get("cbet_hu"), get("cbet_opp_hu")), r(get("cbet_mw"), get("cbet_opp_mw")),
            r(get("barrel2"), get("barrel2_opp")), r(get("barrel3"), get("barrel3_opp")),
            r(get("fold_bet"), get("face_bet")), r(get("fold_cbet"), get("face_cbet")),
            r(get("raise_bet"), get("face_bet"))]
    return hd, vals


print("\n== PREFLOP/POSTFLOP STYLE ==")
hd, _ = statline(lambda k: 0)
print(f"{'':18s}" + " ".join(f"{h:>9s}" for h in hd))
for s in show:
    _, v = statline(lambda k, s=s: g(s, k))
    print(f"{nm(s):18s}" + " ".join(f"{x:9.1%}" for x in v))
for lab, grp in (("TOP%d avg" % TOPN, top), ("field(non-maniac)", field)):
    _, v = statline(lambda k, grp=grp: agg(grp, k))
    print(f"{lab:18s}" + " ".join(f"{x:9.1%}" for x in v))


def med(x):
    return S.median(x) if x else float("nan")


def q(x, p):
    if not x: return float("nan")
    x = sorted(x); return x[min(len(x) - 1, int(p * len(x)))]


print("\n== SIZES: open raise-to (bb) median [p25,p75], 3bet x open, bet/pot by street (median) ==")
for s in show + ["FIELD"]:
    if s == "FIELD":
        Z = collections.defaultdict(list)
        for f in field:
            for k, v in sizes.get(f, {}).items(): Z[k].extend(v)
    else:
        Z = sizes.get(s, {})
    ob = Z.get("open_bb", [])
    print(f"{('FIELD' if s=='FIELD' else nm(s)):14s} open {med(ob):4.1f} [{q(ob,.25):4.1f},{q(ob,.75):4.1f}] n={len(ob):5d} "
          f"| 8-6 {med(Z.get('open_bb_8-6',[])):4.1f} 5-4 {med(Z.get('open_bb_5-4',[])):4.1f} 3-2 {med(Z.get('open_bb_3-2',[])):4.1f} "
          f"| 3bx {med(Z.get('3bet_x',[])):4.1f} | bet/pot F {med(Z.get('bet_frac_s1',[])):4.2f} T {med(Z.get('bet_frac_s2',[])):4.2f} R {med(Z.get('bet_frac_s3',[])):4.2f}"
          f" | openJam eff bb med {med(Z.get('openjam_eff',[])):4.1f}")

print("\n== BY PLAYERS LEFT: VPIP / openJam% of unopened / callJam% ==")
for s in show + ["TOP", "FIELD"]:
    grp = top if s == "TOP" else field if s == "FIELD" else [s]
    out = []
    for B in ("8-6", "5-4", "3-2"):
        h = agg(grp, "hands_" + B)
        out.append(f"{B}: vpip {r(agg(grp,'vpip_'+B),h):4.0%} oJam {r(agg(grp,'open_jam_'+B),agg(grp,'unopened_'+B)):4.0%} "
                   f"oRaise {r(agg(grp,'open_raise_'+B),agg(grp,'unopened_'+B)):4.0%} "
                   f"3b {r(agg(grp,'threebet_'+B),agg(grp,'face_open_'+B)):4.0%} "
                   f"cJam {r(agg(grp,'call_jam_'+B),agg(grp,'face_jam_'+B)):4.0%}(n{agg(grp,'face_jam_'+B)})")
    print(f"{('TOP' if s=='TOP' else 'FIELD' if s=='FIELD' else nm(s)):8s} " + " | ".join(out))

print("\n== VISIBLE CARD: fold-to-bet by BETTOR's visible class (pair/over/low); HU first-in bet rate by OPP's visible class ==")
for s in show + ["TOP", "FIELD"]:
    grp = top if s == "TOP" else field if s == "FIELD" else [s]
    f = " ".join(f"{c}:{r(agg(grp,'fold_bet_'+c),agg(grp,'face_bet_'+c)):4.0%}(n{agg(grp,'face_bet_'+c)})" for c in ("pair", "over", "low"))
    o = " ".join(f"{c}:{r(agg(grp,'fold_ourbet_'+c),agg(grp,'face_ourbet_'+c)):4.0%}(n{agg(grp,'face_ourbet_'+c)})" for c in ("pair", "over", "low"))
    b = " ".join(f"{c}:{r(agg(grp,'hu_bet_'+c),agg(grp,'hu_firstin_'+c)):4.0%}" for c in ("pair", "over", "low"))
    print(f"{('TOP' if s=='TOP' else 'FIELD' if s=='FIELD' else nm(s)):8s} fold[{f}] | vsOURbet[{o}] | HUbetInto[{b}]")

print("\n== CHIP FLOW: pairwise transfers (starting stacks, all hands) and HU-flop net bb ==")
pair = collections.Counter(); pe = collections.Counter()
for a, b, ph, v in A["pair"]:
    pair[(a, b)] += v; pe[(a, b, ph)] += v
hu = {(a, b): (v, n) for a, b, v, n in A["hu"]}
cnt = collections.Counter()  # tables together
for P, BH, SP in A["tables"]:
    ss = list(P)
    for x in ss:
        for y in ss:
            if x != y: cnt[(x, y)] += 1
for s in top:
    if s == you: continue
    net = pair[(you, s)] - pair[(s, you)]; n = cnt[(you, s)]
    hv, hn = hu.get((you, s), (0, 0))
    print(f"US vs {nm(s):14s} tables {n:4d} net {net/n*100:+6.1f}% stack/table | HU-flop hands {hn:5d} our net {r(hv,hn):+6.2f}bb/hand total {hv:+8.0f}bb")
print("HU-flop bb/hand vs anyone:", " ".join(f"{nm(s)} {r(*hu.get((s,'*'),(0,0))):+.2f}(n{hu.get((s,'*'),(0,0))[1]})" for s in show))

print("\n== MANIAC EXTRACTION: chips taken from maniacs per table shared (stacks), early(<=15 hands) / late ==")
for s in show + ["FIELD"]:
    grp = field if s == "FIELD" else [s]
    e = l = n = 0
    for x in grp:
        for m in maniac:
            e += pe[(x, m, "early")] - pe[(m, x, "early")]; l += pe[(x, m, "late")] - pe[(m, x, "late")]; n += cnt[(x, m)]
    print(f"{('FIELD' if s=='FIELD' else nm(s)):14s} maniac-tables-pairs {n:6d} early {r(e,n):+.3f} late {r(l,n):+.3f} stacks per maniac-pairing")

print("\n== TABLE COMPOSITION: mean points by #maniacs at table ==")
by = collections.defaultdict(lambda: collections.defaultdict(list))
for P, BH, SP in A["tables"]:
    k = sum(1 for x in P if x in maniac); k = min(k, 3)
    for x, v in P.items():
        if x in show: by[x][k].append(v)
        if x in field: by["FIELD"][k].append(v)
for s in show + ["FIELD"]:
    print(f"{('FIELD' if s=='FIELD' else nm(s)):14s} " + " ".join(f"{k}m: {S.mean(by[s][k]):5.2f}(n{len(by[s][k])})" for k in sorted(by[s])))

print("\n== SEAT EFFECT (all non-maniac players): mean pts by seat index ==")
seat = collections.defaultdict(list); useat = collections.defaultdict(list)
for P, BH, SP in A["tables"]:
    for x, i, v in SP:
        if x in field: seat[i].append(v)
        if x == you: useat[i].append(v)
print(" ".join(f"s{i}:{S.mean(v):5.2f}" for i, v in sorted(seat.items())))
print("US " + " ".join(f"s{i}:{S.mean(v):5.2f}(n{len(v)})" for i, v in sorted(useat.items())))
