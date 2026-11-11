"""Decision parity, hold'em: the untouched field_bots/claude_default_c_r3 vs. lab/portfolio/default_c/core on the same states.
Both cores get the same RNG seed and eval7 xorshift seed before every decision, and a frozen clock, so any difference
is a code difference. Adapted from v2_parity.py. usage (from lab/): ../.venv/bin/python default_c_parity.py [tables] [field] [seed]"""
import importlib.util, os, random, sys, types
LAB = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
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


old = load("old_core", os.path.join(LAB, "field_bots/claude_default_c_r3/agent.py"))
new = load("new_core", os.path.join(LAB, "portfolio/default_c/core/agent.py"))
assert new.E.ENGINE == "eval7" and new.E.VARIANT == "holdem", (new.E.ENGINE, new.E.VARIANT)
frozen = types.SimpleNamespace(perf_counter=lambda: 0.0)
old.time = frozen
new.time = frozen
# import-time objects
for k in ("classes", "ncomb", "eq1", "eq3", "shove_order", "open_order", "grid", "eq_top"):
    assert old._T[k] == new._T[k], k
assert old.SHOVE_PCT == new.SHOVE_PCT and old.SHOVE_MID == new.SHOVE_MID, "SHOVE_PCT"
assert old.OPEN_PCT == new.OPEN_PCT and old.OPEN_MID == new.OPEN_MID, "OPEN_PCT"
assert old._FRAC_NEG == new._FRAC_NEG and old._FRAC_CUM == new._FRAC_CUM, "_FRAC tables"
assert len(old.CHUNKS) == len(new.CHUNKS) == old.NCH == new.NCH and new.NALL == 1326
for a, b in zip(old.CHUNKS, new.CHUNKS):
    assert len(a) == len(b), "chunk sizes"
    for t, u in zip(a, b):
        assert t[0] == u[2] and t[1] == u[3] and t[2] == u[1][0] and t[3] == u[1][1], "CHUNKS entries"
        assert (str(t[2]), str(t[3])) == u[0], "CHUNKS names"
for (x, y), ci in old.HCLASS.items():
    assert new.E.hand_class([x, y]) == ci, (x, y)
for h, lab in enumerate(old.CLASSES):
    spec = (len(lab) == 2) or (lab[2] == "s" and (lab[0] == "A" or abs(old.RANKS.index(lab[0]) - old.RANKS.index(lab[1])) <= 2))
    assert new.PAIR[h] == (len(lab) == 2) and new.SPEC[h] == spec and new.PREM[h] == (lab in old.PREMIUM), lab
print("import-time objects identical: tables (8 fields), SHOVE/OPEN percentiles, call-width tables, CHUNKS (order, cards, "
      "masks, MC entries), hand classes on all 2652 ordered pairs, pair/speculative/premium flags on 169 classes")

N = {"dec": 0, "diff": 0, "memdiff": 0, "pre": 0, "post": 0}
EX = []


class Dual:
    def __init__(self):
        self.a, self.b = old.Agent(), new.Agent()

    def act(self, state, memory):
        s = N["dec"] = N["dec"] + 1
        old.RNG.seed(s); eval7.xorshift_rand.seed(s)
        a1, m1 = self.a.act(state, memory)
        new.RNG.seed(s); eval7.xorshift_rand.seed(s)
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
