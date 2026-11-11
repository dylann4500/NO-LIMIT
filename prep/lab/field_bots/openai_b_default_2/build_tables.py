"""Build immutable preflop equity tables using only eval7, offline."""
import eval7, json, os, time
RANKS='23456789TJQKA'
C=eval7.Card
CARDS=[C(r+s) for r in RANKS for s in 'cdhs']
def key(i,j):
 a,b=i//4,j//4
 if a==b:return RANKS[a]*2
 a,b=max(a,b),min(a,b)
 return RANKS[a]+RANKS[b]+('s' if i%4==j%4 else 'o')
COMBOS=[(i,j,key(i,j)) for i in range(52) for j in range(i)]
HANDS={}
for i,j,k in COMBOS:HANDS.setdefault(k,[CARDS[i],CARDS[j]])
full=[((CARDS[i],CARDS[j]),1.0) for i,j,k in COMBOS]
t=time.time()
base={k:eval7.py_hand_vs_range_monte_carlo(h,full,[],40000) for k,h in HANDS.items()}
# An equity-versus-strong-range ordering avoids overvaluing weak aces and small pairs.
def initial(k):
 a,b=RANKS.index(k[0])+2,RANKS.index(k[1])+2
 return base[k]+(.018 if len(k)==3 and k[2]=='s' else 0)+(.012 if a-b==1 else 0)
order=sorted(HANDS,key=initial,reverse=True)
init=set(); count=0
for k in order:
 if count>=1326*.23:break
 init.add(k);count+=6 if len(k)==2 else 4 if k[-1]=='s' else 12
strong=[((CARDS[i],CARDS[j]),1.) for i,j,k in COMBOS if k in init]
vs={k:eval7.py_hand_vs_range_monte_carlo(h,strong,[],60000) for k,h in HANDS.items()}
order=sorted(HANDS,key=lambda k:.36*base[k]+.64*vs[k]+(.008 if k[-1:]=='s' else 0),reverse=True)
percentiles={};cum=0
for k in order:
 n=6 if len(k)==2 else 4 if k[-1]=='s' else 12
 percentiles[k]=(cum+n/2)/1326;cum+=n
fractions=[.025,.04,.06,.09,.13,.18,.25,.35,.5,.7,1.]
ranges=[]
for f in fractions:
 keys={k for k,p in percentiles.items() if p<=f}
 ranges.append([((CARDS[i],CARDS[j]),1.) for i,j,k in COMBOS if k in keys])
equities={}
for k,h in HANDS.items():
 equities[k]=[round(eval7.py_hand_vs_range_monte_carlo(h,r,[],100000),5) for r in ranges]
print('built',len(HANDS),'in',time.time()-t, 'seconds')
data={'fractions':fractions,'rank':percentiles,'equity':equities,'random':base,'order':order}
with open(os.path.join(os.path.dirname(__file__),'preflop.json'),'w') as f:json.dump(data,f,separators=(',',':'))
print('top40',order[:40])
