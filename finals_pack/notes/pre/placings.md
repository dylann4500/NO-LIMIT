# Where our regional bot lost its places (pre-event note, for `stylist` and `challenger`)

Drafted Saturday 14 November from the regional's raw hand files (rounds 5 and 6, 20,000 tables each) and official results. Notes only, no bot code.
**Grades** as `strategy/EVIDENCE_TABLE.md`: **A** measured fact; **C** candidate; **D** withdrawn; **arith.** exact arithmetic.

## The answer

1. **The premise needs a correction.** By rounds 5-6 our second places (14.8%, 13.9%) were above the top five's (13.2%, 13.4%). We lacked thirds (10.0%, 10.8% against 12.4%, 12.2%) and firsts (23.1%, 22.4% against 25.1%, 23.6%), and we cashed 47.8%, 47.1% against 50.6%, 49.2% (A, official). "27/11/10" in `whatwins.md` is round 1's bot (27.0 / 10.0 / 8.0); "top teams 22/20/18" matches no top-five team in any round (D).
2. **The places went at 6, 5 and 4 left**, most at 6 and 5: there we busted 15% and 18% of the time, 2 Curry and Lemonade 11-13% and 13-14%. With three left we held up better than the top five (A, official).
3. **We busted by raising all-in, not by calling or blinding down.** With 4-6 left, 71% of our busts were all-in raises (53% an all-in re-raise over an open; median stack at the bust 17.5bb), 7-9% calls, 17-20% after the flop, 2.6% blinded down. Top five: 54 / 23 / 18-19 / 4-5 (A).
4. **Those re-raises paid on average** (+0.42 and +0.48 points each, 2.4-2.6 a table), with a margin of 5-10 points of fold rate, smallest at 4 left (A).
5. **For Sunday**: gate every all-in re-raise on the measured fold rate by players left, and give the style a way to win pots at 4-6 left without staking the stack (C).

## 1. Where each bot busts

Chance of busting at a stage, given it was reached (official results, 20,000 tables per team; round 5 / round 6; all stages in the appendix):

| Players left | avalon | 2 Curry | Lemonade | Top five pooled |
|---|---|---|---|---|
| **6** | **15.0 / 15.2** | 12.6 / 12.4 | 11.5 / 11.4 | 13.4 / 14.2 |
| **5** | **17.5 / 17.9** | 14.4 / 13.9 | 13.2 / 13.1 | 15.7 / 16.0 |
| 4 | 18.4 / 19.6 | 16.7 / 17.5 | 15.3 / 15.3 | 17.1 / 17.7 |

- **Size of the prize**: with the top two's rates at 6 and 5 left alone and all else ours, we reach the money in 51% of tables instead of 47%, about +1.6 points a table (arith. on A; C as a forecast). Lemonade finished round 6 2.1 ahead of us.
- **Heads-up was no surplus**: we won 61-62% of our heads-ups; the top five 64-66%, 2 Curry 67-69% (A).
- **Timing** (A): our 6th, 5th and 4th places fell at median hands 60, 70 and 86 with 17.9, 16.3 and 14.8bb. The top five busted 4th with 10.5-11.2bb; the field with 8bb, a third of them at 5bb or less. We held 10bb or less in 1.9% of our hands at 4-6 left; the field in 9-10%.

## 2. What we were doing when we busted with 4-6 left

| Busts at 4-6 left, % (round 5 / round 6) | n | All-in raise | Call of an all-in | After the flop | Blinded down |
|---|---|---|---|---|---|
| avalon | 7,150 / 7,389 | 71 / 72 | 7 / 9 | 20 / 17 | 2.6 / 2.6 |
| 2 Curry | 330 / 372 | 45 / 47 | 12 / 12 | 37 / 33 | 6 / 5 |
| Lemonade | 321 / 320 | 51 / 49 | 22 / 22 | 20 / 20 | 8 / 9 |
| Top five pooled | 1,818 / 1,928 | 54 / 54 | 22 / 24 | 19 / 18 | 5 / 4 |
| Other 121 teams | 50,852 / 50,579 | 45 / 45 | 16 / 17 | 24 / 22 | 13 / 15 |

An all-in raise ended our tournament at 4-6 left in 25-26% of tables; the top five's in 17-19%, 2 Curry's in 13-16% (A).

**The all-in re-raise over an open** (A; 52,322 / 47,873 of ours at 4-6 left):
- 2.6 / 2.4 a table; top five 1.2 / 1.1, Lemonade 1.4, 2 Curry 0.2.
- Called 20% / 22%; we then won 38% / 40% and lost 4.5 / 4.2 points. Folded to, +1.72. Net +0.48 / +0.42 each.
- **The price rises towards the money.** Called, it cost 2.8-3.1 points at 6 left, 4.0-4.2 at 5, 6.0-6.5 at 4; folded to, it gained 1.5-1.8 throughout. Break-even fold rate: 65-67%, 70%, 77-78%. We got 73-75%, 78-80%, 82-84%.
- The 15-25bb stack made least (+0.39 / +0.30 each) and took 61-63% of these busts.

**Calls were sound** (A): fresh calls of an all-in won 55-57% (+0.37 / +0.45 each; mostly a big stack calling a shorter one, where `whatwins.md` section 4 asks 54%); calls after our own raise won 62-67% (+1.20 / +1.77) against thresholds of 58-65%.

**How the top two took the same stage** (A, at our tables only): 2 Curry made +3.2 / +2.6 points a table at 4-6 left from pots it raised and ended before the flop without an all-in (a quarter of its hands); we made +0.4 / +0.1 that way. Lemonade left 81% of hands unplayed and re-raised all-in more selectively (+0.80 / +0.70 each).

## 3. What a Sunday style should take from it

**Does not depend on the variant:**
- **Guard the two places before the money** (C): print each candidate's bust rate by players left from the first local run.
- **An all-in re-raise needs a fold rate, and the rate needed climbs with each bust** (arith. from today's ICM table; A that it held at the regional). Measure the field's fold rate to our all-ins by players left in practices 1-2 and gate the range on it. Finalists fold less: Boston's top 20 went from 75% to 57.5% (A, `whatwins.md`).
- **Own a second source of points at 4-6 left**: raises that win the pot without the stack at risk (A that the winner had it and we did not; C that copying it pays).
- **Keep**: calls at the ICM threshold; never blinding down.
- **Test heads-up as its own matchup**: 3 points of heads-up win rate are 0.2 points a table (arith.).

**Probably depends on the variant:**
- Winning 38-40% when called (three hole cards keep hands close).
- The field folding 78-84% to an all-in re-raise.
- The post-flop share of busts (ours 17-20%, 2 Curry's 33-37%: the discard and the exposed card).
- Hand numbers and stack depths (the regional's blinds), and which stage is "before the money" (50/30/20, 8 seats).

## Not verified

- Which of our all-in re-raises lost: averages by stack and players left only, not by hand strength.
- The top five away from our tables (1,069-1,146 tables each; pooled, they scored 1.2 lower at our tables than overall in round 6).
- Whether fewer all-ins at 6-5 left would have cost the first places they also won.

## Appendix

**Method.** One streaming pass over each full round file. A bust is the hand a seat's stack reaches zero; players left and the stack in big blinds are taken at that hand's start. Cause: with over 5bb at the bust hand, what the seat did in it (all-in raise first in or over a raise; call of an all-in or call for its last chips; chips in after the flop); with 5bb or less, the last earlier hand in which it lost 40% or more of its stack while playing, if that left it at 8bb or less, else "blinded down". Points by action are sums of the file's own `equity_after - equity_before` (the server's ICM, bust places paid). Top five = final standings: 2 Curry, Lemonade, AZ, sandylikesfrogs, Team 72. Filler seats excluded. The scripts were temporary and are deleted.

**Official places, % of 20,000 tables** (1st / 2nd / 3rd, cash, score):

| Team | Round 5 | Round 6 |
|---|---|---|
| avalon | 23.1 / 14.8 / 10.0, 47.8, 17.95 | 22.4 / 13.9 / 10.8, 47.1, 17.53 |
| 2 Curry | 28.9 / 12.9 / 10.4, 52.2, 20.41 | 27.3 / 13.7 / 11.5, 52.5, 20.08 |
| Lemonade | 25.7 / 15.2 / 13.3, 54.2, 20.09 | 23.9 / 16.4 / 13.8, 54.0, 19.61 |
| AZ | 25.4 / 10.9 / 10.3, 46.6, 18.04 | 24.0 / 10.7 / 10.4, 45.0, 17.27 |
| sandylikesfrogs | 22.6 / 13.8 / 15.2, 51.6, 18.49 | 20.2 / 13.3 / 14.0, 47.4, 16.87 |
| Team 72 | 22.8 / 13.0 / 12.6, 48.4, 17.83 | 22.4 / 12.8 / 11.6, 46.9, 17.39 |
| Top five pooled | 25.1 / 13.2 / 12.4, 50.6, 18.97 | 23.6 / 13.4 / 12.2, 49.2, 18.24 |

Our places by round (1st / 2nd / 3rd): 27.0 / 10.0 / 8.0, 23.7 / 10.3 / 9.0, 26.9 / 12.3 / 9.6, 23.9 / 14.4 / 10.0, then the two above. Top five pooled, rounds 1-4: 31.2 / 10.6 / 10.3, 27.9 / 11.6 / 11.9, 26.2 / 12.1 / 12.2, 25.9 / 12.8 / 12.3. Gap to the top five in round 6, in points: firsts -0.60, seconds +0.15, thirds -0.28.

**Bust rate by stage, all stages** (official; chance of busting given the stage was reached; round 5 / round 6):

| Players left | avalon | 2 Curry | Lemonade | Top five pooled | Other 121 teams |
|---|---|---|---|---|---|
| 8 | 6.1 / 5.9 | 6.7 / 6.3 | 7.6 / 7.9 | 6.7 / 7.0 | 12.6 / 12.6 |
| 7 | 11.0 / 10.7 | 10.1 / 9.9 | 9.8 / 10.1 | 10.3 / 10.9 | 14.7 / 14.7 |
| 6 | 15.0 / 15.2 | 12.6 / 12.4 | 11.5 / 11.4 | 13.4 / 14.2 | 16.9 / 16.8 |
| 5 | 17.5 / 17.9 | 14.4 / 13.9 | 13.2 / 13.1 | 15.7 / 16.0 | 20.2 / 20.2 |
| 4 | 18.4 / 19.6 | 16.7 / 17.5 | 15.3 / 15.3 | 17.1 / 17.7 | 25.5 / 25.4 |
| 3 | 20.9 / 22.9 | 19.9 / 21.9 | 24.5 / 25.5 | 24.4 / 24.9 | 34.0 / 33.9 |
| 2 | 39.1 / 38.3 | 30.9 / 33.4 | 37.1 / 40.7 | 34.4 / 36.2 | 51.1 / 51.0 |

**More on the all-in plays at 4-6 left**: our re-raise over an open made +1.26 / +1.00 points a table; at 25bb+ we usually covered the caller (+0.58 / +0.54 each). Lemonade's won 44-45% when called. The top five's calls after their own raise won 55-56% and broke even (+0.10 ± 0.22 / -0.06 ± 0.21). Lemonade opened first in 1.3-1.5% of the time at 25bb+.

**Bust stage for the other three** (official, round 5 / round 6): at 6 left AZ 16.3 / 16.7, sandylikesfrogs 11.7 / 13.8, Team 72 14.9 / 16.7; at 5 left 19.1 / 19.1, 15.8 / 17.1, 16.3 / 17.2.

**Median bust hand and stack by place** (round 6; at our tables for other teams):

| Place | avalon | Top five | Other teams |
|---|---|---|---|
| 8th | hand 23, 33.5bb | 22, 36.2bb | 12, 46.0bb |
| 7th | 45, 20.4bb | 43, 22.7bb | 37, 20.6bb |
| 6th | 60, 17.9bb | 58, 17.0bb | 57, 14.5bb |
| 5th | 70, 16.3bb | 73, 13.5bb | 74, 10.9bb |
| 4th | 86, 14.8bb | 90, 11.2bb | 93, 7.9bb |
| 3rd | 104, 12.5bb | 105, 12.1bb | 107, 7.9bb |
| 2nd | 125, 12.3bb | 122, 14.1bb | 126, 9.6bb |

Share of busts at 5bb or less: ours 9-14% at every place; top five 7-15%; other teams 12-35% (35% in 4th).

**Bust cause in detail, 4-6 left, round 6** (% of the team's busts in that stage):

| | All-in first in | All-in over a raise | Call | Post-flop call / bet | Short after a lost all-in / call / post-flop pot | Blinded down |
|---|---|---|---|---|---|---|
| avalon | 15.1 | 53.4 | 7.1 | 4.8 / 10.2 | 3.1 / 1.7 / 1.8 | 2.6 |
| 2 Curry | 27.7 | 17.7 | 9.9 | 14.0 / 15.3 | 1.6 / 1.9 / 3.8 | 4.8 |
| Lemonade | 6.6 | 40.0 | 19.4 | 4.7 / 12.8 | 2.5 / 2.5 / 2.5 | 9.1 |
| Top five | 16.0 | 35.9 | 21.7 | 7.4 / 8.2 | 2.1 / 1.9 / 2.3 | 3.9 |
| Other teams | 23.8 | 18.7 | 15.4 | 10.3 / 7.7 | 2.2 / 1.8 / 4.2 | 15.2 |

Other stages, our busts (round 6): 7-8 left (3,236): all-in raise 48%, call 17%, post-flop 33%, blinded 2%. Three left (2,167): 69 / 16 / 11 / 4. Heads-up (2,727): 73 / 14 / 8 / 5.

**Points per table by stage** (above the 12.5 average; other teams at our tables only; round 5 / round 6):

| Stage | avalon | 2 Curry | Lemonade | Top five |
|---|---|---|---|---|
| 7-8 left | +1.62 / +1.65 | +2.36 / +1.94 | +2.26 / +2.25 | +2.14 / +1.68 |
| 4-6 left | +2.75 / +2.35 | +3.94 / +3.01 | +2.71 / +3.06 | +2.75 / +1.97 |
| 3 left | +0.72 / +0.58 | +0.87 / +0.73 | +0.75 / +0.75 | +0.51 / +0.47 |
| Heads-up | +0.37 / +0.45 | +0.32 / +0.54 | +1.12 / +0.61 | +0.54 / +0.44 |

Standard errors: ours about 0.1 per cell at 4-6 left; one other team's about 0.4.

**Our 4-6-left points by action** (round 5 / round 6): all-in over a raise +1.45 / +1.23 (7.0% / 6.5% of hands); call of an all-in +0.39 / +0.47; all-in first in +0.25 / +0.19; post-flop +0.23 / +0.21; pots entered and ended before the flop without an all-in +0.41 / +0.07 (11%); hands not played +0.03 / +0.18.

**All-in re-raise over an open, ours, round 6**: by players left: 6 left n 12,743, called 27%, won 40% when called, +0.36 ± 0.05; 5 left 16,891, 22%, 40%, +0.46 ± 0.04; 4 left 18,239, 18%, 41%, +0.42 ± 0.05. By stack: 5-10bb n 1,343, +0.62 ± 0.19; 10-15bb 5,781, +0.53 ± 0.09; 15-25bb 24,883, +0.30 ± 0.04 (2,461 busts); 25bb+ 15,638, +0.54 ± 0.03 (53 busts). Round 5: 14,015 / 18,231 / 20,076 at 6 / 5 / 4 left, +0.38 / +0.54 / +0.50.

**All-in first in, ours, round 6, 4-6 left**: 16,194 (0.81 a table), called 25%, +0.23 ± 0.04; at 5-15bb only +0.02 to +0.09.

**The "+1.6 points" sum**: our round-6 rates give 0.941 × 0.893 × 0.848 × 0.821 × 0.804 = 47.0% reaching three left; with 12.0% and 13.5% at 6 and 5 left, 51.4%. A cash was worth 37.2 points to us on average; 4.4 points of cashes × 37.2 = 1.6.
