"""Offline preflop equity asset generation; never imported by the agent."""
import eval7, itertools, json, time
from pathlib import Path
R='23456789TJQKA'
cards={r+s:eval7.Card(r+s) for r in R for s in 'shdc'}
def key(a,b):
 x,y=sorted((a[0],b[0]),key=R.index,reverse=True)
 return x+y+('' if x==y else 's' if a[1]==b[1] else 'o')
classes={}
for a,b in itertools.combinations(cards,2): classes.setdefault(key(a,b),[]).append((cards[a],cards[b]))
allhands=[(h,1) for hs in classes.values() for h in hs]
start=time.time()
base={k:float(eval7.py_hand_vs_range_monte_carlo(list(v[0]),allhands,[],18000)) for k,v in classes.items()}
# Playability orders the opening ranges; equity tables use the same ordering.
def score(k):
 a,b=R.index(k[0])+2,R.index(k[1])+2
 s=base[k]
 if a==b: s+=0.012
 elif k[-1]=='s':
  s+=0.022
  if a-b<=2: s+=0.012
  if a-b==1 and a>=9: s+=0.008
 elif a-b>=5 and a<14: s-=0.012
 return s
order=sorted(classes,key=score,reverse=True)
widths=[.03,.05,.08,.12,.18,.25,.35,.5,.7,1.0]
ranges=[]
for w in widths:
 hs=[]
 for k in order:
  hs.extend((h,1) for h in classes[k])
  if len(hs)>=1326*w: break
 ranges.append(hs)
eq={}
for i,k in enumerate(order):
 eq[k]=[round(float(eval7.py_hand_vs_range_monte_carlo(list(classes[k][0]),rng,[],24000)),5) for rng in ranges]
 if i%30==0: print(i,round(time.time()-start,1),flush=True)
Path(__file__).with_name('preflop.json').write_text(json.dumps({'order':order,'widths':widths,'equity':eq},separators=(',',':')))
print('finished',time.time()-start)
