import os, pickle, numpy as np, scipy.sparse as sp
D = os.path.dirname(os.path.abspath(__file__))
NS = (5, 10, 20, 40, 80, 10**6); NLAB = ("5", "10", "20", "40", "80", "all")
AV = 2

class Round:
    def __init__(self, k):
        d = pickle.load(open(os.path.join(D, f"R{k}.pkl"), "rb"))
        self.d = d; self.TOP = d["TOP"]
        self.inv = {v: n for n, v in d["F"].items()}
        rows = d["rows"]
        self.team = np.array([r[2] for r in rows]); self.nh = np.array([r[3] for r in rows])
        self.table = np.array([r[0] * 100000 + r[1] for r in rows])
        lens = np.array([len(r[4]) for r in rows])
        self.off = np.concatenate([[0], np.cumsum(lens)])
        tok = np.concatenate([r[4] for r in rows]).astype(np.int64)
        self.fidl = tok // 4096; self.val = tok % 4096
        self.hid = np.concatenate([r[5] for r in rows]).astype(np.int32)
        self.seat = np.repeat(np.arange(len(rows)), lens)
        self.n = len(rows)
        del d["rows"]

class Vocab:
    """global feature names -> gid; token col = (gid, val)"""
    def __init__(self, rounds):
        names = sorted(set(n for R in rounds for n in R.d["F"]))
        self.names = names; self.gid = {n: i for i, n in enumerate(names)}
        self.fam = np.array([n.split()[0] for n in names])
        for R in rounds:
            mp = np.zeros(max(R.inv) + 1, dtype=np.int64)
            for v, n in R.inv.items(): mp[v] = self.gid[n]
            R.g = mp[R.fidl]
        self.nf = len(names)
    def key(self, g, val): return g * 4096 + val

def counts(g, val, lab, nlab, V):
    """dense [nlab, nf, 256]-ish via sparse: returns dict-free csr [nlab, nf*4096]"""
    m = lab >= 0
    return sp.csr_matrix((np.ones(m.sum()), (lab[m], g[m] * 4096 + val[m])), shape=(nlab, V.nf * 4096))

def log_profiles(C, V, alpha=10.0, beta=0.05):
    """C csr [L, nf*4096] -> dense log P over observed columns only. returns (cols, LP[L, ncols])"""
    C = C.tocsc()
    cols = np.unique(C.indices) if False else np.flatnonzero(np.diff(C.indptr) > 0)
    Cd = C[:, cols].toarray()
    f = cols // 4096
    G = Cd.sum(0)
    nval = np.bincount(f, minlength=V.nf).astype(float) + 1
    Gf = np.bincount(f, weights=G, minlength=V.nf)
    g = (G + beta) / (Gf[f] + beta * nval[f])
    Cf = np.zeros((Cd.shape[0], V.nf))
    for i in range(Cd.shape[0]): Cf[i] = np.bincount(f, weights=Cd[i], minlength=V.nf)
    LP = np.log((Cd + alpha * g[None, :]) / (Cf[:, f] + alpha))
    # unseen column: log(alpha*g_unseen/(Cf+alpha)) with g_unseen = beta/(Gf+beta*nval)
    LU = np.log(alpha * (beta / (Gf + beta * nval))[None, :] / (Cf + alpha))  # [L, nf]
    return cols, LP, LU

def score(g, val, seat, nseat, cols, LP, LU, mask):
    """sum log-lik per seat for tokens in mask. returns S[nseat, L]"""
    key = g[mask] * 4096 + val[mask]
    pos = np.searchsorted(cols, key); pos[pos >= len(cols)] = 0
    hit = cols[pos] == key
    L = LP.shape[0]
    S = np.zeros((nseat, L))
    st = seat[mask]
    for l in range(L):
        w = np.where(hit, LP[l, pos], LU[l, g[mask]])
        S[:, l] = np.bincount(st, weights=w, minlength=nseat)
    return S
