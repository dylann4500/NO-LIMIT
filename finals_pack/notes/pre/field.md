# What the Finals field will do (drafted Saturday 14 November; check and extend on the day)

Grades as in `strategy/EVIDENCE_TABLE.md`: **A** measured on regional data, **C** judgment or simulation;
everything about Sunday's field is C until practice 1 lands. Rates are Bay Area's (8 seats, about 133 hands
per table, three hole cards): preflop and stack-depth rates need only standard hold'em structure; postflop
rates may not survive the twist. Reference values: Appendix A.

## 1. One page: the crowded styles

| Style on Sunday | Share of the 19 (confidence) | Evidence | What punishes it |
|---|---|---|---|
| **Wide pressure with seat learning**: opens 40%, 3-bets 25-40%, re-raises a seat again once it folds, c-bets 80-90% | 40-50% as a first scored bot (medium) | Regional top 20: 5% of teams in round 1, 37% in round 6 (top 5: 20% to 60%); ten of 19 had a per-seat response (A). The public winning story | 4-bets: these bots folded 66-86% to them and the field 4-bet only 7-8% (A). Not folding the first 3-bet at a table: 2 Curry then re-raised 7%, against 43% after a fold (A) |
| **Counter-wave defenders**: fold to 3-bets under 58%, 4-bet 15%+, big blind folds under 45% | 25-35% (low-medium) | Boston's top 20 by round 5 (A, estimated list). Three of Bay Area's top six folded 38-57% and called 31-48% (A) | 3-bets for value only, tighter opens, thinner value bets |
| **Shove-heavy, limp-or-shove** | 15-20% (medium) | Second at Bay Area; Sequoia's recap ("all-in bots" stopped winning) may thin it | Calls at the ICM threshold for the measured range; tight play once it is half the field (C) |
| **Hyper-aggressive rewrites**: 3-bet 40-60%, big blind never folds | 5-10% in round 1, 15-25% by round 4 (low) | The regional's biggest late jumps: Team 123 9.4 to 18.9, thepastaway 13.4 to 20.3 (A) | Wider 4-bets and call-offs (both folded 80%+ to 4-bets); traps |

Tight survivors should be rare (5-10%): the class left the regional top 20 after round 1 and scored 10-11
(A). Common to nearly every style (A): c-bet 74-78%, the bettor folds to a flop raise 49-63%, only 10% of
flop bets are raised, river bluffs are rare.

**Count teams per class; don't average.** The regional top 20's fold to 3-bets in round 6 had quartiles
54 / 72 / 79 and a range of 30-93.

## 2. From practice 1 to rounds 3 and 6

**Practice 1 is a different game (A at the regional, C for Sunday).** 92 of 148 entries were seated, 14% of
them folded everything or never raised, and 5 of the eventual top 20 were absent. Draft bots don't fold: the
field folded 50% to 3-bets (68% by round 3), 4-bet 23% (7%), folded to a flop raise 27% (42%) and open-limped
9% (4%). Tables busted faster: 1.8 all-in collisions before hand 40 (scored rounds 1.0-1.3) and 5.2 players
left at hand 40 (6.1-6.5). Tight play scored 14.8 and a fold-everything bot 10; score correlated with 3-bet
rate at -0.59 (+0.44 by round 5).

So practice 1 overstates tight, value-heavy play and understates pressure, and **a low fold to 3-bets there
is not the counter-wave** unless the teams showing it also open 37%+ and 3-bet 20%+. Finalists build faster:
expect fewer absentees, the same sticky drafts. 44-64% of the eventual top 20 changed bot between consecutive
build practices (A).

**Rounds 1-3.** Regional (A): limping went, fold to 3-bets rose 59% to 68%, 4-bets fell, c-bets and folds to
raises rose. Bay Area's defence lagged four rounds; Boston's arrived by rounds 2-3. Sunday (C): round 1 starts
near the regional's round 5-6, and by round 3 the answer to pressure (4-bets, calls, big blind folding under
45%) is common.

**Rounds 4-6.** Regional top 20 (A): 3-bets 13% to 24%, big blind folds 58% to 43%, fold to 4-bets 26% to 50%;
30% changed bot into the last round, some unseen in practice (one gained 7 points, one lost 3). Rounds 4-6
carry 71% of the weight (official rules): expect rewrites from 4th-10th.

## 3. What to measure in practices 1 and 2

Noise is one standard deviation in a 1,000-table file: pooled field / one team at its 370 of our tables,
measured by cutting rounds 3 and 5 into 1,000-table chunks (A). Pooled field rates are tight ("±2 points" is
their 95% band at worst); one team's rare spots are not; the top 5 pooled sit near half the team figure.
Sampling is not the risk: the field's own move to the next round averaged 1.3-1.6 points per rate (A). So act
when a pooled rate is 2+ points past a threshold in practices 1 and 2 together, among teams that raise.

| # | Statistic | Noise | If... then... so... |
|---|---|---|---|
| 1 | Fold to a 3-bet (opener) | ±0.4 / ±1.4 | 70+: regional folders; wide 3-bets pay. 60-70: plan holds. Under 58 with row 2 high: counter-wave; 3-bet for value only (**PLAN CHALLENGE**, assumption 1) |
| 2 | 4-bet rate (opener re-raises) | ±0.2 / ±0.7 | 15+: counter-wave (Boston 23, Bay Area 7-8). Under 10: nobody punishes light 3-bets yet |
| 3 | Fold to a 4-bet (3-bettor) | ±1.5 / ±5 | 60+ pooled over the teams of row 4: re-aggression pays (contrarian design 1). Never per team: about 100 chances |
| 4 | Teams 3-betting 25%+ with PFR 30%+ | ±0.5 per team | 6+ of 19: wide is crowded; don't join. 2 or fewer: pressure is under-supplied |
| 5 | Open-limp rate; teams limping 15%+ | ±0.1 / ±0.3 | Field 6+: drafts remain; discount this practice. 4+ teams: a limp-or-shove bloc |
| 6 | Open-shove first in at 10bb or less (also 10-15, 15-20); calls of those shoves | ±0.6 / ±2.7; ±0.4 / ±1.5 | Shoves under 30: steal from short stacks. Over 55, and over 30 at 10-15: shove-heavy (**assumption 3**). Calls under 20: shove wider; over 35: for value only |
| 7 | Big blind folds to one open | ±0.4 / ±1.0 | Over 60: steal wide. Under 40: defence wave; open tighter late, bet for value |
| 8 | C-bet; bettor folds to a flop raise; flop raise rate | ±0.4; ±1.1 / ±4.5; ±0.2 | C-bet 75+, folds 55+, raises under 10: raise-bluffing pays (design 2). Folds under 35: raise for value only |
| 9 | Fold to a bet: flop, turn, river | ±0.4, ±0.5, ±0.8 / ±1.2, ±2, ±3 | Flop 58+: bet when checked to. Under 45: value-bet thicker |
| 10 | All-in collisions before hand 40; players left at hand 40; the floor bot's score | about ±0.05 (estimated) | 1.7+, 5.4 or fewer and 10+: the field busts itself; tight gains (design 3) |

Fix definitions first: the regional's fold to 3-bets was 67-70% as a team-equal mean but 73% pooled by
opportunity. Break-evens depend on today's modal open and 3-bet sizes (regional: 2.5bb and 3.0x).

## 4. What PLAN.md assumes about the field, and the sign each has broken

| Assumption (PLAN §1-2, DECISION_RULES §5) | Regional check today | Broken when |
|---|---|---|
| The field folds to 3-bets 60-70% | A: 59% to 68%; practice 1, 50%; the winner 80-87% | Row 1 under 58 or over 72 |
| Finalists start at Boston's counter-wave | C: one regional, estimated list | Row 2 under 10 with row 1 over 65 |
| Limping and flat-calling lose | A: each correlates with score at -0.1 to -0.3 in every round; but Lemonade limped 21% | A top-5 team limps or flats 15%+ |
| Open-shove 35-50% at 10bb or less | A: 41% from round 3; practice 1, 26% | Row 6 |
| Big bets and raises are strong hands | A for the folds; showdown strength unmeasured | Flop raises over 15%, or under half of raisers' shown hands are two pair or better |
| No style the top 5 share beats ours | C: unresolved in simulation | 3+ of the top 5 in one class that isn't ours |
| Scores compress near 12.5 | C; the regional top-20 spread was 1.7-3.0 | Top-to-median gap over 3: a weak tail exists and exploiting it pays |
| Practice rounds are not full of experiments | A: 3% | Over a third of teams differ between a practice and the next scored round |

**Unknown:** the variant; points per place (the rules say they vary by variant); the 20 names; Pittsburgh's
variant and field; whether any finalist recognises opponents by name.

## Appendix A: regional reference values (measured 14 November)

Team-equal means, percent, teams other than us. Throwaway scripts read the 14 local Bay Area files
(`data/README.md`) and were deleted; definitions follow `research/finals_prep/adaptation/extract.py`.

| Statistic | Practice 1 | Round 1 | Round 3 | Round 6 | Top 20, round 6 | Chances per team per table |
|---|---|---|---|---|---|---|
| Fold to 3-bet | 50 | 59 | 68 | 67 | 67 | 4.2 |
| 4-bet | 23 | 12 | 7 | 8 | 9 | 4.2 |
| Fold to 4-bet | 20 | 21 | 31 | 39 | 50 | 0.25 |
| 3-bet | 13 | 8 | 9 | 13 | 24 | 34 |
| Open first in | 31 | 30 | 34 | 35 | 40 | 42 |
| Open-limp | 9 | 7 | 4 | 6 | 3 | 42 |
| Open-shove at 10bb or less / 10-15 / 15-20 | 26 / 10 / 4 | 32 / 13 / 5 | 41 / 20 / 8 | 41 / 22 / 10 | 53 / 31 / 14 | 1.4 / 2.3 / about 2.5 |
| Call a shove of 10bb or less | 20 | 22 | 21 | 23 | 30 | 2.5 |
| Big blind folds to an open | 63 | 67 | 65 | 58 | 43 | 7.7 |
| Flat-call an open outside the big blind | 14 | 12 | 12 | 12 | 8 | 22 |
| C-bet | 61 | 61 | 69 | 74 | 78 | 2.9 |
| Fold to flop / turn / river bet | 48 / 35 / 35 | 48 / 40 / 45 | 52 / 46 / 52 | 53 / 47 / 50 | 58 / 50 / 51 | 5.0 / 1.7 / 0.7 |
| Raise a flop bet | 12 | 10 | 9 | 10 | 10 | 5.0 |
| Bettor folds to a flop raise | 27 | 29 | 42 | 49 | 63 | 0.37 |

Classes (`research/finals_prep/metagame/REPORT.md`, implication 4): wide = 3-bet 25%+ with PFR 30%+;
shove/limp = limp 15%+, open-shove 8%+ or VPIP 50%+; tight = VPIP 20% or less with 3-bet 8% or less.
Rank persistence, rechecked from points at our tables: round-to-round Spearman 0.79-0.88 over 127 teams
(official scores 0.84-0.91); 2.4-5.3 places moved per round within the top 20.

## Appendix B: sources

- Hand files: `/Users/dylan/Documents/GitHub/nolimit-live/data/hands/` (4 build practices, 6 scored rounds).
- `research/finals_prep/adaptation/REPORT.md`, `res_q2.txt`, `res_boston.txt`, `res_q1_top.txt`: field direction, Boston's top 20, bot changes, seat learning.
- `research/finals_prep/redteam/REPORT.md` checks 1-10; `metagame/REPORT.md` (simulation, C); `identity/REPORT.md`; `literature/REPORT.md`.
- Official rules (weights, qualification, payouts, fillers): https://pokerbot.sequoiacap.com/rules.html and `prep/docs/official_rules.txt`.
- Sequoia's Bay Area recap, 9 November (folds to a paired exposed card 72%, no river bluffs, all-in bots stopped winning): https://x.com/sequoia/status/2119839104733200785
- A Bay Area team's repository, whose commits show mid-event copying of the leaders: https://github.com/nnicholas-c/poker_sequoia
- A Boston entrant's eight iterations: https://github.com/AlexPha45/No-Limit-Pokerbots
- Harvard Crimson on the Boston regional: https://www.thecrimson.com/article/2026/11/12/poker-tournament-regional/
- Not found: Pittsburgh's results, a list of finalists, or anything by 2 Curry. (Pittsburgh's variant was found
  later the same morning: `notes/pre/variants.md`.)
