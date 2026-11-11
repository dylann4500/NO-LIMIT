"""Analyze only the supplied round histories; no simulator dependencies."""
import collections as C,gzip,json,os,sys
import eval7
HERE=os.path.dirname(__file__)
H=[json.loads(l) for l in gzip.open(os.path.join(HERE,'../openai_b_default_1/round1/hand_history.jsonl.gz'),'rt')]
agg=C.defaultdict(lambda:[0,0,0]); opp=C.defaultdict(C.Counter); losses=[]; calls=C.defaultdict(lambda:[0,0,0,0]); decisions=[]
for h in H:
 hero=h['seat']; hk=str(hero); live=len(h['stacks']); hole=h['hole']; bb=h['blinds'][1]
 bet=C.Counter();total=C.Counter();pot=0;street=0;board=[];raises=0;mx=0;last=None;actions=[];shows={};wins=C.Counter();vp=set();pr=set();faced=set();lastagg=None
 ends={s:st for k,s,st,cs in h['events'] if k=='stack'}
 net=ends.get(hero,0)-h['stacks'].get(hk,0)
 for idx,(k,s,amt,cs) in enumerate(h['events']):
  if k=='show':shows[s]=cs
  if k=='win':wins[s]+=amt
  if k=='board':board+=cs;street=len(board)-2;bet=C.Counter();mx=0;lastagg=None;continue
  if s is None:continue
  name=h['names'][str(s)]
  if k in ('call','fold','check','raise'):
   cost=max(0,mx-bet[s]);facing=cost>0
   opp[name]['actions'+str(street)]+=1
   if street==0:
    if s not in faced and mx>bb and facing:
     opp[name]['faced_pf']+=1;opp[name]['fold_pf']+=k=='fold';faced.add(s)
    if k in ('call','raise'):vp.add(s)
    if k=='raise':pr.add(s)
   else:
    opp[name]['post_'+k]+=1
    if facing:opp[name]['faced_post']+=1;opp[name]['fold_post']+=k=='fold'
    if k=='raise':opp[name]['bet_pot_sum']+=max(0,(amt-bet[s]-cost)/max(1,pot+cost));opp[name]['bets']+=1
   if s==hero:
    action=dict(table=h['table'],hand=h['hand'],i=idx,street=street,kind=k,cost=min(h['stacks'][hk]-total[s],cost),pot=pot,amount=amt,board=board[:],hole=hole,depth=h['stacks'][hk]/bb,live=live,raises=raises,lastagg=lastagg)
    actions.append(action)
    if k=='call' and street>0:last=action
   if k=='raise':lastagg=name
  add=max(0,amt-bet[s]) if k=='raise' else amt if k in ('call','blind','ante') else 0
  if k in ('raise','call','blind'):bet[s]+=add;mx=max(mx,bet[s])
  if k=='raise' and street==0:raises+=1
  total[s]+=add;pot+=add
 for s in h['stacks']:
  name=h['names'][s];opp[name]['hands']+=1;opp[name]['vp']+=int(s) in vp;opp[name]['pr']+=int(s) in pr
 if not hole:continue
 for group in ['all','players_'+str(live),'depth_'+('0-10' if h['stacks'][hk]/bb<10 else '10-25' if h['stacks'][hk]/bb<25 else '25+'), 'showdown' if hero in shows else 'no_showdown']:
  agg[group][0]+=1;agg[group][1]+=net;agg[group][2]+=net/bb
 pf=[a for a in actions if a['street']==0]
 group='pf_'+('_'.join(a['kind'] for a in pf))
 agg[group][0]+=1;agg[group][1]+=net;agg[group][2]+=net/bb
 if last:
  key=str(last['street'])+':'+('large' if last['cost']/max(1,last['pot'])>.5 else 'small')
  calls[key][0]+=1;calls[key][1]+=net/bb;calls[key][2]+=wins[hero]>0;calls[key][3]+=last['cost']/bb
 for a in actions:a['net_bb']=net/bb;decisions.append(a)
 losses.append(dict(net=net,net_bb=net/bb,h=h))
report={'hands_hero':sum(bool(h['hole']) for h in H),'tables':len(set(h['table'] for h in H)),'groups':dict(agg),'last_post_call':dict(calls),'opponents':{k:dict(v) for k,v in opp.items()},'largest_losses_bb':[v for v in sorted(losses,key=lambda v:v['net_bb'])[:30]]}
with open(os.path.join(HERE,'round_analysis.json'),'w') as f:json.dump(report,f,indent=1)
with open(os.path.join(HERE,'hero_decisions.json'),'w') as f:json.dump(decisions,f)
for k,v in agg.items():print(k, v[0],round(v[1]),round(v[2],1))
print('LAST CALLS',dict(calls))
for name,v in sorted(opp.items()):print(name,'hands',v['hands'],'vp',round(v['vp']/v['hands'],3),'pfr',round(v['pr']/v['hands'],3),'fold_pf',round(v['fold_pf']/max(1,v['faced_pf']),3),'fold_post',round(v['fold_post']/max(1,v['faced_post']),3),'bet_frac',round(v['bet_pot_sum']/max(1,v['bets']),2))
for v in sorted(losses,key=lambda v:v['net_bb'])[:15]:
 h=v['h'];print('LOSS',round(v['net_bb'],1),h['table'],h['hand'],h['hole'],h['blinds'],h['events'])
