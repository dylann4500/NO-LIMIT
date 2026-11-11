"""Pre-submit gate: import time, first-call latency, fuzz legality, latency tail, and score parity.
usage: test_bot.py path/to/bot_dir"""
import importlib, random, sys, time, math
sys.path.insert(0, __file__.rsplit("/", 1)[0])
sys.path.append(__file__.rsplit("/", 1)[0] + "/fake_sdk")  # the adapter imports poker_agent_sdk; the kit's real one wins if installed
pc = time.perf_counter
t = pc()
sys.path.insert(0, sys.argv[1])
bot = importlib.import_module("bot")
print(f"import: {(pc()-t)*1e3:.1f} ms; variant {bot.VARIANT}")
import os
os.environ["POKER_VARIANT"] = bot.VARIANT  # the engine and opponents must play the same game as the bot
from engine import Obs, play_table, points_for
from field import ARCHETYPES, FIELDS
from run import PAYOUTS

class G:
    lat = []
    def __init__(self):
        self.p = bot.Policy()
    def act(self, o):
        t = pc()
        r = self.p.safe_decide(o)
        G.lat.append(pc() - t)
        return r
    def observe(self, seat, street, kind, amount):
        self.p.observe(seat, street, kind)
    def end_hand(self, n):
        self.p.end_hand()

# First decision after import, in a fresh policy.
o = Obs()
o.seat, o.hole, o.board, o.street, o.pot, o.to_call = 0, bot.DECK[-bot.N_HOLE:], [], 0, 30, 20
o.min_raise_to, o.max_raise_to, o.can_raise, o.stack, o.bet, o.cur, o.sb, o.bb = 40, 2000, True, 2000, 0, 20, 10, 20
o.stacks, o.bets, o.in_hand, o.n_alive, o.n_live, o.n_behind, o.raises, o.aggressor, o.n_callers = [2000]*8, [0]*8, [True]*8, 8, 8, 7, 0, -1, 0
t = pc(); r = bot.Policy().safe_decide(o); print(f"first decision: {(pc()-t)*1e6:.0f} us -> {r}")

# Fuzz: random and hostile states, including impossible ones. Must be legal and must not raise.
bad = 0
N = 200000
for i in range(N):
    n = random.randint(2, 8)
    st = [random.choice([0, 1, 5, 20, random.randint(0, 16000)]) for _ in range(8)]
    o.seat = random.randrange(8)
    st[o.seat] = random.choice([1, 5, 40, random.randint(1, 16000)])
    deck = random.sample(bot.DECK, 5 + bot.N_HOLE)
    o.hole = deck[:bot.N_HOLE]
    o.street = random.randrange(4)
    o.board = deck[bot.N_HOLE : bot.N_HOLE + [0, 3, 4, 5][o.street]]
    o.stack = st[o.seat]
    o.stacks = st
    o.bets = [random.choice([0, 0, 20, random.randint(0, 4000)]) for _ in range(8)]
    o.bet = o.bets[o.seat]
    o.in_hand = [random.random() < 0.6 for _ in range(8)]
    o.in_hand[o.seat] = True
    o.pot = random.choice([0, 1, 30, random.randint(0, 16000)])
    o.to_call = random.choice([0, 0, 1, random.randint(0, o.stack)])
    o.cur = o.bet + o.to_call
    o.max_raise_to = o.bet + o.stack
    o.min_raise_to = min(o.cur + random.choice([20, 40, 500]), o.max_raise_to)
    o.can_raise = o.stack > o.to_call and random.random() < 0.8
    o.sb, o.bb = random.choice([(10, 20), (250, 500), (1280, 2560)])
    o.n_alive, o.n_live, o.n_behind = n, random.randint(2, n), random.randint(0, n - 1)
    o.raises, o.n_callers = random.randint(0, 4), random.randint(0, 5)
    o.aggressor = random.choice([-1, random.randrange(8)])
    p = bot.Policy()
    # Force the crash path sometimes by sending garbage in a field.
    if i % 1000 == 0:
        o.hole = None
    k, a = p.safe_decide(o)
    ok = k in (0, 1, 2) and (k != 2 or (o.can_raise and o.min_raise_to <= a <= o.max_raise_to)) and not (k == 0 and o.to_call == 0 and o.hole is not None)
    bad += not ok
print(f"fuzz: {N} states, {bad} illegal or malformed")

# Real game parity and latency.
G.lat = []
pay = list(bot.PAYOUTS)
names = list(FIELDS["typical"]); w = [FIELDS["typical"][k] for k in names]
s = s2 = 0.0
T = 1500
for _ in range(T):
    pos = random.randrange(8)
    bots = [ARCHETYPES[x]() for x in random.choices(names, w, k=7)]
    bots.insert(pos, G())
    e, nh, surv = play_table(bots)
    v = points_for(e, surv, pay)[pos]
    s += v; s2 += v * v
m = s / T
print(f"score vs typical on bot's points table: {m:.2f} ± {math.sqrt((s2/T-m*m)/T):.2f} (fair {sum(pay)/8:.2f})")
L = sorted(G.lat); n = len(L)
q = lambda p: L[min(n - 1, int(p * n))] * 1e6
print(f"latency n={n} p50={q(.5):.1f} p99={q(.99):.1f} p99.9={q(.999):.1f} p99.99={q(.9999):.1f} max={L[-1]*1e6:.1f} us, over 1 ms: {sum(1 for x in L if x > 1e-3)}, over 500 us: {sum(1 for x in L if x > 5e-4)}")
