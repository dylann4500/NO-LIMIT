import asyncio, sys, time, types
sys.path.insert(0, sys.argv[1])
import hub as H
class Cl:
    def __init__(s): s.calls = []
    async def interrupt(s): s.calls.append("interrupt")
    async def disconnect(s): s.calls.append("disconnect")
class Ag:
    def __init__(s, n, quiet):
        s.name = s.title = n; s.state = "working"; s.client = Cl(); s.last_msg_at = time.time() - quiet; s.stall_kicked = 0.0
        s.interrupted = False; s.items = []; s.recs = []; s.task = "t"; s.turn_started = time.time() - quiet
    def record(s, e): s.recs.append(e)
    async def add_item(s, it): s.items.append(it)
class F:
    pass
f = F(); ov = Ag("s-overseer", 0); ov.state = "idle"
busy, hung = Ag("s-data", 5 * 60), Ag("s-tester", 13 * 60)
f.agents = {"s-overseer": ov, "s-data": busy, "s-tester": hung}; f.alerts = []
f.overseer = lambda: ov
async def add_alert(a, t, u): f.alerts.append(t)
f.add_alert = add_alert
ws = lambda: asyncio.run(H.Hub.watch_stalls(f))
ws()
print("busy untouched:", busy.client.calls == [], "| hung interrupted:", hung.client.calls == ["interrupt"], "| overseer told:", len(ov.items) == 1)
ws(); print("no double kick:", hung.client.calls == ["interrupt"])
hung.stall_kicked = time.time() - 100; ws()
print("disconnected after 90 s:", hung.client.calls == ["interrupt", "disconnect"], "| alert:", bool(f.alerts))
ws(); print("once:", hung.client.calls.count("disconnect") == 1)
r = Ag("s-x", 13 * 60); r.stall_kicked = time.time() - 100; r.last_msg_at = time.time() - 10; f.agents["s-x"] = r; ws()
print("recovered agent not disconnected:", "disconnect" not in r.client.calls)
lt = Ag("s-long", 30); lt.turn_started = time.time() - 26 * 60; f.agents = {"s-overseer": ov, "s-long": lt}; ov.items.clear(); ws(); ws()
print("long turn: one overseer note, no interrupt:", len([i for i in ov.items if "one turn" in i["text"]]) == 1 and lt.client.calls == [])
