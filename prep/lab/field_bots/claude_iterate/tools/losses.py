"""Print hands where the bot loses a big share of its stack. usage: losses.py <opp> [tables] [seed]"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "fake_sdk")); sys.path.insert(0, HERE)
import sim, opponents, arena
Agent = arena.load("me", os.path.join(HERE, ".."))
class Wrap:
    def __init__(self):
        self.a = Agent(); self.log = []; self.hn = None; self.start = None
    def act(self, st, mem):
        me = [s for s in st.seats if s.seat == st.seat][0]
        if st.hand_number != self.hn:
            self.hn = st.hand_number; self.log = []
        mod = sys.modules["agent_me"]
        if mod.TRACE is not None: del mod.TRACE[:]
        act, m = self.a.act(st, mem)
        if mod.TRACE: self.log.append(list(mod.TRACE))
        self.log.append((st.board, st.pot, st.to_call, me.stack, me.bet, act))
        self.last = (st, list(st.cards))
        return act, m
opp = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 3)
orig = sim.play_table
for t in range(n):
    w = Wrap()
    seats = ["me"] + [opp] * 7
    bots = [w] + [opponents.OPPS[opp]() for _ in range(7)]
    # monkeypatch: capture stacks per hand via the wrapper's log at hand end using the event log
    pts, places, P, hands = sim.play_table(bots, seats, rng)
    if places[0] >= 6:
        st, cards = w.last
        print("TABLE", t, "place", places[0], "hand", st.hand_number, "blinds", st.blinds, "cards", cards)
        for x in w.log: print("   ", x)
        print("   hist:", [(e.kind, e.seat, e.amount, e.cards) for e in st.history][-30:])
        print("   seats:", [(s.seat, s.stack, s.bet, s.status) for s in st.seats], "me", st.seat)
