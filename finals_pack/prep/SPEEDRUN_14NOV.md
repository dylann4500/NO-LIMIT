# Speedrun, 14 November 03:12-03:47: a timed build hour on an unseen variant

Two headless Claude Code sessions (Opus 5.5, high effort) ran this bundle on a mock variant (flop pass: every player passes a hole card to the left after the flop), no portal, no humans. Both sessions' own reports follow. Their fixes are folded into the bundle (CLAUDE.md, prompts, role files).

# Speedrun: BUILDER build hour (minute 0 = 03:12, stop = 03:47; work finished 03:38)

Variant: San Francisco (NLHE; after the flop each live player passes one hole card to the left, heads-up a swap;
8-max SNG, 2000 chips, 10/20 blinds rising every 20 hands, 250-hand cap, pays 50/30/20; **1 ms per decision + 100 ms
bank per table**). No humans and no portal, so the Monitor/inbox, Dylan, live.py and uploads were skipped. Times
come from git commits, file mtimes and subagent reports.

## 1. Milestones

| Milestone | Plan target | Landed | Minute |
|---|---|---|---|
| platform, stylist A/B/C, challenger D spawned (background, one message) | 0 | 03:13 | 1 |
| `bot/rules.json` (every field sourced file:line; BUILDER checked it) | 5 | 03:13:57 | 2 |
| **v1 released + no-time-bank upload test** (BUILDER re-ran: kit check ok, 0/179 failed) | 10 | 03:15 | 3 |
| Bughunter on v1 spawned → no bugs; found a raise-then-fold-to-shove leak | n/a | 03:15 → 03:23 | 3-11 |
| A/B/C STYLE.md drafts | while waiting | 03:14:30-03:18 | 2-6 |
| D `DESIGN.md` (clean room) | 12 | 03:18:59 | 7 |
| RESEARCH theory tables in theory/out | 15-30 | icm 03:17 · ranking 03:20 · pushfold/calls/breakeven/twist 03:22 · pushfold_icm, HANDOFF 03:24 | 5-12 |
| **Harness** (`bot/tools/harness.py`, packer, upload test) | 15 | 03:21:22 | 9 |
| **`bot/INTERFACE.md`** + v2 shared platform | ~12 | 03:22:11 / 03:22:53 | 10-11 |
| **Styles legal (first build)** | 20 | C 03:22 · A 03:24 · B 03:24 | 10-12 |
| **D legal** (d1) | n/a | first build 03:20 · legal 03:25 · final 03:29 | 13-17 |
| **Theory tables integrated** (ranking + push/fold ON, pass rule H) = v3, plus ICM and leak fixes | 20 / 30 | 03:26 | 14 |
| v4: heads-up blind-swap fix (bug found by stylist C) | n/a | 03:28 | 16 |
| A, B, C rebuilt on v4, legal | before uploads | 03:29 | 17 |
| v5 = D (d1) released | practice-2 T-3 = 03:39 | 03:30:42 | 19 |
| Bughunter on v4 → 1 minor bug (L40) → **v6 with fix** | n/a | spawned 03:28 · report ~03:34 · v6 03:35:08 | 22-23 |
| B-callwide (one change) legal; repacked on v6 | n/a | 03:32 / 03:35 | 20-23 |
| Bughunter on v5 → L45 (3-left ICM: folds all 169 classes); d2 already fixed it (BUILDER verified) → **v7 = d2** | n/a | spawned 03:34 · report 03:36 · v7 03:37:23 | 24-25 |

**State at 03:38:**
- Released: v1-v7, every one with 0 failed in the no-time-bank upload test next to a same-run check_or_fold
  baseline.
- Legal bots: v6 base, A, B, C, B-callwide, D (v7).
- Picks: practice 1 = v4, practice 2 = v7 (d2) (`state/decisions.md`).
- All subagents were finished by 03:38; nothing of mine is running.

**Local strength** against the platform base (± se, local sparring only, not field results):

| Bot | Bot's points | Base points |
|---|---|---|
| A | 18.4 ± 1.8 | 20.3 ± 1.0 |
| B | 20.1 ± 1.5 | 17.8 ± 1.4 |
| C | 23.5 ± 2.7 | 30.8 ± 2.7 (behind two runs in a row) |
| B-callwide | +1.6 ± 1.5 over B | |
| D | 7.5-8.9 | 16-17.5 (se ~2-3) |

D still scores 23 against hold'em-style sparring bots. Nothing beats base locally; the practice rounds decide.

**Overall: every planned build-hour target landed early**: v1 7 minutes early, INTERFACE on time, styles 8
minutes early. By minute 25 we had 7 releases and 3 bug-review loops closed. The remaining risk is in the
*quality* of the tests (sparring-only, a loaded machine), not in speed.

## 2. What slowed things down or blocked whom

1. **The laptop was overloaded.** Load ran 34-51 on 12 cores from 03:18 to 03:30, from about 12 agents plus
   RESEARCH's rig running simulations locally.
   - The bank-0 upload test failed about 0.5% of decisions, all timeouts; the kit's own check_or_fold failed at
     the same rate.
   - The v1 bughunter spent part of its 8 minutes proving it was the machine.
   - Every "0 failed" afterwards needed a same-run check_or_fold baseline, and p99/max timing were unreliable.
   - On the day this hits the T-6 upload test directly. Load fell to 1.5 by 03:37, once the agents finished.
2. **Stylists were idle about 6 minutes** (drafts done 03:14-03:18; INTERFACE at 03:22). C started from v2's code
   at 03:22:00, before INTERFACE.md landed.
3. **Five silent-fallback bugs in 20 minutes**, each found by a person or agent rather than a check:
   - ranking.json had no `rank` key, so `USE_THEORY_RANKING` quietly used the built-in table.
   - `pack.py` refused to overwrite, so a repack kept the OLD zip.
   - The packer's 400 KB cap dropped twist.json and breakeven.json.
   - The 03:33 rename of `BET_TIGHT`/`RAISE_TIGHT` to `*_RANGE` silently disabled C's setting. BUILDER caught it
     by grep.
   - The kit's `icm()` scores a seat busted this hand at 0.

   All are now fixed with checks (unknown-settings guard, aliases, loud drops, safe overwrite), the last one in
   v3 and d2.
4. **Bugs the platform's own checks missed, caught only by a style's counter or a bughunter:**
   - Heads-up SB/BB swap: C's `c_bb_mismatch` counter, 444 of 444 heads-up decisions.
   - The ICM bust payout.
   - L40, the passed card dealt twice heads-up.
   - L45, D folding everything with 3 left.

   The bughunter-per-release loop was the most productive habit of the hour: about 2-6 minutes per review,
   about 1-2 minutes per fix and release.
5. **The kit's default variant is not the pass variant.** `poker-agent play` without `--variant` plays plain
   hold'em. Platform's tools set it, and INTERFACE now warns about it. D found it the hard way.
6. **The Monitor tool on a file-watcher script needed permission** and was refused in this unattended run.
   BUILDER fell back to background `until` loops that fire once. On the day the inbox Monitor
   (`python3 scripts/feed.py builder`) must be pre-approved.
7. **Duplicated discovery.** A, B, C, D and theory each re-derived "pairs are the worst hands, ace-low is best"
   (L1/L2/L3/L7/L11/L14) with their own equity simulations: about 5× the CPU on an already loaded machine. Theory's
   ranking.json had it at 03:20, but nobody broadcast it.
8. **Local strength claims don't compare.** D claimed +10.7 against its own hold'em sparring bots; platform measured
   D at about −8 against base. Each agent picks its own opponents. RESEARCH's tester verdicts for v2-v7 had not
   reached BUILDER by 03:38, so picks were made on local numbers.
9. **BUILDER's own clock slip.** I misjudged the time once (thought it was ~03:38 when it was 03:34) and logged
   two events with wrong times. Run `date` before every logged milestone; never estimate.

## 3. Concrete changes

**prompts/BUILDER.md**
- Minute 0, step 2: "Spawn a `bughunter` on **v1 the moment it's released**, and on every later release including
  D's (always a fresh agent; ≤8 min each)." Both releases reviewed here had a real issue (v1 leak, v5 L45).
- Add a step after minute 0: "**Broadcast the first variant-level finding.** When theory's ranking/twist lands, or
  any report flips a hold'em assumption (today: pairs worst), SendMessage it to every stylist and challenger run
  and `say.py` it to RESEARCH, so nobody re-derives it."
- Add: "**After every platform release, diff the interface:** `git diff <prev>..HEAD -- bot/INTERFACE.md`. If a
  setting was renamed or removed, grep `candidates/` and tell each affected stylist."
- Add: "**CPU budget.** At load above 1.5× cores, tell RESEARCH to move the rig to Modal and pause local fan-out
  before any upload test. An upload test counts only with a same-run check_or_fold baseline."
- Build hour: "Once A/B/C are legal (about minute 17), **continue the same stylist agents** (SendMessage) for
  rebuilds and one-change candidates rather than letting them idle." Rebuilds took 1-2 minutes here because each
  agent kept its context.
- Practice picks: the plan assumed styles at minute 20. They were ready by minute 12, so the minute-20 practice can
  play a style or D, not only the base.
- Add a fallback for the inbox when a Monitor isn't available: one-shot background `until` loops on the next
  milestone file, each with a time cap.

**.claude/agents/platform.md**
- Build hour: "Publish a **stub `bot/INTERFACE.md` by minute 6**: setting names, hook signatures, the pack and check
  commands, even before the code works. Then fill it in." Stylists were idle until minute 10.
- New rule: "**Never fail silently.** Each of these has a check in `checks.py`:
  - unknown style settings make the pack fail;
  - a theory table schema mismatch raises with the keys found;
  - the packer prints every table it drops;
  - existing zips are overwritten atomically, with the sha256 printed."
- "When renaming a setting, keep the old name as an alias for one release and log the rename in INTERFACE.md."
- Minute-0 checks:
  - position (SB/BB/button) derived and compared with the engine's blind events at 2, 3 and 8 players;
  - ICM with a seat busted this hand;
  - "the kit's `icm()` scores busted seats 0";
  - "set the variant explicitly in every test; `poker-agent play` defaults to plain hold'em".
- "Measure every candidate release against the current base in the harness and put the number on the VERSIONS
  line." Platform did this for v5 and v7, and it corrected D's self-reported strength.

**.claude/agents/stylist.md**
- "Before simulating equities, read `notes/LEDGER.md` and `theory/out/ranking.json`/`twist.json`: the variant's big
  finding is probably there."
- "Add a self-check counter for every platform-derived field your style relies on." C's `c_bb_mismatch` found the
  heads-up blind bug, the single most valuable thing any stylist did.
- "Before each repack, `git log -1 -- bot/INTERFACE.md`; if it changed, re-read the settings list."

**.claude/agents/challenger.md**
- "Never use the kit's `poker_agent_sdk.icm` without a busted-seat test. Prefer the platform's ICM helper once it
  exists." D shipped the bug in v5, and it made D fold everything with 3 left.
- "Report strength against the platform base (`bot/tools/harness.py <your zip> base ...`), not only against your
  own sparring bots."

**.claude/agents/bughunter.md**
- "Step 1 of every timing or failed-decision check: run the kit's check_or_fold in the same run. A failure rate at
  or below its rate is the machine, not the bot." This would have saved the v1 review several minutes; the later
  reviews did it because the brief said so.

**CLAUDE.md**
- §7 (or §4): "**Local CPU is shared by every agent.** At most 2 local simulation processes per subagent; bigger
  runs go to Modal. Timing and upload tests count only next to a same-run check_or_fold baseline."
- §7: "**Silent fallbacks are bugs**: every loader, packer and setting fails loudly on a mismatch."
- §7: "Before logging any time, run `date`; never estimate the clock."
- Settings (`.claude/settings.json`): pre-approve the Monitor tool for `python3 scripts/feed.py *`, so the inbox
  never waits on a permission prompt.

---

# Speedrun: RESEARCH build hour, first 35 minutes (minute 0 = 03:12, stop 03:47)

Variant "San Francisco": NLHE where every player passes one hole card to the left after the flop. 8 players per table,
2000 chips, decision time 1 ms + 100 ms bank. No portal, no humans, no practice data; BUILDER ran in parallel.

## Milestones (clock time, minute)

| time | min | milestone | target | source |
|---|---|---|---|---|
| 03:13 | 1 | 6 subagents spawned in one message (theory x3, analyst, tester, scout) | 0 | me |
| 03:13:57 | 2 | `bot/rules.json` written (BUILDER/platform) | - | mtime |
| 03:14:49 | 3 | `releases/v1.zip` (BUILDER) | - | mtime |
| 03:15 | 3 | **rules-card check**: no mismatches; upload cooldown blank on FORMAT copy, flagged (`rig/rules_check.md`) | asap | tester |
| 03:16 | 4 | **`analysis/fp_train.py`** first end-to-end on the sample (0.1 s; re-run by me 03:18, rc 0) | ~25 | scout |
| 03:17 | 5 | **theory `icm.json`** | 22 | mtime |
| 03:17 | 5 | **`analysis/roundcard.py`** first end-to-end on the sample, 0.19 s (<60 s); 1000-table synthetic 4.7 s at 03:22; re-run by me on a round-folder layout 03:23, 0.25 s | ~25 | analyst |
| 03:18 | 6 | **rig** first number (paired runner, seat rotation, 6 sparring bots) | 15 | tester |
| 03:20:53 | 9 | **theory `ranking.json`** (pairs rank 157-169; A-low best) | 15 | mtime |
| 03:22:01 | 10 | **theory `pushfold.json`, `calls.json`, `breakeven.json`** | 30 / 40 | mtime |
| 03:22:44 | 11 | **theory `twist.json`** + reference `theory/twist/pass_rule.py` (+0.133 ± 0.0006 equity HU over default pass) | 25 | mtime |
| 03:23 | 11 | **`theory/HANDOFF.md`**; 03:24 extra `pushfold_icm.json` | 45 | theory |
| 03:24 | 12 | **first verdict on v1** (`rig/verdicts/v1.md`): legal + fast, 16.94 ± 0.90 pts/table vs mix (fair 12.5); 03:25 upload test 0/765 failed | v1 + ~5 | tester |
| 03:25 | 13 | theory summary + v1 verdict posted to builder inbox (`say.py`) | - | me |
| 03:26:41 | 15 | **dry-run "practice download"** on a synthetic 24-table round in the exact kit format: card 0.19 s, fp 0.23 s, headline numbers match a direct count; found 2 bugs | (new) | analyst-2 |
| 03:30 | 18 | bugs fixed (truncated .gz crash, 8-max position labels off by one, gitignore, paths); `analysis/field_trend.py` (drift + yardsticks + §5 assumptions) and `analysis/counters.json` skeleton | download | analyst, scout |
| 03:31 | 19 | fp_train/field_trend truncation-safe; shared stage-folder rule | - | scout |
| 03:27 | 15 | v2, v3 upload tests 0 failed | - | tester |
| 03:28 | 16 | variant-aware sparring `vtag`, `vloose`, `vshover`, field `vmix` | - | tester |
| 03:33-34 | 21-22 | **v4 verdict** (`rig/verdicts/v4.md`): legal + fast. vmix pts/table: v1 13.15, v2 19.80, v3 20.93, v4 20.52, **check_or_fold 20.12**. v4 − v1 +7.38 ± 1.27. **Heads-up regression v4 vs v3: −1.87 ± 0.38** (600 HU tables, 2 seeds). Posted to builder 03:35 | - | tester |

Subagents: 8 runs (theory x3, analyst x2 + 1 continuation, tester + 2 continuations, scout + 2 continuations). All
finished by 03:34; nothing left running (checked with `ps` at 03:35). No Modal used.

Every minute-0 deliverable in RESEARCH.md landed by **minute 12**; the latest target was minute 45.

## What slowed things down or blocked whom

1. **Python environment.** eval7 does not build on the system Python 3.14. `starter-kit/.venv` (3.12 + SDK + eval7)
   already existed, but the theory agents didn't know, and two of them built their own 3.12 venvs (`theory/.venv` +
   one in a scratchpad). Cost: a few minutes per agent. The tester found the kit venv on its own.
2. **CPU contention.** Load average reached 49-54 on 12 cores at 03:19 (both sessions' subagents running Monte Carlo
   at once). Theory's equity run took 6 min instead of about 1. **v1's first upload test failed 3-5 decisions on
   timeouts**, and the kit's own check_or_fold failed 2-4 in the same minute. Under load, a timing test is noise.
   Had nobody run the kit baseline in the same minute, a legal bot would have been called illegal.
3. **Duplicate maths across sessions.** BUILDER's stylists (A, B, C) and the challenger computed pass-variant preflop
   equities themselves (LEDGER L2, L4, L5, L7, L14) while theory computed `ranking.json`. The numbers disagree by 2-5
   SE on pairs because each used a different keep rule. The work was triplicated, and three versions of the "truth"
   competed until theory's file landed at minute 9.
4. **Releases outpaced verdicts.** v1-v4 were released by 03:28 (one every ~4 min). Only v1 had a RESEARCH verdict by
   03:31, and `VERSIONS.md` says "tester: pending" for v2-v4. Nothing told RESEARCH about a release: without the
   inbox I found v2-v4 by `ls`. The single tester was continued serially; one tester per release would have kept up.
5. **The sparring field is pre-variant.** The sparring bots value pocket pairs as in hold'em, while theory says they
   are the worst hands here. v1's first verdict (and the "check_or_fold beats v1 by 3.74 ± 0.96" warning) rests on a
   field that plays the wrong ranking. Variant-aware sparring came only as a second job at 03:27.
6. **Untested download path.** With no practice data, the card had only seen the 7-table kit sample. A synthetic
   round in the exact format (kit history exporter, v1 + sparring) found a crash on a truncated .gz (the card would
   have written nothing), wrong position labels at 8 players, a stage-folder collision between roundcard and
   fp_train (both defaulting to `analysis/sample/`), and a gitignore gap that would let hand data into git.
7. **A subagent couldn't write `REPORT.md`** ("blocked by the subagent rules": the default guidance against
   creating report/doc files). No project hook was involved (`.claude/settings.json` only guards Bash).
8. **Theory targets were too loose.** Everything landed 5-35 minutes early, and the theory agents then went idle. The
   minutes after 03:24 could have bought a second wave: twist EV with betting, multiway all-ins, the value of
   knowing the left neighbour's card multiway, refits against the variant-aware sparring field.
9. **The floor is hard to beat here.** The kit's check_or_fold scores 20.12 in vmix, level with v4 (20.52), and
   27.55 vs v4's 14.56 against seven shovers. Folding is very strong in a field that busts itself. Only the
   floor-bot comparison revealed it, so it must be in every verdict, and it is a candidate PLAN CHALLENGE (a
   much tighter base) for the first practice.
10. **Unseeded, clock-capped bots make paired tests noisy.** v2-v4 seed their randomness from the clock and cap
    Monte Carlo by time, so the same deals give ±0.5 pts/table run to run, and the result depends on load. Pairing
    buys less than it should.
11. **v4 shipped a heads-up regression** (−1.87 ± 0.38 vs v3) because releases don't wait for a RESEARCH verdict.
    Fine for practice, but before a scored round "tester: pending" must not be the state of the active bot.
12. Minor: the FORMAT copy's upload cooldown is blank (a human must read it off the live page). Theory's ranking was
   ready at minute 9, but stylists had already hard-coded their own numbers by then.

## Concrete changes

### `prompts/RESEARCH.md`
- **Minute 0:** spawn `theory` **x3** in the same message (1: ranking + ICM; 2: the twist; 3: push/fold, calls,
  break-evens, HANDOFF). This run did that and all tables landed by minute 12. Paste-ready briefs belong in
  `prompts/minute0-research.md` so the spawn takes under a minute.
- **Minute 0 brief line for every subagent:** "Python with eval7/SDK: `starter-kit/.venv/bin/python` (system python3 may
  not build eval7). Max N workers."
- **New step at ~minute 10 (when v1 exists): dry-run download.** `analyst` runs `analysis/_dryrun/gen.py`, or
  writes it: about 24 tables on the kit engine with v1 + sparring, exported by the kit's history code. Then it runs
  `roundcard.py`, `fp_train.py` and `field_trend.py` on it, cross-checks 2 numbers against a direct count, and
  tries a truncated copy. This is the only end-to-end test before practice 1.
- **New step at ~minute 12 (when theory's ranking lands): theory wave 2.** Twist EV with betting, multiway all-in
  tables, and the value of the left neighbour's known card multiway. Then refit the columns against the
  variant-aware sparring field.
- **On every release (`RELEASED vN` in the inbox):** spawn one fresh `tester` per release, in parallel, instead of
  continuing one tester serially. Write its verdict into `VERSIONS.md`'s tester column via a say to BUILDER.

### `CLAUDE.md`
- §4 or §7, a **CPU budget**: 12 cores are shared by two sessions. Each subagent uses at most 4 local workers, and
  Monte Carlo beyond about 1 minute of CPU goes to Modal (one app). **No timing or upload test counts when load
  > 12**: check `uptime` first, and always run the kit baseline in the same minute (the tester already does).
- §3: add `starter-kit/.venv/bin/python` as the team Python for anything that needs eval7 or the SDK.
- §3: **theory/out is the single source of preflop/equity truth.** Stylists and challengers read it and don't
  recompute it; if it's missing, they ask RESEARCH for an ETA. (The clean-room D challenger is the exception and
  may compute its own.)
- §2: **platform posts `RELEASED vN <sha> <one line>` to the research inbox** on every release.

### `.claude/agents/*.md`
- `theory.md`: the deliverable times (ranking 15, ICM 22, twist 25, push/fold 30, break-even 40, HANDOFF 45) should
  become **ranking + ICM by 10, twist + push/fold + calls by 15, break-even + HANDOFF by 20**, then wave 2. Name the
  venv. One shared keep rule for every table: "keep higher `keep_score` with the flop", from `theory/twist/pass_rule.py`.
- `tester.md`: **once `theory/out/ranking.json` exists, sparring bots must use the variant ranking and the pass
  rule** (`vtag`, `vshover`, `vmix`); hold'em-style sparring is a secondary field. Every verdict includes the kit
  `check_or_fold` floor and the load average.
- `platform.md` (BUILDER's, recommended): seed the bot's RNG from the hand state (table id + hand + seat + history
  length, as the sparring bots do), and cap Monte Carlo by iterations, not wall-clock. Each decision is then
  deterministic per deal and paired tests are exact. The release gate before a scored round is a tester verdict
  that includes a heads-up run (`--players 2`), because heads-up decides 1st vs 2nd (20 points).
- `stylist.md` / `challenger.md` (BUILDER's, recommended): read `theory/out/` and `theory/HANDOFF.md` first. Don't
  rerun preflop equity sims unless you are D.
- `analyst.md`: parsers must survive a truncated .gz (keep complete tables, say so on the card). The stage folder
  rule is `$AVALON_STAGE`, else the folder name minus its `NN-` prefix, else `kit-sample`, shared with
  scout's scripts. Keep `analysis/_dryrun/gen.py` as the dry-run generator.
- `scout.md`: `field_trend.py`, the drift check and the counters skeleton can be built in the build hour (done here
  by minute 18), not first at practice 1.
- All roles: "a file named in your brief (`REPORT.md`, `card.md`, ...) is a requested deliverable: write it."
