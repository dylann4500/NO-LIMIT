"""Our preflop jams: realized ICM points vs folding at that moment, by players alive, context and hand strength.
usage: python -I xjam.py HANDS.gz TABLES.json"""
import collections, gzip, json, sys
from itertools import permutations
from multiprocessing import Pool
import poker_agent_sdk
RANKS="23456789TJQKA"; SUITS="shdc"; RK={r:i for i,r in enumerate(RANKS)}; PERMS=[dict(zip(SUITS,p)) for p in permutations(SUITS)]
G={}
def canon3(cards):
    best=None
    for m in PERMS:
        s="".join(sorted((c[0]+m[c[1]] for c in cards),key=lambda c:(RK[c[0]],c[1]),reverse=True))
        if best is None or s<best: best=s
    return best
def init(cls): G.update(cls=cls)
def work(pair):
    tl,yl=pair; t=json.loads(tl); y=json.loads(yl)["you"]; me=y["seat"]; pay=t["payouts"]; mc=y["cards"]; out=[]
    for hi,h in enumerate(t["hands"]):
        sb_=h["stacks_before"]
        if sb_[me]<=0 or hi>=len(mc) or len(mc[hi])!=3: continue
        n=len(sb_); alive=[i for i in range(n) if sb_[i]>0]; com=[0]*n; last_raiser=None; bb_seat=None; nb=0
        for e in h["events"]:
            k,s=e["kind"],e.get("seat")
            if k=="board": break
            if s is None: continue
            if k=="blind":
                com[s]+=e["amount"]; nb+=1
                if nb==2: bb_seat=s
                continue
            if k=="call": com[s]+=e["amount"]; continue
            if k=="raise":
                if s==me:
                    if e["amount"]>=sb_[me]:
                        ctx="unopened" if last_raiser is None else "vs_raise"
                        tgt=last_raiser if last_raiser is not None else bb_seat
                        if tgt is None or tgt==me: break
                        st=[sb_[i]-com[i] for i in range(n)]; st[tgt]=sb_[tgt]+sum(com[i] for i in range(n) if i!=tgt)
                        vec=[max(0,st[i]) for i in alive]; pf=poker_agent_sdk.icm(vec,pay)[alive.index(me)]
                        v=G["cls"].get(canon3(mc[hi])); bb=h["blinds"][1]
                        out.append((len(alive),ctx,v[0] if v else 0.5,sb_[me]/bb,h["equity_after"][me]-pf))
                    break
                com[s]=e["amount"] if False else com[s]+(e["amount"]-0)  # placeholder, fixed below
                last_raiser=s
            if k=="fold" and s==me: break
    return out
def main():
    with gzip.open(sys.argv[1],"rt") as f:
        f.readline(); L=f.readlines()
    cls=json.load(open(sys.argv[2]))["classes"]
    pairs=[(L[i],L[i+1]) for i in range(0,len(L)-1,2) if not L[i].startswith('{"you"') and L[i+1].startswith('{"you"')]
    with Pool(8,initializer=init,initargs=(cls,)) as p: R=[x for r in p.map(work,pairs,chunksize=32) for x in r]
    nt=len(pairs); print(f"{nt} tables, {len(R)} of our preflop jams")
    for grp,lo,hi in (("7-8",7,8),("5-6",5,6),("4",4,4),("2-3",2,3)):
        for ctx in ("unopened","vs_raise"):
            row=[x for x in R if lo<=x[0]<=hi and x[1]==ctx]
            if not row: continue
            print(f"  {grp:3s} alive {ctx:9s} n={len(row):6d} jam-vs-fold {sum(x[4] for x in row)/len(row):+6.2f} pts each ({sum(x[4] for x in row)/nt:+.3f}/table)")
            for blo,bhi,lab in ((0,.10,"top10%"),(.10,.25,"10-25%"),(.25,.45,"25-45%"),(.45,1.01,"45%+")):
                b=[x[4] for x in row if blo<=x[2]<bhi]
                if len(b)>=30: print(f"        {lab:7s} n={len(b):5d} {sum(b)/len(b):+6.2f} pts each ({sum(b)/nt:+.3f}/table)")
if __name__=="__main__": main()
