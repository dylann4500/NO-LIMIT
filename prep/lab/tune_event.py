"""One-command event tune. Warm-starts from a params file on the blended field, with the real points table
weighted double if event_config.json exists, then reports old vs. new on fields the tuner never saw.

usage: tune_event.py --base tuned_final.json --out tuned_T2.json [--tuner cma] [--tables 40000] [--sigma 0.06] [--fields a,b] [--selfplay tuned_T1.json]
                     [--worst 0.5] [--verdict-fields gen_hold,holdout,stress_mix]
       tune_event.py --cls portal --dir v2 --base defaults --out v2/params_tuned.json [same options]
A cold retune for a new variant: --sigma 0.2. Exploiter files (exploit_*.json) next to this script join the field automatically.
--worst L scores each candidate as mean over fields - L * (mean - worst field). Generated fields: see genfield.py.
--cls portal tunes the portal bot in lab/<dir> (as it would upload, through the platform stand-in and its time limits)
over mtune.PORTAL_SEARCH[<dir>]. --base is "defaults" (the core's own constants), "live" (<dir>/params.json) or a params
file; --out is written flat, in params.json format, so promoting is a copy.
Exit code 0 means new beat or matched old summed over the verdict fields, so it may be submitted after the gate.
"""
import argparse, json, math, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--tuner", default="cma"); ap.add_argument("--tables", type=int, default=40000); ap.add_argument("--sigma", type=float, default=0.06)
    ap.add_argument("--procs", type=int, default=max(2, (os.cpu_count() or 4) - 2))
    ap.add_argument("--selfplay", default=None); ap.add_argument("--eval-tables", type=int, default=3000)
    ap.add_argument("--fields", default=None); ap.add_argument("--cls", default="table"); ap.add_argument("--dir", default="v2")
    ap.add_argument("--worst", type=float, default=0.0); ap.add_argument("--verdict-fields", default="holdout,stress_mix")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    portal = a.cls == "portal"
    # Workers import field.py fresh, so these must be set before any pool starts. A portal base is not a lab Hero file.
    if a.selfplay or not portal:
        os.environ["CAND_PATH"] = a.selfplay or a.base
    os.environ["CAND_TABLE"] = "1"
    ex = sorted(f for f in os.listdir(here) if f.startswith("exploit_") and f.endswith(".json"))
    os.environ["EXPLOIT_PATHS"] = ",".join(os.path.join(here, f) for f in ex)
    import mtune
    from run import evaluate, PAYOUTS, portal_defaults
    if portal:
        search = mtune.PORTAL_SEARCH[os.path.basename(os.path.normpath(a.dir))]
        fixed = {"cls": "portal", "dir": a.dir}
        if a.base == "defaults":
            base = portal_defaults(a.dir, list(search))
        else:
            b = json.load(open(os.path.join(here, a.dir, "params.json") if a.base == "live" else a.base))
            base = dict(portal_defaults(a.dir, list(search)), **b.get("mu", b))
        spec = lambda p: dict(fixed, p=dict(p))
    else:
        search, fixed = mtune.FULL_SEARCH, a.cls
        base = json.load(open(a.base))["mu"]
        spec = lambda p: dict(p, cls=a.cls)
    pays = ["real", "real", "top3", "steep"] if "real" in PAYOUTS else mtune.ALLP
    flds = a.fields.split(",") if a.fields else (mtune.ROBUST_FIELDS if ex else mtune.BLEND_FIELDS)
    start = dict(base)
    print(f"tuning {a.dir if portal else a.cls} on {','.join(flds)}, worst-field weight {a.worst}", flush=True)
    if portal:
        print("start: " + json.dumps(base), flush=True)
    x, log, used, sec = mtune.tune(a.tuner, fixed, search, start, a.tables, fields=flds, payouts=pays, procs=a.procs, sig0=a.sigma, worst=a.worst)
    for k in ("cls", "dir"):
        x.pop(k, None)
    json.dump(x if portal else {"mu": x}, open(a.out, "w"), indent=0)
    print(f"tuned {used} tables in {sec:.0f}s -> {a.out}")
    if portal:
        print("new: " + json.dumps({k: round(v, 4) for k, v in x.items()}), flush=True)
    p = "real" if "real" in PAYOUTS else "steep"
    d = var = 0.0
    for f in a.verdict_fields.split(","):
        fails = {}
        r, _ = evaluate({"old": spec(base), "new": spec(x)}, field=f, payouts=[p], tables=a.eval_tables, procs=a.procs, seed=int(time.time()) % 100000, fails=fails)
        o, n = r["old"][p], r["new"][p]
        d += n[0] - o[0]
        var += o[1] ** 2 + n[1] ** 2
        fl = "".join(f"  {h} failed {100 * sum(v for k, v in c.items() if k != 'decisions') / max(1, c.get('decisions', 0)):.2f}%" for h, c in fails.items())
        print(f"{f:12} old {o[0]:7.2f}±{o[1]:.2f}  new {n[0]:7.2f}±{n[1]:.2f}  diff {n[0] - o[0]:+.2f}±{math.sqrt(o[1] ** 2 + n[1] ** 2):.2f}  on {p}{fl}", flush=True)
    print(f"sum of differences {d:+.2f}±{math.sqrt(var):.2f}")
    print("VERDICT:", "promote (still run the gate)" if d >= 0 else "KEEP OLD: new lost on opponents the tuner never saw")
    sys.exit(0 if d >= 0 else 1)
