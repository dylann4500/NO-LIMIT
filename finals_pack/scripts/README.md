# scripts/: the mechanical jobs

Plain `python3` (3.9+, standard library only). Run them from the repo root. Runtime state lives in `state/`,
inboxes in `inbox/`, round data in `data/rounds/` (all git-ignored). Check everything: `python3 scripts/test_scripts.py`
(about 2 minutes; `--quick` skips the sped-up clock run; `--emu` adds the rehearsal portal when `emu/` is next door).

## The two daemons (humans start them, each in its own terminal tab; both resume from `state/` after a restart)

| Command | What it does |
|---|---|
| `python3 scripts/portal_watch.py` | Reads the portal (GET only) every 15 s (6 s while a round should be finishing). Saves each finished round to `data/rounds/NN-<stage>/` (`results.json`, `round.json`, `hands-first-1000.jsonl.gz`, then `hands-full.jsonl.gz`, `played_by.txt`), keeps `state/status.md` current, writes `state/rounds_seen.json` for the clock, runs `analysis/roundcard.py` and `analysis/fp_train.py` on new data (90 s cap), and posts every event to the inboxes. |
| `python3 scripts/clock.py run` | Posts each step of `scripts/timeline.json` once, to the right inbox; prints Dylan's upload/activate reminders and decision time loudly here (with a beep); keeps `state/clock.md` current; posts the cut-offs (and heads-ups) to the owner session; pins a scored round the portal saw start off-schedule; holds a window whose previous round hasn't started. |

Portal options: `--once` (one poll; prints team, competition, rounds, active bot, the upload cooldown), `--base URL`
(rehearsal: `http://<mac>:8765/tournament/api`), `--key-file PATH` (default `~/.config/no-limit-2026/api-key`),
`--small-hands` (first-1000 only), `--hands-url TEMPLATE` (`{tid}`, `{team}`, `{q}`/`{qa}`).
**Hand data** comes from the real portal's own address, checked on 14 November against the regional's rounds (the
same bytes as our files): `<base>/teams/<team>/tournaments/<round>/hands`, with `?tables=1000` for the first 1,000
tables. The rehearsal copy's `<base>/tournaments/<round>/hands?subset=first-1000` is tried second.
**Still not downloading?** Copy the download link from the portal's round page, then (no restart):
`python3 scripts/portal_watch.py --set-hands-url '<link>'`. Prefer the full-file link; the watcher adds the subset.
**What the watcher takes from the real portal by itself:**
- the upload cooldown the portal states (in `state/status.md` and `--once`);
- the variant's announcement: it posts "THE VARIANT IS ANNOUNCED" to both inboxes with the portal's own time for
  minute 0 and saves the rules text to `state/variant.md` (a head start; the kit and the Format page still decide);
- a newer competition on our key: started while the key still lists only the regional, it says so ("not today's
  event") and switches to the Finals by itself within a minute of it appearing, with no restart;
- old rounds: one that finished more than 12 hours before the watcher first saw it keeps its results but gets no
  hand files (the regional's are 2 GB).
The key is sent only to the portal's own site, never printed, and dropped on a redirect to another host.

## The clock

| Command | |
|---|---|
| `python3 scripts/clock.py start now` / `start 14:02` | minute 0 ("2:05" typed in the afternoon = 14:05) |
| `python3 scripts/clock.py format --build 90 --gap 30 --scored 5` | the Format page's shape (any subset) |
| `python3 scripts/clock.py pin scored3 15:40` / `pin practice5 15:30` / `pin round2.5 15:30` | a round's real time: it and later rounds move; minute 0 and the past don't |
| `python3 scripts/clock.py show` | minute 0, every round's time, the next steps (also in `state/clock.md`) |
| `python3 scripts/clock.py reset` | clears the schedule, sent steps and cut-offs |
| `python3 scripts/clock.py pre builder` / `pre research` | the pre-event research tasks ("start the research") |
| `python3 scripts/clock.py start now --scale 0.5` | rehearsals only: 1 event-minute = 30 s |

Model: scored rounds at minute `build` (60), then every `gap` (20); practices 1-4 at minutes 20/30/40/50 counted
back from scored round 1; one practice 10 minutes before each later scored round. Steps: `b<minute>` in the build,
`T-<n>` before each scored round (round 1 gets T-9 on). Edit the wording in `timeline.json`; the clock re-reads it.
Cut-offs (judged from files; nobody is told to hurry, the pre-registered fallback plays):
data landed T-10 (RESEARCH) · round card within 3 min of the data (RESEARCH) · `one-change <stage>` line in
`notes/LEDGER.md` T-8 (RESEARCH, heads-up T-10) · a new `releases/*.zip` T-12 (BUILDER, heads-up T-14) ·
`state/decisions.md` mentions "round k" T-7 (BUILDER) · the chosen bot's zip exists T-4 (BUILDER, heads-up T-6).

## Messages and the live bot

| Command | |
|---|---|
| `python3 scripts/feed.py builder` / `research` | what each main session runs under the Monitor tool: prints each new inbox line (one line = one wake-up), nothing else; after a re-arm it first prints the lines it missed |
| `python3 scripts/say.py research "text"` | append `HH:MM:SS [from] text` to `inbox/research.log` (+ `state/events.log`); `both` for both |
| `python3 scripts/say.py --record research "text"` | log a message already sent with SendMessage (events.log only) |
| `python3 scripts/live.py v7 "why"` | BUILDER only: declare the live bot (`state/live.json`, must be in `releases/`); posts "LIVE BOT is now v7" to both. `live.py` alone shows it and what the portal runs |

`state/live.json` = the bot for the next scored round (in the build hour: the next practice's). Don't declare the
challenger for a window's practice round; the T-9 reminder puts the live bot back.

## The guard

`scripts/guard.py` is the PreToolUse hook in `.claude/settings.json` (no permission prompts otherwise). It refuses,
with the reason and the safe way: pattern kills (`pkill`, `killall`, `pgrep | xargs kill`), a foreground `wait` /
`sleep` ≥ 20 s / sleep loop, deletes outside the repo and /tmp (or of `.git`, a top-level shared folder, a glob at
a top level), force pushes, `git reset --hard`, `git clean -f`, `git stash` / `restore .` / `checkout -- .` in the
shared folder, sudo, `curl | sh`, Modal deletes, and any write to the organizers' site. Refusals are logged in
`state/guard.log`. Try it: `echo '{"tool_name":"Bash","tool_input":{"command":"pkill -f x"}}' | python3 scripts/guard.py`
