"""Generated bot vs. lab lookup policy: same decisions on the same states, and the same score."""
import json, math, random, sys, os
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), sys.argv[1]]
import bot
from engine import play_table, points_for
from field import ARCHETYPES, FIELDS
from strength import HeroTable, table_equity, feature
params = dict(bot.PARAMS)
# 1. Feature and equity agreement on random states.
bad = 0
for _ in range(100000):
    st = random.choice((3, 4, 5))
    s = random.sample(range(52), 2 + st)
    h, b = s[:2], s[2:]
    w = random.choice([0.05, 0.1, 0.3, 0.7, 1.0])
    if abs(bot.table_equity(h, b, w) - table_equity(h, b, w)) > 1e-9 or bot.feature(h, b) != feature(h, b):
        bad += 1
print("feature/equity mismatches:", bad)
# 2. Decision agreement in real play, with one shadowing the other on the same event stream.
class Shadow:
    n = same = 0
    diffs = {}
    ex = []
    def __init__(self):
        self.g, self.l = bot.Policy(), HeroTable(**params)
    def act(self, o):
        rs = random.getstate()
        a = self.g.safe_decide(o)
        random.setstate(rs)  # both policies must see the same random draw
        b = self.l.act(o)
        kb, ab = b
        if kb == 2:
            if not o.can_raise:
                kb, ab = 1, 0
            else:
                ab = int(min(o.max_raise_to, max(o.min_raise_to, ab)))
        else:
            ab = 0
            if kb == 0 and o.to_call == 0:
                kb = 1
        Shadow.n += 1
        if a == (kb, ab):
            Shadow.same += 1
        else:
            key = ("pre" if o.street == 0 else "post", a[0], kb)
            if len(Shadow.ex) < 3:
                Shadow.ex.append((a, (kb, ab), o.street, o.raises, o.n_alive, o.n_behind, o.to_call, o.stack, list(o.hole)))
            Shadow.diffs[key] = Shadow.diffs.get(key, 0) + 1
        return a
    def observe(self, s, st, k, am):
        self.g.observe(s, st, k)
        self.l.observe(s, st, k, am)
    def end_hand(self, n):
        self.g.end_hand()
        self.l.end_hand(n)
names = list(FIELDS["typical"]); w = [FIELDS["typical"][k] for k in names]
for _ in range(int(sys.argv[2])):
    bots = [ARCHETYPES[x]() for x in random.choices(names, w, k=7)]
    bots.insert(random.randrange(8), Shadow())
    play_table(bots)
print(f"decisions {Shadow.n}, identical {Shadow.same} ({100*Shadow.same/max(1,Shadow.n):.2f}%)", Shadow.diffs)
print(Shadow.ex)
