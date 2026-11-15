# Speedruns A and B, 14 November: Fable 5.2 against Opus 5.5 on the same bundle

Written 14 November 2026, 16:00-16:40 (`date` at the start: Sat 14 Nov 16:00:01 PST). Read-only comparison of
`/Users/dylan/avalon-speedrun` (run A, Claude Fable 5.2, minute 0 = 06:27:00) and `/Users/dylan/avalon-speedrun-b`
(run B, Claude Opus 5.5, minute 0 = 15:14:00). Both clones hold the bundle at 3f6078d. Sources: the four
`notes/SPEEDRUN-*.md` reports, `git log`, file birth and modification times (`stat`), `state/events.log`,
`inbox/*.log`, `releases/VERSIONS.md`, `notes/LEDGER.md`, `rig/out/`, `notes/bughunt/`, `state/guard.log`.
Nothing in either folder was changed and no bot was run.

## Verdict

**Neither model clearly did better, and one run each cannot separate them.** Each run had one large failure of its
own, unrelated to the model: A's packer arrived at minute 15, so no style could play practice 1. In B the base
called no style hooks and both test rigs ran the wrong bot's code, which voided most style measurements from minute 8
to minute 32. Those two failures account for most of the gap between the runs.

What each did better, on the files:
- **Opus 5.5 (B) was faster at the start.** The rules card was in at minute 1.7 (A: 2.4). v1 was released and
  upload-tested at minute 5.9; A released v1 at 8.6, and its first counting upload test was at 11.8. B had the first
  tester verdict at minute 10 (A: 12.7) and every theory table by minute 16-19 (A: final, correct versions at minute 29).
  Every one of B's 7 releases got a tester verdict that included a heads-up run. A got that for 8 of its 9 playable
  releases.
- **Fable 5.2 (A) did more and measured better.** It made 10 releases against 7 and ran 9 bughunters against 7. It kept
  working to minute 44, while B's last recorded activity was at minute 40. Its paired tests were larger (3,600 paired
  tables a verdict against 2,000) and ran on a rig that was valid all along. It used one of those tests to reverse a
  practice pick inside 5 minutes (v6 to v7), and it ended with a found, fixed and tested bot (v10) and a written
  round-1 answer. Its bots' slowest decisions were also 2-4 times faster than B's: maximum about 0.7-1.7 ms, against
  2.2-3.5 ms with 7% of decisions over 1 ms in one field.
- **Both relayed wrong theory numbers** (A for 19 minutes on range columns, B for 8 minutes on a column mix-up).
  Both had a silent failure that shipped in releases: A's draw rule broke full houses in v2 and v3; B's v2 and v3 cut
  their Monte Carlo by the clock, so their decisions changed from run to run.

**Confidence: low.** The A/B difference is no bigger than what two runs of the same model would plausibly show,
and the conditions differed (time of day, machine load, B's 8-hour idle wait and clock reset).

**What I would run tomorrow: Fable 5.2 (about 60/40, a weak preference).** On a 6-hour day the expensive mistakes
are wrong measurements and decisions taken on them. Run A's evidence was the more trustworthy (valid rig, larger
samples, a pick changed on a paired number), it used the whole window, and its records stayed current: VERSIONS.md
carried verdicts, every output was committed, and its PLAN file survived a compaction. Run B left VERSIONS.md at
"tester: pending" for v2-v7, never updated its research PLAN file after minute 27, and left 60 research paths
uncommitted. Opus's quicker start is real but is worth minutes, not points.

Two practical reasons could outweigh this, and neither comes from these runs. First, which model has usage headroom
for 6 hours: run B itself was postponed by an account usage limit at 07:12. Second, a head-to-head of the two best
zips (end of this report). Whichever model plays, the defects marked "yes" below hit both models alike.

## 1. Where a report and the files disagree (the files win)

| Report | Claim | Files | Effect |
|---|---|---|---|
| A builder | `candidates/D/DESIGN.md` first version 06:30 (minute 3) | file born 06:31:38 (minute 4.6) | small |
| A builder | "RELEASED vN" to RESEARCH within about 1 minute of every release | v7: VERSIONS commit 06:59:43, RELEASED message 07:01:38 (events.log): 2 minutes. RESEARCH saw the zip at 07:01:21 | v7's paired number came 3 minutes after the zip |
| A research | v7 tester at 07:03 | `rig/out/verdict-v7.md` born 07:04:24 | small |
| A research | stop at 07:13 | last action 07:10:53, then idle; Modal stopped 07:15:02, commit 07:15:40 (the report says so itself) | overran 07:13 by 2.7 minutes, idle |
| B builder and research | "stop 16:00" | last BUILDER commit 15:52:48; research report written 15:54:06; no file changed after 15:54 except the clock's | **B stopped at about minute 40, not 45**; nothing was declared for practice 4 |
| B builder | D's DESIGN.md at 15:25:09 (minute 11.2) | that is the modification time; the file was born 15:16:29 (minute 2.5) | D's design was in earlier than reported |
| B builder | "on the fixed rig (HU field) B scored -7.5 ± 2.2 and C -3.0 ± 2.0 vs v2" | the only such lines (LEDGER L69) are local, premium 8-player field, 60 tables: v2−B −6.67 ± 3.02, v2−C −3.33 ± 2.62 | the report's numbers can't be traced to a file |
| B builder | milestone table: v4 verdict "due about 15:50" | L73 15:50, L74 (v6) 15:50, L75 (v7) 15:52 | the table was written before they landed; §6 has them |
| B builder | VERSIONS lines | v2-v7 still say "tester: pending" although all 6 verdicts are in LEDGER; v5's line carries a Modal number that L70 later calls invalid | VERSIONS.md was never brought up to date |
| B research | `state/decisions.md` never created | true: neither B session wrote one (A has 06:39-07:10 entries) | no decision trail in B |

Everything else checked out against git, file times and events.log to within a minute: every release time, every
`[live]` declaration, every clock step and every verdict time quoted below.

## 2. Milestone table (minutes after minute 0; A 06:27:00, B 15:14:00)

| Target | Target minute | Run A | Run B |
|---|---|---|---|
| Rules card `bot/rules.json` | 5 | 2.4 (06:29:22) | 1.7 (15:15:40; committed 5.9) |
| Team Python announced | 5 | 2.4 (`bot/PYTHON.md` 06:29:22) | about 5-6 (BUILDER checked the import at 15:20) |
| Rules card checked by the tester | asap | 3.0 (06:29:59) | 3.0 (15:17:01, 25/25 fields) |
| Interface stub | 6 | 3.4 (06:30:24) | 5.9 (commit 7af32f8 15:19:52) |
| Design D's DESIGN.md | 12 | 4.6 (06:31:38) | 2.5 (15:16:29; final 11.2) |
| v1 released | 10 | 8.6 (06:35:33) | 5.9 (15:19:52) |
| v1 upload test that counts | 10 | 11.8 (06:38:50, bughunter 0/240); at release inconclusive, load 17-19 | 5.9 (0/300 at load 16, "borderline") |
| Harness | 15 | 6.3 (`harness.py` 06:32:10) | 11.3 (658ce8d 15:25:15) |
| Packer usable | ~15 | 14.2 (`pack.py` 06:41:09; commit 15.2) | 6.4 (`pack.py` 15:20:22; commit 11.3); liveness gate 15.5; loader fix 21.1 |
| ICM table | 10 | 6.1 | 4.2 |
| Break-evens / exploit table | 15 | 4.1 (`exploit.json`) | 5.9 (`breakevens.json`) |
| Ranking | 10 | 4.5 first (no data block), usable 6.9, **range columns right only at 29.0** | 8.2 first (**column bug**), fixed 9.0, final 16.3 |
| Twist rule | 15 | fallback 3.3, trusted 11.3, **v4 (full-house fix) 25** | fallback 3.0, trusted 8.8, multiway check 12.5 |
| Push/fold + call tables | 15 | 8 (fallback), 10 (v2), last v5 26.9 | 7 (v1), 10.6 (v2) |
| HANDOFF.md | 20 | 12.5 | 11 |
| Theory wave 2 | from ~12 | 14-18, final 27-29 | 12-16.3 |
| Tester's rig, first paired run | 15 | 6.2 (Modal 8.7) | 6 (working 12; Modal ~10). **Comparing two zips on Modal: invalid until 32** |
| First tester verdict (v1) | 15 | 12.7 partial, 16.5 complete | 10 |
| Styles A/B/C legal | 12-15 | A 16, B 22, C 29 | packed 10-17, but **live only after 14.9** (v2 base); A ~15, B 16.8, C ~22-26 |
| Design D legal | 12-15 | 18.6 (released as v4) | 16.5 (D2.zip), released as v4 at 24.4 |
| Every table built in | 20 | 23.5 (call table, reveal ranges); four tables never built in | 19.3 (v3, ranking v2.1); `pushfold_unequal` 22.9 (off) |
| Later releases | — | v2 15.1, v3 15.2, v4 18.6, v5 25.4, v6 30.4, v7 32.7, v8 37.5, v9 39.3 (withdrawn), v10 40.2 | v2 14.9, v3 19.3, v4 24.4, v5 26.7, v6 32.6, v7 34.0 |
| Practice 1 pick declared | 17 | 15.3 v2, replaced 15.7 by v3 | 15.8 v2 |
| Practice 2 pick declared | 27 | 20.3 v4 (D) (held until practice 1 started) | 24.8 v4 (D) |
| Practice 3 pick declared | 37 | 30.5 v6, changed 37.1 to v7 on a paired test | 33.2 v6 (C) |
| Practice 4 pick declared | 47 | 40.2 v8, replaced 41.3 by v10 | **none** (stopped at ~40) |
| Round-1 recommendation | 51 (T-9) | dry run 24.9; final ranking 40.2; BUILDER's answer v10 (fallback v3) at 43.5 | RESEARCH's rig-only input 37.2 (v4/D); BUILDER's view in its report; nothing written to decisions.md |
| Last recorded activity | 45 | 44 (BUILDER), 43.9 (RESEARCH) | 38.8 (BUILDER), 40.1 (RESEARCH) |

## 3. Quality

| | Run A (Fable 5.2) | Run B (Opus 5.5) |
|---|---|---|
| Releases | 10 (v9 withdrawn, marked NOT FOR PLAY) | 7 |
| Releases with a tester verdict including heads-up | 8 of 9 playable (v1-v8 full; v10: paired 8p and HU runs, upload and determinism, no full verdict) | 7 of 7 (LEDGER L19, L66, L62, L73, L68, L74, L75) |
| Bughunter reports | 9 (every release but v9), 2-6 minutes after release | 7 (v1-v7); only v1, v2 left a REPORT.md, the rest are LEDGER lines + test files |
| LEDGER lines | 117 | 75 |
| Paired-test size per verdict | 3,600 paired 8p tables (2,400 for urgent runs) plus heads-up; SEs 0.23-0.39 | 2,000 per 8p field, 600-1,000 HU; v6 800-2,400; SEs 0.16-0.72 |
| Modal throughput measured | 126-151 tables/s (30-table shards) | 93 tables/s |
| Failed decisions | 0 in every run (about 0.6-1.0 million decisions a verdict) | 0 in every run (1.6 million in one) |
| Slowest decisions | Modal p99 310-340 µs; local max 387-832 µs, one 1,685 µs in-process spike (v6); v4 1,382 µs at load 9.7 | v2 p99.9 2.2-2.3 ms, 7.1% over 1 ms in the calls field; v3 multiway p99.9 2.27 ms; v4 max 2.77 ms; v7 max 3.5 ms (load 11) |
| Determinism | v3 not (wall-clock backstop); v5 on, deterministic | v2, v3 not (deadline cut 23.5% of equity calls); v4 (D) not; v5 on, deterministic |

**Bugs found, and by whom**
- A: draw rule threw a made full house (bughunter v2; theory's rule, shipped in v2 and v3); covered-call pot odds and two
  dead counters (bughunter v3); limped-pot big blind read the first-in jam table (bughunter v4); shover width read our
  stack, re-shove width too wide (bughunter v5); two open bugs in style B (bughunter v6); **AA/KK fold to deep all-ins**
  (bughunter v7, a narrow brief; present since v3; fixed in v10); v9's first fix widened multiway calls (platform caught
  it); ranking/multiway range columns up to 6 points wrong (theory run 3's independent matrix); `pfcheck.py` crash.
  The tester found v5's call table cost 0.87 ± 0.32 a table 8-handed and v6 3.07 below v3; the analyst found five
  format bugs on the dry run.
- B: two latent shell bugs (bughunter v1); **AA folds to a 100bb shove** (bughunter v2, L48) and again after flats
  (bughunter v5, L67; inherited by C, L71); multiway timing (L49); multiway gate folds JJ/AK short (L52); deadline
  cuts 23.5% (L53); D crashes on quads boards and runs over 1 ms (L59, L60). The analyst found the base never called
  the style hooks. The rig tester found the import collision and the stale Modal containers. Theory's embedding check
  found v2's stale ranking and two silent fallbacks, and the v4 tester found two more (hook-error counter name,
  style import failure). The v7 tester found a −1.29 ± 0.40 regression.
- Both runs independently built an all-in call path that folds AA when deep, and in both it was a bughunter with a
  narrow question that found it. Nothing in the bundle tests for it yet.

**Silent failures** (wrong with every check passing)
- A: ranking shipped without its data block (2.3 min); range columns wrong for 19 minutes (symmetry check passed);
  the full-house throw in two releases; v5's VERSIONS line carried a wrong fold-to-re-shove claim for 9 minutes; a
  Modal executor ran stale code for 1.5 minutes.
- B: candidates B and D played pure check-fold while pack and check printed "kit check OK" (minute 10-15); two-zip
  comparisons on Modal ran the first zip's code for both (minute 8-32: most stylists' numbers void, L50-L58,
  platform's L58/L64/v5 line); D's postflop hook crashed 2 in 7,450 unseen (counter name mismatch); a style that
  fails to import silently plays the base; v2 shipped a stale ranking; the Monte Carlo deadline made v2/v3
  unrepeatable. B's silent failures cost more measured work than A's.

**Mistakes in decisions and relays**
- A: RESEARCH told BUILDER ranking v2 was "no longer fallback" while the file said fallback (06:38); forwarded two
  numbers from the wrong columns (corrected 06:56). The draw rule was edited in place five times, twice under one label.
  BUILDER packed style B (v6) on a fix release (v5) before v5's verdict; both measured worse than v3. BUILDER
  recovered with v7 on a pre-written rule and a paired test (+0.90 ± 0.23). Practice-1 and practice-4 picks were each
  replaced within a minute (v2 to v3, v8 to v10).
- B: RESEARCH relayed "22 rank 155, 72o 38.2%" from a buggy ranking file (15:23, corrected 15:31). BUILDER broadcast
  the fallback draw rule a minute before it was replaced, and a wrong-column ranking number. v7 was released as
  "base for candidates" before its verdict and then failed it. The B builder report has untraceable numbers (§1).
  VERSIONS.md was left stale and there was no decisions.md.
- **What each run's best bot is, by its own judgment:** A: v10 = v8 + AA/KK call floor. It is level with v3 at 8
  players (+0.09 ± 0.23 over 4,800 paired tables) and identical heads-up, and has had a bughunter and a quick
  tester. A's own tests say nothing it released beat v3 at 8 players. B: v4 = design D. Against v3 it measured +3.16 ± 0.37 heads-up,
  +0.85 ± 0.49 mixed and +0.57 ± 0.40 wide, but −2.21 ± 0.19 in the shove field. It is nondeterministic and carries
  the quads crash and over-1 ms equity (fixed only in the unreleased `candidates/D/build/D.zip` 4da29577).

**Inbox and Monitor expiries.** Both: every clock line woke the session within seconds, every expired inbox Monitor
was re-armed in the same turn, and no line was lost. A: the builder's file-watcher Monitor expired at minute 32 and
was not re-armed. RESEARCH wrote and restarted its own file watcher 3 times. Long clock lines arrived cut off.
RESEARCH overran the stop because no clock line woke it. B: Monitors expired twice per session and were re-armed;
both sessions stopped theirs on the 07:12 HOLD and re-armed at 15:07. B's research handled b20/b30/b40 sensibly
with no practice data (no spawn), but its PLAN file stopped at minute 27.

**Subagents and machine load.** A: about 32 subagents (BUILDER about 16: two or more platform runs, A/B/C/D, 9
bughunters, 1 tester; RESEARCH 16). There were five unrelated sessions on the laptop. Load reached 17-19 on 15 cores
at minute 8 and 7-10 after RESEARCH cut workers. B: about 28 (BUILDER 15: platform-core, platform-tools, A/B/C/D, 7
bughunters, 2 release-only runs; RESEARCH 13), and no unrelated sessions are recorded. Load was 14-24 (22-26 at
minutes 14-17) and 5-10 after minute 26. B's peak load was higher than A's despite less background work, so the
load came from the team's own agents in both runs. The guard hook refused 14 commands in A and 17 in B (mostly
`sleep 20` polls).

## 4. Bundle defects reported by either run (merged), and whether the current bundle still has them

Checked against `/Users/dylan/Documents/GitHub/nolimit-hub/finals_pack/` as of 16:20 (commits to 15:55). "Partly"
means the text was touched but the failure can still happen.

| # | Defect | Run | Still in current bundle |
|---|---|---|---|
| 1 | One `platform` run does rules card, v1, harness and packer in sequence; nothing can be packed before the packer (styles legal at 16-29) | both | **yes** (BUILDER.md:89-91 now states the figures; the minute-0 brief still spawns one platform with the harness "by 15", no packer target) |
| 2 | No "style is live" check: a base that never calls the hooks passes pack/check as check-fold; hook-error counters and failed style imports are silent | B | **yes** (platform.md checks 1-9 have no hook-firing minimum) |
| 3 | Several bots in one process share module names; neither the harness nor the rig is required to isolate them or prove two zips act differently | B | **yes** (platform.md:40 "any mix of bots", no isolation rule) |
| 4 | Warm Modal containers keep old code after a redeploy | both | **partly** (tester.md:57 says "redeploy after a change", which B showed is not enough: stop old containers, version-check each shard) |
| 5 | No lock or queue for concurrent `--modal` jobs (8 at once at minute 21) | B | **yes** |
| 6 | No rule on which platform commit a pick is packed on; a fix release became a base before its verdict (A v5/v6; B v7) | both | **yes** |
| 7 | Release numbers and release-only platform runs when platform is mid-build | both | **partly** (platform.md:3,15 allow parallel runs on their own files; vN is still "the next free", no worktree rule) |
| 8 | A withdrawn release stays as an uploadable `vN.zip` | A | **yes** |
| 9 | Tester verdicts reach VERSIONS.md only through platform (6 relays in A, one wrong for 9 min; never updated in B) | both | **yes** (platform.md:115-117) |
| 10 | Monte Carlo cut by the clock: FIRST_PROMPT says "iteration count and a deadline" | both | **partly** (platform.md:82,177 fixed; FIRST_PROMPT.md:118 unchanged) |
| 11 | Worker cap is per subagent (4), not per session; load 17-26 at minutes 6-17 in both runs | both | **yes** (CLAUDE.md:152 and every role file) |
| 12 | Monitor fallback is a shell sleep loop, which the hook refuses | A | no (e45805d) |
| 13 | "No sleep over 20 s" while the hook refuses 20 s | A | no (now "20 s or more") |
| 14 | Variant-load check before the kit's Python exists; portal name ≠ engine name | A | no (BUILDER.md:57-61) |
| 15 | Kit engine defaults to plain hold'em; only platform is told to set the variant | B | **partly** (platform.md:165 only; stylist, challenger, bughunter, tester files lack it) |
| 16 | Upload test cannot be run with the kit's CLI; platform and tester each wrote a runner | both | partly (tester.md fixed, a49db94; no single shared runner) |
| 17 | `state/live.json` holds one bot; the next pick waits for the current practice to start | A | **yes** (documented in BUILDER.md:96-98, no queue) |
| 18 | Interface stub due at 6 in BUILDER.md but at 12 in platform.md/stylist.md | both | no (2989779, 3ca4db9) |
| 19 | Stylist reads files that don't exist at minute 1; `STYLE_` settings rejected; build path mismatch | A | no (3ab1a39) |
| 20 | The draft keep/throw rule (TWIST_NOTES T2, variants.md) is a flop-draw rule, unlabelled | both | no (39ddbc2, d7b13cb) |
| 21 | "2.2-4.4 µs per deal" is about 5× optimistic once the simulated players' rule calls are counted | B | **yes** (theory.md:94; variants.md:209 has 9-57 µs) |
| 22 | Theory table schema changed without a note; `fallback: true` read as "reject" | A | no (eae5cc5) |
| 23 | Theory checks pass a table with wrong columns, with no data block, or a rule that breaks a full house | both | no (d3ceb80; theory.md:90-92) |
| 24 | Draw rule edited in place after "trusted"; no freeze or version on every change | both | no (a469365) |
| 25 | Twist recipe studies heads-up against random hands only | A | no (a469365) |
| 26 | Three theory runs write HANDOFF.md at once | A | no (1c3357f) |
| 27 | No routing for a bughunter's finding in theory's rule | A | no (076ac2f) |
| 28 | Kit README contradicts RULES.md on revealed cards | both | no (ee3b79b) |
| 29 | Broadcasting provisional numbers: relay a theory file's numbers only with its version, from a checked table | both | **yes** (BUILDER.md:100, RESEARCH.md "THEORY LANDED") |
| 30 | Nothing wakes RESEARCH when a table lands; CLAUDE.md allows "one Monitor" | A | **yes** (CLAUDE.md:30; no watcher script) |
| 31 | Long clock lines arrive cut off in the Monitor event | A | no (a190032) |
| 32 | Testers wait for the RELEASED message, though the zip and `[live]` line arrive first | both | **yes** (RESEARCH.md:103) |
| 33 | Who gives v1's verdict | A | no (521e96f) |
| 34 | No build-hour rehearsal of the edge and round-1 recommendation path | A | **yes** |
| 35 | Codex unusable on this laptop's key | A | no (8d45134) |
| 36 | 300-word subagent reports (actually 400-700) filled RESEARCH's context by minute 27 | A | **yes** (still 300 words) |
| 37 | `modal app stop` aborts without `--yes` | A | no for CLAUDE.md:96 and role files; guard.py:51,67 hints still omit `--yes` |
| 38 | Full hand-file name not given | A | no (1d7a355) |
| 39 | Hold'em jam/call priors (35-50% shove, ~37% call) stated for every variant | A | **yes** (PLAN.md, FIRST_PROMPT.md:183, 351) |
| 40 | Push/fold keyed by players left (should be players behind, call column by shover's seat); 169×169 needed | A | **yes** (FIRST_PROMPT.md:350) |
| 41 | Modal shard size (250 a shard is slow) | A | no (0484b84) |
| 42 | testplan.md: Modal image built only after v1's verdict | both | **yes** (testplan.md step 6) |
| 43 | Team Python has no `modal`; which interpreter | both | **partly** (tester.md, theory.md fixed; FIRST_PROMPT.md:470 still "check that modal imports first") |
| 44 | stat_definitions: heads-up big-blind rule, VPIP/PFR, bets logged as `raise`, draw statistics, depth band over 20bb | both | partly (f384b10 fixed the first three; draw statistics and the >20bb band still missing) |
| 45 | Analyst stage folder collision on dry runs | A | no (292f457) |
| 46 | Dry run writes to fixed `/tmp/dryrun/`, shared by parallel runs | B | **yes** (RESEARCH.md:94, analyst.md:153, LESSONS.md:214) |
| 47 | Leaks lens ranks on outcome against a fold, without card control | A | **yes** (FIRST_PROMPT.md:408-409) |
| 48 | analyst.md asks for the which-style paragraph at 50, RESEARCH.md at 40 | A | no (67b9df0) |
| 49 | DECISION_RULES: SE of the edge and the yardsticks' mean not defined | A | **yes** (DECISION_RULES.md:61-66) |
| 50 | Plan assumptions 2 and 4-7 have no measurable test; 7's fixed 2.0 ignores table count | both | **yes** (DECISION_RULES.md:242-250) |
| 51 | FINGERPRINTING: drift check without a minimum n, near-copies pass the "unknown" gate, filler class contradicts the kit, "alpha 10" ambiguous | both | **yes** (FINGERPRINTING.md:32,40) |
| 52 | A plan challenge raised on synthetic data | A | no (4d17a97) |
| 53 | Process pool leaves orphans when killed | A | no (b028ddf) |
| 54 | macOS: multiprocessing script without a `__main__` guard forks in a loop; no `timeout` command | B | **yes** |
| 55 | Tester verdict format: v1 baseline, heads-up scale | both | no (1b17758); B's extra points (`poker-agent check` needs the zip; name the heads-up opponents) **yes** |
| 56 | "Seven copies" per sparring field vs check_or_fold in every field | B | **yes** (testplan.md:56) |
| 57 | Replay "on Modal" vs "histories never leave this machine" | B | no (tester.md:59) |
| 58 | Rig reports max decision time, which spikes under load (should be p99.9, split by phase) | B | **yes** (tester.md:33) |
| 59 | Clock b20 text says "the first legal, upload-tested style", contradicting the pick rule | B | **yes** (timeline.json:91) |
| 60 | Clock b30 text states "Practice 1's data is in data/rounds/" as fact | B | **yes** (timeline.json:137) |
| 61 | Clock b40 tasks have no branch for "no practice data" | B | **yes** |
| 62 | Start-up reads ~1,300 lines before arming the inbox Monitor | B | **yes** (BUILDER.md:16-19) |
| 63 | No step for a clock reset before minute 0 | B | **yes** (BUILDER.md:175 covers only a stale clock) |
| 64 | Modal app ownership and names: "one app per purpose" vs "only two deployed apps"; no suffix for a concurrent run | B | **partly** (theory.md:114 names theory's app; CLAUDE.md:105 unchanged) |
| 65 | `buildplan.md` and `whatwins.md` not named in the minute-0 briefs | B | **yes** |
| 66 | theory.md tells theory to read `theory/NOTES.md`, which doesn't exist | B | **yes** (theory.md:12,16; `theory/` holds only `out/`) |
| 67 | Pre-notes merge into `notes/plan.md` runs only when a human says "start the research" | B | **yes** |
| 68 | Team Python named two ways (`starter-kit/.venv` and `.venv`) | B | yes (harmless) |
| 69 | Call-table check against a 50% shover is weak in this variant (50% ≈ equilibrium) | B | **yes** (FIRST_PROMPT.md:357) |
| 70 | One-pair defaults check uses showdown cards only; "55% of the pot" ambiguous | B | **yes** (FIRST_PROMPT.md:390) |
| 71 | Theory, analyst and scout idle after minute 12-19 with no practice data | both | **partly** (theory.md:137 for theory; nothing for analyst and scout) |
| 72 | One general bughunter per release misses the narrow bug; earlier tests not carried | A | **partly** (bughunter.md:20-21 re-runs earlier tests; no second, narrow bughunter) |
| 73 | All-in call path folds AA/KK when deep (found in both runs only by bughunters) | both | **yes** (no scripted check in platform.md or bughunter.md) |
| 74 | Undocumented hook refusals (`rm -rf` of one's own folder) | A | no (5fc5f0c) |
| 75 | Times written from memory; no `now.py` printing the time and build minute | A | **yes** (minor) |
| 76 | Other session not yet listed at start-up | A | no (acccdc5) |
| 77 | No minute-45 clock step (the speedrun's stop rule) | both | not a bundle defect: a speedrun brief mismatch |

Count: 77 items. 25 fixed ("no"), 12 partly fixed (#4, 7, 10, 15, 16, 37, 43, 44, 55, 64, 71, 72), 39 still
present ("yes"), and 1 not a bundle defect (#77).
The costliest still present: #2 and #3 (silent wrong measurement), #6 and #9 (pick packed on an unverified base,
stale verdict record), #11 (load), #29 and #32 (relays), #73 (AA fold).

## 5. How comparable the runs are

- **One run each.** Both runs' largest failures were single events: a late packer in A, a hookless base and an
  import collision in B. A rerun of either model would likely hit different ones. With one sample per model,
  differences of a few minutes or one or two releases are inside run-to-run variance.
- **Different conditions.** A ran at 06:27 with five unrelated sessions on the laptop. B ran at 15:14 after its
  sessions had sat idle for about 8 hours (07:12 HOLD for a usage limit, clock reset, minute 0 re-set at 15:07),
  which meant long contexts before the run began. B's research also had its minute-0 briefs drafted in advance,
  which saved about a minute. Load was not lighter in B: it peaked higher (22-26 against 17-19).
- **Same bundle snapshot (3f6078d) and the same kit**, so instruction differences are not a factor. Both ran at high
  effort.
- **B used about 40 of its 45 minutes, A about 44.** Part of A's lead in releases comes from those extra minutes (v8 and v10
  both landed after minute 37).
- **No real field.** Every strength number is sparring against the team's own bots, so "best bot" in either run is
  a guess about the real field. Notably, in both runs check_or_fold matched or beat every bot in self-busting fields.

**What can be concluded:** both models carried the bundle through a build hour with no humans. Both had a legal bot
by minute 6-9, every theory table by minute 16-29, three practice picks declared on time, zero failed decisions, and
real bugs found by their own bughunters. Neither model is unfit for tomorrow.

**What can't be concluded:** which model builds a stronger bot, which makes fewer silent errors, or which is faster
in general. The data supports "Opus started faster, Fable measured more and finished stronger" for these two runs
only. A head-to-head of the two best zips (below) tests the bots, not the models.

## 6. Best bots, for a head-to-head later

- Run A: `/Users/dylan/avalon-speedrun/releases/v10.zip` (sha256 089457a50e7759b5…, the run's round-1 answer).
  The fallback and the 8-player reference is `/Users/dylan/avalon-speedrun/releases/v3.zip` (bc558daac234de65…).
- Run B: `/Users/dylan/avalon-speedrun-b/releases/v4.zip` (design D, sha256 a5d23e6ce811af17…, both sessions'
  round-1 input). The base is `/Users/dylan/avalon-speedrun-b/releases/v5.zip` (10a3894ea5cefff0…). The fixed but
  unreleased D is `/Users/dylan/avalon-speedrun-b/candidates/D/build/D.zip` (4da2957791d317cb…).

All five sha256 values were re-hashed at 16:20 and match the runs' records. Play the variant `turn_draw_holdem`
explicitly, and load each zip in its own process: B showed in-process loading can run the wrong bot's code.
