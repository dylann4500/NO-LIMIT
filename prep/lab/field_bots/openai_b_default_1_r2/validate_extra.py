"""Invoke only the kit's public play.py; never import simulator modules."""
import os,sys,subprocess,json,hashlib
HERE=os.path.dirname(os.path.abspath(__file__));ROOT=os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PY=sys.executable;PLAY=os.path.join(ROOT,'lab','field_kit','play.py')
def play(tables,seed,seats=None):
 cmd=[PY,PLAY,HERE,'--tables',str(tables),'--seed',str(seed)]
 if seats:cmd+=['--seats',seats]
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
 r=json.loads(subprocess.check_output(cmd,cwd=ROOT,env=env,text=True))
 assert r['upload_test']['pass'] and not r['upload_test']['failed'],r
 assert not r['failed'],r
 return r
for tag,tables,seed,seats in [('7_raisers',200,307,'self,'+','.join(['min_raiser']*7)),('7_passive',100,401,'self,'+','.join(['check_or_fold']*7))]:
 if '--uploads-only' in sys.argv:continue
 r=play(tables,seed,seats)
 with open(os.path.join(HERE,'results_final_'+tag+'.json'),'w') as f:json.dump(r,f,indent=1)
 print(tag,r['results']['self'],flush=True)
uploads=[dict(seed=seed,**play(1,seed,'self,check_or_fold')['upload_test']) for seed in range(701,733)]
with open(os.path.join(HERE,'results_final_uploads.json'),'w') as f:json.dump(dict(agent_sha256=hashlib.sha256(open(os.path.join(HERE,'agent.py'),'rb').read()).hexdigest(),tests=uploads),f,indent=1)
print('upload_passes',sum(r['pass'] for r in uploads),'decisions',sum(r['decisions'] for r in uploads),flush=True)
