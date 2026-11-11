"""Opponent archetypes for tuning: rough stand-ins for the kind of bots a 60-minute AI-assisted build produces."""
import random
import eval7
from poker_agent_sdk import Action, ActionKind
import agent as A

FULL = eval7.HandRange(",".join(A._ORDER))
CARD = A.CARD


def legal_map(state):
    return {la.kind: la for la in state.legal_actions}


def safe(state):
    lm = legal_map(state)
    return Action.check() if ActionKind.CHECK in lm else Action.fold()


class Base:
    """Generic tight/loose + equity-threshold bot. Parameters drawn with jitter."""
    P = {}

    def __init__(self, rng=None, jitter=0.25):
        rng = rng or random.Random()
        self.p = {k: (v * (1 + rng.uniform(-jitter, jitter)) if isinstance(v, float) else v) for k, v in self.P.items()}

    def act(self, state, memory):
        try:
            return self.decide(state), b""
        except Exception:
            return safe(state), b""

    # helpers
    def raise_to(self, state, total):
        lm = legal_map(state)
        la = lm.get(ActionKind.RAISE)
        if la is None:
            return self.call(state)
        t = int(max(la.min_amount, min(la.max_amount, int(total))))
        return Action.raise_to(t)

    def call(self, state):
        lm = legal_map(state)
        if ActionKind.CALL in lm:
            return Action.call()
        return Action.check()

    def fold(self, state):
        return safe(state)

    def ctx(self, state):
        me = [s for s in state.seats if s.seat == state.seat][0]
        opps = [s for s in state.seats if s.seat != state.seat and s.status in ("active", "all_in")]
        bb = state.blinds[1]
        tot = me.stack + me.bet
        eff = min(tot, max([o.stack + o.bet for o in opps] or [tot]))
        return me, opps, bb, tot, eff

    def decide(self, state):
        p = self.p
        me, opps, bb, tot, eff = self.ctx(state)
        to_call = state.to_call
        if not state.board:
            pct = A.PCT[A.hand_class(state.cards[0], state.cards[1])]
            nraise = sum(1 for e in state.history if e.kind == "raise")
            effbb = eff / bb
            if effbb <= p["push_bb"]:
                if nraise == 0:
                    return self.raise_to(state, tot) if pct <= p["push"] else (self.fold(state) if to_call > 0 else Action.check())
                return self.call(state) if pct <= p["callpush"] else self.fold(state)
            if nraise == 0:
                if pct <= p["open"]:
                    return self.raise_to(state, bb * p["osize"] + (me.bet if False else 0))
                if to_call == 0:
                    return Action.check()
                if pct <= p["limp"] and to_call <= bb:
                    return self.call(state)
                return self.fold(state)
            if pct <= p["reraise"]:
                if to_call > 0.35 * me.stack:
                    return self.raise_to(state, tot)
                return self.raise_to(state, (me.bet + to_call) * 3)
            if pct <= p["callr"] and to_call <= p["callcap"] * tot:
                return self.call(state)
            if to_call == 0:
                return Action.check()
            return self.fold(state)
        # postflop: equity vs random hands
        eq = eval7.py_hand_vs_range_monte_carlo([CARD[c] for c in state.cards], FULL,
                                                [CARD[c] for c in state.board], 150)
        eq = eq ** (1 + p["mwk"] * (len(opps) - 1))
        pot = state.pot
        if to_call > 0:
            odds = to_call / (pot + to_call)
            if eq >= p["raise_eq"]:
                return self.raise_to(state, me.bet + to_call + pot * p["rsize"])
            if eq >= odds + p["call_m"]:
                return self.call(state)
            return self.fold(state)
        if eq >= p["bet_eq"] or random.random() < p["bluff"]:
            return self.raise_to(state, me.bet + max(bb, pot * p["bsize"]))
        return Action.check()


class Tag(Base):
    P = dict(push_bb=11.0, push=0.25, callpush=0.10, open=0.17, osize=2.6, limp=0.0, reraise=0.035, callr=0.10,
             callcap=0.12, mwk=0.8, raise_eq=0.85, rsize=1.0, call_m=0.06, bet_eq=0.64, bsize=0.6, bluff=0.07)


class Lag(Base):
    P = dict(push_bb=15.0, push=0.40, callpush=0.18, open=0.38, osize=3.0, limp=0.0, reraise=0.08, callr=0.25,
             callcap=0.2, mwk=0.7, raise_eq=0.75, rsize=1.0, call_m=0.0, bet_eq=0.55, bsize=0.75, bluff=0.25)


class Station(Base):
    P = dict(push_bb=8.0, push=0.30, callpush=0.35, open=0.08, osize=2.0, limp=0.55, reraise=0.03, callr=0.50,
             callcap=0.3, mwk=0.6, raise_eq=0.9, rsize=0.6, call_m=-0.08, bet_eq=0.75, bsize=0.5, bluff=0.02)


class Nit(Base):
    P = dict(push_bb=10.0, push=0.12, callpush=0.05, open=0.08, osize=3.0, limp=0.0, reraise=0.025, callr=0.05,
             callcap=0.1, mwk=1.0, raise_eq=0.9, rsize=0.8, call_m=0.15, bet_eq=0.72, bsize=0.6, bluff=0.02)


class Pusher(Base):
    P = dict(push_bb=25.0, push=0.30, callpush=0.14, open=0.15, osize=2.5, limp=0.0, reraise=0.05, callr=0.06,
             callcap=0.1, mwk=0.9, raise_eq=0.7, rsize=3.0, call_m=0.05, bet_eq=0.65, bsize=1.0, bluff=0.05)


class Maniac(Base):
    P = dict(push_bb=20.0, push=0.6, callpush=0.4, open=0.6, osize=3.5, limp=0.0, reraise=0.2, callr=0.5,
             callcap=0.4, mwk=0.5, raise_eq=0.6, rsize=1.2, call_m=-0.05, bet_eq=0.4, bsize=1.0, bluff=0.4)


class CheckOrFold:
    def __init__(self, rng=None):
        pass

    def act(self, state, memory):
        return safe(state), b""


class MinRaiser:
    def __init__(self, rng=None):
        pass

    def act(self, state, memory):
        lm = legal_map(state)
        la = lm.get(ActionKind.RAISE)
        if la is not None:
            return Action.raise_to(int(la.min_amount)), b""
        return (Action.call() if ActionKind.CALL in lm else Action.check()), b""


ARCH = {"tag": Tag, "lag": Lag, "station": Station, "nit": Nit, "pusher": Pusher, "maniac": Maniac,
        "cof": CheckOrFold, "minr": MinRaiser}


class FlakyTag(Tag):
    """A TAG bot that times out on a share of its decisions (fallback: check, else fold)."""
    def __init__(self, rng=None, jitter=0.25):
        super().__init__(rng, jitter)
        self.fail = (rng or random).uniform(0.15, 0.6)

    def act(self, state, memory):
        if random.random() < self.fail:
            return safe(state), b""
        return super().act(state, memory)


ARCH["flaky"] = FlakyTag


class R1Field(Base):
    """Calibrated to round-1 field stats (vpip ~.28, pfr ~.18, 3-bet ~5%, folds ~75-85% to 3-bets,
    postflop aggression ~.25, flop bets mostly value, fold to bet ~.5)."""
    P = dict(push_bb=12.0, push=0.28, callpush=0.12, open=0.18, osize=2.5, limp=0.05, reraise=0.03, callr=0.07,
             callcap=0.1, mwk=0.85, raise_eq=0.85, rsize=1.0, call_m=0.08, bet_eq=0.68, bsize=0.6, bluff=0.04)


ARCH["r1"] = R1Field
