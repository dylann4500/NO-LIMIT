"""Message bus between agents, on one laptop and across both.

- Agent -> agent on the same laptop: delivered in-process at once.
- Agent -> agent on the other laptop: put on a Modal Queue partition named after the receiving person
  ("to-samuel" / "to-dylan"). Only internet access is needed, so a phone hotspot is fine.
- Every outgoing remote message is written to a local outbox first and retried until Modal accepts it,
  so a dropped connection loses nothing. Receivers drop duplicates by message id.
- A shared Modal Dict holds the directory: every agent's name, owner, state and one-line status, so
  each side knows who exists and what they are doing.
If Modal is unavailable, the bus runs local-only and says so in the UI.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Awaitable, Callable

QUEUE = "avalon-hub-bus"
DIRECTORY = "avalon-hub-dir"


def new_id() -> str:
    return "m" + uuid.uuid4().hex[:12]


class Bus:
    def __init__(self, person: str, data: Path, deliver: Callable[[dict], Awaitable[None]], namespace: str = ""):
        self.person = person
        self.data = data
        self.deliver = deliver  # called with a message addressed to one of OUR agents
        self.ns = namespace
        self.outbox_file = data / "outbox.jsonl"
        self.seen_file = data / "seen.json"
        self.seen: set[str] = set(json.loads(self.seen_file.read_text())) if self.seen_file.exists() else set()
        self.outbox: list[dict] = [json.loads(l) for l in self.outbox_file.open()] if self.outbox_file.exists() else []
        self.directory: dict[str, dict] = {}
        self.local_names: set[str] = set()
        self.online = False
        self.error = ""
        self.q = self.d = None
        self._wake = asyncio.Event()

    # ------------------------------------------------------------ setup
    async def start(self):
        try:
            import modal
            self.q = modal.Queue.from_name(QUEUE + self.ns, create_if_missing=True)
            self.d = modal.Dict.from_name(DIRECTORY + self.ns, create_if_missing=True)
            await self.d.put.aio("__ping__", time.time())
            self.online = True
        except Exception as e:  # noqa: BLE001
            self.online, self.error = False, f"Modal unavailable ({type(e).__name__}: {e}); messages stay on this laptop"
        asyncio.create_task(self._send_loop())
        asyncio.create_task(self._recv_loop())
        asyncio.create_task(self._dir_loop())

    # ------------------------------------------------------------ sending
    def person_of(self, agent: str) -> str | None:
        if agent in self.local_names:
            return self.person
        e = self.directory.get(agent)
        if e:
            return e.get("person")
        if agent.startswith("s-"):
            return "samuel"
        if agent.startswith("d-"):
            return "dylan"
        return None

    async def send(self, msg: dict) -> str:
        msg.setdefault("id", new_id())
        msg.setdefault("at", time.time())
        to_person = self.person_of(msg["to"])
        if to_person is None:
            raise ValueError(f"unknown agent '{msg['to']}'")
        if to_person == self.person:
            await self._accept(msg)
            return "delivered"
        self.outbox.append(msg)
        self._save_outbox()
        self._wake.set()
        return "queued for the other laptop" if not self.online else "sent"

    def _save_outbox(self):
        tmp = self.outbox_file.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(m) + "\n" for m in self.outbox))
        tmp.replace(self.outbox_file)

    async def _send_loop(self):
        delay = 1.0
        while True:
            if self.outbox and self.q is not None:
                msg = self.outbox[0]
                try:
                    await self.q.put.aio(msg, partition="to-" + self.person_of(msg["to"]))
                    self.outbox.pop(0)
                    self._save_outbox()
                    self.online, self.error, delay = True, "", 1.0
                    continue
                except Exception as e:  # noqa: BLE001
                    self.online, self.error = False, f"retrying send: {type(e).__name__}"
                    delay = min(delay * 2, 20)
            self._wake.clear()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=delay if self.outbox else 30)
            except asyncio.TimeoutError:
                pass

    # ------------------------------------------------------------ receiving
    async def _accept(self, msg: dict):
        if msg["id"] in self.seen:
            return
        self.seen.add(msg["id"])
        self.seen_file.write_text(json.dumps(sorted(self.seen)[-5000:]))
        await self.deliver(msg)

    async def _recv_loop(self):
        delay = 1.0
        while True:
            if self.q is None:
                await asyncio.sleep(30)
                continue
            try:
                try:
                    items = await self.q.get_many.aio(50, partition="to-" + self.person, timeout=10)
                except Exception as e:  # noqa: BLE001  (an empty queue after the timeout is normal)
                    if type(e).__name__ != "Empty":
                        raise
                    items = []
                self.online, self.error, delay = True, "", 1.0
                for m in items:
                    try:
                        await self._accept(m)
                    except Exception:  # noqa: BLE001
                        pass
            except Exception as e:  # noqa: BLE001
                self.online, self.error = False, f"retrying receive: {type(e).__name__}"
                await asyncio.sleep(delay)
                delay = min(delay * 2, 20)

    # ------------------------------------------------------------ directory
    async def publish(self, name: str, info: dict):
        info = dict(info, person=self.person, seen=time.time())
        self.directory[name] = info
        if self.d is not None:
            try:
                await self.d.put.aio("agent:" + name, info)
            except Exception:  # noqa: BLE001
                pass

    async def _dir_loop(self):
        while True:
            if self.d is not None:
                try:
                    fresh = {}
                    async for k in self.d.keys.aio():
                        if isinstance(k, str) and k.startswith("agent:"):
                            v = await self.d.get.aio(k)
                            if v:
                                fresh[k[6:]] = v
                    for k, v in fresh.items():
                        if k not in self.local_names:
                            self.directory[k] = v
                except Exception:  # noqa: BLE001
                    pass
            await asyncio.sleep(5)
