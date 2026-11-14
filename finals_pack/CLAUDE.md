# Team avalon at the No Limit Finals: read this first (every Claude, every session)

Sunday 15 November 2026, San Francisco. 20 teams build poker bots live with AI agents. The variant is announced at
minute 0 with a starter kit; then a build hour with 4 practice rounds, then about 6 scored rounds 20 minutes apart,
each with a practice round 10 minutes before it. Only the top 3 teams are paid ($100,000 / $50,000 / $25,000): 4th
is worth the same as 20th. (50/30/20 is something else: the points a table gave its 1st-3rd at the regional. The
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
| `state/decisions.md` | every decision asked of the humans: question, evidence, the rule's answer, deadline, the human's words, outcome | BUILDER (bots), RESEARCH (plan challenges) |
| `data/rounds/<NN-stage>/` | `results.json`, `round.json`, `hands-first-1000.jsonl.gz`, then `hands-full.jsonl.gz`, `played_by.txt` | portal watcher (never in git) |
| `notes/format.md` | the organizers' Format page as Dylan pasted it at minute 0 (weights, payouts, cooldown) | BUILDER |
| `bot/` | the platform (the bot's shared code) | `platform` only |
| `candidates/<name>/` | styles, the challenger, fixes, each in its own folder | `stylist`, `challenger` |
| `releases/vN.zip` + `releases/VERSIONS.md` | every released bot (zips stay local, git-ignored); one line each: commit, the zip's sha256, what changed, checks, role, the tester's verdict | `platform` only |
| `theory/out/*.json` + `theory/HANDOFF.md` | today's maths tables (ranking, ICM, push/fold, twist, break-evens): **the single source of preflop and equity truth**. Everyone reads them; nobody re-derives them (only the clean-room design D may compute its own) | `theory` |
| `starter-kit/.venv/bin/python` | **the team's Python** for anything that needs the kit's SDK or its evaluator (set up once at minute 0 by `platform` and announced; system `python3` may not build the evaluator) | `platform` |
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
   plays the bot that is **active when it starts**. Making an already-uploaded bot active is a click on the portal.
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
   what you started, by PID (`cmd > log 2>&1 & echo $! > /tmp/<job>.pid`; later `kill $(cat /tmp/<job>.pid)`) or
   `modal app stop --yes <id>` (without `--yes` it asks for confirmation and aborts when there is no terminal). A hook
   refuses pattern kills. The same hook refuses recursive deletes outside the repo and `/tmp` (or of a whole shared
   folder), `git stash`, `git reset --hard`, `git clean -f`, force pushes, `sudo`, Modal deletes and any write to the
   organizers' site. A refused command means find another way (leave the folder, use a new name), not rephrase it.
7. **Never block your turn**: no foreground `wait`, no `sleep` of 20 s or more, no loops that poll (the hook refuses a shell loop that sleeps, also
   as a Monitor's command: a watcher must be a script, as `scripts/feed.py` is). Start long jobs in the
   background with a log, end your turn, and check when woken. Main sessions: spawn subagents in the background
   (the default from a main session; say `run_in_background: true` if asked), so you stay free for the humans and
   the inbox.
8. **Modal**: one app per purpose (deploy once and call it many times, or one `modal run` that fans out with `.map`).
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
  one message (each in its own folder), Modal for compute, Codex (`codex exec`) for second opinions if logged in (if one call
  fails on a rate limit, drop Codex for the day).
  Subagents may spawn their own helpers (nesting stops at 3 levels; at most about 4 helpers each, one job and one
  output file per helper). Up to 40 subagents can run at once per session (`.claude/settings.json` sets
  `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=40`; the default is 20); past that a spawn fails, so finish or stop idle ones first.
- **Brief subagents like new teammates**: objective, exact input files, output (files plus a report of at most 300
  words with paths), what not to touch, a time limit. Point them at their role file and the strategy docs.
- **Results go to files**, and the report is a summary plus paths. Record every measured result in
  `notes/LEDGER.md` with effect ± se, n and method. Weak evidence is a hypothesis, never a finding.
- **Check before you trust**: re-run, don't re-read. Local wins don't predict the field; the practice rounds do.
- **The laptop's CPU is shared by every agent of both sessions** (a speedrun hit load 50 on 12 cores, and then even
  the kit's do-nothing bot failed timing tests; in a second run four agents at 4 workers each put this laptop's 15
  cores at load 17-19 by minute 8 and v1's upload test was inconclusive). Each subagent runs at most 4 local worker processes; Monte Carlo or
  match runs longer than about a minute of CPU go to Modal (one app per purpose). A timing or upload test counts only
  if `uptime` shows load below the core count AND the kit's `check_or_fold` example runs in the same minute as a
  baseline; otherwise say "inconclusive: machine loaded" and re-run.
- **Silent fallbacks are bugs.** Every loader, packer, setting and table lookup fails loudly on a mismatch (unknown
  setting names, missing keys, a dropped file, a zip that wasn't overwritten). A speedrun had five silent fallbacks
  in 20 minutes, each switching off a feature without a sound.
- **Run `date` before you write a time down**; never estimate the clock.
- **A file named in your brief** (`REPORT.md`, `card.md`, `DESIGN.md`, ...) **is a requested deliverable: write it.**
- **Keep your PLAN file current** (`notes/PLAN-<session>.md`; its first line names your role and prompt file):
  what's running where, open promises, next deadline. **After compaction or a restart, first re-read your prompt file
  (`prompts/BUILDER.md` or `prompts/RESEARCH.md`)**, then your PLAN file, `state/status.md`, `state/clock.md` and the
  tail of your inbox before acting, and re-arm your Monitor.
- Facts about rounds (started, finished, results, active bot) come only from `state/status.md` and `data/`, with
  their time. Never assume a round is running.

## 8. The format may differ from the regional's

Every number in `strategy/` and `notes/pre/` comes from the regional: 8 seats, 2,000 chips (100 big blinds), blinds
from 10/20 rising every 20 hands with no ante, a 250-hand cap, 50/30/20 for 1st-3rd, a 1 ms decision limit, round
weights 1 to 6. None of that is promised for today. The rules card (`bot/rules.json`, from the kit and the Format
page) decides, and whatever depends on seats, stack depth, antes, payouts or weights is recomputed from it.

**The likely Finals case.** This is a default seen in the portal's own code on 14 November. It has not been
announced and an organizer can override it: confirm each line from the kit and the Format page at minute 0.
- 6 players a table; 6,000 chips, which is 300 big blinds at the start; antes from the first level; 12 blind levels
  of 20 hands, from 10/20 with a 4 ante to 2,000/4,000 with 800; a 250-hand cap (the last level starts at hand 221).
  Whether the ante is paid by every player or once a hand is in the kit's engine, not in the portal.
- Points per place, the decision limit and the time bank are not part of that default: probably still 50/30/20,
  which pays half of a 6-seat table, and 1 ms.
- 20 teams at 6 seats make 4 tables an iteration with 4 filler seats: non-scoring copies of bots not already at that
  table, which still take finishing places.
- If so, by arithmetic: the field's mean score is the points paid divided by the seats, about 16.7 a table and not
  12.5; each opponent sits at about 5 in 23 of our tables (roughly 220-250 in 1,000, not 370); one bot's spread per
  table is about 19, not 17.9 (`notes/pre/testplan.md` section 1).

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
was used at the regional). If the competition names a final round (`final_weight` in `state/portal.json`,
`comp_settings`), that round's results and our own bot's health report are held until the organizers reveal them:
nothing from it reaches us. When the leaderboard is held, the standings are hidden and every round that finishes
during the hold has its results held too, practice rounds included. What we do is already written: with the
standings hidden we count as outside the top 3 unless we were clearly in it, and with no practice result by T-6 the
rule's answer is the live bot (`DECISION_RULES.md` §3, `prompts/RESEARCH.md`).

**Round multipliers.** A round's points count times its multiplier, and the series is one of three: linear (1 to
6, Bay Area), Fibonacci (1, 2, 3, 5, 8, 13: Boston and Pittsburgh) or powers of two (1 to 32). The last round is then
29%, 41% or 51% of the total, and every rule that counts "share of the weight played" moves with it. Read
`round_weighting` in `state/portal.json` (`comp_settings`) and the Format page; never assume 1 to 6.

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

More, with what it changes for the bot: `notes/pre/format_finals.md`.
