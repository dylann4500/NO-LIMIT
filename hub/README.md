# Avalon Hub

One screen per person for all of that person's agents. Each laptop runs its own hub; the two hubs pass
messages to each other, so agents settle questions between themselves instead of asking a human to relay.
(Confirmed with the organizers: general infrastructure like this is allowed; bot code is not.)

```
./hub/start.sh samuel ~/nolimit-rehearsal      # on Samuel's laptop
./hub/start.sh dylan  ~/nolimit-rehearsal      # on Dylan's laptop
```

Then open **http://127.0.0.1:7777** and choose your name.

## What you see

- **Sidebar:** your Overseer, then its agents, each with a live status dot (green = working, amber =
  waiting for you, red = error, hollow = not started) and one line on what it is doing. The top line
  says whether you are linked to the other laptop.
- **Chat:** the selected agent's conversation, like Claude Code: your messages, its replies, its tool
  calls (click to expand), and cards for messages it sent to or received from other agents.
- **Banners:** an agent asking permission (Allow / Always for this agent / Deny), or an agent asking you
  to decide or do something (e.g. "upload v4 now").
- **Buttons:** Summary (its latest report), Auto-approve / Asking first, Interrupt, Start / Stop.
- Choosing the other person's name shows their agents read-only (posted summaries); a message you type
  there goes to that agent.

## How it works

- Every agent is a real Claude Code session (Claude Agent SDK) on the laptop's own Claude login, working
  in the team repo. State and transcripts live in `~/.avalon-hub/<person>/`; a restarted hub resumes
  each agent's conversation.
- Agents get hub tools: `send_message` (any agent, either laptop), `list_agents`, `read_agent`,
  `set_status`, `notify_human`, and for the Overseer `start_agent` / `stop_agent`. Standing instructions
  (`roster.py`, PROTOCOL) tell them to message the owning agent directly, never through a human.
- Messages between laptops go through a Modal Queue (team workspace), so any internet connection works,
  phone hotspots included. Outgoing messages are saved locally first and retried until delivered;
  duplicates are dropped.
- Permissions: commands Claude Code would normally ask about are approved automatically, except risky
  ones (force-push, hard reset, recursive deletes, sudo, piping downloads into a shell, ...), which wait
  for a click. "Asking first" on an agent makes it wait for every such command.

## Setup (each laptop, once)

1. Claude Code installed and logged in (`claude` works in a terminal).
2. `uv` installed.
3. Modal logged in to the team workspace (`modal token new`); test with `modal app list`.
4. The team repo cloned, with the plan docs in it (START_HERE.md, FIRST_PROMPT.md, TWIST_NOTES.md,
   PORTAL_AGENT.md).

Options: `--port`, `--model claude-haiku-5-5` (cheap test runs), `--no-autostart`, `--namespace=-test`
(a separate message line for testing), `--data` (state folder).

## Roster

| Samuel | Dylan |
|---|---|
| Overseer: runs Samuel's side, digest of it, the one-page recommendation | Overseer: owns the bot, decides what ships, digest of the builders |
| Portal: reads the organizers' portal, saves hand data, alerts | Builder A: wide pressure |
| Leak finder (Part 2) | Builder B: shove-heavy |
| Analyst: results, trend, style, challenger vs live | Builder C: tight |
| Bug hunter: reviews every new version | Builder D: challenger (fixes, redesigns) |
| Opponents: team profiles and fingerprints (Part 4) | |
| Simulator: paired tests, sparring, cloned field on Modal (Part 3) | |

Edit `roster.py` to change roles, models or who starts automatically.
