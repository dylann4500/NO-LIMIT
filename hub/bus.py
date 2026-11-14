"""Message bus between agents, on one laptop and across both.

- Same laptop: delivered in-process.
- Other laptop: put on a Modal Queue partition "to-<person>". The receiver acknowledges each message
  (a key in the shared Modal Dict) once it is safely in the agent's inbox; the sender keeps the message
  in its outbox and resends until it sees the ack. Receivers drop duplicates by id. So nothing is lost
  to a dropped hotspot, a crash, or a reply lost in flight.
- The same Dict holds the directory (every agent's state and one-line status), the declared live bot and
  the event schedule, so both laptops share them.
- All Modal calls have short timeouts and never block an agent's turn.
"""

from __future__ import annotations

import asyncio
import collections
import json
import time
import uuid
from pathlib import Path
from typing import Awaitable, Callable

QUEUE = "avalon-hub-bus"
DIRECTORY = "avalon-hub-dir"
FRESH = 300          # a directory entry older than this (s) is offline: no new messages are routed to it
ACK_WAIT = 30        # resend a remote message if no ack after this many seconds
MAX_TRIES = 12       # unacknowledged deliveries (puts that succeeded) before it goes to the dead-letter file
GIVE_UP_AFTER = 1800 # seconds; failed puts while the link is down don't count, only this overall age does
PAIR_LIMIT = 30      # more than this many messages between two workers in 10 event-minutes -> hold and alert (a loop)
PAIR_LIMIT_LEAD = 45  # an Overseer and its workers talk constantly by design; only a runaway loop trips this


def new_id() -> str:
    return "m" + uuid.uuid4().hex[:12]


def atomic_write(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


async def guarded(coro, timeout=4.0):
    try:
        return await asyncio.wait_for(coro, timeout)
    except Exception:  # noqa: BLE001
        return None


class Bus:
    def __init__(self, person: str, data: Path, deliver: Callable[[dict], Awaitable[bool]],
                 bounce: Callable[[dict, str], Awaitable[None]], namespace: str = ""):
        self.person = person
        self.data = data
        self.deliver = deliver      # -> True if the message is now safely in a local inbox
        self.bounce = bounce        # tell a local sender its message could not be delivered
        self.ns = namespace
        self.outbox_file = data / "outbox.json"
        self.seen_file = data / "seen.json"
        self.dead_file = data / "dead-letters.jsonl"
        self.seen = collections.OrderedDict((k, 1) for k in load_json(self.seen_file, []))
        # outbox entries: {"msg":..., "tries":n, "sent_at": t or None}
        self.outbox: list[dict] = load_json(self.outbox_file, [])
        self.directory: dict[str, dict] = {}
        self.shared: dict[str, object] = {}   # "live", "schedule" (other shared keys)
        self.shared_ver: dict[str, float] = {}
        self.blobs = None
        self.dirty: dict[str, float] = {}
        self._dirty_evt = asyncio.Event()
        self.merge = None
        self.on_merge = None   # optional (key, local, remote) -> merged value or None (notes: keep both laptops' changes)
        self._persisted = ""
        self.synced = asyncio.Event()   # set after the first directory/shared sync (restart safety)
        try:   # restart without the link: carry on from the last known shared state (clock, rules, ledger, notes)
            saved = json.loads((data / "shared.json").read_text())
            self.shared.update(saved.get("shared", {}))
            self.shared_ver.update(saved.get("ver", {}))
            self.dirty.update(saved.get("dirty", {}))   # values never uploaded before a crash still go out
            if self.dirty:
                self._dirty_evt.set()
        except Exception:  # noqa: BLE001
            pass
        self.local_names: set[str] = set()
        self.all_names: set[str] = set()   # every agent on both laptops (from the roster)
        self.online = False
        self.error = ""
        self.q = self.d = None
        self._wake = asyncio.Event()
        self.pairs: dict[tuple, collections.deque] = collections.defaultdict(collections.deque)
        self.held: list[dict] = []
        self._publish_latest: dict[str, dict] = {}
        self._publish_evt = asyncio.Event()

    # ------------------------------------------------------------ setup
    async def start(self):
        try:
            import modal
            self.q = modal.Queue.from_name(QUEUE + self.ns, create_if_missing=True)
            self.d = modal.Dict.from_name(DIRECTORY + self.ns, create_if_missing=True)
            # shared values (notes, ledger, bots...) live in their own Dict; the directory holds only tiny version
            # stamps, so each 5 s poll downloads just what changed (hotspot data matters)
            self.blobs = modal.Dict.from_name(DIRECTORY + self.ns + "-shared", create_if_missing=True)
            await asyncio.wait_for(self.d.put.aio("__ping__", time.time()), 15)
            self.online = True
        except Exception as e:  # noqa: BLE001
            self.online, self.error = False, f"Can't reach the link to the other laptop ({type(e).__name__}); retrying"
        for fn in (self._send_loop, self._ack_loop, self._recv_loop, self._dir_loop, self._publish_loop, self._shared_loop):
            asyncio.create_task(self._forever(fn))

    def oldest_unsent_age(self) -> float:
        ts = [o["msg"]["at"] for o in self.outbox]
        return time.time() - min(ts) if ts else 0.0

    # ------------------------------------------------------------ routing
    def person_of(self, agent: str) -> str | None:
        if agent in self.local_names:
            return self.person
        e = self.directory.get(agent)
        if e and time.time() - e.get("seen", 0) < FRESH:
            return e.get("person")
        # an agent on the other laptop that is offline or not yet listed: queue for it (delivered when it is back)
        if self.all_names and agent not in self.all_names:
            return None   # a typo or an invented name: the sender gets an error at once instead of a 30-minute silence
        if agent.startswith("s-") and self.person != "samuel":
            return "samuel"
        if agent.startswith("d-") and self.person != "dylan":
            return "dylan"
        return None

    def known(self) -> list[str]:
        return sorted(self.local_names | {k for k, v in self.directory.items() if time.time() - v.get("seen", 0) < FRESH})

    async def send(self, msg: dict) -> str:
        msg.setdefault("id", new_id())
        msg.setdefault("at", time.time())
        to_person = self.person_of(msg["to"])
        if to_person is None:
            raise ValueError(f"no agent named '{msg['to']}' is online. Online: {', '.join(self.known())}")
        # loop guard: agent-to-agent only
        if msg.get("from_kind") == "agent":
            key = tuple(sorted((msg["from"], msg["to"])))
            dq = self.pairs[key]
            now = time.time()
            while dq and now - dq[0] > 600 * getattr(self, "scale", 1.0):   # event minutes (sped-up rehearsals too)
                dq.popleft()
            dq.append(now)
            limit = PAIR_LIMIT_LEAD if any(n.endswith("overseer") for n in key) else PAIR_LIMIT
            if len(dq) > limit:
                self.held.append(msg)
                raise OverflowError(f"held: {msg['from']} and {msg['to']} have exchanged {len(dq)} messages in 10 minutes. "
                                    "This message was dropped. Stop messaging each other; finish your work and summarise in set_status. A human has been told.")
        if to_person == self.person:
            if not await self.deliver(msg):
                raise ValueError(f"'{msg['to']}' could not take the message")
            return "delivered"
        self.outbox.append({"msg": msg, "tries": 0, "sent_at": None})
        self._save_outbox()
        self._wake.set()
        return "sent" if self.online else "queued; the link to the other laptop is down, it will be sent when it is back"

    async def _forever(self, fn):
        """A loop that dies on an unexpected error would silently stop the link: restart it instead."""
        while True:
            try:
                await fn()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                try:
                    with (self.data / "errors.log").open("a") as f:
                        f.write(f"{time.strftime('%H:%M:%S')} bus/{fn.__name__}: {type(e).__name__}: {e}\n")
                except Exception:  # noqa: BLE001
                    pass
                await asyncio.sleep(3)

    def _save_outbox(self):
        atomic_write(self.outbox_file, json.dumps(self.outbox))

    async def _send_loop(self):
        delay = 1.0
        while True:
            due = [o for o in self.outbox if o["sent_at"] is None]
            if due and self.q is not None:
                o = due[0]
                m = o["msg"]
                part = "to-" + (self.person_of(m["to"]) or ("samuel" if m["to"].startswith("s-") else "dylan"))
                try:
                    await asyncio.wait_for(self.q.put.aio(m, partition=part), 15)
                    o["sent_at"], o["tries"] = time.time(), o["tries"] + 1
                    self._save_outbox()
                    self.online, self.error, delay = True, "", 1.0
                    continue
                except Exception as e:  # noqa: BLE001
                    # a failed put means the link is down: keep it, don't count it against the message
                    if time.time() - m.get("at", time.time()) > GIVE_UP_AFTER or type(e).__name__ in ("RequestSizeError", "TypeError"):
                        await self._dead(o, f"{type(e).__name__}")
                        continue
                    self.online, self.error = False, "Link to the other laptop is down; retrying"
                    delay = min(delay * 2, 20)
            self._wake.clear()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=delay if due else 10)
            except asyncio.TimeoutError:
                pass

    async def _dead(self, o, why):
        self.outbox.remove(o)
        self._save_outbox()
        with self.dead_file.open("a") as f:
            f.write(json.dumps({"why": why, **o}) + "\n")
        await self.bounce(o["msg"], f"could not be delivered after {o['tries']} tries ({why})")

    async def _ack_loop(self):
        while True:
            await asyncio.sleep(4)
            if self.d is None:
                continue
            changed = False
            for o in list(self.outbox):
                if o["sent_at"] is None:
                    continue
                k = "ack:" + o["msg"]["id"]
                got = await guarded(self.d.get.aio(k))
                if got:
                    self.outbox.remove(o)
                    changed = True
                    asyncio.create_task(guarded(self.d.pop.aio(k)))
                elif time.time() - o["sent_at"] > ACK_WAIT:
                    if o["tries"] >= MAX_TRIES or time.time() - o["msg"].get("at", time.time()) > GIVE_UP_AFTER:
                        await self._dead(o, "never acknowledged")
                    else:
                        o["sent_at"] = None   # resend
                        changed = True
                        self._wake.set()
            if changed:
                self._save_outbox()

    # ------------------------------------------------------------ receiving
    async def _accept(self, msg: dict) -> bool:
        mid = msg["id"]
        if mid not in self.seen:
            ok = await self.deliver(msg)
            if not ok:
                await self.bounce_remote(msg, f"no agent named '{msg['to']}' on {self.person}'s laptop")
            self.seen[mid] = 1
            while len(self.seen) > 5000:
                self.seen.popitem(last=False)
            atomic_write(self.seen_file, json.dumps(list(self.seen)))
        return True

    async def bounce_remote(self, msg: dict, why: str):
        if msg.get("from_kind") != "agent":
            return
        note = {"id": new_id(), "from": "hub", "from_kind": "hub", "to": msg["from"], "kind": "fyi", "at": time.time(),
                "text": f"Your message {msg['id']} to {msg['to']} was not delivered: {why}."}
        self.outbox.append({"msg": note, "tries": 0, "sent_at": None})
        self._save_outbox()
        self._wake.set()

    async def _recv_loop(self):
        delay = 1.0
        while True:
            if self.q is None:
                await asyncio.sleep(10)
                continue
            try:
                try:
                    items = await asyncio.wait_for(self.q.get_many.aio(50, partition="to-" + self.person, timeout=10), 30)
                except Exception as e:  # noqa: BLE001
                    if type(e).__name__ != "Empty":
                        raise
                    items = []
                self.online, self.error, delay = True, "", 1.0
                for m in items:
                    await self._accept(m)
                    asyncio.create_task(guarded(self.d.put.aio("ack:" + m["id"], time.time())))
            except Exception:  # noqa: BLE001
                self.online, self.error = False, "Link to the other laptop is down; retrying"
                await asyncio.sleep(delay)
                delay = min(delay * 2, 20)

    # ------------------------------------------------------------ directory and shared state
    def publish(self, name: str, info: dict):
        info = dict(info, person=self.person, seen=time.time())
        self.directory[name] = info
        self._publish_latest[name] = info
        self._publish_evt.set()

    async def _publish_loop(self):
        while True:
            await self._publish_evt.wait()
            self._publish_evt.clear()
            batch, self._publish_latest = self._publish_latest, {}
            if self.d is None:
                continue
            for name, info in batch.items():
                await guarded(self.d.put.aio("agent:" + name, info))

    async def set_shared(self, key: str, value):
        """Local at once; the upload happens in the background, coalesced and retried until it succeeds (blob first,
        then the version stamp, so the other laptop never fetches a stale value under a new stamp)."""
        self.shared[key] = value
        ver = (value.get("updated") if isinstance(value, dict) else None) or time.time()
        ver = max(ver, self.shared_ver.get(key, 0) + 0.001)   # a local write always beats what we already hold, even when
        # the other laptop's clock runs ahead of ours (its stamps would otherwise win over our newer write)
        self.shared_ver[key] = ver
        self.dirty[key] = ver
        self._dirty_evt.set()

    def _persist_shared(self):
        try:
            txt = json.dumps({"shared": self.shared, "ver": self.shared_ver, "dirty": self.dirty}, default=str)
            if txt != self._persisted:   # only when something changed (it runs every few seconds)
                atomic_write(self.data / "shared.json", txt)
                self._persisted = txt
        except Exception:  # noqa: BLE001
            pass

    async def _shared_loop(self):
        while True:
            await self._dirty_evt.wait()
            self._dirty_evt.clear()
            if self.d is None or self.blobs is None:
                await asyncio.sleep(5)
                self._dirty_evt.set()
                continue
            self._persist_shared()
            for key, ver in list(self.dirty.items()):
                val = self.shared.get(key)
                mergeable = self.merge is not None and key.startswith("prop:") and isinstance(val, dict)
                try:
                    if mergeable:   # read-merge-write: never overwrite the other laptop's lines or decision
                        remote = await asyncio.wait_for(self.blobs.get.aio("shared:" + key), 15)
                        cur = self.shared.get(key)   # re-read: a local edit may have landed during the await
                        if isinstance(remote, dict) and isinstance(cur, dict):
                            m = self.merge(key, cur, remote)
                            if m == remote:   # the server already has everything we have
                                self.shared[key], self.shared_ver[key] = m, remote.get("updated", ver)
                                if self.dirty.get(key) == ver:
                                    del self.dirty[key]
                                continue
                            m["updated"] = max(m.get("updated", 0), cur.get("updated", 0), remote.get("updated", 0)) + 0.001
                            if self.dirty.get(key) == ver:   # never clobber a newer edit's stamp
                                self.dirty[key] = m["updated"]
                            self.shared[key], val, ver = m, m, m["updated"]
                            self.shared_ver[key] = ver
                            if self.on_merge and m != cur:
                                self.on_merge(key, m)
                        elif isinstance(cur, dict):
                            val = cur
                    await asyncio.wait_for(self.blobs.put.aio("shared:" + key, val), 15)
                    await asyncio.wait_for(self.d.put.aio("ver:" + key, ver), 10)
                    if mergeable:   # verify: a simultaneous write from the other laptop means merge again
                        back = await asyncio.wait_for(self.blobs.get.aio("shared:" + key), 15)
                        if not isinstance(back, dict) or back.get("updated") != val.get("updated"):
                            continue
                    if self.dirty.get(key) == ver:
                        del self.dirty[key]
                except Exception:  # noqa: BLE001
                    pass
            if self.dirty:
                await asyncio.sleep(3)
                self._dirty_evt.set()

    async def _dir_loop(self):
        while True:
            if self.d is not None:
                try:
                    pairs = await asyncio.wait_for(self._items(), 25)
                    versioned = {k[4:] for k, _ in pairs if k.startswith("ver:")}
                    keys = set()
                    for k, v in pairs:
                        keys.add(k)
                        if k.startswith("agent:"):
                            n = k[6:]
                            if n in self.local_names:
                                continue
                            if time.time() - v.get("seen", 0) > 3600:
                                asyncio.create_task(guarded(self.d.pop.aio(k)))   # long gone: forget it
                                self.directory.pop(n, None)
                                continue
                            self.directory[n] = v
                        elif k.startswith("ver:"):
                            sk = k[4:]
                            mergeable = self.merge is not None and sk.startswith("prop:")
                            lv = self.shared_ver.get(sk) or 0
                            if v == lv:
                                continue
                            if mergeable and sk in self.shared:   # a note: merge whichever copy is newer
                                val = await asyncio.wait_for(self.blobs.get.aio("shared:" + sk), 20)
                                cur = self.shared.get(sk)
                                if isinstance(cur, dict) and isinstance(val, dict):
                                    m = self.merge(sk, cur, val)
                                    if m != val:   # ours adds something: send the merged copy, stamped newest
                                        m["updated"] = max(m.get("updated", 0), v, lv) + 0.001
                                        await self.set_shared(sk, m)
                                    else:
                                        self.shared[sk], self.shared_ver[sk] = m, v
                                    if self.on_merge:
                                        self.on_merge(sk, self.shared[sk])
                                    continue
                            if v > lv and sk not in self.dirty:
                                val = await asyncio.wait_for(self.blobs.get.aio("shared:" + sk), 20)
                                cur = self.shared.get(sk)
                                if val is not None and not (isinstance(cur, dict) and isinstance(val, dict)
                                                            and cur.get("updated", 0) > val.get("updated", 0)):
                                    self.shared[sk] = val
                                self.shared_ver[sk] = v
                            elif v < lv - 2 and sk not in self.dirty and sk in self.shared:
                                self.dirty[sk] = lv   # an older copy overwrote ours on the server (a race): send ours again
                                self._dirty_evt.set()
                        elif k.startswith("shared:") and k[7:] not in versioned:   # older format, only if never rewritten
                            sk = k[7:]
                            cur = self.shared.get(sk)
                            if not (isinstance(cur, dict) and isinstance(v, dict) and cur.get("updated", 0) > v.get("updated", 0)):
                                self.shared[sk] = v
                    for n in list(self.directory):
                        if n not in self.local_names and "agent:" + n not in keys:
                            self.directory.pop(n, None)
                    self._persist_shared()
                    self.synced.set()
                except Exception:  # noqa: BLE001
                    pass
            await asyncio.sleep(5)

    async def _items(self):
        out = []
        async for k, v in self.d.items.aio():
            if isinstance(k, str) and (k.startswith(("agent:", "shared:", "ver:"))) and v is not None:
                out.append((k, v))
        return out

    async def _keys(self):
        out = []
        async for k in self.d.keys.aio():
            if isinstance(k, str) and (k.startswith("agent:") or k.startswith("shared:")):
                out.append(k)
        return out
