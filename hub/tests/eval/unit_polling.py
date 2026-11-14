"""Portal checks: every 6 s only while a round should be finishing (2-15 event-min after it starts, until its result
lands), 30 s otherwise.   uv run ... python hub/tests/eval/unit_polling.py hub"""
import sys, time, types
sys.path.insert(0, sys.argv[1])
import hub as H
fails = []
def check(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ("" if c else f" [{d}]")); c or fails.append(n)
class FakeHub:
    def __init__(s, t0):
        s.bus = types.SimpleNamespace(shared={"schedule": {"start": t0, "scale": 1.0, "scored": 6}})
        s.clock = H.Clock.__new__(H.Clock); s.clock.hub = s
w = H.PortalWatcher.__new__(H.PortalWatcher); w.st = {"done_stages": []}
now = time.time()
def at(minute):   # a watcher whose clock says it is `minute` event-minutes after minute 0
    w.hub = FakeHub(now - minute * 60); return w.finishing()
check("before practice 1 (minute 15): slow", not at(15))
check("practice 1 just started (minute 21): slow", not at(21))
check("practice 1 finishing (minute 24): fast", at(24))
w.st["done_stages"] = ["Practice 1"]
check("practice 1 result landed (minute 24): slow again", not at(24))
w.st["done_stages"] = ["Practice 1", "Practice 2", "Practice 3", "Practice 4"]
check("scored round 1 finishing (minute 66): fast", at(66))
w.st["done_stages"] += ["Round 1"]
check("after round 1 landed, before practice 5 (minute 71): slow", not at(71))
check("practice 5 (Round 1.5) finishing (minute 74): fast", at(74))
check("no clock: slow", (setattr(w, "hub", types.SimpleNamespace(bus=types.SimpleNamespace(shared={}))) or not w.finishing()))
check("intervals are 6 s and 30 s", (H.PortalWatcher.FAST, H.PortalWatcher.SLOW) == (6, 30))
print("FAILED:", fails if fails else "none")
