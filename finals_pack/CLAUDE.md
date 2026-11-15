# Team avalon at the No Limit Finals: read this first (every Claude, every session)

Sunday 15 November 2026, San Francisco. 21 teams (the portal's Finals list on 14 November) build poker bots live with AI agents. The variant is announced at
minute 0 with a starter kit; then a build hour with 4 practice rounds, then about 6 scored rounds 20 minutes apart,
each with a practice round 10 minutes before it at Bay Area (the organizers' pages promise practice rounds only in the
build hour: §8). Only the top 3 teams are paid ($100,000 / $50,000 / $25,000): 4th
is worth the same as last. (50/30/20 is something else: the points a table gave its 1st-3rd at the regional. The
Finals' points per place are announced with the variant.) Humans: **Dylan** (steers BUILDER, uploads bots on the portal) and **Samuel** (steers RESEARCH).

## 1. Who runs where

Everything runs on one laptop, in this repo, in Claude Code. Two main sessions, each with its own subagents:

| Session | Steered by | Owns | Spawns (subagent types in `.claude/agents/`) |
|---|---|---|---|
| **BUILDER** | Dylan | the bot: engine, styles, releases, which bot plays (asks the humans), what Dylan uploads | `platform`, `stylist`, `challenger`, `bughunter` |
| **RESEARCH** | Samuel | the maths, each round's data, testing, opponents, the field trend, the T-9 recommendation | `theory`, `analyst`, `tester`, `scout` |

Two scripts do the mechanical jobs (started by a human in their own terminal tabs; never by an agent):
- `scripts/clock.py run`: the schedule. At each step it posts what to do to the right session's inbox.
- `scripts/portal_watch.py`: reads the organizers' portal (read-only). Saves results and hand data under `data/`,
  keeps `state/status.md` current (active bot, standings, rounds) and posts every event to the inboxes: results, the
  announcement and anything urgent to both; "DATA LANDED" and the card runs to RESEARCH only.

Your own start-up instructions are in `prompts/BUILDER.md` or `prompts/RESEARCH.md`.

## 2. How sessions hear things: one inbox each

- `inbox/builder.log` and `inbox/research.log`: append-only. The clock, the portal watcher and the other session all
  write there. Each main session keeps **one Monitor** running on `python3 scripts/feed.py <builder|research>`: it
  prints each new inbox line, and each line wakes you. A long line (a clock step with its TASKS) can arrive cut off in
  the event: read it whole with `tail -n 3 inbox/<builder|research>.log` before you brief from it. The Monitor expires (after 30 minutes at most): **re-arm it every time
  it does**, at once, before anything else.
- **Session to session:** use Claude Code's cross-session messaging: `ListAgents` finds the other session,
  `SendMessage` reaches it at once (it wakes it). One message per point, with numbers and file paths; never
  acknowledgements or thanks. Then log a one-line copy for the record: `python3 scripts/say.py --record <to> "<text>"`
  (writes only to `state/events.log`, so it doesn't arrive twice). If cross-session messaging isn't available, use
  `python3 scripts/say.py <builder|research> "<text>"`, which lands in the other session's inbox. (A message from a
  session in a different permission mode is held until a human approves it: if the other session doesn't react to
  something it should, send it again with `say.py` and tell your human.)
- Subagents never write to inboxes; they report to whoever spawned them.

## 3. Files: where everything lives

| Path | What | Written by |
|---|---|---|
| `strategy/` | the plan and the research (read-only on the day): `DECISION_RULES.md` (how we decide: always applies), `PLAN.md` (the game plan + timeline), `FIRST_PROMPT.md` (the build prompt pack), `TWIST_NOTES.md`, `FINGERPRINTING.md`, `EVIDENCE_TABLE.md`, `LESSONS.md` (what broke in rehearsals) | humans, before the day |
| `state/status.md` | the portal right now: active bot, rounds, standings, last results, the upload cooldown the portal states | portal watcher |
| `state/variant.md` | the variant's rules text as the portal's own API gives it, saved the moment it is announced, with the portal's time for minute 0. A head start while the kit unpacks: the kit and the Format page still decide the rules card | portal watcher |
| `state/schedule.json`, `state/clock.md` | minute 0, the round times, the next steps | clock |
| `state/live.json` | the bot we have **decided** should be active next: each build-hour practice pick, then the round-1 bot, then each scored round's bot (never a window's challenger: BUILDER tells Dylan that file directly) | BUILDER only: `python3 scripts/live.py vN "why"` |
| `state/decisions.md` | every decision asked of the humans: question, evidence, the rule's answer, deadline, the human's words, outcome | BUILDER (bots), RESEARCH (plan challenges): each appends under its own dated heading and never rewrites the other's entry |
| `data/rounds/<NN-stage>/` | `results.json`, `round.json`, `hands-first-1000.jsonl.gz`, then `hands-full.jsonl.gz`, `played_by.txt` | portal watcher (never in git) |
| `notes/format.md` | the organizers' Format page as Dylan pasted it at minute 0 (weights, payouts, cooldown) | BUILDER |
| `bot/` | the platform (the bot's shared code) | `platform` only |
| `candidates/<name>/` | styles, the challenger, fixes, each in its own folder | `stylist`, `challenger` |
| `releases/vN.zip` + `releases/VERSIONS.md` | every released bot (zips stay local, git-ignored); one line each: commit, the zip's sha256, what changed, checks, role, and a pointer to the tester's verdict, which lives in the tester's own `rig/out/verdict-vN.md` | `platform` only (the verdict file: `tester`) |
| `theory/out/*.json` + `theory/HANDOFF.md` | today's maths tables (ranking, ICM, push/fold, twist, break-evens): **the single source of preflop and equity truth**. Everyone reads them; nobody re-derives them (only the clean-room design D may compute its own) | `theory` |
| `starter-kit/.venv/bin/python` | **the team's Python** for anything that needs the kit's SDK or its evaluator (set up once at minute 0 by `platform` and announced; system `python3` may not build the evaluator). It has no `modal` package: Modal jobs are launched with the `modal` command (`modal deploy`, `modal run`), whose own Python has no kit, so the kit's code runs only inside the image, built from the kit's requirements | `platform` |
| `analysis/` | parsers, `roundcard.py`, `fp_train.py`, `field_trend.py`; per round `analysis/<stage>/card.md`, `field_trend.md`, lens reports, where `<stage>` is the stage name with spaces as '-' (`analysis/Practice-1/`, `analysis/Round-2.5/`) | `analyst`, `scout` |
| `rig/` | the test rig: paired runner, sparring bots, Modal fan-out | `tester` |
| `notes/LEDGER.md` | what the team knows: one line per result (id, claim, effect ± se, n, method, file, status) | everyone appends; `tester` marks validated/disputed |
| `notes/PLAN-builder.md`, `notes/PLAN-research.md` | each main session's own plan and memory (survives compaction) | each main session |
| `notes/pre/` | the pre-event research: drafted on Saturday 14 November, then checked and extended in place on the morning, never rewritten (`stat_definitions.md`: how every field rate is counted). RESEARCH merges it into `notes/plan.md` | Saturday's drafts; subagents extend them before minute 0 |

The source lists in `strategy/` and `notes/pre/` name files in the team's archive (`research/`, `docs/`, `rebuild/`,
`emu/`, `data/hands/`, `prep/`): that is another repo. None of those files is here and nothing today needs them;
a path written `finals_pack/<x>` there is `<x>` here.

Grades: the notes and `EVIDENCE_TABLE.md` mark a claim **A** when it was measured at the regional. On the scale that
licenses action today (`DECISION_RULES.md` §4) the regional alone is a **C**, a starting value, until today's rounds
confirm it.

## 4. Hard rules (these never bend)

1. **Every uploaded bot is legal and fast**: zero failed decisions in the checks, the kit's check passes, and it
   passes the upload test with no time bank (2 players, 20 hands, time bank 0). A failed decision (timeout, error,
   illegal action) checks when checking is free and otherwise folds (§8).
2. **Only tested zips are released and uploaded.** A tested bot is active by T-3 of every scored round. Each round
   plays the bot that is **active when it starts**. On the Finals' own pages an upload that passes its test becomes the
   active bot by itself, and a click is what puts an earlier upload back; at Bay Area every activation was a click
   (BUILDER settles which holds after v1's upload, §8). Either way: upload nothing inside a window that is not meant to be the next bot to play (a zip uploaded "to have it ready" would replace the active bot),
   an upload is active only when its test has finished, and the active bot is confirmed in `state/status.md` after
   every upload and every click.
3. **The rules card is right**: players per table, stacks, blinds and antes, hands per match, weights, payouts and the
   upload cooldown come from the kit and the Format page (`bot/rules.json`, written by `platform` at minute 0). Table
   rules are set per round and an organizer can change them between rounds: the bot reads them from `state.config` at
   every table and hard-codes none, and each round's settings are compared with the round before (§8). What the
   portal itself states (the cooldown in `state/status.md`, the rules text in `state/variant.md`) is a cross-check:
   a mismatch goes to Dylan at once.
4. **No pre-written bot code** (everything bot-related is written today); hand histories never go into git.
5. The organizers' portal is read-only for agents. Only Dylan uploads.
6. **Never kill processes by name or pattern** (`pkill`, `killall`, `pgrep | xargs kill`): every Claude process's
   command line contains these instructions, so a pattern like `pkill -f "modal run"` kills every agent. Stop only
   what you started, by PID (`cmd > log 2>&1 & echo $! > /tmp/<job>.pid`; later `kill $(cat /tmp/<job>.pid)`; put your role and target in
   `<job>`, as in `/tmp/tester-v7-mix.pid`: every agent of a session shares `/tmp` and the scratchpad) or
   `modal app stop --yes <id>` (without `--yes` it asks for confirmation and aborts when there is no terminal). A hook
   refuses pattern kills. The same hook refuses recursive deletes outside the repo and `/tmp` (or of a whole shared
   folder), `git stash`, `git reset --hard`, `git clean -f`, force pushes, `sudo`, Modal deletes and any write to the
   organizers' site. A refused command means find another way (leave the folder, use a new name), not rephrase it.
7. **Never block your turn**: no foreground `wait`, no `sleep` of 20 s or more, no loops that poll (the hook refuses a shell loop that sleeps, also
   as a Monitor's command: a watcher there must be a script, as `scripts/feed.py` is). What is allowed, and is the way to
   be woken when a file appears or a job ends: a one-shot in the background that exits on a condition, as a Bash call
   with `run_in_background: true` (`until [ -f releases/v1.zip ]; do sleep 3; done`); you are notified when it exits. A
   subagent waits for its own job the same way, and carries on with other work meanwhile. The hook adds up the
   pauses in one command and reads quoted text too: a note containing "until" or "while" and a pause word is refused
   as a loop, so put such text in a file with the Write tool. Start long jobs in the
   background with a log, end your turn, and check when woken. Main sessions: spawn subagents in the background
   (the default from a main session; say `run_in_background: true` if asked), so you stay free for the humans and
   the inbox.
8. **Modal**: two deployed apps only, `avalon-rig` (the tester's, up to 40 containers) and `avalon-theory` (theory's, up
   to 20), each deployed once and called many times with `.map`, and launched with the `modal`
   command, never with the team Python (it has no `modal` package); every other role calls them or runs locally (20
   containers between them).
   Never launch several `modal run`s at once: the workspace has an app-creation rate limit, and a rehearsal lost a
   round to it. Shared cap: 80 containers.

## 5. Humans

- A human's message is an instruction: do it first. Your reply's **first sentence answers them** (or says
  "Working on it: <what>, ready by HH:MM"), then report when it's done. Never just start working silently.
- Talk like a sharp teammate: plain words, numbers with how sure we are, who's doing what, what the human needs to
  do (or "nothing right now"). Short. No ids or jargon.
- If `state/status.md` or `state/clock.md` is more than 2 minutes old, a script stopped: tell your human "tab 1 (or 2)
  stopped: run it again" (START.md). Never start `portal_watch.py` or `clock.py run` yourself.
- Organizer announcements reach only a human: they show as a banner in a signed-in browser, and the API key cannot
  read them (403). When a human reads you one, check the rules card, the clock and this window's plan against it and
  tell the other session at once.
- Ask a human only for what only a human can do or decide: uploads and activations (Dylan), the decisions in
  `DECISION_RULES.md`, and facts nobody else can see. Never ask them to run a command, relay a message or check
  something you can check.
- **Decisions** are asked in plain words in the session's terminal: what's being decided, the evidence, what each
  answer means, the deadline, and the rule's answer, which plays if nobody answers in time. Record them in
  `state/decisions.md`.

## 6. The plan is a default, not a mandate

Everything in `strategy/` was written before anyone saw today's variant or this field. Strong teams will do things
nobody predicted, and the field moves every round. If today's data says a better path exists, take it: raise a
**PLAN CHALLENGE** (`DECISION_RULES.md` §3). Only the hard rules above never bend. At the regional, our plan locked a
style and we only made small fixes while the field moved; the Challenger and the field trend exist so that doesn't
happen again.

## 7. Working style

- **Share what changes everyone's work at once.** The first variant-level finding (e.g. "pocket pairs are the worst
  hands in this variant") goes to every agent building strategy the moment it's known, so nobody re-derives it.
- **Fan out.** The day is time-boxed; serial work loses. Independent pieces run in parallel: several subagents in
  one message (each in its own folder), Modal for compute (the two deployed apps), Codex (`codex exec`) for second opinions if logged in (if one call
  fails on a rate limit, drop Codex for the day).
  Subagents may spawn their own helpers, in the background whenever the spawner has other work (a foreground
  helper cost one theory run 4.7 minutes; nesting stops at 3 levels; at most about 4 helpers each, one job and one
  output file per helper). Up to 40 subagents can run at once per session (`.claude/settings.json` sets
  `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=40`; the default is 20); past that a spawn fails, so finish or stop idle ones first.
- **Brief subagents like new teammates**: objective, exact input files, output (files plus a report of at most 300
  words with paths), what not to touch, a time limit. Point them at their role file and the strategy docs.
- **Results go to files**, and the report is a summary plus paths. Record every measured result in
  `notes/LEDGER.md` with effect ± se, n and method. Weak evidence is a hypothesis, never a finding.
- **Check before you trust**: re-run, don't re-read. Local wins don't predict the field; the practice rounds do.
- **The laptop's CPU is shared by every agent of both sessions** (a speedrun hit load 50 on 12 cores, and then even
  the kit's do-nothing bot failed timing tests; in a second run four agents at 4 workers each put this laptop's 15
  cores at load 17-19 by minute 8 and v1's upload test was inconclusive). Each **session** keeps its subagents' local worker processes to about 6 in all
  and enforces it itself: every brief gives a worker count (2 unless the session says otherwise, never more than 4),
  and the session checks `uptime` before any timing test and whenever it adds an agent; Monte Carlo or
  match runs longer than about a minute of CPU go to Modal (the two deployed apps, hard rule 8). A timing or upload test counts only
  if `uptime` shows load below the core count AND the kit's `check_or_fold` example runs in the same minute as a
  baseline; otherwise say "inconclusive: machine loaded" and re-run. A request
  for a quiet window ("nothing heavy locally until HH:MM") means no local match or Monte Carlo runs; Modal clients,
  one light process each, carry on, and nobody stops work altogether. On this Mac a script that starts a process
  pool needs an `if __name__ == "__main__":` guard (without it, it forks in a loop), and there is no `timeout`
  command: cap a job inside Python or stop it by its PID.
- **Silent fallbacks are bugs.** Every loader, packer, setting and table lookup fails loudly on a mismatch (unknown
  setting names, missing keys, a dropped file, a zip that wasn't overwritten). A speedrun had five silent fallbacks
  in 20 minutes, each switching off a feature without a sound.
- **Run `date` before you write a time down**; never estimate the clock.
- **Nothing wakes an agent at a clock time.** A main session acts at a time only because a line arrives then: the
  clock posts every step and cut-off, the watcher every round start and result. If something must happen at a time
  that has no clock step, tie it to the step before it or ask your human to say it; never plan to "come back at
  HH:MM" (both timed runs missed their stop that way). A subagent's time limit is kept by the subagent itself, with
  `date` at each step, and checked by the session that spawned it on every wake-up.
- **A file named in your brief** (`REPORT.md`, `card.md`, `DESIGN.md`, ...) **is a requested deliverable: write it.**
- **Keep your PLAN file current** (`notes/PLAN-<session>.md`; its first line names your role and prompt file):
  what's running where, open promises, next deadline. **After compaction or a restart, first re-read your prompt file
  (`prompts/BUILDER.md` or `prompts/RESEARCH.md`)**, then your PLAN file, `state/status.md`, `state/clock.md` and the
  tail of your inbox before acting, and re-arm your Monitor.
- Facts about rounds (started, finished, results, active bot) come only from `state/status.md` and `data/`, with
  their time. Never assume a round is running.

## 8. Which table we play: case F (main) and case R (fallback)

Decided by Dylan on Saturday 14 November: the team prepares for **case F**, the Finals defaults in the portal's own
code, as the main case, and keeps **case R**, the regional's table, as the fallback. Neither is announced. The Finals'
Format page on Saturday afternoon still showed case R, but it is the shared template and no round had been set. The
kit's `state.config` and `RULES.md` and the Format page decide at minute 0: the first line of `platform`'s rules card
says which case holds (F, R, or what differs from both), and BUILDER tells every agent and RESEARCH at once.

| | Case F (main) | Case R (fallback) |
|---|---|---|
| Seats and stack | 6 players, 6,000 chips: 300 big blinds at hand 1 | 8 players, 2,000 chips: 100 big blinds |
| Blinds and antes | 12 levels of 20 hands, 10/20 to 2,000/4,000, each with an ante of 20% of the big blind from the first level (4 at 10/20; the format note counts it per player: check the kit's engine) | the same levels, no ante |
| Hand cap | 250 | 250 |
| Points per place | probably 50/30/20, which pays half the table (not part of the code's default) | 50/30/20: 3 of 8 paid |
| An iteration, with 21 teams | 4 tables, 3 filler seats | 3 tables, 3 filler seats |
| The field's mean score | 16.7 a table | 12.5 |
| Tables one opponent shares with us | about a quarter: roughly 250 of 1,000 | about a third: 300-350 |
| Equity to call all-in, equal stacks | 58.1% on hand 1; 60.6% with 5 left, 65.2% with 4, 57.1% with 3, pot odds heads-up | 55.6% on hand 1; the same from 4 left down |
| Hands a table | about 155 simulated with regional bots, 163-174 measured in a timed run; a seat is dealt 105-115 | about 131; a seat is dealt 90 |
| One bot's spread a table; paired noise | 18.9; about 22/√tables (estimate: measure it) | 17.9; about 21/√tables |
| Sparring field | five copies beside the candidate | seven |
| Rig speed | about 0.9 of the case-R rate (estimate: time the first job) | as measured in `tester.md` |
| A bot that only folds | out near hand 121, about 11 of 16.7 (simulated) | out near hand 102, about 7 of 12.5 |
| Round weights | linear, 1 to 6, as of Saturday afternoon | 1 to 6 at Bay Area |

The case-F column is arithmetic, or simulation on the regional kit's engine, from `notes/pre/format_finals.md`, which
also gives what changes for the bot: depth by level, prices with the ante, where shove-or-fold starts. Everything else
in `strategy/` and `notes/pre/` was measured in case R: a figure with no case label is a case-R figure, to be
recomputed from the rules card in case F. Fillers are non-scoring copies of bots not already at that table; they
still take finishing places.

**Rules are per round** (the portal's round schema; how often organizers use it is unknown). Between rounds an
organizer can change the table rules (seats, stack, blinds and antes, payouts, time limits), the iterations, the
round's multiplier, culling and ICM luck correction. The bot hard-codes none of them; `scout` reports what changed
from the round before on every download.

**Culling, if a round has it switched on, is an early stop inside that round, not elimination.** The round looks
every so many iterations and stops dealing tables to teams it is confident are outside its top places; such a team is
shown as "Culled at look k". Its round still scores, on the tables it played, and it plays every later round as
normal (read from the portal's code; it was off at the regional). For us: fewer tables that round, so a noisier
score, and nothing else: no rule or bar changes.

**The last round may be dark, and the leaderboard can be held at any moment** (read from the portal's code; neither
was used at the regional, and neither was set for the Finals on Saturday afternoon). If the competition names a final round (`final_weight` in `state/portal.json`,
`comp_settings`), that round's results and our own bot's health report are held until the organizers reveal them:
nothing from it reaches us. When the leaderboard is held, the standings are hidden and every round that finishes
during the hold has its results held too, practice rounds included. What we do is already written: with the
standings held, `tester` works them out for all 21 teams from each round's results x weights, and only if that can't be
done do we count as outside the top 3, and with no practice result by T-6 the
rule's answer is the live bot (`DECISION_RULES.md` §3, `prompts/RESEARCH.md`).

**Round multipliers.** A round's points count times its multiplier, and the series is one of three: linear (1 to
6, Bay Area), Fibonacci (1, 2, 3, 5, 8, 13: Boston and Pittsburgh) or powers of two (1 to 32). The last round is then
29%, 41% or 51% of the total, and every rule that counts "share of the weight played" moves with it. The Finals
competition was set to linear, 1 to 6, on Saturday afternoon, and its Format page showed 1x to 6x; an organizer can
change it for any round not yet started. Re-read `round_weighting` in `state/portal.json` (`comp_settings`) and the
Format page at minute 0; never assume.

**What the organizers' own pages say.** From the Boston regional's "Tournament format" and "Getting started" pages
(9 November). The Finals are "the same tournament format with a different poker variant", so this is the best
statement of the platform's rules: re-read Sunday's own pages at minute 0.
- A failed decision (a timeout, an error, an illegal action) checks when checking is free and otherwise folds; in a
  phase the variant adds it takes that phase's automatic choice. It does not always fold.
- Scored play has a time bank: 100 ms a table by default (`state.config.time_bank_ms`); one timeout empties it and
  each table starts with a full one. The upload test has none: a heads-up match of up to 20 hands at the 1 ms limit
  against a check-or-fold bot, rejected if the bot does not start within the start-up allowance, crashes, or fails
  more than 10% of its decisions. Our own bar stays zero failed decisions (hard rule 1).
- Payouts can be drawn per table inside one round, and a round can change the table defaults: the bot reads
  `state.config.payouts` (and the rest of `state.config`) at every table. At the hand cap the bots still seated
  split the remaining points by ICM on their stacks.
- The server does not repair an action. A raise outside the legal range is a failed decision, not clamped, and a
  computed size is rounded down, so a raise one chip short of the minimum, facing a bet, becomes a fold. A copy of the
  bot that crashes or keeps answering late is restarted only a limited number of times a round; after that its
  remaining decisions on that machine play the fallback for the rest of the round.
- Practice rounds are described only for the build hour ("about 1,000 iterations every 10 minutes"). A practice
  round before each scored round is not promised; Bay Area had them. A scored round runs at least 5,000 iterations,
  one table a bot per iteration, and its results "normally arrive in the following 20-minute window": data can land
  later than the timeline's T-13. A window with no practice round has no practice result, and then, as already
  written, the rule's answer is the live bot (`prompts/RESEARCH.md`).
- A tie on the final total is broken by countback: each team's share of tables won in each scored round, times
  that round's multiplier, summed; then the same for 2nd places, and so on. Nothing is decided by chance. A
  disqualified team has no rank and sits out later rounds.
- The upload cooldown on those pages is 30 seconds, the value the regional's API gave and the Finals competition
  showed on Saturday afternoon. What limits a late
  upload is its test, which must finish before the round starts, not the cooldown.
- **An upload activates itself, by the Finals' own pages.** The Finals' Format and Getting started pages (read signed
  in on 14 November), like Boston's: an upload that passes its test match becomes the active bot automatically, unless a newer upload is already active or
  the competition is frozen or over; an earlier upload is chosen on the team page. The Format page saved before Bay
  Area said "An upload alone does not activate it", and that night every activation was a click; that sentence is
  gone from the Finals' page. The bundle is still written for both, and the first upload is still checked. BUILDER settles it at about minute 10: after v1's upload is ready and before any click, it reads
  the active bot in `state/status.md`, tells Dylan and RESEARCH which case holds and records it in `notes/format.md`.

More, with what it changes for the bot: `notes/pre/format_finals.md`.
