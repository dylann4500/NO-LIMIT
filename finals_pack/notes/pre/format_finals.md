# Case F is the main case: how to play 6 seats, 6,000 chips and antes (pre-event note, for every role)

Drafted Saturday 14 November and reworked the same evening after Dylan's decision (15:55) to prepare case F as the main case and keep case R as the fallback. Notes only: no bot code and no strategy tables. Plans, formulas, check values and what to compute first; the day's tables come from the real kit.

**Case F**: 6 players, 6,000 chips (300 big blinds), 20 hands per level, a 250-hand cap, levels (small blind / big blind / ante per player) 10/20/4, 20/40/8, 30/60/12, 50/100/20, 80/160/32, 125/250/50, 200/400/80, 300/600/120, 500/1000/200, 800/1600/320, 1200/2400/480, 2000/4000/800, and most likely the platform's 50/30/20, 1 ms and 100 ms bank. It is what the portal's organizer form fills in for a round under the variant id `finals` or `finals_community` (`prep/PORTAL_FINDINGS_14NOV.md`). **Case R** is the regional table: 8 players, 2,000 chips, no ante. Case F is likely but unconfirmed: the Finals competition exists (21 teams, linear weights 1-6 and a 30 s upload cooldown as of 14 November, `prep/PORTAL_SIGNED_IN_14NOV.md`), but no round is queued and its Format page still shows the shared regional template. `platform` confirms it by minute 2; if it is case R, section 10 applies.

**Grades** (as `strategy/EVIDENCE_TABLE.md`): **arith.** exact arithmetic from the schedule (ICM is Malmuth-Harville, 50/30/20 unless said). **sim**: measured on 14 November on the regional kit's engine at case-F rules with our regional bots, 300-400 tables a run (Appendices A and F): good for length, timing and what a ported regional bot does; grade C as a prediction of Sunday's field. **C**: solver-era hold'em knowledge or argument. Nothing here is above C until Sunday's first practice file.

## The plan on one page

**What decides a case-F table**

1. **Half the table is paid and stacks start at 300bb.** A stack lost in the first 100 hands scores zero; nothing in those hands is worth a stack except a near-certain hand. A call for everything needs 58% at hand 1, not 50%.
2. **About 100 hands are played with room after the flop** (average stack 155bb at hand 21, 76 at 61, 43 at 101; sim). At the regional that phase was 40 hands. Post-flop quality, not shove tables, sets who reaches the money with chips.
3. **Antes make every pot worth taking**: 2.7bb before any action. A 2.5bb open needs 48% folds (62.5% at the regional), an 8bb 3-bet 61% (67%). Folding costs 0.45bb a hand.
4. **Ported regional bots are built wrong for this** (sim, our own bots; several finalists will port theirs): they keep their no-ante ranges, call opens three times as often, fold 84-93% to a 3-bet at any depth, bet three-quarters of the pot on every street at any depth and lose 50bb or more in one hand 2.7 times a table. A probe that did nothing but re-raise every open scored 27.9 against them (average 16.7).
5. **The endgame is deeper**: the bubble (four left) is played at an average 55-90bb, three-handed at 30-75bb, heads-up starts at 30-45bb. Shove-or-fold tables decide only the last levels.

**The plan by phase**

| Phase | When (sim) | A strong, simple, robust plan | What ported bots will do wrong |
|---|---|---|---|
| 1. Deep | hands 1 to about 100; 300bb down to 40bb | Open small and wide by seats left to act; 3-bet small where the measured fold rate pays; flat only in position or closing the action, with hands that make very strong hands; bet when checked to; put a stack in only with a near-certain hand (the stack-off rule, section 1); never be the first all-in before the flop above 60bb | No ante or depth awareness; cold-call 38% of opens; fold to 3-bets; barrel three streets with one and two pair; pay off deep with two pair |
| 2. Transition | hands about 100 to 140; average 43bb down to 26bb; usually four, three, then two players | Re-shove 15-30bb stacks over opens; shove-or-fold first in below the depth theory computes with the ante; call by bubble factor, not chip odds; the big stack opens every unopened pot against middle stacks | Shove and call ranges from no-ante tables (too tight); the 12bb switch arrives late; wrong or missing ICM on the bubble |
| 3. Endgame | bubble 26 hands, three-handed 27, heads-up 33 | As a covered middle stack let the shortest stack bust first; after the money play for first (first is worth 20 more than second); heads-up open most buttons and defend by price | Heads-up the button folds 47% of hands; three-handed opens stay at 41-45% |

**Each role's first ten minutes** (detail in section 5)

| Role | First action in case F |
|---|---|
| `platform` | Confirm seats, stack and the ante per level from `state.config` by minute 2; write them to `bot/rules.json`; the bot reads the config at every table and hard-codes nothing |
| `theory` | The format card from formulas by minute 3, then ICM for 6 to 2 players, the ranking against 1 to 5 opponents, the deep card, then push/fold with the ante |
| stylists | Draft in four depth bands with a size ladder that has non-all-in 3-bets and 4-bets, and the stack-off rule |
| `tester` | Six-seat fields with the ante; add a 100-hand capped run for the deep phase and heads-up and three-handed runs started at the depths that occur |
| `analyst`, `scout` | Four numbers from practice 1 choose the style: fold to 3-bet at 60bb+, fold-through to opens with fold to the flop bet, hands losing 50bb+ per table, and the hand of the third bust |

## 1. Phase 1: the first 100 hands (300bb down to 40bb)

**What it is** (sim). 45 hands a table at an average over 150bb and 48 at 60-150bb; six players for 41 hands, then five. Above 150bb two thirds of hands see a flop, a third of those three-way.

**Before the flop**

- **First in: raise to 2.2-2.5bb, no limps**, a fraction of today's ranking by seats left to act. Hold'em solver without antes at 100bb: about 17 / 21 / 27 / 44% with 5 / 4 / 3 / 2 behind; with these antes widen each by a quarter to a third (C; solvers open 4-6 points wider with 0.7bb of antes, case F has 1.2bb [1][2]). A raise with any hand profits when every seat behind folds 86% (5 behind), 69% (2 behind), or the big blind alone folds 43% (arith.): refit from practice 1. Against callers an open is a value raise plus a flop bet, not a steal: our steal probe was never folded through.
- **Against an open: 3-bet or fold, except flats in position and big-blind calls.** 3-bet to about 3.2 times the open in position, 4 times out of position. Value hands always; bluffs as far as the opener's measured fold rate exceeds the break-even of 61% (8bb) to 66% (10bb). Flat in position, or in the big blind at its price of 22%, with hands that make very strong hands, and only when the stack behind is 20-35 times the call (the old 15-25 rule times a bubble factor of 1.4; C [7][8]).
- **Against a 3-bet: fold no more than the 3-bettor's break-even** (about 60-65% of opens). Continue with a 4-bet to 2.2-3 times the 3-bet, never all-in above 60bb, and with calls in position when the stack behind is 20-35 times the call: that holds above about 150bb, not at 100bb.
- **All-in before the flop above 60bb: never first.** A small 3-bet gets nearly the same folds for a tenth of the risk (sim: 83% folds for 8bb against 93% for a shove). Calling one is the stack-off rule below.

**After the flop**

- **Bet when checked to**, a third to half the pot, heads-up; do not bluff into two or more players. Ported bots fold 45% to bets under half the pot, 59% to mid-size and 70% to pot-size bets at every depth (sim), against break-evens of 25-33%, 43% and 50%.
- **The stack-off rule.** Put the last chips in only with equity against the range that does the same of at least BF / (BF + 1 + 1/ratio), where ratio is the stack left over the pot before the last bet and BF the bubble factor (1.39 at hand 1). Check values at BF 1.39: 58% at ratio 44, 56% at 13, 53% at 4, 48% at 2, 41% at 1; on the bubble (BF 1.87) 63%, 60%, 56% and 48% at 13, 4, 2 and 1 (arith.). The range that puts in 13 or 44 pots is close to the best hands possible, so above ratio 6 only a hand near the top of what the board allows qualifies.
- **What each hand strength is worth** (C [4][5]). One pair: two streets of value at up to two thirds of the pot, then check or call one more bet, and fold to a raise or a third large bet. Two pair or a set: three streets; all the chips when the ratio on the flop was 6 or less (3-bet pots up to 150bb, single-raised pots under about 40bb), and a fold to a raise on the turn or river when it was above 13 unless the seat has shown bluffs. Near-certain hands: build the pot by the formula ((1 + 2 × ratio)^(1/3) − 1) / 2 of the pot per street (1.0 at ratio 13, 0.57 at 4.4), and never slow-play against bots that bet when checked to.
- **Pot control.** A called bet multiplies the pot by 1 + 2 × its fraction: three bets of three quarters of the pot turn 6.7bb into 105bb. Decide on the flop how many streets the hand is worth and check the others; out of position check more [5].
- **Raises and large late bets are strong**: a post-flop raise held two pair or better half the time and at least a pair every time; a river bet of 60% of the pot or more held two pair or better 74% of the time (sim, at 150bb+; C for Sunday). Fold one pair to them unless that seat has shown bluffs.

**Against a seat that shoves 100bb or more.** Call only by the stack-off rule against that seat's measured range: about the best quarter of hands against a seat that shoves every hand (the hands with 58% against a random one; hold'em, C), the best few per cent against a first, unexplained shove. Our shove-every-hand probe was called by each regional bot 8-14% of the time and lost 71% of those calls; it was out by hand 7. Do not re-shove lighter to isolate, and do not bluff-shove: a bystander gains 1.2 points when two others collide.

**Mistakes to expect from AI-built bots here** (section 4): no ante adjustment; limits written as a share of the stack, which triple at 300bb (our bots flat-call up to 12% of the stack: 36bb); one post-flop policy for every stack-to-pot ratio; no cap on what one pair may cost; no bet above the pot, so strong hands are under-bet and draws are cheap.

## 2. Phase 2: the transition (about hands 100 to 140)

**What it is** (sim). Average stack 43bb at hand 101, 32 at 121, 26 at 141; the third bust at a median hand 96 and the fourth at 124, so this is usually the bubble and three-handed play. A stack that only folded holds 10bb at hand 101 and is gone at 121.

- **15-30bb: open small or re-shove.** Re-raise shoves from 25-60bb stacks were folded to 92% of the time and gained 0.55 points each; first-in shoves under 25bb gained 0.18 each against −0.14 at the regional, because of the antes (sim).
- **Shove-or-fold first in starts deeper than the regional's 12bb.** Each success wins 2.7bb, not 1.5: theory solves it with the ante as an input; an upper bound from equal pot-to-stack ratio is about 21bb, not a value.
- **Call by bubble factor.** With four left and stacks of 2.5, 1.5, 1.5 and 0.5 starting stacks: a 1.5 calling the 2.5 needs 72.7%, the 0.5 calling the 2.5 needs 59.6%, the 2.5 calling the 0.5 needs 52.3% (arith.). So the leader opens every unopened pot against the middle stacks; a middle stack does not call off against the leader while a shorter stack is alive; the shortest stack shoves wide, because folding costs it 0.58bb a hand four-handed.
- **Antes lower call thresholds** by 1.5-2 points at 10-15bb (arith.).

**Mistakes to expect**: shove and call ranges from no-ante, eight-seat tables; the fixed 12bb switch; no ICM on the bubble (two of our four regional bots), or an ICM function that scores a busted seat zero.

## 3. Phase 3: the endgame with three paid of six

**What is at stake** (arith.): fourth to third is 20 points, third to second 10, second to first 20. The call threshold at equal stacks is 65.2% with four left, 57.1% with three, 50% heads-up.

- **Bubble, four left** (26 hands a table at an average 55-90bb; sim): pressure applies to raises and bets, not only to shoves. Covered stacks play small pots; the covering stack raises often and bets small.
- **Three left** (27 hands; 75bb at level 5, 48 at 6, 30 at 7): everyone is paid, and first is worth twice what second adds. Open most buttons; 3-bet or re-shove over opens; a middle stack still needs 61.8% to call the leader's shove.
- **Heads-up** (33 hands from a median hand 124; 45bb at level 7, 30 at 8, 18 at 9): chip odds decide everything. Open most buttons to 2bb (any hand profits if the big blind folds 44%); defend the big blind at its price (23-28%); re-shove over opens from 25bb down; shove-or-fold only in the last levels, from tables solved with the 1.9bb pot. Half the tables are over by hand 160, before heads-up stacks average under 30bb.
- **A bot with no endgame still cashes**: the 3-bet probe never opened and never bet after the flop, came second in 83% of tables and never won one.

**Mistakes to expect**: no separate heads-up ranges (our regional bots' button raised 53% and folded 47% heads-up); three-handed opens of 41-45%; published no-ante shove charts.

## 4. What ported regional bots do wrong at these rules (measured)

Six of our regional bots (v10, v9s, v6, v3b, v8, v7) at case F against eight at case R, 400 tables each, and three throwaway probes at case F, 300 tables each. A read of their source agrees: none reads the ante, the table size or the starting stack. All grade sim.

| What they do | At case F | At case R | How to use it |
|---|---|---|---|
| First-in raise by seats behind (5 / 4 / 3 / 2 / 1) | 21 / 23 / 27 / 41 / 49% | 22 / 24 / 28 / 44 / 59% | Unchanged although the break-even fell 14 points: they give up their blinds and antes |
| Facing an open, not in the big blind: fold / call / 3-bet | 57 / 38 / 5% at 150bb+; 62 / 33 / 5% at 60-150bb | 83 / 13 / 4% | Opens get called: raise for value, bet the flop, squeeze the callers |
| Big blind facing an open: fold | 12-14% (four bots), 50% (two) | 17-20%, 66-69% | The two that fold more were the two that won most chips deep |
| Opener facing a 3-bet that is not all-in: fold | 84-93% at every depth | 86-96% | The largest single edge found: see the probe |
| Hands seeing a flop | 67% at 150bb+, a third of them three-way | 60% at 60-150bb, a sixth | More multiway pots than any regional table |
| Preflop raiser bets the flop / turn / river | 80-89% / 79-85% / 74-86%, mostly three quarters of the pot each time | the same on the flop, mostly a third of the pot later | Call with strong hands and let them bet; do not slow-play first |
| Facing a bet: fold on flop / turn / river | 59 / 57 / 65% at any depth (v3b 31 / 45 / 67%) | 62 / 48 / 66% | Bet when checked to |
| Hands in which a seat loses 50bb or more | 2.7 a table; 70% of the losers held one or two pair; last chips in on the turn or river 70-74% | 0.6 a table | The stack-off rule is where points are kept |
| Preflop all-in raises from stacks over 60bb | 2.3 a table, 1.8 of them re-raises; folded to 93-96%; the shover won 30% when called | 1.4 a table | Do not call these light: they are strong |
| Busts | 37% after the flop; 17% from stacks over 60bb | 18%; 3% | Half a bust a table is a 100bb+ stack lost in one hand |
| The bot with the call-down leak (v3b) | 8.9 of 16.7, losing 79bb per 100 hands above 60bb | 10.1 of 12.5 | Depth more than doubles the cost of a post-flop leak |

| Probe (with five regional bots) | Result at case F |
|---|---|
| Re-raises every lone open to 3.2 times it, never continues, never opens | Folded to 83% of the time at 60bb+ and 91% at 25-60bb; 4-bet 5-8%; +46 to +51bb per 100 hands; second in 83% of tables: **27.9 ± 0.6 points** |
| Raises to 2.2bb first in with every hand, never continues | Folded through under 1% of the time; called 65-83%, re-raised 17-35%; 0.8 points |
| Shoves every hand | Called 24% of the time at 150bb+ (each seat 8-14%) and won 29% of those; −1.6 points a shove; out at a median hand 7; 2.6 points (0.4 at case R) |

**Read this with care.** These are our bots, and the fold-to-3-bet figure is our known regional leak (we folded 82-89%; the field 67%, Boston's top teams 58% by round 5). What transfers is the mechanism: a bot ported without ante and depth rules keeps its regional rates while the prices move. With antes a 3-bet to 8bb is profitable with any hand against the regional field's own 67%, and unprofitable against Boston's 58%. Practice 1 says which field we face.

## 5. Role by role

**`platform`.** By minute 2 if the kit allows, and again for every round because rules are per round: `state.config.players`, `starting_stack`, `blinds` (each level `small_blind`, `big_blind`, `ante`), `hands_per_level`, `hand_cap`, `payouts` (this table's own draw), `decision_ms`, `time_bank_ms`, `memory_bytes`. The bot derives depth, pot, seats and payouts from the state at every table and hard-codes none. Engine facts to re-check on Sunday's kit (Appendix A): antes are their own events before the blinds; the pot includes them and a seat's bet does not; the largest raise at hand 1 is to 5,996; a stack no bigger than the ante is all-in on the ante. Offer the styles: effective stack in big blinds, the ratio of stack to pot, seats left to act, the bubble factor against each seat, and a non-all-in size for every raise level.

**`theory`: tables in this order** (times from the speeds measured on 14 November in `agents/theory.md`; the three parallel theory runs keep their split, and this is the priority across them):

| # | Table | Due | Compute | Notes |
|---|---|---|---|---|
| 1 | Format card: depth by level and players, pot by players, break-evens for our sizes, ratios after each raise level, stack-to-call multiples | minute 3 | seconds (formulas) | Sent to every stylist at once; section 6 has the check values |
| 2 | ICM: break-even calls and bubble factors for 6 to 2 players, equal stacks and a grid of stack shares, with the antes as dead money | minute 8 | under a minute (120 orderings a table at six seats, 336 at eight) | Checks: 58.1 / 60.6 / 65.2 / 57.1 / 50%; the busted-seat test |
| 3 | Ranking under the twist against 1 to 5 opponents and a top-30% range | minute 10 | about 40 s on 2 workers per opponent count (heads-up; more players cost more) | As planned, five opponent counts instead of seven |
| 4 | Deep card: the stack-off threshold BF / (BF + 1 + 1/ratio) on a grid, and the equity of each made-hand class against the best 2, 5, 10 and 20% of holdings by board type | minute 13 | grid instant; equities about 2 minutes on Modal | New for case F; the stylists' stack-off rule reads it |
| 5 | The twist's option values and rule | minute 15 | as planned | Unchanged |
| 6 | Push/fold with the ante: heads-up, three-handed, and first-in ranges for 4 to 6 players by seats behind; call tables keyed by shove width, with the bubble factor | minute 18 | heads-up seconds; three-handed about 2 minutes on Modal; the rest 1-2 minutes | A table needs them from about hand 100, but practice 1 plays whole tables |
| 7 | Break-even grids for bets, 3-bets and 4-bets with the ante; the fold cap | minute 20 | seconds | The cap is about 59-68%, not 65-75% |
| 8 | Second wave: heads-up and three-handed opening and defence at 20-75bb; multiway all-ins | after 20 | minutes | Refit from practice 1 |

**Stylists.** Depth bands: over 150, 60-150, 25-60, under 25bb. Six positions by seats left to act. A (pressure): the 3-bet is the weapon if the field folds; otherwise value 3-bets and flop bets in position. B (shove-heavy) has no play above about 25bb: make it the position style for the first 100 hands (opens, flats in position, small bets) and shove-heavy after. C (tight): it reaches 25bb at hand 81 and 10bb at hand 101 if it only folds, so it must open in late position and re-shove from hand 80. Every style carries the stack-off rule, non-all-in 3-bet and 4-bet sizes, a fold-to-3-bet no higher than the break-even, and its own heads-up and three-handed rows at 20-75bb.

**`tester`: counts and speeds** (measured 14 November on this laptop, regional bots as subprocesses, one table in flight per process; spreads for an average bot at 50/30/20):

| Run | Rules | Tables a second per process | Spread per seat | Tables for a 1-point paired difference at 2 SE |
|---|---|---|---|---|
| Full table | 6 seats, case F | 2.6 (case R: 2.9) | 18.9 | about 2,000 (500 for 2 points, 7,900 for 0.5) |
| Deep phase | the same, hand cap 100 | 3.7 | 15.4 | about 1,300 |
| Early phase | the same, hand cap 60 | 5.1 | 10.9 | about 670 |
| Three-handed | 3 seats, 12,000 chips, blinds from level 5 | 10.8 | 12.5 | about 900 |
| Heads-up | 2 seats, 18,000 chips, blinds from level 7 | 33 | 10.0 | about 400 |

A capped table is scored by ICM on the stacks at the cap. The 100-hand cap kept the whole gap between our leaking bot and the others (9 points in both) at 1.4 times the speed and less noise, so it is the cheapest test of deep play. A one-change variant needs about a quarter of these counts. On Modal expect about 0.9 of the regional rate: roughly 125 tables a second at 80 containers and 13,500-18,000 full tables in a five-minute window on 40 (C: time the first job). Every verdict keeps the heads-up run and the `check_or_fold` floor (sim: 11 of 16.7), and adds a run that reaches every blind level and an all-in for less than the ante: the 20-hand upload test sees only level 1. With 169 decisions a seat a table instead of 114, re-check the time bank.

**`analyst` and `scout`.** Skip ante events; identify blinds by amount (heads-up the big blind is posted first); add depth bands above 40bb; re-base the hand-40 markers. From practice 1, report first, by depth band: (1) fold to a 3-bet at 60bb+ (above 66%: 3-bet wide; under 58%: value only); (2) fold-through to opens by seats behind, with fold to a flop bet; (3) hands losing 50bb+ per table and what the losers held; (4) the hand of the third bust against hand 121, when a folder dies; (5) each seat's shoves above 60bb.

**Stays exactly as planned**: the roles, the clock, the decision rules in z units, release and upload discipline, the twist work, the ICM method and its library-trap test, practice rounds as the judge.

## 6. Reference: the shape of a case-F table

- **Depth** (arith.). Average stack in big blinds = 36,000 / (players left × big blind): 300, 150, 100, 60, 37, 24, 15, 10, 6 for the levels up to hand 180 with six alive (Appendix B). With everyone alive, case F is as deep as case R was two levels earlier.
- **Antes** (arith.). Pot before action = 1.5 + 0.2 × players, in big blinds: 2.7 six-handed, 2.3 four-handed, 2.1 three-handed, 1.9 heads-up.
- **Break-evens** (arith.): a bluff needs folds of risk / (risk + pot before it); a call needs call / (pot after the call).

| Play | Case R | F, six-handed | F, three-handed |
|---|---|---|---|
| Open to 2.0bb / 2.5bb from a seat with no blind | 57.1% / 62.5% | 42.6% / 48.1% | 48.8% / 54.3% |
| 3-bet to 8bb / 10bb over a 2.5bb open | 66.7% / 71.4% | 60.6% / 65.8% | 63.5% / 68.5% |
| Re-shove 20bb over a 2.5bb open | 83.3% | 79.4% | 81.3% |
| Open-shove 10bb | 87.0% | 78.7% | 82.6% |
| Big blind's price against 2.0bb / 2.5bb | 22.2% / 27.3% | 17.5% / 22.4% | 19.6% / 24.6% |

- **Ratios of stack to pot** (arith.): after an open and a big-blind call / a 3-bet called / a 4-bet called: 44 / 13 / 5 at 300bb, 22 / 6.5 / 2.4 at 150bb, 14.5 / 4.1 / 1.7 at 100bb; the regional table started at 18 / 4.4 / 1.7.
- **Length, cap, cost** (sim). 155 hands a table (sd 24) against 131; busts at median hands 39, 68, 96, 124, 158. The same bots at case R busted at 29, 47, 62, 73, 87, 105, 130, matching the real regional (`placings.md`: our 6th, 5th, 4th at hands 60, 70, 86). None of 6,000 full tables reached hand 250 (longest 221): by hand 221 the whole table holds 9bb. If the cap is reached, survivors split the unpaid places by ICM on chips. A pure folder is out at hand 121 and cashed 53% of the time (11.1 of 16.7); at case R hand 102, 36% (7.3 of 12.5).

## 7. Reference: tournament equity with six players

- **Method.** E = ICM value of a stack set (a busted seat keeps its place's points). Bubble factor BF = (E_fold − E_lose) / (E_win − E_fold). Break-even equity for an even-money all-in = BF / (1 + BF); with pot odds, risk × BF / (risk × BF + reward).
- **Equal stacks, 50/30/20** (the main case; rows 6 to 2 of `whatwins.md` §4): 58.1% (BF 1.39), 60.6% (1.54), 65.2% (1.87), 57.1% (1.33), 50%. Secondary shapes at 6 / 5 / 4 / 3 left: 65/35 gives 53.8 / 54.8 / 56.6 / 60.6; 60/25/15 gives 56.2 / 58.0 / 61.2 / 55.0; 40/30/20/10 gives 62.5 / 66.7 / 64.3 / 60.0; winner-take-all 50 throughout.
- **Unequal stacks** move it more than seats do; check values in Appendix B.
- **Chips at hand 1**: busting a player takes us from 16.7 to 28.7 points; busting costs 16.7. A bystander gains 1.2 points when two equal stacks collide with six left, 2.3 with five, 5.8 with four.

## 8. Round settings the organizers can change

From `prep/PORTAL_FINDINGS_14NOV.md` and `prep/PORTAL_SIGNED_IN_14NOV.md` (what the portal can do) and the regional kit's engine and hand-history README (what a setting does). None was on at the regional.

- **Rules are per round**: players, stack, blinds, payouts, time limits, luck correction and resampling can all differ between a practice and a scored round. Tables are keyed on players left, ante and payouts and fail loudly outside their grid. The last round's results and our bot's health for it can be held back, so that bot must already be correct at both formats.
- **Payouts**: most likely 50/30/20. Up to five places can be paid, each as a low-high range from which every table draws its own points (with `payout_total`, the places sum to it, each strictly above the next). Read `state.config.payouts` at every table.
- **Seating**: 21 teams seat 24 an iteration, at six seats three full tables and one with 3 scoring seats and 3 fillers. A given opponent is at 25% of our scored tables (35% at eight seats); 14% of our scored tables hold fillers; we sit as a non-scoring filler in 14% of iterations. A 1,000-table practice holds about 250 tables with any one opponent.
- **Culling** (within a round, a team confidently outside its top K stops getting tables): a culled file ends early, so read the table count before any rate; the score has a larger error and leans low. Use each result's own `margin_of_error`.
- **ICM luck correction** (server-side maths, so a guess: all-in outcomes replaced by their expectation in points): same tables seen, lower variance, least in the deep phase; a score recomputed from places will not match the portal's.
- **Resampling**: a table is played until `resampling_threshold` players remain (default 4), then the rest is played 1-8 times with fresh cards; official points average them and the hand file shows only the first. Spread per table at six seats, threshold 4: 18.9 falls to 15.7 / 13.9 / 12.9 at 2 / 4 / 8 continuations (equal stacks at the checkpoint, a best case).
- **Held results and multipliers**: the final round's results and the leaderboard can be hidden, so choose the last bot on earlier rounds. Multipliers are linear 1-6 (the key's setting on 14 November), Fibonacci or powers of two: the last round is 29%, 41% or 51% of the total.

## 9. What in the bundle assumes case R

An audit found 491 lines; Appendix C lists every one by file and line under twelve conversion rules and quotes the 30 that carry the most. With case F the main case, change these first: the rules-card lists, none of which names an ante (9 lines, first `platform.md:27`); the points scale (111 lines: `PLAN.md:39-40` "averages 12.5 ... don't panic at a 15" becomes 16.7, and a 15 is below average; `DECISION_RULES.md:63,240`); co-seating (`DECISION_RULES.md:229` "7 of our 19" becomes 5 of 20, and 370 of 1,000 tables becomes about 250); the ICM unit tests (`platform.md:95-96` "8 equal ≈ 56%" needs six equal 58.1% and five 60.6%); the shared defaults "shove-or-fold at about 12bb" and "no flat call of an open at 10bb+" (`stylist.md:51-52`), which the defaults check would enforce against correct deep play; the "65-75%" fold cap (about 59-68%); and the tester's throughput (`tester.md:42-45`, section 5's table). Regional rates (98 lines) are priors for the first practice only.

## 10. If it is case R after all

Then the pack stands as written and sections 1-6 do not apply; sections 7 (its 8-seat rows are in `whatwins.md`) and 8 hold in either case, and a later round can still switch. Keep the minute-2 check of seats, stack and `ante` (it also catches a mixed format: antes at eight seats make the pot 3.1bb; six seats without antes are measured in Appendix A), and Appendix C as the map of where the format is written into the pack. The ten differences, for whoever needs the comparison:

| # | What | Case R | Case F | Grade |
|---|---|---|---|---|
| 1 | Seats and the average score | 8 seats; average 12.5; 3 of 8 paid | 6 seats; 16.7 with 50/30/20; half the table paid | arith. |
| 2 | Depth | 100bb at hand 1 | 300bb at hand 1; 100bb at hands 41-60, 37bb at 81-100, 15bb at 121-140 with six alive | arith. |
| 3 | Dead money | pot 1.5bb before action | 2.7bb six-handed, 1.9 heads-up; folding costs 0.45bb a hand, 2.4 times as much | arith. |
| 4 | Prices before the flop | 2.5bb open needs 62.5% folds; 8bb 3-bet 66.7%; big blind needs 27.3% | 48.1%; 60.6%; 22.4% | arith. |
| 5 | Stack-to-pot ratio | 18 single-raised, 4.4 in a 3-bet pot | 44 and 13 at 300bb, 22 and 6.5 at 150bb | arith. |
| 6 | Shove-or-fold starts | average stack 24bb by hand 81 | 55bb at hand 81, 32 at 121, 26 at 141 | sim |
| 7 | Table length | 131 hands; 915 decisions a table, 114 a seat | 155 hands; 1,016 a table, 169 a seat; no table reached the cap | sim |
| 8 | Tournament pressure | hand 1 needs 55.6%; five busts to the money; 21% of hands with 5 or 4 left, at 25-40bb | 58.1%; three busts; 35% of hands with 5 or 4 left, at 55-180bb | arith.; sim |
| 9 | What doing nothing scores | folder out at hand 102, cashes 36%: 7.3 of 12.5 | out at hand 121, cashes 53%: 11.1 of 16.7 | sim |
| 10 | Samples and noise | each opponent at 35-37% of our tables; 90 hands dealt per seat per table; spread 17.9; seven sparring copies | 25-26%; about 105-115 hands; 18.9; five copies; about 10% fewer tables per core-second | arith.; sim |

---

## Appendix A. Table shape: measurements (14 November, regional kit engine, variant `flop_discard_reveal`, 400 tables a run)

First set, run on this laptop under load 14-26 with one table in flight per run, decision limit 1 ms, time bank 100 ms, payouts 50/30/20. Throwaway runner outside the repo, deleted. "Regional bots" are v10, v9s, v6, v3b, v8, v7, v9; the kit's examples are `check_or_fold` and `min_raiser`. Intervals are 95%.

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
- **Cost.** Under load, CPU per table (engine plus bot processes) was 0.35-0.37 core-seconds (F-C, F-D) against 0.34 (R-D). Re-timed in the evening at load 4-6 (Appendix F's runs): case F 0.38 s a table for one process (2.6 tables a second; 0.34 core-seconds), case R 0.35 s (2.9; 0.31).
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
| `agents/stylist.md:45` | "B, shove-heavy: few small preflop raises; mostly shove or" | No such play above about 25bb: section 5 makes it the position style for the first 100 hands |
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

**H. Break-evens without dead antes** (16 lines). Becomes: add 0.2bb per live seat to the pot: section 6's table. `DECISION_RULES.md` 221; `EVIDENCE_TABLE.md` 99; `FIRST_PROMPT.md` 300; `PLAN.md` 85, 146; `agents/stylist.md` 54; `agents/theory.md` 49; `pre/contrarian.md` 11; `pre/field.md` 61, 64, 70; `pre/finalists.md` 794; `pre/placings.md` 43; `pre/whatwins.md` 13, 25, 83

**I. Field rates measured eight-handed at 100bb with no ante, used as priors or thresholds** (98 lines). Becomes: a prior for the first practice only, matched by seats left to act and depth band; expect opens up, big-blind folds down, short-stack shoves up, fold-to-3-bet unknown above 100bb; team cards in `finalists.md` describe habits (sizes, adaptation rules) that may carry over, not rates. `DECISION_RULES.md` 211, 212, 217, 222, 223, 234, 235; `EVIDENCE_TABLE.md` 31, 33, 37, 52, 96, 126, 127; `FINGERPRINTING.md` 49, 50, 52; `FIRST_PROMPT.md` 156, 159, 163, 168, 180, 181, 301, 348, 624; `LESSONS.md` 187; `PLAN.md` 21, 22, 28, 34, 185; `TWIST_NOTES.md` 163; `agents/scout.md` 27, 55, 56, 95; `agents/stylist.md` 77; `agents/theory.md` 31; `pre/buildplan.md` 65, 73; `pre/challenger_bar.md` 80, 87, 265; `pre/contrarian.md` 9, 20, 36, 37, 38; `pre/field.md` 4, 5, 12, 13, 18, 28, 29, 34, 44, 58, 59, 61, 62, 63, 65, 66, 67, 69, 76, 136, 137; `pre/finalists.md` 46, 63-67, 84, 86, 89, 102-110, 132, 137, 169, 318-338, 342-564, 852; `pre/stat_definitions.md` 24-40; `pre/variants.md` 64; `pre/whatwins.md` 22, 23, 24, 36, 37, 39, 47, 49, 82

**J. Test counts and throughput** (16 lines). Becomes: five sparring copies; about 0.9 times the tables per second; table counts for a given SE about 1.12 times if the bar stays in points, unchanged if it is rescaled. `FIRST_PROMPT.md` 453, 473, 487, 501, 634; `agents/platform.md` 93; `agents/tester.md` 38, 45, 81, 98; `pre/testplan.md` 38-41, 43, 44, 46, 52; `prompts/RESEARCH.md` 88

**K. Simulated style results at the regional format** (7 lines). Becomes: unknown; the shove corner of the cycle has no early game. `DECISION_RULES.md` 226; `EVIDENCE_TABLE.md` 90, 92, 94; `FIRST_PROMPT.md` 277; `pre/contrarian.md` 21

**L. Other: size bins, recognition accuracy, style premises** (36 lines). Becomes: open sizes in big blinds may shift with antes (solvers open larger), so last round's size fingerprints are weaker; recognition by hand 20 has more events per seat at six seats; depth-restricted statistics ("25bb or more") cover far more hands. `EVIDENCE_TABLE.md` 56, 57; `FINGERPRINTING.md` 19, 21, 29, 72; `FIRST_PROMPT.md` 385, 386, 398, 521, 636, 637; `PLAN.md` 32; `agents/analyst.md` 94; `agents/scout.md` 36, 65, 92; `agents/stylist.md` 45; `pre/buildplan.md` 82; `pre/contrarian.md` 19; `pre/finalists.md` 54, 298, 570, 914; `pre/first1000.md` 76; `pre/placings.md` 63; `pre/stat_definitions.md` 31, 43, 47, 49; `pre/variants.md` 47, 396; `prompts/BUILDER.md` 61

## Appendix D. Sources

Team files: the regional bots' source (`bots/v10`, `v9s`, `v6`, `v3b` in the team's archive; read, never copied), `prep/PORTAL_FINDINGS_14NOV.md` and `prep/PORTAL_SIGNED_IN_14NOV.md` on `emu/rehearsal` (the Finals defaults, per-round rules, culling, luck correction, resampling fields, held results, multipliers, the 21 teams, the Finals Format page), the regional kit's `hand-history/README.md` (resampling: official points average all continuations, the file shows the first), `strategy/EVIDENCE_TABLE.md` (grades; regional rates), `notes/pre/whatwins.md` §4 (equal-stack thresholds, reproduced here to 0.1 point by an independent calculation), `notes/pre/placings.md` and `first1000.md` (real regional bust hands and table length), the regional kit's engine (`sdk/engine/src/poker_engine/table.py`, `seating.py`, `scoring.py`, `holdem.py`).

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
- **Section 8's effects**: resampling is read from the regional kit, not from Sunday's; its variance figures assume equal stacks at the checkpoint. The luck-correction maths and the culling test are server-side and guessed.
- **How Sunday's bots play at 300bb.** Every "sim" figure comes from our own regional bots, which stack off at depth (first bust at a median hand 39) and fold 84-93% to 3-bets, our known regional leak. A field built for case F, or ported from a bot without that leak, will bust later and fold less: the 27.9 points of the 3-bet probe is an upper bound, not a forecast. Section 5's five numbers from practice 1 settle it.
- **The plan in sections 1-3** is argument plus solver-era hold'em knowledge (C). No candidate bot was built or tested at case F; only the three probes were run. The hand-strength rules assume hold'em-like hand values, which the twist may change.
- **The tester's speeds** are for regional bots run as subprocesses on this laptop; in-process bots and Modal were not timed at case F. The table counts scale the pack's measured paired spread (21) by 1.06 and by each run's spread per seat.
- **Speed.** The laptop was running timed tests (load 14-26); only the CPU-time ratio and the decision counts are quoted. Modal was not run at case-F rules.
- **Solver claims.** No six-handed, 300bb, 0.2bb-ante, ICM solution was consulted or run; the sources are 100-200bb cash or tournament hold'em and were read as summaries. The twist may reorder hand values (it did for pairs in mock variants).
- **Push/fold with antes** was not computed: section 5 only says to key it on the ante and expect a deeper threshold.
- **The dead-money ICM figures** use one simple layout (shover outside the blinds).
- **Side pots for a stack all-in on the ante** were not played through, only seen to be dealt.
- **Whether Sunday's engine matches the regional kit's** on ante events, pot and bet fields and seating; and whether any of section 8's settings will be on.
- **The audit**: 27 of 491 line references were re-checked by hand; the opening sections of `prompts/BUILDER.md`, `prompts/RESEARCH.md` and `START.md` were searched, not read; `prep/` was not audited.

## Appendix F. What our regional bots did at case-F rules (14 November, evening)

Second set of runs, load 4-6, same engine and variant, hand logs kept and parsed by a throwaway script (deleted). Depth bands are a seat's effective stack at the start of the hand. Hand classes use the two kept cards and the final board. The probes were three throwaway bots of a few lines each (deleted): they are measuring instruments, not candidates.

| Run | Rules | Seats | Tables | Result |
|---|---|---|---|---|
| F-A2 | case F | v10, v9s, v6, v3b, v8, v7 | 400 | points: v7 19.2, v6 18.8, v8 17.9, v9s 17.8, v10 17.4, v3b 8.9 (each ± 1.9); 158 hands; 4 failed decisions of 410,546 |
| R-A2 | case R | the same six, v9, v5 | 400 | v7 14.8, v10 13.8, v6 13.7, v9s 13.7, v9 12.6, v8 11.6, v3b 10.1, v5 9.8 (± 1.7) |
| F-3bet | case F | v10, v9s, v6, v8, v7 + the 3-bet probe | 300 | probe 27.9 ± 0.6; the others 13.7-14.8 |
| F-steal | case F | the same five + the steal probe | 300 | probe 0.8 ± 0.4; places 4th 26%, 5th 44%, 6th 26% |
| F-shove | case F | the same five + the shove probe | 300 | probe 2.6 ± 1.1; out by hand 5 in 38% of tables, by hand 20 in 87% |
| R-shove | case R | seven regional bots + the shove probe | 300 | probe 0.4 ± 0.4; out by hand 5 in 55% |
| Cap 60, cap 100 | case F, hand cap 60 or 100 | as F-A2 | 400 each | spread per seat 10.9 and 15.4; v3b 12.9 and 9.2 against 16.7-19.5 for the others |
| Three-handed | 3 seats, 12,000 chips, blinds from level 5 | v10, v8, v6 | 400 | 80 hands a table; spread 12.5 |
| Heads-up | 2 seats, 18,000 chips, blinds from level 7 | v10, v8 | 400 | 41 hands a table (10%-90%: 17-63); spread 10.0 |

- **Hands by table-average depth** (F-A2, per table): 45 at 150bb+, 48 at 60-150bb, 54 at 25-60bb, 11 under 25bb. At case R: 0, 24, 81, 27.
- **Points by depth** (ICM points won per 100 hands, by own effective depth 150bb+ / 60-150 / 25-60 / under 25): v8 +2.2 / +1.2 / −2.3 / +4.6; v7 +1.8 / +4.7 / −0.1 / +1.4; v10 +0.5 / +0.2 / +0.5 / +2.3; v6 +0.3 / +2.8 / +1.3 / +3.7; v9s −0.4 / +0.3 / +0.1 / +7.3; v3b −6.2 / −12.7 / −18.2 / +4.6.
- **Open size**: 2.2bb at 150bb+, 2.5bb at 25-150bb, 2.1bb under 25bb (median); no limps. 3-bets were 3.5 times the open, 4-5% of chances.
- **Preflop all-in raises per table at case F** by the raiser's stack: 0.15 at 150bb+, 2.2 at 60-150bb, 5.3 at 25-60bb, 21 under 25bb. First-in shoves under 25bb were folded to 66% of the time and won 43% when called; re-raise shoves under 25bb were folded to 85% and gained 0.53 points each.
- **What a bet held at 150bb+**: a first bet on the flop of 60% of the pot or more was two pair or better 37%, one pair 41%, nothing 21%; on the turn 60 / 32 / 9; on the river 74 / 19 / 7. A raise after the flop: 50 / 50 / 0.
- **The 3-bet probe by opener**: v10, v7, v8, v9s and v6 each folded 86-87% (n 2,400-2,800 each); it was called 9-11% at 60bb+ and 4-bet 7-8%.
- **The shove probe**: per-seat call rates at 150bb+ were v8 8.2%, v7 8.6%, v10 10.1%, v9s 12.3%, v6 13.6%.
- **Short-handed first-in raises at case F**: heads-up button 53%; three-handed button 41%, small blind 45%; no limps.
- **From the source** (a read of v10 and v3b in full, v9s and v6 for differences; line numbers are v10's): nothing reads `blinds.ante`, `config.players` or `config.starting_stack`; push/fold switches at a fixed 12bb (32, 637); the flat-call limit is a share of the stack, `to_call <= 0.12 * my_stack` (721), which is 12bb at the regional and 36bb here; the bot counts its own open as an extra player when it faces a 3-bet (693-695), which is why it folds; any all-in over 20bb is read as the best 20% of hands (682-684); a bet of 48 pots narrows the assumed range exactly as one of 1.5 pots does (801); the largest bet is the pot (881-882). The ante event, six-seat position, other payouts and memory are handled correctly.
