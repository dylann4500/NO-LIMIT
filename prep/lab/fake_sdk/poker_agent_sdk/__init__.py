"""Stand-in for the kit's poker_agent_sdk, written from the portal text (docs/portal_getting_started.md)
before the kit shipped. Only lab tests put lab/fake_sdk on sys.path. The real SDK replaces it at kickoff,
so adapter code must rely only on what the portal documents, never on details of this file.

Deliberately strict where the portal is: action kinds are Enum members (not strings), a kind that is not
offered is illegal, and raise totals outside min_amount..max_amount are not clamped.
"""
from enum import Enum


class ActionKind(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    # Discard variant (lab POKER_VARIANT=hole3discard, our guess at the format; the real kit's RULES.md decides):
    # state.phase == "discard", legal_actions == [LegalAction(DISCARD, 0, len(state.cards) - 1)], and
    # Action(DISCARD, i) drops state.cards[i]. The automatic choice, Action(first.kind, first.min_amount), drops card 0.
    DISCARD = "discard"


class LegalAction:
    __slots__ = ("kind", "min_amount", "max_amount")

    def __init__(self, kind, min_amount=0, max_amount=0):
        self.kind, self.min_amount, self.max_amount = kind, min_amount, max_amount

    def __repr__(self):
        return f"LegalAction({self.kind.value}, {self.min_amount}, {self.max_amount})"


class Action:
    __slots__ = ("kind", "amount")

    def __init__(self, kind, amount=None):
        self.kind, self.amount = kind, amount

    @classmethod
    def fold(cls):
        return cls(ActionKind.FOLD)

    @classmethod
    def check(cls):
        return cls(ActionKind.CHECK)

    @classmethod
    def call(cls):
        return cls(ActionKind.CALL)

    @classmethod
    def raise_to(cls, total):
        return cls(ActionKind.RAISE, total)

    @classmethod
    def discard(cls, index):
        """Drop state.cards[index] (discard variant)."""
        return cls(ActionKind.DISCARD, index)

    def __repr__(self):
        return f"Action({getattr(self.kind, 'value', repr(self.kind))}, {self.amount})"


class Event:
    __slots__ = ("kind", "seat", "amount", "cards")

    def __init__(self, kind, seat=None, amount=None, cards=None):
        self.kind, self.seat, self.amount, self.cards = kind, seat, amount, cards

    def __repr__(self):
        return f"Event({self.kind}, seat={self.seat}, amount={self.amount}, cards={self.cards})"


class Seat:
    __slots__ = ("seat", "stack", "bet", "status", "shown_cards")

    def __init__(self, seat, stack, bet, status, shown_cards=None):
        self.seat, self.stack, self.bet, self.status = seat, stack, bet, status
        self.shown_cards = shown_cards or []


class Config:
    __slots__ = ("table_id", "seat", "variant", "players", "starting_stack", "blinds", "hands_per_level",
                 "hand_cap", "payouts", "decision_ms", "time_bank_ms", "memory_bytes")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


class State:
    """Portal fields: hand (seat, cards, board, pot, to_call, legal_actions, history, phase, variant),
    table (seats, button), tournament (blind_level, blinds, hands_until_next_level, hand_number,
    players_remaining, bust_order), config, time_bank_ms, events."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def can(self, kind):
        for a in self.legal_actions:
            if a.kind == kind:
                return a
        return None


class Agent:
    def act(self, state, memory):
        raise NotImplementedError
