import json, sys, statistics as S, math
R=[json.load(open(p)) for p in sys.argv[1:]]
def tab(A):
    out={}
    for s,v in A['pts'].items():
        if len(v)>=30: out[A['name'].get(s,s)]=(S.mean(v), 1.96*S.pstdev(v)/math.sqrt(len(v)), len(v))
    return out
T=[tab(A) for A in R]
names=set(T[0])&set(T[1])
xs=[T[0][n][0] for n in names]; ys=[T[1][n][0] for n in names]
mx,my=S.mean(xs),S.mean(ys)
r=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
print(f"teams in both: {len(names)}  corr(points r2, r3) = {r:+.2f}")
top=sorted(names,key=lambda n:-(T[0][n][0]+T[1][n][0]))[:15]
for n in top: print(f"{n[:16]:16s} " + "  ".join(f"{t[n][0]:5.2f}±{t[n][1]:4.2f}" if n in t else "  -  " for t in T))
