"""Second-stage search, with fresh seeds and larger table samples."""
import json,os,subprocess,sys,time
from pathlib import Path
from search import MIXES,PLAY,ROOT
CANDIDATES={
 "baseline_v2":{},
 "small":{"dry_size":.25,"wet_size":.5},
 "small_risk":{"dry_size":.25,"wet_size":.5,"risk":.14},
 "small_risk_value":{"dry_size":.25,"wet_size":.5,"risk":.14,"value":.64},
 "small_risk_cautious":{"dry_size":.25,"wet_size":.5,"risk":.14,"cbet":.38,"bluff":.12},
 "balanced":{"dry_size":.30,"wet_size":.55,"risk":.12,"value":.62,"cbet":.50,"bluff":.20},
 "precision":{"dry_size":.30,"wet_size":.55,"risk":.12,"value":.62,"cbet":.50,"bluff":.20,"samples":224,"iterations":512},
}
if __name__=="__main__":
 for name,params in CANDIDATES.items():
  for mix,tables,seed in [("default",400,1907),("stress",200,2917),("dense",100,3919)]:
   t=time.monotonic()
   result=subprocess.run([sys.executable,str(PLAY),str(ROOT),"--tables",str(tables),"--seed",str(seed),"--seats",MIXES[mix]],env=dict(os.environ,POKERBOT_PARAMS=json.dumps(params)),capture_output=True,text=True,check=True)
   report=json.loads(result.stdout)
   row={"name":name,"params":params,"mix":mix,"seconds":round(time.monotonic()-t,1),"seed":seed,"report":report}
   with (ROOT/"search_round2_results.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
   print(name,mix,report["results"]["self"]["mean_points"],report["results"]["self"]["se"],report["failed"],round(time.monotonic()-t,1),flush=True)
