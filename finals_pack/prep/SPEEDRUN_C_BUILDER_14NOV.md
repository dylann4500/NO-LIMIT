# Speedrun C: BUILDER's report

Saturday 14 November 2026, clone `/Users/dylan/avalon-speedrun-c`. Mock variant "Boston" (`flop_auction_holdem`:
hold'em where the flop is chosen by a sealed-bid auction paid in 1,000 never-refilled flop-chips), 6 players,
6,000 chips, blinds and antes. Minute 0 was 16:10 (first set for 08:25, then postponed by the lead at 07:12 and
restarted at 15:07). Stop was 16:56 by the lead's order (minute 46). No humans, no portal: "uploaded" below means
"released, passed the local no-time-bank upload test, and declared with `scripts/live.py`".

**In one paragraph.** The build hour worked to minute 46: a legal bot at minute 11.4 (1.4 minutes late), a real
bot in every practice slot with each pick declared 3-7 minutes before its deadline, 14 releases, and eight
releases with a "fit for a scored round" verdict that includes a heads-up run (v3, v5, v8, v9, v10, v11, v12,
v14) by minute 43. The
weak points were the first 17 minutes (one `platform` agent doing six jobs in series, so v1 was late and the
styles waited 7 minutes) and review speed (every pick was declared before its own bug hunt reported; six of
eight hunts reproduced bugs, none that could zero a round).

Times are from `date`, git commit times and file times unless marked "my log" (`notes/PLAN-builder.md`, written
as things happened). Strength numbers are RESEARCH's, against sparring bots only (grade C).

## 1. Milestones

| Target (source) | Target | Landed | Late / early | How checked |
|---|---|---|---|---|
| Start-up: prompt, strategy and role files read; Monitor armed; RESEARCH found; plan file | before minute 0 | 06:27-06:30 | n/a | Monitor id in my log; `ListAgents` found "RESEARCH speedrun C" on the second call |
| Six build agents spawned in one message (BUILDER.md:55) | 16:10 | 16:10:1x (b0 seen 16:10:0x) | on time | six launch results; briefs were pre-written in `notes/briefs/` |
| RESEARCH told: kit, variant, Format page, rules card path (BUILDER.md:65) | 16:10 | 16:10 | on time | `SendMessage` result + `state/events.log` |
| Team Python built, variant loads in the kit's engine (BUILDER.md:51, PLAN.md:196) | 16:10 | 16:11:57 (`bot/PYTHON.md`) | +2 min | I ran the interpreter at 16:12:09; told RESEARCH 16:12 |
| Rules card `bot/rules.json` (BUILDER.md:57) | minute 5, 16:15 | 16:12:36 | 2.4 min early | opened it; RESEARCH's tester found no mismatch at 16:14 (`rig/out/rules-check.md`) |
| Stub `bot/INTERFACE.md` (BUILDER.md:58) | minute 6, 16:16 | 16:14 (my log) | 2 min early | opened it |
| **v1 released and upload-tested** (BUILDER.md:59, PLAN b10) | minute 10, 16:20 | **16:21:23** (commit 8a5a9c6) | **1.4 min late** | zip sha, VERSIONS line; upload test 0 failed / 700 at load 8.6 with baseline; the 16:20:49 run was inconclusive (loaded) |
| v1 declared (`live.py`) | at release | 16:21:28 | | `state/live.json`, inbox line |
| First variant-level finding broadcast to all stylists and the challenger (BUILDER.md:84) | when known | 16:16 (ranking v1 landed 16:15) | 1 min | five `SendMessage` results |
| Design D legal (BUILDER.md:63, 76: "legal by minute 12-13") | 16:22 | D.zip packed 16:19, quick check passed 16:21 (my log; commit ab4a7e2 16:23:33) | 1 min early | release run's check on the same bytes |
| D's `DESIGN.md` (BUILDER.md:64) | minute 12, 16:22 | not verified: I did not record its first write (file last changed 16:31:50) | unknown | none |
| Test harness: pack, check, upload test (BUILDER.md:59) | minute 15, 16:25 | pack + upload test 16:16:32 (e2a8d24), check 16:22:08 (aa9e764), finished 16:23:17 (39d808b) | 2 min early | used them for v1 and v2 |
| Real interface: an importable platform that styles can pack on (platform.md:35 "by ~12") | 16:22 | 16:26:56 (commit 89a59e7); INTERFACE filled in 16:29:09 | **5-7 min late** | I ran `pack.py bot` at 16:26:47: packed, kit check OK |
| Styles A, B, C legal (BUILDER.md:76 "minute 12-13", :89 "about minute 15") | 16:22-16:25 | B 16:27, C 16:28, A 16:29 | **3-7 min late** | each stylist's check; release runs re-checked A, B, C |
| Practice 1 pick released, tested, declared (minute 17) | 16:27 | v2 = design D, released 16:23:28, declared 16:24:19 | 2.7 min early | sha, VERSIONS, upload test 0 / 521 x 2 at load 12.5 with baseline |
| "One practice must be design D" (BUILDER.md:79) | by practice 3 | practice 1 | | `state/live.json` |
| Shared platform with every theory table built in (BUILDER.md:60 "all by about minute 20") | 16:30 | tables loaded in v3 at 16:30:22 but **not read**; read from v8 at 16:37:35 (d9fc5c7) | **7.6 min late** | my bughunter's read counter on v3's bytes (16:33); core's `report()["table_reads"]` on v8 |
| Practice 2 pick declared (minute 27) | 16:37 | v5 = style A, released 16:33:06, declared 16:33:29 | 3.5 min early | sha, VERSIONS, upload test 0 / 518 x 2 at load 5.8 with baseline |
| Practice 3 pick declared (minute 37) | 16:47 | v9 = style B on the v8 base, released 16:40-16:41, declared 16:41:26 | 5.5 min early | I checked the zip's sha and that its `style.py` is the stylist's frozen blob; upload test 0 / 486 x 2 at load 5.3 with baseline |
| Every style rebuilt on the newest tables before its upload (BUILDER.md:80) | each pick | v5 on the newest base at the time (which did not yet read the tables); v9 on v8 | partly | VERSIONS lines; the table I unzipped (`twist_rule` v2.1 in v5, v2.3 in v8/v9/v10) |
| Fresh bughunter on every release (BUILDER.md:69) | at release | v1, v2, v3, v5, v7, v8, v9, v10 yes (v7 and v8 two minutes after release, v10 six); v4, v6 no (superseded within 2-4 min); v11, v12, v13, v14 no (repacks or fixes of reviewed code in the last 10 minutes) | 8 of 14 | `notes/bughunt/*/REPORT.md` (v7's written by me from the hunter's message) |
| "RELEASED vN" to RESEARCH on every release (BUILDER.md:70) | at release | v1, v2, v3, v5, v9, v10, v11, v12, v14 from me; v6, v7, v8, v13 not: RESEARCH read `VERSIONS.md` and had testers running before I knew of v6, v8 and v13 | 9 of 14 | `state/events.log` |
| Interface diff after every platform release (BUILDER.md:87) | each release | after v3 (16:31:38, two renames, no style affected); after v6 and v8 only through core's report at 16:37 | partly | grep of `candidates/*/style.py` |
| A tester verdict with a heads-up run before any scored round (BUILDER.md:72) | before round 1 | v3 16:36, v5 16:39, v8 and v7 16:42, v9 and v10 16:46, v12 16:47, v11 16:50, v14 16:52: all "fit for a scored round" | in time | `rig/out/v*-verdict.md` |
| Practice 4 pick declared (minute 47) | 16:57 | v14 = style C on the fixed base v11, released 16:48, declared 16:50:12 | 6.8 min early | I checked the zip's sha and style blob; upload test 0 / 494 x 2 at load 3.4 with baseline |
| First challenger briefed at b40 (PLAN.md b40) | 16:50 | brief written 16:46 (`notes/briefs/b40-challenger-1.md`); **not spawned** | not done | my choice: its first output could not land before the 16:56 stop |
| Round-1 bot declared at b50 (BUILDER.md "Round 1") | 17:00 | after the stop | not reached | at the stop the round-1 default is v5 (RESEARCH's recommendation and mine, `state/decisions.md`) |

## 2. What slowed or blocked us, by minutes lost

1. **The styles waited for an importable platform: about 7 minutes each for three stylists (16:19 to 16:27).** The
   interface stub was up at 16:14, but a stub cannot be packed or checked. The core `platform` run wrote the engine
   first (`av_engine.py` at 16:19:49) and had no `agent.py` until 16:26. I asked it at 16:22 to ship a thin
   importable version first. Design D, which carries its own betting code, was legal at 16:21, so it took practice
   1 and the styles only reached practice 2.
2. **Theory's tables were loaded but not read for 7 minutes (v3 at 16:30 to v8 at 16:37).** v3 passed every check
   because a table that is never looked up fails nothing. My bughunter found it at 16:33 by counting reads. v5,
   the practice-2 bot, therefore played on a base that ignored `pushfold.by_auction_state`, `exploit.*` and
   `icm_thresholds.tables`.
3. **v1 was 1.4 minutes late (16:21:23 for a 16:20 target)** and only that close because I started a second
   `platform` run at 16:20:21 to ship check-or-fold from the kit's template. The core run reported at 16:37:
   "I missed the v1 deadline".
4. **A style file changed while its release was being packed: 2-3 minutes, twice avoided or repaired.** v4 was
   packed at 16:30:38, the stylist changed `style.py` at 16:30:56, v5 replaced it at 16:33:06, and RESEARCH's
   tester had already started on v4. It nearly happened again with B (last edit 16:39:10, release run started
   16:39:00); that time I had the run check the git blob before releasing.
5. **Load spike, 16:21 to 16:24: about 1-2 minutes.** Load reached 14.5 and then 31-34 on 15 cores (a macOS
   background burst, a bughunter's test and other sessions; not RESEARCH's rig). The 16:20:49 upload test of v1
   was inconclusive and had to be re-run. RESEARCH moved its rig to Modal at 16:22 and paused local runs
   16:24-16:28. Later load was 3.5-8.
6. **My own context was compacted at about 16:36-16:38: about 2 minutes.** The Monitor expired at 16:37 during
   it and was re-armed at 16:38:30 (no inbox line fell in the gap). I acted on the b27 line at 16:39.
7. **Releases outran reviews.** Ten releases in 20 minutes (16:21 to 16:41); a tester verdict takes about 8
   minutes and a bug hunt 5-8. v4 and v6 were superseded before anyone reviewed them. No minutes lost, but
   RESEARCH had to ask which verdict I needed first, and I learned of v6 and v8 from `VERSIONS.md`, not from the
   core run.
8. **Bug hunts land after the pick is packed.** Each hunt takes 3-6 minutes and a release takes 1-2, so every
   practice pick was declared before its own review came back: v9's three findings arrived at 16:48 (declared
   16:41), and the two bugs in style C arrived at 16:49, one minute after v14 was released on that same style.
   None could zero a round, so nothing was pulled, but v14 goes to practice 4 with two known style bugs and the fix
   (`candidates/C-pricefix/`) was still being built at the stop.
9. **The postponement (07:12 to 15:07)** cost nothing in build time: one minute to shift every time in the briefs
   by +7:45 with a script.

Mine to own: several of my messages between 16:29 and 16:39 carried clock times I had estimated instead of read
from `date`, 1-2 minutes ahead (CLAUDE.md says run `date` first), and one at 16:49:41 said "16:50". The log's own
timestamps are from `date`. In the last 8 minutes I also chose not to start work that could not finish: the b40
challenger was briefed on paper only, and the bugs found in v7 and v9 were recorded with their owners, not sent
out for fixing.

## 3. Where the bundle's instructions were wrong, unclear or missing

| # | Where | Problem | Fix I would make |
|---|---|---|---|
| 1 | `prompts/BUILDER.md:56-60` (one `platform` for Python, rules card, stub, v1 by 10, harness by 15, shared platform) | One agent does these in series and picks its own order; ours built the engine first and missed v1 | Spawn three `platform` runs at minute 0, each with its own files: (a) Python, rules card, then **v1 from the kit's template by minute 6**, then stays on as the release run; (b) `bot/tools/` (pack, check, upload test); (c) the shared platform. I split off (b) myself and it worked (done at minute 13). |
| 2 | `.claude/agents/platform.md:153` ("stub `bot/INTERFACE.md` by minute 6 ... even before the code works") and `:35` ("by ~12") | A stub does not unblock stylists: they need something `pack.py` accepts | Add: "by minute 8 an importable skeleton (`agent.py`, the style hooks, a base that checks or folds) that `pack.py bot` and `check.py` pass; strategy comes after". Add a clock step b8 to BUILDER: "run `pack.py bot`; when it packs, tell the stylists". |
| 3 | `prompts/BUILDER.md:76` ("Styles and design D were legal by minute 12-13") | True for D only; styles were legal at minute 17-19 here | Say "D (standalone) by 10-12; styles 3-5 minutes after the platform imports", and tell the challenger to build D standalone first (ours did, which is why practice 1 had a real bot). |
| 4 | `prompts/BUILDER.md:50-51` and `strategy/PLAN.md:196` (BUILDER itself checks `load_variant` with the kit's Python at minute 0) against `BUILDER.md:56` (`platform` builds that Python) | The Python does not exist when BUILDER is told to use it | Make it `platform`'s first line in `bot/PYTHON.md` ("variant loads and plays one hand"); BUILDER reads that file. |
| 5 | `prompts/BUILDER.md:69-72` (fresh bughunter and a RELEASED message on every release) | With a release every 2 minutes this is ten bug hunts and ten verdicts; two releases were dead before review | "Every release that is declared to play, and every base that styles pack on. A release superseded before review is marked so in `VERSIONS.md`." Also: "only BUILDER asks for a release, and names the number" (two release runs appended v9 and v10 at the same time; I had to assign numbers in the briefs, and v10's line sits before v9's). |
| 6 | Missing everywhere (`CLAUDE.md` §2 last bullet: "Subagents never write to inboxes; they report to whoever spawned them") | A subagent reports only when it ends. The main session has no way to hear "v6 is released" or "`rules.json` is written" from a run that keeps going | Either let `platform` post one line per release to the builder inbox (`scripts/say.py builder "RELEASED vN sha"`), or tell BUILDER to arm a one-shot background watcher per deliverable (`until [ -f X ]; do sleep 3; done`). I used watchers; they are the only reason the minute-2 to minute-11 milestones woke me. |
| 7 | `CLAUDE.md` §4 rule 7 ("no loops that poll", "no `sleep` over 20 s") | Reads as if it forbids fix 6's watchers and a stop-time timer, both of which are background jobs that wake the session | Add: "a background one-shot that exits on a condition is not blocking and is the right way to be woken". |
| 8 | `.claude/agents/stylist.md` (hand-off) | A stylist keeps editing `candidates/<x>/style.py` and repacks `build/<x>.zip` in place after reporting; releases and testers then hold different bytes (v4/v5; RESEARCH saw three packings of C folding 18 / 33 / 48% to a flop bet) | "Your final message names the git blob of `style.py` and the zip's sha256; after that, change only a new folder." And in the release brief: "release only that blob". |
| 9 | `CLAUDE.md:81` ("Modal: one app per purpose") against `strategy/DECISION_RULES.md:33` and every role file ("Modal has only two deployed apps, `avalon-rig` ... and `avalon-theory`") | "One app per purpose" invites a third app | CLAUDE.md:81: "only the two deployed apps `avalon-rig` and `avalon-theory`; everyone else calls them". |
| 10 | `strategy/FIRST_PROMPT.md:82`, `:173`, `:225` (8 players, 2,000 chips, 56% / 65-74% / 57% call thresholds) and `strategy/PLAN.md:85`, `:146` (fold to a 3-bet "usually 65-75%") | Regional numbers stated as defaults. Today: 6 players, 6,000 chips, antes; thresholds 58.1 / 60.6 / 65.2 / 57.1 / 50.0% for 6 to 2 left; fold-to-3-bet ceiling about 57% | Replace each number with "from `bot/rules.json` and `theory/out/icm_thresholds.json` / `exploit.json`" and keep the regional value only as an example in brackets. |
| 11 | `scripts/timeline.json` and the task I was given | No b45 step exists (steps: b0, b10, b17, b20, b27, b30, b37, b40, b47, b50), so "stop at the minute-45 step" could never fire | The lead already replaced it with a time. For the real day nothing to fix. |
| 12 | `prompts/BUILDER.md` (Monitor) | A Monitor armed at 16:07 expires at 16:37, in the busiest stretch | "Re-arm the Monitor when b0 arrives, whatever time it has left", so the first expiry falls at minute 30 by choice and the next after the build hour's picks. |
| 13 | `.claude/agents/platform.md` (checks before a release) | Nothing says a loaded table must be shown to be read | Add to the release checklist: "`report()["table_reads"]` after 200 hands: every packed table has reads > 0, or the VERSIONS line says which are unread". |
| 14 | Kit traps not in `strategy/LESSONS.md` or the role files | Heads-up the engine posts the big blind first and the button is the small blind (D shipped with the wrong seat: its heads-up small blind never raised in v2); `poker_agent_sdk.icm` zeroes a busted seat; `poker-agent play` always fills 6 seats | Add all three to LESSONS.md and one line to `platform.md`, `challenger.md` and `tester.md`: "before the first release, a heads-up table on the real engine: the button raises first-in more than 0%". |
| 15 | `strategy/DECISION_RULES.md` §3 / `state/decisions.md` | A PLAN CHALLENGE "recorded in state/decisions.md" by RESEARCH lands in a file whose header says "Decisions (BUILDER)"; both sessions edit it | Say in CLAUDE.md §3 that both append, each under its own dated heading, and never rewrite the other's entry. |
| 16 | `.claude/agents/bughunter.md` (the report file) | The v7 bughunter said "the harness refused the file" and returned its report only as a message; I wrote `notes/bughunt/v7/REPORT.md` from it | Add: "if the Write tool refuses, write the report with a shell heredoc; a report that exists only in your final message is lost at the next compaction". |
| 17 | `.claude/agents/tester.md` / `rig/sparring/` (RESEARCH's side, seen from mine) | The sparring bots bet by theory's tables, so bugs triggered by odd bets cost nothing on the rig: the base folded one pair for 1 chip into 711 and the buggy base still scored +0.74 to +1.74 | Add one sparring bot that makes legal but odd bets (minimum raises, 1-chip all-ins, tiny flop bets) to every mix. |
| 18 | `.claude/agents/stylist.md` (self-checks) | A style's own counter hid its bug: style C counted zero bids under `C_TWIST_BID`, so "zero bids 1.6%" looked like a base effect | "Count every zero bid, every overridden base action and every fallback in its own counter, and print them in the check's style report." |
| 19 | `prompts/BUILDER.md:69` (bughunter "at most 8 minutes") against `:80-81` (pick released and declared 3 minutes before each practice) | A pick is always declared before its bug hunt reports (see section 2, item 8) | "Spawn the bughunter on the CANDIDATE zip the moment the stylist reports it legal, not on the release; the release run re-checks only that the bytes are the reviewed blob on the reviewed base." |

## 4. Did the Saturday drafts help or mislead?

**Helped**
- `strategy/TWIST_NOTES.md` T13 (line 90, "Auction over board cards, separate currency") was today's variant
  almost exactly. Its direction was right before any maths ran: bid in every auction, pairs lose value, never
  bidding is the worst policy. Theory confirmed all three within 16 minutes (22 ranks 143rd of 169; never
  bidding 10.1 points per table against 21.5 with the rule). Because the stylists and the challenger had read
  it, every candidate bid from its first build.
- `notes/pre/contrarian.md` section 2, "start where the field will end on the twist": matched. Theory's rule
  doubled its bid size once (v2.1 to v2.3, +2.5 ± 0.7) and found four times no better.
- The contrarian memo's floor-bot yardstick: we shipped the floor as v1 and RESEARCH scored every candidate
  against it (22.9 six-handed, 30.0 heads-up), which is how we knew by 16:28 that everything real was 12-15
  points above doing nothing.
- `strategy/LESSONS.md` on the shared CPU and on silent fallbacks: both happened again (load 31; tables loaded
  but unread) and were caught because the checks were already habits.

**Misled**
- T13's sizing advice (line 93, "balance / auctions expected to remain") was wrong for this variant: theory
  measured that a flat budget ran the winner dry in 44% of tables and that sizing by the pot is better. Style C
  drafted a pacing scheme on it (`TWIST_PACE`, `TWIST_FLOP_RATE` settings) that ended switched off.
- `strategy/PLAN.md:85` and `:146`, fold to a 3-bet "usually 65-75%": with antes the ceiling is about 57%.
  Styles A and B drafted to the plan's number and both still fold too much (v5: 60.2% to non-all-in re-raises,
  93% of opens to a 3-bet shove in RESEARCH's stand-in practice).
- `strategy/FIRST_PROMPT.md` Part 1's regional numbers (8 players, 2,000 chips): nobody used them wrongly that
  I saw, because the rules card landed at minute 2.6, but each stylist's notes spend lines re-deriving them.

**Not used by me:** `notes/pre/buildplan.md`, `challenger_bar.md`, `field.md`, `testplan.md`, `variants.md`,
`whatwins.md`, `stat_definitions.md`. I read only `contrarian.md` of `notes/pre/` at start-up, as
`prompts/BUILDER.md` asks; I cannot say whether the others helped the subagents.

## 5. Did the inbox work?

Yes for the clock: every line arrived within seconds of being posted and woke me. Session-to-session messages
(more than 50 from RESEARCH between 16:14 and 16:52) all arrived by `SendMessage`, none through the inbox.

| Clock line | Posted | Seen | Acted |
|---|---|---|---|
| minute 0 set 08:25 | 06:27:17 | before my Monitor (read from the file at start-up) | times written into the briefs |
| clock reset | 07:12:25 | 07:12:40 | Monitor stopped on the lead's HOLD |
| minute 0 set 16:10 | 15:07:08 | 15:07 | Monitor re-armed 15:07; briefs shifted +7:45 |
| b0 | 16:10:00 | 16:10:0x | six agents spawned 16:10:1x; RESEARCH told 16:10 |
| b10 (v1 due) | 16:20:00 | 16:20:2x | rescue release run already started 16:20:21; v1 16:21:23; `live.py` 16:21:28 |
| b17 (practice 1 in 3 min) | 16:27:00 | 16:27:09 | nothing to do: v2 declared 16:24:19 |
| b20 (practice 1 plays; pick practice 2) | 16:30:00 | 16:30:35 | style A chosen; release run 16:31; v5 declared 16:33:29 |
| b27 (practice 2 in 3 min) | 16:37:00 | delivered 16:37; read 16:39:22 (compaction) | nothing to do: v5 declared 16:33:29 |
| b30 (practice 2 plays; pick practice 3) | 16:40:00 | 16:40 | B already chosen 16:39; core continued for the table check; v9 declared 16:41:26 |
| b37 (practice 3 in 3 min) | 16:47:00 | 16:47 | nothing to do: v9 declared 16:41:26; I checked the zip's sha against `state/live.json` |
| b40 (practice 3 plays; pick practice 4; brief the challenger) | 16:50:00 | 16:50:0x | v14 declared 16:50:12; challenger brief written, not spawned |
| b47, b50 | 16:57, 17:00 | after the stop | none |

`[live]` lines (my own `live.py` calls echoed back) arrived at 16:21:28, 16:24:19, 16:33:29, 16:41:26 and 16:50:12, each within a second.

**Monitor expiries and re-arms**

| Armed | Expired | Events | Re-armed | Gap |
|---|---|---|---|---|
| 06:28 | 06:57:57 | 0 | at once | seconds |
| 06:58 | stopped by me 07:12 (lead's HOLD) | 1 | 15:07 on "new minute 0" | the hold |
| 15:07 | 15:37:24 | 1 | at once | seconds |
| 15:37 | 16:07:27 | 0 | at once | seconds |
| 16:07 | about 16:37:30 | 8 | 16:38:30 | about 1 minute (my compaction); no line was posted in it |
| 16:38:30 | stopped by me at the stop (it would have expired about 17:08) | 5 | not re-armed: the run is over | |

What did not work through the inbox: news from my own subagents (see section 3, row 6). The clock told me what
was due; nothing told me what had landed.

## 6. State at the stop

**Declared (`state/live.json`):** v14 for practice 4 (17:00), declared 16:50:12. Before it: v9 (practice 3,
16:50), v5 (practice 2, 16:40), v2 (practice 1, 16:30), v1 (first legal bot). Round 1 (17:10) was not declared
(its step, b50, is after the stop); the default on the evidence is **v5**, with v14 as the challenger. RESEARCH's
stand-in practices (200 synthetic tables each) could not rank v9, v2 and v5.

**Released** (every zip: kit check passed, `check.py --full` 0 failed / 0 illegal / 0 exceptions over about
100,000 states, upload test with 2 players, 20 hands, no time bank next to the `check_or_fold` baseline, load
below 15; "vs v5" = RESEARCH's paired rig against sparring bots, six-handed / heads-up, grade C):

| Bot | What | sha256 (first 12) | Upload test (failed / decisions, load) | Tester verdict | Bug hunt |
|---|---|---|---|---|---|
| v1 | check or fold, zero bid (the floor) | 9a78cdeab305 | 0 / 700, 8.6 | correct; equals the floor (22.9 / 30.0) | none found |
| v2 | design D, standalone; practice 1 | ecc2dbb7de29 | 0 / 521 x 2, 12.5 | fit for practice only: +13.27 ± 0.41 over the floor; heads-up small blind never raises | 1: heads-up blind seat (fixed in v7) |
| v3 | platform base, bid rule v2.1 | 7c33aacbed33 | core's own run | fit for a scored round; vs v2 +0.87 ± 0.46 / +1.16 ± 0.21 | 1: tables loaded, never read (fixed in v8) |
| v4 | style A, older `style.py` | 6388061f12a5 | superseded in 2 minutes, never declared | none | none |
| **v5** | style A on the v3-era base; practice 2; **round-1 default** | d58ca3332921 | 0 / 518 x 2, 5.8 | **fit for a scored round**; vs v2 +1.23 ± 0.47 / +1.20 ± 0.21; folds 60% to non-all-in re-raises (ceiling about 57%) | none found |
| v6 | base + theory wave 2 | bb2c82a76ab0 | core's own run | none (superseded by v8 in 4 minutes) | none |
| v7 | design D2 (v2 + heads-up fixes), standalone | a26de05756fb | 0 / 482 x 2, 7.0 | fit on correctness; behind v5: -1.06 ± 0.66 / -1.40 ± 0.26 | 3 open: folds when priced in as a covered short stack; misreads a short big blind |
| v8 | base, all tables read, bid rule v2.3 | 5985d0cd9a2d | 0 / 486 over 5 seeds, 6.3 | fit for a scored round; vs v5 +0.52 ± 0.54 / +0.28 ± 0.16 | 2: payment bucket read too high; one pair folded at any price (both fixed in v11) |
| v9 | style B on v8; practice 3 | 80d18f66b764 | 0 / 486 x 2, 5.3 | fit for a scored round; vs v5 +0.30 ± 0.39 / +0.34 ± 0.12 | 3 open, none can zero a round (noisy preflop equity at all-in call-offs: platform; first 3-bet read as 33% wide: style B); carries v8's two |
| v10 | style C on v8 | ae77bf25e590 | 0 / 490 x 2, 5.1 | fit for a scored round; vs v5 **+1.74 ± 0.45** / +0.36 ± 0.17 | 2 open in style C: folds one pair to a raise at any price; bids zero with 1-5 flop-chips; carries v8's two |
| v11 | base with v8's two bugs fixed | 91656a29a401 | 0 / 486, 3.2 | fit for a scored round; v11 minus v13 = -0.36 ± 0.15 six-handed over 3,000 paired tables whose three seeds disagree (-0.07, -0.05, -0.95): "between 0 and -1", not settled; heads-up -0.08 ± 0.06 | platform re-ran the two repro scripts: 0 left; no fresh hunt |
| v12 | style A repacked on v8 | 447bbbda8b8e | 0 / 518 x 2, 3.4 | fit for a scored round; vs v5 +1.23 ± 0.31 / +0.12 ± 0.09; folds 58% to a flop bet (v5 43%) | none; carries v8's two |
| v13 | v8 + ranking v4 | c3b10f2fbc07 | core's own run | vs v5 +0.73 ± 0.43 / +0.10 ± 0.21 | none; carries v8's two: do not play |
| **v14** | style C repacked on v11; **practice 4** | b3cd87760b43 | 0 / 494 x 2, 3.4 | **fit for a scored round** (16:52): 0 failed / 464,367; v14 minus v10 = -0.40 ± 0.27 / -0.05 ± 0.08; vs v5 about +1.35 (se about 0.5) / +0.31 | none of its own; style C's two open bugs apply |

I verified the sha of v1, v2, v5, v9, v10, v11 and v14 against `releases/VERSIONS.md` myself, and for v9 and
v14 that the packed `style.py` is the stylist's frozen blob. v3, v6, v8 and v13 were released by the core
`platform` run and I read their numbers from its report and `VERSIONS.md` only.

**Legal candidates, not released**

| Folder | What | State |
|---|---|---|
| `candidates/C-pricefix/` (zip 1f82874cc44f, style blob 66d12de2) | style C with its two bugs fixed, on the v11 base | `--full` 0 failed; both repro scripts clean (809 wrong folds -> 0; 3,869 zero bids -> 0). Not released: no paired run, and the bid fuzz now flags "over the half-balance cap" in 15,830 of 60,000 bids, not investigated. This is the next thing to do: it should replace v14. |
| `candidates/A-vs3betshove/` (zip f0ffb8ddc305, style blob 805550af) | style A calling more 3-bet shoves | `--full` 0 failed; fold to a 3-bet shove 93.8% -> 87.3%; +0.15 ± 0.29 on 800 paired tables: no gain |
| `candidates/D/build/D4.zip` (70d16cae…) | design D as a style on the platform | full check passed (challenger); no edge over the base (+0.5 ± 1.2) |
| `notes/briefs/b40-challenger-1.md` | brief for the first challenger ("auction-first") | written, not spawned |

**Open bugs with owners:** platform: preflop `ctx.equity(width)` noise of 10-24 points at all-in call-offs
(LEDGER L131). Stylist B: a seat's first 3-bet read as 33% wide (L132). Stylist C: fixed in `C-pricefix`, not
released (L135-L136). Challenger: D2's covered-stack price and short-blind read (L112-L113). Platform, unfixed
flag from RESEARCH: every style still folds 58-60% to non-all-in re-raises and 67-93% to all-in ones against a
ceiling of about 57%.

**Still running at the stop:** nothing of mine. All 21 subagents I started (6 at minute 0, 7 release
runs, 8 bug hunts, several continued once or twice) had reported by 16:51:30. I started no Modal app
(`avalon-rig` and the theory app are RESEARCH's; it said it stops them at 16:56). The inbox Monitor was stopped
at the stop. RESEARCH sent its last message at 16:52.
