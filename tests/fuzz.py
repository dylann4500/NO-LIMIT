"""Legality / robustness / latency fuzz for a bot's act() (05_TESTS.md test 2, plus latency).

Usage: python tests/fuzz.py BOT_DIR [N]
Builds random and hostile GameStates (2-10 players, select + betting phases, odd stacks,
garbage memory, cut memory) and checks every return is legal, act never raises, memory
stays < 16 KB. Reports act() latency percentiles (laptop numbers, not the build box).
"""

import gc
import importlib.util
import random
import sys
import time

from poker_agent_protocol.game import (
    Action, BlindLevel, Event, GameState, LegalAction, Seat, TableConfig, is_legal,
)

RANKS = "23456789TJQKA"
DECK = [r + s for r in RANKS for s in "shdc"]
BLINDS = tuple(BlindLevel(sb, 2 * sb) for sb in (10, 20, 30, 50, 80, 125, 200, 300, 500, 800, 1200, 2000))


def load_agent(bot_dir: str):
    spec = importlib.util.spec_from_file_location("bot_agent", f"{bot_dir}/agent.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, bot_dir)
    spec.loader.exec_module(mod)
    return mod.Agent()


def rand_state(rng: random.Random) -> GameState:
    n = rng.randint(2, 10)
    me = rng.randrange(n)
    deck = DECK[:]
    rng.shuffle(deck)
    street = rng.choice(["pre", "select", "flop", "turn", "river"])
    board = {"pre": 0, "select": 3, "flop": 3, "turn": 4, "river": 5}[street]
    board_cards = tuple(deck[:board])
    hole_n = 3 if street in ("pre", "select") else 2
    cards = tuple(deck[board:board + hole_n])
    used = board + hole_n
    level = rng.randrange(len(BLINDS))
    bl = BLINDS[level]
    seats = []
    for i in range(n):
        status = rng.choice(["active"] * 6 + ["folded", "all_in", "busted"])
        if i == me:
            status = rng.choice(["active"] * 8 + ["all_in"])
        stack = 0 if status in ("all_in", "busted") else rng.choice(
            [rng.randint(1, 50), rng.randint(1, 20000), rng.randint(100, 3000)])
        bet = rng.choice([0, 0, bl.big_blind, rng.randint(0, 5000)])
        shown = ()
        if street in ("flop", "turn", "river") and status != "busted" and rng.random() < 0.9:
            shown = (deck[used],)
            used += 1
        seats.append(Seat(i, stack, bet, status, shown))
    if street == "select":
        legal = (LegalAction("select"),)
        phase = "select"
        to_call = 0
    else:
        phase = "betting"
        kinds = []
        to_call = rng.choice([0, 0, bl.big_blind, rng.randint(1, 6000)])
        if to_call == 0:
            kinds.append(LegalAction("check"))
        else:
            kinds.append(LegalAction("fold"))
            kinds.append(LegalAction("call"))
        if rng.random() < 0.8:
            lo = rng.randint(1, 4000)
            hi = lo + rng.choice([0, rng.randint(0, 20000)])
            kinds.append(LegalAction("raise", lo, hi))
        if rng.random() < 0.05 and to_call:
            kinds = [LegalAction("call")]  # all-in-ish: only call
        legal = tuple(kinds)
    cfg = TableConfig(
        table_id="fuzz", seat=me, players=n, variant="flop_discard_reveal", starting_stack=2000,
        blinds=BLINDS, hands_per_level=rng.choice([20, 25]), hand_cap=rng.choice([200, 250]),
        payouts=rng.choice([(50, 30, 20), (60, 25, 15), (40, 35, 25)]), decision_ms=1,
        memory_bytes=65536, time_bank_ms=0,
    )
    events = []
    for _ in range(rng.randint(0, 30)):
        k = rng.choice(["hand", "blind", "fold", "check", "call", "raise", "board", "select",
                        "reveal", "show", "win", "stack", "weird_kind"])
        seat = None if k in ("hand", "board") else rng.randrange(n)
        ev_cards = tuple(rng.sample(DECK, rng.choice([0, 1, 2]))) if k in ("reveal", "show", "board") else ()
        events.append(Event(k, seat, rng.randint(0, 5000), ev_cards))
    events = tuple(events)
    pot = sum(s.bet for s in seats) + rng.randint(0, 20000)
    variant = {"discarded": [deck[used]]} if street in ("flop", "turn", "river") else {"discarded": []}
    return GameState(
        events=events, hand_number=rng.randint(1, 250), seat=me, cards=cards, board=board_cards,
        pot=pot, to_call=to_call, legal_actions=legal, history=events[-10:], seats=tuple(seats),
        button=rng.randrange(n), blind_level=level, blinds=bl,
        hands_until_next_level=rng.randint(1, 25), players_remaining=n, bust_order=(),
        config=cfg, variant=variant, phase=phase, time_bank_ms=0.0,
    )


def rand_memory(rng: random.Random, last: bytes) -> bytes:
    r = rng.random()
    if r < 0.6:
        return last
    if r < 0.7:
        return b""
    if r < 0.8:
        return last[: rng.randint(0, max(0, len(last)))]  # cut memory
    if r < 0.9:
        return bytes(rng.randrange(256) for _ in range(rng.randint(1, 64)))  # garbage
    return rng.choice([b"[]", b"null", b'"x"', b"{\"a\":", b"\xff\xfe", b"{}", b"1e999"])


def legal_select(a: Action) -> bool:
    if a.kind != "select" or a.amount:
        return False
    c = a.cards or (2, 0)
    return (len(c) == 2 and all(type(i) is int and 0 <= i < 3 for i in c) and c[0] != c[1])


def main() -> None:
    bot = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100_000
    agent = load_agent(bot)
    rng = random.Random(12345)
    bad = 0
    raised = 0
    mem_max = 0
    lat = []
    mem = b""
    sel = 0
    worst = (0, -1, None, b"")
    for i in range(n):
        st = rand_state(rng)
        mem = rand_memory(rng, mem)
        t0 = time.perf_counter_ns()
        try:
            action, mem_out = agent.act(st, mem)
        except Exception as e:  # noqa: BLE001
            raised += 1
            if raised <= 3:
                print("RAISED:", repr(e))
            continue
        lat.append(time.perf_counter_ns() - t0)
        if lat[-1] > worst[0]:
            worst = (lat[-1], i, st, mem)
        if not isinstance(mem_out, (bytes, bytearray)):
            bad += 1
            continue
        mem_max = max(mem_max, len(mem_out))
        mem = bytes(mem_out)
        if st.phase == "select":
            sel += 1
            ok = legal_select(action)
        else:
            ok = is_legal(action, st.legal_actions) and type(action.amount) is int
        if not ok:
            bad += 1
            if bad <= 5:
                print("ILLEGAL:", action, st.phase, st.legal_actions)
    lat.sort()
    q = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))] / 1000  # noqa: E731
    print(f"fuzz n={n} select_states={sel} illegal={bad} raised={raised} mem_max={mem_max}B")
    print(f"latency_us p50={q(.5):.1f} p99={q(.99):.1f} p999={q(.999):.1f} max={lat[-1]/1000:.1f}")
    if worst[2] is not None:  # replay the slowest state: reproducible slowness vs OS jitter
        rr = []
        for _ in range(30):
            t0 = time.perf_counter_ns(); agent.act(worst[2], worst[3]); rr.append((time.perf_counter_ns() - t0) / 1000)
        rr.sort()
        print(f"worst i={worst[1]} phase={worst[2].phase} board={len(worst[2].board)} took {worst[0]/1000:.0f} us; "
              f"replay x30 median {rr[15]:.0f} us max {rr[-1]:.0f} us")
    sys.exit(1 if (bad or raised or mem_max >= 16384) else 0)


if __name__ == "__main__":
    main()
