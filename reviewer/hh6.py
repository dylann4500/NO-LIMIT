"""Our preflop decisions: unopened vs facing raise, sizes; postflop bet sizing. usage: python -I hh6.py HANDS.gz [maxlines]"""
import collections, gzip, json, sys
from multiprocessing import Pool
YOU=None
def init(y):
    global YOU; YOU=y
def work(line):
    t=json.loads(line)
    if "hands" not in t or YOU not in t["seats"]: return None
    me=t["seats"].index(YOU); c=collections.Counter(); sizes=[]; bets=[]
    for h in t["hands"]:
        sb_=h["stacks_before"]
        if sb_[me]<=0: continue
        bb=h["blinds"][1] or 1; live=sum(1 for x in sb_ if x>0)
        grp="8-6" if live>=6 else "5-4" if live>=4 else "3-2"
        street=0; raises=0; acted=False; pot=0; streetbet={}
        for e in h["events"]:
            k,s=e["kind"],e.get("seat")
            if k=="blind": pot+=e.get("amount",0); streetbet[s]=e.get("amount",0); continue
            if k=="board": street+=1; streetbet={}; continue
            if s is None or k not in ("fold","check","call","raise"): continue
            if street==0 and s==me and not acted:
                acted=True; ctx="unopened" if raises==0 else "facing_raise" if raises==1 else "facing_3bet+"
                if k=="raise":
                    a="jam" if e["amount"]>=sb_[me] else "raise"
                    if a=="raise" and ctx=="unopened": sizes.append(e["amount"]/bb)
                else: a=k
                c[(grp,ctx,a)]+=1
            if street>0 and s==me and k=="raise":
                prev=streetbet.get(me,0); bets.append((e["amount"]-prev)/max(1,pot))
            if k in ("call","raise"):
                amt=e.get("amount",0)
                if k=="raise": pot+=amt-streetbet.get(s,0); streetbet[s]=amt
                else: pot+=amt; streetbet[s]=streetbet.get(s,0)+amt
            if street==0 and k=="raise": raises+=1
    return c,sizes,bets
def main():
    with gzip.open(sys.argv[1],"rt") as f:
        hdr=json.loads(f.readline()); L=[]
        for i,l in enumerate(f):
            if len(sys.argv)>2 and i>int(sys.argv[2]): break
            if not l.startswith('{"you"'): L.append(l)
    with Pool(8,initializer=init,initargs=(hdr["you"],)) as p: R=[r for r in p.map(work,L,chunksize=32) if r]
    C=collections.Counter(); S=[]; B=[]
    for c,s,b in R: C.update(c); S+=s; B+=b
    print(sys.argv[1][-45:], f"tables={len(R)}")
    for grp in ("8-6","5-4","3-2"):
        for ctx in ("unopened","facing_raise","facing_3bet+"):
            tot=sum(v for (g,cx,a),v in C.items() if g==grp and cx==ctx)
            if not tot: continue
            row={a:C[(grp,ctx,a)]/tot for a in ("fold","check","call","raise","jam")}
            print(f"  {grp:4s} {ctx:13s} n={tot:6d} "+" ".join(f"{a} {v:5.1%}" for a,v in row.items()))
    S.sort(); B.sort()
    if S: print(f"  open size bb: median {S[len(S)//2]:.1f}  p25 {S[len(S)//4]:.1f} p75 {S[3*len(S)//4]:.1f}")
    if B: print(f"  postflop bet/raise size (fraction of pot, approx): median {B[len(B)//2]:.2f} p75 {B[3*len(B)//4]:.2f}  n={len(B)}")
if __name__=="__main__": main()
