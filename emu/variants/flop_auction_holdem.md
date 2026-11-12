# Boston

Standard no-limit hold'em, except that the flop is chosen by a sealed-bid auction paid in flop-chips.

## Rules

- Deal two private hole cards per player from one standard 52-card deck. Play normal preflop betting.
- Every player starts each table with 1,000 flop-chips. Flop-chips are separate from poker chips: they are never replenished, never bet into a pot, and never worth points. A table's balances carry from hand to hand and end with the table.
- After preflop betting, if two or more players remain, deal five auction cards face up, indexed 0 to 4 in dealing order. Every remaining player, including all-in players, submits one sealed bid: five whole numbers, one per auction card, summing to at most their flop-chip balance.
- Each card's score is the total bid on it by all players. The three highest-scoring cards become the flop, dealt in auction order. Ties go to the lower index. If nobody bids anything, cards 0, 1 and 2 become the flop.
- Players pay their bids on the three selected cards only; those flop-chips are destroyed. Bids on the other two cards are returned. The two unselected cards are dead for the rest of the hand.
- Continue normal flop, turn, and river betting. The turn and river come from the remaining deck. Showdown uses the best five cards from the board and the two hole cards, as in hold'em.
- If everyone but one player folds preflop, award the pot without an auction. Bidding costs no poker chips and does not change betting order or side-pot eligibility.
- If players are all in before the flop, the auction completes first; their hands are then shown before the flop is dealt.
- On a failed bid (timeout, exception, or invalid action), the player bids zero on every card. This does not fold the player or surrender an all-in pot.
- Blinds, antes, raises, side pots, uncalled refunds, and automatic showdown disclosure follow the hold'em reference. Bidding uses the normal decision time limit, time bank, and table memory. The variant supports 2–10 players.

## Bot interface

- At `state.phase == "auction"`, `state.variant["auction_cards"]` lists the five auction cards in index order. Return `Action("bid", cards=(b0, b1, b2, b3, b4))`: five non-negative whole numbers, one per card, summing to at most `state.variant["flop_chips"]`. `amount` must be zero.
- The legal action is `bid`, with `max_amount` equal to your flop-chip balance. Empty `cards` explicitly bids zero on every card. The supplied template and examples already use this default in unfamiliar phases.
- Bids are requested one player at a time, in postflop order. Each produces a public `bid` event naming only the bidder. No bid changes anything visible until every player has bid; later bidders cannot see earlier bids.
- `state.variant["flop_chips"]` is your current balance. `state.variant["flop_chips_by_seat"]` lists every seat's current balance, including busted seats. `state.variant["auction_cards"]` appears once the auction cards are dealt; `state.variant["flop_chips_paid"]`, the flop-chips you paid this hand, appears once the auction resolves. Balances update as soon as the auction resolves.
- An `auction` event shows the five cards. The following `board` event shows the three selected cards; the dead cards appear in no later event.
- Betting uses the existing action API; showdown reveals are automatic without a bot turn.
- eval7 knows standard hold'em; it does not know the auction. Exclude the two dead cards when you enumerate turn and river cards.

A minimal bidding handler is:

```python
if state.phase == "auction":
    return Action("bid", cards=(0, 0, 0, 0, 0)), memory
```

Improve how you spend flop-chips across the table; a balance spent early is gone for the table's later hands.

## Hand history

- Each hand adds `flop_chips_before` and `flop_chips_after`: every seat's flop-chip balance before and after the hand.
- Public `bid` events name the bidder only. Your own bids are owner-only `private_events`: one `bid` event per auction card you bid on (its card in `cards`, your bid in `amount`), at the index of your `bid` event.
- Owner-only `flop_chips` events give your balance at the start of each hand you are dealt into (`event_index` -1), and again at the flop's `board` event, after a `flop_chips_paid` event with what you paid (possibly 0).
- An automatic bid is recorded in `automatic` and bids zero on every card. The sample's bids are scripted, not a suggested policy.
