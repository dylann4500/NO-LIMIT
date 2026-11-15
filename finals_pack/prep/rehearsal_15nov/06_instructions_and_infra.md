# 06: Instructions and infrastructure (dress2, 14-15 November)

**Summary (five lines)**
1. The costliest thing was context length, not a wrong rule. The bundle's start-up reading filled the main sessions' context by minute 15. With `autoCompactWindow: 400000` set, the 10 working sessions compacted 34 times. Each compaction blocked its session for 72-129 s, about 57 minutes in all. One of them held Dylan's "Should I keep V16 up?" (T-5 of the weight-8 round) for 3 min 43 s.
2. The bundle helped most where it was mechanical. v1 was out at minute 4 (two platform runs). The pack command worked at minute 10 (skeleton first). Every relay of a maths table quoted its version and time. Each finished round was saved 1-14 s after the organizer finished it. All 66 clock steps were posted, none twice and none missed. Four "wrong bot active" alarms caught every mismatch.
3. Three instruction defects cost real minutes or measurements. The tester's in-process option for keeping bots apart, plus a redeploy that skipped the "stop warm containers" step, left platform-bot Modal numbers unproven from about 23:50 to 00:05:46. The mandated heads-up run on a 2-seat table understated every platform bot until 23:17. The kickoff's "strategy/ is suggestions" contradicts "DECISION_RULES always applies", and the sessions quietly followed the latter.
4. Of the Saturday additions, five were followed: two platform runs, skeleton first, version-and-time relays, times as guides, and the liveness check (built into the tools). "Releases only for picks" was ignored: 7 releases besides v1 never played, and v9 and v10 never got a verdict file. The VERSIONS verdict pointer was updated once in 17 releases, and no `base-vN` tag was ever made. All of these were ignored without comment.
5. Usage: 1.76 B input tokens (98.6% cache reads) and 8.0 M output in 2 h 55 min. Opus used 1.50 B in and 6.5 M out (8 role sessions plus 99 subagents). Fable used 256 M in and 1.5 M out (BUILDER, RESEARCH, OPS). At least 95 M went on 504 foreground `sleep 10-19` polls. All 58 subagents spawned by the Fable sessions ran at **medium** effort.

Kinds of finding are marked **[bundle]** (a defect in the starting bundle's instructions), **[session]** (behaviour despite correct instructions) and **[artefact]** (a rehearsal condition that will not exist on Sunday). Times are laptop times. "BUILDER/x" is a subagent of BUILDER. All line numbers are in the starting bundle (`git show 6fc128f:<file>` in `/Users/dylan/Documents/GitHub/avalon-nolimit`). Transcript evidence is in `dress2-frozen/transcripts/` (flattened by me; nothing there was changed).

---

## 1. Deviations: where a session departed from the bundle or said it was wrong

Ranked by minutes lost or risk. Context length is ranked first but discussed under §3.

### 1.1 Bots "kept apart" in the rig: the weaker option broke, and the redeploy skipped a written step [bundle + session]
- **Instruction.** `.claude/agents/tester.md:42-45`: "its own process, **or its own module name with no shared globals**". The same file at :76-78 says: "stop the app's old containers before redeploying, and have every shard return the hash of the code it ran".
- **What happened.** TESTER chose the module-renaming option (`rig/loader.py`). At 22:30:23 TESTER itself flagged it: "One hero instance plays every table in-process." At 23:56:23 BUILDER relayed the bug STYLIST A and B had found: "on a warm Modal container, when any zip fails to import, its avcore and style modules stay loaded and later PLATFORM zips in that container ... can silently run that code" (`state/events.log:251`). TESTER then redeployed at 23:57:23 without stopping the containers. The shard hash check did catch it: RESEARCH 00:03:23, "all 40 warm containers are old, jobs return stale code 0 tables". But no Modal number came back until TESTER stopped the 40 containers by id (00:03:10-00:03:48). The rig counted as clean only from 00:05:46 (LEDGER L248).
- **Cost.** Platform-zip Modal numbers from about 23:50 to 00:05:46 were declared unproven (events.log:290). v13's "+0.82 ± 0.25 over v12" was invalidated ("22 and 41 of 400 tables differ from local on the same seed"). For about 8 minutes, in round 4's window, the team had no Modal output at all. The stop-before-redeploy step was in `tester.md`, and TESTER had compacted at 22:55, after reading it at 22:27.
- **Right to?** Choosing the in-process option was allowed by the text. Skipping the stop was not.
- **Smallest change.** `tester.md:42`: change "Each bot is kept apart from the others: its own process, or its own module name with no shared globals" to "Each bot runs in its own process". Also make the stop part of the redeploy command written in `rig/NOTES.md`, so it does not depend on memory. No new rule is needed.

### 1.2 The mandated heads-up run is a 2-seat table, so it mis-measured platform bots [bundle]
- **Instruction.** `tester.md:23-26` and `prompts/RESEARCH.md:136`: every verdict includes "a heads-up run (`--players 2`)".
- **What happened.** BUILDER, 23:16:46 (events.log:138): "MEASUREMENT HOLE (STYLIST A): at the rig's heads-up shape (a 2-seat table) the platform's push/fold accessors return None ... Every heads-up number for C6Ld, A and B against v6/v7 understates the platform bot." BUILDER's workaround was to measure "6-seat tables with two left". The platform did what `platform.md:82-85` asks: it refused a table format it did not know. The 2-seat config is a shape the real event never presents.
- **Cost.** Heads-up figures for the A/B/C styles were biased from the first verdicts (about 22:46) until about 23:17, the hour in which styles were compared with design D for practice and round-1 picks.
- **Right to?** Yes.
- **Smallest change.** `tester.md:26`: change "(`--players 2`)" to "(a six-seat table with four seats already out, so `state.config` is the real one)".

### 1.3 The kickoff's "strategy/ is suggestions" against "DECISION_RULES always applies" [bundle, plus the humans' kickoff text]
- **Instructions.** The pasted kickoff (prompts.md, 22:13:30 and 22:13:36): "Apart from the hard rules in CLAUDE.md, treat ... (notes/pre/ and strategy/) as well-informed suggestions". But `CLAUDE.md:49` says "`DECISION_RULES.md` (how we decide: always applies)", `prompts/BUILDER.md:22` says "(how we decide: it always applies)" and `prompts/RESEARCH.md:23` says "(always applies)". DECISION_RULES lives in `strategy/`.
- **What happened.** No session said it saw the conflict (searched: not found). Both main sessions treated DECISION_RULES as binding: "The rule's answer" appears in 20+ asks, for example RESEARCH 23:33:44: "the bar was +0.74, so the rule's answer is v7". When BUILDER thought a bar was wrong, it went through the bundle's own channel (PLAN CHALLENGE Round-1.5, 23:36) rather than invoking the kickoff line.
- **Right to?** Yes. The sessions resolved it the way Dylan most likely meant it. The risk is that a session under time pressure resolves it the other way.
- **Smallest change.** Drop the line from the kickoff. `CLAUDE.md:138-158` (§6, "The plan is a default, not a mandate") already says it, and says it with the right exception. If it is kept, add "(DECISION_RULES.md excepted)". See also §4.

### 1.4 Releases for candidates, not only for picks [bundle tension; session]
- **Instruction.** `prompts/BUILDER.md:207-208` and `.claude/agents/platform.md:143`: "A release is made for a pick or for a fix to a pick". But `prompts/RESEARCH.md:124-136` starts a tester from a release ("The zip starts the tester"), and the T-4 deadline (`BUILDER.md:171`) needs a verdict in hand. A candidate BUILDER might pick therefore had to be released early to get its verdict in time.
- **What happened.** 17 releases. Besides v1, seven never played a round: v4 and v5 (picks withdrawn for bugs, 22:52), and v9, v10, v11, v13 and v15 (candidates). v9's tester was "cut to legal+seat+counts" (events.log:142). v10 never got a verdict file (`rig/out/` has no verdict-v9.md or verdict-v10.md). RESEARCH spawned 23 per-release testers, all sharing `avalon-rig`'s 40 containers (§5.4). No session commented on the rule. Candidate verdicts without a release did work twice: `verdict-A15.md` and `verdict-D10.md`.
- **Smallest change.** Either delete the sentence at `BUILDER.md:207-208`, or replace it with: "a candidate gets its verdict as a candidate (`rig/out/verdict-<name>.md`); release it when it is picked". The second option removes the tension and the tester load. Leaving it alone is also defensible: nothing broke.

### 1.5 Time-bank wording contradicted by the kit [bundle; possibly artefact]
- **Instruction.** `CLAUDE.md:273`: "one timeout empties it".
- **What happened.** RESEARCH/tester a36eb926, 22:42:29 and 22:46:39: "The kit README says an overrun only spends its excess from the 100 ms bank. That contradicts the brief's line that one slow decision empties it." The session went with the kit. The kit was the organizers' mock, so Sunday's kit may differ.
- **Cost.** None found.
- **Smallest change.** `CLAUDE.md:273`: change "one timeout empties it" to "how a slow decision spends it: read the kit's README at minute 0".

### 1.6 RESEARCH relayed a headline from its own simulation [session]
- **Instruction.** `prompts/RESEARCH.md:9` ("no deep work yourself") and :99-101 (relay a number only from the file itself).
- **What happened.** 22:25:05: RESEARCH wrote and ran a 30-line simulation. At 22:25:29 it broadcast "pocket pairs are the WORST hands", citing "two independent simulations". At 22:29:46 it corrected itself: the claim "holds only when the pot is heads-up". Its next relay (22:26:01) followed the rule exactly: "direction only (from run 2's progress line, not yet a file: no number to build on)".
- **Cost.** An over-general broadcast for about 4 minutes.
- **Change.** None. The rule and the correction worked.

### 1.7 Small departures that cost nothing
- BUILDER/platform v1 run, 22:47:04: "One deviation: I wrote the tester field as 'pending (quick check ...)'". This was within the spirit of `platform.md:147`.
- STYLIST B, 23:16:12: "Heads-up: not covered (the mirror has no n=2 rows)". This was a gap in a theory table, not in the bundle.
- RESEARCH, 23:58:24: "the rule was written for one named spot and v15 changes about seven spot families". This concerns a rule the team made during the run, not one in the bundle.

---

## 2. Instructions ignored without comment (Saturday's additions first)

| Instruction (starting bundle) | Followed? | Evidence |
|---|---|---|
| Two platform runs at minute 0 (`BUILDER.md:76-80`, `platform.md:26-30`) | **Yes, and it paid.** | Both were spawned in one message: v1 run at 22:21:50, core run at 22:22:08. v1 was committed at 22:23:57 and released at 22:24 (minute 4; target 6). |
| Importable skeleton first (`platform.md:29`, :201-204; `BUILDER.md:84`) | **Yes, and it paid.** | Platform core: team Python at 22:22:37, rules card at 22:23:32, INTERFACE stub at 22:24:21, "PACK works" at 22:30:13, check and harness at 22:32:13. The first style zip (`B-1.zip`) was packed at 22:31. Earlier timed runs had the pack command at minute 15. |
| Liveness check (`tester.md:113-115`, `platform.md` check 10) | **Built in; rarely reported.** | `bot/tools/check.py` has a "style-live check" (`--hands 200`). `rig/compare.py:240` counts opens and passes. verdict-v1 says "not live by design" and verdict-v2 has a "Liveness" line. Later verdicts do not mention it. No dead bot appeared, so the check was never tested. |
| Bots kept apart in the rig (`tester.md:42-45`) | **Weaker option chosen; it broke.** | See §1.1. |
| Named base commit (`BUILDER.md:123-132`; `platform.md:55-58`) | **Partly.** | The "what counts as worse" rule was written in advance (state/decisions.md:4-8, 22:43). **No `base-vN` tag exists** (`git tag` is empty). The winning D line shipped standalone ("base: none (standalone)" on v6-v9, v11, v14-v16). The style bots named their platform commit. |
| Tester's verdict file as the record (`platform.md:146-148`; `RESEARCH.md:135-136`) | **The file, yes; the pointer, no.** | Verdict files exist for 15 of 17 releases (no v9, no v10). 16 of 17 VERSIONS lines still say "tester: pending" at the end. Only v6 says "tester: rig/out/verdict-v6.md". Decisions were taken from the files, so nobody was misled. The files were also rewritten as tests landed: verdict-v16.md changed 6 times between 00:33 and 00:40, and its first line flipped from "not fit yet (PENDING ...)" to "fit for a scored round" at about 00:36. |
| Releases only for picks (`BUILDER.md:207`; `platform.md:143`) | **No.** | See §1.4. |
| Relay maths numbers with version and time (`RESEARCH.md:99-103`; `BUILDER.md:135-137`) | **Yes, consistently.** | events.log:9, 11, 15, 16, 20, 29, 30, 50, 75 and 402. Examples: "twist_rule.json v0-fallback made 22:23: fallback, path and call shape only"; "ranking.json v2 (made 22:34, fallback false)". The one lapse is §1.6. |
| Report file name (`CLAUDE.md:200-201`) | **Untested.** | No brief named REPORT.md or FINDINGS.md, and no such file exists in the repo. Not found in any transcript. |
| Times are guides (`CLAUDE.md:146-158`) | **Yes.** | Late items were reported in the asked-for form, for example PLATFORM 00:38:40: "the full check.py ... is late. It didn't fit ..., so it starts by itself when ... round 5 finished and takes about 8 minutes". The clock's [deadline] lines were treated as reminders (BUILDER 23:46:04: "Clock reminder only ... nothing is missing"). No rushed check was found. |
| After compaction, re-read the prompt file first (`CLAUDE.md:202-205`; `BUILDER.md:250-253`; `RESEARCH.md:233-237`) | **No: 0 of 11 main-session compactions.** | BUILDER never re-opened `prompts/BUILDER.md` after 22:13:39, except greps at 22:40. At 23:30:43 it even wrote into its PLAN file "(after compaction: re-read prompts/BUILDER.md first)" without doing so. RESEARCH: one grep at 23:06 and a 30-line read at 23:06:41. No visible harm. |
| One message per point, never acknowledgements (`CLAUDE.md:35-36`) | Mostly | Not scored in detail. |
| Platform reads `notes/pre/buildplan.md`, `format_finals.md`, FIRST_PROMPT Part 1 and TWIST_NOTES (`BUILDER.md:73-74`, brief of a8d926068) | **No.** | The platform core run opened **none** of its four named files and still hit every deadline. |

**Proposed:**
- Delete the `base-vN` tag (`platform.md:56`, "a commit you tag `base-vN` once its release has a tester verdict; ").
- Delete the VERSIONS pointer update (`platform.md:147-148`, from "the VERSIONS line says "tester: pending"" to "after it does."). Let the line name `rig/out/verdict-vN.md` from the start.
- Cut the post-compaction instruction to its one useful part: "after compaction, re-arm your Monitor if it has expired". This applies to `CLAUDE.md:202-205`, `BUILDER.md:250-253` and `RESEARCH.md:233-237`.

All three were ignored with no visible cost.

---

## 3. Length and load

### 3.1 The reading cost context, and context cost compactions [bundle + harness]
- **Context at start** (sum of input, cache read and cache write on each API call):
  - BUILDER: 107 k tokens at 22:13:4x (the harness's own system prompt is about 90 k; OPS's first call already used 89.9 k), 208 k at 22:14:2x after the step-2 reading, and 321 k by 22:30.
  - RESEARCH: 112 k, then 198 k, then 335 k.
  - The step-2 reading in `BUILDER.md:22-26` and `RESEARCH.md:23-27` added about **100 k tokens before minute 0**.
- **The setting.** `.claude/settings.json:2` sets `"autoCompactWindow": 400000`. Every compaction fired at a pre-compaction size of 366-375 k.
- **34 compactions, 56.8 minutes of blocked session time:**

| Session | Compactions | Blocked | Ends of each compaction (laptop time) |
|---|---|---|---|
| RESEARCH | 6 | 11.5 min | 22:35:53, 22:57:40, 23:21:03, 23:47:23, 00:15:09, 00:45:50 |
| BUILDER | 5 | 10.1 min | 22:35:14, 23:01:16, 23:30:10, 00:04:21, 00:36:57 |
| CHALLENGER | 4 | 6.4 min | 22:55:00, 23:25:15, 23:59:42, 00:45:51 |
| TESTER, STYLIST A, STYLIST B | 3 each | 4.8 min each | |
| PLATFORM | 3 | 4.3 min | |
| ANALYST | 3 | 4.0 min | |
| SCOUT, STYLIST C | 2 each | 3.0 min each | |

  The `compact_boundary` time is when the session resumes. Each block is the 72-129 s before it.
- **Where compaction hit a human or a deadline (BUILDER):**
  - 00:34:48-00:36:57: Dylan asked "Should I keep V16 up?" at 00:34:56 (T-5 of round 5, weight 8). The answer came at **00:38:39**, 81 s before the start. The inbox Monitor had also expired at 00:36:33 and was only re-armed at 00:38:42.
  - 23:28:09-23:30:10: "v8 is uploaded" (23:27:50) was answered 298 s later.
  - 00:02:12-00:04:21: "V14 is active" (00:04:53) was answered 183 s later.
  - RESEARCH's 23:45:30-23:47:23 and 00:44:03-00:45:50 blocks fell on round 2's and round 5's data landing.
  - Seven role sessions compacted together between 22:55 and 23:01, during the practice-3 pick.
- **Smallest change** (for Dylan to choose; the rehearsal can't tell what the window would be without the setting):
  1. Cut `BUILDER.md:22-26` and `RESEARCH.md:23-27` to "Read `strategy/DECISION_RULES.md` §3; open the other files when a step names them".
  2. Check whether `autoCompactWindow` can be raised on Sunday's models. A larger window means fewer, later compactions.

### 3.2 Briefs pointed at files nobody opened [session; partly bundle]
Of 44 brief references to `notes/pre/` or `strategy/` files, **17 were never touched** by the subagent that received them:
- Platform core: all 4 (`buildplan.md`, `format_finals.md`, `FIRST_PROMPT.md`, `TWIST_NOTES.md`).
- Scout: `finalists.md`.
- Build-hour tester: `format_finals.md`, `FIRST_PROMPT.md`.
- The 4 analyst lenses: `FIRST_PROMPT.md` (all 4).
- 3 bughunters: `FIRST_PROMPT.md`.
- Challenger D: 3 files it was told *not* to use.

The script and results are in my scratchpad.

The main sessions read selectively, as `BUILDER.md:24` ("Skim") invites:
- RESEARCH read `variants.md` [0+70 of 409 lines], `field.md` [90 of 162], `testplan.md` [62 of 112], `format_finals.md` [143 of 381] and `FIRST_PROMPT.md` [325-567].
- Role sessions started with `cat` of their role file (TESTER 22:27:50, SCOUT 22:28:21, PLATFORM 22:28:31, ANALYST 22:28:36, STYLISTS 22:28:43-22:29:07, CHALLENGER 22:29:19).

### 3.3 Instructions lost to compaction: the clearest length effect [session]
- **TESTER** read `tester.md` in full at 22:27:50 and compacted at 22:55:13. At 23:57:23 it redeployed without the stop step that `tester.md:76-78` asks for (§1.1).
- **STYLIST A** hit the same delete refusal three times (22:34:52, 23:40:19, 00:18:05). Compactions fell between them (23:08, 00:04).
- **Main sessions.** No question a human asked was already answered in a bundle file. The human questions in `prompts.md` were all about the live state.

### 3.4 Which `notes/pre/` files were opened, by whom, and did any change a decision

| File (lines) | Opened by | Used for anything? |
|---|---|---|
| `format_finals.md` (381) | 12 agents: BUILDER, RESEARCH, TESTER, SCOUT, ANALYST, 3 stylists, theory 1 and 3, scout, analyst | **Yes, as a check.** LEDGER L2 (theory, 22:26): "8 check values match format_finals §6 exactly". |
| `stat_definitions.md` (68) | 7 agents: RESEARCH, SCOUT, ANALYST, scout, analyst, theory a4296fc, analyst aab31df | **Yes, as definitions.** `analysis/ANALYST_NOTES.md:55` and :78 use its PFR and depth definitions. |
| `whatwins.md` (105) | BUILDER and the 3 stylist subagents | No citation found. Styles B and C were dropped; C was stopped at 23:42 at −7.18 a table. |
| `variants.md` (409) | RESEARCH (70 lines), theory 2 and 3 (grep) | No citation found. |
| `testplan.md` (112) | RESEARCH, build-hour tester, TESTER | No citation found. |
| `field.md` (162) | RESEARCH, scout, SCOUT | No citation found. |
| `first1000.md` (121) | analyst, ANALYST | No citation found. |
| `contrarian.md` (100) | BUILDER only (22:14:07, as `BUILDER.md:50` asks) | No citation found. |
| `buildplan.md` (102) | BUILDER only. The platform it was written for never opened it. | No citation found. |
| `finalists.md` (2,273 lines, 175 KB) | **nobody** (named in the scout's brief) | — |
| `challenger_bar.md` (282), `placings.md` (148), `field_three_regionals.md` (111) | **nobody** | — |

**Could be cut or moved out of the bundle with no loss on this evidence:**
- `finalists.md`, `challenger_bar.md`, `placings.md` and `field_three_regionals.md`: 2,814 lines, never opened.
- `buildplan.md`: its intended reader never opened it, and the platform hit every deadline anyway.
- In `strategy/`: `EVIDENCE_TABLE.md` (135 lines; only its headings were grepped once) and `LESSONS.md` (248; read once by each main session at start, never cited).

**Caveat (artefact).** The rehearsal field was 20 synthetic "Sim" teams. The notes about the real finalists (`finalists.md`, `field.md`, `placings.md`) could not have helped here by construction, so this run cannot judge their value on Sunday. The case for cutting them rests on nobody opening them, not on their content being wrong.

---

## 4. The kickoff line "treat the research as suggestions"

- **How far it travelled.**
  - It reached 77 of 78 subagent briefs: BUILDER (25/25), RESEARCH (30/30), ANALYST (18/18), TESTER (2/2) and RESEARCH's subagents (2/2), but not STYLIST C's one brief. I checked the full brief text, not the truncated log.
  - It reached **0 of 8 role-session briefs**. The humans' own 22:26 messages told those sessions to "follow that role file exactly", the opposite instruction.
- **Effect: no measurable change found.**
  - No session cited the line to justify departing from a note: searched, not found.
  - It did not loosen DECISION_RULES (§1.3). PLAN CHALLENGES came through the bundle's own mechanism: 22:44 (practice 1), 22:59 (practice 2), 23:36 (round 1.5) and 00:38 (round 4).
  - Design choices followed the data. The clean-room D line, which reads no notes by design (`BUILDER.md:88`), won the practices; the A/B/C corners were dropped by 23:42. That outcome is what the bundle's §6 and DECISION_RULES' exploration rule already ask for.
- **For better or worse.** Neutral on this evidence. Its only identifiable cost is the unresolved conflict in §1.3.
- **Proposed.** Remove it from the kickoff, since `CLAUDE.md` §6 already carries it. If Dylan wants to keep it, add "(DECISION_RULES.md excepted)" and pass it to role sessions too.

---

## 5. Machinery

### 5.1 Clock (`scripts/clock.py run`, PID 16623, started by OPS at 22:14:46) [works]
- **All steps posted on time, none duplicated, none missed.** `state/clock_sent.json` lists all 11 build-hour steps (b0, b10, b15, b17, b20, b27, b30, b37, b40, b47, b50) and every T-step for rounds 1-6. That is 66 keys; window 1's T-20 to T-10 fall inside the build hour by design.
- **Guard lines** (`/tmp/ops2-clock.log`):
  - [deadline] at 23:46 and 00:06 (builder, "a new challenger is released"), and at 00:10 and 00:50 (research, one-change line).
  - [CUT-OFF] at 00:08 (builder: no new challenger this window, although v14 was already active for the 00:10 practice; it was released before the window opened), at 00:30 (research: round 4 data not landed by T-10, correct because it was held), and at 00:52 (research).
- **Its "DYLAN" banners went to a log nobody watched [artefact].** OPS started the clock with `nohup ... > /tmp/ops2-clock.log`. The beeps and banners that `START.md:47` puts in Dylan's tab 2 were not seen in this run. Every human reminder came through BUILDER. If OPS runs the scripts on Sunday, the same will happen.
- **The clock cannot see a hidden round.** It posted "T-10 ... The practice round starts now" at 00:30 for the practice that never appeared.

### 5.2 Portal watcher (`scripts/portal_watch.py`, PID 16622) [works, with one data bug]

**Errors.** `state/portal.json` shows `fails 0` and `last_error None` for the whole run. The organizers' 4-second restart at 00:00:09 was invisible: it fell between polls, and the next poll succeeded.

**Download time** (organizer's "done", from `emu/avalon-emu-dress2f-event.log`, to the watcher's "finished" line, from `/tmp/ops2-watch.log`):

| Round | Done → saved | Card / fingerprint |
|---|---|---|
| P1 | 22:42:13 → 22:42:15 (2 s) | 18 s / 12 s |
| P2 | 22:52:20 → 22:52:26 (6 s) | 16 / 22 |
| P3 | 23:02:19 → 23:02:24 (5 s) | 16 / 22 |
| P4 | 23:12:04 → 23:12:11 (7 s) | 16 / 24 |
| R1 | 23:24:36 → 23:24:37 (1 s) | 19 / 29 |
| P5 | 23:32:51 → 23:32:52 (1 s) | 12 / 31 |
| R2 | 23:44:54 → 23:45:00 (6 s) | 13 / 16 |
| P6 (493 s long) | 23:58:13 → 23:58:15 (2 s) | 14 / 33 |
| R3 | 00:04:47 → 00:04:52 (5 s) | 15 / 20 |
| P7 | 00:12:00 → 00:12:14 (14 s) | 14 / 36 |
| R4 (held) | released 00:34:00 → 00:34:01 (1 s) | 15 / 22 |
| R5 | 00:44:28 → 00:44:31 (3 s) | 15 / 25 |
| P9 | 00:51:56 → 00:51:57 (1 s) | 16 / 38 |
| R6 | 01:04:54 → 01:04:57 (3 s) | 13 / 17 |

The full hand file was saved within 1 s of each result.

**Alarms that worked:**
- Four "URGENT: ... the portal's active bot is X, but the declared live bot is Y": 23:33:08 (v8 vs v7; Dylan clicked v7 by 23:35:24), 00:13:15 (v14 vs v8; v8 re-uploaded at 00:14), 00:33:13 and 00:38:00 (v16 vs v8; resolved by re-declaring v16 at 00:39:27).
- The weights change was posted at 00:26:12, 12 s after it took effect.
- "URGENT health: 6243 missed" at 23:58:15.

**Held round 4.** The results were held until 00:34. The watcher posted **"Round 4 started at 00:20:00" a second time at 00:24:59**, when the organizer finished the round but held the results. The second line is spurious and fed BUILDER's 00:28:45 "round 4 is still running, 8 minutes in". The results were then saved 1 s after release.

**Hidden practice (00:30).** The watcher said nothing, by design: `portal_watch.py:477` raises "should have started" only for scored rounds and practices 1-4. BUILDER guessed at 00:30:28 that it was "probably queued behind" round 4. RESEARCH saw at 00:33:33 that "no practice row exists". Dylan was told to keep v16 up until 00:35 in case the practice ran late.

**Data bug: "played by: unknown" on 13 of 14 rounds.**
- `state/status.md` shows "?" in the Played-by column for every round except round 4, and `played_by.txt` exists only in `data/rounds/11-round-4/`.
- `state/portal.json` holds 15 `played_by` entries, keyed by ids that never appear in `rounds_view`. The mock portal gives a round one id while it runs and another once it is finished; round 4's re-sighting is the only match.
- ANALYST, 23:45:25: "The status file doesn't say which bot played it".
- Whether the real portal changes ids like this is unknown. Possibly **[artefact]**; worth a one-line check of `round.json` on Sunday's first round.

### 5.3 Inbox monitors [works]
**BUILDER** armed 7 times:
- 22:13:45 at start.
- 22:20:06, at b0, as asked (`BUILDER.md:56`).
- After expiry: 22:50:10 → 22:50:40 (30 s) and 23:20:40 → 23:21:08 (28 s).
- Pre-emptively at 23:47:58 and 00:06:33.
- After expiry 00:36:33 → **00:38:42 (2 min 9 s), across its compaction and T-3 of round 5.**

**RESEARCH** armed 7 times:
- 22:13:37 at start.
- At b0, but 2 min late: 22:22:07.
- After expiry: 22:52:07 → 22:52:27 (20 s), 23:22:27 → 23:24:03 (1 min 36 s; it was compacting until 23:21:03 and then busy), and 23:54:04 → 23:54:06.
- Pre-emptively at 00:20:56 and 00:47:23.

**No inbox line was lost.** `feed.py` resumes from its position file: the T-3 line of 00:37:00 reached BUILDER at 00:38:43, late but delivered.

Role sessions had no inbox. They relied on relays from RESEARCH and BUILDER (for example, round 2's DATA LANDED reached ANALYST at 23:45:27, 27 s after the watcher).

**Cross-session messages to a busy role session were held until its turn ended [machinery; matters only if role sessions are used again].**
- `CLAUDE.md:35` says "`SendMessage` reaches it at once (it wakes it)".
- BUILDER's 22:40 "HANDOVER" to PLATFORM was delivered at **22:52:25**, because PLATFORM was in one long turn from 22:38:46. The tool result said: "that session is holding it (a turn is in progress there ...) and runs it when that clears" (BUILDER, 22:32:41).
- ANALYST, 22:32:36: "Nothing from you has reached me yet: no HANDOVER and no 22:31 gaps message". It waited until the resend at 22:39:45.

### 5.4 Safety hook (`scripts/guard.py`) [bundle: right on blocking, noisy on deletes]
**32 refusals** in all: 30 in `state/guard.log`, plus 2 OPS refusals at 22:13:38 and 22:13:40, made before `state/` existed. Every one was read from the transcripts with its full command.

- **12 for blocking.** All correct per hard rule 7 (`CLAUDE.md:103-112`).
  - 10 were foreground `until ... sleep` loops, for example STYLIST B subagent 22:23:56 waiting for `bot/INTERFACE.md`.
  - 2 were `sleep 19; sleep 19` (theory, 22:35:40 and 22:39:17), which the hook added up correctly.
  - **Not false alarms.**
- **20 for deletes: all false alarms.**
  - **16** target paths in `/tmp` or the session scratchpad (under `/private/tmp`), written with a shell variable (`rm -rf $SP/bdir`, `rm -rf /tmp/challenger-dn-$z`). `guard.py` refuses any target containing `$` (line 144: `if "$" in t or "`" in t: return False`).
  - **1** was `find $SP/snap1/bot -name __pycache__ -exec rm -rf {} +` (PLATFORM, 22:38:55).
  - **3** were the text "rmtree" in a grep pattern (OPS ×2, while reading the scripts) or `shutil.rmtree(tmp)` inside a Python edit script (TESTER, 00:08:04).
- **Cost.** About one tool round each. No human saw any of them.
- **Proposed.** No instruction change. Optionally, `guard.py` could resolve `VAR=path` assignments made earlier in the same command, and stop matching the bare word "rmtree" inside grep patterns.

The hook did **not** catch 504 foreground `sleep 10-19` calls, each under its 20-s limit; see §6. No `pkill`, `killall`, `git stash`, `git reset --hard` or portal write was attempted (none refused, and none found in the transcripts).

### 5.5 Modal [bundle mostly followed; the starvation is an artefact]
- **Apps.** Only the two named apps were used: `avalon-rig` and `avalon-theory`.
  - `avalon-rig`: deployed 22:26:48 by the build-hour tester; stopped and redeployed 22:30:56; stopped and redeployed by TESTER 22:39:07; redeployed **without a stop** 23:57:23; 40 warm containers stopped by id 00:03:10-00:03:48.
  - `avalon-theory`: deployed 22:29:23.
  - No third app, and no `modal run` fan-out, was found. Stylists, CHALLENGER and testers called the rig with `mcompare.py`.
- **Containers measured** (`modal container list`; `avalon-theory` was never listed):
  - 00:02:20: avalon-rig 40 (all started before the 23:57 redeploy) and the organizer's `nolimit-emu-rounds` 19.
  - 00:13:39: rig 40.
  - 00:26:53: rig 40.
  - 00:32:14: 51 (rig 40, emu 11), with the emu's shards "trickling in while the rig holds 40" (RESEARCH, 00:32:57).
  - The rig sat at its 40-container cap from at least 00:02 to 00:33.
- **Queueing against the shared cap [artefact].**
  - The organizers' round app ran in the team's workspace, which will not be the case on Sunday.
  - The 23:50 practice took 493 s against about 140 s. PLATFORM (00:03:22) traced its 6,243 missed decisions to "Modal shards 17-18 of 19, iterations 900-999" for every team.
  - RESEARCH hypothesised starvation at 00:28:52 ("rehearsal rounds run on Modal in our workspace and starve when the rig is at cap"). It applied a hold from 00:29: "no new Modal jobs during practices and scored rounds". After the hold, practice 9 took 116 s and round 6 took 294 s, both normal.
- **Rate-limit errors:** none found (searched every transcript for "rate limit", "RateLimit" and "429" in a Modal context).
- **Queueing among the team's own jobs** (RESEARCH.md:131-135 predicted it): 23 per-release testers, 16 bughunters, stylists and CHALLENGER all shared `avalon-rig`'s 40 containers. No job failed for it. Times per job were not logged consistently enough to measure the wait.

### 5.6 Laptop load [fine]
- `load.log` covers 22:40-01:08 (148 samples): median 6.2; 5 samples above 12; **one above the 15 cores: 17.95 at 23:26:41**.
- BUILDER reacted at 23:26:16 with quiet windows ("LOAD is 15.4 on 15 cores ... any timing or upload test run now is inconclusive").
- Before 22:40 there is no log. Sessions reported load 7.5 (22:32), 8-10 (22:42) and 11.5 of 15 (22:43, CHALLENGER).
- One release timing test was "inconclusive: machine loaded" (v10, 23:18; the baseline spiked to 64 ms).
- No upload test failed on the laptop.

---

## 6. Usage (from the transcripts' `usage` fields; last value per API message)

| Session | Kind | Model | API calls | Input M (all) | Cache read M | Cache write M | Output M |
|---|---|---|---:|---:|---:|---:|---:|
| BUILDER | main | fable-5-2 | 484 | 121.7 | 119.9 | 1.80 | 0.69 |
| BUILDER | 25 subagents | opus-5-5 | 1,409 | 216.0 | 211.9 | 4.10 | 0.91 |
| RESEARCH | main | fable-5-2 | 534 | 132.5 | 130.5 | 2.03 | 0.81 |
| RESEARCH | 32 subagents | opus-5-5 | 2,046 | 297.4 | 291.8 | 5.56 | 1.33 |
| OPS | main | fable-5-2 | 20 | 2.2 | 2.1 | 0.05 | 0.01 |
| CHALLENGER | role session | opus-5-5 | 677 | 159.3 | 157.9 | 1.37 | 0.58 |
| STYLIST B | role session | opus-5-5 | 570 | 136.5 | 135.3 | 1.20 | 0.52 |
| TESTER | role session | opus-5-5 | 489 | 115.9 | 114.8 | 1.08 | 0.46 |
| TESTER | 2 subagents | opus-5-5 | 205 | 31.5 | 31.1 | 0.35 | 0.12 |
| STYLIST A | role session | opus-5-5 | 439 | 108.1 | 107.1 | 1.02 | 0.44 |
| PLATFORM | role session | opus-5-5 | 458 | 107.1 | 106.0 | 1.10 | 0.50 |
| ANALYST | role session | opus-5-5 | 440 | 104.9 | 103.9 | 1.06 | 0.46 |
| ANALYST | 18 subagents | opus-5-5 | 337 | 40.5 | 38.6 | 1.94 | 0.45 |
| STYLIST C | role session (+1 subagent) | opus-5-5 | 433 | 101.3 | 100.3 | 1.02 | 0.41 |
| SCOUT | role session | opus-5-5 | 355 | 82.7 | 81.9 | 0.79 | 0.33 |
| **Total** | | | **8,896** | **1,757.7** | **1,733.2** | **24.5** | **8.01** |

- **By model.**
  - Opus 5.5: 7,858 calls, 1,501 M in, 6.50 M out. Of that, 8 role sessions used 914 M in and 3.67 M out, and 99 subagents used 587 M in and 2.83 M out.
  - Fable 5.2: 1,038 calls, 256 M in, 1.51 M out.
- **By 30 minutes (all models, input / output):**
  - 22:00-22:30: 90 M / 0.66 M
  - 22:30-23:00: 428 M / 2.12 M (the peak: 10 sessions starting at once)
  - 23:00-23:30: 411 M / 1.77 M
  - 23:30-00:00: 312 M / 1.23 M
  - 00:00-00:30: 277 M / 1.17 M
  - 00:30-01:00: 223 M / 1.01 M
- **By subagent type** (input M): tester ×23: 200; bughunter ×16: 103; theory ×5: 83; platform ×5: 65; analyst ×20: 46; stylist ×3: 41.
  - The single costliest subagent was the platform v1 run (47.8 M in, 232 calls). It stayed alive from 22:21 to 00:06 doing byte copies and issued 95 `sleep` polls.
- **Polling.** 504 foreground `sleep 10`-`sleep 19` calls, almost all by subagents: 149 minutes slept, **at least 95 M input tokens** on the calls that issued them (more on the calls that read the result). Hard rule 7's 20-s cap made subagents poll in many short steps.
  - Optional change: `CLAUDE.md:103` could let a **subagent** `sleep` up to 60 s per call. That cuts the calls threefold, at the cost of a correction arriving up to 60 s later.
- **Effort.**
  - All three main sessions ran at **xhigh** (`START.md:77` says high).
  - The 8 role sessions ran at xhigh.
  - **All 58 subagents spawned by BUILDER and RESEARCH with `model: "opus"` ran at medium effort.** Subagents spawned by the Opus role sessions ran at xhigh: ANALYST 18, TESTER 2, STYLIST C 1.
  - `START.md:78` ("Subagents use the session's model and effort unless ...") is therefore wrong for this setup. Whether medium effort hurt any verdict is not determinable from this run.
  - If Dylan wants them at high, the kickoff line could say "pass model "opus" and effort "high" in each Agent call".
- **Not counted.** The 34 compaction summaries were not in the transcripts' usage fields that I could find, so the totals above probably exclude them.
- **For Sunday's budget.** A comparable 3-hour day with the role-session split costs about 1.8 B input tokens (98-99% cached) and 8 M output. Without the split, the 8 role sessions' 914 M becomes subagent work. In this run the subagents averaged 6 M input each, against 114 M for each long-lived role session. Most of a role session's cost is re-reading its own long context on every call.

---

## Where the bundle helped (for balance)
- **v1 at minute 4.** The two-run split (§2).
- **Pack command at minute 10.** Skeleton first (§2).
- **No fallback number was built on.** Every theory relay carried a version and a time (§2).
- **No inbox line was lost.** The Monitor expired 6 times and `feed.py` resumes from its position file (§5.3).
- **Every active-bot mismatch was flagged.** Four URGENT lines (§5.2).
- **The false standings were caught from saved data.** SCOUT, 00:18:16: "STANDINGS DON'T ADD UP ... 26.024 x1 + 25.564 x2 + 26.046 x3 = 155.29, but its total says 115.71". This worked only because the watcher keeps raw rows in `state/portal.json`.
- **Twelve foreground blocking loops refused.** None of them in a main session.

## What I could not determine
- Whether the 400 k compaction window was a reduction from the harness default. The rehearsal cannot show what a larger window would have done.
- Whether medium-effort subagents produced worse verdicts or bug hunts.
- `avalon-theory`'s container count at any time, and how long jobs queued inside `avalon-rig`.
- Whether the real portal re-ids a round between running and finished (the played-by bug, §5.2).
- Usage of the compaction calls themselves.
- Load before 22:40.
- Any effect of the notes on Sunday's real field (§3.4 caveat).
