# openai_a_icm_5

## Design

The runtime agent is `agent.py`; its only data dependency is the adjacent `preflop.json`. Dependencies are Python's standard library, the documented poker SDK and eval7. No simulator internals were read or imported. All table-specific information travels in returned JSON memory, rather than agent instances or mutable global state.

- **Tournament utility:** exact hero ICM using the configured payouts. A fast closed-form enumeration handles three paid places; subset dynamic programming supports other payout schedules. Large calls compare the prize equity of folding, winning and losing, rather than just chip pot odds. Bubble pressure follows the actual number of paid places. For example, one validation scenario raises the required all-in equity from 66.13% to 77.88% when another player becomes very short.
- **Preflop:** 169 starting-hand classes with equity against ten opponent range widths, generated offline with 24,000 eval7 trials per matchup. Position, suitedness and playability shape opening and defending ranges. Short stacks use a push/fold prize-EV calculation that combines estimated calling ranges, fold equity, effective stack sizes and ICM. Calls against short shoves account for the shover's position; reshoves receive tighter ranges. Deep stacks use small opens, selective value 3-bets, positional defenses and inexpensive set mining.
- **Postflop:** fixed stratified opponent-range samples, hand/draw likelihood weights, a prior bluff component, public betting history and eval7 equity calculations. River equity is exact against the sampled weighted range. Multiway equity is conservatively adjusted. Value sizing, continuation betting, selective river bluffs and strong value raises depend on equity and opponent tendencies.
- **Adaptation:** public events update VPIP, PFR, aggression, folds and postflop responses. Frequent preflop raisers and highly aggressive postflop players receive wider ranges. Persistent folders invite wider steals. Per-hand contributions track raises as street totals and calls as chip increments, limiting apparent pot odds when chips belong to inaccessible side pots.
- **Runtime and legality:** card objects, range samples, draw masks and preflop tables load at import. Expensive straight-draw scans became bit-mask lookups. A depleted time bank switches to cheaper, conservative postflop evaluation. Every returned action passes a final offered-kind and integer raise-bound check.

## Iterations and checks

1. Initial 30-table prototype: upload passed, 20.83 points per bot seat, no failed decisions. Its postflop calculation was too slow for the intended hardware margin.
2. Replaced repeated draw scans with import-time lookup tables; the pressure-equity microbenchmark fell from roughly 400–460 microseconds to about 100 microseconds. A 200-table run scored 22.03 points with no failures.
3. Corrected postflop position, blind-vs-blind shove/call widths, speculative defenses and forced premium shoves that bypassed negative ICM EV. Added the low-bank path, showdown/bluff refinements and side-pot accounting. An intermediate 200-table run scored 22.58 points; one long scheduler pause caused a timeout. An early synthetic slowdown run also exposed timeout risk, which motivated the low-bank path. Final runs are below.

`validate.py` independently checks:

- 640 ICM results against brute-force finish-order enumeration, including winner-take-all and alternative payout schedules.
- Stronger survival incentives with a short stack on the bubble.
- Exact split equity when the board contains a royal flush, across all suits.
- 10,000 randomized SDK states, including unavailable raises, short stacks, different payouts, depleted banks and memory continuity: every action legal and every raise an integer within its offered bounds.
- Public-event contribution accounting and eligible side-pot odds.

The recorded validation passed completely. CPU latency was 54.0 us median, 237.0 us p99, 330.0 us p99.9 and 372.0 us maximum; 2.5 times the maximum is 930 us. Memory in these checks stayed below 400 bytes. Shared-host wall time contains scheduler pauses; CPU time and slowed tournament runs are both reported rather than treating wall-clock outliers as computation cost.

## Final local tournament results

Final standard field, 500 tables, seed 47:

```text
python lab/field_kit/play.py lab/field_bots/openai_a_icm_5 --tables 500 --seed 47
```

- Upload: PASS, 10 decisions, zero failures.
- Bot: **21.92 points per seat**, reported SE 0.44; fair share 12.5.
- Check-or-fold: 5.77 points; min-raiser: 0.40 points.
- Bot finishing places 1 through 8: 492 / 440 / 302 / 109 / 165 / 347 / 145 / 0.
- **333,499 decisions; zero failures of any kind.**
- Wall latency: median 42.5 us, p99 207.6 us, p99.9 10,300 us, maximum 57,157 us. The long shared-host tails were covered by the time banks.
- Maximum memory: 515 bytes.
- Full report: `results/default_500.json`.

Stronger self-play mix, 100 tables, seed 31, seven copies plus one min-raiser:

- Upload passed; bot 14.29 points, min-raiser 0.00.
- **108,516 decisions; zero failures.**
- Wall median 41.6 us, p99 181.2 us; maximum memory 522 bytes.
- Full report: `results/seven_self_100.json`.

The local kit only offers check-or-fold, min-raiser and copies of this bot. These results establish local performance and API correctness; they do not measure strength against the unseen tournament field. Range likelihoods and multiway equity remain approximations, rather than a full equilibrium solver.

## Reproduce

Use `/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python` for `python` above.

```text
python lab/field_bots/openai_a_icm_5/validate.py
python lab/field_bots/openai_a_icm_5/timing_probe.py --tables 100 --seed 53 --factor 2.5
```

`timing_probe.py` runs the public CLI through a temporary agent wrapper that adds 1.5 times each decision's measured CPU cost, approximating 2.5x slower hardware without multiplying unrelated scheduler pauses. `build_equity.py` regenerates the preflop asset offline; it is not imported during play.
