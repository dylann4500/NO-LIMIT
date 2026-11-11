"""Sparring opponents (portal API) approximating the kinds of bots other teams will field.
Used only by dev/arena.py; the submitted agent never imports this."""
import random

import eval7
from poker_agent_sdk import Action

_C = {r + s: eval7.Card(r + s) for r in "23456789TJQKA" for s in "cdhs"}
_DECK = list(_C.values())
RANKS = "23456789TJQKA"


def _legal(state):
    out = {}
    for la in state.legal_actions:
        k = getattr(la.kind, "value", la.kind)
        out[str(k).lower()] = la
    return out


def chen(cards):
    """Chen-formula preflop score (roughly -1..20)."""
    vals = {"A": 10, "K": 8, "Q": 7, "J": 6, "T": 5}
    r = sorted((RANKS.index(c[0]) for c in cards), reverse=True)
    hi = cards[0][0] if RANKS.index(cards[0][0]) >= RANKS.index(cards[1][0]) else cards[1][0]
    score = vals.get(hi, (r[0] + 2) / 2.0)
    if r[0] == r[1]:
        return max(5, score * 2)
    if cards[0][1] == cards[1][1]:
        score += 2
    gap = r[0] - r[1] - 1
    score -= {0: 0, 1: 1, 2: 2, 3: 4}.get(gap, 5)
    if gap <= 1 and r[0] < RANKS.index("Q"):
        score += 1
    return score


_ALL = [(a, b) for i, a in enumerate(_DECK) for b in _DECK[i + 1:]]


def mc_equity(cards, board, n_opp, iters=120, rng=random):
    """Equity vs one random hand via eval7 MC on a sampled range, raised to the number of opponents."""
    hero = [_C[c] for c in cards]
    b = [_C[c] for c in board]
    dead = set(hero) | set(b)
    rngl = [((x, y), 1.0) for (x, y) in rng.sample(_ALL, 160) if x not in dead and y not in dead][:120]
    e = eval7.py_hand_vs_range_monte_carlo(hero, rngl, b, len(rngl) * 4)
    return e ** max(1, n_opp) if n_opp > 1 else e


class _Base:
    def _ctx(self, state):
        lg = _legal(state)
        me = [s for s in state.seats if s.seat == state.seat][0]
        n_opp = sum(1 for s in state.seats if s.seat != state.seat and s.status in ("active", "all_in"))
        bb = state.blinds[1]
        return lg, me, n_opp, bb

    def _raise(self, lg, total):
        la = lg.get("raise")
        if la is None:
            return self._call(lg)
        t = int(max(la.min_amount, min(la.max_amount, total)))
        return Action.raise_to(t)

    def _call(self, lg):
        if "call" in lg:
            return Action.call()
        return Action.check()

    def _fold(self, lg):
        return Action.check() if "check" in lg else Action.fold()


class EquityBot(_Base):
    """Typical 'AI-built equity bot': MC equity vs random hands of the live opponents, pot-odds calls,
    value raises above a threshold, Chen-formula preflop, push/fold when short."""

    def __init__(self, raise_eq=0.62, loose=0.0):
        self.raise_eq = raise_eq
        self.loose = loose
        self.rng = random.Random()

    def act(self, state, memory):
        lg, me, n_opp, bb = self._ctx(state)
        stack_bb = (me.stack + me.bet) / bb
        tc = state.to_call
        if not state.board:
            ch = chen(state.cards) + self.loose
            if stack_bb < 12:
                if ch >= 8 or (tc <= bb and ch >= 6):
                    return self._raise(lg, 10 ** 9), memory
                return (Action.check() if "check" in lg else Action.fold()), memory
            if ch >= 11:
                return self._raise(lg, max(3 * bb, 3 * (me.bet + tc))), memory
            if ch >= 8 and tc <= 4 * bb:
                if tc <= bb:
                    return self._raise(lg, 3 * bb), memory
                return self._call(lg), memory
            if ch >= 6 and tc <= bb:
                return self._call(lg), memory
            return self._fold(lg), memory
        eq = mc_equity(state.cards, state.board, max(1, n_opp), 100, self.rng)
        pot = state.pot
        if eq >= self.raise_eq + 0.04 * (n_opp - 1):
            return self._raise(lg, me.bet + tc + 0.75 * (pot + tc)), memory
        if tc == 0:
            return Action.check(), memory
        if eq >= tc / (pot + tc) + 0.03:
            return self._call(lg), memory
        return Action.fold(), memory


class TagBot(EquityBot):
    def __init__(self):
        super().__init__(raise_eq=0.66, loose=-1.0)


class LooseBot(EquityBot):
    """Loose-aggressive: wide preflop, bets often, bluffs sometimes."""

    def __init__(self):
        super().__init__(raise_eq=0.55, loose=2.5)

    def act(self, state, memory):
        lg, me, n_opp, bb = self._ctx(state)
        if state.board and state.to_call == 0 and self.rng.random() < 0.35:
            return self._raise(lg, me.bet + 0.6 * state.pot), memory
        return super().act(state, memory)


class Station(_Base):
    """Calls almost anything with a pair or a draw, rarely raises."""

    def __init__(self):
        self.rng = random.Random()

    def act(self, state, memory):
        lg, me, n_opp, bb = self._ctx(state)
        tc = state.to_call
        if not state.board:
            ch = chen(state.cards)
            if ch >= 12:
                return self._raise(lg, 3 * bb + me.bet + tc), memory
            if ch >= 4 or tc <= bb:
                if tc <= 0.3 * (me.stack + me.bet) or ch >= 9:
                    return self._call(lg), memory
            return self._fold(lg), memory
        eq = mc_equity(state.cards, state.board, max(1, n_opp), 80, self.rng)
        if eq > 0.8:
            return self._raise(lg, me.bet + tc + 0.5 * state.pot), memory
        if tc == 0:
            return Action.check(), memory
        if eq > 0.28 or tc <= 0.25 * state.pot:
            return self._call(lg), memory
        return Action.fold(), memory


class PushFold(_Base):
    """Shoves a Chen-ranked range, otherwise folds (a common 'safe' tournament bot)."""

    def act(self, state, memory):
        lg, me, n_opp, bb = self._ctx(state)
        ch = chen(state.cards)
        stack_bb = (me.stack + me.bet) / bb
        thr = 10 if stack_bb > 25 else (8 if stack_bb > 12 else 6)
        if not state.board:
            if ch >= thr:
                return self._raise(lg, 10 ** 9), memory
            return self._fold(lg), memory
        if state.to_call == 0:
            return Action.check(), memory
        return self._call(lg), memory


class Maniac(_Base):
    """Raises pot most of the time; calls the rest."""

    def __init__(self):
        self.rng = random.Random()

    def act(self, state, memory):
        lg, me, n_opp, bb = self._ctx(state)
        if self.rng.random() < 0.6:
            return self._raise(lg, me.bet + state.to_call + state.pot), memory
        if state.to_call == 0:
            return Action.check(), memory
        return self._call(lg), memory


KINDS = {"equity": EquityBot, "tag": TagBot, "loose": LooseBot, "station": Station, "pushfold": PushFold,
         "maniac": Maniac}
