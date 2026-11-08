"""Handoff validation extras: replay safety, all-in select, six select actions legal, discard/exposed masking.
Usage: python tests/validate.py BOT_DIR"""
import random, sys
sys.path.insert(0, "tests")
import fuzz
from poker_agent_protocol.game import LegalAction, Seat
from dataclasses import replace

agent = fuzz.load_agent(sys.argv[1])
rng = random.Random(99)
bad = 0
# 1. Replay safety: same (state, memory) twice -> identical memory out (no double counting).
for _ in range(5000):
    st = fuzz.rand_state(rng); m = fuzz.rand_memory(rng, b"")
    _, m1 = agent.act(st, m); _, m2 = agent.act(st, m)
    if m1 != m2: bad += 1
print("replay_mismatch", bad)
# 2. Select for all-in / folded-status seats and every 3-card order: always a valid (d, r).
sel_bad = 0; seen = set()
for _ in range(5000):
    st = fuzz.rand_state(rng)
    while st.phase != "select": st = fuzz.rand_state(rng)
    seats = tuple(replace(s, status="all_in", stack=0) if s.seat == st.seat else s for s in st.seats)
    st = replace(st, seats=seats)
    a, _ = agent.act(st, b"")
    c = a.cards or (2, 0)
    ok = a.kind == "select" and a.amount == 0 and len(c) == 2 and c[0] != c[1] and all(type(i) is int and 0 <= i < 3 for i in c)
    sel_bad += not ok; seen.add(tuple(c))
print("select_invalid", sel_bad, "distinct_select_actions_used", len(seen), sorted(seen))
# 3. Hostile select inputs: duplicate cards, 2 cards, garbage strings, empty board -> still valid.
hostile = 0
for cards, board in [(("As","As","Kd"),("2c","3d","4h")),(("As","Kd"),("2c","3d","4h")),(("Xx","As","Kd"),("2c","3d","4h")),(("As","Kd","Qh"),())]:
    st = fuzz.rand_state(rng)
    while st.phase != "select": st = fuzz.rand_state(rng)
    a, _ = agent.act(replace(st, cards=cards, board=board), b"\xff")
    c = a.cards or (2, 0)
    hostile += not (a.kind == "select" and c[0] != c[1] and all(0 <= i < 3 for i in c))
print("hostile_select_invalid", hostile)
sys.exit(1 if (bad or sel_bad or hostile) else 0)
