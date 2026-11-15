# 05 · The humans and the sessions (dress2)

**Summary (five lines)**
1. Human steering worked. Of 57 human messages, 47 got a reply within 2 minutes, none was ignored, and every answer Samuel gave reached BUILDER word for word. The one late answer that mattered was Dylan's "Should I keep V16 up?" at 00:34:56: BUILDER was compacting and replied 3 min 43 s later, 81 s before the round-5 deadline.
2. The two sessions asked 34 distinct questions in 55 prompts, plus 19 push notifications. Dylan did every upload (median about 1 min, slowest about 5). He never answered the rule questions; he handed the call back three times ("Use whichever is best", "Just choose the best", "You choose"). Samuel answered 6 of RESEARCH's 12 questions, each within 40 s except one; the other 6 got no answer at all.
3. Running roles as 8 separate sessions bought nothing it was meant to buy: no human typed into any of them. It cost a 26-minute handover, peer messages held up to 12 minutes, a message cap that needed a human to unblock it, 23 extra compactions and about half of the night's tokens. **Recommendation: drop it for Sunday** and run the bundle as written, with background subagents.
4. BUILDER and RESEARCH disagreed openly and sensibly. But three times the two humans were given different versions of the same bot question or instruction (round 1 at 23:08, round 2 at 23:28, round 5 at 00:33).
5. OPS kept both scripts up all night and nothing needed a restart. Both sessions asked within 2 minutes whether this was a rehearsal, and both humans said yes, so every session knew from 22:15. That changed behaviour once in a way Sunday won't have: PLATFORM read the organizer emulator's own files and wrote a persistent memory note about them.

Evidence root: `/Users/dylan/avalon-rehearsal-log/dress2-frozen/` (abbreviated `F/`). Repo: `/Users/dylan/Documents/GitHub/avalon-nolimit/` (abbreviated `R/`; bundle = commit `6fc128f`). Times are local. "m+" means minutes after 22:20. I extracted the transcripts with `python3 -I` into my scratchpad; the counts below come from those extracts, from `F/prompts.md` and from `F/cross_session.md`.

Kinds of finding: **[bundle]** a defect in the instructions; **[session]** behaviour despite correct instructions; **[rehearsal]** an artefact that won't exist on Sunday; **[experiment]** a result of the separate-sessions request, which the bundle never asked for.

---

## 0. A premise to correct first

The brief says the sessions "were told it was the real event". They were, in the kickoff ("at the No Limit Finals today", `F/prompts.md` 22:13:30 and 22:13:36). Both sessions questioned it within a minute of starting up:
- RESEARCH, 22:14:43: "the watcher (tab 1) is reading a portal on this laptop, `127.0.0.1:8790` ... the laptop's clock says Saturday 14 November". It asked with buttons "Yes, rehearsal / No, real portal".
- BUILDER, 22:14:52: "If this is a rehearsal, say so and I'll treat nothing about this portal as carrying over to Sunday".
- Samuel answered "Yes, rehearsal" (22:14:52) and Dylan answered "Yes, it's a rehearsal ... we're running it like it's real" (22:15:10).

From 22:15 on, every session knew. Every role-session brief opens "Team avalon is in a timed REHEARSAL" (PLATFORM transcript, 22:28:24 host brief). Other reviewers' findings about "behaviour under real-event pressure" should be read with this in mind. **[rehearsal]**

---

## 1. Every human message (57)

BUILDER received 42, RESEARCH 11 and OPS 4. "Reply" is the session's first text after the message. A turn-end recap counts where noted. "Other" says whether the other main session learned of the message.

| # | Time | To | Message (gist) | Reply after | First sentence answers? | Acted on | Other session learned |
|---|---|---|---|---|---|---|---|
| 1–3 | 22:12:36–40 | B, O, R | "hi! wait for instructions" | 2–3 s | yes | yes | typed to all three |
| 4 | 22:13:24 | OPS | OPS kickoff | 130 s | yes (exact portal output) | yes; also found an old pair of scripts still running | n/a (OPS told not to message) |
| 5 | 22:13:30 | R | RESEARCH kickoff | 67 s | yes | yes | – |
| 6 | 22:13:36 | B | BUILDER kickoff | 2 s | yes | yes | – |
| 7 | 22:14:52 | R | "Yes, rehearsal" | 15 s | yes | recorded in PLAN | yes, 22:15:01 |
| 8 | 22:15:10 | B | "Yes, it's a rehearsal…" | 2 s | yes | recorded | already knew |
| 9 | 22:15:39 | OPS | "Yes, stop both" | 15 s | yes | killed by PID | – |
| 10 | 22:18:54 | OPS | "Minute 0 is 22:20. btw" | 8 s | yes | `clock.py start 22:20` | clock lines reach both |
| 11 | 22:20:18 | B | kit zip, "lets go!" | 8 s | yes | yes | yes (kit in repo) |
| 12 | 22:23:17 | R | kit is in the repo, FYI | 3 s | yes | – | typed to both |
| 13 | 22:23:49 | B | same FYI | 93 s | no: opens with the v1 upload request; acknowledged in paragraph 2 | – | typed to both |
| 14 | 22:26:05 | B | run long roles as their own sessions | 65 s | yes | 5 sessions started 22:28–22:29; names given 22:39 | yes, 22:29:24 |
| 15 | 22:26:15 | R | same, for TESTER/SCOUT/ANALYST | 175 s | yes ("Done") | 3 sessions started 22:27–22:28 | yes, 22:28:52 |
| 16 | 22:29:09 | B | "v1 is uploaded" | 76 s (recap) / 156 s (text) | recap yes; first text no | verified on portal | yes, 22:30:13 |
| 17 | 22:38:19 | B | "V2 is in and active" | 19 s | yes | – | status file |
| 18 | 22:46:13 | B | "V3 is active" | **194 s** | yes | – | status file |
| 19 | 22:50:24 | B | uploads become active by themselves | 15 s | yes | recorded in `notes/format.md` | yes |
| 20 | 22:55:57 | B | "RIV6 is in and active" | 11 s | yes | – | status file |
| 21 | 23:04:57 | B | "v7 is active" | **185 s** | yes | – | status file |
| 22 | 23:09:42 | R | "Yes, that rule" (round 1) | 50 s | yes | recorded | yes, verbatim 23:10:16 |
| 23 | 23:13:57 | B | practice 4 results came in | 46 s | yes | – | portal line |
| 24 | 23:16:46 | B | "So we're going to keep V7 for round 1?" | 6 s | yes | – | n/a |
| 25 | 23:27:50 | B | "v8 is uploaded" | **298 s** | no (opens "please click v7 back") | yes | status file |
| 26 | 23:30:13 | R | "Yes, that rule" (round 2) | 10 s | yes | recorded | yes, 23:30:30 |
| 27 | 23:35:28 | B | "I believe V7 is the active one, if that's what you want" | **131 s** | yes | – | RESEARCH saw status 23:35:46 |
| 28 | 23:39:14 | R | "Yes, v8 on that rule" | 36 s | yes | recorded | yes, 23:39:20 |
| 29 | 23:40:11 | B | "are we supposed to run v7 for round 2?" | 17 s | yes | – | n/a |
| 30 | 23:40:56 | B | "v12 is uploaded" | 14 s | yes | – | status file |
| 31 | 23:42:46 | B | "Use whichever is best." | 18 s | yes | declared v8 | yes (live.py line, decisions 23:43) |
| 32 | 23:47:52 | B | release-history table, general vs field-specific, "are we flat?" | 117 s (table at 179 s) | **no** ("Checking that the 23:50 practice has started…") | full answer, all three parts | not relayed (Dylan's own question) |
| 33 | 23:52:48 | B | "v8 is uploaded" | 5 s | yes | – | yes, 23:53:11 |
| 34 | 00:04:53 | B | "V14 is active" | **183 s** | yes | – | status file |
| 35 | 00:09:37 | R | "Switch if clean" (round 4) | 45 s | yes | recorded | yes, 00:09:57 |
| 36 | 00:11:08 | B | "Just choose the best." | 42 s | the reply addressed #37 | recorded and applied | yes, 00:11:31 |
| 37 | 00:11:44 | B | "there was a bug earlier … we're rank 6. So adjust for that" | 6 s ack, full reply 112 s | yes | re-planned round 4 (v8) | yes, 00:13:15 |
| 38 | 00:14:18 | B | "v8 is uploaded" | 38 s | yes | – | status file |
| 39 | 00:26:45 | B | "V16 is in." | 40 s | yes | – | status file |
| 40 | 00:32:47 | B | "Should I upload V8 or leave V16 up? I think it's just delayed." | 43 s | yes (wait until 00:35, then v8) | – | see §4 |
| 41 | 00:34:45 | B | "results came back. We got fourth." | **234 s** | (combined with #42) | – | portal line |
| 42 | 00:34:56 | B | **"Should I keep V16 up?"** | **223 s** | yes ("Yes: keep v16 up") | v16 played round 5 | yes, 00:39:32 |
| 43 | 00:42:56 | B | "V17 is in and active." | 88 s | yes | – | status file |
| 44 | 00:47:43 | B | "are we going to need to take elevated risk here?" | 36 s | yes ("No, we don't need extra risk to reach 3rd") | – | partly (00:51:03 line) |
| 45 | 00:48:24 | R | "Asked, here's why: They punished us for being mean…" | 60 s | **taken literally** | relayed as a penalty | yes, 00:48:47 |
| 46 | 00:49:05 | R | "wait im KIDDING lol it's a bug" | 19 s | yes | correction relayed | yes, 00:49:27 |
| 47 | 00:49:12 | B | "it was a scoring bug … ignore that comment" | 14 s | yes | recorded | yes, 00:49:22 |
| 48 | 00:49:38 | B | "I have V17 in the practice. Is that supposed to happen?" | 7 s | yes | – | n/a |
| 49 | 00:51:41 | B | "You choose." | 8 s | yes | – | yes, 00:51:03 line |
| 50–52 | 00:51:53–00:52:13 | B | iterate on practice data / "We scored really good" / "What should we do now?" | 93–113 s | yes ("GO: upload v17") | v17 to round 6 | yes |
| 53 | 00:54:50 | B | "v17 is uploaded … that's it?" | 9 s | yes | – | status file |
| 54 | 00:55:33 | B | "what can we expect?" | 18 s | yes | – | n/a |
| 55–57 | 01:05:57–01:06:41 | B | "finished sixth", "Samuel was mean", "what should we have finished?" | 4–10 s | yes | – | n/a |

Reply times: 39 within 60 s, 8 within 61–120 s, 10 over 120 s.

**Late answers (over 2 min)**
- #42, the only one that mattered. Dylan asked "Should I keep V16 up?" at 00:34:56. BUILDER was compacting from 00:34:57 to 00:36:57 (`F/transcripts/…/7fb4c358….jsonl`, compact_boundary at 00:36:57, durationMs 120710). The answer came at 00:38:39, with the upload deadline at 00:37 and round 5 at 00:40. Four minutes earlier BUILDER had told him "At 00:35, upload `releases/v8.zip` whatever the portal shows" (00:33:30). Dylan did not upload, and v16 won round 5 with 27.37. **[session + harness]**
- #25, "v8 is uploaded" at 23:27:50. The reply took 298 s because BUILDER compacted from 23:28:09 to 23:30:10. When it came, the reply asked him to undo the upload.
- #18, #21, #27, #34 and #41 were all status reports (an upload done, a result in), where waiting cost nothing.

**Ignored:** none found. "btw" (#10) was even flagged back: "Your message ended with 'btw' and nothing after it" (OPS, 22:19:02).

**Misunderstood**
- #45. Samuel's joke "They punished us for being mean to other people" went to BUILDER as fact at 00:48:47: "So the gap is an organizer penalty, not a scoring bug". BUILDER passed it to Dylan at 00:48:56. It was corrected 40 s later. **[rehearsal]** No organizer existed to ask, so the answer was invented.
- #37 was not misunderstood, but it delivered the injected false standings: "there was a bug earlier, and it actually turns out we're rank 6". BUILDER checked it against the portal, which showed the same false numbers, and adjusted: "the adjustment is to play the proven bot, v8, in round 4 and not gamble" (00:13:36). Dylan's question 34 minutes later (#44, "are we going to need to take elevated risk here?") suggests he expected the opposite reading of "adjust". **[rehearsal]**

**First-sentence rule** (`R/prompts/BUILDER.md` line 248: "When he asks something, your first sentence answers."): it was kept for every question except #32, where the first sentence was a progress line and the answer followed 3 minutes later.

---

## 2. What the sessions asked of the humans

Asks were counted from the `ask` field of `mcp__ccd_turn__wrap_up` (the question box the app shows) and from push notifications. BUILDER put **22 distinct questions in 36 prompts** to Dylan and sent 18 pushes. RESEARCH put **12 distinct questions in 19 prompts** to Samuel and sent 1 push. OPS asked one question ("Stop the two older copies?"), answered in 11 s.

**Dylan (BUILDER)**

| Ask (first time) | Times asked | Answer | Delay |
|---|---|---|---|
| Upload v1 (22:25:16) | 1 | "v1 is uploaded" | 3 min 53 s |
| Did you click after v1 / did v2 activate itself / do uploads activate themselves (22:30:25 → 22:49:20) | 5 | "they become active like automatically" | 20 min after the first ask, 64 s after the clearest wording |
| Upload v7 (23:04:09) | 1 | "v7 is active" | 48 s |
| Round 1 rule "about 23.8 or better" (23:07:55) | 3 | none; Samuel answered | – |
| Upload v8 for practice (23:27:23) | 1 | "v8 is uploaded" | 27 s |
| Round 2 rule (23:28:08) | 1 | none; Samuel answered a different version | – |
| Click v7 back (23:32:42, marked blocking) | 5 + 3 pushes | "I believe V7 is the active one" | 2 min 46 s |
| Round 3: v8 instead of v7 (23:38:54) | 2 | "Use whichever is best." | 3 min 52 s |
| Upload v12 (23:40:23) | 1 | "v12 is uploaded" | 33 s |
| Upload v8 once the practice runs (23:50:26) | 1 + 2 pushes | "v8 is uploaded" | 2 min 22 s |
| Upload v14 (00:00:44, while round 3 was running) | 1 | "V14 is active" | 4 min 09 s |
| Upload v8 after 00:10 (00:09:23) | 3 + 2 pushes | "v8 is uploaded" | 4 min 55 s |
| Round 4: switch to v14 if clean? (00:10:32) | 1 | "Just choose the best." | 36 s |
| What did the organizers say the bug was? (00:14:51) | 1 | **none** | – |
| Upload v16 (00:24:38) | 1 | "V16 is in." | 2 min 07 s |
| Upload v8 for round 5 (00:32:12, blocking) | 1 + 1 push | he asked back instead; overtaken by events | – |
| Upload v17 for the practice (00:41:30) | 2 | "V17 is in and active." | 1 min 26 s |
| Ask an organizer whether our total gets reset again (00:45:07) | 1 | **none** | – |
| Upload v16 as the round-6 default (00:50:23) | 1 + 1 push | uploaded at 00:51:08 without saying so (`F/TIMELINE.md` [upload]) | 45 s |
| Does v17 play round 6 if clean? (00:51:05) | 1 | "You choose." | 36 s |
| Upload v17 for round 6 (00:54:06) | 1 + 1 push | "v17 is uploaded" | 44 s |
| Write it up for the organizers? (01:05:46) | 1 | none | – |

Dylan answered every upload request. On the five rule questions he never chose an option; three times he handed the call back.

**Samuel (RESEARCH)**

| Ask | Times asked | Answer | Delay |
|---|---|---|---|
| Is the 127.0.0.1 portal the one you mean? (22:14:39) | 1 | "Yes, rehearsal" | 13 s |
| Build wider short-shove calls into the practice-4 bot? (22:59:43) | 1 | **none** (`R/state/decisions.md` line 58: "Human's words: none yet") | – |
| Round 1 rule (23:09:16) | 1 | "Yes, that rule" | 26 s |
| Round 2 rule (23:29:53) | 1 | "Yes, that rule" | 20 s |
| Round 3: v8 on that rule (23:38:56) | 1 | "Yes, v8 on that rule" | 18 s |
| Round 4: stay on v8 or switch if clean (00:07:32) | 3 | "Switch if clean" (not the recommended option) | 2 min 05 s |
| Ask an organizer what the correction was (00:18:42) | 1 | **none** | – |
| Round 5: may a bot play if its misses were laptop stalls? (00:23:58) | **5** | **none** | – |
| Round 5: keep v16 or put v8 back? (00:37:21) | 1 | **none** | – |
| Ask an organizer why we sit exactly 6.00 under 3rd (00:47:58) | 1 | the joke, then "it's a bug" | 26 s |
| Play v17 in round 6 if level with v16? (00:50:51) | 1 | **none** | – |
| Write-up for the organizers? (01:05:33) | 2 | none | – |

Samuel answered 6 of 12. Five of the six came within 40 s. He typed nothing between 22:29 and 23:09, between 23:39 and 00:09, or between 00:09 and 00:48.

**What happened when nobody answered.** The bundle's default applied: the rule's answer plays at T-5 (`R/strategy/DECISION_RULES.md` lines 87–88; `R/prompts/BUILDER.md` T-5 row). RESEARCH told BUILDER at 00:30:15: "Samuel has not answered on t[he round-5 question] … the rule's answer for round 5 is the live bot, v8". The rule's answer then changed to v16 when round 4 landed at 00:34. The short-shove change from 22:59 went into v7 and v8 through testing, without his answer. No round was played on a bot that nobody had chosen.

**Clarity.** The upload asks were exact: a file name, a time, and two answer buttons. Two were unclear:
- The click/activation question took three wordings and 20 minutes to get an answer.
- "may a bot play if its missed decisions were laptop stalls, not its own fault?" asked a human to rule on a technical question. PLATFORM had already shown at 00:03 that such misses were the round's machines. Samuel was asked five times and never answered. **[session]**

**Requests a human should not have had to handle: 8 distinct, 16 counting repeats.**
1. Checking what the session could check:
   - BUILDER, 22:19:21: "Paste or screenshot the Format page to me, and say which table it is". BUILDER had read the table off the kit by 22:23 without his help.
   - RESEARCH, 22:14:43: "tell me the announcement time when the variant drops". The watcher posts that line itself.
   - The click/activation fact, asked 5 times. At 22:30:13 BUILDER told RESEARCH that v1 was already "shown ACTIVE in state/status.md at 22:29".
2. Unblocking the app: BUILDER's push at 22:44:42 asked Dylan to "type any reply in BUILDER: my messages to the other sessions are paused until you do". The cause was the app's 20-message limit, which only bit because of the extra sessions (§3). **[experiment]**
3. Relaying: RESEARCH's push at 00:33:23 told Samuel "Dylan must upload releases/v8.zip now", which contradicted what BUILDER was telling Dylan at that moment (§4). **[session]**
4. A technical judgement: the "laptop stalls" question, asked 5 times. **[session]**
5. Duplicates: the same organizer question went to both humans from both sessions (BUILDER at 00:14:51 and 00:45:07; RESEARCH at 00:18:42 and 00:47:58). **[session]**

No session asked a human to run a shell command. The nearest was "Run `/no-limit-2026-setup` in this session" (22:19:21), with the alternative of handing over the kit, and Dylan did that.

**Asking more than once.** `R/prompts/BUILDER.md` line 247 says "Say each upload/activate request once". BUILDER asked "click v7 back" five times plus three pushes between 23:32 and 23:35, and the v8 upload for round 4 three times plus two pushes. Part of this is the app re-showing the open question at every turn end; the pushes were deliberate. Dylan did act each time, slowly at 23:33–23:35 and 00:09–00:14. **[session]** No change proposed: the rule is already there and short.

---

## 3. The separate-sessions experiment

**What was asked.** At 22:26 both humans asked for the long-lived roles to be "their own sessions that Samuel and I can open and type into". The sessions started at 22:27:39–22:29:09 (`F/TIMELINE.md` [session] lines 65–75).

**Did the humans type into them?** No. All 8 role sessions have 0 human prompts (`F/prompts.md`, Sessions list). The point of the change was never used. I could not tell whether anyone opened them to read.

**What the mid-build switch cost**
- **Handover took 26 minutes.** Each session spent 2–4 minutes reading in, sent "ready" and waited for a HANDOVER message. Handovers arrived as follows:

  | Role | Received |
  |---|---|
  | TESTER | 22:31:50 |
  | ANALYST | 22:32:48; it had complained at 22:32:36 that the handover "has not reached" it, and RESEARCH re-sent it |
  | CHALLENGER | 22:35:50 |
  | STYLIST A | 22:37:14 |
  | SCOUT | 22:38:15 |
  | STYLIST C | 22:40:27 |
  | STYLIST B | 22:44:43, sent 22:38:19 |
  | PLATFORM | **22:52:25, sent 22:40:02** |

  That window covered practices 1 and 2.
- **Messages to a busy session wait for its turn to end.** PLATFORM was in one turn from 22:38:46 to 22:52:22 and received seven BUILDER messages at once at 22:52:25. They included the HANDOVER and "APPLY p12345.diff NOW" (PLATFORM transcript; delivery lags measured against send times: PLATFORM median 0 s but 7 messages over 5 min, the longest 743 s). Meanwhile:
  - PLATFORM had found the heads-up equity bug at 22:41:53.
  - BUILDER released v4 and v5 (style B) carrying that bug, then withdrew them ("Do not upload v4 or v5", 22:52:03).
  - The fix landed at 22:53 (commit `3a76460`).
  - Style B lost its practice-3 slot. v6 took it and won, so the score cost was small.

  CHALLENGER (715 s), ANALYST (408 s) and STYLIST B (384 s) also waited over 5 minutes for at least one message. **[experiment]**
- **The app's message limit.** BUILDER's sends at 22:44:16 and 22:44:23 (to STYLIST A and STYLIST C) failed with: "Not delivered: this session has already messaged Claude Desktop sessions 20 times since your user last typed here". They were the only two failures of 1,278, and both were re-sent by 22:48:14 with nothing lost. I could not tell why RESEARCH (190 sends to BUILDER, Samuel silent for 40 minutes) never hit the limit. Both ran in bypass mode.
- **Context and compaction.** The 8 role sessions compacted 23 times between them (§7). In tokens read, the role sessions' main threads account for about 906 M of the night's roughly 1,733 M: about 52% (cache reads summed from the assistant `usage` fields; BUILDER and RESEARCH mains about 250 M; all subagents about 575 M). Each role session also wrote 7–33 summaries and turn-end recaps addressed to a human who never read them.
- **Shared Modal.** Several sessions ran test jobs at once on one 40-container app. That needed container quotas ("v13's tester and STYLIST B hold 12 each", RESEARCH 00:07:18) and a Modal hold ("MODAL HOLD, all sessions", BUILDER 00:28:53). A rig bug (warm containers leaking one bot's modules into another's job) was found at 23:53–23:57; STYLIST B estimated "about 1 shard in 5 of platform-zip jobs on the old rig ran a leaked platform" (00:08:38). Concurrent jobs from many owners made both problems more likely. Subagents would share the same app, so this is only partly the experiment's doing.

**How work and results flowed back.** Through SendMessage to BUILDER or RESEARCH, plus 102 app notices "The session X you started … finished a turn", which arrived inside the humans' own prompts (71 into BUILDER, 31 into RESEARCH). Nothing was lost permanently. Delays and duplicates:
- PLATFORM's handover (12 min late) and ANALYST's (queued, then re-sent).
- Duplicate drafting during handover. STYLIST B built "B v2" in its scratchpad while BUILDER's subagent was still editing `candidates/B` (22:33:33, 22:44:16). STYLIST A had to re-read `style.py` because "the background subagent just changed" it (22:31:23).
- The organizer question asked four times across two sessions.

**Message volume (1,278 messages in `F/cross_session.md`)**

By direction:

| Direction | Messages | Text |
|---|---|---|
| Session to session | 692 | 802 k chars |
| Parent to subagent | 348 | – |
| Subagent to parent | 238 | – |

By content (keyword sort, checked by hand on the shortest 70 messages):

| Kind | Messages |
|---|---|
| New information or instructions | 1,003 |
| Relays: RESEARCH passing a tester/SCOUT/ANALYST/theory finding to BUILDER (117), BUILDER passing a RESEARCH finding on to builders (38) | 155 |
| Copies of one message to several recipients | 51 |
| Handover and ready lines | 42 |
| Corrections of the sender's own earlier line | 17 |
| End-of-event wind-down | 10 |
| **Acknowledgement only** | **0** |

The shortest message (54 characters) is a correction. The median session-to-session message is 1,070 characters, long for an instruction that said "one line … at each deliverable". The bundle's "never acknowledgements" rule (`R/scripts/say.py` docstring) held. Volume, not acknowledgement, was the cost:
- RESEARCH sent BUILDER 190 messages over 174 minutes, about one every 55 s.
- BUILDER received 281 session messages (395 k characters), plus subagent messages and the 71 app notices.

That inflow is what drove BUILDER to compact every 30 minutes.

**What it bought.** Fresh readers found real problems at read-in:
- TESTER: a warm-container bug (22:30:32).
- SCOUT: two writers on one file (22:32:27).
- ANALYST: 7 issues.
- PLATFORM: the heads-up equity bug (22:41:53).
- STYLIST B: style B folding to only 20% of 3-bets (22:49:46).

Fresh background subagents with the same brief can do this; it did not need separate sessions.

**Recommendation: drop it for Sunday.** Run the roles as background subagents, which is what every bundle file assumes. That needs no bundle change: don't send the "own sessions" message at the kickoff. If a human wants to watch a role, read its output in `notes/` or `candidates/<X>/NOTES.md`. **[experiment]**

---

## 4. BUILDER and RESEARCH with each other

**Disagreements, all handled in the open through `state/decisions.md`**
- **Practice 2 (22:44).** RESEARCH recommended style B. BUILDER kept D2 (v3) because it was "already released, declared and with Dylan five minutes before the start" (`R/state/decisions.md` line 62). D2 came 1st with 21.48. BUILDER was right.
- **The round-2 bar.** RESEARCH tightened it at 23:28 ("my 23:28 message crossed your 23:28:07"). BUILDER then argued it was too strict for small steps (PLAN CHALLENGE Round-1.5, 23:36), RESEARCH agreed, and the rule changed for round 3.
- **Round 4 (00:11).** The two humans' answers ("Switch if clean", "Just choose the best") were reconciled on a strict reading that both sessions agreed. v14 failed it, so v8 played.

**Different statements to the two humans** **[session]**
1. **Round 1.** BUILDER asked Dylan at 23:07:55: "play v7 if practice 4 scores about 23.8 or better". RESEARCH asked Samuel at 23:09:16: "play v7 if practice 4 holds up, otherwise v6?", with a different bar. BUILDER adopted RESEARCH's bar at 23:09. Dylan's "So we're going to keep V7 for round 1?" at 23:16 shows he hadn't followed.
2. **Round 2.** BUILDER asked Dylan at 23:28:08: "keep v8 if the practice is clean and its verdict says fit". RESEARCH asked Samuel at 23:29:53: "play v8 only if the practice shows it clearly ahead". The stricter rule governed, and Dylan was then asked to click v7 back after uploading v8. His "Okay, I believe V7 is the active one, if that's what you want" and "Wait, so are we supposed to run v7 for round 2?" show the confusion.
3. **Round 5, 00:32–00:38, the sharpest case.** Round 4's results were held back by the organizer side until 00:34.

   | Time | From | Said |
   |---|---|---|
   | 00:32:09 | BUILDER push | "GO: upload releases/v8.zip now for round 5" |
   | 00:33:23 | RESEARCH push to Samuel | "Dylan must upload releases/v8.zip now" |
   | 00:33:30 | BUILDER to Dylan | "Leave v16 up for now, but only until 00:35 … At 00:35, upload releases/v8.zip whatever the portal shows" |
   | 00:37:10 | RESEARCH to BUILDER | "the rule's answer is v16 … I recommend Dylan does NOT upload v8 now" |
   | 00:37:21 | RESEARCH to Samuel | "keep v16, which is active now, or put v8 back?" (no answer) |
   | 00:38:39 | BUILDER to Dylan | "Yes: keep v16 up for round 5, and upload nothing now." |

   The bundle already covers this: only "if BUILDER says the portal still shows the old bot at T-3" should RESEARCH have Samuel fetch Dylan (`R/prompts/RESEARCH.md` line 199). RESEARCH's 00:33 push went beyond that.

**Information that reached one human only**
- The round-5 "laptop stalls" question went only to Samuel, 5 times, and was never answered. BUILDER did not put it to Dylan.
- The release-history analysis (23:50:51) and the message-limit unblock went only to Dylan.
- RESEARCH told Samuel round 5 was "weight 5" at 00:24:06, before the weights changed at 00:26, and corrected it at 00:27:16.
- Everything Samuel typed reached BUILDER verbatim. Dylan's decision words reached RESEARCH through `live.py` and `say.py` lines (00:11:31, 00:13:15, 00:49:22).

**Proposed change [bundle, small].** In `R/prompts/RESEARCH.md` line 197, after "Samuel's answer to the decision: relay his exact words to BUILDER with SendMessage.", add: "Put BUILDER's question to Samuel word for word, copied from its `state/decisions.md` entry; never word your own version." This removes cases 1 and 2. Case 3 needs no change.

---

## 5. OPS

- **Did the scripts stay up?** Yes. The watcher and clock (PIDs 16622 and 16623, started 22:14:43) ran to the end. `last_poll` in `R/state/portal.json` is 01:13:10. `last_error` is empty in every one of the 148 snapshots of `state/portal.json`. The clock posted every step through 00:57 (69 `[clock]` lines in `R/inbox/builder.log`). The 4-second portal restart at 00:00:09 left no error.
- **Did anything need restarting?** No. OPS's background watch never woke it; its transcript ends at 22:19:02.
- **Did BUILDER or RESEARCH ever tell a human a script had stopped?** Not found; none did.
- **One real catch at start-up.** An older watcher and clock pair from `~/.Trash/avalon nolimit rehearsal`, running since 21:56 against the same portal and key, still owned `/tmp/ops-*`. OPS started its own pair under `ops2` names, reported the old pair, and stopped it by PID after Dylan's "Yes, stop both" (22:15:48). **[rehearsal]**, but the same leftover could exist on Sunday. At 01:22 today no `portal_watch`/`clock.py` process is running.
- **No change.**

---

## 6. Did any session notice this was a rehearsal, and did it change behaviour?

Both main sessions noticed, asked, and were told yes by 22:15 (§0). The rehearsal changed behaviour in three places:
1. **PLATFORM read the organizer emulator's files** from 00:00:53 to 00:03 to explain the 23:50 practice's misses: `nolimit-emu2/emu/tournament.py`, `rehearsal.py`, `modal_rounds.py` and `runs/dress2/rounds/practice6/results.jsonl` (PLATFORM transcript, Bash calls). It showed "every team failed … only in iterations 900-999" (00:03:15), and that cleared style A's v12 of fault. BUILDER accepted the evidence and noted "The emulator's own run files will not exist on the day" (00:06:45). The reads happened before any fault was set (first at 00:08), so they revealed no fault. **[rehearsal]**
2. **PLATFORM wrote a persistent memory file** at 00:06:22: `/Users/dylan/.claude/projects/-Users-dylan-Documents-GitHub-avalon-nolimit/memory/rehearsal-emulator-miss-data.md`, indexed in that folder's `MEMORY.md` and still present. It loads into any future session opened in a repo at that exact path. START.md puts Sunday's repo at `~/avalon-finals`, a different path, so the risk is low. **Proposed:** Dylan deletes the file and its `MEMORY.md` line, or confirms Sunday's repo path differs. **[rehearsal]**
3. **The Modal hold at 00:28.** BUILDER saw "the rehearsal's round app (nolimit-emu-rounds) in our own workspace" and held all cloud jobs. That was the right call for the rehearsal, where the organizer's rounds shared the team's Modal workspace (the brief confirms this for the 23:50 practice). On Sunday the coupling won't exist. **[rehearsal]**

Not found: any session relaxing a hard rule or a check because "it's only a rehearsal". The rehearsal flag mostly showed up as "nothing carries over to Sunday" in briefs. No session suspected that faults were being injected deliberately. BUILDER only noted at the end that "ours is the only one that doesn't" match (01:06:07).

---

## 7. Context, compaction and restarts

- **No session restarted.** Each has one continuous transcript.
- **34 automatic compactions:**

  | Session | Compactions |
  |---|---|
  | BUILDER | 5 |
  | RESEARCH | 6 |
  | CHALLENGER | 4 |
  | PLATFORM | 3 |
  | STYLIST A | 3 |
  | STYLIST B | 3 |
  | TESTER | 3 |
  | ANALYST | 3 |
  | STYLIST C | 2 |
  | SCOUT | 2 |
  | OPS | 0 |

  Every one fired at about 366–375 k tokens and froze the session for 72–128 s (`durationMs`). BUILDER compacted at 22:35, 23:01, 23:30, 00:04 and 00:37, every 26–34 minutes.
- **Badly timed freezes.** Three BUILDER compactions landed at decision moments:
  - 23:28–23:30: the 23:30 practice upload and the round-2 rule change.
  - 00:02–00:04: the end of round 3.
  - 00:35–00:37: Dylan's round-5 question and deadline (§1, #42).
- **Recovery versus the bundle.** `R/CLAUDE.md` lines 202–205, `R/prompts/BUILDER.md` lines 250–253 and `R/prompts/RESEARCH.md` lines 233–236 say: after compaction, first re-read the prompt file, then the PLAN file, status, clock and inbox, then re-arm the Monitor.
  - In 11 compactions, BUILDER and RESEARCH re-read their prompt file first **0 times**. There were only later targeted lookups (BUILDER grep at 22:40:38; RESEARCH Read at 23:06:41).
  - They read the PLAN file once (RESEARCH `tail -n 25` at 00:18:01). Every other PLAN touch was an append (`cat >> notes/PLAN-builder.md`), for example BUILDER at 23:30:43 writing the heading "after compaction: re-read prompts/BUILDER.md first" without doing it.
  - They did re-read `state/status.md` and the inbox tail in 9 of 11 cases.
- **Role sessions have no recovery rule.** Their briefs gave no recovery instruction and they have no PLAN file. Some re-read their role file (PLATFORM 3 of 3, STYLIST B 3 of 3, CHALLENGER 2 of 4); the others relied on the summary and their NOTES.md.
- **Was anything lost?** Not found. No post-compaction contradiction, repeated job or broken promise traced to a compaction. The app's summary plus the preserved recent messages were enough. The real cost was the frozen minutes.
- **Proposed: no change** to the recovery rule. It is cheap and did no harm, though it was not followed. The fix that addresses the frozen minutes is the §3 recommendation: fewer sessions sending BUILDER less. **[session]**, with frequency **[experiment]**.

---

## Proposed changes, ranked by what they would save on Sunday

1. **Drop the separate-sessions set-up.** Don't send the 22:26 kickoff message; keep the bundle as written. **[experiment]**
2. **`R/prompts/RESEARCH.md` line 197:** add "Put BUILDER's question to Samuel word for word, copied from its `state/decisions.md` entry; never word your own version." **[bundle]**
3. **Delete** `~/.claude/projects/-Users-dylan-Documents-GitHub-avalon-nolimit/memory/rehearsal-emulator-miss-data.md` and its `MEMORY.md` line, unless Sunday's repo path is certainly different. **[rehearsal]**
4. **No change** to the compaction rules, the ask-once rule (`BUILDER.md` line 247), OPS, or the fetch-Dylan rule. Each was correct and worked, or failed only through session behaviour.

## Could not determine
- Whether either human opened any role session to read it.
- Why only BUILDER hit the 20-message limit (both ran in bypass mode).
- Whether Samuel's six unanswered questions were never seen or were left on purpose. Remote Control gives no read receipts.
- Whether the time compaction blocked had any score effect beyond the delays measured above. None is visible in the round results.
