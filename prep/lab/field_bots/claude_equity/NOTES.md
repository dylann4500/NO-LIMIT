# claude_equity: notes

An equity bot. For each decision it estimates our equity against a model of every live opponent's range, prices each legal action (fold, check, call, several bet or raise sizes, jam) by expected value, and plays the best one. Actions that put a big share of the stack at risk are priced with ICM rather than chips.

## Files

- `agent.py` is the bot. It loads `tables.json` at import and uses only the stdlib and `eval7`.
- `tables.json` holds the preflop tables, built offline by `dev/precompute.py`. It contains the 169 hand classes ordered by strength (HU equity vs random + 0.6 × 3-way equity), each class's HU equity against the top-p% of that ordering for 14 values of p, and each class's equity against 1 to 7 random hands.
- `dev/` has tools that the bot never imports:
  - `precompute.py` rebuilds `tables.json` (about 15 s).
  - `sparring.py` has six opponent archetypes written to imitate likely field bots. `equity` uses MC equity vs random hands with pot-odds calls and Chen-formula preflop. `tag` and `loose` are tighter and looser versions of it, `station` calls almost anything, `pushfold` shoves Chen-ranked hands, and `maniac` raises pot most of the time.
  - `arena.py` runs `lab/field_kit/play.py` with those archetypes as extra seat kinds, plus optional `--extra name=bot_dir` seats for A/B tests.
    Example: `.venv/bin/python lab/field_bots/claude_equity/dev/arena.py lab/field_bots/claude_equity --tables 200 --seats self,self,equity,tag,loose,station,pushfold,maniac`

## How a decision works

1. **Opponent stats, kept in `memory` per table.** Memory is a marshal-encoded dict of about 2 KB. `state.events` is replayed through a small state machine that tracks the street, the current bet and each seat's contribution and stack. Per seat it counts:
   - VPIP, PFR, preflop jam frequency
   - fold to a raise, 3-bet frequency, fold to a 3-bet
   - postflop bet frequency when checked to, fold / raise / call when facing a bet
   - calls when facing a big bet

   Counts from the hand in progress are held separately and merged when the next hand starts. Without this, a seat's own open made its estimated range wider at the moment we price a response to it, which caused bad early calls and 4-bets. All ratios are smoothed with priors.
2. **Preflop range of each opponent.** This is a percentile band of the strength-ordered 1,326 combos, chosen by its line:
   - open: top PFR
   - 3-bet: top 3-bet frequency
   - 4-bet+: tighter still
   - call of a raise: from the 3-bet frequency up to 1 − fold-to-raise
   - limp: from PFR/2 up to VPIP
   - check in the BB: any two cards

   All-in jams get their own range from the seat's observed jam frequency, wider when the jammer is short.
3. **Postflop narrowing uses absolute-strength thresholds.** Most field bots compare their hand to a fixed cut-off ("equity vs random ≥ x"). So each sampled combo gets a strength key (made-hand rank, raised for flush draws and open-enders). That key is turned into a percentile against random hands on the same board, and each action filters on that percentile, calibrated by the seat's frequencies:
   - bet keeps the top `bet_freq`
   - raise keeps the top `2 × raise_freq`
   - call drops the bottom `fold_freq`
   - check drops part of the top

   A thin tail of other combos is kept to cover bluffs. An earlier version filtered relative to the opponent's own range, which inflated our equity badly; switching to absolute thresholds was the single biggest gain.
4. **Equity.**
   - Preflop comes from table lookups, with a multiway correction.
   - Flop and turn use `eval7.py_hand_vs_range_monte_carlo` on the sampled combos, with iterations set to a multiple of the range size. That eval7 sampler walks the range in order, so fewer iterations than combos gives biased results.
   - River compares our hand exactly against each sampled combo.
   - Multiway equity is the product over modelled opponents, capped at 3 opponents.
5. **EV of each action.** Fold probability for a bet or raise uses the same threshold model:
   - Each opponent folds the part of its range below its observed fold cut-off, scaled by bet size.
   - That probability is multiplied by a commitment factor: someone getting a good price on the rest of their stack doesn't fold.
   - When called, our equity is measured against the continuing part of the range only.
   - Realization factors are applied for flop and turn, with implied odds for draws, set-mining and suited connectors.
   - Preflop opens use position thresholds, plus an EV steal check driven by how often the players behind fold.
   - At 13 BB or less we play jam or fold, with jam EV computed per possible caller.
6. **ICM.** Any option risking 30% or more of our stack is scored with Malmuth-Harville tournament equity (3 paid places, from `config.payouts`) over the resulting stacks, then converted back to chip-equivalents. This makes the bot properly risk-averse near the bubble and when stacks are equal three-handed. A small model-uncertainty premium (`UNC_RAISE`, `UNC_CALL`) applies to big fold-equity plays.
7. **Safety.**
   - Every returned action goes through `legalize`: only offered kinds are returned, and raise totals are integers clamped to `min..max`.
   - Any exception falls back to check, otherwise fold. Over about 100k decisions in testing, zero exceptions were swallowed and no illegal actions were returned.

## Time budget

The limit is 1 ms per decision, the production machines are about 2.5x slower than this one, and the upload test runs with no time bank.

- Preflop is cheap: about 40 µs CPU at p50.
- Postflop costs are capped:
  - range samples of 50 / 36 / 24 combos (1 / 2 / 3+ opponents)
  - a 26-combo reference sample per street
  - stratified sampling instead of `random.sample`
  - memoized equity for continuing ranges
  - a 0.3 ms guard that stops modelling further opponents
- A `fast` mode (smaller samples, one bet size) switches on when `state.time_bank_ms < 40` or the decision is already slow. This also covers the upload test, where the bank is 0.
- `gc.freeze()` runs after import. Import takes about 60 ms.

Measured CPU per decision on this machine, with the box heavily loaded (load average 60–110 on 15 cores, which inflates CPU time by roughly 1.5x):

| percentile | p50 | p90 | p99 | p99.9 | max |
|---|---|---|---|---|---|
| CPU (µs) | 45 | 155–180 | 215–260 | 280–320 | about 570 |

By street:

| spot | p50 (µs) | p99 (µs) |
|---|---|---|
| HU flop | about 140 | about 215 |
| river, 3 or more opponents | about 270 | about 380 |

Scaling the worst cases by 2.5x still lands under 1 ms. `play.py` reports a handful of timeouts per 100k decisions, with wall-clock maxima of 50–150 ms. Those come from the oversubscribed lab machine, not from our code: CPU max is under 0.6 ms.

## What was tested and how it moved (local)

Mean points per table; fair share is 12.5.

| version | default `play.py` field (4 self, 2 check_or_fold, 2 min_raiser) | mixed sparring field (2 self + equity, tag, loose, station, pushfold, maniac) |
|---|---|---|
| v1: first EV bot, flat risk penalty | 11.3 | 15.2 |
| + real ICM (Malmuth-Harville) in place of the flat penalty | 13.5 | n/a |
| + commitment-aware fold equity | 14.2 | 14.8 |
| + absolute-strength range narrowing | n/a | 18.7 |
| + threshold-consistent fold model with continuing-range equity | 17.4 | 22.0 |
| + no current-hand stat leakage, jam-range model, fold-to-3bet stat | n/a | 24.0 |
| + uncertainty premium, resampling of thin ranges, speedups | 19.4–19.9 | 23.5–25.2 |

The leaks were found by logging every hand in which the bot busted:
- marginal 3-bet jams that relied on fold equity from players who were already pot-committed
- overbet bluffs, where an unbounded size term pushed fold probability to 97%
- calls of 100 BB jams, which happened because the jammer's open was being counted in its own stats

A/B tests of single parameters (uncertainty premium 0 / 0.05 / 0.10, opening ranges ×0.8 / ×1.25) were all within noise at 250 tables.

## Final `play.py` results

`--tables 300 --seed 1`, default seats `self×4, check_or_fold×2, min_raiser×2`:

```
upload_test: pass (10 decisions, 0 failed)
self           19.89 ± 0.60   places [293, 233, 112, 50, 158, 223, 130, 1]
check_or_fold   9.64 ± 0.47
min_raiser      0.58 ± 0.22
```

`--tables 200 --seed 3`, seats `self, check_or_fold×3, min_raiser×4`, gave self 33.39 ± 1.66 (134 wins out of 200).

`dev/arena.py --tables 300 --seed 2`, seats `self×2, equity, tag, loose, station, pushfold, maniac`:

```
self 23.50 ± 0.93 | pushfold 14.41 | equity 12.21 | tag 12.18 | loose 10.36 | station 3.43 | maniac 0.40
```

Head-to-head against 6 copies of one archetype (2 self seats, 120 tables):

| archetype | self points |
|---|---|
| tag | 23.9 |
| equity | 23.2 |
| pushfold | 21.5 |
| loose | 20.2 |
| station | 29.7 |
| maniac | 31.5 |

These head-to-head results come from an earlier version, before the last three fixes.

## Known limitations and ideas

- Cards shown at showdown are not yet used to calibrate an opponent's ranges. That would be the next modelling step.
- Preflop open thresholds by position are hand-set. Only the steal check and the facing-raise decisions are EV-driven.
- Multiway equity is the product of heads-up equities, which runs a little pessimistic.
- Stats are table-local, as the rules require, so the first orbit leans on priors.
