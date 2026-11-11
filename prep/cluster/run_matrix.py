"""Tune the bot for every variant x blind schedule x payout table, one tune_event.py run per job.
usage (from the repo root): .venv/bin/python cluster/run_matrix.py [--tables 200000] [--procs 0] [--jobs 1] [--only holdem,omaha] [--limit N] [--dry]
Each job writes cluster/results/<job>.json (tuned parameters), <job>.log (tuner output and the verdict on fields the
tuner never saw) and <job>.cfg.json (the rules it ran under). Finished jobs are skipped on a rerun, so it can be
stopped and restarted. Summarise with cluster/summarize.py."""
import argparse, itertools, json, os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(ROOT, "lab")
OUT = os.path.join(ROOT, "cluster", "results")

VARIANTS = ["holdem", "shortdeck", "flushfh", "hole3", "omaha"]
# Only 10/20 and 20-hand levels are announced. These bracket the later levels.
SCHEDULES = {
    "slow": [[10, 20], [15, 30], [25, 50], [40, 80], [60, 120], [100, 200], [150, 300], [250, 500]],
    "mid": [[10, 20], [15, 30], [20, 40], [30, 60], [40, 80], [50, 100], [75, 150], [100, 200], [150, 300], [200, 400],
            [300, 600], [400, 800], [500, 1000]],
    "fast": [[10, 20], [20, 40], [30, 60], [50, 100], [75, 150], [100, 200], [150, 300], [200, 400], [300, 600], [400, 800],
             [600, 1200], [800, 1600], [1000, 2000]],
}
# 50/30/20 is the default; a round "may draw payouts per table", so cover a flatter and a steeper table too.
PAYOUTS = {"p532": [50, 30, 20, 0, 0, 0, 0, 0], "p4321": [40, 30, 20, 10, 0, 0, 0, 0], "p6535": [65, 35, 0, 0, 0, 0, 0, 0]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", type=int, default=200000); ap.add_argument("--sigma", type=float, default=0.1)
    ap.add_argument("--eval-tables", type=int, default=12000)
    ap.add_argument("--procs", type=int, default=0, help="processes per job; 0 = all cores / jobs")
    ap.add_argument("--jobs", type=int, default=1, help="jobs at once"); ap.add_argument("--base", default="lab/tuned_real1.json")
    ap.add_argument("--only", default=""); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    procs = a.procs or max(2, (os.cpu_count() or 4) // a.jobs)
    only = set(filter(None, a.only.split(",")))
    jobs = []
    # Default rules first, so the most useful results land early.
    for p, s, v in itertools.product(PAYOUTS, ["mid", "slow", "fast"], VARIANTS):
        if only and v not in only:
            continue
        name = f"{v}__{s}__{p}"
        if os.path.exists(os.path.join(OUT, name + ".json")):
            continue
        cfg = {"blinds": SCHEDULES[s], "points": PAYOUTS[p], "hands_per_level": 20, "max_hands": 250, "start": 2000}
        cp = os.path.join(OUT, name + ".cfg.json")
        env = dict(os.environ, POKER_VARIANT=v, EVENT_CONFIG=cp)
        cmd = [sys.executable, "tune_event.py", "--base", os.path.join(ROOT, a.base), "--out", os.path.join(OUT, name + ".tmp.json"),
               "--tables", str(a.tables), "--sigma", str(a.sigma), "--procs", str(procs), "--eval-tables", str(a.eval_tables)]
        jobs.append((name, cmd, env, cfg))
    jobs = jobs[: a.limit] if a.limit else jobs
    print(f"{len(jobs)} jobs, {a.jobs} at a time, {procs} processes each, {a.tables} tables per tune", flush=True)
    if a.dry:
        for j in jobs:
            print(j[0])
        return
    running = []
    while jobs or running:
        while jobs and len(running) < a.jobs:
            name, cmd, env, cfg = jobs.pop(0)
            json.dump(cfg, open(env["EVENT_CONFIG"], "w"))
            log = open(os.path.join(OUT, name + ".log"), "w")
            running.append((name, subprocess.Popen(cmd, cwd=LAB, env=env, stdout=log, stderr=subprocess.STDOUT), time.time()))
        time.sleep(5)
        for r in running[:]:
            name, proc, t0 = r
            if proc.poll() is not None:
                running.remove(r)
                tmp = os.path.join(OUT, name + ".tmp.json")
                # tune_event exits 1 when the new parameters lose on the holdout; keep them anyway, the log says so.
                if os.path.exists(tmp):
                    os.replace(tmp, os.path.join(OUT, name + ".json"))
                print(f"{name}: exit {proc.returncode} in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
