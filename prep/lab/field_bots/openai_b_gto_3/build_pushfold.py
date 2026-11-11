"""Offline heads-up push/fold subgame solution by fictitious play.
The only poker implementation used here is the permitted eval7 library.
"""
import os,json,time
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['VECLIB_MAXIMUM_THREADS']='1'
import numpy as np
import eval7
HERE=os.path.dirname(__file__)
table=json.load(open(os.path.join(HERE,'preflop.json')))
keys=list(table['rank'])
N=len(keys)
cache=os.path.join(HERE,'pushfold_matrix.npz')
if os.path.exists(cache):
 d=np.load(cache);E=d['E'];C=d['C']
else:
 E=np.zeros((N,N));C=np.zeros((N,N))
 ranges=[eval7.HandRange(k).hands for k in keys]
 for i,k in enumerate(keys):
  h=[eval7.Card(k[0]+'s'),eval7.Card(k[1]+('s' if k[-1]=='s' else 'h'))]
  for j in range(N):
   C[i,j]=sum(not (set(hi)&set(h)) for hi,w in ranges[j])
   if j<i:E[i,j]=1-E[j,i]
   elif j==i:E[i,j]=.5
   else:E[i,j]=eval7.py_hand_vs_range_monte_carlo(h,ranges[j],[],16000)
  if i%30==0:print('equity row',i,flush=True)
 np.savez_compressed(cache,E=E,C=C)
P=C/1225.
out={}
for depth in [2,3,4,5,6,8,10,12,15,20]:
 # Shove payoff relative to folding SB; call payoff relative to folding BB.
 A=P*(2*depth*E-depth-1)
 B=P*(2*depth*E-depth+1)
 shove=np.full(N,.5);call=np.full(N,.3)
 # Warm-started averaging settles the mixed boundary hands as well as pure hands.
 for t in range(1,18001):
  bs=(1.5+A@call>0).astype(float)
  bc=(B@shove>0).astype(float)
  alpha=1/(t+2)
  shove+=(bs-shove)*alpha;call+=(bc-call)*alpha
 mass=(P*shove[None,:]).sum(axis=1)
 eqcall=((P*shove[None,:])*E).sum(axis=1)/np.maximum(1e-12,mass)
 combos=np.array([6 if len(k)==2 else 4 if k[-1]=='s' else 12 for k in keys])
 ev=1.5+A@call
 bb_ev=B@shove
 regret=float(np.dot(combos/1326,np.maximum(ev,0)-shove*ev+np.maximum(bb_ev,0)-call*bb_ev))
 width=float(np.dot(shove,combos)/1326)
 cw=float(np.dot(call,combos)/1326)
 out[str(depth)]={'shove':{k:round(float(x),4) for k,x in zip(keys,shove)},'call':{k:round(float(x),4) for k,x in zip(keys,call)},'equity_call':{k:round(float(x),4) for k,x in zip(keys,eqcall)},'ev':{k:round(float(x),5) for k,x in zip(keys,ev)},'exploitability_bb':round(regret,6),'shove_width':round(width,4),'call_width':round(cw,4)}
 print('depth',depth,'shove',round(width,3),'call',round(cw,3),'gap_bb',round(regret,6),flush=True)
with open(os.path.join(HERE,'pushfold.json'),'w') as f:json.dump(out,f,separators=(',',':'))
