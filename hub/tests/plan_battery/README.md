# Plan battery: does the game plan make the Overseer decide well?

16 decision scenarios (standings, evidence, deadlines) with a pre-registered correct answer each. Most catch
over-caution (holding when the evidence says act); S2, S9 and S15 catch recklessness (acting on weak or broken
evidence). Each scenario is given to the Overseer model with its real instructions (role, PROTOCOL, team
directory, DECISION_RULES, COMMON_RULES) plus the plan sections it reads at kickoff.

Arms: `old` (snapshots saved next to run.py as old_roster.py, old_START_HERE.md, old_FIRST_PROMPT.md),
`new` (the working tree), `compact` (new instructions with the kickoff documents removed, as after compaction).

    git show <rev>:hub/roster.py > old_roster.py; git show <rev>:docs/START_HERE.md > old_START_HERE.md
    git show <rev>:docs/FIRST_PROMPT.md > old_FIRST_PROMPT.md; git show <rev>:hub/hub.py > old_hub.py
    uv run --no-project --with claude-agent-sdk==0.2.181 python run.py claude-opus-5-5 1 old,new

Results on 2026-11-13 (before -> after the DECISION_RULES rewrite): Opus old 13/16, new 16/16; Sonnet x2
old 26/32, new 29/32, compact 30/32. Rerun after any change to the plan or the agents' rules.
