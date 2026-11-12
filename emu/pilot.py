"""Pilot rehearsal: 4 agent-built teams + 16 seats of existing bots, build + 2 rounds, regional variant.

  build (4 teams in parallel, Modal sandboxes) -> upload test -> round 1 -> downloads/results to
  each team -> update (parallel) -> upload test -> round 2 -> summary

Run from the repo root with the prep venv (it has the Modal client); rounds use the kit's Python:
  prep/.venv/bin/python emu/pilot.py --run pilot1
Everything lands in emu/runs/<run>/ (git-ignored). Re-running skips finished steps.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMU = ROOT / "emu"
KITPY = str(ROOT / "starter-kit" / ".venv" / "bin" / "python")
sys.path.insert(0, str(EMU / "teams"))
import run_team  # noqa: E402

OPUS, FABLE = "claude-opus-5-5", "claude-fable-5-2"
HUMAN_MODEL = OPUS  # the simulated competitor at the keyboard
AGENT_TEAMS = [  # (team, persona, coding agent model): the real field ran mostly on frontier models
    ("Ace High", "ace_high", OPUS),
    ("Pressure Point", "pressure_point", FABLE),
    ("Bubble Boys", "bubble_boys", OPUS),
    ("Read The Table", "read_the_table", FABLE),
]
FILL = [  # 16 seats from bots already in the repo (not realistic opponents; the pilot measures the agents)
    ("avalon", "bots/v10"), ("Sim v9s", "bots/v9s"), ("Sim v7", "bots/v7"), ("Sim v6", "bots/v6"),
    ("Sim v5r", "bots/v5r"), ("Sim v3b", "bots/v3b"), ("Sim v3", "bots/v3"), ("Sim v4", "bots/v4"),
    ("Sim m10", "bots/m10"), ("Sim tag", "tests/opponents/tag"),
    ("Sim default b", "prep/lab/field_bots/claude_default_b_r3"),
    ("Sim aggro", "prep/lab/field_bots/claude_aggro_r3"),
    ("Sim icm", "prep/lab/field_bots/claude_icm_r3"),
    ("Sim exploit", "prep/lab/field_bots/claude_exploit_r3"),
    ("Sim gto", "prep/lab/field_bots/claude_gto_r3"),
    ("Sim openai b", "prep/lab/field_bots/openai_b_default_2_r2"),
]
FORFEIT = "starter-kit/examples/check_or_fold"  # placeholder seat for a team with no active bot


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def upload_test(bot: Path) -> dict:
    """The portal's test match: heads-up vs check-or-fold, up to 20 hands, 1 ms, no time bank.
    Rejected if it can't start, crashes, or fails more than 10% of its decisions."""
    if not (bot / "agent.py").is_file():
        return {"ok": False, "reason": "no agent.py at the root of the upload"}
    chk = subprocess.run([str(ROOT / "starter-kit/.venv/bin/poker-agent"), "check", str(bot / "agent.py")],
                         capture_output=True, text=True)
    if chk.returncode:
        return {"ok": False, "reason": "check failed: " + chk.stderr.strip()[-300:]}
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "match.json"
        try:
            out = subprocess.run([KITPY, str(ROOT / "cloud/kit_match.py"), "--tables", "1", "--bank", "0",
                                  "--hand-cap", "20", "--copies", "1", "--out", str(dest), str(bot),
                                  str(ROOT / "starter-kit/examples/check_or_fold")],
                                 capture_output=True, text=True, timeout=600)
            res = json.loads(dest.read_text())
        except (ValueError, OSError, subprocess.TimeoutExpired) as e:
            return {"ok": False, "reason": f"the test match did not finish: {e!r}"}
    t = res["tables"][0]
    label = res["labels"][0]
    fails, decs = t["failures"][label], t["decisions"][label]
    ok = decs > 0 and fails <= 0.10 * decs
    return {"ok": ok, "failed": fails, "decisions": decs,
            "reason": "" if ok else f"failed {fails} of {decs} decisions (limit 10%)"}


def agent_phase(run: str, phase: str, rnd: int, minutes: float, prev: dict) -> dict:
    """Run every agent team's phase in parallel; returns {team: submission dir or None}."""
    def one(spec):
        team, persona, model = spec
        slug = run_team.team_slug(team)
        pdir = "build" if phase == "build" else f"update{rnd}"
        out = EMU / "runs" / run / slug / pdir
        if (out / "result.json").is_file():
            log(f"{team}: {pdir} already done")
        else:
            args = argparse.Namespace(run=run, team=team, persona=persona, model=model,
                                      human_model=HUMAN_MODEL, phase=phase,
                                      round=rnd, minutes=minutes, variant_rules=None,
                                      previous=prev.get(team), downloads=None, results=None)
            if phase == "update":
                args.downloads = str(EMU / "runs" / run / f"round{rnd}" / "downloads" / slug)
                args.results = str(EMU / "runs" / run / f"round{rnd}" / "results")
            log(f"{team}: {pdir} starting ({model}, persona {persona}, {minutes} min)")
            try:
                r = run_team.run(args)
                log(f"{team}: {pdir} done, ${r['cost_usd']}, {r['calls']} calls, agent.py={r['has_agent_py']}")
            except Exception as e:  # noqa: BLE001 - one team's failure must not stop the rehearsal
                log(f"{team}: {pdir} FAILED: {e!r}")
                (out / "result.json").parent.mkdir(parents=True, exist_ok=True)
                (out / "result.json").write_text(json.dumps({"error": repr(e)}))
        test = upload_test(out / "submission")
        (out / "upload_test.json").write_text(json.dumps(test))
        log(f"{team}: upload test {'PASSED' if test['ok'] else 'REJECTED: ' + test['reason']}")
        # A rejected upload leaves the previous active bot in place, as on the portal.
        return team, (str(out / "submission") if test["ok"] else prev.get(team))

    with ThreadPoolExecutor(len(AGENT_TEAMS)) as pool:
        return dict(pool.map(one, AGENT_TEAMS))


def play_round(run: str, rnd: int, active: dict, iterations: int, shards: int) -> dict:
    rdir = EMU / "runs" / run / f"round{rnd}"
    if (rdir / "round.json").is_file():
        log(f"round {rnd} already played")
        return json.loads((rdir / "round.json").read_text())
    entries = [{"team": t, "bot": str(Path(b).resolve().relative_to(ROOT)) if b else FORFEIT}
               for t, b in active.items()] + [{"team": t, "bot": b} for t, b in FILL]
    field = {"name": f"{run} round {rnd}", "rules": {"variant": "flop_discard_reveal", "players": 8},
             "entries": entries, "forfeit": [t for t, b in active.items() if not b]}
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "field.json").write_text(json.dumps(field, indent=1))
    seed = f"{run}-round{rnd}"
    per = iterations // shards
    log(f"round {rnd}: {iterations} iterations in {shards} local shards")
    procs = [subprocess.Popen([KITPY, str(EMU / "tournament.py"), "play", "--field", str(rdir / "field.json"),
                               "--seed", seed, "--first-iteration", str(k * per), "--iterations", str(per),
                               "--out", str(rdir / f"shard{k}"), "--concurrency", "4"],
                              stdout=subprocess.DEVNULL, stderr=open(rdir / f"shard{k}.err", "w"))
             for k in range(shards)]
    for p in procs:
        p.wait()
    subprocess.run([KITPY, str(EMU / "tournament.py"), "merge", "--field", str(rdir / "field.json"),
                    "--round", str(rnd), "--out", str(rdir)] + [str(rdir / f"shard{k}") for k in range(shards)],
                   check=True, stdout=subprocess.DEVNULL)
    summary = json.loads((rdir / "round.json").read_text())
    for t in field["forfeit"]:  # no active bot: the team forfeits the round
        summary["scores"][t]["points"] = 0.0
    (rdir / "round.json").write_text(json.dumps(summary, indent=1))
    write_results(run, rnd)
    for k in range(shards):
        shutil.rmtree(rdir / f"shard{k}", ignore_errors=True)
    return summary


def write_results(run: str, upto: int) -> None:
    """The results page as teams see it: every round's leaderboard so far, and the weighted total."""
    rounds = []
    for r in range(1, upto + 1):
        rounds.append(json.loads((EMU / "runs" / run / f"round{r}" / "round.json").read_text()))
    teams = list(rounds[-1]["scores"])
    total = {t: sum(r["round"] * r["scores"][t]["points"] for r in rounds) for t in teams}
    lines = ["# Results", "", f"After round {upto}. Final score = sum of round score x weight (round k has weight k).", "",
             "| Rank | Team | " + " | ".join(f"Round {r['round']} (x{r['round']})" for r in rounds) + " | Weighted total |",
             "|---|---|" + "---|" * len(rounds) + "---|"]
    for i, t in enumerate(sorted(teams, key=lambda t: -total[t]), 1):
        lines.append(f"| {i} | {t} | " + " | ".join(f"{r['scores'][t]['points']:.2f}" for r in rounds)
                     + f" | {total[t]:.2f} |")
    last = rounds[-1]
    lines += ["", f"## Round {last['round']}: finishes by team", "",
              "| Team | Points/table | Tables | 1st | 2nd | 3rd | Failed decisions |", "|---|---|---|---|---|---|---|"]
    for t in sorted(teams, key=lambda t: -last["scores"][t]["points"]):
        s = last["scores"][t]
        p = s["places"]
        lines.append(f"| {t} | {s['points']:.2f} | {s['tables']} | {p.get('1', p.get(1, 0)):.1%} | "
                     f"{p.get('2', p.get(2, 0)):.1%} | {p.get('3', p.get(3, 0)):.1%} | {s['failed_decisions']} |")
    res = EMU / "runs" / run / f"round{upto}" / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "results.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", default="pilot1")
    p.add_argument("--build-minutes", type=float, default=60)
    p.add_argument("--update-minutes", type=float, default=15)
    p.add_argument("--iterations", type=int, default=1000)
    p.add_argument("--shards", type=int, default=4)
    p.add_argument("--rounds", type=int, default=2)
    a = p.parse_args()
    log(f"pilot {a.run}: {len(AGENT_TEAMS)} agent teams + {len(FILL)} filled seats")
    active = agent_phase(a.run, "build", 0, a.build_minutes, {})
    for rnd in range(1, a.rounds + 1):
        summary = play_round(a.run, rnd, active, a.iterations, a.shards)
        top = sorted(summary["scores"].items(), key=lambda kv: -kv[1]["points"])
        log(f"round {rnd}: " + ", ".join(f"{t} {v['points']:.2f}" for t, v in top[:8]))
        if rnd < a.rounds:
            active = agent_phase(a.run, "update", rnd, a.update_minutes, active)
    cost = 0.0
    for f in (EMU / "runs" / a.run).glob("*/*/result.json"):
        cost += json.loads(f.read_text()).get("cost_usd") or 0
    log(f"pilot done. agent cost ${cost:.2f}. results: emu/runs/{a.run}/round{a.rounds}/results/results.md")


if __name__ == "__main__":
    main()
