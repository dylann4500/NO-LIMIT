"""Play a tournament round's shards on Modal (emu/tournament.py, the kit engine), merge locally.

Each local shard runs two processes per team, so a 20-team round can't use many shards on one
machine; Modal containers take a shard each instead. The round's active bots are uploaded to the
volume, every shard reads them from there and writes its results and per-team download parts back,
and the parts are merged locally into the real-format downloads (tournament.py merge).

  from modal_rounds import play_round_on_modal
  play_round_on_modal(field, seed, iterations, local_round_dir, shards=40)
"""

import io
import json
import shutil
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
EMU = ROOT / "emu"
KIT = ROOT / "starter-kit"
VOLUME = "emu-teams"
_LOCK = threading.Lock()  # one app.run() at a time, even when rounds overlap

app = modal.App("nolimit-emu-rounds")
vol = modal.Volume.from_name(VOLUME, create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("build-essential")
    .pip_install_from_requirements(str(KIT / "requirements.txt"))
    .add_local_dir(str(KIT / "sdk"), "/kit/sdk", copy=True, ignore=["**/__pycache__/**", "**/*.egg-info/**"])
    .run_commands("pip install -e /kit/sdk/agent-protocol -e /kit/sdk/engine -e /kit/sdk/agent-sdk")
    .add_local_file(str(EMU / "tournament.py"), "/emu/tournament.py")
)


@app.function(image=image, cpu=8.0, memory=16384, timeout=3600, volumes={"/vol": vol}, max_containers=100)
def play_shard(field: dict, seed: str, first: int, count: int, key: str, k: int) -> dict:
    """One shard: bots and field come from /vol/<key>; output goes to /vol/<key>/shard<k>."""
    vol.reload()
    fpath = Path(f"/tmp/field{k}.json")
    fpath.write_text(json.dumps(field))
    out = f"/vol/{key}/shard{k}"
    p = subprocess.run([sys.executable, "/emu/tournament.py", "play", "--field", str(fpath), "--seed", seed,
                        "--first-iteration", str(first), "--iterations", str(count), "--out", out,
                        "--concurrency", "8"], capture_output=True, text=True)
    vol.commit()
    return {"k": k, "rc": p.returncode, "stderr": p.stderr[-3000:]}


def _tar(path: Path) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        t.add(path, arcname=".")
    return buf.getvalue()


def play_round_on_modal(field: dict, seed: str, iterations: int, rdir: Path, round_no: int,
                        shards: int = 40, key_prefix: str = "rounds", local_teams: tuple = ("avalon",)) -> dict:
    """Upload bots, play `iterations` over `shards` containers and merge there. Only the round summary,
    results.jsonl and `local_teams`' downloads come back; everyone else's downloads stay on the volume
    (summary["remote_downloads"]) for delivery straight into their sandboxes."""
    key = f"{key_prefix}/{rdir.parent.parent.name}/{rdir.name}-{int(time.time())}"
    remote = json.loads(json.dumps(field))
    import uuid
    remote.setdefault("tournament_id", str(uuid.uuid4()))  # fresh ids per round, as on the platform
    remote.setdefault("ids", {e["team"]: str(uuid.uuid4()) for e in remote["entries"]})
    with vol.batch_upload(force=True) as up:
        for i, e in enumerate(remote["entries"]):
            src = (ROOT / e["bot"]).resolve()
            dest = f"/{key}/bots/{i}"
            for f in src.rglob("*"):
                if f.is_file() and "__pycache__" not in f.parts:
                    up.put_file(str(f), f"{dest}/{f.relative_to(src)}")
            e["bot"] = f"/vol{dest}"
    per = -(-iterations // shards)
    jobs = [(remote, seed, k * per, min(per, iterations - k * per), key, k) for k in range(shards) if k * per < iterations]
    with _LOCK, app.run():
        results = list(play_shard.starmap(jobs))
    bad = [r for r in results if r["rc"]]
    if bad:
        raise RuntimeError(f"{len(bad)} shards failed; first: {bad[0]['stderr'][-1500:]}")
    shard_dirs = [f"/vol/{key}/shard{k}" for *_, k in jobs]
    with _LOCK, app.run():
        summary = merge_round.remote(remote, key, shard_dirs, round_no)
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "round.json").write_text(json.dumps(summary, indent=1))
    for name in ("results.jsonl",):
        _download(f"{key}/merged/{name}", rdir / name)
    for slug in local_teams:  # only the local team(s) need their downloads on this machine
        for entry in vol.listdir(f"{key}/merged/downloads/{slug}"):
            _download(entry.path, rdir / "downloads" / slug / entry.path.rsplit("/", 1)[-1])
    summary["remote_downloads"] = f"/vol/{key}/merged/downloads"
    return summary


def _download(path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in vol.read_file(path):
            f.write(chunk)


@app.function(image=image, cpu=4.0, memory=16384, timeout=3600, volumes={"/vol": vol})
def merge_round(field: dict, key: str, shard_dirs: list[str], round_no: int) -> dict:
    """Merge shards into per-team real-format downloads on the volume; return the round summary."""
    vol.reload()
    fpath = Path("/tmp/field.json")
    fpath.write_text(json.dumps(field))
    out = f"/vol/{key}/merged"
    subprocess.run([sys.executable, "/emu/tournament.py", "merge", "--field", str(fpath), "--round", str(round_no),
                    "--out", out] + shard_dirs, check=True, capture_output=True)
    vol.commit()
    return json.loads(Path(out, "round.json").read_text())
