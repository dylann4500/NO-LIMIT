# openai_b_gto_3

Runtime files: `agent.py`, `preflop.json`, and `pushfold.json`. The bot uses the documented SDK and eval7. No private simulator source was read or imported by the bot, its builders, or its tests; integration tests invoke the public `field_kit/play.py`.

## Strategy

- Preflop: physical-combination-weighted ranges for all 169 starting-hand classes, positional opening charts at 20/40/100 BB, mixed range boundaries, blind completion/defense, linear value 3-bets, and occasional suited-ace blocker 3-bets. Opening and raise sizes vary with effective depth and position.
- Short stacks: an offline 169-by-169 equity matrix with card-removal probabilities, 16,000 Monte Carlo trials per off-diagonal matchup, and 18,000 fictitious-play iterations per blind-versus-blind shove/fold game. Depths are 2/3/4/5/6/8/10/12/15/20 BB; frequencies, EVs, and calling equities are interpolated between depths. The largest remaining best-response gap in these sampled subgames is 0.000221 BB/hand. This is a restricted shove/fold equilibrium, not a claim of full-game NLHE exploitability. Other short-stack opens use an approximate multiway shove EV model.
- Postflop: bounded, stratified opponent-range samples, adjusted for preflop position, betting lines, sizing, relative made strength, and draws. Previous-street calls are evaluated on the previous board, so missed draws remain in river ranges. eval7 handles up to 640 runouts in C. Multiway equity uses a conservative correlated-product approximation.
- Mixed value bets, continuation bets, semibluffs, and river blocker bluffs share sizing families: roughly 33/60% pot on the flop, 67% on the turn, and 75% on the river, with larger sizes for strong value. Marginal showdown hands check frequently.
- Tournament play: payout-aware risk premiums and exact small-field ICM for material heads-up all-in calls with up to four survivors. Unmatched overbets are removed from the hero's accessible pot and credited correctly in ICM outcomes. Certain shared-board chops bypass variance-based ICM decisions.
- Adaptation: regularized per-seat VPIP/PFR/aggression observations widen ranges against habitual raisers and increase stealing against persistent folders. Observations, hand context, and the private PRNG state live only in returned pickle memory. No learned information travels between tables; globals are static lookup data. Seat labels need not be contiguous or ordered numerically.

Import constructs immutable combo samples, rank/draw masks, and positional charts. Expensive preflop equities and subgame solutions are shipped as data. Every decision is projected onto the actual legal-action menu, including integer inclusive raise bounds and call/check substitution when raising is unavailable.

## Runtime protection

Sampling is bounded. Free-check decisions whose policy cannot depend on sampled equity skip sampling. When less than the configured bank reserve remains (60 ms with the default 100 ms bank), postflop decisions use a single hand evaluation and lookup policy. Memory stayed below 1.3 KB in integration testing, comfortably below the free 16 KB allowance.

Wall-clock pauses on this shared host can greatly exceed CPU time. The supplied slowdown verifier adds CPU work equal to 1.5 times the measured decision CPU time, approximating a 2.5x slower machine while retaining play.py's real wall-clock enforcement. This also magnifies exposure to host scheduling pauses; no implementation can guarantee a wall-clock deadline if its process is descheduled beyond the whole bank.

## Tests and iterations

The SDK-only stress test checks 15,513 actions, including 14,000 randomized card/menu/stack/line cases, 1,500 low-bank cases, non-contiguous seats, truncated memory recovery, raised-action substitution, double-paired boards, shared-board nuts, unmatched overshoves, transferable memory, and ICM/payout regressions. All actions were legal and no exceptions occurred. Additional direct probes confirmed that ordinary tight-player statistics do not trigger persistent-folder exploitation, and that depth interpolation reproduces each stored chart at its grid point.

Early iterations caught and fixed a double-paired-board exception, overly tight late-position opens, an unavailable-raise fallback that should call, and uncallable-overbet pot odds. Timing work removed redundant range calculations, bounded the empty-range fallback, reduced serialization cost, and introduced the bank reserve. Saved early JSON reports retain both successes and failures rather than hiding failed development runs.

## Final results

- Default mix, **500 tables**, seed 1019: **22.02 points per bot seat**, reported SE 0.44, versus fair share 12.5. **322,981 decisions; zero timeouts, illegal actions, or exceptions.** Upload passed. Finishing-place counts: 491 / 458 / 287 / 84 / 171 / 320 / 184 / 5 across 2,000 bot seats. Median latency 25.5 us; p99 222.6 us; maximum memory 1,278 bytes. Report: `results/default_500.json`.
- Seven copies plus one min-raiser, 100 tables, seed 419: **14.29 points**, 109,006 decisions, zero failures. The equal division of all points among seven successful copies is 14.2857. Report: `results/self_heavy_100.json`.
- One bot plus seven min-raisers, 100 tables, seed 419: **39.07 points**, 8,958 decisions, zero failures. Report: `results/aggressive_100.json`.
- One bot plus seven check-or-fold opponents, 100 tables, seed 419: **50.00 points**, first in all 100 tables, 12,760 decisions, zero failures. Report: `results/passive_100.json`.
- Upload checks with seeds 1–20: **20/20 passed, zero failed upload decisions**. Every integration run above also passed its upload check. Report: `results/upload_seeds.json`.
- Latest SDK stress timing: p99 CPU 240 us, p99.9 CPU 282 us, maximum CPU 357 us. A simple 2.5x scale gives 0.600 / 0.705 / 0.893 ms respectively. CPU measurements are separate from wall-clock scheduling delays. Report: `results/sdk_stress.json`.

- Final **2.5x CPU-load verification**, 500 tables, seed 1543: **21.55 points**, reported SE 0.45, **318,097 decisions; 12 wall-clock timeouts, zero illegal actions or exceptions**. Upload passed. Median wall latency 69.1 us, p99 1,957.1 us, maximum 94,216.9 us. This test **does not pass a literal zero-timeout requirement**: cumulative wall pauses exhausted some banks despite the measured CPU headroom. Report: `results/slow_2p5_500_final.json`.

 Earlier development reports include wall-clock timeouts: the earlier 500-table slowdown run had two in 314,592 decisions and a maximum wall latency of 174 ms, exceeding the entire 100 ms bank. A previous 200-table slowdown run had zero failures. These observations support substantial CPU headroom but do not justify an unconditional promise about a starved host's wall-clock deadlines.

`results/*.json` preserves original reports, including development failures. `results/runtime_sha256.json` identifies the runtime files.

## Reproduction

From the workspace root, using the provided interpreter:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_gto_3/test_agent.py
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_b_gto_3 --tables 500 --seed 1019
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_gto_3/verify_slow.py --tables 500 --seed 1543 --factor 2.5
```

`build_tables.py` and `build_pushfold.py` regenerate the offline data; `pushfold_matrix.npz` caches the sampled equity/card-removal matrix. The matrix was checked for 1,225 conditional opponent combinations per hero holding, symmetric joint card probabilities, and complementary equities. Regeneration is optional and not part of runtime. Agent mixing and equity sampling intentionally cause some variation between reruns with the same simulator seed.

Local results measure this bot against its copies and the two supplied baselines. They do not establish performance against the actual tournament field or full-game exploitability.
