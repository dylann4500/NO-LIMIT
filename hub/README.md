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
- **Clock:** set minute 0 once (Home page, the `--start HH:MM` option, or an Overseer). Both laptops share
  it. It wakes the Overseers at T-13, T-8, T-5 and T-3 before scored rounds and at T-3 before practice
  rounds. If there's no decision by T-5, the live bot plays.
- **Portal watcher** (Samuel's laptop): reads the portal every minute (read-only), saves each finished
  round's results and our hand histories in `~/portal-data/`, wakes the Overseer and Data, tells Dylan's
  Overseer, and raises an alert if an upload is rejected, if there's no active bot, or if the active bot
  isn't the one Dylan's Overseer declared (checked at T-9 and T-2).
- **Parallel work:** each agent fans out on Claude subagents (up to 4), Modal (shared cap of 80
  containers) and Codex (if installed; separate credits). `roster.py` has the exact rules.

## The screen

- **Needs you** (top of the sidebar): every permission request and every decision an Overseer needs,
  with buttons. The browser tab shows the count, e.g. `(2) Avalon`.
- **Home:** the clock, the declared live bot, the link to the other laptop, and a card for every agent and
  service on both laptops.
- **An agent's page:** its conversation, with tool steps folded into one line ("▸ 9 steps · Bash ×5, Read
  ×4") and agent-to-agent messages as one-line entries you can expand. The latest report is pinned at the
  top. Labels say what it's doing: Working · 3m, Ready, Waiting for you, Usage limit · resumes 21:40,
  Error · retrying, Off. "Usage" shows how much of the Claude allowance is used.
- Messages you send while an agent is busy show as **queued** until it reads them.

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

## Sunday

Start with a fresh state folder and a fresh message line so nothing from rehearsals carries over:

```
./hub/start.sh samuel ~/<sunday-repo> --data ~/.avalon-hub-live/samuel --namespace=-live \
    --portal-base https://pokerbot.sequoiacap.com/tournament/api --portal-key-file ~/.config/no-limit-2026/api-key
./hub/start.sh dylan ~/<sunday-repo> --data ~/.avalon-hub-live/dylan --namespace=-live
```

Set minute 0 on Home as soon as the variant is announced. After the first practice round, copy the
hand-history download link from the portal's team page and restart Samuel's hub with
`--hands-url '<link with the round id replaced by {tid} and the subset part by {q}>'` (the portal's code
doesn't reveal it). Keep both laptops plugged in with lids open.

On a phone hotspot add `--small-hands` to Samuel's command: the watcher then downloads only the small
first-1,000 hand file per round (a scored round's full file can be several hundred MB).

Other options: `--port`, `--model claude-haiku-5-5` (cheap test runs), `--no-autostart`, `--start HH:MM`,
`--portal-data`.
