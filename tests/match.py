"""Run poker-agent's local match with rule overrides, then print a compact summary.

Usage: python tests/match.py [--tables N] [--seed S] [--bank MS] [--hand-cap N]
                             [--hands-per-level N] [--json OUT] BOT_DIR [BOT_DIR ...]
--bank 0 reproduces the upload test match (no time bank). Groups seats by folder name.
"""

import argparse
import asyncio
import contextlib
import functools
import io
import json
import sys
from collections import defaultdict

import poker_agent_sdk.cli as cli
from poker_engine.table import TableRules


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("bots", nargs="+")
    p.add_argument("--tables", type=int, default=200)
    p.add_argument("--seed", default=None)
    p.add_argument("--bank", type=int, default=100)
    p.add_argument("--hand-cap", type=int, default=250)
    p.add_argument("--hands-per-level", type=int, default=20)
    p.add_argument("--decision-ms", type=int, default=1)
    p.add_argument("--json", default=None)
    a = p.parse_args()

    cli.TableRules = functools.partial(
        TableRules, time_bank_ms=a.bank, hands_per_level=a.hands_per_level
    )
    ns = argparse.Namespace(
        bots=[cli.Path(b) for b in a.bots], tables=a.tables, seed=a.seed,
        variant="flop_discard_reveal", decision_ms=a.decision_ms, hand_cap=a.hand_cap,
        history=None, no_history=True, hero=0,
    )
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        asyncio.run(cli.play_local(ns))
    out = json.loads(buf.getvalue())
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=2)
    groups: dict[str, list] = defaultdict(list)
    for label, v in out["bots"].items():
        groups[label.split("#")[0]].append(v)
    print(f"seed={out['seed']} tables={out['tables']} bank={a.bank} cap={a.hand_cap} "
          f"hpl={a.hands_per_level}")
    for name, vs in groups.items():
        pts = [v["average_points"] for v in vs]
        fails = sum(v["failed_decisions"] for v in vs)
        wins = sum(v["places"].get("1", 0) for v in vs)
        tot = sum(sum(v["places"].values()) for v in vs) or 1
        sh = [sum(v["places"].get(str(k), 0) for v in vs) / tot for k in (1, 2, 3)]
        print(f"  {name:16s} seats={len(vs)} avg_pts/seat={sum(pts)/len(pts):6.2f} "
              f"per-seat={pts} wins={wins} 1st/2nd/3rd={sh[0]:.0%}/{sh[1]:.0%}/{sh[2]:.0%} failed={fails}")


if __name__ == "__main__":
    main()
