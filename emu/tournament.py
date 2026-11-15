"""Play one emulated tournament round for a whole field, the way the organizers' workers do.

Every iteration seats every entry once (kit `seat_iteration`: shuffle, tables of rules["players"] (8 at
the regional, 6 at the Finals: emu/tables.py), the short last table filled with non-scoring fillers), plays each table on the kit's real engine with real
bot processes, and keeps:
  - results.jsonl: one line per table (points, places, failures, decisions, hands per seat);
  - one participant download per entry, in the real format: a header line
    (tournament_id, you, entries) and then, for every table the entry sat at (one pair per
    seat, filler seats included), the public table line and its private `you` line, in
    iteration/table order. `<name>-first-1000` holds the first 1,000 iterations.

Run with the kit's Python from the repo root:
  starter-kit/.venv/bin/python emu/tournament.py --field emu/fields/pilot.json --round 1 \
      --iterations 50 --out emu/out/r1

A field file is {"name": ..., "entries": [{"team": "Team name", "bot": "path/to/bot_dir"}, ...],
"rules": {TableRules fields, as in rules_to_dict}}; bot paths are relative to the repo root.
Shard a round with --first-iteration/--iterations and merge the shards with `merge`.
"""

import argparse
import asyncio
import gzip
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from poker_agent_protocol.process import BotPool  # noqa: E402
from poker_agent_sdk.history import encoded  # noqa: E402
from poker_engine.history import private_view, public_view  # noqa: E402
from poker_engine.play import play_table  # noqa: E402
from poker_engine.scoring import table_places, table_points  # noqa: E402
from poker_engine.seating import seat_iteration  # noqa: E402
from poker_engine.table import SitAndGo, rules_from_dict, rules_to_dict, table_seed  # noqa: E402
from poker_engine.variant import load_variant  # noqa: E402

FIRST_SAMPLE = 1000  # iterations in the "-first-1000" download


def load_field(path: str) -> dict:
    field = json.loads(Path(path).read_text())
    teams = [e["team"] for e in field["entries"]]
    if len(set(teams)) != len(teams):
        raise SystemExit("Team names must be unique.")
    for e in field["entries"]:
        bot = (ROOT / e["bot"]).resolve()
        if not (bot / "agent.py").is_file():
            raise SystemExit(f"{e['team']}: no agent.py in {bot}")
        e["path"] = str(bot)
    return field


def register_variant_file(path: str) -> str:
    """A variant module file (a mock Finals variant), loadable by name like a built-in one."""
    import importlib.util

    file = (ROOT / path).resolve()
    name = file.stem
    spec = importlib.util.spec_from_file_location(f"poker_engine.variants.{name}", file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return name


async def play_shard(field: dict, seed: str, first: int, count: int, out: Path,
                     concurrency: int, copies: int) -> dict:
    """Play iterations [first, first+count). Writes results.jsonl and per-team .part.gz
    (gzip members, one per table pair, sorted by iteration/table) into `out`."""
    rules_dict = dict(field.get("rules", {}))
    if "variant_file" in rules_dict:
        rules_dict["variant"] = register_variant_file(rules_dict.pop("variant_file"))
    # Fields smaller than eight play short tables (portal Format page, "Fairness").
    rules_dict["players"] = min(int(rules_dict.get("players", 8)), len(field["entries"]))
    rules = rules_from_dict(rules_dict)
    variant = load_variant(rules.variant)
    teams = [e["team"] for e in field["entries"]]
    path = {e["team"]: e["path"] for e in field["entries"]}
    pools = {t: BotPool([sys.executable, "-m", "poker_agent_sdk.guest", path[t]], copies=copies,
                        cwd=path[t]) for t in teams}
    running = asyncio.Semaphore(concurrency)
    tables: list[dict] = []          # results, one per table
    parts: dict[str, list] = {t: [] for t in teams}  # team -> [(iteration, table, seat, bytes)]

    async def one(iteration: int, number: int, seating) -> None:
        tseed = table_seed(seed, iteration, number)
        table = SitAndGo(rules=rules, variant=variant, table_id=f"{iteration}-{number}", seed=tseed)
        async with running:
            result = await play_table(table, [pools[s.entry] for s in seating])
        pts, places = table_points(result, table.payouts), table_places(result)
        names = [s.entry for s in seating]
        # With the round's entry ids fixed up front (field["ids"]), the public line names them directly,
        # as the real files do, and merging is a plain concatenation.
        seat_ids = [field.get("ids", {}).get(n, n) for n in names]
        raw = {"variant": rules.variant, "iteration": iteration, "table": number, "seats": seat_ids,
               "fillers": [s.filler for s in seating], "payouts": list(table.payouts),
               "hands": table.log}
        pub = encoded(public_view(raw))
        for seat, name in enumerate(names):
            member = gzip.compress(pub + encoded(private_view(raw, seat)), compresslevel=6, mtime=0)
            parts[name].append((iteration, number, seat, member))
        tables.append({
            "iteration": iteration, "table": number, "hands": result.hands_played,
            "payouts": list(table.payouts), "seats": names,
            "fillers": [s.filler for s in seating],
            "points": [round(p, 4) for p in pts], "places": list(places),
            "failures": list(result.failures), "decisions": list(result.decisions),
        })

    start = time.perf_counter()
    tasks = []
    for iteration in range(first, first + count):
        for number, seating in enumerate(seat_iteration(teams, seed=seed, iteration=iteration,
                                                        table_size=rules.players)):
            tasks.append(asyncio.create_task(one(iteration, number, seating)))
    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for p in pools.values():
            await p.stop()
    errors = {t: p.logs.decode(errors="replace")[-4000:] for t, p in pools.items() if p.logs}
    out.mkdir(parents=True, exist_ok=True)
    tables.sort(key=lambda r: (r["iteration"], r["table"]))
    with open(out / "results.jsonl", "w") as f:
        for r in tables:
            f.write(json.dumps(r) + "\n")
    for team, items in parts.items():
        items.sort(key=lambda x: x[:3])
        with open(out / f"{slug(team)}.part.gz", "wb") as f:
            for it, *_rest, member in items:
                f.write(member)
        with open(out / f"{slug(team)}.first.part.gz", "wb") as f:
            for it, *_rest, member in items:
                if it < FIRST_SAMPLE:
                    f.write(member)
    meta = {"seed": seed, "first": first, "count": count, "rules": rules_to_dict(rules),
            "elapsed_s": round(time.perf_counter() - start, 2), "bot_stderr": errors}
    (out / "shard.json").write_text(json.dumps(meta, indent=1))
    return meta


def slug(team: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in team).strip("_").lower()


def merge(field: dict, shards: list[Path], dest: Path, round_no: int, download_teams: list[str] | None = None) -> dict:
    """Concatenate shards (in iteration order) into one round: per-team downloads named like the
    real ones, results.jsonl, and the round score per team. Entry ids are fresh per round, as on
    the real platform; team names are the stable key."""
    shards = sorted(shards, key=lambda s: json.loads((s / "shard.json").read_text())["first"])
    teams = [e["team"] for e in field["entries"]]
    preset = bool(field.get("ids"))
    tid = field.get("tournament_id") or str(uuid.uuid4())
    ids = field.get("ids") or {t: str(uuid.uuid4()) for t in teams}
    entries = [{"entry_id": ids[t], "team_name": t} for t in teams]
    dest.mkdir(parents=True, exist_ok=True)
    downloads = dest / "downloads"
    downloads.mkdir(exist_ok=True)
    results = []
    for s in shards:
        results += [json.loads(line) for line in (s / "results.jsonl").read_text().splitlines()]
    (dest / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in results))
    for team in teams:
        if download_teams is not None and team not in download_teams:
            continue  # only these teams' downloads are wanted (a fixed field: avalon's)
        header = gzip.compress(encoded({"tournament_id": tid, "you": ids[team], "entries": entries}),
                               mtime=0)
        for suffix, part in (("", "part.gz"), ("-first-1000", "first.part.gz")):
            with open(_team_file(downloads, team, tid, suffix), "wb") as f:
                f.write(header)
                for s in shards:
                    data = (s / f"{slug(team)}.{part}").read_bytes()
                    f.write(data if preset else _rename_ids(data, ids))
    score = round_scores(results, teams)
    summary = {"round": round_no, "tournament_id": tid, "entry_ids": ids,
               "iterations": len({r["iteration"] for r in results}), "tables": len(results),
               "scores": score}
    (dest / "round.json").write_text(json.dumps(summary, indent=1))
    return summary


def _team_file(downloads: Path, team: str, tid: str, suffix: str) -> Path:
    d = downloads / slug(team)
    d.mkdir(exist_ok=True)
    return d / f"hands-{tid}{suffix}.jsonl.gz"


def _rename_ids(data: bytes, ids: dict[str, str]) -> bytes:
    """Seats are written with team names during play; the real files name entry ids."""
    out = []
    for member in _gzip_members(data):
        text = gzip.decompress(member).decode()
        pub, priv = text.split("\n", 1)
        rec = json.loads(pub)
        rec["seats"] = [ids[s] for s in rec["seats"]]
        out.append(gzip.compress(encoded(rec) + priv.encode(), compresslevel=6, mtime=0))
    return b"".join(out)


def _gzip_members(data: bytes):
    """Split concatenated gzip members (each table pair is one)."""
    import zlib

    pos = 0
    while pos < len(data):
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        d.decompress(data[pos:])
        used = len(data) - pos - len(d.unused_data)
        yield data[pos:pos + used]
        pos += used


def round_scores(results: list[dict], teams: list[str]) -> dict:
    """Round score = average points over the entry's scored (non-filler) tables, plus places."""
    out = {}
    for t in teams:
        pts, places, fails, decs = [], {}, 0, 0
        for r in results:
            for seat, name in enumerate(r["seats"]):
                if name != t:
                    continue
                fails += r["failures"][seat]
                decs += r["decisions"][seat]
                if r["fillers"][seat]:
                    continue
                pts.append(r["points"][seat])
                places[r["places"][seat]] = places.get(r["places"][seat], 0) + 1
        n = max(1, len(pts))
        out[t] = {"points": round(sum(pts) / n, 3), "tables": len(pts),
                  "places": {k: round(v / n, 4) for k, v in sorted(places.items())},
                  "failed_decisions": fails, "decisions": decs}
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    play = sub.add_parser("play", help="play one shard of iterations")
    play.add_argument("--field", required=True)
    play.add_argument("--seed", required=True, help="the round's seed (same for every shard)")
    play.add_argument("--first-iteration", type=int, default=0)
    play.add_argument("--iterations", type=int, default=20)
    play.add_argument("--out", required=True, help="shard output folder")
    play.add_argument("--concurrency", type=int, default=8)
    play.add_argument("--copies", type=int, default=2)
    m = sub.add_parser("merge", help="merge shards into a round's downloads and scores")
    m.add_argument("--field", required=True)
    m.add_argument("--round", type=int, required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--download-teams", default=None, help="comma-separated teams whose downloads to write (default all)")
    m.add_argument("shards", nargs="+")
    a = p.parse_args()
    field = load_field(a.field)
    if a.cmd == "play":
        meta = asyncio.run(play_shard(field, a.seed, a.first_iteration, a.iterations, Path(a.out),
                                      a.concurrency, a.copies))
        print(json.dumps({k: meta[k] for k in ("first", "count", "elapsed_s")}))
        for team, log in meta["bot_stderr"].items():
            print(f"--- {team} stderr (tail) ---\n{log}", file=sys.stderr)
    elif a.cmd == "merge":
        s = merge(field, [Path(x) for x in a.shards], Path(a.out), a.round,
                  a.download_teams.split(",") if a.download_teams else None)
        for team, v in sorted(s["scores"].items(), key=lambda kv: -kv[1]["points"]):
            print(f"{v['points']:7.2f}  {team:28s} tables={v['tables']} failed={v['failed_decisions']}")
    else:
        p.print_help()


if __name__ == "__main__":
    main()
