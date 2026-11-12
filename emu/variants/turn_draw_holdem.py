"""Hold'em with a sealed one-card draw on the turn; every thrown card is shown face up.

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

DRAW_STREET_CARDS = 4  # The draw comes once the turn is on the board.


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


class TurnDrawHoldem:
    name = "turn_draw_holdem"
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
    ) -> "TurnDrawHand":
        return TurnDrawHand(stacks=stacks, blinds=blinds, rng=rng)


class TurnDrawHand(HoldemHand):
    def __init__(self, *, stacks: tuple[int, ...], blinds: BlindLevel, rng: random.Random) -> None:
        super().__init__(stacks=stacks, blinds=blinds, rng=rng)
        players = len(stacks)
        self._started = False
        self._resolved = False
        self._drawing: deque[int] = deque()
        self._choices: dict[int, tuple[int, ...]] = {}
        self._exchange_event: dict[int, int] = {}
        self._thrown: list[tuple[str, ...]] = [()] * players
        self._drawn: list[tuple[str, ...]] = [()] * players
        # All-in showdowns PokerKit plays before the draw stay private until it resolves.
        self._early_shows: set[int] = set()
        self._deferred: set[int] = set()

    def actor(self) -> int | None:
        state = self._state
        while True:
            if self._drawing:
                return self._drawing[0]
            if (
                not self._started
                and len(state.board_cards) == DRAW_STREET_CARDS
                and sum(state.statuses) > 1
            ):
                self.events()
                self._started = True
                # Folded players are out; all-in players draw too. Postflop order.
                self._drawing.extend(i for i in state.player_indices if state.statuses[i])
                return self._drawing[0]
            if state.actor_index is not None:  # Betting: nothing can be dealt or shown now.
                return state.actor_index
            if state.can_deal_hole():
                state.deal_hole()
            elif state.can_burn_card():
                state.burn_card()
            elif state.can_deal_board():
                state.deal_board()
            elif state.showdown_index is not None:
                if len(state.board_cards) < DRAW_STREET_CARDS:
                    # PokerKit shows all-in hands before the runout; publish them after the
                    # draw, with the cards each player then holds.
                    self.events()
                    self._early_shows.add(len(state.operations))
                state.show_or_muck_hole_cards(True)
            else:
                return state.actor_index

    def legal_actions(self) -> tuple[LegalAction, ...]:
        if self._drawing:
            return (LegalAction("draw"),)
        return super().legal_actions()

    def apply(self, action: Action) -> None:
        if not self._drawing:
            super().apply(action)
            return
        if action.kind != "draw" or action.amount:
            raise ValueError("Draw with Action('draw', cards=()) or cards=(index,).")
        if len(action.cards) > 1 or any(
            type(index) is not int or not 0 <= index < 2 for index in action.cards
        ):
            raise ValueError("Throw at most one card: its index, 0 or 1.")
        player = self._drawing[0]
        self.events()
        self._choices[player] = tuple(action.cards)
        # Acknowledgements say only who has chosen.
        self._events.append(HandEvent("draw", player))
        self._drawing.popleft()
        if not self._drawing:
            self._resolve()

    def _resolve(self) -> None:
        state = self._state
        self._resolved = True
        for player, choice in self._choices.items():  # Postflop order.
            self._exchange_event[player] = len(self._events)
            if not choice:
                self._events.append(HandEvent("exchange", player, 0))
                continue
            hole = state.hole_cards[player]
            thrown, new = hole[choice[0]], state.deck_cards.popleft()
            hole[choice[0]] = new  # The replacement takes the thrown card's place.
            self._thrown[player] = (repr(thrown),)
            self._drawn[player] = (repr(new),)
            self._dealt[player] += self._drawn[player]
            self._events.append(HandEvent("exchange", player, 1, self._thrown[player]))
        for player in sorted(self._deferred):
            self._shown[player] = tuple(map(repr, state.hole_cards[player]))
            self._events.append(HandEvent("show", player, cards=self._shown[player]))
        self._deferred.clear()

    def private(self) -> list[tuple[int, dict[str, Any]]]:
        """Each drawing position's replacement card, at its own `exchange` event."""
        return [
            (p, {"kind": "drawn", "event_index": self._exchange_event[p], "cards": list(cards)})
            for p, cards in enumerate(self._drawn)
            if cards
        ]

    def view(self, player: int) -> HandView:
        view = super().view(player)
        return replace(
            view,
            phase="draw" if self._drawing else view.phase,
            to_call=0 if self._drawing else view.to_call,
            variant={"thrown": list(self._thrown[player]), "drawn": list(self._drawn[player])},
        )

    def events(self) -> tuple[HandEvent, ...]:
        # The reference conversion, one operation at a time, holding back early all-in shows
        # until the draw resolves.
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


VARIANT = TurnDrawHoldem
