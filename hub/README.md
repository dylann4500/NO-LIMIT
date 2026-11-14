# Avalon Hub

One screen per person. Each of you talks mainly to your **Chat** (the lead of your side) and can open any
worker to steer it; the workers run their own helpers in parallel (Claude subagents, Modal, Codex), and the
two laptops' agents message each other directly. Humans decide, steer and upload. (Confirmed with the organizers: general infrastructure like
this is allowed; bot code is not.)

```
./hub/start.sh samuel ~/nolimit-rehearsal \
    --portal-base http://127.0.0.1:8765/tournament/api --portal-key-file ~/.config/avalon-rehearsal/portal-key --rehearsal
./hub/start.sh dylan ~/nolimit-rehearsal --rehearsal
```

Open **http://127.0.0.1:7777** and choose your name. `start.sh` restarts the hub if it ever crashes;
Ctrl+C stops it.

## The layout

| | Samuel | Dylan |
|---|---|---|
| **Chat** (the lead, Opus) | Leads analysis, testing and opponents; the recommendation sent to Dylan's Chat at T-8 | Leads the bot. Asks "which bot?", declares the live bot (and each build-hour practice bot), tells Dylan what to upload or click active |
| Worker | **Analyst** (`s-data`): maths tables, round cards, leaks | **Platform & releases** (`d-platform`): shared code, releases, `bot/` |
| Worker | **Tester** (`s-tester`): correct? stronger? are the numbers true? | **Styles & fixes** (`d-builder`): styles A/B/C, counters, live-bot fixes, in its own copy of the repo |
| Worker | **Opponents** (`s-scout`): field trend, fingerprints, team profiles | **Challenger** (`d-challenger`): design D, then each window's bigger-swing bot, in its own copy of the repo |
| Hub services | **Clock**, **Portal watcher**, **Deadlines**, **Codex** | **Clock**, **Deadlines**, **Codex** |

- **Any agent can message any agent** on either laptop (`send_message`, kinds `task`, `question`, `answer`,
  `fyi`; `fyi` doesn't wake the receiver). Decisions are asked by the two Chats. A human can message any agent;
  its reply must start with the person's name ("Samuel: ...") and answer, or the hub re-raises the message
  after 1 minute.
- **Clock:** set minute 0 once (Start building on the board, the `--start HH:MM` option, or telling a Chat); a
  human can change it later by telling a Chat. Both laptops share it. It wakes the agents at each build-hour milestone (minutes 0, 10,
  15, 20, 30, 40, 50) and at each step of every scored round's window (T-20, T-13, T-12, T-10, T-9, T-8, T-6,
  T-5, T-3; each person gets their own steps). Every lead turn starts with a situation brief: the
  phase, the current step, the next deadline. If there's no decision by T-5, the live bot plays.
- **Portal watcher** (Samuel's laptop): reads the portal every 30 s, and every 6 s while a round should be finishing (read-only), saves each finished
  round's results and our hand histories in `~/portal-data/`, wakes the Chat and the Analyst, tells Dylan's
  Chat, and raises an alert if an upload is rejected, if there's no active bot, or if the active bot
  isn't the one Dylan's Chat declared (checked at T-9 and T-2).
- **Uploads:** each round plays a snapshot of every team's **active** bot at its start; making an
  already-uploaded bot active is a click on the portal. So a window has at most two real uploads (the
  challenger at T-12, and the chosen bot around T-4 to T-3 only if it's a new zip); the cooldown may be up to
  5 minutes.
- **Parallel work:** each agent fans out on Claude subagents, Modal (shared cap of 80 containers) and Codex
  (if installed; separate credits). One Modal app per purpose (deploy once and call it, or one `modal run`
  with `.map`), never bursts of `modal run`: Modal's workspace-wide app-creation limit lost a practice round.
  `roster.py` has the exact rules.

- **Shared context:** at the top of every turn, each agent sees the other agents' briefs (both laptops)
  that changed since its last turn; after a compaction, all of them plus the open notes.
- **Compaction:** between turns, an agent whose context passes 150k tokens (Chats) or 100k (workers)
  compacts itself with a fixed keep-list (live bot, candidates, human decisions, numbers, running jobs,
  promises), except from data landing to T-2 of a scored round, and never while a person's message waits. The agent page shows "Context Nk".
  `AVALON_COMPACT_AT=<tokens>` overrides the threshold for tests.

## The screen

- **Board:** progress tiles grouped by stage, newest first ("Round 1 analysis · in progress" → "done"); click a
  tile to open the agent doing it. **Now** at the top shows the stage, the portal's bot and every agent's state.
- **Chat:** your lead. Decisions show in one slim **Needs you** bar at the top (what's waiting, due time, a
  **Details** button for the evidence); you answer in words and the decision is recorded only from a clear
  human answer. Plan challenges are one line in the Chat and the bell; only Samuel's Chat asks the decision.
  The model-based contradiction check goes to the lead only, never into the humans' Chat.
- **Team chat** (sidebar): Samuel and Dylan's own chat. No agent reads it; it syncs between laptops and takes
  attachments.
- **Message boxes:** every one has a mic button for dictation (browser speech recognition: the text lands in
  the box, you check it and press Enter). Unsent text is kept when you switch agents.
- **Start building** (before minute 0): starts the shared clock now (`/api/start`); the agents then get
  work at each minute from the `DISPATCH` table in `hub.py` and the `CHECKPOINTS` list (behind schedule →
  optional work is skipped).
- **Sidebar (☰):** the Board, your agents (your Chat first), services, Team chat and, behind Show, the other
  person's agents. An agent's page has its pinned brief, its activity (tool steps folded, messages as
  one-liners) and a message box. Agent badges only say "needs you" (no unread counts).
- **Live menu:** every bot; says "tested, not released yet" until Platform releases a zip; downloads a zip.
- **Bell:** a short list of one-line items. Pop-ups only for real emergencies (a rejected upload, no active
  bot; a permission request only with `AVALON_ASK_PERMISSION=1`), one at a time. The screen edges flash only for a bot decision due in under
  3 minutes.

## Reliability

- Messages between laptops go through Modal (any internet connection, hotspots included). Each is
  acknowledged by the receiver and resent until it is; duplicates are dropped; a message that truly can't
  be delivered comes back to the sender. Pending messages survive a hub restart.
- An agent whose turn fails keeps its messages and retries. If it hits a usage limit it shows when it
  resumes; if it's the Opus allowance, it switches itself to Sonnet and carries on.
- No permission prompts: agents' commands run automatically. A short list of dangerous ones is refused
  outright with the reason: deleting outside `/tmp` and the repo, force pushes, `git reset --hard/stash/rebase`,
  `sudo`, Modal deletes, writes to the organizers' site, writes outside the repo, pattern kills
  (`pkill`, `killall`), and a foreground `wait` or long `sleep`. (`AVALON_ASK_PERMISSION=1` brings the old
  click-to-approve prompts back, for tests only.)
- The hub stops leftover helper processes started from its own folders when it starts and when it shuts down.
- Two agents caught messaging each other in a loop (over 10 messages in 10 minutes) are paused and you're
  told.

## Setup (each laptop, once)

1. Claude Code installed and logged in.
2. `uv` installed.
3. Modal logged in to the team workspace (`uv run --no-project --with modal modal app list` works).
4. Optional: Codex CLI installed and logged in (`npm i -g @openai/codex`, then `codex login`), so agents can
   use the OpenAI credits too.
5. The team repo cloned, containing START_HERE.md, FIRST_PROMPT.md, TWIST_NOTES.md, PORTAL_AGENT.md and a
   `.gitignore` that excludes `*.gz`, `*.csv` and `portal-data/`.

## Starting a fresh run (each rehearsal, and Sunday)

Old state makes agents resume old conversations and the clock show an old schedule, so each run gets its
own state folder and message line. Pick a name per run (e.g. `reh2`) and use it on both laptops:

```
./hub/start.sh samuel ~/nolimit-rehearsal --data ~/.avalon-hub-reh2/samuel --namespace=-reh2 \
    --portal-data ~/portal-data-reh2 \
    --portal-base http://127.0.0.1:8765/tournament/api --portal-key-file ~/.config/avalon-rehearsal/portal-key --rehearsal
./hub/start.sh dylan ~/nolimit-rehearsal --data ~/.avalon-hub-reh2/dylan --namespace=-reh2 --rehearsal
```

`--rehearsal` tells the agents the portal is a copy and its facts don't carry over to Sunday. Never use it on
Sunday. Also delete old `PLAN-*.md` and `data/RATES.md` from the team repo (and push) so the Chats start clean.

## Sunday

Start with a fresh state folder and a fresh message line so nothing from rehearsals carries over:

```
./hub/start.sh samuel ~/<sunday-repo> --data ~/.avalon-hub-live/samuel --namespace=-live --portal-data ~/portal-data-live \
    --portal-base https://pokerbot.sequoiacap.com/tournament/api --portal-key-file ~/.config/no-limit-2026/api-key
./hub/start.sh dylan ~/<sunday-repo> --data ~/.avalon-hub-live/dylan --namespace=-live
```

Chat commands the hub handles itself (both laptops follow):
- "start the research" (about 2 hours before): every worker gets its pre-event research topic (notes only).
- "run the check": the pre-flight on both laptops (link, portal read + hand download, Claude, Codex, repo, disk,
  CPU (flags a busy laptop: leftover jobs make local timing tests wrong), clock, same hub code, laptop clocks).
- "the competition starts now" (or "... was announced at 14:02"): minute 0. "reset the clock": clears a clock set
  by mistake (before any scored round).
- "hands link: <url>" (Samuel): the hand-history download link copied from the portal, if the watcher can't
  download on its own; no restart.
- Format and times go to the Chat in words ("the build is 90 minutes", "rounds are every 30 minutes", "scored
  round 3 is at 15:40"); a scored round's real start is also taken from the portal.

Keep both laptops plugged in with lids open.

On a phone hotspot add `--small-hands` to Samuel's command: the watcher then downloads only the small
first-1,000 hand file per round (a scored round's full file can be several hundred MB).

`--worker-model claude-sonnet-5-5` runs the workers on Sonnet (the Chats stay on Opus) to save the Opus/weekly allowance.

Other options: `--rehearsal` (practice runs only: agents are told the portal is a copy), `--port`,
`--model claude-haiku-5-5` (cheap test runs), `--no-autostart`, `--start HH:MM`, `--portal-data`,
`--view-only`.
