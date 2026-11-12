"""A full tournament rehearsal on the real clock: 19 simulated teams + avalon.

Each synthetic team is one Modal sandbox for the whole event, running emu/teams/steer.py in event
mode: a simulated competitor (persona) steering a coding agent from the variant announcement to
the last round. avalon is a local folder you (or your own agent) work in, exactly like a team:
  emu/runs/<run>/avalon/  kit/ portal/ submission/ results/ downloads/ inbox/

Timeline (minutes from the start; --scale shrinks it for tests):
  0 build starts | 20,30,40,50 practice rounds (as at the Bay Area regional) | 60,80,...,160 scored rounds 1-6 (weights 1-6)
At every round start, each team's submission/ is snapshotted ("uploaded"), put through the
portal's upload test (a rejected upload leaves the previous bot active; no bot = forfeit), and the
round plays in the background on the kit engine. When it finishes, every team gets the results
page, its downloads (full + first-1000) and a portal notice.

  prep/.venv/bin/python emu/rehearsal.py --run full1
"""

import argparse
import base64
import io
import json
import shutil
import subprocess
import sys
import tarfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMU = ROOT / "emu"
KITPY = str(ROOT / "starter-kit" / ".venv" / "bin" / "python")
sys.path.insert(0, str(EMU / "teams"))
sys.path.insert(0, str(EMU))
import modal  # noqa: E402
import run_team  # noqa: E402
from pilot import upload_test  # noqa: E402

OPUS, FABLE = "claude-opus-5-5", "claude-fable-5-2"
HUMAN_MODEL = OPUS
# (persona file, coding agent model, pre-event research minutes, CPUs). Mostly frontier models, as in
# the real field. Research and big machines follow the Boston account: the winner had Fable researching
# for ~1.5 h before the start, and some teams rented cloud compute.
TEAMS = [
    ("ace_high", OPUS, 0, 2), ("pressure_point", FABLE, 0, 2), ("bubble_boys", OPUS, 0, 2),
    ("read_the_table", FABLE, 0, 2), ("nit_picks", FABLE, 0, 2), ("river_rats", OPUS, 0, 2),
    ("monte_carlo_kids", FABLE, 60, 16), ("small_blind_energy", OPUS, 0, 2), ("fold_equity", FABLE, 30, 2),
    ("shove_bros", OPUS, 0, 2), ("tiltproof", OPUS, 0, 2), ("the_solvers", FABLE, 45, 2),
    ("variance_hunters", OPUS, 0, 2), ("deep_stack", FABLE, 60, 16), ("showdown_value", OPUS, 0, 2),
    ("button_mashers", OPUS, 0, 2), ("kicker_problems", OPUS, 0, 2), ("blind_ambition", FABLE, 0, 2),
    ("pocket_rockets", FABLE, 90, 2),
]
PREP_SITUATION = """The Finals start in about {minutes} minutes. The variant will only be announced at the start, together with the starter kit, so you can't build the bot yet. Your assistant (Claude Code) is open in your team's working folder on the team build box; portal/ has the website pages you can already read (Getting started, and the Format page without the variant). Use the time the way you planned: research and prepare, and keep notes in the folder so you can use them when the build starts."""
# The Finals field: 7 simulated finalists + avalon = one 8-seat table. Each has regional notes
# (emu/teams/finalists/) drawn from the 2026-11-12 strategy studies: per-seat learning, recognition by
# bet sizes, the field's defence to wide re-raises, simulation, copying the leaders.
FINALS7 = [
    ("pocket_rockets", FABLE, 0, 2), ("pressure_point", OPUS, 0, 2), ("read_the_table", FABLE, 0, 2),
    ("deep_stack", FABLE, 0, 16), ("shove_bros", OPUS, 0, 2), ("nit_picks", OPUS, 0, 2),
    ("showdown_value", OPUS, 0, 2),
]
FINALISTS = EMU / "teams" / "finalists"
AVALON = "avalon"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def team_name(persona: str) -> str:
    return (run_team.PERSONAS / f"{persona}.md").read_text().splitlines()[0].split(":", 1)[1].split("(")[0].strip()


def timeline(scale: float, weights: list[int]) -> list[dict]:
    ev = [{"t": m * 60 * scale, "kind": "practice", "n": i, "label": f"Practice round {i}"}
          for i, m in enumerate((20, 30, 40, 50), 1)]
    ev += [{"t": (60 + 20 * (k - 1)) * 60 * scale, "kind": "scored", "n": k, "label": f"Scored round {k} (x{w})"}
           for k, w in enumerate(weights, 1)]
    # As on the real portal, a practice round runs between scored rounds (10 minutes after each one).
    ev += [{"t": (70 + 20 * (k - 1)) * 60 * scale, "kind": "practice", "n": 4 + k, "label": f"Practice round {4 + k}"}
           for k in range(1, len(weights))]
    ev.sort(key=lambda e: e["t"])
    return ev


class Event:
    def __init__(self, a):
        self.a = a
        self.dir = EMU / "runs" / a.run
        self.dir.mkdir(parents=True, exist_ok=True)
        if a.field == "finals":
            chosen = FINALS7
        else:
            chosen = [t for t in TEAMS if t[0] in a.personas.split(",")] if a.personas else TEAMS[: a.teams]
        self.teams = {team_name(p): (p, m, prep, cpu) for p, m, prep, cpu in chosen}
        self.weights = [int(w) for w in a.weights.split(",")]
        self.slug = {t: run_team.team_slug(t) for t in [*self.teams, AVALON]}
        self.active: dict[str, str | None] = {t: None for t in [*self.teams, AVALON]}
        self.sandboxes: dict[str, modal.Sandbox] = {}
        self.procs = {}
        self.vol = modal.Volume.from_name(run_team.VOLUME, create_if_missing=True)
        self.scored: list[dict] = []
        self.lock = threading.Lock()
        self.events = timeline(a.scale, self.weights)
        self.remote: dict[str, str] = {}  # round name -> volume folder with every team's downloads

    # ---------------------------------------------------------------- setup
    def workspace(self, team: str) -> Path:
        ws = self.dir / self.slug[team] / "workspace" if team != AVALON else self.dir / AVALON
        if ws.exists():
            shutil.rmtree(ws)
        ws.mkdir(parents=True)
        run_team.kit_files(ws / "kit", Path(self.a.variant_rules) if self.a.variant_rules else None)
        rules = (Path(self.a.variant_rules) if self.a.variant_rules else ROOT / "starter-kit" / "RULES.md").read_text()
        run_team.portal_files(ws / "portal", rules.splitlines()[0].lstrip("# ").strip(),
                              "\n".join(rules.splitlines()[1:]).strip(), self.weights)
        for d in ("submission", "results", "downloads", "inbox"):
            (ws / d).mkdir()
        if team == AVALON:
            if self.a.avalon_start != "empty":
                shutil.copytree(ROOT / "bots" / self.a.avalon_start, ws / "submission", dirs_exist_ok=True)
        elif self.a.field == "finals":
            (ws / "notes").mkdir()
            shutil.copy(FINALISTS / f"{self.teams[team][0]}.md", ws / "notes" / "regional_notes.md")
        return ws

    def situation(self, ws: Path) -> str:
        fmt = (ws / "portal" / "format.md").read_text()
        sched = "\n".join(f"- minute {e['t'] / 60 / self.a.scale:.0f}: {e['label']}" for e in self.events)
        return (f"The variant has just been announced and the build has started. Practice rounds (about "
                f"{self.a.practice_iterations} iterations, never scored) run at minutes 20, 30, 40 and 50 of the build, "
                f"then six scored rounds start 20 minutes apart, with a practice round 10 minutes before each. At the start of every round the portal plays "
                f"whatever is in your submission/ folder at that moment (your team uploads it automatically), "
                f"after the upload test. Results and your hand-history downloads appear in results/ and "
                f"downloads/ when each round finishes, and you'll see a notice. Today's schedule:\n{sched}\n\n"
                f"{run_team.SETUP}\n\nThe tournament's Format page, which you've read:\n\n{fmt}")

    def start_team(self, team: str, start: float, prep: int | None = None) -> None:
        persona, model, planned, cpu = self.teams[team]
        prep = int(planned * self.a.prep_scale) if prep is None else prep
        ws = self.workspace(team)
        situation = self.situation(ws)
        key = f"{self.a.run}/{self.slug[team]}/event"
        schedule = {"start": start, "events": [{"t": e["t"], "label": e["label"]} for e in self.events]}
        # The announcement: kit/ and the full portal (with the variant) appear only at the start.
        ann = ws.parent / "announce"
        if ann.exists():
            shutil.rmtree(ann)
        ann.mkdir()
        shutil.move(str(ws / "kit"), ann / "kit")
        shutil.move(str(ws / "portal"), ann / "portal")
        run_team.portal_files(ws / "portal", "To be announced",
                              "The variant is announced at the start of the event, together with the starter kit.",
                              self.weights)
        kit = ws.parent / "announce.tgz"
        kit.write_bytes(run_team.tar_dir(ann))
        with self.vol.batch_upload(force=True) as up:
            up.put_file(io.BytesIO(run_team.tar_dir(ws)), f"/{key}/workspace.tgz")
            up.put_file(str(kit), f"/{key}/announce.tgz")
            up.put_file(io.BytesIO(PREP_SITUATION.format(minutes=prep).encode()), f"/{key}/prep_situation.md")
            ptext = (run_team.PERSONAS / f"{persona}.md").read_text()
            if self.a.field == "finals":
                ptext += "\n" + (FINALISTS / "_common.md").read_text()
            up.put_file(io.BytesIO(ptext.encode()), f"/{key}/persona.md")
            up.put_file(io.BytesIO(situation.encode()), f"/{key}/situation.txt")
            up.put_file(io.BytesIO(json.dumps(schedule).encode()), f"/{key}/schedule.json")
            up.put_file(str(EMU / "teams" / "steer.py"), f"/{key}/steer.py")
        app = modal.App.lookup(run_team.APP, create_if_missing=True)
        total = int(self.events[-1]["t"] + 3600)
        sb = modal.Sandbox.create(
            app=app, image=run_team.image, cpu=float(cpu), memory=4096 * max(2, cpu // 2), timeout=total + 1800 + prep * 60,
            secrets=[modal.Secret.from_name(run_team.SECRET)], volumes={"/vol": self.vol},
            workdir="/home/team", name=f"emu-{self.a.run}-{self.slug[team]}"[:60])
        sb.exec("bash", "-lc",
                f"chmod 700 /vol && mkdir -p /home/team/work /opt/steer /tmp/out && "
                f"tar xzf /vol/{key}/workspace.tgz -C /home/team/work "
                f"&& mv /home/team/work/inbox /home/team/inbox && cp /vol/{key}/steer.py /vol/{key}/persona.md "
                f"/vol/{key}/schedule.json /opt/steer/ "
                f"&& chown -R team:team /home/team /tmp/out", timeout=600).wait()
        sb.set_tags({"run": self.a.run, "team": self.slug[team]})
        self.sandboxes[team] = sb
        seconds = int(self.events[-1]["t"])  # the session runs until the last round starts
        auth = ("AUTH=$( [ -n \"$CLAUDE_CODE_OAUTH_TOKEN\" ] && echo CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN "
                "|| echo ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY )")
        as_team = "runuser -u team -- env HOME=/home/team DISABLE_AUTOUPDATER=1 \"$AUTH\""
        prep_cmd = ""
        if prep:  # research before the announcement: its own session (notes stay in the folder)
            prep_cmd = (f"mkdir -p /opt/prep /tmp/prep && cp /opt/steer/persona.md /opt/prep/ && "
                        f"cp /vol/{key}/prep_situation.md /opt/prep/situation.md && chown -R team /tmp/prep && "
                        f"{as_team} python3 /opt/steer/steer.py /opt/prep {prep * 60} {model} {HUMAN_MODEL} /tmp/prep "
                        f"2> /tmp/prep/claude.err; ")
        cmd = (f"cd /home/team/work && {auth} && {prep_cmd}"
               f"python3 -c 'import time; time.sleep(max(0, {start} - time.time()))' && "
               f"rm -rf /home/team/work/portal && tar xzf /vol/{key}/announce.tgz -C /home/team/work && "
               f"cp /vol/{key}/situation.txt /opt/steer/situation.md && "
               f"chown -R team:team /home/team/work && {as_team} "
               f"python3 /opt/steer/steer.py /opt/steer {seconds} {model} {HUMAN_MODEL} /tmp/out "
               f"2> /tmp/out/claude.err; echo $? > /tmp/out/exit")
        self.procs[team] = sb.exec("bash", "-lc", cmd, timeout=total + 1200)
        log(f"{team}: started ({model}, persona {persona}, {cpu} CPUs, {prep} min pre-event research)")

    # ---------------------------------------------------------------- rounds
    def snapshot(self, team: str, label: str) -> Path:
        dest = self.dir / self.slug[team] / "uploads" / label.split(" (")[0].replace(" ", "_").lower()
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        if team == AVALON:
            src = self.dir / AVALON / "submission"
            if self.a.avalon_replay:  # validation: avalon plays what we actually ran that round
                plan = self.a.avalon_replay.split(",")
                n = int(label.split()[2]) if label.startswith("Scored") else 0
                src = ROOT / "bots" / (plan[n - 1] if n else self.a.avalon_practice)
            shutil.copytree(src, dest / "submission", ignore=shutil.ignore_patterns("__pycache__", ".*"))
            return dest / "submission"
        p = self.sandboxes[team].exec("bash", "-lc", "cd /home/team/work && tar czf - --exclude=__pycache__ "
                                      "--exclude='.*' submission | base64 -w0", timeout=300)
        data = p.stdout.read()
        p.wait()
        with tarfile.open(fileobj=io.BytesIO(base64.b64decode(data)), mode="r:gz") as tar:
            tar.extractall(dest, filter="data")
        return dest / "submission"

    def upload(self, team: str, label: str) -> dict:
        try:
            sub = self.snapshot(team, label)
            test = upload_test(sub)
        except Exception as e:  # noqa: BLE001
            sub, test = None, {"ok": False, "reason": f"upload failed: {e!r}"}
        if test["ok"]:
            self.active[team] = str(sub)
        test["active"] = self.active[team]
        return test

    def play(self, ev: dict) -> None:
        label = ev["label"]
        name = f"{ev['kind']}{ev['n']}"
        rdir = self.dir / "rounds" / name
        rdir.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(8) as pool:
            tests = dict(zip(self.active, pool.map(lambda t: self.upload(t, label), list(self.active))))
        (rdir / "uploads.json").write_text(json.dumps(tests, indent=1))
        for t, r in tests.items():
            if not r["ok"]:
                log(f"{label}: {t} upload REJECTED ({r['reason']}); active stays {r['active']}")
        forfeit = [t for t, b in self.active.items() if not b]
        entries = [{"team": t, "bot": str(Path(b).relative_to(ROOT)) if b else "starter-kit/examples/check_or_fold"}
                   for t, b in self.active.items()]
        field = {"name": f"{self.a.run} {label}", "rules": {"variant": self.a.variant, "players": 8},
                 "entries": entries, "forfeit": forfeit}
        (rdir / "field.json").write_text(json.dumps(field, indent=1))
        iters = self.a.practice_iterations if ev["kind"] == "practice" else self.a.round_iterations
        log(f"{label}: playing {iters} iterations ({len(forfeit)} forfeits)")
        t0 = time.time()
        if self.a.local_rounds:
            self.play_local(rdir, name, iters, ev["n"])
        else:  # Modal: shards in the cloud, merged there; synthetic teams' downloads stay on the volume
            import modal_rounds
            remote = modal_rounds.play_round_on_modal(field, f"{self.a.run}-{name}", iters, rdir, ev["n"],
                                                      shards=self.a.shards, local_teams=(self.slug[AVALON],))
            self.remote[name] = remote["remote_downloads"]
        summary = json.loads((rdir / "round.json").read_text())
        for t in forfeit:
            summary["scores"][t]["points"] = 0.0
        summary.update(kind=ev["kind"], label=label, uploads=tests, play_s=round(time.time() - t0, 1))
        (rdir / "round.json").write_text(json.dumps(summary, indent=1))
        if ev["kind"] == "scored":
            with self.lock:
                self.scored.append(summary)
        log(f"{label}: done in {summary['play_s']}s; " + ", ".join(
            f"{t} {v['points']:.1f}" for t, v in sorted(summary["scores"].items(), key=lambda kv: -kv[1]["points"])[:5]))
        self.deliver(ev, rdir, summary)

    def play_local(self, rdir: Path, name: str, iters: int, round_no: int) -> None:
        shards = min(self.a.shards, 4)  # each local shard runs two processes per team
        per = -(-iters // shards)
        procs = [subprocess.Popen([KITPY, str(EMU / "tournament.py"), "play", "--field", str(rdir / "field.json"),
                                   "--seed", f"{self.a.run}-{name}", "--first-iteration", str(k * per),
                                   "--iterations", str(min(per, iters - k * per)), "--out", str(rdir / f"shard{k}"),
                                   "--concurrency", "4"],
                                  stdout=subprocess.DEVNULL, stderr=open(rdir / f"shard{k}.err", "w"))
                 for k in range(shards) if k * per < iters]
        for p in procs:
            p.wait()
        subprocess.run([KITPY, str(EMU / "tournament.py"), "merge", "--field", str(rdir / "field.json"),
                        "--round", str(round_no), "--out", str(rdir)] + [str(rdir / f"shard{k}") for k in range(len(procs))],
                       check=True, stdout=subprocess.DEVNULL)
        for k in range(len(procs)):
            shutil.rmtree(rdir / f"shard{k}", ignore_errors=True)

    def results_page(self, summary: dict) -> str:
        label = summary["label"]
        lines = [f"# Results: {label}", ""]
        if summary["kind"] == "practice":
            lines += ["Practice round (never scored).", ""]
        lines += ["| Rank | Team | Points/table | 1st | 2nd | 3rd | Failed decisions |", "|---|---|---|---|---|---|---|"]
        rank = sorted(summary["scores"].items(), key=lambda kv: -kv[1]["points"])
        for i, (t, s) in enumerate(rank, 1):
            p = s["places"]
            lines.append(f"| {i} | {t} | {s['points']:.2f} | {p.get('1', 0):.1%} | {p.get('2', 0):.1%} | "
                         f"{p.get('3', 0):.1%} | {s['failed_decisions']} |")
        with self.lock:
            scored = sorted(self.scored, key=lambda s: s["round"])
        if scored:
            teams = list(scored[-1]["scores"])
            w = lambda k: self.weights[k - 1]  # noqa: E731
            total = {t: sum(w(s["round"]) * s["scores"][t]["points"] for s in scored) for t in teams}
            lines += ["", f"## Leaderboard (scored rounds; weights {', '.join(f'R{k} x{x}' for k, x in enumerate(self.weights, 1))})", "",
                      "| Rank | Team | " + " | ".join(f"R{s['round']} (x{w(s['round'])})" for s in scored) + " | Weighted total |",
                      "|---|---|" + "---|" * len(scored) + "---|"]
            for i, t in enumerate(sorted(teams, key=lambda t: -total[t]), 1):
                lines.append(f"| {i} | {t} | " + " | ".join(f"{s['scores'][t]['points']:.2f}" for s in scored)
                             + f" | {total[t]:.2f} |")
        return "\n".join(lines) + "\n"

    def deliver(self, ev: dict, rdir: Path, summary: dict) -> None:
        name = f"{ev['kind']}{ev['n']}"
        page = self.results_page(summary)
        (rdir / "results.md").write_text(page)
        for team in self.active:
            src = rdir / "downloads" / self.slug[team]
            up = summary["uploads"][team]
            status = ("passed the upload test" if up["ok"] else f"was REJECTED by the upload test ({up['reason']}); "
                      f"{'your previous upload played' if up['active'] else 'you had no active bot and forfeited'}")
            notice = (f"{summary['label']} has finished. Your upload {status}. Results: results/{name}.md. "
                      f"Your hand history: downloads/{name}/ (full file and a -first-1000 subset).")
            if team == AVALON:
                ws = self.dir / AVALON
                (ws / "results" / f"{name}.md").write_text(page)
                shutil.copytree(src, ws / "downloads" / name, dirs_exist_ok=True)
                (ws / "inbox" / f"{int(time.time())}-{name}.md").write_text(notice + "\n")
                log(f"avalon: {notice}")
                continue
            if team not in self.sandboxes:
                continue
            key = f"{self.a.run}/{self.slug[team]}/deliver/{name}"
            try:
                with self.vol.batch_upload(force=True) as upl:
                    upl.put_file(io.BytesIO(page.encode()), f"/{key}/{name}.md")
                    upl.put_file(io.BytesIO(notice.encode()), f"/{key}/notice.md")
                    if name not in self.remote:
                        for f in src.iterdir():
                            upl.put_file(str(f), f"/{key}/downloads/{f.name}")
                sb = self.sandboxes[team]
                sb.reload_volumes()
                sb.exec("bash", "-lc",
                        f"mkdir -p /home/team/work/downloads/{name} && cp /vol/{key}/{name}.md /home/team/work/results/ "
                        f"&& cp {self.remote[name] + '/' + self.slug[team] if name in self.remote else '/vol/' + key + '/downloads'}/* "
                        f"/home/team/work/downloads/{name}/ "
                        f"&& cp /vol/{key}/notice.md /home/team/inbox/$(date +%s)-{name}.md "
                        f"&& chown -R team:team /home/team/work/results /home/team/work/downloads /home/team/inbox",
                        timeout=600).wait()
            except Exception as e:  # noqa: BLE001
                log(f"{team}: delivery of {name} failed: {e!r}")

    # ---------------------------------------------------------------- end
    def collect(self, team: str) -> None:
        sb = self.sandboxes[team]
        out = self.dir / self.slug[team]
        try:
            p = sb.exec("bash", "-lc", "cd /tmp && tar czf - out $(ls -d prep 2>/dev/null) | base64 -w0", timeout=600)
            data = p.stdout.read()
            p.wait()
            with tarfile.open(fileobj=io.BytesIO(base64.b64decode(data)), mode="r:gz") as tar:
                tar.extractall(out / "session", filter="data")
            p = sb.exec("bash", "-lc", "cd /home/team/work && tar czf - --exclude=downloads --exclude=kit . | base64 -w0",
                        timeout=600)
            data = p.stdout.read()
            p.wait()
            with tarfile.open(fileobj=io.BytesIO(base64.b64decode(data)), mode="r:gz") as tar:
                tar.extractall(out / "final_workspace", filter="data")
        except Exception as e:  # noqa: BLE001
            log(f"{team}: collect failed: {e!r}")

    def wait_for_start(self) -> float:
        """The event starts when told: emu/runs/<run>/START holds 'now' or a time (HH:MM, today or
        tomorrow) for the build to begin. Write it with `rehearsal.py --run <run> --start now|21:00`."""
        sig = self.dir / "START"
        if not self.a.wait:
            return time.time() + 300 + 60 * max(int(p * self.a.prep_scale) for _, _, p, _ in self.teams.values())
        log(f"READY. Waiting for the start signal ({sig}); nothing runs until then.")
        while not sig.exists():
            time.sleep(5)
        start = parse_start(sig.read_text().strip())
        log(f"start signal: the build begins at {time.strftime('%H:%M:%S', time.localtime(start))}")
        return start

    def run(self) -> None:
        log(f"{self.a.run}: {len(self.teams)} simulated teams + avalon; variant {self.a.variant}; scale {self.a.scale}")
        self.workspace(AVALON)
        log(f"avalon workspace: {self.dir / AVALON} (submission/ starts as bots/v10)")
        start = self.wait_for_start()
        SETUP_S = 300  # creating and filling a sandbox, before its session begins

        def launch(team: str) -> None:
            planned = int(self.teams[team][2] * self.a.prep_scale)
            # Research teams launch early enough for their full research; if the start is too soon,
            # they get whatever lead time is left (as a team that started researching late would).
            launch_at = start - SETUP_S - 60 * planned
            time.sleep(max(0, launch_at - time.time()))
            prep = max(0, min(planned, int((start - time.time() - SETUP_S) / 60)))
            if prep < planned:
                log(f"{team}: only {prep} of {planned} min of pre-event research before the start")
            self.start_team(team, start, prep)

        with ThreadPoolExecutor(len(self.teams)) as pool:
            for f in [pool.submit(launch, t) for t in self.teams]:
                try:
                    f.result()
                except Exception as e:  # noqa: BLE001
                    log(f"team failed to start: {e!r}")
        for t in self.teams:
            if t not in self.sandboxes:
                log(f"{t}: no sandbox; it will forfeit")
        (self.dir / "event.json").write_text(json.dumps({"start": start, "events": self.events,
                                                         "teams": self.teams}, indent=1))
        (self.dir / AVALON / "inbox" / "0-start.md").write_text(
            f"The build starts at {time.strftime('%H:%M:%S', time.localtime(start))}. Schedule: "
            + "; ".join(f"{e['label']} at +{e['t'] / 60:.0f} min" for e in self.events) + "\n")
        log(f"event clock starts at {time.strftime('%H:%M:%S', time.localtime(start))}")
        threads = []
        for ev in self.events:
            time.sleep(max(0, start + ev["t"] - time.time()))
            log(f"=== {ev['label']} starts: snapshotting uploads")
            th = threading.Thread(target=self.play, args=(ev,), daemon=False)
            th.start()
            threads.append(th)
            if ev is self.events[-1]:
                th.join()  # the last round's uploads are taken inside play() before teams stop
        for th in threads:
            th.join()
        with ThreadPoolExecutor(8) as pool:
            list(pool.map(self.collect, list(self.sandboxes)))
        for sb in self.sandboxes.values():
            sb.terminate()
        log(f"done. final results: {self.dir / 'rounds' / 'scored6' / 'results.md'}")


def parse_start(text: str) -> float:
    if text.lower() == "now":
        return time.time() + 360  # time to create and fill the sandboxes
    hh, mm = (int(x) for x in text.split(":"))
    now = time.localtime()
    t = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, hh, mm, 0, 0, 0, -1))
    return t if t > time.time() + 300 else t + 86400 if t < time.time() - 3600 else time.time() + 360


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", required=True)
    p.add_argument("--teams", type=int, default=len(TEAMS), help="how many synthetic teams (max 19)")
    p.add_argument("--personas", default=None, help="comma-separated persona files to use instead of --teams")
    p.add_argument("--scale", type=float, default=1.0, help="timeline scale (0.1 = 10x faster, for tests)")
    p.add_argument("--variant", default="flop_discard_reveal")
    p.add_argument("--variant-rules", default=None, help="RULES.md of a mock variant")
    p.add_argument("--practice-iterations", type=int, default=1000)
    p.add_argument("--round-iterations", type=int, default=5000)
    p.add_argument("--shards", type=int, default=40, help="Modal containers per round (local: at most 4)")
    p.add_argument("--local-rounds", action="store_true", help="play rounds on this machine instead of Modal")
    p.add_argument("--weights", default="1,2,3,4,5,6", help="round weights; Boston used 1,2,3,5,8,13")
    p.add_argument("--field", default="", help="'finals': the 7 simulated finalists with regional notes (+ avalon = 8)")
    p.add_argument("--avalon-start", default="empty", help="avalon's bot at the start: 'empty' (as on Sunday) or a bots/ folder")
    p.add_argument("--prep-scale", type=float, default=1.0, help="scale pre-event research minutes (0 = none)")
    p.add_argument("--avalon-replay", default=None,
                   help="validation: avalon's bot per scored round, e.g. v3b,v5r,v6,v7,v9s,v10 (the real night)")
    p.add_argument("--avalon-practice", default="v3b", help="avalon's bot in practice rounds with --avalon-replay")
    p.add_argument("--wait", action="store_true", help="set up, then wait for --start before anything runs")
    p.add_argument("--start", default=None, help="signal a waiting run: 'now' or HH:MM for the build to begin")
    a = p.parse_args()
    if a.start:
        parse_start(a.start)  # validate
        sig = EMU / "runs" / a.run / "START"
        sig.parent.mkdir(parents=True, exist_ok=True)
        sig.write_text(a.start + "\n")
        print(f"start signal written: {sig} = {a.start}")
        return
    Event(a).run()


if __name__ == "__main__":
    main()
