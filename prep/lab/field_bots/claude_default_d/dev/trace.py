import sys, time, random, os
sys.argv = sys.argv[:1]
import sim
me_cls = sim.load_agent(sim.BOT, "me_agent")
import opponents
rng = random.Random(int(os.environ.get("SEED", "5")))
N = [0]
class Wrap:
    _track = False
    def __init__(self):
        self.a = me_cls()
    def act(self, st, mem):
        r = self.a.act(st, mem)
        N[0] += 1
        me = [s for s in st.seats if s.seat == st.seat][0]
        hist = " ".join("%s%s%s" % (e.kind[0:2], "" if e.seat is None else e.seat, "" if e.amount is None else ":%s" % e.amount) for e in st.history if e.kind not in ("hand",))
        print("H%d bl=%s btn=%d me=%d stk=%d bet=%d pot=%d tc=%d %s %s | %s -> %s" % (st.hand_number, st.blinds, st.button, st.seat, me.stack, me.bet, st.pot, st.to_call, "".join(st.cards), "".join(st.board), hist[-150:], r[0]))
        return r
field = os.environ.get("FIELD", "tag,tag,lag,station,nit,maniac,flaky").split(",")
kinds = ["me"] + field
rng.shuffle(kinds)
print(kinds)
bots = [Wrap() if k == "me" else opponents.make(k) for k in kinds]
pts, h = sim.Table(bots, rng).run()
print(pts, h)
