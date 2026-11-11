# openai_b_aggro_4

The submission is `agent.py` and `preflop.json`. Runtime dependencies are the SDK, eval7, and Python's standard library. The remaining files are development tools and test reports.

## Strategy

An aggressive tournament strategy built around profitable steals and disciplined responses to resistance:

- Open roughly 18% from early position, widening toward 53% on the button and 68% in the small blind before opponent adjustments. Deep suited connectors get an opening-range benefit. Opens start at 2.15 BB; limpers increase the size.
- Learn first-action folds, voluntary participation, preflop raises, responses to reraises, and postflop aggression/folding. Confidence thresholds and priors prevent a few early folds from immediately classifying everyone as an automatic folder. Confirmed folders are attacked much more widely; persistent raisers get larger value raises.
- Use seven precomputed preflop equity ranges for all 169 starting hands. `build_tables.py` used 60,000 Monte Carlo trials per hand/range, with combination-weighted opening percentiles. No tournament observations went into these tables.
- Use fold-equity-based short-stack shoves, position-aware defending, value three-bets, occasional suited-ace blocker bluffs, and selective implied-odds calls. Large jams and repeated raises from ordinary opponents receive much tighter range assumptions.
- Postflop, sample blocker-compatible opponent combinations and weight them by the betting line, actual hand contribution, and draws. Use eval7 for fast runout equity; use exact river equity against unconditioned ranges. Multiway adjustment is deliberately conservative rather than a full multiway solver.
- Value bet, make frequent small flop continuation bets, semibluff useful draws, and barrel selectively. Increase pressure when public action statistics support over-folding. Preserve medium showdown value instead of turning everything into a bluff.
- Apply payout-aware risk adjustments, with exact ICM for expensive heads-up calls when 3–5 tournament players remain. Read the actual blinds and payouts from the supplied state. Exclude uncallable overbet chips from calling pot odds.
- Distinguish board-only pairs/trips/quads from a made hand supplied by our hole cards. Call forced all-in blinds with appropriate equity, and never fold an unbeatable shared board to an overbet.

All opponent information is serialized into the returned memory; nothing learned is stored on `self`, in globals, or across tables. Observed maximum memory was 337 bytes. Import-time card and equity tables are immutable lookup data.

## Runtime and legality

The equity loop uses rank-mask lookup tables and reuses card lists and range tuples to avoid repeated Python allocations. A per-decision clock budget reduces the number of sampled combinations when time is tight; it becomes more conservative when the table's bank is low. The usual target is 250 microseconds on this machine, leaving room for the specified 2.5× slowdown. Preflop uses lookup values rather than simulations.

Every returned action passes a final offered-kind check. Raise totals are integers clamped to the exact offered bounds, including short all-in raises. Free checks are preserved. There are no network calls or decision-time file reads.

The time bank is still necessary for occasional garbage collection or operating-system pauses. A sampled-equity budget cannot prevent a process from being suspended longer than the entire bank. Historical contended runs are retained rather than hidden; see the timing results below.

## Build iterations

1. Implemented the complete strategy and memory-based opponent model. The first 100-table default run scored 20.51 points per self seat, with zero failed decisions. Profiling identified excessive set construction in postflop draw classification.
2. Replaced those operations with rank-mask tables and reduced allocations. A 200-table default run scored 21.49 points per self seat. Tested folder-heavy, raiser-heavy and seven-copy tables. Compared against a frozen first-version bot; the comparison was close and does not establish a significant strategic advantage over that reference.
3. Improved opponent classification, fixed paired-board strength, unmatched overbets, forced all-in blinds and certain chops. Added exact unconditioned river equity, a sampling budget, contract tests, and slower-workload checks. The final source is frozen before the isolated validation runs below.

## Reproducing tests

Run from the repository root with `/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python`:

```sh
PYTHONPATH=lab/fake_sdk /Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_aggro_4/verify.py
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_b_aggro_4 --tables 1000 --seed 20261106
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_aggro_4/bench.py --tables 200 --seed 81499 --workload 3 --seats self,self,self,self,self,self,self,min_raiser
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_aggro_4/bench.py --tables 300 --seed 6701 --seats self,self,rock,rock,station,station,nit,nit
```

`bench.py` extends the published field-kit runner through its SDK adapter. Its optional workload multiplier executes three complete decisions from the same supplied memory per turn and returns the first result. It does not change the submitted Agent or the simulator. `test_opponents.py` supplies independent tight-value, calling-station and very-tight opponents. Only the field kit, SDK, and our own bot/test files were read; no simulator source was read or imported directly.

`verify.py` checks 6,000 varied SDK states with 2–8 seats, all four streets, short stacks, narrow raise bounds, multiple payout schedules, absent raise actions, and replayed events. It also checks all 1,326 starting combinations map to the 169 keys, ICM payout conservation and scale invariance, side-pot pricing, board-only hand categories, forced all-in blind calls, and certain chops.

Equity estimates are stochastic, so a dealing seed does not make every score identical between runs. These are local synthetic opponents, not evidence of a solved strategy against the unknown tournament field.

## Final validation

The final isolated suite used the same frozen source throughout. Raw reports, complete commands, and source hashes are retained in `results/`.

- **Default field, 1,000 tables, seed 20261106:** 21.78 points per self seat, reported standard error 0.32; fair share 12.50. Four self seats, two check-or-fold and two min-raiser seats. Self finishes were `[986, 908, 529, 130, 362, 731, 345, 9]`. The runner recorded **675,781 decisions and zero failures**. Upload passed with 13/13 valid decisions. See `results/default_1000.json`.
- **Three complete decisions per turn, 200 tables, seed 81499:** seven self seats and one min-raiser; **222,460 turns and zero failures**. Upload passed. p99 total wall time for all three decisions was **682.1 microseconds**; maximum wall time was 25.45 ms, covered by the bank. This deliberately runs more decision work than the specified 2.5× slowdown. See `results/workload_3x_200.json`.
- **One self against seven folders, 100 tables:** **50.00 points**, 100 first places; zero failures. See `results/folders_100.json`.
- **One self against seven min-raisers, 100 tables:** **41.40 points**, 57 first places and 43 second places; zero failures. See `results/raisers_100.json`.
- **Seven self copies and one min-raiser, 100 tables:** **14.29 points** per self seat; zero failures. See `results/dense_100.json`.
- **Custom tight/calling field, 300 tables:** two self, two rock, two station and two nit seats; **24.95 points** per self seat, reported standard error 0.92; zero failures. This report also counts the independent SDK opponents' decisions. See `results/custom_field_300.json`.
- **Upload robustness, seeds 1–25:** **25/25 passed**, **270 upload decisions, zero failures** with the strict no-bank upload test; the accompanying 25 one-table runs also had zero failures. See `results/upload_25_seeds.json`.
- **Contract tests:** all **6,000 SDK states**, all starting combinations, memory retries, ICM checks and explicit poker edge cases passed. Maximum serialized memory was **337 bytes**. See `results/contract_checks.json`.

Across the six main final scenarios, the runner recorded **1,313,904 decisions with no timeout, illegal-action or exception failures**. The default-field wall latency was p50 **23.7 µs**, p99 **240.4 µs**, p99.9 **1,881.3 µs**, maximum **33,588.8 µs**. Occasional pauses exceeded the nominal millisecond and used the bank; none exhausted it in the final isolated suite.

An additional 100-table instrumented run recorded act CPU time of p99 **212.7 µs** and p99.9 **253.9 µs**. Multiplying by 2.5 gives about **532 µs** and **635 µs**, respectively. The slowest observed CPU decision was 5.9 ms, consistent with an occasional collection/pause rather than the normal equity loop; the bank is needed for those tails. The equity routine itself had maximum measured CPU time **230.3 µs**. See `results/cpu_profile.json` and `results/profile_100.json`.

Historical timing failures are explicitly retained: a pre-budget 3× run had one timeout during a 69 ms wall spike. Simultaneously running a default and a 3× test later produced pauses up to 166.5 ms, with 51/677,203 and 705/228,994 timed-out decisions respectively. Those reports are in `results/iterations/`. They are not part of the final isolated pass counts. The bot cannot guarantee a legal response arrives before a wall-clock deadline if its process is paused longer than its entire bank; the final CPU profile and isolated workload test provide the relevant computational headroom evidence.

Final runtime source SHA-256: `51b133cb62f2871f4e5a32ef08b1e2ea31adfd9aba86bcec46c01ca8db2153f8`.
Equity-data SHA-256: `85dfa5cc8b086856e5259a4cd612637355515a00a1f53bb71ab216170d9849b6`.
The complete development-file manifest is `results/source_sha256.json`.
