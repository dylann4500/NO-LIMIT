> **Snapshot.** This folder is a copy of `samrocksnature/pokerbot` (branch `prep/adapter-field-cluster` at `17d4f61`, plus the then-uncommitted `lab/v2_next/`), imported into NO-LIMIT on 2026-11-11. It was written before the regional, so it predates the real kit and the event. Paths below are relative to `prep/`. The repo root's `AGENTS.md` takes precedence.

# Agent instructions

Read `README.md` first, then `docs/event_portal.md`, then `docs/BUILD_PROMPT.md` Parts A to E. Once the kit ships, its own `AGENTS.md`, `RULES.md` and `state.config` override all of them.

- Work in `lab/`. Never treat `run2`-`run5` or `snap2` as source.
- Bot code: stdlib only unless a measured gain justifies a package from the kit's `requirements.txt`, under 1 ms per decision, never raises, only offered action kinds, integer raise totals within the legal range.
- Per-table state goes through `memory`, never `self` or globals.
- Run the gate through `./make_submission.sh` before reporting a bot as done, and report the measured numbers.
- Promote parameters only if they win on the holdout field.
- `docs/BUILD_PROMPT.md` is generated. Edit `docs/prompt_template.md` and rerun `tools/build_doc.py`.
- Keep this repo private.
