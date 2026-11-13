# Automatic hand-offs between our agents

For Dylan and Samuel. Adds to `START_HERE.md` and prompt pack Part 5: they say what each agent does,
this says how work gets from one laptop's agents to the other's without anyone copying files.
We still talk out loud about everything (decisions, uploads, "order's up"); this only removes the
copy-paste between agents. Written 12 November, before the rehearsal; tonight tests it.

## How it works

- The shared repo is the only channel. Agents on different laptops and accounts can't message
  each other, and email or chat would need a person to copy files.
- Each receiving chat has a folder. A sender writes one self-contained file there and pushes.
- The receiving chat keeps a check running in the background: every 5 seconds a `git fetch`, which
  downloads nothing unless something changed and costs no tokens. When a new file lands, the
  check exits, Claude Code wakes the chat, and it pulls, does the work, logs it, pushes and
  restarts the check. Measured from Dylan's Mac: a check takes about 0.6 s and a pull about 1 s, so
  a file is picked up within about 10 seconds of being pushed.
- A chat that is busy finishes its current step first, then picks up the file.
- **Nothing here uploads a bot or changes the active bot.** Uploads stay by hand (tonight: Samuel's
  rsync when Dylan says "upload vN"), read out loud every time.

| Folder | Written by | Picked up by |
|---|---|---|
| `orders/main/` | Samuel's agents: findings from practice rounds, reproduced bug fixes, the change we chose at T-8 | Dylan's main chat |
| `orders/builders/` | Samuel's manager: one finding per file | Dylan's builders chat |
| `candidates/<name>/` | Builders on both laptops | Samuel's rig chat |
| `bot/` (tonight), `bots/` (Sunday) | Dylan's main chat | Samuel's rig and bug hunters |
| `status.md`, `analysis/`, `profiles/` | Samuel's manager and analyses | Both of us |

Order files are named `<round>-<nn>-<short-name>.md` (for example `r3-02-fix-fold-counter.md`) and
must stand alone: what to do, why (the numbers), which bot or bots, the check that must pass, and the
deadline. Each receiving folder has a `DONE.md` where the receiver logs one line per file it handled.
Every agent commits only its own files, never `git add -A`, and on a refused push does
`git pull --rebase` and retries.

## The prompts to add

### A · Watcher (append to a chat's main prompt; replace FOLDER)

```
For the rest of the event, stay in sync with our shared repo. Start a check in the BACKGROUND (never
in the foreground): a loop that every 5 seconds runs `git fetch -q origin` and exits as soon as
origin/main has a file in FOLDER that isn't listed in FOLDER/DONE.md. When it exits: `git pull
--rebase`; read each new file in name order and carry it out; append one line per file to
FOLDER/DONE.md ("<file> <time> <one-line result>"); commit only DONE.md and the folders you own (never
`git add -A`); push, and if the push is refused, `git pull --rebase` and push again; then start the
background check again. If you're mid-task when it fires, finish the current step first. Never stop
watching unless I tell you to.
```

### B · Dylan's builders chat (a new chat, opened just before scored round 1)

```
You run our candidate builders for the rest of the event. Read the "Candidate builders" prompt in
docs/FIRST_PROMPT.md Part 5. For every new file in orders/builders/, start one subagent with that
prompt, filling in the live bot's folder and the finding from the file; run them in parallel, don't
wait for one to finish before starting the next. Each subagent works only in its own
candidates/<short-name>/ folder, commits only that folder, and pushes; Samuel's test rig picks it up
from there. Log each subagent's one-line result in orders/builders/DONE.md. You never edit the live
bot or the challenger.
```
followed by watcher A with FOLDER = `orders/builders/`.

### C · Samuel's manager (append to the Part 5 manager prompt)

```
Dylan's chats pick up work from the repo automatically, so hand it over as files, not messages:
- Each finding you want built as a candidate: one file in orders/builders/ (<round>-<nn>-<name>.md)
  with the finding, its size and uncertainty, the rates it should move, and the live bot's folder.
  Push each as soon as it's ready; don't batch. His builders chat starts one builder per file. Your own
  2-5 builders take the findings you don't send there.
- Anything for the live bot or the challenger: one self-contained file in orders/main/ with what to
  change, why, which bot(s), the check that must pass and the deadline. Only two kinds go there
  without asking us: bug fixes you have reproduced (they go into both bots every window) and refreshed
  team profiles. Everything else waits for our decision at T-8; then write the chosen change as an
  order.
- Run the two bug hunters on Codex from your shell, in the background, one on each bot:
  codex exec -s workspace-write -C <repo> -o analysis/bughunt/<round>-<bot>.md "<the Part 5 bug-hunter
  prompt with that bot's folder; write your own tests only under analysis/bughunt/<round>-<bot>/>"
  Read each report when it finishes. Codex never commits; you do.
- Watch our downloads folder <path> (local, no git): when a new round's download appears, treat it as
  me handing it to you. Keep your state in notes/manager.md so a new session can take over.
- Before writing status.md, `git pull` and read orders/main/DONE.md and orders/builders/DONE.md.
- Commit only status.md, notes/manager.md, analysis/ and orders/, never `git add -A`.
```

### D · Samuel's leak finder on practice downloads (append to Part 2 in the build hour)

```
Write your top three findings as one file, orders/main/p<n>-findings.md (n = practice round), in the
order format: each finding with its size, uncertainty and the change you'd make. Push it as soon as
it's written. Dylan's main chat picks it up automatically.
```

### E · Samuel's test rig (append to Part 3a)

```
Keep a background check like this one running all event: every 5 seconds `git fetch -q origin`; exit
when a folder under candidates/ or bot/ is new or changed on origin/main since your last test. When
it exits: `git pull --rebase`, test what's new, append one line per candidate to rig/results.md,
commit only rig/, push, and restart the check.
```

## Who pastes what, tonight

Times are tonight's; on Sunday the same steps run on the event clock.

| Time | Dylan | Samuel |
|---|---|---|
| By 7:45 | Clone the rehearsal repo; copy the kit next to it; open one new chat in the repo (main), with a permission mode that doesn't stop to ask | Create the repo with `FIRST_PROMPT.md`, `START_HERE.md`, `REHEARSAL_TONIGHT.md`, **`TWIST_NOTES.md`** and this file, plus folders `bot/`, `candidates/`, `notes/`, `analysis/`, `orders/main/`, `orders/builders/`, `rig/`; invite Dylan; open the analysis, manager and rig chats in the repo; Codex signed in |
| 8:00 | Main chat: **Part 1** (weights from Samuel, notes folder, kit path) + "read docs/TWIST_NOTES.md" + "`bot/` is the upload folder: put exactly the files to play there, `agent.py` at its root, push, and tell me the version" + **A** with `orders/main/` | Read the Format page aloud (weights, payouts); start the timers |
| By 8:10 | Minimal bot pushed to `bot/`; say "upload v1" | Run the upload command; read back what `ls` shows |
| ~8:15 | (Main starts the B and C style subagents by itself) | Rig chat: **Part 3a** + **E** |
| 8:20-8:50 | Before each practice round: push that style to `bot/`, say "upload vN" | After each practice result: analysis chat **Part 2** with the download path + **D** |
| ~8:55 | New builders chat: **B** + **A** with `orders/builders/` | |
| ~9:07 | | Manager chat: **Part 5 manager** + **C**; rig chat: **Part 3b** |
| Every window | Uploads at T-12 (challenger), T-9 (live back), T-3 (chosen). Orders arrive in main and builders by themselves | Uploads on Dylan's word. The manager picks up each download by itself; read status.md by T-8 and decide together |

The two drills on the rehearsal sheet still apply (crashed manager about 9:28, broken upload about
9:57). For the crashed manager: start a new manager chat with Part 5 + C and "take over from
notes/manager.md".

## What to check tonight

- Does each watcher fire within about 10 seconds of a push, and does the chat restart it afterwards?
  Note any chat that stopped watching.
- Do two agents pushing at once ever lose a file or block each other?
- Does any chat interrupt work it shouldn't (main mid-build)?
- Does anything wait on a person that shouldn't?
