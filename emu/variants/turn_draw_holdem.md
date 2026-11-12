# San Francisco

Standard no-limit hold'em, with a sealed one-card draw on the turn. Every thrown card is shown face up.

## Rules

- Deal two private hole cards per player from one standard 52-card deck. Play normal preflop and flop betting.
- After dealing the turn and before turn betting, every non-folded player chooses to keep both hole cards or to throw one of them and draw a replacement from the deck. Lock every choice before any card is exchanged or shown.
- Once every player has chosen, exchanges happen in postflop order. A thrown card is shown face up to the table and is dead for the rest of the hand. The replacement is private to its owner and plays as a normal hole card.
- Continue normal turn and river betting. The river comes from the remaining deck after every replacement. Showdown uses the best five cards from the board and the two hole cards then held. Every player still in automatically reveals both hole cards, including losing hands; there is no mucking.
- All-in players also choose. If players are all in before the turn, the runout pauses at the turn for the draw; their hands are shown, as held after the draw, once the draw resolves and before the river.
- If everyone but one player folds before the turn, award the pot without a draw. Drawing costs no chips and does not change betting order or side-pot eligibility.
- On a failed choice (timeout, exception, or invalid action), the player keeps both cards. This does not fold the player or surrender an all-in pot.
- Blinds, antes, raises, side pots, uncalled refunds, and automatic showdown disclosure follow the hold'em reference. The draw uses the normal decision time limit, time bank, and table memory. The variant supports 2–10 players.

## Bot interface

- At `state.phase == "draw"`, `state.cards` holds your two hole cards in dealing order. Return `Action("draw", cards=(index,))` to throw the card at that index (0 or 1), or `Action("draw")` with empty `cards` to keep both. `amount` must be zero.
- Choices are requested one player at a time, in postflop order. Each produces a public `draw` acknowledgement naming only the player. Later players cannot see earlier choices.
- When the draw resolves, an `exchange` event for each player, in postflop order, gives the number of cards exchanged in `amount` (0 or 1) and the thrown card in `cards`.
- After the draw, `state.cards` holds your current hole cards; a replacement takes the thrown card's place. `state.variant["thrown"]` and `state.variant["drawn"]` list your own thrown and replacement card, or are empty.
- Betting uses the existing action API; showdown reveals are automatic without a bot turn.
- eval7 knows standard hold'em, not the draw. Remove every thrown card from the deck when you enumerate river cards.

A minimal draw handler is:

```python
if state.phase == "draw":
    return Action("draw"), memory
```

Improve which hands draw and which card to throw; account for opponents' thrown cards in later decisions.

## Hand history

- Public `exchange` events show every thrown card. A hand's public `cards` for a seat are the cards it showed at showdown, after the draw.
- Your private `cards` are every card you were dealt, in dealing order: your two hole cards, then your replacement if you drew. New histories also identify your replacement in an owner-only `drawn` event at the index of your `exchange` event.
- An automatic choice keeps both cards. The sample's choices are scripted, not a suggested policy.
