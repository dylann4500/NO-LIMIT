# The challenger bar: an independent check (Saturday 14 November; both humans read the first ten lines)

**Recommendation: no change to any bar in `strategy/DECISION_RULES.md` section 3.**
- **In the top 3:** keep z ≥ 1.0, and z ≥ 1.5 with a big lead. Grade C (model only: no regional top-3 team gave a test case).
- **4th-8th:** keep z ≥ 0.5, and z ≥ 0 in the last two rounds. Grade A for the direction (regional backtest), C for the exact height.
- **9th or lower:** keep the same bars as 4th-8th. Grade C. A lower bar or playing blind gains nothing until the last round, when our chance is about 1% either way.
- **Measured filter accuracy:** one practice predicts a challenger's edge in the scored round with a standard error of about 0.8 points per table across the regional field and about 1.0 for top-20 teams. The rule's 0.7 is the practice-side noise alone; the memo's 1.0 stands.
- The memo's table reproduces. Its claim that the top-3 bar is too cautious does not hold: for a team in the top 3 the caution costs about half a percentage point of top-3 chance when things go well and earns one to three when practice flatters the challenger.

Notes only; no bot code. Grades: **A** measured on regional data, **C** model or judgment. Everything about
Sunday's 20-team field is C until practice data lands. "Points" are points per table; "percentage points" are
chances of a final top 3.

## 1. How good the practice filter was at the regional (A)

The rule compares a challenger's practice score with the live bot's last scored score, each against yardstick
teams that did not change bot. I rebuilt that comparison for every regional team in the four windows that have
hand files (before rounds 3-6), labelling who played which bot with the archive's change detector.

| What | Result | n |
|---|---|---|
| Same bot in practice and the next scored round: spread of (scored − practice) after the yardstick shift | 0.66 all teams; 0.72 bots new in that practice; 0.94 top-20 teams | 123; 61; 18 |
| Unchanged bot, one scored round to the next, against other unchanged bots | 0.44 | 106 |
| **Error of the rule's edge as a forecast of the scored-round edge** | **0.82**; about 1.0 for top-20 teams (±0.2) | 966 pairs |
| Edge seen in practice against gain realised, bots new in practice and then played | slope 0.97, r 0.95; strong teams 0.74, 0.81 | 61; 23 |

**Backtest.** 23 strong teams (last score 14 or more, or cumulative top 20) showed a new bot in practice and
then played it. The edge had the right sign for 22 of them. The current rule would have played 17 (mean
realised gain +1.21, one loser) and refused 6 (mean −0.57, one winner). For the ten in the cumulative top 20
it was right every time. The top-3 bar (0.7 points) applied to all 23 would have given up a fifth of the
total gain; 1.05 points, three tenths. No top-3 team ever showed a new bot in practice and then played it, so
the top-3 bar has no regional test.

Two cautions. These teams chose to play their bot, which flatters the filter. And one opponent's change was
0.7% of the regional field; on Sunday it is 5%. Expect 1.0 or worse.

## 2. The top-3 model, rebuilt (C)

Twenty score levels, weights 1-6, persistence 0.63 and round-to-round noise 1.04 from the regional top 20; a
challenger with true edge drawn from (mean −0.5, spread 1.5), seen through one practice with error 1.0. My
table matches the memo's within 2 percentage points, so its arithmetic is sound. I then stressed it in about
30 cases. Chance of a final top 3 over a whole day, all starting ranks pooled:

| Case | No challenger | Current bars | Top-3 bar cut to 0.35 points | Bar 0 everywhere | Blind |
|---|---|---|---|---|---|
| Memo's assumptions | 15.1 | 32.2 | 32.4 | 32.3 | 11.0 |
| Rivals field filtered challengers too | 3.3 | 15.3 | 15.4 | 15.6 | 4.8 |
| Practice flatters the challenger by 0.75 | 15.1 | 31.6 | 31.1 | 29.6 | 11.0 |
| Challengers worse than assumed (mean −1.5) | 15.1 | 19.2 | 19.2 | 18.7 | 0.9 |
| Bad challengers, noisy and flattering practice, rivals filtering | 3.3 | 2.4 | 2.3 | 1.9 | 0.0 |

Current bars in points: 0.7 in the top 3 (1.05 with a big lead), 0.35 outside, 0 outside in the last two
rounds. The order is the same inside each rank band, and with a challenger ready in only three windows
(Appendix B).

- Any bar from 0 to 1.0 points lands within about 1 percentage point of the best in every case. Below 0 the
  cost rises fast once practice flatters the challenger.
- Dropping the challenger inside the top 3 costs a team that is there after round 3 about 11 percentage
  points in the memo's case and about 4 with poor challengers. It wins only in the last row, by 2.
- Unknown points per place: scaling every score by 1.6 changes nothing, provided the SE is measured on the
  day and not fixed at 0.7.

## 3. The memo's three readings

1. **"How different the challenger is matters more than the bar."** The first half survives. The second is
   an assumption: a spread of 2.5 adds 12 percentage points only if it costs just half a point of mean.
   Regional top-20 rewrites had a spread of 1.6; no class had 2.5.
2. **"The practice filter is what makes variance pay."** Survives, and the backtest supports it. Blind play
   beats standing still only from about 6th with two rounds left, and never beats the filter.
3. **"It pays at every rank; in the top 3, keep the filter."** Survives every single stress; fails only in
   the combined worst case. The current rule already does this.

What fails: the table's percentages, which halve when rivals do the same (the challenger keeps pace; it does
not put us ahead), and "the top-3 bar is too cautious".

## 4. The memo's three other proposals

- **"Two standard errors off is a plan challenge" is too sensitive: holds (A for the numbers, C for the
  fix).** A pooled field rate's standard error is 0.1-0.5 points in a 1,000-table file, and the regional field
  moved 0.5-2.7 points between consecutive scored rounds. For field rates use "2 points or more outside the
  band, in two downloads running"; keep 2 SE for scores.
- **The maturity adjustment's direction: holds on average, weakly.** Early practices over-reward tight play
  (score against 3-bet rate: r −0.54 in practice 1, +0.25 in round 6). For one unchanged bot the evidence is
  mixed: aggressive bots gained 1.3 points on tight ones from practice 2 to 3, and lost 0.7 from 3 to 4. A
  tie-breaker worth at most 1 point.
- **One definition of fold-to-3-bet: holds (A).** Round 3 was 68.0 as a team-equal mean and 73.1 pooled. The
  plan's 60-70% band was written on team-equal numbers; `stat_definitions.md` makes that the default.

## 5. If you make one edit

No bar needs it. In section 3's first bullet, replace "Practice SE is **at least 0.7** points per table (more
with 20 teams); z = edge / SE of the edge." with:

> SE of the edge: the standard deviation of the yardstick teams' own (practice score − last scored score),
> times √(1 + 1/number of yardsticks), when there are 6 or more yardsticks; with fewer, 0.8. Never below 0.7.
> z = edge / SE. Give the edge in points too, and say so if the SE is above 1.0.

At the regional this gives 0.70-0.77, and it rescales itself if the points per place change. An SE inflated
to 1.4 would cost 1-2 percentage points.

## 6. Not verified

- The filter's accuracy in a 20-team field; whether Sunday's practices have 1,000 tables.
- The mean and spread of our own challengers: the regional figures are other teams' bots.
- The top-3 bar: model only.
- The windows before rounds 1 and 2 (no team kept one bot from practice 3 into round 1; practice 5 was never
  downloaded).
- The best trigger for plan challenges: "2 points" is judgment.

## Appendix A: data, method and measurement tables

**Data.** Official results for all 15 Bay Area rounds and the final standings
(`data/results-bay-area/`, 148 entries, 127 active); 14 hand files (`data/hands/`, read with Python's `-I`).
Throwaway scripts lived in a temp folder and are deleted. The archive's `extract.py` was run unchanged.

**Who played which bot.** Per team and window, the mean squared z over 25 behaviour rates between the
practice, the scored round before and the scored round after (as `adaptation/REPORT.md` section 5: match under
3.5, differ over 6; a scored pair unchanged under 5). My counts for the four windows: same bot in all three 62
(archive 66), new bot in practice and then played 61 (90), changed after practice 102 (144), practice differs
from both 106 (105), practice-only 17 (17), unclear 138 (71). Mine is stricter. Unchanged scored pairs match
the archive to within one (14, 13, 25, 28, 26 against 14, 13, 25, 28, 27). Yardsticks: the teams with the same bot in all three rounds
(9, 14, 19, 20 per window). On the day the next round is unknown, so the live yardstick set is wider.

**Per window, official scores only.** Next scored score on practice score, then (next − previous scored) on
(practice − previous scored). Slope / correlation / residual spread.

| Window | n | Levels, all teams | Levels, top 20 going in | Changes, all teams | Changes, top 20 going in |
|---|---|---|---|---|---|
| Practice 4 → Round 1 (12,500 tables) | 122 | 0.87 / 0.85 / 2.58 | 0.80 / 0.82 / 1.49 | 0.72 / 0.67 / 2.50 | 0.46 / 0.59 / 1.21 |
| Round 1.5 → Round 2 | 126 | 0.89 / 0.92 / 1.57 | 0.88 / 0.65 / 1.25 | 0.96 / 0.76 / 1.64 | 0.19 / 0.24 / 0.87 |
| Round 2.5 → Round 3 | 126 | 0.86 / 0.91 / 1.59 | 0.86 / 0.72 / 1.34 | 0.80 / 0.66 / 1.65 | 0.52 / 0.30 / 1.31 |
| Round 3.5 → Round 4 | 126 | 0.86 / 0.85 / 2.22 | 0.90 / 0.83 / 0.91 | 0.41 / 0.38 / 1.98 | 0.40 / 0.56 / 0.65 |
| Round 4.5 → Round 5 | 126 | 0.86 / 0.85 / 2.21 | 0.84 / 0.74 / 1.10 | 0.73 / 0.42 / 2.26 | 0.19 / 0.20 / 0.86 |
| Round 5.5 → Round 6 | 126 | 0.80 / 0.89 / 1.84 | 0.26 / 0.52 / 1.43 | 0.56 / 0.56 / 1.81 | 0.19 / 0.44 / 1.21 |

The top-20 slopes of 0.2-0.5 mix teams that played their practice bot with teams that did not. Split by that:

| (next − previous) on (practice − previous), yardstick shift removed | n | Slope | r | Residual |
|---|---|---|---|---|
| Practice bot = next bot, all teams | 123 | 0.92 | 0.93 | 0.65 |
| ... by window (rounds 3, 4, 5, 6) | 23, 29, 29, 42 | 0.96, 0.83, 0.77, 0.95 | 0.91, 0.85, 0.86, 0.96 | 0.76, 0.65, 0.58, 0.63 |
| ... final top 20 | 18 | 0.64 | 0.83 | 0.74 |
| New bot in practice, then played: all / strong / final top 20 | 61 / 23 / 8 | 0.97 / 0.74 / 0.69 | 0.95 / 0.81 / 0.80 | 0.73 / 0.72 / 0.95 |
| Practice bot ≠ next bot, all teams | 225 | 0.50 | 0.37 | 2.77 |
| ... by window | 63, 54, 63, 45 | 0.80, 0.29, 0.77, 0.06 | 0.65, 0.25, 0.39, 0.05 | 2.07, 2.84, 3.15, 2.55 |
| ... final top 20 | 30 | 0.13 | 0.18 | 1.56 |
| Unchanged in all three (no true change; pure noise) | 62 | 0.27 | 0.46 | 0.35 |

Among unchanged bots the practice-side edge had a spread of 0.67 (0.73 for strong teams): 16% of them
"showed" an edge of 0.7 or more by noise alone, 6% an edge of 1.0, none 1.5.

**What strong teams' changes were worth** (yardstick-adjusted change in score; last score 14 or more):

| Group | n | Mean | Spread | Better than yardstick | Gain over 1 | Loss over 1 |
|---|---|---|---|---|---|---|
| Unchanged | 16 | −0.29 ± 0.09 | 0.34 | 25% | 0% | 0% |
| New bot shown in practice, then played | 23 | +0.75 ± 0.25 | 1.21 | 74% | 35% | 9% |
| Changed after practice (never practice-tested) | 43 | −0.14 ± 0.27 | 1.80 | 56% | 19% | 23% |
| Practice bot differed from both | 26 | −0.20 ± 0.24 | 1.21 | 46% | 12% | 23% |

So a strong team's untested change was worth about what standing still was, with a spread of 1.2-1.8. The
memo's challenger (mean −0.5, spread 1.5) is, if anything, a little harsh on the mean. These were changes
their teams judged worth playing, so an arbitrary challenger of ours may be worse.

**Backtest by bar** (the 23 strong teams: last score 14 or more, or top 20 on cumulative points; edge in points; gain is the realised change against yardsticks):

| Bar on the edge | Played | Mean gain of played | Mean gain of refused | Total gain | Losers played | Winners refused |
|---|---|---|---|---|---|---|
| Play everything | 23 | +0.75 | — | +17.2 | 6 | 0 |
| 0 | 18 | +1.20 | −0.87 | +21.5 | 1 | 0 |
| 0.35 (z 0.5) | 16 | +1.31 | −0.53 | +20.9 | 0 | 1 |
| 0.7 (z 1.0) | 12 | +1.41 | +0.02 | +17.0 | 0 | 5 |
| 1.05 (z 1.5) | 9 | +1.65 | +0.17 | +14.9 | 0 | 8 |
| Current rule by each team's rank and round | 17 | +1.21 | −0.57 | +20.6 | 1 | 1 |

Five practice-only bots from the top 47 (edges −0.3 to −11.2) were all withdrawn by their teams, as the rule
would have done; one was AZ's, 3rd at the time (edge −0.7). Strong unchanged bots fell 0.38 further per round
than the average yardstick (n 18). The field-wide shift from a practice to the next scored round was −0.81,
−0.34, −0.19 and −0.31 for unchanged bots; the yardsticks remove it. Our own four windows: edge +3.15 before round 3 (play; realised +3.26); −0.07, −0.38 and
−1.30 before rounds 4-6 (the rule keeps the live bot each time; we switched each time and realised −0.52,
−0.05 and −0.44 against yardsticks, about level with a strong unchanged bot's −0.3).

## Appendix B: the model

**Build.** 150,000 simulated days per case, common random numbers across policies. Levels start with spread
1.5; each round level = 0.63 × level + noise of 1.04 (the regional final top 20: lag-1 correlation 0.74,
fitted persistence 0.63). A scored round adds 0.2 of sampling noise. Before each round from 2 on, we may hold
a challenger whose true edge over the live bot is drawn from (mean, spread); practice shows edge + bias +
noise; it plays if that clears the bar; a played challenger's edge then decays like any level. Selecting the
top 20 by final rank overstates mean reversion (top 20 after round 1: persistence 0.91), so a sticky field
was a stress case.

**Replication** (chance of a final top 3 by rank after round 3, challenger in rounds 4-6; memo in brackets):

| | 1st-3rd | 4th-5th | 6th-8th | 9th-12th |
|---|---|---|---|---|
| No challenger | 49.5 (47) | 26.5 (27) | 16.0 (17) | 8.3 (9) |
| Mean −0.5, spread 1.5, bar 0.5 | 61.6 (59) | 41.4 (39) | 30.0 (28) | 19.2 (19) |
| Mean −1.0, spread 2.5, bar 0.5 | 67.7 (65) | 49.5 (47) | 39.2 (37) | 28.2 (27) |
| Mean −0.5, spread 1.5, blind | 33.0 (32) | 19.8 (20) | 14.7 (14) | 9.4 (10) |
| Near copy (spread 0.75), bar 0.5 | 50.6 | 28.2 | 17.7 | 9.5 |

The memo's "+3-4" for a near copy is +1 to +2 here; I could not find the reason.

**One window's bar.** This window's bar varies; every other window plays at 0.5. Worst loss of top-3 chance
against the best bar, across 12 stress cases (percentage points; mean loss in brackets):

| Window, band | Bar 0 | 0.25 | 0.5 | 0.75 | 1.0 | 1.5 | Never | Blind |
|---|---|---|---|---|---|---|---|---|
| Round 2, top 3 | 0.8 (0.2) | 0.7 (0.1) | 0.7 (0.2) | 0.9 (0.2) | 1.3 (0.4) | 1.9 (0.8) | 5.3 (2.9) | 15.0 (8.4) |
| Round 4, top 3, small lead | 2.2 (0.5) | 1.6 (0.3) | 1.2 (0.3) | 1.3 (0.3) | 1.7 (0.5) | 2.5 (1.0) | 5.9 (3.3) | 24.7 (13.7) |
| Round 4, top 3, big lead | 7.2 (0.8) | 5.1 (0.5) | 2.2 (0.3) | 1.4 (0.2) | 1.4 (0.3) | 1.4 (0.4) | 1.9 (0.8) | 39.9 (12.8) |
| Round 6, top 3, small lead | 5.4 (0.9) | 4.2 (0.6) | 3.1 (0.4) | 2.1 (0.3) | 1.4 (0.4) | 1.6 (0.6) | 4.0 (2.1) | 31.3 (17.3) |
| Round 4, 4th-8th | 0.9 (0.2) | 0.9 (0.2) | 1.3 (0.3) | 1.8 (0.4) | 2.3 (0.7) | 3.4 (1.5) | 9.0 (4.6) | 13.3 (7.7) |
| Round 6, 4th-8th | 0.5 (0.1) | 0.9 (0.2) | 1.4 (0.3) | 1.9 (0.5) | 2.5 (0.8) | 3.5 (1.6) | 10.2 (4.7) | 8.9 (4.8) |
| Round 4, 9th or lower | 0.3 (0.1) | 0.5 (0.1) | 0.8 (0.2) | 1.0 (0.3) | 1.3 (0.5) | 2.1 (0.9) | 7.0 (2.9) | 4.2 (2.2) |
| Round 6, 9th or lower | 0.1 (0.0) | 0.1 (0.0) | 0.2 (0.1) | 0.3 (0.1) | 0.4 (0.1) | 0.7 (0.2) | 2.3 (0.8) | 0.2 (0.1) |

Read against the current bars: top 3, 0.7-1.05 points, sits at the low-regret end of its rows and is the
right choice late and with a lead; 4th-8th, 0.35 then 0, likewise; 9th or lower would be marginally better at
0 all day (0.3 against about 0.6), too little to justify an edit. The big-lead rows rest on few simulated
days in the worst case (138), so their worst losses are rough. The 12 cases: the memo's; rivals also filter;
practice flatters by 0.75; practice under-rates by 0.75; mean −1.5; near copy; filter error 1.5; the combined
worst case; mean 0; sticky field; compressed field; a window-to-window bias of spread 1.0.

**Day-long policies** (five windows from round 2; chance of a final top 3 by rank after round 3: 1st-3rd /
4th-8th / 9th or lower):

| Case | No challenger | Current bars | Top-3 bar 0.35 | Bars at SE 1.0 (1.0, 1.5; 0.5, 0) | No challenger in the top 3 | Blind |
|---|---|---|---|---|---|---|
| Memo's assumptions | 49 / 20 / 4 | 68.1 / 37.1 / 12.9 | 68.6 / 37.1 / 12.9 | 67.1 / 36.9 / 12.8 | 56.9 / 35.2 / 12.7 | 39 / 17 / 4 |
| Rivals also filter | 23 / 5 / 0.5 | 49.2 / 19.9 / 4.8 | 50.0 / 20.0 / 4.8 | 47.8 / 19.5 / 4.7 | 33.7 / 18.2 / 4.6 | 26 / 9 / 1 |
| Practice flatters by 0.75 | 49 / 20 / 4 | 68.1 / 36.3 / 12.3 | 67.1 / 35.9 / 12.3 | 68.5 / 36.6 / 12.5 | 56.8 / 34.5 / 12.1 | 39 / 17 / 4 |
| Practice flatters by 1.5 | 49 / 20 / 4 | 64.6 / 32.8 / 10.1 | 61.8 / 32.1 / 10.0 | 66.3 / 33.6 / 10.4 | — | 39 / 17 / 4 |
| Mean −1.5 | 49 / 20 / 4 | 55.0 / 24.8 / 6.0 | 54.9 / 24.8 / 6.0 | 54.7 / 24.9 / 6.1 | 51.4 / 24.4 / 6.0 | 10 / 3 / 0 |
| Near copy (mean −0.3, spread 0.75) | 49 / 20 / 4 | 54.7 / 24.8 / 5.9 | 54.7 / 24.8 / 5.9 | 54.3 / 24.7 / 5.9 | 50.8 / 24.3 / 5.9 | 37 / 14 / 3 |
| Hidden failure: 10% of played challengers lose 5 | 49 / 20 / 4 | 64.9 / 34.0 / 11.8 | 64.6 / 33.8 / 11.8 | 64.5 / 34.0 / 11.7 | 56.2 / 32.9 / 11.6 | 32 / 14 / 3 |
| Ready only for rounds 2, 4, 6 | 49 / 20 / 4 | 60.4 / 30.1 / 9.0 | 60.7 / 30.1 / 9.0 | 59.7 / 29.9 / 8.9 | 53.0 / 29.3 / 8.8 | 40 / 18 / 4 |
| Ready only for rounds 4, 5, 6 | 49 / 20 / 4 | 61.6 / 34.7 / 11.9 | 62.0 / 34.8 / 11.9 | 61.0 / 34.6 / 11.8 | 53.3 / 33.3 / 11.7 | 33 / 17 / 6 |
| Sticky field (persistence 0.9) | 66 / 18 / 1 | 78.5 / 32.1 / 4.5 | 79.0 / 32.1 / 4.5 | 77.9 / 31.8 / 4.5 | 69.9 / 31.1 / 4.5 | 52 / 15 / 1 |
| Flat weights | 64 / 18 / 1 | 78.4 / 34.3 / 6.0 | 78.9 / 34.3 / 6.0 | 77.9 / 34.0 / 5.9 | 69.2 / 33.2 / 5.9 | 50 / 15 / 2 |
| Combined worst case | 23 / 5 / 0.5 | 20.6 / 4.0 / 0.3 | 19.2 / 3.8 / 0.3 | 21.6 / 4.1 / 0.3 | 23.0 / 4.2 / 0.3 | 1 / 0 / 0 |

Monte Carlo error is about 0.3-0.4 per cell; paired differences under 0.5 mean nothing. A second seed moved
no cell by more than 0.3.

**How much the filter's accuracy matters** (memo's assumptions, current bars, all ranks; a second run): error 0.7 → 33.9;
1.0 → 32.0; 1.4 → 29.5; 2.0 → 26.2; no challenger 14.9. At the memo's prior and an error of 1.0, an edge of
0.35 points means a 54% chance the challenger is truly better; 0.7 means 65%; 1.05 means 75%. The break-even
edge is +0.22 (+0.67 with mean −1.5).

**What the model leaves out.** Build time taken from the live bot; opponents adapting to a new bot only after
it has played; the T-4 upload risk; correlation between our challengers; whether a divergent design really
has a wider spread. Its percentages are directions, not forecasts.

## Appendix C: checks on the three other proposals

- **Field rates between downloads** (pooled over teams that raise 10%+; practices 1-4, then rounds 1-6):
  fold to 3-bet 58.0, 65.9, 67.6, 61.8, 67.1, 71.8, 73.3, 73.4, 73.7, 71.7 (binomial error in a 1,000-table
  file 0.49); 4-bet 15.9, 8.9, 7.7, 12.1, 8.2, 6.7, 5.8, 5.9, 6.0, 6.5 (0.29); big blind folds 68.7 ... 58.7
  (0.29; moved 2.1 per scored round); c-bet 60.7 ... 74.5 (0.39; moved 2.7). Real errors are about 1.5-2
  times binomial because hands at one table are not independent.
- **Maturity.** Score against 3-bet rate across teams: −0.54, −0.45, −0.26, −0.25 in practices 1-4; −0.15,
  +0.10, +0.08, +0.25 in rounds 1, 2, 3, 6. Tight class (VPIP 20% or less, 3-bet 8% or less): 14.7, 14.0,
  12.9, 12.6, then 11.8 in round 1. Teams raising 25%+ and 3-betting 12%+: 8.2, 8.8, 11.1, 11.8, then 11.6
  to 14.6. Same bot in two downloads, change in score against its own raise rate: practice 2 → 3, r +0.47
  (36 teams); practice 2 → round 1, r +0.90 (7); practice 3 → 4, r −0.63 (21); practice 1 → 2 and 2 → 4,
  about 0 (32, 19). Every unchanged bot lost 0.7-1.3 points per build-hour step as the field matured, which
  the yardstick subtraction already removes.
- **Fold to 3-bet, team-equal against pooled:** practice 1, 49.6 / 57.0; round 1, 59.2 / 66.7; round 3,
  68.0 / 73.1; round 5, 69.7 / 73.5; round 6, 66.8 / 71.5.

## Sources

- `strategy/DECISION_RULES.md` sections 1-5, `strategy/PLAN.md`, `notes/pre/contrarian.md` section 4,
  `notes/pre/field.md`; `notes/pre/stat_definitions.md`.
- `research/finals_prep/adaptation/REPORT.md` sections 1 and 5 with `res_q1_top.txt`, `res_q5.txt`,
  `res_q5b.txt` (changes against standing still, who changed, the fixed-bot practice shift of +0.37 ± 0.06,
  which my +0.35 matches); `research/finals_prep/redteam/REPORT.md` checks 2, 5 and 7 and Fix B.
- `data/README.md` for the hand-file map.
