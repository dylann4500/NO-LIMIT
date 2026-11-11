"""Archetype opponents for dev/sim.py: rough imitations of what 60-minute AI-built bots tend to look like."""
import json, os, random
import eval7
from poker_agent_sdk import Action, ActionKind

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(os.path.dirname(HERE), "preflop.json")))
CL = {c: i for i, c in enumerate(D["classes"])}
NC = D["combos"]
HU = D["hu"]
VR = [sum(HU[i][j] * NC[j] for j in range(169)) / 1326.0 for i in range(169)]
ORDER = sorted(range(169), key=lambda i: -VR[i])
PCT = [0.0] * 169
acc = 0
for i in ORDER:
    PCT[i] = (acc + NC[i] / 2) / 1326.0
    acc += NC[i]
RV = {r: i for i, r in enumerate("23456789TJQKA")}
EC = {r + s: eval7.Card(r + s) for r in "23456789TJQKA" for s in "shdc"}
ALL = []
for a in EC:
    for b in EC:
        if a < b:
            ALL.append(((EC[a], EC[b]), 1.0))
random.Random(5).shuffle(ALL)
ALL = ALL[:300]


def pct_of(cards):
    a, b = cards
    r1, r2 = a[0], b[0]
    if RV[r1] < RV[r2]:
        r1, r2 = r2, r1
    name = r1 + r2 if r1 == r2 else r1 + r2 + ("s" if a[1] == b[1] else "o")
    return PCT[CL[name]]


def legal(state):
    return {la.kind: la for la in state.legal_actions}


def do_raise(L, total):
    la = L.get(ActionKind.RAISE)
    if la is None:
        return Action.call() if ActionKind.CALL in L else Action.check()
    t = int(max(la.min_amount, min(la.max_amount, total)))
    return Action.raise_to(t)


def passive(L):
    return Action.check() if ActionKind.CHECK in L else Action.fold()


def callchk(L):
    return Action.call() if ActionKind.CALL in L else Action.check()


def equity(state, nopp):
    hc = [EC[c] for c in state.cards]
    bc = [EC[c] for c in state.board]
    e = eval7.py_hand_vs_range_monte_carlo(hc, ALL, bc, 300)
    return e ** (1 + 0.8 * (max(1, nopp) - 1))


class Base:
    # parameters
    open_pct = 0.18
    late_open = 0.30
    call_pct = 0.12
    threebet_pct = 0.04
    push_bb = 10
    push_pct = 0.25
    callshove_pct = 0.10
    bet_eq = 0.62
    raise_eq = 0.85
    call_margin = 0.0
    cbet_freq = 0.0
    open_size = 3.0
    bet_frac = 0.66
    flaky = 0.0

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def act(self, state, memory):
        L = legal(state)
        if self.flaky and self.rng.random() < self.flaky:
            # simulates a timed-out decision: platform fallback
            return (Action.check() if ActionKind.CHECK in L else Action.fold()), memory
        try:
            if not state.board:
                a = self.pre(state, L)
            else:
                a = self.post(state, L)
        except Exception:
            a = passive(L)
        return a, memory

    def info(self, state):
        me = [s for s in state.seats if s.seat == state.seat][0]
        opps = [s for s in state.seats if s.seat != state.seat and s.status in ("active", "all_in")]
        bb = state.blinds[1]
        eff = min(me.stack + me.bet, max([o.stack + o.bet for o in opps] or [0]))
        return me, opps, bb, eff / bb

    def pre(self, state, L):
        me, opps, bb, effbb = self.info(state)
        p = pct_of(state.cards)
        raises = [e for e in state.history if e.kind == "raise"]
        late = state.seat == state.button or len(opps) <= 3
        if effbb <= self.push_bb:
            if not raises:
                if p <= self.push_pct * (1.5 if late else 1.0):
                    return do_raise(L, me.stack + me.bet)
                return passive(L)
            if p <= self.callshove_pct:
                return do_raise(L, me.stack + me.bet) if p < 0.05 else callchk(L)
            return passive(L)
        if not raises:
            op = self.late_open if late else self.open_pct
            if p <= op:
                return do_raise(L, self.open_size * bb)
            if ActionKind.CHECK in L:
                return Action.check()
            if self.limp_pct() and p <= self.limp_pct() and state.to_call <= bb:
                return Action.call()
            return Action.fold()
        if p <= self.threebet_pct:
            return do_raise(L, raises[-1].amount * 3)
        if p <= self.call_pct or (state.to_call <= bb and p <= self.call_pct * 2):
            if state.to_call > 0.5 * me.stack and p > self.callshove_pct:
                return passive(L)
            return callchk(L)
        return passive(L)

    def limp_pct(self):
        return 0.0

    def post(self, state, L):
        me, opps, bb, effbb = self.info(state)
        e = equity(state, len(opps))
        pot = state.pot
        tc = state.to_call
        if tc <= 0:
            if e >= self.bet_eq or (self.cbet_freq and self.rng.random() < self.cbet_freq):
                return do_raise(L, max(bb, int(pot * self.bet_frac)))
            return Action.check()
        odds = tc / float(pot + tc)
        if e >= self.raise_eq:
            return do_raise(L, tc * 3 + me.bet)
        if e >= odds + self.call_margin:
            return callchk(L)
        return passive(L)


class TAG(Base):
    pass


class LAG(Base):
    open_pct = 0.30
    late_open = 0.45
    call_pct = 0.22
    threebet_pct = 0.10
    push_bb = 12
    push_pct = 0.40
    callshove_pct = 0.20
    bet_eq = 0.55
    raise_eq = 0.78
    call_margin = -0.03
    cbet_freq = 0.55
    open_size = 2.5


class Station(Base):
    open_pct = 0.10
    late_open = 0.15
    call_pct = 0.50
    threebet_pct = 0.03
    push_pct = 0.20
    callshove_pct = 0.30
    bet_eq = 0.75
    raise_eq = 0.92
    call_margin = -0.10
    bet_frac = 0.5

    def limp_pct(self):
        return 0.6


class Nit(Base):
    open_pct = 0.08
    late_open = 0.12
    call_pct = 0.05
    threebet_pct = 0.025
    push_pct = 0.12
    callshove_pct = 0.05
    bet_eq = 0.70
    raise_eq = 0.88
    call_margin = 0.08


class Maniac(Base):
    open_pct = 0.55
    late_open = 0.75
    call_pct = 0.40
    threebet_pct = 0.20
    push_bb = 20
    push_pct = 0.6
    callshove_pct = 0.35
    bet_eq = 0.45
    raise_eq = 0.70
    call_margin = -0.08
    cbet_freq = 0.75
    bet_frac = 0.9
    open_size = 3.5


class Flaky(TAG):
    flaky = 0.5


class Shover(Base):
    """Shoves top 30% of hands, folds everything else (common 'simple but strong' push/fold bot)."""
    def pre(self, state, L):
        me, opps, bb, effbb = self.info(state)
        p = pct_of(state.cards)
        raises = [e for e in state.history if e.kind == "raise"]
        if not raises and p <= 0.30:
            return do_raise(L, me.stack + me.bet)
        if raises and p <= 0.08:
            return do_raise(L, me.stack + me.bet)
        return passive(L)

    def post(self, state, L):
        return callchk(L) if ActionKind.CHECK in L else Action.call()


class CheckOrFold:
    def act(self, state, memory):
        L = legal(state)
        return passive(L), memory


class MinRaiser:
    def act(self, state, memory):
        L = legal(state)
        if ActionKind.RAISE in L:
            return Action.raise_to(L[ActionKind.RAISE].min_amount), memory
        return callchk(L), memory


KINDS = {"tag": TAG, "lag": LAG, "station": Station, "nit": Nit, "maniac": Maniac, "flaky": Flaky,
         "shover": Shover, "cof": CheckOrFold, "minr": MinRaiser}


def make(kind, seed=None):
    c = KINDS[kind]
    return c(seed) if issubclass(c, Base) else c()
