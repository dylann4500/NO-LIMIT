# Speedrun C: RESEARCH session report (Saturday 14 November 2026)

Run: build hour only, mock variant `flop_auction_holdem` ("Boston": hold'em, the flop is bought in a sealed-bid
auction with 1,000 never-replenished flop-chips per table). Format today: 6 players, 6,000 chips, blinds and antes
10/20/4 rising every 20 hands, 250-hand cap, 1 ms per decision + 100 ms bank, 50/30/20. Minute 0 = **16:10:00**
(first set for 08:25, reset at 07:12 by the lead for the account's usage limit, set again at 15:07). Minute N =
16:10 + N. Stop ordered for 16:56 by `date`. No humans, no portal: every "practice round" below is a synthetic
stand-in under `/tmp/dryrun-c/` against the tester's sparring bots, so every strength number is **sparring-only
(grade C)**. All times are from `date`, file mtimes or the inbox's own stamps.

Sources: `notes/PLAN-research.md` (my running log), the subagents' final reports, `theory/out/*.json`,
`rig/out/*-verdict.md`, `notes/LEDGER.md` (149 lines at 16:53), `state/events.log`.

**In five lines.** (1) Every first-wave table reached BUILDER by minute 14, each first as a labelled fallback
(minute 6-11); the trusted twist rule and the call table were 4 minutes late (minute 19). (2) The rig ran at
minute 8 and covered all 14 releases: 11 full verdicts with a heads-up run in 2.7-7.7 minutes each, v13 as an extra arm,
v4 and v6 replaced before theirs. (3) The data path (card, leaks lens, field trend, refit, round-1 ranking) ran end to end three
times on synthetic rounds, in under a minute per round. (4) The biggest losses were mine (a stale Format page in
the briefs, a compaction pause) and Modal's (warm containers serving old files, shared-app queueing). (5) The
rig cannot price rare-line bugs: BUILDER's bughunters found four that scored level or better against sparring.

## 1. Milestones

Targets are from `prompts/RESEARCH.md` (build-hour section, lines 75-77 for theory) and `strategy/PLAN.md`.

| Target | Target minute | Landed (`date` / mtime) | Minute | How I checked it |
|---|---|---|---|---|
| Six agents spawned in one message (theory x3, tester, analyst, scout) + my file watcher | m0 | 16:11 (woken 16:10:05) | 1 | spawn results; all six reported files by m6 |
| Rules card check (`rig/out/rules-check.md`) | m5 | 16:14:55 | 4.9 | opened: 23 fields, every one MATCH against the kit and the Format page |
| `ranking.json` fallback (heads-up, 20k deals/class) | m7 | 16:15:53 | 5.9 | opened headline and inputs |
| `ranking.json` full (1-5 opponents, 100k deals/class) | m10 | 16:18:40 (v2); v3 16:26:28 (`order_by_state`); **v4 16:41:05, first not-fallback** | 8.7 / 31 | checks block: combo-weighted mean 50.0 at every size; plain hold'em AA 85.2, 22 50.6 within 1 SE of known values; evaluator 0 mismatches vs eval7 on 90,000 hands. Labelled fallback until v4 only because bids used the first-guess rule |
| `icm_thresholds.json` | m10 | 16:17:19 (v2 16:29) | 7.3 | re-derived the 3-equal-stacks break-even 57.14% by hand; heads-up equals pot odds to 1e-15; matches the engine's `scoring.equity` to 1e-14 |
| `pushfold.json` fallback (plain hold'em equities) | m15 | 16:16:32 | 6.5 | opened |
| `pushfold.json` with auction equities | m15 | 16:22:28 (v2); v4 16:35 (shove-width columns 2 and 5 added by the refit) | 12.5 | equity matrix mean 50.0, AA 74.86 vs ranking's 74.75; converged (best-response gain under 0.005bb); plain hold'em heads-up 10bb check 58.2% jam / 37.5% call |
| `exploit.json` (break-evens with antes) | m15 | 16:18:16 (v2 16:26) | 8.3 | re-derived the 2bb button open cell by hand (needs 42.55% folds); pot-bet and half-pot cells exact |
| `twist_rule.json` fallback (first-guess rule) | m12 | 16:20:43 | 10.7 | opened: 10 test vectors, loss 1.30 ± 0.06 pot-share points vs the simulated best flop |
| `twist.json` (option values) | m15 | 16:21:31 (v4 16:34) | 11.5 | checks: mean pot share over all flops 0.502, symmetric contest 0.50 at every bid size |
| `twist_rule.json` final, not fallback | m15 | **16:28:58 (v2.1), 4 minutes late**; v2.3 16:34 (size doubled after engine runs) | 19.0 | checks: 4,000 random calls legal, hole-order and suit-relabel invariant, loss 0.5 ± 0.05; fallback covered m10.7-m19 |
| `pushfold_vs_call.json` (call tables) | m15 | 16:29:05 (v3 16:31, v4 16:35) | 19.1, 4 late | 3,780 cells, rates in 0-100; explains the 99% ICM jam as fragile to the call rate |
| `theory/HANDOFF.md` | m20 | 16:23:55 (last update 16:38) | 13.9 | sections for all 7 first-wave tables; lookups named |
| Wave 2: `multiway.json` | after m12 | 16:21:49 | 11.8 | within 1.0 point of ranking.json |
| Wave 2: `twist_budget`, `twist_reveal`, `twist_betting` | after m12 | 16:29:05; `twist_betting` engine run 16:31:43; v5 16:39 | 19-21 | pot share all = 0.498; engine: rule v2 21.5 points per table, first guess 18.4, never bid 10.1 (SE 0.9, 240 tables) |
| Extras: `nested_confirm.json`, `bid_sensitivity.json` | - | 16:24:19 / 16:24:31 | 14 | headlines read |
| Theory refit from practice 1 (clock b30) | m30 | 16:34:41 rehearsal on the stand-in (`refit_practice1_synthetic.json`, `theory/refit.py`) | 24.7 | 16 required keys present, stops loudly on a missing key; produced pushfold v4 |
| Rig: `rig/compare.py` (paired, seat rotation, sparring that bids) | m15 | 16:18:04; `rig/NOTES.md` 16:21:07 | 8.1 | first noise run on the right rules at 16:18 |
| Modal throughput measured | after rig | 16:20:25 | 10.4 | log: 6,000 table-plays in 36.7 s = 163 tables/s on 40 containers, first result after 12.7 s |
| First verdict on v1 (clock b15) | m15 | 16:24:55 preliminary; **16:28:49 final with the heads-up run** | 14.9 / 18.8 | read: v1 = the floor (16.82 ± 0.14 six-handed over 10,000 tables, 30.07 heads-up over 4,000); 0 failed of 1,995,279. v1 itself was released at 16:21:28 (m11.5) |
| Round-card script (`analysis/parse.py`, `analysis/roundcard.py`) | m25 | 16:16:17 / 16:18:31 | 8.6 | I re-ran it with the team Python `-I` on the kit sample: card in under 2 s; 0.2 s on 24 tables, 1.46 s on 200, 8.5 s on 1,008 |
| Dry-run download (analyst, about m10) | m10 | 16:21:48 card, 16:22:04 field trend | 12 | 24 synthetic tables of 6 with v1 as us; card = direct count |
| Stand-in practice 1 -> card -> leaks lens (clock b20) | card 3 min and top change 5 min after data | round 16:28:39, card 16:28:45, `lens-leaks.md` 16:31 | 18.7-21 | card = direct count = kit summary (v2 37.05 ± 1.20); LEDGER L51 `one-change Practice 1 (synthetic)` |
| `analysis/fp_train.py`, `analysis/field_trend.py`, `counters.json` skeleton | m25 | 16:21:40 / 16:18:58 / 16:24:04 | 9-14 | files; scout: 4 direct counts match, analyst's parser agrees on 5 rows |
| Field-trend path, one stage | m25-30 | 16:31-16:32 on stand-in practice 1 | 22 | fp_train 0.8 s, field_trend 0.6 s (2.9 / 2.4 s on 1,008 tables) |
| Field-trend path, two stages with cross-round matching (clock b30) | m33-35 | 16:40-16:41 on stand-in practices 1 and 2 | 31 | scout: drift check flagged only our own bot (v2 -> v5), 8 yardsticks of 10; recogniser 66% lagged at 20 hands, 79% same-round |
| Stand-in practice 2 -> card -> leaks | 5 min after data | data 16:39:04, card 16:39:14 (1.28 s), leaks 16:39:59 | 29-30 | 55 s from data to the leaks lens; v5 36.80 ± 1.36 |
| A verdict per release | on release | minutes from the zip to a verdict line with a strength number: v2 7.7; v3 5.5; v5 4.8; v7 5.0; v8 4.4; v9 2.7; v10 5.2; v11 3.9; v12 3.7 (see section 6) | - | line 1 of each `rig/out/vN-verdict.md` read before sending |
| BUILDER's A/B/C question (asked 16:30 for 16:45) | m35 | interim 16:35:51, final 16:41:50 | 25.9 | read `rig/out/abc-head.md`; BUILDER picked B for practice 3 from it at 16:40 |
| Style paragraph (clock b40, analyst task) | m50 | 16:49:45 | 39.8 | from the testers' paired numbers; sparring-only order C (v10) > A on v8 (v12) > base > B (v9) > D2 (v7) |
| Round-1 ranking against the yardsticks (clock b40, tester task) | m50 | 16:50:54 file, sent 16:51:30 | 41.5 | read the analyst's sentence; three bots not separated |

Nothing in the first wave missed its target except the trusted twist rule and the call table (both m19 against
m15), and in both cases a labelled fallback was in BUILDER's hands from m6.5-m10.7.

## 2. What slowed or blocked us, by minutes lost

| Minutes | Who | What |
|---|---|---|
| about 12 | theory-1 (ranking) | Warm Modal containers served old files after a redeploy (3); the ranking run on the real bid rule took 12 minutes, not 4 (8); two evaluator bugs and a numba cache name clash (1). This is why the not-fallback ranking came at m31 |
| about 8.7 | theory-2 (twist) | 4.7 minutes because one of its helper agents ran in the foreground; 4 minutes in BUILDER's "nothing heavy locally" window (16:24-16:28) |
| about 5 | first tester | An oversized 30,000-table v1 run with the slow "caller" sparring field; plus the quiet window and the load burst |
| about 6 | scout | The wrong Format in my brief (below) plus the CPU window |
| about 4 | v5 tester | My retarget from v4 to v5 (v5 replaced v4 100 s after release) cost two restarts; its mix job then took 181 s instead of 68 s on the shared 40 containers |
| about 3 | v2 tester | Queued on Modal behind the first tester's jobs (196 s against 44 s alone) |
| about 2.5 | me | Context compaction at about 16:34-16:36: v6's release (16:33:56) waited 2.5 minutes for its tester |
| about 2 | me, then every agent for 1-2 minutes | **My error:** my briefs carried the Format page as I read it at 06:28 (8 players, 2,000 chips, no antes). The page was rewritten at 15:26 (6 players, 6,000 chips, antes) and I did not re-read it at b0 although the b0 step says "Read the Format page". Caught at 16:12 from BUILDER's b0 message; brief corrected and all six agents told by 16:13 |
| about 2 | theory-3 | Stale Modal container after its own redeploy of the shared `avalon-theory` app |
| about 2 | A/B/C tester | zsh not splitting a variable; a relative history path |
| about 2 | v7 tester | `rig/compare.py` keeps no per-table points, so v7 against v5 needed two more Modal runs with v5 as the baseline |
| about 1 | v8 tester | My retarget from v6 to v8; and `theory/out/ranking.json` changed mid-run, so two of its pairings ran on different sparring play |
| about 1 | analyst | The Format correction |
| 2 commands | me | The guard hook refused two commands whose quoted text contained "until" and a pause word (section 3) |
| not counted | everyone | Load 34.5 on 15 cores at 16:23:22 (macOS daemons plus other sessions): timing tests in that minute were declared inconclusive and v1's was re-run at load 6.3 |

Structural, not minutes: **releases arrived faster than verdicts.** Ten releases in 20 minutes (v1 16:21:28 to
v10 16:40:49; v6-v10 in 7 minutes) against 4.4-7.7 minutes per verdict on a shared 40-container app. Twice a
release was replaced before its verdict (v4 by v5 after 100 s, v6 by v8 after 3.7 min); I retargeted the running
tester instead of spawning another, which worked but cost the v5 tester two restarts.

## 3. Where the bundle's instructions were wrong, unclear, missing or contradictory

| # | File and line | Problem | Exact fix |
|---|---|---|---|
| 1 | `prompts/RESEARCH.md:20` | Says to run "the Monitor tool"; in this app `Monitor`, `SendMessage` and `TaskStop` are deferred tools that must first be loaded with `ToolSearch` | Add: "If Monitor / SendMessage / TaskStop are listed as deferred, load them first: ToolSearch `select:Monitor,SendMessage,TaskStop`" |
| 2 | `scripts/guard.py:32` | The loop pattern (the word while or until, then anything, then the word sleep, on one line) matches prose: two of my commands were refused (07:12, 07:14) because a quoted note contained "until" and later a pause word. Subagents hit it too | Match `while`/`until` only at a command position (start of line or after a semicolon, ampersand, pipe or opening bracket) and strip quoted strings and heredoc bodies first |
| 3 | `scripts/guard.py` help text vs `CLAUDE.md` §4.7 vs `.claude/agents/theory.md` | CLAUDE.md and theory.md say "no `sleep` over 20 s"; the hook refuses exactly 20 and says "20 s or more". Two short pauses chained in one command are refused as well | One wording everywhere: "a pause of 20 s or more, or two pauses in one command, is refused" |
| 4 | `CLAUDE.md` §4.7 and the role files | The no-wait rule gives a subagent no stated way to wait for its own background job (theory-1, v5 tester). A main session is woken by notifications; a subagent is not told what to do | Add to each role file: "To wait for your own job: start it with `run_in_background`, do other work, you are notified when it exits; never chain pauses" |
| 5 | `scripts/clock.py` (the b-step texts; step b0, b20, b30) | The Monitor notification truncates long inbox lines ("...(truncated)"): every clock step arrived cut and had to be re-read from `inbox/research.log` | Keep each clock line under about 400 characters, or put the task list on following lines (`feed.py` prints one event per line) |
| 6 | `scripts/clock.py`, build-hour steps | There is no b45 step although the speedrun brief told both sessions to stop "at the b45 step"; the lead had to send the stop time by hand | Either add a b45 line or brief the stop as a time |
| 7 | `scripts/clock.py` b20 / b30 texts | b20 says practice 1's data "lands about minute 25", b30 says "about minute 33-35" and "Practice 1's data is in data/rounds/": the two steps disagree with each other by 8-10 minutes for the same kind of event | State one lag (play time + N minutes) in both |
| 8 | `.claude/agents/tester.md:38`, `notes/pre/testplan.md:52`, `strategy/FIRST_PROMPT.md:451` | "seven copies" of each sparring bot assumes 8 players per table | "players − 1 copies (from the rules card)" |
| 9 | `.claude/agents/theory.md` (Python section) and `CLAUDE.md` §3 (team Python row) | The team Python has no `modal`; nobody says the Modal CLI's own Python (or system `python3`) must launch Modal jobs | Add: "`starter-kit/.venv` has no `modal`: launch Modal with the `modal` CLI, and build the image from the kit's requirements" |
| 10 | `.claude/agents/theory.md` (hands per table) | Says 120-140 hands per table; measured 163-174 today (6 players, 6,000 chips, antes) | "Measure hands per table in the first engine run; never assume" |
| 11 | `.claude/agents/analyst.md:89` | Players-left buckets "6-8, 4-5, 2-3" assume 8 seats; with 6 the top bucket is one value | Derive the buckets from the rules card |
| 12 | `.claude/agents/analyst.md:35` and `:138` | "else `kit-sample`" is ambiguous about where the kit sample lives and what the output folder is called when there is no `NN-` round folder | Name the path (`starter-kit/hand-history/`) and the output folder for it |
| 13 | `.claude/agents/scout.md:33-37` | Never says how `fp_train.py` finds the earlier stage or how teams are matched across rounds; the scout chose "the latest lower-numbered `NN-` folder already analysed, never a test folder; match by team name" | Write that rule into the role file |
| 14 | `notes/pre/stat_definitions.md` line 9 | The default mean filters on "PFR 3%+" before PFR is defined | Define PFR above it |
| 15 | `notes/pre/stat_definitions.md` lines 18, 26, 29, 49 and the rows "Big blind folds to an open", "Collisions before hand 40" | Which big blind sets the stack depth; whether a small-blind complete is a limp; whether an iso-raise over limpers is an open; line 49's heads-up rule ("the big blind was the seat of the last blind posted") is WRONG for this kit: heads-up the engine posts the big blind first and the button (small blind) posts last | State each choice; replace line 49 with "the big blind is the seat that posted the larger blind" (what D2 and the platform now do) |
| 16 | `notes/pre/testplan.md:14` (step 6) | "Only then the Modal image build": the deploy took 13 s and the first tester needed Modal before step 4-5 finished | Move the deploy to step 1, in the background |
| 17 | `notes/pre/testplan.md:12` (step 4) | "four hold'em-style fields now": skipped today, the variant-aware field was ready at m8; the plan has no slow-field warning (the "caller" field cost 100 s per 600 tables) and no warning that Modal's timing columns are not a timing test (23 would-be timeouts on throttled CPUs) | Add both warnings; make step 4 optional |
| 18 | `notes/pre/field.md:82`, `strategy/DECISION_RULES.md:240` | "Scores compress near 12.5" is the 8-player par; today's par is 16.67 six-handed and 40 heads-up | "par = 100 / players" |
| 19 | `strategy/TWIST_NOTES.md` T13 | Its budget "balance ÷ auctions remaining" ran winners dry in 44% of tables in the engine | Replace with "size by the pot: balance × pot / (k × total chips), cap half the balance; fit k on the engine" |
| 20 | `CLAUDE.md` §7 (CPU) / BUILDER's quiet-window request | "Nothing heavy locally 16:24-16:28" did not say whether Modal clients (one process each) count; two agents stopped altogether | "Modal clients are fine; no local match or Monte Carlo runs" |
| 21 | `prompts/RESEARCH.md` (a fresh tester per release) vs release cadence | One fresh tester per release assumes releases minutes apart; today five came in 7 minutes on one 40-container app | Add: "a release that replaces one whose verdict is not out: retarget the running tester, keep the old release as an extra paired arm" and "at most 1,000 tables per job while another tester is running" |
| 22 | `prompts/RESEARCH.md` (act on "RELEASED") | The `releases/VERSIONS.md` line and the zip precede BUILDER's RELEASED message by 20-80 s, and the `[live]` inbox line can come first too | "Spawn the tester on the VERSIONS.md line (watch the file); the message is the confirmation" |
| 23 | `prompts/RESEARCH.md:77` ("As each lands, SendMessage BUILDER one line") | Subagents report only at the end, so "as each lands" needs a file watcher that the bundle does not provide; I wrote one (scratchpad `watch.py`, 3 s poll on `theory/out/`, `releases/`, `rig/out/*.md`) | Ship `scripts/watch_files.py` and say to run it under a second Monitor |
| 24 | `rig/compare.py` (written today, for `tester.md`'s spec) | Saves no per-table points, so two runs on the same seeds cannot be paired afterwards | Spec: "save per-table points per bot" |
| 25 | `.claude/agents/tester.md` vs my briefs | The role file wants verdicts appended to `rig/NOTES.md`; I asked for `rig/out/vN-verdict.md` with the verdict in line 1 (that worked better for forwarding) | Make `rig/out/vN-verdict.md`, verdict sentence in line 1, the standard |
| 26 | Stylists' packing (BUILDER side; found by the A/B/C tester) | Candidate zips were repacked in place during testing (C three times: its packings fold 18 / 33 / 48% to a flop bet) | "A candidate zip is never overwritten: new sha, new file name; every pick names its sha256" |
| 27 | Scratchpad | Shared by all subagents of a session: pid files of different agents mix; the hook also refuses recursive deletes there, which no brief says | One sub-folder per agent, stated in the briefs |
| 28 | `theory/out/` | A scratch file (`ranking_v2_pending.json`) appeared among the tables | "Only finished tables in `theory/out/`; work files in `theory/cache/`" |
| 29 | `.claude/agents/tester.md` (heads-up run) and my v7 brief | A heads-up run against the sparring mix cannot show a heads-up fix (v7's fix read as −0.32 ± 0.28 against the mix, about +1.2 ± 0.4 directly against v5) | "For a heads-up change also run `--field live --players 2` (head to head against the live bot)" |
| 30 | `.claude/agents/theory.md` / `theory/HANDOFF.md` format | A table re-issue that changes a constant its readers hard-code is not flagged: rule v2.1 -> v2.3 halved the budget constant (0.6 -> 0.3 × 36,000) and the platform's reveal-shift code kept 0.6, so v8-v13 read opponents' payments 1-2 buckets too high (BUILDER's bughunter, LEDGER L120) | HANDOFF gets a "CHANGED CONSTANTS" line per re-issue, and every table carries the constants its readers need (`normal_payment(...)` as data, never re-derived in bot code) |
| 31 | `.claude/agents/scout.md` (field trend rows) | A field-rate row can move because OUR bot changed: between the two stand-in rounds the unchanged sparring bots' "fold to bets" moved −11/−16/−19 points and "fold to 3-bets" 46.0 -> 39.4 only because they faced v5 instead of v2 | Compute field rates on pots we are not in (or say "vs us" and "vs others" separately) before calling a movement a trend |
| 32 | `releases/VERSIONS.md` lines 7 and 12 (platform) | Memory figures do not match the testers' (769 B vs 873-903 B; 1,031 B vs 1,318 B); harmless against 65,536 | Take the figure from the same run as the verdict, or drop it |
| 33 | `CLAUDE.md` §4.6 and §4.8, role files (`modal app stop <id>`) | Without a terminal `modal app stop <id>` asks "Are you sure" and aborts; my first stop at 16:55:07 did nothing | Write `modal app stop -y <id>` everywhere |

## 4. Did the Saturday drafts help or mislead?

- **`notes/pre/variants.md` §4 (the drill recipe for a new twist): helped.** Theory-2 followed it: step 1 at
  16:13, step 2 at 16:13:47 (50,000 deals in 0.34 s), the fallback rule at 16:20:39 (minute 10.6), `twist.json`
  at 16:21, the first trusted rule at 16:29 (minute 19). Its verdict: "the recipe helped, especially stored
  spots". Theory-1: the recipe's "time first" held (169 classes × 20,000 deals in 5 s). Against the drills'
  7.4 / 15.5 minutes, today's 10.7 / 19 were slower by about 3.5 minutes, and that gap is the foreground helper
  (4.7 min) and the quiet window, not the recipe. Theory-3 never opened it and did not need it.
- **`strategy/TWIST_NOTES.md` auction entries (T13): half right, and one line misled.** Right: pairs lose value
  (T13 said 22 ranks about 118th; today 143rd-152nd) and the points ladder matched ours, so the ranking's shape was
  no surprise and the checks were faster. Missing: nothing on all-in equity compression (AA 75% heads-up, not 85%),
  nothing on a seat with zero balance (it loses 100+ bb/100 heads-up), nothing on reading the opponent's payment
  after the auction (worth +2.0 ± 0.5 points per table). **Misled:** the "balance ÷ auctions remaining" budget ran
  winners dry in 44% of tables; the fitted rule sizes by the pot instead. Net: the twist table was a little faster
  to check, not better, and one of its rules had to be thrown away.
- **`notes/pre/testplan.md`: usable as written, with two edits.** The first tester followed it and had the rig at
  m8.1; its expected spread (19 points) and the floor warning were right. Wrong today: step 6's "only then" Modal
  (it was needed first), "seven copies", step 4's hold'em-first fields (skipped). Later testers did not use it:
  they copied the previous verdict file and its probes, which was faster.
- **`notes/pre/stat_definitions.md`: usable only with guesses.** It helped: analyst's and scout's independent
  parsers agreed on 5 rows and on 4 direct counts. It misled once (line 49, heads-up blinds) and needed guesses
  on six definitions (section 3, rows 14-15).
- **`notes/pre/field.md` §3 thresholds helped** the scout set the field-trend rows; its 12.5 par misleads at 6
  players.

## 5. Did the inbox work?

Yes for waking: every line woke me within about 5 s through the Monitor. Two weaknesses: long lines arrive
truncated, and the first-wave work never depends on the clock (four of five steps asked for things already done).

**Clock steps and inbox lines**

| Line | Posted | Acted | What I did |
|---|---|---|---|
| minute 0 set: 08:25 | 06:27:17 | 06:28 | Monitor armed, PLAN file written |
| clock reset | 07:12:25 | 07:12 | not mine; did not restart it; asked BUILDER; HOLD from the lead 07:13; Monitor stopped 07:14 on its instruction |
| minute 0 set: 16:10 | 15:07:08 | 15:07:20 | Monitor re-armed; it replayed this line from its saved position |
| b0 | 16:10:00 | 16:10:05 woken; six agents + watcher launched 16:11 | Text truncated in the notification |
| [live] v1 | 16:21:28 | 16:21:37 | tester told (verdict now), analyst told (dry-run); BUILDER's RELEASED message came 16:21:50 |
| [live] v2 | 16:24:19 | 16:24:20 | a fresh tester was already spawned off the VERSIONS.md line (16:24:10) |
| b15 | 16:25:00 | already done | rig ran from 16:18; v1's preliminary verdict sent 16:25:05, final 16:29 |
| b20 | 16:30:00 | 16:30 | no portal, no DATA LANDED: the analyst had been building the stand-in practice 1 since 16:26; card 16:28:45, leaks 16:31 |
| [live] v5 | 16:33:29 | 16:33 | the v4 tester retargeted to v5 |
| b30 | 16:40:00 | 16:38 (two minutes early) and 16:40:05 | refit rehearsal had landed 16:34:41; analyst and scout resumed 16:38 on a stand-in practice 2; both reported by 16:41 |
| [live] v9 | 16:41:26 | already done | v9's tester had been running since about 16:41:05 off the watcher |
| b40 | 16:50:00 | 16:49:45 (15 s early) and 16:50:30 | Its analyst task (which style was rewarded, one paragraph by minute 50) was sent to BUILDER at 16:49:45 from the testers' paired numbers. Its tester task (rank the practice bots against the yardsticks for the round-1 live bot): analyst resumed 16:50:30, stand-in practice 3 built by 16:50:48, ranking 16:50:54, sent to BUILDER 16:51:30. Both 8-10 minutes before the step's own deadline (minute 50 = 17:00, after the ordered stop) |
| [live] v14 | 16:50:12 | already done | v14's tester had been running since 16:48:40 off the watcher |

Releases I acted on from the file watcher, before any message: v2 (16:24:10 -> 16:24:20), v3 (16:30:40 -> 16:31),
v4 (16:31:31 -> 16:32), v5 (16:33:11 -> 16:33), v6 (16:33:59 -> 16:36:30, late: compaction), v7 (16:36:56 ->
16:37:05), v8 (16:37:38 -> 16:38, retarget), v9 and v10 (16:40:44-49 -> about 16:41:05), v12 (16:43:28 -> 16:44:50),
v13 (16:44:48 -> added as an arm 16:45), v11 (16:46:36 -> about 16:46:50), v14 (16:48:30 -> 16:48:40). BUILDER's
RELEASED message arrived 20-80 s after each zip; a tester was already running every time.

**Monitor expiries and re-arms**

| When | Event |
|---|---|
| 06:28:20 | armed (task b6nao60tk) |
| 06:58:23 | expired (30 min, 0 events); re-armed in the same turn |
| 07:14 | stopped with TaskStop on the lead's HOLD (no Monitor armed 07:14-15:07) |
| 15:07:20 | re-armed on "new minute 0 = 16:10" (bv2m9vi3g); replayed the 15:07:08 line at once |
| 15:37:25 | expired (1 event); re-armed in the same turn (by5pf6uw3) |
| 16:07:27 | expired (0 events); re-armed in the same turn (b1abojabv); load 4.4 |
| 16:37:27 | expired (6 events); re-armed 16:37:30 (bund81huy); b30 at 16:40:00 arrived on it |
| 16:53:30 | the file-watcher Monitor (bbgcv21it, armed 16:23) expired after 30 min and 111 events; not re-armed, 2.5 minutes before the stop |
| 16:55:10 | inbox Monitor stopped with TaskStop at the ordered stop |

No inbox line was lost across an expiry: `feed.py` keeps its position, and each re-arm took 3 s or less. The
second Monitor (my file watcher) was restarted twice to tighten its filter (it first announced every code edit).

Session-to-session: about 50 messages to BUILDER by 16:53 (51 `say.py --record` copies in `state/events.log`), 16 recorded
from it; all delivered at once, none lost. One of mine had to be corrected two minutes later (v11 vs v13: I
sent a two-seed "nothing measurable" at 16:50; a third seed made it −0.36 ± 0.15, corrected 16:52): provisional
lines should say how many seeds are still running. BUILDER's requests and my answers: A/B/C question asked 16:30 for 16:45, answered
16:36 (interim) and 16:42 (final); verdict priority (16:35) passed to the testers within a minute.

## 6. State at the stop

**Theory tables in `theory/out/`** (all three theory agents finished by 16:43; nothing running)

| Table | Version at the stop | Fallback? | Checks that passed |
|---|---|---|---|
| `ranking.json` | v4, 16:41 | no (bids from the shipped rule) | combo-weighted mean 49.989 (want 50.0); plain hold'em AA 85.20, 72o 34.73, 22 50.64, AKs 67.22 within 1 SE of known values; evaluator 0 mismatches vs eval7 on 90,000 hands. 3+ opponent columns ± 1 point (the rule moved to v2.3 mid-run) |
| `icm_thresholds.json` | v2, 16:29 (re-issued 16:40) | no | heads-up = pot odds to 1e-15; equal stacks 50.0 / 57.14 / 65.22 / 60.61 / 58.14% for 2-6 left; matches the engine's `scoring.equity` to 1e-14; I re-derived 57.14 by hand |
| `pushfold.json` | v4, 16:35 | labelled fallback (ranges solved on the first-guess bid rule, not v2.3); converged | best-response gain under 0.005bb (chip) / 0.01 points (ICM); equity matrix mean 50.0; plain hold'em heads-up 10bb 58.2% jam / 37.5% call as expected; call column +1.51 ± 0.19 bb/100 vs a 50% shover |
| `pushfold_vs_call.json` | v4, 16:35 | labelled fallback (same reason) | 3,780 cells, all rates in 0-100; 4-left ICM button 10bb jam 100 / 92 / 13 / 7% at call rates 5 / 10 / 20 / 30% |
| `exploit.json` | v2, 16:26 | no | pot-bet 50%, half-pot 33.3% exact; 2bb button open with antes needs 42.55% folds (I re-derived it) |
| `twist.json` | v4, 16:34 | no | mean pot share over all flops 0.502; symmetric contest 0.50 at every bid size; max SE 0.004 |
| `twist_rule.json` | v2.3, 16:36 | no | 4,000 random calls legal; hole-order and suit-relabel invariant; auction-order equivariant in 89%; 10 test vectors; flop choice loses 0.5 ± 0.05 pot-share points to a simulated choice |
| `twist_budget.json` | v2, 16:34 | no | symmetric contest 0.498; three-way symmetric 0.331; doubling the 16:29 size +2.5 ± 0.7 points per table, four times no better |
| `twist_reveal.json` | v1, 16:34 | no | pot share over all cells 0.498 (naive flop equity 0.603) |
| `twist_betting.json` | v5, 16:39 | no | engine: rule v2 21.5 points per table, first guess 18.4, never bid 10.1 (240 tables, SE 0.9); post-auction rules +2.0 ± 0.5 (1,200 tables) |
| `multiway.json` | v1, 16:21 (re-issued 16:41) | labelled fallback (first-guess rule) | width-100 mean × (k+1)/2 = 49.95-49.99; within 0.23 mean / 1.02 max points of ranking.json |
| `nested_confirm.json`, `bid_sensitivity.json` | v1, 16:24 | evidence files | nested re-run of 18 classes within 0.79 points of ranking.json |
| `refit_practice1_synthetic.json` | v2, 16:35 | path test on the stand-in, not the field | 28 columns, 16 required keys present, 7 optional missing (listed in HANDOFF), all rates in 0-1 |

`theory/HANDOFF.md` last updated 16:38. Every strength claim in these tables is against sparring bots or in
all-in simulation; none is solved with a betting tree.

**Tester's verdicts** (all sparring-only, paired deals with seat rotation, the kit's `check_or_fold` floor in the
same tables: about 23.0 six-handed, 30.05 heads-up)

| Release | What | Verdict (time from release) | Failed decisions | Six-handed (n paired tables) | Heads-up (n) |
|---|---|---|---|---|---|
| v1 | check-or-fold, zero bid | equals the floor; first legal bot (7.4 min, final) | 0 of 1,995,279 | 16.82 ± 0.14 pooled over five fields (10,000) | 30.07 (4,000) |
| v2 | design D, standalone | fit for a practice round only: heads-up button never raises (0 of 4,206) (7.7 min) | 0 | +13.27 ± 0.41 vs the floor (2,000) | +16.06 ± 0.18 vs the floor (2,000) |
| v3 | platform base | fit for a scored round (5.5 min) | 0 of 790,036 | +0.87 ± 0.46 vs v2 (2,000) | +1.16 ± 0.21 vs v2 (2,000) |
| v4 | style A, older style.py | superseded by v5 after 100 s; no verdict | 0 | +0.16 ± 0.48 vs v2 (2,000) | - |
| v5 | style A | **fit for a scored round; BUILDER's round-1 default** (4.8 min to the first heads-up number) | 0 of 701,978 | +1.23 ± 0.47 vs v2 (2,000) | +1.20 ± 0.21 vs v2 (2,000) |
| v6 | base + theory wave 2 | superseded by v8 after 3.7 min | 0 | +0.60 ± 0.35 vs v3 (1,000) | +0.10 ± 0.11 vs v3 (1,000) |
| v7 | D2 (D + heads-up fix) | fit on correctness, behind v5 everywhere (5.0 min) | 0 of 388,278 | −1.06 ± 0.66 vs v5 (1,000) | −1.40 ± 0.26 vs v5 (1,000); head to head −2.30 ± 0.38 |
| v8 | base + table wiring, rule v2.3 | fit for a scored round (4.4 min); two bugs found later by BUILDER's bughunter | 0 of 472,026 | +0.74 ± 0.42 vs v3; +0.52 ± 0.54 vs v5 (1,000) | +0.14 ± 0.13 vs v3; +0.28 ± 0.16 vs v5 (1,000) |
| v9 | style B on v8 (played "practice 3") | fit for a scored round (1.6 min provisional, 2.7 final line) | 0 of 460,860 | +0.30 ± 0.39 vs v5 (2,000) | +0.34 ± 0.12 vs v5 (2,000) |
| v10 | style C on v8 | fit for a scored round; flag: spends flop-chips fast (5.2 min) | 0 of 474,612 | **+1.74 ± 0.45 vs v5 (2,000; fresh deals alone +1.62 ± 0.62)** | +0.36 ± 0.17 vs v5 (2,000) |
| v11 | base, both v8 bugs fixed | fit for a scored round, "not shown as good as v13" (3.9 min to the line; final 16:51) | 0 of 525,716 | −0.36 ± 0.15 vs v13 (3,000; three seeds −0.07, −0.05, −0.95, each ± 0.27: they disagree, unsettled); +0.37 and +0.63 vs v5 (se 0.55) | −0.08 ± 0.06 vs v13 (1,000) |
| v12 | style A on v8 | fit for a scored round (3.7 min) | 0 of 451,998 | +1.23 ± 0.31 vs v5 (2,000, repeated) | +0.12 ± 0.09 vs v5 (2,000) |
| v13 | v8 code, refreshed tables | fit as a base (arm in v12's jobs) | 0 of 387,334 | +0.73 ± 0.43 vs v5 (2,000) | +0.10 ± 0.21 vs v5 (1,000) |
| v14 | style C on v11 (declared for "practice 4", round 1's challenger) | fit for a scored round; keeps v10's level within noise (1.5 min provisional, 4.0 final line) | 0 of 464,367 | −0.40 ± 0.27 vs v10 (2,000; seeds −0.79 and −0.01, each ± 0.38); about +1.35 vs v5 (derived, se about 0.5) | −0.05 ± 0.08 vs v10 (2,000) |
| A/B/C/D2/D3 | candidate zips, 16:30 packings | B furthest in behaviour (92 rate-points from A, 124 from D); nothing below the floor | 0 | vs v2: A +0.44 ± 0.47, B −1.05 ± 0.45, C +1.57 ± 0.43, D3 −0.70 ± 0.44 (2,000 each) | A +1.11, B +0.93, C +0.87, D3 +1.01 (all ± 0.21; 2,000 each) |

What the verdicts could not see: BUILDER's bughunters reproduced bugs in v8-v10/v12/v13 (payment bucket, one-pair
fold ignoring the price) and in style C (v10, v14) that cost nothing measurable against sparring, because the
sparring bots bet by theory's tables and seldom make small bets or raises. The rig measures legality, speed and
gross strength; it does not price rare-line bugs.

**Stand-in practice rounds** (200 tables each, sparring field): practice 1 with v2 37.05 ± 1.20; practice 2 with
v5 36.80 ± 1.36. Practice 3 with v9 37.52 ± 1.24 (built in 27 s, card 4 s
later). Yardstick-adjusted edges for the round-1 rule (`analysis/Practice-3/round1-ranking.md`): v9 +27.67 ± 1.33,
v2 +27.33, v5 +26.27 ± 1.44: not separated (z 0.18 and about 0.7). Three 200-table practices cannot rank these
bots; the paired rig carried every comparison.

**Measured Modal throughput** (`avalon-rig`, 40 containers): 6,000 table-plays in 36.7 s = 163-166 tables/s for
one job alone, first result after 12.7 s; 98 tables/s over five single-style fields (the "caller" field is slow);
with two to three testers sharing the app a 2,000-table job took 44-196 s. Local: 53 tables/s on 4 workers.
`avalon-theory` (20 containers): 169 classes × 20,000 deals in 5 s. Deploy 13 s.

**Decisions and challenges:** one PLAN CHALLENGE (Build: the twist is the largest edge; bid rule and post-auction
rules first-class in every style), recorded in `state/decisions.md` at 16:41 with BUILDER's agreement; the rule's
answer applied (no human). No other decision was RESEARCH's.

**Price of the base fix on sparring:** v11 − v13 = −0.36 ± 0.15 (3,000 tables) and v14 − v10 = −0.40 ± 0.27
(2,000): about −0.4 six-handed twice, small and probably real against opponents that bet honestly; heads-up nil.

**Where BUILDER stood at 16:53:** v14 declared for practice 4 (round 1's challenger), v5 the round-1 default.

**Still running at the stop: nothing.** All 19 subagent runs had reported by 16:53 (theory x3; analyst, three
runs; scout, two runs; eleven tester runs). No local job of ours in `ps` at 16:55. Modal: `avalon-theory`
(`ap-OeicVuBmfOIhfkiVmvRjMG`) stopped by its agent at 16:42; `avalon-rig` (`ap-xdnA8xzwdwlHPDoJQQJxPh`) stopped by
me at 16:55:13 with 0 containers running (`modal app list` shows both "stopped"). The inbox Monitor was stopped at
16:55:10; the file-watcher Monitor had expired at 16:53:30 and was not re-armed. The last inbox line was the
16:50:12 `[live] v14`; nothing arrived after it. Files written by this session outside the subagents' folders:
`notes/PLAN-research.md`, `notes/briefs/research-common.md`, this report, one entry in `state/decisions.md`, and a
pointer note in the shared notes folder. Nothing was committed to git (the task did not ask for it; hand
histories stayed under `/tmp/dryrun-c/`).

