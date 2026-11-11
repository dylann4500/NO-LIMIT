"""Decision parity, hold'em: the strategy v2 was merged from (field_bots/claude_default_b_r2) vs. lab/v2/core on the same states.
Both cores get the same _rng seed and eval7 xorshift seed before every decision, and a frozen clock, so any difference
is a code difference. usage (from lab/): ../.venv/bin/python parity.py [tables] [field] [seed]"""
import importlib.util, os, random, sys, types
LAB = "/Users/dylan/Documents/GitHub/pokerbot/lab"
for p in (LAB, os.path.join(LAB, "fake_sdk"), os.path.join(LAB, "field_kit")):
    sys.path.insert(0, p)
os.environ.pop("POKER_VARIANT", None)
import eval7, engine
from platform_sim import Plat, Stats, play_platform_table
from field import ARCHETYPES, FIELDS


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


old = load("old_core", os.path.join(LAB, "field_bots/claude_default_b_r2/agent.py"))
new = load("new_core", os.path.join(LAB, "v2/core/agent.py"))
assert new.E.ENGINE == "eval7", new.E.ENGINE
frozen = types.SimpleNamespace(perf_counter=lambda: 0.0)
old.time = frozen
new.time = frozen
# import-time objects
assert old.CALLQ == new.CALLQ, "CALLQ"
assert len(old.PRANGES) == len(new.PRANGES)
for a, b in zip(old.PRANGES, new.PRANGES):
    assert [(t[0], t[1]) for t in a] == [t[0] for t in b], "PRANGES order"
    assert all(t[2] == u[1] and t[3] == u[2] for t, u in zip(a, b)), "PRANGES cards"
for ci in range(169):
    for x in "shdc":
        for y in "shdc":
            for r1 in "23456789TJQKA":
                for r2 in "AKQJT98765432":
                    if r1 + x != r2 + y:
                        assert old.class_of(r1 + x, r2 + y) == new.class_of([r1 + x, r2 + y])
    break
print("import-time objects identical: CALLQ, PRANGES (order, cards, MC entries), class_of on all 2652 ordered pairs")

N = {"dec": 0, "diff": 0, "memdiff": 0, "pre": 0, "post": 0}
EX = []


class Dual:
    def __init__(self):
        self.a, self.b = old.Agent(), new.Agent()

    def act(self, state, memory):
        s = N["dec"] = N["dec"] + 1
        old._rng.seed(s); eval7.xorshift_rand.seed(s)
        a1, m1 = self.a.act(state, memory)
        new._rng.seed(s); eval7.xorshift_rand.seed(s)
        a2, m2 = self.b.act(state, memory)
        N["post" if state.board else "pre"] += 1
        if (a1.kind, a1.amount) != (a2.kind, a2.amount):
            N["diff"] += 1
            if len(EX) < 5:
                EX.append((state.cards, state.board, a1, a2))
        if m1 != m2:
            N["memdiff"] += 1
        return a1, m1


tables = int(sys.argv[1]) if len(sys.argv) > 1 else 100
field = sys.argv[2] if len(sys.argv) > 2 else "typical"
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 5)
names = list(FIELDS[field]); w = [FIELDS[field][k] for k in names]
for _ in range(tables):
    bots = [ARCHETYPES[k]() for k in rng.choices(names, w, k=5)]
    for _ in range(3):  # three dual seats per table
        bots.insert(rng.randrange(len(bots) + 1), Plat([Dual()]))
    play_platform_table(bots, rng=rng, stats=Stats())
print(f"{tables} tables ({field}): {N['dec']} decisions ({N['pre']} preflop, {N['post']} postflop), "
      f"{N['diff']} action differences, {N['memdiff']} memory differences")
for e in EX:
    print("  diff:", e)
