"""Run the public starter-kit tester only; never imports simulator internals."""
import argparse,json,os,subprocess,sys,time,hashlib
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PLAY=os.path.join(ROOT,'lab','field_kit','play.py')
parser=argparse.ArgumentParser()
parser.add_argument('--mixed-tables',type=int,default=600)
parser.add_argument('--upload-seeds',type=int,default=32)
parser.add_argument('--uploads-only',action='store_true')
args=parser.parse_args()
plans=[
 ('release_mixed',args.mixed_tables,101,None),
 ('release_7_self',150,211,'self,self,self,self,self,self,self,min_raiser'),
 ('release_7_raisers',150,307,'self,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser'),
 ('release_7_passive',100,401,'self,check_or_fold,check_or_fold,check_or_fold,check_or_fold,check_or_fold,check_or_fold,check_or_fold'),
]
if args.uploads_only:plans=[]
for name,tables,seed,seats in plans:
 cmd=[sys.executable,PLAY,HERE,'--tables',str(tables),'--seed',str(seed)]
 if seats:cmd+=['--seats',seats]
 print('Running',name,tables,'tables',flush=True)
 p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=True)
 report=json.loads(p.stdout)
 report['seed']=seed
 report['agent_sha256']=hashlib.sha256(open(os.path.join(HERE,'agent.py'),'rb').read()).hexdigest()
 assert report['upload_test']['pass'],report['upload_test']
 assert not {k:v for k,v in report['failed'].items() if k!='timeout'},report['failed']
 with open(os.path.join(HERE,'results_'+name+'.json'),'w') as f:json.dump(report,f,indent=1)
 print(json.dumps({'run':name,'self':report['results']['self'],'upload':report['upload_test'],'failed':report['failed'],'latency_us':report['latency_us']}),flush=True)
uploads=[]
for seed in range(701,701+args.upload_seeds):
 cmd=[sys.executable,PLAY,HERE,'--tables','1','--seed',str(seed)]
 p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=True)
 report=json.loads(p.stdout)['upload_test'];report['seed']=seed;uploads.append(report)
summary={'runs':len(uploads),'passed':sum(r['pass'] for r in uploads),'decisions':sum(r['decisions'] for r in uploads),'reports':uploads}
with open(os.path.join(HERE,'results_release_uploads.json'),'w') as f:json.dump(summary,f,indent=1)
print('Upload seeds:',summary['passed'],'/',summary['runs'],'decisions',summary['decisions'],flush=True)
assert summary['passed']==summary['runs'],summary
