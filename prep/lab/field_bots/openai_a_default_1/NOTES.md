# openai_a_default_1

Runtime entry point: `agent.py`, with `preflop.json` in the same directory. Runtime dependencies are the standard library, `poker_agent_sdk`, and `eval7`. No simulator internals are read or imported by the bot or its tests. All tournament tests run through the supplied `field_kit/play.py`.

## Approach

- **Preflop:** offline Monte Carlo equities for all 169 starting-hand classes against 12 range widths, using 120,000 trials per matchup. Position, stack depth, pot odds, suitedness, implied odds, and opponent tendencies govern opening, defending, and reraising. Short-stack shoves use estimated fold equity, calling ranges, effective contributions, and tournament risk. Deep open shoves and repeated reraises receive substantially tighter default ranges. An all-in blind retains an unselected range.
- **Opponent adaptation:** public events update VPIP, preflop raising, postflop actions, folds, minimum raises, and shown-hand tendencies. Expected activity is normalized by table size so normal heads-up aggression is not mistaken for an automatic raiser. Established folders are attacked cheaply; repeated automatic raisers are value-targeted.
- **Postflop:** infer preflop ranges, then reweight combinations using calls, bets, raises, bet sizes, made hands, and draws on each street. Hand-class stratification plus explicitly included possible pocket sets improves sampling efficiency. Stratum weights preserve the sets' true frequency. Normally sample 64 other combinations, reducing work when the bank is low. C-backed Monte Carlo estimates flop/turn equity; weighted hand comparisons estimate river equity. Betting distinguishes value, protection, continuation bets, selective semi-bluffs, and restrained river bluffs.
- **Tournament decisions:** exact top-three ICM calculations, with a subset dynamic program for deeper payout schedules, price meaningful calling risk. Contribution reconstruction caps inaccessible side pots. Multiway equity and opponent response models remain approximations; this is a practical range-based player, not a solved equilibrium strategy.
- **Runtime and legality:** immutable tables load at import. Persistent information travels only in `memory`. Cached posteriors avoid repeating prior-street work. A soft deadline and bank-aware sampling bound expensive work. Cyclic GC is deferred during `act` and its original setting is restored in `finally`. A single action gateway checks offered kinds and clamps integer raise totals to the supplied limits. Cached ranges are discarded before exceeding the memory allowance.

## Build iterations

1. Built preflop tables, opponent tracking, range inference, and tournament-aware decisions. The first 100-table run scored 21.32 points but exposed a latency tail.
2. Added posterior caching, heads-up adjustments, GC deferral, and regression coverage. Captured and fixed an ICM division by zero caused by a fractional-chip residue near elimination. A larger 144-combination estimator scored 21.59 in 500 tables but had 44 wall-clock timeouts.
3. Replaced it with stratified, set-protected sampling and reduced work as the bank declines. Offline comparisons against complete weighted ranges supported the smaller estimator. Corrected prospective shove contributions and all-in blind handling. The final candidate below had no failed decisions in 900 tables.

## Final validation

- **15 regression tests passed**, including 2,000 randomized legal-action cases, all-in nuts, shared board nuts, deep-shove folds, short raises, short blinds, ICM including custom payouts, cache transitions, memory recovery/limits, and GC restoration. See `results_tests.txt`.
- **6,000 additional stress decisions:** zero illegal actions. Covered preflop through river, 2–8 players, custom payouts, and banks of 0/5/20/50/100 ms. With a deadline clock scaled by 2.5 and measured CPU time multiplied by 2.5: p50 **215 µs**, p99 **480 µs**, p99.9 **600 µs**, maximum **742.5 µs**, zero above 1 ms. This checks CPU headroom; it is not an actual slower machine. See `results_stress.txt`.
- Every final `play.py` run passed its upload test: 10 upload decisions per run, with no crashes or failures.

## Final play.py results

All results use the final bot and the supplied timing enforcement. Points are per bot seat; ± values are the runner's standard errors.

- **Default mix, 500 tables, seed 101:** self **21.22 ± 0.44** points versus 12.50 fair share; check-or-fold 5.76, min-raiser 1.80. **276,863 decisions, zero failures.** Self finishing counts: `[464, 424, 326, 149, 130, 270, 225, 12]`. Latency p50 34.7 µs, p99 291.2 µs; peak memory 7,528 bytes. Raw report: `results_default_500.json`.
- **Seven self copies / one min-raiser, 200 tables, seed 103:** self **14.19 ± 0.49** points, close to the 14.29 ceiling if the min-raiser scores nothing; min-raiser 0.65. **215,214 decisions, zero failures.** Raw report: `results_dense_200.json`.
- **One self / seven check-or-fold, 100 tables, seed 17:** self **50.00 points**, first in all 100 tables. **12,278 decisions, zero failures.** Raw report: `results_folders_100.json`.
- **One self / seven min-raisers, 100 tables, seed 31:** self **37.70 ± 1.02** points, finishing first/second/third 40/57/3 times. **3,135 decisions, zero failures.** Raw report: `results_maniacs_100.json`.

**Total: 900 tables, 507,490 tournament decisions, zero illegal actions, exceptions, or timeouts.** Peak memory across these runs was 7,774 bytes. Occasional wall-time outliers above 1 ms used the bank; the largest was 62.19 ms. The reference opponents are limited, so these scores measure local behavior rather than predict performance against other entrants.

## Reproduce

From the workspace root, using the supplied Python:

```sh
PY=/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python
BOT=lab/field_bots/openai_a_default_1
$PY "$BOT/test_agent.py"
PYTHONPATH=lab/fake_sdk $PY "$BOT/stress_test.py"
$PY lab/field_kit/play.py "$BOT" --tables 500 --seed 101
$PY lab/field_kit/play.py "$BOT" --tables 200 --seed 103 --seats self,self,self,self,self,self,self,min_raiser
$PY lab/field_kit/play.py "$BOT" --tables 100 --seed 17 --seats self,check_or_fold,check_or_fold,check_or_fold,check_or_fold,check_or_fold,check_or_fold,check_or_fold
$PY lab/field_kit/play.py "$BOT" --tables 100 --seed 31 --seats self,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser
```

`build_tables.py` regenerates the offline equity data; it is not needed at runtime. Monte Carlo sampling and wall-clock scheduling can vary results between runs, even with the same simulator seed.
