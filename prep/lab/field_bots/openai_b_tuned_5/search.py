"""Parameter search using only the public play.py command."""
import json, os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PLAY=ROOT.parents[1]/"field_kit"/"play.py"
CANDIDATES={
 "baseline":{},
 "open_130":{"open":1.3},
 "open_160":{"open":1.6},
 "open_080":{"open":.8},
 "risk_140":{"risk":.14},
 "risk_000":{"risk":0},
 "value_640":{"value":.64},
 "value_540":{"value":.54},
 "bluff_high":{"cbet":.85,"bluff":.42},
 "bluff_low":{"cbet":.38,"bluff":.12},
 "threebet_580":{"threebet":.58},
 "threebet_660":{"threebet":.66},
 "call_loose":{"call_edge":.005},
 "call_tight":{"call_edge":.055},
 "size_small":{"dry_size":.25,"wet_size":.50},
 "size_large":{"dry_size":.50,"wet_size":.80},
 "range_tight":{"range_filter":.75},
 "range_wide":{"range_filter":1.3},
}
MIXES={
 "default":"self,self,self,self,check_or_fold,check_or_fold,min_raiser,min_raiser",
 "stress":"self,check_or_fold,check_or_fold,check_or_fold,min_raiser,min_raiser,min_raiser,min_raiser",
 "dense":"self,self,self,self,self,self,self,min_raiser",
}
if __name__=="__main__":
 out=ROOT/"search_results.jsonl"
 for name,params in CANDIDATES.items():
  for mix in ["default","stress"]:
   tables=80 if mix=="default" else 40
   t=time.monotonic()
   env=dict(os.environ,POKERBOT_PARAMS=json.dumps(params))
   cmd=[sys.executable,str(PLAY),str(ROOT),"--tables",str(tables),"--seed","731","--seats",MIXES[mix]]
   result=subprocess.run(cmd,env=env,capture_output=True,text=True,check=True)
   report=json.loads(result.stdout)
   row={"name":name,"params":params,"mix":mix,"seconds":round(time.monotonic()-t,1),"report":report}
   with out.open("a") as f: f.write(json.dumps(row)+"\n")
   print(name,mix,report["results"]["self"]["mean_points"],report["results"]["self"]["se"],report["failed"],round(time.monotonic()-t,1),flush=True)
