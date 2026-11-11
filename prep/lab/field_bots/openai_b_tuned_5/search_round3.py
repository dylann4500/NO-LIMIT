"""Final parameter selection with independent seeds."""
import json,os,subprocess,sys,time
from search import MIXES,PLAY,ROOT
BAL={"dry_size":.30,"wet_size":.55,"risk":.12,"value":.62,"cbet":.50,"bluff":.20}
CANDIDATES={
 "baseline_v3":{},
 "balanced_v3":BAL,
 "small_value_v3":{"dry_size":.25,"wet_size":.5,"risk":.14,"value":.64},
 "precision_v3":dict(BAL,samples=224,iterations=512),
 "tight_rank_v3":dict(BAL,range_weight=.50),
 "old_rank_v3":dict(BAL,range_weight=0.0),
 "cautious_v3":dict(BAL,threebet=.64,value=.64,cbet=.45,bluff=.15),
}
if __name__=="__main__":
 for name,params in CANDIDATES.items():
  for mix,tables,seed in [("default",600,4211),("stress",300,5231),("dense",100,6247)]:
   t=time.monotonic()
   result=subprocess.run([sys.executable,str(PLAY),str(ROOT),"--tables",str(tables),"--seed",str(seed),"--seats",MIXES[mix]],env=dict(os.environ,POKERBOT_PARAMS=json.dumps(params)),capture_output=True,text=True,check=True)
   report=json.loads(result.stdout)
   row={"name":name,"params":params,"mix":mix,"seconds":round(time.monotonic()-t,1),"seed":seed,"report":report}
   with (ROOT/"search_round3_results.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
   print(name,mix,report["results"]["self"]["mean_points"],report["results"]["self"]["se"],report["failed"],round(time.monotonic()-t,1),flush=True)
