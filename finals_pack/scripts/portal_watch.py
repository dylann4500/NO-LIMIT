#!/usr/bin/env python3
"""Read the organizers' portal (READ-ONLY) for the whole event: save each round's results and our hand data, keep
state/status.md current, and post every event to the inboxes. A human starts it in its own terminal tab.

  python3 scripts/portal_watch.py                 # the watcher: leave it running
  python3 scripts/portal_watch.py --once          # one poll: prints the team, competition and what it saw
  python3 scripts/portal_watch.py --set-hands-url '<the hand download link copied from the portal>'
                                                  # no restart needed: the running watcher picks it up
Options:
  --base URL          default https://pokerbot.sequoiacap.com/tournament/api (rehearsal: http://<mac>:8765/tournament/api)
  --key-file PATH     default ~/.config/no-limit-2026/api-key (never printed)
  --hands-url TPL     hand download template, or a copied link: {tid} = round id, {team} = our team id, {q} = the
                      first-1000 query ('?tables=1000&subset=first-1000') or '' (full), {qa} = the same with '&'
                      (links that already have a query). Not needed normally: the watcher tries the real portal's
                      <base>/teams/{team}/tournaments/{tid}/hands{q}, then the rehearsal copy's
                      <base>/tournaments/{tid}/hands{q}
  --small-hands       only the first-1000 file (on a phone hotspot)

GET requests only, User-Agent avalon-portal-watch/1.0, Bearer key (sent only to the portal's own site; dropped on
a redirect elsewhere). Polls every 15 s; every 6 s from 2 to 15 event-minutes after a round's scheduled start
(state/schedule.json) until its result lands.
Writes: data/rounds/NN-<stage>/ (results.json, round.json, hands-first-1000.jsonl.gz, hands-full.jsonl.gz,
played_by.txt), state/status.md, state/rounds_seen.json (for the clock), state/portal.json (its own state), and
state/variant.md (the variant's rules text from the portal, once, when it is announced).
Runs analysis/roundcard.py and analysis/fp_train.py on each new round folder if they exist.
A round that finished more than 12 hours before the watcher first saw it (the regional's, while the Finals isn't on
our key yet) keeps its results but gets no hand files. Once a minute the watcher looks whether a newer competition
has appeared on the key and switches to it by itself.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import io
import ipaddress
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clock as C  # noqa: E402
from say import post  # noqa: E402

ROOT = C.ROOT
UA = "avalon-portal-watch/1.0"
BASE = "https://pokerbot.sequoiacap.com/tournament/api"
KEYFILE = "~/.config/no-limit-2026/api-key"
SLOW, FAST = 15, 6
# Hand downloads. The real portal (checked on 14 Nov against the regional's rounds, byte for byte against our files):
#   GET <base>/teams/<team>/tournaments/<round>/hands             the full file
#   GET <base>/teams/<team>/tournaments/<round>/hands?tables=1000 the first 1,000 tables
# It IGNORES ?subset=... (and then sends the full file), so the small query carries both names: the rehearsal copy
# (emu/portal_server.py) serves <base>/tournaments/<round>/hands and reads ?subset=first-1000. The shapes are tried
# in this order until one gives hand data; a link set with --set-hands-url goes first.
SMALL_Q = "tables=1000&subset=first-1000"
SMALL_KEYS = ("tables=", "subset=")
HANDS_TEMPLATES = ("{base}/teams/{team}/tournaments/{tid}/hands{q}", "{base}/tournaments/{tid}/hands{q}")
OLD_ROUND_S = 12 * 3600   # a round that finished longer ago than this isn't today's: its results are kept, no hand files
FOLLOW_KEY_S = 60         # how often to look whether a newer competition (the Finals) has appeared on our key
# "submission_cooldown_seconds" and "frozen" are the real portal's names; "upload_cooldown_seconds" the rehearsal copy's
COMP_KEYS = ("final_weight", "final_revealed_at", "leaderboard_held", "round_weighting", "weights",
             "icm_luck_correction", "upload_cooldown_seconds", "submission_cooldown_seconds", "frozen")
RUNPY = ("import runpy, sys; sys.path.insert(0, sys.argv[1]); sys.argv = sys.argv[2:]; "
         "runpy.run_path(sys.argv[0], run_name='__main__')")
DEFAULT_ST = {"done": [], "done_stages": [], "subs": [], "need_hands": {}, "landed_at": {}, "played_by": {},
              "seen_start": {}, "checked": [], "results": {}, "fails": 0}


# ------------------------------------------------------------------ helpers
def ts_of(x):
    """An ISO time from the portal -> epoch seconds (None if unreadable)."""
    if not x:
        return None
    try:
        s = str(x).strip().replace("Z", "+00:00")
        s = re.sub(r"(\.\d{6})\d+", r"\1", s)            # Python 3.9 reads at most 6 decimals
        s = re.sub(r"\.(\d{1,5})(?=[+-]|$)", lambda m: "." + m.group(1).ljust(6, "0"), s)
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, TypeError):
        return None


def same_site(a: str, b: str) -> bool:
    """The portal's own site: the same host, or the same registrable domain (api.x.com and x.com)."""
    ha, hb = (urlsplit(a).hostname or "").lower(), (urlsplit(b).hostname or "").lower()
    if not ha or not hb:
        return False
    if ha == hb:
        return True
    for h in (ha, hb):
        try:
            ipaddress.ip_address(h)
            return False
        except ValueError:
            pass
    return ha.split(".")[-2:] == hb.split(".")[-2:] and len(ha.split(".")) >= 2


class _KeyStaysHome(urllib.request.HTTPRedirectHandler):
    """urllib copies every header onto a redirect: never carry our key to another site (a signed storage link)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and not same_site(newurl, req.full_url):
            new.remove_header("Authorization")
        return new


def to_template(url: str, known_ids) -> tuple:
    """A hand-download link copied from the portal -> a template with {tid} and {q}/{qa} (hub.py's set_hands_url)."""
    url = str(url or "").strip().strip("<>").strip("'\"").rstrip(".,)")
    if not url.startswith("http"):
        return None, "That isn't a link (it should start with http)."
    if "{tid}" not in url:
        ids = sorted({i for i in known_ids if i}, key=len, reverse=True)
        hit = next((i for i in ids if i in url), None)
        if not hit:
            m = re.search(r"/(?:tournaments|rounds?)/([^/?#]+)", url)
            hit = m.group(1) if m else None
        if not hit:
            return None, "I couldn't find the round's id in that link. Paste the link of a round's hand download as copied."
        url = url.replace(hit, "{tid}")
    if "{q}" not in url and "{qa}" not in url:
        u = urlsplit(url)
        rest = [p for p in u.query.split("&") if p and not p.startswith(SMALL_KEYS)]   # keep a signature as it was
        url = urlunsplit(u._replace(query="&".join(rest))) + ("{qa}" if rest else "{q}")
    return url, f"Hand-history link set: {url}"


def first_reason(old, new: str) -> str:
    """Which download failure to show when several addresses were tried: the first, unless it was only a 404."""
    return new if (old is None or ("404" in old and "404" not in new)) else old


def rel(root: Path, p) -> str:
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(p)


def mb(n: int) -> str:
    return f"{n / 1e6:.1f} MB"


# ------------------------------------------------------------------ the watcher
class Watcher:
    def __init__(self, root, base: str, keyfile: str, hands_url: str | None = None, small_only: bool = False,
                 echo: bool = True):
        self.root = Path(root)
        self.out = self.root / "data" / "rounds"
        self.statef = C.sp(self.root, "portal.json")
        self.base = base.rstrip("/")
        self.key = Path(keyfile).expanduser().read_text().strip()   # never printed
        if not self.key:
            raise ValueError(f"the key file {keyfile} is empty")
        self.opener = urllib.request.build_opener(_KeyStaysHome)
        self.small_only, self.echo = small_only, echo
        self.st = dict(copy.deepcopy(DEFAULT_ST), **C.load_json(self.statef, {}))   # never share the default's lists
        self.checked = set(self.st.get("checked") or [])
        self.cid, self.team = None, None
        self.team_name, self.comp_name = self.st.get("team_name") or "avalon", self.st.get("comp_name") or ""
        self.threads: list = []
        self.full_jobs: set = set()
        self.posted: list = []
        self.hands_ok = None     # the download shape that last gave hand data (tried first from then on)
        self.ident_at = 0.0      # when we last asked the portal which competition this key plays in
        self.cli_hands = bool(hands_url)
        if hands_url:
            tpl, msg = to_template(hands_url, self.known_ids())
            if not tpl:
                raise ValueError(msg)
            self.st["hands_url"], self.st["hands_url_at"] = tpl, time.time()

    # -------------------------------------------------- plumbing
    def say(self, to: str, text: str) -> None:
        post(to, text, "portal", root=self.root)
        self.posted.append((to, text))
        if self.echo:
            C.quiet(f"-> {to}: {C.short(text, 160)}")

    def known_ids(self):
        return set(self.st.get("done") or []) | set((self.st.get("need_hands") or {}).keys()) | \
            set((self.st.get("seen_start") or {}).keys())

    def hands_urls(self) -> list:
        """The hand-download shapes to try, best first: a link a human set, the shape that last worked, the known ones."""
        out = []
        for t in [self.st.get("hands_url"), self.hands_ok] + [t.replace("{base}", self.base) for t in HANDS_TEMPLATES]:
            if t and t not in out:
                out.append(t)
        return out

    def adopt(self, disk: dict) -> None:
        """A hands link set from the command line while this runs (newer than ours): use it, retry at once."""
        if (disk.get("hands_url_at") or 0) > (self.st.get("hands_url_at") or 0) and disk.get("hands_url"):
            self.st["hands_url"], self.st["hands_url_at"] = disk["hands_url"], disk["hands_url_at"]
            for info in (self.st.get("need_hands") or {}).values():
                info["since"] = time.time()
                info.pop("pinged", None)
                info.pop("warned", None)
            if self.echo:
                C.quiet(f"using the new hands link: {self.st['hands_url']}")

    def sync(self) -> None:
        self.adopt(C.load_json(self.statef, {}))

    def save(self) -> None:
        with C.Lock(self.root, ".portal.lock"):
            self.adopt(C.load_json(self.statef, {}))
            self.st["checked"] = sorted(self.checked)
            C.write_json(self.statef, self.st)

    def get(self, path: str, raw: bool = False):
        url = path if path.startswith("http") else self.base + path
        h = {"User-Agent": UA, "Accept": "*/*" if raw else "application/json"}
        if same_site(url, self.base):
            h["Authorization"] = f"Bearer {self.key}"
        req = urllib.request.Request(url, headers=h, method="GET")
        with self.opener.open(req, timeout=120 if raw else 20) as r:
            data = r.read()
        if raw:
            return data
        return json.loads(data.decode("utf-8") or "null")

    def schedule(self):
        return C.load_json(C.sp(self.root, "schedule.json"), None)

    # -------------------------------------------------- who we are
    def pick_team(self) -> dict:
        """The team (and its competition) this key plays for right now: the newest competition when the key lists
        several (the regional and the Finals), or the one named by AVALON_COMPETITION_ID."""
        teams, last, answered = [], None, False
        for path in ("/auth/api-key", "/me"):   # the real portal answers /auth/api-key for API keys
            try:
                d = self.get(path)
                answered = True
                teams = [{"id": t.get("team_id") or t.get("id"), "competition_id": t.get("competition_id")}
                         for t in ((d or {}).get("teams") or [])]
                if teams:
                    break
            except urllib.error.HTTPError as e:
                answered, last = True, e
            except Exception as e:  # noqa: BLE001
                last = e
        want = os.environ.get("AVALON_COMPETITION_ID")
        if want:
            teams = [t for t in teams if t["competition_id"] == want] or teams
        if not teams:
            if (not answered and last is not None) or (isinstance(last, urllib.error.HTTPError) and last.code in (401, 403)):
                raise last          # no answer at all, or the key refused: say that, not "no team"
            raise RuntimeError(f"the key lists no team ({type(last).__name__ + ': ' + str(last) if last else 'empty answer'})")
        if len(teams) > 1 and not want:   # e.g. the regional and the Finals: take the newest competition
            comps = {c.get("id"): c for c in ((self.get("/competitions") or {}).get("items") or [])}
            teams.sort(key=lambda t: str((comps.get(t["competition_id"]) or {}).get("created_at")
                                         or (comps.get(t["competition_id"]) or {}).get("starts_at") or ""))
        return teams[-1]

    def identify(self, t: dict | None = None) -> None:
        t = t or self.pick_team()
        if self.st.get("cid") and self.st["cid"] != t["competition_id"]:
            self.archive(self.st["cid"], t["competition_id"])
        self.cid, self.team = t["competition_id"], t["id"]
        comp = self.get(f"/competitions/{self.cid}") or {}
        self.comp_name = comp.get("name") or self.cid
        self.team_name = (self.get(f"/teams/{self.team}") or {}).get("name") or "avalon"
        self.st.update(cid=self.cid, team_id=self.team, team_name=self.team_name, comp_name=self.comp_name)
        self.ident_at = time.time()

    def follow_key(self, now: float) -> None:
        """Once a minute: has the key moved to a newer competition (the watcher was started while the key still
        listed only the regional, and the Finals has appeared since)? Then switch to it, with no restart. A look
        that fails changes nothing: the poll itself reports a portal that doesn't answer."""
        if now - self.ident_at < FOLLOW_KEY_S:
            return
        self.ident_at = now
        try:
            t = self.pick_team()
        except Exception:  # noqa: BLE001
            return
        if t.get("competition_id") and t["competition_id"] != self.cid:
            self.identify(t)

    def archive(self, old_cid: str, new_cid: str) -> None:
        """A different competition on this key (the rehearsal, then Sunday): start fresh; keep the old data aside."""
        stamp = time.strftime("%Y%m%d-%H%M")
        moved = ""
        if self.out.exists() and any(self.out.iterdir()):
            dest = self.out.with_name(f"rounds.old-{str(old_cid)[:8]}-{stamp}")
            self.out.rename(dest)
            moved = f"; the old round data moved to {rel(self.root, dest)}/"
        for name in ("rounds_seen.json", "variant.md"):
            try:
                C.sp(self.root, name).unlink()
            except FileNotFoundError:
                pass
        self.hands_ok = None
        C.write_json(C.sp(self.root, f"portal.old-{str(old_cid)[:8]}.json"), self.st)
        keep = {k: self.st[k] for k in ("hands_url", "hands_url_at") if k in self.st and self.cli_hands}
        self.st = dict(copy.deepcopy(DEFAULT_ST), **keep)   # a hands link from the old portal doesn't fit the new one
        self.checked = set()
        self.say("both", f"new competition on this key ({new_cid}; was {old_cid}): starting fresh{moved}.")

    # -------------------------------------------------- rounds
    def rounds(self) -> list:
        d = self.get(f"/competitions/{self.cid}/tournaments")
        items = d.get("items", []) if isinstance(d, dict) else (d or [])
        rounds = [dict(r) for r in items if not r.get("cancelled_at") and r.get("status") not in ("cancelled", "canceled")]
        counts: dict = {}
        for r in sorted(rounds, key=lambda r: str(r.get("created_at") or "")):   # the real portal has no labels
            if r.get("kind") != "practice":     # "scored", "final", ...: one counter, so a "final" isn't round 1
                r["kind"] = "scored"
            counts[r["kind"]] = counts.get(r["kind"], 0) + 1
            if not r.get("label"):
                r["label"] = (f"{'Scored' if r['kind'] == 'scored' else 'Practice'} round {counts[r['kind']]}"
                              + (f" (x{r['weight']})" if r.get("weight") and r["kind"] == "scored" else ""))
            if r["kind"] == "practice":         # "Practice n" in the build; "Round k.5" after scored round k
                ks = counts.get("scored", 0)
                r["stage"] = f"Practice {counts['practice']}" if ks == 0 else f"Round {ks}.5"
                r["_n"] = counts["practice"] if ks == 0 else 4 + ks
            else:
                r["stage"], r["_n"] = f"Round {counts['scored']}", counts["scored"]
        return sorted(rounds, key=lambda r: str(r.get("created_at") or ""))

    def round_ids(self) -> tuple:
        d = self.get(f"/competitions/{self.cid}/tournaments")
        items = d.get("items", []) if isinstance(d, dict) else (d or [])
        return tuple(sorted((str(r.get("id")), bool(r.get("completed_at"))) for r in items))

    def finishing(self, now: float) -> bool:
        """From 2 to 15 event-minutes after a round's scheduled start, until its result has landed."""
        s = self.schedule()
        if not C.started(s):
            return False
        U, landed = C.unit(s), set(self.st.get("done_stages") or [])
        return any(ts + 2 * U <= now < ts + 15 * U and C.stage_of_round(kind, k) not in landed
                   for kind, k, ts in C.events(s))

    # -------------------------------------------------- one poll
    def poll(self) -> None:
        now = time.time()
        self.sync()
        if not self.cid:
            self.identify()
        else:
            self.follow_key(now)
        rounds = self.rounds()
        prev_ok = self.st.get("last_ok") or 0
        newly = self.track_starts(rounds, now, prev_ok)
        self.check_silent(rounds, now)
        new_done = [r for r in rounds if r.get("completed_at") and r["id"] not in self.st["done"]]
        if not self.st.get("baseline_done"):   # rounds that finished before the watcher first ran: saved quietly,
            self.st["baseline_done"] = True     # one catch-up line, not N "new round" events
            self.st["quiet_ids"] = [r["id"] for r in new_done]
        quiet_ids, caught = set(self.st.get("quiet_ids") or []), []
        for r in new_done:
            try:
                fr = self.landed(r, quiet=r["id"] in quiet_ids)
                if r["id"] in quiet_ids:
                    caught.append(fr)
                (self.st.get("land_fail") or {}).pop(r["id"], None)
            except Exception as e:  # noqa: BLE001   results not ready yet, a timeout: try again next poll
                fails = self.st.setdefault("land_fail", {})
                fails[r["id"]] = fails.get(r["id"], 0) + 1
                if fails[r["id"]] == 3:
                    self.say("both", f"can't read the result of {r['stage']} yet ({type(e).__name__}: {str(e)[:120]}); "
                                     "still retrying every poll.")
                if fails[r["id"]] >= 40:   # ~10 minutes: stop, say so
                    self.st["done"].append(r["id"])
                    self.say("both", f"URGENT: gave up reading the result of {r['stage']} after 40 tries "
                                     f"({type(e).__name__}). Download it from the portal's round page into data/rounds/.")
        if caught:
            n_old = sum(1 for r in new_done if r["id"] in (self.st.get("old_rounds") or []))
            if n_old == len(caught):   # e.g. started on the regional's competition before the Finals is on the key
                self.say("both", f"catch-up: the portal shows {self.comp_name or self.cid} with {n_old} round(s) that all "
                                 f"finished more than {OLD_ROUND_S // 3600} hours ago: not today's event. Their results "
                                 "are saved (no hand files). The watcher switches by itself when a newer competition "
                                 "appears on this key.")
            else:
                self.say("both", f"catch-up: {len(caught)} round(s) had already finished before the portal watcher "
                                 "started; results and our hand data are saved in " + ", ".join(caught) + ". These are NOT "
                                 "new rounds; check notes/PLAN-research.md for what was already analysed."
                                 + (f" ({n_old} of them finished more than {OLD_ROUND_S // 3600} hours ago: results only, "
                                    "no hand files.)" if n_old else ""))
        self.retry_hands()
        standings = self.read_standings()
        self.watch_competition()
        active = self.read_team(now)
        self.check_team(now)
        for r in newly:
            self.round_started(r, active)
        self.write_seen(rounds)
        self.st["last_ok"], self.st["last_poll"] = time.time(), time.time()
        if self.st.get("fails", 0) >= 3:
            self.say("both", f"the portal answers again (after {self.st['fails']} failed checks).")
        self.st["fails"], self.st["last_error"] = 0, None
        self.st["rounds_view"] = [{k: r.get(k) for k in ("id", "stage", "label", "kind", "weight", "created_at",
                                                         "completed_at")} for r in rounds]
        self.save()
        self.write_status(standings, time.time())

    def failed(self, e: Exception) -> None:
        self.st["fails"] = int(self.st.get("fails") or 0) + 1
        err = f"{type(e).__name__}: {str(e)[:160]}"
        self.st["last_error"], self.st["last_poll"] = err, time.time()
        if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403):
            err += " (the key was refused: check the key file)"
        if self.st["fails"] == 3:
            self.say("both", f"URGENT: the portal has not answered for 3 checks in a row ({err}). The watcher keeps "
                             "trying; check the network and the portal page.")
        if self.echo:
            C.quiet(f"poll failed ({self.st['fails']} in a row): {err}")
        try:
            self.save()
            self.write_status(self.st.get("standings") or [], time.time(), error=err)
        except Exception:  # noqa: BLE001
            pass

    # -------------------------------------------------- starts, the clock's view
    def track_starts(self, rounds: list, now: float, prev_ok: float) -> list:
        """First sighting of each round. A running round's start is exact when we were polling just before (or the
        portal's own creation time is within 10 minutes); one first seen finished is not (no pin from it)."""
        seen, newly = self.st.setdefault("seen_start", {}), []
        for r in rounds:
            if r["id"] in seen:
                continue
            ca = ts_of(r.get("created_at"))
            if r.get("completed_at"):
                seen[r["id"]] = {"at": ca or now, "exact": False, "stage": r["stage"]}
                continue
            if ca and now - 600 < ca <= now + 5:
                at, exact = min(ca, now), True
            else:
                at, exact = now, bool(prev_ok and now - prev_ok <= 3 * SLOW)
            seen[r["id"]] = {"at": at, "exact": exact, "stage": r["stage"]}
            newly.append(r)
        return newly

    def write_seen(self, rounds: list) -> None:
        seen = self.st.get("seen_start") or {}
        out = {}
        for r in rounds:
            e = seen.get(r["id"])
            if e:
                out[r["stage"]] = {"at": e["at"], "exact": e["exact"], "id": r["id"], "kind": r["kind"],
                                   "done": bool(r.get("completed_at"))}
        cur = C.load_json(C.sp(self.root, "rounds_seen.json"), {})
        if (cur or {}).get("rounds") != out or (cur or {}).get("cid") != self.cid:
            C.write_json(C.sp(self.root, "rounds_seen.json"), {"cid": self.cid, "updated": time.time(), "rounds": out})

    def check_silent(self, rounds: list, now: float) -> None:
        """No round on the portal 8 event-minutes after one should have started: the clock, the key or the competition
        is wrong. Once per expected round."""
        s = self.schedule()
        if not C.started(s):
            return
        U = C.unit(s)
        for kind, k, ts in C.events(s):
            key = f"silent:{int(float(s['start']))}:{kind}{k}"
            if ts + 8 * U < now < ts + 20 * U and key not in self.checked:
                n_kind = sum(1 for r in rounds if r["kind"] == kind)
                need = k if kind == "scored" else (k if k <= 4 else None)
                if need and n_kind < need:
                    self.checked.add(key)
                    self.say("both", f"URGENT: {C.event_label(kind, k)} should have started at {C.hhmm(ts)}, but the "
                                     f"portal ({self.comp_name or self.cid}) shows {n_kind} {kind} round(s). Is the clock "
                                     "right (clock.py show / pin), or the competition (AVALON_COMPETITION_ID)?")

    def round_started(self, r: dict, active) -> None:
        pb = self.st.setdefault("played_by", {})
        pb.setdefault(r["id"], active or "no bot")
        live = (C.live_bot(self.root) or {}).get("bot")
        at = (self.st["seen_start"].get(r["id"]) or {}).get("at") or time.time()
        bot = C.norm_bot(active) if active else None
        if not active:
            self.say("both", f"URGENT: {r['stage']} started at {C.hms(at)} with NO active bot: we forfeit it. "
                             + (f"Make {live} active now (releases/{live}.zip)." if live else "Make a tested bot active now."))
        elif r["kind"] == "scored" and live and not C.same_bot(live, active):
            self.say("both", f"URGENT: {r['stage']} started at {C.hms(at)} with {active} active, but the decided bot "
                             f"(state/live.json) is {live}. It plays the whole round with {bot}; tell BUILDER if that was "
                             "intended (the next window starts from the bot that really played).")
        else:
            extra = f" (the declared live bot is {live})" if live and not C.same_bot(live, active) else ""
            self.say("both", f"{r['stage']} started at {C.hms(at)}: playing {bot}{extra}.")

    # -------------------------------------------------- a round finished
    def folder_for(self, r: dict) -> Path:
        n = len(self.st["done"]) + 1
        slug = C.stage_slug(r["stage"]).lower()
        folder = self.out / f"{n:02d}-{slug}"
        meta = C.load_json(folder / "round.json", None)
        if meta and meta.get("id") != r["id"]:     # an older run's folder of the same name: never mix two rounds
            folder = self.out / f"{n:02d}-{slug}-{str(r['id'])[:6]}"
        return folder

    def landed(self, r: dict, quiet: bool = False) -> str:
        """A round finished: save results and hands, then tell the sessions; run the card in the background.
        Raises if the results can't be read (poll() retries the round next time)."""
        res = self.get(f"/tournaments/{r['id']}/results")
        if not isinstance(res, dict) or not isinstance(res.get("items"), list):
            raise RuntimeError("results not ready")
        held = str(res.get("status") or "").lower() == "held"   # the organizers hold the scores: the hands still count
        if not res["items"] and not held and (self.st.get("land_fail") or {}).get(r["id"], 0) < 5:
            raise RuntimeError("results list empty (not ready yet?)")
        stage, label = r["stage"], r["label"]
        folder = self.folder_for(r)
        folder.mkdir(parents=True, exist_ok=True)
        C.write_text(folder / "results.json", json.dumps(res, indent=1))
        pbot = (self.st.get("played_by") or {}).get(r["id"])
        health = self.health_for(r["id"])
        if not pbot and health.get("submission_id"):
            pbot = next((u.get("filename") for u in self.st.get("uploads") or [] if u.get("id") == health["submission_id"]), None)
        meta = {k: r.get(k) for k in ("id", "kind", "stage", "label", "weight", "created_at", "completed_at")}
        meta.update(played_by=pbot, saved_at=time.time(), competition=self.cid)
        C.write_json(folder / "round.json", meta)
        if pbot and pbot != "no bot":
            C.write_text(folder / "played_by.txt", pbot + "\n")
        # A round first seen long after it finished (the regional's, when the Finals isn't on the key yet) is not
        # today's data: keep its results, but never pull gigabytes of old hand files over the venue's Wi-Fi.
        old = quiet and (ts_of(r.get("completed_at")) or time.time()) < time.time() - OLD_ROUND_S
        files = [] if old else self.fetch_hands(r["id"], folder, small_first=True)
        if files:
            self.st.setdefault("landed_at", {})[stage] = time.time()
        elif old:
            self.st.setdefault("old_rounds", []).append(r["id"])
        else:
            self.st["need_hands"][r["id"]] = {"folder": str(folder), "label": label, "stage": stage, "since": time.time()}
        items = sorted(res["items"], key=lambda x: -(x.get("average_points") or 0))
        ours = next((i for i, x in enumerate(items, 1) if x.get("team_name") == self.team_name
                     or (self.team and x.get("team_id") == self.team)), None)
        me = items[ours - 1] if ours else None
        top = items[0] if items else {}
        self.st.setdefault("results", {})[r["id"]] = {
            "place": ours, "n": len(items), "pts": (me or {}).get("average_points"), "moe": (me or {}).get("margin_of_error"),
            "top": top.get("team_name"), "top_pts": top.get("average_points"), "folder": rel(self.root, folder)}
        fr = rel(self.root, folder) + "/"
        if quiet:
            if files and not self.small_only:
                self.start_full(r["id"], folder, stage, quiet=True)
            self.st["done"].append(r["id"])
            self.st.setdefault("done_stages", []).append(stage)
            self.save()
            return fr
        pb = f" · played by {C.norm_bot(pbot)}" if pbot and pbot != "no bot" else " · played by: unknown"
        if me:
            line = (f"{stage} finished: we were {ours} of {len(items)} with {(me.get('average_points') or 0):.2f} "
                    f"(±{(me.get('margin_of_error') or 0):.2f}); 1st {top.get('team_name')} {(top.get('average_points') or 0):.2f}"
                    f"{pb} · data: {fr}")
        elif held:
            line = f"{stage} finished: the organizers are holding its results (no scores yet){pb} · data: {fr}"
        else:
            line = f"URGENT: {stage} finished and we have NO result (forfeit? no active bot?){pb} · data: {fr}"
        hl = self.health_text(health)
        if hl:
            line += f" · {hl}"
        if ".5" in stage:
            line += " · this is the challenger's practice number for the T-8 rule"
        if not files:
            line += " · hand data not downloadable yet (retrying)"
        self.say("both", line)
        if me and (me.get("contender") is False or me.get("culled_at_look")):
            self.say("both", f"after {stage} the portal marks us culled in that round (culled_at_look: {me.get('culled_at_look') or 'culled'}). "
                             "That is an early stop inside one round, not elimination: we were dealt fewer tables, the round "
                             "still scores on the tables we played (a noisier score), later rounds are unaffected and no "
                             "decision rule changes.")
        nt = next((me.get(k) for k in ("tables", "tables_played", "n_tables") if me and me.get(k) is not None), None)
        if me and (nt == 0 or me.get("forfeited")):
            self.say("both", f"URGENT: we played no tables in {stage} (forfeited: {bool(me.get('forfeited'))}): no active "
                             "bot, or a crash? Check the active bot now.")
        if files:
            self.data_landed_msg(stage, folder, files)
            if not self.small_only:
                self.start_full(r["id"], folder, stage)
        s = self.schedule() or {}
        if r["kind"] == "scored" and stage == f"Round {int(s.get('scored', 6))}":
            self.say("both", f"that was the last scored round ({stage}): the event is over. Record what you have; stop any "
                             "Modal apps and background jobs you started (by id / PID).")
        self.st["done"].append(r["id"])   # only now: a crash before this re-announces the round after a restart
        self.st.setdefault("done_stages", []).append(stage)
        self.save()
        return fr

    def data_landed_msg(self, stage: str, folder: Path, files: list, late: bool = False) -> None:
        cards = [n for n in ("roundcard.py", "fp_train.py") if (self.root / "analysis" / n).exists()]
        self.say("research", f"DATA LANDED{' (late)' if late else ''} {stage} {rel(self.root, folder)}/ "
                             f"({', '.join(Path(f).name for f in files)}, results.json"
                             + ("; the full file follows" if not self.small_only and not any("full" in f for f in files) else "")
                             + (f"; portal_watch is running {' and '.join(cards)} on it now" if cards else
                                "; no analysis/roundcard.py yet: run the card by hand") + ")")
        for name in cards:
            self.spawn(self.card_job, folder, stage, name)

    def health_for(self, tid: str) -> dict:
        try:
            d = self.get(f"/teams/{self.team}/health")
            items = d.get("items", []) if isinstance(d, dict) else (d or [])
            return next((x for x in items if x.get("tournament_id") == tid), {}) or {}
        except Exception:  # noqa: BLE001
            return {}

    @staticmethod
    def health_text(h: dict) -> str:
        if not h:
            return ""
        dec, miss, rst = h.get("decisions") or 0, h.get("missed") or 0, h.get("restarts") or 0
        bad = (dec and miss / dec > 0.01) or rst or h.get("gave_up")
        t = f"health: {miss} missed of {dec:,} decisions, {rst} restarts" + (", GAVE UP" if h.get("gave_up") else "")
        return ("URGENT " + t + " (missed decisions fold: check the bot's timing)") if bad else t

    # -------------------------------------------------- hand data
    def fetch_hands(self, tid: str, folder: Path, small_first: bool = False, only_full: bool = False,
                    shared: bool = True) -> list:
        """Download our hand files for a round: gzip verified to the end, written atomically; plain JSON lines are
        compressed; an HTML page or an error is rejected and the reason kept in st['hands_err'] (main thread only:
        a background download passes shared=False)."""
        files, err = [], None
        want = [("first-1000", "?" + SMALL_Q)] + ([] if (self.small_only or small_first) else [("full", "")])
        if only_full:
            want = [("full", "")]
        for suffix, q in want:
            p = folder / f"hands-{suffix}.jsonl.gz"
            if p.exists() and p.stat().st_size > 100:
                files.append(str(p))
                continue
            why = None   # why this file failed: the first reason, but a 404 (no such address here) yields to a later,
            for tpl in self.hands_urls():   # more telling one (an HTML page, a broken file); None once the file is saved
                try:
                    url = (tpl.replace("{tid}", tid).replace("{team}", str(self.team or ""))
                           .replace("{q}", q).replace("{qa}", q.replace("?", "&")))
                    data = self.get(url, raw=True)
                    head = data[:400].lower()
                    if data[:1] in (b"{", b"[") and len(data) > 100 and b"<html" not in head:
                        data = gzip.compress(data)   # plain JSON lines: keep them, in the format everything reads
                    if data[:2] != b"\x1f\x8b":
                        kind = "an HTML page (a login or error page?)" if b"<html" in head or b"<!doctype" in head else "not gzip"
                        why = first_reason(why, f"got {len(data)} bytes that aren't hand data ({kind}: {data[:40]!r})")
                        continue
                    if len(data) <= 100:
                        why = first_reason(why, f"got only {len(data)} bytes")
                        continue
                    with gzip.GzipFile(fileobj=io.BytesIO(data)) as g:   # a truncated download never counts as saved
                        while g.read(1 << 20):
                            pass
                    tmp = p.with_name(p.name + ".tmp")
                    tmp.write_bytes(data)
                    os.replace(tmp, p)
                    files.append(str(p))
                    self.hands_ok, why = tpl, None
                    break
                except Exception as e:  # noqa: BLE001
                    why = first_reason(why, f"{type(e).__name__}: {str(e)[:160]}")
            err = why or err
        if err and shared:
            self.st["hands_err"] = err
        return files

    def start_full(self, tid: str, folder: Path, stage: str, quiet: bool = False) -> None:
        if tid in self.full_jobs or (folder / "hands-full.jsonl.gz").exists():
            return
        self.full_jobs.add(tid)

        def job():
            try:
                got = self.fetch_hands(tid, folder, only_full=True, shared=False)
                if got and not quiet:
                    self.say("research", f"full hand file for {stage} saved: {rel(self.root, got[0])} "
                                         f"({mb(Path(got[0]).stat().st_size)})")
            finally:
                self.full_jobs.discard(tid)
        self.spawn(job)

    def retry_hands(self) -> None:
        for tid, info in list((self.st.get("need_hands") or {}).items()):
            folder = Path(info["folder"])
            files = self.fetch_hands(tid, folder, small_first=True)
            stage = info.get("stage") or info.get("label")
            if files:
                self.st["need_hands"].pop(tid, None)
                self.st.setdefault("landed_at", {})[stage] = time.time()
                self.save()
                self.data_landed_msg(stage, folder, files, late=True)
                if not self.small_only:
                    self.start_full(tid, folder, stage)
            elif time.time() - info["since"] > 300 and not info.get("pinged"):
                info["pinged"] = True
                self.say("both", f"URGENT: the hand data for {stage} hasn't downloaded for 5 minutes (last error: "
                                 f"{self.st.get('hands_err') or 'none recorded'}). Copy the hand download link from the "
                                 "portal's round page and paste the link: python3 scripts/portal_watch.py --set-hands-url "
                                 "'<link>' (no restart needed).")
            elif time.time() - info["since"] > 1200 and not info.get("warned"):
                info["warned"] = True
                self.say("both", f"the hand data for {stage} still can't be downloaded after 20 minutes (last error: "
                                 f"{self.st.get('hands_err') or 'none'}). Download it by hand from the round page into "
                                 f"{rel(self.root, folder)}/hands-first-1000.jsonl.gz, or set the link with --set-hands-url.")

    # -------------------------------------------------- analysis scripts
    def spawn(self, fn, *args) -> None:
        t = threading.Thread(target=fn, args=args, daemon=True)
        t.start()
        self.threads.append(t)
        self.threads = [x for x in self.threads if x.is_alive()]

    def card_job(self, folder: Path, stage: str, name: str) -> None:
        """Run analysis/<name> on the round folder (90 s cap), then post the card's path or the failure's tail."""
        script = self.root / "analysis" / name
        py = self.root / ".venv" / "bin" / "python"
        uvb = shutil.which("uv")
        cmd = [str(py)] if py.exists() else ([uvb, "run", "--no-project", "--with", "numpy", "--with", "pandas", "python"]
                                             if uvb else [sys.executable or "python3"])
        t0 = time.time()
        extra = ["--quick"] if name == "fp_train.py" else []    # its quick mode fits the 90 s cap (scout's role file)
        try:
            p = subprocess.Popen(cmd + ["-I", "-c", RUNPY, str(script.parent), str(script), str(folder)] + extra,
                                 cwd=str(self.root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 env={**os.environ, "AVALON_STAGE": stage}, start_new_session=True)
            try:
                out, _ = p.communicate(timeout=90)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(p.pid, signal.SIGKILL)   # our own child's process group, by its PID
                except OSError:
                    pass
                p.communicate()
                self.say("research", f"analysis/{name} stopped after 90 s on {stage} (too slow): run it by hand now; "
                                     "speed up the script after T-3.")
                return
        except Exception as e:  # noqa: BLE001
            self.say("research", f"couldn't run analysis/{name} for {stage}: {type(e).__name__}: {e}")
            return
        tail = re.sub(r"\s+", " ", out.decode(errors="replace")).strip()
        dt = time.time() - t0
        if p.returncode != 0:
            self.say("research", f"analysis/{name} FAILED on {stage} (exit {p.returncode}): …{tail[-600:]} — run the card "
                                 "by hand now; fix the script after T-3.")
            return
        fp = name.startswith("fp")
        made = []
        try:
            for f in (self.root / "analysis").rglob("*"):
                if f.is_file() and f.stat().st_mtime >= t0 - 1 and f.suffix != ".py":
                    is_fp = "fp" in f.relative_to(self.root / "analysis").parts[:-1] or "fp" in f.name.lower()
                    if is_fp == fp and (fp or ("card" in f.name.lower() and f.suffix == ".md")):
                        made.append(f)
        except OSError:
            pass
        slug = C.stage_slug(stage).lower()
        made.sort(key=lambda f: (slug in str(f).lower(), f.stat().st_mtime), reverse=True)   # this round's own first
        where = rel(self.root, made[0]) if made else f"analysis/{C.stage_slug(stage)}/" + ("fp/" if fp else "card.md")
        what = "fingerprint card ready" if fp else "card ready"
        self.say("research", f"{what}: {where} ({stage}; {name} took {dt:.0f} s)" + (f". Output: {tail[-300:]}" if tail else ""))

    # -------------------------------------------------- standings, settings, team
    def read_standings(self) -> list:
        try:
            d = self.get(f"/competitions/{self.cid}/standings")
            items = d.get("items") if isinstance(d, dict) else d
            held = isinstance(d, dict) and bool(d.get("held"))
            if not isinstance(items, list) or (held and not items):
                raise RuntimeError("leaderboard held" if held else "no standings")
            self.st["standings"] = items
            if held and not self.st.get("standings_held"):
                self.st["standings_held"] = True
                self.say("both", "the portal marks the standings as held: totals may be stale. Until they're back, "
                                 "DECISION_RULES treats us as outside the top 3 unless we were clearly in it; RESEARCH works "
                                 "out our total from each round's results x weights.")
            elif not held and self.st.get("standings_held"):
                self.st["standings_held"] = False
                self.say("both", "the standings can be read again.")
            return items
        except Exception as e:  # noqa: BLE001   a held leaderboard never stops the active-bot checks
            if not self.st.get("standings_held"):
                self.st["standings_held"] = True
                self.say("both", f"the standings can't be read ({type(e).__name__}: {str(e)[:80]}): the leaderboard may "
                                 "be held. Active-bot checks continue. Until it's back, DECISION_RULES treats us as outside "
                                 "the top 3 unless we were clearly in it; RESEARCH works out our total from each round's "
                                 "results x weights.")
            return self.st.get("standings") or []

    def watch_competition(self) -> None:
        """Format settings the organizers can change mid-event (a late final weight, a held leaderboard)."""
        try:
            comp = self.get(f"/competitions/{self.cid}") or {}
        except Exception:  # noqa: BLE001
            return
        now_ = {k: comp.get(k) for k in COMP_KEYS if k in comp}
        old = self.st.get("comp_settings")
        self.st["comp_settings"] = now_
        if old is not None and now_ != old:
            diff = "; ".join(f"{k}: {old.get(k)} -> {now_.get(k)}" for k in COMP_KEYS if old.get(k) != now_.get(k))
            self.say("both", f"URGENT: the organizers changed the competition settings: {diff}. BUILDER updates the rules "
                             "card (bot/rules.json); RESEARCH re-checks the bar for the next decision.")
        try:
            self.note_variant(comp)
        except Exception as e:  # noqa: BLE001   an extra: it must never stop the round and active-bot checks
            if self.echo:
                C.quiet(f"couldn't save the variant's rules text ({type(e).__name__}: {str(e)[:120]})")

    def cooldown(self):
        """The upload cooldown in seconds as the portal itself states it (None if it doesn't)."""
        cs = self.st.get("comp_settings") or {}
        v = cs.get("submission_cooldown_seconds", cs.get("upload_cooldown_seconds"))
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    def note_variant(self, comp: dict) -> None:
        """The real portal stamps the announcement (variant_announced_at = minute 0) and serves the variant's rules
        text at /competitions/<id>/variant. Once per announcement, and only for today's (not the regional's): save the
        text to state/variant.md and tell both sessions the portal's own time for minute 0."""
        at = comp.get("variant_announced_at")
        t = ts_of(at)
        if not t or self.st.get("variant_at") == at:
            return
        if t < time.time() - OLD_ROUND_S:
            self.st["variant_at"] = at
            return
        v = self.get(f"/competitions/{self.cid}/variant") or {}
        rules = v.get("rules") if isinstance(v, dict) else None
        if not isinstance(rules, str) or not rules.strip():
            return                      # not readable yet: look again at the next poll
        title = str(v.get("title") or v.get("id") or comp.get("variant") or "?")
        cd = self.cooldown()
        C.write_text(C.sp(self.root, "variant.md"),
                     f"<!-- Saved {C.hms(time.time())} by scripts/portal_watch.py from the portal's own API. Variant "
                     f"\"{title}\" (id {v.get('id') or comp.get('variant')}), announced at {C.hms(t)} = minute 0. "
                     "The kit's RULES.md and state.config and the Format page still decide the rules card. -->\n\n"
                     + rules.rstrip() + "\n")
        self.st["variant_at"] = at
        s = self.schedule()
        clock = ("" if C.started(s) else
                 f" The clock isn't started: RESEARCH runs python3 scripts/clock.py start {time.strftime('%H:%M', time.localtime(t))}.")
        self.say("both", f"THE VARIANT IS ANNOUNCED on the portal: \"{title}\", at {C.hms(t)} (the portal's own time = "
                         f"minute 0). Its rules text is saved in state/variant.md ({len(rules.splitlines())} lines): read it "
                         "now, before the kit is unpacked; the kit and the Format page still decide the rules card."
                         + (f" Upload cooldown per the portal: {cd:g} s." if cd is not None else "") + clock)

    def read_team(self, now: float):
        team = self.get(f"/teams/{self.team}") or {}
        try:
            subs = self.get(f"/teams/{self.team}/submissions")
            subs = subs.get("items", subs) if isinstance(subs, dict) else subs
        except Exception:  # noqa: BLE001
            subs = None
        if not isinstance(subs, list):
            subs = team.get("submissions") or []
        self._subs = subs
        act_id = team.get("active_submission_id")
        act = next((x for x in subs if x.get("id") == act_id), None) if act_id else None
        active = team.get("active_filename") or (act or {}).get("filename")
        self.st["active"] = {"filename": active, "id": act_id, "sha256": (act or {}).get("sha256") or "",
                             "uploaded": (act or {}).get("created_at") or team.get("active_created_at"), "at": now}
        newest = sorted(subs, key=lambda u: ts_of(u.get("created_at")) or 0, reverse=True)
        self.st["uploads"] = [{k: u.get(k) for k in ("id", "filename", "status", "rejection_reason", "created_at",
                                                      "sha256", "size_bytes")} for u in newest[:15]]
        return active

    def check_team(self, now: float) -> None:
        subs = getattr(self, "_subs", [])
        live = C.live_bot(self.root) or {}
        lname = live.get("bot")
        first = not self.st.get("subs_baseline")
        for u in subs:
            if u.get("id") in self.st["subs"] or u.get("status") not in ("ready", "rejected", "cancelled"):
                continue
            self.st["subs"].append(u["id"])
            if first or u.get("status") != "rejected":
                continue
            act = (self.st.get("active") or {}).get("filename")
            text = f"URGENT: upload {u.get('filename')} was REJECTED by the portal: {u.get('rejection_reason') or 'no reason given'}."
            if lname and C.same_bot(lname, u.get("filename")):
                prev = (live.get("prev") or {}).get("bot")
                text += (f" It was the declared live bot ({lname}); the previous bot stays active on the portal "
                         f"({act or 'none'}). BUILDER: have platform fix it" +
                         (f", or put {prev} back: python3 scripts/live.py {prev} \"{lname} rejected\"." if prev else "."))
            else:
                text += f" The previous bot stays active ({act or 'none'})."
            self.say("both", text)
        self.st["subs_baseline"] = True
        s = self.schedule()
        if not C.started(s) or not self.team:
            return
        U, tk = C.unit(s), int(float(s["start"]))
        act = (self.st.get("active") or {})
        active = act.get("filename")
        for kind, k, ts in C.events(s):
            for mins in ((7, 2) if kind == "scored" else (2,)):   # scored: T-7 and T-2; practice: T-2
                key = f"{tk}:{kind}{k}-{mins}"
                if key in self.checked or not (ts - mins * U <= now < ts):
                    continue
                self.checked.add(key)
                lbl = C.event_label(kind, k)
                if not active:
                    msg = (f"URGENT: {lbl} starts at {C.hhmm(ts)} and there is NO active bot on the portal: we forfeit it "
                           "unless one is made active" + (f" ({lname}: releases/{lname}.zip)." if lname else "."))
                elif kind == "scored" and lname and not C.same_bot(lname, active):
                    msg = (f"URGENT: scored round {k} starts at {C.hhmm(ts)} (T-{mins}) and the portal's active bot is "
                           f"{active}, but the declared live bot (state/live.json) is {lname}. Dylan: make {lname} active, "
                           "or BUILDER: say it's intended.")
                elif kind == "scored" and lname and mins == 2 and live.get("sha256") and act.get("sha256") \
                        and live["sha256"] != act["sha256"]:
                    msg = (f"URGENT: scored round {k} starts at {C.hhmm(ts)}: the active bot is named {active} but it is "
                           f"NOT the file releases/{lname}.zip (different sha256). Upload releases/{lname}.zip and activate it.")
                else:
                    continue
                self.say("both", msg)

    # -------------------------------------------------- state/status.md
    def write_status(self, standings: list, now: float, error: str | None = None) -> None:
        L = [f"# Portal status (written {C.hms(now)} by scripts/portal_watch.py)", ""]
        ok = self.st.get("last_ok")
        L.append(f"Last poll {C.hms(self.st.get('last_poll') or now)}: " +
                 ("OK" if not error else f"**FAILED** ({error}); last OK {C.hms(ok) if ok else 'never'}")
                 + (f" · base {self.base}" if self.base != BASE else ""))
        cd = self.cooldown()
        L.append(f"Competition: {self.comp_name or '?'} · team **{self.team_name}**"
                 + (f" · upload cooldown per the portal: {cd:g} s" if cd is not None else ""))
        act = self.st.get("active") or {}
        a = act.get("filename")
        line = f"**Active bot on the portal: {a or 'NONE (a round starting now is forfeited)'}**"
        if act.get("sha256"):
            line += f" (sha256 {act['sha256'][:12]}…)"
        if act.get("uploaded"):
            line += f", uploaded {C.hhmm(ts_of(act['uploaded']))}"
        L.append(line)
        live = C.live_bot(self.root)
        if live:
            match = C.same_bot(live["bot"], a)
            shaok = not (live.get("sha256") and act.get("sha256")) or live["sha256"] == act["sha256"]
            L.append(f"Declared live bot (state/live.json): **{live['bot']}** ({live.get('why', '')}) — " +
                     ("MATCHES the portal" if match and shaok else "same name as the portal's but a DIFFERENT FILE (sha256)"
                      if match else "does NOT match the portal (fine during a practice round; must match by T-3 of a scored round)"))
        else:
            L.append("Declared live bot (state/live.json): none yet")
        s = self.schedule()
        if C.started(s):
            nxt = next(((kind, k, ts) for kind, k, ts in C.events(s) if ts > now), None)
            if nxt:
                L.append(f"Next on the clock: {C.event_label(nxt[0], nxt[1])} at {C.hhmm(nxt[2])}")
        L += ["", "## Rounds", "", "| Stage | Round | Started | State | Played by | Us | Top |", "|---|---|---|---|---|---|---|"]
        seen, pb, res = self.st.get("seen_start") or {}, self.st.get("played_by") or {}, self.st.get("results") or {}
        for r in self.st.get("rounds_view") or []:
            rid = r["id"]
            if not r.get("completed_at"):
                state = "**running**"
            elif rid in (self.st.get("need_hands") or {}):
                state = "finished · hands NOT downloaded yet"
            elif rid in (self.st.get("old_rounds") or []):
                state = "finished long ago · results only"
            elif rid in self.st.get("done", []):
                state = "finished · data saved"
            else:
                state = "finished · reading results"
            x = res.get(rid) or {}
            us = (f"{x['place']}/{x['n']} · {x['pts']:.2f} ±{(x.get('moe') or 0):.2f}" if x.get("place") and x.get("pts") is not None
                  else ("no result" if x else ""))
            topc = f"{x.get('top')} {x['top_pts']:.2f}" if x.get("top_pts") is not None else ""
            st_at = (seen.get(rid) or {}).get("at")
            L.append(f"| {r['stage']} | {r.get('label') or ''} | {C.hhmm(st_at) if st_at else ''} | {state} | "
                     f"{C.norm_bot(pb[rid]) if pb.get(rid) and pb[rid] != 'no bot' else ('NO BOT' if pb.get(rid) else '?')} | {us} | {topc} |")
        L += ["", "## Standings (top 10)" + (" — HELD / may be stale" if self.st.get("standings_held") else ""), "",
              "| # | Team | Total |", "|---|---|---|"]
        for i, x in enumerate((standings or [])[:10], 1):
            name = x.get("team_name") or "?"
            name = f"**{name}**" if name == self.team_name else name
            L.append(f"| {x.get('rank', i)} | {name} | {(x.get('total') or 0):.2f} |")
        ours = next((x for x in standings or [] if x.get("team_name") == self.team_name), None)
        if ours and not any(x is ours for x in (standings or [])[:10]):
            L.append(f"| {ours.get('rank')} | **{self.team_name}** | {(ours.get('total') or 0):.2f} |")
        L += ["", "## Uploads (newest first)", "", "| Time | File | Status | Reason |", "|---|---|---|---|"]
        for u in (self.st.get("uploads") or [])[:8]:
            L.append(f"| {C.hhmm(ts_of(u.get('created_at')))} | {u.get('filename')} | {u.get('status')} | "
                     f"{C.short(u.get('rejection_reason') or '', 80)} |")
        warn = []
        if error:
            warn.append(f"the last poll failed: {error} ({self.st.get('fails', 0)} in a row)")
        rv = self.st.get("rounds_view") or []
        if rv and len(self.st.get("old_rounds") or []) == len(rv):
            warn.append(f"every round of {self.comp_name or 'this competition'} finished more than {OLD_ROUND_S // 3600} "
                        "hours ago: this is NOT today's event. The watcher switches by itself when a newer competition "
                        "appears on this key; if it never does, the key file isn't on the Finals team")
        for tid, info in (self.st.get("need_hands") or {}).items():
            warn.append(f"hand data for {info.get('stage')} not downloaded since {C.hhmm(info.get('since'))} "
                        f"(last error: {self.st.get('hands_err') or 'none'}); fix: python3 scripts/portal_watch.py "
                        "--set-hands-url '<link>'")
        if self.st.get("standings_held"):
            warn.append("standings held or unreadable")
        if live and a and not C.same_bot(live["bot"], a):
            warn.append(f"the portal runs {a}, the declared live bot is {live['bot']}")
        if not a:
            warn.append("NO active bot on the portal")
        rej = [u for u in (self.st.get("uploads") or [])[:3] if u.get("status") == "rejected"]
        for u in rej:
            warn.append(f"rejected upload: {u.get('filename')} ({C.short(u.get('rejection_reason') or '', 100)})")
        L += ["", "## Warnings", ""] + ([f"- {w}" for w in warn] or ["- none"])
        C.write_text(C.sp(self.root, "status.md"), "\n".join(L) + "\n")

    # -------------------------------------------------- the loop
    def wait_jobs(self, timeout: float = 300) -> None:
        end = time.time() + timeout
        for t in list(self.threads):
            t.join(max(0.0, end - time.time()))

    def loop(self) -> None:
        last_full, ids = 0.0, None
        print(f"Portal watcher: {self.base} (Ctrl-C stops it; restart any time: it resumes from state/portal.json).",
              flush=True)
        beat = 0.0
        while True:
            now = time.time()
            fast = self.finishing(now)
            try:
                if not fast or now - last_full >= SLOW or ids is None:
                    self.poll()
                    last_full = time.time()
                    ids = self.round_ids() if fast else None
                else:   # the fast window: a 6 s look at the round list; a change triggers the full poll
                    cur = self.round_ids()
                    if cur != ids:
                        self.poll()
                        last_full, ids = time.time(), cur
                if time.time() - beat > 300 and self.echo:
                    beat = time.time()
                    C.quiet(f"polling OK ({self.comp_name}; active bot {(self.st.get('active') or {}).get('filename')})")
            except KeyboardInterrupt:
                raise
            except Exception as e:  # noqa: BLE001
                self.failed(e)
                if self.echo and int(self.st.get("fails") or 0) <= 1:
                    traceback.print_exc()
            time.sleep(FAST if self.finishing(time.time()) else SLOW)


# ------------------------------------------------------------------ commands
def set_hands_url(root: Path, link: str) -> int:
    with C.Lock(root, ".portal.lock"):
        st = C.load_json(C.sp(root, "portal.json"), {}) or {}
        ids = set(st.get("done") or []) | set((st.get("need_hands") or {}).keys()) | set((st.get("seen_start") or {}).keys())
        tpl, msg = to_template(link, ids)
        if not tpl:
            print(f"portal_watch.py: {msg}", file=sys.stderr)
            return 2
        st["hands_url"], st["hands_url_at"] = tpl, time.time()
        for info in (st.get("need_hands") or {}).values():
            info["since"] = time.time()
            info.pop("pinged", None)
            info.pop("warned", None)
        C.write_json(C.sp(root, "portal.json"), st)
    post("research", f"hand-history link set: {tpl} (the watcher retries the missing downloads at its next poll)",
         "portal", root=root)
    print(msg + ". The running watcher uses it at its next poll (within 15 s) and retries the missing downloads; "
                "it's kept across restarts.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=os.environ.get("AVALON_PORTAL_BASE") or BASE)
    ap.add_argument("--key-file", default=os.environ.get("AVALON_PORTAL_KEY_FILE") or KEYFILE)
    ap.add_argument("--hands-url", default=None, help="hand download template ({tid}, {q}/{qa}) or a copied link")
    ap.add_argument("--set-hands-url", default=None, metavar="LINK", help="store a copied hand-download link and exit")
    ap.add_argument("--small-hands", action="store_true", help="only the first-1000 file")
    ap.add_argument("--once", action="store_true", help="one poll, then exit (prints what it saw)")
    a = ap.parse_args(argv)
    if a.set_hands_url:
        return set_hands_url(ROOT, a.set_hands_url)
    try:
        w = Watcher(ROOT, a.base, a.key_file, a.hands_url, a.small_hands)
    except FileNotFoundError:
        print(f"portal_watch.py: no key file at {a.key_file}. Put the portal API key there (Settings → API keys), "
              "chmod 600.", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"portal_watch.py: {e}", file=sys.stderr)
        return 2
    if not a.once:
        try:
            w.loop()
        except KeyboardInterrupt:
            print("\nportal watcher stopped.")
            w.wait_jobs(5)
            return 0
    try:
        w.poll()
    except Exception as e:  # noqa: BLE001
        w.failed(e)
        print(f"portal_watch.py --once: the poll FAILED: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
        return 1
    w.wait_jobs(300)
    rv = w.st.get("rounds_view") or []
    print(f"Portal OK: team {w.team_name} ({w.team}), competition \"{w.comp_name}\" ({w.cid}).")
    print(f"Rounds: {len(rv)}" + (" — " + ", ".join(f"{r['stage']} {'finished' if r.get('completed_at') else 'running'}"
                                                   for r in rv) if rv else ""))
    print(f"Active bot: {(w.st.get('active') or {}).get('filename') or 'NONE'}")
    for r in rv:
        x = (w.st.get("results") or {}).get(r["id"])
        if x:
            print(f"Saved {x.get('folder')}/: " + ", ".join(sorted(p.name for p in (ROOT / x['folder']).iterdir())))
    if w.st.get("need_hands"):
        print(f"Hand data missing for: {', '.join(i.get('stage') for i in w.st['need_hands'].values())} "
              f"(last error: {w.st.get('hands_err')})")
    if rv and len(w.st.get("old_rounds") or []) == len(rv):
        print(f"NOTE: every round here finished more than {OLD_ROUND_S // 3600} hours ago, so \"{w.comp_name}\" is not "
              "today's event (results saved, no hand files). The running watcher switches by itself when a newer "
              "competition appears on this key.")
    cd = w.cooldown()
    if cd is not None:
        print(f"Upload cooldown per the portal: {cd:g} s")
    print(f"Posted {len(w.posted)} inbox line(s); status in state/status.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
