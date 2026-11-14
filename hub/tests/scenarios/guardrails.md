# Guardrails audit: what steers the agents down a fixed path (Finals, 15 Nov)

Read in full: hub/roster.py, the hub.py playbook block (BUILD, WINDOW, DISPATCH, REMINDERS, CHECKPOINTS, ROUTES, FANOUT, GUARD, situation(), HUMAN_STEPS, post_default_note), DECISION_RULES, START_HERE, FIRST_PROMPT, TWIST_NOTES, FINGERPRINTING, FINALS_PLAYBOOK, plus SUNDAY.md and AGENTS.md (stale text there gets read too).
Note: hub agents run with `setting_sources=[]` (hub.py:1817), so CLAUDE.md/AGENTS.md are NOT auto-loaded. An agent still sees them if it opens them.

## Verdict in one paragraph
The hard safety rules are tight and correct. The trouble is the *strategy* scaffolding around them. Exploration is pinned to a regional-derived plan (A/B/C styles in practices 1-3, then incremental "up to three changes" fixes on the live bot). The one agent meant to explore, d-challenger, **gets no task until minute 40** (DISPATCH has no b0 entry for it). Its per-window brief is **physically impossible as worded**: "revise from this round's data" at T-13, with release due at T-12. And it may rewrite only when "outside the top 6". **Nobody owns "has the field changed / is our plan still right?"** No path tells a worker it may challenge the plan. The T-8 switch bar is strict, and it compares a challenger's practice score with the live bot's *scored* score, which are different fields, so switches are both rare and noisy. Net effect: the structure reproduces the regional failure mode (locked style, incremental tweaks, field trends unowned). It is less likely than at the regional to ship bad bots, which the cut-offs handle well.

---

## 1. Prescriptive instructions, classified
(a) justified hard safety rule · (b) prior presented as a rule · (c) path-locking, no escape hatch · (d) fine

**Build-hour schedule**
1. hub.py:2558 BUILD "Practice round 1 plays style A (a different style each practice round)." Also 2559-2560 (B at 30, C at 40), 2561 "Practice round 4 re-plays the leader", DISPATCH b20/b30/b40 "Style A … for practice round 1; B next", "Style B for practice 2", "Style C for practice 3". START_HERE.md:68, 185 and FIRST_PROMPT.md:282 "I'll rotate which one is active". **(c).** The clock hands these out as CRITICAL. DECISION_RULES.md:80 ("Pick the most informative candidate") is the only escape hatch, and the clock overrides it. It also contradicts FINALS_PLAYBOOK.md:124-125: "put the style we trust least" in practice 1.
2. hub.py:2589/2591 DISPATCH b20 "so style B in practice 2 uses them [ranking+ICM]", and b30 "so style C in practice 3 is the first real-field test of the full tables"; CHECKPOINTS b40 likewise. **(c), and it biases the result.** A plays with no today-tables, B with some, C with all of them. The P1/P2/P3 fields also mature from minimal bots (everyone uploads at minute 10) to real ones, and the sizes grow (1,000 → 2,500 → 10,000 iterations). So "best real-field scorer" (2561, b50) measures *when* a style played as much as *what* it is.
3. roster.py:335-337 d-builder "You keep the three styles … A wide pressure, B shove-heavy, C tight", and FIRST_PROMPT.md:263-272. **(b).** These are corners of a cycle simulated on the Bay Area variant only (DECISION_RULES.md:140-142 says so). No agent is asked whether today's variant makes a different axis dominant: twist-centric play, or postflop vs preflop. TWIST_NOTES says the twist was worth ~8 pts/table in one mock, more than any style choice.
4. d-challenger has no b0/b10/b20/b30 task. Its first task is b40 (hub.py:2596), although BUILD_NOTES creates a "Challenger" tile at minute 0. **(c) by omission:** for 40 minutes, exploration is assigned to nobody.

**Per-window loop**
5. DECISION_RULES.md:46 "up to **three independent changes**, each in a different situation". Also roster.py:200 LENSES.leaks "(up to three, in different situations)", roster.py:251, 327, 338, hub.py:2569, 2602, 2605, 2607, START_HERE.md:75. **(b).** The count is arbitrary. The real constraints are independence, a setting and a branch count. It frames each window as "pick ≤3 leaks", which is the regional's incremental pattern.
6. DECISION_RULES.md:51-52 says each live change needs "z ≥ 1 … 1.5 SE in the top 3". **(b).** FINALS_PLAYBOOK.md:195-196 says thresholds are for all-or-nothing choices only. A change behind a setting is not all-or-nothing.
7. roster.py:250-254 s-data ROUNDS: "The defaults check first, then our leaks (Part 2) and up to three independent changes". DISPATCH T13 (hub.py:2602) says the same. **(c).** The Analyst's whole per-round mandate is *our* leaks. Part 2 Q3 ("what the best teams do that we don't") and Q4 (rates that correlate with points) are not in any LENS (roster.py:198-205). So "what is winning now" has no owner.
8. roster.py:347-348 and DECISION_RULES.md:76-78: "Default design: the best response to the field's MEASURED mix of styles". **(b), and reasonable.** But it is the *only* design direction given, and the measured mix lags by 1-2 rounds (see 10).
9. roster.py:349 / DECISION_RULES.md:84 / hub.py:2606: "Outside the top 6 after 15% of the total weight: a fresh rewrite." **(c).** 4th-6th never triggers a rewrite, yet 4th pays nothing. 15% of the weight means after round 3 under both linear and Boston weights, by which point ~70% of the points remain and a rewrite has had no time to mature. There is no trigger based on field change, only on standings.
10. hub.py:2606 DISPATCH T13 d-challenger: "revise it from this round's data … ready for the T-12 upload". **(c), impossible.** Data lands at T-13 and the challenger must be released by T-12 (GUARD hub.py:3172, WINDOW T-12). In practice the challenger always uses data ≥1 window old, and a "fresh rewrite" can never be built inside one window.
11. DECISION_RULES.md:37-41, the T-8 bar. Outside the top 3, 1.0 SE (0.5 in the last two rounds). In the top 3, 1.5 SE. Measured as the "practice-round score minus the live bot's most recent comparable score". **(b), and mis-specified.** See §3.4.
12. roster.py:286 s-scout: "Never put team profiles into default play: counters only behind CTR_<team>." **(d)** for single teams. But if the *whole field* moves, nobody is told to move default play (field_priors only feed the seat priors).
13. DECISION_RULES.md:136-139, FIRST_PROMPT.md:288-291, roster.py:336-337 (style C's definition), hub.py:2584: "fold to 3-bets … no more than break-even, usually 65-75%". **(b), and stated as a rule inside the d-builder role and DISPATCH.** FINALS_PLAYBOOK.md:33 shows the regional *winner* folded 81-87% to 3-bets. The 65-75% figure is a prior that the winner itself broke.
14. FIRST_PROMPT.md:157-158 "Raise or fold before the flop; limping and flat-calling raises lost money". FIRST_PROMPT.md:274-281: shared defaults "no open-limping … a style that breaks one by accident fails the check". **(b), with only a weak escape hatch** ("deliberately overrides one and says so in VERSIONS.md"). This is exactly the user's example: if the Finals field turns limp-shove, or the variant makes limping +EV, the check and s-data's "defaults check first" (roster.py:250) push against it.
15. DECISION_RULES.md:131-134 "Never use a weight above 10 for a field prior", and FINGERPRINTING's 0.6 / 50% / 55% / δ_max gates. **(b), low impact, (d) in practice.**
16. roster.py:353-354 "any adaptive rule ships ON in the challenger". **(b).** Confounds what the challenger's practice score is measuring.
17. roster.py:177-179: only d-platform commits to main; d-platform does every release. **(a).**
18. DECISION_RULES §2, rules 1-4 (legal and fast, tested upload, live bot back at T-9, rules card right, no pre-written code). **(a), keep exactly.** The cut-offs (DECISION_RULES.md:58-74, GUARD) are **(a)** too: they remove the incentive to rush.
19. Places agents are told to wait. KICKOFF (roster.py:188-192): the Chats "Until the clock starts, answer … and wait". Workers are not autostarted (hub.py:4203). FIRST_PROMPT Part 0 (pre-event research, "the Boston winner researched 1.5 h") is **assigned to nobody** in the hub and is missing from SUNDAY.md. **(c) by omission.** DISPATCH T13 s-data "not before; wait for it" is **(d)**.

---

## 2. Contradictions and stale references

**Who does what**
- FIRST_PROMPT.md:257-259: "You own the platform and style A; spawn two subagents for B and C". The hub splits this between d-platform (platform) and d-builder (A/B/C).
- What challenger 1 is: FIRST_PROMPT.md:283-285 "the next best [style] stays alive as the challenger … the third is dropped"; FINALS_PLAYBOOK.md:139-141 "the best of the styles that didn't win the build"; hub.py:2596 "best response to that mix". These are three definitions.
- FIRST_PROMPT Part 5 Manager (538-551) "start … six to ten candidate builders, two bug hunters…", and KICKOFF tells s-overview to read Part 5. But roster.py:230 says the Chat does no deep work (at most 2 short subagents). FINALS_PLAYBOOK.md:161-171 describes a 20-agent model that no longer exists.
- FINALS_PLAYBOOK.md:83-86: Samuel owns "the clock … the manager agent … the live dashboard", which contradicts START_HERE §5.
- d-builder "tell d-overview which should play which practice round" (roster.py:341-342), while the clock fixes A/B/C. SUNDAY.md:85 says a "Which bot?" note asks which style plays at 20/30/40, but no DISPATCH task creates one.

**Decisions in the Chat vs greenlight on the board**
- hub.py:2723-2724 HUMAN_STEPS "8": "open the Use-which-bot note on the board and greenlight or reject".
- hub.py:3334 default note "Greenlight to confirm."
- SUNDAY.md:84-87, 108-110 ("Open the 'Which bot?' note", "Upload the greenlit bot", "Post ideas with + New idea"; ideas were removed in b0ece36).
- AGENTS.md:10-11 "one Overseer per person … a Decisions board where humans greenlight".

**Default when nobody answers**
- DECISION_RULES.md:32 "the rule's answer plays, not 'no change'". SUNDAY.md:109 says "T-5: No decision means the live bot plays". hub.py:3332 posts "Default: the live bot … keeps playing", and the DECISION_RULES.md:70 cut-off table says "with the live bot as default".

**Removed agents and 'notes'**
- roster.py:138 "Skeptic recomputes"; hub.py:1695 "or the skeptic decides" (no skeptic exists, so disagreements have no resolver).
- roster.py:89 "every agent and note that used it"; team_directory (roster.py:381) "the ledger, the notes and the repo"; hub.py:1804 "Every board note's full conversation is mirrored".
- "Overseer" is in agent-facing strings (hub.py:2178 "Only your Overseer talks to humans", 1097, situation() "Message the other Overseer").
- DECISION_RULES.md:68 has the typo "the leadeer".
- AGENTS.md:56 "Gate every release with `reviewer/gate.sh`". gate.sh:11/34 **blocks PFR outside 17-27%**, the band FINALS_PLAYBOOK.md:36-39 says "would have blocked the winner". The danger is that an agent finds and follows it.

**Numbers that disagree**
- Fold to 3-bet: "strong bots … 63-68%" (DECISION_RULES.md:138), "strong bots folded 70-77%" (FIRST_PROMPT.md:290), "top teams … 58%" (START_HERE.md:42), winner 81-87% (PLAYBOOK.md:33).
- Field rank correlation: 0.84-0.91 (PLAYBOOK.md:41, EVIDENCE_TABLE) vs 0.76-0.83 (FIRST_PROMPT.md:592).
- Recognition at 20 hands: 73% (START_HERE.md:45, FINGERPRINTING) vs 67% with 73% at 40 (FIRST_PROMPT.md:608).
- Switch bar inside the top 3: 1.5 SE (rules) vs "two" (PLAYBOOK.md:106). Live-bot changes per window: 3 (rules) vs "1; 2 only if unrelated" (PLAYBOOK.md:149).
- Rewrite trigger: top 6 after 15% (rules) vs "outside the top 3 after two rounds" (PLAYBOOK.md:142).
- Counter gate: lagged recall ≥50% (roster.py:282) vs ≥55% (FINGERPRINTING.md:47, 58).
- AGENTS.md:66 "1,000-table samples swing by about ±2 points" vs SE 0.65.
- FINALS_PLAYBOOK.md:195-196 (no thresholds except all-or-nothing) vs per-change z bars.

---

## 3. Agent dynamics in the lean hub

**3.1 Where new strategy comes from.** In practice it comes from three places: (i) d-builder's A/B/C, which are fixed in advance; (ii) s-data's ≤3 leaks of *our* bot plus s-scout's per-team counters, which are incremental by construction; (iii) d-challenger, which starts at minute 40, is anchored to a "default design", is one window stale, and is only allowed a rewrite outside the top 6. No prompt asks any agent to start from the kit and today's variant and design what it thinks is best, ignoring the regional. Part 0's pre-event research would have been the natural place, and it is unassigned.

**3.2 Who notices that the field changed.** Nobody, as a job. s-scout measures *per-team* drift to switch counters off (FINGERPRINTING §2). s-data refits table *columns* from field rates (REMINDERS T13). Neither is asked for a field-level trend: "the top 8 now limp-shove at ≤15bb", "3-bet rates doubled since round 2", "the top 5 teams cluster in style X and we're not in it". Neither is asked to test the plan's assumptions against that trend. The data needed (field_priors.json per round, per-team profiles) is already produced; the question is just never asked.

**3.3 Who may say "abandon the plan", and how it reaches humans.** PROTOCOL gives workers only one channel: report to your Chat. Clock tasks arrive as "Your task now (CRITICAL)" with "workers start on it at once" (roster.py:43-44). Nothing gives a worker permission, let alone an obligation, to say "this task is the wrong task". The Chats "own the plan" (roster.py:291), but their turns are filled with clock relays, situation briefs, checkpoint pressure ("if you're behind … put everyone on the critical path"), reminders and human messages. The only cross-Chat step-back is a 3-line T-20 sync (hub.py:2630). Humans see tiles and the decisions the Chat asks about, and "which bot?" is the only standing decision. A strategic pivot (switch base style, build a rewrite now) has no decision kind, no owner and no deadline, so it would surface only if a human happens to ask.

**3.4 Incentives created by the T-8 bar.**
- *The comparison is confounded.* After the build hour, the live bot never plays a practice round, so the "comparable score" is its **scored** result. That came from a different field: in practice rounds most of the 19 other teams are testing *their* challengers (75-90% change bots). That bias has unknown sign and is plausibly ±0.5 pts/table, the same size as the effects we want to detect.
- *Power is low.* SE(diff) ≈ √(0.65² + 0.13²) ≈ 0.66. For a challenger that is truly +0.5 pts/table better, P(clears 1.0 SE) ≈ 41% and P(clears 1.5 SE) ≈ 23%. For a truly equal challenger, P(false switch) is 16% / 7%. So with a lead, real improvements are mostly rejected. Outside the top 3, the bar works against the stated posture, because variance is good when 4th pays nothing.
- *Evidence never pools.* The challenger is "revised" every window, so each 1,000-iteration practice starts from zero.
- *Status quo.* The rule's default is "live + ≤3 tested changes". The auto-posted note headline is "live bot keeps playing". This is the regional's incremental pattern again.
- *What agents learn from this:* d-challenger learns its bot rarely plays. s-data/d-builder learn the live-bot fix path is where things ship. Both push toward small, safe tweaks.

**3.5 Is there a skeptic or a from-scratch mechanism?** Neither exists. s-tester verifies *numbers*, not *strategy*. The "skeptic" in hub.py:1695 no longer exists, so ledger disagreements have no tie-breaker.

**3.6 Is the build hour over-scripted?** Yes. Practices 1-3 are forced to A/B/C, the table rollout is staggered so later styles look better, practice 4 is forced to "re-play the leader", and the challenger lane sits idle. Meanwhile every finalist knows wide 3-betting won (START_HERE.md:41). Style A is the consensus trade, and the cycle says limp-or-shove punishes it. The plan knows this but still assigns A to the slot with the least information (practice 1, 1,000 iterations, a field of minimal bots).

**3.7 What works and should be kept.** Cut-offs that cut scope, not care. The decide-by-default rule. The "evidence below A is a reason to try where cheap" principle. The "unverified is not wrong" principle. The tested-upload hard rules. The direct clock→worker dispatch. These stop rushing, and none of the proposals below loosens them.

---

## 4. Proposals (by expected impact on a top-3 finish)

### P1. A from-scratch lane from minute 0 (d-challenger)
**Why:** this is the only structural answer to "what would we have found if we had started from scratch". It turns 40 idle minutes into a mature alternative. Rewrites need lead time, which one window can never give (see §1.10).
- Add DISPATCH `b0` for d-challenger: *"Clean-room design D. Read only the kit, RULES.md, the rules card, TWIST_NOTES §0-2 and s-data's tables as they land. Do NOT read the A/B/C definitions or FIRST_PROMPT's regional strategy section. By minute 12, write candidates/D/DESIGN.md: what today's variant rewards, the 2-3 strategic axes that matter most (preflop width, twist use, postflop, short-stack), and the design you'd build if nobody had told you anything. Build it on the platform as a style. It is eligible for any practice slot once it passes rule 2.1. report_progress('Style D (clean-room)')."*
- Rewrite roster.py:346-349: *"Its job is to find what this field pays. Keep a standing alternative design maturing across windows: the clean-room line D, a best response to the measured field mix, or whatever the latest field-trend check (P2) points to. Choose, and say why in one line. A fresh rewrite is a normal option at any standing, not an emergency. Build the next challenger from the data you have; you cannot wait for the T-13 download, so target the window after."*
- Fix hub.py:2606 to match: *"Challenger for the NEXT window's practice: build from the newest data you have; release by T-12 only what is already tested; otherwise the most informative released bot plays."*
- **Safety:** it releases only through d-platform, after s-tester's correctness check and the upload test (rule 2.1). It builds on the platform, so there is no duplicated legality code. "Clean-room" here means design independence. All code is still written on the day.

### P2. A per-round field-trend and plan-assumption check, with power to escalate
**Why:** this is the missing owner for "unexpected trends across competitors".
- s-scout, ROUTES fp_ready plus the role: *"Every download, write analysis/<stage>/field_trend.md. (1) Field-level rates by round (open, limp, 3-bet, fold to 3-bet, open-shove by depth, fold to a bet by street, twist use), each with Δ vs last round in SE. (2) The style cluster of the top 5 teams and how it moved. (3) Check the PLAN ASSUMPTIONS list (below) against the data. If any assumption is broken by ≥2 SE, or the top-5 cluster shifted, send `task` 'PLAN CHALLENGE <stage>: <assumption>, <evidence>, <what I'd do instead>' to both Chats and to d-challenger."*
- Put the PLAN ASSUMPTIONS in DECISION_RULES §5 as a checklist: field folds to 3-bets ~63-68%; open-limping loses; flat-calling at 10bb+ loses; field open-shoves 35-50% at ≤10bb; our base style is the best response to the measured mix; the twist value is what s-data's table says.
- Add a LENS `"winners"` in roster.py: *"What the top 5 teams this round do differently from us (Part 2 Q3-Q4): the biggest pays-for-them gaps, with n. Do not filter by our current style."* Make it one of the three lens subagents every round, rotating which other lens drops.
- PROTOCOL addition: *"A PLAN CHALLENGE is answered within your next turn. Restate it to your human in plain words: what changed, what it means, what we'd do differently, and what it would cost. If it means changing the base style or rewriting, create `propose(kind="question")` with the default 'd-challenger takes it as the next challenger'."*
- **Safety:** this is analysis only. It changes what gets *built and tested*, and never bypasses testing.

### P3. Permission to challenge the plan (COMMON_RULES, every agent)
Add to roster.py COMMON_RULES:
> *"The plan (the clock's tasks, the styles, the counts in How we decide) is a default, not a mandate. If evidence says a task is the wrong thing to do (the field moved, a style is dominated, the variant makes another approach better), tell your Chat in one message with the evidence and what you'd do instead, then carry on with the task unless redirected. Being right about the plan matters more than finishing the task as written. Never use this to skip a hard rule or a test."*

Also edit roster.py:43-44 from "workers start on it at once" to *"workers start on it at once, or say why something else is better"*.
**Why:** this costs nothing. It stops clock tasks from overriding judgment, and keeps all hard rules intact.

### P4. De-script the build hour and remove the comparison bias
- BUILD 2558-2561 →
  - *"(20) Practice 1 plays the first legal, upload-tested style (any)."*
  - *"(30, 40) d-overview picks the most informative candidate (A, B, C, D or other) by T-2 of each practice; every style ships with the newest shared tables at upload time."*
  - *"(50) Practice 4: the leader, or the closest untested contender if the leader is already clear."*
- Remove "so style B in practice 2 uses them" and "so style C … the first real-field test of the full tables" from DISPATCH b20/b30. Replace with: *"build each table into the platform as it lands; every style picks it up at its next upload."*
- b40 s-tester and b50 s-data: *"Rank the styles adjusting for confounds: which tables each had, practice size, and field maturity. Add replay tests of every style on the P2 and P3 downloads (same field, same deals). State which comparison carries the decision."*
- d-builder role: *"Styles A/B/C are starting corners; replace any of them the moment the twist analysis or practice data suggests a better axis."*
- **Safety:** unchanged. Each practice still plays only a rule-2.1 bot.

### P5. Make the T-8 bar measure the right thing (DECISION_RULES §3)
Replace lines 35-41 with:
> *"Measure the challenger's edge as a difference-in-differences: (challenger's practice score − the practice scores of yardstick teams) − (live bot's last scored score − the same teams' scored scores). Yardstick teams are those s-scout's drift check shows did NOT change bot between those two rounds; if fewer than 4 exist, use field-median-normalised scores and say so. Pool the challenger's practice rounds when its core is unchanged (only added settings). You may add the replay-test difference on the newest download at half weight.*
> *Play the challenger if it passed rule 2.1 and the pooled z is: outside the top 3, ≥ 0.5 (≥ 0 in the last two rounds); in the top 3, ≥ 1.0 (≥ 1.5 only if our lead over 4th exceeds one round's typical swing)."*

**Why:** the current bar compares two different fields. On top of that its power is low (41%/23% for a +0.5 bot). Outside the top 3 the payoff rewards variance, and the regional showed caution cost the most. **Safety:** rule 2.1 still gates every bot, and the decision is still made at T-8 by the humans. No step is shortened.

### P6. Downgrade path-locking priors to priors
- DECISION_RULES.md:46 → *"Ship every independent change that clears the bar, each behind its own setting with a branch count (three is typical, not a cap)."* Remove "up to three" from roster.py:200/251/327/338 and hub.py:2569/2602/2605/2607.
- roster.py:336-337, hub.py:2584 (C's definition): drop "usually 65-75%" from role text. Keep it in DECISION_RULES §5 only, and add *"(the regional winner folded 81-87%; break-even for today's sizes decides)"*.
- FIRST_PROMPT.md:274-281 → *"…the check run counts each and reports it; a style that breaks one must say whether it is intended. If this field or variant pays for limping or flat-calling (s-scout's field trend, s-data's winners lens), that is a finding, not a failure."* And roster.py:250 → *"the defaults check (as a report, not a gate)"*.
- DECISION_RULES.md:84 → *"Not in the top 3 once 15% of the weight has played, or a PLAN CHALLENGE stands: the challenger slot carries the alternative-design line (P1), not a revision."*
- **Safety:** none of these touch §2.

### P7. Assign Part 0 (pre-event research)
Change KICKOFF from "answer and wait" to *"start Part 0 now"*:
- s-data: topic A, Pittsburgh plus twist valuation shortcuts.
- d-challenger: *"what will the Finals field do, given every finalist knows the three regionals? Which style is crowded, and what punishes it?"*
- s-tester/s-scout: topics C/D, notes only.

All outputs go to notes, with no bot code (allowed: "prompts and notes may be brought"). This needs a "pre-event" mode that starts the workers before b0; if that's not feasible, a human can type the task into each worker the morning of. **Why:** the Boston winner's 1.5 h of research. A field-anticipation memo is the cheapest defence against an unexpected meta.

### P8. Clean up contradictions (low cost, avoids confused agents)
- **Default-note wording:** fix the hub.py:2723-2724 HUMAN_STEPS text ("answer in your Chat") and hub.py:3332-3334 ("Default: the rule's answer (<live/challenger>)"; drop "Greenlight"). Align SUNDAY.md:109 and DECISION_RULES.md:70 with "the rule's answer plays".
- **Removed agents and notes:** delete "Skeptic" (roster.py:138, hub.py:1695: "re-run; s-tester decides"). Replace "notes" with "files/tiles" (roster.py:89, 381). Replace "Overseer" with "Chat" in agent-facing strings.
- **FIRST_PROMPT Part 1 (257-260, 282-286):** "d-platform owns the platform; d-builder the styles; the challenger is d-challenger's line".
- **FIRST_PROMPT Part 5 Manager:** mark it as "manual fallback only". Change KICKOFF to read DECISION_RULES §3 instead.
- **FINALS_PLAYBOOK §3-4:** add a banner "superseded by DECISION_RULES/START_HERE for counts, bars, roles".
- **AGENTS.md:** drop "Gate every release with reviewer/gate.sh" (the PFR band) and describe the lean hub.
- **Numbers:** reconcile the disagreeing ones listed in §2 (fold-to-3-bet, rank correlation, recognition, counter gate).

### Not recommended
- **A 5th "skeptic" agent per laptop.** P1-P3 give the same function with no new coordination load, and the reinforcement study found extra reminders can hurt.
- **Loosening any §2 hard rule or the cut-offs.** They are what prevent the "rushing / bad bots" failure, and every proposal above keeps them.
