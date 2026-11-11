"""Sequential experiment driver. One process, no pgrep, each stage isolated; a failed stage is logged and skipped."""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
BUDGET_MIN = float(sys.argv[1])
T0 = time.time()
LOG = open(os.path.join(HERE, "progress.log"), "a", buffering=1)

def say(s):
    LOG.write(f"[{(time.time()-T0)/60:5.1f}m] {s}\n")

def run(name, cmd, env=None, out=None):
    if (time.time() - T0) / 60 > BUDGET_MIN:
        say(f"SKIP {name}: over budget")
        return False
    say(f"start {name}")
    t = time.time()
    with open(os.path.join(HERE, out or f"{name}.log"), "w") as f:
        r = subprocess.run([PY, "-u"] + cmd, cwd=HERE, env=dict(os.environ, **(env or {})), stdout=f, stderr=subprocess.STDOUT)
    say(f"{'done' if r.returncode == 0 else 'FAILED rc=%d' % r.returncode} {name} in {(time.time()-t)/60:.1f}m")
    return r.returncode == 0

BASE = {"TUNE_TABLE": "1", "TUNE_BASE": "1", "START_JSON": "tuned_robust.json"}
ALLF = "typical,strong,aggro,passive"
ALLP = "top3,linear,steep,wta"
run("A_tune_lookup", ["tune.py", "lookup", ALLP, ALLF, "12", "60", "10"], BASE)
run("B_compare", ["exp2.py", "compare"])
run("G_sensitivity", ["exp2.py", "sensitivity"])
for p in ["top3", "linear", "steep", "wta"]:
    run(f"C_tune_{p}", ["tune.py", f"lookup_{p}", p, ALLF, "10", "60", "10"], dict(BASE, START_JSON="tuned_lookup.json"))
run("C_specific", ["exp2.py", "specific"])
run("D_tune_v3", ["tune.py", "lookup_v3", ALLP, ALLF, "10", "60", "10"], {"TUNE_TABLE": "1", "START_JSON": "tuned_lookup.json"})
run("D_v3", ["exp2.py", "v3"])
for i in (1, 2, 3):
    prev = "tuned_lookup.json" if i == 1 else f"tuned_meta{i-1}.json"
    run(f"E_tune_meta{i}", ["tune.py", f"meta{i}", "top3,steep,linear", "mirror,all_mirror", "8", "60", "10"],
        {"TUNE_TABLE": "1", "TUNE_BASE": "1", "START_JSON": prev, "CAND_PATH": prev, "CAND_TABLE": "1"})
run("E_meta", ["exp2.py", "meta"])
say("ALL DONE")
