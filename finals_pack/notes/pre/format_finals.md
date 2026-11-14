# If Sunday's table is case F: 6 seats, 6,000 chips, antes (pre-event note, for every role)

Drafted Saturday 14 November; extended the same afternoon with the portal findings (section 7). Notes only: no bot code and no strategy tables. Formulas, check values and what to compute first; the day's tables come from the real kit.

**Case F** is what the organizers' portal code fills in for a round of a competition whose variant id is `finals` or `finals_community`, wherever that round's rules are left empty (`prep/PORTAL_FINDINGS_14NOV.md`): 6 players, 6,000 chips, 20 hands per level, a 250-hand cap, and levels (small blind / big blind / ante per player) 10/20/4, 20/40/8, 30/60/12, 50/100/20, 80/160/32, 125/250/50, 200/400/80, 300/600/120, 500/1000/200, 800/1600/320, 1200/2400/480, 2000/4000/800. **Case R** is the regional table again: 8 players, 2,000 chips, the same levels, no ante. Those defaults do not touch payouts, the decision time or the time bank, so the most likely case F keeps the platform's 50/30/20, 1 ms and 100 ms bank: half the table is paid. That is the case this note works first; other payout shapes are secondary (section 3). Case F is not confirmed: an organizer can override any field, rules are set per round and can change between rounds (section 7), and the twist is unknown. `platform` confirms or refutes it by minute 2 (section 5). If it is refuted, read sections 6 and 7 and stop.

**Grades** (as `strategy/EVIDENCE_TABLE.md`): **arith.** exact arithmetic from the schedule (ICM is Malmuth-Harville, 50/30/20 unless said); **sim** measured on the regional kit's engine with regional bots at case-F rules, 400 tables a run (Appendix A): those bots were never tuned for 300 big blinds or antes, so it is good for length and timing and grade C for anything else; **C** solver-era hold'em knowledge or argument, untested on our field. Nothing here is above C until Sunday's first practice file.

## Case R against case F: the ten differences that matter most

| # | What | Case R | Case F | Comes from | Grade |
|---|---|---|---|---|---|
| 1 | Seats and the average score | 8 seats; an average seat scores 12.5; 3 of 8 paid | 6 seats; 16.7 with 50/30/20 (the platform default, which the Finals defaults leave alone); half the table is paid | seats | arith. |
| 2 | Depth | 100bb at hand 1 | 300bb at hand 1; 100bb only at hands 41-60, 37bb at 81-100, 15bb at 121-140 with all six alive: the same depth arrives two levels (40 hands) later | stack | arith. |
| 3 | Dead money | pot before any action 1.5bb | each seat antes 0.2bb every hand: 2.7bb six-handed, 2.1 three-handed, 1.9 heads-up. Folding costs 0.45bb a hand, 2.4 times a regional table | ante | arith. |
| 4 | Prices before the flop | a 2.5bb open needs 62.5% folds; an 8bb 3-bet 66.7%; the big blind needs 27.3% against 2.5bb | 48.1%; 60.6%; 22.4% | ante | arith. |
| 5 | Stack-to-pot ratio | single-raised pot 18, 3-bet pot 4.4: in a 3-bet pot, bets of 57% of the pot on three streets put the stacks in | 44 and 13 at 300bb, 22 and 6.5 at 150bb: a 3-bet pot at 300bb needs pot-sized bets on all three streets. An all-in before the flop is over 100 times the pot | stack | arith. |
| 6 | When play turns shove-or-fold | average stack 24bb by hand 81 | 55bb at hand 81, 32 at 121, 26 at 141: about the first 100 hands are played with room after the flop | stack | sim |
| 7 | Table length | 131 hands; 915 decisions a table, 114 a seat | 155 hands (one table in ten under 123 or over 183); 1,016 decisions a table, 169 a seat. No table reached hand 250 | stack | sim |
| 8 | Tournament pressure | hand 1 needs 55.6% to call all-in; five busts to the money; 21% of hands with 5 or 4 left, at an average 25-40bb | hand 1 needs 58.1%; three busts to the money; 35% of hands with 5 or 4 left, at an average 55-180bb | seats, stack | arith.; sim |
| 9 | What doing nothing scores | a pure folder is out at hand 102 and cashes 36%: 7.3 of 12.5 | out at hand 121, cashes 53%: 11.1 of 16.7 | stack, seats | sim |
| 10 | Samples and noise | each opponent at 7 of 19 = 37% of our tables (35% with the 21 teams now listed); 90 hands dealt per seat per table; spread per seat-table 17.9; seven sparring copies | 5 of 19 = 26% (25% with 21 teams); about 105-115 hands; 18.9; five copies; about 10% fewer tables per core-second | seats, stack | arith.; sim |

## 1. The shape of a case-F table

**Depth** (arith.). Average stack in big blinds = 36,000 / (players left × big blind): 300, 150, 100, 60, 37, 24, 15, 10, 6 for the nine levels up to hand 180 with six alive; one bust multiplies it by 6/5, the next by 5/4, and so on (Appendix B). With everyone alive, case F is as deep as case R was two levels earlier (1.0 to 1.25 times).

**Antes** (arith.). Pot before action = 1.5 + 0.2 × players, in big blinds. A seat that only folds holds 145bb at hand 21, 91 at 41, 50 at 61, 25 at 81, 10 at 101 and is gone at hand 121 (case R: 48, 30, 15, 8, 2, gone at 113).

**Break-evens** (arith.): fold rate a pure bluff needs = risk / (risk + pot before it); price of a call = call / (pot after the call).

| Play | Case R | F, six-handed | F, three-handed |
|---|---|---|---|
| Open to 2.0bb / 2.5bb from a seat with no blind | 57.1% / 62.5% | 42.6% / 48.1% | 48.8% / 54.3% |
| 3-bet to 8bb / 10bb over a 2.5bb open | 66.7% / 71.4% | 60.6% / 65.8% | 63.5% / 68.5% |
| Re-shove 20bb over a 2.5bb open | 83.3% | 79.4% | 81.3% |
| Open-shove 10bb | 87.0% | 78.7% | 82.6% |
| Big blind's price against 2.0bb / 2.5bb | 22.2% / 27.3% | 17.5% / 22.4% | 19.6% / 24.6% |

**Three phases** (sim; C). Average depth was 155bb at hand 21, 112 at 41, 76 at 61, 55 at 81, 43 at 101, 32 at 121, 26 at 141, 18 at 161. Hands 1-60: deep, every single-raised pot has a stack-to-pot ratio over 10. Hands 61-120: 30-75bb, raises and re-shoves, some play after the flop. From about hand 120-140: shove-or-fold for most stacks. Busts came at median hands 39, 68, 96, 124 and 158. The same bots at case R busted at 29, 47, 62, 73, 87, 105, 130, which matches the real regional (`placings.md`: our 6th, 5th, 4th at hands 60, 70, 86), so the engine and bots reproduce regional timing.

**Length, the cap, cost** (sim). 155 hands a table (sd 24) against 131. None of the 4,000 tables in Appendix A reached hand 250 (longest 221): by hand 221 the whole table holds 9bb. If the cap is ever reached, survivors split the unpaid places by ICM on their chips. A case-F table costs about 1.1 times a case-R table in CPU (1,010-1,016 decisions against 914-924); a seat makes 48% more decisions per table, so the per-table time bank is spread thinner.

## 2. What deep stacks and antes change in strategy

Solver sources are hold'em; the twist will move ranges, so read every number as a direction and a size, and express ranges as fractions of today's ranking as planned. All grade C unless marked.

| Topic | Case-R note | Case F | Why |
|---|---|---|---|
| Opening width | top teams opened 39-41% over 8 seats | Index by seats left to act: the first seat has 5 behind. Hold'em solver without antes at 100bb: about 17 / 21 / 27 / 44% with 5 / 4 / 3 / 2 behind. With antes widen each by a quarter to a third, early seats most | Break-even 48% not 62.5% (arith.). With 0.7bb of antes solvers open 4-6 points wider per seat; nine-handed with 0.9bb early seats nearly double. Case F has 1.2bb [1][2] |
| A pure steal | not priced | Profits with any hand when every seat behind folds 86% (5 behind), 69% (2 behind), or the big blind alone folds 43% to a small-blind open | arith.; refit from practice 1 by seats behind |
| Blind defence | big blind needs 27% | Needs 22%: defend wider, with hands that make strong hands; out of position at a ratio of 44 realizes less. First-in small blind folds a third of hands, not half | [1]; ICM hits the out-of-position player harder [5] |
| 3-bets | winner 3-bet 34-39%; field folded 67% (A, at 100bb) | Bluff break-even 61% (8bb) to 66% (10bb). Above 150bb the opener has the odds to call (39 times the call behind), so do not assume 67% holds: measure fold-to-3-bet by depth band. Size up out of position (10-11bb); from the big blind polarize | arith.; [3][4] |
| 4-bets, all-ins | 4-bet or shove at 100bb | 4-bets are not all-in: about 3 times the 3-bet deep, 2 times at 100bb; medium pairs stop 4-betting; flat more strong hands. All-in before the flop above 150bb only with the very top: a call needs 58% against the shover's range | [3][4]; arith. |
| Position | flats are as good as the play behind them (A) | Stronger: in position calls gain, out-of-position flats outside the big blind lose more | [3][5] |
| Sizing and planning | "big late bets are value" (C, from bets near all-in) | Bet per street to be all-in by the river = ((1 + 2 × ratio)^(1/3) − 1) / 2 of the pot: 1.74 at ratio 44, 1.0 at 13, 0.57 at 4.4. One pair is a two-street hand above ratio 10. Re-key the rule on bet / pot and bet / stack: a pot-sized bet is no longer near all-in. Under ICM bet smaller and check more | arith.; [4][5][6] |
| Small pairs, suited connectors | folded to 3-bets | Flopping a set is 11.8%; the old rule wants 15-25 times the call behind, and a bubble factor of 1.4 raises that to 20-35. Enough against opens above about 75bb, against 3-bets only near 300bb (39) and not at 150bb (19) | arith.; [7][8]; pairs lost value in two of three mock variants |

**Regional lessons that weaken.** Wide 3-bets for fold equity alone in levels 1-3. Shove and re-shove ranges by depth: still right, but 40 hands later, and each is cheaper with antes. The shove-heavy style has nothing to do above about 25bb, which is the first 100 hands. "No flat call of an open at 10bb+": at 100bb+ in position that default is probably wrong, and the defaults check would flag correct play. "A fold-only bot busts near hand 100 and finishes 4th": it lasts to 121 and cashed 53% (sim). The style cycle in `EVIDENCE_TABLE.md` §3b was simulated at 100bb: unknown here.

**Lessons that strengthen.** A raise needs a planned answer to the next raise (there are now three or four raise levels before all-in). Fold against the measured bluff rate after the flop, and watch the overshoot: most early chips now move after the flop. In-table adaptation: 169 decisions a seat and 41 hands six-handed against the same five seats. Survival: half the table is paid, and a bystander gains 1.2 points per collision from hand 1 (0.4 at eight). The ICM library test and the heads-up verdict stay mandatory.

## 3. Tournament equity with six players

- **Method.** E = ICM value of a stack set (a busted seat keeps its place's points). Bubble factor BF = (E_fold − E_lose) / (E_win − E_fold). Break-even equity for an even-money all-in = BF / (1 + BF); with pot odds, risk × BF / (risk × BF + reward). Heads-up, BF is 1.
- **Equal stacks** are rows 6 to 2 of `whatwins.md` §4; the table starts on row 6. Check values for 50/30/20: 58.1% (BF 1.39), 60.6% (1.54), 65.2% (1.87), 57.1% (1.33), 50%. Other shapes at 6 / 5 / 4 / 3 left: 65/35 gives 53.8 / 54.8 / 56.6 / 60.6; 60/25/15 gives 56.2 / 58.0 / 61.2 / 55.0; 40/30/20/10 gives 62.5 / 66.7 / 64.3 / 60.0; winner-take-all 50 throughout.
- **Where it peaks**: one place outside the money. With three paid that is 4 left, which case F reaches after two busts and plays at an average 55-90bb, not 25-40bb (sim): bubble pressure applies to raises and bets, not only to shoves.
- **Unequal stacks** move it more than seats do. Four left with stacks of 2.5, 1.5, 1.5 and 0.5 starting stacks: a 1.5 calling the 2.5 needs 72.7%, the 2.5 calling the 0.5 needs 52.3%. More check values in Appendix B.
- **Antes** lower a call threshold by 1.5-2 points at 10-15bb and 1 point at 25bb (big blind calling a shove six-handed at 15bb: 52.9% against 54.4%).
- **Chips at hand 1**: busting a player takes us from 16.7 to 28.7 points; busting costs 16.7.
- **Three-handed and heads-up** (sim). Three left from median hand 96, at 75bb (level 5), 48 (6) or 30 (7) each. Heads-up from median hand 124 for 33 hands, at 45bb (level 7), 30 (8), 18 (9) or 11 (10); case R went heads-up at 20-32bb. Both need a raise-and-call game first (solver heads-up at 50bb: the small blind folds 4% [9]); shove-or-fold tables matter only at the end: half the tables are over by hand 160, before heads-up stacks average under 30bb. Published shove charts assume no ante: the heads-up pot is 1.9bb, not 1.5, so recompute.

## 4. What in the bundle assumes case R

An audit of `strategy/`, `.claude/agents/` and `notes/pre/` (plus `CLAUDE.md`, `prompts/`, `START.md`) found 491 lines. Appendix C lists every one by file and line under twelve conversion rules, and quotes the 30 that carry the most. In short:

1. **No rules-card list names an ante** (9 lines, first `platform.md:27`): add ante per level, and check stack and seats.
2. **Points scale** (111 lines: `PLAN.md:39-40` "averages 12.5 ... don't panic at a 15", `DECISION_RULES.md:63,240`, every bar in `challenger_bar.md`): average 16.7; a 15 is below average; noise about 1.06 times; measure the SE on the day and keep bars in z.
3. **Seats and co-seating** (39 lines: `DECISION_RULES.md:229` "7 of our 19"): 5 of 19, or 5 of 20 with the 21 teams the portal now lists; 250-263 of 1,000 tables, not 370; five sparring copies; checks at 6, 3 and 2 players.
4. **Chances per table** (45 lines) and **table length and hand-number markers** (45 lines: "120-140 hands", "hand 40", "busts near hand 100"): 150-160 hands; hand 40 is 112bb deep with 5.3 alive; remeasure every chances figure.
5. **ICM check values** (26 lines: `platform.md:95-96` "8 equal ≈ 56%"): six equal 58.1%, five 60.6%; 4, 3 and 2 unchanged.
6. **Shove depths and depth bands** (43 lines: "about 12bb", bands ending at "40+") and **break-evens** (16 lines: `whatwins.md:25` "65%", the "65-75%" fold cap): recompute with the ante; add bands above 40bb; the cap is about 59-68%.
7. **Regional rates used as priors or thresholds** (98 lines) and **simulated style results** (7 lines): priors for the first practice only.
8. **Test counts and throughput** (16 lines: `tester.md:42-45`): about 0.9 times the tables per second.

## 5. The first ten minutes under case F

- **`platform` (by minute 2 if the kit allows, before anything else is computed; then again for every round, because rules are per round).** The bot itself reads `state.config` at every table and hard-codes none of it. From any decision's `state.config`: `players` (6), `starting_stack` (6000), `blinds` (12 levels, each `small_blind`, `big_blind`, `ante`; first (10, 20, 4), last (2000, 4000, 800)), `hands_per_level` (20), `hand_cap` (250), `payouts` (this table's own draw: read it every table), `decision_ms`, `time_bank_ms`, `memory_bytes`. Cross-check the kit engine's `TableRules` defaults and the Format page, write the ante into `bot/rules.json`, and announce "case F" or "case R" to both sessions. Then check the engine facts in Appendix A (antes are their own events; the pot includes them, a seat's bet does not).
- **`theory`, in this order.** (1) Minute 3, from formulas only: the depth table, pot by players, and the break-even card of section 1, sent to every stylist. (2) ICM for 6 to 2 players with today's payouts, checked against section 3. (3) Ranking as planned, against 1 to 5 opponents. (4) New: a deep-stack card (ratio after each raise level, the per-street bet formula, stack-off equity from the bubble factor, stack-to-call ratios). (5) Push/fold and call tables keyed on the ante and 2-6 players; a table needs them only from about hand 100, so they follow the deep card if time is short. (6) Heads-up and three-handed at 20-75bb.
- **Each stylist.** Depth bands: over 150, 60-150, 25-60, under 25bb. Six positions named by seats left to act. Opens widened for the ante. A size ladder with non-all-in 3-bets and 4-bets, and a written stack-off rule per band. A (pressure): lean on steals and bets in position, 3-bet bluffs only where the measured fold rate beats 61-66%. B (shove-heavy): say what it does for the first 100 hands, or become a position style. C (tight): plan for 25bb at hand 81 and 10bb at hand 101 if it only folds.
- **`tester`.** Six-seat fields (five sparring copies), the ante in every run, the heads-up run kept. Re-time the first job (expect about 0.9 of the regional rate) and measure the noise again (expect 21-22 / √tables). Add a run that reaches every blind level and an all-in for less than the ante: the 20-hand upload test sees only level 1. Report the floor bot (sim: 11 of 16.7).
- **`analyst` and `scout`.** Skip ante events, identify blinds by amount, add depth bands above 40bb, re-base the hand-40 markers. Report first: the hand of the third bust against hand 121, when a folder dies. If most tables are in the money before 121, survival pays.
- **Stays exactly as planned.** The roles, the clock, the decision rules in z units, release and upload discipline, the twist work, the ICM method and its library-trap test, the practice rounds as the judge.

## 6. If it is case R after all

Then nothing in sections 1, 2 and 5 applies and the pack stands as written (section 7 applies in either case, and a later round can still switch). Three things are still worth keeping: the minute-2 check of seats, stack and `ante` in `state.config` (it costs nothing, and it also catches a mixed format, such as antes at eight seats, where the pot is 3.1bb, or six seats without antes, measured in Appendix A); Appendix C as the map of where the format is written into the pack; and the six-to-two rows of section 3, which every eight-seat table passes through.

## 7. Round settings an organizer can change (added 14 November, from the portal's code)

Sources: `prep/PORTAL_FINDINGS_14NOV.md` and `prep/PORTAL_SIGNED_IN_14NOV.md` for what the portal can do; the regional kit's engine and hand-history README for what a setting does. None of these was on at the regional. Effects on variance are arith. where a number is given and C otherwise.

- **Rules are per round.** Every round carries its own players, stack, blinds, payouts, time limits, luck correction and resampling, so a practice round can be case R and a scored round case F. The bot reads `state.config` at every table and derives depth, pot, seats and payouts from it. Tables are keyed on players left, ante and payouts and fail loudly outside their grid. `analyst` and `tester` re-read each round's `rules` before using that round's numbers. The last round's results and our bot's health for it can be held back, so a format first used in the last round would never be seen: the bot for that round must already be correct at both formats.
- **Payouts.** Most likely 50/30/20 at six seats. The schema allows up to five paid places and a low-high pair per place. In the regional engine a pair is a range: each table draws its own points, and with `payout_total` set every table's places add up to that total, each strictly above the next. `state.config.payouts` holds the table's own draw.
- **Seating.** The portal lists 21 Finals teams (the pack says 20). Each iteration seats 24: at six seats three full tables and one with 3 scoring seats and 3 fillers. A given opponent is at 25% of our scored tables (5 of 20; 35% at eight seats); 14% of our scored tables hold fillers (23% at eight); we also sit as a non-scoring filler in 14% of iterations. With 20 teams those are 26%, 10% and 20%. Our tables in a round equal its iterations (Format page: at least 5,000 scored, about 1,000 practice), so a 1,000-table practice holds about 250 tables with any one opponent.
- **Culling** (within one round, a team confidently outside that round's top K stops getting tables; its round still scores on the tables played). Tables seen: a culled team's file ends at its last look, so read the table count before any rate. Variance: a culled score has a larger error and was stopped because it was low, so it leans low; contenders probably finish against contenders only, a harder field, and the file's opponent mix shifts to the top K. Use each result's own `margin_of_error`, never a fixed SE.
- **ICM luck correction** (`all_in_only`, or `legacy` = all-in and river; the maths is server-side, so a guess): all-in outcomes are replaced by their expectation in tournament points. Tables seen: unchanged. Variance: lower, most where play is shove-or-fold and least in case F's first 100 hands, where chips move without all-ins. Official points stop being place payouts, so a score recomputed from places will not match the portal. A correct decision stays correct.
- **Resampling** (regional kit: `play_resampled`, and the hand-history README). A table is played until `resampling_threshold` players remain (2-9, default 4, always below the table size); the rest is then played `resampling_continuations` times (1-8) with fresh cards, each from the same memory and time bank. Official points average the continuations; the hand file shows only the first. Tables seen: the same count, but one in K of the late games that scored. Spread per table for an average bot at 50/30/20, with equal stacks at the checkpoint (a best case): six seats, threshold 4, 18.9 falls to 15.7 / 13.9 / 12.9 at K = 2 / 4 / 8; threshold 5, 14.3 / 11.4 / 9.6; eight seats, threshold 4, 17.9 falls to 15.4 / 14.0 / 13.3. Over half of a case-F table's hands are played with four or fewer, so each table costs more and a round may run fewer iterations.
- **Held results.** The final round's results and our bot's health for it can be held until the organizers reveal them, and the leaderboard can be held at any time: choose the last bot on earlier rounds and practice.
- **Multipliers**: linear 1-6, Fibonacci 1, 2, 3, 5, 8, 13, or powers of two 1-32. The last round is 29%, 41% or 51% of the total. The key showed linear at 15:44 on 14 November; it can change.
- **Variant id.** `finals` and `finals_community` get identical table defaults: treat them the same. The Finals Format page showed the regional table (8 players, 2,000 chips, no antes) on 14 November, with no variant set and no round queued. The case-F defaults are applied when a round is added under one of those ids, so that page says little either way.

---

## Appendix A. Measurements (14 November, regional kit engine, variant `flop_discard_reveal`, 400 tables a run)

Run on this laptop under load 14-26 with one table in flight per run, decision limit 1 ms, time bank 100 ms, payouts 50/30/20. Throwaway runner outside the repo, deleted. "Regional bots" are v10, v9s, v6, v3b, v8, v7, v9; the kit's examples are `check_or_fold` and `min_raiser`. Intervals are 95%.

| Run | Rules | Seats | Hands a table: mean (10%-90%) | Decisions a table / a seat | Median hand of each bust | In the money by hand 100 / 120 |
|---|---|---|---|---|---|---|
| F-A | 6 × 6,000, antes | six different regional bots | 154.5 (123-183) | 1,016 / 169 | 39, 68, 96, 124, 158 | 57% / 85% |
| F-C | 6 × 6,000, antes | v10 ×2, v9s ×2, v6, v3b | 156.0 (128-184) | 1,016 / 169 | 38, 66, 94, 120, 156 | 60% / 88% |
| F-D | 6 × 6,000, antes | five regional + `check_or_fold` | 159.3 (130-184) | 1,010 / 168 | 50, 89, 118, 125, 162 | 22% / 62% |
| F-B | 6 × 6,000, antes | four regional + both examples | 149.7 (116-180) | 860 / 143 | 5, 50, 100, 120, 151 | 50% / 76% |
| F without antes | 6 × 6,000 | as F-A | 164.4 (137-190) | 994 / 166 | 52, 87, 111, 138, 166 | 33% / 64% |
| Six seats, regional stack | 6 × 2,000 | as F-A | 118.2 (96-142) | 680 / 113 | 35, 57, 74, 91, 119 | 96% / 100% |
| R-A | 8 × 2,000 | v10, v9s, v6, v3b, two each | 131.4 (107-154) | 915 / 114 | 29, 47, 62, 73, 87, 105, 130 | 79% / 98% |
| R-C | 8 × 2,000 | eight different regional bots | 131.6 (109-152) | 914 / 114 | 30, 48, 63, 74, 89, 107, 133 | 77% / 99% |
| R-D | 8 × 2,000 | seven regional + `check_or_fold` | 130.4 (111-149) | 924 / 116 | 37, 58, 71, 87, 101, 108, 130 | 48% / 99% |
| R-B | 8 × 2,000 | six regional + both examples | 130.8 (106-153) | 872 / 109 | 4, 39, 65, 83, 98, 106, 130 | 58% / 98% |

- **Average stack in big blinds at hands 21 / 41 / 61 / 81 / 101 / 121 / 141 / 161** (players alive in brackets at 41, 81, 121). F-A: 155 / 112 (5.3) / 76 / 55 (4.1) / 43 / 32 (2.8) / 26 / 18. R-A: 52 / 39 (6.9) / 28 / 24 (4.1) / 22 / 18 (2.3) / 14 / 9.
- **Average depth when each bust came** (F-A, median with 10%-90%): first 150bb (60-300), second 72 (45-180), third 56 (22-90), fourth 30 (20-75). The stack that busted first held a median 51bb at the start of that hand.
- **Hands by players alive.** F-A: 41 with six, 27 with five, 26 with four, 27 with three, 33 heads-up. R-A: 29, 17, 14, 13, 14, 18, 26 from eight down to two. Hands dealt per seat per table: 105-106 (F-A, F-C) against 83-84 (R-A, R-C; the real regional was 90).
- **The folder** (`check_or_fold`). F-D: 11.1 ± 1.0 points of a 16.7 average; places 2nd 5%, 3rd 48%, 4th 40%, 5th 6.5%; out at median hand 121. R-D: 7.3 ± 1.0 of 12.5; 2nd 2.5%, 3rd 33%, 4th 51%, 5th 13%; out at hand 102. With a `min_raiser` also at the table (out by hand 5): 16.1 ± 1.0 in F-B, 8.2 ± 1.0 in R-B.
- **What the antes did** (F-A against the same seats without antes): 10 hands shorter, first bust at hand 39 instead of 52, in the money by hand 100 in 57% of tables instead of 33%.
- **Cost.** CPU per table, engine plus bot processes: 0.35-0.37 core-seconds (F-C, F-D) against 0.34 (R-D): about 2.7-2.9 tables per core-second against 2.9. Wall-clock rates ranged 1.7-2.5 tables a second for the same rules as the load changed, so they are not quoted as a result.
- **Failed decisions**: 0-28 per run of 270,000-407,000 (worst F-A, 0.007%). Inconclusive on a loaded machine.
- **Spread per seat-table**: 18.86 at six seats and 17.85 at eight for 50/30/20, exact for any field with no ties: sqrt(sum of squared payouts / seats − mean²).
- **Seating** (the engine's `seat_iteration`, 20,000 draws). 20 teams: six-seat tables come as 6 + 6 + 6 and one table of 2 scoring seats with 4 fillers; a given opponent is at 26% of our scored tables (37% at eight seats); our scored table is the short one 10% of the time (20%); we also sit as a filler in 20% of draws (the same). 21 teams, as the portal now lists: 6 + 6 + 6 and one table of 3 scoring seats with 3 fillers; 25% (35%); 14% (23%); 14% (14%).
- **Engine facts with an ante** (regional kit's engine; check them on Sunday's): each live seat posts an `ante` event before the blinds; heads-up the big blind is posted before the small blind; the pot a bot sees includes the antes (54 at hand 1 six-handed) but a seat's bet does not, and stacks are already net of the ante, so the largest raise at hand 1 is to 5,996; a stack no bigger than the ante is all-in on the ante; the hand log's `blinds` field is [small, big, ante].

## Appendix B. Arithmetic

**Average stack in big blinds, case F** (36,000 chips) by level and players alive, with case R (16,000 chips, eight alive) beside it:

| Level | Hands | Big blind | 6 | 5 | 4 | 3 | 2 | R, 8 alive |
|---|---|---|---|---|---|---|---|---|
| 1 | 1-20 | 20 | 300 | 360 | 450 | 600 | 900 | 100 |
| 2 | 21-40 | 40 | 150 | 180 | 225 | 300 | 450 | 50 |
| 3 | 41-60 | 60 | 100 | 120 | 150 | 200 | 300 | 33 |
| 4 | 61-80 | 100 | 60 | 72 | 90 | 120 | 180 | 20 |
| 5 | 81-100 | 160 | 37.5 | 45 | 56 | 75 | 112 | 12.5 |
| 6 | 101-120 | 250 | 24 | 29 | 36 | 48 | 72 | 8 |
| 7 | 121-140 | 400 | 15 | 18 | 22.5 | 30 | 45 | 5 |
| 8 | 141-160 | 600 | 10 | 12 | 15 | 20 | 30 | 3.3 |
| 9 | 161-180 | 1,000 | 6 | 7.2 | 9 | 12 | 18 | 2 |
| 10 | 181-200 | 1,600 | 3.8 | 4.5 | 5.6 | 7.5 | 11 | 1.2 |
| 11 | 201-220 | 2,400 | 2.5 | 3 | 3.8 | 5 | 7.5 | 0.8 |
| 12 | 221-250 | 4,000 | 1.5 | 1.8 | 2.2 | 3 | 4.5 | 0.5 |

- **Stack-to-pot ratio** after a 2.5bb open and a big-blind call / a 3-bet to 10bb called / a 4-bet to 25bb called (22bb at 100bb or less), six-handed with antes: 300bb: 44 / 13 / 5.2. 150bb: 22 / 6.5 / 2.4. 100bb: 14.5 / 4.1 / 1.7. 75bb: 10.8 / 3.0 / 1.1. Regional (100bb, no ante): 17.7 / 4.4 / 1.7.
- **Stack behind as a multiple of the call**: calling a 2.5bb open, 119 at 300bb, 59 at 150bb, 39 at 100bb, 29 at 75bb; the opener calling a 3-bet to 10bb, 39 / 19 / 12 / 9.
- **Fold cost per hand** (1.5 + 0.2n) / n big blinds: 0.45 at six, 0.58 at four, 0.70 at three, 0.95 heads-up; case R 0.19 at eight.
- **Bystander's gain** when two equal stacks collide and one busts, equal stacks, 50/30/20: +1.2 with six left, +2.3 with five, +5.8 with four, +3.3 with three.
- **At the cap**, 50/30 heads-up: each player gets 30 + 20 × chip share (1 point per 1,800 chips).
- **Unequal stacks**, break-even to call all-in (starting stack = 1; 50/30/20). Four left (2.5, 1.5, 1.5, 0.5): 1.5 calling the 2.5 needs 72.7%; the 0.5 calling the 2.5 needs 59.6%; the 2.5 calling the 0.5 needs 52.3%. Four left (3, 2, 0.5, 0.5): the 2 calling the 3 needs 77.3%. Six left (2, 1, 1, 1, 0.5, 0.5): a 1 calling the 2 needs 61.9%; the 2 calling a 1 needs 56.5%. Three left (3, 2, 1): the 2 calling the 3 needs 61.8%; the 3 calling the 1 needs 51.7%.
- **ICM calls with dead money** (big blind calling a shove, equal stacks, shover outside the blinds, antes against no antes): six left 10bb 50.3% / 52.5%, 15bb 52.9% / 54.4%, 25bb 54.9% / 55.9%; four left 15bb 61.2% / 62.0%.

## Appendix C. Every line in the pack that assumes case R

Method: one reader went through all 26 files of `strategy/`, `.claude/agents/` and `notes/pre/` and `CLAUDE.md` in full, and the minute-0 sections of `prompts/` and `START.md`; every quote was matched to its line by script; 27 lines were re-checked by hand. Classification into the rules below was by script and is approximate at the edges. Paths are relative to `finals_pack/`; `pre/` is `notes/pre/`, `agents/` is `.claude/agents/`, the rest are in `strategy/` unless a folder is shown. `a-b` is a block of rows. Nothing was edited.

### C.1 The thirty lines that carry the most

| File:line | Text | In case F |
|---|---|---|
| `agents/platform.md:27` | "players per table, stack, blinds and their schedule, hands per match, time limit and" | Add the ante per level. Same list at `DECISION_RULES.md:47`, `PLAN.md:198`, `agents/tester.md:27`, `agents/theory.md:15`, `CLAUDE.md:74`, `prompts/BUILDER.md:57`, `START.md:81`, `pre/whatwins.md:11` |
| `PLAN.md:39-40` | "averages 12.5 points per table ... Don't panic at a 15." | Averages 16.7; a 15 is below average; the same relative score is about 20 |
| `DECISION_RULES.md:63` | "Practice SE is **at least 0.7** points per" | About 0.74 for the same table count (spread 18.9 not 17.9): measure it |
| `DECISION_RULES.md:240` | "compressed near 12.5 points per table; differences under 2.0 ... (1.4 between a" | Near 16.7; about 2.1 and 1.5 at the same table count |
| `DECISION_RULES.md:229` | "each team sits at about 7 of our 19 tables" | 5 of 19 (26%); 5 of 20 with 21 teams |
| `FIRST_PROMPT.md:409` | "about 370 each with 20 teams at 8 seats" | About 263 of 1,000 (250 with 21 teams); `pre/first1000.md:43` "1,840 of our tables instead of 370" becomes 1,316 and 263 (1,250 and 250) |
| `FINGERPRINTING.md:17` | "8 + 8 + 4 teams with 4 fillers at the short table" | 6 + 6 + 6 + 2 with 4 fillers, ours the short table 10% of the time; with 21 teams 6 + 6 + 6 + 3 with 3 fillers, 14% |
| `agents/analyst.md:98` | "SE = 21/√tables: 0.66 at 1,000, 0.47 at 2,000, 0.30 at 5,000" | About 22/√tables: 0.70, 0.50, 0.31 (C until measured). Same at `agents/tester.md:36,83`, `FIRST_PROMPT.md:248,450`, `pre/first1000.md:53` |
| `pre/first1000.md:25` | "at our tables they average (100 - our score)/7" | (100 − our score) / 5 |
| `agents/platform.md:95-96` | "8 equal ≈ 56%, 3 equal ≈ 57%, 4 equal ≈ 62-65% (50/30/20)" | Add 6 equal = 58.1%, 5 equal = 60.6%; the 8-seat check cannot run. Same at `agents/bughunter.md:39`, `agents/theory.md:39-40`, `FIRST_PROMPT.md:174,226`, `pre/buildplan.md:72` |
| `FIRST_PROMPT.md:231` | "right at 8, 3 and 2 players and after a bust" | At 6, 3 and 2 players, with ante events and an all-in on the ante. Same at `FIRST_PROMPT.md:599`, `agents/bughunter.md:41,99`, `agents/platform.md:97,160` |
| `TWIST_NOTES.md:85` | "50/30/20 with 8 players needs 8×7×6 = 336 orderings" | 6×5×4 = 120: the full-table ICM costs about a third |
| `agents/theory.md:46` | "jam/fold by fictitious play keyed by players left, position and stack (bb)" | Solve with the ante in the pot, players 2-6. Same at `FIRST_PROMPT.md:347` |
| `agents/stylist.md:52` | "shove-or-fold first in at about 12bb or less" | Recompute: each fold-through wins 2.7bb, not 1.5, so the depth rises; do not carry 12. Same at `FIRST_PROMPT.md:179,286`, `pre/whatwins.md:46` |
| `agents/stylist.md:51` | "no flat call of an open at 10bb+ except big-blind defence" | Probably wrong in position at 100bb+; the defaults check (`FIRST_PROMPT.md:285-288,394`, `agents/analyst.md:39`, `agents/platform.md:88-89`, `agents/bughunter.md:58`) would flag it |
| `agents/stylist.md:45` | "B, shove-heavy: few small preflop raises; mostly shove or" | No such play above about 25bb: section 5 |
| `agents/stylist.md:48` | "near hand 100 and finishes 4th" | Hand 121; 3rd in 48% and 4th in 40% of sim tables. Same at `FIRST_PROMPT.md:281` |
| `pre/whatwins.md:25` | "8bb over a 2.5bb open risks 8 to win 4: 65% folds" | Risks 8 to win 5.2: 60.6% (the no-ante figure is 66.7%) |
| `agents/stylist.md:54` | "65-75%, a starting value" | About 59-68% for 3-bets to 7.5-11bb. Same at `DECISION_RULES.md:221`, `PLAN.md:85,146`, `FIRST_PROMPT.md:300`, `EVIDENCE_TABLE.md:99`, `pre/contrarian.md:11` |
| `pre/whatwins.md:83` | "**Transfers exactly**: section 4 and the break-evens." | Section 4 does (start on row 6, minus 1-2 points for antes when short); the break-evens do not |
| `pre/field.md:64` | "Over 60: steal wide. Under 40: defence wave" | The steal break-even falls from 62.5% to 48%: shift both thresholds down about 14 points |
| `pre/stat_definitions.md:49` | "The big blind was the seat of the last blind posted. An ante, straddle or dead blind breaks that" | Antes are separate `ante` events posted before the blinds, so the rule survives six-handed on the regional engine; heads-up the last blind posted is the small blind. Identify blinds by amount |
| `FIRST_PROMPT.md:384-386` | "(6-8, 4-5, 2-3) ... bucketed <10, 10-20, 20-40, 40+" | Players left 5-6, 4, 2-3; add 40-100, 100-200, 200+. Same at `agents/analyst.md:92-94`, `pre/stat_definitions.md:19`, `FINGERPRINTING.md:29` |
| `pre/stat_definitions.md:53` | "Depth bands and the hand-40 marker assume 2,000 chips" | Hand 40 is 112bb deep with 5.3 of 6 alive (sim); the regional hand-40 depth arrives near hand 80 |
| `pre/contrarian.md:38` | "1.7+ all-in collisions per table before hand 40, 5.4 or fewer players left at hand 40, and the floor bot scores 10+" | Re-base all three: use busts before hand 121 and the floor bot against 16.7 (sim 11.1). Same at `pre/field.md:67`, `pre/stat_definitions.md:39-40` |
| `agents/theory.md:43` | "over a whole table (roughly 120-140 hands)" | 150-160 hands; a seat is dealt 105-115 (sim). Same at `FIRST_PROMPT.md:142`; `pre/variants.md:395` "40 auctions per table" scales with it |
| `FIRST_PROMPT.md:638` | "Median chances per seat per table: fold to a 3-bet 1, fold to a flop bet 3, turn 1, river 0" | Unknown: 48% more decisions a seat and more play after the flop. Remeasure from practice 1 |
| `pre/finalists.md:49` | "the regional's 90 hands dealt per seat per table" | About 105-115, so a team needs about 0.8 times the shared tables; shared tables are 0.71 times as common, so the Tables column at lines 54-67 is about 1.1 times in tables of ours |
| `agents/tester.md:43` | "139 tables a second, 250 tables a shard, 2.6 tables a second per container" | About 125 and 2.3-2.4 (C): time the first job. `agents/tester.md:45` "15,000-20,000 tables" becomes about 13,500-18,000 |
| `agents/tester.md:38` | "re-raises wide (seven" | Five copies. Same at `FIRST_PROMPT.md:453`, `pre/testplan.md:52` |

### C.2 Every line, by conversion rule

**A. Rules-card field lists with no ante** (9 lines). Becomes: add the ante per level; confirm seats and stack. `DECISION_RULES.md` 47; `PLAN.md` 198; `agents/platform.md` 27; `agents/tester.md` 27; `agents/theory.md` 15; `pre/whatwins.md` 11; `CLAUDE.md` 74; `prompts/BUILDER.md` 57; `START.md` 81

**B. Points scale: scores, gaps, bars and standard errors in points per table** (111 lines). Becomes: average 16.7 (if 100 points to three places); spread per seat-table 18.9, so standard errors are about 1.06 times at the same table count; an edge that is a share of the average is worth 1.33 times as many points; keep every bar in z and take the SE from the day. `DECISION_RULES.md` 15, 18, 63, 69, 89, 90, 103, 240; `EVIDENCE_TABLE.md` 38, 42, 49, 50, 54, 96, 129; `FINGERPRINTING.md` 97, 107; `FIRST_PROMPT.md` 84, 147, 183, 248, 338, 450, 451, 457; `PLAN.md` 25, 39, 40, 79; `TWIST_NOTES.md` 95; `agents/analyst.md` 98, 100; `agents/challenger.md` 65, 68, 74, 89; `agents/tester.md` 36, 71, 82, 83, 101; `agents/theory.md` 72; `pre/challenger_bar.md` 7, 22, 24, 27, 30, 39, 40, 52, 85, 95, 98, 149, 152, 171-173, 186, 187, 219, 249, 264, 268; `pre/contrarian.md` 20, 21, 30, 41, 47, 54, 56, 61; `pre/field.md` 17, 30, 82; `pre/finalists.md` 304, 306, 722; `pre/first1000.md` 9, 11, 12, 22, 25, 35-41, 43, 49, 53, 119; `pre/placings.md` 8, 24, 57, 131, 148; `pre/testplan.md` 24, 25, 26, 36, 54, 72, 89; `pre/whatwins.md` 27, 28, 29, 48, 74, 75, 84; `CLAUDE.md` 6; `prompts/RESEARCH.md` 98, 141

**C. Seats, co-seating and fillers** (39 lines). Becomes: 6 seats, 5 opponents; each opponent at 5/19 of our tables (5/20 with 21 teams); checks at 6, 3 and 2 players; "4-6 left" is the whole table from hand 1; one scored table in ten has four filler seats (one in seven has three, with 21 teams). `DECISION_RULES.md` 229; `FINGERPRINTING.md` 17, 22, 33; `FIRST_PROMPT.md` 44, 83, 231, 384, 409, 599; `LESSONS.md` 212; `TWIST_NOTES.md` 31, 174; `agents/analyst.md` 58, 92; `agents/bughunter.md` 41, 99; `agents/platform.md` 97, 160; `pre/field.md` 50; `pre/finalists.md` 20, 44, 55, 822, 839; `pre/first1000.md` 18, 24, 43; `pre/placings.md` 9, 10, 12, 53, 55; `pre/stat_definitions.md` 40, 55; `pre/testplan.md` 94; `pre/variants.md` 9; `pre/whatwins.md` 75

**D. Chances per seat per table, prior weights, noise of a rate** (45 lines). Becomes: about 1.3 times the hands and 1.5 times the decisions per seat per shared table (sim), 0.71 times the shared tables; prior weights (4, 30) are strengths and stay; every "n chances" and "±" figure is remeasured from practice 1. `DECISION_RULES.md` 216; `EVIDENCE_TABLE.md` 130, 131; `FINGERPRINTING.md` 94; `FIRST_PROMPT.md` 158, 191, 523, 524, 542, 622, 631, 638; `agents/analyst.md` 71, 105; `agents/platform.md` 82; `pre/buildplan.md` 63, 64; `pre/challenger_bar.md` 79, 259; `pre/contrarian.md` 31, 36, 37; `pre/field.md` 53, 58, 60, 119-134; `pre/finalists.md` 49, 54, 55, 56, 57, 58, 59, 60, 61, 62; `pre/first1000.md` 29, 31, 99-115; `pre/stat_definitions.md` 9, 10, 16, 54; `pre/variants.md` 196, 395

**E. Table length, hand-number markers, timings** (45 lines). Becomes: 150-160 hands a table; a marker at hand h in case R sits near hand h + 40 for depth; file size and parse time per table about 1.2 times plus one ante event per live seat per hand (about 630 a table); round and download times scale with it. `DECISION_RULES.md` 74, 153; `FINGERPRINTING.md` 84; `FIRST_PROMPT.md` 142, 281, 432, 471, 472, 520, 633, 634; `PLAN.md` 113, 202, 223; `TWIST_NOTES.md` 85; `agents/analyst.md` 28, 32, 48, 102; `agents/stylist.md` 48; `agents/tester.md` 42, 43, 44; `agents/theory.md` 43; `pre/buildplan.md` 58; `pre/contrarian.md` 22; `pre/first1000.md` 16, 43, 75, 119; `pre/placings.md` 26, 105-115; `pre/stat_definitions.md` 39, 53; `pre/testplan.md` 45, 46, 62, 73; `pre/variants.md` 187; `prompts/RESEARCH.md` 80, 108, 120, 145

**F. ICM values and their unit tests** (26 lines). Becomes: the table starts at six (58.1%); 4, 3 and 2 left are unchanged; antes take 1-2 points off short-stack calls; bystander gains start at +1.2. `EVIDENCE_TABLE.md` 75; `FIRST_PROMPT.md` 57, 173, 174, 226, 227, 627; `TWIST_NOTES.md` 85; `agents/bughunter.md` 39; `agents/platform.md` 95, 96; `agents/theory.md` 39, 40; `pre/buildplan.md` 71, 72; `pre/contrarian.md` 19, 20; `pre/placings.md` 46; `pre/whatwins.md` 53, 55-62, 64, 65, 66, 67, 68

**G. Shove depths and depth bands** (43 lines). Becomes: recompute every depth with the ante in the pot (direction: shove-or-fold starts deeper; an upper bound from equal pot-to-stack ratio is 12 × 2.7 / 1.5 ≈ 21bb, not a value); these depths arrive 40 hands later; bands need rows above 40bb; measured shove and call rates are regional priors. `DECISION_RULES.md` 176, 236; `FIRST_PROMPT.md` 179, 274, 285, 286, 288, 347, 394; `LESSONS.md` 169; `agents/analyst.md` 39; `agents/bughunter.md` 58; `agents/platform.md` 88, 89; `agents/stylist.md` 47, 51, 52; `agents/theory.md` 46; `pre/contrarian.md` 19; `pre/field.md` 63, 79, 127; `pre/finalists.md` 56, 59, 60, 61, 62, 95, 230, 240, 677, 867; `pre/placings.md` 10, 44; `pre/stat_definitions.md` 19, 30, 34; `pre/whatwins.md` 46, 76, 81, 98

**H. Break-evens without dead antes** (16 lines). Becomes: add 0.2bb per live seat to the pot: section 1's table. `DECISION_RULES.md` 221; `EVIDENCE_TABLE.md` 99; `FIRST_PROMPT.md` 300; `PLAN.md` 85, 146; `agents/stylist.md` 54; `agents/theory.md` 49; `pre/contrarian.md` 11; `pre/field.md` 61, 64, 70; `pre/finalists.md` 794; `pre/placings.md` 43; `pre/whatwins.md` 13, 25, 83

**I. Field rates measured eight-handed at 100bb with no ante, used as priors or thresholds** (98 lines). Becomes: a prior for the first practice only, matched by seats left to act and depth band; expect opens up, big-blind folds down, short-stack shoves up, fold-to-3-bet unknown above 100bb; team cards in `finalists.md` describe habits (sizes, adaptation rules) that may carry over, not rates. `DECISION_RULES.md` 211, 212, 217, 222, 223, 234, 235; `EVIDENCE_TABLE.md` 31, 33, 37, 52, 96, 126, 127; `FINGERPRINTING.md` 49, 50, 52; `FIRST_PROMPT.md` 156, 159, 163, 168, 180, 181, 301, 348, 624; `LESSONS.md` 187; `PLAN.md` 21, 22, 28, 34, 185; `TWIST_NOTES.md` 163; `agents/scout.md` 27, 55, 56, 95; `agents/stylist.md` 77; `agents/theory.md` 31; `pre/buildplan.md` 65, 73; `pre/challenger_bar.md` 80, 87, 265; `pre/contrarian.md` 9, 20, 36, 37, 38; `pre/field.md` 4, 5, 12, 13, 18, 28, 29, 34, 44, 58, 59, 61, 62, 63, 65, 66, 67, 69, 76, 136, 137; `pre/finalists.md` 46, 63-67, 84, 86, 89, 102-110, 132, 137, 169, 318-338, 342-564, 852; `pre/stat_definitions.md` 24-40; `pre/variants.md` 64; `pre/whatwins.md` 22, 23, 24, 36, 37, 39, 47, 49, 82

**J. Test counts and throughput** (16 lines). Becomes: five sparring copies; about 0.9 times the tables per second; table counts for a given SE about 1.12 times if the bar stays in points, unchanged if it is rescaled. `FIRST_PROMPT.md` 453, 473, 487, 501, 634; `agents/platform.md` 93; `agents/tester.md` 38, 45, 81, 98; `pre/testplan.md` 38-41, 43, 44, 46, 52; `prompts/RESEARCH.md` 88

**K. Simulated style results at the regional format** (7 lines). Becomes: unknown; the shove corner of the cycle has no early game. `DECISION_RULES.md` 226; `EVIDENCE_TABLE.md` 90, 92, 94; `FIRST_PROMPT.md` 277; `pre/contrarian.md` 21

**L. Other: size bins, recognition accuracy, style premises** (36 lines). Becomes: open sizes in big blinds may shift with antes (solvers open larger), so last round's size fingerprints are weaker; recognition by hand 20 has more events per seat at six seats; depth-restricted statistics ("25bb or more") cover far more hands. `EVIDENCE_TABLE.md` 56, 57; `FINGERPRINTING.md` 19, 21, 29, 72; `FIRST_PROMPT.md` 385, 386, 398, 521, 636, 637; `PLAN.md` 32; `agents/analyst.md` 94; `agents/scout.md` 36, 65, 92; `agents/stylist.md` 45; `pre/buildplan.md` 82; `pre/contrarian.md` 19; `pre/finalists.md` 54, 298, 570, 914; `pre/first1000.md` 76; `pre/placings.md` 63; `pre/stat_definitions.md` 31, 43, 47, 49; `pre/variants.md` 47, 396; `prompts/BUILDER.md` 61

## Appendix D. Sources

Team files: `prep/PORTAL_FINDINGS_14NOV.md` and `prep/PORTAL_SIGNED_IN_14NOV.md` on `emu/rehearsal` (the Finals defaults, per-round rules, culling, luck correction, resampling fields, held results, multipliers, the 21 teams, the Finals Format page), the regional kit's `hand-history/README.md` (resampling: official points average all continuations, the file shows the first), `strategy/EVIDENCE_TABLE.md` (grades; regional rates), `notes/pre/whatwins.md` §4 (equal-stack thresholds, reproduced here to 0.1 point by an independent calculation), `notes/pre/placings.md` and `first1000.md` (real regional bust hands and table length), the regional kit's engine (`sdk/engine/src/poker_engine/table.py`, `seating.py`, `scoring.py`, `holdem.py`).

Outside sources, all hold'em, read on 14 November through page summaries, not line by line:

1. GTO Wizard, "How to Crush Ante Cash Games" (100bb, 7-max, 0.7bb of antes: opens 4-6 points wider per seat; first-in small blind folds 33% instead of 54%; big blind continues about 10 points more; larger opens and 3-bets): https://blog.gtowizard.com/how_to_crush_ante_cash_games/
2. Upswing, "What is an Ante & How Do They Change Your Strategy?" (nine-handed, 0.1bb each: a 2.25bb open needs 48% instead of 60%; early seats open about 20% instead of 10%, 28% instead of 16%): https://upswingpoker.com/poker-antes-tournament-raising-strategy/
3. GTO Wizard, "IP 4-Betting in Deep-Stacked Cash Games" and "OOP 4-Betting in Deep-Stacked Cash Games" (200bb against 100bb: big-blind 3-bets more polar; 4-bets about three times the 3-bet instead of two; medium pairs stop 4-betting; more checking in position): https://blog.gtowizard.com/ip-4-betting-in-deep-stacked-cash-games/ and https://blog.gtowizard.com/oop-4-betting-in-deep-stacked-cash-games/
4. Upswing, "What is a Deep Stack & How Should You Adjust Your Play" (3-bet to 10-11bb out of position at 200bb; flat QQ and AK more; play the raiser's hand more defensively out of position; one solver's ranges barely change from 100bb to 300bb): https://upswingpoker.com/deep-stack-strategy-tips/
5. GTO Wizard, "How ICM Quietly Shapes Postflop Strategy From the Start" (a 1.8% risk premium already raises checking from 48% to 54% and shifts bets smaller; out-of-position equity realization falls from 96% to 90%): https://blog.gtowizard.com/how-icm-quietly-shapes-postflop-strategy-from-the-start/
6. GTO Wizard, "How ICM Impacts Postflop Strategy" (big bets shrink, small bets become checks): https://blog.gtowizard.com/how-icm-impacts-postflop-strategy/
7. GTO Wizard, "The Trouble With Implied Odds" (the full stack is rarely won): https://blog.gtowizard.com/the-trouble-with-implied-odds/
8. SplitSuit, "Implied Odds" and PokerStrategy forum threads (the 15, 20 and 25 times rules of thumb): https://www.splitsuit.com/implied-odds-poker
9. GTO Wizard, "Heads up! Exploiting SB's Preflop Mistakes" (50bb with a 0.12bb ante: the small blind folds 4% and raises 64%): https://blog.gtowizard.com/heads-up-exploiting-sbs-preflop-mistakes/
10. GTO Wizard, "What is the Bubble Factor in poker tournaments?" (definition; required equity = BF / (BF + 1)): https://blog.gtowizard.com/what-is-the-bubble-factor-in-poker-tournaments/

The six-seat opening percentages without antes (17 / 21 / 27 / 44%) are from secondary chart pages that agree with each other (17.6, 22.9, 28.1, 44.2) and not from a solver run by us. The with-ante widening is our extrapolation from sources 1 and 2.

## Appendix E. What could not be verified

- **Case F itself**: a default in the organizers' round form, not an announcement, and the server may apply its own defaults. Payouts are most likely 50/30/20 but unset; iterations per round and the twist are unknown. The team count is 21 on the portal and 20 in the pack.
- **Section 7's effects**: resampling is read from the regional kit, not from Sunday's; its variance figures assume equal stacks at the checkpoint. The luck-correction maths and the culling test are server-side and guessed.
- **How Sunday's bots play at 300bb.** Every "sim" figure comes from regional bots that stack off at depth (first bust at a median hand 39); a field built for case F may bust later, which lengthens tables and takes the money away from a folder. The third-bust hand in practice 1 settles it.
- **Speed.** The laptop was running timed tests (load 14-26); only the CPU-time ratio and the decision counts are quoted. Modal was not run at case-F rules.
- **Solver claims.** No six-handed, 300bb, 0.2bb-ante, ICM solution was consulted or run; the sources are 100-200bb cash or tournament hold'em and were read as summaries. The twist may reorder hand values (it did for pairs in mock variants).
- **Push/fold with antes** was not computed: section 5 only says to key it on the ante and expect a deeper threshold.
- **The dead-money ICM figures** use one simple layout (shover outside the blinds).
- **Side pots for a stack all-in on the ante** were not played through, only seen to be dealt.
- **Whether Sunday's engine matches the regional kit's** on ante events, pot and bet fields and seating; and whether any of section 7's settings will be on.
- **The audit**: 27 of 491 line references were re-checked by hand; the opening sections of `prompts/BUILDER.md`, `prompts/RESEARCH.md` and `START.md` were searched, not read; `prep/` was not audited.
