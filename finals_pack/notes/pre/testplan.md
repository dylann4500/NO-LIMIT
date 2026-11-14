# The day's test plan (pre-event note, topic D, for `tester`)

Drafted Saturday 14 November for Sunday's `tester` to check and extend. Notes only, no code; methods are in words.

**Grades** (as `strategy/EVIDENCE_TABLE.md`): **A** measured fact; **B** a method or change validated on full-table results; **C** candidate (one regional, simulation, one clean-room run, argument); **D** withdrawn; **arith.** exact arithmetic. Only the sparring bots' hand values and the replay deck order assume standard hold'em (section 8).

## What `tester` does in its first 15 minutes because of this note

1. **Minutes 0-5: the rules card, then today's noise figure.** Check the card field by field; from its payouts and seats take the per-table spread in section 1 and write today's sample sizes into the rig's notes.
2. **By minute 6 the runner prints a number** (speedrun: minute 6, A). Its first run is the noise run: the same zip as LIVE and as CAND on the same deals must show a paired difference of exactly zero. If not, the bot is clock-seeded or time-capped: tell `platform` at once.
3. **Second run: the same bot on two disjoint sets of deals.** That difference is today's noise.
4. **Sparring**: four hold'em-style fields now; the variant-aware field once theory's ranking exists (speedrun: ranking at minute 9, field at 16).
5. **First verdict on v1 by minute 12** (speedrun: 12), with a heads-up run, check-or-fold in the same field and the load average.
6. **Only then** the Modal image build, in the background. Its first job measures tables per second.

Not in the build hour: the cloned field. Built in the hour, uncalibrated, it scored our bot 12.2 against a real 18.4 (A).

## 1. Noise first, on paired deals

Paired deals: the same table seed, cards by position and seat rotation for LIVE and CAND.

| Quantity | Figure | Grade | Not 8-handed / other payouts |
|---|---|---|---|
| One bot's spread per table | 17.9 for an average bot at 8 seats, 50/30/20; measured 17-23 in every run, hence "20/√tables" | arith.; A | Winner-take-all 33; 65/35 23; 40/30/20/10 15; 6 seats 19; 10 seats 17; heads-up 10. Tables needed go with the square |
| Paired difference, two different designs | 18-28 a table: ±1.04 at 400 tables, ±0.86 at 600, ±0.39 at 5,000. That is 1.25 times one bot's error; unpaired is 1.41 | A | Scales with row 1 |
| Paired difference, a one-change variant | About 11: ±0.1 at 12,000 tables | A, simulation | Scales with row 1 |
| The pack's "13/√tables" | True only for near-identical variants | D for different designs | Same |
| Clock-seeded or time-capped bots | ±0.5 points a table run to run on identical deals | A, speedrun | Same |

Pairing helps little between designs because a table diverges at the first different decision (A): the remedy is more tables.

## 2. What sample size separates candidates by 1 point

Tables per candidate for a paired difference to reach 2 standard errors (arith., from section 1):

| Gap | Two different designs (spread 21) | One-change variant (spread 11) |
|---|---|---|
| 2 points | 450 | 120 |
| 1 point | 1,800 (3,100 for very different bots) | 500 |
| 0.5 point | 7,100 | 1,900 |
| 0.3 point | 19,600 | 5,400 |

- **The best of several looks better than it is**: by 0.85 standard errors for the best of 3, 1.03 of 4, 1.54 of 10 (arith.). To pick a true 1-point winner among four designs: about 4,000 tables each, then section 6.
- **Heads-up**: 600 tables gave ±0.38 (A), so 1 point needs about 400.
- **Local**: 20-31 tables a second on 4 processes against simple bots, 7 against clones (A). An 1,800-table pair takes 2-3 minutes; a 400-table run sees only 2-point holes.
- **Modal**: measured 6,000 tables in 2 minutes on 40 containers, 50 a second (A). The pack's target (20,000 tables for 3-4 candidates in 5 minutes) needs 200-270 a second and has never been run (C). At the measured rate a window affords four candidates at 4,000 tables.

## 3. Sparring bots to write

| Field | Made of | For |
|---|---|---|
| Calls everything; shoves constantly; premiums only; re-raises wide | Seven copies each, plus a mix; each plays the twist, some at random, some by theory's rule | Holes: a loss of over 2 standard errors to any one. A loose candidate lost 8.5 ± 1.5 to the premiums-only field (B) |
| The same four on today's ranking and twist rule | The main field once the ranking exists | Hold'em-valued sparring misjudged bots where pairs were the worst hands (A) |
| The kit's check-or-fold, in every field | The floor | It scored 20.1 beside our 20.5 in the speedrun (A): local fields that bust themselves flatter folding |
| Field-like sparring, from the first download | The four re-set to the field's measured rates | Rate targets. Regional proxies read a fold rate at 21-26% that was 57-69% on the field (A) |

Every verdict names its field, deals and seeds: design D claimed +10.7 against its own sparring and measured -8 against the base (A).

## 4. Replay testing on a downloaded round

- **Method**: rebuild each of our tables in the kit's engine with a rigged deck (our cards, the board, every shown or exposed card, random filler); find the deal order by probing; replay the logged actions; check stacks every hand and drop tables that drift; ask each candidate at each of our decisions.
- **Measured**: 1,012 tables, 134,032 hands, zero drift, 71 seconds on 4 processes; 5 minutes to build (A, regional kit).
- **It tells** where and how often a candidate differs from the logged bot and from the live bot, with no opponent model: run it first on every download.
- **It does not tell** what the table would have scored: chips at the one decision are exact, points are not (A; C).

## 5. The cloned field, on Modal, between rounds

- **Build**: one stand-in per team from its measured rates, acting by hand strength ranked within the range it would hold at that point (ranked among all hands, a clone folded 27% to re-raises where its team folded 80%: A); the whole fold/call/raise split calibrated in clones-only loops; bluffs added until river bettors' showdown win rate matches (71% against a real 65% before: A).
- **First, every round**: the bot that actually played, against its real score. Calibrated, it was within 0.2-0.7 in four rounds (B). A miss means warnings only.
- **Right twice**: a collapse (predicted -5.6 to -7.8, real about -9, from data held before the upload) and a gain (+1.6 to +2.9, real +2.3) (B, one regional).
- **Blind to**: gaps under 1 point (one pair ran -0.74 to +0.60 by bluff setting); the order of strong teams; opponents who respond. Forward predictions ran 0-1.8 high (A).
- **Use**: three opponent models (base, more or fewer bluffs, responding clones, the last never validated: C); a warning light only; a veto needs a predicted loss of 2 points or more with an understood reason.
- **Cost**: fit, calibration and three candidates took 10 minutes on 12 local cores (A).

## 6. The confirmation run

Rerun the top two on fresh deals before recommending either: in the clean-room test two candidates at +2.4 and +1.7 held at +2.0 and +2.2, and neither cleared 2 standard errors (B). Fresh deals remove luck, not model error, so confirm under a second opponent model too (C).

## 7. What local results can and cannot predict

| Local | Real field | Grade |
|---|---|---|
| v4 beat our older bots by +4.4 (600 tables) | 9.17, 100th of 125; the bot before it 19.02. Our old bots folded to aggression; the field called | A |
| v6: no strength test; cloned field +1.6 to +2.9 | +2.3 | B |
| 30 pre-event bots that tested locally | 18 found it neutral or wrong-signed | A |

- **Can predict**: legality and speed; a hole against a simple strategy; whether a targeted rate is hit; a heads-up regression (-1.9 ± 0.4 shipped unchecked: A); a collapse of several points, once the cloned field is calibrated.
- **Cannot predict**: an order within 1-2 points; strength from beating our own bots; adaptive rules; how 19 strong teams respond.
- **The practice round judges, with noise of its own.** A 1,000-table practice has a standard error of at least 0.7 (A, regional), so two practices must differ by 2 points to mean anything (arith.). A fixed bot scored 0.37 ± 0.06 higher in practice than in the next scored round (A). Only 8-17% of regional teams kept one bot from scored round through practice to scored round (A): among 19 opponents expect 2-4 yardsticks, so the field-median fallback will be usual (C).

## 8. If the format is not the one assumed

- **Not 8-handed or other payouts**: redo section 1's first row; section 2 scales by the square of the spread. Run every field at today's table size: a rehearsal ran every test at the wrong one (A).
- **Fillers**: with 20 teams about a fifth of our tables may seat copies of submitted bots (C): add that table shape once the Format page confirms it.
- **Hold'em-only**: the first four sparring bots value hands as hold'em does; the replay deck order is the regional engine's and must be probed again.

## Sources

Team archive (paths from the repo root):
- `finals_pack/.claude/agents/tester.md`, `finals_pack/strategy/FIRST_PROMPT.md` Parts 3 and 6, `DECISION_RULES.md` sections 3-4, `EVIDENCE_TABLE.md` section 4, `LESSONS.md`, `finals_pack/prep/SPEEDRUN_14NOV.md`.
- `research/finals_prep/prompttest/test_rig.md` (the clean-room rig: runner speed, paired errors at 200-600 tables, sparring results, replay, the failed in-hour cloned field, the fresh-deals rerun).
- `research/finals_prep/clone_field/REPORT.md` (calibration, the two predictions, forward bias, timing); `research/finals_prep/metagame/REPORT.md` and `appendix.md` (errors at 12,000 tables, one-change variants, clones of strong teams).
- `research/finals_prep/adaptation/REPORT.md` (practice against scored rounds, unchanged teams, round noise); `research/finals_prep/redteam/REPORT.md` (fillers and table shares at 20 teams).
- `docs/STEERING.md`, `docs/BUILDLOG.md` (v3-v10 local tests against real results; proxy opponents; seed flips); `docs/writeup/avalon-writeup.tex` (results by round).

Computed for this note (scratch arithmetic outside the repo): per-table spreads by payout shape, the sample-size table, the expected best of k (standard normal order statistics).

Outside source: variance reduction for poker evaluation exists (AIVAT reached the same significance with a tenth of the hands in the GTO Wizard benchmark, https://arxiv.org/abs/2603.23660) but needs a value model nobody can build in the hour; noted so nobody starts it on Sunday.
