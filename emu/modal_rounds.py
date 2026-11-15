"""Play a tournament round's shards on Modal (emu/tournament.py, the kit engine), merge locally.

Each local shard runs two processes per team, so a 20-team round can't use many shards on one
machine; Modal containers take a shard each instead. The round's active bots are uploaded to the
volume, every shard reads them from there and writes its results and per-team download parts back,
and the parts are merged locally into the real-format downloads (tournament.py merge).

  from modal_rounds import play_round_on_modal
  play_round_on_modal(field, seed, iterations, local_round_dir, shards=19)

Containers: EMU_MAX_CONTAINERS (environment, read at import; default 20) caps the whole app: play_shard gets
that number minus one, merge_round one, so overlapping rounds never hold more (the workspace limit is 100 and the
team's own test rig may use 80 of it during a rehearsal).

The image installs the kit's SDK from EMU_KIT (environment, read at import) or starter-kit/: for a
mock variant, rehearsal.py points EMU_KIT at the mock kit it built, so the engine has the variant.
open_session() keeps one app running for the whole event (one app creation instead of two per
round); without it each call runs its own app.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
EMU = ROOT / "emu"
KIT = Path(os.environ.get("EMU_KIT") or ROOT / "starter-kit")
VOLUME = "emu-teams"
MAX_CONTAINERS = max(2, int(os.environ.get("EMU_MAX_CONTAINERS") or 20))
SHARD_CONTAINERS = MAX_CONTAINERS - 1  # one is kept for merge_round
# One tournament.py process drives every table of its shard (one engine, one core), so an 8-CPU container runs
# several, each on a slice of the shard's iterations (EMU_PROCS_PER_CONTAINER, default 4, 2 tables at once each).
PROCS = max(1, int(os.environ.get("EMU_PROCS_PER_CONTAINER") or 4))
_LOCK = threading.Lock()  # one app.run() at a time, even when rounds overlap
_SESSION = None  # an app.run() context kept open for the whole event (open_session)

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


@app.function(image=image, cpu=8.0, memory=16384, timeout=3600, volumes={"/vol": vol},
              max_containers=SHARD_CONTAINERS)
def play_shard(field: dict, seed: str, first: int, count: int, key: str, k: int) -> dict:
    """One shard: bots and field come from /vol/<key>; output goes to /vol/<key>/shard<k>/p<j>, one folder per
    process (PROCS processes, each on a slice of [first, first + count))."""
    vol.reload()
    fpath = Path(f"/tmp/field{k}.json")
    fpath.write_text(json.dumps(field))
    per = -(-count // PROCS)
    procs, dirs = [], []
    for j in range(PROCS):
        if j * per >= count:
            break
        out = f"/vol/{key}/shard{k}/p{j}"
        dirs.append(out)
        procs.append(subprocess.Popen(
            [sys.executable, "/emu/tournament.py", "play", "--field", str(fpath), "--seed", seed,
             "--first-iteration", str(first + j * per), "--iterations", str(min(per, count - j * per)), "--out", out,
             "--concurrency", str(max(1, 8 // PROCS))], stdout=subprocess.DEVNULL,
            stderr=open(f"/tmp/shard{k}-p{j}.err", "w")))
    errs = [(p.wait(), Path(f"/tmp/shard{k}-p{j}.err").read_text()) for j, p in enumerate(procs)]
    vol.commit()
    bad = [e for rc, e in errs if rc]
    return {"k": k, "rc": 1 if bad else 0, "stderr": (bad[0] if bad else "")[-3000:], "dirs": dirs}


def _tar(path: Path) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        t.add(path, arcname=".")
    return buf.getvalue()


def play_round_on_modal(field: dict, seed: str, iterations: int, rdir: Path, round_no: int,
                        shards: int = SHARD_CONTAINERS, key_prefix: str = "rounds", local_teams: tuple = ("avalon",),
                        remote_downloads: bool = True) -> dict:
    """Upload bots, play `iterations` over `shards` containers and merge there. Only the round summary,
    results.jsonl and `local_teams`' downloads come back; everyone else's downloads stay on the volume
    (summary["remote_downloads"]) for delivery straight into their sandboxes.
    remote_downloads=False (a fixed field: nobody else needs downloads): the merge writes only `local_teams`'
    downloads, in the container's own disk, and returns them; nothing merged is written to the volume (volume
    writes run at a few MB/s: every team's downloads of a 5,000-table round took over 10 minutes)."""
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
    with _running():
        results = list(play_shard.starmap(jobs))
    bad = [r for r in results if r["rc"]]
    if bad:
        raise RuntimeError(f"{len(bad)} shards failed; first: {bad[0]['stderr'][-1500:]}")
    shard_dirs = [d for r in sorted(results, key=lambda r: r["k"]) for d in r["dirs"]]
    rdir.mkdir(parents=True, exist_ok=True)
    if not remote_downloads:
        teams = [e["team"] for e in remote["entries"] if _slug(e["team"]) in local_teams]
        with _running():
            out = merge_round_local.remote(remote, shard_dirs, round_no, teams)
        (rdir / "round.json").write_text(json.dumps(out["summary"], indent=1))
        for rel, data in out["files"].items():
            (rdir / rel).parent.mkdir(parents=True, exist_ok=True)
            (rdir / rel).write_bytes(data)
        out["summary"]["remote_downloads"] = None
        return out["summary"]
    with _running():
        summary = merge_round.remote(remote, key, shard_dirs, round_no)
    (rdir / "round.json").write_text(json.dumps(summary, indent=1))
    for name in ("results.jsonl",):
        _download(f"{key}/merged/{name}", rdir / name)
    for slug in local_teams:  # only the local team(s) need their downloads on this machine
        for entry in vol.listdir(f"{key}/merged/downloads/{slug}"):
            _download(entry.path, rdir / "downloads" / slug / entry.path.rsplit("/", 1)[-1])
    summary["remote_downloads"] = f"/vol/{key}/merged/downloads"
    return summary


def _slug(team: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in team).strip("_").lower()  # as tournament.slug


@app.function(image=image, cpu=4.0, memory=16384, timeout=3600, volumes={"/vol": vol}, max_containers=1)
def merge_round_local(field: dict, shard_dirs: list[str], round_no: int, teams: list[str]) -> dict:
    """Merge into the container's disk with only `teams`' downloads; return the summary and those files."""
    vol.reload()
    fpath = Path("/tmp/field.json")
    fpath.write_text(json.dumps(field))
    out = Path("/tmp/merged")
    shutil.rmtree(out, ignore_errors=True)
    subprocess.run([sys.executable, "/emu/tournament.py", "merge", "--field", str(fpath), "--round", str(round_no),
                    "--out", str(out), "--download-teams", ",".join(teams)] + shard_dirs, check=True, capture_output=True)
    files = {"results.jsonl": (out / "results.jsonl").read_bytes()}
    for f in (out / "downloads").rglob("*.gz"):
        files[str(f.relative_to(out))] = f.read_bytes()
    return {"summary": json.loads((out / "round.json").read_text()), "files": files}


def image_has_variant(variant: str) -> Path:
    """The variant module the round image will install (KIT/sdk is copied into it whole);
    raises FileNotFoundError if it isn't there."""
    f = KIT / "sdk/engine/src/poker_engine/variants" / f"{variant}.py"
    if not f.is_file():
        raise FileNotFoundError(f"the round image is built from {KIT / 'sdk'}, which has no {f.name}")
    return f


def open_session() -> None:
    """Start one app for the whole event; rounds then run inside it, overlapping if they must."""
    global _SESSION
    with _LOCK:
        if _SESSION is None:
            ctx = app.run()
            ctx.__enter__()
            _SESSION = ctx


def close_session() -> None:
    global _SESSION
    with _LOCK:
        ctx, _SESSION = _SESSION, None
    if ctx is not None:
        try:
            ctx.__exit__(None, None, None)
        except Exception:  # noqa: BLE001 - the app may already be gone
            pass


@contextmanager
def _running():
    if _SESSION is not None:
        yield
    else:
        with _LOCK, app.run():
            yield


def _download(path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in vol.read_file(path):
            f.write(chunk)


@app.function(image=image, cpu=4.0, memory=16384, timeout=3600, volumes={"/vol": vol}, max_containers=1)
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
