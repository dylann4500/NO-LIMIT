# 01 Timeline: what happened when, against the bundle, and where the time went

**Summary (five lines)**
1. The build hour mostly ran early: v1 at m4.0 and uploaded at m8.0, the rules card at m3.5, the interface stub at m4.3, the rig at m10. Every practice pick was declared before its b17/27/37/47 step, with 2 to 5 minutes of upload margin. Theory's tables were built into the platform late, at m33.7 and m49.9 against "about minute 20".
2. A shared platform existed (code from m5, pack and check from m10 to m11, commit `bfcb0b5` at m19.1). It was never named the base, and the bots that won practices and five of six scored rounds were the standalone D line. The first platform bot to play a portal round was v12, in the 23:50 practice (m90).
3. Every round played the bot that BUILDER meant to play at the start (checked by file hash against the portal's own snapshots). No scored round played a bot without a "fit" verdict, but v16's verdict landed at 00:35:28, 32 s before the T-4 switch deadline, with its bug hunt having run no tests.
4. Most scored windows were late on the T-9 put-back (T-4:48 to T-7:15 against T-9). Round 5 was the muddle: a GO for v8, then "wait until 00:35", then BUILDER went dark for 3.5 min in a context compaction while Dylan's "Should I keep V16 up?" waited. The answer "keep v16" came at T-1:21 and the declaration at T-0:33.
5. The largest losses of time: context compactions in the two main sessions (about 24 min dark in all, one inside round 5's T-6.5 to T-3), GOs buried in a high message rate (1.9 to 3.9 min from GO to upload), the round-5 churn, the 23:50 practice lost to Modal contention (a rehearsal artefact), and the platform and style line, which used four sessions for 90 minutes before its first portal read.

Paths: `F/` = `/Users/dylan/avalon-rehearsal-log/dress2-frozen/`, `R/` = `/Users/dylan/Documents/GitHub/avalon-nolimit/`, `E/` = `/Users/dylan/Documents/GitHub/nolimit-emu2/emu/runs/dress2/`. "m" = minutes after 22:20:00; "T-x" = minutes before the scored round. The bundle is commit `6fc128f` ("starting bundle") of `R/`.

**Classification key:** [B] a defect in the bundle's instructions · [S] session behaviour despite correct instructions · [A] a rehearsal artefact that will not exist on Sunday.

**Logger caveat [A]:** the collector started at 22:40:23 (`F/collector.log` line 1), so `F/files.log` and `F/snapshots/` say nothing about the first 20 minutes. Build-hour times below come from the subagents' own Write calls in `F/transcripts/`, file mtimes, `F/git.log`, and the relay lines in `F/TIMELINE.md`.

---

## 1. The build hour: targets against actuals

Targets come from the bundle's `prompts/BUILDER.md` (minute-0 steps 1 to 5 and "The build hour"), `prompts/RESEARCH.md` ("Minute 0", "Then, still in the build hour") and `strategy/PLAN.md` (Build hour table, lines 93 to 104 and 205 to 240).

| Target (source) | Target minute | Actual | m | Evidence |
|---|---|---|---|---|
| Case F/R established, told to all (BUILDER step 1) | asap | RESEARCH relays "kit says case F" at 22:22:41 | 2.7 | `F/TIMELINE.md` 22:22:41 relay |
| Team Python announced (BUILDER step 2, core run) | asap | 22:23:58 "team Python ready starter-kit/.venv/bin/python" | 4.0 | `F/TIMELINE.md` 22:23:58 relay |
| Rules card `bot/rules.json` (BUILDER step 2) | 5 | first written 22:23:28 by the platform core run | 3.5 | Write in `F/transcripts/.../7fb4c358.../subagents/agent-a8d9260680289ef1a.jsonl` |
| Rules card checked against the kit (RESEARCH tester) | asap | `rig/out/rules_check.md` 22:24:29; RESEARCH: "no mismatch against the kit" 22:23:50 | 4.5 | tester `agent-a87d471cba9fc621d.jsonl`; `F/session_timeline.md` 22:23:50 |
| Interface stub `bot/INTERFACE.md` | 6 | 22:24:15 | 4.3 | core run Write |
| First legal bot v1 released | about 6 (deadline 10) | commit `bcf0b43` 22:23:57, VERSIONS 22:24:04, declared 22:24:32 | 4.0 / 4.5 | `F/git.log`; `F/TIMELINE.md` 22:24:32 [live] |
| v1 uploaded and active | 10 | uploaded 22:27:57 (Dylan: "v1 is uploaded" 22:29:09) | 8.0 | `F/emu/run/avalon/portal_state.json` subs[0] |
| Activation behaviour settled (BUILDER step 4: read it at v1's upload) | about 8 to 10 | "ACTIVATION SETTLED (Dylan, 22:50)". At 22:29:27 BUILDER still told RESEARCH "v1 not yet uploaded" | 30.8 | `F/TIMELINE.md` lines 77, 199 [S] |
| Importable skeleton `bot/avcore/` | about 15 | 22:25:13 to 22:29:23 (agent.py) | 5.2 to 9.4 | core run Writes |
| Pack and check commands | by 15 | `bot/tools/pack.py` 22:30:06, `check.py` 22:31:14 | 10.1, 11.2 | core run Writes |
| Test harness (platform) | by 15 | `bot/tools/harness.py` 22:32:01 | 12.0 | core run Write |
| Platform committed | none set | `bfcb0b5` "platform core: avcore base, rules card, interface, pack/check/harness tools" 22:39:07; core reported "not yet clean on speed: 3 of 20,400 decisions over 1 ms" | 19.1 | `F/git.log`; `F/session_timeline.md` 22:39:24 FINISH |
| Theory's tables built into the platform | about 20 | push/fold and range-equity accessors and post-pass model `3a76460` 22:53:42; multiway call threshold `74a436e` 23:09:52 | 33.7, 49.9 | `R/` git log [S] |
| Format card (theory 1) | 3 | `format_card.json` v1 "made 22:25" | 5.8 | relay 22:26:17; mtime 22:25:47 |
| ICM thresholds + hand ranking | 10 | ICM v1 mtime 22:26:41 (relayed 22:29); ranking v1 a fallback at 22:29, ranking v2 (fallback false) made 22:34 | 6.7 / 14.4 | `F/TIMELINE.md` 22:29:00, 22:38:23 |
| Multiway call table `call_multiway.json` | about 12 | mtime 22:27:50, relayed 22:29 | 7.8 | same |
| Twist rule `twist_rule.json` | 15 | v0 fallback 22:23; v1 (fallback false) made 22:29 | 9.7 | relay 22:30:17 |
| Push/fold, call tables, break-evens | 15 | pushfold v1 a fallback at 22:29; pushfold-v2 made 22:33 | 13.5 | relay 22:38:23 |
| `theory/HANDOFF.md` | 20 | "HANDOFF.md exists" 22:29:41 | 9.7 | relay 22:29:41 |
| Deep card | 3 (with format card) | `deep_card.json` v1 made 22:31 | 12.6 | relay 22:32:31 |
| Test rig: paired runner, sparring, Modal (RESEARCH tester) | 15 | `rig/compare.py` 22:25:38, `rig/modal_app.py` 22:26:44 | 5.6 to 6.7 | tester Writes |
| Verdict on v1 | none set | `rig/out/verdict-v1.md` 22:30:14 | 10.2 | tester Write |
| Dry-run download (analyst) | about 10 | "dry run passed", relayed 22:30:54 | 10.9 | `F/TIMELINE.md` 22:30:54 |
| Round card ready for practice 1 (about 25) | 25 | `analysis/roundcard.py` 22:28:31; card on practice 1 ready 22:42:33 (18 s) | 8.5 / 22.6 | analyst Write; `F/TIMELINE.md` 22:42:33 |
| Scout tools (fp_train, field_trend, counters) | practice 1 | 22:26:27 to 22:31:30; fingerprint card 22:42:27 | 6.5 to 11.5 | scout Writes; `F/TIMELINE.md` 22:42:27 |
| Design D: DESIGN.md | 12 | 22:24:19 | 4.3 | challenger `agent-a6ba040e97e66dd3f.jsonl` |
| Design D legal and released (v2) | practice 1 | v2 22:32:53 (standalone) | 12.9 | `F/git.log` |
| Styles A/B/C legal on the platform | 2 to 4 min after the packer (BUILDER build hour) | A.zip and B-1.zip packed by 22:31 (mtimes). At 22:41: "every style on the platform had decisions over 1 ms" (gc setting). First style release v4 (B-2) at 22:46:59, on the "OLD base", withdrawn 22:52 for two bugs | 11 / 27 | `F/TIMELINE.md` 22:41:29 decision; `R/rig/out/verdict-v4.md` line 1 [S] |
| Practice 1 pick declared (b17) | 17 | v2 declared 22:36:07 | 16.1 | `F/TIMELINE.md` [live-json] |
| Practice 2 pick declared (b27) | 27 | v3 (D2) 22:44:41 | 24.7 | same |
| Practice 3 pick declared (b37) | 37 | v6 (D2b) 22:55:30. The 22:46 plan was style B; B was withdrawn at 22:52 | 35.5 | same; `F/TIMELINE.md` 22:46:17 decision |
| Practice 4 pick declared (b47) | 47 | v7 (D3b) 23:02:52 | 42.9 | same |
| Tester's ranking of practices 1-3, and the style the field rewarded (RESEARCH b40) | 50 | "RECOMMENDATION round 1: v6 live; v7 if practice 4 edge >= -0.6" 23:07:31 | 47.5 | `F/cross_session.md` line 3491 |
| Round-1 bot declared at b50 (tester's best of practices 1-3 = v6; practice 4's bot the challenger) | 50 | v7 stayed declared from 23:02:52. Rule "v7 if practice 4 holds up (about 23.8 or better), otherwise v6", Samuel "Yes, that rule" 23:09:42; re-declared "ROUND 1 bot: v7" 23:12:22 | 52.4 | `F/prompts.md` 23:09:42; `F/TIMELINE.md` 23:12:22 |
| Role sessions (the humans' experiment) | none in the bundle | asked 22:26:05/15; started 22:27:39 to 22:29:09; handovers 22:32 (TESTER) to 22:40 (PLATFORM) | 7.7 to 20 | `F/TIMELINE.md` [session] lines; PLAN-builder lines 146-158 [A] |

**Was there one shared platform the styles built on, and when?** Yes for the styles, no for the team. `bot/avcore` was importable from m5 to m9, packable from m10, and committed at m19.1 (`bfcb0b5`). It was never named the base: the decision written at 22:41:29 ("There is no base yet: no platform commit has a tester verdict") is the only base entry in `R/state/decisions.md` (line 5), and `git tag -l` is empty. Styles A, B and C packed on it, first on the uncommitted tree (v4 and v5 "on the OLD base (pre-bfcb0b5)"), later on named commits (v10, v12 on `d257455`; v13 on `5384acc`; v17 on `29760d1`). Every D-line release (v2, v3, v6, v7, v8, v9, v11, v14, v15, v16) says "base: none (standalone)" in `R/releases/VERSIONS.md`, and v16.zip is a single 265 KB `agent.py`. The bots that played practices 1-5 and scored rounds 1-5 were all standalone. The platform's first portal round was v12 in the 23:50 practice; its only scored round was round 6 (v17). [S]: the bundle's base procedure was written up at 22:41 and then dropped. Whether the procedure is worth keeping belongs to the platform and strategy reviewers.

---

## 2. Every practice and scored round: what played, declared, uploaded, margin

"Played" is the portal's truth. Each round's frozen submission (`E/avalon/uploads/<stage>/submission/`, the folder named in `F/emu/run/rounds/<stage>/uploads.json`) was matched file by file (sha256) to `R/releases/vN.zip`. Every stage matched exactly one release. Upload times are from `F/emu/run/avalon/portal_state.json` (UTC-8). Margin = round start minus the upload that made the bot active.

| Stage | Start | Played | Declared (live.py) | Uploaded (portal id) | Margin | Verdict at start | Note |
|---|---|---|---|---|---|---|---|
| Practice 1 | 22:40 | v2 (D) | 22:36:07 | 22:37:59 (64856003) | 2:01 | legal/fast YES 22:36:24; fit 22:43:24 (after) | ok for a practice |
| Practice 2 | 22:50 | v3 (D2) | 22:44:41 | 22:45:35 (93d58a9a) | 4:25 | legal/fast 22:47:17; fit 22:53:28 (after) | RESEARCH asked for B instead at 22:46; kept, as it was already with Dylan |
| Practice 3 | 23:00 | v6 (D2b) | 22:55:30 | 22:55:49 (3015adfd) | 4:11 | fit 23:03:32 (after) | ok for a practice |
| Practice 4 | 23:10 | v7 (D3b) | 23:02:52 | 23:04:41 (781d5724) | 5:19 | fit 23:09:34 (26 s before) | |
| **Scored 1** | 23:20 | v7 | 23:12:22 (re-declared) | active since 23:04:41 | 15:19 | fit incl. heads-up | clean |
| Practice 5 | 23:30 | v8 (challenger) | not declared (correct) | 23:27:45 (a3f3aaa9) | 2:15 | fit, file 23:29:47 | the pick was v10 or v9 until 23:25:58 |
| **Scored 2** | 23:40 | v7 | 23:33:38 | 23:35:12 (3af621b1), re-upload | 4:48 | fit | put back 4 min late (see §3) |
| Practice 6 | 23:50 | v12 (style A) | not declared | 23:40:52 (add98b19) | 9:08 | fit 23:38:45 | ran 493 s; v12 missed 6,243 decisions [A] |
| **Scored 3** | 00:00 | v8 | 23:43:01 | 23:52:45 (4208e617), re-upload | 7:15 | fit | |
| Practice 7 | 00:10 | v14 (D5) | not declared | 00:04:43 (908f364b), during scored 3 | 5:17 | fit 23:57:52 | |
| **Scored 4** | 00:20 | v8 | 00:14:36 (after the upload; already live since 23:43) | 00:14:13 (b33d32c8), re-upload | 5:47 | fit | |
| Practice 8 | 00:30 | v16 (D7) | not declared | 00:26:34 (da6d7c2a) | 3:26 | **"not fit yet (PENDING)"** (file written 00:32:39) | hidden from the portal [A]; legal checks only (allowed for a practice) |
| **Scored 5** | 00:40 | v16 | **00:39:27 (T-0:33)** | active since 00:26:34 | 13:26 | fit written 00:35:28 (T-4:32); bug hunt "no test has run yet" 00:34:40 | live.json said v8 from 00:14:36 to 00:39:27 while v16 was active |
| Practice 9 | 00:50 | v17 (A15) | not declared | 00:42:40 (8a6187ed), during scored 5 | 7:20 | fit 00:40:50 | |
| **Scored 6** | 01:00 | v17 | 00:54:01 | 00:54:29 (a1e454bc), re-upload | 5:31 | fit | |

**Wrong bot, or a bot without a verdict?** No round played a bot other than the one BUILDER meant at the start. No scored round played a bot without a written "fit". Two near-misses:
- **Round 5 (v16) [S][A]:** the "fit" headline was written at 00:35:28 by a Bash rewrite of `rig/out/verdict-v16.md`, replacing "not fit yet (PENDING, draft 00:32)" (tester `F/transcripts/.../c8d0c4aa.../subagents/agent-a2bebb529824bebf6.jsonl`). That was 32 s before the T-4 deadline. v16 never had a visible portal practice. Its release bug hunt reported "nothing failed and nothing reproduced, but no test has run yet" (00:34:40, `F/cross_session.md` line 8998). For 25 minutes the declared bot (v8) and the active bot (v16) differed. At 00:33:30 BUILDER had told Dylan "At 00:35, upload releases/v8.zip whatever the portal shows". v16 played because Dylan asked a question instead of uploading, and the rule's answer then moved to v16.
- **Practice 8 (v16)** played on legal and fast checks only. The bundle allows that for a practice; noted because the same bot then played a weight-8 round.

**Click against re-upload [S]:** all five put-backs (v7 23:35:12, v8 23:52:45, v8 00:14:13, v16 00:51:08, v17 00:54:29) were re-uploads, never the "Make active" click that BUILDER asked for (23:32:48: "please click v7 back"). The mock portal has the button (`/Users/dylan/Documents/GitHub/nolimit-emu2/emu/portal_server.py:637`). Each re-upload costs the cooldown and the upload test, about 30 to 50 s before the bot shows active. Harmless tonight.

---

## 3. Scored windows 2 to 6: each step against the bundle's default

Defaults (`prompts/BUILDER.md` window table, `strategy/PLAN.md` lines 120-131): T-15 challenger released · T-12 challenger active · T-10 practice · T-9 live bot put back once the practice shows started (at T-5 at the latest) · T-8 ask · T-5 the rule's answer if nobody answers · T-4 switch deadline · T-3 chosen bot active, nothing decided after.

**Round 1 (23:20), for reference:** question asked at 23:08:02 (T-11:58), Samuel's rule 23:09:42, RESEARCH FINAL 23:12:32, BUILDER "Round 1 plays v7" 23:14:43, active since 23:04:41. Clean.

### Round 2 (23:40, x2)
| Step | Time | T- | Against the default | Evidence |
|---|---|---|---|---|
| Challenger released | v8 23:07:57 | T-32 | early | `F/git.log` |
| Challenger uploaded / active | 23:27:45 / 23:28:42 | T-12:15 | on time (GO 23:27:28, after the 23:27 cutoff) | `portal_state.json`; BUILDER 23:27:28 "GO: upload releases/v8.zip now" |
| Practice | 23:30:00 to 23:32:51 | T-10 | on time | `F/emu/.../event.log` |
| BUILDER dark (compaction) | 23:28:08 to 23:30:28 | T-11.9 to T-9.5 | | §4 loss 1 |
| Rule put to Samuel; answer | RESEARCH "asking Samuel now" 23:28:59; "Yes, that rule" 23:30:13 | T-9:47 | Dylan was never asked a separate question | `F/prompts.md` 23:30:13 |
| Put-back request | "please click v7 back" 23:32:48 | T-7:12 | 1:48 late; the rule tightened while BUILDER was dark | BUILDER transcript 23:32:48 |
| Final declaration | v7 23:33:38 (BUILDER "Final for round 2: v7" 23:33:46) | T-6:22 | on time | `F/TIMELINE.md` [live-json] |
| Put back (re-upload) / active | 23:35:12 / 23:35:44 | T-4:48 / T-4:16 | **4:12 later than T-9**; before T-3 | `portal_state.json` |
| **Muddle** | 23:39:02 BUILDER posts the **round-3** question; 23:39:14 Samuel "Yes, v8 on that rule"; 23:40:11 Dylan "Wait, so are we supposed to run v7 for round 2?" | T-0:58 to T+0:11 | a next-round question 58 s before a start | `F/prompts.md` [S] |

### Round 3 (00:00, x3)
| Step | Time | T- | Against the default | Evidence |
|---|---|---|---|---|
| Challenger released | v12 23:34:13 | T-25:47 | early | `F/git.log` |
| Challenger uploaded / active | 23:40:52 / 23:41:46 | T-19:08 | early by design (after round 2 started) | `portal_state.json` |
| Question asked; Samuel; Dylan | 23:39:02; 23:39:14; 23:42:46 "Use whichever is best." | T-20:58 to T-17 | 12 min early | `F/prompts.md` |
| Declaration | v8 23:43:01 ("unless style A clears its bar at 23:50") | T-16:59 | early | `F/TIMELINE.md` |
| Practice | 23:50:00 to **23:58:13 (493 s)** | T-10 | the result came after T-4, so style A could not qualify | event log [A] |
| Put-back GO | 23:50:51, at the top of a long answer with the release-history table Dylan asked for at 23:47:52; repeated 23:51:07, 23:51:40, 23:52:11 | T-9:09 | on time, but buried | BUILDER transcript [S] |
| Put back (re-upload) / active | 23:52:45 / 23:52:50 | T-7:15 | 1:45 later than T-9 | `portal_state.json` |
| RESEARCH: no practice result at T-6, so v8 | 23:54:17 | T-5:43 | on time | `F/cross_session.md` line 6142 |
| RESEARCH FINAL | 23:59:08 ("v12 missed 6,243 decisions in the practice") | T-0:52 | for the record only | line 6565 |

### Round 4 (00:20, x4)
| Step | Time | T- | Against the default | Evidence |
|---|---|---|---|---|
| Challenger released | v14 23:55:47 | T-24:13 | early | `R/` git log |
| Challenger GO / uploaded | 00:00:50 / 00:04:43 (during scored round 3) | T-15:17 | early; 3:53 from GO to upload, with BUILDER dark 00:02:12 to 00:04:23 | `portal_state.json`; compaction |
| Samuel's answer (via RESEARCH, before BUILDER asked Dylan) | "Switch if clean" 00:09:37 | T-10:23 | | `F/prompts.md` |
| Practice | 00:10:00 to 00:12:00 | T-10 | on time | event log |
| Put-back GO and question to Dylan (one message) | 00:10:38 | T-9:22 | on time | BUILDER transcript |
| Dylan | 00:11:08 "Just choose the best."; 00:11:44 "there was a bug earlier, and it actually turns out we're rank 6" | | the false standings arrive mid-window [A] | `F/prompts.md` |
| RESEARCH FINAL v8; BUILDER "play the proven bot, v8" | 00:12:24; 00:13:36 | T-7:36; T-6:24 | on time | lines 7740; transcript |
| Put back (re-upload) / active | 00:14:13 / 00:14:59 | T-5:47 | 3:13 later than T-9 | `portal_state.json` |
| Declaration (re-declared after the upload) | 00:14:36 | T-5:24 | | `F/TIMELINE.md` |

### Round 5 (00:40, weight 8 after the 00:26 change): v8 and v16, exactly
| Time | T- | Who | What | Evidence |
|---|---|---|---|---|
| 00:14:36 | | BUILDER | live.json = v8 for round 4 (and, by default, round 5) | `F/TIMELINE.md` |
| 00:20:40 | | organizer | round 4's results held to 00:34; the 00:30 practice hidden; Fibonacci weights from 00:26 | `analysis/organizer_faults.log` [A] |
| 00:21:58 | T-18 | PLATFORM | v16 (D7) released (`bfb2809`); release checks clean 00:22:26 | `R/` git log; BUILDER 00:22:26 |
| 00:23:22 | | RESEARCH | "v16 at 00:30 agreed; round-5 default I put to Samuel is v14" | `F/cross_session.md` line 8344 |
| 00:24:45 | T-15:15 | BUILDER | "GO: upload releases/v16.zip now. It plays the 00:30 practice" | transcript |
| 00:26:34 / 00:27:04 | T-13:26 | Dylan / portal | v16 uploaded / active ("V16 is in." 00:26:45) | `portal_state.json` |
| 00:28 to 00:33 | | BUILDER, RESEARCH | round 4 still shows "running": blamed on their own Modal jobs; every session told to hold Modal (00:28:40 to 00:29:06). The real cause was the organizer's hold [A] | lines 8605-8660, 8947 |
| 00:30:00 | T-10 | portal | practice 8 plays v16 (27.5, 1st) but is hidden: the team never sees it [A] | event log; `organizer_faults.log` |
| 00:30:11 to 00:31:46 | | BUILDER | holds the v8 put-back until "the practice shows as running or at about 00:33" | transcript |
| 00:30:15, 00:31:13 | T-9 | RESEARCH | "RECOMMENDATION round 5 at T-9: v8"; "v8 must be ... active by 00:37" | lines 8796, 8848 |
| 00:32:17 | T-7:43 | BUILDER | "**GO: upload releases/v8.zip now.** ... Round 5 is v8"; v16 "has no practice and no tester's verdict yet" | transcript |
| 00:32:39 | | v16 tester | verdict file written: "not fit yet (PENDING, draft 00:32)" | tester transcript |
| 00:32:47 | T-7:13 | Dylan | "Should I upload V8 or leave V16 up? I think it's just delayed." | `F/prompts.md` |
| 00:33:26 | T-6:34 | RESEARCH | "Please give Dylan GO for releases/v8.zip now" | line 8980 |
| 00:33:30 | T-6:30 | BUILDER | "Leave v16 up for now, but only until 00:35 ... **At 00:35, upload releases/v8.zip whatever the portal shows.**" and "v16 can't qualify for round 5 in time" | transcript |
| **00:33:30 to 00:37:01** | **T-6:30 to T-2:59** | BUILDER | **dark: auto-compaction** (boundary 00:36:57, 368k tokens before) | BUILDER jsonl `compact_boundary` |
| 00:34:01 | T-5:59 | portal | round 4 lands: 4th, 25.68; v8 0 missed | `F/TIMELINE.md` |
| 00:34:40 | | bug hunter | v16: "no test has run yet" (its runs were gated on round 4 finishing) | line 8998 [B][A] |
| 00:34:45 / 00:34:56 | T-5:04 | Dylan | "The results came back. We got fourth." / "**Should I keep V16 up?**" | `F/prompts.md` |
| 00:35:00 | T-5 | clock | "No clear human answer by now: the rule's answer plays" (nobody applied it: BUILDER was dark) | queued in the BUILDER transcript |
| 00:35:28 | T-4:32 | v16 tester | headline rewritten to "fit for a scored round" | tester transcript |
| 00:36:00 | T-4 | | switch deadline; v16 qualifies by 32 s | |
| 00:36:25 | T-3:35 | RESEARCH | "STOP-AND-ASK ... Proposal that fails safe: Dylan uploads v8 now as planned ... If it says fit, v16 goes back up at 00:38" | line 9082 |
| 00:36:40 | T-3:20 | v16 tester | "v16 VERDICT 00:36: fit for a scored round" | line 9118 |
| 00:37:10 | T-2:50 | RESEARCH | "FINAL round 5: v16, already active; do not upload v8" | line 9184 |
| 00:38:39 | T-1:21 | BUILDER | "**Yes: keep v16 up for round 5, and upload nothing now.**" (3 min 43 s after Dylan asked) | transcript |
| 00:39:27 | T-0:33 | BUILDER | live.py v16 "ROUND 5 bot (x8): the rule's answer outside the top 3" | `F/TIMELINE.md` |
| 00:40:00 | T-0 | portal | round 5 plays v16 (snapshot = v16.zip); true score 27.37, 1st | hash match; results.md |

In short: by the bundle's T-9 rule ("Only a challenger with a tester verdict may stay active past T-9"), v16 should have come down at about 00:31 to 00:35. BUILDER ordered that at 00:32:17, softened it to "at 00:35" when Dylan pushed back, and then went dark. Meanwhile three facts changed: the round-4 result landed with the false standings, v16 got its verdict at T-4:32, and RESEARCH reversed to v16 under the last-rounds bar. Nobody uploaded anything, so v16 stayed, and it was the rule's answer by then. The declaration after T-3 broke "After T-3 nothing is decided". It was harmless because nothing needed to change on the portal. Lateness: the put-back never happened, and the answer and declaration came at T-1:21 and T-0:33. Muddle: three opposite instructions in 6 minutes (GO v8, wait until 00:35, keep v16).

### Round 6 (01:00, x13)
| Step | Time | T- | Against the default | Evidence |
|---|---|---|---|---|
| Challenger released | v17 00:40:36 | T-19:24 | early | `R/` git log |
| Challenger GO / uploaded / active | 00:41:39 / 00:42:40 / 00:43:11 (during scored round 5) | T-17:20 | early | `portal_state.json` |
| Dylan | 00:49:38 "Wait, I have V17 in the practice. Is that supposed to happen" | T-10:22 | the T-12 upload went in 17 minutes earlier, so he lost track | `F/prompts.md` |
| Practice | 00:50:00 to 00:51:56 | T-10 | on time | event log |
| Put-back GO / re-upload | 00:50:25 / 00:51:08 | T-8:52 | on time | transcript; `portal_state.json` |
| Question | 00:51:11 | T-8:49 | on time | transcript |
| Dylan | 00:51:41 "You choose." | | | `F/prompts.md` |
| RESEARCH FINAL / BUILDER GO v17 | 00:53:38 / 00:53:46 | T-6:14 | on time | line 10354; transcript |
| Declaration | 00:54:01 | T-5:59 | on time | `F/TIMELINE.md` |
| Upload / active | 00:54:29 / 00:55:16 | T-5:31 / T-4:44 | on time | `portal_state.json` |

**Pattern [S]:** the put-back landed at T-4:48, T-7:15, T-5:47, never, and T-8:52 against T-9. The late ones followed a BUILDER compaction (round 2), a GO buried in a long answer (round 3), or news arriving mid-window (round 4, the false standings [A]). Margins never fell below 4:16 before a scored start. Questions were asked anywhere from T-21 to T-7:43, not at T-8. Twice (rounds 2 and 6) Dylan was confused by an instruction about the other bot.

---

## 4. Where the minutes went: the five largest losses

| # | Loss | Minutes | Cause | Kind | Evidence |
|---|---|---|---|---|---|
| 1 | **Context compactions in the two main sessions.** BUILDER compacted 5 times: dark 22:33:12-22:35:16, 22:59:23-23:01:17, 23:28:08-23:30:28, 00:02:12-00:04:23, 00:33:30-00:37:01. RESEARCH compacted 6 times (about 2 min each). Role sessions compacted 2 to 4 times each | BUILDER 12.0, RESEARCH 11.8; the worst was 3.5 min inside round 5's T-6.5 to T-3 | contexts reached about 368k tokens every 25 to 35 min, driven by relay volume: 1,252 SendMessage calls (RESEARCH 505, BUILDER 299) and 154 BUILDER turn ends in the 105 min after 23:20 | [S], real on Sunday | `compact_boundary` entries in `F/transcripts/.../7fb4c358...jsonl` and `c8d0c4aa...jsonl`; counts from `F/cross_session.md`, `F/session_timeline.md` |
| 2 | **GOs buried in a high message rate**, so GO to upload ran 1.9 to 3.9 min: v1 3:25 (22:24:32 to 22:27:57), round-3 put-back 1:54 (GO at the top of a release-history table), practice 7 3:53 (with BUILDER dark), round-4 put-back 3:35 (rank-6 news), round-2 put-back 2:24 | about 15 of upload margin | Dylan reads a terminal that posts about 1.5 turns a minute, many of them "Nothing for you to do". Each GO shared a message with tables and news. Every put-back was a re-upload, not a click | [S] | GO and upload times in §2 and §3; BUILDER 23:50:51, 23:51:07, 23:51:40, 23:52:11 |
| 3 | **Round-5 decision churn** from 00:24:45 to 00:39:27: three opposite instructions; the answer at T-1:21 and the declaration at T-0:33. Also about 9 min of testing stalled (v16's bug hunt and local verdict runs, the ANALYST 12.5-min gap) because runs were gated on "round 4 shows finished" | about 15 of main-session attention; v16's verdict about 7 min later than it could have been | Artefacts: results held and the practice hidden. Session: compaction at the critical minute; a "wait until 00:35" given to a human. Bundle: the quiet-window and bug-hunt gating keyed to the portal's "finished" flag; the T-9 put-back keyed to "practice shows started" | [A] + [S] + [B] | §3 round-5 table |
| 4 | **The 23:50 practice lost.** It ran 493 s against about 140 s; v12 (style A's first portal test) missed 6,243 decisions; the result came at 23:58:13, after round 3's T-4 | 8 min of the round plus the build line's only portal read until 00:50 | the team's own rig held up to 40 Modal containers in the workspace the mock rounds ran on. Modal holds were ordered only at 00:28, and then for the wrong round (round 4's delay was the organizer's hold) | [A] on Sunday (the organizers' rounds will not share the team's Modal); [S] in the misdiagnosis | `F/cross_session.md` lines 6565, 8605-8660, 8947; BUILDER 23:56:34 |
| 5 | **The platform and style line took 90 minutes to its first portal read.** Platform committed m19.1 and "not clean on speed"; never named the base. B's v4/v5 (m27/m29) withdrawn for bugs at 22:52; C's v10 (23:18) never played, and C stopped at 23:42 ("loses about 7 points a table to v7"). A's first portal round was 23:50 (lost, loss 4); its next was 00:50. Role sessions sat read-only from about 22:28 until their 22:32-22:40 handovers | about 4 sessions x 90 min for one round-6 bot; practices 1-5 all played the D line, against the bundle's "at least every other practice plays a genuinely different design" until 30% of the weight | no named base meant every style re-proved its timing; the gc setting in `runner.py` pushed decisions over 1 ms (PLAN-builder line 148); the role-session switch at m6 to m20 [A] | [S] (+[A] for the handover) | `R/releases/VERSIONS.md`; `R/rig/out/verdict-v4.md`, `-v5.md`; `F/TIMELINE.md` 22:41:29, 22:46:17; BUILDER 23:42:32 |

Smaller ones, under 3 minutes each: activation behaviour settled at m30.8 rather than at v1's upload; the round-3 question posted at T-0:58 of round 2; the 00:48-00:49 "penalty" joke relayed and retracted in three BUILDER turns.

---

## 5. How sessions used time after the build hour (23:20 to 01:05, 105 min)

Active minutes = minutes with at least one assistant entry (session; or its subagents). Gaps = stretches of 4 minutes or more with no assistant entry. Computed from `F/transcripts/`.

| Session | Active min (session / subagents / either) | Gaps of 4+ min (total) | What the gaps were | Useful output that reached the portal after 23:20 |
|---|---|---|---|---|
| BUILDER | 89 / 63 / 99 | 4 (round 6 running) | none: 154 turn ends, mostly relays and "nothing for you" | decisions; every GO |
| RESEARCH | 95 / 79 / 97 | 0 | none: 283 messages sent after 23:20 | every recommendation; the standings and pin analysis |
| CHALLENGER | 78 / 0 / 78 | 0 | none | v14, v16 (played P7, P8, R5); v9, v11, v15, D9, D10 never played |
| STYLIST A | 68 / 0 / 68 | 9 | waiting on Modal runs (23:41, 23:49) | v12 (P6, lost), v17 (P9, R6) |
| STYLIST B | 65 / 0 / 65 | 16 | load-18 laptop (23:26); Modal hold (00:29-00:38) | pieces merged into D-line candidates that never played |
| STYLIST C | 49 / 4 / 50 | 28 | quiet windows and Modal queue (23:51-00:00, 00:10-00:21, 00:31-00:40) | v10 (never played); stopped 23:42 and redirected to the D line; the d3h_defend setting went into v16 |
| PLATFORM | 60 / 0 / 60 | 28 | "local runs queued behind round 4"; "full check waits for round 5" (00:38-00:48) | platform commits for v17's base `29760d1` |
| TESTER | 69 / 8 / 73 | 24 | waiting on round data and quiet windows | verdict cross-checks; standings sums |
| ANALYST | 59 / 39 / 66 | 37 | "Nothing to run until Round 4 lands" (00:17-00:23, 00:24-00:36) | round cards and lenses |
| SCOUT | 44 / 0 / 44 | 47 | quiet windows (23:17-23:24, 23:59-00:05) and waiting for data (23:47-23:58, 00:18-00:27) | field trend; the round-4 PLAN CHALLENGE (copies, donors) |
| OPS | 0 | all | by design (ran the scripts) | |

Reading [S]: after the build hour, the two main sessions were never idle; they were saturated by relaying, which also drove their compactions (loss 1). The role sessions were active 44 to 78 of 105 minutes. Their gaps were waiting, not idleness: quiet windows during rounds, Modal holds, data not yet landed (round 4's held results [A] made the longest of them). The work that reached the portal after 23:20 came from CHALLENGER (the D line) and STYLIST A. STYLIST B and C, and most of PLATFORM's later commits, fed candidates that never played.

---

## Proposed changes (exact wording; Dylan decides)

1. **Compactions in the window** (loss 1, real on Sunday). In Dylan's own START.md checklist, not a session rule, add one line: "When each scored round starts (T-20), type `/compact` in BUILDER and ask Samuel to do the same in RESEARCH." The dark two minutes then fall at T-20, not in T-9 to T-3. This is a human action and adds nothing to the sessions' instructions.
2. **GO messages** (loss 2). In `prompts/BUILDER.md`, under "Talking to Dylan" (bundle line 246), replace "Keep it short: what's happening, what he must do and by when (exact file names: `releases/v7.zip`), or "nothing right now"." with "When Dylan must act, that message holds only the action, the file and the deadline; everything else goes in the next message. When nothing is needed from him, say nothing." This replaces a line rather than adding one.
3. **Gating on the portal's "finished" flag** (loss 3, [B]): no change. Results can be late on Sunday too. RESEARCH.md already says late data stops only new changes, and the T-9 row already has "at T-5 at the latest". The muddle came from the compaction and the softened instruction, not from the rule.
4. **Click against re-upload**: no change. It cost seconds.
5. **The 23:50 practice and Modal**: no change. On Sunday the organizers' rounds do not share the team's Modal workspace [A].

## Could not determine
- Build-hour file creation from `F/files.log` (it starts at 22:40:23). Times above come from subagent Write calls and mtimes.
- Whether Dylan saw BUILDER's 00:33:30 "at 00:35, upload v8" before asking at 00:34:56. Nothing in the logs shows what was on his screen.
- When the portal's active bot was first seen as v1 (no watcher snapshot before 22:40).
- Exact compaction start times: the "dark" span runs from the last assistant entry to the next one, so it includes any time spent waiting for a turn to start.
