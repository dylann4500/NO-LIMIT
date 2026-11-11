"""Opponent archetypes: a guess at what a field of one-hour, AI-assisted bots looks like.
Nothing here is measured from the real field. Treat it as a stress test.
"""
import random
import pk
from pk import equity_vs_range

FOLD, CALL, RAISE = (0, 0), (1, 0), None
R = random.random


def pct(o):
    return pk.pct(o.hole)


def raise_to(o, x):
    return (2, int(x))


class FoldBot:
    """A crashing or timing-out bot: the platform auto-checks or folds for it."""
    def act(self, o):
        return CALL if o.to_call == 0 else FOLD


class RandomBot:
    def act(self, o):
        r = R()
        if r < 0.25 and o.to_call:
            return FOLD
        if r < 0.75 or not o.can_raise:
            return CALL
        return raise_to(o, o.min_raise_to + R() * (o.max_raise_to - o.min_raise_to) * 0.3)


class Station:
    """Rarely folds, rarely raises."""
    def __init__(self, width=0.6):
        self.width = width

    def act(self, o):
        if o.street == 0:
            if pct(o) < self.width or o.to_call == 0:
                return CALL
            return FOLD
        if o.to_call == 0:
            return CALL
        if o.to_call > o.pot * 1.2 and equity_vs_range(o.hole, o.board, 1.0, 12) < 0.55:
            return FOLD
        return CALL


class Maniac:
    """Huge raises and frequent all-ins."""
    def __init__(self, width=0.5, jam=0.2):
        self.width, self.jam = width, jam

    def act(self, o):
        if o.street == 0 and pct(o) > self.width:
            return CALL if o.to_call == 0 else FOLD
        if o.can_raise:
            if R() < self.jam:
                return raise_to(o, o.max_raise_to)
            if R() < 0.6:
                return raise_to(o, o.cur + o.pot)
        return CALL


class Jammer:
    """All-in with the top `width`, otherwise fold. A common cheap 1 ms design."""
    def __init__(self, width=0.2):
        self.width = width

    def act(self, o):
        if o.street == 0:
            if pct(o) < self.width:
                return raise_to(o, o.max_raise_to) if o.can_raise else CALL
            return CALL if o.to_call == 0 else FOLD
        return CALL if o.to_call == 0 else (raise_to(o, o.max_raise_to) if o.can_raise else CALL)


class TAG:
    """Chart preflop, then continuation bets plus pot odds. A typical assistant 'solid' bot."""
    def __init__(self, open_w=0.2, call_w=0.08, cbet=0.6, value=0.72):
        self.open_w, self.call_w, self.cbet, self.value = open_w, call_w, cbet, value

    def act(self, o):
        p = pct(o)
        if o.street == 0:
            if o.raises == 0:
                if p < self.open_w and o.can_raise:
                    return raise_to(o, 3 * o.bb + o.n_callers * o.bb)
                return CALL if o.to_call == 0 else FOLD
            if p < self.call_w * 0.5 and o.can_raise:
                return raise_to(o, o.cur * 3)
            if p < self.call_w or (o.to_call <= 0.1 * o.stack and p < self.open_w * 0.6):
                return CALL
            return FOLD
        eq = equity_vs_range(o.hole, o.board, 0.35, 24)
        if o.to_call == 0:
            if eq > self.value - 0.1 and o.can_raise and R() < self.cbet + 0.3:
                return raise_to(o, o.pot * 0.66)
            return CALL
        if eq > self.value + 0.1 and o.can_raise:
            return raise_to(o, o.cur + o.pot * 0.75)
        if eq > o.to_call / (o.pot + o.to_call) + 0.08:
            return CALL
        return FOLD


class MCPotOdds:
    """The most likely assistant-written bot: MC equity vs. a random hand, raised to the number
    of live opponents, compared with pot odds."""
    def __init__(self, rollouts=20, raise_at=0.7):
        self.rollouts, self.raise_at = rollouts, raise_at

    def act(self, o):
        opp = max(1, o.n_live - 1)
        if o.street == 0:
            eq = pk.hu_eq(o.hole)
        else:
            eq = equity_vs_range(o.hole, o.board, 1.0, self.rollouts)
        eq = eq ** min(opp, 3)
        odds = o.to_call / (o.pot + o.to_call) if o.to_call else 0
        if eq > self.raise_at and o.can_raise:
            return raise_to(o, o.cur + o.pot * 0.75)
        if o.to_call == 0:
            return CALL
        return CALL if eq >= odds else FOLD


class ShortFolder:
    """TAG deep, then jam-or-fold under 15 big blinds."""
    def __init__(self):
        self.t = TAG(0.18, 0.06)

    def act(self, o):
        if o.street == 0 and o.stack + o.bet < 15 * o.bb:
            w = 0.1 + 0.02 * (15 - (o.stack + o.bet) / o.bb)
            if pct(o) < w:
                return raise_to(o, o.max_raise_to) if o.can_raise else CALL
            return CALL if o.to_call == 0 else FOLD
        return self.t.act(o)


ARCHETYPES = {
    "fold": FoldBot,
    "random": RandomBot,
    "station": Station,
    "maniac": Maniac,
    "jam20": lambda: Jammer(0.2),
    "jam08": lambda: Jammer(0.08),
    "tag": TAG,
    "nit": lambda: TAG(0.10, 0.04, 0.5, 0.78),
    "lag": lambda: TAG(0.40, 0.15, 0.8, 0.62),
    "mc": MCPotOdds,
    "shortfold": ShortFolder,
}

# Field mixes as weights. All guesses: compare across them rather than trusting any single one.
FIELDS = {
    "early_buggy": {"fold": 3, "random": 2, "station": 2, "maniac": 2, "jam20": 1, "jam08": 1, "tag": 3, "nit": 1, "lag": 1, "mc": 5, "shortfold": 1},
    "typical": {"fold": 1, "random": 1, "station": 2, "maniac": 2, "jam20": 1, "jam08": 1, "tag": 4, "nit": 2, "lag": 2, "mc": 5, "shortfold": 3},
    "strong": {"maniac": 1, "jam08": 1, "tag": 5, "nit": 3, "lag": 3, "mc": 3, "shortfold": 6},
    "aggro": {"maniac": 5, "jam20": 4, "jam08": 2, "lag": 4, "tag": 2, "mc": 2},
    "passive": {"station": 6, "mc": 5, "nit": 4, "tag": 2, "fold": 1},
}


# Copies of the candidate, used to test against a field as well prepared as we are.
def _tuned(path):
    import json, os
    from hero import Hero
    d = {}
    if os.path.exists(path):
        d = json.load(open(path))["mu"]
    return lambda: Hero(**d)

import os as _os
_here = _os.path.dirname(__file__)
ARCHETYPES["cand"] = _tuned(_os.path.join(_here, "tuned_robust.json"))
FIELDS["mirror"] = {"cand": 5, "tag": 2, "shortfold": 2, "nit": 1, "lag": 1, "mc": 1}
FIELDS["all_mirror"] = {"cand": 1}


# ---- Holdout opponents. The tuner never sees these; they exist only to detect overfitting. ----
class AllIn:
    """Moves all-in every hand."""
    def act(self, o):
        return raise_to(o, o.max_raise_to) if o.can_raise else CALL


class MinRaiser:
    """Min-raises any playable hand and calls down too much."""
    def act(self, o):
        if o.street == 0 and pct(o) > 0.55:
            return CALL if o.to_call == 0 else FOLD
        if o.can_raise and R() < 0.5:
            return raise_to(o, o.min_raise_to)
        return CALL if o.to_call <= o.pot else FOLD


class PotSizer:
    """Tier chart; pot-sized bets by made-hand strength, folds to pressure without a strong hand."""
    def act(self, o):
        p = pct(o)
        if o.street == 0:
            if p < 0.15 and o.can_raise:
                return raise_to(o, o.cur + o.pot)
            if p < 0.35 and o.to_call <= 3 * o.bb:
                return CALL
            return CALL if o.to_call == 0 else FOLD
        eq = equity_vs_range(o.hole, o.board, 0.5, 16)
        if eq > 0.68 and o.can_raise:
            return raise_to(o, o.cur + o.pot)
        if o.to_call == 0:
            return CALL
        return CALL if eq > 0.6 else FOLD


class ChipLeaderBully:
    """Loose and aggressive when above average stack, tight when below."""
    def __init__(self):
        self.big, self.small = TAG(0.45, 0.2, 0.9, 0.6), TAG(0.12, 0.05, 0.5, 0.75)

    def act(self, o):
        avg = sum(o.stacks) / max(1, o.n_alive)
        return (self.big if o.stack > avg else self.small).act(o)


class SizedPusher:
    """Jam width grows as the stack shrinks; flat-calls small raises when deep."""
    def act(self, o):
        bbs = (o.stack + o.bet) / o.bb
        p = pct(o)
        if o.street == 0:
            w = 0.5 if bbs < 6 else 0.3 if bbs < 12 else 0.12 if bbs < 25 else 0.05
            if p < w and o.can_raise:
                return raise_to(o, o.max_raise_to)
            if bbs >= 25 and p < 0.25 and o.to_call <= 3 * o.bb:
                return CALL
            return CALL if o.to_call == 0 else FOLD
        if o.to_call == 0:
            return CALL
        eq = equity_vs_range(o.hole, o.board, 0.25, 16)
        return CALL if eq > o.to_call / (o.pot + o.to_call) else FOLD


ARCHETYPES.update({"allin": AllIn, "minraise": MinRaiser, "potsize": PotSizer, "bully": ChipLeaderBully, "pusher": SizedPusher})
FIELDS["holdout"] = {"allin": 1, "minraise": 3, "potsize": 4, "bully": 4, "pusher": 4}
FIELDS["holdout_soft"] = {"minraise": 5, "potsize": 3, "bully": 1, "fold": 1}
