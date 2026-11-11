# openai_a_default_2

## Approach

An exploitative, tournament-aware no-limit hold'em agent designed for the 1 ms decision budget. Runtime dependencies are Python's standard library and `eval7`. The only data file read is `preflop.json`, resolved relative to `agent.py` and loaded at import. All table information travels in SDK `memory`; there is no persistent table information on `self` or in globals.

- **Preflop:** position and stack dependent opening, isolation, defense, value reraising, and short-stack shove EV. Offline equities cover all 169 starting-hand classes against nine conventional strength ranges (180,000 Monte Carlo deals per entry). Another offline simulation uses 18,000 complete deals per starting-hand class to estimate joint equity against one through seven random opponents. This avoids treating multiway results as independent, particularly for pocket pairs.
- **Opponent adaptation:** public events track participation, preflop raises, repeated small reraises, postflop aggression, checks, calls, folds and revealed bluff candidates. Heads-up/three-handed participation is tracked separately. Priors shrink noisy statistics. Proven indiscriminate raisers, callers and check-or-fold opponents get different ranges and exploit policies.
- **Postflop:** card removal and action-conditioned opponent ranges, including made hands and draws. Up to 72 or 88 candidate combinations are reweighted and explicitly resampled into 160 entries: the installed `eval7` equity functions ignore their input range weights. C-level Monte Carlo estimates future equity; river equity is exact against the sampled posterior. Additional opponents and main/side-pot eligibility are included. Value bets, continuation bets, probes and occasional semibluffs use position, equity and stack-to-pot ratio.
- **Tournament utility:** substantial heads-up calls compare exact ICM utility for folding, winning and losing, using the actual configured payouts. The implementation preserves guaranteed prizes after cashing and uses a subset dynamic program for alternative payout schedules. Short all-in blinds and unmatched contributions are handled explicitly.
- **Runtime:** lookup tables and card/range objects are prepared at import. A worker-clock deadline bounds range conditioning, so slower workers automatically do less work. When the remaining bank falls below 15 ms, the bot uses a smaller posterior sample and fewer runouts. Cyclic GC is paused only within `act` and its previous setting is restored in `finally`; reference counting remains active. Memory stays far below the free 16 KB allowance.
- **Legality:** the final adapter uses only offered action kinds and clamps integer raise totals to the exact legal interval. It handles unavailable raises, all-in underraises and free checks.

## Build and regression tests

Three development stages: initial range-based strategy and 30-table smoke test; opponent/ICM/position refinements and larger matches; then side-pot, short-blind, sampling and runtime hardening. A review found and fixed a small-range sampling error, paired-board trips classification, preflop versus postflop position differences, and unnecessary deep-stack overjams. Timing investigation separated actual CPU work from host scheduling stalls and identified rare cyclic-GC pauses.

The independent regression suite is `test_agent.py`. Run from the repository root:

```sh
PYTHONPATH=lab/fake_sdk /Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_a_default_2/test_agent.py
```

It covers all 169 hand classes; distinct range samples; equity on nuts/shared nuts; paired boards; ICM prize conservation, guaranteed cash and alternative payouts; bubble risk; side pots; short all-in blind refunds; memory across separate Agent instances; GC restoration, including exceptions; legal-action clamping; and 1,800 randomized states with varied cards, positions, seat identifiers, stacks, histories and payouts. It imports no simulator implementation.

Local matches were run only through `lab/field_kit/play.py`. No other simulator source was read or imported directly. Several early runs experienced large host scheduling stalls, including wall times above 100 ms for decisions using under 0.35 ms of CPU. Those intermediate wall-clock timeout counts motivated separate CPU measurements and slower-worker tests; they are not treated as clean runtime passes.

## Final validation

The final confirmation match and validation sweep passed. Raw reports are in `validation/`.

- **Main mixed match:** 500 tables, seed 137, default mix of four bot copies, two check-or-fold and two min-raisers. Bot mean **20.96 points**, reported SE 0.45, versus fair share 12.5. Opponent means: check-or-fold 7.37, min-raiser 0.70. Bot finishing counts across its 2,000 seats: `[486, 437, 226, 86, 203, 334, 226, 2]`. **351,989 decisions, zero failures**, including zero illegal actions, exceptions or timeouts. Wall latency: p50 37.8 µs, p99 201.3 µs, p99.9 1,265.6 µs, max 21,804 µs. The time bank absorbed the rare wall-time overruns. Maximum memory 1,625 bytes. Report: `validation/default_seed137_500.json`.
- **Synthetic 2.5× CPU slowdown:** 100 default-mix tables, seed 109. The wrapper reduces the conditioning deadline by 2.5 and adds 1.5× the measured decision CPU time, while preserving the SDK's 1 ms limit and normal bank. Mean 20.60 points, **70,196 match decisions, zero failures**. Including upload, 70,206 calls were measured: raw CPU p50 31.0 µs, p99 144.584 µs, p99.9 181.125 µs, maximum 420.167 µs. Two raw calls exceeded 400 µs; all completed within the available decision limit plus bank after scaling. Scaled wall p99 367.8 µs and p99.9 469.8 µs. Reports: `validation/slow_seed109_100.json`, `validation/slow_cpu_seed109.json`.
- **Seven copies plus one min-raiser:** 100 tables, seed 113; bot mean 14.26 points; zero failures. This primarily exercises self-play, multiple callers and late-game states.
- **One bot against seven min-raisers:** 200 tables, seed 127; mean **35.31 points**, reported SE 0.80; 66 firsts, 124 seconds, nine thirds, one fourth. Zero failures. Wall p99 149.0 µs, maximum 533.3 µs; maximum memory 1,665 bytes.
- **One bot against seven check-or-fold opponents:** 100 tables, seed 131; **50.00 points and 100 wins**; zero failures. Wall p99 50.8 µs, maximum 774.8 µs.
- **Repeated upload checks:** seeds 0–29, **30/30 passed**, 300 upload decisions with zero failures. Each invocation also ran one normal table, all without failures. The kit does not support `--tables 0`, so the sweep used `--tables 1`.
- **Independent regression suite:** all **12 tests passed**, including 1,800 randomized states with both depleted and full banks and varying configured time limits. Output: `validation/unit_tests.txt`.

The last two normal mixed-match commands were:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_a_default_2 --tables 500 --seed 107
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_a_default_2 --tables 500 --seed 137
```

For completeness, seed 107 returned 20.59 points over 344,183 decisions with five wall-clock timeouts during a run whose maximum wall latency was 122.96 ms. A preceding 1,000-table run, before the depleted-bank sampling mode, returned 20.84 points over 699,185 decisions with 42 wall-clock timeouts and maximum wall latency 169.11 ms. These reports are retained as `validation/default_seed107_500_host_stalls.json` and `validation/pre_final_seed101_1000_host_stalls.json`; no illegal-action or exception failures occurred. The clean final run and slowdown run establish CPU/runtime headroom, while arbitrary host descheduling remains outside the bot's control.

Range conditioning and multiway postflop correlation are approximations. These local baseline matchups do not establish performance against the unseen tournament field.
