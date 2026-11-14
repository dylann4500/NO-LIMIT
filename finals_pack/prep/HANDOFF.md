# Handoff: team avalon's Finals setup (from Samuel's Claude, Saturday 14 November, ~04:30)

You're picking up the preparation for the No Limit poker-bot **Finals on Sunday 15 November** (San Francisco) for
team **avalon**: Samuel and Dylan. Everything you need is in this repo; this page tells you what exists, why, what's
been verified, and what to do on Saturday, most important first. Read it fully, then `prep/INVESTIGATE.md`.

## 1. The event, in one paragraph

20 strong teams build poker bots live with AI agents. The variant (a twist on no-limit hold'em) is announced at
minute 0 together with a starter kit. Then: a build hour with practice rounds at minutes 20, 30, 40, 50; then about
6 scored rounds 20 minutes apart, each preceded by a practice round at T-10. Bots are a Python file with a 1 ms
decision limit; 8-player sit-and-go tables; our score is average points per table (50/30/20 for 1st-3rd), weighted
by round. **Only the top 3 teams are paid**: 4th is worth the same as 20th. Each round plays the bot that is
**active on the organizers' portal when the round starts**; Dylan uploads zips there and clicks to activate them.
**No pre-written bot code may be brought** (notes, prompts, research and these scripts are fine; anything that plays
poker is written on the day). Hand histories never go into git.

## 2. Where things are

- **Repo:** https://github.com/dylann4500/NO-LIMIT, branch `emu/rehearsal`, latest commit `d9208cb`.
- **The Sunday bundle:** `finals_pack/` (this folder). On Sunday a fresh private repo is made from its contents
  **minus `prep/`** and cloned to `~/avalon-finals` on the laptop that runs everything (`START.md` step 1).
- **The research behind the plan:** `finals_pack/strategy/` (distilled) and, in the main repo,
  `research/finals_prep/` (six studies, ~31k words), `docs/EVIDENCE_TABLE.md` (every claim graded).
- **The tournament simulator** (for rehearsals): `emu/` in the main repo (`emu/README.md`).
- **The retired custom hub** (`hub/`): a web dashboard with 8 agents over two laptops, used in four simulations and
  one practice run on 13-14 Nov. Retired for Sunday because its own plumbing (cross-laptop sync, notifications,
  answer tracking) caused most of the practice run's problems. Don't use it; its lessons are in `strategy/LESSONS.md`.

## 3. The Sunday setup (what the bundle does)

One laptop (Dylan's), one repo, Claude Code. Read `CLAUDE.md`, `START.md`, `prompts/`, `.claude/agents/` and
`scripts/README.md` for the details; the shape:

| Piece | What | Steered by |
|---|---|---|
| **BUILDER** session (`prompts/BUILDER.md`) | the bot: platform, styles, challenger, releases, which bot plays (asks the humans) | Dylan |
| **RESEARCH** session (`prompts/RESEARCH.md`) | maths tables, each round's data, testing, opponents, field trend, the T-9 recommendation | Samuel |
| Subagents (`.claude/agents/`) | BUILDER's: `platform` (only writer of `bot/` and `releases/`), `stylist`, `challenger` (exploration: a clean-room design D from minute 0), `bughunter`. RESEARCH's: `theory`, `analyst`, `tester`, `scout`. They may spawn helpers | the sessions |
| `scripts/clock.py run` (terminal tab 2) | the schedule from `scripts/timeline.json`: posts each step and cut-off to the right session's inbox; prints Dylan's upload/activate reminders with a beep | humans start it |
| `scripts/portal_watch.py` (tab 1) | reads the portal (GETs only), saves results and hand data under `data/`, writes `state/status.md`, posts events, runs the round card when data lands | humans start it |
| Inboxes | `inbox/<session>.log`; each session runs the Monitor tool on `scripts/feed.py <session>`; sessions talk to each other with Claude Code's `SendMessage` and log copies with `say.py --record` | |
| `.claude/settings.json` + `scripts/guard.py` | no permission prompts for ordinary work; a deny list; a PreToolUse hook that refuses pattern kills, blocking waits, deletes outside the repo/tmp, force pushes, portal writes | |
| `strategy/` | `DECISION_RULES.md` (how we decide: always applies), `PLAN.md` (plan + timeline + who does what when), `FIRST_PROMPT.md` (build prompt pack), `TWIST_NOTES.md`, `FINGERPRINTING.md`, `EVIDENCE_TABLE.md`, `LESSONS.md` | |

Key design choices and why:
- **Mechanical jobs are scripts, not Claudes** (clock, portal): LLMs are bad at being on time, and a polling agent
  burns context.
- **The plan is a default, not a mandate.** At the regional (6th of ~150) our plan locked a style and we only made
  small fixes while the field moved. Now: the challenger builds a design from scratch from minute 0; the scout writes
  the field trend every round and checks the plan's written assumptions; any agent can raise a PLAN CHALLENGE that
  reaches both humans; an exploration budget keeps different designs in the practice rounds.
- **Decisions are pre-registered** (DECISION_RULES §3): which bot plays uses a field-adjusted bar (yardstick teams
  that didn't change bots), different for inside/outside the top 3; with no human answer by T-5 the rule's answer
  plays. Hard rules (legal, fast, tested, rules card right, no pre-written code) never bend.
- **Facts come from files with timestamps** (`state/`, `data/`), never from memory.

## 4. What's verified (and how)

- **Claude Code mechanics** (from the official docs, 14 Nov; see `prep/INVESTIGATE.md` §"Already verified"): the
  Monitor tool (30-minute watches, re-arm on expiry), background subagents by default, continuing a subagent with
  SendMessage, nesting up to 3 levels, ~20 concurrent subagents per session (raise with
  `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=40`), built-in cross-session messaging (ListAgents/SendMessage; not in
  bypass-permissions mode), hooks applying to subagents in every mode, deny-beats-allow, effort levels,
  `autoCompactWindow`.
- **Scripts:** `python3 scripts/test_scripts.py` (202 quick / 223 full checks pass on Python 3.9 and 3.14): the
  portal watcher against the simulator's portal copy, the clock through restarts (each step and cut-off once), 44
  guard decisions, the key never printed.
- **A timed speedrun** (`prep/SPEEDRUN_14NOV.md`): headless BUILDER + RESEARCH (Opus 5.5, high effort) on an unseen
  mock variant, no humans, no portal. Every build-hour target landed early: rules card 1.3 min, v1 released with a
  passing no-time-bank upload test at 2-3 min, all theory tables by 12, interface 10, styles A/B/C legal by 12, design
  D legal by 13, 7 releases and 3 bug-review loops by minute 25. Found and fixed: CPU overload (load 50 on 12 cores
  invalidates timing tests), duplicated equity work, releases outpacing tester verdicts (a heads-up regression
  shipped), five silent fallbacks, idle stylists, an untested data path, idle theory agents, and the "trust this
  folder" requirement.
- **A 16-point consistency review** of the bundle; all fixed (one meaning for `state/live.json`, challenger released
  T-15 / activated T-12, one theory schedule, the round-1 rule, git and zip handling, Modal caps, stage folder names).

**Not yet tested** (your Saturday): two humans with real Claude Code sessions end to end, the Monitor waking an idle
interactive session on this laptop, the real portal (its hand-download link, cooldown, round naming), an 8-seat
field with Opus agents over 6 rounds.

## 5. What to do on Saturday (in order)

1. **Set up the laptop that runs Sunday** (`START.md` "Saturday night"): `claude` logged in (Samuel uses a second
   account with an Ultra plan on Sunday: whichever account this laptop uses, check the plan); Python 3.12 and `uv`;
   Modal logged in to the team workspace; the portal key file `~/.config/no-limit-2026/api-key` (Samuel AirDrops it;
   never paste keys anywhere); copy Samuel's `~/.claude/skills/no-limit-2026-setup/` skill; optional `codex` login.
2. **Mechanics checks** (`prep/INVESTIGATE.md` §2, 15 minutes): trust the folder and confirm `/permissions`; the
   Monitor wakes an idle session; cross-session SendMessage between two sessions; the guard refuses
   `pkill -f x` / `sleep 60` / `rm -rf ~/x` and allows `rm -rf build/`; background subagents; concurrency.
3. **One full rehearsal in a separate clone** (`~/avalon-rehearsal`, never the Sunday clone): the simulator on the
   machine that has it set up (`emu/README.md`; needs `starter-kit/` with its venv, `prep/.venv` with Modal, the
   `emu-anthropic` Modal secret), e.g.
   `prep/.venv/bin/python emu/rehearsal.py --run reh5 --field finals --variant flop_auction_holdem --variant-rules emu/variants/flop_auction_holdem.md --round-iterations 3000 --wait`,
   then `emu/portal_server.py --run reh5` and `emu/rehearsal.py --run reh5 --start HH:MM`. The simulator now
   self-checks the variant's engine before READY, uses one Modal app per event with retries, has a Format page and
   stops its sandboxes on exit. Point tab 1 at it: `python3 scripts/portal_watch.py --base http://<simulator
   host>:8765/tournament/api --key-file <the rehearsal key file>`. Tell both sessions it's a rehearsal. Write every
   confusion, silence, delay and wrong answer to `notes/rehearsal_findings.md`; check the per-window timings (data
   landing → T-9 recommendation → T-8 decision → T-3 active bot).
4. **Fix the bundle** from what the rehearsal shows (prompts, role files, timeline, scripts); add each lesson to
   `strategy/LESSONS.md`; re-run `python3 scripts/test_scripts.py`; keep the docs consistent with each other.
5. **Optional research** (`prep/INVESTIGATE.md` §7): the anticipated Finals meta (finalists studied both regionals;
   Boston's top 20 had swung to folding ~57% to 3-bets and 4-betting ~23% by round 5), Pittsburgh's variant and
   results, twist-valuation drills (notes only).
6. **Before Sunday:** build the Sunday repo from `finals_pack/` minus `prep/`; clone it to `~/avalon-finals`; trust it;
   nothing else in it.

## 6. Rules and constraints (don't break these)

- No pre-written bot code in the Sunday repo or brought to the event. Notes, prompts, analysis plans and the scripts
  here are fine.
- Hand histories never go into git. Run Python that reads them with `-I`.
- The organizers' portal: read-only GETs with a non-default User-Agent; only Dylan uploads.
- Never paste or print API keys; never put them in a repo.
- Never kill processes by name or pattern (a `pkill -f "modal run"` in a rehearsal killed every agent): by PID only.
- Modal: one app per purpose; never bursts of `modal run` (the workspace's app-creation rate limit lost a practice
  round); stop the simulator properly (its sandboxes bill until stopped).
- Don't push to repos that aren't the team's, and don't change Claude Code permission settings outside this repo's
  `.claude/settings.json` without the humans saying so.
- In the main repo, `prep/run2` to `prep/run5` and `prep/snap2` are raw evidence from the regional: never edit or
  import from them.

## 7. Open questions and known risks

- **The real portal's hand-download URL** isn't known; the watcher guesses `/tournaments/{tid}/hands`. If downloads
  fail on Sunday, Samuel copies the link and RESEARCH runs `portal_watch.py --set-hands-url '<link>'`.
- **The upload cooldown:** assume up to 5 minutes (a public summary says 5; the regional portal said 30 s). The
  window has at most two real uploads (challenger ~T-15/T-12, a new chosen bot ~T-4); everything else is a click.
- **Does a Monitor event wake an idle interactive session reliably on this laptop?** The bundle depends on it for the
  clock and portal events; test it (§5 step 2). Fallback in `prompts/BUILDER.md`.
- **Main-session context over four hours:** compaction is set early (`autoCompactWindow` 400k); after compaction a
  session re-reads its prompt and PLAN file. Watch `/context` in the rehearsal.
- **The speedrun's strategy hint:** in that test variant the kit's do-nothing bot scored as well as ours in a field
  that busts itself. The tester now reports that floor every time; on Sunday it's a candidate PLAN CHALLENGE if it
  holds on the real field.

## 8. If you need more

- What went wrong before and the rule that prevents it: `strategy/LESSONS.md`.
- Why each decision rule exists: `strategy/DECISION_RULES.md` (with the research grades in `EVIDENCE_TABLE.md`).
- The scenario walk-throughs of the retired hub (many still apply): `hub/tests/scenarios/` in the main repo.
- The speedrun reports: `prep/SPEEDRUN_14NOV.md`. The Saturday test list: `prep/INVESTIGATE.md`.
