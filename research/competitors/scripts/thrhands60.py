import random, eval7
R="23456789TJQKA"
def build_two(n=600, seed=1):
    rnd=random.Random(seed); deck=[r+s for r in R for s in "shdc"]; out={}
    for ra in range(13):
        for rb in range(ra+1):
            for suited in ((False,True) if ra!=rb else (False,)):
                a=R[ra]+"s"; b=R[rb]+("s" if suited else "h"); rest=[c for c in deck if c not in (a,b)]; w=0.0
                for _ in range(n):
                    smp=rnd.sample(rest,7); h1=eval7.evaluate([eval7.Card(c) for c in [a,b]+smp[2:]]); h2=eval7.evaluate([eval7.Card(c) for c in smp[:2]+smp[2:]])
                    w+=1 if h1>h2 else (0.5 if h1==h2 else 0)
                out[(ra,rb,suited)]=w/n
    return out
T=build_two()
lab=lambda k: R[k[0]]+R[k[1]]+("" if k[0]==k[1] else ("s" if k[2] else "o"))
for t,name in ((0.5375,"top60"),):
    ks=sorted((k for k,v in T.items() if v>=t), key=lambda k:-T[k])
    print(name, "best-2-card class needs HU equity >=", t, ":", len(ks), "classes, weakest:", ", ".join(lab(k) for k in ks[-8:]))
