#!/usr/bin/env python3
"""Claude Code PreToolUse hook for Bash (Monitor commands come through it too): refuse the few commands that hurt
everyone, with the reason and the safe way. Everything else runs with no prompt.

Refused: killing processes by name or pattern (pkill, killall, pgrep/ps | xargs kill, kill $(pgrep ...));
a foreground `wait`, `sleep` of 20 s or more, or a loop that sleeps (fine with run_in_background); recursive
deletes outside the repo and /tmp (or of the repo itself, .git, a top-level shared folder, a glob at a top
level, via '..', variables or ~); force pushes; git reset --hard; git clean -f; git branch -D; git stash /
restore / checkout -- of whole folders in the shared repo folder (fine in a separate worktree); sudo; curl | sh;
Modal deletes; any write to the organizers' site (POST/PUT/PATCH/DELETE, -d/--data/-F/-T to
pokerbot.sequoiacap.com or /tournament/api).

Reads the hook JSON on stdin; prints {"hookSpecificOutput": {... "permissionDecision": "deny" ...}} or nothing;
always exits 0. Any error inside means allow (a broken guard must never stop work). Wired in .claude/settings.json.
Test by hand:  echo '{"tool_name":"Bash","tool_input":{"command":"pkill -f x"}}' | python3 scripts/guard.py
"""

import json
import os
import re
import shlex
import sys
import time

PROC_KILL = re.compile(
    r"\bpkill\b|\bkillall5?\b"
    r"|\b(?:pgrep|pidof)\b[^\n;&]*\|\s*xargs\s+(?:-\S+\s+)*kill\b"
    r"|\bps\b[^\n;&]*\|[^\n;&]*\bxargs\s+(?:-\S+\s+)*kill\b"
    r"|\bkill\b[^\n;&|]*(?:\$\(|`)\s*(?:pgrep|pidof|ps)\b"
    r"|\bkill\s+(?:-\S+\s+)*-1\b|\bkill\s+(?:-\S+\s+)*0\b")
BLOCKING = re.compile(r"(?:^|[;&|\n]\s*)wait(?:\s+%?\$?\w+)*\s*(?:$|[;&|\n])|\bsleep\s+(?:[2-9]\d|\d{3,}|\d+(?:\.\d+)?[mh]\b)"
                      r"|\b(?:while|until)\b[^\n]*\bsleep\b")
GIT = r"\bgit(?:\s+-[Cc]\s+\S+)*\s+"
DANGER = [
    (r"\brm\s+(?:-\S*[rR]|--recursive)", "a recursive delete outside the repo and /tmp (or of a whole shared folder)"),
    (r"\bfind\b[^\n]*\s-delete\b", "find -delete outside the repo and /tmp"),
    (r"\bfind\b[^\n]*\s-exec(?:dir)?\s+rm\b", "find -exec rm outside the repo and /tmp"),
    (r"rmtree", "rmtree of a folder outside the repo and /tmp"),
    (r"(?<![.\w])unlink\s+(?!\()", "unlink outside the repo and /tmp"),   # the shell command (not os.unlink(p))
    (GIT + r"push\b[^\n;&|]*(?:--force|\s-f\b|\s\+\S)", "a force push"),
    (GIT + r"reset\b[^\n;&|]*--hard", "git reset --hard"),
    (GIT + r"clean\b[^\n;&|]*\s-\w*f", "git clean -f"),
    (GIT + r"clean\b[^\n;&|]*--force", "git clean --force"),
    (GIT + r"branch\b[^\n;&|]*\s-D\b", "git branch -D"),
    (r"\bsudo\b", "sudo"),
    (r"\bmkfs", "mkfs"),
    (r"\b(?:curl|wget)\b[^|\n]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b", "piping a download into a shell"),
    (r"chmod\s+-R\s+777", "chmod -R 777"),
    (r"\bdd\s+if=", "dd"),
    (r">\s*/dev/(?:sd|disk)", "writing to a disk device"),
    (r"\bmodal\s+(?:app\s+(?:delete|rm)|volume\s+(?:rm|delete)|secret\s+(?:delete|rm)|environment\s+delete)",
     "a Modal delete (use `modal app stop --yes <id>` to stop an app)"),
]
_W = r"(?:-X\s*(?:POST|PATCH|PUT|DELETE)\b|--request[=\s]+(?:POST|PATCH|PUT|DELETE)\b|--data\b|--data-\w+|\s-d\s|\s-F\s|--form\b|\s-T\s|--upload-file\b|--json\b|--post-data\b|--post-file\b|--method[=\s]+(?:POST|PATCH|PUT|DELETE)\b)"
_SITE = r"(?:pokerbot\.sequoiacap\.com|/tournament/api)"
PORTAL_WRITE = [re.compile(_SITE + r"[^\n]*" + _W, re.I), re.compile(_W + r"[^\n]*" + _SITE, re.I),
                re.compile(r"\.(?:post|patch|put|delete)\([^\n]*(?:sequoiacap|tournament/api)", re.I),
                re.compile(r"method\s*=\s*['\"](?:POST|PATCH|PUT|DELETE)['\"][^\n]*(?:sequoiacap|tournament/api)"
                           r"|(?:sequoiacap|tournament/api)[^\n]*method\s*=\s*['\"](?:POST|PATCH|PUT|DELETE)['\"]", re.I)]
# shared top-level folders of the repo: never deleted whole (their contents, one by one, are fine)
PROTECT = (".git", ".claude", "bot", "releases", "strategy", "notes", "state", "data", "data/rounds", "inbox",
           "scripts", "analysis", "candidates", "theory", "theory/out", "rig", "prompts", "starter-kit")

PROC_KILL_HELP = ("Not run: killing processes by name or pattern (pkill, killall, pgrep/ps | xargs kill, kill $(pgrep ...)) "
                  "also matches the Claude sessions' own processes, whose command lines contain their instructions; it "
                  "killed every agent in a rehearsal. Stop only what you started, by PID: start background jobs as "
                  "`cmd > /tmp/<job>.log 2>&1 & echo $! > /tmp/<job>.pid`, then `kill $(cat /tmp/<job>.pid)`. Modal: "
                  "`modal app stop --yes <app-id>` (see `modal app list`). If these words were only text (a search, a file "
                  "you're writing), write them as p[k]ill / kill[a]ll or use the Write tool.")
BLOCKING_HELP = ("Not run: a foreground `wait`, a `sleep` of 20 s or more, or a loop that sleeps blocks your whole turn, "
                 "so the humans and your inbox can't reach you until it ends. Start long jobs in the background with a "
                 "log (`cmd > /tmp/x.log 2>&1 &`, or the Bash tool's run_in_background), end your turn, and check the "
                 "log when you're next woken (a subagent's report or an inbox line wakes you).")
RISKY_HELP = ("This is on the short list of dangerous actions: deleting outside the repo and /tmp (or the repo itself, "
              ".git, a whole shared top-level folder, a glob at a top level, via '..', variables or ~); force pushes; git "
              "reset --hard; git clean -f; git branch -D; git stash / restore / checkout -- of folders in the shared repo "
              "folder (both sessions' uncommitted work lives there); sudo; Modal deletes; curl | sh; writes to the "
              "organizers' site (the portal is read-only for agents: only Dylan uploads). Do it a safer way: name the "
              "exact paths inside your own folder, a normal push, a new branch, a separate git worktree (git worktree "
              "add /tmp/<name>), or ask your main session why it's needed. Text for a file: use the Write tool.")


def blocking(cmd: str) -> bool:
    """A foreground wait / long sleep / sleep loop; heredoc bodies and backgrounded segments (`... &`) don't count."""
    c = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?.*?\n.*?\n\1\b", "", cmd, flags=re.S)
    c = re.split(r"(?<!&)&(?![&>])", c)[-1]   # whatever ran before a lone `&` is in the background
    total = sum(float(x) * (60 if u == "m" else 3600 if u == "h" else 1)
                for x, u in re.findall(r"\bsleep\s+(\d+(?:\.\d+)?)([mh]?)\b", c))
    return bool(BLOCKING.search(c)) or total >= 20


HEREDOC = re.compile(r"([^\n]*?)<<-?[ \t]*(['\"]?)(\w+)\2([^\n]*)\n(.*?)\n[ \t]*\3[ \t]*(?=\n|$)", re.S)


def strip_text_heredocs(cmd: str) -> str:
    """Drop the bodies of heredocs that only write text (cat/tee > file <<EOF): they aren't run. A heredoc fed to a
    shell or an interpreter (bash <<EOF, python3 - <<EOF) stays checked."""
    def repl(m):
        pre = re.split(r"&&|\|\||;|\|", m.group(1))[-1]
        if re.match(r"\s*(?:cat|tee)\b", pre):
            return m.group(1) + "<<" + m.group(2) + m.group(3) + m.group(2) + m.group(4) + "\n" + m.group(3)
        return m.group(0)
    return HEREDOC.sub(repl, cmd)


def project_root(cwd: str) -> str:
    p = os.environ.get("CLAUDE_PROJECT_DIR")
    if p:
        return os.path.realpath(p)
    d = os.path.realpath(cwd or os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.realpath(cwd or os.getcwd())
        d = parent


def split_segments(cmd: str) -> list:
    return [s for s in re.split(r"&&|\|\||;|\||\n", cmd)]


def _abs(t: str, cwd: str) -> str:
    home = os.path.expanduser("~")
    if t.startswith("~"):
        t = home + t[1:]
    return os.path.normpath(t if t.startswith("/") else os.path.join(cwd or "/", t))


def scrub_deletes(cmd: str, project: str, cwd: str) -> str:
    """hub.py's tmp_scrub: drop deletions (rm, unlink, find ... -name ... -delete) whose every target is inside the
    repo, /tmp or $TMPDIR and isn't a root itself, .git, a shared top-level folder, a glob at a top level, or outside
    via '..'; leave everything else for the danger check."""
    real = lambda p: os.path.realpath(p) if os.path.exists(p) else p  # noqa: E731
    safe = [r.rstrip("/") for r in ([project] if project else [])] + ["/tmp", "/private/tmp"]
    tmpdir = os.environ.get("TMPDIR", "").rstrip("/")
    if tmpdir:
        safe.append(os.path.realpath(tmpdir))
    prot = {project} | {os.path.join(project, x) for x in PROTECT} if project else set()

    def inside(t: str, cwd_: str) -> bool:
        if re.match(r"^\$\{?TMPDIR\}?/[^*?\[]", t):
            return True
        if "$(" in t or "`" in t:
            return False      # a command's output: anything
        if "$" in t:
            # an unknown variable: judge the literal part before it. "/tmp/x-$k" or "$SP/run/$v" (SP set earlier in
            # this command) stays inside its folder whatever the variable holds; "$X/y", "/tmp/$k" or "data/$k"
            # could be a top-level folder (or the root) when the variable is empty: refused
            lit = t[:t.find("$")]
            if not lit or lit.endswith("/"):
                return bool(lit.strip("/")) and inside(lit.rstrip("/"), cwd_)
            lp = _abs(lit, cwd_)
            stem = os.path.join(real(os.path.dirname(lp)), os.path.basename(lp))
            if any(x.startswith(stem) for x in prot):     # "dat$x" could be data/, "rel$x" releases/
                return False
            return inside(lit, cwd_)
        p = _abs(t, cwd_)
        p = os.path.join(real(os.path.dirname(p)), os.path.basename(p)) if not any(c in p for c in "*?[") else p
        judge = p
        if any(c in p for c in "*?["):
            judge = os.path.dirname(p)          # a glob: judge the folder it expands in
            if any(c in judge for c in "*?["):
                judge = re.split(r"[*?\[]", judge)[0].rstrip("/")
            if judge in safe or judge in prot:
                return False
        if not any(judge == r or judge.startswith(r + "/") for r in safe) or p in safe or p in prot:
            return False
        if project and (p == os.path.join(project, ".git") or p.startswith(os.path.join(project, ".git") + "/")):
            return False
        return True

    out, env = [], {}

    def sub(t: str) -> str:   # $NAME / ${NAME} set earlier in this same command (SP=/private/tmp/...; rm -rf $SP/x)
        return re.sub(r"\$\{?(\w+)\}?", lambda m: env.get(m.group(1), m.group(0)), t)

    for part in re.split(r"(&&|\|\||(?<!\\);|\||\n)", cmd):
        try:
            toks = shlex.split(part)
        except ValueError:
            out.append(part)
            continue
        while toks and toks[0] in ("do", "then", "else", "{", "(", "!", "export"):   # the command follows the keyword
            toks = toks[1:]
        if toks and all(re.fullmatch(r"\w+=\S*", x) for x in toks):   # NAME=value on its own: remembered
            for x in toks:
                k, v = x.split("=", 1)
                env[k] = sub(v)
            out.append(part)
            continue
        while toks and re.fullmatch(r"\w+=\S*", toks[0]):
            toks = toks[1:]
        toks = [sub(x) for x in toks]
        if toks and (toks[0] in ("grep", "egrep", "fgrep", "rg", "ag", "ack") or toks[:2] == ["git", "grep"]) \
                and "$(" not in part and "`" not in part:
            continue      # it only reads: a pattern like "rmtree" or "rm -rf" is text
        if toks and toks[0] == "cd" and len(toks) > 1:
            cwd = _abs(toks[1], cwd)
        if toks and toks[0] in ("rm", "unlink"):
            targets = [t for t in toks[1:] if not t.startswith("-")]
            if targets and all(inside(t, cwd) for t in targets):
                continue
        ex = toks.index("-exec") if "-exec" in toks else -1     # find ... -exec rm -rf {} +: as find -delete
        if toks and toks[0] == "find" and len(toks) > 1 and ("-name" in toks or "-iname" in toks) and \
                ("-delete" in toks or toks[ex + 1:ex + 2] == ["rm"] and ex > 0):
            base = _abs(toks[1], cwd)   # selected files only
            if any(base == r or base.startswith(r + "/") for r in safe) and not base.startswith(os.path.join(project, ".git")):
                continue
        out.append(part)
    c = "".join(out)
    return re.sub(r"shutil\.rmtree\(\s*['\"](?![/~.])[^'\"]+['\"]", "", c)   # a relative folder of its own


def in_main_tree(d: str, project: str) -> bool:
    if not project:
        return False
    rp = os.path.realpath(d)
    if not (rp == project or rp.startswith(project + "/")):
        return False
    return not rp.startswith(os.path.join(project, ".claude", "worktrees") + "/")


def wide(paths: list, gdir: str) -> bool:
    for p in paths:
        if p in (".", "./", ":/", ":(top)", "*", "-A", "--all") or p.endswith("/") or any(c in p for c in "*?["):
            return True
        if os.path.isdir(_abs(p, gdir)):
            return True
    return False


def git_issue(cmd: str, cwd: str, project: str):
    """git stash / restore / checkout -- that would throw away uncommitted work in the shared repo folder."""
    for part in split_segments(cmd):
        try:
            toks = shlex.split(part)
        except ValueError:
            continue
        while toks and (re.fullmatch(r"\w+=\S*", toks[0]) or toks[0] in ("command", "nohup", "time", "env")):
            toks = toks[1:]
        if not toks:
            continue
        if toks[0] == "cd" and len(toks) > 1:
            cwd = _abs(toks[1], cwd)
            continue
        if toks[0] != "git":
            continue
        gdir, i = cwd, 1
        while i < len(toks) and toks[i].startswith("-"):
            if toks[i] in ("-C", "-c") and i + 1 < len(toks):
                if toks[i] == "-C":
                    gdir = _abs(toks[i + 1], gdir)
                i += 2
                continue
            i += 1
        if i >= len(toks) or not in_main_tree(gdir, project):
            continue
        sub, args = toks[i], toks[i + 1:]
        if sub == "stash" and (not args or args[0] not in ("list", "show")):
            return "git stash in the shared repo folder (it would take the other session's uncommitted work too)"
        if sub == "restore":
            staged_only = ("--staged" in args or "-S" in args) and not ("--worktree" in args or "-W" in args)
            paths = [a for a in args if not a.startswith("-")]
            if not staged_only and (not paths or wide(paths, gdir)):
                return "git restore of a whole folder in the shared repo folder (it discards everyone's uncommitted work there)"
        if sub == "checkout":
            if "-f" in args or "--force" in args:
                return "git checkout -f in the shared repo folder"
            paths = args[args.index("--") + 1:] if "--" in args else (args if args[:1] == ["."] else [])
            if ("--" in args or paths) and (not paths or wide(paths, gdir)):
                return "git checkout -- of a whole folder in the shared repo folder (it discards uncommitted work)"
    return None


def decide(inp: dict):
    """None (allow) or the reason to refuse."""
    tool = inp.get("tool_name") or ""
    ti = inp.get("tool_input") or {}
    cmd = ti.get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        return None
    cwd = inp.get("cwd") or os.getcwd()
    project = project_root(cwd)
    text = strip_text_heredocs(cmd)
    if PROC_KILL.search(text):
        return PROC_KILL_HELP
    # a Monitor's command (e.g. `python3 scripts/feed.py builder`) runs long by design and doesn't hold the turn; it
    # may reach this hook as Bash, recognisable by the Monitor's own input fields
    monitor = tool == "Monitor" or "timeout_ms" in ti or "ws" in ti
    if not monitor and not ti.get("run_in_background") and blocking(cmd):
        return BLOCKING_HELP
    for rx in PORTAL_WRITE:
        if rx.search(text):
            return "Not run (a write to the organizers' site). " + RISKY_HELP
    scrubbed = scrub_deletes(text, project, os.path.realpath(cwd) if os.path.isdir(cwd) else cwd)
    for rx, why in DANGER:
        if re.search(rx, scrubbed):
            return f"Not run ({why}). " + RISKY_HELP
    why = git_issue(text, cwd, project)
    if why:
        return f"Not run ({why}). " + RISKY_HELP
    return None


def log(project: str, cmd: str, reason: str) -> None:
    try:
        path = os.path.join(project, "state", "guard.log")
        if os.path.isdir(os.path.dirname(path)):
            with open(path, "a") as f:
                f.write(f"{time.strftime('%H:%M:%S')} refused: {cmd[:300]!r} :: {reason[:80]}\n")
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    try:
        inp = json.loads(sys.stdin.read() or "{}")
        reason = decide(inp)
        if reason:
            log(project_root(inp.get("cwd") or os.getcwd()), (inp.get("tool_input") or {}).get("command", ""), reason)
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                     "permissionDecisionReason": reason}}))
    except Exception:  # noqa: BLE001   a broken guard must never stop work
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
