# San Francisco

Standard no-limit hold'em, except that after the flop every player passes one hole card face down to the player on their left.

## Rules

- Deal two private hole cards per player from one standard 52-card deck. Play normal preflop betting.
- After dealing the flop and before flop betting, every non-folded player chooses one of their two hole cards to pass. Lock every choice before any card moves.
- Each card goes face down to the next non-folded player clockwise (to the left). Every player ends with the card they kept and the card passed to them. With two players left, they swap. Folded players neither pass nor receive.
- Only the passer and the receiver know the passed card. Each player therefore knows one card now held by the player to their left, and nobody sees a card leave or arrive.
- Continue normal flop, turn, and river betting. Showdown uses the best five cards from the board and the two hole cards then held. Every player still in automatically reveals both hole cards, including losing hands; there is no mucking.
- All-in players also pass. If players are all in before the flop, their hands are shown, as held after the passes, once the passes resolve and before the turn is dealt.
- If everyone but one player folds preflop, award the pot without passing. Passing costs no chips and does not change betting order or side-pot eligibility.
- On a failed choice (timeout, exception, or invalid action), the player passes the second card dealt (index 1). This does not fold the player or surrender an all-in pot.
- Blinds, antes, raises, side pots, uncalled refunds, and automatic showdown disclosure follow the hold'em reference. Passing uses the normal decision time limit, time bank, and table memory. The variant supports 2–10 players.

## Bot interface

- At `state.phase == "pass"`, `state.cards` holds your two hole cards in dealing order. Return `Action("pass", cards=(index,))` with the index (0 or 1) of the card to pass. Empty `cards` explicitly requests the default, index 1. `amount` must be zero.
- `state.variant["pass_to"]` is the seat that will receive your card and `state.variant["receive_from"]` the seat whose card you will receive.
- Choices are requested one player at a time, in postflop order. Each produces a public `pass` acknowledgement naming only the player. One public `passes` event, without cards, marks the moment every card moves.
- After the passes, `state.cards` holds the card you kept, then the card you received. `state.variant["passed"]` and `state.variant["received"]` list those two cards, or are empty before the passes.
- Betting uses the existing action API; showdown reveals are automatic without a bot turn.
- eval7 knows standard hold'em, not passing. The card you passed is live in your left neighbor's hand, not in the deck.

A minimal passing handler is:

```python
if state.phase == "pass":
    return Action("pass", cards=(1,)), memory
```

Improve which card to give away; use the card you know your left neighbor holds in later decisions.

## Hand history

- A hand's public `cards` for a seat are the cards it showed at showdown, after the passes.
- Your private `cards` are the two cards you were dealt, in dealing order. New histories identify the card you passed and the card you received in owner-only `passed` and `received` events at the index of the `passes` event.
- An automatic choice passes index 1. The sample's choices are scripted, not a suggested policy.
