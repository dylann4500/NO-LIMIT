# Rehearsal review, night of 14 to 15 November (run `dress2`)

Six reviews of the full rehearsal, combined into one list. **Nothing in the bundle has been changed.** Section 3 is the
list to decide: 4 habits for the two of you, 6 small edits I recommend, and 12 reviewer proposals I'd leave alone
until after the event.

The detailed reports, with times and file pointers for every claim, are in `prep/rehearsal_15nov/`.

## 1. The short answer

- **The workflow works.** On the true results we finished 1st of 21, about 50 standings points clear of 2nd, and 1st
  in five of the six scored rounds. The portal showed 6th because false standings were one of the injected faults.
- **The bots got better all night.** Against the opponents that never changed, our bot went from 2.3 points a table
  below them (practice 1) to 9.6 above them (round 6).
- **The field was weaker than Sunday's.** It was 20 opponents made from bots this same workflow built in a
  75-minute run that afternoon, plus the kit's two example bots. The run shows the process improves a bot over three
  hours and decides sensibly. It does not show we beat finalists.
- **The biggest cost was not a wrong rule.** It was sessions going dark while the app compacted their context: 34
  times, about 2 minutes each, 57 minutes in all. One landed on the round-5 decision.

## 2. What happened

### What worked

| Area | Result |
|---|---|
| Which bot played | Every round played the bot BUILDER meant to play (checked by file hash). |
| Decisions | Every which-bot decision except round 5 followed a written rule with the right bar. Recomputing with the true list of unchanged teams changes none of them. |
| Plan challenges | All four were right, including round 4's "three copies of us and four donors", which matches what was injected exactly. |
| Build hour | First legal bot at minute 4, on the portal at minute 8. Pack command at minute 10. All four practice picks declared with 2 to 5 minutes to spare. |
| Test rig | It predicted small steps well: +0.58 predicted against +0.51 true, and +0.96 against +1.04. |
| Scripts | The clock posted 66 of 66 steps. The watcher saved every round 1 to 14 seconds after it finished, with no errors, and its four wrong-bot alarms were all correct. Nothing needed a restart. |
| Steering | 47 of 57 human messages were answered within 2 minutes and none was ignored. Samuel's answers reached BUILDER word for word. |
| Spotting changes | Hostile bots and the copies of our own bot were reported 1 to 3 minutes after the data landed. The weights change was seen in 12 seconds. SCOUT proved the standings were false from saved round data. |
| Saturday's rules | "Big lead", "late data" and "times are guides" were all used and held. |

### What didn't, ranked by what it would cost on the real day

1. **Compaction freezes.** BUILDER froze 5 times and RESEARCH 6 times, about every 30 minutes. Three of BUILDER's
   landed on decision moments. The worst was 00:35 to 00:37, on top of Dylan's "Should I keep V16 up?" five minutes
   before round 5. This is real on Sunday.
2. **The eight separate role sessions.** Nobody typed into any of them. They cost a 26-minute handover, 23 of the
   34 compactions and about half the night's tokens. They flooded the two main sessions with 1,278 messages, which
   is what drove those sessions to compact so often. During the handover two bots shipped with a bug another session
   had already found.
3. **Round 5 was decided by accident.** The rule said the current bot, v8. RESEARCH switched to v16 after the
   deadline, BUILDER was frozen, and v16 played because it was the bot left on the portal. It won the round, by
   luck. Three things lined up: results the organizer held back (injected), the freeze, and a phrase of mine in the
   decision rules that both sessions misread (edit B1).
4. **Upload requests buried in long messages.** From "go" to the upload took 1.9 to 3.9 minutes, because each
   request shared a message with tables and news.
5. **Two styles were dropped without ever playing a portal round.** BUILDER ruled out styles B and C on test-rig
   numbers that were later marked unproven. Style A, which the rig underrated by 2 to 4 points, won round 6. The
   bundle's wording was right and wasn't followed.
6. **"Zero failed decisions", read strictly, kept the better bot out of round 4.** v14 was held back over 6 missed
   decisions caused by a stalled machine. Its copies in the field then beat v8 by about 0.5 a table, which is about
   2 standings points at that round's weight.
7. **The two of you heard different versions of the same decision three times** (rounds 1, 2 and 5), because
   RESEARCH re-worded BUILDER's question for Samuel.
8. **The heads-up test ran on a two-seat table**, a format the event never shows. Platform bots refused it, so
   their heads-up numbers were too low for the first 30 minutes of comparing styles.
9. **A later bot dropped earlier fixes.** v17 (round 6) lost two fixes the previous bots had. Separately, a bug in
   how the main design valued all-in calls lived through rounds 1 to 5; fixing it measured about 0.
10. **Subagents ran at medium effort.** All 58 that BUILDER and RESEARCH started on Opus did, because nothing set
    the effort. START.md says otherwise.
11. **Half the opponents' scheduled version changes went unreported** (7 of 14). Five of the seven misses were
    steps that barely change behaviour. Fingerprinting scored 41 to 47% against its own bar of 55% and was correctly
    never switched on.

### Things that only happen in a rehearsal

- The 23:50 practice ran slowly and our bot missed 6,243 decisions. Our own test rig shared a Modal workspace with
  the mock organizer's rounds. On Sunday their rounds don't run in our Modal.
- The sessions blamed the held round on that same cause and paused their own testing. Same reason, same answer.
- Both sessions asked within two minutes whether this was a rehearsal, and you both said yes. Every session knew
  from 22:15.
- The copies of our bot were v14, the bot on the portal at the moment it was copied, not v8, the bot we were playing
  in scored rounds then.

## 3. Decisions

### A. Habits for the two of you (no rule changes)

| # | Habit | Why |
|---|---|---|
| A1 | **Leave the roles as background subagents**, as the bundle is written. Don't ask for them as separate sessions. Steer through BUILDER and RESEARCH. | Item 2 above. This also removes most of item 1. |
| A2 | **Type `/compact` in your session when each scored round starts.** Try it once during set-up to confirm it works in the desktop app. | The session is dark for about two minutes while the round runs, when nothing can be changed anyway, and is back before results land. It then won't freeze by itself in the minutes before the next round. |
| A3 | **Three questions worth asking your session.** Before a style is dropped: "has it played a portal practice?" At T-5: "what is on the portal, and what does the rule say?" When a new line takes over: "did it keep the previous bot's fixes?" | Items 3, 5 and 9. Each would have caught the problem in one message. |
| A4 | **Set both sessions to effort high when you create them, and use a fresh folder** (`~/avalon-finals`, the day-of command), not last night's `avalon-nolimit`. | Last night's sessions ran at xhigh, which answers slower. Last night's folder also has a memory note about the mock portal, which a session started there would load. |

### B. Edits to the bundle I recommend

**Approved by Dylan and Samuel and applied on 15 November, 03:55** (full script tests pass, 228 of 228; the starting
bundle zip is repacked). B2 also changed the second mention of the bar in `strategy/FIRST_PROMPT.md`'s upload-test
check, and B5 was worded for either table ("the day's full table with all but two seats already out").

| # | File | Change | Why |
|---|---|---|---|
| B1 | `strategy/DECISION_RULES.md`, the section for a day with no practice rounds | Delete "(the last-rounds bar)" from the "Rounds 5 and 6" bullet. After the section's opening sentence add: "On a day with practice rounds, nothing in this section applies." | Item 3. Both sessions quoted this section as a live rule on a day it didn't apply. The phrase was mine. |
| B2 | `CLAUDE.md` hard rule 1 and line 276, `strategy/DECISION_RULES.md` line 36, and the matching line in `strategy/FIRST_PROMPT.md` | "zero failed decisions in the checks" becomes "no more failed decisions in the checks than the kit's `check_or_fold` bot has in the same run (a stalled machine fails every bot's decisions; on a quiet machine that is zero)". | Item 6. The testers already judge timing against that baseline. **This edits a hard rule, so it needs both of you.** |
| B3 | `prompts/BUILDER.md`, "Talking to Dylan" | "Keep it short: what's happening, what he must do and by when (exact file names: `releases/v7.zip`), or "nothing right now"." becomes "When he must act, that message holds only the action, the exact file (`releases/v7.zip`) and the deadline; everything else goes in a separate message. When nothing is needed from him, don't message him to say so." | Item 4. |
| B4 | `prompts/RESEARCH.md`, where it puts the decision to Samuel | Add: "Put BUILDER's question to Samuel in BUILDER's words, copied from its `state/decisions.md` entry, not a version of your own." | Item 7. |
| B5 | `.claude/agents/tester.md` line 26 | "a heads-up run (`--players 2`)" becomes "a heads-up run at the real table's settings (six seats with four already out; a bare `--players 2` table is a format the event never shows, and platform bots refused it in the 14 November rehearsal)". | Item 8. |
| B6 | `START.md` | Four edits, below. | Items 1, 2 and 10. |

**B6 in full:**

1. The starters become the ones you pasted last night, with two changes: the Opus line also sets the effort, and the
   "suggestions" line excepts the decision rules. Two reviewers found that line contradicts "DECISION_RULES always
   applies"; the sessions happened to resolve it the right way. BUILDER's starter (RESEARCH's is the same with
   Samuel and `prompts/RESEARCH.md`):

   ```
   You are the BUILDER session for team avalon at the No Limit Finals today. Dylan is at this terminal.
   Read prompts/BUILDER.md now and follow its process, starting with its start-up steps.
   Run every subagent on Opus at high effort: pass model "opus" and effort "high" in each Agent call, and tell each subagent to do the same for its helpers.
   Apart from the hard rules in CLAUDE.md and the decision rules in strategy/DECISION_RULES.md, treat the strategy and research in this repo (notes/pre/ and strategy/) as well-informed suggestions made before the event, not instructions to follow to the letter. Use them at a high level, make your own design choices, and where today's games and data disagree with them, the data wins. Say the same in every brief you give a subagent.
   ```

2. "During the day" gains one bullet: "**Both:** when the portal shows a scored round has started, type `/compact` in
   your session. It goes dark for about two minutes and is back before the results land."
3. After "Both of you can type into either session" add: "Leave the roles as background subagents. Asked for as
   separate sessions in the 14 to 15 November rehearsal, nobody typed into them, and they cost a 26-minute handover
   and most of the night's context compactions."
4. Correct the sentence about subagent effort: a subagent started with model "opus" and no effort ran at medium, not
   at the session's effort.

**On effort for subagents (part of B6.1):** last night the builders were separate sessions at xhigh. With A1 they
become subagents, which ran at medium. "High" is the middle and matches the guideline you gave me on Saturday
(Opus at high or xhigh for implementation). Passing the effort in the Agent call works: the six reviewers behind
this page were started that way. If you'd rather keep medium, which hit every build-hour deadline last night, say
so and I'll leave the effort out.

### C. Proposed by a reviewer; I'd leave alone until after the event

Each is either a removal of something the sessions ignored at no cost, or an untested change on the morning of the
event. Say the number if you want one applied.

| # | Proposal | Why I'd leave it |
|---|---|---|
| C1 | Cut the start-up reading to the decision rules only (it costs about 100k tokens before minute 0). | It moves only the first freeze, by about 10 minutes. The reading may be why the build hour went well. |
| C2 | Raise the compaction window above 400k. | Untested. Nobody knows what a longer context does to answer speed. A2 covers the scored rounds. |
| C3 | Test rig: every bot in its own process. | Another reviewer disagrees. It's a design change to a rig built on the day, and the rig's own hash check caught the leak. |
| C4 | Delete "a standalone design is ported the moment the pack command arrives". | Ignored last night with mixed results: the standalone line won five rounds, and its private copy hid the all-in bug. |
| C5 | Delete or reword "a release is made only for a pick". | Ignored; nothing broke. |
| C6 | Delete the `base-vN` tag, the VERSIONS verdict pointer and the "re-read your prompt after compaction" step. | Ignored at no cost. A second reviewer says keep the last one. |
| C7 | Reword the bug hunter's all-in check; delete its Codex second opinion (never ran in 16 hunts). | Small value. The all-in fix measured about 0. |
| C8 | Delete "between two close candidates for round 1, prefer the more aggressive". | It shifted one bar by a point and decided nothing. |
| C9 | One line in `strategy/FINGERPRINTING.md` about a team that changes against everyone. | Optional; the missed steps changed little. |
| C10 | Reword the time-bank line in `CLAUDE.md`. | The bundle's line matches the organizers' own page. The mock kit differed. |
| C11 | Code changes: the safety hook's 20 false alarms on scratch deletes, a watcher warning when standings don't add up, longer sleeps for subagents. | No code changes on the morning. None cost more than a tool call. |
| C12 | Drop the pre-event notes nobody opened (`finalists.md` and three others). | A field of synthetic teams can't judge notes about the real finalists. Unopened files cost nothing. |

## 4. What the run could not tell us

- How styles B and C would have scored on the portal. They never played.
- Whether medium effort made any verdict or bug hunt worse.
- Whether v17's gain holds against a field that re-raises. It lost 1.5 points a table at tables with the injected
  re-raiser.
- Whether the real portal renumbers a round between "running" and "finished" as the mock did. The watcher showed
  "played by ?" for 13 of 14 rounds because of it. The wrong-bot alarms don't depend on it.
- What a larger compaction window would have done.

## 5. GTO Wizard

**Decided (Dylan, 15 November): no GTO Wizard benchmark.** What follows is the reasoning from the review, kept for
the record.

Run nothing before the event. The benchmark is heads-up no-limit hold'em at 200 big blinds against their solver bot,
scored in big blinds per 100 hands. Our bots are built for a six-seat tournament table with a twist, so the bot
would need the twist stripped out first. Every hand played is public under the key's name, and the team's adapter
has two defects (seat numbering, and bot errors it swallows). After the event: fix the adapter, strip the twist from
last night's best bot, and play 5,000 hands. Details: `prep/rehearsal_15nov/07_gto_wizard_benchmark.md`.

## 6. Where everything is

- The seven reports: `prep/rehearsal_15nov/` (timeline, decisions, detection, bots and tests, humans and sessions,
  instructions and infrastructure, GTO Wizard).
- The full log of the run, on Dylan's laptop only: `~/avalon-rehearsal-log/` (every prompt, every message between
  sessions, transcripts, snapshots of the repo's state files, the organizer side's fault log).
- The team's repo as the run left it: `~/Documents/GitHub/avalon-nolimit` (bots stay there; none of it goes into
  Sunday's repo).
