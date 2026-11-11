# 06 · Timeline and decision rules

One person owns submissions. Plug in, and keep lids open.

## Build hour
| Minutes | Do |
|---|---|
| 0-5 | Read the kit: `RULES.md` (variant, any extra phase), `README.md`, `AGENTS.md`, `state.config` fields, blind schedule, payouts. Answer the 4 convention questions in `01_RULES.md`. |
| 5-15 | **A minimal legal bot, uploaded.** Platform layer plus a simple strategy: push/fold ≤12 bb with a top-x% chart, open the top 15-20%, continue postflop with top pair or better, otherwise check/fold. Run tests 1-4, upload, **confirm "Active bot"**. Practice rounds every 10 minutes will exercise it. |
| 15-30 | Variant engine and tables. Then the preflop strategy from `03_STRATEGY.md` (classes, eq_pre, push/fold ICM EV, open/3-bet/call rules). Test, upload. |
| 30-45 | Postflop: Monte Carlo against narrowed ranges, bet-size EV, call/raise thresholds. Opponent stats in memory. Test (all 8), measure latency on the build box, upload. |
| 45-55 | Apply the field fixes in `04_FIELD.md` that are cheap: fold one pair to raises and big late bets, wider shove calls, table-size open rates, light 3-bets against folders. Test, upload by minute 55. |
| 55-60 | Hands off. Confirm the active bot. |

If something breaks, roll back to the last uploaded file immediately, then debug.

## Two people: split the work so the hour is enough
- **Person A (platform and safety):** P1, then P2.
  - Get the minimal bot uploaded by minute 15.
  - Write the test harness from `05_TESTS.md` (fuzz, conventions, re-delivery, latency on the build box).
  - Own every upload.
- **Person B (poker):** P3 from minute 5, in a **separate file** (`engine.py`, `build_tables.py`, `strategy.py`) that plugs into A's `agent.py` through one function, `decide(view, mem) -> (kind, amount, mem)`. Then P4, then P5.
- **Merge** at about minute 30 and again at 45. A runs the tests, then uploads.

## If you're behind, cut in this order (never cut safety)
1. P5's field fixes. Each is about +0.5-1 point; skip them all if needed.
2. Postflop bet-size EV: replace it with "bet 2/3 pot with equity ≥ 0.65, check otherwise".
3. Postflop range narrowing: keep the preflop width only.
4. Never cut: the platform layer, the legality funnel, push/fold by ICM, and the tests.

## Between rounds (results arrive in the next window)
1. **Check for failures first:** the team page shows failed decisions, restarts and tracebacks. Any nonzero count gets fixed first.
2. **Download our hand histories** (the smaller subset) and analyse them with a quick script:
   - chips won and lost by street, position, stack depth and action;
   - each opponent's VPIP/PFR, fold to bets, shove ranges from showdowns, what big bets and raises held.
3. **Make one or two targeted changes** for the biggest leak, the way the simulated teams did. Test it against the previous version in the same run and keep it only if it wins.
4. **Upload at least 3 minutes before the next round,** and confirm the active bot. In T6, ship only a clear win.

## Rules of thumb
- **Never be without an active bot.** No active bot scores 0, and a crash plays check-or-fold for the rest of the round (about 180 weighted points lost in T6).
- **A frozen bot falls behind** as the field adapts (1st → 5th in two simulated rounds). Keep improving, but gate every change.
- **Spend effort on T4-T6:** they're 71% of the score.
