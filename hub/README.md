# Avalon Hub

One screen per person. Each of you talks only to your **Overseer**; it runs the workers, the workers run
their own helpers in parallel (Claude subagents, Modal, Codex), and the two laptops' agents message each
other directly. Humans only decide and upload. (Confirmed with the organizers: general infrastructure like
this is allowed; bot code is not.)

```
./hub/start.sh samuel ~/nolimit-rehearsal \
    --portal-base http://127.0.0.1:8765/tournament/api --portal-key-file ~/.config/avalon-rehearsal/portal-key
./hub/start.sh dylan ~/nolimit-rehearsal
```

Open **http://127.0.0.1:7777** and choose your name. `start.sh` restarts the hub if it ever crashes;
Ctrl+C stops it.

## The layout

| | Samuel | Dylan |
|---|---|---|
| **Overseer** (Opus) | Your only chat. The analysis, and the recommendation sent to Dylan's Overseer at T-8 | Dylan's only chat. Decides what plays, declares the live bot, tells Dylan what to upload |
| Worker | **Data** (Opus): our leaks and opponent profiles from every round | **Platform** (Opus): shared code, releases, `bot/` |
| Worker | **Tester** (Sonnet): one verdict per candidate: correct? stronger? | **Builder** (Opus): styles A/B/C and the challenger, in its own copy of the repo |
| Hub services | **Clock**, **Portal watcher** | **Clock** |

- **Any agent can message any agent** on either laptop (`send_message`, kinds `task`, `question`, `answer`,
  `fyi`; `fyi` doesn't wake the receiver). Decisions belong to the two Overseers; only Overseers talk to
  humans.
- **Clock:** set minute 0 once (Start building on the board, the `--start HH:MM` option, or telling an Overseer); a
  human can change it later by telling an Overseer. Both laptops share it. It wakes the Overseers at each build-hour milestone (minutes 0, 10,
  15, 20, 30, 40, 50) and at each step of every scored round's window (T-20, T-13, T-12, T-10, T-9, T-8, T-6,
  T-5, T-3; each person gets their own steps). Every Overseer turn starts with a situation brief: the
  phase, the current step, the next deadline. If there's no decision by T-5, the live bot plays.
- **Portal watcher** (Samuel's laptop): reads the portal every 30 s, and every 6 s while a round should be finishing (read-only), saves each finished
  round's results and our hand histories in `~/portal-data/`, wakes the Overseer and Data, tells Dylan's
  Overseer, and raises an alert if an upload is rejected, if there's no active bot, or if the active bot
  isn't the one Dylan's Overseer declared (checked at T-9 and T-2).
- **Parallel work:** each agent fans out on Claude subagents (up to 4), Modal (shared cap of 80
  containers) and Codex (if installed; separate credits). `roster.py` has the exact rules.

- **Shared context:** at the top of every turn, each agent sees the other agents' briefs (both laptops)
  that changed since its last turn; after a compaction, all of them plus the open notes.
- **Compaction:** between turns, an agent whose context passes 180k tokens (Overseers) or 250k (workers)
  compacts itself with a fixed keep-list (live bot, candidates, human decisions, numbers, running jobs,
  promises), except from T-9 to T-2 of a scored round. The agent page shows "Context Nk".
  `AVALON_COMPACT_AT=<tokens>` overrides the threshold for tests.

## The screen

- **Board** (the default and usually the only thing open): sticky notes, one per idea, analysis,
  suggestion or live-bot decision, each with a one-sentence plain-English headline (agents must write one
  when they post). Colour and label say the kind: Live bot (green), Suggestion (yellow), Analysis
  (lavender), Research (teal), Your idea (blue). Rows: Needs your call, Being worked on (+ New idea),
  Recent.
- **Click a note:** a side panel with details, evidence and a chat. What you type goes to the note
  author's Overseer (`/api/props/{id}/ask`), which routes it and answers in the chat with
  `update_proposal(note=...)`. If it's your call, a red box says what's asked; you answer in words and the
  Overseer records `update_proposal(status=approved|rejected, decided_by=...)` only from a clear human answer.
- **Start building** (before minute 0): starts the shared clock now (`/api/start`) and tells the
  Overseer to begin; both Overseers then dispatch work at each minute from the `DISPATCH` table in
  `hub.py` and check the `CHECKPOINTS` list (behind schedule → optional work is skipped).
- **Agents ▾:** the hidden side panel with Overview, your agents, services and, behind Show, the other
  person's agents. An agent's page has its pinned brief, its activity (tool steps folded, messages as
  one-liners) and a message box.
- **Bell:** permission requests, notes needing your call, and Overseer messages; new ones pop up in the
  corner and the tab title shows the count.

## Reliability

- Messages between laptops go through Modal (any internet connection, hotspots included). Each is
  acknowledged by the receiver and resent until it is; duplicates are dropped; a message that truly can't
  be delivered comes back to the sender. Pending messages survive a hub restart.
- An agent whose turn fails keeps its messages and retries. If it hits a usage limit it shows when it
  resumes; if it's the Opus allowance, it switches itself to Sonnet and carries on.
- Risky commands (deletes, force pushes, `git stash/restore/rebase`, killing processes, Modal deletes, any
  write to the organizers' portal, writes outside the repo) always wait for a click; unanswered requests are
  refused after 3 minutes so nothing stalls before a deadline. "Commands: Ask me" makes an agent ask for
  every command Claude Code would normally ask about.
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
    --portal-base http://127.0.0.1:8765/tournament/api --portal-key-file ~/.config/avalon-rehearsal/portal-key
./hub/start.sh dylan ~/nolimit-rehearsal --data ~/.avalon-hub-reh2/dylan --namespace=-reh2
```

Also delete old `PLAN-*.md` and `data/RATES.md` from the team repo (and push) so the Overseers start clean.

## Sunday

Start with a fresh state folder and a fresh message line so nothing from rehearsals carries over:

```
./hub/start.sh samuel ~/<sunday-repo> --data ~/.avalon-hub-live/samuel --namespace=-live --portal-data ~/portal-data-live \
    --portal-base https://pokerbot.sequoiacap.com/tournament/api --portal-key-file ~/.config/no-limit-2026/api-key
./hub/start.sh dylan ~/<sunday-repo> --data ~/.avalon-hub-live/dylan --namespace=-live
```

Press **Start building** on the board as soon as the variant is announced. After the first practice round, copy the
hand-history download link from the portal's team page and restart Samuel's hub with
`--hands-url '<link with the round id replaced by {tid} and the subset part by {q}>'` (the portal's code
doesn't reveal it). Keep both laptops plugged in with lids open.

On a phone hotspot add `--small-hands` to Samuel's command: the watcher then downloads only the small
first-1,000 hand file per round (a scored round's full file can be several hundred MB).

`--worker-model claude-sonnet-5-5` runs the workers on Sonnet (Overseers stay on Opus) to save the Opus/weekly allowance.

Other options: `--port`, `--model claude-haiku-5-5` (cheap test runs), `--no-autostart`, `--start HH:MM`,
`--portal-data`.
