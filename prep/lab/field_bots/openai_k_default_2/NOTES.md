openai_k_default_2 is a tournament policy with position-aware preflop ranges, native equity estimates, public-action opponent models, and payout-aware commitment decisions. Runtime dependencies are Python's standard library and eval7.

The immutable preflop artifact contains all 169 starting-hand classes against 16 opening/continuation ranges. It was generated offline with 24,000 random-opponent trials per class and 16,000 trials per class/range pair. `build_tables.py` regenerates it; the delivered artifact is loaded once at import. Betting uses actual blinds, stacks, offered bounds, and pot size. Short stacks use fold equity and shove/reshove EV; large calls and near-money commitments use ICM. The default payout calculation is exact in quadratic time; arbitrary schedules use bounded subset calculations. Established automatic folders receive reduced winning-power estimates in payout calculations. When several opponents are all-in, bounded representative winning orders settle the side pots before comparing call/fold payout value, including simultaneous elimination order. This avoids taking a cheap chip gamble when folding secures a paid finish.

Postflop, the bot blocks known cards and conditions the most informative opponent's range on preflop role, bet size, raises, prior aggression, board texture, and observed tendencies. It uses 120 strength-stratified combinations, native runout sampling on the flop/turn, and weighted comparisons on the river. Other opponents receive a conservative joint-equity adjustment. Value sizing, selective continuation bets, semi-bluffs, and river bluff catching respond to position, stack depth, board danger, and observed folding/aggression. Revealed river bets help calibrate bluff estimates. Multiway equity and action likelihoods are approximations.

All player learning travels in serialized per-table memory. Module globals contain immutable cards, ranges, and equity tables; no opponent information crosses tables. Returned memory stayed below 1.2 KB in the final tests. A small configured memory limit is honored, and the public hand history can rebuild a lost current-hand model. The bot reduces sampling as soon as the time bank drops below 80 ms, preserving reserve for host pauses; tighter decision limits also reduce work. Cyclic GC is disabled because these objects do not form cycles. Every return passes a central offered-action/bounds guard; an outer recovery path also returns an offered action.

The build progressed through three main iterations:

1. Position/range prototype and initial mixed-table tests. The first upload passed; 20 tables scored 22.12 points per seat, but timing spikes required investigation.
2. Timing and tournament correctness: bounded posterior work, lookup-based draws, correct postflop blind order, exact payout checks, side-pot eligibility, and shared-board nuts. A 200-table mixed run scored 21.92 ± 0.70 points per seat.
3. Range sampling, revealed-action calibration, and controlled internal comparisons. A 1,500-case comparison against full-range river calculations reduced equity RMSE from 0.0327 with hash sampling to 0.0244 with strength stratification at the same 120-combination limit. Internal policy comparisons were noisy; the 1,000-table four-policy test completed 1,293,825 decisions with no failed decisions. The final version also fixes forced blind all-ins, heads-up opening size, memory recovery, and multiway payout decisions.

Validation uses `validate.py`, which calls the decision implementation directly so the recovery path cannot hide an exception. It checks 6,000 varied decisions, changed payouts, fresh instances, memory replay/recovery, exact and restricted raise bounds, forced action sets, side pots, shared nuts, and forced blind all-ins. Forty-two random payout schedules were checked against exhaustive finishing-order enumeration. Four analytical multiway payout cases check equal stacks, unequal side pots, and seat symmetry. Final validation and simulator JSON files are in `results/`.

<!-- FINAL_RESULTS -->
Final frozen-policy results (mean points per self seat; ± is the simulator standard error). All runs use the documented play.py entry point. The equal-share baseline is 12.5 points.

- Default mix: 4 self / 2 min_raiser / 2 check_or_fold: 1,000 tables, **22.41 ± 0.31 points**, 663,095 decisions; failures {'timeout': 9}; upload PASS. Full output: `results/mixed_1000_seed63.json`.
  Reported wall time: p50 49.5 µs, p99 345.1 µs, max 125112.7 µs. Maximum returned memory: 960 bytes.
- Dense mix: 7 self / 1 min_raiser: 500 tables, **14.29 ± 0.31 points**, 606,576 decisions; failures {'timeout': 5}; upload PASS. Full output: `results/dense_500_seed64.json`.
  Reported wall time: p50 55.9 µs, p99 348.9 µs, max 106525.0 µs. Maximum returned memory: 1028 bytes.
- Aggression stress: 1 self / 7 min_raiser: 200 tables, **37.28 ± 0.96 points**, 11,642 decisions; failures none; upload PASS. Full output: `results/maniacs_200_seed65.json`.
  Reported wall time: p50 107.6 µs, p99 3522.2 µs, max 63868.4 µs. Maximum returned memory: 907 bytes.
- Passivity stress: 1 self / 7 check_or_fold: 100 tables, **50.00 ± 0.00 points**, 12,249 decisions; failures none; upload PASS. Full output: `results/folders_100_seed66.json`.
  Reported wall time: p50 43.3 µs, p99 254.8 µs, max 41574.7 µs. Maximum returned memory: 615 bytes.
- 2.5× CPU-cost test, default mix: 250 tables, **22.68 ± 0.62 points**, 167,159 decisions; failures none; upload PASS. Full output: `results/slowed_2p5x_mixed_250_seed62.json`.
  Reported wall time: p50 131.4 µs, p99 1532.0 µs, max 82780.6 µs. Maximum returned memory: 910 bytes.
- 2.5× CPU-cost test, dense mix: 200 tables, **14.29 ± 0.49 points**, 243,257 decisions; failures {'timeout': 20}; upload PASS. Full output: `results/slowed_2p5x_dense_200_seed68.json`.
  Reported wall time: p50 148.7 µs, p99 5535.3 µs, max 64755.4 µs. Maximum returned memory: 1026 bytes.

Across these final simulator runs: 1,703,978 decisions, failures {'timeout': 34}, and upload tests all passed. No illegal action or exception was reported.
The independent 6,000-case suite passed. Thread CPU time was p50 110.1 µs, p99 239.7 µs, maximum 440.0 µs; the observed maximum scales to 1100.0 µs at 2.5× CPU cost. These CPU measurements exclude host descheduling.

Artifact SHA-256:
- `agent.py`: `e47c912ce9976eb8f32b78907af9ad42fba11a58db6dc26409a59922fca657fb`
- `preflop.pkl`: `892896727075a25855b6114551e87ab9531b60e222eff8372fde44d45195c794`
<!-- END_FINAL_RESULTS -->

The simulator was used only through `lab/field_kit/play.py`; no simulator implementation was read or imported. Internal comparison wrappers logged public snapshots for offline scoring and never fed logged information into any policy. The supplied SDK was used for interface validation.

Reproduce the checks with the supplied Python environment, from the workspace root:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_k_default_2/validate.py
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_k_default_2 --tables 1000 --seed 63
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_k_default_2/slow_check --tables 250 --seed 62
```

`slow_check` is a test-only wrapper that adds 1.5 times the policy's measured thread CPU cost after each decision. It approximates 2.5× total CPU cost, including the upload test with no bank. It is not the tournament entry point.

Timing limits remain subject to the host: profiling observed a 57.43 ms wall-clock decision that used only 70.75 µs of thread CPU. Earlier runs and the final large normal-speed run recorded rare wall-clock timeouts, so an absolute no-timeout guarantee is not established. The final results retain all failure counts. Local opponents are kit baselines and internal policy variants; these scores do not establish strength against the other tournament teams.
