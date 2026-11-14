"""Integration eval (checklist method I): two real hubs (Samuel + Dylan) linked over Modal, a fake organizers'
portal this script controls, agents switched off (AVALON_NO_AGENTS=1, so no Claude usage).

  uv run --no-project --with aiohttp==3.14.5 --with claude-agent-sdk==0.2.181 --with modal==1.6.4 \
      python hub/tests/eval/integration.py --out /tmp/eval-int

Prints PASS/FAIL per checklist id and writes results.json in --out. Leaves the hubs running with --keep (for the
screenshot pass).
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from aiohttp import ClientSession, ClientTimeout, web

HUB = Path(__file__).resolve().parents[2]
RESULTS: list[dict] = []


def check(cid: str, name: str, ok: bool, detail: str = ""):
    RESULTS.append({"id": cid, "name": name, "ok": bool(ok), "detail": detail[:400]})
    print(f"{'PASS' if ok else 'FAIL'} {cid:4} {name}" + (f"  [{detail[:200]}]" if detail and not ok else ""), flush=True)


# ------------------------------------------------------------------ fake portal
class Portal:
    def __init__(self):
        self.rounds: list[dict] = []
        self.subs: list[dict] = []
        self.active = None
        self.uas: set[str] = set()
        self.methods: set[str] = set()
        self.results_fail = 0   # answer 503 to this many results calls (results not ready yet)

    def app(self):
        p = self

        @web.middleware
        async def spy(req, handler):
            p.uas.add(req.headers.get("User-Agent", ""))
            p.methods.add(req.method)
            return await handler(req)
        app = web.Application(middlewares=[spy])
        J = web.json_response
        r = app.router
        r.add_get("/api/auth/api-key", lambda q: J({"teams": [{"team_id": "avalon", "competition_id": "c1"}]}))
        r.add_get("/api/competitions/c1", lambda q: J({"id": "c1", "name": "Eval Finals"}))
        r.add_get("/api/competitions/c1/tournaments", lambda q: J({"items": p.rounds}))
        r.add_get("/api/competitions/c1/standings", lambda q: J({"items": [
            {"rank": 1, "team_name": "Shove Bros", "total": 30.0}, {"rank": 2, "team_name": "avalon", "total": 26.2},
            {"rank": 3, "team_name": "Tight Club", "total": 20.0}]}))
        r.add_get("/api/teams/avalon", lambda q: J({"id": "avalon", "name": "avalon", "active_submission_id": p.active}))
        r.add_get("/api/teams/avalon/submissions", lambda q: J({"items": p.subs}))

        async def results(q):
            if p.results_fail > 0:
                p.results_fail -= 1
                return J({"error": "not ready"}, status=503)
            return J({"items": [{"team_name": "avalon", "average_points": 26.25, "margin_of_error": 1.2},
                                {"team_name": "Shove Bros", "average_points": 30.0, "margin_of_error": 1.0}]})
        r.add_get("/api/tournaments/{tid}/results", results)

        async def hands(q):
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb") as g:
                g.write(b"".join(b'{"hand": %d, "seed": "%s"}\n' % (i, os.urandom(8).hex().encode()) for i in range(300)))
            return web.Response(body=buf.getvalue(), content_type="application/gzip")
        r.add_get("/api/tournaments/{tid}/hands", hands)
        return app


# ------------------------------------------------------------------ helpers
async def api(s: ClientSession, base: str, method: str, path: str, body=None, raw=None, headers=None):
    t0 = time.time()
    kw = {"json": body} if body is not None else {}
    if raw is not None:
        kw = {"data": raw, "headers": {"X-Avalon": "1", "Content-Type": "application/octet-stream", **(headers or {})}}
    async with s.request(method, base + path, **kw) as r:
        ct = r.headers.get("Content-Type", "")
        data = await (r.json() if "json" in ct else r.read())
        return r.status, data, time.time() - t0


async def wait_for(fn, timeout=60, every=1.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = await fn()
        if v:
            return v
        await asyncio.sleep(every)
    return None


def make_repo(d: Path, with_card: bool):
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    (d / "README.md").write_text("eval repo\n")
    for f in ("bot", "releases", "analysis", "notes"):
        (d / f).mkdir(exist_ok=True)
    if with_card:   # a stand-in round-card script: writes analysis/<stage>/card.md
        (d / "analysis" / "roundcard.py").write_text(
            "import os, sys, re, pathlib\n"
            "st = os.environ.get('AVALON_STAGE', 'x')\n"
            "out = pathlib.Path('analysis') / re.sub(r'[^A-Za-z0-9.]+', '-', st)\n"
            "out.mkdir(parents=True, exist_ok=True)\n"
            "(out / 'card.md').write_text('# card for ' + st + '\\nfolder ' + sys.argv[1] + '\\n')\n"
            "print('card ok', st)\n")
        (d / "analysis" / "fp_train.py").write_text("raise SystemExit('fp deliberately failing')\n")
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=e@x", "-c", "user.name=eval", "commit", "-qm", "init"], check=True)


def start_hub(person, port, repo, data, ns, extra, log):
    env = {**os.environ, "AVALON_NO_AGENTS": "1"}
    cmd = [sys.executable, str(HUB / "hub.py"), "--person", person, "--repo", str(repo), "--data", str(data),
           f"--namespace={ns}", "--port", str(port), "--no-codex", "--model", "claude-haiku-5-5"] + extra
    return subprocess.Popen(cmd, stdout=open(log, "a"), stderr=subprocess.STDOUT, env=env, cwd=str(HUB))


def zip_bytes(tag: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("agent.py", f"# eval bot {tag}\n")
    return buf.getvalue()


# ------------------------------------------------------------------ the run
async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep", action="store_true", help="leave the hubs and portal running at the end")
    ap.add_argument("--ports", default="7811,7812,8811")
    a = ap.parse_args()
    out = Path(a.out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    ps, pd, pp = (int(x) for x in a.ports.split(","))
    ns = f"-eval{int(time.time())}"

    portal = Portal()
    runner = web.AppRunner(portal.app())
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", pp).start()
    (out / "key").write_text("evalkey\n")

    make_repo(out / "repo-s", with_card=True)
    make_repo(out / "repo-d", with_card=False)
    S, D = f"http://127.0.0.1:{ps}", f"http://127.0.0.1:{pd}"
    sx = ["--portal-base", f"http://127.0.0.1:{pp}/api", "--portal-key-file", str(out / "key"),
          "--portal-data", str(out / "pd"), "--scale", "0.05"]
    procs = {"samuel": start_hub("samuel", ps, out / "repo-s", out / "data-s", ns, sx, out / "hub-s.log"),
             "dylan": start_hub("dylan", pd, out / "repo-d", out / "data-d", ns, ["--scale", "0.05"], out / "hub-d.log")}
    async with ClientSession(timeout=ClientTimeout(total=60)) as s:
        async def up(base):
            try:
                st, d, _ = await api(s, base, "GET", "/api/state")
                return st == 200
            except Exception:  # noqa: BLE001
                return False
        t0 = time.time()
        okS, okD = await wait_for(lambda: up(S), 60), await wait_for(lambda: up(D), 60)
        check("S1", "both hubs serve /api/state", okS and okD, f"{time.time() - t0:.0f}s")
        st = lambda base: api(s, base, "GET", "/api/state")

        async def state(base):
            return (await st(base))[1]

        # link
        async def linked():
            x, y = await state(S), await state(D)
            return x["bus"]["online"] and y["bus"]["online"] and any(r["name"].startswith("d-") for r in x["remote"]) \
                and any(r["name"].startswith("s-") for r in y["remote"])
        check("B2", "laptops see each other's agents (directory)", await wait_for(linked, 120, 3))
        check("Q2", "agents are off in this test (no Claude usage)", all(g["state"] in ("stopped", "idle") for g in (await state(S))["agents"]))

        # S7: responsiveness under parallel load
        t1 = time.time()
        rs = await asyncio.gather(*[st(S) for _ in range(20)])
        check("S7", "20 parallel /api/state answered < 3 s", all(r[0] == 200 for r in rs) and time.time() - t1 < 3, f"{time.time() - t1:.2f}s")

        # C3: bad schedule value
        c, d, _ = await api(s, S, "POST", "/api/schedule", {"start": "25:99"})
        check("C3", "bad HH:MM is refused with a clear error", c == 400 and "HH:MM" in json.dumps(d), json.dumps(d))
        # json_only middleware: a non-JSON POST is refused
        async with s.post(S + "/api/start", data="x", headers={"Content-Type": "text/plain"}) as r:
            check("S7b", "non-JSON POSTs refused (403)", r.status == 403)

        # PF: "run the check" in the Chat runs the pre-flight on both laptops, results in both Chats
        c, d, _ = await api(s, S, "POST", "/api/agents/s-overview/send", {"text": "run the check"})
        async def pf(base, ovn):
            return next((t for t in (await state(base)).get("overviews", {}).get(ovn, []) if "Pre-flight check" in str(t.get("text"))), None)
        pfs = await wait_for(lambda: pf(S, "s-overview"), 150, 3)
        check("PF1", "pre-flight results in Samuel's Chat", bool(pfs), (pfs or {}).get("text", "")[:300])
        check("PF2", "pre-flight reads the portal", bool(pfs) and "✅ **Portal: read access" in pfs["text"], (pfs or {}).get("text", "")[:600])
        check("PF3", "pre-flight also ran on Dylan's laptop", bool(await wait_for(lambda: pf(D, "d-overview"), 150, 3)))
        print("      " + ((pfs or {}).get("text", "") or "").replace("\n", "\n      ")[:1500])

        # C1: telling the Chat "the competition starts now" starts the clock (the hub does it, no model needed)
        c, d, _ = await api(s, S, "POST", "/api/agents/s-overview/send", {"text": "the competition starts now"})
        check("C1a", "'the competition starts now' in the Chat starts the clock", c == 200 and "Clock started" in json.dumps(d), json.dumps(d))
        async def dsched():
            return (await state(D)).get("schedule")
        check("C1", "clock reaches Dylan's laptop", bool(await wait_for(dsched, 30)))
        c, d, _ = await api(s, D, "POST", "/api/start", {})
        check("C1b", "second Start is refused (clock already running)", c == 400)
        t0_before = (await state(S))["schedule"]["start"]
        await api(s, S, "POST", "/api/agents/s-overview/send", {"text": "ok it's starting now, go!"})
        await asyncio.sleep(3)
        check("C1c", "a vague 'it's starting now' doesn't move a running clock", (await state(S))["schedule"]["start"] == t0_before)
        x = await state(S)
        check("C4", "stage is Build at minute 0", x.get("stage") == "Build", x.get("stage"))

        # N3: build-hour progress tiles on both screens (one per work stream, both laptops)
        def tiles_of(st_, prefix):
            return [x for x in st_.get("tiles", []) if x["id"].startswith(prefix)]
        async def builds(base):
            ts_ = tiles_of(await state(base), "build-")
            return ts_ if len(ts_) >= 7 else None
        bS, bD = await wait_for(lambda: builds(S), 40), await wait_for(lambda: builds(D), 40)
        check("N3a", "7 build-hour tiles on Samuel's board", bool(bS), str(len(bS or [])))
        check("N3b", "the same tiles on Dylan's board", bool(bD) and {x["id"] for x in bS} == {x["id"] for x in bD})
        check("N3t", "tiles are plain (label + state + owner, no prompting)", bool(bS) and all(set(x) >= {"label", "state", "owner"} and len(x["label"]) < 60 for x in bS),
              json.dumps((bS or [{}])[0]))
        check("N3o", "every tile's owner is a real agent", bool(bS) and all(x["owner"] in ("d-platform", "d-builder", "d-challenger", "s-tester", "s-data", "s-scout") for x in bS))

        # C9: changing the clock is announced in both Chats (same minute 0, 3 scored rounds instead of 6)
        sch = (await state(S))["schedule"]
        c, d, _ = await api(s, S, "POST", "/api/schedule", {"start": time.strftime("%H:%M:%S", time.localtime(sch["start"])),
                                                           "scored": 3, "scale": 0.05})
        async def told(base, ovn):
            return any("clock was changed" in str(t.get("text")) for t in (await state(base)).get("overviews", {}).get(ovn, []))
        check("C9a", "a clock change is announced in Samuel's Chat", c == 200 and bool(await wait_for(lambda: told(S, "s-overview"), 20)))
        check("C9b", "… and in Dylan's Chat", bool(await wait_for(lambda: told(D, "d-overview"), 40, 2)))

        # N5 + N8: new idea, then close it
        c, idea, _ = await api(s, S, "POST", "/api/props", {"title": "Try a 2.2x open in late position", "body": ""})
        check("N5", "idea posted", c == 200 and idea.get("id"), json.dumps(idea)[:200])
        c, e, _ = await api(s, S, "POST", "/api/props", {"title": "  "})
        check("N5b", "empty idea refused", c == 400)
        async def seen_on_d(pid):
            return any(p["id"] == pid for p in (await state(D))["props"])
        check("N5c", "idea appears on Dylan's board", bool(await wait_for(lambda: seen_on_d(idea["id"]), 30)))
        c, d, _ = await api(s, S, "POST", f"/api/props/{idea['id']}/ask", {"text": "what's the sample size?"})
        check("N6", "asking in a note is accepted and shown in its thread",
              c == 200 and any("sample size" in str(t.get("text")) for t in d.get("thread", [])), json.dumps(d)[:300])
        c, d, _ = await api(s, D, "POST", f"/api/props/{idea['id']}/act", {"action": "remove"})
        check("N8a", "Dylan can close Samuel's idea", c == 200, json.dumps(d)[:200])
        async def gone_on_s():
            p = next((p for p in (await state(S))["props"] if p["id"] == idea["id"]), None)
            return p is None or p.get("status") == "removed"
        check("N8", "closed on Samuel's board too", bool(await wait_for(gone_on_s, 30)))
        c, d, _ = await api(s, S, "POST", "/api/props/NOPE/act", {"action": "approve"})
        check("N8b", "acting on a missing note gives an error, not a crash", c == 400)

        # L1/L2/L5: a release on Samuel's laptop shows on both, downloads on Dylan's with the same bytes
        z1 = zip_bytes("v1")
        (out / "repo-s" / "releases" / "v1.zip").write_bytes(z1)
        (out / "repo-s" / "releases" / "latest.zip").write_bytes(z1)   # an alias: must not be listed
        async def bot_on(base, name):
            return next((b for b in (await state(base)).get("bots", []) if b["name"] == name and b["status"] == "ready"), None)
        check("L1", "v1 listed as ready on Samuel's Live menu", bool(await wait_for(lambda: bot_on(S, "v1"), 45)))
        check("L1b", "aliases (latest.zip) are not listed", not await bot_on(S, "latest"))
        check("L5a", "v1 listed on Dylan's Live menu", bool(await wait_for(lambda: bot_on(D, "v1"), 30)))
        async def dl():
            c, d, _ = await api(s, D, "GET", "/api/bots/v1/download")
            return d if c == 200 and isinstance(d, (bytes, bytearray)) else None
        got = await wait_for(dl, 40, 3)
        check("L2", "Dylan downloads v1 (built on Samuel's laptop) with identical bytes", got == z1)
        c, d, _ = await api(s, D, "GET", "/api/bots/v99/download")
        check("L2b", "missing bot download gives a clear 404", c == 404)

        # L3: make live from Dylan's menu; both laptops agree
        c, d, _ = await api(s, D, "POST", "/api/live", {"file": "releases/v1.zip"})
        async def live_on(base):
            return ((await state(base)).get("live") or {}).get("filename") == "v1.zip"
        check("L3", "make live from Dylan's menu shows on both laptops", c == 200 and bool(await wait_for(lambda: live_on(S), 30)))

        # P1/P5/P6: portal watcher, no active bot, rejected upload
        portal.subs.append({"id": "sub1", "filename": "v0.zip", "status": "rejected", "rejection_reason": "timeout in upload test"})
        async def alert_with(base, word):
            return next((x for x in (await state(base))["alerts"] if word.lower() in x["text"].lower()), None)
        al = await wait_for(lambda: alert_with(S, "REJECTED"), 90, 3)
        check("P5a", "rejected upload → urgent alert on Samuel's screen", bool(al) and al.get("urgent"))
        check("P5b", "… and on Dylan's screen", bool(await wait_for(lambda: alert_with(D, "REJECTED"), 40, 3)))
        check("P1", "portal reads are GET-only with a non-default User-Agent",
              portal.methods <= {"GET"} and all(u.startswith("avalon-") for u in portal.uas), f"{portal.methods} {portal.uas}")
        svc = next((v for v in (await state(S))["services"] if v["name"] == "s-portal"), {})
        check("P6", "standings in the Portal service", "Shove Bros" in (svc.get("summary") or ""), (svc.get("task") or ""))

        # P2/P3/N3: practice 1 plays and finishes
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        portal.subs.append({"id": "sub2", "filename": "v1.zip", "status": "ready"})
        portal.active = "sub2"
        portal.rounds.append({"id": "t-practice-1-abcdef", "kind": "practice", "created_at": now, "completed_at": None})
        async def live_tile():
            return next((x for x in (await state(S)).get("tiles", []) if x["id"] == "round-Practice-1" and "playing" in x["state"]), None)
        ln = await wait_for(live_tile, 90, 3)
        check("N3c", "'Practice 1 · playing v1' tile when the round starts", bool(ln) and "v1" in ln["state"], json.dumps(ln or {}))
        portal.rounds[-1]["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        t_done = time.time()
        async def an_tile():
            return next((x for x in (await state(S)).get("tiles", []) if x["id"] == "analysis-Practice-1"), None)
        an = await wait_for(an_tile, 90, 3)
        check("P2a", "'Practice 1 analysis · in progress' tile when results land", bool(an) and an["state"] == "in progress", json.dumps(an or {}))
        tl = {x["id"]: x["state"] for x in (await state(S)).get("tiles", [])}
        check("P2t", "'Practice 1 data · done' and 'Practice 1 · finished' tiles", tl.get("data-Practice-1") == "done" and tl.get("round-Practice-1") == "finished", json.dumps(tl))
        check("P2u", "the same tiles on Dylan's board", bool(await wait_for(_async_state(D, lambda st_: any(x["id"] == "analysis-Practice-1" for x in st_.get("tiles", []))), 40, 2)))
        files = list((out / "pd").rglob("hands-*.jsonl.gz"))
        check("P2b", "results and hand file saved", bool(files) and any((out / "pd").rglob("results.json")))
        await api(s, S, "POST", "/api/agents/s-overview/send", {"text": "run the check"})
        async def pf_dl():
            return next((t for t in (await state(S)).get("overviews", {}).get("s-overview", [])
                         if "hand-history download" in str(t.get("text")) and "saved and verified" in str(t.get("text"))), None)
        check("PF4", "pre-flight downloads and verifies a real hand file once a round has finished", bool(await wait_for(pf_dl, 150, 3)))
        card = out / "repo-s" / "analysis" / "Practice-1" / "card.md"
        check("P3a", "the hub ran the round card script (card.md written)", bool(await wait_for(lambda: _exists(card), 30)))
        inbox = lambda n: json.loads((out / "data-s" / "agents" / n / "inbox.json").read_text()) \
            if (out / "data-s" / "agents" / n / "inbox.json").exists() else []
        def routed():
            return any("Round card for Practice 1" in i.get("text", "") for i in inbox("s-data"))
        check("P3b", "card_ready routed to s-data although fp_train failed", bool(await wait_for(_async(routed), 30)))
        check("P3c", "fp_train failure reported to s-scout", any("fp_train.py" in i.get("text", "") for i in inbox("s-scout")))
        dl = [i for i in inbox("s-data") if "DATA LANDED" in i.get("text", "")]
        lat = (dl[0]["at"] - t_done) if dl else None
        check("H3", "data landed -> the Analyst told within 45 s of the portal marking the round done (30 s polling)", lat is not None and lat < 45, f"{lat}")
        check("P2c", "the Analyst and Samuel's Chat woken with DATA LANDED / NEW ROUND RESULT",
              any("DATA LANDED" in i.get("text", "") for i in inbox("s-data")) and
              any("NEW ROUND RESULT" in i.get("text", "") for i in inbox("s-overview")))
        dinbox = lambda n: json.loads((out / "data-d" / "agents" / n / "inbox.json").read_text()) \
            if (out / "data-d" / "agents" / n / "inbox.json").exists() else []
        check("P2d", "Dylan's Chat told of the result on Dylan's laptop",
              bool(await wait_for(_async(lambda: any("Practice round 1" in i.get("text", "") or "finished" in i.get("text", "")
                                                     for i in dinbox("d-overview"))), 40)))
        # N4: build note B1 closes when the portal runs a bot
        await asyncio.sleep(6)
        dchat = (await state(D)).get("overviews", {}).get("d-overview", [])
        check("C10", "the hub's 'make sure Dylan uploads' message never appears under Dylan's name",
              not any(t.get("who") == "Dylan" and "Make sure Dylan uploads" in str(t.get("text")) for t in dchat))
        # A3: every worker got its minute-0 task from the clock directly (both laptops); the challenger starts later
        got = {n: any("[clock: Build hour, minute 0]" in i.get("text", "") for i in inbox(n)) for n in ("s-data", "s-tester", "s-scout")}
        got.update({n: any("[clock: Build hour, minute 0]" in i.get("text", "") for i in dinbox(n)) for n in ("d-platform", "d-builder", "d-challenger")})
        check("A3", "the clock handed each worker its minute-0 task (challenger: not yet)", all(got[n] for n in ("s-data", "s-tester", "s-scout", "d-platform", "d-builder")) and not got["d-challenger"], str(got))
        async def b1_done():
            return next((x for x in (await state(S)).get("tiles", []) if x["id"] == "build-1" and x["state"] == "done"), None)
        check("N4", "'Build · v1 and the platform' turns done once the portal runs a bot", bool(await wait_for(b1_done, 40)))

        # P7: results that fail at first are retried, not skipped
        portal.results_fail = 2
        portal.rounds.append({"id": "t-practice-2-abcdef", "kind": "practice", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                              "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        async def an2():
            return next((x for x in (await state(S)).get("tiles", []) if x["id"] == "analysis-Practice-2"), None)
        check("P7", "a round whose results fail twice is retried and analysed", bool(await wait_for(an2, 240, 5)))
        pst = json.loads((out / "data-s" / "portal_state.json").read_text())
        check("G6", "landing times are saved (the deadline guard survives a restart)", "Practice 1" in pst.get("landed_at", {}))

        # F1/F3/F4/F5: staged attachment, not sent until Enter
        c, f, _ = await api(s, S, "POST", "/api/upload?hold=1&name=shot.png", None, raw=b"\x89PNG\r\n\x1a\n" + b"0" * 2000)
        check("F1", "staged upload saved but not handed to the Chat",
              c == 200 and f.get("id") and not any("shot.png" in i.get("text", "") for i in inbox("s-overview")), json.dumps(f))
        c, img, _ = await api(s, S, "GET", f"/api/inbox/{f['id']}")
        check("F5", "thumbnail served from /api/inbox/<id>", c == 200 and isinstance(img, (bytes, bytearray)) and img[:4] == b"\x89PNG")
        async def thumb_on_d():
            c, img, _ = await api(s, D, "GET", f"/api/inbox/{f['id']}")
            return c == 200 and img[:4] == b"\x89PNG"
        check("F5b", "the same thumbnail opens from Dylan's laptop (viewing Samuel's Chat)", bool(await wait_for(thumb_on_d, 40, 4)))
        c, d, _ = await api(s, S, "POST", "/api/upload?name=empty.txt", None, raw=b"")
        check("F1b", "empty upload refused", c == 400)

        # H1/B1: Samuel writes into Dylan's Chat; it shows in Dylan's Chat history
        c, d, _ = await api(s, S, "POST", "/api/agents/d-overview/send", {"text": "Dylan's chat: eval ping 42"})
        check("B1a", "message to the other laptop's Chat accepted", c == 200 and d.get("remote"), json.dumps(d))
        async def in_dchat():
            ov = (await state(D)).get("overviews", {}).get("d-overview", [])
            return any("eval ping 42" in str(t.get("text")) for t in ov)
        check("H1", "it appears in Dylan's Chat history", bool(await wait_for(in_dchat, 40, 2)))
        async def in_dchat_on_s():
            ov = (await state(S)).get("overviews", {}).get("d-overview", [])
            return any("eval ping 42" in str(t.get("text")) for t in ov)
        check("H1b", "Samuel sees Dylan's Chat (incl. that line) on his own screen", bool(await wait_for(in_dchat_on_s, 40, 2)))
        c, d, _ = await api(s, S, "POST", "/api/agents/x-nobody/send", {"text": "hi"})
        check("B4", "unknown agent name refused clearly", c == 404, json.dumps(d))
        c, d, _ = await api(s, S, "POST", "/api/agents/s-overview/send", {"text": "  "})
        check("H1c", "empty Chat message refused", c == 400)

        # X2: dismiss an alert on both
        al = await alert_with(S, "REJECTED")
        if al:
            await api(s, S, "POST", f"/api/alerts/{al['id']}/dismiss", {})
        check("X2", "dismissed alert leaves Samuel's bell", not any(x["id"] == (al or {}).get("id") for x in (await state(S))["alerts"]))

        # G5: deadlines service exists only after a cut; approvals endpoint errors cleanly
        c, d, _ = await api(s, S, "POST", "/api/approvals/nope", {"decision": "allow"})
        check("R7b", "answering a vanished permission request gives a clear message", c == 404)

        # S3: restart Samuel's hub; notes, live bot and clock survive; no clock step re-sent
        sent_before = json.loads((out / "data-s" / "clock_sent.json").read_text()) if (out / "data-s" / "clock_sent.json").exists() else []
        props_before = {p["id"] for p in (await state(S))["props"]}
        procs["samuel"].terminate()
        procs["samuel"].wait(15)
        procs["samuel"] = start_hub("samuel", ps, out / "repo-s", out / "data-s", ns, sx, out / "hub-s.log")
        check("S3a", "Samuel's hub comes back", bool(await wait_for(lambda: up(S), 60)))
        x = await state(S)
        check("S3b", "notes survive the restart", props_before <= {p["id"] for p in x["props"]},
              str(len(props_before - {p['id'] for p in x['props']})))
        check("S3c", "clock and live bot survive", bool(x.get("schedule")) and (x.get("live") or {}).get("filename") == "v1.zip")
        ov_s = inbox("s-overview")
        n_b0 = sum(1 for i in ov_s if "Build hour, minute 0" in i.get("text", ""))
        n_w0 = sum(1 for i in inbox("s-data") if "[clock: Build hour, minute 0]" in i.get("text", ""))
        check("S3w", "the clock gave the Analyst its minute-0 task directly, once", n_w0 == 1, f"{n_w0} copies")
        check("S3d", "the minute-0 dispatch was not sent twice", n_b0 <= 1, f"{n_b0} copies; sent marks {len(sent_before)}")
        check("S3e", "the rounds already analysed aren't re-processed as new",
              sum(1 for y in x.get("tiles", []) if y["id"].startswith("analysis-")) == 2 and
              sum(1 for i in inbox("s-data") if "DATA LANDED" in i.get("text", "")) <= 2)
        errs = (out / "data-s" / "errors.log").read_text() if (out / "data-s" / "errors.log").exists() else ""
        check("S8", "no background errors recorded on Samuel's hub", not errs.strip(), errs[:300])

        # C10: a clock that is off by many minutes is flagged against the portal's real round start, in both Chats
        await api(s, S, "POST", "/api/schedule", {"start": time.strftime("%H:%M:%S", time.localtime(time.time() - 1800)),
                                                 "scored": 3, "scale": 0.05})
        portal.rounds.append({"id": "t-practice-3-abcdef", "kind": "practice", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                              "completed_at": None})
        async def drift_told(base, ovn):
            return any("clock looks off" in str(t.get("text")) for t in (await state(base)).get("overviews", {}).get(ovn, []))
        check("C10a", "clock drift vs the portal is flagged in Samuel's Chat", bool(await wait_for(lambda: drift_told(S, "s-overview"), 120, 5)))
        check("C10b", "… and in Dylan's Chat", bool(await wait_for(lambda: drift_told(D, "d-overview"), 60, 3)))

        # H7: a Chat message nobody answers is raised again with the Chat after 150 s (agents are off here)
        await api(s, S, "POST", "/api/agents/s-overview/send", {"text": "what is the live bot doing right now?"})
        await asyncio.sleep(170)
        check("H7", "an unanswered Chat message is re-raised with the Chat",
              any("haven't answered" in i.get("text", "") for i in inbox("s-overview")))

        # S5 view-only preview
        vo = subprocess.Popen([sys.executable, str(HUB / "hub.py"), "--person", "samuel", "--repo", str(out / "repo-s"),
                               "--data", str(out / "data-s"), f"--namespace={ns}", "--port", str(ps + 100), "--view-only"],
                              stdout=open(out / "hub-view.log", "a"), stderr=subprocess.STDOUT, cwd=str(HUB))
        V = f"http://127.0.0.1:{ps + 100}"
        if await wait_for(lambda: up(V), 60):
            c, d, _ = await api(s, V, "POST", "/api/agents/s-overview/send", {"text": "are you there?"})
            ov = (await state(V)).get("overviews", {}).get("s-overview", [])
            check("S5", "view-only preview answers with the preview notice and runs nothing",
                  any("view-only" in str(t.get("text")) for t in ov) and all(g["state"] in ("stopped", "idle") for g in (await state(V))["agents"]))
        else:
            check("S5", "view-only preview starts", False)
        vo.terminate()

    (out / "results.json").write_text(json.dumps(RESULTS, indent=1))
    bad = [r for r in RESULTS if not r["ok"]]
    print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} passed" + (": failed " + ", ".join(r["id"] for r in bad) if bad else ""))
    if a.keep:
        print(f"hubs left running: {S} (samuel), {D} (dylan); portal :{pp}", flush=True)
        await asyncio.Event().wait()
    for p in procs.values():
        p.terminate()
    await runner.cleanup()


def _exists(p: Path):
    async def f():
        return p.exists()
    return f()


def _async_state(base, pred):
    async def f():
        async with ClientSession(timeout=ClientTimeout(total=20)) as s2:
            async with s2.get(base + "/api/state") as r:
                return pred(await r.json())
    return f


def _async(fn):
    async def f():
        return fn()
    return f



if __name__ == "__main__":
    asyncio.run(main())
