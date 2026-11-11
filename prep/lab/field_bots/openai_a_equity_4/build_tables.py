"""Offline-only construction of the shipped preflop equity model."""
import eval7, random, json, time, os
RANKS='23456789TJQKA'
CARDS=[eval7.Card(r+s) for r in RANKS for s in 'cdhs']
rng=random.Random(130297)
full=eval7.HandRange('22+,A2+,K2+,Q2+,J2+,T2+,92+,82+,72+,62+,52+,42+,32')
classes={}
for hi in range(12,-1,-1):
 for lo in range(hi,-1,-1):
  for suited in ([False] if hi==lo else [True,False]):
   key=RANKS[hi]+RANKS[lo]+('' if hi==lo else 's' if suited else 'o')
   h=[CARDS[4*hi+3],CARDS[4*lo+(3 if suited else 2)]]
   eq=eval7.py_hand_vs_range_monte_carlo(h,full,[],50000)
   bonus=(.015 if suited else 0)+(.008 if hi==lo else 0)+(.008 if suited and hi-lo<=2 and hi>=5 else 0)
   classes[key]={'h':h,'eq':eq,'score':eq+bonus,'combos':6 if hi==lo else 4 if suited else 12}
ordered=sorted(classes,key=lambda k:classes[k]['score'],reverse=True)
combos=[]; percent={}; cum=0
for k in ordered:
 d=classes[k]; percent[k]=(cum+d['combos']*.5)/1326;cum+=d['combos']
 hi=RANKS.index(k[0]);lo=RANKS.index(k[1]); suited=k.endswith('s')
 for s in range(4):
  for t in range(4):
   if hi==lo and t>=s: continue
   if hi!=lo and ((s==t)!=suited): continue
   a=hi*4+s;b=lo*4+t
   combos.append((a,b))
qs=[.05,.10,.18,.30,.50,.75,1.0]
ranges=[combos[:max(10,round(q*1326))] for q in qs]
# Use C for low-noise heads-up equities; multiway Monte Carlo deals all holes
# before the board, correctly accounting for card removal and tied pots.
t0=time.time(); out={}
for ix,key in enumerate(ordered):
 h=classes[key]['h']; hi=[c.rank*4+c.suit for c in h]; hm=(1<<hi[0])|(1<<hi[1]); row=[]
 for qi,rr in enumerate(ranges):
  legal=[(a,b,(1<<a)|(1<<b)) for a,b in rr if not ((1<<a)|(1<<b))&hm]
  hr=eval7.HandRange('');hr.hands=[((CARDS[a],CARDS[b]),1.0) for a,b,_ in legal]
  values=[1.0,eval7.py_hand_vs_range_monte_carlo(h,hr,[],35000)]
  for n in range(2,8):
   total=0.; trials=2600
   for trial in range(trials):
    mask=hm; opponents=[]
    for j in range(n):
     for attempt in range(200):
      a,b,m=rng.choice(legal)
      if not m&mask: break
     else:
      available=[c for c in range(52) if not (1<<c)&mask];a,b=rng.sample(available,2);m=(1<<a)|(1<<b)
     mask|=m;opponents.append((CARDS[a],CARDS[b]))
    board=[]
    while len(board)<5:
     c=rng.randrange(52)
     if not (1<<c)&mask:
      mask|=1<<c;board.append(CARDS[c])
    hv=eval7.evaluate(h+board);ties=1;won=True
    for opp in opponents:
     ov=eval7.evaluate(list(opp)+board)
     if ov>hv: won=False;break
     if ov==hv: ties+=1
    if won: total+=1/ties
   values.append(round(total/trials,6))
  row.append(values)
 out[key]=row
 if ix%10==0: print(ix,key,round(time.time()-t0,1),flush=True)
path=os.path.join(os.path.dirname(__file__),'preflop.json')
with open(path,'w') as f:json.dump({'q':qs,'order':ordered,'percent':percent,'equity':out},f,separators=(',',':'))
print('DONE',round(time.time()-t0,1),path,flush=True)
