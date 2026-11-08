# 02 · Architecture

Three layers, so the strategy never touches the platform's quirks or the variant's rules.

```
agent.py              Agent class: platform layer (conventions, memory envelope, legality), warm-up, GC
  strategy.py         decide(view, mem) -> (kind, amount, mem): pure poker logic on a canonical view
  engine.py           every variant-dependent thing: deck, cards, hand classes, evaluation, equity, tables
  tables_<variant>.json   precomputed at build time by build_tables.py
```

## 1. Platform layer (write it first; it's what keeps the bot eligible)
- **Canonical view.** Present the strategy with one convention: stacks exclude this street's bet, the pot includes this street's bets, your own actions appear in events, and kinds are lowercase strings. Wrap the state in a small proxy that overrides only those fields and passes everything else through, methods included.
- **Detect the conventions at runtime,** and store what you learn in a small header at the front of `memory`.
  - **Stack convention first.** Preflop, a seat's stack + antes + (if excluded) its bet equals its hand-start stack. Hand-start stacks come from the previous hand's `stack` events, or `starting_stack` on the table's first hand.
  - **Fallback for the stack convention:** if your bet is above 0 and raising is offered, `max_amount` is stack + bet when the stack excludes the bet, and equals the stack when it includes it.
  - **Pot convention second, and only once the stack convention is known.** Use chip conservation: Σ(stack excl. bet) + pot_total = starting_stack × seats. If you test the pot before the stack convention is settled, "stack includes bet + pot excludes bets" can't be told apart from the default, which is a real bug we hit.
  - **Own-action echo:** after acting, store your action (kind, seat, amount; call = chips added) in the header. On the next turn, if the first action event isn't yours, the platform doesn't echo, so inject your stored action at the front of the events.
- **Memory envelope:** 2-byte magic, flags, the pending own action, then the strategy's memory untouched. Anything unreadable starts the table over; never raise on bad memory. Keep it small: about 600 B is plenty.
- **Legality funnel:** every decision ends in one function that maps the strategy's (kind, amount) onto offered kinds.
  - Raise becomes an int clamped to [min, max]; if raising isn't offered, call, else check.
  - Fold becomes check when check is offered.
  - An unknown phase gets the automatic choice.
  - **`act` wraps everything in try/except** and returns a legal fallback with the incoming memory.
- **Re-delivered events:** after a failure, the same events come again with the previous memory. Derive all state from (memory in, events) → memory out, so nothing gets double-counted.

## 2. Strategy layer
See `03_STRATEGY.md`. It reads only the canonical view and its own memory: per-seat opponent stats, about 15 counters per seat.

## 3. Variant engine
- **One module holds every variant-dependent call:**
  - parse a card
  - the hand class / canonical key of hole cards
  - preflop equity of a class against the top-x% range, for x in a grid of widths (0.04 … 1.0)
  - range lists by width
  - evaluate a hand (best 5 of N, under the variant's rules)
  - postflop equity against a sampled range within a deadline
- **Hold'em:** use eval7, which is fast C. Its Monte Carlo against a range runs about 30 µs for 300 iterations on a Mac.
- **Other variants:** a stdlib evaluator. Use bitmask rank/flush tables built at import, and a rank-multiset value cache **capped at 40k entries**, because dict resizes past that stall 1-4 ms.
  - Shortdeck: 36 cards, A-6-7-8-9 straight, flush beats a full house.
  - Omaha: exactly 2 hole + 3 board.
  - Pineapple/discard: see `04_FIELD.md`'s note and the kit's rules.
- **Tables:** precompute class × width equity with multiprocessing at build time. Hold'em takes about 4 s on 8 cores; Omaha needs many samples (minutes) because its hands are close in equity.
- **Monte Carlo deadline:** stop at about 0.34 ms after `act` starts. On the build box (about 1.3× slower than a Mac) the p99 is then about 0.4 ms.

## 4. Startup and timing
- **Import:** build or load tables at import, make one full throwaway decision on a synthetic state, then run `gc.collect(); gc.freeze()`.
- **Raise the GC threshold** with `gc.set_threshold(20000, 50, 100)`. Collector pauses were the **only** decisions over 1 ms on the build box (up to 7 ms); with the higher threshold the slowest decision was 0.3 ms.
- **Measure on the build box,** not your laptop, and compare p99 and max, not the mean. Our final bot: hold'em p50 83 µs, p99 220 µs, max 291 µs; Omaha p99 388 µs, max 466 µs; 0 of 220k decisions over 1 ms.
