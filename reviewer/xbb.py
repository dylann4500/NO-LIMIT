"""Big blind facing a single non-all-in open (no limpers/callers): our call/3bet vs fold, in ICM points, by opener position & our strength.
usage: python -I xbb.py HANDS.gz TABLES.json"""
import collections, gzip, json, math, sys
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
        sb_=h["stacks_before"]; n=len(sb_)
        if sb_[me]<=0 or hi>=len(mc) or len(mc[hi])!=3: continue
        alive=[i for i in range(n) if sb_[i]>0]
        if len(alive)<3: continue
        b=h["button"]; order=[(b+k)%n for k in range(1,n+1) if sb_[(b+k)%n]>0]  # clockwise from seat after button; button last
        sbs,bbs=order[0],order[1]
        if bbs!=me: continue
        pos={order[-1]:"BTN",sbs:"SB"}
        if len(order)>=4: pos[order[-2]]="CO"
        com=[0]*n; opener=None; bad=False; bb=h["blinds"][1]
        for e in h["events"]:
            k,s=e["kind"],e.get("seat")
            if k=="board": break
            if s is None: continue
            if k=="blind": com[s]+=e["amount"]; continue
            if s==me:
                if opener is None or bad: break
                st=[sb_[i]-com[i] for i in range(n)]; st[opener]=sb_[opener]+sum(com[i] for i in range(n) if i!=opener)
                pf=poker_agent_sdk.icm([max(0,st[i]) for i in alive],pay)[alive.index(me)]
                v=G["cls"].get(canon3(mc[hi]))
                a="fold" if k=="fold" else "call" if k=="call" else ("jam" if e["amount"]>=sb_[me] else "3bet")
                out.append((pos.get(opener,"EP/MP"),v[0] if v else .5,a,h["equity_after"][me]-pf,len(alive)))
                break
            if k=="call": 
                if opener is None: bad=True  # limper
                else: bad=True              # cold caller before us
                com[s]+=e["amount"]
            elif k=="raise":
                if opener is not None or e["amount"]>=sb_[s]: bad=True
                opener=s; com[s]=max(com[s],e["amount"])
    return out
def ms(v):
    m=sum(v)/len(v); sd=math.sqrt(sum((x-m)**2 for x in v)/max(1,len(v)-1)); return m, sd/math.sqrt(len(v))
def main():
    with gzip.open(sys.argv[1],"rt") as f:
        f.readline(); L=f.readlines()
    cls=json.load(open(sys.argv[2]))["classes"]
    pairs=[(L[i],L[i+1]) for i in range(0,len(L)-1,2) if not L[i].startswith('{"you"') and L[i+1].startswith('{"you"')]
    with Pool(8,initializer=init,initargs=(cls,)) as p: R=[x for r in p.map(work,pairs,chunksize=32) for x in r]
    nt=len(pairs); print(sys.argv[1][-30:], f"{nt} tables, {len(R)} BB-vs-single-open spots")
    if "--split" in sys.argv:
        for lab,cond in (("alive=3",lambda a:a==3),("alive>=4",lambda a:a>=4)):
            for op in ("BTN","CO","EP/MP"):
                v=[x[3] for x in R if x[0]==op and x[2]=="call" and x[1]>0.30 and cond(x[4])]
                if len(v)>=40:
                    m,se=ms(v); print(f"  SPLIT {lab:8s} opener {op:5s} weak(pct>.30) calls n={len(v):5d} call-vs-fold {m:+.2f} +-{se:.2f} pts ({sum(v)/nt:+.3f}/table)")
    for op in ("EP/MP","CO","BTN","SB"):
        row=[x for x in R if x[0]==op]
        if not row: continue
        c=collections.Counter(x[2] for x in row); tot=len(row)
        print(f"  opener {op:5s} n={tot:6d} fold {c['fold']/tot:4.0%} call {c['call']/tot:4.0%} 3bet {c['3bet']/tot:4.0%} jam {c['jam']/tot:4.0%}")
        for lo,hi,lab in ((0,.30,"top30%"),(.30,.60,"31-60%"),(.60,1.01,"61-100%")):
            v=[x[3] for x in row if x[2]=="call" and lo<=x[1]<hi]
            if len(v)>=50:
                m,se=ms(v); print(f"      CALL {lab:7s} n={len(v):5d}  call-vs-fold {m:+.2f} ±{se:.2f} pts   ({sum(v)/nt:+.3f} pts/table)")
if __name__=="__main__": main()
