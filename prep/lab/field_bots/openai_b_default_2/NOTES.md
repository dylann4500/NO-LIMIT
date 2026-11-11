# openai_b_default_2

The upload payload is `agent.py` and `preflop.json` in this directory. The agent uses only the standard library and `eval7`. It reads no simulator source, uses no network, and stores all learned information in the SDK's per-table memory. Other Python files are local test and development tools.

## Strategy

- **Preflop:** an offline table covers all 169 starting-hand classes against 11 opponent-range widths, with 100,000 Monte Carlo trials per table entry. Separate opening ranks favor suited, connected hands. Opens, isolation raises, blind defense, value three-bets, occasional blocker three-bets, and short-stack shoves account for position, actual blinds, effective stacks, limpers, and opponents.
- **Opponent adaptation:** public events track VPIP, preflop raises, calls, checks, aggression, fold opportunities, and revealed bluffs. Statistics reset between tables. Priors prevent a few observations from completely determining a player's range; persistent folders and frequent raisers receive specific exploit adjustments.
- **Postflop:** blocked-card-aware opponent particles are weighted by preflop action and current/earlier street actions. Earlier likelihoods are tempered to account for correlation. `eval7` estimates showdown equity on flop/turn and evaluates the sampled range exactly on river. Heads-up decisions also estimate equity against the hands that continue to a bet, helping distinguish thin value, protection, and unprofitable bluffs.
- **Multiway and side pots:** approximate joint equity includes a shared-runout correction for flush/straight draws; a draw that beats both opponents on the same runout should not have its hit probability squared. Contribution layers limit the pots the hero can win. Playing the board receives explicit split-pot treatment.
- **Tournament utility:** exact three-prize ICM, and subset dynamic programming for other payout schedules, price significant calls and late-stage shoves. Large value reraises also face an ICM check. A busted player receives the applicable already-earned prize, rather than automatically zero. Effective-stack losses and additional matching chips are distinguished.
- **Sizing and mixing:** smaller dry-board continuation/protection bets, larger wet-board/value bets, selective steals and semibluffs, and value-heavy raises against calling/raising stations. Mixed decisions derive from the hand and private cards rather than table information in global variables.

## Runtime and legality

Only immutable tables and SDK action constants live in globals; `self` stores no tournament information. Compact `marshal` memory carries statistics, the current hand's public action summary, contributions, and equity caches. The measured footprint is under 2 KB, well below the free 16 KB allowance.

Particle work checks a soft deadline at 45% of `decision_ms`, every eight candidates. Sampling shortens as the deadline approaches. A time bank below 50 ms disables the additional calling-range calculation and reduces particle counts; below 10 ms the primary sample shrinks again. Preflop requires no live Monte Carlo calculation. All raises are converted to integers and clamped against the offered raise's bounds, and every returned action passes a final offered-kind check. Action kinds are identified using SDK action factories, avoiding an assumption that enum values are strings. The exception boundary returns an offered passive action and preserves the previous memory; direct tests separately detect any exception inside the strategy.

The deadline leaves time for the C equity call, remaining strategy logic, and serialization. It cannot prevent a host from suspending the process longer than the entire allowance. Early exploratory runs experienced substantial wall-clock pauses; sampled 10–44 ms calls used only roughly 100–280 microseconds of thread CPU. A larger pre-freeze comparison included a 361 ms wall-clock outlier. These reports are retained rather than discarded. The scaled-clock tests approximate slower hardware; they are not measurements on the tournament machines.

## Development and tests

The work proceeded through preflop/equity play, runtime and ICM corrections, then action-conditioned range and continuing-range improvements. Important fixes included already-earned prizes in ICM, shared board ties, side-pot eligibility, correlated multiway draws, and extreme bubble call thresholds.

`test_agent.py` checks exact ICM against an independent permutation calculation for 2–8 players and several payout schedules; event accounting and memory replay; bubble folds; shared royal flushes; draw correlation; and randomized SDK states. Fuzzing covers deep and short stacks, noncontiguous seat IDs, all streets, multiple all-ins, arbitrary payout schedules, and short all-in raise bounds. It asserts offered action kinds, integer raises within bounds, compact valid memory, and zero strategy exceptions.

`compare.py` invokes the supplied `field_kit/play.py` entry point, registering frozen SDK agents through its existing adapter. `rivals.py` supplies separate tight, balanced, and loose strategies sharing the static preflop tables, not the main strategy. No simulator implementation is inspected or imported directly by these tools.

Intermediate results are in `results/iterations/`. In the 1,000-table pre-freeze comparison against the third checkpoint, the newer strategy averaged 12.92 points versus 12.08. That run had six wall-clock timeouts across 1,294,001 combined decisions. The result supports the direction of the changes without establishing performance against the live tournament field.

## Final verification

The final reports and exact commands are saved in `results/`; `manifest.json` records hashes of the tested agent and equity asset. The preceding verification suite is retained in `results/before_bank_guard/`: its 500-table default run averaged 21.32 points but had one timeout in 366,499 decisions. That prompted earlier time-bank protection and the 45% soft deadline. Final results for the hashed upload payload:

- **Default mix, 500 tables, seed 703:** **21.15 points per bot (SE 0.45)** versus a 12.5-point fair share. Upload passed with 0/10 failed decisions. **361,046 match decisions, zero failures**. Our 2,000 seats finished first through eighth: 492 / 436 / 231 / 56 / 222 / 369 / 193 / 1. Local wall latency p50 92.7 microseconds, p99 325.8 microseconds; peak memory 1,679 bytes. Report: `results/default_500.json`.
- **One bot versus seven check-or-fold opponents, 100 tables, seed 704:** 50.00 points; won all 100 tables; upload passed and zero failed decisions. Report: `results/passive_100.json`.
- **One bot versus seven min-raisers, 100 tables, seed 705:** 38.40 points (SE 0.99); 42 wins and 58 second-place finishes; upload passed and zero failed decisions. Report: `results/aggressive_100.json`.
- **Diverse sparring field, 300 tables, seed 2049:** our two seats averaged **19.98 points (SE 0.80)**, versus tight 13.60, balanced 10.57, and loose 5.85. Upload passed. There was **one wall-clock timeout** across 346,437 combined SDK decisions, with a 108.083 ms maximum wall time, longer than even the full 1 ms decision allowance plus 100 ms bank. No illegal actions or strategy exceptions were reported. This host-level timing risk remains documented; the standard final mix had no failures. Report: `results/diverse_300.json`.
- **Final SDK stress tests:** 20,000 deep-stack plus 20,000 short-stack cases at a simulated 2.5x clock, with zero illegal actions and zero strategy exceptions. Scaled thread-CPU p99 / maximum: deep **643.8 / 774.1 microseconds**; short **635.5 / 770.9 microseconds**. Every sampled scaled CPU duration was below 1 ms. Reports: `results/stress_deep_20000_2_5x.json` and `results/stress_short_20000_2_5x.json`.

The final four simulation runs total 1,000 tables. All final runs passed the upload test. Full raw latencies, including scheduling outliers, are retained in the JSON reports. Numerical regression checks also confirm that duplicating combinations represents range likelihoods correctly; eval7 ignores the numeric HandRange weights, so the agent explicitly duplicates combinations instead.

Final `agent.py` SHA-256: `3ea5d9c583c33fb3d182f730144469135b1d33142c53642e3a355b4d509e42a9`.


Reproduce a standard match from the workspace root:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_b_default_2 --tables 500 --seed 703
```

Run the slower-machine clock stress test:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_default_2/test_agent.py 20000 2.5 short
```

The strategy remains an approximate range/utility model rather than a full equilibrium solver. Opponent ranges are sampled, joint equity is approximated, and multiway ICM outcomes assign contested chips to a representative winner. Local opponents and checkpoints are useful regression tests, not a prediction of live-field points.
