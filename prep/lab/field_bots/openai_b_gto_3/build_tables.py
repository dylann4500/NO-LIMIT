"""Offline equity tables; uses only eval7, never the tournament simulator."""
import eval7, json, os
R='23456789TJQKA'
keys=[]
for hi in range(12,-1,-1):
 for lo in range(hi,-1,-1):
  keys.extend([R[hi]+R[lo]] if hi==lo else [R[hi]+R[lo]+'s',R[hi]+R[lo]+'o'])
# A playability ordering: pair/ace strength, suitedness, connectivity.
def merit(k):
 a,b=R.index(k[0])+2,R.index(k[1])+2
 if a==b:return 38+a*4.2
 suited=k[-1]=='s'; gap=a-b
 score=a*3.1+b*1.55+(8 if suited else 0)
 if gap==1:score+=5
 elif gap==2:score+=2
 elif gap>=4:score-=min(8,(gap-3)*1.6)
 if a==14:score+=6+(3 if suited and b<=5 else 0)
 if b>=10:score+=4
 return score
ordered=sorted(keys,key=merit,reverse=True)
# Percentiles count physical combinations rather than the 169 canonical hands.
rank={}; acc=0
for k in ordered:
 combos=6 if len(k)==2 else 4 if k[-1]=='s' else 12
 rank[k]=(acc+combos/2)/1326
 acc+=combos
cuts=[.025,.05,.08,.12,.18,.25,.35,.50,.70,1.0]
ranges=[]
for c in cuts:
 ranges.append(eval7.HandRange(','.join(k for k in ordered if rank[k]<=c)).hands)
data={}
for k in keys:
 hand=[eval7.Card(k[0]+'s'),eval7.Card(k[1]+('s' if k[-1]=='s' else 'h'))]
 data[k]=[round(eval7.py_hand_vs_range_monte_carlo(hand,r,[],30000),4) for r in ranges]
with open(os.path.join(os.path.dirname(__file__),'preflop.json'),'w') as f:
 json.dump({'cuts':cuts,'rank':rank,'equity':data},f,separators=(',',':'))
print('wrote',len(data),'hands')
