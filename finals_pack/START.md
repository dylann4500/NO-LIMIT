# Finals day: how to start (for Samuel and Dylan)

Everything runs on Dylan's laptop, in this repo: two Claude Code sessions (**BUILDER**, Dylan; **RESEARCH**, Samuel)
plus two scripts (the **clock** and the **portal watcher**). No dashboard. You talk to your session in its terminal.

## Saturday night (once, about 20 minutes)

1. **Make the repo.** A fresh private GitHub repo (e.g. `avalon-finals`) whose contents are exactly this folder,
   minus `prep/` (that's for Saturday's checks only). Clone it on Dylan's laptop: `git clone <url> ~/avalon-finals`.
   No bot code goes in it. Never run a rehearsal in this clone (see the end).
2. **Accounts on Dylan's laptop:**
   - `claude` logged in to the account you both use on Sunday (`claude`, then `/login`). Samuel types into RESEARCH
     from his own computer through Remote Control, and he only sees this laptop's sessions if his computer is
     signed in to the **same Claude account** (he opens claude.ai/code there).
   - The portal key in `~/.config/no-limit-2026/api-key` (Samuel's key: AirDrop the file, never paste it in a chat
     or the repo). Check it: `python3 scripts/portal_watch.py --once` should print the team and competition. Until
     the organizers put us in the Finals competition it prints the regional ("Bay Area") with a note that this is
     not today's event; the running watcher switches to the Finals by itself when it appears on the key.
   - `modal` logged in to the team workspace (`modal app list` works). Optional: `codex` logged in, and able to answer:
     try `codex exec "2+2"` (on 14 November this laptop's login was an API key limited to 10,000 tokens a minute and no
     question ran).
      - `uv` installed (`brew install uv`) and Python 3.12 (`python3.12 --version`; else `brew install python@3.12`):
     the kit's environment needs it.
   - The starter-kit setup skill: copy Samuel's `~/.claude/skills/no-limit-2026-setup/` folder to the same place on
     Dylan's laptop. On Sunday it fetches the kit into `starter-kit/` and builds its Python (answer "only on this
     computer" if it asks where to set up).
3. **Check the scripts:** `cd ~/avalon-finals && python3 scripts/test_scripts.py` (all pass).
4. **Trust the folder once:** run `claude` in `~/avalon-finals` and accept the "trust this folder?" question. Until
   you do, Claude Code ignores the repo's settings (the no-permission-prompt list), and every command asks you.
   Then type `/permissions` and check the allow and deny lists from `.claude/settings.json` are there; `/exit`.
5. **Decide who claims the $250 Codex credit** before anyone opens the link.

## Sunday, 2-3 hours before the start

Open four terminal tabs in `~/avalon-finals` (keep the laptop plugged in; run `caffeinate -dims &` once):

| Tab | Command | What it is |
|---|---|---|
| 1 | `python3 scripts/portal_watch.py` | reads the portal every 15 s, saves data, posts events (leave it running) |
| 2 | `python3 scripts/clock.py run` | posts each step to the sessions and prints Dylan's upload/activate reminders here, with a beep |
| 3 | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=40 claude -n BUILDER --remote-control BUILDER` → `/model`, `/effort high` → paste the BUILDER starter (below) | Dylan's session |
| 4 | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=40 claude -n RESEARCH --remote-control RESEARCH` → `/model`, `/effort high` → paste the RESEARCH starter (below) | Samuel's session: he types into it from his own computer (claude.ai/code, the same Claude account, the session named RESEARCH) |

**Remote Control:** `--remote-control <name>` shows the session on claude.ai/code for anyone signed in to the same
account; `-n <name>` names it so the two sessions can find each other. Both of you can type into either session, from
the laptop or remotely. Agree who types where: nobody has tested two people typing into one session at the same
moment. **Start both sessions in the same permission mode:** a session holds messages that come from a session in
a different mode until a human approves them. So never start just one of them with
`--dangerously-skip-permissions`; the repo's settings already remove the permission prompts.

**Model and effort:** the strongest model you have (Opus 5.5 or Fable 5.2) at **high** effort for both sessions
(`/model`, `/effort high`; `xhigh`/`max` think longer and answer slower). Subagents use the session's model and effort
unless a role file or the session picks another. The `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=40` prefix raises the
default limit of 20 subagents running at once per session (checked on 14 Nov: the 21st spawn fails outright, it
does not queue). `.claude/settings.json` sets the same value in its `env` block, so sessions that are not started
from a command line (the desktop app) get it too: checked on 14 Nov, 24 subagents ran at once in a desktop-app
session in this folder. To confirm in any session: `echo $CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` prints 40.

**BUILDER starter** (paste into tab 3):
```
You are the BUILDER session for team avalon at the No Limit Finals today. Dylan is at this terminal.
Read prompts/BUILDER.md now and follow it exactly, starting with its start-up steps.
```

**RESEARCH starter** (paste into tab 4):
```
You are the RESEARCH session for team avalon at the No Limit Finals today. Samuel is at this terminal.
Read prompts/RESEARCH.md now and follow it exactly, starting with its start-up steps.
```

Then, about 2 hours before minute 0, type **"start the research"** into both sessions: each spawns its morning
research (notes only, no code: it checks and extends Saturday's drafts in `notes/pre/`), and RESEARCH merges it into
`notes/plan.md`.

## Minute 0 (the variant is announced)

1. **Samuel** tells RESEARCH: "the variant was announced at 14:02" (or "it starts now"). RESEARCH starts the clock.
   (Or run it yourself in any tab: `python3 scripts/clock.py start now`.) Tab 1 helps: within 15 seconds of the
   announcement it posts "THE VARIANT IS ANNOUNCED" with the portal's own time and saves the rules text to
   `state/variant.md`; if nobody has given RESEARCH a time yet, it starts the clock from that and tells Samuel.
2. **Dylan** runs `/no-limit-2026-setup` in BUILDER (it fetches the kit into `starter-kit/` and builds its Python),
   or downloads the kit from the portal into `starter-kit/`, and tells BUILDER "the kit is in starter-kit/".
3. **Both** read the portal's Format page: weights, payouts, the upload cooldown, anything unusual. If the shape
   differs (build length, round spacing, number of rounds), tell RESEARCH in words ("the build is 90 minutes",
   "rounds are every 30 minutes", "there are 5 scored rounds"). Paste or screenshot the Format page into BUILDER
   too (the rules card needs it).

## During the day

- **Dylan:** watch tab 2 (the clock) and BUILDER. You upload and activate on the portal:
  - the first bot at about minute 10;
  - the bot BUILDER names for each practice;
  - the challenger at T-12;
  - re-activate the live bot at T-9 (a click), once the practice round has started;
  - the chosen bot by T-3 (a click if it's already uploaded).

  Each round plays the bot that is active when it starts.
- **Both:** answer decisions in words in the session that asks (BUILDER asks "which bot?"; RESEARCH asks plan
  challenges). The question shows the rule's answer, which plays if nobody answers by the deadline. Samuel can
  answer a bot decision in RESEARCH; it relays his words.
- **Steer** by typing to your session: "why?", "do X first", "research Y". It hands the work to the right subagent and
  answers you first.
- **Hand data not downloading?** It should by itself: the watcher uses the real portal's own address (checked on
  14 November). If it doesn't, copy the hand download link from the portal and run
  `python3 scripts/portal_watch.py --set-hands-url '<link>'` (no restart).

## When something goes wrong

| What you see | Do |
|---|---|
| Upload rejected (tab 1 / BUILDER) | The previous bot stays active. BUILDER has platform fix it and gives you a new file |
| No active bot / wrong active bot (tab 1, urgent) | Make the right bot active on the portal now |
| The clock is wrong | Tell RESEARCH the right time ("round 3 starts at 15:42"), or `python3 scripts/clock.py pin scored3 15:42` |
| A session seems stuck | Type "status?" in it. If it doesn't answer within a minute, press Esc and ask again |
| A session crashed or closed | In its tab: `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=40 claude --resume`, pick the conversation that starts "You are the BUILDER (or RESEARCH) session", `/effort high`, then say "re-read prompts/BUILDER.md (or RESEARCH.md) and your PLAN file, and re-arm your Monitor". Don't use `--continue` (it may pick the other session's conversation) and never `--dangerously-skip-permissions` (it holds the other session's messages). Remote Control normally reconnects by itself; if Samuel can't see the session, type `/remote-control RESEARCH` in it |
| Samuel can't see RESEARCH on his computer | His computer must be signed in to the same Claude account as this laptop; then, in the session's tab: `/remote-control RESEARCH` |
| Tab 1 still says "not today's event" at minute 0 | The key doesn't list the Finals yet. Ask the organizers whether avalon is in the Finals competition; if the Finals team has its own key (Settings → API keys on the portal), put it in `~/.config/no-limit-2026/api-key` (a file, never pasted into a chat) and restart tab 1 |
| Tab 1 or 2 stopped | Run its command again; both resume from `state/` |
| Modal "rate limit" | Tell the session: one Modal app per purpose, no bursts; wait a minute |
| You disagree at T-8 and there's no time | The rule's answer plays |

## Rehearsal with this setup (Saturday)

**Never rehearse in `~/avalon-finals`**: a rehearsal leaves bot code, releases and state behind, and Sunday must start
from a clean repo. Use a separate clone: `git clone <url> ~/avalon-rehearsal` (trust it once, as above), and run the
same four tabs there, pointed at the rehearsal portal on Samuel's Mac (the simulator: ask Samuel's Claude to start
one): `python3 scripts/portal_watch.py --base http://100.111.100.112:8765/tournament/api --key-file <the rehearsal
key>` and the clock started at the rehearsal's minute 0. Tell both sessions at the start: "this is a rehearsal: the
portal is a copy; nothing about the copy (its cooldown, its pages, the simulated teams) carries over to Sunday".
If you ever did run something in `~/avalon-finals`, delete it, clone again and trust it again.
