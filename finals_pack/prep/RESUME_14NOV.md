# Where the overnight work stopped (Saturday 14 November, 07:12) and how to resume

The account's weekly usage reached 98% at 07:11, so everything below was left in a safe state. After the reset,
tell the lead session "resume".

## Finished but NOT yet reviewed or merged (each on its own local branch, one worktree each under
`~/Documents/GitHub/nolimit-live/.claude/worktrees/`)

| Branch | What | Commits |
|---|---|---|
| `claude/consistency-f16a1e` | Consistency read of the bundle: 19 small fixes; 10 judgment items listed in its report | `3f6078d..c310d03` |
| `claude/sample-check-43944f` | `notes/pre/first1000.md` (the first-1000 file is a fair sample; our score read +0.40 ± 0.24 high; recommends fetching 5,000 tables first) and `notes/pre/placings.md` | `07e153d` |
| `claude/dossiers-a3a3a5` | `notes/pre/finalists.md`: cards for nine Bay Area teams, Boston and Pittsburgh second-hand, a recognition table | `81872ad` |
| `claude/tabletop-887e98` | `prep/TABLETOP_14NOV.md`: 18 scenarios, 36 fresh agents: 5 clear, 10 slow, 3 split, 0 wrong; 14 proposed wordings (none applied) | `93486eb` |
| `claude/pre-variants-6eefac` | Three more drills in `notes/pre/variants.md` and `TWIST_NOTES.md` (now 19 twists; `theory.md` still says eighteen) | `0b926ae`, `3020f19` |

The lead reviews each diff, merges what is sound into `emu/rehearsal`, runs the quick suite and pushes. Nothing
here has been checked by the lead yet: treat every number in the table as that session's own claim.

## Timed runs

- **Run A (Fable, turn-draw variant, 06:27-07:11): finished.** Reports: `~/avalon-speedrun/notes/SPEEDRUN-builder.md`
  and `SPEEDRUN-research.md`. BUILDER reports v1-v10 released and every practice pick on time; only "styles
  legal by minute 15" was late (minutes 16-29). Not yet read by the lead; its instruction fixes are not applied.
- **Run B (Opus 5.5, same variant) and run C (Fable, auction variant): held, never started.** Their clocks are
  stopped and reset; their four sessions are idle. To run one: `cd ~/avalon-speedrun-b` (or `-c`),
  `python3 scripts/clock.py start HH:MM`, `python3 scripts/clock.py run`, and tell both of its sessions the new
  minute 0. Run A plus five research sessions used about 23 points of the weekly limit in 40 minutes.
- Bot code from these runs lives only in `~/avalon-speedrun*`. It never goes into the Sunday repo.
