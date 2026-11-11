# openai_k_default_1

Tournament bot built and tested on 2026-11-06 using only the field kit, public SDK,
and permitted libraries. No simulator implementation files were read or imported
by the bot, training tools, or tests. Matches were run through `play.py`.

## Design

The bot combines positional preflop ranges, a Bayesian postflop range model,
opponent adaptation, and payout-aware tournament decisions.

- **Preflop:** frozen equity tables for all 169 hand classes against eleven
  nested ranges. Position, effective blinds, limpers, opening versus reraising,
  short-stack shoves, and observed VPIP/PFR change the ranges and sizing.
  Premium range ordering is explicit rather than ranking hands solely by equity
  against random cards. Multiway equity includes a correlation correction.
- **Postflop:** candidate ranges exclude known cards and are weighted by betting
  and calling evidence on the most recent two streets. Value, draw and bluff
  likelihoods depend on aggression and bet size. A small neural equity surrogate
  handles common high-card, pair and two-pair decisions. Trips and better use
  direct native evaluation; expensive close heads-up calls receive a native
  refinement when time permits. Multiway estimates include nut-draw equity
  floors. Value betting, protection, continuation bets, selective blocker bluffs
  and draw semibluffs use these estimates.
- **Adaptation:** per-table statistics distinguish tight folders, callers and
  players who repeatedly raise. A high opening frequency alone does not identify
  a player as a constant raiser. Observed repeated small reraises and public
  showdowns supply additional evidence. Consistent folders are attacked widely;
  persistent raisers are value-targeted and bluffed less.
- **Tournament risk:** exact top-three ICM has a fast closed-form implementation,
  including at eight players. A subset solver handles other payout structures
  in smaller fields. Meaningful calls use win/fold/lose utility, and other
  decisions use a stack-sensitive bubble premium. A short caller's inaccessible
  side pot stays outside their winnings in both pot odds and ICM. This matters
  when several opponents go all-in and folding can secure a paid position.

All evolving information lives in serialized `memory`. Immutable cards, ranges,
draw flags and model weights load at import, so copies can alternate between
tables without retaining private table state on `self` or in globals.

## Runtime and legality

- Every action goes through one final legality adapter. It uses only offered
  kinds, rounds raise sizes to integers, and clamps totals to the offered bounds.
- Memory peaked at approximately 1.1 KB in final matches, below the free 16 KB
  allowance. Runtime assets are `preflop.json`, `draws.bin`, and `equity_model.npz`.
  There are no subprocesses, network requests, training, or filesystem writes
  inside a decision.
- Candidate and rollout counts are bounded. A decision deadline skips optional
  work. With the default 100 ms bank, a small reserve policy takes over below
  65 ms; the threshold scales down for smaller configured banks. This path does
  no rollouts, neural inference, or recursive ICM. The no-bank upload uses it too.
- Decision objects are acyclic. Cyclic GC is temporarily disabled during the
  call and the caller's original setting is restored in `finally`, keeping
  unrelated heap collections out of the timed decision.

## Development and training

Three broad iterations were tested: an initial range player, corrected ranges
and opponent models, then the fast equity model and timing/ICM refinements.
The initial 30-table run scored 17.16 points per bot with timing failures. A
120-table range revision scored 19.31. Profiling identified both expensive range
work and large differences between CPU time and wall time. The final version
uses precomputed draw flags, bounded ranges, fast inference, and the bank reserve.

`build_tables.py` generates the preflop tables and straight-draw lookup.
`train_equity.py` trains a NumPy-only 231–192–96–1 network from 240,000 synthetic
deals and direct range-model labels, with 30,000 held out. No tournament results
or hidden simulator data are training inputs. Validation RMSE was 0.0546 equity;
high-card and pair RMSE were 0.0303 and 0.0473. Full metrics are in
`training_report.json`. The bundled weights are ready to use; no training is
needed to upload.

## Tests

`test_agent.py` passed all 13 tests. They cover 2,500 randomized legal-action
contracts, 360 multi-street/large-pot decisions, short all-in bounds, replayed
events, interleaved agent copies, memory size, 3,000 draw-lookup comparisons,
shared board nuts, opening versus reraising ranges, loose-player classification,
ICM against exhaustive permutations under several payouts, multiway elimination
risk, side-pot ICM, and restoration of the caller's GC setting.

Final results below use the runtime files identified by SHA-256 in
`results/manifest.json`. Points and places are those reported by the kit; at the
hand cap points use ICM, so first place by stack need not award exactly 50.

- **Default mix, 500 tables, seed 73:** **21.69 ± 0.45 SE points per bot**, versus
  12.5 fair share. Upload passed, **zero failed decisions in 380,851 decisions**.
  Median latency 59.8 µs; p99 345.3 µs. Maximum memory 1,049 bytes.
  Raw report: `results/default_500.json`.
- **One bot versus seven check-or-fold players, 200 tables, seed 211:**
  **49.77 ± 0.02 points**, ranked first in all 200 tables. Upload passed and
  zero failed decisions. Raw report: `results/passive_200.json`.
- **One bot versus seven constant raisers, 200 tables, seed 307:**
  **39.30 ± 0.71 points**, top two in all 200 tables. Upload passed and zero
  failed decisions. Raw report: `results/raisers_200.json`.
- **Seven copies versus one constant raiser, 200 tables, seed 401:**
  **14.24 ± 0.49 points per copy**; the raiser averaged 0.35. Upload passed.
  There was **one timeout in 252,748 decisions**; the reported maximum wall
  latency was 96.66 ms. There were no illegal actions or exceptions.
  Raw report: `results/mirrors_200.json`.
- **Instrumented repeat of the mirror stress, 200 tables, same seed:**
  **14.27 ± 0.49 points**, zero failed decisions in 259,138 decisions. The
  wrapper measured CPU and wall time separately: its largest wall pause was
  71.01 ms while the decision used 374.0 µs of CPU. CPU p99 was 280.0 µs.
  Reports: `results/mirrors_profile_200.json` and `results/mirrors_cpu.json`.
- **2.5× CPU-cost slowdown, default mix, 200 tables, seed 117:**
  **22.55 ± 0.69 points**, upload passed, **zero failed decisions in 156,167
  tournament decisions**. The external test wrapper padded each call to 2.5×
  its measured thread CPU time. Unpadded CPU p99/p99.9 were 283.6/362.1 µs,
  equivalent to 0.709/0.905 ms at 2.5×. The rare maximum was 1.221 ms after
  scaling, absorbed by the bank. Raw reports: `results/slow_200.json` and
  `results/slow_cpu.json`.

The additional mirror timeout is retained in the report rather than counted as
a clean run. Earlier local runs also showed wall-clock stalls of tens of
milliseconds while direct CPU benchmarks were much shorter. The bank policy is
intended to absorb these tails. The slowdown test is a CPU-cost approximation,
not a run on the physical tournament machines. Opponent-strength evidence here
is limited to the provided baselines and mirror copies.

Across these six final match configurations/runs there were 1,094,289 tournament
decisions, no illegal actions or exceptions, and the one documented wall-clock
timeout. Every upload test passed.

## Reproduce

Run from the workspace root with the supplied Python environment:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_k_default_1/test_agent.py
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_k_default_1 --tables 500 --seed 73
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_k_default_1 --tables 200 --seed 307 --seats self,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_k_default_1/stress.py --tables 200 --seed 117 --multiplier 2.5
```

Sampling and wall-clock scheduling can change match trajectories between runs.
