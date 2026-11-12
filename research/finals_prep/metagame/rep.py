"""helpers: R(name) -> result; ms(name) -> (mean, se, n); pd(a, b) -> paired diff a-b (mean, se); style(name)"""
import os, pickle, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import fitlib
_C = {}


def R(name):
    if name not in _C:
        _C[name] = pickle.load(open(os.path.join(HERE, "out", name + ".pkl"), "rb"))
    return _C[name]


def have(name):
    return os.path.exists(os.path.join(HERE, "out", name + ".pkl"))


def _ms(xs):
    n = len(xs)
    m = sum(xs) / n
    return m, (sum((x - m) ** 2 for x in xs) / (n - 1) / n) ** 0.5, n


def ms(name):
    return _ms([r[2] for r in R(name)["rows"]])


def pd(a, b):
    B = {r[0]: r[2] for r in R(b)["rows"]}
    return _ms([r[2] - B[r[0]] for r in R(a)["rows"] if r[0] in B])


def style(name, who="HERO"):
    return fitlib.style(R(name)["acc"], who)


def tourney(name):
    d = {}
    for it, e, p in R(name)["rows"]:
        d.setdefault(e, []).append(p)
    return {e: _ms(v) for e, v in d.items()}
