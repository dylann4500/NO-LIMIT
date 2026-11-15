# 02 Decisions: which bot played, exploration, plan challenges, faults, Saturday rules (dress2)

**Summary (five lines)**
1. Every which-bot call except round 5 was made by a written rule with the right bar, and the true yardsticks would have changed none of them. The sessions' yardstick sets were wrong in 3 of 5 cases (Drift, Bluff, Arrow counted as unchanged; up to 10 stable teams dropped), but the edges moved by 0.26 at most (R1 +1.39 → +1.13), and no bar was crossed.
2. Round 5 broke the rules. The cut-off rule (no practice result at T-6 → the live bot, v8) was applied at 00:30-00:33 and then dropped at 00:37, after T-4 and with BUILDER compacting. v16 played because it was the bot left active. Both sessions read "the last-rounds bar" as "the strongest bot with a verdict, measured or not", a meaning taken from the no-practice-day section. The bot was good (27.37, 1st), but the call was not made by the rule.
3. The false standings changed two bars: rounds 5 and 6 were run as "6th, last two rounds" (z ≥ 0). On the true standings (1st, leading 4th by 45.6 and then 91.7) the bar was z ≥ 1.5, and round 6 would have stayed on v16. v17's switch (+1.18 adjusted in round 6) helped, but only because of the fault.
4. Exploration went 7 of 9 practices to the D line. Style A was measured twice and won on the portal both times. Style B and style C never played a portal table. BUILDER vetoed them on rig numbers that TESTER later marked UNPROVEN (L254, 00:10, a container-leak bug), and nobody measured them again. The truth says the D line deserved most slots, but the vetoes were not sound by the bundle's own test.
5. Of the Saturday rules: "big lead" and "late data" were used and worked. "One switch deadline" held in rounds 1-4 and 6 and failed in round 5. "Standings held" was never triggered (the fault was standings that were wrong, not hidden). "Times are guides" was used as cover in round 5. The no-practice-day section was never in force, yet its sub-bullets were quoted twice as live rules (00:16, 00:36). That is the one wording defect worth fixing.

Sources: final `state/decisions.md` = `dress2-frozen/snapshots/010620/state/decisions.md` (cited below as "dec L<n>"); BUILDER transcript `7fb4c358…jsonl`, RESEARCH `c8d0c4aa…jsonl` (times are local, from the JSONL timestamps); session edge files `avalon-nolimit/rig/out/edge-*.json`, `rank-*.json`; true results `nolimit-emu2/emu/runs/dress2/rounds/<stage>/results.md`; true field `fixed_bots_by_round.json` plus `organizer_swaps.log`. My recomputation: `analysis/02_edge.py` (reads `02_load.py`), with output in `analysis/02_edges_out.txt`.

Kinds of finding: **[bundle]** a defect in the instructions, **[session]** a session's behaviour despite correct instructions, **[artefact]** something of the rehearsal that will not exist on Sunday.

---

## 1. Every "which bot plays" decision

### How I recomputed
- Edge = (challenger's practice score − mean of yardsticks in that practice) − (live bot's reference score − mean of the same yardsticks then). SE = SD of the yardsticks' own changes × √(1+1/n) for n ≥ 6, floor 0.7 × 1.06 = 0.74, exactly as in DECISION_RULES §3 (lines 66-76).
- "True stable" = every opponent whose effective bot was identical in both stages. This uses the schedule (NOTES §11) plus the 00:11 swaps: the hostile bots on Switch DC/BA/CD and Delta's v7 folder, and the v14 copies on the v9/v10/v12 folders. It includes the three switch teams before 00:11, because their bot is the same zip every round. "Strict 7" is the seven never-change teams.
- Ground truth on the copies: from scored round 4 on, Castle (v12 folder), Bedrock (v9, round 4 only) and Basalt (v9, rounds 4-5 and practices 8-9) played avalon's v14. Cobra joined them at practice 9 when its schedule moved it onto v12. Bishop had left v10 at round 4, so it was never a copy.

### 1a. Build-hour practice picks (rule: "the most informative test", BUILDER's call; DECISION_RULES lines 116-119, 234-236)

| Practice | Candidates | What BUILDER used | Pick | Human | True result | True adjusted gain over the previous pick (20 stable teams, no field change P1-P4) |
|---|---|---|---|---|---|---|
| P1 22:40 | v1, v2 (D) | "the only bot besides the v1 placeholder with zero failed decisions and nothing over 1 ms" (dec L15) | v2 | Dylan: "V2 is in and active" (22:38) | 16.87, 13th | n/a |
| P2 22:50 | v3 (D2), v4 (B-2) | RESEARCH 22:44 "RECOMMEND practice 2 = style B"; BUILDER kept D2 "because it was already released, declared and with Dylan five minutes before the start" (dec L62) | v3 | none | 21.48, 1st | +4.81 ± 0.74 (z 6.5) |
| P3 23:00 | v6 (D2b), B (v4/v5 withdrawn 22:52 for two bugs) | CHALLENGER +4.95 ± 1.49 over D2 in a D2-copies field (dec L63) | v6 | none | 24.38, 1st | +3.07 ± 0.74 (z 4.1) |
| P4 23:10 | v7 (D3b), v3 | rule fixed at 22:59: "v7 if v6 is level with or above v3's 21.48" (dec L64) | v7 | none | 25.48, 1st | +1.13 ± 0.74 (z 1.5) |

Each pick was a fair "most informative" call given the bot that had been released. On the truth each step was a real gain. See section 2 for what this did to exploration.

### 1b. Scored rounds

| Round | Live vs challenger | Session numbers (file) | Bar used, and the bar by the bundle | Rule's answer | Humans' words | Played, true result | True edge (true stable / strict 7) | Would true yardsticks change it? |
|---|---|---|---|---|---|---|---|---|
| R1 23:20 | v6 (best adjusted of P1-3) vs v7 (P4) | +1.39 ± 0.73, z 1.9, 10 yardsticks (`rank-p1p4.md`) | Sessions: v7 if edge ≥ **−0.6**. Bundle: z ≥ 0.5 or 1.0 (no standings yet) | v7 | Samuel "Yes, that rule" (23:09:42); Dylan "So we're going to keep V7 for round 1?" (23:16:46) | v7, 26.02, 1st | +1.13 ± 0.74, z 1.52 / +1.18, z 1.47 | No: clears every possible bar |
| R2 23:40 | v7 (R1 26.02) vs v8 (P5 26.61) | +0.55 ± 0.74, z 0.74, 15 yardsticks (`edge-r15-y15.md`) | z ≥ 1.0, since the lead over 4th, 5.44, is under 6. Bundle: the same | v7 | Samuel "Yes, that rule" (23:30:13); Dylan "Okay, I believe V7 is the active one, if that's what you want." (23:35:28) | v7, 25.56, 1st | +0.54, z 0.72 / +0.62, z 0.84 | No |
| R3 00:00 | v7 (R2 25.56) vs v8 (small-step rule) and v12 = A6 (P6) | v8: pooled +0.58 ± 0.24 (z 2.4), ANALYST spot z 3.0 (dec L138-139). A6: P6 landed 23:58:13, after T-6 | v8 by the sessions' new "small step" rule, which also cleared the written "change to the live bot" bar (real-data z ≥ 1.5; dec L139). A6: z 1.5 (lead 16.46 > 9) plus RESEARCH's own +1.75 against v8 | v8 | Samuel "Yes, v8 on that rule" (23:39:14); Dylan "Use whichever is best." (23:42:46) | v8, 26.05, 1st | v12 P6 vs v7 R2: +1.46, z 1.96 / +1.46, z 1.97. Under +1.75, and late and 2.9% missed anyway. v8 R3 vs v7 R2 after the fact: +0.57 | No |
| R4 00:20 | v8 (R3 26.05) vs v14 (P7 25.82) | −0.17 ± 0.74 (16 yardsticks, `edge-r35-vs-r3-scout35.md`); 6 missed | Small-step rule, condition (2) "0 missed" read strictly (dec L163). Bundle letter on the false standings (6th): z ≥ 0.5; on the truth: z ≥ 1.5 (lead 33.6 > 12) | v8 | Samuel "Switch if clean" (00:09:37); Dylan "Just choose the best." (00:11:08) | v8, 25.68, 4th (three v14 copies above it) | −0.14, z −0.19 / −0.22 | No: negative under any bar |
| R5 00:40 | v8 (R4 25.68) vs v16 (no visible practice) and v14 | Rig only: v16 +1.07 ± 0.37 sane, +1.09 ± 0.32 field1; no portal edge | Sessions: "last-rounds bar: the strongest bot with a verdict" (RESEARCH 00:37:10). Bundle: no practice result by T-6 → the live bot (DECISION_RULES line 216; CLAUDE.md lines 286-288) | v8 by the bundle; v16 by the sessions | Samuel: none since 00:09. Dylan "Should I upload V8 or leave V16 up? I think it's just delayed." (00:32:47), "Should I keep V16 up?" (00:34:56) | v16, 27.37, 1st | Hidden P8 (00:30, v16 27.48): +1.51, z 2.04 / +1.72, z 2.32. After the fact, R5 vs R4: +2.12, z 2.86 | The yardsticks no. The hidden practice would have qualified v16 at z ≥ 1.5 had anyone seen it |
| R6 01:00 | v16 (R5 27.37) vs v17 = A15 (P9 27.66) | +0.63 ± 0.78, z 0.81, 19 yardsticks (`edge-r55-vs-Round5-z3.md`) | First z ≥ 1.5 (00:47, "rows count"), then **z ≥ 0** (00:51, "portal totals are our standing", 6th, last rounds). On the truth: lead over 4th 91.7 > 39 → z ≥ 1.5 | v17 | Dylan "You choose. … close the gap most effectively." (00:51:41), "if it's clean or if it's good, then we might as well run it" (00:51:53); Samuel no answer by 00:54 | v17, 28.58, 1st | +0.63, z 0.81 / +0.52, z 0.51. After the fact, R6 vs R5: +1.18, z 1.59 | No: the session set equals the true set. The **false standings** changed it: on the truth v16 plays |

### 1c. Were the sessions' yardstick teams the right ones?

| Decision | Teams that really changed between the two stages | Session set errors |
|---|---|---|
| R1 (P3→P4) | none | Used 10 and dropped 10 stable teams. That is harmless but noisier, and the edge was overstated by +0.26 (+1.39 against +1.13) |
| R2 (R1→P5) | Sim Drift (v7→v14 at P5) | **Included Drift** and dropped 5 stable teams (Switch DC, Bluff, Arrow, Ace, D3). RESEARCH's FINAL (23:33:22) quotes "SCOUT: no team changed bot", which is false |
| R3/A6 (R2→P6) | Sim Bluff (v10→v15 at P6) | **Included Bluff.** Dropped Bishop and C1, which were stable here; Bishop was dropped for its R1.5→R2 change (RESEARCH 23:48 item 4), which is not inside this pair. "First team to change bot today" (23:48) is also false: Castle changed at R2, Ace and Delta at R1, Drift at P5 |
| R4 (R3→P7) | Sim Arrow (v4→v13 at P7) | The decision set (`scout35`) is clean but dropped Cobra, Bluff and Basalt. Two other files the sessions produced (`scout`, `s17`) included Arrow |
| R6 (R5→P9) | Sim Cobra (onto the avalon-copy folder at P9) | **Exact**: 19 teams, Cobra excluded (RESEARCH 00:53: "Cobra changed bots: 25.83 from 20.68") |

So SCOUT caught the big jumps (Bishop's post-flop change, Arrow, Cobra) and missed the same-family steps (Drift D2→D3, Bluff B3→B4, Castle C→C3). It cost nothing because the yardsticks moved together (SD of the changes 0.4-0.6), so one wrong team in 15-19 shifts the mean by under 0.1. Finding: **[session]** (SCOUT's drift check) is real but low-cost. Proposal: **no change**. The rule's formula is robust to a wrong team or two, and the floor SE (0.74) set z in every decision except R6.

### 1d. Notes on single decisions

- **R1, the −0.6 bar [bundle, minor].** RESEARCH, 23:06:39: "Standing: no scored round yet, so no standings: the bar is z >= 0.5 … 'prefer the more aggressive, worth at most 1 point', applies … v7 plays round 1 if its adjusted edge over v6 is -0.6 or better". The bundle gives no standing before round 1, so the session guessed. It also turned the one-sentence tie-break (DECISION_RULES lines 101-102) into a 1-point discount on the bar, which made it a non-inferiority test. The outcome was the same, since z was 1.9 (true 1.52).
- **R2, classification flip [session].** At 23:25 RESEARCH treated v8 as "the live bot plus this window's one tested change", which only needed the practice "not below −0.74". At 23:28 it withdrew that because the real-data support (L127) "leaned on … a wider spot" (dec L95). For four minutes Dylan held the 23:28 version and Samuel the corrected one; BUILDER re-asked Dylan at 23:32 (dec L102). BUILDER's own view at 23:32:48: "I would have kept v8 unless the practice came out worse". On the truth v8 was worth about +0.55 a table, roughly 1 standings point at weight 2.
- **R3, the "small-step rule" (PLAN CHALLENGE Round-1.5) [session, effect nil].** It was written at 23:36-23:39 because a +0.5 step can never show z ≥ 1.0 in one practice. In R3 the written path also admitted v8 (ANALYST's spot read, z 3.0, dec L139), and in R4 v14 failed either way, so the new rule changed no decision. The A6 bar of +1.75 was RESEARCH's own construction, and it said so: "The +1.75 is my reading, not the written rule" (RESEARCH text after 23:48).
- **R4 [session, deliberate].** On the portal's 6th place the letter gives z ≥ 0.5 plus a divergent challenger. RESEARCH (00:17:03 to BUILDER): "I agree bolder is the wrong move, and recommend we apply none of that". It was disclosed and agreed with BUILDER. v14's edge was negative, so nothing turned on it.
- **R5 [session + bundle wording].** See section 4b.
- **R6 [faults].** RESEARCH changed the bar twice in four minutes on the humans' words about the 6.00 gap: z 1.5 at 00:47; "played to win on our own rows" at 00:50; "portal totals are our standing … z >= 0" at 00:51. Both sessions put the same question to their human (BUILDER 00:50:55, RESEARCH 00:50:58).

### 1e. Were the rules any good in practice?
- At these gaps the rules were conservative and cheap. The only switch the bars refused was v8 in R2, worth about 1 standings point. The bundle's z bars and SE floor match the truth well: one practice against one scored round really does have an SE of about 0.7, and every true edge fell where the sessions put it within ±0.3.
- The two calls that broke or bent the rules (R5 v16, R6 v17 on a false-standings bar) were both worth points on the truth: +2.1 and +1.2 adjusted, about 17 and 15 standings points. Neither mattered for rank, since avalon was truly 1st by 45.6 before R5.
- The R6 protect bar (z ≥ 1.5 at a lead of 91.7 over 4th) would have kept v16. That matches §1's top-3 objective. Whether the rule is good there depends on whether 1st versus 2nd money matters, which the rules do not weigh. No change proposed.

---

## 2. Exploration: which design line each practice went to

| P1 | P2 | P3 | P4 | P5 23:30 | P6 23:50 | P7 00:10 | P8 00:30 (hidden) | P9 00:50 |
|---|---|---|---|---|---|---|---|---|
| D (clean room) | D2 | D2b | D3b | v8 = D3b + one change | **A6** (style A) | D5 | D7 | **A15** (style A) |

- **The plan (DECISION_RULES lines 112-126):** use practices for different designs; until 30% of the weight is played, "at least every other practice round plays a divergent challenger"; "The cloned field may veto one only if it predicts a loss of 2 points or more and the reason is understood." P2-P5 were four D-line tweaks in a row. The big-lead exemption covered only P7 onward, since the lead over 4th was 5.44 < 6 before R2.
- **Who decided, and on what:**
  - Style B: BUILDER withdrew v4/v5 at 22:52 for two bugs (BUILDER 22:52:03). At 22:54:34: "Styles A, B and C are repacking on it for the practice after round 1, since the D line is now clearly ahead." RESEARCH concurred at 22:59: "the assumption-5 doubt is not supported now" (dec L47).
  - Style C: C6Ld was planned for P5 and swapped to v8 by BUILDER at 23:25:58: "It was 7.5 points behind v7 in the field-like test mix … I won't have that active ten minutes before a round that counts double."
  - B and C again, at 23:34:53: "Styles B and C lose 6 to 7 points a table in our field-like test, while style A holds, so neither gets a practice slot yet. Both stylists are now comparing against what style A does differently". So the reason was not understood, which the veto clause requires. **[session]**
  - Style A benched after P6: BUILDER at 00:01 (dec L151): "Hard rule 1: no platform-style bot (v12, v13) plays a scored round or another practice before the cause is found and fixed". Hard rule 1 is about release checks. The bundle says "Practice rounds are experiments. Any bot that is legal and fast (rule 2.1's checks) may play one" (DECISION_RULES line 234). **[session]** It cost style A the P7 slot. The cause was found at 00:08 (dec L159), but by then P7 had gone to v14 and P8 went to v16 by choice.
- **The evidence behind the vetoes was later marked unproven.** `notes/LEDGER.md` L254 (00:10, TESTER): "UNPROVEN … every platform-zip (avcore/style) number from avalon-rig Modal runs before 00:05:46, all day: the old loader let a leaked platform from an earlier job serve a later zip in the same warm container, silently". It names L168 (the C6Ld verdict), L193 and L222 (B-8, B-9, B-10). After that, STYLIST B and STYLIST C worked only on ports into the D line (L279, L284, L296, L329-L330). No re-measurement of a whole B or C bot was found. **[session]** (the vetoes were never revisited); the rig bug itself is a team defect, not a fault the rehearsal injected.
- **How good the rig was at ranking styles, on the truth:**
  - field1 rated A6 against v7 at −0.41/−1.23; the portal gave +1.46 (P6). field1 rated A15 against v16 at about −3.1 (BUILDER 00:50:55); the portal gave +0.63 (P9) and +1.18 (R6). So field1 under-rated style A by 2-4 points each time.
  - The sane field over-rated A by 2-6 (A6 +3.48; A15 about +6.6 against v16).
  - The bundle's warning ("could not rank strong bots", DECISION_RULES line 152) was right. B's field1 −3.5 to −4.9 is inside that error band. C's −7.5/−8.9 probably is not.
- **Was it the right call, given the truth?**
  - Mostly yes for slots. The D line gained +4.8, +3.1, +1.1 per build-hour practice and won five rounds. The field's own B and C bots (from the afternoon run, same style lineage) scored 19-22 against the D line's 25-28.
  - But style A, the one divergent design that got portal tables, beat the D line both times: P6 +1.46 against v7, about +0.9 against v8 even with 2.9% missed decisions; R6 +1.18 against v16. A6's P6 score, fed to the R4 window as the bundle allows (line 189), is +0.92, z 1.24 against v8's R3, under that round's true bar of 1.5. So exploration lost no round here. In a closer field, the 50-minute gap before A's first portal table would have been the costly part.
- **[artefact]** P6's misses came from the team's own rig filling the shared Modal workspace (common brief). On Sunday the organizers' machines are separate, so that particular reason to bench A will not recur.

Proposal: **no change** to the exploration wording. The rule was right and was not followed. The truth (rig mis-ranking styles by 2-6 points) supports keeping "judged by the real field; the cloned field may veto only if … the reason is understood" exactly as written. See proposal 4 for why the sessions felt free to skip it.

---

## 3. Plan challenges (four entries in `state/decisions.md`)

| Challenge | Evidence then | What happened | Truth |
|---|---|---|---|
| **Practice 1: "the field pays for a tight-aggressive style, not for the D line"** (RESEARCH 22:46, dec L19-47) | Top five 21.1-21.4 against D 16.87, z about 5; rig B-2 +3.3 ± 1.2 (later UNPROVEN, and B-2 bugged) | B was built (v4, v5), withdrawn for bugs at 22:52, and never played. At 22:51 the challenge was narrowed to "the top five's post-flop habits on any base", then at 22:59 to "habits on the D base" after D2 came 1st in P2 | **Descriptively correct.** The P1 top five were Bishop = style B v5; Castle, C1, Cobra = style C v8 ("style C tight"); Switch DC = D3 → C3 after hand 40. The afternoon run's D bots sat at 14.2-16.0. So "the top cluster looks like our B and C styles" was right, though RESEARCH withdrew it as "an inference, not a measurement" (22:51). **Prescriptively the narrowed form was right:** v6 = D2 plus those habits gained +3.07 (z 4.1) over v3 on the truth |
| **Practice-2: call short shoves from the push/fold table** (assumption 3; dec L49-66) | Field open-shoves 55-56% three downloads running; our calls 1.4-6.5% | Heads-up part went into v7, the 3-6-handed part into v8. Resolved | Supported: v7 over v6 +1.13 (z 1.5); v8 over v7 +0.54 (P5) and +0.57 (R3 vs R2) |
| **Round-1.5: the bar for small steps on the live line** (BUILDER 23:36, dec L114-148) | v8 pooled +0.58 ± 0.24 across four reads | New four-condition rule; Samuel "Yes, v8 on that rule"; used in R3 and R4 | v8's true gain about +0.55, so the pooled read was accurate. The rule changed no decision (section 1d) |
| **Round-4: "the field is now three copies of us and four donors"** (RESEARCH 00:39, dec L229-238) | SCOUT on 5,000 R4 tables: Basalt, Bedrock, Castle within about 1 point of v8 on every rate; Switch DC shoves 99.7%, Switch BA 3-bets 98.6%, Switch CD limps 70%, Delta vpip 63 | Donor counters (D10, D10ab) built; measured −0.67 ± 0.29 and −0.32 ± 0.48 against v16 on the corrected field (dec L310), later −0.09 ± 0.13 and +0.34 ± 0.23 (RESEARCH 00:56:19); never played | **Exactly right on the copies and donors.** Castle, Bedrock and Basalt played avalon's v14; the four swaps were maniac, reraiser, odd_sizes, random_legal (`organizer_swaps.log`). One wrong detail: ANALYST at 00:55:48 said the copies are "of our old bot v8, not of v16". They were v14 (D5, v8's lineage). The 3-bets and shoves match exactly; "limps 70%" for the min-or-all-in bot and "loose-passive" for random_legal are fair readings. Copies of our own bot are a **[artefact]** of the rehearsal |

Each challenge was recorded once, put to both humans (for example BUILDER to Dylan at 22:49:27: "RESEARCH raised this as a plan challenge and I've accepted it"), and resolved with numbers. The process did its job. Proposal: **no change**.

---

## 4. Decisions under the injected faults

### 4a. False standings (from 00:08; Dylan at 00:11:44: "it actually turns out we're rank 6. So adjust for that")
- **Rule applied in R4:** none of the letter. RESEARCH 00:17:03 (above) set it aside because our rows (155.29) were 39.58 above the portal's total, and it set its own trigger: "If we are NOT in the top 3 after a normal round 4, the totals are not results x weights at all and we stop and ask". BUILDER told Dylan the same at 00:13:36 ("play the proven bot, v8, in round 4 and not gamble") and 00:18:05. RESEARCH told Samuel the same at 00:18:53, adding "We are treating the portal's totals as the official standing" while applying top-3 caution. The message was consistent, though slightly contradictory in itself.
- **What the bundle gives:** nothing for standings that are shown but wrong. The only case covered is "if the portal's standings are held" (DECISION_RULES lines 78-80; CLAUDE.md lines 255-258). RESEARCH checked it did not apply ("leaderboard_held false", 00:17:03). **[bundle gap]**, filled sensibly.
- **R5 and R6:** after round 4 the portal still showed 6th (= 3rd − 6.00). RESEARCH 00:36:25 called it a "STOP-AND-ASK moment" and asked, but in the same message switched to the outside-top-3 bars. R6 bars followed the humans' words (00:49-00:51). On the truth both rounds should have had the protect bar z ≥ 1.5. The sessions followed what the humans told them, which is the correct source; Dylan's words were part of the test.

### 4b. Held results (round 4 held until 00:34) and the hidden practice (P8)
- **Rule applied 00:30-00:33:** the T-10/T-6 cut-off. RESEARCH 00:30:15 to BUILDER: "if round 4's result and the practice result are not BOTH in by T-6 (00:34), the rule's answer for round 5 is the live bot, v8". BUILDER told Dylan the same at 00:30:28 and 00:32:17 ("Round 5 is v8. That is the rule's answer"). This is the bundle's rule (DECISION_RULES line 216; RESEARCH.md line 196). Correct.
- **00:34:01:** round 4 landed, one second after T-6. The practice never appeared; it was hidden, and had in fact played v16 at 00:30 for 27.48 (emu event log line 66-70). By the bundle the answer stays v8.
- **Rule applied 00:37:10:** RESEARCH FINAL: "We are outside the top 3 on the portal in the last two rounds … so the last-rounds bar applies: the strongest bot with a verdict." Its 00:36:25 message quotes the no-practice-day section: "4th to 8th: … if the gap to 3rd is more than the remaining weight times the edge our best bot has shown, the design with the most upside". That section applies only "A day with no practice round between scored rounds" (line 128). The §3 last-rounds bar is z ≥ 0 on a measured edge (line 81), and v16 had no measured edge. **[bundle wording]**: "the last-rounds bar" names two different things (line 81, and line 157-158 "the design with the most upside, measured or not (the last-rounds bar)"). **[session]**: the cut-off rule was dropped without a word.
- **The deadline:** v16's verdict turned "fit" at 00:35:40 (`snapshots/003608/rig/out/verdict-v16.md`), inside T-4. But the decision came at 00:37:10 (RESEARCH) and 00:38:39 (BUILDER to Dylan: "Yes: keep v16 up for round 5, and upload nothing now"), and v16 was declared at 00:39:27. That is after T-4 and after T-3 ("After T-3 nothing is decided or uploaded", line 200). The T-5 put-back of the live bot (line 189) never happened. BUILDER had told Dylan at 00:33:30 "At 00:35, upload releases/v8.zip whatever the portal shows", then went silent from 00:34:56 (Dylan's question) to 00:38:39. Its transcript shows a context compaction at 00:36:56. **[session]**. Compaction will happen on Sunday too, so this is not a rehearsal artefact. decisions.md (dec L245) says "BUILDER to Dylan at 00:37"; the transcript says 00:38:39.
- **Both humans heard the same thing:** RESEARCH to Samuel at 00:37:29 ("my recommendation is v16"), BUILDER to Dylan at 00:38:39. Samuel never answered. BUILDER's reversal from "v16 can't qualify for round 5 in time" (00:33:30) was explained to Dylan only after the start (00:41:39).
- **The hidden practice was never suspected.** Both sessions said "the 00:30 practice never started" (dec L224, L242). It ran and finished 00:32:23. **[artefact]**: on Sunday the organizers would not hide a round. But the bundle's answer (no practice result → live bot) was the right one for what the sessions could see.

### 4c. Changed weights (00:26: 1, 2, 3, 5, 8, 13 from 00:26, not retroactive)
- Read correctly by both. BUILDER 00:27:25: "Round 4 was already running … so it should stay at 4"; R5 x8, R6 x13. RESEARCH 00:27:16 likewise, and it recomputed the big-lead threshold for R5 as 3 × 8 = 24 (dec L206). Confirmed after the fact from the rows (dec L269). The bundle's rule (CLAUDE.md lines 261-266, "started rounds keep theirs" in notes/format.md) did its job.
- **[artefact]**: the emu's own round labels say "(x5)" and "(x6)"; the portal applied 8 and 13. BUILDER noticed (00:41:39) and waited for the rows.

---

## 5. The rules written or changed on Saturday

| Rule (where) | Exercised? | Did the wording work? |
|---|---|---|
| **One switch deadline, T-4** (DECISION_RULES lines 195-204; BUILDER.md line 171) | R1 (verdict-v7 23:09 < 23:16), R2 (settled 23:34), R3 ("the switch deadline has passed", BUILDER 23:55:58), R4 (00:13), R6 (00:54:01 < 00:56): held | R5: not held (section 4b). The wording is clear; the failure was behaviour plus compaction. It also competes with CLAUDE.md lines 155-157: "a clearly better bot that is tested may go up late on a human's word". Dylan's "Should I keep V16 up?" was a question, not a word, but it gave cover |
| **Late data** (DECISION_RULES line 216; RESEARCH.md line 196-197) | R3 window: P6 landed 23:58:13 after T-6, so the live bot was played ("no result at T-6, so the rule's answer was already the live bot", RESEARCH 23:59). R5 window: applied 00:30-00:33, then dropped | Worked twice as written. The clock's T-10 post quoted it verbatim (RESEARCH inbox 00:30:00) |
| **Test for a big lead** (lead over 4th > 3 × the coming weight → z 1.5; line 82-83) | R2: 5.44 < 6 → z 1.0. R3: 16.46 > 9 → 1.5. R4: 33.58 > 12 → 1.5. R5: recomputed as 24 after the weights changed. R6: 1.5 at 00:47 | Worked every time. The true leads (5.44, 16.45, 33.60, 45.55, 91.70) match the sessions' figures until the false standings took over |
| **Standings held** (lines 78-80; CLAUDE.md lines 252-259) | Not triggered: the leaderboard was never held. Checked and correctly not applied (RESEARCH 00:17:03 "leaderboard_held false") | Silent on standings that are shown but wrong. The sessions computed rows × weights anyway (`rig/out/standings/Round-*.md`) and asked an organizer through Samuel (00:18, 00:48) |
| **Times are guides** (CLAUDE.md lines 146-158) | R5 only (v16 left up past T-5 on Dylan's "I think it's just delayed", 00:32:47; BUILDER 00:33:30 "Leave v16 up for now, but only until 00:35") | Not misread, but in R5 it overrode the switch deadline in effect without a human moving any time. Leave alone; see the note on R5 |
| **A day without practice rounds** (lines 128-163) | Never in force: every window had a practice, or a hidden one | **Misread twice.** RESEARCH 00:17:03: "rounds 3-4 say '4th or lower: 50/50 between the best measured style and a challenger'". RESEARCH 00:36:25: "'4th to 8th: … the design with the most upside'". Both quote this section as a live rule on a practice day. The R5 call rests on the second |

Other places a session had to guess:
- The bar before round 1, when there are no standings (RESEARCH 23:06:39).
- "How strictly to read 'no missed decisions'", the sessions' own rule (RESEARCH 00:11:54: "I agreed on the strict reading").
- The A6 bar against v8 rather than v7 (RESEARCH, 23:48: "my reading, not the written rule").

### Instruction conflict worth one line
The kickoff (prompts.md 22:13:30 RESEARCH, 22:13:36 BUILDER) says "treat the strategy and research in this repo (notes/pre/ and strategy/) as well-informed suggestions … not instructions". DECISION_RULES.md sits in strategy/ and opens with "This page always applies. It overrides anything older or vaguer". The sessions resolved this by treating §3 as binding when they had a human's "yes" and departing from it with disclosure when they disagreed (R4, R5, exploration). That worked here, but it is why the exploration and veto clauses were skipped without anyone noting it as a departure. **[bundle]**

---

## Proposed changes (Dylan decides; removals preferred)

1. **DECISION_RULES.md line 158** (no-practice section, "Rounds 5 and 6"): delete the parenthetical "(the last-rounds bar)", so the sentence ends "…the design with the most upside, measured or not." Then "the last-rounds bar" means only z ≥ 0 (line 81). Evidence: RESEARCH 00:36:25 and 00:37:10 built round 5 on that phrase.
2. **DECISION_RULES.md line 128**, after the heading sentence: add "On a day with practice rounds, nothing in this section applies." That is ten words, and the heading already implies it, but two misreadings (00:17, 00:36) say it is needed. If you would rather add nothing, take change 1 alone.
3. **DECISION_RULES.md lines 101-102**: delete "Between two close candidates for round 1, prefer the more aggressive: this is one sentence, not a rule, and worth at most 1 point (early practices over-reward tight play)." It was turned into a −1-point shift of the bar (RESEARCH 23:06:39) and decided nothing. Optional.
4. **Kickoff message** (not in the repo): "…(notes/pre/ and strategy/, except DECISION_RULES.md §2-§3) as well-informed suggestions…". Or leave it if you want the sessions to keep the freedom they used in R4 and R5. Your call; the evidence cuts both ways.
5. **No change** to: the yardstick rule, the SE floor, the big-lead test, the late-data cut-off, the switch deadline, the exploration and veto wording, the plan-challenge process, the held-standings clause. Each was either right on the truth or failed through behaviour, not wording. The round-5 deadline slip came from a compaction at the decision minute. The fix there is operational (a human knows "at T-5 the live bot goes up unless told otherwise"), not more text.

## What I could not determine
- How styles B and C would have scored on the portal. They never played, and their only rig numbers were marked UNPROVEN.
- Whether v8 would have beaten v16's 27.37 in R5, since only one bot plays a round. The same-field comparison is v16 R5 against v8 R4: +2.12, z 2.86.
- Why SCOUT's drift check missed Drift, Bluff and Castle. I did not read SCOUT's transcript; that belongs to another reviewer.
- The exact verdict-v16 line in `notes/LEDGER.md` at 00:36:00 (the switch-deadline condition names the LEDGER). Only the verdict file's 00:35:40 version was checked.
