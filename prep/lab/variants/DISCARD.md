# Discard variants

The organizers tie the event to MIT's 6.9630 Pokerbots class, whose 2026 variant deals three hole cards and has each player discard one. This file sets out MIT's rules as their engine implements them, what an 8-seat version leaves open, and what the lab does about each open point.

Source: https://github.com/mitpokerbots/engine-2026 (commit `69f0ff1`, Jan 16 2026), mainly `engine.py` and `python_skeleton/`. I read the code; I didn't run it.

## MIT 2026 rules, from their engine

MIT plays heads-up: 400 chips, blinds 1/2, 1000 hands per match. Player index 0 is the small blind and button, and index 1 is the big blind. The seats swap every hand.

| Street (engine id) | What happens |
|---|---|
| 0, preflop | Each player gets **3 hole cards** (`deck.deal(3)`). Betting as in hold'em; the small blind acts first. |
| Flop | **2 community cards** (`deck.peek(2)`). There is **no betting** on this two-card flop. |
| 2, first discard | The **big blind (out of position) discards first**. Its only legal action is `DiscardAction(i)`, `i` in 0..2 indexing its hand. The card goes **face up onto the board**: `board.append(hand.pop(i))`. The other player's only legal action is Check, a pass. |
| 3, second discard | The **button discards second, after seeing the first discard**. Discards are sequential, not simultaneous. The board now has 4 cards. |
| 4, betting | First postflop betting round, on 2 flop cards + 2 discards. The big blind acts first. |
| 5, turn | +1 card (5-card board), betting. |
| 6, river | +1 card (6-card board), betting. |
| Showdown | `pkrbot.evaluate(board + hand)`: the **2 kept hole cards + all 6 board cards, best 5 of 8**, standard hand ranks. Ties split. |

Details that matter for a bot:
- **Discarded cards are community cards.** Both players can use both discards. Your discard can pair the board, or add a third card of a suit, for your opponent too.
- **Discards are public.** The history carries `D<i>` (the index), and the next board message shows the card itself.
- **The discard happens even when a player is all in.** Streets 2 and 3 offer Discard regardless of stacks, so every player still in the hand reduces to two cards.
- **A failed discard folds in MIT's engine.** An illegal response, a bad index or a timeout falls back to "Check if legal, else Fold". During a discard street Check isn't legal, so the player folds. Our portal says a failed decision in a variant phase takes the "automatic choice" instead (`Action(first.kind, first.min_amount)`, which would drop card 0).
- The turn and river come from deck positions 3 and 4, and position 2 goes unused. That's harmless and behaves like a burn card.
- The skeleton's sample bot always plays `DiscardAction(0)`.

## What an 8-seat version leaves open (check against RULES.md at kickoff)

| Question | MIT (heads-up) | Lab assumption (`POKER_VARIANT=hole3discard`) |
|---|---|---|
| Who discards, in what order | BB then button | Every player still in the hand, in postflop order (first to act discards first, button last), each seeing the earlier discards |
| Where discards go | Board, as community cards | Board (MIT). `DISCARD_DEAD=1` makes them revealed but dead. With k players at the flop, the final board is 4 + k cards |
| Flop size, betting on it | 2 cards, no betting | Same |
| All-in players | They discard | They discard |
| Action format | `DiscardAction(index)` | `state.phase == "discard"`, one legal kind `DISCARD` with `min_amount=0`, `max_amount=len(cards)-1`; `Action(DISCARD, i)` drops `state.cards[i]` (see `lab/fake_sdk`) |
| Failed decision | Fold | Automatic choice: drop card 0 |
| Public record | `D<i>` in history, card on the board | A `discard` event (seat, `cards=[card]`), plus the card in `state.board` |
| Showdown | 2 kept + board, best 5 | Same |

The riskiest guesses are the multiway board (all discards to the board) and the action format. Everything kit-specific in our bots is in the `KIT:` constants at the top of `lab/v2/core/discard.py`.

## Strategy notes

- Only two cards play at showdown, so a preflop hand's value is roughly its best two-card subset plus some option value from the third card. Our preflop tables approximate this: a 3-card hand scores as its best 2 with a 5-card board.
- The discard is a public, shared card. A good discard keeps your pair or draw and doesn't hand the field one. For example, don't discard a third card of a suit already on the board, or a card that pairs the board when you can't use the pair.
- Discarding second is an information edge: you see one more card before choosing.
- `discard_choice` (`lab/v2/core/discard.py`) uses Monte Carlo. It scores each candidate drop by the heads-up showdown equity of the two cards kept, against a villain hand, over the same runouts for every option. The runouts include our own discard on the board, the turn and river, and one unknown card for each player who discards after us. It takes about 0.3 ms. On shared deals it beats "drop the lowest card" and the lab's "keep the best preflop pair" (see `lab/v2/README.md`).

## Other plausible discard and draw twists

- **Pineapple:** 3 hole cards; discard 1 after preflop betting, before the flop; normal 5-card board. Discards are usually dead (face down).
- **Crazy Pineapple:** 3 hole cards; discard 1 after the flop betting round.
- **Lazy Pineapple (Tahoe-like):** 3 hole cards, no discard until showdown; the best hand uses at most 2 of them.
- **Irish:** 4 hole cards, Omaha-style preflop and flop betting; discard 2 after the flop; hold'em rules after that.
- **Draw rounds:** swap 1 (or k) hole cards for fresh ones from the deck at a fixed street. This is the hold'em analogue of 5-card or triple draw. The swapped cards are often hidden.
- **MIT 2026 with dead discards:** revealed but not community cards (`DISCARD_DEAD=1` in the lab).

`discard_choice(hole, board, to_come, n_after, ...)` works for any hand size and board: it drops one card from `hole`. Set `to_board=False` (or `DISCARD_TO_BOARD = False`) for dead discards. To discard two cards (Irish), call it twice, or extend it to score subsets.
