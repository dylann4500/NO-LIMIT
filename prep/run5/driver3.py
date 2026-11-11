"""Sequential: tuners, policy families, final comparison, round protocols. No process-name waits."""
import json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["CAND_PATH"] = "tuned_meta1.json"; os.environ["CAND_TABLE"] = "1"
BUDGET_MIN = float(sys.argv[1]); T0 = time.time()
LOG = open("progress.log", "a", buffering=1)
def say(s): LOG.write(f"[{(time.time()-T0)/60:5.1f}m] {s}\n")
def over(): return (time.time() - T0) / 60 > BUDGET_MIN
def L(n): return json.load(open(n))["mu"]
def save(n, mu, **kw): json.dump(dict(mu=mu, **kw), open(n, "w"), indent=0)

def stage_tuners():
    import mtune
    from run import evaluate
    from hero import DEFAULT
    start = {k: DEFAULT[k] for k in mtune.BASE_SEARCH}
    specs, rows = {}, {}
    with open("S1_tuners.log", "w", buffering=1) as f:
        for name in mtune.TUNERS:
            for seed in (1, 2, 3):
                if over(): return
                x, log, used, sec = mtune.tune(name, "table", mtune.BASE_SEARCH, start, 40000, seed=seed)
                save(f"t_{name}_{seed}.json", x, log=[(u, t) for u, t, _ in log])
                third = next((d for u, t, d in log if u >= 13000), x)
                specs[f"{name}_{seed}_early"] = third; specs[f"{name}_{seed}_final"] = x
                print(f"{name} seed {seed}: used {used} tables in {sec:.0f}s, {len(log)} steps", file=f)
                say(f"tuner {name} {seed} {sec:.0f}s")
        for fld in ["holdout", "stress_mix"]:
            r, _ = evaluate(specs, field=fld, payouts=["top3", "gym"], tables=2500, seed=2718)
            for k, v in r.items():
                rows.setdefault(k, []).append(v["gym"][0])
        for name in mtune.TUNERS:
            e = [sum(rows[f"{name}_{s}_early"]) / 2 for s in (1, 2, 3)]; z = [sum(rows[f"{name}_{s}_final"]) / 2 for s in (1, 2, 3)]
            print(f"{name:8} gym(100/60/40..; fair 31.9) mean of holdout+stress:  13k tables {sum(e)/3:6.2f} {[round(x,1) for x in e]}   40k tables {sum(z)/3:6.2f} {[round(x,1) for x in z]}", file=f)

def stage_policies():
    import mtune, methods
    b = L("tuned_blend.json")
    jobs = [
        ("ctx", "ctx", methods.ctx_search(), dict(b), 120000, {"sig0": 0.15}),
        ("ctxall", "ctx", {**mtune.BASE_SEARCH, **methods.ctx_search()}, dict(b), 200000, {"sig0": 0.12}),
        ("ev", "ev", methods.EV_SEARCH, {**b, **methods.EV_DEFAULT}, 120000, {"sig0": 0.25}),
        ("evall", "ev", {**mtune.BASE_SEARCH, **methods.EV_SEARCH}, None, 200000, {"sig0": 0.12}),
        ("resid", "linear", methods.linear_search(0.5), dict(b), 150000, {"sig0": 0.12}),
        ("scratch", "linear0", methods.linear_search(3.0), dict(b), 300000, {"sig0": 0.25}),
    ]
    for name, cls, search, start, budget, kw in jobs:
        if over(): return
        if start is None:
            start = L("p_ev.json")
        x, log, used, sec = mtune.tune("cem", cls, search, start, budget, seed=11, **kw)
        save(f"p_{name}.json", x, log=[(u, t) for u, t, _ in log])
        say(f"policy {name} {used} tables {sec:.0f}s")

def stage_q():
    import subprocess
    say("q training")
    subprocess.run([sys.executable, "-u", "qtrain.py", "tuned_blend.json", "30", "8000", "blend"], stdout=open("S3_q.log", "w"), stderr=subprocess.STDOUT)
    say("q done")

def stage_compare():
    from run import evaluate
    b, m0, m3 = L("tuned_blend.json"), L("tuned_lookup.json"), L("tuned_meta3.json")
    H = {"blend": dict(b, cls="table"), "mc15_blend": dict(L("tuned_mcblend.json"), rollouts=15)}
    for n in ["ctx", "ctxall", "ev", "evall", "resid", "scratch"]:
        if os.path.exists(f"p_{n}.json"):
            H[n] = L(f"p_{n}.json")
    if os.path.exists("q_blend.json"):
        H["q_cautious"] = dict(b, cls="q", qfile="q_blend.json", nmin=2000, delta=0.2)
        H["q_bold"] = dict(b, cls="q", qfile="q_blend.json", nmin=300, delta=0.05)
    H["switch_r0r3"] = dict(cls="switch", weak=m0, tough=m3)
    H["switch_blendr3"] = dict(cls="switch", weak=b, tough=m3)
    with open("S4_compare.log", "w", buffering=1) as f:
        P = ["gym", "top3", "linear", "wta"]
        for fld, cand in [("holdout", "tuned_blend.json"), ("holdout_soft", "tuned_blend.json"), ("stress_mix", "tuned_blend.json"), ("stress_3bet", "tuned_blend.json"), ("mirror", "tuned_blend.json"), ("all_mirror", "tuned_blend.json"), ("all_mirror", "tuned_meta3.json"), ("typical", "tuned_blend.json")]:
            if over(): return
            os.environ["CAND_PATH"] = cand
            r, _ = evaluate(H, field=fld, payouts=P, tables=4000, seed=31337)
            print(f"\n== field={fld} cand={cand}\n" + "".ljust(16) + "".join(p.rjust(14) for p in P), file=f)
            for k, row in r.items():
                print(k.ljust(16) + "".join(f"{row[p][0]:8.2f}±{row[p][1]:4.2f} " for p in P), file=f)
        os.environ["CAND_PATH"] = "tuned_meta1.json"

HID = {1: ("early_buggy", "tuned_blend.json"), 2: ("typical", "tuned_blend.json"), 3: ("strong", "tuned_blend.json"), 4: ("mirror", "tuned_lookup.json"), 5: ("hidden", "tuned_meta1.json"), 6: ("hidden", "tuned_meta3.json")}

def stage_protocols():
    import mtune
    from run import evaluate
    from field import FIELDS
    def score(mu, t, seed):
        f, c = HID[t]
        os.environ["CAND_PATH"] = c
        r, _ = evaluate({"x": dict(mu, cls="table")}, field=f, payouts=["gym"], tables=4000, seed=seed)
        return r["x"]["gym"][0]
    with open("S5_protocols.log", "w", buffering=1) as lf:
        for seed in (1, 2):
            for proto in ["frozen", "refresh", "league", "lastfield", "gated"]:
                if over(): return
                cur = L("tuned_blend.json"); hist = []; scores = []
                path = f"pv_{proto}_{seed}_0.json"; save(path, cur); hist.append(path)
                for t in range(1, 7):
                    s = score(cur, t, seed * 100 + t); scores.append(s)
                    if t == 6 or proto == "frozen":
                        continue
                    if proto == "league":
                        os.environ["CAND_LEAGUE"] = ",".join(hist); os.environ["CAND_PATH"] = hist[-1]
                        flds = ["typical", "strong", "aggro", "all_league", "league_mix"]
                    elif proto == "lastfield":
                        os.environ["CAND_PATH"] = HID[t][1]
                        flds = [HID[t][0], HID[t][0], "typical", "strong"]
                    else:
                        os.environ["CAND_PATH"] = hist[-1]
                        flds = mtune.BLEND_FIELDS
                    x, log, used, sec = mtune.tune("cem", "table", mtune.BASE_SEARCH, cur, 30000, seed=seed * 10 + t, fields=flds, payouts=["gym", "top3", "steep"], sig0=0.08, pop=20, elite=5, tables=25)
                    x.pop("cls", None)
                    if proto == "gated":
                        keep = 0.0
                        os.environ["CAND_PATH"] = hist[-1]
                        for f in ["holdout", "stress_mix"]:
                            r, _ = evaluate({"new": dict(x, cls="table"), "old": dict(cur, cls="table")}, field=f, payouts=["gym"], tables=3000, seed=t * 7)
                            keep += r["new"]["gym"][0] - r["old"]["gym"][0]
                        if keep < 0:
                            x = cur
                    cur = x
                    path = f"pv_{proto}_{seed}_{t}.json"; save(path, cur); hist.append(path)
                w = sum((i + 1) * s for i, s in enumerate(scores)) / 21.0
                print(f"seed {seed} {proto:10} weighted {w:6.2f}  rounds {[round(s,1) for s in scores]}", file=lf)
                say(f"protocol {proto} seed {seed} weighted {w:.2f}")

if __name__ == "__main__":
    from field import FIELDS
    for name, fn in [("tuners", stage_tuners), ("policies", stage_policies), ("q", stage_q), ("compare", stage_compare), ("protocols", stage_protocols)]:
        if over():
            say(f"SKIP {name}"); continue
        say(f"start {name}")
        try:
            fn()
            say(f"finished {name}")
        except Exception as e:
            import traceback
            say(f"FAILED {name}: {e}\n{traceback.format_exc()}")
    say("ALL DONE")
