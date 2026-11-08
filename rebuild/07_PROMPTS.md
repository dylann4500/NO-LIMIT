# 07 · Prompts (paste in order; fill the <...>)

## P1 · Read the kit (minute 0)
```
Read the starter kit fully: README.md, RULES.md, AGENTS.md, the SDK, the examples. Don't write code yet. Report:
1. The exact Agent API, action constructors, the state and config fields, and the event kinds and amounts.
2. Answers to the four conventions in rebuild/01_RULES.md: does Seat.stack include the street bet? Does pot include this street's bets? Are own actions echoed in events? Are kinds strings or enums? Show where in the SDK you found each.
3. The variant's rules versus standard hold'em (deck, hole cards, board, ranking, extra phases or action kinds), the blind schedule and the payouts.
4. How to run the local simulator and the upload checks.
```

## P2 · Platform layer and minimal bot (minute 5)
```
Build agent.py per rebuild/02_ARCHITECTURE.md section 1:
- the canonical view with runtime convention detection (stack first, then pot by chip conservation, then own-action echo), using the kit answers as defaults;
- the memory envelope, the legality funnel, and a try/except fallback.
Strategy for now: push/fold at ≤12 bb with the top 30% at 8 bb (narrower when deeper), open the top 18%, continue postflop with top pair or better, otherwise check/fold.
Add the import-time warm-up decision, gc.freeze() and gc.set_threshold(20000, 50, 100).
Run rebuild/05_TESTS.md checks 1-4 and report the numbers. Then pack it for upload.
```

## P3 · Variant engine and preflop (minute 15)
```
Build engine.py per rebuild/02_ARCHITECTURE.md section 3 for this variant: <variant rules>.
Use eval7 if it's plain hold'em, otherwise a stdlib evaluator with a capped cache.
Write build_tables.py (multiprocessing) for class × range-width equity at widths 0.04,0.07,0.10,0.14,0.19,0.25,0.32,0.40,0.50,0.62,0.78,1.0, plus strength percentiles.
Then implement the preflop strategy in rebuild/03_STRATEGY.md exactly: opponent range model, push/fold by ICM-blend utility, open/3-bet/call rules, all constants as given.
Then build a table-driven check that recreates every spot in rebuild/08_REFERENCE_SPOTS.md and compares our action. Report mismatches outside the light-3-bet band, and fix them.
Test, measure latency, report.
```

## P4 · Postflop and opponent model (minute 30)
```
Implement the postflop section of rebuild/03_STRATEGY.md:
- villain range narrowing by bets, raises and calls (with the size and street factors);
- Monte Carlo against the narrowed range within a 0.34 ms deadline;
- the facing-a-bet rules;
- the bet-size EV.
Per-seat opponent stats go in memory, counted at hand end. Run all of rebuild/05_TESTS.md, including latency on the build box. Report the numbers.
```

## P5 · Field fixes (minute 45)
```
Apply these changes from rebuild/04_FIELD.md, each behind a constant:
- fold one pair to raises and to big turn/river bets unless the bettor raises often;
- widen assumed shove ranges to roughly 40-60% at ≤20 bb, scaled by observed shove rate;
- track open rates separately for 6+, 4-5, 3 and 2 players;
- light 3-bets against openers who fold to raises over 55%.
Compare against the previous version in the same simulator run, keep only changes that don't lose, and report.
```

## P6 · Between rounds
```
Here are our round-<k> hand histories: <path>. Analyse them with a script:
- our chips won and lost by street, position, stack depth and action;
- each opponent's VPIP/PFR, fold-to-bet rates, showdown hands for shoves and for big bets and raises.
List the 3 biggest leaks with numbers. Propose ONE change, implement it behind a constant, test it against the current bot in the same run, and recommend ship or don't ship. Don't upload without my OK.
```
