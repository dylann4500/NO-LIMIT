# Team avalon at the No Limit Finals: read this first (every Claude, every session)

Sunday 15 November 2026, San Francisco. 20 teams build poker bots live with AI agents. The variant is announced at
minute 0 with a starter kit; then a build hour with 4 practice rounds, then about 6 scored rounds 20 minutes apart,
each with a practice round 10 minutes before it. Only 1st, 2nd and 3rd are paid (50/30/20): 4th is worth the same
as 20th. Humans: **Dylan** (steers BUILDER, uploads bots on the portal) and **Samuel** (steers RESEARCH).

## 1. Who runs where

Everything runs on one laptop, in this repo, in Claude Code. Two main sessions, each with its own subagents:

| Session | Steered by | Owns | Spawns (subagent types in `.claude/agents/`) |
|---|---|---|---|
| **BUILDER** | Dylan | the bot: engine, styles, releases, which bot plays (asks the humans), what Dylan uploads | `platform`, `stylist`, `challenger`, `bughunter` |
| **RESEARCH** | Samuel | the maths, each round's data, testing, opponents, the field trend, the T-9 recommendation | `theory`, `analyst`, `tester`, `scout` |

Two scripts do the mechanical jobs (started by a human in their own terminal tabs; never by an agent):
- `scripts/clock.py run`: the schedule. At each step it posts what to do to the right session's inbox.
- `scripts/portal_watch.py`: reads the organizers' portal (read-only). Saves results and hand data under `data/`,
  keeps `state/status.md` current (active bot, standings, rounds) and posts every event to both inboxes.

Your own start-up instructions are in `prompts/BUILDER.md` or `prompts/RESEARCH.md`.

## 2. How sessions hear things: one inbox each

- `inbox/builder.log` and `inbox/research.log`: append-only. The clock, the portal watcher and the other session all
  write there. Each main session keeps **one Monitor** running on `python3 scripts/feed.py <builder|research>`: it
  prints each new inbox line, and each line wakes you. The Monitor expires (after 30 minutes at most): **re-arm it every time
  it does**, at once, before anything else.
- **Session to session:** use Claude Code's cross-session messaging: `ListAgents` finds the other session,
  `SendMessage` reaches it at once (it wakes it). One message per point, with numbers and file paths; never
  acknowledgements or thanks. Then log a one-line copy for the record: `python3 scripts/say.py --record <to> "<text>"`
  (writes only to `state/events.log`, so it doesn't arrive twice). If cross-session messaging isn't available, use
  `python3 scripts/say.py <builder|research> "<text>"`, which lands in the other session's inbox.
- Subagents never write to inboxes; they report to whoever spawned them.

## 3. Files: where everything lives

| Path | What | Written by |
|---|---|---|
| `strategy/` | the plan and the research (read-only on the day): `DECISION_RULES.md` (how we decide: always applies), `PLAN.md` (the game plan + timeline), `FIRST_PROMPT.md` (the build prompt pack), `TWIST_NOTES.md`, `FINGERPRINTING.md`, `EVIDENCE_TABLE.md`, `LESSONS.md` (what broke in rehearsals) | humans, before the day |
| `state/status.md` | the portal right now: active bot, rounds, standings, last results | portal watcher |
| `state/schedule.json`, `state/clock.md` | minute 0, the round times, the next steps | clock |
| `state/live.json` | the bot we have **decided** should be active next: each build-hour practice pick, then the round-1 bot, then each scored round's bot (never a window's challenger: BUILDER tells Dylan that file directly) | BUILDER only: `python3 scripts/live.py vN "why"` |
| `state/decisions.md` | every decision asked of the humans: question, evidence, the rule's answer, deadline, the human's words, outcome | BUILDER (bots), RESEARCH (plan challenges) |
| `data/rounds/<NN-stage>/` | `results.json`, `hands-first-1000.jsonl.gz` (and full), `played_by.txt` | portal watcher (never in git) |
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
| `notes/pre/` | the morning research | subagents, before minute 0 |

## 4. Hard rules (these never bend)

1. **Every uploaded bot is legal and fast**: zero failed decisions in the checks, the kit's check passes, and it
   passes the upload test with no time bank (2 players, 20 hands, time bank 0). A bot that times out auto-folds.
2. **Only tested zips are released and uploaded.** A tested bot is active by T-3 of every scored round. Each round
   plays the bot that is **active when it starts**. Making an already-uploaded bot active is a click on the portal.
3. **The rules card is right**: players per table, stacks, blinds, hands per match, weights, payouts and the upload
   cooldown come from the kit and the Format page (`bot/rules.json`, written by `platform` at minute 0).
4. **No pre-written bot code** (everything bot-related is written today); hand histories never go into git.
5. The organizers' portal is read-only for agents. Only Dylan uploads.
6. **Never kill processes by name or pattern** (`pkill`, `killall`, `pgrep | xargs kill`): every Claude process's
   command line contains these instructions, so a pattern like `pkill -f "modal run"` kills every agent. Stop only
   what you started, by PID (`cmd > log 2>&1 & echo $! > /tmp/<job>.pid`; later `kill $(cat /tmp/<job>.pid)`) or
   `modal app stop <id>`. A hook refuses pattern kills.
7. **Never block your turn**: no foreground `wait`, no `sleep` over 20 s, no loops that poll. Start long jobs in the
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
  one message (each in its own folder), Modal for compute, Codex (`codex exec`) for second opinions if logged in.
  Subagents may spawn their own helpers (nesting stops at 3 levels; at most about 4 helpers each, one job and one
  output file per helper). About 20 subagents can run at once per session (more if the session was started with
  `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` raised); past that a spawn fails, so finish or stop idle ones first.
- **Brief subagents like new teammates**: objective, exact input files, output (files plus a report of at most 300
  words with paths), what not to touch, a time limit. Point them at their role file and the strategy docs.
- **Results go to files**, and the report is a summary plus paths. Record every measured result in
  `notes/LEDGER.md` with effect ± se, n and method. Weak evidence is a hypothesis, never a finding.
- **Check before you trust**: re-run, don't re-read. Local wins don't predict the field; the practice rounds do.
- **The laptop's CPU is shared by every agent of both sessions** (a speedrun hit load 50 on 12 cores, and then even
  the kit's do-nothing bot failed timing tests). Each subagent runs at most 4 local worker processes; Monte Carlo or
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
