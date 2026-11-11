"""Aggregate R1..R6 pickles from analyze.py into the per-round profile and the ICM call-mask study.
usage: python -I aggregate.py   (reads R1.pkl..R6.pkl next to this file)"""
import collections, math, os, pickle, sys
D = os.path.dirname(os.path.abspath(__file__))
OFF = {"R1": 18.10, "R2": 16.73, "R3": 19.05, "R4": 18.26, "R5": 17.95, "R6": 17.53}
W = {f"R{i}": i for i in range(1, 7)}
RS = ["R1", "R2", "R3", "R4", "R5", "R6"]
data = {r: pickle.load(open(os.path.join(D, f"{r}.pkl"), "rb")) for r in RS}


def ms(v):
    n = len(v); m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1)) if n > 1 else float("nan")
    return m, sd, sd / math.sqrt(n), n


def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 2
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


print("== Q1/Q2 per-round profile ==")
hdr = ("rnd tables  pts    off   diff   sd    se   | VPIP  PFR  jam%  | F2B-flopHU F2B-flop F2B-post | "
       "1st   2nd   3rd   oom   cap  tie | bustHand(all/oom) | auto(total, tables)")
print(hdr)
P = {}
for r in RS:
    T = data[r]["tables"]
    pts = [t["pts"] for t in T]; m, sd, se, n = ms(pts); P[r] = (m, se, sd, n)
    c = collections.Counter()
    for t in T: c.update(t["c"])
    pl = collections.Counter(t["place"] for t in T)
    bh = [t["bust_hand"] for t in T if t["bust_hand"] is not None]
    bo = [t["bust_hand"] for t in T if t["place"] == "oom"]
    auto_tables = sum(1 for t in T if t["c"].get("auto", 0) > 0)
    h = c["hands"]
    print(f"{r} {n:6d} {m:6.3f} {OFF[r]:5.2f} {m-OFF[r]:+6.3f} {sd:5.2f} {se:5.3f} | "
          f"{c['vpip']/h:5.1%} {c['pfr']/h:5.1%} {c['jam']/h:5.2%} | "
          f"{c['flop_fold_hu']/c['flop_face_hu']:6.1%} (n={c['flop_face_hu']}) {c['flop_fold']/c['flop_face']:6.1%} {c['post_fold']/c['post_face']:6.1%} | "
          f"{pl['1st']/n:5.1%} {pl['2nd']/n:5.1%} {pl['3rd']/n:5.1%} {pl['oom']/n:5.1%} {pl['cap']/n:4.1%} {pl['bust_tie']+pl['?']} | "
          f"{sum(bh)/len(bh):5.1f} / {sum(bo)/len(bo):5.1f} | {c['auto']}, {auto_tables}")
print("hands dealt per round:", {r: sum(t["c"]["hands"] for t in data[r]["tables"]) for r in RS})
print("auto examples:", {r: data[r]["examples"].get("auto", [])[:2] for r in RS})
m5, se5, sd5, n5 = P["R5"]; m6, se6, sd6, n6 = P["R6"]
d = m6 - m5; sed = math.sqrt(se5 ** 2 + se6 ** 2); z = d / sed
pval = math.erfc(abs(z) / math.sqrt(2))
print(f"R6-R5 = {d:+.3f} pts/table, SE {sed:.3f}, 95% CI [{d-1.96*sed:+.3f}, {d+1.96*sed:+.3f}], z={z:.2f}, two-sided p={pval:.3f}")
print(f"  weighted (x6 for R6): one SE of R6 alone = {6*se6:.2f} weighted points")

print("\n== Q3 facing a preflop all-in (first such decision per hand), by players alive ==")
print("rnd alive  spots  /table  call%  [95% CI]        | calls  meanD  [95% CI]        | clean calls (HU pot, no later caller): n  meanD [CI]")
S = {}
for r in RS:
    T = data[r]["tables"]; nt = len(T)
    sp = [s for t in T for s in t["spots"]]
    bad = sum(1 for s in sp if abs(s["Uafter"] - s["Uafter_mine"]) > 1e-3)
    for a in (2, 3, 4, 5):
        x = [s for s in sp if s["alive"] == a]
        k = sum(1 for s in x if s["act"] != "fold"); n = len(x)
        lo, hi = wilson(k, n)
        dl = [s["Uafter"] - s["UF"] for s in x if s["act"] != "fold"]
        md, sdd, sed_, nn = ms(dl) if len(dl) > 1 else (float("nan"),) * 4
        cl = [s["Uafter"] - s["UF"] for s in x if s["act"] != "fold" and not s["multi"] and not s["later"] and s["njams"] == 1]
        mc, sdc, sec, nc = ms(cl) if len(cl) > 1 else (float("nan"),) * 4
        S[(r, a)] = dict(n=n, k=k, nt=nt, rate=k / n if n else float("nan"), dmean=md, dse=sed_, dn=nn, dl=dl, x=x)
        print(f"{r}  {a}    {n:6d} {n/nt:6.3f} {k/n:6.1%} [{lo:5.1%},{hi:5.1%}] | {nn:5d} {md:+6.2f} [{md-1.96*sed_:+5.2f},{md+1.96*sed_:+5.2f}] | {nc:5d} {mc:+6.2f} [{mc-1.96*sec:+5.2f},{mc+1.96*sec:+5.2f}]")
    if bad: print(f"  {r}: {bad} spots where platform equity_after != my ICM")
    x23 = [s for s in sp if s["alive"] in (2, 3)]
    k = sum(1 for s in x23 if s["act"] != "fold"); lo, hi = wilson(k, len(x23))
    dl = [s["Uafter"] - s["UF"] for s in x23 if s["act"] != "fold"]; md, _, se_, nn = ms(dl)
    S[(r, "23")] = dict(n=len(x23), k=k, nt=nt, rate=k / len(x23), dmean=md, dse=se_, dn=nn, dl=dl, x=x23)
    print(f"{r} 2-3    {len(x23):6d} {len(x23)/nt:6.3f} {k/len(x23):6.1%} [{lo:5.1%},{hi:5.1%}] | {nn:5d} {md:+6.2f} [{md-1.96*se_:+5.2f},{md+1.96*se_:+5.2f}]")

print("\n== Bug signature: share of 2-3-alive spots where the buggy mask threshold exceeds the correct one, and fold rate by threshold gap ==")
for r in RS:
    x = S[(r, "23")]["x"]
    g = [s for s in x if s["tbug"] is not None and s["t"] is not None]
    big = [s for s in g if s["tbug"] - s["t"] > 0.10]
    small = [s for s in g if s["tbug"] - s["t"] <= 0.10]
    f = lambda L: sum(1 for s in L if s["act"] != "fold") / max(1, len(L))
    print(f"{r}: spots {len(g)}, gap>0.10: n={len(big)} call {f(big):5.1%};  gap<=0.10: n={len(small)} call {f(small):5.1%}")

print("\n== Calls in band [t, tbug) by equity proxy (eq vs top-w range from tables_bayarea.json) ==")
WID = [0.05, 0.10, 0.20, 0.35, 0.50, 1.0]
for wi in (4, 5):
    for r in RS:
        x = S[(r, "23")]["x"]
        inb = [s for s in x if s["eqw"] and s["t"] is not None and s["tbug"] is not None and s["t"] <= s["eqw"][wi] < s["tbug"]]
        above = [s for s in x if s["eqw"] and s["tbug"] is not None and s["eqw"][wi] >= s["tbug"]]
        f = lambda L: sum(1 for s in L if s["act"] != "fold") / max(1, len(L))
        dl = [s["Uafter"] - s["UF"] for s in inb if s["act"] != "fold"]
        md, _, se_, nn = ms(dl) if len(dl) > 1 else (float("nan"),) * 4
        print(f"w={WID[wi]:.2f} {r}: masked-band spots n={len(inb)} ({len(inb)/len(x):.0%}) call {f(inb):5.1%} | above tbug n={len(above)} call {f(above):5.1%} | band calls n={nn} meanD {md:+.2f} [{md-1.96*se_:+.2f},{md+1.96*se_:+.2f}]")

print("\n== Cost estimate: missing calls per table x R6 value per call x weight ==")
for a in (2, 3):
    print(f"alive={a}: R6 value/call {S[('R6',a)]['dmean']:+.3f} (se {S[('R6',a)]['dse']:.3f}, n {S[('R6',a)]['dn']})")
tot = {}
for r in ("R4", "R5"):
    cost = 0.0; var = 0.0
    for a in (2, 3):
        s6 = S[("R6", a)]; sk = S[(r, a)]
        spt = sk["n"] / sk["nt"]
        dr = s6["rate"] - sk["rate"]
        se_dr = math.sqrt(s6["rate"] * (1 - s6["rate"]) / s6["n"] + sk["rate"] * (1 - sk["rate"]) / sk["n"])
        miss = dr * spt; se_miss = se_dr * spt
        v = s6["dmean"]; se_v = s6["dse"]
        c = miss * v; vc = (v * se_miss) ** 2 + (miss * se_v) ** 2
        cost += c; var += vc
        print(f"{r} alive={a}: spots/table {spt:.3f}, rate {sk['rate']:.1%} vs R6 {s6['rate']:.1%} -> missing calls/table {miss:+.4f} (se {se_miss:.4f}); pts/table {c:+.4f} (se {math.sqrt(vc):.4f})")
    print(f"{r}: pts/table {cost:+.4f} +- {1.96*math.sqrt(var):.4f}; weighted x{W[r]}: {W[r]*cost:+.3f} +- {1.96*W[r]*math.sqrt(var):.3f}")
    tot[r] = (W[r] * cost, W[r] ** 2 * var)
c = sum(v[0] for v in tot.values()); s = math.sqrt(sum(v[1] for v in tot.values()))
print(f"R4+R5 weighted cost: {c:+.3f} +- {1.96*s:.3f} (95%)")
