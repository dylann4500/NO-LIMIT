# How much teams adapted at the regionals

2026-11-12. Data: our 6 scored and 8 practice downloads from the Bay Area regional (avalon at every table), the portal's official per-round results for all 15 Bay Area rounds (GET only, cached today), and 13 Boston files from a friend's team (p-doom maximizers). Nothing in the repo was changed or committed; nothing left this machine.

**REPORT.md was not saved.** The harness refused the write ("subagents should return findings as text, not write report files"), and I did not work around it. This message is the full report; save it as REPORT.md if you want the file. All scripts and raw output tables are in the work folder (listed at the end).

Tags: **[M]** measured, **[E]** estimated (depends on a model or threshold I chose), **[R]** reasoned (inference, not in the data).

## Headline

1. **Opponents were not fixed.** 78-90% of Bay Area teams played a detectably different bot in each scored round than in the one before, and most changes were large (a rate moving 5+ points). Boston: 75-84%. [M]
2. **For strong teams, changing was the price of staying level, not a source of gain.** A team that kept its bot lost 0.87, 0.90, 0.23, 0.23 and 0.03 points per table in the five gaps. Top-20 teams lost about 0.65 per round whether they changed or not (changed minus unchanged: -0.01 ± 0.18). [M]
3. **Tune against the last field, not a forecast.** "Same as last round" beat trend extrapolation over 23 tendencies: mean error 1.29 vs 1.72 points (field), 1.60 vs 2.00 (top 20), 5.9 vs 11.0 (single team). Exceptions: the top 20's re-raise rate and big-blind defence, which moved the same way five rounds running. [M]
4. **The clearest adaptation was inside a table, not between rounds.** The winner (2 Curry) re-raised a fresh opener 18% of the time, 43% after that seat folded to one re-raise, 62% after two, 76-83% after three or more, and 7% if the seat did not fold the first time. 27 of 122 Bay Area teams (10 of the other 19 in the top 20) show a strong response of this kind on at least one decision. Boston had five times as many re-raise learners. [M]
5. **No sign of teams targeting named opponents.** Every large "plays differently against avalon" effect I could check is explained by what avalon's seat had done earlier at that table. [M]
6. **Practice rounds were not full of experiments, but they were stale.** Only 32% of teams demonstrably played their next scored bot in the practice round; 54% certainly played something else (mostly the previous bot). A fixed bot scored 0.37 ± 0.06 higher in practice than in the scored round that followed, and about the same as in the scored round before (-0.06 ± 0.05). [M]

## Method and limits

- One pass per file replays every hand and counts, per team, 25 rates (open, re-raise, fold to re-raise, shoves, bet when checked to and fold to bet by street, exposure choices and more) and size distributions. The stack replay had 0 mismatches in the 15.9 million scored-round hands, and our points per table recompute to the official scores exactly. [M]
- Sample per team: about 1,100 tables per scored round (standard errors: open 0.2 points, fold to re-raise 0.7, flop fold 0.7, river fold 1.8) and about 54 per 1,000-table practice round (1.0, 3.3, 3.2, 7.8). [M]
- Every team is seen only with avalon at the table. Two teams that never changed (Cmupc, Fish) show no drift between R1 and R6 (mean z² 1.2-1.3 against a null of 1.3), so a changing field does not by itself trigger the change detector. [M]
- Scores are the portal's official averages (standard error 0.15 scored, 0.65 for a 1,000-table practice). Boston has no official scores: team scores there come from the friend's tables (about 370 per team per round, standard error about 1.0), so only group means are meaningful. [M]
- Boston file order (4 build practices, 6 scored, 3 practice files between scored rounds) is inferred from which files share the most unchanged teams and from file sizes; it matches a monotone rise in the field's re-raise rate. [E]

## 1. Between rounds

Classes per team and pair of rounds:
- **Unchanged:** mean z² over the 25 rates under 5 and no size distribution shifted by 15% of its mass.
- **Clear jump:** at least one rate moved 5+ points with |z| ≥ 5, or a size distribution moved 30%.
- **Rewrite-scale:** a jump with root-mean-square rate change of 10+ points or 8+ rates moving 5+ points.
- **Small tweak:** detectable but below that.

Splitting each file into odd and even tables flags 1 of 756 team-rounds as changed. [M]

| Gap (126 teams) | Unchanged | Small tweak | Clear jump | Rewrite-scale | Changed | Median RMS change of changers |
|---|---|---|---|---|---|---|
| R1→R2 | 14 | 10 | 39 | 63 | 89% | 10.2 points |
| R2→R3 | 13 | 9 | 53 | 51 | 90% | 8.8 |
| R3→R4 | 25 | 3 | 56 | 42 | 80% | 7.9 |
| R4→R5 | 28 | 7 | 45 | 46 | 78% | 7.0 |
| R5→R6 | 27 | 3 | 52 | 44 | 79% | 5.9 |

63 of 126 teams changed in all five gaps, 35 in four, 2 never. [M]

| Final rank | Team-gaps | Unchanged | Tweak | Jump | Rewrite-scale | Mean RMS change |
|---|---|---|---|---|---|---|
| 1-5 | 25 | 24% | 12% | 52% | 12% | 4.1 points |
| 6-20 | 70 | 13% | 3% | 67% | 17% | 5.4 |
| 21-60 | 200 | 10% | 6% | 44% | 40% | 8.2 |
| 61-100 | 200 | 18% | 6% | 38% | 38% | 8.9 |
| 101-127 | 135 | 27% | 3% | 15% | 56% | 14.8 |

Changers were everywhere. The top changed as often as the middle but by half as much; the bottom either stood still or rewrote. [M]

**Did changes help?** Official score change to the next round, 630 team-gaps. "Adjusted" removes the pull toward the mean (Δ = 2.38 - 0.19 × previous score).

| Class | n | Mean Δ score | Adjusted | SD of Δ | Improved | Gained 5+ places | Lost 5+ places |
|---|---|---|---|---|---|---|---|
| Unchanged | 107 | -0.34 | -0.53 ± 0.08 | 0.54 | 25% | 6% | 36% |
| Small tweak | 32 | -0.91 | -0.49 ± 0.17 | 0.91 | 19% | 3% | 50% |
| Clear jump | 245 | -0.23 | +0.05 ± 0.07 | 1.05 | 44% | 27% | 36% |
| Rewrite-scale | 246 | +0.50 | +0.24 ± 0.20 | 3.41 | 57% | 44% | 34% |

- Size of behaviour change against score change: r = +0.11 (-0.02 adjusted); against the absolute score change: r = +0.70. Bigger changes meant bigger swings, not better results on average. [M]
- Gains of 1.5+ points: 92, of which 81 were rewrite-scale and 3 came from a top-20 team. Losses of 1.5+: 94, of which 50 were rewrite-scale and 25 came from a top-20 team. [M]

Mean Δ score by standing in the round just played (n in brackets):

| Rank in round n | Unchanged | Tweak | Jump | Rewrite-scale | Changed minus unchanged |
|---|---|---|---|---|---|
| 1-20 | -0.67 ± 0.12 (18) | -0.90 ± 0.41 (7) | -0.65 ± 0.16 (53) | -0.68 ± 0.39 (17) | -0.01 ± 0.18 |
| 21-60 | -0.63 ± 0.09 (22) | -1.09 ± 0.26 (14) | -0.21 ± 0.10 (94) | -0.51 ± 0.30 (70) | +0.23 ± 0.16 |
| 61-127 | -0.16 ± 0.06 (67) | -0.69 ± 0.24 (11) | -0.02 ± 0.11 (98) | +1.07 ± 0.30 (159) | +0.76 ± 0.20 |

- No unchanged top-20 team improved (0 of 18). The top 20's mean score fell from 19.25 in R1 to 17.43 in R6 while the field's spread narrowed (SD 4.84 → 3.94): weak teams repaired themselves and the points the leaders took from them went away. [M]
- The R1 leaders fell furthest: TeamBallHog 22.4 → 15.5, Team 72 22.2 → 17.4, WAYS-ER TEAM 21.4 → 15.3, AZ 21.2 → 17.3, sandylikesfrogs 20.7 → 16.9. 2 Curry (20.4 → 20.1) and Lemonade (19.8 → 19.6) held. [M]
- Three of those five fallers have strong in-table exploits of folders (section 3). [M] The likely reading: bots built to punish weak play lose their income as weak play disappears. [R]
- Rank correlation between consecutive rounds: 0.84, 0.88, 0.91, 0.86, 0.91 (official scores, 127 teams). [M]

## 2. Direction of the field

Team-equal means, percent. "Field" = 126 active teams; "Top 20" = the other 19 teams in the final top 20.

| Tendency | Group | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|---|
| Open, first in | Field | 30.4 | 32.7 | 34.3 | 34.5 | 34.6 | 34.5 |
| | Top 20 | 39.8 | 39.1 | 40.1 | 40.1 | 41.2 | 39.4 |
| Re-raise | Field | 8.3 | 7.7 | 8.8 | 10.2 | 10.3 | 13.0 |
| | Top 20 | 9.8 | 12.7 | 13.1 | 15.8 | 18.7 | 23.7 |
| Fold to re-raise | Field | 59.2 | 64.0 | 68.0 | 69.1 | 69.7 | 66.8 |
| | Top 20 | 63.7 | 67.1 | 71.4 | 71.1 | 71.4 | 68.4 |
| 4-bet | Top 20 | 7.6 | 8.2 | 5.8 | 5.7 | 5.7 | 6.9 |
| Shove, per hand dealt | Field | 3.3 | 3.7 | 4.5 | 5.3 | 4.6 | 5.8 |
| | Top 20 | 5.4 | 5.9 | 5.5 | 6.0 | 6.0 | 6.4 |
| Big blind folds to an open | Field | 66.9 | 66.4 | 64.8 | 63.1 | 59.1 | 57.8 |
| | Top 20 | 58.5 | 58.9 | 54.6 | 51.3 | 49.6 | 40.2 |
| Bet when checked to: flop | Field | 52.0 | 59.3 | 63.1 | 64.0 | 67.5 | 66.0 |
| | Top 20 | 66.9 | 67.3 | 69.1 | 71.3 | 71.8 | 72.3 |
| turn | Field | 43.0 | 48.6 | 49.6 | 51.1 | 53.4 | 53.1 |
| | Top 20 | 51.2 | 53.1 | 57.4 | 62.3 | 61.2 | 64.0 |
| river | Field | 40.1 | 44.8 | 43.6 | 44.7 | 46.0 | 46.5 |
| | Top 20 | 45.1 | 46.7 | 47.5 | 51.2 | 49.8 | 52.3 |
| Fold to a bet: flop | Field | 48.3 | 48.4 | 52.3 | 52.3 | 51.0 | 53.3 |
| | Top 20 | 51.2 | 53.4 | 56.9 | 57.8 | 54.7 | 58.0 |
| turn | Field | 40.1 | 40.1 | 45.5 | 47.0 | 45.6 | 46.1 |
| | Top 20 | 46.3 | 48.1 | 53.8 | 53.7 | 51.7 | 51.1 |
| river | Field | 44.7 | 46.2 | 51.1 | 52.2 | 48.1 | 49.6 |
| | Top 20 | 53.1 | 54.1 | 60.0 | 56.9 | 54.8 | 53.5 |
| Expose the lower kept card (showdowns) | Field | 64.1 | 63.5 | 64.0 | 64.2 | 64.0 | 62.5 |
| | Top 20 | 61.2 | 58.5 | 57.5 | 55.9 | 56.8 | 56.2 |
| Exposed card ten or higher | Field | 59.7 | 61.1 | 62.8 | 61.9 | 61.4 | 61.7 |

The full 23-tendency table is in `res_q2.txt`. [M]

**Was it a best response?** Partly, and one-sided.
- **Aggressors responded.** The field folded to 59-64% of re-raises in R1-R2, and re-raises rose every round among the top 20 (9.8% → 23.7%). Folds to bets rose through R4 and bets when checked to rose with them. [M]
- **Defenders lagged.** Fold to re-raise went up for four rounds while re-raises doubled, and only dipped in R6 (-3 points; 4-bets +1.2). Folds to turn and river bets peaked in R3-R4 and came down 2-6 points after. [M]
- **The one prompt counter was the big blind.** Its fold rate to opens fell every round (top 20: 58.5% → 40.2%). [M]
- **Team by team the response is real but small.** Controlling for the team's own level, what a team experienced in round n predicts its change:
  - opponents folding to my flop bets → I bet more: β = +0.15, t = 3.6, n = 604 (top 20: +0.28, t = 2.7)
  - same on the turn: β = +0.18, t = 4.3
  - my shoves being called → I shove less: β = -0.15, t = -3.8
  - being re-raised more → I fold less: β = -0.14, t = -2.5
  - big blinds folding → top-20 teams open more: β = +0.42, t = 3.4
  - for comparison, plain convergence (own level against own change) is r = -0.39 to -0.49. [M]
- **Variant choices barely moved** in the field (lower-card exposure 64% throughout); the top 20 drifted 5 points toward showing the higher card. [M]

**Is the next round predictable?** Mean absolute forecast error for R3-R6, in points.

| Forecast of round n+1 | Field mean | Top-20 mean | A single team |
|---|---|---|---|
| Same as round n | 1.29 | 1.60 | 5.93 |
| Trend from rounds n-1 and n | 1.72 | 2.00 | 10.96 |
| Half the trend | 1.27 | 1.68 | 8.19 |

- The trend wins 75 of 184 (tendency, group, round) forecasts. Consecutive field moves have the same sign 56 of 92 times (correlation of consecutive changes +0.26 field, +0.14 top 20): a little momentum, too little to extrapolate in full. [M]
- Where the trend did win for the top 20: re-raise rate (error 1.80 vs 2.77), big-blind fold (3.81 vs 4.70), VPIP and PFR. These moved the same way in every round. [M]
- Boston gives the same answer: 1.25 vs 1.55 (field), 1.85 vs 2.48 (top 20), 5.78 vs 10.28 (team). [M]

## 3. Opponent-specific play

**Against avalon versus anyone else, same situation.** Mantel-Haenszel within strata (street, position or role, own stack, pot or bet size bucket, players left, the bettor's exposed card class, opener's stack, half of table); six decisions; 734 team-decision tests pooled over six rounds.
- The whole field treats avalon a little differently: folds 2.6 points more to its re-raises, bets 2.7 points more when it checks, folds 2.1 points less to its bets. A common shift like this is a property of avalon's lines that my buckets miss, so each team is tested against the field's median, not against zero. [M, E]
- 200 tests pass a 1% false-discovery threshold on that basis and 196 keep their sign between odd and even rounds, but only 15 are 5+ points from the field. Odd-round and even-round team effects correlate 0.95 for re-raising and 0.54-0.74 for the rest (SD across teams 1.1-2.3 points). [M]

| Team (final rank) | Decision | Against avalon | Matched, against others | Effect | First half of table | Second half |
|---|---|---|---|---|---|---|
| 2 Curry (1) | re-raise its open | 46.0% | 34.9% | +11.2 | +8.7 | +16.9 |
| stanford deviants (11) | re-raise its open | 37.1% | 29.1% | +8.4 | +6.8 | +12.1 |
| Team 123 (7), from R3 | re-raise its open | 35.2% | 29.9% | +5.7 | +3.6 | +11.1 |
| stanford deviants (11) | open into its big blind | 50.0% | 56.4% | -6.4 | -4.9 | -7.6 |
| Maniac (13) | fold to its bet | 45.3% | 54.9% | -9.1 | -8.6 | -10.6 |
| Gavilan (14) | fold to its bet | 58.5% | 66.7% | -7.9 | -7.9 | -7.9 |
| one in a krillion (18) | bet when it checks | 87.8% | 80.1% | +7.7 | +7.0 | +9.3 |
| WAYS-ER TEAM (15), AZ (3), TS (26), Po Stitch (30) | fold to its re-raise | 65-84% | 56-76% | +8 | +3 to +6 | +9 to +12 |

**These are seat effects, not name effects.** A targeted pass over 2 Curry's 138,000 re-raise decisions against a single opener (both stacks 25bb+, no callers):

| What the opener did when re-raised earlier at this table | 2 Curry vs avalon | 2 Curry vs others | stanford deviants vs others | Team 123 (R3-R6) vs others |
|---|---|---|---|---|
| Never re-raised yet | 16.7% (8,560) | 18.3% (42,726) | 18.4% | 30.0% |
| Faced 1, did not fold | 9.9% (776) | 7.3% (12,397) | 9.9% | 23.1% |
| Faced 1, folded | 40.9% (3,835) | 43.2% (13,422) | 29.4% | 42.7% |
| Faced 2, folded 2 | 61.6% (2,031) | 62.3% (6,116) | 38.0% | 50.4% |
| Faced 2, folded 0 | 14.1% (64) | 7.1% (3,306) | 8.3% | 9.9% |
| Faced 3+, folded 80%+ | 82.6% (4,308) | 75.7% (13,683) | 51.7% | 66.8% |
| Faced 3+, folded under 50% | 12.1% (116) | 11.6% (5,767) | 13.8% | 15.4% |

- Given the same history, avalon and everyone else get the same treatment. Avalon was re-raised more because it folded to 82-87% of re-raises, and 2 Curry's bot noticed after one fold. [M]
- Team 123 had no such rule in R1-R2 (4% whatever the history), added it before R3, and went from 12.8 to 17.8 that round in a rewrite-scale change. Other things changed too, so the gain is not attributable to the rule alone. [M]

**Seat-level response tests across all teams.** Logistic regression per team and round: the action against a seat, on that seat's in-table rate so far (deviation from its team's norm, shrunk). Controls: the seat's team norm, the rest of the table's history as a placebo, blind level, players left, both stacks, who covers, the situation. Effects are per +10 points of deviation.
- The field's median effect is not zero on two tests (bet when checked to -0.7, fold to bet -1.7). I read that as leftover confounding, so a team is flagged only if it is beyond the field median. [E]
- The placebo is quiet: 1-4% of team-rounds beyond |z| = 3 (10% for steals). [M]
- Avalon is a positive control. Its bots tracked raise frequency, fold-to-bet and bet frequency per seat, and the test finds all three (z = 29-36, 16-75 and 6-14) and nothing on the big-blind statistic it did not track (z = 0-2). [M]

| Response | Teams flagged (of 122-123) | Strong (|z| ≥ 10 and 3+ points beyond the field) | Largest |
|---|---|---|---|
| Re-raise openers who have folded to re-raises | 7 | 3 | 2 Curry +31.9, Team 123 +15.7, stanford deviants +15.3 |
| Re-raise openers who open often | 17 | 2 | AZ +6.2, Team 123 +3.4 |
| Open SB/BTN when the big blind has been folding | 16 | 3 | stanford deviants +3.5, Inabot +3.2, prior_updating... +3.2 (Team 72 +3.0, TeamBallHog +2.9 flagged) |
| Bet when checked to against seats that fold to bets | 27 | 20 | TeamBallHog +15.1, Team 72 +12.2, stanford deviants +10.4 |
| Fold less to seats that bet often | 20 | 7 | AZ -6.5, Maniac -6.5, Chikerbot -6.0, Gavilan -5.6, TeamBallHog -5.3 |
| Call shoves from seats that shove often | 28 | 4 | Prath +5.9, all vibes +5.8, Clippers Championship +5.6 |

- Strong on at least one: 27 teams. By final rank: 3 of the top 5 (2 Curry, AZ, Team 72), 7 of 14 in places 6-20, 10 of 40 in 21-60, 7 of 64 below. Any flag: 58 teams, including 18 of the 19 other top-20 teams. [M, E]
- Raw cross-tabs agree with the regressions. [M]
  - Bet when checked to, heads-up, against a seat that has folded to under 34% / 34-67% / over 67% of the bets it faced at this table: TeamBallHog 57 / 85 / 94%, Team 72 53 / 72 / 95%, stanford deviants 42 / 58 / 79%. 2 Curry (68 / 70 / 72%) and Lemonade (62 / 66 / 68%) are flat.
  - Fold to a bet from a seat that has bet under 40% / 40-70% / over 70% of the time: AZ 72 / 60 / 44%, Maniac 69 / 59 / 46%.
- These rules were in the bots from round 1 and barely spread during the night. Teams with a large per-round response: re-raise-on-folds 2, 2, 3, 3, 4, 4; bet-against-folders 12, 16, 18, 16, 15, 16. [M]
- After controlling the seat's history, a "this seat is avalon" term is still 4+ points from the field for 1 to 18 teams depending on the decision (for example one in a krillion opening 12 points more into avalon's big blind in every round). I cannot tell whether that is another statistic they tracked, something in avalon's sizes, or recognition. The effects are steady across rounds in which avalon's bot changed a lot, which points to a generic in-table statistic. [M for the residual, R for the reading]

## 4. Within a table

Hand number and blind level are almost the same variable (20 hands per level), so "first third against last third, controlling blind level" has little overlap. Three designs:
- (a) last third against first third within players-left and own-stack-in-bb buckets, no level control;
- (b) adjacent thirds within the same blind level;
- (c) second half against first half of each 20-hand level: level, stage, players left and stack bucket fixed, ten more hands of experience.

| Tendency | (a) field median drift | (b) field median | (c) field median | Teams in (c) with 1.5+ points and |z| ≥ 5 |
|---|---|---|---|---|
| Open | +3.2 | +0.2 | +0.3 | 9 |
| Re-raise | +0.7 | +0.1 | 0.0 | 3 |
| Fold to re-raise | (almost no overlap) | -0.9 | +0.4 | 5 |
| Bet when checked to, flop | (no overlap) | -0.2 | +0.8 | 4 |
| Fold to flop bet | (almost no overlap) | -1.4 | -0.3 | 1 |

- For most teams there is no drift once the state is fixed: the field median is within 1 point on every tendency in (c) and within about 2 in (b). [M]
- Teams that do drift within a blind level [M]:
  - sandylikesfrogs: opens +7.7 points in the second half of every level, re-raises +3.0, folds to re-raises +6.4, in all six rounds
  - prior_updating...: opens +4.4, folds to re-raises +4.2
  - 2 Curry (re-raises +2.6) and stanford deviants (re-raises +2.7)
  - Team 72: opens +2.4; in design (b) folds to re-raises 5.7 points less as the table goes on
  - Litmus, one in a krillion, Spartan Mathematics: flop bets +4 to +5
- In design (a), re-raising late in a table is far above the field for AZ (+24.6), 2 Curry (+21.6), Lemonade (+11.7), sandylikesfrogs (+9.0) and TeamBallHog (+8.9). For 2 Curry that is the seat learning above. For AZ and Lemonade it mostly disappears inside a blind level (+1.4, +1.0), so it looks like a rule keyed to stage, not learning. [M for the numbers, R for the reading]
- The section-3 tests are the better evidence of in-table learning, because they condition on what was observed, not on the clock. [R]

## 5. Practice rounds against scored rounds

Each practice round is compared with the scored round before and after, per team, on the same 25 rates. With 54 tables per team only clear differences are detectable: "match" = mean z² under 3.5, "differ" = over 6. Among teams whose two scored bots were identical, the median practice-to-scored mean z² is 1.4-1.9, so the test is calibrated. [M]

| Practice → scored | Teams | Same bot in all three | New bot already in practice | Changed after the practice | Differs from both | Practice-only experiment | Unclear | Practice bot = next scored bot | Certainly different |
|---|---|---|---|---|---|---|---|---|---|
| P6 → R3 | 124 | 10 | 19 | 40 | 33 | 2 | 20 | 23% | 60% |
| P7 → R4 | 124 | 15 | 22 | 29 | 29 | 7 | 22 | 30% | 52% |
| P8 → R5 | 122 | 20 | 15 | 45 | 22 | 5 | 15 | 29% | 59% |
| P9 → R6 | 123 | 21 | 34 | 30 | 21 | 3 | 14 | 45% | 44% |
| All | 493 | 66 | 90 | 144 | 105 | 17 | 71 | 32% | 54% |

- The top 20 look the same as everyone else: 32% same as next, 54% certainly different. [M]
- The commonest case (29%) is a team still on its previous scored bot in the practice round and uploading in the last ten minutes. 2 Curry did that twice, Team 72 four times. [M]
- Practice-only experiments were rare: 17 of 493 (3%). Two were top-20 teams (AZ in P8; Always Folds in P9, scoring 6.3 against 17.2 and 16.6 either side). "Differs from both" (21%) is an intermediate version or two changes in one window. [M]
- Field tendencies in a practice round sit between the two scored rounds: where the field moved 1+ point, the practice round had made about half the move in the median, with wide scatter because practice samples are small. [M]

**How biased is a practice score?** Teams that demonstrably had the same bot in both rounds, official scores:

| Comparison | Teams | Practice minus scored | By round (P6, P7, P8, P9) |
|---|---|---|---|
| Practice − following scored round | 156 | +0.37 ± 0.06 | +0.66, +0.49, +0.04, +0.34 |
| Practice − previous scored round | 210 | -0.06 ± 0.05 | -0.47, +0.21, -0.14, +0.20 |

- Our own same-bot pairs agree within their noise: P6−R3 +0.70, P7−R4 +0.80, P9−R6 -0.55 (each ±0.66), and P3−R1 +0.92 ± 0.27. [M]
- The shift is a level shift, not a style effect. Its spread across same-bot teams (0.70) is no wider than sampling noise (0.67), and it does not correlate with a team's open, re-raise, shove, bet or fold rates (|r| ≤ 0.15, n = 156) or its strength (r = +0.09). [M]
- So the playbook's comparison (challenger's practice score against the live bot's last scored result) is unbiased on average, with a round-to-round wobble of about ±0.3 that takes the standard error from 0.65 to about 0.7. [E]
- Read as a forecast of the next scored round, a practice score is about 0.4 too high, and so is the live bot's last scored result (section 1). [E]
- Across all teams the practice score still tracks the next scored score: r = 0.85-0.93 for P5-P9. The scatter beyond sampling noise (1.5-2.2 points) is the teams' own bot changes. [M]

## 6. Boston

231 entries, 191 teams seen in all six scored files, about 370 tables per team per round, variant with a sealed auction for the flop. One viewpoint, no official scores.

- **Between rounds.** 75-84% changed each gap (unchanged / tweak / jump / rewrite-scale of 191: 42/5/65/79, 31/10/80/70, 46/8/81/56, 48/7/75/61, 48/5/83/55). The smaller sample hides more small changes than at Bay Area. Score changes by class match Bay Area: unchanged -0.46 ± 0.09 adjusted, jump +0.06 ± 0.09, rewrite-scale +0.28 ± 0.19 with SD 3.7. Size of change against absolute score change r = +0.55, against signed change +0.01. [M; score noise about 1.4 per team-gap]
- **Direction.** The same push toward aggression: field re-raise 8.6 → 14.4, flop bet when checked to 49.8 → 63.4, big-blind fold 67.0 → 57.4, large auction bids 12.4% → 21.0% of auctions. [M]
- **The defence came sooner at the top.** The estimated top 20 re-raised 14.3 → 27.0 → 24.5% (R1, R5, R6); their fold to re-raise fell 75.0 → 57.5 → 60.4% and 4-bets rose 8.9 → 23.4 → 18.3%. At Boston the defence arrived by round 2-3; at Bay Area not until round 6. [M; the top-20 list is estimated from noisy scores]
- **Forecasts.** Same-as-last beats the trend (numbers in section 2). [M]
- **Against the viewpoint team.** 17 team-decision pairs are 5+ points from the field after correction. The largest belong to teams that also show strong seat learning (Du-o opens 8.3 points less into p-doom's big blind; big little sharks re-raises it 6.5 points more). The Bay Area explanation fits; there is no second viewpoint to test recognition. [M, R]
- **Seat-level learning was much more common.** 15 teams have a strong re-raise-on-folds response (Bay Area 3); teams with a large per-round response were 10, 9, 11, 18, 17, 16 of 192 (Bay Area 2-4 of 122). 34 teams have a strong response of some kind, including 12 of the estimated top 20 and all of the top 4. Only one shows the shove-calling response. [M]
- **Within a table.** Too little data per team for the within-level design; one team (big little sharks) stands out, consistent with its seat learning. [M]
- **Practice against scored.** Three practice files sit between scored rounds. Same bot as the next scored round in 31%, 42% and 40% of teams; still on the previous bot in 39%, 40% and 29%; practice-only experiments 1, 2 and 4 of 191. Fixed-bot shift, practice minus next scored: +0.42 ± 0.16 on the 10,000-table practice (n = 59); +0.24 ± 0.32 and -0.30 ± 0.33 on the 1,000-table ones. [M]
- **What Boston cannot show.** Score effects per team, a like-for-like variant-choice comparison (auction bids are visible only as chips spent), and anything about recognition of named teams.

## 7. How sophisticated were the best teams, and what to expect from 20 finalists

What the data shows:
- The two teams that stayed on top did opposite things between rounds. 2 Curry changed in every gap but by small amounts (RMS 2-5 points, never rewrite-scale). Lemonade rewrote once (R2→R3, +1.3), then left its bot alone for three rounds and lost 0.1, 0.5 and 0.5. Neither chased the field. [M]
- The winner's adaptation was built before round 1 and ran inside each table: it re-raised a seat after one observed fold and stopped after one observed call. [M]
- The other strong round-1 bots relied on in-table exploitation of folders and lost 4-7 points over the night. [M]
- Round-to-round responses to what a team experienced exist but are weak (β around 0.15); most between-round movement is convergence toward the field and repair of obvious faults. [M]
- Nobody demonstrably played named opponents, and almost nobody used practice rounds to experiment or to hide. [M]
- Aggression rose for six rounds; the defence to it came late at Bay Area and early at Boston. [M]

What I infer for Sunday:
- Every finalist will change its bot in every window. A team profile built from the last round will be off by about 6 points per rate for the average team (the regional team-level error), less for teams that only tune. [E from the regional, R for the transfer]
- At least half the field will learn seats in-table (10 of 19 and 12 of 20 in the two regional top 20s), and after everyone has read a regional's data the 2 Curry rule is the obvious thing to copy. Expect to be re-raised and bet into within one or two folds at each table. [R]
- The defence will not lag four rounds this time. Boston's top teams were folding to 58% of re-raises and 4-betting 23% by round 5; finalists start from there. A plan built on "they fold to re-raises" has a short life. [R]
- With 19 opponents instead of 147, one team's change is 5% of our field instead of 0.7%. The practice-to-scored shift will depend more on who changed, and its variance will exceed the ±0.3 measured here by an amount this data cannot give. [R]
- Recognition of named teams becomes feasible with 19 opponents seen constantly, and we plan it ourselves. The regionals give no evidence either way. [R]
- No weak tail means the regional's main source of points (teams that fold too much) is absent. Scores will sit near 12.5 with small gaps, so the ±0.7 noise of a practice comparison is large relative to the differences being judged. [R]

## What this means for the plan

Assumptions the data contradicts:
1. **Opponents as fixed.** 80-90% change every gap. Rebuild profiles and the cloned field from the newest round only, shrunk toward the field; never extrapolate a single team's trend (error 11.0 against 5.9). [M]
2. **"Clones don't adapt" is a bigger hole than the prompt pack says.** The winner's edge against us ran through in-table seat learning, which a frequency clone cannot reproduce. Give at least the top clones a seat-learning rule (re-raise after a fold, bet into seats that fold, call down seats that bet), or the cloned field will keep rating a bot that folds to 85% of re-raises as safe. [R from M]
3. **Our tells are read within one or two hands.** Any rate of ours far from the field (fold to re-raise 85%, fold to bets 70%+) is found by these bots at every table. Early actions at a table set how a learner treats us for the rest of it: against 2 Curry's rule, not folding to the first re-raise cut later re-raises from 18% to 7%; folding raised them to 43%. Worth a candidate change: defend the first re-raise and the first big blind at each table wider than later ones. [M for the rule, R for the counter]
4. **A practice score as a forecast.** It overstates the next scored round by about 0.4 for a fixed bot, and more than half the field will have changed by then. Keep the playbook's comparison (unbiased on average) but use ±0.7 as its standard error, not ±0.6. [M, E]
5. **Small changes to the live bot keep us level.** Teams that only tweaked did no better than teams that stood still (-0.49 against -0.53 adjusted), and standing still cost up to 0.9 a round early on. One evidence-backed fix per window is a floor, not a way up. [M]
6. **Rewrites as the way up for a strong team.** 81 of 92 gains of 1.5+ were rewrite-scale, but only 3 came from a top-20 team, and top-20 rewrites averaged -0.68 ± 0.39 with 4 of 17 improving. The hail-mary slot is for when we are well outside the top 3, as the playbook says; it is not a routine tool. [M]

Safe to ignore:
- Trend forecasts of the field, except half the last move on a tendency the leaders have moved the same way two rounds running (re-raise rate, big-blind defence). [M]
- Opponents experimenting or sandbagging in practice rounds (3%). [M]
- A style-dependent practice bias at regional field sizes (none detectable); revisit in a 20-team field. [M, R]
- Generic first-third-to-last-third drift in a profile. Store how a team responds to what a seat has done, which is where the real effects are; fewer than 10 teams drift on the clock. [M]
- Named-team targeting as something the regional field did. Not as something finalists might do. [M, R]

## Files

All under `/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/strategy/adaptation/`:
- **Extraction:** `extract.py` (rates and sizes), `extract2.py` (adds half-of-level and half-of-table strata), `extract3.py` (adds the faced seat's stack to the seat-history records), `q3c_extract.py` (named teams' re-raise decisions). Outputs in `out/`, `out2/`, `out3b/`, `out3/`, about 10 GB in total and safe to delete.
- **Analyses:** `q1.py`, `q1b.py` (changes and scores), `q2.py` (direction, forecasts), `q3a.py` (against avalon), `q3b2.py`, `q3b2_report.py`, `q3b3.py` (seat history), `q4.py`, `q4b.py` (within table), `q5.py` (practice), `boston.py`, `boston_q3a.py`. Run with `starter-kit/.venv/bin/python -I` from that folder (it has numpy; the extractors run on plain `python3 -I`).
- **Full output tables:** `res_q1.txt`, `res_q1_top.txt`, `res_q2.txt`, `res_q3a.txt`, `res_q3a_late.txt`, `res_q3c.txt`, `res_q3b2.txt`, `res_q3b3.txt`, `res_crosstab.txt`, `res_q4.txt`, `res_q5.txt`, `res_q5b.txt`, `res_boston.txt`, `res_boston_q3a.txt`, `res_boston_q3b2.txt`, `res_boston_q4.txt`.
- **Portal results cache:** `api/` (standings, tournament list, results for all 15 Bay Area rounds including practice 5, which was never downloaded as hands).