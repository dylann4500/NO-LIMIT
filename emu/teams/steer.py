"""Runs inside a team's sandbox (as the `team` user): a simulated competitor steering a coding agent.

Two Claude Code sessions per phase, both in the team's folder (each resumed by its session id, so
they never mix and the competitor sees the same folder the person would):
  - the coding agent: the team's assistant, with tools and the workspace;
  - the competitor: an LLM playing the person at the keyboard. It never
    touches files; it reads the assistant's replies and decides what to type next, in character
    (persona.md), under the phase's clock.
The competitor writes the first message too, from the situation (situation.md). The loop runs
until the phase's time is up; a reply that comes in after the deadline is still kept.

usage: python3 steer.py STEER_DIR SECONDS AGENT_MODEL HUMAN_MODEL OUT_DIR
STEER_DIR holds persona.md and situation.md. Writes OUT_DIR/transcript.jsonl (the agent's
stream-json, every call in order), OUT_DIR/human.jsonl (each competitor turn) and steer.json.
"""

import json
import os
import subprocess
import sys
import time

WORK = os.environ.get("EMU_WORK", "/home/team/work")
INBOX = os.environ.get("EMU_INBOX", "/home/team/inbox")  # event mode: portal notices (practice and round results), one .md each
WAIT_RULE = """
- New results show up on the portal during the event; you'll see them marked NEW ON THE PORTAL.
- If there's genuinely nothing worth doing until new results arrive (a person would grab a coffee or watch the leaderboard), reply with exactly WAIT. Don't use it to avoid work you'd actually do."""
DONE_RULE = """
- When you're done with your assistant for this session (the submission is where you want it and there's nothing more worth doing before the deadline), reply with exactly WAIT and you'll stop typing. Don't send acknowledgements like "ok" or emoji just to fill time."""
MIN_CALL_S = 90  # don't start another exchange with less than this left
HUMAN_RULES = """You are role-playing a competitor in a live pokerbot tournament, sitting at your computer and typing to your AI coding assistant (Claude Code) in a terminal. Stay fully in character as the person below; never mention that this is a simulation or a role-play.

{persona}

How to respond:
- Each time, you'll see the clock and your assistant's latest reply (plus a short note of what it ran). Reply with ONLY the next message you type to your assistant: no quotes, no preamble, no stage directions.
- Write like a real person in a hurry: usually 1-4 sentences, sometimes a short list. You don't write code yourself. You can ask questions, ask it to research something (the rules, the kit, the hand history, poker strategy), ask for tests or numbers, push a direction, change your mind, or tell it to wrap up and make sure the submission works.
- You only know what you've read on the tournament website and what your assistant tells you. You can be wrong, impatient or distracted the way this person would be.
- Watch the clock: whatever is in submission/ when time runs out gets uploaded."""


def sh_claude(args, cwd, timeout_s, env):
    try:
        return subprocess.run(["timeout", "--signal=INT", str(max(5, int(timeout_s)))] + args, cwd=cwd,
                              stdin=subprocess.DEVNULL, capture_output=True, env=env)
    except Exception as e:  # noqa: BLE001
        return subprocess.CompletedProcess(args, 1, b"", repr(e).encode())


def parse_agent(stream: bytes) -> tuple[dict, str]:
    """The final result event, and a short note of what the agent did (commands, files)."""
    result, cmds, files = {}, [], []
    for line in stream.decode(errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result":
            result = ev
        if ev.get("type") == "assistant":
            for item in ev.get("message", {}).get("content", []):
                if item.get("type") != "tool_use":
                    continue
                inp = item.get("input", {})
                if item.get("name") == "Bash":
                    cmds.append(str(inp.get("command", ""))[:100])
                elif inp.get("file_path"):
                    files.append(f"{item['name']} {inp['file_path'].replace(WORK + '/', '')}")
    note = f"(It ran {len(cmds)} commands"
    if cmds:
        note += ", the last few: " + " | ".join(cmds[-3:])
    if files:
        note += f"; files touched: {', '.join(dict.fromkeys(files[-6:]))}"
    return result, note + ")"


def first_session(stream: bytes):
    """The session id from the stream's init event (a call cut off by the clock has no result)."""
    for line in stream.decode(errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("session_id"):
            return ev["session_id"]
    return None


def clock(start, deadline):
    el, left = int(time.time() - start), int(deadline - time.time())
    return f"[{el // 60}:{el % 60:02d} elapsed, about {max(0, left) // 60} minutes left]"


def main() -> None:
    steer_dir, seconds, agent_model, human_model, out = sys.argv[1:6]
    seconds = float(seconds)
    persona = open(f"{steer_dir}/persona.md").read().strip()
    situation = open(f"{steer_dir}/situation.md").read().strip()
    system = HUMAN_RULES.format(persona=persona)
    env = dict(os.environ)
    # Event mode (a whole tournament in one session): schedule.json gives the event's start time and
    # its timeline, and notices (practice/round results) arrive as files in INBOX.
    schedule = None
    if os.path.exists(f"{steer_dir}/schedule.json"):
        schedule = json.load(open(f"{steer_dir}/schedule.json"))
        system += WAIT_RULE
    else:
        system += DONE_RULE
    start = schedule["start"] if schedule else time.time()
    deadline = start + seconds
    calls, human_turns = [], []
    sessions = {"agent": None, "human": None}
    seen: set[str] = set()

    def clock_line() -> str:
        line = clock(start, deadline)
        if schedule:
            now = time.time() - start
            nxt = next((e for e in schedule["events"] if e["t"] > now), None)
            line = f"[{int(now) // 60}:{int(now) % 60:02d} into the event"
            if nxt:
                line += f"; next: {nxt['label']} in about {max(0, int(nxt['t'] - now)) // 60} min"
            line += "]"
        return line

    def notices() -> str:
        if not os.path.isdir(INBOX):
            return ""
        new = sorted(f for f in os.listdir(INBOX) if f.endswith(".md") and f not in seen)
        seen.update(new)
        return "".join(f"\nNEW ON THE PORTAL: {open(os.path.join(INBOX, f)).read().strip()}\n" for f in new)

    def flush() -> None:
        with open(f"{out}/human.jsonl", "w") as f:
            for h in human_turns:
                f.write(json.dumps(h) + "\n")
        summary = {
            "agent_model": agent_model, "human_model": human_model, "calls": calls,
            # Claude Code reports a resumed session's running total, so a session's cost is its last figure.
            "agent_cost_usd": round(max([c["cost_usd"] or 0 for c in calls] or [0]), 4),
            "human_cost_usd": round(max([h["cost_usd"] or 0 for h in human_turns] or [0]), 4),
            "turns": sum(c["turns"] or 0 for c in calls),
        }
        summary["cost_usd"] = round(summary["agent_cost_usd"] + summary["human_cost_usd"], 4)
        with open(f"{out}/steer.json", "w") as f:
            json.dump(summary, f, indent=1)

    def human(text: str) -> str:
        args = ["claude", "-p", text, "--model", human_model, "--output-format", "json",
                "--append-system-prompt", system,
                "--disallowedTools", "Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch,Task,NotebookEdit"]
        if sessions["human"]:
            args[1:1] = ["--resume", sessions["human"]]
        p = sh_claude(args, WORK, 180, env)
        try:
            res = json.loads(p.stdout.decode(errors="replace"))
        except ValueError:
            res = {}
        sessions["human"] = res.get("session_id") or sessions["human"]
        msg = (res.get("result") or "").strip().strip('"')
        human_turns.append({"t": round(time.time() - start, 1), "saw": text[-3000:], "typed": msg,
                            "cost_usd": res.get("total_cost_usd"), "exit": p.returncode,
                            "stderr": p.stderr.decode(errors="replace")[-300:]})
        return msg or "keep going, and make sure submission/ works"

    def wait_for_news() -> str:
        """The competitor chose to wait: idle until a notice arrives (or 5 minutes, or the end)."""
        until = min(deadline, time.time() + 300)
        while time.time() < until:
            news = notices()
            if news:
                return news
            time.sleep(10)
        return "\n(A few minutes pass; nothing new on the portal.)\n"

    message = human(f"{clock_line()}\n{situation}\n{notices()}\nWhat do you type to your assistant first?")
    failures = 0
    with open(f"{out}/transcript.jsonl", "ab") as transcript:
        while True:
            while schedule and message.strip().upper().rstrip(".") == "WAIT" and time.time() < deadline - 30:
                news = wait_for_news()
                message = human(f"{clock_line()}{news}\nWhat do you type to your assistant? (WAIT to keep waiting)")
            if time.time() > deadline - 30 or message.strip().upper().rstrip(".") == "WAIT":
                break  # out of time, or (single session) the person is done
            args = ["claude", "-p", message, "--model", agent_model, "--output-format", "stream-json",
                    "--verbose", "--dangerously-skip-permissions"]
            if sessions["agent"]:
                args[1:1] = ["--resume", sessions["agent"]]
            t0 = time.time()
            p = sh_claude(args, WORK, deadline - time.time() + 30, env)
            transcript.write(p.stdout)
            transcript.flush()
            result, note = parse_agent(p.stdout)
            sessions["agent"] = result.get("session_id") or sessions["agent"] or first_session(p.stdout)
            calls.append({"t": round(t0 - start, 1), "seconds": round(time.time() - t0, 1), "exit": p.returncode,
                          "message": message, "cost_usd": result.get("total_cost_usd"),
                          "turns": result.get("num_turns"), "is_error": result.get("is_error"),
                          "stderr": p.stderr.decode(errors="replace")[-500:]})
            flush()
            if time.time() > deadline - MIN_CALL_S:
                break
            failed = p.returncode not in (0, 124) or bool(result.get("is_error"))
            failures = failures + 1 if failed else 0
            if failed and not schedule and failures >= 3:
                break  # a short phase: auth or usage-limit trouble, stop instead of looping
            if failed and schedule:
                if failures >= 10:
                    break
                time.sleep(60 * min(failures, 5))  # rate limited or overloaded: back off, keep the session
            reply = (result.get("result") or "(no reply: the assistant stopped with an error)").strip()
            message = human(f"{clock_line()}\nYour assistant replied:\n{reply[-6000:]}\n{note}\n{notices()}\n"
                            "What do you type next?")
    flush()


if __name__ == "__main__":
    main()
