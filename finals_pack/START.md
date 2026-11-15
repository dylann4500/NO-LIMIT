# Finals day: how to start (for Samuel and Dylan)

Everything runs on Dylan's laptop, in this repo: two Claude Code sessions (**BUILDER**, Dylan; **RESEARCH**, Samuel)
plus two scripts (the **clock** and the **portal watcher**). No dashboard. The two sessions run in the Claude desktop app's Code tab (every check and timed run on 14 November
ran there); the two scripts run in terminal tabs. You talk to your session by typing into it.

## Saturday night (once, about 20 minutes)

1. **Make the repo.** `~/avalon-finals` on Dylan's laptop: a fresh local git repo whose contents are exactly this
   folder, minus `prep/` (that's for Saturday's checks only). It needs no GitHub remote, because everything runs on
   this laptop (decided 14 November; a private remote is only a backup). No bot code goes in it. Never run a
   rehearsal in it (see the end).
2. **Accounts on Dylan's laptop:**
   - The Claude desktop app signed in to the account you both use on Sunday, with Fable 5.2 offered in its Code tab
     (if it is a new account, check both tonight; `claude` in a terminal is a separate login and only the fallback).
     Samuel types into RESEARCH from his own computer through Remote Control, and he only sees this laptop's sessions
     if his computer is signed in to the **same Claude account** (claude.ai/code or the desktop app there; checked on
     14 November: a message typed on his computer reached a session on this laptop).
   - The portal key in `~/.config/no-limit-2026/api-key` (Samuel's key: AirDrop the file, never paste it in a chat
     or the repo). Check it: `python3 scripts/portal_watch.py --once` should print the team and competition (on
     14 November it printed team avalon and the competition "Finals", with 0 rounds). If it ever prints the regional
     ("Bay Area") with a note that this is not today's event, the key does not list the Finals: see the table below.
   - `modal` logged in to the team workspace (`modal app list` works). Optional: `codex` logged in, and able to answer:
     try `codex exec "2+2"` (on 14 November this laptop's login was an API key limited to 10,000 tokens a minute and no
     question ran).
      - `uv` installed (`brew install uv`) and Python 3.12 (`python3.12 --version`; else `brew install python@3.12`):
     the kit's environment needs it.
   - The starter-kit setup skill: copy Samuel's `~/.claude/skills/no-limit-2026-setup/` folder to the same place on
     Dylan's laptop. On Sunday it fetches the kit into `starter-kit/` and builds its Python (answer "only on this
     computer" when it asks where to set up: our team has a build box assigned for the Finals, `finals-team-6`, so the
     skill will offer it, but everything in this plan runs on this laptop).
3. **Check the scripts:** `cd ~/avalon-finals && python3 scripts/test_scripts.py` (all pass).
4. **Trust the folder once:** start a session in `~/avalon-finals` in the desktop app's Code tab and accept the "trust
   this folder?" question (or run `claude` there). Until you do, Claude Code ignores the repo's settings: the allow
   list, the safety hook and the 40-subagent limit. To check, ask that session to run
   `echo $CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (it prints 40) and `pkill -f no_such_process` (the hook refuses it);
   then close it. It leaves nothing in the repo.
5. **Decide who claims the $250 Codex credit** before anyone opens the link.

## Sunday, 2-3 hours before the start

Keep the laptop plugged in and awake (`caffeinate -dims &` in a terminal tab).

**Two terminal tabs in `~/avalon-finals`**, for the scripts:

| Tab | Command | What it is |
|---|---|---|
| 1 | `python3 scripts/portal_watch.py` | reads the portal every 15 s, saves data, posts events (leave it running) |
| 2 | `python3 scripts/clock.py run` | posts each step to the sessions and prints Dylan's upload/activate reminders here, with a beep |

**Two sessions in the Claude desktop app** (Code tab), one after the other:

1. Start a new session in the folder `~/avalon-finals`.
2. Before the first message set the model to Fable 5.2, the effort to high, and the permission mode: **the same mode
   in both sessions** (a session holds messages that come from a session in a different mode until a human approves
   them). Every check and timed run on 14 November used Bypass permissions, with the repo's hook still refusing
   dangerous commands; the default mode with the repo's allow list was never tried in the desktop app and may stop a
   subagent on a permission question.
3. Paste the starter below as the first message.
4. Rename the session **BUILDER** (Dylan's) or **RESEARCH** (Samuel's): the two sessions find each other by name.
5. Check that Remote Control is on for the session. Samuel opens RESEARCH from his own computer, signed in to the
   same Claude account; there the sessions are listed under Remote Control, by name.

Both of you can type into either session, from the laptop or remotely. A message looks the same to the session
wherever it was typed, so say who you are when it matters. Agree who types where: nobody has tested two people typing
into one session at the same moment.

**Another way to start them, and the one every timed run on 14 November used:** type to any Claude Code session in
the desktop app "start two sessions in ~/avalon-finals, titled BUILDER and RESEARCH, effort high, each with its
starter from START.md". It has to be a message you typed yourself.

**Fallback, not tested on 14 November: terminal tabs.** `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=40 claude -n BUILDER
--remote-control BUILDER` (and the same with RESEARCH), then `/model`, `/effort high` and the starter. `-n` names the
session and `--remote-control` shows it on claude.ai/code. Never start just one of the two with
`--dangerously-skip-permissions`.

**Model and effort:** Fable 5.2 at **high** effort for both sessions (`xhigh`/`max` think longer and answer slower).
Subagents use the session's model and effort unless a role file or the session picks another. Both ways were
run on 14 November: with every agent on Fable (two timed runs), and with the two sessions on Fable and every subagent
on Opus (the dress run, at six seats: neither session saw a subagent's work limited by it, and it used about a quarter
of the Fable allowance). **To run the subagents on Opus, add this line to each starter:** "Run every subagent on Opus:
pass model "opus" in each Agent call, and tell each subagent to do the same for its helpers." Without the line they
run on Fable. The default limit is 20
subagents running at once per session (checked on 14 Nov: the 21st spawn fails outright, it does not queue).
`.claude/settings.json` raises it to 40 in its `env` block for every session started in this folder: checked on
14 Nov, 24 subagents ran at once in a desktop-app session. To confirm in any session:
`echo $CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` prints 40.

**BUILDER starter** (BUILDER's first message):
```
You are the BUILDER session for team avalon at the No Limit Finals today. Dylan is at this terminal.
Read prompts/BUILDER.md now and follow it exactly, starting with its start-up steps.
```

**RESEARCH starter** (RESEARCH's first message):
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
2. **Dylan** runs `/no-limit-2026-setup` in BUILDER (it fetches the kit into `starter-kit/` and builds its Python;
   answer "only on this computer", not the build box),
   or downloads the kit from the portal into `starter-kit/`, and tells BUILDER "the kit is in starter-kit/".
3. **Both** read the portal's Format page. First: which case is the table, case F (6 players, 6,000 chips, antes) or case R (8 players, 2,000 chips, no ante)
   (`CLAUDE.md` §8)? Say it to your session in those words. Then weights, payouts, the upload cooldown, anything
   unusual. If the shape
   differs (build length, round spacing, number of rounds), tell RESEARCH in words ("the build is 90 minutes",
   "rounds are every 30 minutes", "there are 5 scored rounds"). Paste or screenshot the Format page into BUILDER
   too (the rules card needs it).

## During the day

- **One of you keeps the portal open in a signed-in browser tab all day** (Dylan's upload tab will do). Organizer
  announcements appear only there, as a banner refreshed every 5 minutes: the API key cannot read them (checked on
  14 November: 403), so neither script and neither session will ever see one. Read each announcement to your session
  in words, at once.
- **Dylan:** watch tab 2 (the clock) and BUILDER. You upload and activate on the portal:
  - the first bot at about minute 10;
  - the bot BUILDER names for each practice;
  - the challenger at T-12;
  - re-activate the live bot at T-9 (a click), once the practice round has started (BUILDER says when), and at T-5 at the latest if none has;
  - the chosen bot by T-3 (a click if it's already uploaded).

  **An upload activates itself, by the Finals' own pages** (read on 14 November). They say a zip that passes its upload test becomes
  the active bot without a click, and a click is how an earlier upload is put back; at Bay Area it took a click every
  time. BUILDER still checks it on the first upload (it will ask you to upload v1 and wait a moment before
  clicking). So never upload a zip just to have it on the portal, expect a late upload to be active only when its
  test has finished, and after every upload and every click check which bot the portal shows as active.

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
| A session crashed or closed | Reopen it from the desktop app's session list (it keeps its name), check its effort is still high, and say "re-read prompts/BUILDER.md (or RESEARCH.md) and your PLAN file, and re-arm your Monitor". In a terminal: `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=40 claude --resume` and pick the conversation that starts "You are the BUILDER (or RESEARCH) session"; don't use `--continue` (it may pick the other session's conversation). Remote Control normally reconnects by itself |
| Samuel can't see RESEARCH on his computer | His computer must be signed in to the same Claude account as this laptop's desktop app; then check the session's Remote Control switch is on (in a terminal session: `/remote-control RESEARCH`). On his side the sessions are listed under Remote Control, by name |
| Tab 1 still says "not today's event" at minute 0 | The key doesn't list the Finals yet. Ask the organizers whether avalon is in the Finals competition; if the Finals team has its own key (Settings → API keys on the portal), put it in `~/.config/no-limit-2026/api-key` (a file, never pasted into a chat) and restart tab 1 |
| Tab 1 or 2 stopped | Run its command again; both resume from `state/` |
| Modal "rate limit" | Tell the session: one Modal app per purpose, no bursts; wait a minute |
| You disagree at T-8 and there's no time | The rule's answer plays |

## Rehearsal with this setup (Saturday)

**Never rehearse in `~/avalon-finals`**: a rehearsal leaves bot code, releases and state behind, and Sunday must start
from a clean repo. Use a separate copy of the bundle, `~/avalon-rehearsal` (trust it once, as above), and run the
same two tabs and two sessions there, pointed at the rehearsal portal on Samuel's Mac (the simulator: ask Samuel's Claude to start
one): `python3 scripts/portal_watch.py --base http://100.111.100.112:8765/tournament/api --key-file <the rehearsal
key>` and the clock started at the rehearsal's minute 0. The clock has no line for a stop and nothing wakes a session at a clock
time: end a rehearsal by typing "stop" into both sessions, or name a clock step as the stop in what you tell them (b40,
b47 and b50 exist; there is no b45). Tell both sessions at the start: "this is a rehearsal: the
portal is a copy; nothing about the copy (its cooldown, its pages, the simulated teams) carries over to Sunday".
If you ever did run something in `~/avalon-finals`, delete it, build it again from the bundle and trust it again.
