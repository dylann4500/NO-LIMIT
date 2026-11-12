# Red-team report on the Finals plan (avalon, 2026-11-12)

Scope: `docs/FINALS_PLAYBOOK.md` and `docs/FIRST_PROMPT.md` Parts 0-6. Nothing in the repo was edited or committed.

**REPORT.md was not saved.** The Write tool refused a report file from a subagent, and I did not route around it. This message is the full report; save it yourself if you want the file. The check scripts and their outputs are in `/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/strategy/redteam/` (`chk.py`, `an.py`, `an2.py`, `adapt.py`, `chk1000.pkl`, `chkfull.pkl`).

## 0. Bottom line

The team lead is right. Almost every number supporting the plan was measured on a field that did not respond to anyone. I checked this: at the regional, openers did not fold less to a seat that had already 3-bet them repeatedly (check 4). The winner's style was a one-step exploit of a field that stood still. On Sunday all 20 teams know that style won, all have per-seat counters, and most will run something like our plan. The plan does not handle four consequences:

1. **Our selection device compares scores taken against different fields.** The three styles are scored at minutes 20, 30 and 40 against three different fields. The challenger's practice score is compared with the live bot's score from a different round. The field moves by about as much as the swap threshold between those measurements.
2. **Every test we own (cloned field, replay) holds opponents fixed.** That overrates any extreme style, aggressive or tight, and cannot see a counter-strategy at all.
3. **Profiles, clones and priors are built from "the latest download".** That is often a practice round, where teams may play something they will not play in the scored round. Even at the regional, 20-60% of the top-20 teams had a materially different bot each round.
4. **The posture rules stop one step short.** "Protect what's working" inside the top 3 makes us a fixed target for every team running our own "one specialist per team ahead" prompt. Nothing covers the last round, which nobody can answer and which is 29-41% of the score.

The most valuable change is structural and needs rehearsal before Sunday: **put the styles (later: live bot, challenger, and a control copy of last round's bot) inside one upload, chosen at random per table.** Every comparison is then same-round and same-field. It closes gaps 1 and 6, removes the T-12/T-9 double upload, and blurs our own profile.

## 1. The opponent model

Assume a strong finalist has everything below; we have each item ourselves.

| They have | Consequence for us |
|---|---|
| The public story of all three regionals (wide 3-betting won Bay Area, jam-heavy came second, a Boston rewrite jumped 18 places, the winner researched for 1.5 hours) | "Pressure" is the most common first bot, not our edge. Hail-mary rewrites in rounds 3-4 are common |
| Their own regional's data and the same leak list | Their prompt says "AI-built bots fold to 3-bets 70-85% and their big bets are honest". Our bots, built by the same models from a similar prompt, fit that description |
| The same frontier agents in parallel | Designs and bugs are correlated across teams; changes arrive every round |
| Per-seat counters with priors, and recognition by bet sizes | They adapt to a 35% 3-bettor inside one table and key priors on our sizes by hand 10-20 |
| Downloads with team names; each opponent shares 37% of our tables (7 of 19) | Each sees about 370 tables of our challenger per practice round and about 7,400 of our live bot per 20,000-table round |
| A clone or simulation rig | They test counters against a clone of last round's us |
| The same top-3-only payoff | 17 teams are told to be bold; 3 are told to protect |
| The round weights | Rounds 1-2 (14% of the total with linear weights, 9% with Boston's) are paid experiments. Anything that loses value once seen is held for the heavy rounds |

The right response depends on which level a team is at, so measure it (Fix C) instead of guessing:

- **L0 fixed:** same play whoever is at the table. This was the regional field (checked).
- **L1 follows the field:** rates move between rounds toward what paid.
- **L2 responds at the table:** folds less to a frequent 3-bettor.
- **L3 plays the name:** treats a seat recognised as us differently from hand 1.
- **L4 hides or misleads:** practice bot differs from scored bot, sizes rotated or copied, late unseen change.

## 2. What I checked in data

All from our Bay Area files: the first 1,000 tables of each of the 14 round files, except checks 4, 9 and 10, which use full files.

"Bot changed" is a proxy: PFR moved more than 4 points, or VPIP more than 5, or the modal open size changed. Each team has about 4,000 hands per sample, so 4 PFR points is over 4 standard errors. The proxy misses postflop-only changes, so true rates are higher.

| # | Question | Result |
|---|---|---|
| 1 | Is the field the same from one build practice round to the next? | No. Teams with a working bot: 90, 114, 120, 124 across practices 1-4. Among the eventual top 20, the bot changed between consecutive build practices in 64%, 44% and 47%, and between practice 4 and scored round 1 in 35% |
| 2 | Is the practice field the same as the scored field ten minutes later? | No. Top-20 teams whose bot changed between the practice round and the scored round after it: 50% (R3), 15% (R4), 10% (R5), 20% (R6). All teams: 28-40% |
| 3 | How stale is a clone field built from the previous scored round? | Top-20 teams with a changed bot from one scored round to the next: 45%, 60%, 35%, 20%, 30% |
| 4 | Did the regional field respond to being 3-bet often? | No. Field fold-to-3-bet by how many 3-bets that seat had already made at the table (R5 full file, hands 1-30, 6+ players): 66.3% (none), 66.7% (1-2), 65.4% (3-5), 70.4% (6+). Hands 31-60: 73.5 / 73.0 / 71.5 / 70.8. Against 2 Curry it went up: 65.9 / 73.1 / 75.2 / 80.2. 2 Curry learned who folds; the field did not learn who raises |
| 5 | Did anyone run a practice-only bot (our challenger pattern)? | Rarely. Top 20: 1 of 80 team-windows. All teams: 28 of 475 (6%). Always Folds raised 0.0% of hands in the last practice and 32% in the scored round after. So our evidence that practice predicts scored comes from a field where almost nobody did what we plan to do |
| 6 | Did teams save changes for the last round? | Some. sandylikesfrogs PFR 23.8 (R5) → 25.7 (practice) → 33.8 (R6). bill & ted 6.1 → 5.3 → 18.4, not shown in practice. 30% of the top 20 changed bot into R6 |
| 7 | Same bot: practice score against the scored round after it (figures from `data/README.md`) | +0.92 (practice 3 → R1, about 4 SE), +0.70, +0.70, -0.35 (each ±0.65). Pooled +0.5 ±0.3. Suggests practice scores run high; not established |
| 8 | What are fillers? | Random copies of submitted bots (rules, line 75), carrying the copied team's id. Our own bot appears as a filler at our own tables. With 20 teams, 20% of our tables will have 4 fillers |
| 9 | Do rate changes continue, as "lean the prior further that way" assumes? | No. After a rate moved more than 3 points, the next move was in the same direction 35-45% of the time and averaged -0.15 to +0.01 of the first move (PFR, 3-bet, fold to bet, fold to 3-bet; full files, 127 teams). Changes are steps, not trends |
| 10 | Is rank persistence as high among the top 20 as in the whole field? | No. Spearman between consecutive rounds, points at our tables: all 127 teams 0.79-0.88; the top 20 by six-round total 0.79, 0.49, 0.73, 0.72, 0.41. Mean rank move was 3-4.5 places per round. Caveat: about ±0.6 per team-round, and the top 20 are selected on the total |

Three team trajectories from check 10 matter for the argument:

- **TeamBallHog never changed** (PFR about 30, 2.9bb opens every round) and scored 20.4 → 17.7 → 16.1 → 16.8 → 15.6 → 14.7.
- **Team 123 rewrote** and went 9.4 → 18.9.
- **Last-round changes cut both ways:** thepastaway jumped 13.4 → 20.3 in R6; sandylikesfrogs' switch to more aggression scored 15.2 after 18.3.

Not checked, because other agents own them: recognition accuracy and hiding, detailed round-to-round adaptation, style match-ups.

## 3. Element by element

| Element | Assumes about opponents | If 5 / 10 / all 19 do the same | How it is exploited | Best response; where the chain stops | Verdict |
|---|---|---|---|---|---|
| Pre-event research (Part 0) | Our research is an edge | All 20 arrive with the same conclusions; the research defines the common first bot | Anyone can aim at the consensus bot before hand 1 | Add a fifth topic: "what will the consensus bot be, and what beats it" | Keep, add topic |
| "Ranks barely move after round 1" | Finals ranks are as sticky as the regional's | — | — | Among the top 20 they are not (check 10); a bot that stands still decays about 1 point a round (TeamBallHog) | Soften: the first bot matters, but so does every round |
| First prompt: regional strategy priors | The Finals field has the regional's leaks | The priors describe us. "Wide 3-bets with disciplined folds to 4-bets" is exactly what a counter is written for | 4-bet or jam light over a wide 3-bettor that folds 80%+; trap a bot that bets whenever checked to | Ranges set by rates measured in practice 1-2, with a defence floor (Fix F) | Keep the checks; make the strategy paragraph conditional |
| Safety, speed, ICM and statistics checks | Nothing | Everyone does them | Not exploitable | — | **Survives** |
| Three styles + tight reserve D | One style is right for a fixed field | If 10 teams field B, B against B is a 3-bet war the looser opener loses. D is the right answer but never plays the real field before it is needed, and is judged only by clones that do not punish tightness | A team expecting B-heavy tables opens tight and stacks off wide | D gets real tables from practice 2 (Fix A) | Keep the four designs; change the scoring |
| Choosing by practice score in the build | Practices 1, 2, 3 are the same field | They are not (check 1). The minute-20 style plays a field with 27% missing or starter bots | Systematic bias: pressure looks best against starter bots | All styles in every practice round, random per table (Fix A) | **Replace** the rotation |
| Challenger in the practice slot, swap at 1 SE | Practice field equals scored field; last scored result is a fair baseline | If all 19 play challengers in practice, the practice field is experiments and the scored field is live bots. The score, the profile refresh and the clones then all come from bots that will not be there | A practice decoy is free (Always Folds, check 5). The comparison has an unknown offset of 0.5-1 point (checks 2, 7), as big as the threshold | Challenger as an arm on 15-25% of scored tables, or correct by the offset of unchanged teams (Fix A, B) | Keep the challenger; **replace** the comparison |
| One change per round to the live bot | Our score change is caused by our change | The field moves 20-60% of its top bots each round; our R3-R6 fell 19.05 → 17.53 while we fixed things | No one needs to exploit it; the attribution is not there, and one change a round is too slow against that field | A control arm (last round's bot on 10-15% of tables) gives same-round attribution; then ship 2-3 flagged changes | **Replace** the reasoning; loosen the limit |
| Leak finder step 2 (our actions against our own fold) | Last round resembles next | Unaffected | Hard to game | — | **Survives** |
| Leak finder steps 3-4 (copy the best five; rates that correlate with points) | What paid the leaders pays next round | Everyone moves toward the leaders at once; the leaders' edge came from the field not doing that | A leader sits one step ahead: tighter opens and lighter 4-bets as the herd arrives | Test "copy the leaders" candidates against a field where a third have also copied (Fix D, H) | Keep with a guard |
| Replay testing | Opponents would have acted the same | Fine | "How those spots turned out" reflects the old bot's image | Use only for where and how often we differ | Keep as a diff tool |
| Cloned field | Opponents keep last round's frequencies whatever we do | If everyone tunes on last round's clones, everyone ships a best response to a field that is gone | It rewards any candidate leaning harder on a fixed frequency; "forward predictions ran 0-1.8 high" is this bias. The -2 veto cannot catch what clones never punish | Add responding clones, with response strength measured from downloads (Fix D) | Keep as veto; **needs a guard** |
| Best-of-ten with a fresh-deal rerun | Selection bias is deal noise | Same for all | The rerun uses the same clones, so the candidate exploiting a clone artefact wins twice | Confirm on a different field model (Fix D) | Keep, one sentence |
| Team profiles and recognition by sizes | Sizes are stable and honest; the latest download shows the bot we will meet | If all recognise by sizes, all hide sizes; the feature decays to the field prior, which is harmless | Borrow a profile by copying its sizes (a maniac in a nit's sizes gets our folds); change sizes each round. Our "vary sizes in a small band" makes us the only team with odd sizes | Match on behaviour too; drop a match that live rates contradict; use the most common sizes (Fix E) | Keep; **needs guards** |
| Per-seat counters and priors | — | Everyone has them; this is what ends the level-0 field | Too few chances per table to bait | — | **Survives** |
| Change tracking ("lean the prior further that way"; follow the recent or against-us rate) | Changes continue | — | They do not (check 9). A recent window on 0-4 chances is noise | Use the new level, shrunk; cap recency for rare rates (Fix E) | Fix one sentence |
| Opponent specialists, one per team ahead | Teams ahead are static and do not watch how they are treated | The top 3 each face up to 17 tailored counters, change identity, and the counters miss | A leader can show a leak in a light round and close it in a heavy one | Rank targets by gain × stability; track whether the target closes the leak (Fix C item 6) | Keep, re-rank |
| Top-3 posture | Others' risk attitudes do not matter | 17 teams go bold together: more jams and rewrites in rounds 2-4 (D answers this). Inside the top 3, "protect" means a fixed profile in the heaviest rounds | The leader is everyone's target | Hold the strategy, rotate the identity, keep rates near break-even (Fix G) | Keep outside top 3; **fix** inside |
| Round weights: "experiment early" | Others do not also discount early rounds | Early field ≠ late field; early profiles are of experiments | Holding the real counter for rounds 5-6 | Arms in rounds 1-3; early profiles provisional; a last-round build (Fix G). If culling is on, the rule is wrong | Keep, with the culling check |
| Last round | Not addressed | Everyone's last move is unanswerable | A last-round change aimed at the round-5 leaders | Fix G | **Missing** |
| Timing: challenger up at T-12, live back at T-9 | Portal behaves as at the regional | Fine | Self-inflicted: a failed re-upload plays the challenger in a scored round. It also shows all 19 teams our challenger ten minutes early | One upload per window with arms | Simplify via Fix A |
| Hail-mary rewrite | A rewrite is a rare bold move | It is the famous Boston story; expect several | — | Clone veto and D cover the field effect. The Boston jump was from 45th of 100+; a 20-team field has less room | Keep |

## 4. Gaps ranked by expected cost

Costs are rough judgments. "Points" are per table per round. For scale, the regional gap from 3rd to 6th was about 1.2 per table per round.

| Rank | Gap | Expected cost | Why | To close |
|---|---|---|---|---|
| 1 | Styles and challenger chosen by comparing scores from different fields | 0.3-0.8 per table over the event; perhaps 10-15 percentage points of top-3 probability | Styles sit within 0.5-1 point of each other; noise is ±0.6 / ±0.4 / ±0.2 with a field shift of the same order. We would pick the best style about half the time, and each later swap decision carries an offset as big as its threshold | **Real work:** Fix A (rehearse). Cheap partial: Fix B |
| 2 | Every test holds opponents fixed, in a field that will respond | 1-3 per table for one round when it bites (a mild v4), most likely in round 2-3 after a "more aggression" candidate tops the clone ranking; 0.2-0.4 averaged | The clone veto was validated on a level-0 field (check 4); it passes exactly the candidates that get punished | **Real work:** Fix D. Cheap partial: the defence floor in Fix F |
| 3 | We lead with the consensus style | 0.3-1 per table in rounds 1-2 if the field is B-heavy | B's edge was a 66-74% fold to 3-bets; a field that 4-bets or calls a little more removes it | Cheap: Fix F, plus D as an arm |
| 4 | Fixed target when top 3; nothing on the last round or on held-back changes | Applies only if we are in or near the top 3; then 0.3-1 per table in rounds worth 52-66% of the total | "Protect" plus a visible size signature plus 17 teams running our specialist prompt; a static bot decayed about 1 point a round at the regional | Cheap: Fix G |
| 5 | Profiles, priors and clones built from whatever came last | 0.1-0.4 per table | Checks 2 and 3; one stale profile is wrong at 37% of our tables | Cheap: Fix E |
| 6 | "One change per round keeps the result readable" | Perhaps 0.2-0.5 per table by round 4 from fixes held back | The result is not readable anyway, and top-20 ranks move 3-4.5 places a round | Falls out of Fix A (control arm) |
| 7 | Copying the leaders when everyone does | 0.1-0.3 per table | Leak-finder steps 3-4 | One sentence (Fix H) |
| 8 | Size jitter makes us unique; identity can be borrowed | Under 0.2 per table | Part 4, last bullet | One sentence (Fix E) |
| 9 | Trend-leaning and recency in priors | Under 0.1 per table | Check 9 | One sentence (Fix E) |
| 10 | Fillers: 20% of tables have 4 random copies, some our own bot | Small unless a style self-destructs against itself | Check 8 | One line: run each style against copies of itself; keep filler seats in recognition |
| 11 | Platform options change the posture | Large if culling is on and we experimented early | The playbook lists the options with no action attached | One paragraph (Fix G) |

## 5. The fixes, as prompt-ready text

### Fix A · Arms: several bots in one upload, random per table (closes 1 and 6; helps 3 and 5)

```
Package the bots as ARMS of one upload. submission/ holds one file with a thin dispatcher and each bot as
a self-contained section (its own tables and settings; shared platform layer and variant engine only).
On the first decision of a table the dispatcher picks an arm and writes it into the table's memory; every
later decision at that table goes to that arm. Pick the arm from a hash of our own first-hand hole cards
and seat (both are in our download, so the analysis can recompute which arm played each table without any
log), compared against a weights table at the top of the file, e.g. ARMS = {"A": 25, "B": 25, "C": 25,
"D": 25}. If the memory is missing or unreadable, recompute or fall back to the first arm. The safety
shell wraps the dispatcher, and an exception inside one arm falls back to the passive action and is
counted per arm. Run the full check list on the packed file once per arm (force each arm in turn), and
the latency test with all arms imported.

Weights by phase:
- Build practice rounds 1-4: all styles that pass the checks, equal weights. Never one style per round:
  the field changes between practice rounds, so only same-round comparisons count.
- Scored round 1: the leader 70%, the others split 30%. Round 1 is 1/21 to 1/32 of the total.
- Later scored rounds: live bot with this window's changes 70-75%; challenger 15%; CONTROL, last round's
  live bot unchanged, 10-15%. In the last two rounds: live 90%, control 10%, no challenger, unless we are
  outside the top 3 and the challenger is ahead.
- Practice rounds between scored rounds: live 50%, challenger 50%. That catches a challenger that is 3 or
  more points worse; it does not rank them.

After every round report, per arm: tables, points per table, standard error (measure the per-table
standard deviation in this file; do not assume 20), and the difference to the live arm with its error.
Decide with these, from the same round only:
- challenger replaces live when its difference is above +1 standard error outside the top 3, +2 inside;
- this window's changes are kept when live minus control is not below -1 standard error; otherwise revert
  and say which flag is suspected;
- pool an arm's evidence across rounds only after subtracting each round's live-arm score.
Say on the day if any rule or portal check forbids random choice inside a bot; if so, fall back to Fix B.
```

Counter-check on Fix A itself:

- **Precision:** at a per-table SD of about 20, a 15% arm of a 20,000-table round is 3,000 tables, so the difference to live is about ±0.40. Four equal arms across practices 3 and 4 give about ±0.27 each.
- **Cost:** a challenger 1 point worse on 15% of tables costs 0.15 per table that round.
- **What opponents see:** a blend of arms, which is a worse profile of any one of them than they get now.
- **What can break:** one file carries every bot, so a dispatcher bug zeroes the round. Rehearse it in `emu/` and force each arm through the gate.
- **Rules:** I found nothing in `prep/docs/official_rules.txt` against it (100 MB file limit, 1 ms). Confirm on the day.

### Fix B · If arms are not possible: correct the practice score for the field

```
Never compare a practice score with a scored-round score directly. From the portal results take every
team's practice score and its previous scored-round score. From the practice download, mark the teams
whose bot is unchanged since that scored round (same open sizes, and open, re-raise and fold rates within
noise). The field offset is the median over those unchanged teams of (practice minus previous scored),
with its error. Our challenger's corrected lead = (challenger practice - offset) - live bot's previous
score. Apply the swap rule to the corrected lead, with the offset's error added to the standard error.
Report how many teams changed bot for the practice round; if more than a third of the field did, say the
practice field is not the scored field and treat the score as a disaster check only.
```

### Fix C · The level meter (every download)

```
From this download, measure for every team, with counts and errors:
1. RESPONSE WITHIN A TABLE. Its fold, call and re-raise rates facing a 3-bet, split by how many 3-bets
   that seat had already made at the table (0, 1-2, 3-5, 6+), within the same hand-number band. The same
   for folding to a bet after the flop by how often that seat has bet when checked to, and for calling a
   shove by how often that seat has shoved. A flat line is a team that does not respond. Give the slope.
2. RESPONSE TO US BY NAME. Its rates against us in the first 15 hands of a table compared with its rates
   against other seats in the first 15 hands. A gap before it could have learned anything at the table
   means it recognises us. Then the same comparison against the previous round: did its treatment of us
   change the round after we changed?
3. BOT CHANGES. For each team, is this file's bot the same as its previous scored round's, and (when the
   next scored file arrives) was its practice bot the same as the bot it then played? Keep a table per
   team: unchanged / practice showed its next bot / changed after the practice / practice-only bot. A
   team's history here says how far to trust its practice-round profile.
4. SIZES. How many teams share each open size and bet-size pattern; which teams vary sizes from table to
   table or round to round; which team's sizes now match another team's old sizes.
5. THE FIELD. Open, 3-bet, 4-bet, fold-to-3-bet, fold-to-4-bet, shove and call-a-shove rates for the
   whole field, this round and every earlier one, and how many teams sit close to the current leader's
   style. From the fold-to-3-bet and 4-bet rates compute directly what a bluff 3-bet and a marginal open
   earn at our sizes.
6. LEAKS WE ATTACKED. For every team-specific counter we shipped: did the target's rate move the round
   after?
End with one line per team: fixed / follows the field / responds at the table / plays our name / hides,
and one line for the field. The manager uses this to set how hard each exploit leans: full against fixed
teams, half against teams that respond at the table, none against a team that changed bot for this round.
```

### Fix D · Clones that respond, and scenario fields (add to Part 3, item 5)

```
Clones that hold their frequencies whatever we do will approve any candidate that leans harder on those
frequencies. So build each field twice. FIXED: as fitted. RESPONDING: each clone also counts, per seat,
how often that seat opens, 3-bets, bets when checked to and shoves, and shifts its own fold, call and
re-raise rates toward the break-even response as the counts grow. Set the speed of that shift from the
level meter (item 1): a team measured as flat gets none; where nothing is measured yet, assume a shift
that removes half the edge by hand 40. Also build two scenario fields from the fixed one: STEP (every
clone that changed last round replaced by the field average, since changed teams do not keep moving the
same way) and HERD (the third of the clones nearest the leader replaced by the leader's clone).
A candidate is fit to ship only if it does not lose 2 or more points in the fixed field AND does not lose
1 or more in the responding field. Report all four fields per candidate. A candidate that wins in the
fixed field and loses in the responding field is an exploit with a short life: allowed as a challenger
arm, not as the live bot in the last two rounds. The confirmation run for the top two candidates uses a
field model the first run did not (different bluff share, and the responding field), not only new deals.
```

### Fix E · Profiles for a moving, hiding field (add to Part 4)

```
Tag every download as scored or practice. A team's profile is built from scored rounds; its practice
round is a second, provisional profile ("what it may play next"), weighted by that team's record of
actually playing its practice bot (level meter item 3; before any record exists, a quarter of the
weight). At the table, score each seat against both profiles of every team.
Recognise on behaviour as well as sizes: a seat whose open and re-raise rates at this table are more than
two standard errors from the matched profile loses the match, however well the sizes fit. Never give more
weight to a size match alone than to the field prior.
Replace "lean the prior further in the direction of the move" with: use the newest scored round's rate,
shrunk toward the team's average over all rounds in proportion to its noise. On our regional data a rate
that moved kept moving the same way only 35-45% of the time. For rates with fewer than five chances per
table, the recent-window and against-us adjustments may move the estimate by at most a fifth of the
distance to the prior within one table.
Our own sizes: do not jitter. Use the most common open size and bet fractions among the top half of the
field in the latest scored round, so that we are one of several teams with those sizes; change to the new
most common set each round. Report after each round how many teams share our sizes.
```

### Fix F · Style from the measured field (replace Part 1's first strategy bullet; add to the style list)

```
Every team here knows wide 3-betting won our regional, so expect it at most tables and expect bots written
to punish it. Do not hard-code a style. Each bot's opening, 3-bet, 4-bet and call-off ranges are functions
of measured rates with priors: 3-bet light only against an opener whose fold-to-3-bet estimate clears the
break-even for our size by a margin, and stop when 4-bets come back more often than the bluffs can stand;
open fewer hands as the seats behind us 3-bet more; 4-bet and call off wider against a seat that 3-bets
often. Whatever the estimates say, keep a floor: never fold more than about 75% to 3-bets or to 4-bets
over a table, and never bet 100% of the time when checked to. A bot that folds 85% to the next raise is
what every opponent's prompt describes.
The styles differ in their priors and defaults, not in whether they listen: B starts by assuming openers
fold, D starts by assuming raisers are loose. From the first practice download, compute what a bluff
3-bet and a marginal open actually earned in this field and tell me which starting assumption the field
supports. Before trusting any style, run it at a table of seven copies of itself and at a table of seven
copies of the pressure bot; one that loses badly to either has a hole a 20-team field will find.
For sparring, also have three cheap subagents each write "the bot a rival team's agent would write from
this kit" from a plain two-line prompt, and use those as the default local field: they are a better guess
at Sunday's opponents than a calling station.
```

### Fix G · Leading, held-back changes, the last round, platform options (playbook "How we decide" and the manager prompt)

```
- Read the Format page for culling, luck correction and a late final weight before choosing a risk
  posture. If teams can be culled, the early rounds are not for experiments: weight the leader arm 90%
  until the cull has passed. If luck correction is on, re-measure every standard error from the files.
- Inside the top 3 we are the team everyone below is studying, and a bot that stands still loses about a
  point a round as the field moves. Protect the strategy and change the identity: new sizes every round,
  and move any rate of ours that an opponent could aim at (fold to 3-bets, fold to bets by street, bet
  when checked to) to within 10 points of its break-even value. Each round, from the level meter item 2,
  list the teams whose treatment of us changed and what they now do; that list sets next round's change.
- Sort every exploit into two kinds. Durable: works even if the target sees it (sound ranges, ICM). Ship
  at once. Perishable: stops working once the target reacts (a counter keyed to one team's leak or
  sizes). Ship a perishable exploit only against teams the level meter marks as fixed, track item 6, and
  keep a list of perishable exploits tested only in the cloned field or on a small arm for the last
  round, when nobody can react.
- The last round. Prepare it from round 4: one build with every durable fix, every perishable exploit
  still valid on the newest profiles, and profile trust lowered for any team that changed bot in the
  last practice round or has a record of late changes. Others will do the same to the round-5 leaders, so
  if that is us, the last-round build also carries new sizes and the defence floors. An untested bold
  change in the last round is a coin flip (at our regional one gained 7 points and one lost 3): take it
  only when outside the top 3.
- Rounds 1-2 show experiments, ours and theirs. Do not build team-specific counters on round-1 data
  alone unless the level meter shows the team's bot unchanged into round 2.
- Opponent specialists: rank targets by expected gain per table x share of our tables (37% each) x how
  unchanged the team has been, not by whether they are ahead of us. A team ahead gets priority only when
  the estimates are close, because points taken from it count twice.
```

### Fix H · One sentence for leak finder step 3

```
Every team is copying the same leaders from the same kind of table, so for each "they do it more and it
pays" gap also say what it would earn if a third of the field did it too, and whether the leaders' own
rate for it rose or fell since the previous round; a move the leaders are already backing away from is
not a candidate.
```

## 6. Where each chain stops

Every "we do X, they counter, we counter that" chain in the plan ends in the same place. The size of each lean is set by a measured rate, the measurement is redone every round, and the lean has a floor and a cap. That replaces picking a level to play at:

- **Fixed teams:** full weight on the exploit.
- **Teams that respond at the table:** half weight.
- **Teams that changed bot or hide:** field prior only.
- **Our own rates while we are a target:** none further than about 10 points from break-even.

## 7. What survives unchanged

- The safety shell, latency design, one-file packing and check list (Part 1 checks 1-8).
- Unit-testing every library function, the ICM edge cases, and bug hunters reading cold on a different model.
- Leak finder step 2 (our actions against our own fold): it needs no opponent model.
- "Local wins against our own bots decide nothing" and "never gate on looking like the average team".
- Per-seat counters with priors, counting responses to our own bets, opportunities-based rates.
- The cap on any profile's pull, and treating an unmatched seat as a new bot.
- The cloned field as a disaster veto, with Fix D beside it.
- Building D at all, and giving A, B and C the milder response to aggression.
- Testing far more candidates than we ship, with agents in parallel.
- The bold posture outside the top 3.
- A minimal legal bot active by minute 10, and hands off for the last ten minutes of the build.