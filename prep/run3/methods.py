"""Alternative policy families, all built on the same preflop table, lookup equity and engine."""
import json, math, os, random
from hero import Hero, DEFAULT, FOLD, CALL
from pk import pct
from strength import HeroTable

R = random.random


# ---- 1. Contextual thresholds: postflop thresholds vary by street and heads-up vs. multiway. ----
CTX_NAMES = ["value_eq", "call_margin", "raise_eq", "bet_frac"]


class HeroCtx(HeroTable):
    def __init__(self, **kw):
        super().__init__(**kw)
        base = self.p
        self.ctx = {}
        for st in (1, 2, 3):
            for hu in (0, 1):
                d = dict(base)
                for n in CTX_NAMES:
                    d[n] = base[n] + base.get(f"d_{n}_{st}{hu}", 0.0)
                self.ctx[(st, hu)] = d

    def postflop(self, o):
        keep = self.p
        self.p = self.ctx[(o.street, 1 if o.n_live == 2 else 0)]
        r = super().postflop(o)
        self.p = keep
        return r


def ctx_search():
    s = {}
    for st in (1, 2, 3):
        for hu in (0, 1):
            s[f"d_value_eq_{st}{hu}"] = (-0.15, 0.15)
            s[f"d_call_margin_{st}{hu}"] = (-0.12, 0.12)
            s[f"d_raise_eq_{st}{hu}"] = (-0.12, 0.1)
            s[f"d_bet_frac_{st}{hu}"] = (-0.4, 0.6)
    return s


# ---- 2. Explicit EV: choose the postflop action with the best risk-adjusted value, per-seat fold rates. ----
EV_DEFAULT = {"f0": 0.45, "fk": 0.35, "calldown": 0.6, "lam": 0.2, "lam4": 0.25, "real": 0.85, "ev_margin": 0.0}


class HeroEV(HeroTable):
    def __init__(self, **kw):
        d = dict(EV_DEFAULT)
        d.update(kw)
        super().__init__(**d)
        self.faced, self.folds, self.pending = {}, {}, set()

    def observe(self, seat, street, kind, amount):
        super().observe(seat, street, kind, amount)
        if street > 0:
            if seat in self.pending and kind != 2:
                self.pending.discard(seat)
                self.faced[seat] = self.faced.get(seat, 0) + 1
                if kind == 0:
                    self.folds[seat] = self.folds.get(seat, 0) + 1
            if kind == 2:
                self.pending = set(range(8)) - {seat}

    def end_hand(self, n):
        super().end_hand(n)
        self.pending = set()

    def _f(self, s, ratio):
        p = self.p
        base = (self.folds.get(s, 0) + p["f0"] * 8.0) / (self.faced.get(s, 0) + 8.0)
        return min(0.95, base * ratio ** p["fk"])

    def postflop(self, o):
        p = self.p
        if o.aggressor >= 0 and o.to_call > 0:
            base = (p["range_raise"] if o.raises >= 2 else p["range_bet"]) * max(0.7, min(2.2, self._vpip(o.aggressor) / 0.3))
        else:
            base = p["range_unraised"]
        base = min(1.0, base * (1.0 + p["sh_range"] * (8 - o.n_alive) / 6.0))
        opp = max(1, o.n_live - 1)
        ex = 1 + 0.65 * (min(opp, 4) - 1)
        eq = self.eq(o.hole, o.board, base) ** ex
        eqc = self.eq(o.hole, o.board, max(0.03, base * p["calldown"])) ** ex
        lam = p["lam"] + (p["lam4"] if o.n_alive <= 4 else 0.0)
        pot = float(max(1, o.pot))
        best, act = (eq * pot * p["real"] if o.to_call == 0 else -1e-9 + 0.0), (CALL if o.to_call == 0 else FOLD)
        if o.to_call > 0:
            ev = eq * pot - (1 + lam) * (1 - eq) * o.to_call - p["ev_margin"] * o.to_call
            if ev > best:
                best, act = ev, CALL
        if o.can_raise:
            others = [s for s in range(len(o.stacks)) if s != o.seat and o.in_hand[s] and o.stacks[s] > 0]
            for to in (o.cur + 0.5 * pot, o.cur + pot, o.max_raise_to):
                to = max(o.min_raise_to, min(to, o.max_raise_to))
                add = to - o.bet
                f = 1.0
                for s in others:
                    f *= self._f(s, (to - o.cur) / pot)
                called = add - o.to_call
                ev = f * pot + (1 - f) * (eqc * (pot + called) - (1 + lam) * (1 - eqc) * add) - p["ev_margin"] * add
                if ev > best:
                    best, act = ev, (2, to)
        return act


EV_SEARCH = {"f0": (0.1, 0.8), "fk": (0.0, 1.0), "calldown": (0.2, 1.0), "lam": (0.0, 1.0), "lam4": (0.0, 1.0), "real": (0.4, 1.1), "ev_margin": (0.0, 0.3)}


# ---- 3. Small linear policy over features; optionally a residual on top of the rule. ----
N_FEAT = 14


def features(self, o):
    hp = pct(o.hole)
    if o.street == 0:
        s = 1.0 - hp
    else:
        s = self.eq(o.hole, o.board, 0.4) ** (1 + 0.65 * (min(max(1, o.n_live - 1), 4) - 1))
    pot = float(max(1, o.pot))
    odds = o.to_call / (pot + o.to_call) if o.to_call else 0.0
    stack = float(max(1, o.stack))
    m = math.log(max(1.0, (o.stack + o.bet) / float(o.sb + o.bb))) / 4.0
    ag = self._vpip(o.aggressor) if o.aggressor >= 0 else 0.3
    return [1.0, s, odds, min(2.0, o.to_call / stack), m, min(5.0, stack / pot) / 5.0, o.n_live / 8.0, o.n_alive / 8.0, o.n_behind / 8.0,
            1.0 if o.street == 1 else 0.0, 1.0 if o.street == 2 else 0.0, 1.0 if o.street == 3 else 0.0, ag, min(o.raises, 3) / 3.0]


def _action(o, i):
    pot = float(max(1, o.pot))
    if i == 0:
        return CALL if o.to_call == 0 else FOLD
    if i == 1 or not o.can_raise:
        return CALL
    if i == 2:
        return (2, o.cur + max(0.5 * pot, 1))
    if i == 3:
        return (2, o.cur + pot)
    return (2, o.max_raise_to)


def _index(o, a):
    if a[0] == 0:
        return 0
    if a[0] == 1:
        return 1
    if a[1] >= o.max_raise_to:
        return 4
    return 2 if a[1] - o.cur <= 0.75 * max(1, o.pot) else 3


class HeroLinear(HeroTable):
    """rule_bonus > 0: the rule's action gets a bonus, so all-zero weights reproduce the rule exactly."""
    rule_bonus = 1.0

    def __init__(self, **kw):
        w = kw.pop("W", None)
        extra = {k: kw.pop(k) for k in list(kw) if k.startswith("w_")}
        super().__init__(**kw)
        self.W = [[extra.get(f"w_{i}_{j}", 0.0) for j in range(N_FEAT)] for i in range(5)]

    def act(self, o):
        x = features(self, o)
        rule = super().act(o) if self.rule_bonus else None
        ri = _index(o, rule) if rule else -1
        best, bi = -1e18, 1
        for i in range(5):
            if i >= 2 and not o.can_raise:
                continue
            if i == 0 and o.to_call == 0:
                continue
            v = sum(a * b for a, b in zip(self.W[i], x)) + (self.rule_bonus if i == ri else 0.0)
            if v > best:
                best, bi = v, i
        if bi == ri:
            return rule
        return _action(o, bi)


class HeroLinearScratch(HeroLinear):
    rule_bonus = 0.0


def linear_search(limit):
    return {f"w_{i}_{j}": (-limit, limit) for i in range(5) for j in range(N_FEAT)}


# ---- 4. Tabular Q overrides learned from self-play hand results, falling back to the rule. ----
def q_key(self, o):
    if o.street == 0:
        s = min(9, int(pct(o.hole) * 10))
    else:
        e = self.eq(o.hole, o.board, 0.4) ** (1 + 0.65 * (min(max(1, o.n_live - 1), 4) - 1))
        s = min(9, int(e * 10))
    pot = float(max(1, o.pot))
    if o.to_call == 0:
        fc = 0
    elif o.to_call >= 0.5 * max(1, o.stack):
        fc = 4
    else:
        r = o.to_call / pot
        fc = 1 if r < 0.33 else 2 if r < 0.8 else 3
    m = (o.stack + o.bet) / float(o.sb + o.bb)
    mb = 0 if m < 4 else 1 if m < 8 else 2 if m < 15 else 3 if m < 30 else 4
    nl = 0 if o.n_live == 2 else 1 if o.n_live == 3 else 2
    bh = 0 if o.n_behind == 0 else 1 if o.n_behind <= 2 else 2
    return f"{o.street}{s}{fc}{mb}{nl}{bh}"


_QCACHE = {}


def _loadq(path):
    q = _QCACHE.get(path)
    if q is None:
        q = _QCACHE[path] = json.load(open(path))
    return q


class HeroQ(HeroTable):
    """Q[key] = list of 5 [mean_reward, count]. Overrides the rule only with enough evidence."""
    def __init__(self, qfile=None, eps=0.0, nmin=200, delta=0.05, collect=False, **kw):
        super().__init__(**kw)
        self.Q = _loadq(qfile) if qfile else {}
        self.eps, self.nmin, self.delta, self.collect = eps, nmin, delta, collect
        self.rec, self.seat = [], -1
        self.out = {}

    def act(self, o):
        rule = super().act(o)
        k = q_key(self, o)
        ri = _index(o, rule)
        i = ri
        q = self.Q.get(k)
        if q and q[ri][1] >= self.nmin:
            best = q[ri][0] + self.delta
            for j in range(5):
                if j >= 2 and not o.can_raise:
                    continue
                if j == 0 and o.to_call == 0:
                    continue
                if q[j][1] >= self.nmin and q[j][0] > best:
                    best, i = q[j][0], j
        if self.eps and R() < self.eps:
            i = random.randrange(5)
            if i == 0 and o.to_call == 0:
                i = 1
            if i >= 2 and not o.can_raise:
                i = 1
        if self.collect:
            self.seat = o.seat
            self.rec.append((k, i))
        return rule if i == ri else _action(o, i)

    def hand_result(self, stacks, start):
        if not self.rec:
            return
        u = lambda s: 100.0 * (s / 16000.0) ** 0.7
        r = u(stacks[self.seat]) - u(start[self.seat])
        for k, i in self.rec:
            row = self.out.setdefault(k, [[0.0, 0] for _ in range(5)])
            row[i][0] += r
            row[i][1] += 1
        self.rec = []


# ---- 5. Portfolio: switch between two tuned parameter sets from how tough the table looks. ----
class HeroSwitch(HeroTable):
    def __init__(self, weak=None, tough=None, band=(0.18, 0.5), frac=0.6, after=15, **kw):
        super().__init__(**(weak or {}))
        self.pw, self.pt = self.p, dict(self.p)
        self.pt.update(tough or {})
        self.band, self.frac, self.after = band, frac, after

    def act(self, o):
        seats = [s for s in range(len(o.stacks)) if s != o.seat and o.stacks[s] + o.bets[s] > 0 and self.hands.get(s, 0) >= self.after]
        tough = False
        if len(seats) >= 2:
            lo, hi = self.band
            n = sum(1 for s in seats if lo <= self.vpip.get(s, 0) / max(1, self.hands.get(s, 1)) <= hi)
            tough = n >= self.frac * len(seats)
        self.p = self.pt if tough else self.pw
        return super().act(o)


CLASSES = {"ctx": HeroCtx, "ev": HeroEV, "linear": HeroLinear, "linear0": HeroLinearScratch, "q": HeroQ, "switch": HeroSwitch}
