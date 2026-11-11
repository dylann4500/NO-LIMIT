# Round 2 bot: openai_k_default_2_r2

The tournament entry point is `agent.py`; its only data dependency is the immutable `preflop.pkl` copied from round 1. Runtime dependencies remain the standard library and eval7. The original `openai_k_default_2` source and data were left unchanged.

## What round 1 exposed

The leaderboard reported 12.69 ± 0.64 points per table over 800 tables, with no failed decisions. The supplied history is a subset: 17,178 hands at 120 tables, including hands after our elimination. There are 11,745 hands in which our starting stack is positive, and 17,973 reconstructed decisions. `analyze_round.py` reconstructs public SDK snapshots using only the supplied JSON histories; it never reads or imports simulator implementation code.

Raw losing-hand totals would misleadingly count already-posted blinds as the cost of calling. Measuring each first preflop call relative to folding at that decision gives:

- All 1,610 initial preflop calls/completions together: +53.8 BB relative to folding.
- Offsuit hands: −444.3 BB in 1,032 calls.
- Small-blind calls: −362.4 BB in 365 calls.
- Big-blind calls: +511.1 BB in 1,061 calls. Broad big-blind defense, especially against late opens, should be preserved.
- Pocket pairs: +268.2 BB; suited hands: +229.9 BB. A blanket reduction of every calling range would discard useful hands.

Large losses also showed weak pairs and high cards following multiple large bets. On 176 revealed turn-call observations, the original model estimated roughly 50% equity against the bettor, whereas equity against its revealed hand averaged about 44.5%. These revealed observations are selected by showdown and are not an unbiased sample of all bets.

The old posterior independently rejected hands from a 120-combination range, sometimes leaving very few candidates. It mostly assessed earlier aggression using the current board rather than the board visible when the action occurred. It also let high ordinary betting frequency make a raise almost as broad as an ordinary bet. Across the public field histories, revealed flop raises contained only 4 weak hands out of 155, compared with 635 weak hands out of 1,333 opening flop bets. Raises and bets need different models.

There is also profitable aggression to recover: opponents folded 238/366 times to our larger turn bets and 157/211 times to our larger river bets. These rates are conditional on our actual historical betting range; they justify selective additional bluffs, not assuming that every hand can bluff profitably.

## Changes

1. Tightened dominated offsuit cold calls, especially from the small blind and against early opens. Kept wider big-blind defense against steals and retained pair/suited-hand opportunities. Expanded value reraises modestly against genuine wide opening ranges.
2. Added explicit equity-realization margins for weak postflop showdown hands when future streets still require decisions. All-in calls continue to use their full runout equity and the existing payout-aware thresholds.
3. Conditioned candidate hands on each earlier action and the board then visible. Historical evidence is tempered, particularly on the river, to account for correlated bluffing strategies rather than treating each bet as independent proof of strength.
4. Replaced independent rejection with systematic weighted resampling before native flop/turn equity evaluation. River comparisons use the actual likelihood weights directly.
5. Separated the likelihood of raises from opening bets. Ordinary aggression no longer makes a large raise uniformly loose. Publicly revealed weak raises and unmistakable serial minraising can still relax the model. Straights/sets/two pair lose relative quality on flush boards, and nonflush holdings receive extra discount when explaining a raise on such a board.
6. Added per-street faced-bet/fold counters in serialized table memory. Selective turn barrels and river stabs use these observations with modest field-informed priors. Bluffing remains reduced against calling stations and during payout pressure. A continuing barrel requires that the opponent called the previous street.
7. Preserved the existing legal-action guard, defensive recovery, actual configuration support, ICM/side-pot calculations, shared-board-nuts handling, and time-bank sampling reductions. No opponent identity or mutable learning crosses tables.

## Validation and local results

Final frozen policy (mean points per self seat; ± is the kit's reported standard error):

- **Direct comparison, 1,000 tables, seed 222:** 4 revised / 4 original. Revised **12.98 ± 0.29**, original **12.02 ± 0.28**. 1,261,692 SDK decisions; no failures. `results/head_to_head_1000_final.json`.
- **Default mix, 1,000 tables, seed 223:** 4 revised / 2 min_raiser / 2 check_or_fold. **23.01 ± 0.31**. 650,741 decisions; no failures. `results/mixed_1000_final.json`. For context, the unchanged original scored 22.09 ± 0.49 over a separate 400-table seed-210 run; this is not a paired comparison.
- **Aggressive stress field, 500 tables, seed 225:** 2 revised / 2 original / 4 synthetic pressure policies. Revised **14.00 ± 0.53**, original **12.36 ± 0.55**, pressure **11.82 ± 0.41**. 509,706 decisions; no failures. `results/pressure_field_500_final.json`.
- **2.5× CPU cost, default mix, 500 tables, seed 224:** **23.25 ± 0.43**. 327,466 decisions; no failures. p99 wall time 709.6 µs. `results/slowed_mixed_500_final.json`.

These final runs total **3,000 tables and 2,749,605 SDK decisions, with zero illegal actions, exceptions, or timeouts**. Every upload test passed with zero failed decisions. Comparison-run decision counts include the original and synthetic SDK agents as well as the revised bot. Maximum returned memory was 1,117 bytes.

The final 6,000-decision independent suite passed, as did all five focused round-two regressions. Thread CPU time in the independent suite: p50 115.5 µs, p99 193.2 µs, maximum 410.6 µs. `results/validation_final.json` records the details. An offline replay of the recorded decisions removed 472 original preflop calls; the 469 first-divergence folds would have saved 595.9 BB relative to those hands' recorded outcomes. This is a diagnostic on the sample used for development, not an independent estimate of future points. The revised mean equity on the 176 revealed turn calls was about 44.0%, compared with 44.4% against the revealed hands. `results/replay_final.json` contains the other action changes and calibration results.

Earlier variants and stress runs are retained under `results/` with explicit `v1`, `v2`, or `v3` names; only the four runs above use the exact final artifact. `results/final_summary.json` and `results/artifact_manifest.json` record the final run list and hashes.

Final artifact SHA-256:

- `agent.py`: `f26b09b2617cc4ee616ac07f214a738d00f8ef5a8500fd86ee6b3ea221a81077`
- `preflop.pkl`: `892896727075a25855b6114551e87ab9531b60e222eff8372fde44d45195c794`

The original agent still matches its supplied round-one hash, `e47c912ce9976eb8f32b78907af9ad42fba11a58db6dc26409a59922fca657fb`.

The kit baselines and the synthetic pressure policy are local checks, not a reproduction of the tournament field. The comparison harness executes the supplied `play.py` through `runpy` and registers extra SDK agents using the loader/adapter already exposed there; it does not read or directly import simulator modules. `test_pressure/agent.py` is a stress opponent constructed from broad aggregate betting tendencies, not another team's source.

`validate.py` invokes `_act` directly, so the defensive exception fallback cannot hide a failure. It checks 6,000 varied decisions, altered payouts and offered actions, memory replay/recovery, exact raise bounds, shared nuts, forced blind all-ins, and side pots. It also checks 42 random payout schedules against exhaustive finishing-order enumeration and four analytical multiway cases. `test_round2.py` adds five checks for street-specific statistics and old-memory extension, strong versus weak raise evidence, monotone-board hand quality, the small-blind offsuit calling leak, and preserving weak board-playing hand quality on flush-threat boards.

All diagnostics and test wrappers are development tools. The submitted runtime loads only `agent.py` and `preflop.pkl`. The history-derived snapshots can be regenerated by `analyze_round.py`; no history files or revealed private cards are read by the tournament bot.

Reproduce from the workspace root using `/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python`:

```sh
POKER_PY=/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python
"$POKER_PY" lab/field_bots/openai_k_default_2_r2/validate.py
"$POKER_PY" lab/field_bots/openai_k_default_2_r2/test_round2.py
"$POKER_PY" lab/field_kit/play.py lab/field_bots/openai_k_default_2_r2 --tables 1000 --seed 223
"$POKER_PY" lab/field_bots/openai_k_default_2_r2/compare_kit.py lab/field_bots/openai_k_default_2_r2 --tables 1000 --seed 222 --seats self,self,self,self,baseline,baseline,baseline,baseline
"$POKER_PY" lab/field_bots/openai_k_default_2_r2/compare_kit.py lab/field_bots/openai_k_default_2_r2 --tables 500 --seed 225 --seats self,self,baseline,baseline,pressure,pressure,pressure,pressure
"$POKER_PY" lab/field_kit/play.py lab/field_bots/openai_k_default_2_r2/slow_check --tables 500 --seed 224
```

`slow_check` adds 1.5 times the measured thread CPU cost to each decision, including upload, approximating the documented 2.5× slower tournament machines. A per-decision wall time above 1 ms is not necessarily a timeout because the tournament provides a time bank. Zero observed timeouts does not establish a guarantee against arbitrary host descheduling.
