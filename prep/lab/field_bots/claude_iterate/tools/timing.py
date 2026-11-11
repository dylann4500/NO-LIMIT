"""Find slowest decisions. usage: timing.py seats tables"""
import os, random, sys, time, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "fake_sdk")); sys.path.insert(0, HERE)
import sim, opponents, arena
Agent = arena.load("me", os.path.join(HERE, ".."))
import cProfile, pstats
slow = []
class Wrap:
    def __init__(self, a): self.a = a
    def act(self, st, mem):
        t = time.thread_time(); r = self.a.act(st, mem); dt = time.thread_time() - t
        slow.append((dt, len(st.board), st.to_call, len(st.events), len([s for s in st.seats if s.status in ('active','all_in')]), st.hand_number))
        return r
seats = sys.argv[1].split(","); n = int(sys.argv[2])
rng = random.Random(1)
pool = [Agent(), Agent()]
pr = cProfile.Profile() if os.environ.get("PROF") else None
if pr: pr.enable()
for t in range(n):
    order = seats[:]; rng.shuffle(order)
    bots = [Wrap(pool[rng.randrange(2)]) if k == "me" else opponents.OPPS[k]() for k in order]
    sim.play_table(bots, order, rng)
if pr:
    pr.disable(); pstats.Stats(pr).sort_stats("cumulative").print_stats(18)
slow.sort(reverse=True)
L = sorted(x[0] for x in slow)
print("n", len(L), "p50 %.1f p99 %.1f p999 %.1f max %.1f us" % (L[len(L)//2]*1e6, L[int(len(L)*.99)]*1e6, L[int(len(L)*.999)]*1e6, L[-1]*1e6))
for x in slow[:12]: print("%.0fus board=%d to_call=%d events=%d inhand=%d hand=%d" % (x[0]*1e6, *x[1:]))
