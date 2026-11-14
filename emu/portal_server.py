"""A local copy of the event portal for rehearsals: same API paths as the real site, plus simple pages.

Runs next to emu/rehearsal.py and serves ONE team (avalon) for a run:

  prep/.venv/bin/python emu/portal_server.py --run r9            # http://<this Mac>:8765/tournament/

What it does, like the real portal:
  - Upload a zip (page or POST /api/teams/<team>/submissions?filename=x.zip, raw zip body). The upload
    test (20 heads-up hands vs check-or-fold, no time bank, <=10% failed decisions) runs straight away:
    status goes validating -> ready | rejected, with rejection_reason and check_log.
  - Make a ready upload the active bot (page button or PATCH /api/teams/<team> {"active_submission_id"}).
    Activating copies it into emu/runs/<run>/avalon/submission/, which the rehearsal snapshots at each
    round start. A new upload is NOT made active by itself: always confirm the active bot.
  - Rounds, results, standings and our hand-history downloads, read from the rehearsal's own files.
  - Format and Getting started pages (avalon/portal/*.md: without the variant until the start).
  - Upload cooldown: one upload per --cooldown seconds (default: the run's setting, else 30); a sooner
    upload gets 429 with Retry-After. The upload test plays the run's variant on the run's kit.

API (participant paths copied from the real site's front-end code; Bearer key required):
  GET  /api/me                                   GET /api/competitions
  GET  /api/competitions/<cid>                   GET /api/competitions/<cid>/tournaments
  GET  /api/competitions/<cid>/standings         GET /api/competitions/<cid>/teams
  GET  /api/tournaments/<tid>                    GET /api/tournaments/<tid>/results
  GET  /api/teams/<team>   PATCH /api/teams/<team>
  GET  /api/teams/<team>/submissions             POST /api/teams/<team>/submissions?filename=
  GET  /api/teams/<team>/health
  GET  /api/tournaments/<tid>/hands[?subset=first-1000]   (mock only: the real download link is on the
                                                          team and round pages; find it on the day)
The API key is in emu/runs/<run>/avalon/portal/api-key (also printed at start). Keep this server on
your own network: it copies the organizers' site and must never be published.
"""

from __future__ import annotations

import argparse
import html
import io
import json
import math
import re
import shutil
import secrets
import socket
import sys
import threading
import time
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "emu"))
from pilot import upload_test  # noqa: E402

TEAM = "avalon"
NS = uuid.UUID("6f1c3c2e-6c55-4c8e-9a39-0b6a1d2f7a11")
uid = lambda *parts: str(uuid.uuid5(NS, "/".join(parts)))  # noqa: E731
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))  # noqa: E731


class Portal:
    def __init__(self, run: str, cooldown: int | None = None):
        self.run = run
        self.dir = ROOT / "emu" / "runs" / run
        self.ws = self.dir / TEAM
        self.store = self.ws / "portal_uploads"
        self.store.mkdir(parents=True, exist_ok=True)
        self.state_file = self.ws / "portal_state.json"
        self.lock = threading.Lock()
        self.state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {"subs": [], "active": None}
        # One key for every rehearsal run, so links shared with a teammate keep working.
        stable = Path.home() / ".config" / "avalon-rehearsal" / "portal-key"
        stable.parent.mkdir(parents=True, exist_ok=True)
        if not stable.exists():
            old = self.ws / "portal" / "api-key"
            stable.write_text(old.read_text() if old.exists() else "nlk_" + secrets.token_hex(16) + "\n")
            stable.chmod(0o600)
        self.key = stable.read_text().strip()
        keyf = self.ws / "portal" / "api-key"
        keyf.parent.mkdir(parents=True, exist_ok=True)
        keyf.write_text(self.key + "\n")
        sf = self.dir / "settings.json"  # written by rehearsal.py: variant, cooldown, kit
        self.settings = json.loads(sf.read_text()) if sf.exists() else {}
        self.cooldown = cooldown if cooldown is not None else int(self.settings.get("cooldown", 30))
        self.cid = uid(run, "competition")
        self.team_id = uid(run, "team", TEAM)

    def save(self):
        self.state_file.write_text(json.dumps(self.state, indent=1))

    # ---- rounds, results, standings (read from the rehearsal's files) ----
    def event(self):
        f = self.dir / "event.json"
        return json.loads(f.read_text()) if f.exists() else None

    def rounds(self):
        ev = self.event()
        if not ev:
            return []
        out, now = [], time.time()
        for e in ev["events"]:
            start = ev["start"] + e["t"]
            if start > now:
                continue
            name = f"{e['kind']}{e['n']}"
            if not (self.dir / "rounds" / name).exists():
                continue  # the tournament never started this round (e.g. the run was stopped)
            rj = self.dir / "rounds" / name / "round.json"
            r = json.loads(rj.read_text()) if rj.exists() else {}
            done = bool(r.get("scores"))
            w = e["n"] if e["kind"] == "scored" else 0
            m = re.search(r"\(x(\d+)\)", e.get("label", ""))
            if m:
                w = int(m.group(1))
            out.append({"id": r.get("tournament_id") or uid(self.run, name), "name": name, "label": e["label"],
                        "kind": e["kind"], "weight": w, "iterations": r.get("iterations", 0),
                        "created_at": iso(start), "completed_at": iso(rj.stat().st_mtime) if done else None,
                        "round": r, "done": done})
        return out

    def find_round(self, tid):
        return next((r for r in self.rounds() if r["id"] == tid), None)

    def results(self, rd):
        r = rd["round"]
        items = []
        moe = self.margins(rd["name"])
        forfeit = set(json.loads((self.dir / "rounds" / rd["name"] / "field.json").read_text()).get("forfeit", [])) \
            if (self.dir / "rounds" / rd["name"] / "field.json").exists() else set()
        for team, s in (r.get("scores") or {}).items():
            places = [s["places"].get(str(i), 0.0) for i in range(1, 9)]
            items.append({"team_id": uid(self.run, "team", team), "team_name": team, "forfeited": team in forfeit,
                          "tables": s["tables"], "average_points": s["points"], "margin_of_error": moe.get(team),
                          "places": places})
        items.sort(key=lambda x: -x["average_points"])
        return {"tournament_id": rd["id"], "status": "completed" if rd["done"] else "running", "items": items}

    def margins(self, name):
        f = self.dir / "rounds" / name / "results.jsonl"
        if not f.exists():
            return {}
        pts: dict[str, list] = {}
        for line in f.open():
            d = json.loads(line)
            for team, p, fill in zip(d["seats"], d["points"], d["fillers"]):
                if not fill:
                    pts.setdefault(team, []).append(p)
        out = {}
        for team, xs in pts.items():
            n = len(xs)
            if n > 1:
                m = sum(xs) / n
                sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
                out[team] = round(1.96 * sd / math.sqrt(n), 2)
        return out

    def standings(self):
        tot: dict[str, dict] = {}
        for rd in self.rounds():
            if rd["kind"] != "scored" or not rd["done"]:
                continue
            for it in self.results(rd)["items"]:
                t = tot.setdefault(it["team_name"], {"team_id": it["team_id"], "team_name": it["team_name"],
                                                    "total": 0.0, "tournaments": []})
                t["total"] += rd["weight"] * it["average_points"]
                t["tournaments"].append({"tournament_id": rd["id"], "weight": rd["weight"],
                                         "average_points": it["average_points"]})
        items = sorted(tot.values(), key=lambda x: -x["total"])
        for i, x in enumerate(items, 1):
            x.update(rank=i, disqualified=False, school=None, tie_broken=False, previous_rank=None,
                     total=round(x["total"], 2))
        return {"items": items, "held": False}

    # ---- submissions ----
    def sub_view(self, s):
        return {k: s.get(k) for k in ("id", "team_id", "account_id", "filename", "rejection_reason", "check_log",
                                       "status", "size_bytes", "created_at", "sha256")}

    def team(self):
        a = next((s for s in self.state["subs"] if s["id"] == self.state["active"]), None)
        return {"id": self.team_id, "competition_id": self.cid, "name": TEAM, "school": None,
                "active_submission_id": self.state["active"], "active_filename": a and a["filename"],
                "active_created_at": a and a["created_at"], "members": [],
                "submissions": [self.sub_view(s) for s in reversed(self.state["subs"])], "health": self.health()}

    def health(self):
        out = []
        for rd in self.rounds():
            s = (rd["round"].get("scores") or {}).get(TEAM)
            if s:
                out.append({"tournament_id": rd["id"], "kind": rd["kind"], "weight": rd["weight"],
                            "created_at": rd["created_at"], "submission_id": None, "decisions": s.get("decisions", 0),
                            "missed": s.get("failed_decisions", 0), "restarts": 0, "gave_up": False, "error_log": ""})
        return out

    def started(self):
        ev = self.event()
        return bool(ev) and ev["start"] <= time.time()

    def cooldown_left(self):
        last = self.state.get("last_upload", 0)
        return max(0, math.ceil(last + self.cooldown - time.time()))

    def upload(self, filename: str, body: bytes):
        sid = str(uuid.uuid4())
        import hashlib
        s = {"id": sid, "team_id": self.team_id, "account_id": uid(self.run, "account"), "filename": filename,
             "status": "validating", "rejection_reason": None, "check_log": None, "size_bytes": len(body),
             "created_at": iso(time.time()), "sha256": hashlib.sha256(body).hexdigest()}
        d = self.store / sid
        d.mkdir(parents=True)
        (d / "upload.zip").write_bytes(body)
        with self.lock:
            self.state["subs"].append(s)
            self.state["last_upload"] = time.time()
            self.save()
        threading.Thread(target=self.check, args=(s,), daemon=True).start()
        return s

    def check(self, s):
        d = self.store / s["id"]
        bot = d / "bot"
        reason, log = None, ""
        try:
            if s["size_bytes"] > 50 * 1024 * 1024:
                raise ValueError("upload is over 50 MB")
            with zipfile.ZipFile(io.BytesIO((d / "upload.zip").read_bytes())) as z:
                names = z.namelist()
                if len(names) > 1000:
                    raise ValueError("more than 1,000 entries")
                for n in names:
                    if n.startswith("/") or ".." in Path(n).parts:
                        raise ValueError(f"unsafe path in zip: {n}")
                z.extractall(bot)
            pys = list(bot.rglob("*.py"))
            for p in pys:
                if re.search(r"^\s*(import|from)\s+(poker_engine|pokerkit)\b", p.read_text(errors="ignore"), re.M):
                    raise ValueError(f"{p.relative_to(bot)} imports poker_engine or pokerkit")
            if not (bot / "agent.py").is_file():
                raise ValueError("no agent.py at the root of the upload")
            r = upload_test(bot, self.settings.get("variant"), self.settings.get("kit"))
            log = json.dumps(r)
            if not r["ok"]:
                reason = r["reason"]
        except (ValueError, zipfile.BadZipFile, OSError) as e:
            reason = str(e)
        with self.lock:
            s.update(status="rejected" if reason else "ready", rejection_reason=reason, check_log=log or reason)
            self.save()

    def activate(self, sid):
        s = next((x for x in self.state["subs"] if x["id"] == sid), None)
        if not s:
            return 404, {"detail": "no such submission"}
        if s["status"] != "ready":
            return 409, {"detail": f"submission is {s['status']}, only a ready upload can be made active"}
        sub = self.ws / "submission"
        tmp = self.ws / ".submission.new"
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(self.store / sid / "bot", tmp, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.rmtree(sub, ignore_errors=True)
        tmp.rename(sub)
        with self.lock:
            self.state["active"] = sid
            self.save()
        return 200, self.team()

    def hands_file(self, rd, subset):
        d = self.ws / "downloads" / rd["name"]
        if not d.exists():
            return None
        files = sorted(d.glob("hands-*.jsonl.gz"))
        want = [f for f in files if f.name.endswith("-first-1000.jsonl.gz")] if subset else \
            [f for f in files if not f.name.endswith("-first-1000.jsonl.gz")]
        return want[0] if want else None


# ---------------------------------------------------------------- pages
CSS = """
:root{--bg:#f5f6f8;--panel:#fff;--fg:#1b1f24;--muted:#646d78;--line:#dfe3e8;--accent:#2457c5;--ok:#1d7a46;--bad:#b42318;--warn:#8a5a00}
@media (prefers-color-scheme:dark){:root{--bg:#121417;--panel:#1a1d21;--fg:#e6e9ed;--muted:#9aa3ad;--line:#2b3036;--accent:#7aa2ff;--ok:#5ccf8f;--bad:#ff8a80;--warn:#f0c062}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,sans-serif}
.wrap{max-width:1050px;margin:0 auto;padding:0 16px 48px}
header{background:var(--panel);border-bottom:1px solid var(--line)}
header .wrap{display:flex;gap:18px;align-items:center;flex-wrap:wrap;padding-top:12px;padding-bottom:12px}
header b{font-size:1.05rem} header a{color:var(--muted);text-decoration:none} header a.on{color:var(--fg);font-weight:600}
h1{font-size:1.3rem;margin:22px 0 6px} h2{font-size:1.05rem;margin:24px 0 8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:10px 0}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums} .tw{overflow-x:auto}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;font-size:.92rem;white-space:nowrap}
th{color:var(--muted);font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em}
.ready{color:var(--ok);font-weight:600}.rejected{color:var(--bad);font-weight:600}.validating{color:var(--warn);font-weight:600}
.md th,.md td{white-space:normal} .md code{font-size:.9em} .md pre{overflow-x:auto}
.me td{font-weight:700} .muted{color:var(--muted)} a{color:var(--accent)}
button{font:inherit;padding:5px 12px;border-radius:6px;border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}
button.ghost{background:none;color:var(--accent)} .big{font-size:1.15rem;font-weight:700}
"""


def page(title, body, on=""):
    nav = "".join(f'<a class="{"on" if on == k else ""}" href="/tournament/{k}">{v}</a>'
                  for k, v in (("team", "Team"), ("rounds", "Rounds"), ("standings", "Standings"), ("format", "Format")))
    return (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,"
            f"initial-scale=1'><title>{html.escape(title)} · No Limit (rehearsal)</title><style>{CSS}</style>"
            f"</head><body><header><div class=wrap><b>No Limit · rehearsal portal</b>{nav}</div></header>"
            f"<div class=wrap>{body}</div></body></html>")


def md_inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\w)", r"<i>\1</i>", t)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"<a href='\2'>\1</a>", t)


def md_html(text):
    """Enough Markdown for the portal pages: headings, paragraphs, lists, tables, code blocks."""
    out, para, lines, i = [], [], text.splitlines(), 0

    def flush():
        if para:
            out.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para.clear()
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            flush()
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        if m := re.match(r"(#{1,6})\s+(.*)", ln):
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{md_inline(m.group(2))}</h{n}>")
        elif ln.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            head, *body = rows or [[]]
            out.append("<div class=tw><table><tr>" + "".join(f"<th>{md_inline(c)}</th>" for c in head) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in body)
                       + "</table></div>")
            continue
        elif re.match(r"\s*([-*]|\d+\.)\s+", ln):
            flush()
            tag = "ol" if re.match(r"\s*\d+\.", ln) else "ul"
            items = []
            while i < len(lines) and (re.match(r"\s*([-*]|\d+\.)\s+", lines[i])
                                      or (lines[i].startswith("  ") and lines[i].strip() and items)):
                if re.match(r"\s*([-*]|\d+\.)\s+", lines[i]):
                    items.append(re.sub(r"\s*([-*]|\d+\.)\s+", "", lines[i], count=1))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{md_inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        elif not ln.strip():
            flush()
        else:
            para.append(ln.strip())
        i += 1
    flush()
    return "\n".join(out)


def fmt_t(s):
    import calendar
    return time.strftime("%H:%M:%S", time.localtime(calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")))) if s else ""


class Handler(BaseHTTPRequestHandler):
    P: Portal = None  # type: ignore

    def log_message(self, *a):
        pass

    def authed(self):
        k = self.P.key
        h = self.headers.get("Authorization", "")
        if h == f"Bearer {k}":
            return True
        c = self.headers.get("Cookie", "")
        return f"nlk={k}" in c

    def send(self, code, body, ctype="application/json", extra=None):
        data = body if isinstance(body, bytes) else (json.dumps(body) if ctype == "application/json" else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text") else ""))
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        p = u.path.rstrip("/")
        if p.startswith("/tournament/login"):
            if q.get("key", [""])[0] == self.P.key:
                return self.send(302, b"", "text/plain", {"Set-Cookie": f"nlk={self.P.key}; Path=/; HttpOnly",
                                                           "Location": "/tournament/team"})
            return self.send(200, page("Sign in", "<h1>Sign in</h1><form class=card><p>API key (in "
                                       "<code>emu/runs/&lt;run&gt;/avalon/portal/api-key</code>)</p><input name=key "
                                       "size=44 autofocus> <button>Sign in</button></form>"), "text/html")
        if p.startswith("/tournament/api") or p.startswith("/api"):
            if not self.authed():
                return self.send(401, {"detail": "Missing or invalid API key"})
            return self.api_get(p.split("/api", 1)[1], q)
        if not self.authed():
            return self.send(302, b"", "text/plain", {"Location": "/tournament/login"})
        return self.page_get(p, q)

    def do_POST(self):
        u = urlparse(self.path)
        p = u.path.split("/api", 1)[-1].rstrip("/")
        if not self.authed():
            return self.send(401, {"detail": "Missing or invalid API key"})
        m = re.fullmatch(r"/teams/([^/]+)/submissions", p)
        if m and m.group(1) in (self.P.team_id, TEAM):
            fn = parse_qs(u.query).get("filename", ["upload.zip"])[0]
            n = int(self.headers.get("Content-Length", "0"))
            if n > 50 * 1024 * 1024:
                return self.send(413, {"detail": "upload is over 50 MB"})
            body = self.rfile.read(n)
            with self.P.lock:
                wait = self.P.cooldown_left()
            if wait:
                return self.send(429, {"detail": f"Your team can upload once every {self.P.cooldown} seconds. "
                                                 f"Try again in {wait} s."}, extra={"Retry-After": str(wait)})
            s = self.P.upload(fn, body)
            return self.send(201, self.P.sub_view(s))
        return self.send(404, {"detail": "not found"})

    def do_PATCH(self):
        p = urlparse(self.path).path.split("/api", 1)[-1].rstrip("/")
        if not self.authed():
            return self.send(401, {"detail": "Missing or invalid API key"})
        m = re.fullmatch(r"/teams/([^/]+)", p)
        if m and m.group(1) in (self.P.team_id, TEAM):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
            if "active_submission_id" in body:
                code, out = self.P.activate(body["active_submission_id"])
                return self.send(code, out)
            return self.send(200, self.P.team())
        return self.send(404, {"detail": "not found"})

    def api_get(self, p, q):
        P = self.P
        p = p.rstrip("/")
        comp = {"id": P.cid, "name": f"No Limit rehearsal ({P.run})", "upload_cooldown_seconds": P.cooldown,
                "variant": P.settings.get("variant", "flop_discard_reveal") if P.started() else None}
        if p == "/auth/api-key":   # what the real portal answers for an API key (its /me is browser-only)
            return self.send(200, {"expires_at": "2026-12-31T00:00:00Z", "ends_with": P.key[-8:],
                                   "teams": [{"competition_id": P.cid, "team_id": P.team_id}]})
        if p == "/me":
            return self.send(200, {"id": uid(P.run, "account"), "email": "avalon@rehearsal",
                                   "teams": [{"id": P.team_id, "name": TEAM, "competition_id": P.cid}]})
        if p == "/competitions":
            return self.send(200, {"items": [comp]})
        if p == f"/competitions/{P.cid}":
            return self.send(200, comp)
        if p == f"/competitions/{P.cid}/tournaments":
            return self.send(200, {"items": [{"id": r["id"], "competition_id": P.cid, "kind": r["kind"],
                                              "weight": r["weight"], "iterations": r["iterations"],
                                              "label": r["label"], "created_at": r["created_at"],
                                              "completed_at": r["completed_at"], "cancelled_at": None}
                                             for r in P.rounds()]})
        if p == f"/competitions/{P.cid}/standings":
            return self.send(200, P.standings())
        if p == f"/competitions/{P.cid}/teams":
            ev = P.event() or {"teams": {}}
            return self.send(200, {"items": [{"id": uid(P.run, "team", t), "name": t} for t in list(ev["teams"]) + [TEAM]]})
        m = re.fullmatch(r"/tournaments/([^/]+)(/results|/hands)?", p)
        if m:
            rd = P.find_round(m.group(1))
            if not rd:
                return self.send(404, {"detail": "no such round"})
            if m.group(2) == "/results":
                return self.send(200, P.results(rd))
            if m.group(2) == "/hands":
                f = P.hands_file(rd, q.get("subset", [""])[0] == "first-1000")
                if not f:
                    return self.send(404, {"detail": "hand history not ready"})
                return self.send(200, f.read_bytes(), "application/gzip",
                                 {"Content-Disposition": f'attachment; filename="{f.name}"'})
            return self.send(200, {k: rd[k] for k in ("id", "kind", "weight", "iterations", "label", "created_at",
                                                     "completed_at")})
        m = re.fullmatch(r"/teams/([^/]+)(/submissions|/health)?", p)
        if m and m.group(1) in (P.team_id, TEAM):
            t = P.team()
            return self.send(200, {"": t, "/submissions": {"items": t["submissions"]},
                                   "/health": {"items": t["health"]}}[m.group(2) or ""])
        return self.send(404, {"detail": "not found"})

    def page_get(self, p, q):
        P = self.P
        if p in ("/tournament", "", "/tournament/team"):
            t = P.team()
            act = next((s for s in t["submissions"] if s["id"] == t["active_submission_id"]), None)
            def action(s):
                if s["id"] == t["active_submission_id"]:
                    return "<b>Active</b>"
                if s["status"] == "ready":
                    return '<button onclick="act(\'%s\')">Make active</button>' % s["id"]
                return ""
            rows = "".join(
                f"<tr><td>{fmt_t(s['created_at'])}</td><td>{html.escape(s['filename'])}</td>"
                f"<td class={s['status']}>{s['status']}</td><td class=muted>{html.escape(s['rejection_reason'] or '')}</td>"
                f"<td>{action(s)}</td></tr>"
                for s in t["submissions"])
            body = (f"<h1>Team avalon</h1><div class=card><div class=muted>Active bot</div><div class=big>"
                    f"{html.escape(act['filename']) + ' · uploaded ' + fmt_t(act['created_at']) if act else 'None: you forfeit any round that starts now'}"
                    f"</div></div><h2>Upload</h2><div class=card><input type=file id=f accept=.zip> "
                    f"<button onclick=up()>Upload</button> <span id=msg class=muted>A .zip with agent.py at its root. "
                    f"The upload test runs at once; then make it active. One upload every {P.cooldown} s.</span></div>"
                    f"<h2>Uploads</h2><div class='card tw'><table><tr><th>Time</th><th>File</th><th>Status</th>"
                    f"<th>Reason</th><th></th></tr>{rows or '<tr><td colspan=5 class=muted>No uploads yet</td></tr>'}"
                    f"</table></div><script>"
                    f"async function up(){{const f=document.getElementById('f').files[0];if(!f)return;"
                    f"document.getElementById('msg').textContent='Uploading…';"
                    f"const r=await fetch('/tournament/api/teams/{TEAM}/submissions?filename='+encodeURIComponent(f.name),{{method:'POST',body:f}});"
                    f"if(!r.ok){{document.getElementById('msg').textContent='Upload refused: '+(await r.json()).detail;return}}"
                    f"document.getElementById('msg').textContent='Uploaded; testing…';setTimeout(()=>location.reload(),1500)}}"
                    f"async function act(id){{const r=await fetch('/tournament/api/teams/{TEAM}',{{method:'PATCH',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{active_submission_id:id}})}});"
                    f"if(!r.ok)alert((await r.json()).detail);location.reload()}}"
                    f"if([...document.querySelectorAll('.validating')].length)setTimeout(()=>location.reload(),3000)"
                    f"</script>")
            return self.send(200, page("Team", body, "team"), "text/html")
        if p == "/tournament/rounds":
            rows = "".join(
                f"<tr><td><a href='/tournament/rounds/{r['id']}'>{html.escape(r['label'])}</a></td>"
                f"<td>{fmt_t(r['created_at'])}</td><td>{'completed ' + fmt_t(r['completed_at']) if r['done'] else 'running'}</td></tr>"
                for r in reversed(P.rounds()))
            return self.send(200, page("Rounds", f"<h1>Rounds</h1><div class='card tw'><table><tr><th>Round</th>"
                                       f"<th>Started</th><th>Status</th></tr>{rows or '<tr><td colspan=3 class=muted>No rounds yet</td></tr>'}"
                                       f"</table></div>", "rounds"), "text/html")
        m = re.fullmatch(r"/tournament/rounds/([^/]+)", p)
        if m:
            rd = P.find_round(m.group(1))
            if not rd:
                return self.send(404, page("Round", "<h1>No such round</h1>"), "text/html")
            res = P.results(rd)
            rows = "".join(
                f"<tr class={'me' if it['team_name'] == TEAM else ''}><td>{i}</td><td>{html.escape(it['team_name'])}</td>"
                f"<td>{it['average_points']:.2f}</td><td>±{it['margin_of_error'] or 0:.2f}</td>"
                + "".join(f"<td>{x * 100:.1f}%</td>" for x in it["places"][:3]) + "</tr>"
                for i, it in enumerate(res["items"], 1))
            dl = ""
            if P.hands_file(rd, False):
                dl = (f"<h2>Your hand history</h2><div class=card><a href='/tournament/api/tournaments/{rd['id']}/hands'>"
                      f"Full</a> · <a href='/tournament/api/tournaments/{rd['id']}/hands?subset=first-1000'>First 1,000</a></div>")
            return self.send(200, page(rd["label"], f"<h1>{html.escape(rd['label'])}</h1><p class=muted>"
                                       f"{'Completed ' + fmt_t(rd['completed_at']) if rd['done'] else 'Running: results land when it finishes'}</p>"
                                       f"<div class='card tw'><table><tr><th>#</th><th>Team</th><th>Points/table</th>"
                                       f"<th>Margin</th><th>1st</th><th>2nd</th><th>3rd</th></tr>{rows}</table></div>{dl}",
                                       "rounds"), "text/html")
        if p in ("/tournament/format", "/tournament/getting-started"):
            name = "format.md" if p.endswith("format") else "getting-started.md"
            f = P.ws / "portal" / name
            text = f.read_text() if f.exists() else "# Not published yet"
            other = ("<a href='/tournament/getting-started'>Getting started</a>" if name == "format.md"
                     else "<a href='/tournament/format'>Format</a>")
            note = "" if P.started() else "<p class=muted>The variant is announced at the start of the event.</p>"
            body = (f"<div class='card md'>{note}<p class=muted>Upload cooldown: {P.cooldown} s · {other}</p>"
                    f"{md_html(text)}</div>")
            return self.send(200, page("Format" if name == "format.md" else "Getting started", body, "format"),
                             "text/html")
        if p == "/tournament/standings":
            st = P.standings()["items"]
            rows = "".join(f"<tr class={'me' if x['team_name'] == TEAM else ''}><td>{x['rank']}</td>"
                           f"<td>{html.escape(x['team_name'])}</td><td>{x['total']:.2f}</td></tr>" for x in st)
            return self.send(200, page("Standings", f"<h1>Standings</h1><div class='card tw'><table><tr><th>Rank</th>"
                                       f"<th>Team</th><th>Total</th></tr>{rows or '<tr><td colspan=3 class=muted>No scored rounds yet</td></tr>'}"
                                       f"</table></div>", "standings"), "text/html")
        return self.send(404, page("Not found", "<h1>Not found</h1>"), "text/html")


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--cooldown", type=int, default=None, help="upload cooldown, seconds (default: the run's, else 30)")
    ap.add_argument("--host", default="0.0.0.0", help="0.0.0.0 = reachable on your Wi-Fi; 127.0.0.1 = this Mac only")
    a = ap.parse_args()
    Handler.P = Portal(a.run, a.cooldown)
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    ip = lan_ip()
    print(f"rehearsal portal for run {a.run}: http://{ip}:{a.port}/tournament/  (this Mac: http://127.0.0.1:{a.port}/tournament/)")
    print(f"API base: http://{ip}:{a.port}/tournament/api   key: {Handler.P.key}")
    print(f"team id: {Handler.P.team_id}   competition id: {Handler.P.cid}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
