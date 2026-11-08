"""Our late (CO/BTN/SB) first-in opens vs folding in ICM points, >=3 alive, >=15bb, by hand pct band; folds measured too (fold = 0 forward by construction).
usage: python -I xsteal.py HANDS.gz TABLES.json"""
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
        bb=h["blinds"][1] or 1
        if sb_[me]/bb<15: continue
        b=h["button"]; order=[(b+k)%n for k in range(1,n+1) if sb_[(b+k)%n]>0]
        sbs,bbs=order[0],order[1]; late={order[-1],sbs}
        if len(order)>=4: late.add(order[-2])
        if me not in late: continue
        com=[0]*n; nb=0
        for e in h["events"]:
            k,s=e["kind"],e.get("seat")
            if k=="board": break
            if s is None: continue
            if k=="blind": com[s]+=e["amount"]; continue
            if s!=me:
                if k in ("call","raise"): break   # someone entered before us: not first-in
                continue
            a="fold" if k=="fold" else ("jam" if (k=="raise" and e["amount"]>=sb_[me]) else ("open" if k=="raise" else k))
            if a in ("open","fold"):
                st=[sb_[i]-com[i] for i in range(n)]; st[bbs]=sb_[bbs]+sum(com[i] for i in range(n) if i!=bbs)
                pf=poker_agent_sdk.icm([max(0,st[i]) for i in alive],pay)[alive.index(me)]
                v=G["cls"].get(canon3(mc[hi]))
                out.append((a, v[0] if v else .5, len(alive), h["equity_after"][me]-pf))
            break
    return out
def main():
    with gzip.open(sys.argv[1],"rt") as f:
        f.readline(); L=f.readlines()
    cls=json.load(open(sys.argv[2]))["classes"]
    pairs=[(L[i],L[i+1]) for i in range(0,len(L)-1,2) if not L[i].startswith('{"you"') and L[i+1].startswith('{"you"')]
    with Pool(8,initializer=init,initargs=(cls,)) as p: R=[x for r in p.map(work,pairs,chunksize=32) for x in r]
    nt=len(pairs); print(sys.argv[1][-30:-9], nt, "tables")
    for lo,hi in ((0,.25),(.25,.35),(.35,.45),(.45,.60)):
        for grp,cond in (("8-5 alive",lambda a:a>=5),("4-3 alive",lambda a:a<=4)):
            o=[x[3] for x in R if x[0]=="open" and lo<=x[1]<hi and cond(x[2])]; f=[x for x in R if x[0]=="fold" and lo<=x[1]<hi and cond(x[2])]
            if len(o)>=40:
                m=sum(o)/len(o); se=math.sqrt(sum((v-m)**2 for v in o)/(len(o)-1)/len(o))
                print(f"  pct {lo:.2f}-{hi:.2f} {grp}: opens n={len(o):5d} open-vs-fold {m:+.2f} ±{se:.2f} pts | folds n={len(f):5d} (open rate {len(o)/(len(o)+len(f)):.0%})")
if __name__=="__main__": main()
