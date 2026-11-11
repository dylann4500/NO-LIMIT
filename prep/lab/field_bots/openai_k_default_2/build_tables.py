"""Rebuild the immutable preflop equity artifact offline (not loaded by the bot).
Native Monte Carlo makes the regenerated values slightly different each run.
"""
import eval7, itertools, pickle, time
from pathlib import Path
ROOT=str(Path(__file__).resolve().parent)
rs='23456789TJQKA'; suits='cdhs'
cards=[eval7.Card(r+s) for r in rs for s in suits]
combos=list(itertools.combinations(range(52),2))
full=[([cards[a],cards[b]],1.0) for a,b in combos]
def key(a,b):
 x,y=a//4,b//4
 if x<y:x,y=y,x
 return rs[x]+rs[y]+('' if x==y else 's' if a%4==b%4 else 'o')
classes={}
for a,b in combos:classes.setdefault(key(a,b),[]).append((a,b))
start=time.time(); equity={}
for k,cs in classes.items():
 a,b=cs[0]
 equity[k]=float(eval7.py_hand_vs_range_monte_carlo([cards[a],cards[b]],full,[],24000))
def score(k):
 a,b=rs.index(k[0]),rs.index(k[1]);v=equity[k]
 if len(k)==2:v-=max(0,7-a)*.006
 elif k[-1]=='s':
  v+=.024
  gap=a-b
  if gap<=2:v+=.012
  if gap==3:v+=.004
  if a==12 and b<=3:v+=.018
 return v
order=sorted(classes,key=score,reverse=True)
widths=[.025,.04,.06,.08,.10,.13,.16,.20,.25,.30,.36,.45,.55,.70,.85,1.]
ranges=[];percentile={}; running=0
for k in order:
 percentile[k]=(running+.5*len(classes[k]))/1326
 running+=len(classes[k])
for w in widths:
 rng=[];count=0
 for k in order:
  if count>=1326*w:break
  for a,b in classes[k]:rng.append(([cards[a],cards[b]],1.))
  count+=len(classes[k])
 ranges.append(rng)
table={}
for i,k in enumerate(order):
 a,b=classes[k][0]
 table[k]=[float(eval7.py_hand_vs_range_monte_carlo([cards[a],cards[b]],rng,[],16000)) for rng in ranges]
print('generated',len(table),'in',time.time()-start,'seconds')
with open(ROOT+'/preflop.pkl','wb') as f:pickle.dump((widths,percentile,equity,table,order),f,protocol=4)
print('first range order',order[:50])
