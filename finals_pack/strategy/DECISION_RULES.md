# How we decide (both sessions, every subagent, every turn)

This page always applies. It overrides anything older or vaguer in the other documents. The research behind each
line is in `EVIDENCE_TABLE.md` and `FIRST_PROMPT.md` Part 6.

Who is who (`CLAUDE.md` §1): the **BUILDER** session (Dylan; subagents `platform`, `stylist`, `challenger`,
`bughunter`) owns the bot and asks the humans which bot plays; the **RESEARCH** session (Samuel; subagents
`theory`, `analyst`, `tester`, `scout`) owns the maths, the data, testing, opponents and the T-9 recommendation.
`scripts/clock.py` posts every step, cut-off and reminder below into the inbox of the session that acts on it.

## 1. What we are playing for

Only the top 3 teams are paid: $100,000, $50,000 and $25,000 (official rules). Finishing 4th pays the same as
finishing last, so our goal is the best chance of a top-3 finish, not the smallest chance of a bad round. (50 / 30 /
20 is not the prizes: it is the points a table gave its 1st-3rd at the regional, and the rules say the points per
place can change with the variant; they are announced at minute 0.)

Freezing doesn't hold a lead. At the Bay Area regional, top-20 teams fell back about 0.65 points per table per
round **whether or not they changed** (changed minus unchanged: −0.01 ± 0.18). For top teams, **rewrites had the
same average as standing still but three times the spread**: 24% improved, by up to +3.8, against none of the
unchanged ones. Most big gains in the whole field came from rewrite-scale changes. And our most cautious calls
there (a stats band on releases, a freeze on the fold rules) cost us more than any risky one. When a choice is
close, prefer the option that learns more or gains more.

**The plan is a default, not a mandate.** Everything below §2 was written before anyone saw today's variant or
this field. Strong teams will do things nobody predicted, and the field moves every round. When today's data
says a better path exists, take it; the only things that never bend are the hard rules.

## 2. The few hard rules (and why)

These protect against losing a whole round. Nothing else on this page is a hard rule. (`CLAUDE.md` §4 adds the
working rules that never bend either: the portal is read-only for agents and only Dylan uploads; no pattern kills;
never block your turn; Modal has only two deployed apps, `avalon-rig` (`tester`, up to 40 containers) and
`avalon-theory` (`theory`, up to 20), and the other roles call them or run locally, sharing 20 (80 in all).)

1. **Every bot we upload is legal and fast**: zero failed decisions in the checks, the kit's check passes,
   and it passes the upload test with no time bank. *(A bot that times out or acts illegally checks when
   checking is free and otherwise folds, and can zero a round.)* **A bot plays a scored round only with a `tester` verdict that includes a heads-up run.**
   *(In a speedrun a release with no verdict shipped a heads-up regression of −1.9 ± 0.4.)* A verdict's first words are
   "fit for a scored round" or "not fit": fit means correct, fast, and a heads-up run no worse than the live bot's
   by more than 2 SE.
2. **Only upload a zip that has been through that test**, put the `state/live.json` bot back as active after the
   practice round, and have a tested bot active by T-3 every round. *(A missed upload or an untested zip can zero
   a round. A missed deadline is a failure to report and fix, not a safe outcome.)* Each round plays a snapshot of
   every team's **active** bot taken at its start. Making an already-uploaded bot active is a click on the portal, not
   an upload. On the organizers' newest pages an upload that passes its test also becomes active by itself (at Bay Area
   it did not: BUILDER settles which holds after v1's upload). Either way, upload nothing inside a window that is not meant to be the next bot to play (a zip uploaded "to have it ready" would replace the active bot), and confirm the active bot in `state/status.md` after every upload and every click. Assume the upload **cooldown** may be up to 5 minutes until the Format page says otherwise (read it at
   minute 0; `state/status.md` shows the figure the portal itself states; it was 30 seconds on the regionals' pages, in
   the regional's API and on the Finals competition on Saturday afternoon), so
   plan at most two real uploads per window (§3, "Uploads").
3. **The rules card is right**: players per table, stacks, blinds, hands per match, round weights, payouts
   and the cooldown come from the kit and the Format page. *(At a rehearsal we ran every test at the wrong
   table size.)* Every figure on this page given in points per table (0.7, 0.8, 1.4, 2.0, 2 and 3) assumes 8 players
   and 50/30/20. By minute 5 `tester` works out today's per-table spread and the multiplier (spread / 17.9), which
   `platform` writes in `bot/rules.json`; both sessions multiply those figures by it (in case F at 50/30/20 it is
   18.9 / 17.9 = 1.06). Bars given in z do not change. Role-file check values marked 50/30/20 are not used on another
   payout.
4. **No pre-written bot code; hand histories never go into git.** *(Event rules.)*

## 3. Decisions, written in advance

The rule's answer **is** the default. If nobody answers in time, the rule's answer plays, not "no change".

**Which bot plays a scored round** (worked out by the RESEARCH session, whose recommendation reaches BUILDER by T-9;
asked by the BUILDER session at T-8; decided by the humans):
- **Measure the challenger against the field, not against a different field.** The challenger's practice round
  and the live bot's last scored round had different opponents (in practice rounds most teams test new bots). So
  compare each with **yardstick teams**, the teams `scout`'s drift check says did not change bot between the two
  rounds: edge = (challenger's practice score − the yardsticks' practice scores) − (live bot's last scored score
  − the yardsticks' scored scores). With fewer than 4 yardsticks, use scores minus the field median, and say so.
  No hand file for the scored round means no yardsticks: use scores minus the field median (`results.json` is enough).
  Every score in this comparison is taken from the round's results file (`results.json`), never from a hand file.
  Pool the challenger's practice rounds when its core is unchanged. SE of the edge: the standard deviation of the yardstick teams' own (practice score − last scored score),
  times √(1 + 1/number of yardsticks), when there are 6 or more yardsticks; with fewer, 0.8. Never below 0.7. z = edge /
  SE. Give the edge in points too, and say so if the SE is above 1.0. (0.8 and 0.7 are points per table at 8 seats and
  50/30/20: times the day's multiplier, §2 rule 3.)
- Play the challenger if it passed rule 2.1 and:
  - **we are outside the top 3** (if the portal's standings are held, the standings are `tester`'s totals for all 21
    teams from each round's results x weights; only if those can't be computed either are we treated as outside the
    top 3): z ≥ **0.5**
    (**the last-rounds bar**: z ≥ 0 in the last two rounds: a coin flip with upside beats certain 4th);
  - **we are in the top 3**: z ≥ **1.0**, or z ≥ 1.5 if our lead over 4th on the standings is more than 3 x the
    coming round's weight, in the standings' own points (before a round of weight 4: more than 12).
- Otherwise the live bot plays, with this window's changes (below).
- An earlier released bot with a verdict is a candidate like any other: compare its last scored round with the live
  bot's against yardstick teams, same bars.
- BUILDER writes the question in `state/decisions.md` and asks it in its terminal, with the rule, both bots'
  numbers and the rule's answer. The rule's answer plays at T-5 if no human has answered (BUILDER applies it with
  `scripts/live.py`); either human can overrule it, unless the other has given the opposite answer: then the rule's
  answer stands until they agree, and both sessions say so to both humans at once. Dylan makes the click the rule's
  answer needs even if he argued against it. If he won't, the live bot stays active: BUILDER re-declares it and records
  why. If the portal still shows the old bot at T-3, BUILDER says so once to Dylan and has RESEARCH ask Samuel to fetch
  him; the click stays valid until the round starts. If the round starts on the old bot, BUILDER re-declares the bot that
  played (`live.py`), and the next window compares against it.
- The practice's download (stage `Round k.5`) lands near T-8: before the decision only `tester`'s field-adjusted
  edge matters; the full analysis loop on it runs after T-3.
- **Round 1:** the live bot is `tester`'s adjusted best scorer of practices 1-3 **among bots whose verdict has a
  heads-up run at b50**; a higher-ranked bot whose verdict lands by T-4 replaces it by a click, with no question asked
  (declared at b50 with `scripts/live.py`, no question asked then); practice 4's bot, if different, is the challenger; the edge = each
  bot's practice score minus the yardstick teams' scores in the same practice; the same bars; asked once, at T-8 of
  round 1. Between two close candidates for round 1, prefer the more aggressive: this is one sentence, not a rule, and
  worth at most 1 point (early practices over-reward tight play).

**Changes to the live bot each window:** every independent change that clears the bar, each in a different
situation, each behind its own on/off setting, each with a branch-fired count, the combined build passing rule
2.1. Usually one to three; more is fine when each is independent and tested. A change that targets a rate (e.g.
"fold to 3-bets at 74%") must show that rate in a local run (within about 5 points of the target) before it ships.
*(In a rehearsal a change aimed at 74.6% played at 92.8% because only "it fired" was checked.)* Each change needs
real-data support of z ≥ 1 when we're outside the top 3 and z ≥ 1.5 in the top 3; below that, it goes to the
challenger or the next practice round to be measured first.

**Exploration (every window, at any standing).** One 1,000-table practice round can only tell apart bots about
1.4 points apart, so small tweaks are invisible there and the practice slot is wasted on them. Use it for
**different designs**. Explore-then-commit is the classic way to lose a moving game; keep several whole
alternatives alive and re-choose as results come in.
- **Build hour:** at least one practice round plays a design derived fresh from today's rules (`challenger`'s
  clean-room design D), not from the regional style notes. Which bot plays each practice is the most
  informative test, chosen by the BUILDER session (declared with `scripts/live.py`, as is the round-1 bot; after
  round 1 only scored-round bots are declared: see "Uploads").
- **Until 30% of the total weight has been played:** at least every other practice round plays a *divergent*
  challenger (a different style class or a rewrite, not the live bot plus tweaks), even when we're in the top 3,
  unless our lead over 4th is that big (more than 3 x the coming round's weight, as defined above).
- **After that:** `challenger` keeps one divergent line alive as insurance against a field shift; raise the
  budget again whenever a PLAN CHALLENGE stands or we are behind 3rd.
- Divergent candidates are judged by the real field (practice rounds). The cloned field may veto one only if it
  predicts a loss of 2 points or more and the reason is understood.

**Plan challenges.** Any session or subagent whose evidence says a plan assumption (§5) or the base style is wrong
for today raises a PLAN CHALLENGE: a subagent reports it at once to the session that spawned it, and that session
tells the other one (`SendMessage` to BUILDER or RESEARCH, and `say.py --record`). Both sessions put it to their
human at once, in plain words. RESEARCH records it once in `state/decisions.md` (one challenge, one entry; BUILDER
adds its view to that entry, never a second one). By default BUILDER has `challenger` build the alternative for the
next practice round it can be released for (released by T-15 of that window; a challenge raised later targets the
practice after). BUILDER redirects the running `challenger` to it unless a human says to keep both lines. Nothing from a
challenge enters this window's live bot unless it is already a validated `one-change` line with a tested build by T-8. A challenge never waits for the next scheduled step, and never skips a hard rule or a
test.

**Uploads.** `state/live.json` (set only by the BUILDER session, with `scripts/live.py`) is the bot that should be
active for the next round that counts toward the plan: in the build hour, each practice pick and then the round-1
bot; after round 1, the scored-round bot only. A window's challenger is never declared with `scripts/live.py`: it is
packed and tested by T-16, released by `platform` by T-15 (`releases/vN.zip`, a `VERSIONS.md` line with its
sha256), and at T-12 BUILDER tells Dylan its exact file to activate (he uploads it if it isn't on the portal yet);
it plays the practice round at T-10, and at T-9 Dylan puts the `state/live.json` bot back (a click). So a window
has at most two real uploads, about 8 minutes apart: the challenger at T-12 and, only if the chosen bot is a new
zip, the chosen bot at about T-4 to T-3. Putting the live bot back, and choosing the challenger, are clicks on bots
already uploaded: BUILDER tells Dylan which version to click in the portal's uploads list. Never let a cooldown
leave the chosen bot unuploaded at T-3. When in doubt about what is on the portal or which file is which, the live bot stays
active. (This is not a tie-break for the which-bot rule.) The T-9 put-back assumes the
practice started at T-10. Before saying "put vL back", BUILDER reads `state/status.md`: if the practice round is not
shown as started, the challenger stays active, BUILDER tells Dylan to wait (the clock's beep is early) and tells
RESEARCH. The live bot goes back the moment the watcher posts the practice's start, and at T-5 at the latest whether
or not it has started. A practice that starts after T-8 cannot give a result by T-6: the rule's answer is the live bot
and that practice feeds the next window. Only a challenger with a `tester` verdict may stay active past T-9. If uploads activate themselves, the
challenger's upload at T-12 is also its activation, the T-9 click is unchanged (it puts an earlier upload back), and
a new chosen bot uploaded at T-4 becomes active only when its upload test finishes: if that is after the round
starts, the live bot, active since T-9, plays.

**Deadlines: one switch deadline, T-4.** A bot can be the chosen bot only if at T-4:00 its zip is released, its
`VERSIONS.md` line has the upload test, and a `tester` verdict with a heads-up run is in `notes/LEDGER.md` (the
tester's own file, `rig/out/verdict-vN.md`, holds the same verdict). A verdict, an answer or a number that arrives
after T-4:00 feeds the next window. T-5 is when BUILDER applies the rule's answer if no human has answered; a rule's
answer that waits on a verdict ("v11 if its verdict lands, else v9") is settled at T-4:00. From T-4 to T-3 there is
only Dylan's click or upload. After T-3 nothing is decided or uploaded; the one thing still allowed is the click that
makes the declared bot active. If the chosen bot isn't active at the start, the live bot plays: report the miss and
its cause, and fix the cause for the next window. T-4 and the other T-minus times are defaults: a human may move one
in words for a window (`CLAUDE.md` §6, "Times are guides"), never past the point where an upload's test can still
finish before the start.

**Cut-offs (`scripts/clock.py` posts each one into the inbox of the session that owns it; deadlines cut scope,
never care).** At the regional, countdown reminders made bots rush and ship untested. Here a late step simply
loses its slot and the safe default plays, so there is nothing to gain by hurrying, and you are never asked to.
If you won't make a cut-off, deliver a smaller version or let the fallback happen; never skip a test to make one.
Sessions give every subagent a time limit in its brief and keep an honest ETA for each running job in their PLAN
file (`notes/PLAN-<session>.md`): a late estimate only lets the session re-scope early.

| Cut-off | If it hasn't happened | Who is told |
|---|---|---|
| T-12: a new challenger released (due by T-15) | Practice plays the most informative already-tested bot (else the live bot); the challenger keeps building for next window | BUILDER, Dylan (`challenger` isn't interrupted) |
| T-10: last round's data landed | No new **changes to the live bot** from that round: live bot plus already-validated changes. The which-bot decision still runs: if that round's result and the practice result are both in by T-6, `tester` gives the edge (yardsticks if the file exists, else scores minus the field median, said so) and the rule's answer follows it. If either is missing at T-6, the rule's answer is the live bot | both sessions, both humans |
| 3 min after data: round card written | `analyst` computes the decision numbers by hand; the card script is fixed after T-3 | RESEARCH (it stops the card job and re-briefs `analyst`) |
| T-8: one-change proposal recorded | No new-data change in the live bot; the idea goes to the challenger or next practice | RESEARCH (it stops `analyst`'s proposal), BUILDER |
| T-7: "Which bot?" decision asked | BUILDER asks it at once, with the rule's answer as the default | BUILDER, both humans |
| T-4: the chosen bot released and tested | The live bot (active since the practice round) plays; nothing is uploaded | BUILDER (it stops `platform`'s release), both humans (urgent) |

When the clock posts a cut-off, the owning session checks the files (`state/status.md`, `data/rounds/`,
`analysis/<stage>/card.md` with the stage name's spaces as '-', e.g. `analysis/Round-2/card.md`, `notes/LEDGER.md`,
`state/decisions.md`, `releases/VERSIONS.md`); if the step hasn't happened, it applies the fallback and tells the
people in the last column. Only the two sessions hear about cut-offs (at the times above, or earlier if an ETA is
late), so they can cut scope or add a helper; subagents are never told to hurry. A missed cut-off is reported with its cause at the next T-20 sync between the sessions.

**The challenger** is the team's exploration. Its job is to find what this field pays: a clean-room design, a new
style, the best response to the field's **measured** mix of styles, what a PLAN CHALLENGE or the winners lens points
to, or a fresh rewrite. A rewrite is a normal option at any standing, not an emergency. Data for a round lands at
about T-13, while the challenger is packed and tested by T-16 and released by T-15, so each challenger is built from
the data already in hand (it starts at the previous window's T-13) and targets the next window.

**Practice rounds are experiments.** Any bot that is legal and fast (rule 2.1's checks) may play one; the `tester`
verdict is needed only for a scored round. Pick the most informative candidate; a strength verdict from local tests
is not required.

**When to be bolder:**
- Behind 3rd, or outside the top 3 once 15% of the total weight has been played: the challenger slot carries a
  divergent design, and the bar drops as above.
- A PLAN CHALLENGE stands, or two or more plan assumptions (§5) are off (a field rate 2 points or more outside its band in two
  downloads running; a score by 2 SE or more): the plan's premise is
  false today; say so to both humans and put the alternative in the next practice round.
- The portal marks us out of contention: RESEARCH asks Samuel to ask an organizer at once whether such teams still
  play and can still be paid (BUILDER tells Dylan what it means and asks him for nothing else). Until the answer,
  nothing changes. If it is final, the last-rounds bar (z ≥ 0) applies from then on. Hard rule 1 still holds: no
  verdict, no scored round.
- The last round is 29% of all points with multipliers 1 to 6, 41% with Fibonacci, 51% with powers of two; the Finals was set to 1 to 6 on Saturday afternoon, re-read at minute 0: plan it from the round before (durable fixes plus any exploit
  we've been holding back).

**Worked examples** (how these rules play out):
- We're 5th, 1.2 behind 3rd before round 3; the challenger beat the live bot by +0.9 field-adjusted (z 1.3) in
  practice, passed the upload test and has `tester`'s verdict (heads-up run included); `tester`'s re-run of the
  edge isn't done. → Play the challenger, labelled "unverified".
- We're 1st by 4 points before round 5; a +0.4 change is at z 1.0. → Keep the live bot; play the change in the next
  practice round to measure it.
- We're 8th; three independent fixes (+0.3, +0.35, +0.25, z about 2 each, each behind a setting, combined
  build legal). → Ship all three.
- After round 2, `scout`'s field trend shows the top 5 teams now limp-or-shove at 15bb or less and fold to 3-bets
  58%; our wide-3-bet base loses to them. → PLAN CHALLENGE; `challenger` builds the counter-style; it plays the
  next practice round whatever our standing.
- The challenger fails the no-time-bank test once in three runs. → It doesn't play, whatever its score
  (hard rule 2.1); fix it for the next window.

**When behind schedule:** drop extra verification passes and polish first; keep idea generation, the field trend,
opponent profiles and the challenger. Never drop the hard rules.

## 4. Evidence: what each grade lets you do

- **A: measured on real event data** (practice or scored rounds, our hand histories). Act on it.
- **B: replay tests, the cloned field, paired local tests that agree with A-signals.** Act on it in the
  challenger and the practice slot; ship to the live bot when it is consistent with what the real field
  shows.
- **C: simulation, the regional only, or judgment.** A starting value or a hypothesis: try it where it is
  cheap to be wrong (practice rounds, the challenger, a setting that defaults off), and let the real field
  judge. Never block a change because a C-grade rule says otherwise.

Local wins do not predict the field (a bot of ours was +4.4 locally and 100th of 125). Use local play for
legality, speed and sanity; use the practice rounds for strength.

**Weigh signals by how solid they are.** A leak seen in two rounds' data in the same direction (`analyst` marks
these persistent in `notes/LEDGER.md`) is strong evidence: ship its fix. One round's number is weaker; pool rounds when you can.
When you pick the best of k candidates, discount its edge by about 0.6 x SE for the best of 2, 0.85 of 3, 1.0 of 4,
1.2 of 5, 1.5 of 10, 1.9 of 20 (the best of 10, each measured to about ±0.3, looks about +0.5 better than it is by
chance alone). This is for picking one of k measured the same way (round 1's pick, k fixes from one lens). It does not apply
to the challenger-against-live edge: the bars already allow for it. Never re-tune toward one practice round's
difference under 2 SE.

**Unverified is not wrong.** A `notes/LEDGER.md` line still `proposed` may be cited with the label "unverified".
Only a line **disputed with a reproduced counter-number** blocks a switch. If `tester` runs out of time re-running a
number, say so and decide (the bot's own `tester` verdict with a heads-up run is still required: §2 rule 1).

## 5. Starting values, not limits

**Behaviour rates and arithmetic are priors; hand rankings, equity cut-offs, twist values and style sizes are not**
(`theory` recomputes those for today's variant). Two regionals' *whole* fields looked alike (fold to 3-bets 67% in
both, open-shove at 10bb or less 41% in both), but their **top 20s did not**: Boston's top teams went from folding
75% to 3-bets to 57.5% by round 5 and 4-betting 23%, then partly reversed; Bay Area's barely moved. The Finals
field is the top teams of all three regionals, who studied the same lessons, so expect them to start near or past
that counter-wave.
- **Seat priors:** start each seat at the field rate with weight 4 (as if 4 observations). Until the first
  practice download use the regional values (FIRST_PROMPT Part 1); from that download on, `analyst` replaces
  them with the Finals field's rates (analysis/field_priors.json). Never use a weight above 10 for a field
  prior; team-profile priors from Finals rounds get weight about 30, capped.
- Use them, measure them, override them when this event's data says otherwise, and say why.
- **Folding to re-raises:** recompute the break-even fold rate for our open size and range (usually 65-75% in case R, about 59-68% with case F's antes, for
  3-bets of 3-3.5x). Folding far above it invites the seat-learners (2 Curry re-raised a seat 18% fresh, 43% after
  one fold, 62% after two). It is a default, not a cap: the regional winner itself folded 81-87%. It is about our
  opens facing 3-bets, not folding to 4-bets after our own light 3-bets.
- **Styles A/B/C are three corners to try, not a menu:** the cycle (wide beats tight, shove beats wide, tight beats
  shove) held only in pure simulated fields on the Bay Area variant; at realistic mixes no lead exceeded 1.4 points,
  and the clones could not rank strong teams. Today's rules may make another axis matter more (the twist,
  postflop, short stacks). Practice rounds decide.
- **Opponent exploitation is core work, not optional:** each of the 20 other teams sits at about a quarter of our
  tables in case F and about a third in case R (`CLAUDE.md` §8); profiles and counters run every window.
- **Read the round weights, payouts and cooldown from the Format page**; never assume weights 1-6. The portal's
  `round_weighting` names the series: linear (1 to 6), Fibonacci (1, 2, 3, 5, 8, 13: Boston and Pittsburgh used it) or
  powers of two (1 to 32). The watcher keeps it in `state/portal.json` (`comp_settings`) and posts any change. On Saturday
  afternoon the Finals competition was set to linear: re-read it at minute 0.

**Plan assumptions** (`scout` checks each against every download; a field rate 2 points or more outside its band in two downloads running, or a score off by 2 SE or more, is a PLAN CHALLENGE):
1. When we 3-bet an open, the opener folds about 60-70% of the time.
2. Open-limping loses money in this field, and so does flat-calling opens at 10bb+ without a stated postflop plan
   (flat calls are allowed where the style states the plan behind them; the check run still counts them).
3. The field open-shoves 35-50% of first-in chances at 10bb or less.
4. After the flop, big bets and raises are mostly strong hands (one pair should fold to raises).
5. Our base style is the best response to the field's measured mix (no style the top 5 share beats it).
6. The twist is worth what `theory`'s tables say, and the field uses it about as well as we do.
7. Scores are compressed near the field's mean (the points paid divided by the seats: 16.7 a table in case F with
   50/30/20, 12.5 in case R); differences under 2.0 between two practice rounds (1.4 between a
   practice round and a scored round) are noise. (A check on the field, not a bar: the bars in §3 are in z.)
8. Our base style beats the kit's do-nothing example (`check_or_fold`) on the real field by 1 point or more.
   (`analyst`'s defaults check gives the kit-example teams' scores on every card. Two downloads in which they match or
   beat the bot we played is a PLAN CHALLENGE; its alternative takes the next practice it can be released for, ahead
   of the b40 "leader or closest rival" pick.)
