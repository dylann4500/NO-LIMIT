import json,gzip,os,collections as C,eval7
HERE=os.path.dirname(__file__)
changes=json.load(open(os.path.join(HERE,'replay_changes.json')))
cs={(d['table'],d['hand'],d['i']):d for d in changes}
g=C.defaultdict(lambda:[0,0,0]);examples=[]
for line in gzip.open(os.path.join(HERE,'../openai_b_default_1/round1/hand_history.jsonl.gz'),'rt'):
 h=json.loads(line);shows={s:cards for kind,s,amount,cards in h['events'] if kind=='show'};hero=h['seat'];stacks={int(s):v for s,v in h['stacks'].items()};bet=C.Counter();folds=set()
 for i,(k,s,amt,cs2) in enumerate(h['events']):
  d=cs.get((h['table'],h['hand'],i))
  if d and d['cost'] and d['board'] and d['actions'][0][0] in ('call','fold') and d['actions'][1][0] in ('call','fold'):
   vs=[(s2,cards) for s2,cards in shows.items() if s2!=hero and s2 not in folds]
   if vs and (len(d['board'])==5 or d['cost']>=stacks[hero]):
    hole=[eval7.Card(c) for c in d['cards']];bd=[eval7.Card(c) for c in d['board']]
    if len(bd)==5:
     hr=eval7.evaluate(hole+bd);ranks=[eval7.evaluate([eval7.Card(c) for c in cards]+bd) for s2,cards in vs];eq=1/(1+ranks.count(hr)) if hr>=max(ranks) else 0
    else:eq=eval7.py_hand_vs_range_monte_carlo(hole,[(tuple(eval7.Card(c) for c in vs[0][1]),1.)],bd,10000)
    ev=(eq*(d['pot']+d['cost'])-d['cost'])/h['blinds'][1]
    delta=ev if d['actions'][1][0]=='call' else -ev
    key=str(len(bd))+':'+d['actions'][0][0]+'->'+d['actions'][1][0]
    g[key][0]+=1;g[key][1]+=delta;g[key][2]+=delta>0
    examples.append(dict(**d,delta_bb=delta,eq=eq,vs=vs))
  if k=='board':bet=C.Counter()
  if k in ('blind','call','raise','ante'):
   add=max(0,amt-bet[s]) if k=='raise' else amt
   stacks[s]-=add
   if k!='ante':bet[s]+=add
  if k=='fold':folds.add(s)
print(dict(g))
for d in sorted(examples,key=lambda d:-d['delta_bb']):print(d)
with open(os.path.join(HERE,'terminal_call_audit.json'),'w') as f:json.dump(dict(groups=dict(g),examples=examples),f,indent=1)
