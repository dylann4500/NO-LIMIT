# openai_a_default_1_r2

Runtime: `agent.py` and `preflop.json`. Standard library, `eval7`, and the documented `poker_agent_sdk`. All decision adaptation stays in per-table `memory`; no opponent identities or cross-table observations enter the strategy. The original directory was left unchanged. Simulator source was neither read nor imported by our analysis, bot, or testing helpers; tournament games were run through the supplied `lab/field_kit/play.py`.

## Round 1 diagnosis

Leaderboard: 12.15 ± 0.56 points in 800 tables, 41.8% top three but only 7.5% wins, with zero failures. This suggested a strategic rather than operational problem. The supplied history covers 120 complete tables: 17,261 hands, including 13,347 with our bot still alive and 17,524 decisions by our bot. Public-SDK replay of the original reproduced 99.47% of recorded action kinds; Monte Carlo randomness, timing-dependent sampling, and approximate replay legality account for discrepancies.

The actionable findings were:

- **Fold estimates were wrong against aggressive players.** The old denominator treated every opponent postflop bet as a refusal to fold, even when it was the first wager. The field folded on 66.8% of river responses, yet our model often labeled frequent bettors difficult to bluff. Our bot bet only 57/530 free river opportunities (10.8%, versus the field's 25.4%) and folded 118/161 river responses (73.3%). It also missed flop probes and delayed continuation bets.
- **Position priors were mismatched to the field.** Unopened raise frequencies were approximately 15.6% eight-handed under the gun, 51.8% on the button, 61.9% in the small blind, and 80.6% heads-up on the button. Our opening schedule was too wide early and too narrow late; our opponent model assigned only about 50% to an ordinary heads-up button open.
- **Shove calls depend on tournament stage.** Observed 7–13 BB open shoves faced calls/reraises about 15.7% of the time four-handed versus 31.0% heads-up. The old model overestimated bubble calls and underestimated heads-up calls. Our four-handed hands lost 241.9 BB in this sample, while heads-up button hands lost 53.6 BB over 206 hands. These are descriptive samples, not isolated causal estimates.
- **Rare strong hands could vanish from posterior samples.** One queen-high-flush loss had estimated river equity of 100% despite a possible ace-high flush. Flop particles survived across new boards without ensuring support for newly important nut combinations. All made flushes also received identical aggression strength, exaggerating weak flushes against large raises.

`analyze.py`, `field_stats.py`, `history_analysis.json`, `field_stats.json`, and compressed replay diagnostics preserve the investigation. Showdown equity summaries are selected by reaching showdown and should not be interpreted as unbiased range calibration.

## Changes

1. Memory version 4 tracks actual facing-wager responses and separate street fold counts, with small samples shrunk toward field priors. First bets and checks no longer corrupt fold estimates.
2. Position-specific opening/range priors, cheaper 2.1 BB ordinary opens, somewhat wider value reraises, and stage-specific shove response assumptions. Existing online adaptation, ICM calling premiums, deep-shove caution, and reference-opponent exploits remain.
3. More flop continuation bets and position probes, more delayed turn bets, and selective half-pot river bluffs against observed folders. River continuation estimates allow weaker pairs to pay small value bets, with 30%-pot sizing for thinner value.
4. Stronger turn/river raise filtering, especially repeated or oversized raises. First-bet aggression no longer flattens raise likelihoods as strongly.
5. Refresh sampled ranges when the board changes. Protect nut-flush combinations on three-flush boards and rare two-card nut straights, in addition to pocket sets; stratum weights preserve their frequency. Evaluate prior-street evidence again after refresh. Distinguish nut and lower flushes, non-nut straights, and vulnerable made hands on flush boards. A deadline cannot stop before protected combinations and a minimum ordinary sample are processed.
6. Retain the single legal-action gateway, bounded serialized memory, bank-aware sample sizes, soft deadlines, and GC restoration. Added four targeted regressions for response accounting, heads-up ranges, relative flush strength, and new-board nut-flush support.

## Final validation

- **19 regression tests passed**, including the existing 2,000 randomized legal-action checks. `results_tests.txt`.
- **6,000 additional stress decisions**, with zero illegal actions. At a 2.5x scaled soft clock and CPU-time scale: p99 517.5 µs, p99.9 600 µs, max 735 µs, zero over 1 ms. This is a CPU-headroom approximation, not a slower physical machine. `results_stress.txt`.
- Full-history replay with the 2.5x clock: **17,524 decisions**, CPU p99 520 µs, p99.9 752.5 µs, max 1,417.5 µs; three above 1 ms. This replay includes diagnostic capture overhead. Rare overruns therefore still rely on the documented time bank. `results_history_stress.txt`.
- **Final default mix, 400 tables, seed 229:** 20.57 ± 0.50 points, **235,205 decisions, zero failed decisions**; upload passed with 10/10 decisions. Latency p50 41.8 µs, p99 385.7 µs; maximum serialized memory 8,633 bytes. `results_final_default_400.json`. The original's separate 300-table seed-211 reference benchmark scored 21.60 ± 0.56, so this simple-opponent benchmark does not demonstrate an improvement.
- **Final direct comparison, 300 tables, seed 311:** four revised bots versus four original bots, through official `play.py`; **377,949 decisions, zero failures**, upload passed. Per-variant expected points were **14.97 revised versus 10.03 original**, a paired difference of **4.94 ± 0.70 SE** points. p99 latency including observation collection was 309.9 µs; maximum memory 8,816 bytes. `results_matchup_final_300.json`, `score_matchup_final_300.json`.

The direct-comparison helper only observes SDK states and never feeds its observations into either policy. The official runner aggregates all `self` seats, so it reports 12.5 overall. Variant scores are independently reconstructed from the last public SDK decision, public bust order, contributions/side pots, and ICM. For 296 tables with an unknown final runout, the helper averages 1,000 possible runouts, conditioning on the cards observed by the participating SDK seats. These are **expected terminal scores, not the simulator's realized per-variant labels**. They test improvement against our original policy, not the unavailable live opponent field.

An earlier 1,000-table comparison before the final flush-strength/protection refinements estimated 14.69 versus 10.31, difference 4.38 ± 0.40 SE, over 1,254,728 decisions with no failures. Its reports are labeled preliminary; the final 300-table comparison above is the validation of the delivered code. Earlier default-mix reports likewise document intermediate versions.

## Reproduce

From the workspace root:

```sh
PY=/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python
BOT=lab/field_bots/openai_a_default_1_r2
$PY "$BOT/analyze.py"
$PY "$BOT/field_stats.py"
$PY "$BOT/test_agent.py"
PYTHONPATH=lab/fake_sdk $PY "$BOT/stress_test.py"
$PY lab/field_kit/play.py "$BOT" --tables 400 --seed 229
$PY lab/field_kit/play.py "$BOT/matchup" --tables 300 --seed 311 --seats self,self,self,self,self,self,self,self
$PY "$BOT/matchup/score.py"
SCALED_CLOCK=1 $PY "$BOT/replay.py" "$BOT/agent.py" /tmp/replay_scaled_final.json
```

`matchup/` is a test-only observer/dispatcher which also reads the original bot; upload the top-level bot directory, whose actual agent reads only its adjacent `preflop.json`. Simulator RNG and C-backed Monte Carlo/timing can vary between runs.
