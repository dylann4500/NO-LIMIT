"""Offline preflop equity data generator; never runs during a decision."""
import eval7, itertools, json, os
R='23456789TJQKA'
classes={}
allhands=[]
for i,a in enumerate([r+s for r in R for s in 'cdhs']):
 for b in [r+s for r in R for s in 'cdhs'][:i]:
  ra,rb=R.index(a[0]),R.index(b[0]);hi,lo=max(ra,rb),min(ra,rb)
  key=R[hi]+R[lo]+('' if hi==lo else 's' if a[1]==b[1] else 'o')
  pair=(eval7.Card(a),eval7.Card(b))
  classes.setdefault(key,pair);allhands.append((pair,1.0,key))
random_range=[(p,w) for p,w,k in allhands]
strength={k:eval7.py_hand_vs_range_monte_carlo(list(p),random_range,[],100000) for k,p in classes.items()}
def score(k):
 a,b=R.index(k[0]),R.index(k[1]);suited=k.endswith('s')
 # Deep-stack ordering rewards suitedness, connectivity and pocket pairs.
 return strength[k]+(.026 if suited else 0)+(.012 if suited and a-b<=2 else 0)+(.012 if a==b else 0)
order=sorted(classes,key=score,reverse=True)
percent={};total=0
for k in order:
 n=6 if len(k)==2 else 4 if k[-1]=='s' else 12
 percent[k]=(total+n/2)/1326;total+=n
bounds=[.05,.08,.12,.18,.25,.35,.5,.7,1.0]
ranges={str(v):[(p,w) for p,w,k in allhands if percent[k]<=v] for v in bounds}
data={}
for k,p in classes.items():
 data[k]=[round(strength[k],5),round(percent[k],5)]+[round(eval7.py_hand_vs_range_monte_carlo(list(p),ranges[str(v)],[],50000),5) for v in bounds]
with open(os.path.join(os.path.dirname(__file__),'preflop.json'),'w') as f:json.dump({'bounds':bounds,'hands':data},f,separators=(',',':'))
print('Wrote',len(data),'classes; strongest 35%:',','.join(k for k in order if percent[k]<.35))
