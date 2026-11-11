"""Sequential verification through the supplied kit entry point and SDK tests."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PYTHON=sys.executable
ENV=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',POKER_REFERENCE='../openai_b_default_2/agent.py')
manifest={'files':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ['agent.py','preflop.json']},'runs':{}}
commands=[
 ('regressions',[str(HERE/'test_round2.py')]),
 ('final_stress_deep_12000',[str(HERE/'test_agent.py'),'12000','2.5']),
 ('final_stress_short_12000',[str(HERE/'test_agent.py'),'12000','2.5','short']),
 ('final_default_500',[str(ROOT/'lab/field_kit/play.py'),str(HERE),'--tables','500','--seed','612']),
 ('final_vs_round1_400',[str(HERE/'compare.py'),str(HERE),'--tables','400','--seed','613','--seats','self,self,self,self,v1,v1,v1,v1']),
 ('final_diverse_250',[str(HERE/'compare.py'),str(HERE),'--tables','250','--seed','614','--seats','self,self,tight,tight,balanced,balanced,loose,loose']),
 ('final_replay',[str(HERE/'replay.py'),str(HERE/'agent.py'),str(HERE/'results/final_replay.json')]),
]
for name,args in commands:
    dest=HERE/'results'/(name+('.txt' if name in ('regressions','final_replay') else '.json'))
    print('Starting',name,flush=True);t=time.monotonic()
    with dest.open('w') as out:subprocess.run([PYTHON]+args,cwd=ROOT,env=ENV,stdout=out,check=True)
    manifest['runs'][name]={'command':[PYTHON]+args,'seconds':round(time.monotonic()-t,2)}
    if name.startswith('final_') and name not in ('final_replay',):
        r=json.loads(dest.read_text())
        if 'upload_test' in r:
            print(name,'upload',r['upload_test'],'points',{k:v['mean_points'] for k,v in r['results'].items()},'failed',r['failed'],flush=True)
            assert r['upload_test']['pass'] and not r['upload_test']['failed'],r['upload_test']
            assert not r['failed'],r['failed']
        else:print(name,'cases',r['cases'],'CPU',r['scaled_cpu_us'],flush=True)
    else:print('Finished',name,flush=True)
    (HERE/'results/manifest.json').write_text(json.dumps(manifest,indent=2))
assert all(hashlib.sha256((HERE/n).read_bytes()).hexdigest()==v for n,v in manifest['files'].items())
print('Verification complete; payload hashes unchanged.',flush=True)
