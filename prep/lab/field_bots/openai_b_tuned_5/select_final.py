"""Confirm the final settings after the three-bet range refinement."""
import json,os,subprocess,sys,time
from search import MIXES,PLAY,ROOT
BAL={"dry_size":.30,"wet_size":.55,"risk":.12,"value":.62,"cbet":.50,"bluff":.20,"samples":224,"iterations":512}
CANDIDATES={
 "precision_final":BAL,
 "cautious_final":dict(BAL,dry_size=.25,wet_size=.50,risk=.14,threebet=.64,value=.64,cbet=.45,bluff=.15),
 "small_final":dict(BAL,dry_size=.25,wet_size=.50,risk=.14,value=.64,cbet=.62,bluff=.28),
 "defensive_final":dict(BAL,call_edge=.04),
}
if __name__=="__main__":
 for name,params in CANDIDATES.items():
  for mix,tables,seed in [("default",1000,8291),("stress",500,9391)]:
   t=time.monotonic()
   result=subprocess.run([sys.executable,str(PLAY),str(ROOT),"--tables",str(tables),"--seed",str(seed),"--seats",MIXES[mix]],env=dict(os.environ,POKERBOT_PARAMS=json.dumps(params)),capture_output=True,text=True,check=True)
   report=json.loads(result.stdout)
   row={"name":name,"params":params,"mix":mix,"seconds":round(time.monotonic()-t,1),"seed":seed,"report":report}
   with (ROOT/"selection_results.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
   print(name,mix,report["results"]["self"]["mean_points"],report["results"]["self"]["se"],report["failed"],round(time.monotonic()-t,1),flush=True)
