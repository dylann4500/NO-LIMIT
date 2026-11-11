"""One-command event tune. Warm-starts from a params file on the blended field, with the real points table
weighted double if event_config.json exists, then reports old vs. new on fields the tuner never saw.

usage: tune_event.py --base tuned_blend.json --out tuned_T2.json [--tuner cem] [--tables 40000] [--cold] [--fields a,b] [--selfplay tuned_T1.json]
Exit code 0 means new beat or matched old on holdout+stress, so it may be submitted after the gate.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--tuner", default="cem"); ap.add_argument("--tables", type=int, default=40000)
    ap.add_argument("--procs", type=int, default=max(2, (os.cpu_count() or 4) - 2))
    ap.add_argument("--cold", action="store_true"); ap.add_argument("--selfplay", default=None)
    ap.add_argument("--fields", default=None); ap.add_argument("--cls", default="table")
    a = ap.parse_args()
    # Workers import field.py fresh, so these must be set before any pool starts.
    os.environ["CAND_PATH"] = a.selfplay or a.base
    os.environ["CAND_TABLE"] = "1"
    import mtune
    from run import evaluate, PAYOUTS
    base = json.load(open(a.base))["mu"]
    pays = ["real", "real", "top3", "steep"] if "real" in PAYOUTS else mtune.ALLP
    flds = a.fields.split(",") if a.fields else mtune.BLEND_FIELDS
    kw = {"sig0": 0.3 if a.cold else 0.1} if a.tuner == "cem" else {}
    start = dict(base)
    x, log, used, sec = mtune.tune(a.tuner, a.cls, mtune.BASE_SEARCH, start, a.tables, fields=flds, payouts=pays, procs=a.procs, **kw)
    x.pop("cls", None)
    json.dump({"mu": x}, open(a.out, "w"), indent=0)
    print(f"tuned {used} tables in {sec:.0f}s -> {a.out}")
    p = "real" if "real" in PAYOUTS else "steep"
    d = 0.0
    for f in ["holdout", "stress_mix"]:
        r, _ = evaluate({"old": dict(base, cls=a.cls), "new": dict(x, cls=a.cls)}, field=f, payouts=[p], tables=3000, procs=a.procs, seed=int(time.time()) % 100000)
        o, n = r["old"][p], r["new"][p]
        d += n[0] - o[0]
        print(f"{f:12} old {o[0]:7.2f}±{o[1]:.2f}  new {n[0]:7.2f}±{n[1]:.2f}  on {p}")
    print("VERDICT:", "promote (still run the gate)" if d >= 0 else "KEEP OLD: new lost on opponents the tuner never saw")
    sys.exit(0 if d >= 0 else 1)
