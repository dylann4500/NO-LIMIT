"""Does one tune over weak and self-play fields together match both specialists?"""
import json, os, subprocess, sys
code = """
import json, os, sys
sys.path.insert(0, '.')
from run import evaluate
if __name__ == '__main__':
    L = lambda n: dict(json.load(open(n))['mu'], cls='table')
    H = {'r0_weakfield': L('tuned_lookup.json'), 'r1_selfplay': L('tuned_meta1.json'), 'r3_selfplay': L('tuned_meta3.json'), 'blend': L('tuned_blend.json'), 'tag': 'tag'}
    P = ['top3', 'steep', 'linear', 'wta']
    r, _ = evaluate(H, field=os.environ['F'], payouts=P, tables=4000, seed=1234)
    print('== field=%s cand=%s' % (os.environ['F'], os.environ['CANDN']))
    for k, row in r.items():
        print('  ' + k.ljust(13) + ''.join(f'{p}:{row[p][0]:7.2f}±{row[p][1]:4.2f} ' for p in P), flush=True)
"""
if __name__ == "__main__":
    for f, c, n in [("holdout", "tuned_lookup.json", "-"), ("typical", "tuned_lookup.json", "-"), ("all_mirror", "tuned_lookup.json", "r0"), ("all_mirror", "tuned_meta1.json", "r1"),
                    ("all_mirror", "tuned_meta3.json", "r3"), ("mirror", "tuned_meta1.json", "r1"), ("stress_mix", "tuned_lookup.json", "-"), ("all_mirror", "tuned_blend.json", "blend")]:
        env = dict(os.environ, F=f, CAND_PATH=c, CAND_TABLE="1", CANDN=n)
        o = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
        print(o.stdout.rstrip() or o.stderr[-400:], flush=True)
