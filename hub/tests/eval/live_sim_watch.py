"""Every minute: snapshot both hubs; stop everything if the weekly allowance nears the limit."""
import json, subprocess, time, urllib.request
SP = "/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/sim4"
def st(port):
    try:
        return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=20).read())
    except Exception as e:
        return {"error": str(e)}
def stop(why):
    open(f"{SP}/STOPPED", "w").write(why)
    for pat in ("simhuman.py", "namespace=-sim4", "emu/rehearsal.py --run sim4", "portal_server.py --run sim4"):
        subprocess.run(["pkill", "-f", pat])
t0 = time.time()
while True:
    rows, worst = [], 0.0
    for who, port in (("samuel", 7791), ("dylan", 7792)):
        s = st(port)
        if "error" in s:
            rows.append(f"{who}: DOWN {s['error'][:80]}"); continue
        for a in s["agents"]:
            u = a.get("usage") or {}
            if "seven_day" in str(u.get("type") or "") and u.get("used") is not None:
                worst = max(worst, float(u["used"]))
            if u.get("status") == "rejected":
                worst = max(worst, 1.0)
        rows.append(f"{who}: stage={s.get('stage')} live={(s.get('live') or {}).get('filename')} active={(s.get('portal_active') or {}).get('filename')} "
                    f"working={sum(a['state']=='working' for a in s['agents'])} err={sum(a['state']=='error' for a in s['agents'])} "
                    f"notes={len(s.get('props', []))} alerts={len(s.get('alerts', []))} bots={[b['name']+':'+b['status'] for b in s.get('bots', [])[:6]]}")
    with open(f"{SP}/watch.log", "a") as f:
        f.write(time.strftime("%H:%M:%S ") + f"weekly={worst:.2f} | " + " || ".join(rows) + "\n")
    if worst >= 0.92:
        stop(f"weekly allowance at {worst:.0%}"); break
    if time.time() - t0 > 85 * 60:
        stop("time limit (85 min)"); break
    time.sleep(60)
