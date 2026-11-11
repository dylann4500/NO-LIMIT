"""Reproduce final validation using only the public SDK and supplied play.py.

Run with the tournament Python. Simulator implementation files are never read
or imported here. The optional slower-machine wrapper exists only in a temp dir.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time

BOT=Path(__file__).resolve().parent
ROOT=BOT.parents[2]
PLAY=ROOT/'lab/field_kit/play.py'
OUT=BOT/'results'
PYTHON=sys.executable

def execute(args,name):
    path=OUT/name
    with path.open('w') as f:
        result=subprocess.run([PYTHON,*map(str,args)],cwd=ROOT,stdout=f,stderr=subprocess.PIPE,text=True)
    if result.returncode:
        raise RuntimeError(f'{name}: {result.stderr}')
    print('Finished',name,flush=True)
    if name.endswith('.json'):
        return json.loads(path.read_text())

def match(bot,tables,seed,name,seats=None):
    args=[PLAY,bot,'--tables',tables,'--seed',seed]
    if seats: args+=['--seats',seats]
    return execute(args,name)

SLOW_WRAPPER='''import time
from types import SimpleNamespace
import verification_core as core
_origin=time.perf_counter_ns()
core.time=SimpleNamespace(perf_counter_ns=lambda:_origin+int((time.perf_counter_ns()-_origin)*2.5))
class Agent(core.Agent):
    def act(self,state,memory):
        t=time.process_time_ns()
        answer=super().act(state,memory)
        duration=time.process_time_ns()-t
        target=t+int(duration*2.5)
        while time.process_time_ns()<target:
            pass
        return answer
'''

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--tables',type=int,default=1000)
    ap.add_argument('--slow-tables',type=int,default=200)
    ap.add_argument('--upload-seeds',type=int,default=30)
    a=ap.parse_args()
    OUT.mkdir(exist_ok=True)
    digest=hashlib.sha256((BOT/'agent.py').read_bytes()).hexdigest()
    execute([BOT/'test_agent.py'],'sdk_normal.txt')
    execute([BOT/'test_agent.py','--slow-clock'],'sdk_slow_clock.txt')
    reports={}
    reports['default']=match(BOT,a.tables,20261106,'final_default.json')
    with tempfile.TemporaryDirectory(prefix='poker_2_5x_') as tmp:
        slow=Path(tmp)
        shutil.copyfile(BOT/'agent.py',slow/'verification_core.py')
        shutil.copyfile(BOT/'preflop.json',slow/'preflop.json')
        (slow/'agent.py').write_text(SLOW_WRAPPER)
        reports['slow']=match(slow,a.slow_tables,20261107,'final_slow_2_5x.json')
    reports['raisers']=match(BOT,200,20261108,'final_raisers.json','self,'+','.join(['min_raiser']*7))
    reports['folders']=match(BOT,100,20261109,'final_folders.json','self,'+','.join(['check_or_fold']*7))
    sweep=[]
    for i in range(a.upload_seeds):
        args=[PYTHON,str(PLAY),str(BOT),'--tables','1','--seed',str(9100+i),'--seats','self,check_or_fold']
        r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,check=True)
        sweep.append({'seed':9100+i,**json.loads(r.stdout)['upload_test']})
    (OUT/'upload_sweep.json').write_text(json.dumps(sweep,indent=2)+'\n')
    manifest={'agent_sha256':digest,'preflop_sha256':hashlib.sha256((BOT/'preflop.json').read_bytes()).hexdigest(),
              'python':sys.version,'completed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
              'upload_seeds':a.upload_seeds,'upload_passes':sum(x['pass'] for x in sweep)}
    assert digest==hashlib.sha256((BOT/'agent.py').read_bytes()).hexdigest(),'Agent changed during validation'
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2),flush=True)
    for name,r in reports.items():
        print(name,'score',r['results']['self']['mean_points'],'failed',r['failed'],'upload',r['upload_test']['pass'],flush=True)
    if not all(x['pass'] for x in sweep):
        raise RuntimeError('One or more upload seeds failed; see upload_sweep.json')
    if not all(r['upload_test']['pass'] for r in reports.values()):
        raise RuntimeError('An upload test failed; see reports')
    if any(r['failed'] for r in reports.values()):
        raise RuntimeError('A match recorded failed decisions; see raw reports')
if __name__=='__main__':main()
