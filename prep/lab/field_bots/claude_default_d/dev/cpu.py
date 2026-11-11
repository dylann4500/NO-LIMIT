import sys, time, random, os
sys.argv = sys.argv[:1]
import sim
me_cls = sim.load_agent(sim.BOT, "me_agent")
import opponents
rng = random.Random(3)
cpu = []; wall = []
class Wrap:
    _track = False
    def __init__(self):
        self.a = me_cls()
    def act(self, st, mem):
        c0 = time.thread_time_ns(); t0 = time.perf_counter_ns()
        r = self.a.act(st, mem)
        cpu.append(time.thread_time_ns() - c0); wall.append(time.perf_counter_ns() - t0)
        return r
field = "tag,tag,lag,station,nit,maniac,flaky".split(",")
for t in range(80):
    kinds = ["me", "me", "me"] + field[:5]
    rng.shuffle(kinds)
    bots = [Wrap() if k == "me" else opponents.make(k, rng.random()) for k in kinds]
    sim.Table(bots, rng).run()
for name, v in (("cpu", cpu), ("wall", wall)):
    v.sort()
    print(name, "n=%d p50 %.0f p90 %.0f p99 %.0f p99.9 %.0f max %.0f us" % ((len(v),) + tuple(v[min(len(v)-1, int(q*len(v)))]/1e3 for q in (.5,.9,.99,.999)) + (v[-1]/1e3,)))
