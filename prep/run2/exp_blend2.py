import json, sys
sys.path.insert(0, '.')
from run import evaluate
if __name__ == '__main__':
    L = lambda n: json.load(open(n))['mu']
    H = {'lookup_blend': dict(L('tuned_blend.json'), cls='table'), 'mc40_blend': L('tuned_mcblend.json'), 'mc15_blend': dict(L('tuned_mcblend.json'), rollouts=15), 'mc40_warm': L('tuned_mcwarm.json')}
    P = ['top3', 'steep', 'linear', 'wta']
    for f in ['holdout', 'stress_mix', 'typical', 'mirror']:
        r, _ = evaluate(H, field=f, payouts=P, tables=3000, seed=9090)
        print('== field=' + f)
        for k, row in r.items():
            print('  ' + k.ljust(13) + ''.join(f'{p}:{row[p][0]:7.2f}±{row[p][1]:4.2f} ' for p in P), flush=True)
