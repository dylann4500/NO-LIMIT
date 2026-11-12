"""Run mrun jobs on Modal (clone-only jobs; real-bot heroes stay local because of the 1 ms limit).
usage: prep/.venv/bin/python modal_app.py JOBS.json [chunk=400]
Bundle (built by bundle.sh): mrun.py, lib/, fields/<f>/{field.json,cdf.json,adj.json,teams/*/params.json,arch/*.json}.
No hand histories or acc.pkl leave this machine."""
import json, os, pickle, sys, time
from pathlib import Path
import modal

HERE = Path(__file__).resolve().parent
KIT = Path("/Users/samuelchoi/NoLimit/NO-LIMIT/starter-kit")
app = modal.App("nolimit-strategy-sim")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("build-essential")
    .pip_install_from_requirements(str(KIT / "requirements.txt"))
    .add_local_dir(str(KIT / "sdk"), "/kit/sdk", copy=True, ignore=["**/__pycache__/**", "**/*.egg-info/**"])
    .run_commands("pip install -e /kit/sdk/agent-protocol -e /kit/sdk/engine -e /kit/sdk/agent-sdk")
    .add_local_dir(str(HERE / "bundle"), "/mg", copy=True)
)


def _one(t):
    import asyncio
    sys.path.insert(0, "/mg")
    sys.path.insert(0, "/mg/lib")
    import mrun
    job, first, count = t
    rows, acc = asyncio.run(mrun.run(job, first, count))
    if job["mode"] == "hero":
        acc = {k: {"HERO": v.get("HERO", {})} for k, v in acc.items()}
    return job["name"], rows, acc


@app.function(image=image, cpu=8.0, memory=8192, timeout=3000, max_containers=95, retries=2)
def chunk(tasks: list):
    import multiprocessing
    with multiprocessing.Pool(8) as p:
        return p.map(_one, tasks, chunksize=1)


def main():
    import collections, types

    def _merge(a, b):
        for team, cells in b["cells"].items():
            d = a["cells"].setdefault(team, {})
            for k, v in cells.items():
                c = d.get(k)
                if c is None:
                    d[k] = list(v)
                else:
                    for i in range(4):
                        c[i] += v[i]
        for team, sz in b["sizes"].items():
            d = a["sizes"].setdefault(team, {})
            for k, hist in sz.items():
                dd = d.setdefault(k, {})
                for v, c in hist.items():
                    dd[v] = dd.get(v, 0) + c
        for team, s in b["stats"].items():
            d = a["stats"].setdefault(team, collections.Counter())
            d.update(s)
        return a
    fitlib = types.SimpleNamespace(merge=_merge, new_acc=lambda: {"cells": {}, "sizes": {}, "stats": {}})
    jobs = json.load(open(sys.argv[1]))
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    out = HERE / "out"
    todo = [j for j in jobs if not (out / (j["name"] + ".pkl")).exists()]
    print(len(jobs), "jobs,", len(todo), "to run", flush=True)
    if not todo:
        return
    args = []
    for j in todo:
        p = per // 3 if j["mode"] == "tourney" else per
        for f in range(0, j["tables"], p):
            args.append((j, f, min(p, j["tables"] - f)))
    by = {j["name"]: j for j in todo}
    res = {n: ([], fitlib.new_acc()) for n in by}
    left = {n: sum(1 for a in args if a[0]["name"] == n) for n in by}
    t0 = time.time()
    with app.run():
        groups = [args[i:i + 8] for i in range(0, len(args), 8)]
        for name, rows, acc in (x for g in chunk.map(groups, order_outputs=False) for x in g):
            res[name][0].extend(rows)
            fitlib.merge(res[name][1], acc)
            left[name] -= 1
            if left[name] == 0:
                rows, acc = res.pop(name)
                rows.sort(key=lambda x: (x[0], str(x[1])))
                with open(out / (name + ".pkl"), "wb") as f:
                    pickle.dump({"job": by[name], "rows": rows, "acc": acc}, f)
                m = sum(x[2] for x in rows) / len(rows)
                print(f"{name:44s} n={len(rows)} pts={m:6.2f} t={time.time() - t0:.0f}s", flush=True)
    print("total chunks", len(args), "elapsed", round(time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
