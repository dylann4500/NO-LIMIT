"""Meta drift: tune against a field dominated by the previous round's bot, repeatedly.
Cross-table of every round's bot against every round's field."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
ROUNDS = 3

def p(i):
    return os.path.join(HERE, "tuned_robust.json" if i == 0 else f"tuned_meta{i}.json")

def tune(i):
    env = dict(os.environ, CAND_PATH=p(i - 1))
    out = subprocess.run([PY, "-u", "tune.py", f"meta{i}", "top3,steep,linear", "mirror,all_mirror", "10", "80", "10"], env=env, cwd=HERE, capture_output=True, text=True)
    print(f"tuned round {i}:", out.stdout.splitlines()[-40:][0] if out.stdout else out.stderr[-400:], flush=True)

def cross():
    code = """
import json, os, sys
sys.path.insert(0, %r)
from run import evaluate
if __name__ == '__main__':
    names = json.loads(os.environ['H'])
    H = {k: json.load(open(v))['mu'] for k, v in names.items()}
    H['tag'] = 'tag'
    r, _ = evaluate(H, field=os.environ['F'], payouts=['top3', 'steep', 'linear'], tables=4000, seed=77)
    print(json.dumps({k: {q: round(v[q][0], 2) for q in v} for k, v in r.items()}))
""" % HERE
    names = {f"r{i}": p(i) for i in range(ROUNDS + 1)}
    for f in ["all_mirror", "mirror", "holdout", "typical"]:
        for i in range(ROUNDS + 1):
            if f not in ("all_mirror", "mirror") and i > 0:
                continue
            env = dict(os.environ, CAND_PATH=p(i), H=json.dumps(names), F=f)
            o = subprocess.run([PY, "-c", code], env=env, capture_output=True, text=True, cwd=HERE)
            print(f"field={f} (cand=r{i}):", o.stdout.strip() or o.stderr[-300:], flush=True)

if __name__ == "__main__":
    for i in range(1, ROUNDS + 1):
        tune(i)
    cross()
    for i in range(ROUNDS + 1):
        m = json.load(open(p(i)))["mu"]
        print(f"r{i}", {k: round(m[k], 3) for k in ["open_a", "open_b", "hu_open", "jam_m", "jam_scale", "call_jam", "call_open", "threebet", "call_margin", "value_eq", "bluff_freq", "bet_frac"]})
