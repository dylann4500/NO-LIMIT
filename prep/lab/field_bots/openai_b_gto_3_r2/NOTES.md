# openai_b_gto_3_r2

Upload/runtime files: **agent.py, preflop.json, pushfold.json**. The two JSON lookup files are unchanged copies of round one's tables. The original `openai_b_gto_3/` directory was left unchanged.

## What round one exposed

The full leaderboard reports **11.99 points/table, SE 0.61, in 800 tables**, with **zero failed decisions**. Fair share is 12.5, so the small deficit alone is not statistically decisive. The supplied hand-history sample contains **17,162 hands from 120 tables**, of which our bot was alive for 11,522. It is a subset of the leaderboard, not 800 tables of independent hand evidence.

`analyze_round.py` reconstructs street investments, pots, legal call costs, hole-card strength, action sequences, and final stack changes from the supplied gzip. It reads only our histories and the SDK/library surface. Its saved findings are in `results/round1_analysis.json` and `.txt`.

The clearest actionable difference was insufficient pressure. Conditional on acting without an outstanding opponent bet, our observed bet frequencies were **26% flop / 23% turn / 14% river**. The leading `claude_default_b` was **73% / 74% / 69%**. Many opponents folded 60–85% of their observed river responses. These are descriptive frequencies, with different hand/position distributions, rather than causal estimates. Still, the gap justified testing more continuation bets and checked-to probes instead of only changing all-in charts.

Calling also needed more discrimination. In this sample, eight river calls with an absolute one-pair hand facing a bet at least 40% of the existing pot won once and had **-91.57 BB incremental realized call payoff**. By contrast, medium-size one-pair river calls were profitable in aggregate. This argues for distinguishing bet size and street rather than folding every bluff catcher. Absolute one-pair classification excludes paired-board two-pair hands; the sample is small and showdown-selected. First-action preflop calls facing a raise lost 631 BB over 967 hands, including all subsequent actions; that is a descriptive hand result, not the incremental EV of calling versus folding.

## Changes

- Increase heads-up continuation bets, add checked-to flop probes and delayed turn stabs, and increase selected river bluffs. Sizes are shared across value and bluffs: about 36% pot on heads-up flops, 60% turn, 67% river. Multiway pure bluffing remains infrequent.
- Bet a somewhat wider value range and make a small increase in late-position opening ranges. Reduce the maximum cold-calling range outside the big blind from 32% to 25%; big-blind defense and the solved short-stack tables are retained.
- Add independent flop/turn/river counts for betting opportunities, bets, faced bets, and folds. Use regularized field priors and observations from the current table. A high flop betting frequency no longer automatically implies an equally wide river betting range.
- Condition ranges more strongly on repeated barrels and large late-street bets. Apply extra caution to expensive weak bluff catches. Keep smaller river bets sufficiently wide: an initial, tighter version discarded too many profitable medium-size calls in replay, so that part was relaxed before final validation.
- Preserve legal-menu projection, integer raise bounds, table-local pickle memory, short-stack interpolation, payout/ICM handling, and the low-bank reserve. New counters accept older six-counter memory and reset outstanding bets at each hand.

No runtime team-name lookup, cross-table learning, opponent source inspection, or network access is used. All persistence travels in SDK memory. Runtime globals are immutable lookup data. The prior bank-reserve caveat still applies to arbitrary host descheduling, although both final 500-table runs had zero failures.

## Final validation

- **Unchanged public play.py, default mix, 500 tables, seed 2329:** **21.22 points/bot seat**, reported SE 0.45; **315,078 decisions, zero timeouts/illegal actions/exceptions**. Upload passed with zero failed decisions. p99 latency 143.3 microseconds, p99.9 201.3 microseconds; maximum memory 1,494 bytes. `results/default_final_500.json`.
- **2.5x CPU-load verification, default mix, 500 tables, seed 2521:** **21.02 points**, reported SE 0.45; **309,376 decisions, zero failures**. Upload passed. p99 latency 353.8 microseconds, p99.9 472.0 microseconds; maximum memory 1,498 bytes. This wrapper adds CPU work equal to 1.5 times measured decision CPU, rather than simulating an entire slower host. `results/slow_final_2p5_500.json`.
- **Revised versus original, four seats each, 400 tables, seed 9127:** **13.50 versus 11.50 points/seat**, **480,927 decisions, zero failures**. Upload passed. The public kit's runner was copied to a temporary directory and only its seat-loading branch extended to load the original bot through the same adapter; simulator logic and source were not inspected. `compare_original.py` reproduces this setup. `results/vs_original_v2_400.json`.
- **Upload seeds 1–20:** **20/20 pass, zero failed upload decisions**, with one ordinary table per seed and zero table failures. `results/upload_seeds_final.json`.
- **SDK stress:** 15,513 legal decisions including randomized menus, low banks, non-contiguous seats, shared-board nuts, unmatched overbets, truncated memory, transferable memory, and ICM regressions. Zero exceptions. p99 CPU 146 microseconds, p99.9 174 microseconds. `results/sdk_stress_final.json`.
- **New event-statistics regressions:** incremental batches, street separation, old-memory migration, new-hand reset, and anonymized seat labels passed (`test_round2.py`).
- **Historical replay:** reconstructs SDK states along observed paths and replays both policies. It is an audit, not a counterfactual tournament. In the final recorded replay, river continues on showdown-labeled paths fell from 99 to 65, committed call cost fell from 1,075 to 673 BB, and fixed-hole/free-runout calling EV was approximately 961 versus 979 BB. This calculation is selection-biased, ignores future betting, and cannot estimate tournament points. Monte Carlo and policy mixes cause small variation between reruns. `results/replay_summary.json`.

Earlier development reports are retained: `baseline_100.json` ran the unchanged round-one policy; `revised_200.json`, `slow_2p5_200.json`, and `vs_original_300.json` ran the first revised candidate. That candidate beat the original 14.12 versus 10.88 points in 300 mixed tables. Only the final reports above describe the shipped policy.

The actual tournament opponents are unavailable for local replay. Baseline results and beating our previous bot do **not** establish a round-two field score. Reported point SEs come from the supplied runner and do not adjust for correlation among seats sharing a table.

## Reproduction

From the workspace root, use `/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python` as `PY`:

```sh
PY=/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python
$PY lab/field_bots/openai_b_gto_3_r2/analyze_round.py
$PY lab/field_bots/openai_b_gto_3_r2/replay_round.py
$PY lab/field_bots/openai_b_gto_3_r2/test_agent.py
$PY lab/field_bots/openai_b_gto_3_r2/test_round2.py
$PY lab/field_kit/play.py lab/field_bots/openai_b_gto_3_r2 --tables 500 --seed 2329
$PY lab/field_bots/openai_b_gto_3_r2/verify_slow.py --tables 500 --seed 2521 --factor 2.5
$PY lab/field_bots/openai_b_gto_3_r2/compare_original.py --tables 400 --seed 9127
```

Only the permitted public kit/SDK, our original bot, and our supplied round-one data were read. Integration tests run the public runner (or the described seat-loading-only copy); no private simulator files were read or imported by the bot or analysis scripts.
