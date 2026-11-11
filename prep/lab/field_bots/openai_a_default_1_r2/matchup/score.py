"""Score final public SDK observations with expected unresolved runouts."""
import json,random,statistics,sys,eval7
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lab/fake_sdk'))
sp=importlib.util.spec_from_file_location('scoring_bot',str(HERE.parent/'agent.py'));NEW=importlib.util.module_from_spec(sp);sp.loader.exec_module(NEW)
rng=random.Random(218);payouts=[50,30,20,0,0,0,0,0]
allvalues=[];unresolved=0;tables=json.load(open(str(HERE/'observations.json')))
for d in tables.values():
 if len(d['seats'])!=8:continue
 seats={s:[stack,bet,status] for s,stack,bet,status in d['seats']}
 con={s:0 for s in seats};bets={s:0 for s in seats}
 for k,s,a,c in d['history']:
  if k=='board':bets={s:0 for s in seats}
  elif k in ('blind','ante','call','raise'):
   add=a-bets[s] if k=='raise' else a;con[s]+=add
   if k!='ante':bets[s]+=add
 hero=d['seat'];kind,amt=d['action'];start={s:seats[s][0]+con[s] for s in seats}
 if kind in ('raise','call'):
  add=min(seats[hero][0],d['cost']) if kind=='call' else amt-seats[hero][1]
  seats[hero][0]-=add;con[hero]+=add
 if kind=='fold':seats[hero][2]='folded'
 live=[s for s in seats if seats[s][2]!='busted'];eligible=[s for s in live if seats[s][2]!='folded']
 holes={int(s):cs for s,cs in d['holes'].items()};known=set(d['board'])|{c for hh in holes.values() for c in hh};deck=[str(c) for c in eval7.Deck().cards if str(c) not in known]
 unknown=[s for s in eligible if s not in holes]
 iterations=1000 if len(eligible)>1 and (len(d['board'])<5 or unknown) else 1
 unresolved+=iterations>1;averages=[0.]*8
 for _ in range(iterations):
  sample=rng.sample(deck,5-len(d['board'])+2*len(unknown));board=d['board']+sample[:5-len(d['board'])];at=5-len(d['board']);hc=holes.copy()
  for s in unknown:hc[s]=sample[at:at+2];at+=2
  ranks={s:eval7.evaluate([eval7.Card(c) for c in hc[s]+board]) for s in eligible} if len(eligible)>1 else {eligible[0]:1}
  final={s:seats[s][0] for s in seats};last=0
  for amount in sorted(set(con.values())-{0}):
   pot=(amount-last)*sum(v>=amount for v in con.values());can=[s for s in eligible if con[s]>=amount]
   if not can:can=eligible
   top=max(ranks[s] for s in can);win=[s for s in can if ranks[s]==top]
   for s in win:final[s]+=pot/len(win)
   last=amount
  values=[0.]*8
  for i,s in enumerate(d['bust']):values[s]=payouts[7-i]
  positive=[s for s in live if final[s]>1e-7];zeros=sorted((s for s in live if final[s]<=1e-7),key=lambda s:-start[s])
  for i,s in enumerate(zeros):values[s]=payouts[len(positive)+i]
  for i,s in enumerate(positive):values[s]=NEW.icm_value([final[x] for x in positive],i,payouts)
  for s in range(8):averages[s]+=values[s]/iterations
 assert abs(sum(averages)-100)<.01,averages
 allvalues.append(averages)
new=[sum(v[::2])/4 for v in allvalues];old=[sum(v[1::2])/4 for v in allvalues];diff=[a-b for a,b in zip(new,old)]
res={'tables':len(new),'new_mean':statistics.mean(new),'old_mean':statistics.mean(old),'paired_difference':statistics.mean(diff),'difference_se':statistics.stdev(diff)/len(diff)**.5,'unresolved_final_runouts':unresolved,'method':'Official play.py, four original / four revised bots. Payouts inferred from final public SDK decision, averaging 1000 unknown final runouts; not simulator result labels.'}
print(json.dumps(res,indent=2));json.dump(res,open(str(HERE/'matchup_score.json'),'w'),indent=2)
