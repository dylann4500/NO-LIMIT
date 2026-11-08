import gzip, json, sys, functools
PAY=[50,30,20]
def icm(stacks):
    """Malmuth-Harville: live players (stack>0) share prizes PAY[:n]."""
    idx=[i for i,s in enumerate(stacks) if s>0]; n=len(idx); pr=(PAY+[0]*8)[:n]
    tot=sum(stacks[i] for i in idx); eq={i:0.0 for i in idx}
    @functools.lru_cache(None)
    def rec(rem, place):
        # returns dict-like tuple of contributions: expected prize for each remaining player given remaining set
        res=[0.0]*len(stacks)
        if place>=len(pr) or not rem: return tuple(res)
        T=sum(stacks[i] for i in rem)
        for i in rem:
            p=stacks[i]/T
            res[i]+=p*pr[place]
            sub=rec(tuple(j for j in rem if j!=i), place+1)
            for j in range(len(stacks)): res[j]+=p*sub[j]
        return tuple(res)
    return rec(tuple(idx),0)
with gzip.open(sys.argv[1],"rt") as fh:
    fh.readline(); m=0; worst=0; cnt=0
    for line in fh:
        t=json.loads(line)
        if "hands" not in t: continue
        for h in t["hands"][:]:
            sa=h["stacks_after"]; ea=h["equity_after"]
            if sum(1 for s in sa if s>0)>6: continue
            e=icm(sa)
            for i,s in enumerate(sa):
                if s>0:
                    d=abs(e[i]-ea[i]); worst=max(worst,d); cnt+=1
        m+=1
        if m>=40: break
print("live-player equity checks",cnt,"max abs diff vs Malmuth-Harville",round(worst,4))
