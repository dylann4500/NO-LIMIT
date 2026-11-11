"""Analyze public histories only; does not read/import simulator internals."""
import collections,gzip,json,os,sys
import eval7
ROOT=os.path.dirname(__file__)
HISTORY=os.path.join(ROOT,'../openai_b_gto_3/round1/hand_history.jsonl.gz')
C=collections.Counter; agg=collections.defaultdict(lambda:[0,0.,0.]); field=collections.defaultdict(C); large=[]; decisions=[]
for ln in gzip.open(HISTORY,'rt'):
 h=json.loads(ln); hero=h['seat']; start={int(k):v for k,v in h['stacks'].items()}
 if hero not in start or start[hero]<=0:continue
 bets=C();spent=C();board=[];pot=0;street=0;raises=C(); active=set(start); first={};heroacts=[]; revealed={};pfvp=set();pfraise=set();prevr={};latest=None
 for i,(kind,seat,amount,cards) in enumerate(h['events']):
  if kind=='board':
   board+=cards;street+=1;bets=C();continue
  if kind=='show':revealed[seat]=cards
  if kind not in ('blind','ante','raise','call','check','fold'):continue
  if kind in ('raise','call','check','fold'):
   cost=min(start.get(seat,0)-spent[seat],max(bets.values(),default=0)-bets[seat]); before=pot
   cat=None;made=None
   if seat==hero:
    if board:cat=eval7.evaluate([eval7.Card(x) for x in h['hole']+board])>>24
    d={'table':h['table'],'hand':h['hand'],'index':i,'street':street,'kind':kind,'amount':amount,'cost':cost,'pot':pot,'active':len(active),'stack':start[hero]-spent[hero], 'bets':dict(bets),'prior_raises':raises[street], 'hole':h['hole'],'board':list(board),'cat':cat,'bb':h['blinds'][1]}
    heroacts.append(d);decisions.append(d)
   name=h['names'][str(seat)]; f=field[name];f['actions']+=1
   if street==0:
    if seat not in first:first[seat]=kind
    if kind in ('raise','call'):pfvp.add(seat)
    if kind=='raise':pfraise.add(seat)
   else:
    f['post_actions']+=1
    if kind=='raise':
     f['post_raise']+=1
     f['post_bet_pot_sum']+=max(0,(amount or 0)-bets[seat])/max(1,pot)
    if cost>0:
     f['facing_bet']+=1;f['fold_to_bet']+=(kind=='fold')
   if kind=='raise':raises[street]+=1
   if kind=='fold':active.discard(seat)
  if kind in ('blind','ante','call','raise'):
   delta=amount-bets[seat] if kind=='raise' else amount
   spent[seat]+=delta;pot+=delta
   if kind!='ante':bets[seat]+=delta
  if kind=='raise':latest=(seat,street)
 end={e[1]:e[2] for e in h['events'] if e[0]=='stack'}; net=end.get(hero,0)-start[hero];bb=h['blinds'][1]
 for seat in start:
  f=field[h['names'][str(seat)]];f['hands']+=1;f['vpip']+=seat in pfvp;f['pfr']+=seat in pfraise
 tags=['all',f'players_{len(start)}',f'depth_{"short" if start[hero]/bb<=12 else "medium" if start[hero]/bb<=30 else "deep"}']
 for t in tags:
  a=agg[t];a[0]+=1;a[1]+=net;a[2]+=net/bb
 pf=[a for a in heroacts if a['street']==0];post=[a for a in heroacts if a['street']>0]
 if pf:
  first=pf[0]
  if first['kind']=='fold':tag='first_fold'
  elif first['kind']=='raise':tag='first_raise_facing_raise' if first['prior_raises'] else 'first_open'
  elif first['kind']=='call':tag='first_call_raise' if first['prior_raises'] else 'first_limp'
  else:tag='first_check'
  a=agg[tag];a[0]+=1;a[1]+=net;a[2]+=net/bb
 if post:
  last=post[-1];tag=f"post_last_{last['street']}_{last['kind']}_cat{last['cat']}";a=agg[tag];a[0]+=1;a[1]+=net;a[2]+=net/bb
 for d in heroacts:
  d['net']=net;d['netbb']=net/bb;d['revealed']=revealed;d['endboard']=board
 if net<0:large.append((net,net/bb,h,heroacts))
print('GROUPS n chips bb')
for k,v in sorted(agg.items()):print(k,[round(x,2) for x in v])
print('FIELD')
for name,f in sorted(field.items()):
 print(name,'hands',f['hands'],'vpip',round(f['vpip']/f['hands'],3),'pfr',round(f['pfr']/f['hands'],3),'agg',round(f['post_raise']/max(1,f['post_actions']),3),'fold_bet',round(f['fold_to_bet']/max(1,f['facing_bet']),3))
print('LARGEST LOSSES')
for net,nb,h,acts in sorted(large,key=lambda x:x[0])[:18]:
 print(h['table'],h['hand'],'net',net,round(nb,1),'hole',h['hole'],'players',len(h['stacks']))
 print('actions',[(a['street'],a['kind'],a['amount'],a['cost'],a['pot'],a['cat']) for a in acts])
 print('events',[e for e in h['events'] if e[0]!='stack'])
with open(os.path.join(ROOT,'results/round1_decisions.json'),'w') as f:json.dump(decisions,f)
with open(os.path.join(ROOT,'results/round1_analysis.json'),'w') as f:json.dump({'groups':dict(agg),'field':dict(field)},f,indent=2)
