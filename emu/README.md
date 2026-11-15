# emu/: a full rehearsal of the No Limit Finals

A private, local replica of the tournament for workflow and prompting practice: the real kit engine, the
portal's pages and rules, real-format hand-history downloads, and a field of 19 synthetic teams. Each is a
simulated competitor (an LLM playing a person at the keyboard, with a persona) steering a Claude Code agent
(Opus 5.5 or Fable 5.2) in its own Modal sandbox, from the variant announcement to the last round. You play
the 20th seat, **avalon**, from a local folder.

Everything stays private: the portal pages are a rehearsal copy of the organizers' site, and hand
histories never leave this machine or the team's Modal workspace.

## Run a rehearsal

```bash
prep/.venv/bin/python emu/rehearsal.py --run full1                 # 19 teams, real clock, regional variant
prep/.venv/bin/python emu/rehearsal.py --run t1 --personas pressure_point,pocket_rockets --scale 0.1   # quick test
prep/.venv/bin/python emu/rehearsal.py --run r8 --field finals --round-iterations 3000 --prep-scale 0 --wait   # 7 finalists + avalon
```

| Option | Meaning |
|---|---|
| `--scale` | timeline speed (1.0 = real: 60-minute build, practice every 10 min, scored rounds every 20 min) |
| `--weights` | round weights, `1,2,3,4,5,6` (Bay Area) or `1,2,3,5,8,13` (Boston) |
| `--prep-scale` | scales the pre-event research some teams do (0 = none; Pocket Rockets researches 90 min) |
| `--variant` / `--variant-rules` | a mock Finals variant: an engine variant module plus its RULES.md. The run builds a mock kit with it (`variants/make_kit.py`, in `runs/<run>/kit_build`) for every team's kit, the upload test, local rounds and the Modal round image; a self-check before READY stops the run if the variant doesn't load (test: `emu/test_variant_install.py`) |
| `--cooldown` | upload cooldown in seconds (default 30, as at the regional), on the Format page and enforced by `portal_server.py` |
| `--practice-iterations`, `--round-iterations` | round sizes (defaults 1,000 / 5,000; 3,000 keeps scored rounds inside 20 min) |
| `--local-rounds` | play rounds on this Mac instead of Modal |
| `--field finals` | 7 simulated finalists, each with regional notes (`teams/finalists/`): per-seat learning, recognition by sizes, defence to wide re-raises, simulation, copying the leaders. With avalon, one 8-seat table |
| `--avalon-start` | avalon's bot at the start: `empty` (default, as on Sunday) or a `bots/` folder |
| `--table` | `regional` (default: 8 x 2,000, no antes) or `finals` (6 x 6,000, blinds and antes 10/20/4 .. 2000/4000/800; `tables.py`): the kit's defaults, the upload test, every round, seating and the Format page |
| `--field-file` | a fixed-bot field (`fields/finals_dress.json`): opponents as team + bot folder or zip, the same bot all event; no sandboxes, no agent teams, no Modal secret |
| `--shards`, `--local-workers`, `--local-concurrency` | Modal shards a round (19; the app is capped at `EMU_MAX_CONTAINERS`, default 20, incl. the merge); local shard processes (4) and tables at once per process (4) |

Needs: the kit in `starter-kit/` (with `.venv`), the Modal client in `prep/.venv` signed in to the team
workspace, and the Modal secret `emu-anthropic` (a Claude Code OAuth token or an Anthropic API key).

## Finals rehearsal with a fixed field

See `NOTES_FINALS_REHEARSAL.md`: Finals table, 17 fixed opponents from the 14 Nov timed run, avalon through the mock
portal (`portal_server.py`) from any folder, read by `finals_pack/scripts/portal_watch.py`.

## Play avalon yourself

When the run starts it prints the event clock. Your team folder is `emu/runs/<run>/avalon/`:
`kit/` and the Format page with the variant (both appear only at the start), `portal/` (Getting started, Format), `submission/` (starts as `bots/v10`), and, as rounds finish,
`results/`, `downloads/<round>/` (full and `-first-1000`) and `inbox/` (portal notices). Open your own
Claude Code (or Codex) in that folder and work the way you will on Sunday. At every round start
`submission/` is snapshotted, put through the portal's upload test, and played.

## What's in here

| Path | What it does |
|---|---|
| `rehearsal.py` | the event: sandboxes, clock, uploads and upload test, rounds, results pages, deliveries |
| `tournament.py` | one round on the kit engine: seating, scoring, real-format per-team downloads |
| `modal_rounds.py` | rounds sharded over Modal containers and merged there |
| `teams/steer.py` | the simulated competitor loop (runs inside each sandbox) |
| `teams/personas/` | the 19 competitors: background, how they steer AI, habits; some research before the event, rent compute, or attempt hail-mary rewrites |
| `teams/run_team.py` | the sandbox image (2-vCPU build box + Claude Code) and single-phase runs |
| `portal/pages/` | the portal's Getting started and Format pages (variant and weights filled in per run) |
| `pilot.py` | the first pilot: 4 teams, build + 2 rounds |
| `realism.py` | synthetic vs real field: per-team profiles (train R1-R3 / held-out R4-R6, real top 20) and rank dynamics |
| `benchmark/gtow.py` | GTO Wizard benchmark adapter (public leaderboard: avalon's serious hold'em bots only) |

## Realism targets (what the synthetic field should reproduce)

- Real Bay Area top-20 profiles: VPIP, PFR, 3-bet, fold to 3-bet, jams, fold to bet by street, c-bet,
  showdown rates (`emu/runs/real_field/reference.json`, built by `realism.py real`).
- Field drift across rounds (Bay Area: 3-bet rate 8% to 18% over six rounds).
- Rank persistence between rounds: Bay Area 0.76-0.83, Boston median 0.68; big jumps come from rewrites,
  not incremental tweaks (Boston account, 2026-11-11).

## Costs

Measured in the pilot: about $15-17 API-equivalent per team-hour of active work (Opus or Fable), under $2
for the simulated human. Claude Code reports a resumed session's running total, so a session's cost is
its last figure, not the sum. Modal compute (sandboxes and round containers) is small next to that;
check the workspace's usage page for exact figures.
