# The team build box (regional, 2026-11-06)

What `reviewer/gate.sh` step 4 (`GATE_BOX`) ran on, and why its latency numbers were the authority. Recorded 2026-11-11 from the repo's own notes; the box itself is offline (SSH times out), so nothing below was re-measured.

## Machine

- **What it was:** the organizers' per-team build machine, "a remote Ubuntu machine set up like the ones your bot plays on in the tournament" (`prep/docs/portal_getting_started.md`). Each member logged in as `ubuntu@<address>` with their own SSH key registered on the portal; the address came from the team page's Build box tab.
- **CPU:** 2 vCPU, Intel Xeon 8488C (`prep/tools/calibrate.py`, `BOX_MS = 26.4`, best of 9).
- **Speed vs the Mac:** about 1.3x slower on the bot's workload, eval7 Monte Carlo included (`calibrate.py`, `rebuild/02_ARCHITECTURE.md`).
- **OS / Python:** Ubuntu; the kit's venv was Python 3.12 built from the kit's `requirements.txt` (same pins as `docs/env/kit-env.txt`). The exact Ubuntu and patch versions were not recorded.
- **Threads:** production limits OpenMP/MKL/OpenBLAS to one thread (`portal_getting_started.md`); our bots were stdlib + eval7, so this did not matter for them.

## Layout used by the gate

```
~/work/live/
  starter-kit/          the event kit, with its own .venv (Python 3.12)
  tests/match.py        copied from this repo's tests/
  gate_<release>/       created per gate run: the release's files, scp'd from the Mac
```

`gate.sh` copies the release to `~/work/live/gate_<name>/` over `scp`, then runs `tests/match.py --tables 20 --bank 0 --hand-cap 20` against `examples/check_or_fold` for 3 seeds (`b1 b2 b3`) and sums the failed decisions. The kit and `tests/` were synced by hand (`scp`) at the start of the night; nothing synced them automatically.

## What was measured there

- Every release from m10 to v10: 0 failed decisions in the no-bank upload test on the box (`docs/STEERING.md`).
- Collector pauses were the only decisions over 1 ms on the box (up to 7 ms) until `gc.freeze()` plus `gc.set_threshold(20000, 50, 100)`; after that the slowest decision was 0.3 ms (`rebuild/02_ARCHITECTURE.md`).
- The Mac's own latency numbers were unreliable under load (BUILDLOG: "Build-box gate is the authority on latency").

## For the Finals

The Finals box is a new machine with a new address. Re-register SSH keys if the portal asks, rebuild `~/work/live` as above, and rerun `prep/tools/calibrate.py` on it to get a fresh time scale. Never commit the address, user names or keys.
