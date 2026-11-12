"""Hold'em where every player passes one hole card to the left after the flop.

A mock Finals variant for team avalon's rehearsal, written in the style of the organizers'
built-in variants. Not organizer code.
"""

import random
from collections import deque
from dataclasses import replace
from typing import Any

from poker_agent_protocol.game import Action, BlindLevel, LegalAction
from pokerkit import (
    AntePosting,
    BlindOrStraddlePosting,
    BoardDealing,
    CheckingOrCalling,
    ChipsPulling,
    CompletionBettingOrRaisingTo,
    Folding,
    HoleCardsShowingOrMucking,
    HoleDealing,
)

from poker_engine.holdem import HoldemHand
from poker_engine.variant import Hand, HandEvent, HandView

PASS_STREET_CARDS = 3  # Passing comes once the flop is on the board.
DEFAULT_PASS = 1  # The automatic choice: pass the second-dealt card.


class PrivateLog:
    """A `TableExtension` logging each hand's owner-only details by seat, as its record's
    `private` list. Each seat's download gets only its own."""

    def __init__(self, players: int) -> None:
        pass

    def deal_options(self, seats: tuple[int, ...]) -> dict[str, Any]:
        return {"seats": seats}

    def hand_over(self, hand: Hand, seats: tuple[int, ...]) -> dict[str, Any]:
        return {
            "private": [
                {"seat": seats[position], **event}
                for position, event in hand.private()  # type: ignore[attr-defined]
            ]
        }


class FlopPassHoldem:
    name = "flop_pass_holdem"
    title = "San Francisco"
    public_id = "san_francisco"
    max_players = 10
    extension = PrivateLog

    def deal(
        self,
        *,
        stacks: tuple[int, ...],
        blinds: BlindLevel,
        rng: random.Random,
        seats: tuple[int, ...] | None = None,
    ) -> "FlopPassHand":
        return FlopPassHand(stacks=stacks, blinds=blinds, rng=rng, seats=seats)


class FlopPassHand(HoldemHand):
    def __init__(
        self,
        *,
        stacks: tuple[int, ...],
        blinds: BlindLevel,
        rng: random.Random,
        seats: tuple[int, ...] | None = None,
    ) -> None:
        super().__init__(stacks=stacks, blinds=blinds, rng=rng)
        players = len(stacks)
        self._seats = tuple(range(players)) if seats is None else tuple(seats)
        self._started = False
        self._passing: deque[int] = deque()
        self._order: tuple[int, ...] = ()  # Every passing position, clockwise from the SB.
        self._choices: dict[int, int] = {}
        self._passes_event: int | None = None
        self._passed: list[tuple[str, ...]] = [()] * players
        self._received: list[tuple[str, ...]] = [()] * players
        # All-in showdowns PokerKit plays before the passes stay private until they resolve.
        self._early_shows: set[int] = set()
        self._deferred: set[int] = set()

    def actor(self) -> int | None:
        state = self._state
        while True:
            if self._passing:
                return self._passing[0]
            if (
                not self._started
                and len(state.board_cards) == PASS_STREET_CARDS
                and sum(state.statuses) > 1
            ):
                self.events()
                self._started = True
                # Folded players are out; all-in players pass too. Postflop order.
                self._order = tuple(i for i in state.player_indices if state.statuses[i])
                self._passing.extend(self._order)
                return self._passing[0]
            if state.actor_index is not None:  # Betting: nothing can be dealt or shown now.
                return state.actor_index
            if state.can_deal_hole():
                state.deal_hole()
            elif state.can_burn_card():
                state.burn_card()
            elif state.can_deal_board():
                state.deal_board()
            elif state.showdown_index is not None:
                if len(state.board_cards) < PASS_STREET_CARDS:
                    # PokerKit shows all-in hands before the runout; publish them after the
                    # passes, with the cards each player then holds.
                    self.events()
                    self._early_shows.add(len(state.operations))
                state.show_or_muck_hole_cards(True)
            else:
                return state.actor_index

    def legal_actions(self) -> tuple[LegalAction, ...]:
        if self._passing:
            return (LegalAction("pass"),)
        return super().legal_actions()

    def apply(self, action: Action) -> None:
        if not self._passing:
            super().apply(action)
            return
        if action.kind != "pass" or action.amount:
            raise ValueError("Pass with Action('pass', cards=(index,)).")
        if len(action.cards) > 1 or any(
            type(index) is not int or not 0 <= index < 2 for index in action.cards
        ):
            raise ValueError("Pass exactly one card: its index, 0 or 1.")
        player = self._passing[0]
        self.events()
        self._choices[player] = action.cards[0] if action.cards else DEFAULT_PASS
        # Acknowledgements say only who has chosen.
        self._events.append(HandEvent("pass", player))
        self._passing.popleft()
        if not self._passing:
            self._resolve()

    def _neighbors(self, player: int) -> tuple[int, int]:
        """The passing positions to this one's left (receiving) and right (giving)."""
        order = self._order
        k = order.index(player)
        return order[(k + 1) % len(order)], order[k - 1]

    def _resolve(self) -> None:
        state = self._state
        passed = {p: state.hole_cards[p][i] for p, i in self._choices.items()}
        for player, index in self._choices.items():
            hole = state.hole_cards[player]
            kept = hole[1 - index]
            received = passed[self._neighbors(player)[1]]
            # The kept card first, then the card received from the right.
            hole[0], hole[1] = kept, received
            self._passed[player] = (repr(passed[player]),)
            self._received[player] = (repr(received),)
        self._passes_event = len(self._events)
        self._events.append(HandEvent("passes"))
        for player in sorted(self._deferred):
            self._shown[player] = tuple(map(repr, state.hole_cards[player]))
            self._events.append(HandEvent("show", player, cards=self._shown[player]))
        self._deferred.clear()

    def private(self) -> list[tuple[int, dict[str, Any]]]:
        """Each passing position's passed and received card, at the public `passes` event."""
        if self._passes_event is None:
            return []
        return [
            (p, {"kind": kind, "event_index": self._passes_event, "cards": list(cards[p])})
            for p in self._order
            for kind, cards in (("passed", self._passed), ("received", self._received))
        ]

    def view(self, player: int) -> HandView:
        view = super().view(player)
        variant: dict[str, Any] = {
            "passed": list(self._passed[player]),
            "received": list(self._received[player]),
        }
        if self._order and player in self._order:
            left, right = self._neighbors(player)
            variant["pass_to"] = self._seats[left]
            variant["receive_from"] = self._seats[right]
        return replace(
            view,
            phase="pass" if self._passing else view.phase,
            to_call=0 if self._passing else view.to_call,
            variant=variant,
        )

    def events(self) -> tuple[HandEvent, ...]:
        # The reference conversion, one operation at a time, holding back early all-in shows
        # until the passes resolve.
        operations = self._state.operations
        while self._recorded < len(operations):
            operation = operations[self._recorded]
            if self._recorded in self._early_shows:
                assert isinstance(operation, HoleCardsShowingOrMucking)
                self._deferred.add(operation.player_index)
            else:
                self._record_operation(operation)
            self._recorded += 1
        if not self._state.status and not self._settled:
            # Uncalled bets are refunded without an operation, so state final stacks outright.
            self._settled = True
            for player, stack in enumerate(self._state.stacks):
                self._events.append(HandEvent("stack", player, stack))
        return tuple(self._events)

    def _record_operation(self, operation: object) -> None:
        match operation:
            case HoleDealing(player_index=player, cards=cards):
                self._dealt[player] += tuple(map(repr, cards))
            case AntePosting(player_index=player, amount=amount):
                self._events.append(HandEvent("ante", player, amount))
            case BlindOrStraddlePosting(player_index=player, amount=amount):
                self._events.append(HandEvent("blind", player, amount))
            case BoardDealing(cards=cards):
                self._events.append(HandEvent("board", cards=tuple(map(repr, cards))))
            case Folding(player_index=player):
                self._events.append(HandEvent("fold", player))
            case CheckingOrCalling(player_index=player, amount=amount):
                self._events.append(HandEvent("call" if amount else "check", player, amount))
            case CompletionBettingOrRaisingTo(player_index=player, amount=amount):
                self._events.append(HandEvent("raise", player, amount))
            case HoleCardsShowingOrMucking(player_index=player, hole_cards=cards) if cards:
                self._shown[player] = tuple(map(repr, cards))
                self._events.append(HandEvent("show", player, cards=self._shown[player]))
            case HoleCardsShowingOrMucking(player_index=player):
                self._events.append(HandEvent("muck", player))
            case ChipsPulling(player_index=player, amount=amount) if amount:
                self._events.append(HandEvent("win", player, amount))



VARIANT = FlopPassHoldem
