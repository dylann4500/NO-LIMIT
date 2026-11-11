"""Decision latency distribution for the candidate bot in real game positions. Run on an idle machine."""
import gc, random, sys, time
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import play_table
from field import ARCHETYPES, FIELDS
from hero import Hero
from pk import equity_vs_range

pc = time.perf_counter


class Timed:
    samples = {0: [], 1: [], 2: [], 3: []}
    def __init__(self, rollouts):
        self.h = Hero(rollouts=rollouts)
        self.observe = self.h.observe
        self.end_hand = self.h.end_hand
    def act(self, o):
        t = pc()
        r = self.h.act(o)
        Timed.samples[o.street].append(pc() - t)
        return r


def run(rollouts, tables=300, gc_mode="on"):
    Timed.samples = {0: [], 1: [], 2: [], 3: []}
    gc.enable()
    if gc_mode == "off":
        gc.collect(); gc.freeze(); gc.disable()
    names = list(FIELDS["typical"])
    w = [FIELDS["typical"][k] for k in names]
    for _ in range(tables):
        bots = [ARCHETYPES[s]() for s in random.choices(names, w, k=7)]
        bots.insert(random.randrange(8), Timed(rollouts))
        play_table(bots)
    gc.enable()
    gc.unfreeze()
    allv = sorted(x for v in Timed.samples.values() for x in v)
    n = len(allv)
    q = lambda p: allv[min(n - 1, int(p * n))] * 1e6
    over = sum(1 for x in allv if x > 1e-3)
    print(f"rollouts={rollouts:<4} gc={gc_mode:<3} n={n:<7} p50={q(.5):7.1f}us p99={q(.99):7.1f} p99.9={q(.999):7.1f} p99.99={q(.9999):8.1f} max={allv[-1]*1e6:8.1f}  over1ms={over}")


for r in (10, 40, 100, 200):
    run(r)
run(100, gc_mode="off")
run(200, gc_mode="off")

# Import and table load cost, which matters if the platform re-imports per table.
t = pc()
import numpy as np
print(f"import numpy: {(pc()-t)*1e3:.1f} ms")
t = pc()
_ = [i * i for i in range(10000)]
print(f"pure python 10k-element list comprehension: {(pc()-t)*1e6:.0f} us")

# Size versus load time for a table saved to disk.
import os, pickle, tempfile
d = tempfile.mkdtemp()
for mb in (1, 10, 90):
    b = bytes(random.getrandbits(8) for _ in range(1000)) * (mb * 1000)
    p = os.path.join(d, "x.bin")
    open(p, "wb").write(b)
    t = pc(); data = open(p, "rb").read(); t1 = pc() - t
    arr = np.frombuffer(data, dtype=np.uint8)
    t = pc(); v = arr[12345]; t2 = pc() - t
    t = pc(); w = data[12345]; t3 = pc() - t
    print(f"{mb}MB read {t1*1e3:.1f} ms; numpy scalar index {t2*1e6:.2f} us; bytes index {t3*1e6:.3f} us")
