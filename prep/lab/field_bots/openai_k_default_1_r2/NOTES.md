# openai_k_default_1_r2

Round-two revision of `openai_k_default_1`, built on 2026-11-06. The original
directory is unchanged. Runtime files are **agent.py, preflop.json, draws.bin**.
Everything else here is development code or an analysis/test result.

## What round one showed

The leaderboard scored the original bot **10.49 +/- 0.55 points over 800 tables**,
with a 6.4% win rate, 35.6% top-three rate, and no failed decisions. Fair share is
12.5 points. The provided histories cover a sample of **120 tables, 17,232 hands,
and 13,200 hands in which our bot was still alive**; hands after our elimination
are excluded from our chip-flow analysis.

The main actionable findings were:

- **Missed pressure after checks.** Opponents folded 746 of 1,150 responses to
  river bets (64.9%). We checked 612 of 740 free river decisions (82.7%). The old
  range model ignored checks entirely and retained only two streets of positive
  evidence. A caller could stay implausibly strong after checking multiple
  streets, preventing both thin value bets and profitable probes/bluffs.
- **Reraises were much stronger than ordinary bets.** Among revealed opposing
  reraises, median made-hand strength against a fixed uniform legal range was
  97.3rd percentile on the flop (160 observations), 96.9th on the turn (59), and
  94.9th on the river (28). The old model gave too much weight to weak pairs and
  air in these ranges. For example, KQ on K-6-2 was assigned about 72% equity
  when facing a large reraise; the revealed opponent held AK. The revised model
  assigns about 42% on this recorded decision. This example illustrates the
  range change, not a claim that every top-pair call was wrong.
- **Too little preflop initiative.** Only 116 of our 2,190 preflop raising actions
  were reraises, versus 2,952 of 16,575 for opponents. The combination of a high
  equity threshold and positional priors often flatted hands suitable for value
  three-bets. Four- and three-player hands also produced the largest aggregate
  chip losses, consistent with a need to contest more pots as the table shrinks.

Showdown reveals are a selected sample: these percentiles are descriptive, not
unbiased labels for every betting range. Chip losses alone do not prove a
decision was bad. The changes therefore combine the public observations with
separate local match tests rather than fitting a policy to revealed winners.

`summarize_histories.py` reproduces public action frequencies, chip flows and
reraising-strength summaries in `results/field_summary.json`. `analyze.py`
reconstructs documented SDK states at our decisions and replays the original
range estimates; `--candidate` evaluates the revised model on those same
recorded states. This reconstruction assumes a full time bank because the
histories do not report the bank remaining. It does not estimate counterfactual
tournament scores. The two replay files and summaries are retained in results.

## Changes

- Include checking evidence and retain all three streets in the posterior.
  Checks by frequent bettors reduce the weight of their strongest hands.
- Tighten true postflop reraises substantially, especially turn/river reraises,
  while keeping ordinary continuation bets and strong draws in broader ranges.
- Replace the neural surrogate with bounded native eval7 range evaluation for
  all categories. The surrogate was trained on the old likelihoods and would
  give inconsistent answers after this change. It and NumPy are no longer
  runtime dependencies. Candidate limits are 104 on earlier streets, 128 on the
  river, and 64 for the secondary opponent, with 384 native rollouts where needed.
- Store separate table-local fold/opportunity counts for each postflop street.
  Seven-observation priors use the observed field rates; actual opponents quickly
  move these estimates. Use them for more frequent continuation bets, turn
  probes after checks, and river bluffs with weak showdown equity.
- Widen positional opening ranges modestly and lower the value three-bet equity
  threshold against a single raise from 61.5% to 59%, retaining the bubble risk
  adjustment and the tighter threshold against multiple raises.

The original ICM, side-pot handling, final legality adapter, bank reserve policy,
and GC protection remain. Memory schema 3 adds six counters per seat. All mutable
table information remains serialized in SDK memory; nothing is carried between
tables. No opponent identities or tournament table identifiers drive the policy.

## Validation and local results

All listed uploads passed. All listed runs had **zero illegal actions,
exceptions, or timeouts**. Occasional decisions exceeded the base 1 ms and were
absorbed by the time bank. Points are the runner's payout/ICM results.

- **Four revisions vs four round-one copies, 250 tables, seed 1301:** revision
  **14.39 +/- 0.60**, original **10.61 +/- 0.52**; revision won 164 of 250 tables.
  343,672 combined SDK decisions. `results/pressure_compare_250.json`.
- **One revision vs seven round-one copies, 400 tables, seed 1319:** revision
  **17.85 +/- 1.05**; 98 firsts and 187 top-three finishes. Reference copies
  averaged 11.74. 556,461 combined SDK decisions. `results/one_vs_old_400.json`.
- **Final independent seed, one revision vs seven round-one copies, 600 tables,
  seed 1511:** revision **16.53 +/- 0.82**, reference **11.92 +/- 0.27**;
  126 firsts and 272 top-three finishes. Upload passed; no failures in 830,795
  combined SDK decisions. `results/final_one_vs_old_600.json`.
- **More aggressive reference sensitivity, 300 tables, seed 1423:** revision
  **12.26 +/- 0.51**, compared with **10.33 +/- 0.46** for the original in a
  separate run with the same seed and opponent mix. The aggressive reference
  scored 12.74 against the revision, so this is a close matchup, not a demonstrated
  edge. This development opponent only increases the original bot's continuation
  bets and probes; it is not another team's implementation. Reports are
  `results/pressure_sensitivity_300.json` and
  `results/old_pressure_sensitivity_300.json`.
- **Default kit mix, 250 tables, seed 923:** **21.77 +/- 0.63**, 195,243 decisions,
  p99 200.4 us. `results/pressure_default_250.json`.
- **One revision vs seven constant raisers, 200 tables, seed 307:**
  **39.40 +/- 0.71**, top two in every table, 14,702 decisions.
  `results/raisers_200.json`.
- **One revision vs seven check-or-fold players, 200 tables, seed 211:**
  **49.78 +/- 0.02**, first in all 200 tables, 32,185 decisions.
  `results/passive_final_200.json`.
- **Seven revisions vs one constant raiser, 200 tables, seed 401:**
  **14.27 +/- 0.49** per revision, 253,395 decisions; p99 234.1 us, maximum
  serialized memory 1,178 bytes. `results/mirror_final_200.json`.
- **2.5x CPU-cost stress, default mix, 200 tables, seed 117:**
  **21.85 +/- 0.70**, 153,439 tournament decisions. Unpadded CPU p99/p99.9 were
  226.4/299.3 us, or 0.566/0.748 ms after scaling. The rare scaled CPU maximum
  was 1.206 ms. The bank absorbed all overruns; upload passed without a bank.
  `results/slow_final_200.json` and `results/slow_final_200_cpu.json`.

The 15 unit/contract tests passed, including 2,500 randomized legal-action
states, 360 multi-street decisions, ICM against exhaustive permutations, shared
board nuts, side pots, event replay, copy interleaving, memory size and GC state.
New tests check that checks weaken ranges, reraises strengthen them, and street
fold counters update independently. `results/unit_tests.txt`.

The native-only first experiment scored 13.80 against 11.20 for the original in
150 tables; adding pressure/preflop changes produced the 250-table result above.
These earlier comparisons preceded removal of unused neural-loading code; the
playing policy was the same. The final runtime files are hashed in
`results/manifest.json`. Local references and simple baselines are not the full
tournament field, and runner standard errors for multiple copies do not account
for dependence between seats at the same table.

## Reproduce

Use `/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python` from the workspace
root (shown as `$PY` below):

```sh
$PY lab/field_bots/openai_k_default_1_r2/summarize_histories.py
$PY lab/field_bots/openai_k_default_1_r2/analyze.py
$PY lab/field_bots/openai_k_default_1_r2/analyze.py --candidate
$PY lab/field_bots/openai_k_default_1_r2/test_agent.py
$PY lab/field_kit/play.py lab/field_bots/openai_k_default_1_r2 --tables 250 --seed 923
$PY lab/field_bots/openai_k_default_1_r2/compare.py lab/field_bots/openai_k_default_1_r2 --tables 250 --seed 1301 --seats self,self,self,self,old,old,old,old
$PY lab/field_bots/openai_k_default_1_r2/stress.py --tables 200 --seed 117 --multiplier 2.5
```

`compare.py` executes the public `play.py` entry point and registers extra SDK
agents through that runner's existing adapter. `stress.py` launches `play.py`
with a development wrapper. No simulator implementation files were opened or
directly imported by our bot, analysis, or development scripts. No network calls,
subprocesses, training, or file writes occur in the playing bot's decisions.
