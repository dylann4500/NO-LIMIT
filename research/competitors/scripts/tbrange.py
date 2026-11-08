"""2 Curry's (and others') shown non-jam 3-bet hands: 2-card HU-equity percentile distribution. Showdown-biased toward strong hands."""
import json, sys, random, itertools, collections
import eval7
R="23456789TJQKA"
def build_two(n=400, seed=1):
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
def key(a,b):
    ra,rb=R.index(a[0]),R.index(b[0])
    if ra<rb: ra,rb,a,b=rb,ra,b,a
    return (ra,rb,a[1]==b[1] and ra!=rb)
deck=[r+s for r in R for s in "shdc"]
allv=sorted(T[key(a,b)] for a,b in itertools.combinations(deck,2))
pct=lambda v: sum(1 for x in allv if x>v)/len(allv)
OUT=sys.argv[1]
for r in ("o1","o2","o3"):
    A=json.load(open(f"{OUT}/{r}/threebet.json")); nm=A["name"]
    grp=collections.defaultdict(list)
    for team,cards in A["shown"]:
        grp["2 Curry" if nm.get(team)=="2 Curry" else ("US" if team==A["you"] else "others")].append(cards)
    for g in ("2 Curry","US","others"):
        cs=grp[g]
        if not cs: continue
        ps=[pct(T[key(a,b)]) for a,b in cs]
        pairs=sum(1 for a,b in cs if a[0]==b[0])/len(cs); ax=sum(1 for a,b in cs if "A" in (a[0],b[0]) and a[0]!=b[0])/len(cs)
        b=lambda lo,hi: sum(1 for p in ps if lo<=p<hi)/len(ps)
        print(f"{r} {g:8s} shown n={len(cs):5d} | 2-card percentile: top10 {b(0,.10):4.0%} 10-25 {b(.10,.25):4.0%} 25-50 {b(.25,.50):4.0%} 50-100 {b(.50,1.01):4.0%} | pairs {pairs:4.0%} A-x {ax:4.0%}")
