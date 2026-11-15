"""Run one synthetic team's coding agent (Claude Code, headless) in a Modal sandbox.

A synthetic team works the way a real one does: a lightly steered AI assistant on a build box
with the starter kit, the portal pages, and (between rounds) its own hand-history downloads
and the results page. Nothing from this repo is visible to it.

  phases:  build   the 60-minute build after the variant announcement
           update  between rounds: read the downloads/results, improve the bot (default 15 min)

Each run uploads the team's workspace to the Modal volume `emu-teams`, runs `claude -p` in a
sandbox shaped like the team build box (2 vCPU, Python 3.12 + the kit's exact libraries + the kit
SDK), and downloads the result to emu/runs/<run>/<team>/<phase>/:
  submission/       the bot the team "uploaded" (agent.py at its root), if any
  transcript.jsonl  the agent's full stream-json transcript (tool calls, messages)
  result.json       duration, cost and token usage reported by Claude Code, exit status

Needs the Modal secret `emu-anthropic` holding ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN.

  prep/.venv/bin/python emu/teams/run_team.py --run pilot1 --team "Ace Agents" \
      --persona ace_high --model claude-opus-5-5 --phase build --minutes 60
"""

import argparse
import io
import json
import os
import shutil
import tarfile
import time
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent.parent
KIT = ROOT / "starter-kit"
EMU = ROOT / "emu"
BRIEFS = EMU / "teams" / "briefs"
PERSONAS = EMU / "teams" / "personas"
APP = "nolimit-emu-teams"
VOLUME = "emu-teams"
SECRET = "emu-anthropic"

KIT_SKIP = {".venv", "__pycache__", ".DS_Store"}

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("build-essential", "git", "curl", "ca-certificates", "nodejs", "npm", "procps")
    .pip_install_from_requirements(str(KIT / "requirements.txt"))
    .add_local_dir(str(KIT / "sdk"), "/opt/kit/sdk", copy=True,
                   ignore=["**/__pycache__/**", "**/*.egg-info/**"])
    .run_commands(
        "pip install -e /opt/kit/sdk/agent-protocol -e /opt/kit/sdk/engine -e /opt/kit/sdk/agent-sdk",
        "npm install -g @anthropic-ai/claude-code",
        "useradd -m -s /bin/bash team",
    )
)


def team_slug(team: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in team).strip("_").lower()


def kit_files(dest: Path, variant_rules: Path | None, source: Path = KIT) -> None:
    """The starter kit exactly as a team downloads it (no venv, no local histories). `source` is
    starter-kit/ or, for a mock variant, the mock kit emu/variants/make_kit.py built for the run
    (its engine holds the variant's module)."""
    def ignore(d, names):
        skip = {n for n in names if n in KIT_SKIP}
        if Path(d).name == "hand-history":
            skip |= {n for n in names if n.endswith(".gz") and not n.startswith("sample")}
            skip |= {n for n in names if n.startswith("local-")}
        return skip
    shutil.copytree(source, dest, ignore=ignore)
    if variant_rules:
        shutil.copy(variant_rules, dest / "RULES.md")


def schedule_table(weights=(1, 2, 3, 4, 5, 6)) -> str:
    rows = ["| Round | After build | Weight |", "|---|---|---|"]
    for k, w in enumerate(weights, 1):
        rows.append(f"| {k} | {'Build ends' if k == 1 else f'+{20 * (k - 1)} min'} | {w}x |")
    return "\n".join(rows)


def portal_files(dest: Path, variant_title: str, variant_rules: str, weights=(1, 2, 3, 4, 5, 6),
                 cooldown: int = 30, table: str = "regional") -> None:
    """The Getting started and Format pages; `table` (emu/tables.py) fills the table rows and the player count."""
    import sys
    sys.path.insert(0, str(EMU))
    import tables
    players = tables.TABLES[table]["players"]
    dest.mkdir(parents=True, exist_ok=True)
    for page in ("getting-started.md", "format.md"):
        text = (EMU / "portal" / "pages" / page).read_text()
        text = text.replace("{{TABLE_ROWS}}", tables.format_rows(table)).replace("{{PLAYERS_WORD}}", tables.WORDS[players])
        text = text.replace("{{PLAYERS}}", str(players))
        text = text.replace("{{VARIANT_TITLE}}", variant_title).replace("{{VARIANT_RULES}}", variant_rules)
        text = text.replace("{{SCHEDULE_TABLE}}", schedule_table(weights)).replace("{{COOLDOWN}}", str(cooldown))
        (dest / page).write_text(text)


SETUP = """Your assistant (Claude Code) is open in your team's working folder on the team build box (2 vCPUs, set up like the tournament machines; the kit's SDK is installed and `poker-agent` is on the PATH). In that folder: kit/ is the starter kit you downloaded (README.md, RULES.md, AGENTS.md, sdk, examples, hand-history sample), portal/ has the website pages, and submission/ is what you'll upload: whatever is in submission/ (agent.py at its root) when time runs out is what gets uploaded. Your assistant hasn't been told anything yet in this session."""


def situation_for(a, ws: Path) -> str:
    """What the simulated competitor knows when the phase starts (they've read the website)."""
    fmt = (ws / "portal" / "format.md").read_text()
    if a.phase == "build":
        return (f"The variant has just been announced and the {a.minutes:.0f}-minute build has started. "
                f"Practice rounds will run during the build; the scored rounds start when it ends.\n\n"
                f"{SETUP}\n\nThe tournament's Format page, which you've read:\n\n{fmt}")
    results = ""
    if a.results and (Path(a.results) / "results.md").is_file():
        results = (Path(a.results) / "results.md").read_text()
    return (f"Round {a.round} has just finished and the results are up. The next round starts in about "
            f"{a.minutes:.0f} minutes and plays whatever bot is uploaded by then.\n\n{SETUP} Since the "
            f"last session, your bot from before is in submission/, the published results are in results/, "
            f"and downloads/ has your team's hand history from round {a.round} as the portal offers it "
            f"(the full file and a smaller -first-1000 subset). This is a new session of your assistant: it "
            f"doesn't remember the earlier one, but its notes in submission/ may help.\n\n"
            f"The results page you're looking at:\n\n{results}")


def make_workspace(a) -> Path:
    """Build the team's workspace locally, under emu/runs/<run>/<team>/<phase>/workspace."""
    out = EMU / "runs" / a.run / team_slug(a.team) / a.phase_dir
    ws = out / "workspace"
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    rules = Path(a.variant_rules) if a.variant_rules else None
    kit_files(ws / "kit", rules)
    rules_text = (rules or KIT / "RULES.md").read_text()
    title = rules_text.splitlines()[0].lstrip("# ").strip()
    portal_files(ws / "portal", title, "\n".join(rules_text.splitlines()[1:]).strip())
    sub = ws / "submission"
    if a.previous:
        shutil.copytree(a.previous, sub)
    else:
        sub.mkdir()
    for src, name in ((a.downloads, "downloads"), (a.results, "results")):
        if src:
            shutil.copytree(src, ws / name)
    return out


def tar_dir(path: Path) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(path, arcname=".")
    return buf.getvalue()


def run(a) -> dict:
    a.phase_dir = a.phase if a.phase == "build" else f"update{a.round}"
    out = make_workspace(a)
    persona = (PERSONAS / f"{a.persona}.md").read_text()
    situation = situation_for(a, out / "workspace")
    (out / "situation.md").write_text(situation)
    key = f"{a.run}/{team_slug(a.team)}/{a.phase_dir}"
    vol = modal.Volume.from_name(VOLUME, create_if_missing=True)
    with vol.batch_upload(force=True) as up:
        up.put_file(io.BytesIO(tar_dir(out / "workspace")), f"/{key}/workspace.tgz")
        up.put_file(io.BytesIO(persona.encode()), f"/{key}/persona.md")
        up.put_file(io.BytesIO(situation.encode()), f"/{key}/situation.md")
        up.put_file(str(EMU / "teams" / "steer.py"), f"/{key}/steer.py")
    app = modal.App.lookup(APP, create_if_missing=True)
    limit = int(a.minutes * 60)
    sb = modal.Sandbox.create(
        app=app, image=image, cpu=2.0, memory=8192, timeout=limit + 900,
        secrets=[modal.Secret.from_name(SECRET)], volumes={"/vol": vol}, workdir="/home/team",
        name=f"emu-{team_slug(a.team)}-{a.phase_dir}-{int(time.time())}"[:60],
    )
    try:
        sh = lambda cmd, t=600: sb.exec("bash", "-lc", cmd, timeout=t)  # noqa: E731
        p = sh(f"mkdir -p /home/team/work /opt/steer && tar xzf /vol/{key}/workspace.tgz -C /home/team/work "
               f"&& cp /vol/{key}/steer.py /vol/{key}/persona.md /vol/{key}/situation.md /opt/steer/ "
               f"&& mkdir -p /tmp/out && chown -R team:team /home/team /tmp/out")
        p.wait()
        # Only the auth variable that is set is passed (an empty one would confuse the CLI).
        cmd = (f"cd /home/team/work && AUTH=$( [ -n \"$CLAUDE_CODE_OAUTH_TOKEN\" ] && "
               f"echo CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN || echo ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY ) "
               f"&& runuser -u team -- env HOME=/home/team DISABLE_AUTOUPDATER=1 \"$AUTH\" "
               f"python3 /opt/steer/steer.py /opt/steer {limit} {a.model} {a.human_model} /tmp/out "
               f"2> /tmp/out/claude.err; echo $? > /tmp/out/exit")
        t0 = time.time()
        p = sh(cmd, limit + 600)
        p.wait()
        elapsed = time.time() - t0
        p = sh(f"cd /home/team/work && find submission -name __pycache__ -prune -exec rm -rf {{}} + ; "
               f"tar czf /vol/{key}/out.tgz submission && "
               f"cp /tmp/out/transcript.jsonl /tmp/out/human.jsonl /tmp/out/claude.err /tmp/out/exit "
               f"/tmp/out/steer.json /vol/{key}/ ; "
               f"sync /vol")
        p.wait()
    finally:
        sb.terminate()
    return fetch(a, out, key, elapsed)


def read_volume(vol, path: str, wait_s: float = 120) -> bytes:
    """A sandbox's volume writes can take a moment to become visible outside it: retry."""
    deadline = time.time() + wait_s
    while True:
        try:
            return b"".join(vol.read_file(path))
        except FileNotFoundError:
            if time.time() > deadline:
                raise
            time.sleep(3)


def fetch(a, out: Path, key: str, elapsed: float) -> dict:
    """Download a finished phase's submission, transcript and steering record from the volume."""
    vol = modal.Volume.from_name(VOLUME)
    data = read_volume(vol, f"{key}/out.tgz")
    sub = out / "submission"
    if sub.exists():
        shutil.rmtree(sub)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tar.extractall(out, filter="data")
    transcript = read_volume(vol, f"{key}/transcript.jsonl")
    (out / "transcript.jsonl").write_bytes(transcript)
    err = read_volume(vol, f"{key}/claude.err").decode(errors="replace")
    exit_code = read_volume(vol, f"{key}/exit").decode().strip()
    steer = json.loads(read_volume(vol, f"{key}/steer.json") or b"{}")
    (out / "steer.json").write_text(json.dumps(steer, indent=1))
    try:
        (out / "human.jsonl").write_bytes(read_volume(vol, f"{key}/human.jsonl", wait_s=10))
    except FileNotFoundError:
        pass
    result = {
        "team": a.team, "persona": a.persona, "model": a.model, "human_model": a.human_model,
        "phase": a.phase_dir, "minutes_allowed": a.minutes, "elapsed_s": round(elapsed, 1),
        "exit": exit_code, "has_agent_py": (sub / "agent.py").is_file(),
        "cost_usd": steer.get("cost_usd"), "agent_cost_usd": steer.get("agent_cost_usd"),
        "human_cost_usd": steer.get("human_cost_usd"), "turns": steer.get("turns"),
        "calls": len(steer.get("calls", [])), "stderr_tail": err[-2000:],
    }
    (out / "result.json").write_text(json.dumps(result, indent=1))
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", required=True, help="rehearsal name, e.g. pilot1")
    p.add_argument("--team", required=True)
    p.add_argument("--persona", required=True, help=f"one of {sorted(x.stem for x in PERSONAS.glob('*.md'))}")
    p.add_argument("--model", default="claude-opus-5-5", help="the coding agent's model (Claude Code --model)")
    p.add_argument("--human-model", default="claude-opus-5-5", help="the simulated competitor's model")
    p.add_argument("--phase", choices=["build", "update"], default="build")
    p.add_argument("--round", type=int, default=0, help="the round that just finished (update)")
    p.add_argument("--minutes", type=float, default=60)
    p.add_argument("--previous", help="the team's current submission folder (update)")
    p.add_argument("--downloads", help="folder with the team's hand-history downloads (update)")
    p.add_argument("--results", help="folder with the published results (update)")
    p.add_argument("--variant-rules", help="RULES.md of a mock variant (default: the kit's)")
    a = p.parse_args()
    print(json.dumps(run(a), indent=1))


if __name__ == "__main__":
    main()
