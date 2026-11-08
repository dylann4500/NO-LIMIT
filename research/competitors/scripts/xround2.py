import json, sys, statistics as S, math
labs=sys.argv[1].split(","); R=[json.load(open(p)) for p in sys.argv[2:]]
def tab(A):
    out={}
    for s,v in A['pts'].items():
        if len(v)>=30: out[A['name'].get(s,s)]=(S.mean(v), 1.96*S.pstdev(v)/math.sqrt(len(v)), len(v))
    return out
T=[tab(A) for A in R]; last=T[-1]
rk=sorted(last,key=lambda n:-last[n][0])
print("rank in last file; columns: "+" | ".join(labs))
for i,n in enumerate(rk[:16]):
    print(f"{i+1:3d} {n[:18]:18s} "+" | ".join(f"{t[n][0]:5.2f}±{t[n][1]:4.2f}" if n in t else "     new    " for t in T))
us=[n for n in last if n=='avalon']
if us: print(f"avalon rank {rk.index('avalon')+1}/{len(rk)}: "+" | ".join(f"{t['avalon'][0]:5.2f}±{t['avalon'][1]:4.2f}" if 'avalon' in t else "-" for t in T))
import itertools
for a,b in itertools.combinations(range(len(T)),2):
    ns=set(T[a])&set(T[b]); xs=[T[a][n][0] for n in ns]; ys=[T[b][n][0] for n in ns]
    mx,my=S.mean(xs),S.mean(ys); r=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
    print(f"corr {labs[a]}-{labs[b]} n={len(ns)} r={r:+.2f}")
