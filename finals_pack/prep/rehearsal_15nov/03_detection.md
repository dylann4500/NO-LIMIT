# 03 Detection: what the team saw of the field and the portal, how fast, and how right

**Summary (five lines)**
1. Every opponent change that showed up as a clear change in behaviour was reported within 1 to 3 minutes of the data landing, and described correctly: Bishop R2, Ace R3, Arrow P7, the four hostile bots, the copies of our own bot, and every later swap (Bedrock, Delta, Cobra, Basalt).
2. Of the 14 scheduled version steps, 7 were reported. Five of the 7 misses were version steps the team's own rate tables cannot tell apart. Ace at R1 could have been caught: its flop raise rate fell from 15.5% to 4.0%, `fp_train` flagged it, and SCOUT overruled the flag.
3. The portal faults were handled unevenly. The weights change was seen in 12 s. The false standings were taken apart correctly by SCOUT 10 min after they were injected. The held round 4 and the hidden 00:30 practice were never recognised: both were blamed on the team's own Modal use, which led to a Modal hold that stopped the team's own testing. The portal restart left no trace.
4. Fingerprinting was built and its recognition accuracy was measured every round (41 to 47% at 20 hands, against a bar of 55%). It was never switched on in a bot. The only counter that shipped (Min Raiser) works from an in-table count and needs no recognition. Of the three teams that switch design within a table, Switch BA was found and DC was suspected once. Nobody found the hand at which they switch.
5. Data reached the decisions quickly. The watcher's card was ready 13 to 19 s after landing, SCOUT's first line came 0.5 to 4 min after, ANALYST's 1 to 7 min after, and each FINAL bot pick 10 s to 3 min after its practice landed. Most of the leaks the analysis found were fixed in a later release, but v17 (round 6) dropped two of those fixes and the counters proposed after round 4 never played.

Method. "First visible" means the time the portal watcher posted "Round X finished" (TIMELINE.md `(builder) [portal]` lines), which was 2 to 18 s after the organizer finished the round, except for round 4, which was held. Whether a change was visible in behaviour is judged from the team's own per-team rates in `/Users/dylan/Documents/GitHub/avalon-nolimit/analysis/<stage>/field_trend.json` and from the automatic flags in `analysis/<stage>/fp/drift.json`. Neither shows any hand data. The truth comes from `emu/fixed_bots_by_round.json`, section 11 of `NOTES_FINALS_REHEARSAL.md`, `analysis/organizer_faults.log` and `analysis/organizer_swaps.log`. The team's stage names map as follows: Round-1.5 = P5 (23:30), Round-2.5 = P6 (23:50), Round-3.5 = P7 (00:10), Round-5.5 = P9 (00:50). There is no Round-4.5, because P8 was hidden.

Three facts about the ground truth that the brief does not state:
- **The copies were avalon's v14, not v8.** The overwritten `agent.py` in all three folders has sha256 `2d0da2435f2d…`, the same as `agent.py` inside `releases/v14.zip`. v8's is `aa308ddd…`. v14 was the active upload from 00:04:43 to 00:14:13 (`emu/run/avalon/portal_state.json`).
- **Cobra also played the copy.** Its scheduled step to v12 at P9 points at the overwritten folder `bots/v12-e1925f13`, so Cobra played v14 in P9 and R6. Bishop did not: it left the v10 folder at R4. The copies therefore played as follows: Castle R4, P8, R5, P9, R6; Bedrock R4 only; Basalt R4, P8, R5, P9; Cobra P9, R6.
- **Many scheduled steps land on a version another team already plays.** Ace v4 = Arrow v4, Bishop v10 = Bluff v10, Bishop v15 = B4 = Bluff v15, Delta v14 = Drift v14 = D3 v14, Bedrock v11 = Basalt v11 = Base11 v11. Several steps between near-identical designs therefore barely change behaviour.

---

## 1. Detection table

Times are local. "Δ" is the time from first visible to first report, in minutes.

### 1a. Scheduled version steps (14)

| # | True change (stage, start) | Visible in behaviour? (team's own rates) | Detected? by whom, when, Δ | Accuracy / evidence |
|---|---|---|---|---|
| 1 | Ace v3→v4, R1 23:20 | **Yes.** raise flop bet 15.5% (n 1,278) → 4.0% (n 6,927); river fold 20.7 → 26.8; c-bet 84.9 → 78.7. `fp_train` flag c (fold_bet_1 z 4.4, open z −4.3) | **Missed.** SCOUT 23:27:01: "no team changed bot from P4 to R1" | The miss lies with SCOUT's overrule, not the tool. RESEARCH repeated at 23:49:45: "First team to change bot today" (Bishop). False. |
| 2 | Delta v2→v7, R1 | No (every rate within noise; no flag) | Missed | Not detectable from these rates. |
| 3 | Drift v7→v14, P5 23:30 | Weak (fold to c-bet heads-up 0.7 → 2.3%, z 3.5; raise flop bet 12.4 → 10.4). Flag c | Missed. SCOUT 23:33:20 "no team changed bot from Round 1". Its own TESTER list left Drift out on flag c | The tool caught it; SCOUT read the flag as noise. |
| 4 | Bishop v5→v10, R2 23:40 | Yes (fold to flop bet 79 → 34, z −29) | **SCOUT 23:46:49 (TESTER) / 23:46:56 (RESEARCH), Δ 1.9.** RESEARCH → BUILDER 23:49:45 | Exact: "preflop is identical, so it now plays like B4 and Bluff". v10 is Bluff's old version. ANALYST 23:52:06 valued the change: "Bishop's change did not cost us". |
| 5 | Castle v8→v12, R2 | No (open 49.6 → 50.5; no flag) | Missed | Not detectable. |
| 6 | Bluff v10→v15, P6 23:50 | Weak (fold to flop bet 34.3 → 28.7, z −4.6). Flag c, one of 14 flag c's that window | Missed. SCOUT 23:59:08: "no team changed bot … the 14 flag-c rate moves look like the field answering A6" | Confounded with our own switch to A6. SCOUT withdrew the "answering A6" reading at 00:15:10, but never revisited Bluff. |
| 7 | Ace v4→v13, R3 00:00 | Yes (open 47.6 → 55.2, open-shove 5.1 → 9.0) | **SCOUT 00:07:11, Δ 2.3** | Exact, including "post-flop the same". |
| 8 | Basalt v6→v9, R3 | Weak (open z 3.7). Flag c | Missed. Basalt stayed in the 00:07 yardstick list | Hard to see. |
| 9 | Arrow v4→v13, P7 00:10 | Yes (open 47.9 → 55.0) | **SCOUT 00:13:10, Δ 1.0** | "The same preflop change Ace made at R3". Exact: both are now v13. SCOUT also predicted "expect another in round 4" (00:13:14), which came true. |
| 10 | Bishop v10→v15, R4 00:20 | No within R4 (moved with its twins B4 and Bluff). Flag c | Missed. SCOUT 00:36:40 listed Bishop as "unswapped, with the same style as R3" | v15 ≈ v10 in these rates, and the whole field moved in R4. |
| 11 | Bedrock v9 (copy at R4) → v11, P8 00:30 (hidden) | Yes, from R5's data (open 48 → 33) | **SCOUT 00:45:10 (R5 landed 00:44:31), Δ 0.7**; "Base11's twin" 00:46:51 | Correct: v11 is Base11's bot. "Back to its R3 style" is close enough (v9 ≈ v11). That the step happened at the hidden P8 was unknowable. |
| 12 | Delta v7 (random) → v14, R5 00:40 | Yes | **SCOUT 00:45:10, Δ 0.7**; "a D3/Drift twin" 00:46:59 | Exact: v14 is D3's and Drift's bot. |
| 13 | Cobra v8 → v12 = **avalon v14 copy**, P9 00:50 | Yes (flat 1.6 → 20.7) | **SCOUT 00:55:07, Δ 3.2**; ANALYST 00:55:35 | "Swapped into a third copy of our D-line": correct. ANALYST: "copies of v8": wrong version (see 1c). |
| 14 | Basalt v9 (copy) → v11, R6 01:00 | Yes | **SCOUT 01:05:39, Δ 0.7**; "a triplet of Base11 and Bedrock" 01:06:55 | Exact. |

Score: 7 of 14 reported, all correctly described, with a median Δ of 1.0 min. Of the 7 misses, 5 had no usable signal in the team's rates (Delta R1, Castle R2, Bishop R4, and weakly Basalt R3 and Bluff P6) and 2 had one (Ace R1 strongly, Drift P5 weakly). The automatic drift flags in `fp/drift.json` caught 12 of the 14 steps (all but Delta R1 and Castle R2) and every hostile or copy change. Their precision was poor: flag c fired on 13 or 14 teams in P6, R3 and P9. Flag a fired only on real swaps (R4: 7 of 7, R5: 2, P9: 1, R6: 1) and never falsely.

### 1b. The three teams that switch design within a table (until R4, when they became hostile)

| Team (truth) | Detected? | Evidence |
|---|---|---|
| Switch BA, v11 → v13 after hand 80 | **Suspected 22:44:44** (P1 landed 22:42:15, Δ 2.5): "Switch BA and Switch DC score 0% at 40 hands … (in-table switchers?)". **Confirmed for BA 23:28:20**, from P2 to P4: "Switch BA folds 14-26 pts LESS after hand 20 against everyone. It switches style mid-table (its name fits)" | Right team and right kind of change. The split was at hand 20 rather than 80, and the switch hand was never estimated. Relayed to BUILDER 23:36:05. Found as a by-product of a check for adaptation to us. |
| Switch DC, v14 → v12 after hand 40 | Suspected once (22:44:44, above). Never followed up | Missed. |
| Switch CD, v12 → v14 after hand 60 | No | Missed. |

### 1c. The four hostile bots and the copies of avalon's bot (all first played R4. R4's data was held until 00:34:01. True finish 00:24:53)

| Truth | Detected? by whom, when, Δ (from 00:34:01) | Accuracy |
|---|---|---|
| Switch DC → all in preflop every hand | SCOUT 00:34:41 "collapsed … new donor bots" (Δ 0.7); 00:36:00 "shoves everything (open-shove and 3-bet 99.7%)" (Δ 2.0) | Exact. |
| Switch BA → re-raises every open | SCOUT 00:36:00 "3-bets 98.6% preflop, then folds 87% to flop bets"; TESTER 00:51:09 "min-3-bet, 1.57× the open" | Exact. |
| Switch CD → only minimum or all-in sizes | SCOUT 00:36:00 "limps 70% and calls (pfr 4.7%)"; TESTER 00:51:09 "limps 69.7% … calls 66%" | **Partial.** The behaviour was described, but the size rule (min or all-in) was never named, so it was modelled as a limp-calling station. |
| Delta (v7 folder) → uniform random | SCOUT 00:36:00 "loose-passive (vpip 63, limp 34%)", 00:40:48 "wild"; **TESTER 00:51:09: "It is a uniform-random bot: equal odds among the legal kinds"** (Δ 17) | Wrong first label, exact 17 min later. |
| Copies of avalon v14: Castle, Bedrock, Basalt (R4) | SCOUT 00:36:00 "Basalt, Bedrock and Castle now play like OUR bot … possibly a newer one than v8" (Δ 2.0); 00:40:48 "I lean to a v14-or-later D-line (its add-only ICM calls), but that's a hypothesis" | **SCOUT was right about the version** and said so with care. |
| Same, version claimed later | ANALYST 00:48:47 "near-CLONES of v8"; ANALYST 00:55:35 "copies of v8, not v16"; RESEARCH → BUILDER 00:55:42 "Copies are v8 clones" | **Wrong version.** ANALYST's test (three-handed blind fold) cannot separate v8 from v14, because d3h only arrived in v16, and v14 was never in the comparison. Cost was small (heads-up v14 − v8 = 0.00 ± 0.07, 23:51), but TESTER's "five v8 copies" field was the wrong copy. |
| Copy persistence: Bedrock left at P8, Cobra joined at P9, Basalt left at R6, Castle stayed | 00:45:10, 00:55:07, 01:05:39 | All correct. Nobody wrongly called Bishop a copy. |
| What a copy costs | SCOUT 00:48:22 (fillers removed): v8 R4 with no copy 27.66 ± 0.44, one copy 25.26 ± 0.42, two 21.40 ± 0.69 | A sound measurement after one correction (00:40 numbers included filler tables). |

### 1d. Portal faults

| Truth | First visible | Detected? by whom, when, Δ | Accuracy / explanation |
|---|---|---|---|
| False standings, 00:08:00 | `state/status.md` 00:08:57 snapshot: avalon 6th, 115.71. The watcher posted no event | No session raised it before Dylan's message at 00:11:44 ("there was a bug earlier, and it actually turns out we're rank 6"). BUILDER 00:12 (relay 00:13:24): "deduction of 39.58 not explained by the round rows" (Δ ≈ 3.5). **SCOUT 00:18:16: "STANDINGS DON'T ADD UP … By results.json x weights we are 1st with 155.29"** (Δ 9.3) | SCOUT exact, including the three other teams affected. TESTER found the formula at 00:37 ("3rd-placed … minus 6.00"). RESEARCH 00:16 first accepted it as "the portal corrected its totals". Wrong explanation: RESEARCH 00:48:47, from Samuel's joke: "the gap is an organizer penalty, not a scoring bug", corrected 00:49:27. |
| Round 4 results held, 00:20:40 → 00:34 | About 00:25:30 (rounds normally land by +5 min) | BUILDER 00:27:12: "Round 4 was still running at 00:26:49 (6 min 49 s)" | **Wrong explanation throughout.** BUILDER 00:29 MODAL HOLD: "the rounds probably share Modal capacity with our fan-out". RESEARCH 00:32:57: "our own rig jobs … take the capacity the round's shards need". Never recognised as a hold. |
| 00:30 practice hidden | 00:30 onwards (no row) | Noticed as missing: BUILDER 00:31 "the practice is queued behind it"; RESEARCH 00:34 "has NOT started"; STYLIST B 00:38 "no row" | **Wrong explanation.** Taken to be queued, then "starved" ("the 00:50 practice must not be starved like the 00:30 one", 00:44-00:45). RESEARCH even saw the hidden practice's containers ("those 8 started at 00:30:05-00:30:15", 00:32:57) and read them as round 4's shards. |
| Weights → 1,2,3,5,8,13 from 00:26 | 00:26:00 (portal.json snapshot 002704) | **Watcher URGENT 00:26:12 (Δ 0.2)**; BUILDER 00:27: "round 4 stays x4, round 5 x8, round 6 x13" | Correct. RESEARCH doubted it at about 00:41 (the "x5" label); SCOUT settled it at 00:45:10 ("multiplier says x8 and the label x5"). |
| 23:50 practice slow (493 s), caused by the team's own rig on the shared Modal | About 23:53; landed 23:58:15 | BUILDER clock T-6 23:54: "No practice result at T-6"; RESEARCH 23:58: "slow, not hung … v12's start-up cost per worker is my guess" | First guess wrong; ANALYST 00:03 "loaded host" was closer; **correct cause only at 00:29 (BUILDER, "not proven") and 00:32:57 (RESEARCH, measured containers)**, 31 to 35 min later, and then misapplied to round 4. |
| Portal restart, 00:00:09 (about 4 s) | — | **Not found**: no error in any log, transcript or inbox | Expected for a 4 s gap between polls. Costs nothing. |

### 1e. False alarms (changes reported that did not happen)

| When, who | Claim | Truth |
|---|---|---|
| 23:05 SCOUT (P3) | B4, Bluff, Switch BA "fold 14-19 pts less to OUR bets" (adaptation?) | No adaptation. SCOUT withdrew it at 23:35 (texture and v6's new bets). Labelled a hypothesis throughout. |
| 23:59 SCOUT (P6) | 14 teams' rate moves are "the field answering A6" | Withdrawn 00:15:10 ("I withdraw it"). The one real change in that window (Bluff) was lost in it. |
| 23:49:45 RESEARCH → BUILDER | Bishop is the "first team to change bot today" | Ace had changed at R1. |
| 00:36:36 SCOUT (R4 card) | Ace and B4 fold to our 3-bets 42-44 pts less in hands 1-20 (n 30-36, labelled a hypothesis) | Neither changed. |
| 00:48:47 ANALYST, relayed 00:49:14 | "The strong house teams copy the bot we played the round before" | False. There was one injection, of v14. Refuted by ANALYST at 00:55:35. |
| 00:55 SCOUT (P9) | Ace and Arrow fold 13-16 pts less to our 3-bets ("may be noise or a small change") | No change. Hedged. |

### 1f. Wrong explanations (a real event, the wrong cause)

- Held round 4 and hidden practice → "our Modal fan-out starves the rounds" (00:29 to 00:45). Consequence: a team-wide Modal hold. v16's gated runs were skipped (BUILDER 00:34: "the runs I had gated skipped"), and STYLIST B reported "D8's field1 and heads-up runs did not happen" (00:38).
- The slow 23:50 practice → "v12's start-up cost" (23:58), then v12's 6,243 misses → "a growth bug" (RESEARCH → BUILDER 00:00:54), revised to host load at 00:03:52. That revision was the right direction.
- The standings → "the portal corrected its totals" (RESEARCH 00:16), then "an organizer penalty" (00:48:47). SCOUT's "fault" reading stood in the end (01:05:39).
- The copies → "v8" (00:48 to 01:07) instead of v14.
- Delta in R4 → "loose-passive" until TESTER's 00:51 count.

---

## 2. Question 1: the 23:45 "which opponents changed?" answer

**Not found as a human message.** `prompts.md` has no human prompt to RESEARCH between 23:39:14 ("Yes, v8 on that rule") and 00:09:37, and RESEARCH's transcript around 23:45 contains only monitor events and peer messages. The answer the team actually gave at that moment was SCOUT's R2 field trend (23:46:56), which RESEARCH relayed to BUILDER at 23:49:45: "Sim Bishop changed its post-flop play … First team to change bot today". Scored against the schedule up to R2 (P6 had not landed):

| Team | Truth by R2 | Team's answer | Verdict |
|---|---|---|---|
| Bishop | changed at R2 | changed | correct |
| Ace | changed at R1 | not changed | **wrong** (the signal was visible, see 1a #1) |
| Drift | changed at P5 | not changed | wrong (weak signal, flagged by the tool) |
| Delta | changed at R1 | not changed | wrong (no signal) |
| Castle | changed at R2 | not changed | wrong (no signal) |
| The other 15 | not changed | not changed | correct |

So 16 of 20 teams were right, but only 1 of the 5 changes was found. The claim "first team to change" was false. Of the four misses, only Ace was clearly findable in the data.

## 3. Question 2: precision and recall of the yardstick lists

Truth for each window is "the same bot at both stages". A second check is the bundle designer's strict set, the seven teams that never change (D3, B4, Base11, C1, Placeholder, Check Or Fold, Min Raiser). The lists are SCOUT → TESTER in `cross_session.md` at the times shown.

| Window (SCOUT's list, time) | n | Precision | Recall | Wrongly included | Strict-7 in list | Switch teams in list |
|---|---|---|---|---|---|---|
| P1→P2 (22:59) | 12 | 12/12 | 12/20 | — | 3 | 3 |
| P1-P3 strict (23:05) | 10 | 10/10 | 10/20 | — | 3 | 3 |
| P4, the 13 it recommends (23:13) | 13 | 13/13 | 13/20 | — | 6 | 2 |
| P4→R1 (23:27) | 15 | 14/15 | 14/18 | **Delta** | 6 | 2 |
| R1→P5 (23:33) | 12 | 12/12 | 12/19 | — | 3 | 3 |
| P5→R2 (23:47) | 18 | 17/18 | 17/18 | **Castle** | 6 | 3 |
| R2→P6 main (23:59) | 18 | 17/18 | 17/19 | **Bluff** | 6 | 3 |
| R2→P6 strict 6 (23:59) | 6 | 6/6 | 6/19 | — | 3 | 0 |
| R2→R3 main (00:07) | 17 | 15/17 | 15/17 | **Basalt, Bluff** | 6 | 3 |
| P6→R3 strict 7 (00:07) | 7 | 7/7 | 7/18 | — | 3 | 1 |
| R3→P7 (00:13) | 16 | 16/16 | 16/19 | — | 7 | 3 |
| P7→R4 strict 3 (00:36) | 3 | 3/3 | 3/12 | — | 3 | 0 |
| P7→R4 strict + "usable" (00:36) | 13 | 12/13 | 12/12 | **Bishop** | 7 | 0 |
| R4→R5 strict 12 (00:46) | 12 | 12/12 | 12/18 | — | 5 | 1 |
| R4→R5 strict + "with care" (00:46) | 18 | 18/18 | 18/18 | — | 7 | 3 |
| R5→P9 "all but Cobra" (00:55) | 19 | 19/19 | 19/19 | — | 7 | 3 |

Pooled over the main list of each window up to R4 (P2, P4, R1, P5, R2, P6, R3, P7, R4): precision 128/134 (96%); after R4 it was 100%. Every wrongly included team was a version step with little or no behaviour change (Delta R1, Castle R2, Bluff P6, Basalt R3, Bishop R4), so the yardstick error that actually reached TESTER's edges was near zero in effect. Recall was low in the build hour (50 to 65%) because SCOUT dropped every team with a drift flag, and those flags were mostly confusion between clones. From R2 on it was 84 to 100%. One caveat for Sunday: every main list included the three switch teams, which the rehearsal designer had ruled out as yardsticks. That did no harm here, because between rounds they were the same bot.

## 4. Question 3: fingerprinting and recognising seats

- **Built:** yes. `analysis/fp_hh.py`, `analysis/fp_train.py` (likelihood model, calibration, drift flags, yardsticks, profiled-us, counters), `analysis/field_trend.py` and `analysis/counters.json`. They ran on every download through the watcher in 12 to 39 s.
- **Accuracy measured:** yes, every round. Same-round top-1 at 20 hands was 40 to 47% and lagged 26 to 46%, against a bar of 55%. ECE ran 0.026 to 0.07. Our own seat was named 99% of the time by hand 20, and only 33% in R4, when the copies sat at the tables (SCOUT 00:36:36). Min Raiser was recognised with certainty (recall 1.0 at 40 hands). The low accuracy is mostly an artefact of the rehearsal: SCOUT named the duplicate families correctly at 22:44:44 ("Bluff/B4, Ace/Arrow, Castle/Cobra/C1/Switch CD, Basalt/Base11/Bedrock, Delta/Drift/D3"), and Castle, C1 and Cobra were literally the same bot (v8) at P1.
- **Used in a bot:** no. `FP_ON` stayed false all night. The one counter switched on (Min Raiser, 23:41) is v11's `d4b_rr_seat`, an in-table count of a seat's min-raises; SCOUT said at 23:41:25 that it needs "no recognition". It was in v11, v14 and v16, so it played only in R5 (v16; Min Raiser 2.46 → 1.50, SCOUT 00:46:51). v17, the R6 bot, has no min-raise code (grep of `releases/v17.zip`). The donor counters (00:36 to 00:38) were also designed recognition-free ("never from a team name: the organizers swap bots every round").
- **Did anyone notice a seat changing mid-table?** Partly (1b). SCOUT suspected BA and DC at 22:44:44 and confirmed BA at 23:28:20 using a hand-20 split. The method in `strategy/FINGERPRINTING.md` §4 looks for the interaction "vs us minus vs others", which by design removes a change that hits everyone, so the BA finding was a by-product of a check RESEARCH asked for at 23:05:54. Nobody estimated a switch hand. DC and CD were not found. Nothing in a bot reacted to it.

## 5. Question 4: from landing to a usable card, trend or recommendation

| Stage | Landed (watcher) | Card / fp card | SCOUT first line | ANALYST first line | Pick that used it |
|---|---|---|---|---|---|
| P1 | 22:42:15 | +18 s / +12 s | 22:43:38 (+1.4 min) | 22:43:26 (+1.2) | — |
| P2 | 22:52:26 | +16 / +22 s | 22:56:43 (+4.3) | 22:53:11 (+0.8) | — |
| P3 | 23:02:24 | +16 / +23 s | 23:03:30 (+1.1) | 23:03:23 (+1.0) | — |
| P4 | 23:12:11 | +16 / +23 s | 23:13:02 (+0.9) | 23:14:20 (+2.2) | R1 FINAL v7 23:12:32 (+0.4) |
| R1 | 23:24:37 | +18 / +29 s | 23:27:01 (+2.4) | 23:27:47 (+3.2) | — |
| P5 | 23:32:52 | +13 / +32 s | 23:33:20 (+0.5); full trend 23:37:33 (+4.7) | 23:39:23 (+6.5; tasked 23:38) | R2 FINAL v7 23:33:30 (+0.6) |
| R2 | 23:45:00 | +13 / +17 s | 23:46:56 (+1.9) | 23:52:06 (+7.1; busy on a count) | — |
| P6 | 23:58:15 (8 min late) | +14 / +32 s | 23:59:08 (+0.9) | 23:59:23 (+1.1) | R3 FINAL v8 23:59:08 (+0.9) |
| R3 | 00:04:52 | +15 / +19 s | 00:07:16 (+2.4) | 00:06:41 (+1.8) | — |
| P7 | 00:12:14 | +14 / +36 s | 00:13:14 (+1.0) | 00:13:11 (+1.0) | R4 FINAL v8 00:12:24 (+0.2) |
| R4 | 00:34:01 (held 9.1 min) | +15 / +22 s | 00:34:28 (+0.5); copies 00:36:00 (+2.0) | 00:38:17 (+4.3) | R5 FINAL v16 00:37:10 (+3.2) |
| P8 | never shown | — | — | — | — |
| R5 | 00:44:31 | +15 / +39 s | 00:45:10 (+0.7) | 00:45:41 (+1.2) | — |
| P9 | 00:51:57 | +16 / +38 s | 00:55:07 (+3.2) | 00:54:07 (+2.2) | R6 FINAL v17 00:53:38 (+1.7) |
| R6 | 01:04:57 | +13 / +18 s | 01:05:39 (+0.7) | 01:05:50 (+0.9) | — |

Every pick came within 3.2 min of its data. When data failed to arrive (P6 by T-6, R4 and P8 by T-10), the written fallback ("no practice result … the rule's answer is the live bot", `prompts/RESEARCH.md`) was applied on time (23:54:17, 00:30:15). Deeper reads, such as copy costs and counters, took 6 to 14 min, which is the next round's window.

## 6. Question 5: what the team concluded about its own bot, and whether a release acted on it

| Finding from hand data (who, when) | Release that acted | Outcome |
|---|---|---|
| v2 calls post-flop bets too light (ANALYST 22:45:43) | v6 (D2b, P3): fold to a 40%+ first bet without top pair, and more | Acted within 15 min. Became the base of v7 and v8. |
| Heads-up big blind loses, worst under 10bb (ANALYST 22:51:54) | v7 (D3b): heads-up BB calls by push/fold tables | Acted. "v7's heads-up big blind fix works" (23:15:02). |
| Over-folding to all-ins (ANALYST 23:14:20) | v8: call first-in all-ins at 3-6 left by ICM tables | Acted. Confirmed on a scored round: "+0.33 a table, z 7.4" (RESEARCH 00:09:03). Played R3 and R4. |
| The `icm_ok` bug, "v7 fixes only preflop heads-up; the rest is still bugged" (ANALYST 23:16) | v16 (D7): `d7_allin_icm_fixed`, `d7_hu_post_fixed` | Acted. Played R5 (27.37, our best scored round until R6). |
| v6, v7 and v8 fold about 80% to Min Raiser's min-raises (SCOUT 23:07, 23:28, 23:37) | v11 → v14 → v16 (`d4b_rr_seat`) | Acted, but first played in R5. **Dropped in v17 (R6).** |
| Three-handed and heads-up are the thin stages (ANALYST 23:53: 3 left +0.12, 2 left −0.09 a table) | v16: `d3h_defend` | Acted in R5. **v17 lacks it** (ANALYST 00:57:17 "v17 lacks d3h"). R6 then measured three-handed blind defence at −0.65 ± 0.15, z −4.3: "the one clear loss" (01:07:22). |
| Our bot is fully identifiable (99% by hand 20), but the field does not adapt to us (SCOUT 22:44, 23:35) | None needed: "no reason to vary play to avoid being read" (RESEARCH 23:36:05) | Correct for this field. |
| R4: facing a first bet of 40%+ pot now costs −1.41 ± 0.38 (ANALYST 00:38:17) | None targeted it. v17's narrowing folds to "honest" bets, which ANALYST judged "worth LESS in this field" (00:48:47) | Not acted. |
| R4/R5: copies fold 84% to our 3-bets → 3-bet wider at 9-12bb (SCOUT 00:40:58, 00:55:14) | D10c / D10 (STYLIST B → CHALLENGER) got "fit, no measured edge" (00:56:13) and was not played | **v17 did the opposite on size**: its 7-9bb 3-bets got 67-68% folds and lost −0.26 (ANALYST 01:07:22). |
| Donor counters a-c (RESEARCH 00:38:19) | D10 (`d10_vs_limper` and others), not played | Not acted. R6: "v17 feeds the donors" (SCOUT 01:06:55). |

In short, the build-hour and early-round findings were turned into releases within one window, with measured gains. The findings after round 4 were not. The final release (v17, a different style line) dropped two fixes the D-line had proved (Min Raiser, d3h), and the R6 data then showed the d3h loss.

---

## 7. Classification and proposals

| Finding | Kind | Cost on Sunday | Proposal |
|---|---|---|---|
| Held round and hidden practice blamed on our own Modal; the resulting hold stopped our testing (1d, 1f) | **Artefact of the rehearsal** (the rounds really did run in our Modal workspace, and the 23:50 practice really was slowed by our rig), applied wrongly to a later fault | Medium if repeated: lost test runs at the moment they mattered | No change to the bundle. On Sunday the rounds cannot share our Modal, and `CLAUDE.md` already says results "normally arrive in the following 20-minute window" and that a missing practice means the live bot. For future rehearsals: run the emulator's rounds outside the team's Modal workspace. |
| Ace R1 and Drift P5: true drift flags overruled as noise (1a #1, #3) | **Instruction + behaviour.** `strategy/FINGERPRINTING.md` §2 treats flag (c) as "refresh the rates, keep the counters", never as "changed bot"; SCOUT then generalised "flags are noise among look-alikes" | Low here (the missed steps changed little); could matter with real teams | Optional, one line, `strategy/FINGERPRINTING.md` §2 after "(c) alone → refresh the rates, keep the counters.": add "If a (c) move is 5+ points against everyone, not just us, say in the field trend that the team may have changed bot." Otherwise no change. |
| Copies named v8, not v14, after SCOUT had said v14 (1c) | Behaviour | Negligible (v14 ≈ v8); the scenario cannot happen on Sunday | No change. |
| No session raised the standings change for about 3.5 min; Dylan's message came first | Behaviour (the watcher posts no event when standings stop adding up) | Low: SCOUT diagnosed it at 00:18 | No change. If wanted, the watcher could warn when a total ≠ rows × weights (code, not a rule). |
| Fingerprinting never reached its bar and was never used; the switchers were mostly missed | Mostly an **artefact** (a field of near-duplicate bots). §4's "vs us minus vs others" removes a change that hits everyone | Low | No change. Leave it loose. |
| v17 dropped proven fixes (Min Raiser, d3h) | Behaviour (style lines not merged) | Real, if it repeats | Outside detection. The challenger and merge reviewer should own it. No rule proposed here. |

**What I could not determine:** whether the 22:44 "in-table switchers?" hint for Switch DC was ever followed up outside the messages (SCOUT's transcript shows no later work on DC); whether any human outside the logged sessions asked "which opponents changed" at 23:45 (for example by voice to Samuel); the exact second the portal first served the false standings (the watcher snapshots are about 60 s apart); and how much of TESTER's edge numbers depended on the wrongly included yardstick teams (TESTER's edge files were not re-run).
