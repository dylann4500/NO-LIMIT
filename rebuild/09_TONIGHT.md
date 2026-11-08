# 09 · Tonight's variant: three cards, discard one, expose one (read this first)

The kit's `RULES.md` is the authority. This is how to play it well.

## The variant in one line
You're dealt 3 cards with normal preflop betting. At the flop, before betting, everyone still in **discards 1 (private, dead) and exposes 1 of the 2 kept cards (public)**. From then on it's hold'em: best 5 of board + your 2 kept cards.

## API facts (from RULES.md)
- **Selection:** `state.phase == "select"`. `state.cards` holds 3 cards in dealing order. Return `Action("select", cards=(discard_index, reveal_index))`: distinct ints 0-2, amount 0. Empty `cards` means the default (2, 0).
- **After resolution:** `state.cards` holds your 2 kept cards, and `state.seats[i].shown_cards` holds each player's **exposed card**. A `reveal` event names the seat and card. `state.variant["discarded"]` is your discard.
- **Failed selection** (timeout, exception, invalid) discards the last-dealt card and exposes the first. It doesn't fold, but it counts as a failed decision toward the 10% upload-test limit, so always return a valid select.
- **eval7** `HandRange` and the `py_hand_vs_range_*` helpers assume 2 hole cards, so use them only after selection. `eval7.evaluate` takes any number of cards.

## Minute-10 bot (upload this first)
Start from the kit's template `agent.py`, which already plays legally.
- **Select:** keep the best pair of the three on this flop, scored as (made hand with the board, then draw value, then high cards). Expose the kept card that gives away least: the one not pairing the board, or not part of a flush draw, or the lower card.
- **Preflop:** play only hands where some 2 of the 3 cards are a pair 66+, two cards ≥ T, or a suited ace. Raise 2.5 bb with those, shove at ≤10 bb with them, otherwise check or fold.
- **Postflop:** bet 2/3 pot and call with top pair or better, otherwise check or fold.

Run tests 1-4 from `05_TESTS.md` (the selection phase must show 0 failures), then upload and confirm.

## Full-strength plan (the 03_STRATEGY design, adapted)
1. **Preflop strength of a 3-card hand** is its value *after choosing the best 2 on the flop*.
   - **Fast version (do this first):** take the hold'em percentile of the best of its three 2-card subsets, then improve it by about 15-25% for flexibility. Three suited cards, connected cards or a pair plus a high card play better than their best pair alone.
   - **Better version:** a build-time Monte Carlo over canonical 3-card classes (up to 22,100 combos; group by suit isomorphism). Per class, deal flops, pick the kept pair by the selection rule, run out against a random opponent doing the same, and store equity by range width. Multiprocessing, a few minutes.
   - Everyone's hands are stronger than hold'em, so **open and call ranges in `03_STRATEGY.md` apply to percentiles of this new ranking, not to hold'em hands.** Showdowns are stronger too, so value thresholds go up.
2. **Selection (biggest new edge).** For each of the 3 possible discards, compute the kept pair's equity on this flop against a "best 2 of 3" opponent range: a strong-ish 2-card range, roughly the top 50-60%. Use eval7 Monte Carlo with about 100 iterations each, so all three fit well inside 1 ms. Keep the best. Then expose whichever kept card leaks less about the made hand or draw.
3. **Postflop edge: every opponent has one card face up.** Each villain's kept hand is {exposed card + one hidden card}, only about 45 combos. Narrow that further by their betting (the `03_STRATEGY` range narrowing applies). Compute equity **exactly against those combos**; it's cheap. This is far more information than standard hold'em: use it in every call, bet and fold.
4. **Dead cards:** your discard plus every exposed card. Remove them from all deck sampling.
5. **Reading exposures:** an exposed A or K means their hidden card was chosen to go with it. Weight the hidden card toward hands that make sense: a pair with the board, a high card, suited with the exposed card.
6. **All-ins:** all-in players still select, so keep the selection handler fast and safe for all-in seats too.

## Field habits that likely carry over (04_FIELD.md)
- The field folds 50-70% to postflop bets, and big late bets and raises are strong.
- Shoves are wider than charts suggest.
- Light 3-bets get through.
- Most other bots will use the default selection or a naive "keep best pair" rule, and few will exploit opponents' exposed cards. That's our edge.
