"""Reproduce round-2 validation by executing play.py, without simulator imports."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile,time
BOT=Path(__file__).resolve().parent;ROOT=BOT.parents[2];OUT=BOT/'results';PLAY=ROOT/'lab/field_kit/play.py'
PY=sys.executable;OLD=BOT.parent/'openai_a_iterate_3'

def match(name,bot=BOT,tables=200,seed=20261119,seats=None,opponent=None):
 args=[PY,str(PLAY),str(bot),'--tables',str(tables),'--seed',str(seed)]
 if seats:args+=['--seats',seats]
 if opponent:args+=['--opponent',opponent]
 t=time.monotonic();r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,check=True)
 data=json.loads(r.stdout);(OUT/name).write_text(r.stdout)
 print(name,'seconds',round(time.monotonic()-t,1),'score',data['results']['self']['mean_points'],'failed',data['failed'],'upload',data['upload_test']['pass'],flush=True)
 return data
SLOW='''import time
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
        while time.process_time_ns()<target: pass
        return answer
'''
def main():
 hashes={x:hashlib.sha256((BOT/x).read_bytes()).hexdigest() for x in ['agent.py','preflop.json']}
 reports=[]
 for script,args,out in [('test_agent.py',[],'sdk_normal.txt'),('test_agent.py',['--slow-clock'],'sdk_slow_clock.txt'),('test_adaptation.py',[],'adaptation.txt')]:
  r=subprocess.run([PY,str(BOT/script),*args],cwd=ROOT,capture_output=True,text=True,check=True);(OUT/out).write_text(r.stdout);print(out,r.stdout.strip(),flush=True)
 reports.append(match('final_vs_original.json',tables=1200,seed=20261125,seats='self,self,self,self,baseline,baseline,baseline,baseline',opponent='baseline='+str(OLD)))
 reports.append(match('final_heads_up.json',tables=500,seed=20261120,seats='self,baseline',opponent='baseline='+str(OLD)))
 reports.append(match('final_default.json',tables=500,seed=20261121))
 with tempfile.TemporaryDirectory(prefix='poker_r2_slow_') as d:
  p=Path(d);shutil.copyfile(BOT/'agent.py',p/'verification_core.py');shutil.copyfile(BOT/'preflop.json',p/'preflop.json');(p/'agent.py').write_text(SLOW)
  reports.append(match('final_slow_2_5x.json',bot=p,tables=200,seed=20261122))
 reports.append(match('final_raisers.json',tables=100,seed=20261123,seats='self,'+','.join(['min_raiser']*7)))
 reports.append(match('final_folders.json',tables=50,seed=20261124,seats='self,'+','.join(['check_or_fold']*7)))
 sweep=[]
 for seed in range(9200,9230):
  r=subprocess.run([PY,str(PLAY),str(BOT),'--tables','1','--seed',str(seed),'--seats','self,check_or_fold'],cwd=ROOT,capture_output=True,text=True,check=True)
  sweep.append(dict(seed=seed,**json.loads(r.stdout)['upload_test']))
 (OUT/'upload_sweep.json').write_text(json.dumps(sweep,indent=2)+'\n')
 assert hashes=={x:hashlib.sha256((BOT/x).read_bytes()).hexdigest() for x in hashes}
 assert all(r['upload_test']['pass'] and not r['failed'] for r in reports)
 assert all(r['pass'] and not r['failed'] for r in sweep)
 manifest=dict(hashes=hashes,upload_passes=sum(x['pass'] for x in sweep),upload_decisions=sum(x['decisions'] for x in sweep),upload_failures=sum(sum(x['failed'].values()) for x in sweep),completed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest),flush=True)
if __name__=='__main__':main()
