**Superseded by `docs/BUILD_PROMPT.md`, which has the newer results and the final design. Kept for background.**

# No Limit tournament playbook (Bay Area regional, Nov 6)

**Read first:** every score below comes from our own simulator against opponents we wrote. The real field, blind schedule, points table, variant and API are unknown until kickoff. Trust the direction of these findings more than the size.

## The plan in one paragraph

Ship a legal bot within 15 minutes. Then build a small policy that depends on the variant only through two functions, `pct(hole)` and `eq(hole, board, range_width)`, with about 25 thresholds in one dict. Use a small lookup table for `eq` first. Tune with one short blended run: **weak opponent mixes and copies of your own bot together**. Promote a change only if it wins on opponents the tuner never saw. **Call tight, jam short, attack heads-up, and don't fuss over any single threshold.** If practice rounds show spare time, upgrade `eq` to 40 deadline-guarded rollouts with the lookup as fallback. T4-T6 are 71% of the score, so keep improving after the build, and never ship anything that hasn't passed the safety gate.

## Ask these first (5:30 check-in, or email pokerbot@sequoiacap.com tonight)

1. **May we bring prepared code, tables or parameters?** The rules say teams have 60 minutes to build (3.3), and the announcement says "from scratch". The rules ban copying another team's code (6.1) but don't address your own prepared code. Winners face code review (5.4), so get this answered rather than guessing.
2. **May we use tools beyond Astra and Codex?** Rule 3.4 names only those two. Don't assume Claude or other assistants are allowed during the build phase.
3. **Is local or cloud compute restricted?** The rules don't say.
4. **Is non-stdlib Python, such as numpy, available in the sandbox?** Plan on no.

If prepared code is ruled out, `docs/CODEX_PROMPTS.md` rebuilds the design from a blank repo, and what you've learned tonight still applies.

## What the rules force

| Rule | Consequence |
|---|---|
| 1 ms per decision; a miss means check/fold (3.7) | Stdlib tables and short loops. Stop computing well before 1 ms. |
| 100 MB, no network (3.6, 3.7) | Everything is computed before submission. |
| State resets per table; anonymous (3.8) | Opponent reads last one table only, up to 200 hands. |
| 8 seats, 2,000 chips, 10/20, up every 25 hands, 200-hand cap (4.4) | Starts at 100 BB deep. 35% of tables hit the cap in our sim, and 195 hands was the average in all-tuned fields. |
| Points by finish, ICM at the cap (4.5) | Chip EV is not the objective. Read the points table before tuning. |
| 10,000 tables per round (4.3) | Luck mostly averages out, so maximize expected points and don't seek variance. |
| One submission per 5 min; frozen at each round start (3.5, 4.2) | Submit at least 3 minutes before each freeze and confirm it was accepted. |
| Weights 1-6 (4.7) | T6 alone is 29%. Don't panic over T1. |

**Clock (from kickoff):** build 0-60; T1 at 60, T2 at 80, T3 at 100, T4 at 120, T5 at 140, T6 at 160. Practice rounds run every 10 minutes during the build.

## What we found

Top3 means a 50/30/20 table, where a fair share is 12.5. "Holdout" and "stress" opponents were never seen by the tuner. Noise is shown as ± one standard error where it matters.

**1. Tuning generalizes and pays off fast.** On the holdout, an untuned bot scored 16.7, generation 3 of tuning (under a minute on 10 cores) scored 22.0, and it plateaued near 23 by generation 8. A first pass reached 23.2 vs. the best simple baseline's 18.9. So tune as soon as anything works, and don't wait for a long run.

**2. Blend your training field. This was the most useful single finding.** Tuning only against weak bots leaves you exploitable by anyone who self-plays. Tuning only by self-play gives up points against weak bots. One blended tune (typical, strong, aggro, mirror and all-copies fields) did close to the best of both:

| Field (top3) | Weak-field tune (r0) | Self-play (r3) | Blend |
|---|---|---|---|
| Holdout (unseen) | 24.3 | 21.1 | **24.8** |
| Typical | 30.0 | 26.6 | **29.7** |
| Stress mix (unseen) | 25.5 | 19.1 | **24.1** |
| Table of r0 copies | 13.0 | 15.6 | **15.7** |
| Table of r1 copies | 10.8 | 13.0 | **12.9** |
| Table of r3 copies | 10.1 | 12.5 | **12.4** |
| Table of blend copies | 10.3 | 12.8 | 12.7 |

Self-play converged after about one round and showed no cycling across three rounds in this policy space. It favored more bluffing (18% to 39%), more 3-betting (2% to 4.6%) and wider short-stack jams.

**3. Lookup vs. Monte Carlo: start with lookup, upgrade if the host allows.** The lookup is 26 KB (478 feature cells), 7 µs per call, and builds in 5-35 seconds. With equal tuning, 40 live rollouts do beat it:

| Field | Lookup | MC 40 | MC 15 | MC 100 |
|---|---|---|---|---|
| Holdout, top3 | 24.61 | 24.99 | 24.68 | 25.34 |
| Mirror, top3 | 20.34 | 21.58 | 20.80 | 21.52 |
| Typical, top3 | 30.21 | 31.36 | 30.49 | 31.48 |
| Holdout, winner-take-all | 35.53 | 38.09 | 37.38 | 38.56 |

Each is ±0.3 on top3 and ±0.6 on winner-take-all. So MC 40 is worth about +0.4 to +1.2 on top3 and more on top-heavy tables, while 100 adds little beyond 40. Latency on this laptop: lookup p99 16 µs; hybrid MC p99 109 µs, with the machine busy. **An earlier version of these notes said the lookup matched MC; that came from unequal tuning and was wrong.**

With blended tuning on both sides, the gap on top3 was: holdout 24.09 lookup vs. 25.05 MC 40 vs. 25.31 MC 15; stress mix 23.60, 25.60, 24.65; typical 29.96, 30.81, 31.02; mirror 18.45, 18.94, 19.08 (each ±0.4). So 15 rollouts is a reasonable cheaper setting, and either MC setting beats the lookup by about 0.5-2 points when it fits within the limit.

The lookup wins clearly where rollouts don't fit: Omaha lookup 22.8 vs. 19.2 for the 8 rollouts that fit (mc40 22.4 would take about 1.5 ms). 3-hole lookup 24.4 vs. MC 40 23.0. Short deck lookup 22.8 vs. MC 40 24.0.

**4. The score is flat near the tuned values, so don't hand-tweak.** Moving any single threshold ±40% changed the score by about 1 point at most, within noise of a slightly low baseline draw. Opening width barely matters either: even against bots written to punish it, 0.5x to 1x width stayed within noise, and 0.75x was equal or slightly better. Big structural mistakes still hurt:

| Change | Top3 effect (typical / strong / aggro / passive, ±0.28) |
|---|---|
| Jam from 45 BB (M<30) | -5.0 / -5.6 / -3.8 / -4.3 |
| Jam only under 9 BB (M<6) | +0.3 / +0.6 / 0.0 / +1.5 |
| No opponent modeling | -2.1 / -2.1 / -0.4 / -0.6 |
| No extra margin in close spots | -1.8 / -0.9 / -1.9 / +0.1 |
| MC with only 5 rollouts | -2.8 / -2.8 / -2.2 / -2.9 |

**5. These did not earn their place. Skip them unless the real rules change the picture.**
- **Exact ICM price on big calls:** slightly better on flat tables, but -3 to -9 on winner-take-all in three of four fields. Untuned, so possibly improvable.
- **Calling jams from each seat's observed raise rate:** helped heads-up vs. a maniac (46% to 52%) but lost overall (-1.5 holdout, -1.7 mirror). Untuned margins.
- **Chip-leader widening, extra c-bets and tightening near the cap:** the tuner drove all three almost to zero.
- **Tuning for one specific point table:** it didn't reliably win on its own table, and field mix mattered more. Tune on the real table anyway since it costs 2 minutes, but with the blended fields.

**6. Blind schedule: the result was robust.** On assumed, slow, doubling and in-between schedules, the bot led on top-heavy tables in both fields tested (about 23-28 vs. 11-21 for baselines). Tables run long: about 190 hands per table in tuned fields, so the 200-hand cap and ICM at the cap matter. On a **flat table with slow blinds, passive bots keep up** (fold-only 5.0 vs. 4.8), so check the real points table.

**7. Heads-up matters a lot.** The first version treated the heads-up small blind as early position, opened only about 14% there, and finished second too often, matching the failure a public repo reported. After fixing it, the typical-field finish was first 45%, second 11%. Blend opens 96% heads-up. Remaining weakness: heads-up against very erratic raisers (about 46-52% vs. a maniac).

**8. The 1 ms limit.**
- A stdlib evaluator with rank-count keys does about 0.34 µs per 7-card hand. That's about 20x faster than the Treys-based estimate in the literature notes.
- Timeouts come from OS preemption, not from slow code. On a saturated machine, 10-99 of about 200,000 decisions went over 1 ms (max about 10 ms) even with a deadline guard. On an idle machine, the MC bot had none (max 217 µs). The host's load is unknown, so watch for timeouts in practice rounds.
- `import numpy` took 615 ms, a serious risk if the platform re-imports per table. The reference bot imports in about 10-25 ms.
- GC caused an observed 1.9 ms spike. Freeze and disable it at the end of import.

**9. Adapter errors cost points silently.** A simple `max(bets)` mistake caused 173 illegal actions in 1,500 tables without crashing. With a correct adapter, parity with the direct policy was exact within noise (59.74 vs 59.86, 2,500 paired tables). Seeing only actions up to your own decision costs about 1-2 of those 60 points, so check whether the kit exposes actions after your fold.

**Field caveat:** one public repo describes a tuned 49-threshold bot built for this event, so expect some prepared teams. Its numbers are self-reported on placeholder rules and aren't comparable to ours. https://github.com/EthanXu07/poker-bot-overview

## Design

```
kit API -> adapter (the only API-aware code) -> policy(PARAMS) -> pct(hole)             table built from kit evaluator
                                                                -> eq(hole,board,width)  lookup; optionally rollouts + lookup fallback
```

Safety is not optional: try/except around everything, clamp to legal bounds, `gc.collect(); gc.freeze(); gc.disable()` at the end of import, one warm-up call, and a deadline check inside any loop.

**Blend-tuned starting values** (lookup bot; retune at the event on the real rules. These thresholds are coupled, so don't read too much into any one of them, like `range_raise` being wider than `range_bet`):

| Parameter | Value | Meaning |
|---|---|---|
| First-in open | `0.172 + 0.725/(behind + 0.5)` | 27% with 7 behind, 46% with 2, 66% with 1 |
| Heads-up open / jam | 0.96 / 0.98 | Nearly every hand |
| Open size | 2.1 BB | Small |
| Short-stack switch | M < 6.0 (about 9 BB) | Then jam or fold |
| Jam width | `1.14 x chart x (1 + 0.051 x (6.7 - M))` | Chart by players behind: 1, .69, .44, .34, .27, .22, .20, .18 |
| Call a jam | Top 3.4% base | Widened by the seat's looseness and short-handedness |
| 3-bet / 4-bet | Top 4.1% / 1.2% base | Rare |
| Call extra equity | +13.7 points over pot odds, +10.7 more with 4 or fewer alive | Demand a real edge |
| Value bet | eq > 0.69, 0.60 pot | Small |
| Bluff | 27% heads-up when checked to | Half pot |
| Raise | eq > 0.84 | Rare |
| Villain range | 82% unraised, 12% vs bet, 16% vs raise | Widened short-handed and for loose seats |

## Team split (two laptops)

| Minute | Person A: bot and platform | Person B: lab |
|---|---|---|
| 0-5 | Read the kit with P0. Find the submission path. | Copy the points table, blinds and variant into config. |
| 5-15 | **Submit the safe bot (P1).** Confirm acceptance. | Build `pct` tables for the variant (P2). Eyeball the top 20 hands. |
| 15-30 | Write the adapter; test legality with the fuzz gate. Find out what history is visible. | Build the small strength table (P3); check its error. Time the kit simulator. |
| 30-45 | Policy on real tables (P5). Submit if the gate passes. | Fast engine and field if needed (P4). Start the first tune. |
| 45-55 | Merge tuned parameters. Run the gate. **Submit.** | Holdout check. Run a second tune from the best so far. |
| 55-60 | Hands off. Confirm T1's active bot. | Keep tuning for T2. |

**Rules of the road:** one person owns submission. Nothing is submitted unless the gate shows 0 errors and 0 illegal actions, and p99.9 latency is under about 300 µs. Keep the last known-good bot file. Give Codex one task at a time with clear files, and read each diff.

## Between rounds (T1-T6)

- **Each 20-minute cycle:** 2 minutes reading results, 10 minutes tuning, 3 minutes holdout, gate and submit, 5 minutes margin. Submit by T-3 minutes.
- **One change per round.** With 10,000 tables, score noise is about ±0.6 on a 100-point table if each team really plays them all, so per-round comparisons are useful. If tables are shared among teams, noise is larger, so check how many tables each team played. The field also shifts between rounds, so compare our rank and gap to other teams, not just our raw score.
- **Training mix:** include copies of your own bot from the first tune. If scores suggest a tough field, weight self-play and mirror fields more. If the leaderboard shows many weak bots, weight typical and passive more.
- **Host speed:** once practice rounds confirm low timeouts, try the MC hybrid and compare. It's a one-flag change that can be reverted.
- **Never in the final 5 minutes:** new logic. Only parameter changes that already passed the gate.
- **If a round goes badly:** first check for timeouts and crashes in any logs, then for adapter mistakes (raise-by vs raise-to, stack including bets), and only then blame strategy.
- **Disputes** go to a Gamemaster before the next round starts (6.3).

## Variant response

Read the announcement, then find the row. **Whatever it is, the safe bot ships first.**

| Announced | Do | Watch for |
|---|---|---|
| Short deck | Rebuild `pct` and the strength table with the kit's evaluator. Hold'em-tuned parameters transferred well, but retune. The lookup's error was highest here (10.5 points), so prefer MC if time allows. | Equities compress: call more, fold fewer dominated hands. A-6-7-8-9 straight and flush rank are easy to get wrong. |
| Re-ranked hands | Same rebuild; usually minor. | Don't trust any hardcoded hand order. |
| Extra hole cards (3-card, Omaha) | Rebuild both tables: Omaha took 65 s for `pct` and 35 s for the lookup. Evaluate 2-from-hand. | **Use the lookup, not rollouts.** Omaha lookup 22.8 vs. 19.2 for the MC that fits in 1 ms. |
| Discard or draw decision | Add an action: keep whichever hand has the best `pct`, or the best equity on the board. | Check how it's exposed in the API. |
| Pot limit | Remove jam logic above the pot limit; use max-legal raises. | Push-fold charts don't transfer directly. |
| Antes or straddles | Treat as a bigger pot: open wider. | Check whether `pot` includes them. |
| Bounties or a custom points table | Add the bounty to the win value; retune on the real table. | Flat tables reward survival and top-heavy ones reward winning. |
| Hi-lo or multiple boards | Equity = expected pot share over each board or half. | Rework the strength table's features. |
| Auction, blotto or other mini-game | Handle the new decision separately and simply, then tune it with a single parameter. | MIT's class has used these twists. Don't let the twist eat the time needed for the base bot. |

## Tonight

1. Email the organizers the questions above.
2. **Run a sealed rehearsal (60 min):** one person changes `rehearsal/kit/rules_card.json` and sets `POKER_VARIANT` without telling the other. Build from `rehearsal/kit/my_bot_template.py` using the prompts, then check with `python simulate.py <bot> MyAgent 1000`. `rehearsal/solution/adapted_bot.py` is the worked answer, so don't read it first.
3. Check Codex login works, test a prompt, and bring chargers.
4. Know how to create a clean Python environment offline, in case venue Wi-Fi is bad.
5. Be at the venue when doors open. Note the email says 5:00 and the rules say check-in at 5:30; kickoff is 6:00 sharp.

## Files

- `docs/official_rules.txt`: rules text retrieved Nov 5
- `docs/CODEX_PROMPTS.md`: event-day prompts
- `docs/research_literature.md`: sourced literature review
- `lab/`: engine, field, tuner, experiments; `lab/test_engine.py` validates the simulator
- `reference_bot/bot.py`: generated lookup policy with blend parameters, subject to question 1 above; its adapter is unimplemented on purpose
- `reference_bot_mc/bot.py`: deadline-guarded rollouts with lookup fallback, using `run2/tuned_mcblend.json`
- `rehearsal/`: mock kit and worked adapter
- `snap2/`: logs and parameters for the first tuning, ablation, ICM, heads-up and variant runs; `lab/last_*.log` for the jam-call test
- `run2/`: logs and parameters for lookup tuning, sensitivity, point tables, features, meta-drift, the fair MC comparison and the blend; `run2/tuned_blend.json` is the recommended starting point
- `snap4/`, `snap5/`, `snap6/`: abandoned, never ran. Safe to delete.
- `third_party/poker-gym`: unofficial public simulator, cloned but **not run or used** (see below)

## Third-party simulator

`mack-dot/poker-gym` is a public, MIT-licensed rehearsal simulator with independent sparring bots, and would be a useful outside check on our results. It's cloned but wasn't audited or run: the automatic permission check blocked the command touching it. Decide for yourselves whether to run it, and look through it first. Don't put its code in a submission without clearing it with a Gamemaster (rule 6.1). Its runbook says "1,000 ms" per decision; the official rules say 1 ms.
