import sys, numpy as np
sys.path.insert(0, '.')
from recog import *
rg = np.random.default_rng(3)
isSZ = V.fam == "SZ"
isopen = np.array([n.startswith("SZ open") for n in names]); isbet = np.array([n.startswith("SZ bet") for n in names]); is3b = names == "SZ 3b"
isgran = np.array([n.startswith("SZ gran") for n in names])
def jitter(Rk, step=1):
    val = Rk.val.copy(); m = (Rk.tteam == AV) & (isopen | isbet | is3b)[Rk.g]
    val[m] = val[m] + rg.integers(-step, step + 1, m.sum())
    return val
def coarse(Rk, val):
    v = val.copy(); g = Rk.g
    m = isopen[g]; v[m] = np.round(v[m] / 5)       # 0.25 bb
    m = isbet[g]; v[m] = np.round(v[m] / 4)        # 0.1 pot
    m = is3b[g]; v[m] = np.round(v[m] / 3)         # 0.3x
    return v
famC = FAMS["ALL"] & ~isgran   # coarse recogniser also drops chip-rounding features
def run(label, fam, mk_tr, mk_te):
    acc = {N: [] for N in (10, 20, 40, 10**6)}; mac = {N: [] for N in acc}
    for k in range(1, 6):
        S = evalpair(R[k], R[k + 1], fam, vtr=mk_tr(R[k]), vte=mk_te(R[k + 1]), Ns=tuple(acc))
        tm = R[k + 1].team
        for N in acc:
            pred = S[N].argmax(1); acc[N].append(np.mean(pred[tm == AV] == AV)); mac[N].append(np.mean([np.mean(pred[tm == t] == t) for t in range(L)]))
    print(f"{label:78s} avalon found @10/20/40/all: " + " ".join(f"{100 * np.mean(acc[N]):5.1f}" for N in acc) + " | macro 20 teams: " + " ".join(f"{100 * np.mean(mac[N]):5.1f}" for N in acc), flush=True)
real = lambda Rk: Rk.val
run("exact-size recogniser, no jitter", FAMS["ALL"], real, real)
run("exact-size recogniser, we jitter +-1 step, first round", FAMS["ALL"], real, lambda Rk: jitter(Rk))
run("coarse-bin recogniser (0.25bb / 0.1 pot, no chip-rounding), no jitter", famC, lambda Rk: coarse(Rk, Rk.val), lambda Rk: coarse(Rk, Rk.val))
run("coarse-bin recogniser, we jitter +-1 step (0.05bb / 2.5% pot), first round", famC, lambda Rk: coarse(Rk, Rk.val), lambda Rk: coarse(Rk, jitter(Rk)))
run("coarse-bin recogniser, we jitter +-3 steps (0.15bb / 7.5% pot), first round", famC, lambda Rk: coarse(Rk, Rk.val), lambda Rk: coarse(Rk, jitter(Rk, 3)))
run("coarse-bin recogniser, we jitter +-3 steps, later rounds", famC, lambda Rk: coarse(Rk, jitter(Rk, 3)), lambda Rk: coarse(Rk, jitter(Rk, 3)))
