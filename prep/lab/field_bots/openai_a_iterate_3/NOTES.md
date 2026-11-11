# openai_a_iterate_3

Upload `agent.py` and `preflop.json` together. `Agent` is defined at module level. The other files are development tests and evidence; the bot does not import them.

## Approach

The bot combines position- and stack-dependent preflop play with action-conditioned opponent ranges and fast equity estimates. Preflop equity is loaded at import from 169 hand classes against nine range widths. The offline generator used 100,000 trials for random-opponent strength and 50,000 per hand/range matchup. Small pairs, suitedness and connectivity receive playability adjustments.

Postflop, public action history conditions a sampled range on pairs, draws, betting streets, raises and bet size. Eval7 estimates future equity on the flop and turn and evaluates the conditioned range exactly on the river. Multiway estimates account for shared improving runouts and reduce the influence of short all-in players on larger side pots. Calls use only the pot the hero can win.

Per-table memory tracks VPIP, preflop raising, repeated raises, postflop betting, calling and folding. Priors prevent small samples from overwhelming the model. Opening frequency and reraising frequency remain distinct. The bot adjusts to habitual folders, indiscriminate raisers and calling stations. There is no learning or state shared between tables or Agent copies.

Large heads-up calls and value shoves use ICM with the actual payout configuration, including payouts already guaranteed when players bust. Bubble pressure also affects opening ranges. On the river, an exact search finds the strongest possible opposing hand using rank-pair representatives plus flush and straight-flush candidates. An unbeatable hand is never folded because its equity includes a large probability of splitting the pot.

## Runtime and legality

- Import-time card objects and preflop tables; no preflop rollouts.
- Computation guard at 42% of the configured decision limit, capped at 420 microseconds. Range construction stops early, raw ranges shrink, and rollout counts decrease as the budget runs out. Bounded evaluator work and serialization finish after that soft guard.
- Reserve-bank protection lowers computation to 150 microseconds below 35 ms of bank and 80 microseconds below 10 ms. With a depleted reserve, free decisions use a cheap made-hand value bet or check instead of a rollout.
- Per-street equity caching and compact protocol-4 pickle memory. Final default-match maximum memory: 735 bytes.
- Every returned action is checked against offered kinds. Raise totals are integers clamped to the offered bounds. A value raise becomes a call when raising is unavailable.
- A final exception guard returns a legal check/fold. Tests also call the decision path without that guard, so it cannot conceal implementation exceptions.

## Development and checks

Three main passes established a safe baseline, added tournament utility and board/range modeling, then refined range priors, side pots, timing and action safety. The initial 1,000-table baseline averaged 19.41 points. A subsequent 1,000-table comparison scored 13.23 versus that baseline's 11.77. Some earlier concurrent comparisons recorded wall-clock timeouts on the heavily loaded host; their raw reports are retained. No illegal-action or exception failures were observed.

The final SDK test runs 10,000 diverse states, including learned broad ranges, narrow ranges, multiway pots, all-ins and restricted legal actions. It checks the uncaught decision path, action legality, memory size, board-only pairs, contribution accounting, side-pot eligibility, payout conservation, guaranteed finishing prizes, extreme bubble pressure and forced calls with shared nuts. It runs again with the bot's clock advancing at 2.5x speed.

The river-ceiling search matched exhaustive enumeration of every legal opposing hole-card combination on 1,000 random cases and 275 additional targeted straight, flush, straight-flush, full-house and quads cases.

## Final play.py results

The four primary validation matches and upload sweep use the exact agent hash in `results/manifest.json`. The default and slowdown reports below are the final sequential repeats.

- Default mix, seed 20261106, **1,000 tables**: **21.42 +/- 0.31 points** per bot seat (standard error); fair share 12.5. **547,299 decisions; 6 failed decisions: {'timeout': 6}.** Upload passed. Finishes for the four bot seats combined: 949 / 882 / 588 / 243 / 325 / 596 / 412 / 5.
- **2.5x CPU-cost emulation**, seed 20261107, 200 default tables: **21.04 +/- 0.71 points**. **106,293 decisions; 7 failed decisions: {'timeout': 7}.** Upload passed. The wrapper scales the internal clock and adds CPU work to reach 2.5x decision cost; simulator limits and the bank remain unchanged.
- One bot against seven minimum raisers, seed 20261108, 200 tables: **35.90 +/- 0.66 points**; zero failed decisions; upload passed.
- One bot against seven check-or-fold bots, seed 20261109, 100 tables: **50.00 +/- 0.00 points**, 100 first-place finishes; zero failed decisions; upload passed.
- Additional upload sweep: **30/30 passed**, 300 decisions, 0 failures.
- Final bot versus the initial baseline, seed 20261112, 1,000 tables with four seats each: **14.69 +/- 0.30 versus 10.31 +/- 0.26 points**. The combined report recorded 13 timeouts: {'self': 1, 'baseline': 4}, with 8 unattributed. No illegal-action or exception failures.

Default wall latency: p50 30.5 us / p99 395.5 us. Slowdown wall latency: p50 83.4 us / p99 7401.2 us. SDK stress CPU p99: 299.0 us normally and 263.0 us with the accelerated clock, including bank values 0, 5, 20, 40 and 100 ms.

The shared host produced occasional wall-clock scheduling stalls exceeding the entire 100 ms bank, including a 130 ms outlier. Concurrent same-code runs recorded five default-field timeouts and one slowdown timeout; these are retained as `final_default_loaded_host.json` and `final_slow_loaded_host.json`. Earlier comparisons are also retained. Reserve-bank protection reduces computation after stalls, but cannot prevent the operating system from suspending the process. The local CPU-cost tests and upload sweep establish timing margin, rather than a guarantee about arbitrary host scheduling.

The supplied opponents and saved bot revisions differ from the unknown tournament field. Multiway equity and opponent action likelihoods remain approximations.

## Reproduction

From the workspace root, with the provided tournament Python:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_a_iterate_3/validate.py
```

This runs both SDK suites, the normal and emulated-slow matches, both extreme fields and the upload sweep. It writes unmodified play.py JSON reports and a SHA-256 manifest to `results/`.

`build_tables.py` regenerates the shipped preflop data. `test_agent.py` imports only the public fake SDK and this bot. Validation executes the supplied `play.py`; it never reads or directly imports simulator implementation files. An optional `--opponent NAME=BOT_DIR` argument was added to `field_kit/play.py` to compare saved revisions; normal play.py behavior is unchanged.
