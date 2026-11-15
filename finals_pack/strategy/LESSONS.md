# Lessons: what broke, and the rule that prevents it now

For both sessions and every subagent. Each item is what happened and where, then the rule that now prevents it.
Sources: the evaluation rounds and live simulations of the old agent hub (13-14 November; "eval", "sim7"), the
scenario audits ("audit"), the practice run of 14 November ("prac1") and the regional itself. "(hard)" marks a
hard rule from `CLAUDE.md` §4. Lessons about the hub's screens and the link between two laptops are left out:
neither exists any more.

## Agents and processes

- **A pattern kill stopped every agent, twice** (sim7). The tester ran `pkill -f "modal run"` to stop its own
  jobs; every agent's command line holds its instructions, so the pattern matched all 8 agents. → Never kill by
  name or pattern (`pkill`, `killall`, `pgrep | xargs kill`). Save the PID when you start a job and stop only
  that PID, or use `modal app stop --yes <id>`. (hard; a hook refuses pattern kills)
- **A blocking wait made an agent ignore a human for minutes** (prac1). The tester ran 6 `modal run` jobs in a
  foreground shell and then `wait`; Samuel's message sat about 100 s before the agent even saw it, and neither of
  his two messages was ever answered. → Never block your turn: no foreground `wait`, no `sleep` of 20 s or more, no
  polling loops. Long jobs run in the background with a log; end your turn and check when woken. Main sessions
  spawn subagents with `run_in_background: true`. (hard)
- **An agent compacted before answering a human** (prac1). Interrupted for Samuel's message, the tester first
  compacted 106k tokens; his message showed "queued" for about a minute. → A human's message comes before
  anything else, compaction included. Main sessions keep their context lean (file dumps stay in subagents;
  reports are a summary plus paths), so compaction is rare. After one, re-read your prompt file
  (`prompts/BUILDER.md` or `prompts/RESEARCH.md`) first, then your PLAN file, `state/status.md`, `state/clock.md` and
  the inbox tail before acting, and re-arm your Monitor.
- **A reply that ignored the human counted as an answer** (prac1). After compacting, the tester answered another
  agent's urgent task instead of Samuel; any text counted as a reply, so nothing chased it. In eval round 3 a
  human's message went unanswered three times while the agent kept working. → Your reply's first sentence answers
  the human, or says "Working on it: <what>, ready by HH:MM". Anything else is not an answer, and the human
  should say so. (`CLAUDE.md` §5)
- **Leads promised messages they could not send** (eval round 3). A session speaks only when something wakes it.
  → Never say "I'll tell you when..." unless an inbox line, a subagent's report or the Monitor will wake you then;
  otherwise say where the result will appear.
- **Leftover worker processes pinned all 12 cores for 2 hours** (prac1). A test rig's process pool from an earlier
  simulation outlived its parent, and that night's local latency tests were wrong. → Every job you start has its
  PID and log in your PLAN file and is stopped when done. Time bots only on an idle machine (check `top` first),
  with the kit's check-or-fold bot in the same run as a baseline. Humans: look at Activity Monitor on Sunday
  morning.
- **A checkout in the shared tree would swap files under every other agent** (audit). → One repo, many agents:
  never `git checkout <commit>`, `git stash` or `git reset --hard` in the working tree. Test an old commit in its
  own worktree (`git worktree add /tmp/t-<sha> <sha>`). Each subagent works in its own folder; only `platform`
  edits `bot/` and writes `releases/`.
- **What failed was state, not rules** (eval rounds 1-3). Repeating the rules to agents didn't help (in a test,
  reminders added nothing and caused the one error); stale status lines, stale summaries, missing context and
  silence did the damage. → State lives in files: `notes/PLAN-<session>.md` (what's running where, open
  promises, next deadline), updated at every step. Any status you give says "as of HH:MM".
- **A lead kept quoting old times after the clock changed** (eval round 1). → Read times from `state/clock.md`
  each time you quote one, never from memory.
- **A hung connection left an agent "working" forever** (eval round 1). → A session silent for 5 minutes while a
  step is due: its human presses Esc, asks "status?" and has it carry on from its PLAN file.
- **Jobs died with a restart and nobody knew; steps due during it were skipped** (eval round 1, audit). → After a
  restart, check every job listed in the PLAN file and rerun what died. A missed step is done late and labelled
  LATE, never skipped.
- **A "+36 points" result was a broken test** (simulations). → Check before you trust: re-run, don't re-read. An
  implausibly large effect is a bug until `tester` reproduces it.
- **Apps and jobs outlived the event** (audit). → After the last round: record, then `modal app stop --yes` your apps
  and kill your own PIDs.

## Modal

- **Bursts of `modal run` hit Modal's app-creation limit and lost a round** (prac1). The tester launched 6
  `modal run`s at once; Modal's workspace-wide limit on creating apps then stopped the rehearsal's practice-1
  round from starting. Sunday's rounds don't run on our Modal, but the same limit can stop every agent's tests
  mid-window. → Only two deployed apps: `avalon-rig` (`tester`) and `avalon-theory` (`theory`), each deployed once
  and called many times (`.map` over shards); the other roles call them or run locally. Never several `modal run`s
  at once. Caps: `tester` up to 40 containers, `theory` up to 20, everyone else shares 20 (80 in all). On "App
  create rate limit exceeded", stop launching and use an app that's already deployed. (hard)
- **Modal jobs were stopped with a pattern kill** (sim7). → `modal app list`, then `modal app stop --yes <id>` for your
  own apps only.
- **Nobody watched for forgotten apps** (audit). → Stop a `modal run` app when its job is done; one running for
  over 45 minutes is probably forgotten. The two deployed apps (`avalon-rig`, `avalon-theory`) stay up until the
  event ends.
- **Modal could be down at the decision** (audit). → Run locally at reduced n and label the result so; the
  decision doesn't wait for Modal.

## Data and portal

- **The starter kit lacked the variant's engine** (prac1). The rehearsal kit had the rules page but not the
  variant's engine; agents built a home-made engine and every local test ran on it. → At minute 0, before
  anything else, BUILDER checks with the kit's Python that the kit's engine loads today's variant
  (`load_variant("<variant>")`, with the engine's own name for it: list its variants) and plays a table; if the kit's Python isn't built yet, `platform`'s first step does it.
  If it doesn't load, tell both humans at once.
- **Agents learned facts about the rehearsal portal as if they applied to Sunday** (prac1: "the cooldown is about
  a minute, not 5"). → Nothing learned in a rehearsal carries over. The cooldown, weights, payouts, table sizes,
  page names and timings come from today's kit and Format page (`bot/rules.json`). A rehearsal is announced to
  both sessions at its start, and Sunday starts from a fresh repo.
- **Every test ran at the wrong table size** (an earlier rehearsal). → The rules card is written at minute 0 from
  the kit and the Format page, `tester` checks it, and every test reads it.
- **Agents used the last rehearsal's data until caught** (simulations). → Facts about rounds come only from
  `state/status.md` and `data/rounds/`, with their time.
- **Agents heard about new data only after the round card ran, and a failing fingerprint script held the card
  back** (eval round 1). → Start the moment the watcher posts "DATA LANDED": the card, fingerprinting and the
  analyses run side by side, and one failing never blocks the others. RESEARCH briefs `analyst`, `scout` and
  `tester` whether or not the card ran.
- **"Data landed" was counted before the hand file arrived, and an empty result right after a round was called a
  forfeit** (eval round 2). → Data has landed when the hand file is in `data/rounds/<NN-stage>/` and opens. An
  empty result just after a round means "not yet". A forfeit shows as our row with 0 tables, or our failed
  decisions in the hand file: urgent, to both humans.
- **A practice result could be credited to the wrong bot** (audit). → The bot that played is the one active when
  the round started (`data/rounds/<NN-stage>/played_by.txt`), never the one we meant to play.
- **The round card ran without the analysts' Python packages** (audit: the system `python3` had no numpy). → Run
  `analysis/roundcard.py` once by hand the way the watcher runs it, on practice 1's data at the latest.
- **A stray "it starts now" put the clock 6 minutes off for the rest of a simulation** (eval round 2). → Only a
  human's words set the clock (one exception: with no clock started, RESEARCH starts it from the watcher's "THE
  VARIANT IS ANNOUNCED" line, which carries the portal's own time for minute 0). When a scored round really starts at
  another time, pin it
  (`python3 scripts/clock.py pin scored<k> HH:MM`); never move minute 0 after round 1.
- **A hidden leaderboard switched off the checks** (audit). → Standings hidden: work out our total from each
  round's results and weights; if that's impossible, treat us as outside the top 3 (`DECISION_RULES.md` §3).
- **A silent portal went unnoticed** (audit). → No round seen 8 minutes after an expected start, or
  `state/status.md` going stale during a round: tell both humans (the watcher may be down, or the round delayed).

## Decisions and uploads

- **Practice picks were never declared, so nobody asked Dylan to upload** (prac1). `platform` released v3 for
  practice 1, nothing declared it, and Dylan was never asked. → BUILDER declares every pick, build-hour practices
  included, never a window's challenger, with `python3 scripts/live.py vN "why"`, and asks Dylan in its terminal
  with the exact file (for the challenger too, at T-12, without declaring it). The clock's reminder 3 minutes
  before each practice is the backstop, not the plan.
- **"Built" was shown for a bot with no zip** (prac1). The tester marked v3 ready after testing it, but `platform`
  hadn't packed it. → A bot can be uploaded only when `releases/vN.zip` and its line in `releases/VERSIONS.md`
  exist. "Tested" (`tester`'s verdict) is not "released". Dylan is only told to upload a file that exists.
- **One plan challenge became 3 alerts and 2 separate decisions** (prac1). → One challenge, one entry in
  `state/decisions.md`, written by RESEARCH; BUILDER adds its view to that entry. Each human hears it once, in
  one line.
- **A "contradiction" model guessed wrong, again and again** (prac1). It flagged "declared v3, active v6" all
  through the build hour (a practice pick was meant to be active) and garbled the stage. → No model guesses at
  contradictions; compare the files. `state/live.json` against the active bot in `state/status.md`, at T-3 and
  just after each round starts. During a practice, the practice pick is the right bot.
- **The rule's answer was never applied at T-5** (audit), and older docs said "no answer means the live bot
  plays". → With no clear human answer by T-5, BUILDER applies the rule's answer itself, and it may be the
  challenger. "No change" is not the default.
- **Two humans gave opposite answers and one silently won** (audit). → Say so to both; the rule's answer stands
  until they agree.
- **A conditional yes ("once the tester passes it") triggered the upload at once** (eval rounds 1-2). → A
  conditional answer is recorded when its condition holds; until then the deadline and the rule's answer apply.
- **An untested zip could be chosen at T-4, and a rejected upload stayed "live"** (audit). → Only a zip with its
  upload-test numbers in `releases/VERSIONS.md` is declared for a scored round. After a rejection the previous
  bot stays active: BUILDER re-declares it, and Dylan uploads nothing until `platform` has a fixed, tested file.
- **The recommendation raced the question at T-8, and the rule's answer was left to two hurried hand
  calculations** (audit). → RESEARCH's recommendation is due at T-9. `tester` computes the yardstick comparison
  before the practice lands, the threshold goes first, and the final answer follows the moment the practice
  lands.

## Humans and noise

- **Screen overload** (prac1): flashing edges, piled-up pop-ups, a huge decision box and false "doesn't add up"
  posts; Samuel couldn't tell what was going on. → Tell the humans less, better: one line per point. A decision
  in plain words: what, the evidence in two lines, what each answer means, the deadline, the rule's answer. A
  plan challenge is one line, never urgent. Urgent is only a rejected upload, no or the wrong active bot, or a
  decision due in under 3 minutes.
- **Stale instructions kept coming** (eval rounds 1-2: "upload v3 now" after v4 went live; "which bot played
  isn't confirmed" after it was). → Before telling Dylan to do anything, re-read `state/live.json` and
  `state/status.md`. Say each request once, with its time; never repeat one that's done or overtaken.
- **A summary called a rejected bot "the challenger"** (eval round 1). → Never give a bot a role the files don't
  state.
- **Agents asked for things nobody can see** (simulations). → Ask a human only for what only a human can do or
  decide: uploads and activations, the decisions, facts nobody else can see. Never ask them to run a command,
  relay a message or check something you can check. (`CLAUDE.md` §5)
- **Permission prompts slowed everyone down** (prac1). → Commands run without prompts; a hook refuses the
  dangerous few. A refused command means find another way, not try again.

## Strategy process

- **A change aimed at a 74.6% fold-to-3-bet rate played at 92.8%** (eval round 1). Only "the branch fired" was
  checked. → A change that targets a rate shows that rate in a local run, within about 5 points, before it
  ships (`DECISION_RULES.md` §3).
- **v1-v10 limped and flat-called because nothing checked** (simulation 1); the leak was still there in scored
  round 1. → The defaults check runs in every check run and heads every round analysis: open-limp rate, flat
  calls of opens at 10bb+ outside the big blind, first-in non-shove raises under 12bb, one-pair calls of raises.
  A style that breaks one says whether it's intended.
- **Local +4.4 was 100th of 125 on the real field** (regional, v4): our old versions folded to aggression and the
  field didn't. → Local play is for legality, speed and sanity; the practice rounds judge strength. Wins against
  our own bots prove nothing.
- **The kit's ICM zeroed busted players** (regional): our bot folded winning calls for two rounds. → Unit-test
  every library function a decision depends on, with edge cases: 2 and 3 players left, a busted player in a
  paid place.
- **Folds to our own bets were never counted, and a raise-frequency rate was inverted** (regional, v10). → A
  scripted event sequence with a known answer for every statistic; every rate between 0 and 1; opponents'
  responses to our own actions counted.
- **The flop over-calling leak played through round 2, though the data to catch it existed after the first
  practice round** (regional). → Analyse real hand histories from the first practice round on.
- **Our cautious calls cost the most** (regional: a stats band on releases blocked a winning feature; a freeze on
  the fold rules kept a costly leak through rounds 3-6). → Never block a change for looking unusual; standing
  still is not safe.
- **The plan locked a style while the field moved** (regional). → The challenger line, the field trend on every
  download and PLAN CHALLENGES (`DECISION_RULES.md` §3). In sim7 this worked: after practice 1 the opponents
  agent (today's `scout`) found both rivals folding 81-92% to 3-bets against the plan's 60-70%, and the
  challenger built the counter.
- **The build hour was over-scripted** (audit: practices forced to A, B, C in turn; the challenger idle until
  minute 40). → Each build practice plays the most informative test; one is design D, built from scratch from
  minute 0.
- **The T-8 comparison was confounded** (audit: the challenger's practice and the live bot's scored round faced
  different fields). → Compare both against yardstick teams (`DECISION_RULES.md` §3).
- **The docs disagreed with each other** (audit: three definitions of the challenger, two defaults for an
  unanswered decision, a release gate that would have blocked the regional winner). → `DECISION_RULES.md` wins
  over every other document.

## From the 14 November speedrun (a timed build hour on an unseen variant, this bundle)

- About 12 agents running simulations locally pushed the load to 50 on 12 cores; the kit's do-nothing bot then failed
  timing tests too. **Rule:** about 6 local workers a session, handed out by the session (2 a subagent as a rule, never more than 4), long runs on Modal, and a timing or upload test
  counts only with load below the core count and `check_or_fold` run in the same minute.
- Five agents re-derived the variant's hand ranking with their own simulations and disagreed. **Rule:** `theory/out`
  is the single source of equity truth; BUILDER broadcasts the first variant-level finding at once.
- Releases came every 4 minutes and verdicts lagged; a release with no verdict shipped a heads-up regression
  (-1.9 ± 0.4). **Rule:** one tester per release; no scored round without a verdict that includes a heads-up run.
- Five silent fallbacks in 20 minutes (a missing key used a default table, a repack kept the old zip, the packer
  dropped tables for size, a renamed setting switched a feature off, the kit's ICM zeroed a busted seat). **Rule:**
  fail loudly; aliases for renames; INTERFACE diff after every release.
- The stylists idled 6 minutes waiting for the interface. **Rule:** a stub `bot/INTERFACE.md` by minute 6.
- The data path had only been tested on the kit's 7-table sample; a synthetic round found three bugs (truncated file
  crash, 8-max position labels, a folder collision). **Rule:** the dry-run download at about minute 10, into
  a fresh `/tmp/dryrun-<HHMM>/` (never `data/rounds/`).
- The theory agents finished by minute 12 and then idled. **Rule:** tighter targets and a second wave.
- In that variant the kit's do-nothing bot scored as well as ours in a field that busts itself. **Rule:** every
  verdict reports the floor bot; if folding is that strong on the real field, it's a PLAN CHALLENGE.
- A fresh repo ignored `.claude/settings.json` until the folder was trusted. **Rule:** START.md step: trust it once.

## From the 14 November checks against the real portal (read-only, the regional's finished rounds)

- The watcher's hand-download address was a guess copied from our own rehearsal portal; the real portal answered it
  with 404. The first-1000 query was a guess too: the real portal ignores a query it doesn't know and sends the full
  270 MB file. One `--once` against the regional's rounds found both, a day early. **Rule:** whatever talks to the
  organizers' systems is checked against the real thing before the day (GET only), never only against our copy of
  it; a download is judged by its size and checksum, not by "it answered 200".
- A watcher started while our key still listed only the regional would have stayed on the regional all day: it asked
  "which competition?" once, at start-up. **Rule:** a script that runs for hours re-checks what it assumed at
  start-up. The watcher now follows the key by itself and says "not today's event" until the Finals appears.
- The watcher's "start fresh" state shared its lists with the old state, so after a switch the first Finals round
  would have been filed as round 16 with the regional's rounds marked done. A test of the switch itself found it.
  **Rule:** test the transition, not only each side of it.
- The Format page saved before Bay Area said "An upload alone does not activate it", and the bundle was built on
  "upload, then a click". The Getting started page of the same week and both of Boston's pages say a passing upload
  becomes active by itself. **Rule:** a fact about the platform is re-read on the day's own pages and settled by one
  observation (v1's upload, minute 10); until then every step is written to be right in both cases, and the active
  bot is confirmed in `state/status.md` after every upload and every click.
- The portal's API states the upload cooldown, the announcement time and the variant's rules text; we had planned
  to read all three off web pages by hand. **Rule:** take a fact from the system that owns it (`state/status.md`,
  `state/variant.md`) and keep the human reading as the cross-check.
