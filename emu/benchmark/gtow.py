"""Benchmark a kit-API bot (agent.py with Agent.act(state, memory)) against GTO Wizard AI.

GTO Wizard's Researcher API plays heads-up no-limit hold'em, 50/100 blinds, 200 bb deep, stacks
reset every hand, scored with AIVAT (luck-adjusted). This adapter turns each API state into the
starter kit's GameState, asks the bot, and sends its action back, so any hold'em bot written for
the kit plays unchanged. Bots for non-hold'em variants (3 hole cards, auctions) cannot play here.

RESULTS ARE PUBLIC: every hand counts toward the key's leaderboard entry ("Avalon / Stanford
University"). Team decision (2026-11-11): benchmark only avalon's own serious bots with this key.

Quota: 10,000 hands/day, 25,000/week, 50,000/month per user; at most 20 hands at once.
Key: GTOW_API_KEY in ~/.config/gtow.env (chmod 600), never in the repo.

  starter-kit/.venv/bin/python emu/benchmark/gtow.py play bots/<bot> --hands 500 --out emu/runs/gtow/<name>.jsonl
  starter-kit/.venv/bin/python emu/benchmark/gtow.py summary emu/runs/gtow/<name>.jsonl
  starter-kit/.venv/bin/python emu/benchmark/gtow.py selftest bots/<bot>   # offline, no API calls
"""

import argparse
import importlib.util
import json
import math
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from poker_agent_protocol.game import Action, BlindLevel, Event, GameState, LegalAction, Seat, TableConfig

API = "https://researcher.gtowizard.com"
GAME = "HUNL 200BB"
SB, BB, STACK = 50, 100, 20000
USER_AGENT = "nolimit-benchmark-client/0.1"  # the API's firewall rejects Python's default agent


def api_key() -> str:
    if os.environ.get("GTOW_API_KEY"):
        return os.environ["GTOW_API_KEY"].strip()
    for line in open(os.path.expanduser("~/.config/gtow.env")):
        if line.startswith("GTOW_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("No GTOW_API_KEY in the environment or ~/.config/gtow.env")


class Client:
    def __init__(self, key: str):
        self.h = {"X-API-Key": key, "Content-Type": "application/json", "User-Agent": USER_AGENT}

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        for attempt in range(8):
            req = urllib.request.Request(API + path, method=method, headers=self.h,
                                         data=json.dumps(body).encode() if body is not None else None)
            try:
                return json.load(urllib.request.urlopen(req, timeout=180))
            except urllib.error.HTTPError as e:
                if e.code in (502, 503, 504) and attempt < 7:  # engine busy: back off, as the official client does
                    time.sleep(min(32, 2 ** (attempt + 1)))
                    continue
                raise RuntimeError(f"{method} {path}: HTTP {e.code} {e.read()[:300]!r}") from None
        raise RuntimeError("unreachable")


# ---------------------------------------------------------------- translation
def split_board(board: str) -> list[str]:
    return [board[i:i + 2] for i in range(0, len(board or ""), 2)]


def rebuild(gs: dict, hero: int, button: int) -> dict:
    """Replay GTO Wizard's action history into kit-style facts. Seats: 0 = hero, 1 = GTO Wizard.
    Heads-up: the button posts the small blind and acts first preflop; the big blind acts first after."""
    other = 1 - hero
    bb_seat = 1 - button
    events = [Event("hand", None, 1), Event("blind", button, SB), Event("blind", bb_seat, BB)]
    committed = {button: SB, bb_seat: BB}
    bets = {button: SB, bb_seat: BB}
    folded = set()
    street = 0
    order = [button, bb_seat]  # preflop order
    turn = 0
    board = split_board(gs["board_cards"])
    for tok in gs["action_history"]:
        if tok == "_":
            street += 1
            bets = {0: 0, 1: 0}
            order = [bb_seat, button]
            turn = 0
            cards = board[:3] if street == 1 else board[2 + street - 1:2 + street] if street <= 3 else []
            if cards:
                events.append(Event("board", None, 0, tuple(cards)))
            continue
        seat = order[turn % 2]
        turn += 1
        if tok == "f":
            folded.add(seat)
            events.append(Event("fold", seat))
        elif tok == "k":
            events.append(Event("check", seat))
        elif tok == "c":
            add = max(bets.values()) - bets[seat]
            bets[seat] += add
            committed[seat] += add
            events.append(Event("call", seat, add))
        elif tok.startswith("b"):
            total = int(float(tok[1:]))
            committed[seat] += total - bets[seat]
            bets[seat] = total
            events.append(Event("raise", seat, total))
        else:
            raise ValueError(f"unknown action token {tok!r}")
    actor = order[turn % 2]
    return {"events": events, "committed": committed, "bets": bets, "folded": folded, "actor": actor,
            "pot": sum(committed.values()), "board": board, "other": other}


def to_state(resp: dict, hand_no: int, memory_events_seen: int) -> tuple[GameState, int]:
    gs = resp["game_state"]
    players = gs["players"]
    hero = next(i for i, p in enumerate(players) if p.get("hole_cards"))
    pos = [str(p.get("position", "")).upper() for p in players]
    button = next((i for i, p in enumerate(pos) if p in ("SB", "BTN", "BU", "BUTTON", "SB/BTN")), None)
    if button is None:
        raise ValueError(f"cannot tell the button from positions {pos}")
    f = rebuild(gs, hero, button)
    if abs(f["pot"] - float(gs["total_pot"])) > 1:  # the consistency guard
        raise ValueError(f"pot mismatch: rebuilt {f['pot']} vs API total_pot {gs['total_pot']} "
                         f"(history {gs['action_history']}, positions {pos})")
    to_call = max(f["bets"].values()) - f["bets"][hero]
    legal = []
    for a in gs["legal_actions"]:
        if a == "f":
            legal.append(LegalAction("fold"))
        elif a == "k":
            legal.append(LegalAction("check"))
        elif a == "c":
            legal.append(LegalAction("call", int(to_call), int(to_call)))
        elif a == "b" and gs.get("raise_range"):
            legal.append(LegalAction("raise", int(math.ceil(gs["raise_range"]["min"])),
                                     int(gs["raise_range"]["max"])))
    seats = tuple(Seat(s, int(STACK - f["committed"][s]), int(f["bets"][s]),
                       "folded" if s in f["folded"] else ("all_in" if STACK - f["committed"][s] <= 0 else "active"))
                  for s in (0, 1))
    blinds = BlindLevel(SB, BB)
    cfg = TableConfig("gtow", 0, 2, "no_limit_holdem", STACK, (blinds,), 10 ** 6, 10 ** 6, (100,), 1000, 65536, 1000)
    hist = tuple(f["events"])
    state = GameState(
        events=hist[memory_events_seen:], hand_number=hand_no, seat=0,
        cards=tuple(split_board(players[hero]["hole_cards"])), board=tuple(f["board"]), pot=int(f["pot"]),
        to_call=int(to_call), legal_actions=tuple(legal), history=hist[1:], seats=seats,
        button=0 if button == hero else 1, blind_level=1, blinds=blinds, hands_until_next_level=10 ** 6,
        players_remaining=2, bust_order=(), config=cfg, variant={}, phase="betting", time_bank_ms=1000.0)
    return state, len(hist)


def to_request(action: Action, gs: dict) -> dict:
    la = gs["legal_actions"]
    if action.kind == "raise" and "b" in la:
        rr = gs["raise_range"]
        return {"action": "b", "amount": int(max(rr["min"], min(rr["max"], int(action.amount))))}
    if action.kind in ("call", "raise") and "c" in la:
        return {"action": "c"}
    if action.kind in ("check", "call", "fold") and "k" in la:
        return {"action": "k"}
    if action.kind == "fold" and "f" in la:
        return {"action": "f"}
    return {"action": "k"} if "k" in la else ({"action": "c"} if "c" in la else {"action": "f"})


# ---------------------------------------------------------------- bot loading and play
def load_agent(bot_dir: str):
    path = Path(bot_dir).resolve() / "agent.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(f"bot_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Agent


def play_hand(client: Client, AgentCls, hand_no: int, lock: threading.Lock, out) -> dict:
    agent = AgentCls()
    memory, seen = b"", 0
    resp = client.call("POST", "/hands", {"game_name": GAME})
    hid = resp["hand_id"]
    actions = []
    while not resp["game_state"]["is_hand_over"]:
        gs = resp["game_state"]
        state, seen_now = to_state(resp, hand_no, seen)
        try:
            action, memory = agent.act(state, memory)
            seen = seen_now
        except Exception as e:  # noqa: BLE001 - a crashing bot plays the passive action, as on the platform
            action = Action.check() if "k" in gs["legal_actions"] else Action.fold()
            actions.append(f"(bot raised {type(e).__name__})")
        req = to_request(action, gs)
        actions.append(req)
        resp = client.call("POST", f"/hands/{hid}/act", req)
    gs = resp["game_state"]
    rec = {"hand_id": hid, "winnings": gs["winnings"], "aivat": gs["aivat_score"], "actions": actions,
           "history": gs["action_history"], "board": gs["board_cards"]}
    with lock:
        out.write(json.dumps(rec) + "\n")
        out.flush()
    return rec


def summary(path: str) -> str:
    recs = [json.loads(l) for l in open(path)]
    n = len(recs)
    if not n:
        return "no hands"
    def stat(key):
        xs = [r[key] / BB * 100 for r in recs if r[key] is not None]  # bb/100 per hand
        m = sum(xs) / len(xs)
        sd = (sum((x - m) ** 2 for x in xs) / max(1, len(xs) - 1)) ** 0.5
        return m, 1.96 * sd / len(xs) ** 0.5
    w, wci = stat("winnings")
    a, aci = stat("aivat")
    return (f"{n} hands | AIVAT {a:+.1f} ± {aci:.1f} bb/100 (luck-adjusted) | raw {w:+.1f} ± {wci:.1f} bb/100 | "
            f"bot errors {sum(any(isinstance(x, str) for x in r['actions']) for r in recs)}")


def selftest(bot_dir: str, n: int = 2000) -> None:
    """Offline: random but legal GTO Wizard-shaped states through the translation and the bot."""
    AgentCls = load_agent(bot_dir)
    rng = random.Random(7)
    deck = [r + s for r in "23456789TJQKA" for s in "shdc"]
    bad = 0
    for i in range(n):
        rng.shuffle(deck)
        hero_btn = rng.random() < 0.5
        hist, bets, street = [], {0: SB, 1: BB}, 0  # seat 0 = button
        pot = SB + BB
        for _ in range(rng.randint(0, 6)):
            if rng.random() < 0.3 and len([h for h in hist if h == "_"]) < 3:
                hist.append("_"); street += 1; bets = {0: 0, 1: 0}
                continue
            hist.append(rng.choice(["k", "c", f"b{max(bets.values()) + BB * rng.randint(1, 5)}"]))
        board = "".join(deck[2:2 + [0, 3, 4, 5][min(3, hist.count("_"))]])
        try:
            players = [{"name": "hero", "stack": 0, "position": "SB" if hero_btn else "BB", "hole_cards": deck[0] + deck[1]},
                       {"name": "GTO Wizard", "stack": 0, "position": "BB" if hero_btn else "SB", "hole_cards": None}]
            f = rebuild({"action_history": hist, "board_cards": board}, 0, 0 if hero_btn else 1)
        except ValueError:
            continue
        resp = {"game_state": {"players": players, "action_history": hist, "board_cards": board,
                               "total_pot": f["pot"], "legal_actions": ["f", "c", "b"],
                               "raise_range": {"min": max(f["bets"].values()) + BB, "max": STACK}, "is_hand_over": False}}
        try:
            state, _ = to_state(resp, i, 0)
            action, _ = AgentCls().act(state, b"")
            to_request(action, resp["game_state"])
        except Exception as e:  # noqa: BLE001
            bad += 1
            if bad <= 3:
                print("error:", type(e).__name__, e, hist)
    print(f"selftest: {n} states, {bad} errors")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    pl = sub.add_parser("play")
    pl.add_argument("bot")
    pl.add_argument("--hands", type=int, default=100)
    pl.add_argument("--concurrency", type=int, default=5)
    pl.add_argument("--out", required=True)
    pl.add_argument("--yes-public", action="store_true", help="confirm: these hands count on the public leaderboard")
    sm = sub.add_parser("summary")
    sm.add_argument("file")
    st = sub.add_parser("selftest")
    st.add_argument("bot")
    a = p.parse_args()
    if a.cmd == "play":
        if not a.yes_public:
            raise SystemExit("These hands count on Avalon's PUBLIC leaderboard entry. Re-run with --yes-public.")
        client, AgentCls, lock = Client(api_key()), load_agent(a.bot), threading.Lock()
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        with open(a.out, "a") as out, ThreadPoolExecutor(min(a.concurrency, 20)) as pool:
            futures = [pool.submit(play_hand, client, AgentCls, i + 1, lock, out) for i in range(a.hands)]
            for i, fut in enumerate(futures, 1):
                try:
                    fut.result()
                except ValueError as e:  # translation guard tripped: stop before more public hands
                    print(f"STOPPED: {e}")
                    for f2 in futures:
                        f2.cancel()
                    break
                if i % 50 == 0:
                    print(summary(a.out), flush=True)
        print(summary(a.out))
    elif a.cmd == "summary":
        print(summary(a.file))
    elif a.cmd == "selftest":
        selftest(a.bot)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
