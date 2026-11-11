# Cluster jobs

## Job 2 (current): big mock-tournament rounds for v2

**Stop job 1 if it's still running.** Every finished tune came back "keep old": tuning against our hand-written opponents hurts. Then:

```bash
git pull
.venv/bin/python cluster/run_leagues.py --dry   # 6 jobs: 2 fields x 3 blind schedules
.venv/bin/python cluster/run_leagues.py         # 8000 iterations each, all cores, timing calibrated automatically
```

- **Machines:** with two, split by schedule. Machine A: `--only mid,fast`. Machine B: `--only slow`.
- **Results:** each job writes `cluster/results2/<field>__<schedule>/leaderboard.json`.
- **Sending them back:** push `cluster/results2/` to the `cluster-results` branch as before. Partial results are useful.
- **When we ask for a candidate check:** `git pull`, then rerun with `--cands lab/v2_next`. The candidate joins every job next to v2.

# Job 1 (retired): tune every variant

This tunes the bot for 5 poker variants × 3 blind schedules × 3 payout tables (45 jobs). Each job is a CMA-ES tune of about 40 parameters over simulated 8-player tournaments, followed by a check against opponents the tuner never saw. Everything is CPU-bound pure Python. **The GPUs aren't used, so what matters is the number of cores.**

**Keep this private.** It's our team's tournament code.

## Setup (once per machine)

Python 3.12 is required. 3.13 or later won't do.

```bash
cd pokerbot
python3.12 -m venv .venv
.venv/bin/pip install numpy eval7 scipy   # eval7 and scipy are for the AI-generated opponent bots
.venv/bin/python lab/test_engine.py   # ~20 s, must end with ALL PASS
.venv/bin/python tools/calibrate.py    # speed vs the tournament build box; send us the line it prints
```

## Run

From the repo root:

```bash
.venv/bin/python cluster/run_matrix.py --dry   # list the jobs
.venv/bin/python cluster/run_matrix.py         # run them all, one at a time, every core per job
```

Options:

- `--jobs 2` runs two jobs at once, splitting the cores between them. Use 1 job per ~16 cores.
- `--only holdem,shortdeck` restricts to some variants. **To split across machines**, give each machine different variants:
  - Machine A: `--only holdem,shortdeck`
  - Machine B: `--only flushfh,hole3`
  - Machine C: `--only omaha`. Omaha is the slowest, about 3× per table.
- `--tables 200000` is the tuning budget per job. Lower it if time is short. 100000 is still useful.
- Rerunning skips finished jobs, so it's safe to stop it and start again.

The defaults (50/30/20 payouts, mid schedule) run first, so the most useful results land early. Use `tmux`, or run it under `nohup ... &`, so it survives a dropped SSH session.

**Rough timing:** about 60 simulated tables per core per second. On a 32-core machine a 200k-table job takes about 2–3 minutes, and all 45 take about 2 hours. Split over three machines, about 45 minutes. Omaha jobs take longer.

## Results

Each job writes to `cluster/results/`:

- `<variant>__<schedule>__<payouts>.json`: the tuned parameters
- `.log`: tuner output, plus the before/after scores on never-seen opponents and a `VERDICT` line
- `.cfg.json`: the rules the job ran under

```bash
.venv/bin/python cluster/summarize.py   # one line per job
```

**To send results back**, use either option:

- Commit `cluster/results/` to a branch named `cluster-results` and push it. **Don't push to `main`.**
- Or zip the folder and send it: `zip -r results.zip cluster/results`.

Partial results are useful too. Send what's finished whenever someone asks.

## If something breaks

- **`ModuleNotFoundError: numpy`:** the venv isn't being used. Run with `.venv/bin/python`.
- **A job log ends in a traceback:** send that log. The other jobs keep running.
- **Very slow:** check `nproc`. Other heavy work on the same machine slows every job.
