# Is the first-1,000-table file a fair sample? (pre-event note, for `analyst`, `scout`, `tester`)

Drafted Saturday 14 November from the regional's raw hand files and official results. Notes only, no code.
**Grades** as `strategy/EVIDENCE_TABLE.md`: **A** measured fact; **C** candidate; **arith.** exact arithmetic.

## The answer

1. **A fair sample, and a small one.** The file is the round's first 1,000 iterations in order, byte for byte the head of the full file. Seats, fillers, table length and field rates match the rest of the round within noise (A, 7 rounds).
2. **Our score from it is good to ±1.3 points (95%).** It missed the full round by +0.40 on average and by +2.0 once (round 5: 3.1 standard errors, with our bot's own rates unchanged, so luck) (A).
3. **A small early lift cannot be ruled out**: first half of a scored round minus second half, +0.31 ± 0.12 (C). No correction: it is under half a standard error at 1,000 tables.
4. **Take scores from `results.json`, never from the hand file.** It has every team over every table. The hand file shows other teams only at our tables, 0.6-0.9 below their official scores (A; arith.).
5. **Fetch 5,000 tables first, not 1,000** (C: the download is unmeasured). Our score's error falls from 0.66 to 0.30, rate noise 2.2 times, and it reads in 5 seconds.

## 1. How the tables are chosen

By iteration number, not by finishing time: iterations 0 to 1,000, identical to the first 1,006-1,026 records of the full file in all six rounds that have both (A). So short tables are not over-represented: hands per table differ by -0.5 to +1.6 between the first block and the rest (z -0.6 to +2.2), and seat counts per team and filler shares match (appendix).

**One trap**: 0.6-0.9% of records (2.3% in practice 4, with three filler seats) are tables where a filler seat plays **a copy of our bot**: our entry id in a seat flagged filler. They are not in the official score (A). With four filler seats on Sunday that may be one extra table for every five iterations (C).

## 2. Scores against sampling noise

- **Our gap, first 1,000 minus full round**: +0.41, +0.46, -1.12, +0.33, +0.29, +2.00, +0.42 (practice 4, rounds 1-6); expected SE 0.54-0.67; z +0.8, +0.7, -1.7, +0.5, +0.5, +3.1, +0.7. Mean +0.40 ± 0.24; without round 5, +0.13 ± 0.26 (A).
- **Block 0 is like any block**: of 133 blocks of 1,000 iterations, 6 lie beyond 2 standard errors (6.1 expected) and 1 beyond 3: round 5's block 0. In it we won 26.6% of tables against 22.9%, with all 20 of our own rates within 2.4 block-spreads (A).
- **Other teams at our tables** (874 team-rounds, about 56 tables each): z has mean -0.03 and spread 0.99; no pattern by final rank or score level, and a team's gap does not repeat between rounds (correlations -0.08 to +0.04). No kind of bot is favoured (A).
- **Their scores in our file are shifted**: at our tables they average (100 - our score)/7, measured 0.58-0.90 below official in scored rounds and 0.46 above when we scored 9.2 (A; arith.).

## 3. Field rates

First block against each later block, 18 rates of `stat_definitions.md`, 7 rounds: 126 z-scores with mean -0.09 and spread 1.04; the largest (3.5) is a difference of 0.5 points (A). A 1,000-table team-equal rate carries 0.1-0.8 points of noise.

**Two rates fail team-equal at 1,000 tables**: fold to a 4-bet (26 teams reach 20 chances: 51% against 31% in the full file) and bettor folds to a flop raise (47 teams: 53% against 42%). Only heavy re-raisers qualify (A). Report them pooled with n.

## 4. Which N to fetch

| N | SE of our score | Two rounds of N compared | One opponent at our tables (20 teams) | File | Read / full pass |
|---|---|---|---|---|---|
| 1,000 | 0.66 | 0.93 | 1.09 | 13.5 MB | 1 s / 3 s |
| 2,000 | 0.47 | 0.66 | 0.77 | 27 MB | 2 s / 6 s |
| 3,000 | 0.38 | 0.54 | 0.63 | 40 MB | 3 s / 9 s |
| 5,000 | 0.30 | 0.42 | 0.49 | 67 MB | 5 s / 15 s |
| 20,000 | 0.15 | 0.21 | 0.24 | 270 MB | 20 s / 65 s |

Spread per table 20.5-21.7 and times are measured (A); the rest arith. **5,000**: parsing is no constraint in 12 minutes, and 67 MB is 7 seconds at 10 MB a second, over a minute at 1 MB. Each Sunday opponent is then seen at about 1,840 of our tables instead of 370. A practice round of 1,000 tables is one sample of 1,000 whatever N is: against it, even the full scored round only reaches 0.68.

## 5. Wording to adopt (not applied by this note)

**`strategy/DECISION_RULES.md`**, after "Practice SE is at least 0.7":

> **Scores come from `results.json`, never from the hand file**: it covers every table and every team (`margin_of_error` is 1.96 standard errors). The first-N hand file is the round's first N iterations: fair but small. At the regional its score for us missed the full round by +0.4 on average and 2.0 once, and it shows other teams only at our tables, about (100 - our score)/7. Use it for rates and for where points were won and lost.

**`.claude/agents/analyst.md`**, replacing the Noise bullet's first sentence:

> **Noise:** SE = 21/√tables: 0.66 at 1,000, 0.47 at 2,000, 0.30 at 5,000, 0.15 at 20,000; the 95% range is twice that. Take every score from `results.json`. Before scoring us from a hand file, drop tables where our entry id sits in a seat flagged filler. Take the table count from the file, not its name. A team-equal rate needs most teams at 20+ chances: otherwise report it pooled with its n.

**`scripts/portal_watch.py`**, one line: `SMALL_Q = "tables=5000&subset=first-1000"`. The saved name stays `hands-first-1000.jsonl.gz`; re-run the script checks (one names `?tables=1000`).

## Not verified

- The portal's time to send 5,000 tables, and its answer when N exceeds the round's tables (no portal calls made).
- How many tables Sunday's practice rounds have.
- The filler-copy share with four filler seats.
- Any cause for the first-half lift.

## Appendix

**Method.** One streaming pass per file (full files of scored rounds 1-6 and practice 4; six first-1000 files), keeping per table: iteration, table id, seats, fillers, hands, final points per seat, and per seat the counters behind 18 rates of `stat_definitions.md`. Our seat is the header's `you` id in a seat not flagged filler; the recomputed score equals the official one in all seven rounds. Round 6 has no first-1000 file: its iterations 0-1,000 were used. Gap SE = spread × √(1/n - 1/N). Rates: blocks of 1,000 iterations, team-equal over other teams with PFR 3%+ and 20+ chances; z = (block 0 - mean of later blocks) / their spread. The scripts were temporary and are deleted.

**Selection checks, first block against the rest** (A):

| Check | Result |
|---|---|
| Full file | Sorted by iteration; 20,000 iterations (12,500 in practice 4), 16 tables each, we sit at one |
| Teams seated | Seat counts per team: chi-square 90-143 on 123-125 degrees of freedom; 124-126 teams in both |
| Fillers | A filler seat at 6.2-7.5% of tables in the first block, 6.1-6.6% after |
| Hands per table | 126-136 in both; z -0.6 to +2.2 |
| Players at hand 41, collisions by hand 40 | z within ±1.6 except one +2.6 (practice 4) |
| Consecutive tables | Lag-1 correlation of our points within ±0.011 (SE 0.007) |

**Our score, first block against the full round** (A):

| Round (bot) | First 1,000 | Full | Gap | SE of the gap | z |
|---|---|---|---|---|---|
| Practice 4 (v4) | 9.58 | 9.17 | +0.41 | 0.54 | +0.8 |
| 1 (v3b) | 18.56 | 18.10 | +0.46 | 0.67 | +0.7 |
| 2 (v5r) | 15.61 | 16.73 | -1.12 | 0.65 | -1.7 |
| 3 (v6) | 19.38 | 19.05 | +0.33 | 0.66 | +0.5 |
| 4 (v7) | 18.55 | 18.26 | +0.29 | 0.64 | +0.5 |
| 5 (v9s) | 19.95 | 17.95 | +2.00 | 0.64 | +3.1 |
| 6 (v10) | 17.95 | 17.53 | +0.42 | 0.63 | +0.7 |

**Longer prefixes** (gap, z; prefixes overlap, so these are not independent tests). Round 1: 2,000 +0.06 (+0.1), 3,000 +0.24 (+0.7), 5,000 +0.61 (+2.3). Round 2: -1.15 (-2.6), -0.64 (-1.8), -0.57 (-2.2). Round 3: +0.54 (+1.2), +0.42 (+1.2), +0.08 (+0.3). Round 4: +0.48 (+1.1), +0.14 (+0.4), +0.31 (+1.2). Round 5: +1.46 (+3.3), +0.69 (+2.0), +0.53 (+2.1). Round 6: +0.35 (+0.8), +0.38 (+1.1), +0.31 (+1.2).

**First half minus second half, our score**: +0.39, +0.20, +0.34, +0.67, -0.01, +0.25 (rounds 1-6; SE 0.29-0.31 each). One of several tests tried, hence C. 2 Curry gained 1.2 points at our tables in second halves (z -2.4, third most extreme of 124 teams: not significant alone).

**Other teams by final rank, first block minus rest, pooled points**: top 20: -0.32, -0.32, +0.41, -0.57, -0.60, -0.72, -0.16 (practice 4, rounds 1-6; mean z -0.07 to -0.29, SE 0.23); ranks 21-60: -0.40 to +0.52; ranks 61+: -0.27 to +0.30. The top 20's small minus is the mirror of our plus at the same tables.

**Rates reproduced.** Round 3 full file against `stat_definitions.md`: 15 of 18 agree to rounding. Three differ: open 35.7 against 34, limp 1.9 against 4, flat-call 9.9 against 12 (cause not found; both files here use one code, so the comparison holds).

**Noise of a 1,000-table team-equal rate** (spread across blocks, mean of 7 rounds; z of block 0 per round, practice 4 then rounds 1-6):

| Rate | Spread | z of block 0 |
|---|---|---|
| Open first in | 0.17 | +0.9 -1.3 +0.6 -0.8 -0.5 -1.7 +0.7 |
| Open-limp | 0.07 | within ±0.5 |
| Open-shove ≤10bb / 10-15 / 15-20 | 0.62 / 0.44 / 0.26 | within ±2.1 |
| 3-bet | 0.09 | within ±1.4 |
| Flat-call outside the big blind | 0.12 | +2.2 -0.8 -2.2 -1.3 +0.1 +0.2 +0.5 |
| Big blind folds to an open | 0.24 | within ±1.1 |
| Fold to a 3-bet / 4-bet | 0.55 / 0.32 | within ±1.3 |
| Fold to a 4-bet | 2.78 | within ±0.9 |
| Call a shove of ≤10bb | 0.44 | within ±1.3 |
| C-bet | 0.41 | -2.3 -0.1 -0.6 +1.1 -3.1 +0.9 -0.8 |
| Fold to a flop / turn / river bet | 0.36 / 0.55 / 0.80 | flop +2.2 once; turn +3.5 and -2.4; river within ±1.9 |
| Raise a flop bet | 0.22 | within ±1.5 |
| Bettor folds to a flop raise | 1.72 | -0.2 +0.2 -1.5 +2.3 +0.4 -0.6 -2.0 |

11 of 126 lie beyond 2 (about 8 expected with 19 later blocks).

**N table, further column.** A 1,000-table practice compared with an N-table scored round: 0.93, 0.81, 0.76, 0.72, 0.68 for N = 1,000 to 20,000 (arith.). Read line by line: 5,000 tables are 630 MB of JSON.

**Filler-copy tables**: 165, 184, 148, 128, 167, 155 in rounds 1-6 and 297 in practice 4. Counting them moves our full-round score by at most 0.03 and a first-block score by at most 0.14.
