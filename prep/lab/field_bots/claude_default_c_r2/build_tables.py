"""Offline generator for tables.json (run once; agent.py only reads the JSON).

Tables:
  classes     169 hand classes ("AA", "AKs", "AKo", ...)
  eq1         equity vs one random hand
  eq3         equity vs three random hands (share of pot)
  shove_order class indices sorted by eq1 (strongest first)  -> "top p%" ranges
  open_order  class indices sorted by a blend of eq1 and eq3 -> opening / playability ranking
  grid        list of range widths p (fraction of 1326 combos)
  eq_top      eq_top[h][b] = equity of class h vs the top grid[b] of shove_order
"""
import json, os, random, sys, time
import eval7

R = "23456789TJQKA"
S = "shdc"
random.seed(12345)

def classes():
    out = []
    for i in range(12, -1, -1):
        for j in range(12, -1, -1):
            if i == j:
                out.append(R[i] + R[j])
            elif i > j:
                out.append(R[i] + R[j] + "s")
                out.append(R[i] + R[j] + "o")
    return out

CL = classes()
IDX = {c: k for k, c in enumerate(CL)}

def combos_of(label):
    a, b = label[0], label[1]
    if len(label) == 2:
        return [(a + S[x], b + S[y]) for x in range(4) for y in range(x + 1, 4)]
    if label[2] == "s":
        return [(a + s, b + s) for s in S]
    return [(a + x, b + y) for x in S for y in S if x != y]

def rep(label):
    a, b = label[0], label[1]
    if len(label) == 2:
        return (a + "s", b + "h")
    if label[2] == "s":
        return (a + "s", b + "s")
    return (a + "s", b + "h")

def main():
    t0 = time.time()
    deck = [eval7.Card(r + s) for r in R for s in S]
    allc = []
    for i in range(52):
        for j in range(i + 1, 52):
            allc.append(((deck[i], deck[j]), 1.0))
    random.shuffle(allc)
    # eq1 via eval7 MC vs the full range
    eq1 = []
    for c in CL:
        h = [eval7.Card(x) for x in rep(c)]
        e = eval7.py_hand_vs_range_monte_carlo(h, allc, [], 60000)
        eq1.append(round(float(e), 4))
    print("eq1 done", time.time() - t0, file=sys.stderr)
    # eq3 via python MC
    ev = eval7.evaluate
    eq3 = []
    N3 = 6000
    for c in CL:
        h = [eval7.Card(x) for x in rep(c)]
        rest = [d for d in deck if d not in h]
        tot = 0.0
        for _ in range(N3):
            smp = random.sample(rest, 11)
            board = smp[:5]
            mine = ev(h + board)
            best = 0
            ties = 1
            win = True
            for k in range(3):
                v = ev([smp[5 + 2 * k], smp[6 + 2 * k]] + board)
                if v > mine:
                    win = False
                    break
                if v == mine:
                    ties += 1
            if win:
                tot += 1.0 / ties
        eq3.append(round(tot / N3, 4))
    print("eq3 done", time.time() - t0, file=sys.stderr)
    shove_order = sorted(range(169), key=lambda k: -eq1[k])
    # normalise each metric to its rank percentile and blend
    def z(v):
        m = sum(v) / len(v)
        sd = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5
        return [(x - m) / sd for x in v]
    z1, z3 = z(eq1), z(eq3)
    blend = [0.55 * z1[k] + 0.45 * z3[k] for k in range(169)]
    open_order = sorted(range(169), key=lambda k: -blend[k])
    grid = [0.02, 0.03, 0.045, 0.06, 0.08, 0.10, 0.125, 0.15, 0.18, 0.21, 0.25, 0.30, 0.35, 0.40, 0.47, 0.55, 0.65, 0.77, 0.90, 1.0]
    ncomb = [len(combos_of(c)) for c in CL]
    # top-p combo lists by shove order
    eq_top = [[0.0] * len(grid) for _ in range(169)]
    for b, p in enumerate(grid):
        target = p * 1326
        rng = []
        cum = 0
        for k in shove_order:
            if cum >= target - 1e-9:
                break
            cs = combos_of(CL[k])
            take = cs if cum + len(cs) <= target + 3 else cs[: max(1, int(round(target - cum)))]
            rng.extend(take)
            cum += len(take)
        rr = [((eval7.Card(a), eval7.Card(bb)), 1.0) for a, bb in rng]
        random.shuffle(rr)
        it = max(20000, 12 * len(rr))
        for k in range(169):
            h = [eval7.Card(x) for x in rep(CL[k])]
            eq_top[k][b] = round(float(eval7.py_hand_vs_range_monte_carlo(h, rr, [], it)), 4)
        print("grid", p, len(rr), time.time() - t0, file=sys.stderr)
    out = dict(classes=CL, ncomb=ncomb, eq1=eq1, eq3=eq3, shove_order=shove_order, open_order=open_order,
               grid=grid, eq_top=eq_top)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables.json")
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("wrote", path, time.time() - t0, file=sys.stderr)
    print("shove top 30:", [CL[k] for k in shove_order[:30]])
    print("open top 40:", [CL[k] for k in open_order[:40]])
    print("open 40-80:", [CL[k] for k in open_order[40:80]])

if __name__ == "__main__":
    main()
