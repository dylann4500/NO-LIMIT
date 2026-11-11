# coord/: the shared task board

One board for every agent and person working in this repo, on any machine and network. A manager agent posts tasks, workers take them, and everyone sees who is doing what and which files are off-limits. That way nobody runs the same eval twice or edits a file someone else is changing.

**How it works.** The board lives on its own git branch, `coord`, on GitHub. Each change is one small commit pushed there. Git refuses a push that isn't based on the latest board, so when two agents grab the same task at the same moment, exactly one wins and the other gets a clear "already taken". `coord.py` never touches your working tree, index or current branch, so the board itself can never cause a merge conflict. It's stdlib Python; no install.

## Setup (each person, once per clone)

```bash
git clone https://github.com/dylann4500/NO-LIMIT.git && cd NO-LIMIT
python3 coord/coord.py whoami --set <your-name>   # e.g. dylan, sam, kai
python3 coord/coord.py status
```

Claude Code picks up `.claude/settings.json` in the repo, which adds two hooks to every session:
- **Session start:** the board is printed into the agent's context, along with the rules.
- **Before every Edit/Write:** if the file is inside a task another agent holds, the edit is blocked with a message naming the holder.

## Commands

| Who | Command | Does |
|---|---|---|
| everyone | `status` | the board: pinned direction, open tasks, in progress, stale, finished, recent check-ins |
| everyone | `note [ID] "text"` | a check-in, on a task or board-wide |
| manager | `post ID "what" [--for NAME] [--priority N] [--paths ...] [--cmd ...] [--compute ...] [--details ...]` | queue a task; `--for` reserves it for one agent |
| manager | `assign ID NAME` | reassign an open task (`''` = anyone) |
| manager | `note --pin "text"` | direction shown at the top of the board (latest 5 pins) |
| worker | `take [ID]` | take a task; with no ID, the best one for you (yours first, then priority) |
| worker | `claim ID "what" --paths ...` | self-started work |
| worker | `renew ID [--hours N]` | keep holding it (default expiry 4 h) |
| worker | `done ID --result "..."` | finish, with a one-line result and where the output is |
| worker | `release ID [--why ...]` | give it up; a posted task goes back to the queue |
| anyone | `check PATH...` | exit 2 if someone else holds the path |

`--paths` are repo paths the work will edit; they are held while the task is active. Paths overlap when one contains the other (`bots/dn` holds `bots/dn/agent.py`). Claiming a whole top-level folder needs `--broad`. An expired task shows as STALE and anyone may take it over. Several agents on one clone? Give each its own name per command with `--as NAME` (or the `COORD_NAME` environment variable).

## Rules that keep merges clean

1. **Hold before you touch.** Take or claim a task, with every path you will edit, before editing files or launching an eval or training run.
2. **Own folders.** New bots and experiments go in new folders named for you (`bots/<name>-<version>/`, `cloud/results/` stays local). Shared files (`cloud/kit_match.py`, `AGENTS.md`, `prep/lab/engine.py`...) need a task holding them.
3. **Small, frequent pushes.** `git pull --rebase` before you start and before you push; push when the task is done, then mark it `done`.
4. **Results as text.** Raw eval output stays out of git. The `done --result` line says what came out and where it lives.

## Prompts

**Manager agent** (paste into the Claude session that distributes work):

```
You are the manager for the NO-LIMIT team. Read AGENTS.md, then run `python3 coord/coord.py status`.
Break the current goal into independent tasks that don't edit the same files, and post each one with
`python3 coord/coord.py post ID "what" --paths <files it edits> --cmd <exact command if it's an eval>
--details <what done looks like>`. Use --for NAME only when a task needs a specific person's machine or
context. Pin today's direction with `note --pin`. Every 20-30 minutes, run `status`: read check-ins and
results, post follow-ups, re-queue stale work, and never post a task that duplicates one in progress or done.
Don't edit code yourself unless you claim it first.
```

**Worker agent:**

```
You are a worker on the NO-LIMIT team. Read AGENTS.md, then run `python3 coord/coord.py status`.
Take work with `python3 coord/coord.py take` (or `take ID`), do exactly that task, and only edit the paths it
holds. Post a short `note ID "..."` check-in at milestones or every ~30 minutes, `renew ID` if it will run
past its expiry, then push your commits (git pull --rebase first) and finish with
`done ID --result "<one line: the number and where the output is>"`. If you're blocked, `release ID --why ...`.
When done, take the next task.
```
