"""Test opponents modelled on typical quickly-built bots (TAG equity bot, LAG, station, pusher, nit)."""
import json
import os
import random

import eval7
from poker_agent_sdk import Action

HERE = os.path.dirname(os.path.abspath(__file__))
_P = json.load(open(os.path.join(HERE, "..", "preflop.json")))
PCT = _P["pct"]
RV = {r: i for i, r in enumerate("23456789TJQKA")}
CARD = {r + s: eval7.Card(r + s) for r in "23456789TJQKA" for s in "shdc"}
_full = []
for a in CARD:
    for b in CARD:
        if a < b:
            _full.append((a, b))
_rng = random.Random(5)
FULL = eval7.HandRange("AA")
FULL.hands = [((CARD[a], CARD[b]), 1.0) for a, b in _rng.sample(_full, 250)]


def cls(a, b):
    ra, rb = a[0], b[0]
    if RV[ra] < RV[rb]:
        ra, rb = rb, ra
    if ra == rb:
        return ra + rb
    return ra + rb + ("s" if a[1] == b[1] else "o")


def kn(k):
    return getattr(k, "value", k)


def lm(state):
    return {kn(a.kind): a for a in state.legal_actions}


def do(state, kind, amt=0):
    L = lm(state)
    if kind == "raise" and "raise" in L:
        a = L["raise"]
        return Action.raise_to(int(max(a.min_amount, min(a.max_amount, amt))))
    if kind in ("raise", "call"):
        if "call" in L:
            return Action.call()
        return Action.check()
    if "check" in L:
        return Action.check()
    return Action.fold()


class Base:
    open_thr = 0.2
    threebet = 0.05
    call_thr = 0.12
    push_bb = 12
    push_thr = 0.25
    bet_eq = 0.6
    raise_eq = 0.82
    call_margin = 0.05
    bluff = 0.0
    sizing = 0.66

    def act(self, state, memory):
        bb = state.blinds[1]
        me = [s for s in state.seats if s.seat == state.seat][0]
        stack = me.stack + me.bet
        h = cls(*state.cards)
        p = PCT[h]
        L = lm(state)
        to_call = state.to_call
        opps = [s for s in state.seats if s.seat != state.seat and kn(s.status) in ("active", "all_in")]
        if not state.board:
            raises = sum(1 for e in state.history if kn(e.kind) == "raise")
            if stack <= self.push_bb * bb:
                if p <= self.push_thr * (1.0 if raises == 0 else 0.5):
                    return do(state, "raise", 10 ** 9), memory
                return do(state, "check" if to_call == 0 else "fold"), memory
            if raises == 0:
                if p <= self.open_thr:
                    return do(state, "raise", 3 * bb), memory
                if to_call == 0:
                    return do(state, "check"), memory
                return do(state, "fold"), memory
            if p <= self.threebet:
                return do(state, "raise", state.to_call * 3 + max(s.bet for s in state.seats)), memory
            if p <= self.call_thr and to_call <= 0.25 * stack:
                return do(state, "call"), memory
            if p <= self.threebet * 0.6:
                return do(state, "call"), memory
            return do(state, "check" if to_call == 0 else "fold"), memory
        hand = [CARD[c] for c in state.cards]
        board = [CARD[c] for c in state.board]
        e1 = eval7.py_hand_vs_range_monte_carlo(hand, FULL, board, 200)
        eq = e1 ** max(1, len(opps))
        pot = state.pot
        if to_call == 0:
            if eq >= self.bet_eq or random.random() < self.bluff:
                return do(state, "raise", int(pot * self.sizing)), memory
            return do(state, "check"), memory
        odds = to_call / (pot + to_call)
        if eq >= self.raise_eq:
            return do(state, "raise", 3 * to_call + me.bet), memory
        if eq >= odds + self.call_margin:
            return do(state, "call"), memory
        return do(state, "fold"), memory


class TAG(Base):
    pass


class LAG(Base):
    open_thr = 0.4
    threebet = 0.1
    call_thr = 0.3
    push_thr = 0.4
    bet_eq = 0.5
    raise_eq = 0.75
    bluff = 0.3
    call_margin = 0.0


class Station(Base):
    open_thr = 0.15
    threebet = 0.03
    call_thr = 0.5
    push_thr = 0.2
    bet_eq = 0.7
    raise_eq = 0.9
    call_margin = -0.08


class Pusher(Base):
    push_bb = 1000
    push_thr = 0.22


class Nit(Base):
    open_thr = 0.08
    threebet = 0.03
    call_thr = 0.06
    push_thr = 0.12
    bet_eq = 0.7
    call_margin = 0.12


class Maniac(Base):
    open_thr = 0.7
    threebet = 0.25
    call_thr = 0.6
    push_thr = 0.6
    bet_eq = 0.35
    raise_eq = 0.6
    bluff = 0.5
    call_margin = -0.05
    sizing = 1.0


OPPS = {"tag": TAG, "lag": LAG, "station": Station, "pusher": Pusher, "nit": Nit, "maniac": Maniac}


class CheckOrFold:
    def act(self, state, memory):
        L = lm(state)
        return (Action.check() if "check" in L else Action.fold()), memory


class MinRaiser:
    def act(self, state, memory):
        L = lm(state)
        if "raise" in L:
            return Action.raise_to(int(L["raise"].min_amount)), memory
        return (Action.call() if "call" in L else Action.check()), memory


OPPS.update(cof=CheckOrFold, minr=MinRaiser)
