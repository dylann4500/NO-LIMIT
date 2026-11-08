"""What hands do we 3-bet (non-all-in) and raise postflop with? Uses our private cards."""
import gzip, json, sys, collections
R="23456789TJQKA"
def cls(c3):
    rs=sorted((R.index(c[0]) for c in c3), reverse=True)
    if len(set(rs))<3: return "pair+"
    if rs[0]>=12: return "A-high"
    if rs[0]>=10: return "Q/K-high"
    return "<=J-high"
path=sys.argv[1]; pend={}
with gzip.open(path,"rt") as fh:
    head=json.loads(fh.readline()); you=head["you"]; tabs={}
    lines=fh.readlines()
res=collections.Counter(); base=collections.Counter()
for i in range(0,len(lines)-1):
    t=json.loads(lines[i])
    if "hands" not in t: continue
    y=json.loads(lines[i+1]).get("you")
    if not y: continue
    me=t["seats"].index(you)
    for hi,h in enumerate(t["hands"]):
        if hi>=len(y["cards"]) or not y["cards"][hi]: continue
        cl=cls(y["cards"][hi]); raises=0; tot=collections.Counter(); con=collections.Counter(); street=0
        for e in h["events"]:
            k=e["kind"]; s=e.get("seat")
            if k=="board": street+=1; con=collections.Counter(); continue
            if k=="blind": tot[s]+=e["amount"]; con[s]+=e["amount"]; continue
            if k=="call": tot[s]+=e["amount"]; con[s]+=e["amount"]
            if street==0 and s==me and k in("fold","call","raise") and raises==1:
                base[cl]+=1
                if k=="raise":
                    allin=tot[s]+e["amount"]-con[s]>=h["stacks_before"][s]
                    res[(cl,"jam" if allin else "3bet")]+=1
            if k=="raise":
                tot[s]+=e["amount"]-con[s]; con[s]=e["amount"]
                if street==0: raises+=1
print("facing one open: our 3-bet rate by our 3-card class")
for cl in ("pair+","A-high","Q/K-high","<=J-high"):
    n=base[cl]; print(f"  {cl:9s} n={n:6d} 3bet {res[(cl,'3bet')]/max(1,n):5.1%} jam {res[(cl,'jam')]/max(1,n):5.1%}")
