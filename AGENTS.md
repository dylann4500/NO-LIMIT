# Agent instructions

This is team avalon's working repo (Dylan Nguyen and Samuel Choi) for the No Limit pokerbot competition. We finished 6th of 148 at the Menlo Park regional on 2026-11-06 and qualified for the **Finals on Sunday, November 15, 2026 in San Francisco** as a wildcard. The Finals use the same format with a **different, unannounced poker variant**. Prizes: $100k / $50k / $25k for 1st-3rd.

## The Finals plan (current, as of 2026-11-12, night)

Questions about what we're doing on Sunday: start with `docs/START_HERE.md` (what we learned, the plan, and
the agent hub), then `docs/SUNDAY.md` (the day step by step) and `docs/REHEARSAL.md` (practice runs);
`docs/Finals_Handbook.pdf` is all three plus the game-plan visual. On the day each person runs the **agent
hub** (`hub/`, see `hub/README.md`): four agents per person (a Chat that leads, three workers), a clock, a portal watcher, and
decisions asked in the Chat and answered in words. The agents follow `docs/FIRST_PROMPT.md` and `docs/TWIST_NOTES.md`
(humans no longer paste them); `docs/EVIDENCE_TABLE.md` grades every finding; `docs/FINALS_PLAYBOOK.md` has
the longer reasoning; `research/finals_prep/` holds the studies; `emu/` is the rehearsal emulator and portal
copy. Where these disagree with older docs (`rebuild/`, the write-up), the Finals docs are newer and win.

## Working in parallel (task board): do this before anything else

Several agents on different machines work in this repo at once. They coordinate through one shared board (`coord/coord.py`, details in `coord/README.md`). A session-start hook prints it; an edit hook blocks edits to files another agent holds.

1. **Look first:** `python3 coord/coord.py status`. Never start something that is already in progress or done there.
2. **Hold before you touch:** take a posted task (`take [ID]`) or claim your own work (`claim ID "what" --paths <every path you will edit>`) before editing files or launching an eval, tuning or training run. A pure eval run claims with no paths but a `--cmd`, so nobody repeats it.
3. **Check in** with `note ID "..."` at milestones or about every 30 minutes; `renew ID` before the expiry.
4. **Finish:** `git pull --rebase`, push your commits, then `done ID --result "<one line: the number, and where the output is>"`. Blocked: `release ID --why ...`.
5. **Merge hygiene:** new work goes in new folders named for you (`bots/<name>-<version>/`); shared files need a task holding them; pull with rebase before starting and before pushing; never edit a path another agent holds.
6. **Manager agents** post tasks (`post`), pin direction (`note --pin`), and re-queue stale work. They don't edit code without claiming it.

## Read first

1. `README.md`: what we built, how the night was run, and the results.
2. `docs/writeup/avalon-writeup.pdf`: the full write-up (design, evaluation method, results, error analysis, post-event findings).
3. `docs/STEERING.md`: the time-stamped decision log from the night. `docs/BUILDLOG.md`: the build agent's test log.
4. `rebuild/`: the knowledge-only kit (rules, architecture, strategy, field, tests, timeline, prompts) for building a bot from scratch in under an hour.
5. `prep/README.md`: the pre-event training repo (simulator, tuners, opponent field, variant-generic v2 bot).

## Layout

| Path | What it is |
|---|---|
| `bots/<version>/` | Every bot built on the night. `bots/v10` is the final submission |
| `releases/` | The exact zips uploaded or considered |
| `reviewer/` | Release gate (`gate.sh`), behavior diff (`bdiff.sh`, `behavior.py`), round analyzer (`analyze_round.sh`) and hand-history analyses |
| `tests/` | Local matches (`match.py`; `--bank 0` = upload-test conditions), fuzzing, field-proxy opponents |
| `research/` | Variant research, round 2 review, competitor research, and `post_event/` (the analysis behind the write-up) |
| `prep/` | Snapshot of the pre-event repo `samrocksnature/pokerbot` (branch `prep/adapter-field-cluster` at `17d4f61`, plus the uncommitted `lab/v2_next/`). Training and eval infrastructure: `prep/lab/` (engine, field bots, CMA-ES tuners, league, adapter, v2 bot), `prep/cluster/`, `prep/benchmark/` (Slumbot) |
| `coord/` | The shared task board (`coord.py`) every agent uses to take work and hold files; it lives on the `coord` branch. `.claude/settings.json` hooks show it at session start and guard edits |
| `cloud/` | Batch evals on the kit's real engine, locally (`kit_match.py`) or fanned out on Modal (`nl_modal.py`); see `cloud/README.md`. Modal client: `prep/.venv/bin/modal` |
| `data/` | `data/README.md` maps every hand-history file to its round. The files themselves are local only (`data/hands/`, git-ignored) |
| `starter-kit/` | The organizer's kit, local only (git-ignored, not redistributable). Its Python at `starter-kit/.venv/bin/python` has eval7 |
| `docs/writeup/` | The write-up, LaTeX source and PDF (build with `tectonic`) |

## Rules for working here

- **Keep the repo private.** Never commit hand histories (they contain other teams' play and exceed GitHub's file limit) or the starter kit.
- **The official rules** are in `prep/docs/official_rules.txt`; on event day the kit's `RULES.md`, `AGENTS.md` and `state.config` override everything here. Note rule 3.4: it names Astra and Codex as the AI tools teams may use to build bots. Confirm with the organizers what else is allowed before the Finals.
- Run Python that reads hand histories with `-I`.
- Bot code: under 1 ms per decision with no time bank, never raises an exception, only legal action kinds, per-table state only through `memory`. Check every release with the bot's own check run and the upload test, and report the measured numbers (`reviewer/gate.sh` is the regional's gate: its stats band would have blocked the regional winner; don't use it as a gate).
- Judge changes on real-field hand data, never on wins against our own older bots.
- `prep/run2`-`run5` and `prep/snap2` are raw evidence: never edit or import from them.

## Lessons from the regional (details in the write-up, Sections 6-7)

- The flop over-calling leak was live through round 2 and decided our placing; the data to catch it existed after the first practice round. Analyze real hand histories from the very first round.
- `poker_agent_sdk.icm()` scores a busted stack 0 even when the bust place pays. Unit-test every library function a decision depends on, with edge cases (2 players, busted stacks, paid places).
- v4 beat our own old bots by +4.4 locally and scored 9.17 in the real field. Local wins against our own versions mean nothing.
- Track how the field responds to us, not just our own VPIP and PFR: fold to 3-bets, and fold to bets by street against the field's rates. We folded to 82-87% of 3-bets while the field's 3-bet rate nearly doubled, and after v6 we folded to heads-up bets 20-30 points more often than the field.
- 1,000-table samples swing by about ±2 points; compare full files of the same round type.
