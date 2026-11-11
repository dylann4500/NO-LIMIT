"""Release checks through play.py only, including a CPU slowdown wrapper."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from search import MIXES,PLAY,ROOT
cases=[
 ("final_default",ROOT,1000,31111,MIXES["default"]),
 ("final_stress",ROOT,1000,41113,MIXES["stress"]),
 ("final_dense",ROOT,300,51131,MIXES["dense"]),
 ("final_passive",ROOT,200,61141,"self,self,check_or_fold,check_or_fold,check_or_fold,check_or_fold,check_or_fold,check_or_fold"),
 ("final_selfplay",ROOT,100,71143,",".join(["self"]*8)),
 ("final_slow_2_5",Path("/tmp/openai_b_tuned_5_slow"),300,81157,MIXES["default"]),
]
if __name__=="__main__":
 slow=cases[-1][1]
 slow.mkdir(parents=True,exist_ok=True)
 template='''import importlib.util,time
spec=importlib.util.spec_from_file_location("real_bot",TARGET)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Agent(m.Agent):
 def act(self,state,memory):
  t=time.process_time_ns()
  result=super().act(state,memory)
  target=t+int((time.process_time_ns()-t)*2.5)
  while time.process_time_ns()<target: pass
  return result
'''
 (slow/"agent.py").write_text(template.replace("TARGET",repr(str(ROOT/"agent.py"))))
 manifest={"sha256":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ["agent.py","params.json","preflop.json"]}}
 (ROOT/"release_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
 env=dict(os.environ);env.pop("POKERBOT_PARAMS",None)
 for name,folder,tables,seed,mix in cases:
  t=time.monotonic()
  run=subprocess.run([sys.executable,str(PLAY),str(folder),"--tables",str(tables),"--seed",str(seed),"--seats",mix],capture_output=True,text=True,env=env,check=True,timeout=420)
  report=json.loads(run.stdout)
  (ROOT/(name+".json")).write_text(json.dumps(report,indent=2)+"\n")
  print(name,report["results"]["self"]["mean_points"],report["failed"],report["latency_us"],"seconds",round(time.monotonic()-t,1),flush=True)
