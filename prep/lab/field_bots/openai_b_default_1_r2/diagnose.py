import json,gzip,collections as C,os,eval7
HERE=os.path.dirname(__file__); H=[json.loads(l) for l in gzip.open(os.path.join(HERE,'../openai_b_default_1/round1/hand_history.jsonl.gz'),'rt')]
D=json.load(open(os.path.join(HERE,'hero_decisions.json'))); ds={(d['table'],d['hand'],d['i']):d for d in D}
g=C.defaultdict(lambda:[0,0,0,0,0]);pool=C.defaultdict(lambda:[0,0]);top=[]
for h in H:
 street=0;bet=C.Counter();mx=0;nr=0;vp=set();board=[];post=C.Counter();aggs=C.Counter();lastagg=None;start=h['stacks'];hero=h['seat'];bb=h['blinds'][1];shows={s:cs for k,s,amt,cs in h['events'] if k=='show'};total=C.Counter();fold=set()
 for i,(k,s,amt,cs) in enumerate(h['events']):
  if k=='board':board+=cs;street=len(board)-2;bet=C.Counter();mx=0;continue
  if s is None:continue
  if k in ('raise','call','fold','check'):
   if street==0 and nr>=2 and mx>bb and s in vp:
    pool['fold3b'][0]+=1;pool['fold3b'][1]+=k=='fold'
    pool['fold3b_'+h['names'][str(s)]][0]+=1;pool['fold3b_'+h['names'][str(s)]][1]+=k=='fold'
   if k=='raise' and street:aggs[s]+=1
   if k=='raise':
    lastagg=s
    if street==0:nr+=1
   if s==hero and h['hole']:
    d=ds[(h['table'],h['hand'],i)];cost=d['cost'];pot=d['pot']
    if k=='call' and street:
     vs=[(s2,cs2) for s2,cs2 in shows.items() if s2!=hero and s2 not in fold]
     if vs:
      cards=[eval7.Card(c) for c in h['hole']];bd=[eval7.Card(c) for c in board]
      if street==3:
       hr=eval7.evaluate(cards+bd);rs=[eval7.evaluate([eval7.Card(c) for c in v]+bd) for s2,v in vs];eq=1/(1+rs.count(hr)) if hr>=max(rs) else 0
      else:
       eq=eval7.py_hand_vs_range_monte_carlo(cards,[(tuple(eval7.Card(c) for c in vs[0][1]),1.)],bd,3000)
      cat=eval7.handtype(eval7.evaluate(cards+bd));frac=cost/max(1,pot);ev=eq*(pot+cost)-cost
      terminal=street==3 or cost>=start[str(hero)]-total[hero]
      keys=['call_'+str(street),'call_'+str(street)+'_'+cat,'barrels_'+str(aggs[lastagg]),'terminal_'+str(terminal)]
      for key in keys:
       g[key][0]+=1;g[key][1]+=eq;g[key][2]+=cost/max(1,pot+cost);g[key][3]+=ev/bb;g[key][4]+=cost/bb
      top.append((ev/bb,h['table'],h['hand'],h['hole'],board[:],cat,vs,round(eq,3),round(cost/(pot+cost),3),aggs[lastagg],k))
   if k in ('raise','call') and street==0:vp.add(s)
   if k=='fold':fold.add(s)
  add=max(0,amt-bet[s]) if k=='raise' else amt if k in ('call','blind','ante') else 0
  if k in ('raise','call','blind'):bet[s]+=add;mx=max(mx,bet[s])
  total[s]+=add
for k,v in g.items():print(k,'n',v[0],'trueEQ',round(v[1]/v[0],3),'odds',round(v[2]/v[0],3),'EVbb',round(v[3],1),'costbb',round(v[4],1))
print('FOLD3BET',dict(pool))
for t in sorted(top)[:35]:print(t)
