# Finals playbook (Sunday 2026-11-15, San Francisco)

For Dylan and Samuel. No code may be brought into the event; prepared prompts and knowledge may. Everything
below is knowledge or a prompt. Numbers are from our regional hand histories, the portal's API (read with our
key on 2026-11-11), and the Boston regional (a friend's data and account).

## 1. What went wrong at the regional, and what first place took

| Place | Team | R1 | R2 | R3 | R4 | R5 | R6 | Weighted total |
|---|---|---|---|---|---|---|---|---|
| 1 | 2 Curry | 20.40 | 20.24 | 21.15 | 20.47 | 20.41 | 20.08 | 428.72 |
| 2 | Lemonade | 19.78 | 19.34 | 20.67 | 20.62 | 20.09 | 19.61 | 421.08 |
| 6 | avalon | 18.10 | 16.73 | 19.05 | 18.26 | 17.95 | 17.53 | 376.71 |

**The gap to 1st was 52 weighted points: about 2.5 points per table in every round.** Our known mistakes
explain about half of it:

| Mistake | Cost (weighted points) |
|---|---|
| Over-calling flop and turn bets in R1-R2 (fixed in v6; the data showed it after practice round 1) | 4-7 |
| Over-folding after v6: we folded 73/66/78% to heads-up bets by street, the field 52/45/48% | up to ~16 (≤0.9/table over R3-R6) |
| SDK `icm()` bug: busted stacks scored 0, so we folded profitable 2-3-handed all-in calls in R4-R5 | ~1.4 |
| Folding 82-87% to 3-bets while the field's 3-bet rate doubled (6.9% → 12.3%) | part of R6's -0.43 |
| **Total of known fixes** | **~22-25 → about 400: 3rd place** |

**The other ~27 points was a different bot.** 2 Curry scored 20+ in *every* round, including round 1, so
its first hour decided its result. Its style, measured from our tables:

| | 2 Curry | Lemonade | avalon |
|---|---|---|---|
| VPIP / PFR | 38-43% / 34-41% | 25-28% / 10-16% | 30% / 23% |
| 3-bet | **32-39%**, wide (half its shown 3-bets were outside the top 10%) | 13-22%, mostly jams | 16-17%, premiums only |
| Fold to 3-bet | 81-87% | 22-33% | 85-87% |
| Flop / turn fold to bet | 61-67% / 45% | 68-74% / 30-54% | 32% → 70% / 48% → 65% |

- **Our own release gate would have blocked the winner.** It required PFR 17-27%; 2 Curry ran 34-41%. The
  band was set from the field's median after v4's failure, so it protected us from bad aggression and from
  good aggression alike. v4 failed because it 3-bet blindly and then folded 96% to 4-bets and played badly
  postflop, not because its PFR was high.
- **Ranks barely move after round 1.** Bay Area round-to-round rank correlation was 0.76-0.83; Boston's was a
  median of 0.68. Most teams' placing was set by the bot they had at the end of the build.
- **Big jumps come from rewrites, not tweaks.** Boston: a team stuck around 45th had a subagent write a fresh
  "hail mary" bot after round 3 and gained 18 places in one round (+2 points per table). Our own v4 rewrite
  failed, but it was released without real-field evidence.
- **The Boston winner researched before the start.** Fable ran for ~1.5 hours before the build on past
  competitions (including our Stanford/Bay Area regional) and pokerbot design, then the team kept prompting
  all night. Teams at the Finals will have done the same about all three regionals.

**What it takes to win on Sunday:**
1. A strong first bot within the build hour, starting from research done beforehand.
2. Postflop calibrated to the field from the first practice round: fold to bets near the field's rates, not
   far above or below.
3. Real preflop aggression (wide 3-bets with disciplined folds to 4-bets) judged by the field's response
   (their fold to 3-bet, re-raise rates), never blocked by a fixed VPIP/PFR band.
4. Three independently written bots with different styles from minute 10, the winner chosen by practice-round results.
5. Every library function a decision depends on unit-tested with edge cases (the ICM bug).

## 2. What we know about the Finals format

- 20 teams (5 per regional + 5 wildcards): 3 tables per iteration (8 + 8 + 4 teams + 4 non-scoring fillers).
  Opponents are all strong teams, so the soft spots that paid at the regional are gone.
- A different variant, announced at the start with the kit. Regionals so far: Bay Area = 3 hole cards,
  discard one and expose one on the flop; Boston = the flop is bought at a sealed auction with a separate
  currency. **Pittsburgh runs tomorrow (11-12): get its variant and results.** Each variant added a decision
  phase with a new action kind and new `state.variant` fields.
- **Round weights vary**: Bay Area 1-6 (`round_weighting: linear`), Boston 1, 2, 3, 5, 8, 13. Read the Format
  page; with Boston's weights the last round is 13/32 of the total.
- The platform supports, per competition: a `final_weight` revealed late (`final_revealed_at`), a held
  leaderboard (`leaderboard_held`), per-round culling of teams out of contention (`contender`,
  `culled_at_look` in results) and ICM luck correction (`icm_luck_correction`). None were used at the
  regional. Expect any of them.
- Bay Area's clock (portal timestamps): four practice rounds in the build, at minutes 20, 30, 40 and 50
  (1,000 → 2,500 → 10,000 → 12,500 iterations), then a 1,000-iteration practice about 10 minutes before
  each later scored round. Practice results came back in 1-3 minutes; scored results in 6-8. Scored rounds: 20,000 iterations at Bay Area,
  10,000+ at Boston.
- Uploads auto-activate when they pass the test match (the portal now says so). 30-second cooldown.

## 3. Roles and timeline

| Who | Owns |
|---|---|
| **Dylan** | the coding agents that build and change bots (the main bot and the style tracks), packing, uploads, confirming the active bot |
| **Samuel** | the clock and deadlines; the manager agent and every analysis under it; the live dashboard; the one-page recommendation each window |

**Per-round deadlines.** A practice round starts 10 minutes before every scored round and plays whatever
bot is active, so each 20-minute window has two uploads: the challenger for the practice round, then the
live bot for the scored round.

| Time to scored round | What happens |
|---|---|
| T-20 | Scored round starts. The challenger is already packed and tested from the last window. |
| T-13 | Scored result and download land |
| T-12 | Challenger uploaded and confirmed active |
| T-10 | Practice round starts and plays the challenger |
| T-9 | Live bot put back as active straight away (re-upload the current one) |
| T-8 | Practice result lands. **Decide: live bot, live bot with this window's change, or the challenger.** Chosen bot packed. |
| T-6 | Tested under upload-test conditions (no time bank) |
| T-3 | Chosen bot uploaded and confirmed active on the team page |

- The challenger's practice score is its validation, and it arrives in time for the same round: at the
  regional, practice results landed 1-3 minutes after the practice started (T-9 to T-7).
- It is 1,000 iterations, about ±0.6 points, against ±0.13 for the live bot's scored result. Swap on a
  lead of about one standard error when we're outside the top 3, two when we're inside.
- The scored download lands about 3 minutes before the practice round, so the change the live bot gets
  at T-3 was built and tested on the previous round's download. Only quick items (a bug fix, refreshed
  profiles) can use the newest one.
- Practice start times drifted at the regional (7-10 minutes before the scored round). The poller should
  announce "practice started" and "practice result"; go by those, not the wall clock.
- If the challenger isn't ready by T-12, skip it that window: a challenger left active at T-0 plays the
  scored round. Once the live bot is back at T-9, a missed deadline means the previous live bot plays.
- Confirm on the day that the Finals keeps this schedule (Format page).

**Before the start (about 2 hours):** four research agents in parallel (prompt pack Part 0), merged into a
plan. Sign in to Modal.

**Build hour:**
- 0-5: read the kit and the Format page (weights, payouts, anything unusual in `state.config`).
- by 10: a minimal legal bot uploaded and confirmed active, so a bot is always live.
- 10-50: three bots with different styles (balanced, wide-pressure, shove-heavy) built in parallel; the
  test rig starts at about minute 15. Practice rounds 1, 2 and 3 (minutes 20, 30, 40) each play a
  different style; practice 4 (minute 50, the largest) re-plays the leader to confirm. Practice 1 is only
  1,000 iterations (about ±0.6 points), so put the style we trust least there.
- 50-60: hands off. The best real-field scorer is active for scored round 1.

**Every window after that:** the round loop (prompt pack Part 5).

## 4. The operating model

**How many bots.** Three during the build, two afterwards.
- The build has four practice rounds, so three styles can each get one real-field score and the leader
  one confirmation. A fourth style would have to be chosen blind (more
  styles can still be filtered in simulation).
- After the build there is one practice round between scored rounds, so one alternative can be tested on
  the real field per window: the **challenger**, the best of the styles that didn't win the build. The
  third bot is dropped.
- The challenger slot is also where a hail-mary rewrite goes if we're stuck outside the top 3 after two
  rounds.

**How many changes per window.**

| | Live bot | Challenger |
|---|---|---|
| Changes shipped | 1; 2 only if they touch unrelated situations | 2-4, or a redesign |
| Why | its scored result must stay readable, and a bad change costs weighted points | it only plays a practice round, and it is judged as a whole |
| Kind | evidence-backed fixes from the leak finder | bigger bets: a style element, more aggression, a rewrite |

Outside that count, every window, both bots get: bug fixes, refreshed team profiles, and any change proven
on one that suits the other. If the challenger's practice score clearly beats the live bot's last result,
they swap.

**Test far more than we ship.** Six to ten candidate changes are built and tested each window; one ships.
The best of many always looks better than it is (about +0.5 points by luck among ten), so the top two are
rerun on fresh deals before either ships.

**Agents per window** (prompt pack Parts 2-5; start them all at once):

| Agents | Job |
|---|---|
| 1 manager | starts the rest, merges everything into one page with a recommendation |
| 1 + 5 | one extraction pass, then five area analyses: before the flop, after the flop, the variant's own phase, short stacks and the last four players, how the field treats us |
| 6-10 candidate builders | one change each, on a copy of the live bot |
| 1 test rig | replay testing, the cloned field and paired runs on Modal, confirmation runs |
| 2 bug hunters | independent review of the live bot and the challenger |
| 1 per team ahead of us | that team's weaknesses and a tailored counter for its profile |
| 1 profiles | rebuilds every team's profile from the latest download |

Split the agents across both our Claude accounts so neither hits a burst limit, with an API key as
overflow. Don't hold agents back to save usage: an untested idea costs more.

**Budget beyond Claude** (as of 2026-11-11). The organizers cover no compute or tools; the team gets
$250 in Codex credits in total. Samuel's OpenAI organization also has $1,000 in API credits.
Modal is on us.

| Money | Use it for |
|---|---|
| Codex credits ($250 for the team) | the two bug hunters and one candidate builder per window, and one of the three style bots in the build hour: a different model makes different mistakes, so its review and its design are more independent than another Claude agent's |
| OpenAI API credits ($1,000) | overflow for the same Codex jobs once the event credits run out or a Claude limit hits; rehearsal runs before Sunday |
| Claude (both subscriptions) | everything else: the main bot, the manager, the analyses |

Before Sunday: install Codex on both laptops, sign in, and run one bug-hunt prompt from the pack through
it in the rehearsal so the first use isn't on the day.

**How we decide.**
- Only the top 3 win. Outside the top 3, take the bolder option when the evidence is roughly even; a
  challenger that looks better by about one standard error is worth playing. Inside the top 3, protect
  what's working, more so as the round weights grow.
- Experiment early: round 1 is 1/21 of the score with linear weights (1/32 with Boston's); the last two
  rounds are about half.
- Estimates use all the evidence in proportion to its strength (weighted blends, no hard thresholds).
  Thresholds are only for all-or-nothing choices like switching bots.
- The real field is the judge: practice-round and scored results first, then replay testing, then the
  cloned field. A local win against our own bots decides nothing.
- Never gate a change on looking like the average team. Our regional gate would have blocked the winner.

**Prompts:** all in `docs/FIRST_PROMPT.md` (Parts 0-5), with the evidence for each line in Part 6. The
live-dashboard poller: have Samuel's agent write a read-only script that polls
`/api/competitions/<id>/standings`, `/tournaments` and `/api/tournaments/<id>/results` every minute with our
portal key, downloads each round's hand history as it completes (copy the download URL once from the
browser's Network tab) and hands it to the manager.

## 5. Rehearsal

`emu/` replays all of this with 19 simulated teams (see `emu/README.md`). Practise the roles above in it, on a
mock variant, before Sunday.
