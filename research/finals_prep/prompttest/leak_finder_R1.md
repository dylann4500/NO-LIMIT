## 1. Findings for the manager (scored round 1, 1,000-table sample; we are "avalon", in 1,001 non-filler seats)

**How I defined things (I had to guess these; see the critique):**
- **Situation cell:** street × situation × players left (6-8, 4-5, 2-3) × effective stack (<10, 10-20, 20-40, 40+ bb) × whether checking is free.
- **Value:** points equity after the hand minus before, for that seat.
- **z-score:** I split our tables into 20 blocks in file order, took the action-minus-baseline difference in each block, and divided the mean by its standard error.
- **Raise sizes:** before the flop, "small" is a raise to at most 2.5 times the bet faced. After the flop, "small" is a raise of at most 0.55 × (pot + amount to call). An all-in raise counts as "all-in"; an all-in call counts as a call.
- **Benchmark teams:** the 10 best other teams by points per table: TeamBallHog 21.9, WAYS-ER 21.3, AZ 20.8, 2 Curry 19.2, sandylikesfrogs 19.1, tuh 18.9, one in a krillion 18.8, bill & ted 18.5, Team 72 18.5, Team 82 18.3. Each played only 44–63 tables.
- **Where we stand:** avalon averages 18.56 points per table, 8th of 127 teams. The average is 12.5.
- **Step 1 (failures):** we had 0 automatic actions, both before the selection phase and in it.

### Before the flop

**Step 2: our actions that do worse than our own fold** (in the "cost" column, uses per table × difference)

| # | Cell | Action | Uses per table | Action vs fold | z | Cost per table |
|---|---|---|---|---|---|---|
| 1 | facing one raise, 4-5 players, 20-40bb | call | 0.69 | −0.84 vs −0.08 (diff −0.76) | −3.3 | −0.53 |
| 2 | facing one raise, 6-8 players, 20-40bb | call | 0.79 | −0.57 vs −0.04 (diff −0.53) | −3.2 | −0.42 |
| 3 | facing one raise, 4-5 players, 40+bb | call | 0.62 | diff −0.41 | −1.6 | −0.25 |
| 4 | facing one raise, 4-5 players, <10bb | call | 0.15 | diff −0.55 | −1.6 | −0.08 |
| 5 | facing one raise, 4-5 players, 10-20bb | call | 0.09 | diff −0.81 | −0.9 | −0.08 |

Next in line were large opens with 4-5 players at 40+bb (−0.16, z −0.5) and shoving unopened with 4-5 players at 10-20bb (−0.11, z −0.2). Both are noise.

**Important caveat on rows 1–5:** the prompt's cells do not include position. Pooled together, calling an open with 4+ players and 20bb+ is −0.23 against folding (4.8 uses per table, z −4.1). But 61% of those calls come from the big blind, while most folds come from seats with no blind in the pot. Splitting by position shrinks the difference a lot:

| Position | Call vs fold | Uses per table | z |
|---|---|---|---|
| Big blind | −0.15 | 2.9 | −1.45 |
| Small blind | −0.10 | 1.2 | −0.8 |
| Other seats | −0.04 | 0.8 | −0.6 |

So the leak is real in direction, but it is about 0.3–0.5 points per table, not about 1.3.

**Step 3: what the best teams do more that pays for them** (score = frequency gap × our uses of the cell per table × their difference)

| # | Cell | Action | Their rate vs ours | Their gain over their fold | Our own gain |
|---|---|---|---|---|---|
| 1 | unopened, 6-8 players, 40+bb | large open | 11.0% vs 3.3% | +0.23 (z 3.9) | +0.45 (z 4.5) |
| 2 | facing one raise, 4-5 players, 20-40bb | large re-raise | 7.4% vs 3.3% | +1.09 (z 4.8) | +1.27 (z 3.0) |
| 3 | facing one raise, 6-8 players, 40+bb | large re-raise | 6.4% vs 4.3% | +0.45 (z 1.9) | +0.97 (z 5.9) |
| 4 | facing one raise, 6-8 players, 20-40bb | large re-raise | 6.0% vs 3.2% | +1.06 (z 5.2) | +0.72 (z 2.2) |
| 5 | unopened, 2-3 players, <10bb | small open | 12.3% vs 0% | +0.66 (z 4.3) | — |

Close behind: they open small with 2-3 players at 20-40bb at 53% to our 23%, and they re-raise 10-20bb with 4-5 players where we never do.

**Before the flop, the three findings:**
1. **We call opens too often instead of re-raising or folding.** Pooled it is −0.23 per call (z −4.1), but only about −0.1 within each position (z about −1.5). That puts the cost at roughly 0.3–0.5 points per table. **Change:** with 20bb+ and 4+ players, move about a third of our calls of an open into large re-raises and the rest into folds. Our flat-call rate in those cells should drop from about 20% to about 13%. Our large re-raise rate should go from about 3% to about 6–7%, which matches the top teams.
2. **We rarely open large at a full table with deep stacks.** We do it 3.3% of the time against their 11%. It pays for them (+0.23, z 3.9) and for us (+0.45, z 4.5). **Change:** shift some small opens to large ones (about 3 times the big blind) at 40+bb with 6-8 players, targeting about 10%.
3. **Short-handed (2-3 players) we open too little.** At 20-40bb we open small 23% of the time against their 53%. Their opens beat their folds by +0.15 (z 1.2), and our own small opens there beat our folds by +0.41 (z 4.2). **Change:** raise our opening rate there toward 40–50%.

### After the flop

**Step 2: our actions that do worse than our own fold or free check**

| # | Cell | Action | Uses per table | Action vs baseline | z | Cost per table |
|---|---|---|---|---|---|---|
| 1 | flop, facing a re-raise, 6-8 players, 40+bb | call | 0.19 | −3.21 vs −0.65 (diff −2.56) | −2.9 | −0.49 |
| 2 | flop, facing a re-raise, 4-5 players, 40+bb | call | 0.05 | diff −8.05 | −1.9 | −0.39 |
| 3 | flop, facing a re-raise, 6-8 players, 20-40bb | call | 0.08 | diff −4.05 | −4.2 | −0.33 |
| 4 | flop, facing a re-raise, 4-5 players, 20-40bb | call | 0.07 | diff −4.52 | −3.2 | −0.32 |
| 5 | flop, first to act, 4-5 players, 20-40bb | small bet (vs check) | 0.26 | diff −1.01 | −2.3 | −0.26 |

Pooled over all cells:
- **Calling a re-raise:** on the flop it is −3.59 against folding (0.50 uses per table, z −7.2), about **−1.8 points per table**. On the turn it is −2.78 (0.21 per table, z −2.5). On the river it is −0.73 (z −0.5), which is noise.
- **Small bet as first to act, against checking:** flop −0.31 (2.3 per table, z −2.7); turn −0.42 (1.4 per table, z −2.3). That is about 1.3 points per table.
- **Large bet as first to act, against checking:** it does better than checking on every street. Flop +0.61 (z 4.5), turn +1.62 (z 7.2), river +2.68 (z 14.9).
- **Calling a single bet on the flop:** with 6-8 players at 20-40bb it is −0.98 (0.18 per table, z −2.2).

**Step 3: what the best teams do more that pays for them**

| # | Cell | Action | Their rate vs ours | Their gain | Our own gain |
|---|---|---|---|---|---|
| 1 | turn, first to act, 6-8 players, 40+bb | large bet | 35% vs 28% | +2.11 (z 5.4) | +2.72 (z 8.1) |
| 2 | turn, facing a bet, 6-8 players, 40+bb | large raise | 7.6% vs 4.1% | +3.61 (z 2.8) | — |
| 3 | turn, checked to, 6-8 players, 40+bb | large bet | 39% vs 29% | +1.74 (z 4.1) | +2.72 (z 6.5) |
| 4 | river, facing a bet, 6-8 players, 40+bb | call | 37% vs 17% | +1.15 (z 1.3) | +0.37 (z 0.9) |
| 5 | river, facing a bet, 6-8 players, 20-40bb | call | 37% vs 26% | +4.64 (z 3.3) | — |

These gaps are small: the scores are all 0.17 or less.

**After the flop, the three findings:**
1. **We call too many re-raises on the flop and turn.** On the flop it is −3.6 per call, 0.5 uses per table, z −7.2, about −1.8 points per table. Because we call with our better hands, this is a floor on the loss. **Change:** fold more when facing a re-raise on the flop and turn. Cut the call rate there by at least half; we make about 0.7 such calls per table now.
2. **Our small first-to-act bets do worse than checking, while our large ones do much better.** Small bets on the flop and turn cost about 1.3 points per table (z −2.7 and −2.3). This likely feeds finding 1: small bets get raised, then we call. **Change:** stop small first-to-act bets on the flop and turn. Split them into checks (weak hands) and large bets (strong hands). The small-bet share as first to act should go from 42–45% to under 15%. The large-bet share should rise toward 50% on the flop and 40% on the turn.
3. **On the turn at full, deep tables we bet large less often than the top teams.** We are at 28–29% against their 35–39%, and it pays for both. **Change:** this comes out of finding 2's resizing, with a target of about 35% large turn bets.

## 2. Timeline
| Time | What |
|---|---|
| 16:24:31 | Start |
| 16:25:59 | Extraction finished: 1,012 tables, 907k decisions, one pass taking 12 s wall time on one core. That was about 1.5 min after starting, mostly reading docs. |
| 16:26:41 | Step 2 and step 3 tables ready, 2.2 min in |
| 16:27:12 | Position and pooling checks done, answers ready, 2.7 min in |

Writing this report took a few more minutes after that.

## 3. Critique of the prompt
1. **Cells without position give a wrong ranking before the flop.** The prompt says: "situation (unopened; checked to; facing one bet or raise; facing a re-raise)". Pooled, my top preflop leak was −0.76 (z −3.3); within each position it shrinks to about −0.1 to −0.15 (z −1.5). The fold baseline is mostly from seats with no blind in the pot, and the calls are mostly from the big blind. Followed literally, this ranks a mix of seat positions as the biggest preflop leak. Proposed wording: "situation (…), and for decisions before the flop, position: small blind, big blind, or other (button and heads-up count as the small blind). Always compare an action with the fold from the same position."
2. **Raise sizes are not defined.** "small raise, large raise" was a guess on my part (2.5 times the bet faced before the flop; 0.55 of the pot after it). Proposed wording: "small raise = raise to ≤2.5× the bet faced before the flop, or ≤55% of pot after it; large = bigger, but not all-in."
3. **"Situation" is ambiguous.** It is unclear whether the comparison cell is the situation alone or situation × players × stack, and what "unopened" means before the flop (limps? the big blind's free option?). I used the full cell, and put the big blind's option under "checked to". Proposed wording: "Compare within street × situation × players left × stack bucket (<10, 10-20, 20-40, 40+ bb) × position before the flop. A limped pot counts as unopened; the big blind's option counts as checked to."
4. **The ranking splits one leak into many small rows.** "Rank by uses per table x difference" applied per cell spreads one leak across stack and player-count cells. "Call a re-raise on the flop" appears as four separate rows, while the pooled figure (−1.8 per table, z −7.2) is the real headline. Proposed addition: "Also report each action pooled across stack and player-count cells (summing count × difference), and rank leaks on the pooled figure."
5. **The z-score recipe is incomplete.** "a z-score from splitting the tables into 20 blocks" does not say how; I used the mean of the block differences over its standard error. Proposed: "z = mean of the 20 block differences / (their SD/√20); a block missing either action is dropped."
6. **The benchmark teams have small samples, and the prompt hides this.** In "take the 10 best other teams in this file by points per table", the other teams have about 55 tables each against our 1,000. Their cells are thin, and their ranking by points is itself noisy (a standard error of roughly ±2 points). Proposed addition: "pool the 10 into one group; require at least 30 uses in a cell; state how many tables they have."
7. **"Failures first" overstates what the file shows.** The file records only our own automatic actions, and other teams' failures are not visible. Say so: "only our own failures are in the file."
8. **"Effective stack" and "all-in" are not defined.** Effective stack could mean at the start of the hand or at the decision, and could include folded players. An all-in call could count as a call or as an all-in. I used: the smaller of our starting stack and the biggest starting stack among players still in, and all-in calls counted as calls. Specify both.
9. **The timing promise checks out.** "A full pass should take well under a minute" was accurate (12 s). The whole job fits comfortably in 12 minutes.

**Files** (all in /private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/prompttest/leak/):
- Scripts: extract.py, analyze.py, check2.py
- Tables: out/decisions.csv, out/table_points.csv, out/step2_pre.csv, out/step2_post.csv, out/step3_pre.csv, out/step3_post.csv