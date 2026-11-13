# Finals: start here

For Dylan and Samuel. This assumes you remember the regional and nothing since. Read this first (about
fifteen minutes), then the rehearsal sheet for tonight. Everything else is reference. Last updated
Thursday 12 November, evening.

## 1. What we learned since the regional

The Finals are on Sunday 15 November in San Francisco. Confirmed: 20 teams and no house bots. The
variant is announced at the start. We may bring prompts and notes but no code.

At the regional we finished 6th (376.71). 2 Curry won with 428.72, about 2.5 points per table per round
more than us.

- **Our own mistakes cost about 22-25 points; fixing them alone would have put us about 3rd.** They were:
  - over-calling flop and turn bets early;
  - over-folding after v6;
  - the SDK's ICM function scoring a busted stack as 0;
  - folding 82-89% to re-raises.

  v10 also had two counting bugs: the raise-frequency stat was inverted, and folds to our own bets were
  never counted.
- **The rest was style, and one rule in particular.** 2 Curry opened about 40% of hands and re-raised
  wide. Its bot also tracked each seat at the table: it re-raised a fresh opener 18% of the time, 43%
  after that seat had folded to one re-raise, and 62% after two folds. We folded to most re-raises, so it
  kept re-raising us. Ten of the other 19 top teams had some per-seat rule like this.
- **Almost everyone changed their bot every round (78-90% of teams).** For strong teams, changing only
  kept them level: top-20 teams lost about 0.65 points per table per round whether they changed or not.
  So the bot at the end of the build matters a lot, and you still have to keep improving.
- **The field gets harder at the Finals.** Every finalist knows wide re-raising won. By round 5 at
  Boston, the top teams already folded only 58% to re-raises and re-raised back 23% of the time.
- **Big jumps come from rewrites, mostly for teams far behind.** 81 of 92 big gains came from rewrites,
  but only 3 of those were by a top-20 team. For top-20 teams, rewrites lost 0.68 points on average.
- **Bet sizes identify a team quickly.** With last round's data, the right team is named 73% of the time
  by hand 20. We used the same sizes all night and were identifiable by about hand 7. Hiding our sizes
  works for one round at most and costs value, so we don't hide them. Instead we avoid big exploitable
  gaps, such as folding 89% to re-raises when the field folds 65%.
- **No style wins everywhere; they form a cycle.** In simulation, wide re-raising beats a field of tight
  bots, limp-or-shove beats a field of wide re-raisers, and tight beats a field of shovers. Against a
  strong field the three were within a point of each other. So we build all three and let the real
  field choose.
- **Expect lower scores.** Against a field of only strong teams, our regional bots scored about 14-15
  points per table in simulation, not 18-20. The average is 12.5.

## 2. The game plan

1. **Before the start (about 2 hours):** four research agents work in parallel on likely twists, what
   wins, a build plan and a test plan. Then one agent merges their notes into a plan.
2. **Build hour:**
   - minute 0: paste the first prompt and give the coding agent `docs/TWIST_NOTES.md` with the kit;
   - by minute 10: a minimal legal bot is uploaded;
   - by minute 15: a test harness that shows decision times, the bot's memory and which branches fire;
   - by minute 20: today's hand ranking simulated (a twist can change it completely: in one mock
     variant pocket pairs became the worst hands), and every style defined on that ranking;
   - then **one shared platform** (rules, equity, per-seat counters, memory, safety) with **three
     styles** on top as parameter sets: wide-pressure, shove-heavy and tight (in simulation each beats
     a field of one of the others, so the real field picks);
   - practice rounds at minutes 20, 30 and 40 each play a different style, and minute 50 re-plays the
     leader;
   - the best real score goes live for scored round 1, and the runner-up becomes the **challenger**.
3. **Every 20-minute window:**
   1. download the hand history;
   2. five analysis agents look for our leaks;
   3. six to ten candidate changes are built and tested;
   4. **one** tested change goes into the live bot;
   5. the challenger plays the practice round.

   We swap the two if the challenger clearly scores better.
4. **Adapt to individual seats, not to the "table mood".** Each seat's live counts are blended with what
   we know about its team, and every adjustment is capped. Against seats that raise a lot, call off and
   re-raise wider; folding more is the wrong answer to aggression.
5. **Evidence before shipping.** Every finding is graded (`docs/EVIDENCE_TABLE.md`). An analysis that
   sounds convincing is a *candidate* until it is tested, and only tested changes go into the live bot.

## 3. What we tested today, and what it changed

We ran the prompts themselves, clean-room, the way they'll be used on Sunday:

| Test | Result | What changed |
|---|---|---|
| The first prompt on two unfamiliar mock variants (a turn draw, a flop card pass), 60 minutes each | Legal bot in under 2 minutes, three styles in under 20. Each run produced real silent bugs, caught only by the scripted checks | Test harness by minute 15; rebuild the current hand from its history (not memory); test the ICM call/fold step against reference values; define styles on today's ranking; team recognition moved out of hour one |
| The leak finder on our real round-1 data, knowing the answer | In under 3 minutes it found the leak v6 fixed (calling raises of our flop bet, about 1.8 points per table) | Compare before-the-flop actions within the same position; rank leaks after pooling across stack sizes |
| The test-rig prompt, 60 minutes | Paired runner in 2 minutes, sparring in 4, replay with zero drift; the rushed cloned field failed its own check | Split into a build-hour brief (runner, sparring, replay) and a between-rounds brief (cloned field on Modal) |
| Tonight's rehearsal, compressed to 25 minutes | Ran end to end: rounds, uploads, results and downloads | Ready for 8 PM |

The silent bugs the build tests made are the same kinds we shipped at the regional: a "folded to our
raise" counter that never counted, and an all-in call that counted the pot twice. The checks in the
first prompt catch them, so never skip the checks to save time.

## 4. Who does what

| | Dylan | Samuel |
|---|---|---|
| Owns | The bot: building, changing, packing, uploading, confirming the active bot | The clock and deadlines; the analysis; the one-page recommendation each window |
| Agents (own Claude account) | Main bot session; 3-5 candidate builders | Manager; extraction + 5 area analyses; team profiles; test rig; poller; 2-5 more candidate builders |
| Other compute | | Codex (the team's $250) for 2 bug hunters; Modal for the test rig |

The decision at each deadline is made together. Details: `docs/Compute_and_Roles.pdf`.

## 5. Before Sunday

- [ ] **Tonight, 8 PM: the rehearsal** (`docs/REHEARSAL_TONIGHT.md`).
- [ ] Decide who claims the $250 Codex credit before anyone opens the link (suggested: Samuel). It
      goes to whichever account opens it first.
- [ ] Get the friend's $170 into the team Modal workspace (Dylan's). Set the spend limit there.
- [ ] Cap auto-reload on the Stanford VRITS Anthropic org (about $138 left, auto-reload is on).
- [ ] Find out Pittsburgh's variant and results (it ran 12 November).
- [ ] Both laptops: Claude Code, GitHub and Modal signed in; Codex installed and signed in.
- [ ] Make a fresh private repo for Sunday containing only `docs/FIRST_PROMPT.md`, the playbook and
      notes. No code.
- [ ] Read `docs/FIRST_PROMPT.md` once all the way through, so you know what each prompt does.

## 6. On the day

**Build hour** (minutes from the announcement):

| Minute | What happens | Who |
|---|---|---|
| 0-5 | Fetch the kit (setup skill). Paste the first prompt (prompt pack Part 1) and give the agent `docs/TWIST_NOTES.md`. Read the Format page: round weights, payouts, anything unusual | Both |
| by 10 | Minimal legal bot uploaded; read the active bot's name out loud | Dylan |
| 10-50 | Shared platform first, then three styles in parallel. Test rig starts at about minute 15 (Part 3a: paired runs and sparring; the cloned field waits for 3b after round 1) | Dylan builds, Samuel measures |
| 20, 30, 40 | Each practice round plays a different style | Dylan uploads |
| 50 | Practice round re-plays the leader | |
| 50-60 | Hands off. The best real-field scorer is active for scored round 1 | Dylan |

**Every window after that.** A practice round starts 10 minutes before each scored round and plays
whatever bot is active, so each window has two uploads.

| Time to scored round | What happens | Who |
|---|---|---|
| T-20 | Scored round starts. The challenger is already packed and tested | |
| T-13 | Scored result and download land. Samuel starts the manager (Part 5) | Samuel |
| T-12 | Challenger uploaded and confirmed active | Dylan |
| T-10 | Practice round starts and plays the challenger | |
| T-9 | Live bot put back as active straight away | Dylan |
| T-8 | Practice result lands. **Decide together:** live bot, live bot plus this window's change, or the challenger | Both |
| T-6 | Chosen bot tested under upload-test conditions (no time bank) | Dylan |
| T-3 | Uploaded; read the active bot out loud from the team page | Dylan |

If the challenger isn't ready by T-12, skip it that window. Once the live bot is back at T-9, a missed
deadline just means the previous live bot plays. Never rush an untested upload.

## 7. How we decide

- **Live bot:** one change per round (two only if they touch unrelated situations), and only a tested
  one.
- **Challenger:** two to four changes, or a redesign. It only plays practice rounds. Default choice:
  the style that beats whatever is currently winning.
- **Every style:** never fold more than about 75% to re-raises.
- **Outside the top 3:** take the bolder option when the evidence is roughly even. A challenger ahead by
  about one standard error is worth playing.
- **Inside the top 3:** protect what works, more so in the heavy late rounds.
- **Stuck mid-table after two rounds:** put a fresh rewrite in the challenger slot.
- **What counts as evidence, in order:** real-field results (practice and scored), then replay testing,
  then the cloned field. The cloned field is a warning light, not a ranking. Beating our own bots proves
  nothing.
- **Never block a change because it makes us look unusual.** The regional winner looked nothing like the
  average team.

## 8. The documents, in reading order

| Document | When you need it |
|---|---|
| `docs/START_HERE.md` (this) | Now |
| `docs/REHEARSAL_TONIGHT.md` | Tonight |
| `docs/Finals_Game_Plan.pdf` | Printable version of the plan; keep it open on the day |
| `docs/Compute_and_Roles.pdf` | What compute we have and whose agents run where |
| `docs/TWIST_NOTES.md` | Give to the coding agent at minute 0: how to value 12 plausible twists, a checklist for any new phase, five silent-bug tests |
| `docs/FIRST_PROMPT.md` | Every prompt you will paste, in order (Parts 0-5), with the evidence (Part 6) |
| `docs/FINALS_PLAYBOOK.md` | The longer reasoning: what went wrong, the format, the operating model |
| `docs/EVIDENCE_TABLE.md` | How sure we are of each finding, and the test each proposed change needs |

## 9. Not settled yet

- Pittsburgh's variant.
- Whether the cloned field ranks candidates reliably. A test is running; until it reports, use the
  cloned field only to catch disasters.
- The cloned field on the day: a clean-room test built the paired runner, sparring and replay inside
  30 minutes, but its cloned field, built in a hurry, failed its own check. It now waits until after
  round 1 and runs on Modal (Part 3b).
- Whether this many agents is manageable for two people, whether either Claude account gets throttled,
  and whether Modal queues. Tonight answers these.
