"""Hold'em whose flop is bought at a sealed-bid auction, paid in flop-chips that last the table.

Mock of the Boston regional variant for team avalon's Finals rehearsal, rebuilt from the
organizers' Format page and the event shapes in the Boston hand histories. Not organizer code.
"""

import random
from collections import deque
from dataclasses import replace
from typing import Any

from poker_agent_protocol.game import Action, BlindLevel, LegalAction

from poker_engine.holdem import HoldemHand
from poker_engine.variant import Hand, HandEvent, HandView

FLOP_CHIPS = 1000  # Each player's flop-chips at the start of every table, never replenished.
AUCTION_CARDS = 5
FLOP_CARDS = 3


class FlopChips:
    """A `TableExtension` keeping each seat's flop-chips from hand to hand at one table, and
    logging each hand's balances and every seat's owner-only details."""

    def __init__(self, players: int) -> None:
        self.balances = [FLOP_CHIPS] * players

    def deal_options(self, seats: tuple[int, ...]) -> dict[str, Any]:
        return {"flop_chips": tuple(self.balances), "seats": seats}

    def hand_over(self, hand: Hand, seats: tuple[int, ...]) -> dict[str, Any]:
        before = list(self.balances)
        for position, paid in enumerate(hand.flop_chips_paid()):  # type: ignore[attr-defined]
            self.balances[seats[position]] -= paid
        return {
            "flop_chips_before": before,
            "flop_chips_after": list(self.balances),
            # Organizer log only: every seat's bids. Each seat's download gets its own.
            "private": [
                {"seat": seats[position], **event}
                for position, event in hand.private()  # type: ignore[attr-defined]
            ],
        }


class FlopAuctionHoldem:
    name = "flop_auction_holdem"
    title = "Boston"
    public_id = "boston"
    max_players = 10
    extension = FlopChips

    def deal(
        self,
        *,
        stacks: tuple[int, ...],
        blinds: BlindLevel,
        rng: random.Random,
        flop_chips: tuple[int, ...] | None = None,
        seats: tuple[int, ...] | None = None,
    ) -> "FlopAuctionHand":
        return FlopAuctionHand(
            stacks=stacks, blinds=blinds, rng=rng, flop_chips=flop_chips, seats=seats
        )


class FlopAuctionHand(HoldemHand):
    def __init__(
        self,
        *,
        stacks: tuple[int, ...],
        blinds: BlindLevel,
        rng: random.Random,
        flop_chips: tuple[int, ...] | None = None,
        seats: tuple[int, ...] | None = None,
    ) -> None:
        super().__init__(stacks=stacks, blinds=blinds, rng=rng)
        players = len(stacks)
        self._seats = tuple(range(players)) if seats is None else tuple(seats)
        # Per table seat, so a bot sees every seat's balance, busted seats included.
        self._by_seat = list(
            [FLOP_CHIPS] * (max(self._seats) + 1) if flop_chips is None else flop_chips
        )
        self._start = [self._by_seat[seat] for seat in self._seats]  # Per position.
        self._auctioned = False
        self._auction: list[Any] = []  # The five PokerKit cards, in auction order.
        self._bidding: deque[int] = deque()
        self._bids: dict[int, tuple[int, ...]] = {}
        self._bid_event: dict[int, int] = {}
        self._flop: list[Any] = []  # The three cards won, in auction order, until dealt.
        self._paid: list[int] | None = None  # Per position, once the auction resolves.

    def actor(self) -> int | None:
        state = self._state
        while True:
            if self._bidding:
                return self._bidding[0]
            if state.actor_index is not None:  # Betting: nothing can be dealt or shown now.
                return state.actor_index
            if (
                not self._auctioned
                and state.status
                and not state.board_cards
                and sum(state.statuses) > 1
                and not state.can_deal_hole()
            ):
                # Preflop betting is over with two or more players left: auction first, even
                # before an all-in showdown.
                self._open_auction()
                return self._bidding[0]
            if state.can_deal_hole():
                state.deal_hole()
            elif state.can_burn_card():
                state.burn_card()
            elif state.can_deal_board():
                if self._flop:
                    # The deck no longer holds the auctioned cards: put the winners on top.
                    for card in reversed(self._flop):
                        state.deck_cards.appendleft(card)
                    self._flop = []
                state.deal_board()
            elif state.showdown_index is not None:
                state.show_or_muck_hole_cards(True)
            else:
                return state.actor_index

    def _open_auction(self) -> None:
        state = self._state
        self.events()
        self._auctioned = True
        self._auction = [state.deck_cards.popleft() for _ in range(AUCTION_CARDS)]
        self._events.append(HandEvent("auction", cards=tuple(map(repr, self._auction))))
        # Folded players are out; all-in players bid too. Postflop order, button last.
        self._bidding.extend(i for i in state.player_indices if state.statuses[i])

    def legal_actions(self) -> tuple[LegalAction, ...]:
        if self._bidding:
            return (LegalAction("bid", 0, self._start[self._bidding[0]]),)
        return super().legal_actions()

    def apply(self, action: Action) -> None:
        if not self._bidding:
            super().apply(action)
            return
        player = self._bidding[0]
        if action.kind != "bid" or action.amount:
            raise ValueError("Bid with Action('bid', cards=(b0, b1, b2, b3, b4)).")
        bids = action.cards or (0,) * AUCTION_CARDS
        if (
            len(bids) != AUCTION_CARDS
            or any(type(bid) is not int or bid < 0 for bid in bids)
            or sum(bids) > self._start[player]
        ):
            raise ValueError(
                "Give five whole-number bids, one per auction card, summing to at most your "
                "flop-chips."
            )
        self.events()
        self._bids[player] = tuple(bids)
        self._bid_event[player] = len(self._events)
        # Public: who bid, never how much or on which cards.
        self._events.append(HandEvent("bid", player))
        self._bidding.popleft()
        if not self._bidding:
            self._resolve()

    def _resolve(self) -> None:
        scores = [sum(bids[i] for bids in self._bids.values()) for i in range(AUCTION_CARDS)]
        # Highest totals win; ties go to the lower index. No bids at all: cards 0, 1 and 2.
        ranked = sorted(range(AUCTION_CARDS), key=lambda i: (-scores[i], i))
        won = sorted(ranked[:FLOP_CARDS])  # Dealt in auction order.
        self._flop = [self._auction[i] for i in won]
        self._paid = [
            sum(self._bids[p][i] for i in won) if p in self._bids else 0
            for p in range(len(self._start))
        ]
        for position, paid in enumerate(self._paid):
            self._by_seat[self._seats[position]] -= paid

    def flop_chips_paid(self) -> tuple[int, ...]:
        """Flop-chips each position paid this hand: its bids on the three cards won."""
        return tuple(self._paid or [0] * len(self._start))

    def private(self) -> list[tuple[int, dict[str, Any]]]:
        """Each position's owner-only details, attached to the public event where each takes
        effect: its balance before the hand (-1), its bids per card (its `bid` event), then
        what it paid and its new balance (the flop's `board` event)."""
        out: list[tuple[int, dict[str, Any]]] = [
            (p, {"kind": "flop_chips", "event_index": -1, "amount": balance})
            for p, balance in enumerate(self._start)
        ]
        if not self._bids:
            return out
        for p in sorted(self._bids, key=self._bid_event.__getitem__):
            for card, amount in zip(self._auction, self._bids[p], strict=True):
                if amount:
                    out.append(
                        (
                            p,
                            {
                                "kind": "bid",
                                "event_index": self._bid_event[p],
                                "cards": [repr(card)],
                                "amount": amount,
                            },
                        )
                    )
        events = self.events()
        flop = next(
            (
                i
                for i in range(max(self._bid_event.values()) + 1, len(events))
                if events[i].kind == "board"
            ),
            None,
        )
        if flop is not None and self._paid is not None:
            for p in sorted(self._bids, key=self._bid_event.__getitem__):
                out.append((p, {"kind": "flop_chips_paid", "event_index": flop, "amount": self._paid[p]}))
                out.append(
                    (p, {"kind": "flop_chips", "event_index": flop, "amount": self._start[p] - self._paid[p]})
                )
        return out

    def view(self, player: int) -> HandView:
        view = super().view(player)
        balance = self._start[player] - (self._paid[player] if self._paid else 0)
        variant: dict[str, Any] = {
            "flop_chips": balance,
            "flop_chips_by_seat": list(self._by_seat),
        }
        if self._auction:
            variant["auction_cards"] = [repr(card) for card in self._auction]
        if self._paid is not None:
            variant["flop_chips_paid"] = self._paid[player]
        return replace(
            view,
            phase="auction" if self._bidding else view.phase,
            to_call=0 if self._bidding else view.to_call,
            variant=variant,
        )


VARIANT = FlopAuctionHoldem
