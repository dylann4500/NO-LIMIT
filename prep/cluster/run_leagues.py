"""Big mock-tournament rounds on the cluster: how v2 (our submission) ranks against the generated field under each
blind schedule, with enough tables to resolve half a point.
usage (from the repo root): .venv/bin/python cluster/run_leagues.py [--iters 8000] [--procs 0] [--only fast,mid] [--time-scale 0.7] [--dry]
Each job writes cluster/results2/<job>/leaderboard.json and a .log; finished jobs are skipped on a rerun.
Extra candidates (e.g. lab/v2_next) join every job with --cands lab/v2_next."""
import argparse, os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(ROOT, "lab")
OUT = os.path.join(ROOT, "cluster", "results2")


def bots(pred):
    fb = os.path.join(LAB, "field_bots")
    return [os.path.join("field_bots", d) for d in sorted(os.listdir(fb)) if pred(d) and os.path.exists(os.path.join(fb, d, "agent.py"))]


FIELDS = {
    # The latest simulated field: Claude teams after two rounds of improving, OpenAI teams after one.
    "latest": lambda: bots(lambda d: d.endswith("_r3") or (d.startswith("openai_") and d.endswith("_r2"))),
    # Every bot version we built, generation 1 to 3.
    "all": lambda: bots(lambda d: True),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=8000); ap.add_argument("--procs", type=int, default=0)
    ap.add_argument("--only", default=""); ap.add_argument("--cands", default=""); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--time-scale", default="auto", help="auto: measured with tools/calibrate.py against the build box")
    a = ap.parse_args()
    procs = a.procs or max(2, (os.cpu_count() or 4) - 1)
    if a.time_scale == "auto":  # the Mac measured 0.83 of the box and ran at 0.7; keep the same margin here
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import calibrate
        a.time_scale = f"{0.85 * calibrate.bench() / calibrate.BOX_MS:.2f}"
        print("time scale", a.time_scale)
    only = set(filter(None, a.only.split(",")))
    cands = [os.path.abspath(c) for c in a.cands.split(",") if c]
    jobs = []
    for sched in ("mid", "fast", "slow"):
        if only and sched not in only:
            continue
        for fname, f in FIELDS.items():
            name = f"{fname}__{sched}" + ("__" + "_".join(os.path.basename(c) for c in cands) if cands else "")
            if os.path.exists(os.path.join(OUT, name, "leaderboard.json")):
                continue
            cmd = [sys.executable, "league.py", "--iters", str(a.iters), "--procs", str(procs), "--hh-iters", "0", "--schedule", sched, "--time-scale", a.time_scale,
                   "--ours", os.path.join(LAB, "v2"), "--out", os.path.join(OUT, name), "--entrants", *f(), *cands]
            jobs.append((name, cmd))
    print(f"{len(jobs)} jobs, {procs} processes each, {a.iters} iterations")
    for name, cmd in jobs:
        print(name, flush=True)
        if a.dry:
            continue
        os.makedirs(os.path.join(OUT, name), exist_ok=True)
        t = time.time()
        with open(os.path.join(OUT, name + ".log"), "w") as log:
            subprocess.run(cmd, cwd=LAB, stdout=log, stderr=subprocess.STDOUT)
        print(f"  done in {time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
