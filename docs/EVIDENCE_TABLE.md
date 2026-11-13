# Evidence table: what we believe, why, and what would justify acting on it

For Samuel, Dylan and any agent that updates the plan. Written 2026-11-12 after an outside review of the
strategy studies. The review's main point: findings were being promoted from "interesting" to "settled"
without a test. This table is the gate. **A row changes the prompt pack only at the grade it has earned.**

Sources are the study reports in `research/finals_prep/` (literature, redteam, adaptation, identity,
clone_field). All data is one regional (Bay Area, 148 teams, one variant) seen from our tables only, plus
a friend's Boston files. Nothing here has been tested on a 20-team field.

## Grades

On the day, what each grade licenses is set by `DECISION_RULES.md` §4 (A: act; B: act in the challenger and
practice, ship live when consistent with real-field signals; C: try where it's cheap to be wrong).

| Grade | Meaning | What it may change |
|---|---|---|
| **A. Measured fact** | A description of what happened, checked against the data, with no causal claim | Facts and numbers in the docs |
| **B. Tested change** | A change to the bot or process whose effect was measured on full-table results (real rounds, or simulation that passed its own validation) | A default in the prompt pack |
| **C. Candidate** | A plausible change supported by observation or argument, not yet tested | On the day: may be played as the challenger or in a practice round, ship behind a setting, or go live outside the top 3 when the decision rule fires; say "grade C, untested on the real field". Never on its own a reason to block a change |
| **D. Withdrawn** | Contradicted by data or by a sound objection | Removed from the docs; never the sole reason for a switch |

Three kinds of evidence are kept apart throughout: **chip accounting** at one decision (exact), **modelled
tournament value** (chips converted to points by a model), and **real tournament results** (the only
thing that counts, and noisy).

## 1. Claims I stated too strongly

| Claim as I put it | What the data actually shows | What else could explain it | Grade now | Test before it changes a default |
|---|---|---|---|---|
| "The winner's edge was learning each seat inside the table" | 2 Curry re-raised an opener 18% of the time with no history, 43% after one fold, 7% after one non-fold (138,000 decisions, stacks 25bb+, single opener). That it adapts is measured. | Its contribution to winning is not measured. Stack depth, position, players left and which seats survive are only partly controlled. Its other choices may matter more. | A for "it adapts"; C for "this is why it won" | Play an adapting and a non-adapting version of the same bot in the cloned field with responding opponents; compare full-table points |
| "Defend the first re-raise at a table wider" | Against 2 Curry's rule, seats that did not fold the first time were re-raised less afterwards | A loose call or 4-bet costs chips now; the later saving may be smaller. Only a few teams had such a rule at the regional. | C | Full-table scoring of the variant against responding clones, and against fixed clones to see what it costs when nobody is learning |
| "Moving to common bet sizes costs a few tenths to a point per table" | Fold rates rise with the size faced (flop: 29% at a third pot, 51% at half, 72% at full pot) | Observational: different hands, boards, stacks and bettors choose different sizes. Not a controlled experiment, so no cost figure follows. | A for the fold-rate table; the cost figure is D | Change only the sizes of one bot and replay it against the same field model on the same deals |
| "Masking is settled: don't" | Simulated relabelling of our sizes: hidden for one round, found again once profiles refresh. "Uses the common sizes" is itself identifiable. | Opponents' in-hand reactions to the new sizes were not replayed. Recognition accuracy is not the objective; points are. | B for "masking hides us one round at most"; C for "choose sizes for value" | Covered by the sizing test above |
| "A called bet at showdown is a fair sample of that bet" (Part 4) | — | Wrong in general. Whether a bet is called depends on the caller's cards and on public information (here including the bettor's exposed card), both of which correlate with what the bettor holds. | D | Reword: showdowns are selected evidence; give a range, not a rate |
| "Replay scores a fold exactly" | Folding instead of calling gives the exact chip result of that decision | It does not give the table's finish: later hands would have gone differently | A for chips; C for points | Report replay results as chips, with the modelled points conversion labelled as a model |
| "Any rate more than 10 points from the field is a leak" | Our 89% fold to re-raises (field 65%) was exploitable in principle | A gap can be a good exploit, a different opportunity mix or a different style. The regional winner was far from the field on several rates. Our own gate once blocked good aggression this way. | D as a rule; C as a prompt for questions | A gap is listed with what an informed opponent would do about it and what that costs; it becomes a candidate, not a fix |
| "Nothing that loses 2+ points in the cloned field gets uploaded" | The cloned field reproduced one collapse (−6 to −8 vs real −9) and one gain (+1.6 to +2.9 vs +2.3) | Two cases. Opponents were frozen. Fresh seeds remove noise, not model error. | C | The ordering validation now running (below) |
| "Ranks barely move after round 1" | Whole field: round-to-round rank correlation 0.84-0.91 | Among the top 20 it was 0.41-0.79, with moves of 3-4.5 places per round | A, corrected | — |
| "Lean a team's prior further in the direction it just moved" | — | Measured twice: a rate that moved kept moving the same way 35-45% of the time; "same as last round" beat trend forecasts at both regionals | D | Remove |
| "Vary our sizes within a small band" | — | A recogniser that bins sizes still finds us; the band is its own signature | D | Remove |
| "Folding more is the answer to an aggressive field" | A pure folder finished 4th most often (4.7 points) | Tightness answers teams busting each other. Against raises and steals, folding is what loses; the counter there is re-raising and calling wider. | C, narrowed | The style-matchup simulations (running) |

## 2. Measured facts worth keeping (grade A)

| Fact | Numbers | Limits |
|---|---|---|
| Almost every team changes its bot every round | 78-90% per round at Bay Area, 75-84% at Boston | Detection threshold is the study's own |
| For top-20 teams, changing kept them level | Lost about 0.65 points per table per round whether they changed or not; no unchanged top-20 team improved (0 of 18) | Regression to the mean partly corrected |
| Large gains came from rewrites, but rarely for strong teams | 81 of 92 gains of 1.5+ points were rewrite-scale; 3 were by a top-20 team; top-20 rewrites averaged −0.68 ± 0.39 | — |
| "Same as last round" predicts the field better than a trend | Error 1.29 vs 1.72 points (field), 5.9 vs 11.0 (single team) | Two exceptions among the top 20: re-raise rate and big-blind defence moved the same way every round |
| Aggression rose all night; the defence came late at Bay Area, early at Boston | Top-20 re-raise 9.8% → 23.7%; Boston's top teams folded only 58% to re-raises and 4-bet 23% by round 5 | Boston's top-20 list is estimated |
| Some teams respond to what a seat has done at the table | Strong response on at least one decision in 27 of 122 Bay Area teams, 10 of the other 19 in the top 20 | No evidence anyone played named opponents |
| Practice rounds were not full of experiments | 3% practice-only bots; a fixed bot's practice score matched its previous scored round (−0.06 ± 0.05) and ran 0.37 ± 0.06 above the next one | More than half the field uploads after the practice round. With 20 teams one team is 5% of the field, so this will be noisier |
| The field differs between build-hour practice rounds | 44-64% of the eventual top 20 changed bot between consecutive build practices | Proxy measure |
| Sizes carry most of the recognition signal | 20 candidates, previous-round profiles: 73% correct by hand 20 with sizes, 31% without | Field was not hiding; our own sizes never changed |
| We were identifiable almost at once | Half our seats by about hand 7 | — |
| Regional practice-round timing | Practice results in 1-3 minutes; scored in 6-8; practice starts 7-10 minutes before the scored round | One event |

## 3. Proposed changes and the test each needs

Priority follows the review's order: correct rules and counters, a strong baseline, reliable candidate
evaluation, measured adaptation to opponents, then identity-based refinements. Deception, style mixing
and agent volume come last.

| # | Proposed change | Support | Grade | Test and pass mark |
|---|---|---|---|---|
| 1 | One shared platform (rules, equity, counters, memory, legal actions); styles are parameter sets or small swappable decision parts | v10's two bugs were in shared counting code written once and never cross-checked; three separate rewrites triple that surface | C | Rehearsal: does one platform with three parameter sets get three working bots to a practice round faster and with fewer failures than three separate builds? |
| 2 | In-table adaptation that is specific ("this opener folds to this size at this stack depth"), blended with priors, conservative default | Literature (bounded deviation by sample size); measured thin counts per table | C | Adaptive vs non-adaptive version, full-table points, fixed and responding clones |
| 3 | Trust old profiles less when the seat's live behaviour conflicts with them | Sizes can be copied; 80-90% of teams change each round | C | Simulated: recogniser with and without the live-rate check, scored on points, not accuracy |
| 4 | Bring our rare-spot rates nearer break-even where an informed opponent could use the gap | Our fold to re-raises was 89% vs field 65% | C | Per gap: what an informed opponent gains, what closing it costs against uninformed ones; ship if the full-table result is not worse |
| 5 | Responding clones in the test rig | The cloned field cannot see a counter-strategy; some top teams do respond | C | Does adding them improve the ordering test? (running) |
| 6 | Two policies in one upload, assigned per table, for same-round comparison | Build-hour fields differ between practice rounds | C | Rehearsal, baseline vs one challenger only. Assignment must be balanced and unrelated to cards or seat strength (check the split by hand strength and position), must survive the memory mechanism, and must be recoverable in analysis. Rules permitting. No control arm in scored rounds without a stated reason: it has a cost |
| 7 | Re-aggression style (4-bet and call re-raises wider) as the counter to wide re-raising | Literature; Boston's top teams did it | C | Style-matchup simulations (running), then a practice round |
| 8 | Tight mode against tables where others are busting each other | Bystander gains are small with 8 left (+0.4 per collision), large with 4 (+5.8), by ICM arithmetic | C | Same simulations; trigger must be measured all-ins per table, not "the table is aggressive" |
| 9 | Pick sizes from the measured response to sizes | Fold-rate table (observational) | C | Sizing-only replay on fixed deals |
| 10 | A plan for the last round and for leading | Argument; a static bot lost about a point a round | C | Cannot be tested on regional data; decide the rule in rehearsal and keep it simple |

Nothing in this section is grade B yet. Only two changes we have ever made are: v6's fold-to-flop-raise
fix (+2.3 real) and the ICM fix (about +1.4 modelled).

## 3b. Style-matchup simulations (cloned field, regional variant)

All grade C: simulation only, frozen opponents, and the simulator's ranking reliability is still being
tested. "Holds" means over 2 points and the same direction under both clone settings. Source:
`research/finals_prep/metagame/REPORT.md`.

| Finding | Strength in simulation | What it suggests testing |
|---|---|---|
| Styles form a cycle: wide re-raising beats an all-tight field (+5.7), limp-or-shove beats an all-wide field (+2.6), tight beats an all-limp-or-shove field (+2.3) | Holds | Build the three corners (pressure, shove-heavy, tight) and let practice rounds pick; plan the challenger as the next style in the cycle after the leader |
| Against the actual top 20, limp-or-shove, tight and wide are within 1 point | Unresolved | Nothing to choose in advance: the real field decides |
| Wide re-raising wins the full regional field but loses 3 points when weak teams are removed; limp-or-shove loses about 0.4 | Holds | Don't assume the regional winner's style transfers to 20 strong teams |
| Tight is the worst main answer to wide re-raisers; it pays only against shove, limp or loose-calling fields | Holds | Trigger tight play from measured opponent types, not "aggression"; against re-raisers fold less to 3-bets and re-shove |
| Calling off all-ins much more often costs 1-3 points | Holds | Keep call-offs narrow in any tight mode |
| The averaged "balanced" profile is never best | Holds, but it is an average of rates, not a coherent bot | Build balanced as a coherent equity bot or replace it with tight |
| Our bots score about 14-15 against a top-20-only field, not 18-20; v10 folds 89-93% to 3-bets vs 70-77% for the strong styles | Holds for the drop | Expect lower scores; fold no more than about 75% to 3-bets (also suggested by the identity study) |

Adopted into the prompt pack on 2026-11-12 (Samuel's call, still grade C): the three build styles are now
pressure, shove-heavy and tight, and every style folds no more than about 75% to re-raises.

## 4. Simulator validation: what is established and what is running

- **Established:** in two cases the cloned field got a large difference right in sign and rough size, and
  our own score within about 1 point in the same round.
- **Not established:** that its ranking of candidates is right when the difference is under about 2
  points; that it holds against opponents who respond; that it holds for a 20-strong field.
- **Running now:** a pre-registered ordering test on all 14 real results from the regional: fits from
  pre-round data only, every adjacent bot pair, three opponent models (default, more bluffs, responding),
  wrong-sign cases named. No tuning on the targets.
- **No untouched holdout exists** for our own bots: every scored round has been looked at. The true
  out-of-sample tests are the rehearsal and Sunday's practice rounds.
- A synthetic 20-team field is not expected to reproduce our regional scores; those are different
  competitions. It is judged on behaviour profiles and on rank dynamics.

## 5. What has not been done at all

A full rehearsal of the two-person decision loop. Infrastructure exists (`emu/`); no window has been run
end to end with both of us making the decision against the clock. This is the next milestone (see the
playbook), ahead of any further research.

## Do regional numbers transfer to a new variant? (13 November)

Bay Area (`flop_discard_reveal`) and Boston (`flop_auction_holdem`) fields compared on the same statistics
(`research/finals_prep/adaptation/res_q2.txt`, `res_boston.txt`; a new 3,000-table extraction of each R1/R6):
fold to 3-bet 67.2% vs 67.3%; open-shove first in at <=10bb 41.3% vs 40.6%, 10-15bb 22.0% vs 24.2%, 15-20bb
9.8% vs 12.5%; call a shove <=10bb 19.8% vs 19.7%; fold to a flop bet 53.5% vs 52.8%; PFR 22.2% vs 21.5%; only
VPIP moved (about 3 points higher with 3 hole cards). Teams changing bots 78-90% vs 75-84% per round; unchanged
bots -0.53 ± 0.08 vs -0.46 ± 0.09; practice above the next scored round +0.37 vs +0.42. Shrinkage test: a prior
from the other variant (weight 4) was as accurate as the target field's own mean and cut per-seat error by
about a third in the first 1-8 chances (e.g. fold to 3-bet RMSE 14 vs 22 points at n=4); by n = 16 all priors
agree; a stale or heavy prior (weight 10 on round 1) hurt. **Grade A (measured, two regionals).** The plan's
earlier "70-85% fold to 3-bets" and "40-60% shoves at <=20bb" came from the pre-event simulated field, not
either regional, and are withdrawn (grade D).

