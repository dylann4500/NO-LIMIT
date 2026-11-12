import pickle, collections, numpy as np, json
RS = collections.Counter(); OP = collections.Counter(); perround = {}
for k in range(1, 7):
    d = pickle.load(open(f"R{k}.pkl", "rb")); TOP = d["TOP"]
    RS.update(d["resp"]); OP.update(d["opn"]); perround[k] = (d["resp"], d["opn"])
    del d
BL = ["<0.28", "0.28-0.40", "0.40-0.55", "0.55-0.70", "0.70-0.90", "0.90-1.25", ">1.25", "all-in"]
MID = [0.2, 0.33, 0.5, 0.65, 0.75, 1.0, 1.5, None]
def agg(sel):
    c = np.zeros((4, 8, 3))
    for (bt, st, bk, ag, rc, hu, a), n in RS.items():
        if sel(bt, st, bk, ag, rc, hu): c[st, bk, a] += n
    return c
def show(title, c):
    print("\n" + title); print(f"{'street':6s} {'bet/pot':10s} {'n':>8s} {'fold%':>6s} {'call%':>6s} {'raise%':>6s} {'±se':>5s} {'breakeven':>9s} {'bluffEV/pot':>11s} {'called/pot':>10s}")
    for st in (1, 2, 3):
        for bk in range(8):
            n = c[st, bk].sum()
            if n < 100: continue
            f, ca, r = c[st, bk] / n; se = (f * (1 - f) / n) ** .5
            s = MID[bk]
            ex = f"{100 * s / (1 + s):9.0f} {f - (1 - f) * s:11.3f} {(ca + r) * s:10.3f}" if s else ""
            print(f"{['', 'flop', 'turn', 'river'][st]:6s} {BL[bk]:10s} {int(n):8d} {100 * f:6.1f} {100 * ca:6.1f} {100 * r:6.1f} {100 * se:5.1f} {ex}")
show("A. HU, responders = other top-20 teams, bettors = everyone (6 rounds)", agg(lambda bt, st, bk, ag, rc, hu: hu == 1 and rc == 1))
show("A2. HU, responders = other top-20, bettors = top-20 only (excl. avalon)", agg(lambda bt, st, bk, ag, rc, hu: hu == 1 and rc == 1 and bt >= 0 and bt != 2))
show("B. HU, bettor = avalon, responders = other top-20", agg(lambda bt, st, bk, ag, rc, hu: hu == 1 and rc == 1 and bt == 2))
show("B2. HU, bettor = avalon, responders = everyone", agg(lambda bt, st, bk, ag, rc, hu: hu == 1 and bt == 2))
show("A3. multiway (3+ in pot), responders = other top-20, bettors = everyone", agg(lambda bt, st, bk, ag, rc, hu: hu == 0 and rc == 1))
# within-bettor: fold rate slope
print("\nC. within-bettor (same team, different sizes), HU, responders = all non-filler: fold% by bucket per team (n>=400), R1-6 pooled")
for st in (1, 2, 3):
    print(["", "flop", "turn", "river"][st])
    difs = []
    for bt in range(20):
        c = np.zeros((8, 3))
        for (b, s_, bk, ag, rc, hu, a), n in RS.items():
            if b == bt and s_ == st and hu == 1 and rc != 0: c[bk, a] += n
        ok = [bk for bk in range(7) if c[bk].sum() >= 400]
        if len(ok) >= 2:
            print(f"  {TOP[bt]:18s} " + "  ".join(f"{BL[bk]}:{100 * c[bk, 0] / c[bk].sum():.0f}%(n={int(c[bk].sum())})" for bk in ok))
            lo, hi = ok[0], ok[-1]
            difs.append((c[hi, 0] / c[hi].sum() - c[lo, 0] / c[lo].sum()) / (MID[hi] - MID[lo]))
    print(f"  mean fold-rate slope per +1.0 pot of bet size, within team: {100 * np.mean(difs):.1f} points (sd across {len(difs)} teams {100 * np.std(difs):.1f})")
# preflop
OL = ["2.0 (min)", "2.05-2.25", "2.25-2.45", "2.45-2.75", "2.75-3.25", ">3.25"]
def oagg(sel):
    c = collections.defaultdict(lambda: np.zeros(11))
    for (tm, pos, bk, deep, st), n in OP.items():
        if sel(tm, pos, bk, deep): c[(pos, bk)][st] += n
    return c
def oshow(title, c):
    print("\n" + title)
    print(f"{'pos':4s} {'size bb':10s} {'opens':>8s} {'all fold%':>9s} {'called%':>8s} {'3bet%':>6s} | per responder(top20): {'fold%':>6s} {'call%':>6s} {'3bet%':>6s} | {'opener bb/open':>14s}")
    for pos in ("EP", "MP", "CO", "BTN", "SB"):
        for bk in range(6):
            v = c.get((pos, bk))
            if v is None or v[0] < 300: continue
            n = v[0]; r = v[7:10]; rs = r.sum() or 1
            print(f"{pos:4s} {OL[bk]:10s} {int(n):8d} {100 * v[1] / n:9.1f} {100 * v[2] / n:8.1f} {100 * v[3] / n:6.1f} | {100 * r[0] / rs:27.1f} {100 * r[1] / rs:6.1f} {100 * r[2] / rs:6.1f} | {v[10] / n:14.3f}")
oshow("D. Preflop opens (no limpers, not all-in, opener >=25bb), openers = everyone incl. avalon", oagg(lambda tm, pos, bk, deep: deep == 1))
oshow("D2. openers = avalon only", oagg(lambda tm, pos, bk, deep: deep == 1 and tm == 2))
oshow("D3. openers = other top-20", oagg(lambda tm, pos, bk, deep: deep == 1 and tm >= 0 and tm != 2))
# per responder fold rate vs size, pooled over positions, standardised by position
print("\nD4. per-responder (top-20) response to an open by size, weighted to a common position mix (openers = everyone, deep)")
c = oagg(lambda tm, pos, bk, deep: deep == 1)
posw = {p: sum(c[(p, b)][7:10].sum() for b in range(6) if (p, b) in c) for p in ("EP", "MP", "CO", "BTN", "SB")}
for bk in range(6):
    num = np.zeros(3); w = 0; n = 0
    for p in posw:
        v = c.get((p, bk))
        if v is None or v[7:10].sum() < 200: continue
        num += posw[p] * v[7:10] / v[7:10].sum(); w += posw[p]; n += v[7:10].sum()
    if w: print(f"  {OL[bk]:10s} n={int(n):8d} fold {100 * num[0] / w:5.1f} call {100 * num[1] / w:5.1f} 3bet {100 * num[2] / w:5.1f}")
