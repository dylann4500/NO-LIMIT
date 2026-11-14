import subprocess, sys, time, json, os, urllib.request
sys.path.insert(0, sys.argv[1]); import hub as H
SP = sys.argv[2]
p = subprocess.Popen(["sleep", "300"]); time.sleep(0.5)
d = H.descendants(os.getpid()); print("descendant seen:", any(pid == p.pid for pid, _ in d))
print("wrong command spared:", H.stop_processes([(p.pid, "something else")]) == 0 and p.poll() is None)
# a previous run "left" this sleep: a new hub must stop it on start
q = subprocess.Popen(["sleep", "301"], start_new_session=True); time.sleep(0.5)
cmd = next(c for pid, c in H.descendants(os.getpid()) if pid == q.pid)
os.makedirs(f"{SP}/data", exist_ok=True); json.dump([[q.pid, cmd]], open(f"{SP}/data/children.json", "w"))
subprocess.run(["git", "init", "-q", f"{SP}/repo"])
h = subprocess.Popen([sys.executable, f"{sys.argv[1]}/hub.py", "--person", "samuel", "--repo", f"{SP}/repo", "--data", f"{SP}/data",
                      "--namespace=-orph", "--port", "7841", "--no-codex", "--no-autostart"], env={**os.environ, "AVALON_NO_AGENTS": "1"},
                     stdout=open(f"{SP}/hub.log", "w"), stderr=subprocess.STDOUT)
for _ in range(60):
    try:
        urllib.request.urlopen("http://127.0.0.1:7841/api/state", timeout=2); break
    except Exception:
        time.sleep(1)
time.sleep(4)
print("leftover stopped by the new hub:", q.poll() is not None)
# a tool's worker that detached from the hub (its parent shell exited) but was in the last snapshot
r2 = subprocess.Popen(["sleep", "302"], start_new_session=True); time.sleep(0.5)
cmd2 = next(c for pid, c in H.descendants(os.getpid()) if pid == r2.pid)
json.dump([[r2.pid, cmd2]], open(f"{SP}/data/children.json", "w"))
h.send_signal(15); h.wait(20); print("hub exits cleanly on SIGTERM:", h.returncode == 0)
time.sleep(4); print("a detached worker from the last snapshot is stopped at shutdown:", r2.poll() is not None)
p.kill()
