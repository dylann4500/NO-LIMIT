# claude_equity_r2: notes

Round-2 version of `claude_equity`. The round-1 bot is unchanged in `../claude_equity/`. This version is the same design with a recalibrated opponent model and new preflop thresholds, based on the round-1 hand histories. The analysis scripts were throwaway Python run over `../claude_equity/round1/hand_history.jsonl.gz` (17,110 hands, 120 tables).

## Round 1: what cost us points

We scored 10.46 ± 0.60 points per table (fair share 12.5) and placed 19th of 22. We won 11% of tables and finished top 3 in 31%, while 7th and 8th made up 31.5% of finishes. Across the logged hands we lost about 400 chips per table.

**Style compared with the field** (computed from the events of every seat at our tables):

| | VPIP | PFR | postflop aggression | bb/100 |
|---|---|---|---|---|
| claude_equity (us) | 0.36 | 0.31 | 0.24 | −6.2 |
| top 3 by bb/100 (claude_icm, ours, claude_default_b) | 0.27–0.29 | 0.21–0.22 | 0.28–0.63 | about +14 to +18 |

We were too loose preflop and too passive after the flop.

**Postflop calls lost a lot. Postflop bets won.**

| our action | flop | turn | river |
|---|---|---|---|
| call (won / net per hand) | 37% / −144 | 41% / −391 | 31% / −947 |
| bet when checked to (won / net per hand) | 83% / +236 | 90% / +555 | 96% / +593 |

Yet we bet only 35%, 27% and 27% of the time when checked to on the flop, turn and river.

**How the field behaves:**
- It folds 44–73% to postflop bets, more often to bigger bets.
- It raises a bet only 3–6% of the time.
- It bets when checked to 49%, 35% and 24% of the time on the flop, turn and river. Bets get stronger street by street, so a late bet means strength.
- Openers fold 73–81% to 3-bets.

Our opponent model assumed opponents fold less, raise more and bet wider than this, so it overrated our equity when calling and underrated our fold equity when betting.

**Preflop results by category and effective stack:**

| category | stack | hands | net per hand |
|---|---|---|---|
| non-all-in open | under 20 BB | 291 | −102 |
| non-all-in open | 20–40 BB | 649 | −37 |
| non-all-in open | 40+ BB | 1,224 | +14 |
| flat call of a raise | under 20 BB | 153 | −74 |
| open jam | all | 258 | +148 |
| 3-bet jam | all | 150 | +228 |

The jams were profitable even though they account for most of our busts.

## Changes in r2

All the new constants sit together near the top of the agent class code, after `UNC_CALL`.

1. **`FOLD_PRIOR` 0.45 → 0.55.** This is the prior for how often an opponent folds to a postflop bet. It drives both the fold equity of our bets and what we assume about an opponent's range after they call. The field folded 44–73%. Effect: more value bets and more bluffs.
2. **`BET_STREET` (flop ×0.95, turn ×0.75, river ×0.6).** When an opponent bets, its range is narrowed using its pooled bet frequency, now scaled down on later streets. The bluff tail kept for turn and river bets is thinner (1 in 14 instead of 1 in 9). The bet-frequency prior is 0.40 and the raise-frequency prior drops from 0.10 to 0.05, so a raise reads as strong.
3. **Smaller payoff assumed for postflop calls.**
   - river: 1.0 → `CALL_RIVER` 0.9
   - turn: 0.95 → 0.88
   - flop: 0.90 → 0.85
   - an all-in call: 0.95 (it used to be scored with no reduction)
4. **Preflop:**
   - Open jam-or-fold now runs up to 15 BB effective instead of 13 (`JAM_BB`).
   - Non-jam opening ranges are 20% tighter below 35 BB (`OPEN_MID`).
   - The EV steal widening now applies only at 35 BB or more, and needs a combined fold chance of at least 45% from the players behind.
   - Flat calls of a raise below 22 BB are assumed to win back less of the pot (factor lowered by 0.10), so at short stacks the choice becomes jam or fold.

## Local results for r2

| test | r2 | comparison |
|---|---|---|
| `play.py --tables 200 --seed 1`, default seats | 20.45 ± 0.72 | r1: 19.89 |
| head-to-head: 2× r2, 2× r1, equity, tag, pushfold, loose (250 tables) | 18.97 ± 0.94 | r1: 13.72 ± 0.88 |
| head-to-head: 2× r2, 2× r1, 2× tag, 2× equity (250 tables) | 19.78 ± 0.95 | r1: 15.06 ± 0.92 |
| r2 vs a stronger version (fold prior 0.62, river ×0.5, river call 0.85), 250 tables | 17.70 | variant: 17.20 |

The stronger variant was within noise, so I kept the more moderate calibration that matches the round-1 data.

In the `play.py` run the upload test passed, the bot returned no illegal actions and raised no swallowed exceptions. CPU time per decision was 44 µs at p50 and 235 µs at p99, measured on a machine running at load average about 90. Every timeout reported locally came from wall-clock stalls of 50–175 ms on the overloaded lab machine, not from our CPU time.

---

# Round-1 notes (claude_equity), unchanged


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
