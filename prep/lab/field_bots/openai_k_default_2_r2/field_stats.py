import json,gzip,collections,sys
from pathlib import Path
import analyze_round as ar
p=ar.policy;teams=collections.defaultdict(collections.Counter);reveals=collections.defaultdict(collections.Counter)
for l in gzip.open(ar.ROOT.parent/'openai_k_default_2'/'round1'/'hand_history.jsonl.gz','rt'):
 h=json.loads(l);board=[];pot=0;bets={};mx=0;street=0;ag=None;nr=0;acts={};preag=None;shown={e[1]:e[3] for e in h['events'] if e[0]=='show'};finalbet={}
 for k,s,a,c in h['events']:
  if k=='board':
   board+=c;street=len(board)-2;bets={};mx=0;ag=None;nr=0;acts={}
  if k in ('blind','ante','call','raise'):
   inc=a-bets.get(s,0) if k=='raise' else a
  if k in ('fold','call','raise','check'):
   name=h['names'][str(s)];facing=mx>bets.get(s,0)
   if street:
    teams[name]['post_actions']+=1
    if k=='raise':
     teams[name]['post_bets']+=1
     key=f'{street}_{"raise" if mx else "bet"}'
     if s in shown:
      cards=shown[s];ids=[p.CARD_INDEX[c] for c in board];br,suits,bset,conn,wet=p.texture(ids);bv=p.eval7.evaluate([p.CARDS[i] for i in ids]);bs=sorted(bset);mask=sum(1<<r for r in bset);fs=next((i for i,x in enumerate(suits) if x>=3),-1);tf=[r for r in range(12,-1,-1) if r*4+fs not in ids][:3] if fs>=0 else [-1]*3;ms=max((i+4 for i in range(9) if (mask&(31<<i)).bit_count()>=3),default=3);ctx=([br.count(r) for r in range(13)],bs[-1],bs[-2] if len(bs)>1 else bs[-1],bv>>24,suits,mask,bv,tf,ms);ci=[p.CARD_INDEX[c] for c in cards];q=p.made_quality(*ci,p.eval7.evaluate([p.CARDS[i] for i in ci+ids]),ctx)
      reveals[key]['shown']+=1;reveals[key]['weak' if q<.45 else 'medium' if q<.73 else 'strong']+=1
      if q<.45:teams[name]['shown_weak_bets']+=1
      teams[name]['shown_bets']+=1
    if facing:
     typ='self' if ag==h['seat'] else 'other';fraction=mx/max(1,pot-mx)
     key=f'{street}_{typ}_{"small" if fraction<.45 else "large"}'
     teams[key]['faced']+=1;teams[key][k]+=1
   elif k=='raise':preag=s
  if k in ('blind','ante','call','raise'):
   pot+=inc
   if k!='ante':bets[s]=bets.get(s,0)+inc
   mx=max(mx,bets.get(s,0))
   if k=='raise':ag=s;nr+=1
print(json.dumps({'teams':dict(teams),'revealed_bets':dict(reveals)},indent=2))
