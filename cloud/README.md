# cloud/: batch evals on Modal

Plays bots against each other on the **starter kit's real engine** (`starter-kit/sdk`, pokerkit underneath), locally or fanned out over Modal containers. The same script, `kit_match.py`, runs in both places, so a cloud number is a local number at scale.

## Setup (done once per machine)

```bash
prep/.venv/bin/pip install modal     # the Modal client lives in the prep venv
prep/.venv/bin/modal token new       # browser approval; writes ~/.modal.toml
```

The kit must be unpacked in `starter-kit/` with its `.venv` (see the root README). The Modal image is built from the kit's own `requirements.txt` (Python 3.12, the competition's exact library versions) plus the kit SDK, and is cached after the first build. **If the kit changes (Finals kit), the image rebuilds automatically on the next run.**

## Local run

```bash
starter-kit/.venv/bin/python cloud/kit_match.py --tables 200 \
    bots/v10 bots/v10 bots/v9s bots/v9s bots/v6 bots/v6 bots/v3b bots/v3b
```

Each argument is one seat. Seats are reshuffled every table. Output: points per seat with a 95% interval over tables, 1st-place rate, and failed/total decisions per bot folder. `--out FILE` keeps every table's result.

## Modal run

```bash
prep/.venv/bin/modal run cloud/nl_modal.py::main \
    --bots bots/v10,bots/v10,bots/v9s,bots/v9s,bots/v6,bots/v6,bots/v3b,bots/v3b \
    --tables 4000 --name v10_field
```

- Splits the tables into shards of `--per-shard` (default 50; 100 is a good size above 2,000 tables), one container each, up to 200 at once. `--cpu` sets CPUs per container (default 4).
- With two local entrypoints in the file, the `::main` (or `::lab`) suffix is required.
- Prints points per seat ±95%, places, failed decisions, and **each folder's paired difference against the first folder listed** (computed per table, so the shared luck of a table cancels). Put the candidate first.
- Writes per-table results to `cloud/results/<name>.json` (git-ignored).
- Bot folders are synced at every run from `bots/`, `tests/`, `reviewer/`, `tools/`, `cloud/`, `prep/` and `starter-kit/examples/`. Edit a bot and rerun; no rebuild.

### Measured (2026-11-11, all-strong field v10/v9s/v6/v3b x2, 4,000 tables)

| | 4 CPUs per container (default) | 2 CPUs (`--cpu 2`) |
|---|---|---|
| Wall time (40 shards x 100 tables) | 103 s | 67 s |
| Shard time min/median/max | 27 / 41 / 49 s | 27 / 41 / 57 s |
| Failed decisions | 7 in 3.8M | 47 in 3.8M |
| Compute used | ~1.8 core-hours | ~0.9 core-hours |

- **Resolution:** 4,000 tables gives ±0.36 points per seat and ±0.6 on a paired difference (95%). 20,000 tables gets the paired difference to about ±0.26. The real event's scored rounds were ~20,000 tables.
- **Result:** v10 13.12, v9s 13.24, v6 12.89, v3b 10.74. v6 through v10 are within noise of each other in this field, and v3b is 2.4 behind, matching the direction of the real field (v6's fold rules).
- **Failed decisions on Modal are host noise** at a rate of a few per million (0 on the Mac in 185k). They don't move averages, but **gate latency on the Mac or the build box**, never on a cloud run. Use 4 CPUs when timing matters, 2 to halve cost for strategy comparisons.
- A container runs about 2.5 tables/s. Wall time is mostly container start and the slowest shard, so very small runs aren't faster in the cloud than on the Mac (~10 tables/s locally).

### Rule knobs (both scripts)

| Flag | Meaning | Default |
|---|---|---|
| `--variant` | an installed engine variant | `flop_discard_reveal` |
| `--variant-file path.py` | play a variant module that is not installed (a mock Finals variant); the module defines `VARIANT` like the kit's own | |
| `--bank` | time bank ms per table; `0` + 2 seats + `--hand-cap 20` = the upload test | 100 |
| `--decision-ms` | decision limit | 1 |
| `--hand-cap`, `--hands-per-level` | table length and blind pace | 250, 20 |
| `--blinds` | `'10/20,20/40,...'`, last level repeats | kit schedule |
| `--payouts`, `--payout-total` | `'50,30,20'`, or ranges `'40-60,20-40,10-30'` with a total, as the engine draws per table | 50/30/20 |
| `--starting-stack` | | 2000 |

### Lab jobs on one big container

For `prep/lab`'s multi-core tuners and leagues (pure Python, CPU-bound):

```bash
prep/.venv/bin/modal run cloud/nl_modal.py::lab --cpu 32 \
    --cmd "python lab/test_engine.py" --collect "cluster/results2" --name leagues1
```

The command runs from a writable copy of `prep/`; `--collect` paths come back into `cloud/results/<name>/`.

## What is never uploaded

Only the folders listed above are synced. `data/` (hand histories), every `.venv`, `hand-history/` folders, and any file named `hands-*.jsonl*` are excluded in `nl_modal.py` (`SYNC`, `NEVER`). Uploading hand histories needs the team's explicit OK first: they contain other teams' play.
