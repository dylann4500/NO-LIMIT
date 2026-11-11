"""Validates what the experiments rest on, using checks independent of the code under test."""
import random, sys
from itertools import combinations
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import pk, engine
from pk import evaluate, icm
from engine import play_table, points_for
from field import ARCHETYPES
from hero import Hero

fails = 0
def check(name, ok, detail=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name, detail)
    fails += not ok

# 1. Independent naive five-card evaluator, written differently: tuple of category then tiebreak ranks.
def naive5(cs):
    r = sorted((c >> 2 for c in cs), reverse=True)
    fl = len({c & 3 for c in cs}) == 1
    cnt = {x: r.count(x) for x in set(r)}
    by = sorted(cnt, key=lambda x: (-cnt[x], -x))
    shape = sorted(cnt.values(), reverse=True)
    st = -1
    if len(cnt) == 5:
        if r[0] - r[4] == 4:
            st = r[0]
        elif r == [12, 3, 2, 1, 0]:
            st = 3
    if st >= 0 and fl: return (8, st)
    if shape == [4, 1]: return (7, *by)
    if shape == [3, 2]: return (6, *by)
    if fl: return (5, *r)
    if st >= 0: return (4, st)
    if shape == [3, 1, 1]: return (3, *by)
    if shape == [2, 2, 1]: return (2, *by)
    if shape == [2, 1, 1, 1]: return (1, *by)
    return (0, *r)

def naive7(cs):
    return max(naive5(c) for c in combinations(cs, 5))

random.seed(3)
bad = 0
N = 60000
for _ in range(N):
    s = random.sample(range(52), 14)
    a, b = s[:7], s[7:]
    fa, fb = evaluate(a), evaluate(b)
    na, nb = naive7(a), naive7(b)
    if (fa > fb) != (na > nb) or (fa == fb) != (na == nb):
        bad += 1
check(f"7-card ordering agrees with naive evaluator on {N} random pairs", bad == 0, f"mismatches={bad}")
# Boards that force ties and shared hands.
bad = 0
for _ in range(20000):
    s = random.sample(range(52), 9)
    board = s[:5]
    a, b = s[5:7] + board, s[7:9] + board
    if (evaluate(a) > evaluate(b)) != (naive7(a) > naive7(b)) or (evaluate(a) == evaluate(b)) != (naive7(a) == naive7(b)):
        bad += 1
check("same-board comparisons, including chops, agree", bad == 0, f"mismatches={bad}")

# 2. Category frequency for 7 cards against published exact counts of 133,784,560 hands.
EXACT = {8: 41584, 7: 224848, 6: 3473184, 5: 4047644, 4: 6180020, 3: 6461620, 2: 31433400, 1: 58627800, 0: 23294460}
T = 400000
c = {k: 0 for k in EXACT}
for _ in range(T):
    c[evaluate(random.sample(range(52), 7)) >> 20] += 1
ok = True
for k, v in EXACT.items():
    p = v / 133784560
    se = (p * (1 - p) / T) ** 0.5
    if abs(c[k] / T - p) > 4.5 * se:
        ok = False
        print("   category", k, c[k] / T, p)
check("7-card category frequencies match exact counts", ok)

# 3. Known preflop equities.
aa = pk.hu_eq([48, 49])
check("AA vs random about 85.2%", abs(aa - 0.852) < 0.02, f"{aa:.3f}")
# 4. ICM against brute force over finishing orders.
from itertools import permutations
def brute(st, pay):
    n = len(st); out = [0.0] * n
    for perm in permutations(range(n)):
        p = 1.0; rem = float(sum(st))
        for i in perm:
            p *= st[i] / rem; rem -= st[i]
        for place, i in enumerate(perm):
            out[i] += p * (pay[place] if place < len(pay) else 0)
    return out
ok = True
for _ in range(50):
    n = random.randint(2, 5)
    st = [random.randint(1, 5000) for _ in range(n)]
    pay = sorted((random.randint(0, 100) for _ in range(n)), reverse=True)
    a, b = icm(st, pay), brute(st, pay)
    ok &= all(abs(x - y) < 1e-6 for x, y in zip(a, b))
check("ICM matches brute force", ok)

# 5. Hand-worked side pot. A 100, B 300, C 300 all-in; A has the best hand, B beats C.
class Script:
    def __init__(self, a): self.a = a
    def act(self, o): return self.a(o)
def jam(o): return (2, o.max_raise_to) if o.can_raise else (1, 0)
orig = engine.START
# Run the same settlement rule through the engine with rigged cards.
class RigRng:
    def __init__(self, cards, btn=0): self.cards, self.btn = cards, btn
    def randrange(self, n): return n - 1  # button moves to seat 0 first
    def sample(self, deck, k): return self.cards[:k]
sp = lambda s: ['23456789TJQKA'.index(s[i]) * 4 + 'shdc'.index(s[i + 1]) for i in range(0, len(s), 2)]

def one_hand(stacks, cards, sb=10, bb=20):
    """Single rigged hand using the engine's table loop with chosen starting stacks."""
    n = len(stacks)
    res = {}
    class B:
        def __init__(s, i): s.i = i
        def act(s, o): return jam(o)
        def end_hand(s, h): raise StopIteration
    # Patch stacks through a temporary copy of the module constant.
    start = engine.START
    return None

# Chip conservation and rule invariants over many real tables, with deep instrumentation through wrappers.
class Audit:
    def __init__(self, inner):
        self.b = inner
        if hasattr(inner, "observe"): self.observe = inner.observe
        if hasattr(inner, "end_hand"): self.end_hand = inner.end_hand
    def act(self, o):
        Audit.calls += 1
        total = sum(o.stacks) + o.pot
        if total > engine.START * 8 or total < 0: Audit.bad.append(("chips above total", total))
        if min(o.stacks) < 0: Audit.bad.append(("negative stack", list(o.stacks)))
        if o.to_call < 0 or o.to_call > o.stack: Audit.bad.append(("to_call", o.to_call, o.stack))
        if o.can_raise and not (o.min_raise_to <= o.max_raise_to): Audit.bad.append(("raise bounds", o.min_raise_to, o.max_raise_to))
        if o.max_raise_to != o.bet + o.stack: Audit.bad.append(("max raise", o.max_raise_to))
        if o.hole is None or len(set(o.hole + o.board)) != len(o.hole) + len(o.board): Audit.bad.append(("dup cards",))
        if len(o.board) != [0, 3, 4, 5][o.street]: Audit.bad.append(("board size", o.street, len(o.board)))
        return self.b.act(o)
Audit.calls = 0; Audit.bad = []
names = ["fold", "random", "station", "maniac", "jam20", "jam08", "tag", "nit", "lag", "mc", "shortfold", "allin", "minraise", "potsize", "bully", "pusher"]
PAYS = [[50, 30, 20, 0, 0, 0, 0, 0], [100, 50, 30, 20, 10, 5, 2, 0], [7, 6, 5, 4, 3, 2, 1, 0]]
pt_bad = chip_bad = capped = 0
TAB = 4000
for t in range(TAB):
    bots = [Audit(ARCHETYPES[random.choice(names)]()) for _ in range(7)] + [Audit(Hero())]
    random.shuffle(bots)
    e, nh, s = play_table(bots)
    capped += nh >= engine.MAX_HANDS
    # Every seat is accounted for exactly once.
    seen = [x for g in e for x in g] + list(s)
    if sorted(seen) != list(range(8)): chip_bad += 1
    # Final chips are conserved when anyone survives.
    if sum(s.values()) != engine.START * 8: chip_bad += 1
    for pay in PAYS:
        pts = points_for(e, s, pay)
        if abs(sum(pts) - sum(pay)) > 1e-6 or min(pts) < -1e-9: pt_bad += 1
check(f"invariants across {Audit.calls} decisions", not Audit.bad, str(Audit.bad[:3]))
check(f"chips conserved and all seats placed on {TAB} tables", chip_bad == 0, f"bad={chip_bad}; reached 200-hand cap: {capped/TAB:.0%}")
check("points conserved on every table", pt_bad == 0, f"bad={pt_bad}")

# 6. Hand-worked side pot through the settle rule: rig seats and cards so the result is known.
class Stacked:
    """Plays one table where everyone jams, with known cards; verifies main and side pot payout."""
import types
src = open(engine.__file__).read().replace("stacks = [START] * n", "stacks = list(STACKS)")
m = types.ModuleType("rigged"); m.__dict__["STACKS"] = None
sys.modules["rigged"] = m
exec(compile(src, "rigged", "exec"), m.__dict__)
def rig(stacks, board, holes, max_hands=1):
    # Button lands on seat 0 because randrange returns n-1.
    m.STACKS = stacks; m.MAX_HANDS = max_hands
    n = len(stacks)
    live = [i for i in range(n) if stacks[i] > 0]
    cards = sp(board) + [c for seat in live for c in sp(holes[seat])]
    bots = [types.SimpleNamespace(act=jam) for _ in range(n)]
    e, nh, surv = m.play_table(bots, [(10, 20)], RigRng(cards))
    return {i: surv.get(i, 0) for i in range(n)}
# Three-way: seat 0 has 100, seats 1, 2 have 300. Board is rainbow low, 0: AA, 1: KK, 2: QQ.
r = rig([100, 300, 300], "2s7h9dJc3s", {0: "AsAh", 1: "KsKh", 2: "QsQh"})
check("side pot: short AA wins main 300, KK wins side 400", r == {0: 300, 1: 400, 2: 0}, str(r))
# Short stack loses to the side-pot winner, and the excess bet is returned to the big stack.
r = rig([100, 300, 900], "2s7h9dJc3s", {0: "4s4h", 1: "QsQh", 2: "KsKh"})
check("uncalled excess returned", r == {0: 0, 1: 0, 2: 1300}, str(r))
# Chop between two equal stacks with a board straight.
r = rig([200, 200], "TsJhQdKcAs", {0: "2s2h", 1: "3s3h"})
check("board-plays chop", r == {0: 200, 1: 200}, str(r))
print("\nALL PASS" if not fails else f"\n{fails} FAILED")
