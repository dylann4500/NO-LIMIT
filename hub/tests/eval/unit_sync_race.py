import asyncio, sys, tempfile, time, random
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import bus as B, hub as H
class FD:
    class _A:
        def __init__(s, f): s.aio = f
    def __init__(s, store, jitter): s.store, s.j = store, jitter
    def __getattr__(s, n):
        st, j = s.store, s.j
        async def put(k, v, **kw): await asyncio.sleep(random.uniform(0, j)); st[k] = v
        async def get(k, default=None): await asyncio.sleep(random.uniform(0, j)); return st.get(k, default)
        async def items():
            for k, v in list(st.items()): yield k, v
        async def pop(k): st.pop(k, None)
        return FD._A({"put": put, "get": get, "items": items, "pop": pop}[n])
async def trial(seed):
    random.seed(seed)
    D, BL = {}, {}
    mk = lambda p: B.Bus(p, Path(tempfile.mkdtemp()), None, None, "-t")
    s, d = mk("samuel"), mk("dylan")
    for x in (s, d):
        x.d, x.blobs = FD(D, 0.3), FD(BL, 0.3); x.merge = lambda k, a, b: H.merge_note(a, b)
    base = {"id": "P1", "title": "idea", "status": "new", "thread": [], "updated": time.time()}
    s.shared["prop:P1"] = d.shared["prop:P1"] = dict(base); s.shared_ver["prop:P1"] = d.shared_ver["prop:P1"] = base["updated"]
    t = time.time()
    await s.set_shared("prop:P1", dict(base, thread=[{"at": t, "who": "Samuel", "text": "sample size?"}], updated=t))
    await d.set_shared("prop:P1", dict(base, status="removed", updated=t + 0.003))
    tasks = [asyncio.create_task(f()) for x in (s, d) for f in (x._shared_loop, x._dir_loop)]
    await asyncio.sleep(25)
    for t_ in tasks: t_.cancel()
    a, b = s.shared["prop:P1"], d.shared["prop:P1"]
    return a["status"] == b["status"] == "removed" and len(a["thread"]) == len(b["thread"]) == 1
async def main():
    res = await asyncio.gather(*[trial(i) for i in range(12)])
    print(f"converged {sum(res)}/{len(res)}")
asyncio.run(main())
