# The plan: game plan and timeline

For both sessions and both humans: what we learned, the game plan, the timeline, how we decide in short, and who
does what at each step. It is a default, not a mandate (`CLAUDE.md` §6): when today's data says a better path
exists, raise a PLAN CHALLENGE (`DECISION_RULES.md` §3). The rules themselves are in `DECISION_RULES.md`; what
broke in rehearsals is in `LESSONS.md`; the briefs for the subagents are in `FIRST_PROMPT.md`.

## 1. What we learned since the regional

At the regional we finished 6th (376.71). 2 Curry won with 428.72, about 2.5 points per table per round
more than us.

- **Our own mistakes cost about 22-25 points; fixing them alone would have put us about 3rd.** They were:
  - over-calling flop and turn bets;
  - over-folding after v6;
  - the starter kit's ICM function scoring a busted stack as 0;
  - folding 82-89% to re-raises.

  v10 also had two counting bugs: an inverted raise-frequency stat, and folds to our own bets that were
  never counted.
- **Style mattered, and one rule in particular.** 2 Curry opened about 40% of hands, re-raised wide, and
  tracked each seat: it re-raised a fresh opener 18% of the time, 43% after that seat had folded to one
  re-raise, and 62% after two. We folded to most re-raises, so it kept re-raising us. Three other top-20 teams
  had a strong rule exactly like this; ten had a strong per-seat response of some kind.
- **Almost everyone changed their bot every round (78-90% of teams).** Top-20 teams fell back about 0.65
  points per round whether they changed or not, so freezing never holds a lead.
- **The Finals field is harder.** Every finalist knows wide re-raising won. By round 5 at Boston, the top
  teams already folded only 58% to re-raises and re-raised back 23% of the time.
- **Big jumps come from rewrites.** For top-20 teams, rewrites averaged the same as standing still (−0.68 vs
  −0.67) but with three times the spread: 24% improved, by up to +3.8; no unchanged team did. With only the
  top 3 paid, that upside is worth having.
- **Bet sizes identify a team quickly:** the right team is named 73% of the time by hand 20. Hiding our
  sizes costs value and works for one round at most, so we don't hide them. Instead we avoid big
  exploitable gaps, such as folding 89% to re-raises when the field folds 65%.
- **No style wins everywhere.** In simulation (Bay Area variant, pure fields only) they formed a cycle:
  wide re-raising beats tight, limp-or-shove beats wide re-raisers, tight beats shovers. In realistic mixes
  the differences were small and the simulation couldn't rank strong teams. So the styles are starting
  points, one design is built fresh from today's rules, and the real field chooses.
- **Expect lower scores:** a field of only strong teams averages the points paid divided by the seats: 16.7 a table
  in case F and 12.5 in case R (`CLAUDE.md` §8). In case R our regional bots simulate at 14-19 against such a field,
  depending on the fit: don't panic at a 15 there. In case F a 15 is below the mean, and the same relative score is
  about 20.
- **The field moves.** Boston's top 20 went from folding 75% to re-raises to 57.5% by round 5 and partly back.
  Finalists studied both regionals, so expect them to start near that point and keep moving. **The plan is a
  default, not a mandate:** a session or subagent that sees the plan is wrong for today's field raises a
  *plan challenge* to both of you.

How sure we are of each of these: `EVIDENCE_TABLE.md`.

## 2. The game plan

1. **Build hour.** At minute 0 the clock posts the build-hour steps to both sessions.
   - BUILDER has `platform` write the rules card, then build:
     - a minimal legal bot by minute 10;
     - a test harness by minute 15;
     - each of `theory`'s tables built in as it lands (all by about minute 20, so every practice from practice 1
       uses the newest tables);
     - then **one shared platform** (rules, equity, per-seat counters, memory, safety), on which `stylist`
       builds **three styles**: wide pressure (A), shove-heavy (B) and tight (C).
   - From minute 0 `challenger` also builds **design D from scratch**: from today's rules only, without our
     regional style notes.
   - RESEARCH has three `theory` agents compute today's maths tables (all by minute 20, then a second wave),
     `analyst` write the hand-history parsers and the round card, `tester` build the test rig and `scout` the
     fingerprinting, all ready for practice 1's data.

   Practice rounds at minutes 20-50 each play the most informative candidate (BUILDER picks; one is D), every
   one with the newest shared tables so the comparison is fair. `tester`'s best scorer of practices 1-3,
   adjusted for the field and the round size, goes live for scored round 1, declared at minute 50; practice 4's
   bot, if different, is its challenger, asked once at T-8 of round 1.
2. **Every 20 minutes after that:**
   1. a scored round lands (the portal watcher saves it and tells both sessions);
   2. RESEARCH analyses it (`analyst`, `scout`, `tester`);
   3. BUILDER builds a challenger and fixes (`challenger`, `stylist`, `platform`);
   4. the challenger plays the practice round 10 minutes before the next scored round;
   5. you decide together what plays: the live bot, the live bot plus the tested changes that cleared the bar,
      or the challenger. RESEARCH recommends by T-9; BUILDER asks at T-8.

   Each window `scout` also writes the **field trend** (what the field and the top 5 do now, and which plan
   assumptions still hold), and `analyst`'s **winners lens** asks what the best teams do that we don't. Until
   about 30% of the weight is played, at least every other practice round plays a genuinely different design,
   not a tweak: one practice round can't measure small tweaks anyway.
3. **Adapt to individual seats, not to the "table mood".** Per-seat counts are blended with what we know
   about each team, and every adjustment is capped. Against seats that raise a lot, call down and re-raise
   wider; folding more is the wrong answer to aggression.
4. **Evidence before shipping, but standing still isn't safe.** An analysis that sounds convincing is a
   candidate until the real field (a practice round) has tested it; candidates go into the challenger and
   practice rounds quickly. Folding to a 3-bet of our open: no more than break-even (usually 65-75% in case R; about 57-68% with case F's antes: two styles drafted to the regional number folded too much in a timed run).

## 3. The timeline

**Build hour** (minutes from the variant announcement):

| Minute | What happens | Who |
|---|---|---|
| 0-5 | Samuel gives RESEARCH the announcement time and it starts the clock (if nobody has, RESEARCH starts it from the portal watcher's "THE VARIANT IS ANNOUNCED" line; the same line means the portal's rules text is in `state/variant.md`, a head start while the kit unpacks); kit fetched into `starter-kit/`; Format page read (round weights, payouts, the upload cooldown, anything unusual; a different shape goes into the clock); BUILDER starts `platform` on the rules card and Part 1 with `TWIST_NOTES.md`; RESEARCH starts `theory`, `analyst`, `tester` and `scout` | Both |
| 0 | `challenger` starts design D from scratch (today's rules only) | BUILDER |
| by 10 | Minimal legal bot uploaded and active | Dylan (BUILDER names the file) |
| 15 | Test rig running (paired runs, sparring) | RESEARCH (`tester`) |
| 17, 27, 37, 47 | BUILDER has declared the bot for the next practice (the most informative test) with `scripts/live.py`; 3 minutes before each practice the clock reminds Dylan in its tab and BUILDER tells him the file: upload it, or activate it if it's already uploaded | Dylan |
| 20, 30, 40, 50 | Practice rounds | |
| 50 | BUILDER declares `tester`'s adjusted best scorer of practices 1-3, among bots whose verdict has a heads-up run at b50, for scored round 1 (`scripts/live.py`; no question then). Practice 4's bot, if different, is round 1's challenger | BUILDER |
| after 50 | Round 1 runs like every window from T-9: Dylan makes the declared bot active (a click: it's already uploaded); the round-1 question is asked once, at T-8 | Dylan, both humans |

**Every window after that.** At Bay Area a practice round started 7 to 10 minutes before each scored round; the
organizers' pages describe practice rounds only for the build hour, so the first window shows whether today has them
(`CLAUDE.md` §8). The table below assumes one 10 minutes before each scored round. Each round plays a
snapshot of every team's **active** bot taken at its start. Making an already-uploaded bot active is a click
on the portal, not an upload, so a window has at most two real uploads, about 8 minutes apart: the challenger
at T-12 and, only if the chosen bot is a new zip, the chosen bot around T-4 to T-3. `state/live.json` holds the
scored-round bot all window; the challenger is never declared with `scripts/live.py`. On the organizers' newest pages
an upload that passes its test becomes active by itself (at Bay Area it took a click; BUILDER settles which at
minute 10): then the T-12 upload is also the activation, the T-9 click still puts the live bot back, and a new zip
uploaded at T-4 is active only when its test ends. Either way the active bot is confirmed in `state/status.md` after
every upload and every click, and nothing is uploaded inside a window that is not meant to be the next bot to play.

| Time to scored round | What happens | Who |
|---|---|---|
| T-20 | Previous scored round starts. The sessions sync in 3 lines; in the last two rounds (`state/clock.md`), the last-rounds bar and the last round's plan | Both sessions |
| T-16 | This window's challenger packed and tested | BUILDER (`challenger`), RESEARCH (`tester`) |
| T-15 | The challenger released: `releases/vN.zip` and a `releases/VERSIONS.md` line with its sha256 | BUILDER (`platform`) |
| T-13 | Previous round's result and hand data land (the portal watcher saves them under `data/rounds/`, runs the round card and posts to both inboxes); RESEARCH analyses; BUILDER's stylists start on the one-change lines already in the LEDGER | Both sessions |
| T-12 | Challenger made active: BUILDER tells Dylan its exact file (he uploads it if it isn't on the portal yet: the first real upload); never declared with `scripts/live.py` | Dylan (BUILDER names the file) |
| T-10 | Practice round plays the challenger | |
| T-9 | The `state/live.json` bot put back as active, once `state/status.md` shows the practice round as started (and at T-5 at the latest): a click in the portal's uploads list, no re-upload | Dylan (BUILDER asks) |
| T-9 | RESEARCH sends BUILDER the recommendation (the threshold, then the final answer once the practice lands) | RESEARCH |
| T-8 | **Decide** by the pre-registered rule (`DECISION_RULES.md` §3): the challenger if it clears the field-adjusted bar for our standing, else the live bot with this window's tested changes. BUILDER asks in its terminal, with the rule's answer, and records it in `state/decisions.md`. The practice's download lands about now: before the decision only `tester`'s field-adjusted edge matters; its full analysis runs after T-3 | Both humans |
| T-6 | Chosen bot tested with no time bank | BUILDER (`platform`) |
| T-5 | No human answer: BUILDER applies the rule's answer itself (`scripts/live.py`) | BUILDER |
| T-3 | Chosen bot active: a click if it's already uploaded (the challenger or the live bot), else uploaded around T-4 to T-3 (active only when its upload test ends); active bot confirmed in `state/status.md` | Dylan |

Once the live bot is back at T-9, a missed deadline means the previous live bot plays: that is a failure to
fix, not a safe outcome (bots that stood still lost as much as bots that changed). Only tested zips are ever
uploaded.

## 4. How we decide (the short version)

The full rules are in `DECISION_RULES.md`; they always apply.

- **Goal:** a top-3 finish (only 1st-3rd pay). Standing still is not safe.
- **Live bot:** every independent tested change that clears the bar, each in a different situation and behind
  its own setting (usually one to three).
- **Challenger:** the team's exploration: the clean-room design, a new style, the best response to the field's
  measured mix, what a plan challenge points to, or a fresh rewrite. A rewrite is normal at any standing.
- **Which bot plays:** compared against yardstick teams (those that didn't change), so the challenger's
  practice and the live bot's scored round are on one scale. The challenger plays at z ≥ 0.5 outside the top 3
  (≥ 0 in the last two rounds), z ≥ 1.0 in the top 3 (1.5 when our lead over 4th is more than 3 x the coming round's weight, in standings points). If nobody answers in time,
  BUILDER applies the rule's answer at T-5. In round 1 the live bot is the adjusted best scorer of practices 1-3 among bots whose verdict has a heads-up run at b50
  and the challenger is practice 4's bot, if different.
- **Exploration:** until 30% of the weight is played, at least every other practice round plays a different
  design, at any standing unless our lead is big.
- **Plan challenges:** any session or subagent may say the plan is wrong for today, with evidence; both of you
  hear it, RESEARCH records it once in `state/decisions.md`, and by default `challenger` builds the
  alternative for the next practice.
- **Folding to re-raises:** near break-even (usually 65-75% in case R, about 59-68% with case F's antes) is the default, not a cap (the regional winner
  folded 81-87%); it doesn't apply to folding to 4-bets after our own light 3-bets.
- **Standings or results held:** `tester` works out all 21 teams' totals from each round's results and multipliers; only
  where that can't be done do we count as outside the top 3, and with no practice result by T-6 the rule's
  answer is the live bot. The last round's results may be held altogether (`CLAUDE.md` §8).
- **Bolder:** behind 3rd, or outside the top 3 after 15% of the weight: the challenger slot carries a divergent
  design and the bar drops; plan the last round (29% of all points with multipliers 1 to 6, 41% with Fibonacci, 51% with powers of two; the Finals was set to 1 to 6 on Saturday afternoon, re-read at minute 0) from the round before.
- **What counts as evidence, in order:**
  1. real-field results (practice and scored);
  2. replay testing;
  3. the cloned field, which is a warning light, not a ranking.

  Beating our own bots proves nothing.
- **Never block a change because it makes us look unusual.** The regional winner looked nothing like
  the average team.

## 5. Who does what, when

The clock (`python3 scripts/clock.py run`, in its own terminal tab) posts each step below into the inbox of the
session that acts, and prints Dylan's upload and activate reminders in its tab. `b<n>` is minute n of the build
hour; `T<n>` is n minutes before each scored round. Sessions spawn subagents in the background, several in one
message, each with a time limit; a subagent reports only to the session that spawned it, and the sessions pass
paths to each other with `SendMessage` to BUILDER or RESEARCH (and `say.py --record`). The cut-offs in
`DECISION_RULES.md` §3 (T-12, T-10, data + 3 minutes, T-8, T-7, T-4) are posted the same way. In a path,
`<stage>` is the stage name with spaces as '-' (`analysis/Practice-1/`, `analysis/Round-2.5/`).

**The format may differ** (build length, the gap between scored rounds, the number of rounds). At minute 0 both
humans read the Format page and tell RESEARCH the shape in words; it sets the clock with
`python3 scripts/clock.py format ...` (e.g. `format --build 90`, `format --scored 5`). When a scored round really
starts at another time, `python3 scripts/clock.py pin scored<k> HH:MM` moves it and every later step follows (the
clock also picks up real starts from the portal). The steps keep their names: `b<n>` counts from minute 0, `T<n>`
back from each scored round. Scored round 1's live bot is declared at b50 (`tester`'s adjusted best scorer of
practices 1-3, no question then); practice 4 is its practice round, and practice 4's bot, if different, is its
challenger. From T-9 it runs like every window; the round-1 question is asked once, at T-8 (`DECISION_RULES.md`
§3, "Round 1").

**Before minute 0** (notes only, no bot code: event rules). Every file below was drafted on Saturday 14 November:
each brief is to check and extend the draft in place and list what changed at the top, not to start over.

| Step | Session | Subagent: the brief | Deliverable |
|---|---|---|---|
| pre (about 2 h before minute 0, when a human types "start the research" in both sessions) | RESEARCH | `theory`: FIRST_PROMPT Part 0 topic A: the three regional variants (Pittsburgh's is in the 14 November draft), ten plausible Finals twists and the fastest correct way to value each by enumeration | `notes/pre/variants.md` |
| | RESEARCH | `scout`: what will the Finals field do? Every finalist knows the regional lessons (wide 3-betting won, per-seat adaptation, fold to 3-bets about 65%): which styles will be crowded, what punishes them, how practice 1 (mostly minimal bots) will differ from round 3, what to watch first | `notes/pre/field.md` |
| | RESEARCH | `tester`: topic D: today's test plan (sparring bots, paired deals, noise first, replay on a download, the cloned field on Modal, a confirmation run) | `notes/pre/testplan.md` |
| | BUILDER | `platform`: topic C: the first-hour build plan (the safety shell, three layers, what to precompute at import, a 0.3 ms equity estimate, per-seat estimates with priors, the checks that catch the bugs that sank bots) | `notes/pre/buildplan.md` |
| | BUILDER | `stylist`: topic B: what wins sit-and-gos of AI-built bots (preflop aggression with planned responses, postflop folding vs bluff rates, shove-or-fold by depth, ICM for other payouts, heads-up and 3-handed) | `notes/pre/whatwins.md` |
| | BUILDER | `challenger`: the contrarian memo: assume 20 strong teams read the same regional lessons; three designs that would beat that field, what each loses to, how one practice round would tell us which this field pays | `notes/pre/contrarian.md` |
| | RESEARCH | itself: merge the six into one page; both humans read the contrarian memo | `notes/plan.md` |

**The build hour** (`b<n>` = minutes from the announcement)

| Step | Session | Subagent: the brief | Deliverable |
|---|---|---|---|
| b0 | Humans | Samuel gives RESEARCH the announcement time (it runs `clock.py start`; with no time given, it uses the one in the watcher's "THE VARIANT IS ANNOUNCED" line); both read the Format page (a different shape goes into the clock); Dylan puts the kit in `starter-kit/` | the clock running |
| | BUILDER | itself first: check with the kit's Python that the kit's engine loads today's variant (`load_variant` with the engine's own name for it, which can differ from the portal's title); if not, tell both humans at once (if the kit's Python isn't built yet, `platform`'s first step makes this check) | |
| | BUILDER | `platform`: the rules card first, its first line saying which case holds, F or R (`CLAUDE.md` §8) (`bot/rules.json` from the kit and the Format page: players per table, stacks, blinds and antes, hands per match, time limits, weights, payouts, cooldown) within 5 minutes; then FIRST_PROMPT Part 1 with `TWIST_NOTES.md`: a minimal legal bot by minute 10, the test harness by 15, each of `theory`'s tables built in as it lands (all by about minute 20, so every practice from practice 1 uses the newest tables), then the shared platform with every Part 1 check passing | `bot/rules.json`, `bot/` |
| | BUILDER | `stylist`: Part 1 (styles, shared defaults) and `TWIST_NOTES.md`: styles A (wide pressure), B (shove-heavy), C (tight) as settings on the platform as soon as its interface is published. They are starting corners: if today's rules clearly favour another axis (the twist, postflop, short stacks), say so and build that instead of the weakest corner | `candidates/<style>/` |
| | BUILDER | `challenger`: clean-room design D from the kit, the rules card, `TWIST_NOTES.md` and `theory`'s tables only (not the A/B/C definitions or FIRST_PROMPT's regional strategy): what today's variant rewards, the 2-3 axes that matter most, the design you'd build if nobody had told you anything, what would show it's wrong; then build it on the platform | `candidates/D/DESIGN.md` by minute 12, then `candidates/D/` |
| | RESEARCH | `theory`, three agents in parallel: the maths tables (FIRST_PROMPT Part 1b): hand ranking and ICM thresholds by minute 10; the twist's option values (its decision rule in `theory/out/twist_rule.json`), push/fold, call tables and break-evens by 15; `theory/HANDOFF.md` by 20; then a second wave. RESEARCH tells BUILDER each path as it lands (`SendMessage` to BUILDER, and `say.py --record`), and `platform` builds it in at once | `theory/out/*.json`, `theory/HANDOFF.md` |
| | RESEARCH | `analyst`: parsers for today's hand-history format and `analysis/roundcard.py` (card in under 60 s, with the defaults check and `analysis/field_priors.json`), ready for practice 1's download (about minute 25); at about minute 10 (when v1 exists) a dry-run download into a fresh `/tmp/dryrun-<HHMM>/`, never `data/rounds/` | `analysis/roundcard.py` |
| | RESEARCH | `tester`: the rules card checked against the kit and Format page as soon as it appears; then FIRST_PROMPT Part 3a: the paired runner on identical deals and sparring bots that use the twist | `rig/`, running by minute 15 |
| | RESEARCH | `scout`: `analysis/fp_train.py` (`FINGERPRINTING.md`), running on practice 1's labelled download in under 60 s (quick mode) | `analysis/fp_train.py` |
| b10 | BUILDER | `platform`: v1 released now, upload-tested; BUILDER declares it (`python3 scripts/live.py v1 "first legal bot"`) and tells Dylan the file | `releases/v1.zip` and its `releases/VERSIONS.md` line; Dylan uploads it; BUILDER reads `state/status.md` before any click to settle whether uploads activate themselves today, then it is made active if it isn't |
| b15 | RESEARCH | `tester`: the rig runs now: the first verdict on v1 (correct? timing? a heads-up run?), sent on to BUILDER | a `notes/LEDGER.md` line |
| b17 | BUILDER | itself: practice 1 starts in 3 minutes. The declared pick (`state/live.json`) is released and upload-tested; tell Dylan the exact file to upload, or to click it active if it's already on the portal (the clock reminds him too) | the pick active by minute 20 |
| b20 | BUILDER | `stylist`: the next style ready (legal and upload-tested is enough); every style rebuilt with the newest shared tables before its upload, so practice scores compare styles, not timing | a style ready to release |
| | BUILDER | `platform`: `theory`'s tables built in as they land (ranking, ICM thresholds, the twist rule, push/fold, call tables, break-evens; all by about minute 20; behind settings, ON once checked), so every style uploaded from now on uses them | a new release |
| | BUILDER | itself: pick practice 2's bot (minute 30): the most informative test, not a rota; declare it with `scripts/live.py` by minute 27 | `state/live.json` |
| | RESEARCH | `analyst`, spawned on practice 1's DATA LANDED (never to wait for it): the defaults check, then the leaks of the bot that played (Part 2), the top change within 5 minutes | `analysis/Practice-1/card.md`, ledger lines |
| b27 | BUILDER | itself: as b17, for practice 2 | the pick active by minute 30 |
| b30 | BUILDER | `platform`: check every `theory` table is built in, and build in `theory`'s refits from practice 1 as they land; every style picks them up at its next upload | a new release |
| | BUILDER | `stylist`: each style kept current with the platform; the next one ready for practice 3 | |
| | BUILDER | itself: pick practice 3 (minute 40): the candidate whose real-field score we most need (D if not yet measured); declare it by minute 37 | `state/live.json` |
| | RESEARCH | `theory`: the call tables' shove-width and fold-rate columns refitted from practice 1's real data and re-issued | `theory/out/` |
| | RESEARCH | `analyst`, spawned on practice 2's DATA LANDED: its leaks, and the styles played so far compared on the real field | the card, ledger lines |
| | RESEARCH | `scout`: the first FIELD TREND from practices 1-2 (practice 1's field is mostly minimal bots), first profiles, recogniser accuracy (same-round), how identifiable we are | `analysis/<stage>/field_trend.md` |
| b37 | BUILDER | itself: as b17, for practice 3 | the pick active by minute 40 |
| b40 | BUILDER | `stylist`: the styles kept current; whichever BUILDER names for practice 4 ready by minute 47 | |
| | BUILDER | `challenger`: from practices 1-3 (real-field scores, `scout`'s field trend and profiles), the first challenger for the practice before scored round 2: D matured, the best response to the field's measured mix, or what the data points to; one line why | `candidates/<name>/` |
| | BUILDER | itself: pick practice 4 (minute 50): the leader, or its closest unmeasured rival if the leader is already clear (if it isn't the round-1 live bot, it is round 1's challenger); declare it by minute 47 | `state/live.json` |
| | RESEARCH | `tester`: every bot that played practices 1-3 (A, B, C, D, ...) ranked by its practice score minus the yardstick teams' scores in the same practice, adjusting for confounds (which tables each had, practice size, how mature the field was), with replay tests of each on the same downloads; by minute 50 the adjusted best scorer (the round-1 live bot), with a verdict that includes a heads-up run; say which comparison carries the decision. Started on practices 1-2; RESEARCH continues it with practice 3's data when it lands (about minute 45) | a ranking, which RESEARCH sends BUILDER by minute 50 |
| | RESEARCH | `analyst`: which style did the field reward in practices 1-3, and what are the best teams doing (winners lens)? One paragraph with the numbers, to BUILDER by minute 50 for the round-1 live bot; if no style we built matches what wins, a PLAN CHALLENGE. Continued with practice 3's data like `tester` | a paragraph sent to BUILDER |
| b47 | BUILDER | itself: as b17, for practice 4 | the pick active by minute 50 |
| b50 | BUILDER | itself: declare `tester`'s adjusted best scorer of practices 1-3, among bots whose verdict has a heads-up run at b50 (a higher-ranked bot whose verdict lands by T-4 replaces it by a click, no question asked), for scored round 1 (`python3 scripts/live.py vN "round 1: adjusted best scorer"`; it already played, so it's released and uploaded); no question now. Practice 4's bot, if different, is round 1's challenger; the round-1 question is asked once, at T-8 (`DECISION_RULES.md` §3, "Round 1") | `state/live.json`; the round-1 bot made active at T-9 (a click) |
| | RESEARCH | itself: the round-1 recommendation by T-9, like every window: the edge = each bot's practice score minus the yardstick teams' scores in the same practice; the same bars | "RECOMMENDATION round 1" sent to BUILDER |

**Every scored window** (`T<n>` = minutes before the scored round)

| Step | Session | Subagent: the brief | Deliverable |
|---|---|---|---|
| T20 | Both | itself: sync in 3 lines (`SendMessage` to the other session, and `say.py --record`): what changed on your side, what you need from the other, the plan for this window; update your PLAN file | |
| | RESEARCH | itself: step back. From the last field trend and winners lens, is our base approach still right? If not, tell Samuel now and BUILDER (a PLAN CHALLENGE), so `challenger` builds the alternative | |
| | RESEARCH | `tester`: the challenger's paired-test verdicts (a heads-up run included) and methods verified now (they don't depend on the new round); `rig/verify_card.py` and a Codex brief pre-armed to recompute the card's headline numbers from a hand file, so at T-13 only the data path changes | |
| | BUILDER | itself: the "Which bot?" question drafted in `state/decisions.md`: the rule, both bots' numbers as they land, the rule's answer; this window's challenger packed and tested by T-16 | a draft entry |
| | Both, when `state/clock.md` shows these are the last two rounds | itself: apply the last-rounds bar (`DECISION_RULES.md` §3) and plan the last round: durable fixes, any exploit held back, the bar for our standing and the weights | |
| T15 | BUILDER | `platform`: the tested challenger released as `releases/vN.zip` (a `VERSIONS.md` line with its sha256), with a `bughunter` pass in the background; Dylan activates it at T-12. Nothing tested: the most informative released bot instead | `releases/vN.zip` and its `VERSIONS.md` line |
| T13 | (portal watcher) | `scripts/portal_watch.py` saves the round's results and hands, runs `analysis/roundcard.py` when it exists, and posts the result line to both inboxes and "DATA LANDED" to RESEARCH's | `data/rounds/<NN-stage>/`, `analysis/<stage>/card.md` |
| | RESEARCH | `scout`: the FIELD TREND first (plan assumptions checked; a PLAN CHALLENGE if a field rate is 2 points or more outside its band in two downloads running, or a score is off by 2 SE or more), then the fingerprint card: counters on or off by the gate, `counters.json` for `platform`, accuracy and drift lines for `tester`, by T-9 | `analysis/<stage>/field_trend.md`, `analysis/<stage>/fp/` |
| | RESEARCH | `analyst`, one per lens, each spawned on DATA LANDED, never to wait for it (winners; leaks, with the defaults check first; two of sizing / twist / the biggest opponent), plus a Codex recompute of the top number: every independent change that clears the bar; then opponent profiles where a profile pays most | `one-change <stage>` in `notes/LEDGER.md` by T-9, sent to BUILDER |
| | RESEARCH | `theory`: the call and fold columns refitted from the new data and re-issued (real-field numbers outrank the tables) | `theory/out/` |
| | RESEARCH | `tester`: the numbers the T-8 decision may rest on re-run (the card's headline, `analyst`'s changes), persistent leaks first, each line marked validated or disputed; a verdict for every pending candidate (correct? a heads-up run? paired vs the live bot); if on track, the cloned field on Modal for the challenger | ledger statuses |
| | BUILDER | `challenger`: this window's practice plays the challenger already released (or the most informative released bot); start the NEXT challenger now from this round's data, the field trend and any PLAN CHALLENGE: D, the best response to the measured mix, or a rewrite; one line why; packed and tested by the next window's T-16 | `candidates/<name>/` |
| | BUILDER | `stylist`: this window's live-bot fixes, starting now from the one-change lines already in `notes/LEDGER.md` (persistent leaks first), one stylist per line, then one per new line as RESEARCH sends it (lines due by T-9); opponent counters from `scout`; each independent, behind its own setting, in its own folder, each sent to `tester` (via RESEARCH) | `candidates/<name>/` |
| | BUILDER | `platform`: the bugs `tester` reported fixed; this window's live-bot changes built (each independent, behind a setting) | a release candidate |
| T12 | BUILDER | itself: tell Dylan the challenger's exact file to activate (he uploads it if it isn't on the portal yet); never declare it with `scripts/live.py` (`state/live.json` stays the scored-round bot). Nothing released: name the released bot to activate instead, or leave the live bot | the challenger active for the practice round; Dylan's first real upload of the window, if it wasn't on the portal |
| T10 | RESEARCH | itself: the practice round starts and plays the challenger. Cut-off check: has last round's data landed? If not, no change from new data (the live bot plus already-validated changes); tell both humans | |
| T9 | BUILDER | itself: Dylan told to put the `state/live.json` bot back as active straight away (a click in the portal's uploads list, no re-upload); nothing to re-declare, since the challenger was never declared | the live bot active |
| | RESEARCH | itself, with `tester`'s yardstick numbers: the recommendation to BUILDER (`SendMessage` to BUILDER, and `say.py --record`): the rule (standing, the field-adjusted bar), both bots' numbers, the rule's answer as a released file, the evidence (validated, or labelled unverified). Before the practice lands: the threshold (the practice score the challenger needs); the final answer the moment it lands; no practice result by T-6: the rule's answer is the live bot | "RECOMMENDATION round k" sent to BUILDER |
| T8 | BUILDER | itself: the "Which bot?" question asked in its terminal: what's decided, both bots' numbers, what each answer means, the deadline (T-5) and the rule's answer; recorded in `state/decisions.md`. Samuel may answer in RESEARCH, which relays his words. (Cut-offs: the one-change proposal at T-8, the question at T-7) | the humans' answer, in words |
| | RESEARCH | itself: the practice's download (stage `Round k.5`; practice 4 before round 1) lands near now: before the decision only `tester`'s field-adjusted edge matters; the full analysis loop on it runs after T-3 | the final answer to BUILDER |
| T6 | BUILDER | `platform`: the chosen bot tested with no time bank and released, with a `bughunter` pass | `releases/vN.zip` and its `VERSIONS.md` line |
| T5 | BUILDER | itself: no clear human answer, so the rule's answer is applied (`python3 scripts/live.py vN "rule's answer: no answer by T-5"`), recorded, and Dylan told what to click or upload. Opposite answers: the rule's answer stands until they agree | `state/live.json`, `state/decisions.md` |
| T3 | BUILDER | `platform`: the chosen bot's release ready and its exact file confirmed; Dylan makes it active (a click if it's already uploaded, else he uploads the new zip at about T-4 to T-3); BUILDER checks `state/status.md` shows it active. If it wasn't released and tested by T-4, the live bot plays and nothing is uploaded | the chosen bot active; after this nothing changes |
| | Both | itself: anything not yet in `notes/LEDGER.md` recorded; PLAN file updated (what plays, what's running where, open promises); every subagent's next task ready for when data lands. Then RESEARCH starts the full analysis loop on the practice's download | |

**Standing habits.** Every release gets a `bughunter` pass in the background; a bug it reproduces goes to
`platform` first. About every 10 minutes each session asks: is any finding only in a report rather than in
`notes/LEDGER.md`, is any subagent idle while work is queued, and is there independent work (tests, sweeps,
re-checks, a second opinion) to put on Modal or Codex now? Re-arm the inbox Monitor every time it expires.
