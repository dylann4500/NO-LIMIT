# Rehearsal tonight (Thursday 12 November, 8:00-10:50 PM)

For Dylan and Samuel. A full Finals day compressed into one evening:

- **Opponents:** seven simulated finalist teams, each an AI "competitor" steering its own Claude Code
  agent in the cloud. They play us, and each other, on one 8-seat table per game.
- **Variant:** the Bay Area one (3 hole cards, discard one and expose one after the flop).
- **Our seat starts empty, as on Sunday.** If no bot is in place at a round, we forfeit it.
- **The goal is to practise the loop and find where it breaks, not to score well.**

## Schedule

| Time | Event |
|---|---|
| 7:30 | Samuel tells the Claude session that built this to set up the rehearsal. It takes about 10 minutes and nothing plays until 8:00 |
| 8:00 | **Build starts** (minute 0) |
| 8:20 / 8:30 / 8:40 / 8:50 | Practice rounds 1-4 |
| 9:00 | Scored round 1 (x1) |
| 9:10 | Practice round 5 |
| 9:20 | Scored round 2 (x2) |
| 9:30 | Practice round 6 |
| 9:40 | Scored round 3 (x3) |
| 9:50 | Practice round 7 |
| 10:00 | Scored round 4 (x4) |
| 10:10 | Practice round 8 |
| 10:20 | Scored round 5 (x5) |
| 10:30 | Practice round 9 |
| 10:40 | Scored round 6 (x6) |
| about 10:50 | Final results; 15-minute debrief |

## Where things are (on Samuel's Mac)

Our team folder is `~/NoLimit/NO-LIMIT/emu/runs/r8/avalon/`:

| Folder | What it is |
|---|---|
| `kit/` | The starter kit (appears at 8:00) |
| `portal/` | Getting started and Format pages |
| `submission/` | **The upload.** Whatever is here when a round starts is what plays, with `agent.py` at its root |
| `results/` | Round results, as they finish |
| `downloads/<round>/` | Our hand histories, full and first-1000 |
| `inbox/` | Portal notices: upload accepted or rejected, round finished |

How tonight differs from Sunday:

- **Uploading:** you copy the bot folder into `submission/` instead of using the website. The upload
  test runs when the round starts, and its verdict appears in `inbox/`. On Sunday the portal tests right
  away.
- **No dashboard:** results and downloads appear in the folders, with a notice in `inbox/`. The poller
  prompt isn't needed tonight.

## Setup (do this by 7:45)

**Practise the no-code rule.** Don't open Claude Code inside `NO-LIMIT/`, because the old bots and
scripts are there. Instead:

1. **Samuel:** create a fresh private GitHub repo, e.g. `avalon-rehearsal`. Add `FIRST_PROMPT.md`,
   `START_HERE.md` and this file, plus empty folders `bot/`, `candidates/`, `notes/` and `analysis/`.
   Invite Dylan.
2. **Both:** clone it. Dylan copies the Bay Area kit next to it (it's the `starter-kit/` folder in your
   NO-LIMIT checkout) and works in the fresh repo.
3. **Samuel:** open the Claude Code sessions in the fresh repo too. Point the analysis at
   `~/NoLimit/NO-LIMIT/emu/runs/r8/avalon/downloads/`.
4. **Upload command** (Samuel runs it on Samuel's Mac whenever Dylan says "upload vN"; it is also what
   "confirming the active bot" means tonight):

```
cd ~/avalon-rehearsal && git pull
rsync -a --delete bot/ ~/NoLimit/NO-LIMIT/emu/runs/r8/avalon/submission/
ls ~/NoLimit/NO-LIMIT/emu/runs/r8/avalon/submission/
```

   Dylan commits and pushes the bot to `bot/` first, then says the version out loud. Samuel replies with
   what `ls` shows.

## The loop, with tonight's times

**Build hour (8:00-9:00):** follow `START_HERE.md` section 5.
- 8:00: Dylan pastes prompt pack Part 1.
- by 8:10: a minimal bot is in `submission/`.
- about 8:15: the test rig starts (Part 3).
- 8:20, 8:30, 8:40: each practice round plays a different style; 8:50 re-plays the leader.

**Each window** (shown for scored round 2 at 9:20; shift by 20 minutes for the others):

| Time | What happens |
|---|---|
| about 9:07 | Round 1 download lands. Samuel starts the manager (Part 5) |
| 9:08 | Challenger uploaded |
| 9:10 | Practice round plays the challenger |
| 9:11 | Live bot put back |
| about 9:12-9:14 | Practice result lands. Decide together |
| 9:14 | Chosen bot tested with no time bank |
| 9:17 | Uploaded and confirmed |

## Two failures we trigger on purpose

1. **Crashed manager (window before scored round 3, about 9:28).** Samuel closes the manager session at
   T-12. Restart it from the notes in the repo and still reach a decision by T-8. If that's impossible,
   the previous live bot plays.
2. **Broken upload (window before scored round 4, about 9:57).** Dylan uploads a version with `agent.py`
   renamed. At 10:00, check `inbox/`: the upload should be rejected and the previous bot should play.
   Then upload the real one for practice round 8.

## Keep a log as you go

Use `notes/log.md` in the fresh repo. One line per event:

- each deadline, hit or missed and by how much;
- every rate-limit message (time and agent);
- anything that waited for Modal;
- every decision and the evidence behind it.

## Debrief questions (10:50)

1. Which deadline did we miss, and why?
2. Was the manager's one-page recommendation ready by T-8 every time?
3. Did either Claude account get throttled? Did Modal queue?
4. Did the bug hunters (Codex) find anything the Claude agents missed?
5. Which prompts were unclear or produced the wrong thing? Fix them in `FIRST_PROMPT.md` tomorrow.
6. What would we cut to make the loop fit in 20 minutes?

## Costs

About $30 of Modal compute. The team workspace's limit is about $50 total until the friend's $170 arrives
or Modal raises the limit after a payment. Keep the Modal usage page open; if it nears the limit, tell the
Claude session and it moves round-playing to the Mac.
