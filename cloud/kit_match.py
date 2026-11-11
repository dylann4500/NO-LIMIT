"""Play bots against each other on the starter kit's real engine and write per-table results.

The same script runs locally and inside a Modal container (cloud/nl_modal.py), so a cloud
result is the local result at scale. It follows `poker-agent play` (kit cli.play_local): real
bot processes, two copies per folder, the kit's seating, payouts and scoring. On top of that:
- every TableRules field is settable (variant, blinds pace, cap, bank, payouts, stack, ...);
- `--variant-file` plays a variant module that is not installed (a mock Finals variant);
- results are kept per table, so callers can compute paired differences and standard errors.

Usage (from the repo root, with the kit's Python):
  starter-kit/.venv/bin/python cloud/kit_match.py --tables 200 --out /tmp/r.json \
      bots/v10 bots/v10 bots/v9s bots/v9s bots/v6 bots/v6 \
      starter-kit/examples/check_or_fold starter-kit/examples/min_raiser
Upload-test conditions: two bots, --bank 0 --hand-cap 20.

Each bot argument is one seat; repeat a folder to give it more seats. Results are grouped by
the folder path as given. Seats are reshuffled on every table.
"""

import argparse
import asyncio
import importlib.util
import json
import secrets
import sys
import time
from pathlib import Path

from poker_agent_protocol.process import BotPool
from poker_engine.play import play_table
from poker_engine.scoring import table_places, table_points
from poker_engine.seating import seat_iteration
from poker_engine.table import SitAndGo, TableRules, rules_to_dict
from poker_engine.variant import load_variant


def register_variant_file(path: str) -> str:
    """Make a variant module file loadable by name, as if it were built into the engine.
    Its name is the file's stem; the module must define VARIANT, like the built-in ones."""
    file = Path(path).resolve()
    name = file.stem
    module_name = f"poker_engine.variants.{name}"
    spec = importlib.util.spec_from_file_location(module_name, file)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load a variant from {file}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "VARIANT"):
        raise ValueError(f"{file} defines no VARIANT.")
    return name


def parse_payouts(text: str) -> tuple[tuple[int, int], ...]:
    """'50,30,20' -> fixed places; '40-60,20-40,10-30' -> a range per place."""
    out = []
    for part in text.split(","):
        low, _, high = part.strip().partition("-")
        out.append((int(low), int(high or low)))
    return tuple(out)


def build_rules(a: argparse.Namespace, players: int) -> TableRules:
    fields = {
        "variant": a.variant,
        "players": players,
        "decision_ms": a.decision_ms,
        "time_bank_ms": a.bank,
        "hand_cap": a.hand_cap,
        "hands_per_level": a.hands_per_level,
    }
    if a.starting_stack:
        fields["starting_stack"] = a.starting_stack
    if a.payouts:
        fields["payouts"] = parse_payouts(a.payouts)
    if a.payout_total:
        fields["payout_total"] = a.payout_total
    if a.blinds:  # '10/20,20/40,...'
        from poker_agent_protocol.game import BlindLevel

        levels = []
        for part in a.blinds.split(","):
            small, big = part.strip().split("/")
            levels.append(BlindLevel(int(small), int(big)))
        fields["blinds"] = tuple(levels)
    return TableRules(**fields)


async def run(a: argparse.Namespace) -> dict:
    bots = [Path(b).resolve() for b in a.bots]
    if not 2 <= len(bots) <= 10 or not all((b / "agent.py").is_file() for b in bots):
        raise SystemExit("Give 2 to 10 bot folders that each contain agent.py.")
    if a.variant_file:
        a.variant = register_variant_file(a.variant_file)
    rules = build_rules(a, len(bots))
    variant = load_variant(rules.variant)
    seed = a.seed or secrets.token_hex(8)
    labels = [f"{name}#{i}" for i, name in enumerate(a.bots)]
    pools = {
        b: BotPool([sys.executable, "-m", "poker_agent_sdk.guest", str(b)], copies=a.copies, cwd=str(b))
        for b in set(bots)
    }
    running = asyncio.Semaphore(a.concurrency)
    records: list[dict] = []

    async def one_table(number: int) -> None:
        seating = seat_iteration(labels, seed=seed, iteration=number, table_size=len(bots))[0]
        table = SitAndGo(rules=rules, variant=variant, table_id=f"t{number}", seed=f"{seed}:{number}")
        seats = [pools[bots[labels.index(s.entry)]] for s in seating]
        async with running:
            result = await play_table(table, seats)
        pts = table_points(result, table.payouts)
        places = table_places(result)
        records.append({
            "table": number,
            "hands": result.hands_played,
            "payouts": list(table.payouts),
            "seats": [s.entry for s in seating],
            "points": {s.entry: pts[i] for i, s in enumerate(seating)},
            "places": {s.entry: places[i] for i, s in enumerate(seating)},
            "failures": {s.entry: result.failures[i] for i, s in enumerate(seating)},
            "decisions": {s.entry: result.decisions[i] for i, s in enumerate(seating)},
        })

    start = time.perf_counter()
    tasks = [asyncio.create_task(one_table(n)) for n in range(a.first_table, a.first_table + a.tables)]
    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for p in pools.values():
            await p.stop()
    logs = {Path(b).name: p.logs.decode(errors="replace")[-4000:] for b, p in pools.items() if p.logs}
    records.sort(key=lambda r: r["table"])
    return {
        "seed": seed,
        "rules": rules_to_dict(rules),
        "labels": labels,
        "groups": {label: label.rsplit("#", 1)[0] for label in labels},
        "elapsed_s": round(time.perf_counter() - start, 2),
        "tables": records,
        "bot_stderr": logs,
    }


def summarize(out: dict) -> str:
    """One line per bot folder: points per seat with a 95% interval over tables."""
    import statistics

    groups = sorted(set(out["groups"].values()), key=list(out["groups"].values()).index)
    lines = [f"seed={out['seed']} tables={len(out['tables'])} variant={out['rules']['variant']} "
             f"elapsed={out['elapsed_s']}s"]
    for g in groups:
        labels = [l for l, gg in out["groups"].items() if gg == g]
        per_table = [sum(t["points"][l] for l in labels) / len(labels) for t in out["tables"]]
        mean = statistics.fmean(per_table)
        se = statistics.stdev(per_table) / len(per_table) ** 0.5 if len(per_table) > 1 else 0.0
        fails = sum(t["failures"][l] for t in out["tables"] for l in labels)
        decs = sum(t["decisions"][l] for t in out["tables"] for l in labels)
        firsts = sum(t["places"][l] == 1 for t in out["tables"] for l in labels)
        lines.append(f"  {g:40s} seats={len(labels)} pts/seat={mean:6.2f} ±{1.96 * se:5.2f} "
                     f"1st={firsts / (len(labels) * len(out['tables'])):5.1%} failed={fails}/{decs}")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("bots", nargs="+", help="bot folders, one per seat")
    p.add_argument("--tables", type=int, default=200)
    p.add_argument("--first-table", type=int, default=0, help="table numbers start here (sharding)")
    p.add_argument("--seed", default=None)
    p.add_argument("--variant", default="flop_discard_reveal")
    p.add_argument("--variant-file", default=None, help="a variant module .py to play instead")
    p.add_argument("--bank", type=int, default=100, help="time bank ms per table; 0 = upload test")
    p.add_argument("--decision-ms", type=int, default=1)
    p.add_argument("--hand-cap", type=int, default=250)
    p.add_argument("--hands-per-level", type=int, default=20)
    p.add_argument("--starting-stack", type=int, default=0)
    p.add_argument("--blinds", default=None, help="'10/20,20/40,...'; the last level repeats")
    p.add_argument("--payouts", default=None, help="'50,30,20' or ranges '40-60,20-40,10-30'")
    p.add_argument("--payout-total", type=int, default=0)
    p.add_argument("--concurrency", type=int, default=8, help="tables in flight (kit default 8)")
    p.add_argument("--copies", type=int, default=2, help="processes per bot folder (kit default 2)")
    p.add_argument("--out", default=None, help="write the full per-table JSON here")
    a = p.parse_args()
    out = asyncio.run(run(a))
    if a.out:
        Path(a.out).write_text(json.dumps(out))
    print(summarize(out))
    for name, log in out["bot_stderr"].items():
        print(f"--- {name} stderr (tail) ---\n{log}", file=sys.stderr)


if __name__ == "__main__":
    main()
