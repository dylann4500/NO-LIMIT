"""Runs after driver.py. Fair MC comparison: gives Monte Carlo the same warm second tune the lookup received."""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
LOG = open(os.path.join(HERE, "progress2.log"), "a", buffering=1)
T0 = time.time()
def say(s): LOG.write(f"[{(time.time()-T0)/60:5.1f}m] {s}\n")
ENV = {"TUNE_BASE": "1", "START_JSON": "tuned_robust.json"}
say("start mc warm tune")
with open("F_tune_mcwarm.log", "w") as f:
    r = subprocess.run([PY, "-u", "tune.py", "mcwarm", "top3,linear,steep,wta", "typical,strong,aggro,passive", "12", "60", "10"], cwd=HERE, env=dict(os.environ, **ENV), stdout=f, stderr=subprocess.STDOUT)
say(f"mc warm tune rc={r.returncode}")
code = """
import json, sys
sys.path.insert(0, '.')
from run import evaluate
if __name__ == '__main__':
    L = lambda n: json.load(open(n))['mu']
    H = {'lookup_tuned': dict(L('tuned_lookup.json'), cls='table'), 'mc_warm_r40': L('tuned_mcwarm.json'), 'mc_warm_r15': dict(L('tuned_mcwarm.json'), rollouts=15), 'mc_warm_r100': dict(L('tuned_mcwarm.json'), rollouts=100)}
    P = ['top3', 'steep', 'linear', 'wta']
    for f in ['holdout', 'holdout_soft', 'mirror', 'typical', 'strong']:
        r, _ = evaluate(H, field=f, payouts=P, tables=5000, seed=8080)
        print('== field=' + f)
        for k, row in r.items():
            print('  ' + k.ljust(14) + ''.join(f'{p}:{row[p][0]:7.2f}±{row[p][1]:4.2f} ' for p in P), flush=True)
"""
with open("F_fair.log", "w") as f:
    r = subprocess.run([PY, "-u", "-c", code], cwd=HERE, stdout=f, stderr=subprocess.STDOUT)
say(f"ALL DONE rc={r.returncode}")
