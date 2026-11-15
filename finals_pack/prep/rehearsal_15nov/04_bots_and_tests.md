# 04: The bots and the testing (dress2, 14 to 15 November 2026)

**Summary (five lines)**
1. The bots did get better, and most of the gain is real. avalon's field-adjusted score went from -2.3 (v2, practice 1) to +9.6 points a table (v17, round 6). The organizer's v14 copies give an independent check in the same rounds: v14 - v8 +0.51 ± 0.32 (R4), v16 - v14 +1.04 ± 0.35 (R5), v17 - v14 +2.38 ± 0.36 (R6).
2. The paired rig predicted the small D-line steps well: v14 - v8 sane +0.58 ± 0.24 against +0.51 ± 0.32 true, and v16 - v14 field1 +0.96 ± 0.40 against +1.04 ± 0.35. It did not predict style A: sane said +7.7 and field1 said -2.0 for v17 - v8, and the truth was about +2.9. The practice edges (SE 0.74) could not resolve steps of 0.5.
3. The costliest call came from the tests, not a bot. A strict "any missed decision fails" reading kept v14 out of round 4 over 6 host-stall misses. Its copies then missed decisions at the field's own background rate and beat v8 by about 0.5 a table.
4. The D line's ICM bug (an all-in shover counted as busted when we fold) was in every D release from v2 (22:32) and played rounds 1-4 in full and round 5 in part. Two checks in the bundle point straight at it; neither caught it. Practice data and STYLIST B found it at 23:09. Fixing it was worth little: about 0 measured.
5. The styles did not end on one platform. The winning D line stayed a standalone file to v16, and style A (v17) won round 6 on the platform. The cost was a second ICM, a rig bug that only hit platform zips, and platform checks that could not run on D. The gain was that D was 3x faster.

Sources: true results `nolimit-emu2/emu/runs/dress2/rounds/<stage>/results.jsonl`, my own recomputation (`python3 -I`, scripts in the session scratchpad); team files under `avalon-nolimit/` (releases/VERSIONS.md, rig/out/verdict-*.md, notes/bughunt/*/NOTES.md, notes/LEDGER.md); `dress2-frozen/` (TIMELINE.md, cross_session.md, load.log). "Adj" = avalon's points a table minus the mean of the four never-changing real yardsticks (Sim D3, B4, Base11, C1), with SE from the per-table points. Errors are 1 SE throughout (the portal's "±" is about 2 SE).

---

## 1. Every release

Origin: **T** = theory tables, **D** = seen in round data, **B** = a bug fix, **S** = a style design.

| Rel (time) | What changed (origin) | Tester's paired result (verdict file) | Bug hunter (notes/bughunt/) | True score, every stage played (± SE) |
|---|---|---|---|---|
| v1 22:24 | minimal legal bot (plan) | legal only; HU vs floor 30.07 ± 0.07 (verdict-v1) | none | never played (uploaded 22:27, replaced before P1) |
| v2 22:32 | design D clean-room, own ICM and pass rule (S) | vs v1 sane +18.7 ± 0.7; HU +16.3 ± 0.3; fit (verdict-v2) | D: none reproduced; ICM tested on static equal stacks only ("icm_ok only ever busts one ... does not fire") | P1 16.87 ± 0.59, 13th of 21, adj -2.27 |
| v3 22:44 | D2 = D + action-narrowed equity + twist_rule v1 (T) | vs v2 sane +3.23 ± 0.70; HU h2h +0.54 ± 0.29; fit | D2: nothing reproduced | P2 21.48 ± 0.61, 1st, adj +2.48 |
| v4 22:47 | style B-2 shove-heavy on the old platform (S, T) | not fit, withdrawn 22:52; quick vs v2 +3.3 ± 1.2 six-max, HU -0.40 ± 0.38 | positional-argument trap; STYLIST B: fold to 3-bet 20% vs 56% target (style.py:314); PLATFORM: exact evaluator on a 3-4 card board | never played |
| v5 22:49 | B-3 = B-2 + ranking v2, fold-to-3-bet 0.50 (T, B) | not fit; vs B-2 -0.48 ± 1.06 | same two bugs as v4 | never played |
| v6 22:54 | D2b = practice-1 postflop and blind fixes (D), bluff 0.40 | vs v3 sane +2.00 ± 0.37 (3,600 tables); HU +0.48 ± 0.20; **odd-bets field -8.72 ± 0.71** (folds 58% to a min-raise of its bet); fit with one hole | re-shove fires with a limper in (10.5%); short BB read as SB (read only) | P3 24.38 ± 0.63, 1st, adj +5.69 |
| v7 23:00 | D3b = HU big-blind calls/jams by pushfold-v5 (T, after D: v2 lost heads-up) + re-shove call | vs v6 sane +1.87 ± 0.24; HU +1.46 ± 0.22; rule 3 "almost dead code"; fit | L99 rule 3 fires with a third player; L100 nearest row instead of row below | P4 25.48 ± 0.64; **R1 26.02 ± 0.28; R2 25.56 ± 0.28** (1 filler miss in R1) |
| v8 23:08 | challenger-2 = v7 + ICM call tables for first-in all-ins at 3-6 left (T, after D: L138 over-fold) | vs v7 pooled sane +0.42 ± 0.32 (2,000); clean re-run 00:16 sane +0.71 ± 0.43, field1 +0.11 ± 0.24; fit | L142 wrong row and depth source (2 of 252 spots in case F); L143 seats mislabelled when SB is all-in for the ante | P5 26.61 ± 0.63; **R3 26.05 ± 0.28** (10 misses); **R4 25.68 ± 0.28, 4th** |
| v9 23:14 | D4 = five fixes: L88, L99, L100, blind positions (B) + raise pricing (D: v6's min-raise hole) | no verdict (tester retargeted to v8 at 23:22) | L145 top pair folds facing a covering all-in raise (rare) | never played |
| v10 23:18 | style C6Ld on platform d257455 (S) | no verdict; quick vs v7 sane -2.70 ± 0.91 | L156 two pair read as one pair; dead settings and unread table; L153 memory-dump order; push/fold off at any other format | never played |
| v11 23:24 | D4b = rule 3 moved so it fires (B) + per-seat min-raise memory (D), bluff 0.50 | vs v7 sane +0.72 ± 0.50; vs v8 -0.03 ± 0.39; odd-bets +7.57 ± 0.52; fit; "icm_ok bug still present" | L158 folds to a small all-in raise at any price | never played |
| v12 23:34 | style A6 on d257455 + v6's postflop fixes (S, D) | vs v7 sane +3.48 ± 0.90, field1 -0.41 ± 0.63; clean re-run 00:16-00:18 vs v8 +2.43 ± 0.91 / -0.85 ± 0.93; fit | L197 minor misclass; ICM call test could not run (old Ctx) | P6 26.87 ± 0.70, but **5,530 scoring + 713 filler misses**; clean iterations 1-900 27.47 (TESTER 00:05:53) |
| v13 23:48 | A7d = A6 rebuilt on 5384acc, depth limits (B, T) | vs v8 sane +3.75 ± 0.89, field1 -0.54 ± 0.90; 3x v8's decision time; fit (00:16) | F1: a jam-depth setting changes nothing up to 65bb | never played |
| v14 23:55 | D5 = D4d + add-only shove table + ICM fix at short_call only (B), bluff 0.40 | vs v8 pooled sane +0.58 ± 0.24, field1 +0.21 ± 0.13; HU -0.04 ± 0.07; fit (23:59) | L243 a priced all-in call still gated by the old ICM; L244 short call priced against the biggest stack | P7 25.82 ± 0.62 (6 misses). **Copies:** R4 26.18 ± 0.16 (Castle 25.69, Basalt 26.54, Bedrock 26.32, each ± 0.28); R5 26.33 ± 0.20; R6 26.21 ± 0.20 |
| v15 23:56 | D6 = v14 + two preflop all-in spots (D: L146 analyst one-change) | vs v8 sane +0.87 ± 0.39, field1 +0.30 ± 0.27; vs v14 +0.34 ± 0.31 / -0.09 ± 0.23; fit (00:30) | nothing in the diff; garbage memory hits the catch-all 23 times (legal answer, inherited) | never played |
| v16 00:22 | D7 = v15 + ICM fixed at the all-in and HU post-call sites (B) + 3-handed blind defence from shorthanded.json (T) | vs v8 sane +1.07 ± 0.37, field1 +1.09 ± 0.32; vs v14 +0.34 ± 0.42 / +0.96 ± 0.40; fit (00:39:39) | **code reading only, no run before R5**: HU post-call margin 0.08 not 0.05; 3-bet all-in up to 35bb; post_raise HU still on the old ICM | P8 27.48 ± 0.65 (hidden); **R5 27.37 ± 0.29** (1 scoring + 11 filler misses) |
| v17 00:40 | A15 = A line on platform 29760d1, EQ_NARROW (T: post-pass narrowing), DEGRADE with bank-only trigger (D: P6 misses) | vs v8 sane +7.69 ± 0.82 (carried from A12), field1 -2.00 ± 0.90; HU sane -0.38 ± 0.20 (-1.9 SE), h2h +2.56 ± 0.37; fit (00:48) | T1: first decision after a very long hand 1.0-1.2 ms (also in v13) | P9 27.66 ± 0.69 (8 misses, 1 table); **R6 28.58 ± 0.30** (3 misses, 1 table) |

The copies are faithful. `field/bots/{v12-e1925f13,v10-27592ea2,v9-678b419e}/agent.py` all have sha256 2d0da2435f2d…, the same as `agent.py` in `releases/v14.zip`, and v14 is a single file. I checked which teams played them from each round's `fixed_bots.json` and the swap log:

- R4: Castle, Basalt, Bedrock.
- R5: Castle, Basalt.
- R6: Castle and **Sim Cobra**. Cobra moved to the v12 folder at P9/R6; the brief does not list it.
- Sim Bishop moved to v15 at R4, so it never played a copy in a scored round.

**v14 against what avalon played, same round (copy minus avalon, unpaired, ± SE):**

| Round | avalon played | Pooled copies minus avalon | Per copy | Rig said |
|---|---|---|---|---|
| R4 | v8 | **v14 - v8 = +0.51 ± 0.32** | +0.02, +0.86, +0.64 (± 0.40) | sane +0.58 ± 0.24, field1 +0.21 ± 0.13 |
| R5 | v16 | **v16 - v14 = +1.04 ± 0.35** | +0.98, +1.11 | sane +0.34 ± 0.42, field1 +0.96 ± 0.40 |
| R6 | v17 | **v17 - v14 = +2.38 ± 0.36** | +2.36, +2.39 | not run against v14 directly (sane-implied about +7, field1-implied about -2) |

Chained, these give v16 - v8 ≈ +1.55 ± 0.47 and v17 - v8 ≈ +2.89 ± 0.49. The copies' missed decisions were 0, 1 and 5 (R4), 7 and 3 (R5), 4 and 0 (R6) per about 970,000. That is the same background rate as the house bots. This confirms TESTER's 00:13:34 reading that v14's 6 practice misses were host stalls ("replayed ... v14 answers those 6 states in 0.02-0.15 ms", cross_session.md:7849).

## 2. Did the local tests predict the field?

| Step | Tester predicted (sane / field1) | Portal gain (my adjustment, or same-round copies) | Team's own portal edge |
|---|---|---|---|
| v3 - v2 | +3.23 ± 0.70 / - | +4.75 ± 0.96 (P2 - P1) | - |
| v6 - v3 | +2.00 ± 0.37 / - | +3.21 ± 0.98 (P3 - P2) | - |
| v7 - v6 | +1.87 ± 0.24 / +0.25 (L157) | +0.92 ± 0.99 (P4); +1.60 ± 0.73 (R1/R2 mean vs P3) | - |
| v8 - v7 | +0.42 ± 0.32 / +0.11 ± 0.24 | +1.05 ± 0.73 (P5); +0.15 ± 0.38 (R3 vs R1/R2) | R1.5 +0.55 ± 0.74; spot value +0.33 a table, z 7.4 (RESEARCH 00:09:03) |
| v12 - v7 | +3.14 ± 0.90 / -0.74 ± 0.92 | +1.31 ± 0.78 (P6 incl. misses) | clean iterations +2.05 ± 0.74 (TESTER 00:05:53) |
| v14 - v8 | +0.58 ± 0.24 / +0.21 ± 0.13 | -0.17 ± 0.76 (P7); **+0.51 ± 0.32 (R4 copies)** | -0.19 ± 0.74 (TESTER 00:12:44) |
| v16 - v14 | +0.34 ± 0.42 / +0.96 ± 0.40 | **+1.04 ± 0.35 (R5 copies)**; +0.47 ± 0.79 (P8 copies) | - |
| v16 - v8 | +1.07 ± 0.37 / +1.09 ± 0.32; v8-copies field +0.76 ± 0.51 (L312) | ≈ +1.55 ± 0.47 (chained) | - |
| v17 - v8 | +7.69 ± 0.82 / -2.00 ± 0.90 | ≈ +2.89 ± 0.49 (chained); **v17 - v14 +2.38 ± 0.36 (R6)** | "+1.88 over Castle, +2.11 over Basalt" (BUILDER 00:54, unaware these were v14) |

Where they disagreed, and why:
- **Early D steps (v3, v6): the portal gave 1.2 to 1.6 times the sane-field number.** TESTER measured this at 23:20 (LEDGER L157: "portal ~1.2 x sane ... field1 halves them"). The field was weaker and easier to exploit than the sane sparring. This is a known scale factor, not a miss.
- **Style A (v12, v13, v17): the two sparring fields disagreed by 4 to 10 points, and the truth lay between them.** verdict-v17.md gives the reason: "The sparring bots in the sane field raise only with two pair or better ... So the rig rewards narrowing." field1 is five copies of one generic `FieldLike` bot fitted to P1-P2 averages (verdict-v14.md:54). It is not a cloned field. The bundle's cloned field (tester.md, "The cloned field") was never built. Kind: session behaviour; there was no time.
- **Small D-line steps (v8, v14, v16): the rig was right and the practice was noise.** A practice edge has an SE floor of 0.74, while each step was 0.3 to 1.1. v14 read -0.19 ± 0.74 in P7 and +0.51 ± 0.32 in R4 against its copies. The paired rig, at 2,000+ tables, was the better instrument here.
- **Rig contamination (23:42-00:05) changed no decision.** The clean re-runs of v12 fell within noise: sane +3.48 became +3.14, field1 -0.41 became -0.74 (TESTER 00:15:54 and 00:18:16). Only v13's heads-up figure was withdrawn (RESEARCH 00:08:49).
- **The field changed under the tests.** From R4 there were the v14 copies and four hostile bots. The team saw it at once (SCOUT 00:36: "Basalt, Bedrock and Castle now play like our D-line bot") and ran v16 against a v8-copies field: +0.76 ± 0.51 (cross_session.md:9303). That run was well judged.

## 3. General gains and field-specific gains

**Evidence that the core is general: the D line scores the same whoever runs it.** The v14 copies scored 26.2 to 26.5 against a field whose best non-D teams scored 20 to 22.4. In R4 each copy took its points mainly from the four hostile "donors" (ANALYST, cross_session.md:9304).

Opponent mix, tables with and without hostile bots (my computation, ± about 0.55 per cell):

| Round, bot vs v14 copies | No hostile at the table | With re-raiser (Switch BA) | With maniac (Switch DC) | With odd sizes (Switch CD) | With random (Delta) |
|---|---|---|---|---|---|
| R4 v8 / copies | 23.97 / 24.77 | 25.42 / 26.28 | 25.19 / 26.10 | 28.74 / 27.78 | 27.59 / 27.93 |
| R5 v16 / copies | 26.28 / 25.00 | 27.81 / 26.24 | 27.16 / 26.45 | 28.97 / 28.34 | 27.76 / 26.65 |
| R6 v17 / copies | **29.45 / 24.92** | **25.40 / 26.94** | 27.23 / 26.33 | 31.25 / 28.15 | 28.90 / 27.24 |

- **General (it should carry to tomorrow):**
  - v7's heads-up big-blind calls by pushfold-v5. It is equilibrium theory, and the spot paid +0.72 ± 0.10 a table in practice 4 (L141).
  - v8's ICM call table: theory, +0.33 a table at z 7.4 on round 3's own spots.
  - v16's ICM fixes and 3-handed defence. v16 led the copies by +0.6 to +1.6 against every opponent group in R5, and by +0.76 ± 0.51 against v8 copies in the rig.
- **Field-specific:**
  - **v17's EQ_NARROW.** It reads an opponent's bets as hand strength. It beat v14 by +4.5 at tables with no hostile bot (honest, never-adapting workflow bots) and lost to v14 by -1.5 ± 0.75 at tables with the re-raiser. Tomorrow's field will hold more bluffing and re-raising than the afternoon bots did, so v17's +2.4 is the gain most at risk.
  - **v6's postflop folds.** These were fitted to practice 1's honest bettors. They had a known hole against min-raisers (-8.72 in the odd-bets field) that stayed in v7 and v8 through four scored rounds.
  - **The one-change lines.** These copied the practice-1 top five (L146 and the others). They worked because the field held still: "every field rate is within 0.1 SE of P2" (SCOUT 23:04).
- **Exploiting the hostile bots:** D10ab, built against the 3-bet folder, was never released, and the tester could not show it stronger (+0.21 ± 0.26, verdict-D10.md). Every bot in this field gained from the donors, so that gain says nothing about tomorrow.

## 4. Bugs: introduced, caught, reached a scored round?

| Defect | Introduced | Caught (time, by, how) | Reached a scored round? |
|---|---|---|---|
| Rig: warm Modal containers kept stale theory tables / RIG_HOLDEM | rig build, about 22:30 | 22:35, TESTER: job v2-m-sane6 had all 50 shards stale (verdict-v2.md); fixed 22:38-22:41 with code and table hashes | no; no verdict used it |
| Platform DEADLINE_HIT and gc pauses over 1 ms | bfcb0b5 22:39 (and earlier drafts) | 22:33, STYLIST B's first pack ("DEADLINE_HIT fired 55 times"); fixed c7e9800 22:54 ("no clock in any decision") | no; it kept every platform style out of P1 (decision 22:41:29) |
| B-2/B-3 open width (style.py:314) and evaluator on a 3-4 card board | v4/v5 | 22:50, STYLIST B (own measurement) and PLATFORM; confirmed by the v4 tester | no; withdrawn 22:52 |
| **D's icm_ok counts an all-in shover as busted when we fold** (HU it never calls) | **v2, 22:32** (`base = {s.seat: s.stack ...}` in v2's agent.py:364) | missed by the D bug hunt at 22:34; symptom in practice data and the v7 tester's runs ("v6 fold 454/454" HU under 10bb); root cause STYLIST B 23:09:21; partly fixed v14 (short_call), v16 (all-in and HU post-call) | **yes: R1-R4 in full (v7, v8), R5 in part (post_raise HU still old).** Measured value of the fix small: all sites +0.01 ± 0.29 (L204); the gate in v14 +0.00 ± 0.06 (L243) |
| Re-shove fires with a limper in | v6 | bug hunt v6 22:59 | yes, R1-R4 (v7, v8); fixed v9 (never played), so the fix reached R5 via v16 |
| Min-raise hole (folds 58% to a min-raise of its own bet) | v6 | v6 tester 23:08 (odd-bets sparring bot, -8.72 ± 0.71) | yes, R1-R4; fixed v9/v11, so R5 via v16 |
| Rule 3 near-dead; L99 third player; L100 nearest row | v7 | v7 tester and bug hunt 23:03 | yes, R1-R4 (wrong numbers, no failed decision) |
| L142 wrong push/fold row and depth; L143 seat labels when SB is all-in for the ante | v8 | bug hunt v8 23:15 (independent oracle on the real engine) | yes, R3-R4 (2 of 252 spots in case F) |
| L145, L158 (raise-pricing gaps) | v9, v11 | bug hunts 23:17, 23:20 | no |
| L153 memory-dump order; L156 two-pair class | platform d257455, v10 | bug hunt v10 23:19 (memlimit test) | no; L153 fixed fe4a0ff 23:28 |
| **Memory growth suspect: `@lru_cache(maxsize=200000)` on icm._mh** | platform d257455 (v10, v12, v13) | STYLIST A, raised by BUILDER 00:09:57; soaks found no growth (PLATFORM 00:09: "37.2 MB at table 100 and still 37.2 MB at table 1,500"; RESEARCH soak 00:16: currsize 0); bounded 367277c 00:15 | no (v12 only played P6) |
| **Rig loader leaks bare `avcore`/`style` modules after a failed import, so a platform zip silently runs another zip's code** | rig/loader.py (not in git; before 23:42) | 23:51-23:53, STYLIST A and STYLIST B, through a crash ("unknown setting 'EQ_NARROW'"); TESTER fixed 23:57:26; old containers served until 00:03:48 ("stale code" hash check); clean 00:05:46; contamination about 1 shard in 5 for platform zips (STYLIST B same-seed proof 00:08:34) | no bot effect; platform numbers 23:42-00:05 re-run |
| check.py broken by uncommitted `avcore.narrow` in the tree; ICM call test cannot run on d257455 | 23:45 | v13 and v14 testers (23:48, 23:53); they used the committed eqcheck or the kit check | no |
| rig/flips.py overwrote its own outputs | rig | TESTER 00:10:26 ("output now named <played>-<asked> (no overwrite)") | no |
| **v12's 6,243 practice misses** | environment: the rig's 40 containers in the shared Modal workspace (brief); v12's thin margin made it worst (6,243 vs 3,828 for the next team) | ANALYST 00:00:22 (late-round pattern); RESEARCH 00:00:54 called it "a growth bug"; PLATFORM 00:03:15 "all teams"; RESEARCH 00:03:52 "laptop load"; true cause seen 00:29-00:32 (round app in the team's own Modal workspace) | P6 only. load.log contradicts the laptop reading: 3.3-8.5 during P6, lower than R1 or P5 (9.9), which had 0 misses |
| v14's 6 misses in P7 | not a defect | TESTER replay 00:13:34 (host stall); confirmed by the copies' own rates in R4-R6 | the strict reading kept v14 out of R4 (about -0.5 a table × 4) |
| L243, L244 (v14 ICM gate, short-call opponent) | v14 | bug hunt v14 23:58-00:06 | fixed in v16 (d7_allin_icm_fixed, d7_sc_shover) |
| v16 margin 0.08 not 0.05; 3-bet all-in to 35bb | v16 | code reading 00:34, never run | **v16 played R5 without the hunt's runs or the VERSIONS extended set** ("extended set NOT RUN", VERSIONS v16 line, 00:34:19) |
| v17 T1: about 1.1 ms after a very long hand | platform (v13 too) | bug hunt v17 00:38 | in R6 (3 misses, 1 table, decision 230+); not shown to be the cause |

**Bundle checks that caught something:**
- Per-shard code hash (tester.md "Modal"): caught 22:35 and 00:02.
- Odd-bets bot in every sparring mix: caught v6's hole.
- Mandatory heads-up run: v4's -0.40/-1.00, v6's 0/947 HU fold symptom, v17's -1.9 SE.
- Positions, check 3: L143.
- Branch counts, check 5: rule 3 dead, v10 dead settings, v13 F1.
- Memory, check 7: L153.
- Hard-coded format, check 11: C's push/fold switches off at other formats.
- Claimed rates, check 9: B's fold to 3-bets.
- Same-minute check_or_fold baseline: correctly cleared v4, v8, v9 and v12 timeouts as load.
- The watcher's health line: "URGENT health: 6243 missed", 23:58:15.

**Never fired, or never ran:**
- Codex second opinion: "not done" in all 16 hunt notes.
- Deep all-in spot, check 12: never run on any D release; run as a measurement on v10/v12 only.
- Cloned field: never built.
- Rules-card check: ran, "rules card: OK"; nothing to catch.
- Alive check and self-test: never failed.
- HU seat-by-blind-amount check (13): passed every time.
- The kit's upload test with no bank: never caught a true bot defect; every hit was traced to load.

**Two checks named the ICM bug's class and still missed it** (session behaviour, correct instructions): bughunter.md "Rules that bit us" says "The kit's library ICM scored a busted stack 0, and two independently written bots made the same error", and its 14 November note says "ICM with a seat busted this hand". The D hunt tested equal static stacks only (notes/bughunt/D/NOTES.md:20-28).

## 5. Failed decisions and timing

On the portal, avalon's failed decisions (the portal count includes filler seats):
- 0 in P1-P5, R2 and R4.
- R1 1 (filler); R3 10 on 4 tables; P7 6 on 2 tables; P8 1; R5 12 (1 scoring); P9 8 on 1 table; R6 3 on 1 table.
- P6 6,243 (rehearsal artefact).

Outside P6, every count is within the house bots' own range in the same round (for example R5: Sim Drift 16, Switch CD 10). Misses in scored rounds cost nothing measurable.

How the team handled 1 ms:
- **Standalone D for P1** (decision 22:41:29), because the platform's gc and deadline code went over 1 ms.
- **No clock in any decision** from c7e9800 (22:54).
- **Every timing claim carried the load and a same-minute check_or_fold baseline**, as the bundle asks. Runs at load 14.8-18.7 (v12, 23:25) were labelled "inconclusive: machine loaded" and re-run quiet at 23:33. load.log peaks at 17.95 at 23:26 (40 claude processes, 50 python).
- **Quiet rule** "by state not clock" (RESEARCH 00:03:52) and a **Modal hold** (BUILDER 00:29).
- **DEGRADE.** 367277c (00:15), then the timer trigger was turned off in 29760d1 (00:29) after STYLIST A measured the timer firing on slow rig containers: -1.97 ± 0.48 (00:27:24). v17 shipped with the bank-only trigger. Whether it fired in R6 is not determined.
- **The cost of style A in time:** mean 0.133 ms against D's 0.047 ms (verdict-v13). This 3x is real on any host.
- **Kind of finding:** the laptop-load diagnosis for P6 was wrong. Rounds ran on Modal in the team's own workspace, so the cause is a rehearsal artefact. On Sunday neither the laptop nor the team's Modal use touches the portal. The quiet rule then only protects local timing measurements, which is its legitimate use.

## 6. One platform, or separate bots?

They ended as separate bots:
- **The D line was standalone** from v2 to v16: one `agent.py`, its own ICM, ranking and pass rule, and 31 D-family candidate folders.
- **Styles A, B and C were settings on the platform:** 22, 10 and 15 zips. Only v12 (P6) and v17 (P9, R6) played. B was withdrawn and C was never uploaded.

The bundle says a standalone design "is ported the moment the pack command arrives" (prompts/BUILDER.md:130-131). Nobody ported D, and nobody recorded a decision not to.

What the split cost:
- **The ICM bug existed only in D's private copy.** The platform's ICM was correct ("The D line's bug ... is NOT in A6", bughunt v12). The platform's equity and ICM checks in check.py were "not applicable (standalone)" on every D release (VERSIONS v8-v16), so the one test that would have caught it could not run there.
- **Fixes were ported by hand in both directions.** v6's fixes went into A6; D5-icmfix and D-3h were built by STYLIST B and C for the D line; A6's preflop went into D8, never released. Each needed its own measurement.
- **The rig's loader bug only hit platform zips** (D zips "not affected", RESEARCH 23:58).

What it bought:
- D was 3x faster and immune to platform regressions, which won P1.
- Diversity: v17 (A) beat v16 (D) by about 1.3 a table in R6.

Kind: a bundle instruction that the run's evidence does not support. Leave the split alone; drop the porting sentence.

## Proposed changes

1. `strategy/DECISION_RULES.md` line 36: replace "zero failed decisions in the checks" with "no more failed decisions than the kit's check_or_fold in the same run (on the portal: no more than the house bots in the same round)". This brings in no new idea: the bundle's own testers already judge timing by that baseline. Read this way, v14 plays R4.
2. `prompts/BUILDER.md` line 130-131: delete "and is ported the moment the pack command arrives".
3. `.claude/agents/bughunter.md` check 12 (and the matching sentence in `tester.md` "Correct:"): replace the deep-spot paragraph with one shorter line: "Calls of all-ins: facing an all-in at any depth with 2 to 6 left, compare each call and fold with the tournament-equity threshold for the players left; a call below it or a fold above it is a bug." The bug lived in heads-up and short shoves, a spot the current check 12 excludes. This one is optional: the fix's measured value was small.
4. `.claude/agents/bughunter.md`: delete the "A second opinion by a different method" (Codex) paragraph. It never ran in 16 hunts.
5. No change to the rig, timing or quiet-rule instructions. The loader and container bugs broke rules the bundle already states ("its own module name with no shared globals"; "stop the app's old containers before redeploying"). The hash check caught them.

## Not determined

- Whether DEGRADE fired in P9 or R6, and whether v17's misses were T1.
- When the loader leak first contaminated a job before 23:42 (rig/ is not in git).
- Whether the residual old-ICM site in v16 cost anything in R5.
- Whether v17's narrowing gain survives a field that bluff-raises.
