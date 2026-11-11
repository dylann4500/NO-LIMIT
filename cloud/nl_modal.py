"""Batch evals on Modal: the starter kit's real engine, fanned out over many containers.

Every shard runs cloud/kit_match.py, the same script you run locally, in an image built from
the kit's own requirements.txt (Python 3.12, the competition's exact libraries) with the kit
SDK installed. The repo's bot folders are synced at each run, so edits need no image rebuild.

  prep/.venv/bin/modal run cloud/nl_modal.py --bots bots/v10,bots/v10,bots/v9s,bots/v9s,... \
      --tables 4000 --name v10_vs_v9s

Results land in cloud/results/<name>.json (per table) with a summary printed: points per seat
with 95% intervals, and each folder's paired difference against the first folder listed.

`lab` runs any command from prep/ on one large container, for the lab's multi-core tuners and
leagues:  prep/.venv/bin/modal run cloud/nl_modal.py::lab --cmd "python lab/test_engine.py"

Privacy: only the folders in SYNC are uploaded. Hand histories (data/), the kit's .venv and
anything named hands-*.jsonl* are never sent.
"""

import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "starter-kit"
REMOTE = "/repo"

# Repo folders synced into every container, at the same relative paths.
SYNC = ["bots", "tests", "reviewer", "tools", "cloud", "prep", "starter-kit/examples"]
NEVER = [
    "**/__pycache__/**", "**/*.pyc", ".venv/**", "**/.venv/**", "**/.DS_Store",
    "**/hands-*.jsonl*", "**/hand-history/**",
    "run2/**", "run3/**", "run4/**", "run5/**", "snap2/**", "submission/upload/**",
    "results/**",
]

app = modal.App("nolimit-eval")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("build-essential")  # eval7 builds from source if no wheel matches
    .pip_install_from_requirements(str(KIT / "requirements.txt"))
    .add_local_dir(str(KIT / "sdk"), "/kit/sdk", copy=True, ignore=["**/__pycache__/**", "**/*.egg-info/**"])
    .run_commands("pip install -e /kit/sdk/agent-protocol -e /kit/sdk/engine -e /kit/sdk/agent-sdk")
)
for folder in SYNC:
    image = image.add_local_dir(str(ROOT / folder), f"{REMOTE}/{folder}", ignore=NEVER)


@app.function(image=image, cpu=4.0, memory=4096, timeout=3600, max_containers=200)
def play_shard(args: list[str]) -> dict:
    """One kit_match.py run; `args` are its command-line arguments."""
    out = f"/tmp/shard-{time.time_ns()}.json"
    proc = subprocess.run(
        [sys.executable, f"{REMOTE}/cloud/kit_match.py", *args, "--out", out],
        cwd=REMOTE, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"kit_match failed ({proc.returncode}):\n{proc.stderr[-4000:]}")
    result = json.loads(Path(out).read_text())
    result["host_cpus"] = os.cpu_count()
    return result


@app.function(image=image, cpu=32.0, memory=32768, timeout=6 * 3600)
def lab_job(cmd: str, collect: list[str]) -> dict:
    """Run a shell command from a writable copy of prep/; return its output and any files
    under the `collect` paths (relative to prep/) as {path: text}."""
    work = "/work/prep"
    shutil.copytree(f"{REMOTE}/prep", work, dirs_exist_ok=True)
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    proc = subprocess.run(["bash", "-lc", cmd.replace("../.venv/bin/python", "python")
                           .replace(".venv/bin/python", "python")],
                          cwd=work, capture_output=True, text=True, env=env)
    files = {}
    for rel in collect:
        base = Path(work, rel)
        paths = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()] if base.exists() else []
        for p in paths:
            try:
                files[str(p.relative_to(work))] = p.read_text()
            except UnicodeDecodeError:
                pass
    return {"returncode": proc.returncode, "stdout": proc.stdout[-200_000:], "stderr": proc.stderr[-50_000:],
            "files": files, "cpus": os.cpu_count()}


def merge(shards: list[dict]) -> dict:
    tables = sorted((t for s in shards for t in s["tables"]), key=lambda t: t["table"])
    first = shards[0]
    return {"seed": first["seed"], "rules": first["rules"], "labels": first["labels"],
            "groups": first["groups"], "tables": tables,
            "elapsed_s": sum(s["elapsed_s"] for s in shards),
            "bot_stderr": {k: v for s in shards for k, v in s["bot_stderr"].items()}}


def report(out: dict) -> str:
    groups = list(dict.fromkeys(out["groups"].values()))
    tables = out["tables"]
    n = len(tables)

    def per_table(g: str) -> list[float]:
        labels = [l for l, gg in out["groups"].items() if gg == g]
        return [sum(t["points"][l] for l in labels) / len(labels) for t in tables]

    def ci(xs: list[float]) -> tuple[float, float]:
        return statistics.fmean(xs), (1.96 * statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0)

    hands = statistics.fmean(t["hands"] for t in tables)
    lines = [f"tables={n} variant={out['rules']['variant']} seed={out['seed']} mean hands/table={hands:.0f} "
             f"shard CPU-time={out['elapsed_s']:.0f}s"]
    base = per_table(groups[0])
    for g in groups:
        labels = [l for l, gg in out["groups"].items() if gg == g]
        xs = per_table(g)
        m, h = ci(xs)
        fails = sum(t["failures"][l] for t in tables for l in labels)
        decs = sum(t["decisions"][l] for t in tables for l in labels)
        places = [sum(t["places"][l] == k for t in tables for l in labels) / (n * len(labels)) for k in (1, 2, 3)]
        line = (f"  {g:36s} seats={len(labels)} pts/seat {m:6.2f} ±{h:4.2f}  "
                f"1st/2nd/3rd {places[0]:4.0%}/{places[1]:4.0%}/{places[2]:4.0%}  failed {fails}/{decs}")
        if g != groups[0]:
            dm, dh = ci([b - x for b, x in zip(base, xs)])
            line += f"  | {groups[0]} minus this: {dm:+.2f} ±{dh:.2f}"
        lines.append(line)
    return "\n".join(lines)


@app.local_entrypoint()
def main(
    bots: str,
    tables: int = 2000,
    per_shard: int = 50,
    seed: str = "",
    name: str = "",
    variant: str = "flop_discard_reveal",
    variant_file: str = "",
    bank: int = 100,
    decision_ms: int = 1,
    hand_cap: int = 250,
    hands_per_level: int = 20,
    payouts: str = "",
    payout_total: int = 0,
    blinds: str = "",
    starting_stack: int = 0,
    concurrency: int = 8,
    cpu: float = 4.0,
):
    """--bots is a comma-separated list of bot folders (repo-relative), one per seat."""
    seats = [b.strip() for b in bots.split(",") if b.strip()]
    for b in seats:
        if not (ROOT / b / "agent.py").is_file():
            raise SystemExit(f"{b}/agent.py not found (paths are relative to the repo root)")
        if not any(b == f or b.startswith(f + "/") for f in SYNC):
            raise SystemExit(f"{b} is outside the synced folders {SYNC}")
    seed = seed or f"s{time.time_ns() % 10**9}"
    common = ["--seed", seed, "--variant", variant, "--bank", str(bank), "--decision-ms", str(decision_ms),
              "--hand-cap", str(hand_cap), "--hands-per-level", str(hands_per_level),
              "--concurrency", str(concurrency)]
    for flag, value in (("--variant-file", variant_file), ("--payouts", payouts), ("--blinds", blinds)):
        if value:
            common += [flag, value]
    if payout_total:
        common += ["--payout-total", str(payout_total)]
    if starting_stack:
        common += ["--starting-stack", str(starting_stack)]
    jobs = []
    for first in range(0, tables, per_shard):
        count = min(per_shard, tables - first)
        jobs.append([*seats, *common, "--tables", str(count), "--first-table", str(first)])
    print(f"{len(jobs)} shards x <= {per_shard} tables, seed {seed}")
    t0 = time.time()
    runner = play_shard if cpu == 4.0 else play_shard.with_options(cpu=cpu, memory=int(max(2048, cpu * 1024)))
    shards = list(runner.map(jobs, order_outputs=False))
    out = merge(shards)
    out["wall_s"] = round(time.time() - t0, 1)
    out["args"] = {"bots": seats, "tables": tables, "per_shard": per_shard, "cpu": cpu}
    out["shard_elapsed_s"] = sorted(s["elapsed_s"] for s in shards)
    dest = ROOT / "cloud" / "results" / f"{name or seed}.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out))
    print(report(out))
    print(f"wall {out['wall_s']}s; per-table results in {dest.relative_to(ROOT)}")
    for bot, log in out["bot_stderr"].items():
        print(f"--- {bot} stderr (tail) ---\n{log[-1500:]}")


@app.local_entrypoint()
def lab(cmd: str, collect: str = "", cpu: float = 32.0, name: str = ""):
    """Run `cmd` from prep/ on one container. --collect is comma-separated prep-relative paths
    to bring back into cloud/results/<name>/."""
    paths = [c.strip() for c in collect.split(",") if c.strip()]
    res = lab_job.with_options(cpu=cpu, memory=int(max(4096, cpu * 1024))).remote(cmd, paths)
    print(res["stdout"])
    if res["stderr"]:
        print(res["stderr"], file=sys.stderr)
    dest = ROOT / "cloud" / "results" / (name or f"lab-{int(time.time())}")
    for rel, text in res["files"].items():
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    print(f"exit {res['returncode']} on {res['cpus']} CPUs; {len(res['files'])} files -> {dest.relative_to(ROOT)}")
