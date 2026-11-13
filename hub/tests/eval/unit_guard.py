import asyncio, sys, time, tempfile, types
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import hub as H

class Ag:
    def __init__(s, name): s.name, s.title, s.items, s.eta = name, name, [], None
    async def add_item(s, it): s.items.append(it)

class FakeHub:
    def __init__(s, person, sch):
        s.person, s.data = person, Path(tempfile.mkdtemp()); s.repo = s.data / "repo"; s.repo.mkdir()
        s.landed_at, s._ledger, s._bots, s._props, s.alerts, s.lives = {}, [], [], [], [], []
        s.bus = types.SimpleNamespace(shared={"schedule": sch})
        names = ["s-overseer", "s-data", "s-pipeline"] if person == "samuel" else ["d-overseer", "d-platform", "d-challenger"]
        s.agents = {n: Ag(n) for n in names}
    def overseer(s): return next(a for a in s.agents.values() if a.name.endswith("overseer"))
    def ledger(s): return s._ledger
    def bots(s): return s._bots
    def props(s): return s._props
    def find_bot_file(s, f): return None
    def set_service(s, *a, **k): pass
    async def alert_all(s, ag, text, urgent): s.alerts.append((text, urgent))
    async def save_prop(s, p): s._props.append(p)
    async def make_live(s, f, who, note="", tell=True): s.lives.append(f); s.bus.shared["live"] = {"file": f, "filename": Path(f).name, "at": time.time()}

def run(g): asyncio.run(g.tick())
U = 60 * 0.01   # scale 0.01: an event-minute is 0.6 s
fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name); cond or fails.append(name)

# Window before scored round 2: ts = t0 + 80U. Put "now" at T-11 (start + 9U)
def mk(person, T):
    ts = time.time() + T * U
    t0 = ts - 80 * U
    h = FakeHub(person, {"start": t0, "scale": 0.01, "scored": 6})
    return h, H.DeadlineGuard(h), ts

# 1. samuel, data landed, card missing 3+ min after landing -> card cut; data ok
h, g, ts = mk("samuel", 9.5)
h.landed_at["Round 1"] = ts - 13 * U
run(g)
check("data met when landed", f"{int(ts)}:data" in g.done and f"{int(ts)}:data:cut" not in g.done)
check("card cut 3 min after landing", f"{int(ts)}:card:cut" in g.done and any("Cut-off" in i["text"] and i.get("urgent") for i in h.agents["s-pipeline"].items))
# 2. heads-up on change at T-10 goes only to the overseer, not the worker
check("change heads-up to overseer only", any("isn't done" in i["text"] for i in h.agents["s-overseer"].items)
      and not any("isn't done" in i["text"] for i in h.agents["s-data"].items))
check("heads-up never says hurry", all("Do NOT tell anyone to hurry" in i["text"] for i in h.agents["s-overseer"].items if "isn't done" in i["text"]))
# 3. change cut at T-8 when nothing recorded
h, g, ts = mk("samuel", 7.5); h.landed_at["Round 1"] = ts - 13 * U
(h.repo / "analysis" / "Round-1").mkdir(parents=True); (h.repo / "analysis" / "Round-1" / "card.md").write_text("x")
run(g)
check("card met when file exists", f"{int(ts)}:card:cut" not in g.done)
check("change cut at T-8", f"{int(ts)}:change:cut" in g.done and any("No change from this window" in i["text"] for i in h.agents["s-data"].items))
# 4. change recorded -> no cut
h, g, ts = mk("samuel", 7.5); h.landed_at["Round 1"] = ts - 13 * U
h._ledger.append({"question": "one-change Round 1", "at": time.time()})
(h.repo / "analysis" / "Round-1").mkdir(parents=True); (h.repo / "analysis" / "Round-1" / "card.md").write_text("x")
run(g); check("no cut when change recorded", not any(k.endswith(":cut") for k in g.done))
# 5. data never landed by T-10 -> data cut, no card cut
h, g, ts = mk("samuel", 9.5); run(g)
check("data cut at T-10", f"{int(ts)}:data:cut" in g.done and f"{int(ts)}:card:cut" not in g.done and any("hadn't landed" in a[0] for a in h.alerts))
# 6. ETA late -> early heads-up (T-16, before the T-10 warn point)
h, g, ts = mk("samuel", 16); h.landed_at["Round 1"] = ts - 17 * U
(h.repo / "analysis" / "Round-1").mkdir(parents=True); (h.repo / "analysis" / "Round-1" / "card.md").write_text("x")
h.agents["s-data"].eta = ts - 5 * U; run(g)
check("late ETA triggers early heads-up", any("expects to finish" in i["text"] for i in h.agents["s-overseer"].items))
h, g, ts = mk("samuel", 16); h.agents["s-data"].eta = ts - 12 * U; h.landed_at["Round 1"] = ts - 17 * U
(h.repo / "analysis" / "Round-1").mkdir(parents=True); (h.repo / "analysis" / "Round-1" / "card.md").write_text("x")
run(g); check("on-time ETA: silence", not h.agents["s-overseer"].items)
# 7. dylan: challenger cut at T-12 doesn't interrupt the challenger
h, g, ts = mk("dylan", 11.5); run(g)
ch = h.agents["d-challenger"].items
check("challenger cut, not interrupted", f"{int(ts)}:challenger:cut" in g.done and ch and not ch[0].get("urgent") and not ch[0].get("wake"))
# 8. dylan: no note by T-7 -> default note with live bot
h, g, ts = mk("dylan", 6.5); h.bus.shared["live"] = {"file": "releases/v4.zip", "filename": "v4.zip", "at": ts - 40 * U}
h._bots.append({"name": "v9", "status": "ready", "updated": time.time()})
run(g); check("default note posted", any(p["kind"] == "bot" and p["bot"] == "releases/v4.zip" for p in h._props))
# 9. chosen not ready at T-4 -> revert to prev
h, g, ts = mk("dylan", 3.5)
h._props.append({"kind": "bot", "created": time.time()}); h._bots.append({"name": "v9", "status": "ready", "updated": time.time()})
h.bus.shared["live"] = {"file": "releases/v10.zip", "filename": "v10.zip", "at": ts - 8 * U, "prev": {"file": "releases/v4.zip", "filename": "v4.zip"}}
h.bus.shared["bot:v10"] = {"status": "building"}
run(g); check("unready chosen bot reverted", h.lives == ["releases/v4.zip"] and any("Upload nothing" in a[0] and a[1] for a in h.alerts))
# 10. chosen ready -> no revert
h, g, ts = mk("dylan", 3.5)
h._props.append({"kind": "bot", "created": time.time()}); h._bots.append({"name": "v9", "status": "ready", "updated": time.time()})
h.bus.shared["live"] = {"file": "releases/v10.zip", "filename": "v10.zip", "at": ts - 8 * U, "prev": {"file": "releases/v4.zip"}}
h.bus.shared["bot:v10"] = {"status": "ready", "sha256": "ab"}
run(g); check("ready chosen bot stays", not h.lives)
# 11. once only
n = len(h.alerts); run(g); run(g); check("idempotent", len(h.alerts) == n)
print("FAILED:", fails if fails else "none")
