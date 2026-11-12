"""Write a mock starter kit for one mock variant, the way the organizers ship a real one.

    starter-kit/.venv/bin/python emu/variants/make_kit.py <variant_id> <out_dir> [--force]

The kit is a copy of starter-kit/ (no .venv, __pycache__ or local hand histories) where:
  - sdk/engine/src/poker_engine/variants/ holds only __init__.py, the variant's module, its
    rules page and any `_helper` modules it imports, so `poker-agent play` defaults to it;
  - RULES.md is the variant's rules page;
  - the participant export (poker_engine/history.py) and its validator
    (poker_agent_sdk/local_history.py) gain the variant's public hand fields and owner-only
    private events, at the points where the organizers' kit varies by variant (SPECS below);
  - hand-history/ holds a new sample.jsonl(.gz), played on the kit's own engine with the kit's
    examples and a scripted sample bot; Bay Area's CASES.md and coverage.json are dropped and
    the README's private-event bullet is rewritten for the variant.
README.md and AGENTS.md keep the organizers' text.

Use the kit without installing it: put its three src folders first on PYTHONPATH (see
`kit_env`), or install them into a throwaway venv. Variant modules and rules live beside this
file in emu/variants/.
"""

import argparse
import gzip
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
KIT = ROOT / "starter-kit"
VARIANTS = "sdk/engine/src/poker_engine/variants"
SRC = ("sdk/agent-protocol/src", "sdk/engine/src", "sdk/agent-sdk/src")

# Per variant: hand fields the participant export keeps, event kinds that must name a seat,
# and owner-only private events: kind -> (has cards, has amount, public events it may attach
# to: None = the hand's start (index -1), "own:KIND" = this seat's KIND event, else any KIND).
SPECS: dict[str, dict] = {
    "flop_auction_holdem": {
        "hand_fields": ["flop_chips_before", "flop_chips_after"],
        "seat_kinds": ["bid"],
        "private": {
            "flop_chips": (False, True, [None, "board"]),
            "bid": (True, True, ["own:bid"]),
            "flop_chips_paid": (False, True, ["board"]),
        },
        "readme": (
            "- `flop_chips`: your flop-chip `amount` at the start of the hand (`event_index` -1)\n"
            "  and again after the auction, at the flop's `board` event.\n"
            "- `bid`: one per auction card you bid on, with the card in `cards` and your bid in\n"
            "  `amount`, at your own public `bid` event.\n"
            "- `flop_chips_paid`: the flop-chips you paid (possibly 0), at the flop's `board` event.\n"
        ),
    },
    "turn_draw_holdem": {
        "hand_fields": [],
        "seat_kinds": ["draw", "exchange"],
        "private": {"drawn": (True, False, ["own:exchange"])},
        "readme": (
            "- `drawn`: your replacement card, at your own public `exchange` event. These records\n"
            "  contain only your own cards.\n"
        ),
    },
    "flop_pass_holdem": {
        "hand_fields": [],
        "seat_kinds": ["pass"],
        "private": {
            "passed": (True, False, ["passes"]),
            "received": (True, False, ["passes"]),
        },
        "readme": (
            "- `passed` / `received`: the card you passed to your left and the card passed to you,\n"
            "  effective at the public `passes` event. These records contain only your own cards.\n"
        ),
    },
}


def kit_env(kit: Path) -> dict[str, str]:
    """The environment running the kit's sources ahead of any installed starter kit."""
    env = dict(os.environ)
    paths = [str(kit / src) for src in SRC]
    env["PYTHONPATH"] = os.pathsep.join(paths + [env["PYTHONPATH"]] if env.get("PYTHONPATH") else paths)
    return env


def patch(path: Path, anchor: str, new: str, *, before: bool = False, replace: bool = False) -> None:
    """Insert `new` after (or before, or instead of) the one occurrence of `anchor`."""
    text = path.read_text()
    if text.count(anchor) != 1:
        raise SystemExit(f"{path}: expected one {anchor!r}; the kit changed, update make_kit.")
    text = text.replace(anchor, new if replace else (new + anchor if before else anchor + new))
    path.write_text(text)


def patch_history(kit: Path, variant: str) -> None:
    spec = SPECS[variant]
    history = kit / "sdk/engine/src/poker_engine/history.py"
    note = f"# Mock variant {variant} (emu/variants/make_kit.py)."
    if spec["hand_fields"]:
        patch(
            history,
            'SHOWN_KINDS.add("reveal")\n',
            f"{note}\nPUBLIC_HAND_FIELDS.update({tuple(spec['hand_fields'])!r})\n",
        )
    patch(
        history,
        '    return sorted(result, key=lambda event: event["event_index"])\n',
        f"    {note}\n"
        '    for event in record.get("private", []):\n'
        '        if event.get("seat") == seat:\n'
        '            fields = {key: event[key] for key in ("cards", "amount") if key in event}\n'
        '            add(event["kind"], event["event_index"], **fields)\n',
        before=True,
    )
    validator = kit / "sdk/agent-sdk/src/poker_agent_sdk/local_history.py"
    private = spec["private"]
    anchors = {kind: tuple(at) for kind, (_, _, at) in private.items()}
    patch(
        validator,
        '    card_kinds.update(("kept", "discarded"))\n',
        f"    {note}\n"
        f"    variant_anchors: dict[str, tuple[str | None, ...]] = {anchors!r}\n"
        f"    card_kinds.update({tuple(k for k, v in private.items() if v[0])!r})\n"
        f"    amount_kinds.update({tuple(k for k, v in private.items() if v[1])!r})\n",
    )
    patch(
        validator,
        "        identity: tuple[int, int, str, tuple[str, ...]] = (number, index, kind, ())\n",
        "        identity: tuple[int, int, str, tuple[str, ...]] = (\n"
        "            number,\n"
        "            index,\n"
        "            kind,\n"
        '            tuple(event["cards"]) if kind in variant_anchors and "cards" in event else (),\n'
        "        )\n",
        replace=True,
    )
    patch(
        validator,
        "        public = events[index] if index >= 0 else None\n",
        "        if kind in variant_anchors:\n"
        "            require(\n"
        "                any(\n"
        "                    public is None\n"
        "                    if anchor is None\n"
        "                    else public is not None\n"
        '                    and public["kind"] == anchor.removeprefix("own:")\n'
        '                    and (not anchor.startswith("own:") or public.get("seat") == own["seat"])\n'
        "                    for anchor in variant_anchors[kind]\n"
        "                ),\n"
        '                "Private event does not match its public event.",\n'
        "            )\n",
    )
    if spec["seat_kinds"]:
        patch(
            validator,
            '                    "reveal",\n',
            "".join(f'                    "{kind}",\n' for kind in spec["seat_kinds"]),
        )


def patch_readme(kit: Path, variant: str) -> None:
    readme = kit / "hand-history/README.md"
    patch(
        readme,
        "- `kept` / `discarded`: your retained or discarded `cards`, effective at your discard or the\n"
        "  simultaneous reveal. These records contain only your own cards.\n",
        SPECS[variant]["readme"],
        replace=True,
    )


def helpers(module: Path) -> list[str]:
    """The `_helper` variant modules this module imports."""
    found = re.findall(r"poker_engine\.variants\.(_\w+)|from poker_engine\.variants import (_\w+)",
                       module.read_text())
    return sorted({a or b for a, b in found})


def build(variant: str, out: Path, force: bool) -> None:
    module, rules = HERE / f"{variant}.py", HERE / f"{variant}.md"
    if variant not in SPECS or not module.is_file() or not rules.is_file():
        raise SystemExit(f"No mock variant {variant!r} in {HERE} (known: {', '.join(SPECS)}).")
    if out.exists():
        if not force:
            raise SystemExit(f"{out} exists; pass --force to replace it.")
        shutil.rmtree(out)
    shutil.copytree(
        KIT,
        out,
        ignore=lambda folder, names: [
            n
            for n in names
            if n in (".venv", "__pycache__", ".DS_Store")
            or (Path(folder).name == "hand-history" and n.startswith("local-"))
        ],
    )
    variants = out / VARIANTS
    for item in variants.iterdir():
        if item.name != "__init__.py":
            item.unlink()
    shutil.copy2(module, variants / module.name)
    shutil.copy2(rules, variants / rules.name)
    for helper in helpers(module):
        source = HERE / f"{helper}.py"
        source = source if source.is_file() else KIT / VARIANTS / f"{helper}.py"
        shutil.copy2(source, variants / f"{helper}.py")
    shutil.copy2(rules, out / "RULES.md")
    patch_history(out, variant)
    for name in ("CASES.md", "coverage.json"):  # Bay Area's case index for its own sample.
        (out / "hand-history" / name).unlink(missing_ok=True)
    patch_readme(out, variant)
    # The sample is played by the kit's own engine, in a child process using the kit's sources.
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--sample", variant, str(out)],
        check=True,
        env=kit_env(out),
        cwd=out,
    )
    print(f"Mock kit for {variant} written to {out}")
    print(f"Use it: PYTHONPATH={kit_env(out)['PYTHONPATH']} {sys.executable} -m poker_agent_sdk.cli play ...")


# A scripted bot for the sample: random legal play, varied variant choices, and an occasional
# invalid choice so the sample shows automatic fallbacks. Not shipped in the kit.
SAMPLE_BOT = '''
import random
import poker_agent_sdk
from poker_agent_sdk import Action, GameState


class Agent(poker_agent_sdk.Agent):
    def act(self, state: GameState, memory: bytes) -> tuple[Action, bytes]:
        rng = random.Random(f"{state.config.table_id}:{state.hand_number}:{state.seat}:{len(state.history)}")
        if state.phase == "auction":
            if rng.random() < 0.04:
                return Action("bid", cards=(state.variant["flop_chips"] + 1, 0, 0, 0, 0)), memory
            bids = [0] * 5
            for _ in range(rng.randint(0, min(60, state.variant["flop_chips"]))):
                bids[rng.randrange(5)] += 1
            return Action("bid", cards=tuple(bids)), memory
        if state.phase == "draw":
            if rng.random() < 0.04:
                return Action("draw", cards=(2,)), memory
            return Action("draw", cards=rng.choice([(), (0,), (1,)])), memory
        if state.phase == "pass":
            if rng.random() < 0.04:
                return Action("pass", cards=(0, 1)), memory
            return Action("pass", cards=(rng.randrange(2),)), memory
        if state.phase != "betting":
            first = state.legal_actions[0]
            return Action(first.kind, first.min_amount), memory
        if (r := state.can("raise")) and rng.random() < 0.2:
            return Action.raise_to(r.max_amount if rng.random() < 0.15 else r.min_amount), memory
        if state.can("call") and rng.random() < 0.6:
            return Action.call(), memory
        return (Action.check() if state.can("check") else Action.fold()), memory
'''


def sample(variant: str, kit: Path) -> None:
    """Play the sample's tables on the kit's engine and write hand-history/sample.jsonl(.gz)."""
    import asyncio

    from poker_agent_protocol.process import BotPool
    from poker_agent_sdk.history import encoded
    from poker_agent_sdk.local_history import HistoryIndex
    from poker_engine.history import private_view, public_view
    from poker_engine.play import play_table
    from poker_engine.table import SitAndGo, TableRules
    from poker_engine.variant import installed_variants, load_variant

    assert installed_variants() == [variant], installed_variants()
    import poker_engine

    assert Path(poker_engine.__file__).resolve().is_relative_to(kit.resolve()), poker_engine.__file__
    ids = [f"00000000-0000-0000-0000-{n:012d}" for n in range(1, 9)]
    header = {
        "tournament_id": "00000000-0000-0000-0000-000000000064",
        "you": ids[0],
        "entries": [
            {"entry_id": entry, "team_name": f"Sample Team {chr(65 + n)}"}
            for n, entry in enumerate(ids)
        ],
    }
    # (players, hand cap, filler seats): full tables, short ones, heads-up, and fillers.
    layouts = [(8, 60, 0), (8, 60, 0), (6, 60, 0), (8, 40, 2), (3, 60, 0), (2, 80, 0), (8, 250, 0)]
    with tempfile.TemporaryDirectory() as scratch:
        bot = Path(scratch) / "sample_bot"
        bot.mkdir()
        (bot / "agent.py").write_text(SAMPLE_BOT)
        paths = {
            "sample": bot,
            "check_or_fold": kit / "examples/check_or_fold",
            "min_raiser": kit / "examples/min_raiser",
        }

        async def play() -> list[bytes]:
            pools = {
                name: BotPool([sys.executable, "-m", "poker_agent_sdk.guest", str(path)],
                              copies=2, cwd=str(path))
                for name, path in paths.items()
            }
            rng = random.Random(f"sample:{variant}")
            members = []
            try:
                for number, (players, cap, fillers) in enumerate(layouts):
                    seats = [ids[0], *rng.sample(ids[1:], players - 1)]
                    rng.shuffle(seats)
                    kinds = [rng.choice(["sample", "sample", "check_or_fold", "min_raiser"])
                             for _ in seats]
                    kinds[seats.index(ids[0])] = "sample"
                    rules = TableRules(variant=variant, players=players, hand_cap=cap)
                    table = SitAndGo(rules=rules, variant=load_variant(variant),
                                     table_id=f"sample-{number}", seed=f"sample:{variant}:{number}")
                    await play_table(table, [pools[kind] for kind in kinds])
                    flags = [False] * players
                    for seat in rng.sample([s for s in range(players) if seats[s] != ids[0]], fillers):
                        flags[seat] = True
                    raw = {"variant": variant, "iteration": 0, "table": number, "seats": seats,
                           "fillers": flags, "payouts": list(table.payouts), "hands": table.log}
                    you = seats.index(ids[0])
                    members.append(encoded(public_view(raw)) + encoded(private_view(raw, you)))
            finally:
                for pool in pools.values():
                    await pool.stop()
            return members

        members = asyncio.run(play())
    folder = kit / "hand-history"
    lines = [encoded(header), *members]
    (folder / "sample.jsonl").write_bytes(b"".join(lines))
    (folder / "sample.jsonl.gz").write_bytes(
        b"".join(gzip.compress(line, compresslevel=6, mtime=0) for line in lines)
    )
    with HistoryIndex(folder / "sample.jsonl.gz") as index:  # The kit's own validator.
        tables = len(index.tables)
    print(f"sample: {tables} tables, validated by the kit's validator")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("variant")
    parser.add_argument("out", type=Path)
    parser.add_argument("--force", action="store_true", help="replace an existing out_dir")
    parser.add_argument("--sample", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.sample:
        sample(args.variant, args.out)
    else:
        build(args.variant, args.out.resolve(), args.force)


if __name__ == "__main__":
    main()
