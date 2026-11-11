"""General tuner testbed. Same fitness for all algorithms: mean over (field, points table) of score / fair share."""
import json, math, os, random, sys, time
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import play_table, points_for
from field import ARCHETYPES, FIELDS
from run import PAYOUTS, make

BLEND_FIELDS = ["typical", "strong", "aggro", "all_mirror", "mirror"]
ALLP = ["top3", "steep", "linear", "wta"]
BASE_SEARCH = {
    "open_a": (0.02, 0.2), "open_b": (0.1, 0.8), "hu_open": (0.3, 1.0), "hu_jam": (0.3, 1.0), "sh_widen": (0.0, 5.0), "sh_range": (0.0, 2.0), "jam_scale": (0.4, 1.3),
    "call_open": (0.03, 0.25), "threebet": (0.015, 0.12), "fourbet": (0.01, 0.06), "open_size": (2.0, 4.0), "threebet_mult": (2.5, 4.0), "steal_fold_bonus": (0.0, 0.8),
    "jam_m": (5.0, 25.0), "jam_slope": (0.0, 0.2), "call_jam": (0.03, 0.25), "call_jam_short": (0.0, 0.05), "range_unraised": (0.3, 1.0), "range_bet": (0.1, 0.6),
    "range_raise": (0.03, 0.3), "value_eq": (0.55, 0.85), "bluff_freq": (0.0, 0.5), "bet_frac": (0.33, 1.2), "call_margin": (-0.03, 0.15), "raise_eq": (0.7, 0.95),
    "commit_spr": (0.5, 3.0), "icm_margin": (0.0, 0.15),
}


def _eval(a):
    """Returns mean normalised score of one candidate. Same seed means the same tables and seats for all candidates."""
    spec, fields, payouts, tables, seed = a
    rng = random.Random(seed)
    random.seed(seed)
    tot = 0.0
    for f in fields:
        names = list(FIELDS[f]); w = [FIELDS[f][k] for k in names]
        for _ in range(tables):
            seats = rng.choices(names, w, k=7)
            bots = [ARCHETYPES[s]() for s in seats]
            pos = rng.randrange(8)
            bots.insert(pos, make(spec))
            e, nh, s = play_table(bots)
            for p in payouts:
                tot += points_for(e, s, PAYOUTS[p])[pos] / (sum(PAYOUTS[p]) / 8.0)
    return tot / (tables * len(fields) * len(payouts))


class Box:
    """Maps [0,1]^d to parameter dicts."""
    def __init__(self, search, fixed):
        self.keys = list(search); self.lo = np.array([search[k][0] for k in self.keys]); self.hi = np.array([search[k][1] for k in self.keys]); self.fixed = fixed

    def enc(self, d):
        return np.clip((np.array([d.get(k, 0.0) for k in self.keys]) - self.lo) / (self.hi - self.lo), 0, 1)

    def dec(self, x):
        d = dict(self.fixed)
        v = self.lo + np.clip(x, 0, 1) * (self.hi - self.lo)
        d.update({k: float(a) for k, a in zip(self.keys, v)})
        return d


class Ctx:
    def __init__(self, box, fields, payouts, procs, seed):
        self.box, self.fields, self.payouts, self.rng = box, fields, payouts, np.random.default_rng(seed)
        self.pool = Pool(procs); self.used = 0; self.t0 = time.time(); self.log = []

    def batch(self, xs, tables):
        s = int(self.rng.integers(1 << 30))
        r = self.pool.map(_eval, [(self.box.dec(x), self.fields, self.payouts, tables, s) for x in xs], chunksize=1)
        self.used += len(xs) * tables * len(self.fields)
        return np.array(r)

    def mark(self, x):
        self.log.append((self.used, round(time.time() - self.t0, 1), self.box.dec(x)))


def t_cem(c, x0, budget, sig0=0.25, pop=30, elite=6, tables=30):
    mu, sig = x0.copy(), np.full_like(x0, sig0)
    while c.used < budget:
        xs = [mu.copy()] + [np.clip(mu + c.rng.normal(size=mu.size) * sig, 0, 1) for _ in range(pop - 1)]
        r = c.batch(xs, tables)
        e = np.array([xs[i] for i in np.argsort(-r)[:elite]])
        mu = 0.7 * e.mean(0) + 0.3 * mu
        sig = np.maximum(0.03, 0.8 * e.std(0) + 0.2 * sig)
        c.mark(mu)
    return mu


def t_cma(c, x0, budget, sig0=0.2, tables=30):
    n = x0.size; lam = 4 + int(3 * math.log(n)); lam = max(lam, 14); mu_n = lam // 2
    w = np.log(mu_n + 0.5) - np.log(np.arange(1, mu_n + 1)); w /= w.sum(); me = 1 / (w ** 2).sum()
    cc, cs = (4 + me / n) / (n + 4 + 2 * me / n), (me + 2) / (n + me + 5)
    c1 = 2 / ((n + 1.3) ** 2 + me); cm = min(1 - c1, 2 * (me - 2 + 1 / me) / ((n + 2) ** 2 + me))
    ds = 1 + 2 * max(0, math.sqrt((me - 1) / (n + 1)) - 1) + cs; chi = math.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n * n))
    m, s, C, pc, ps = x0.copy(), sig0, np.eye(n), np.zeros(n), np.zeros(n)
    while c.used < budget:
        D, B = np.linalg.eigh(C); D = np.sqrt(np.maximum(D, 1e-12))
        zs = c.rng.normal(size=(lam, n)); ys = zs * D @ B.T
        xs = [np.clip(m + s * y, 0, 1) for y in ys]
        r = c.batch(xs, tables)
        o = np.argsort(-r)[:mu_n]
        yw = (ys[o] * w[:, None]).sum(0); m = np.clip(m + s * yw, 0, 1)
        ps = (1 - cs) * ps + math.sqrt(cs * (2 - cs) * me) * (B @ ((B.T @ yw) / D))
        hs = np.linalg.norm(ps) / math.sqrt(1 - (1 - cs) ** (2 * (c.used + 1))) < (1.4 + 2 / (n + 1)) * chi
        pc = (1 - cc) * pc + hs * math.sqrt(cc * (2 - cc) * me) * yw
        C = (1 - c1 - cm) * C + c1 * np.outer(pc, pc) + cm * (ys[o].T * w) @ ys[o]
        s *= math.exp((cs / ds) * (np.linalg.norm(ps) / chi - 1)); s = min(s, 0.4)
        c.mark(m)
    return m


def t_paired(c, x0, budget, sigma=0.1, lam=10, tables=30):
    """(1+lambda) with a two-stage acceptance on fresh tables, like the public repo's method."""
    x = x0.copy()
    while c.used < budget:
        xs = [x.copy()] + [np.clip(x + c.rng.normal(size=x.size) * sigma, 0, 1) for _ in range(lam)]
        r = c.batch(xs, tables)
        i = int(np.argmax(r))
        if i != 0:
            r2 = c.batch([x, xs[i]], tables * 3)
            if r2[1] > r2[0]:
                x = xs[i]; sigma = min(0.2, sigma * 1.1)
            else:
                sigma = max(0.03, sigma * 0.9)
        c.mark(x)
    return x


def t_spsa(c, x0, budget, a=0.05, ch=0.12, tables=60):
    x, k = x0.copy(), 1
    while c.used < budget:
        d = c.rng.choice([-1.0, 1.0], size=x.size)
        ck = ch / k ** 0.101
        r = c.batch([np.clip(x + ck * d, 0, 1), np.clip(x - ck * d, 0, 1)], tables)
        g = (r[0] - r[1]) / (2 * ck) * d
        x = np.clip(x + (a / (k + 5) ** 0.3) * g * 8, 0, 1)
        k += 1
        if k % 5 == 0:
            c.mark(x)
    return x


def t_halving(c, x0, budget, sigma=0.2, n=27, tables=8):
    """Successive halving: many candidates on few tables, the survivors on many; restart around the winner."""
    x = x0.copy()
    while c.used < budget:
        xs = [x.copy()] + [np.clip(x + c.rng.normal(size=x.size) * sigma, 0, 1) for _ in range(n - 1)]
        t = tables
        while len(xs) > 1:
            r = c.batch(xs, t)
            xs = [xs[i] for i in np.argsort(-r)[: max(1, len(xs) // 3)]]
            t *= 3
        x = xs[0]; sigma = max(0.04, sigma * 0.85)
        c.mark(x)
    return x


TUNERS = {"cem": t_cem, "cma": t_cma, "paired": t_paired, "spsa": t_spsa, "halving": t_halving}


def tune(name, spec_cls, search, start, budget, seed=1, fields=BLEND_FIELDS, payouts=ALLP, procs=10, **kw):
    fixed = dict(start)
    if spec_cls:
        fixed["cls"] = spec_cls
    box = Box(search, fixed)
    c = Ctx(box, fields, payouts, procs, seed)
    x = TUNERS[name](c, box.enc(start), budget, **kw)
    c.pool.close()
    return box.dec(x), c.log, c.used, time.time() - c.t0
