import sys, numpy as np, collections, json
sys.path.insert(0, '.')
from lib import *
R = {k: Round(k) for k in range(1, 7)}; V = Vocab(R.values()); TOP = R[1].TOP
print("seats per team per round:", {k: int(np.median(np.bincount(R[k].team, minlength=20)[[i for i in range(20) if i != 2]])) for k in R})
def dist(Rk, team, name_prefix):
    gs = [i for i, n in enumerate(V.names) if n.startswith(name_prefix)]
    m = np.isin(Rk.g, gs) & (Rk.team[Rk.seat] == team)
    return collections.Counter(Rk.val[m].tolist())
def top(c, scale, k=3):
    n = sum(c.values()) or 1
    return " ".join(f"{v/scale:g}:{100*x/n:.0f}%" for v, x in c.most_common(k)), n
out = {}
for pref, scale in (("SZ open", 20), ("SZ bet s1", 40), ("SZ bet s2", 40), ("SZ bet s3", 40), ("SZ 3b", 10), ("SZ gran pre", 1), ("SZ gran post", 1)):
    print("\n==", pref, "(top values : share) per round; entropy bits in R6")
    for ti, t in enumerate(TOP):
        line = []
        for k in (1, 3, 6):
            s, n = top(dist(R[k], ti, pref), scale)
            line.append(f"R{k}[{s}]")
        c = dist(R[6], ti, pref); p = np.array(list(c.values())) / max(1, sum(c.values())); H = -(p * np.log2(p)).sum()
        out[(pref, t)] = (c.most_common(1)[0][0] / scale if c else None, float(H), len(c))
        print(f"{t:20s} H={H:4.2f} nd={len(c):3d} " + "  ".join(line))
