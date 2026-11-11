"""Analyze supplied public histories; imports no simulator code."""
import collections as C, gzip,json,sys
from pathlib import Path
import eval7
ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent/'openai_a_iterate_3/round1/hand_history.jsonl.gz'
stats=C.defaultdict(lambda:C.Counter()); opp=C.defaultdict(lambda:C.Counter()); losses=[]; tables=C.Counter(); large_calls=[]
for line in gzip.open(SRC,'rt'):
 h=json.loads(line); hero=h['seat']; names=h['names']; bb=h['blinds'][1]; tables[h['table']]+=1
 start={int(k):v for k,v in h['stacks'].items()}; end={s:a for k,s,a,c in h['events'] if k=='stack'}
 if hero not in start or start[hero]<=0: continue
 net=end.get(hero,start[hero])-start[hero]; board=[]; bets=C.Counter(); contrib=C.Counter(); phase=0; acts=[]; raises=0; folded=set(); shown={}; pot=0; last_hero=None; hero_raises=0; saw=False
 pf=C.defaultdict(set); post=[]; records=[]
 for kind,s,a,c in h['events']:
  if kind=='board': phase+=1; board+=c; bets.clear(); continue
  if kind=='show': shown[s]=c
  if kind in ('blind','ante','call','raise'):
   delta=max(0,a-bets[s]) if kind=='raise' else a
  else: delta=0
  if kind in ('raise','call','fold','check'):
   if s==hero:
    label=('pre','flop','turn','river')[phase]
    cat=eval7.evaluate([eval7.Card(x) for x in h['hole']+board])>>24 if board else -1
    rec=dict(street=label,kind=kind,cost=delta,board=board[:],cat=cat,pot=pot,raises=raises,remaining=len(start)-len(folded),to_call=max(bets.values(),default=0)-bets[s])
    records.append(rec)
    stats['actions '+label][kind]+=1
    acts.append((label,kind,a,cat)); last_hero=rec
    if phase==0 and kind=='raise': hero_raises+=1
    if phase: saw=True
   name=names[str(s)]
   if phase==0:
    pf[s].add(kind)
    if kind=='raise': raises+=1
   else:
    opp[name]['post_'+kind]+=1
    if kind=='raise':opp[name]['post_raise_'+str(phase)]+=1
   if kind=='fold':folded.add(s)
  if delta:
   pot+=delta;contrib[s]+=delta
   if kind!='ante':bets[s]+=delta
 for s in start:
  o=opp[names[str(s)]];o['hands']+=1;o['vpip']+=bool(pf[s]&{'raise','call'});o['pfr']+=('raise' in pf[s])
 group='no voluntary preflop'
 pacts=[r for r in records if r['street']=='pre']
 if any(x['kind']=='call' for x in pacts):group='preflop call'
 if hero_raises:group='preflop raise'
 if not saw and group!='no voluntary preflop':group+=' no flop decision'
 for k in ('all',group,'players '+str(len(start))):stats[k].update(hands=1,net=net,invested=contrib[hero],showdown=hero in shown)
 if last_hero:
  k=last_hero['street']+' last '+last_hero['kind'];stats[k].update(hands=1,net=net,invested=contrib[hero])
  if last_hero['kind']=='call' and hero in shown:
   k+=' category '+str(last_hero['cat']);stats[k].update(hands=1,net=net,invested=contrib[hero])
 if net< -400:
  losses.append(dict(net=net,table=h['table'],hand=h['hand'],bb=bb,players=len(start),hole=h['hole'],acts=acts,shown=shown,events=h['events']))
 if hero in shown:
  hv=eval7.evaluate([eval7.Card(x) for x in h['hole']+board]);vs=[eval7.evaluate([eval7.Card(x) for x in c+board]) for s,c in shown.items() if s!=hero]
  if vs:
   for r in records:
    if r['kind']=='call' and r['cost']>0:
     k='showdown calls '+r['street'];stats[k].update(n=1,win=hv>max(vs),tie=hv==max(vs),cost=r['cost'],net=net)
 out=None
report={'groups':dict(stats),'opponents':dict(opp),'tables':len(tables),'hands':sum(tables.values()),'max_hands':max(tables.values()),'largest_losses':sorted(losses,key=lambda x:x['net'])[:40]}
(ROOT/'results/history_analysis.json').write_text(json.dumps(report,indent=2))
print('TABLES',len(tables),'HANDS',sum(tables.values()),'MAX',max(tables.values()))
for k,v in stats.items():print(k,dict(v))
print('OPPONENTS')
for k,v in opp.items():print(k,dict(v))
print('BIGGEST LOSSES')
for h in sorted(losses,key=lambda x:x['net'])[:20]:print({k:v for k,v in h.items() if k!='events'})
