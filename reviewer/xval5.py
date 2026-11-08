"""Cross-validate v5's two changes on real v3b hands.
A) river, not facing a bet, we bet while some live villain's visible card + board beats us -> v5 checks.
   Measure v3b's forward chips from that decision (v5's check-then-fold/lose = 0 forward).
B) <=5 alive, we call an all-in (or our call puts us all-in), heads-up -> v5 may fold if equity < ICM threshold.
   Measure v3b's realized ICM points vs the fold alternative (points if we had folded there), split by hand strength.
usage: python -I xval5.py HANDS.gz TABLES.json"""
import collections, gzip, json, sys
from itertools import permutations
from multiprocessing import Pool
import eval7, poker_agent_sdk
RANKS="23456789TJQKA"; SUITS="shdc"; RK={r:i for i,r in enumerate(RANKS)}; PERMS=[dict(zip(SUITS,p)) for p in permutations(SUITS)]
G={}; CC={}
def card(c):
    if c not in CC: CC[c]=eval7.Card(c)
    return CC[c]
def canon3(cards):
    best=None
    for m in PERMS:
        s="".join(sorted((c[0]+m[c[1]] for c in cards),key=lambda c:(RK[c[0]],c[1]),reverse=True))
        if best is None or s<best: best=s
    return best
def init(you,cls): G.update(you=you,cls=cls)
def work(pair):
    tl,yl=pair; t=json.loads(tl); y=json.loads(yl)["you"]; me=y["seat"]; pay=t["payouts"]
    kept={e["hand"]:e["cards"] for e in y["private_events"] if e["kind"]=="kept"}; mycards=y["cards"]
    A=[]; B=[]
    for hi,h in enumerate(t["hands"]):
        sb_,sa=h["stacks_before"],h["stacks_after"]
        if sb_[me]<=0: continue
        n=len(sb_); com=[0]*n; street_tot=[0]*n; street=0; board=[]; shown={}; folded=set(); river_bet=False
        alive=[i for i in range(n) if sb_[i]>0]
        jam_seat=None; done=False
        for e in h["events"]:
            k,s=e["kind"],e.get("seat")
            if k=="board":
                street+=1; board+=e.get("cards") or []; street_tot=[0]*n; continue
            if k=="reveal" and s is not None and e.get("cards"): shown[s]=e["cards"][0]
            if s is None: continue
            if k=="blind":
                com[s]+=e["amount"]; street_tot[s]+=e["amount"]; continue
            if k=="fold": folded.add(s); continue
            if k=="call":
                if s==me and not done and len(alive)<=5 and jam_seat is not None:
                    # we call an all-in: compare realized points with folding here
                    live=[i for i in alive if i not in folded]
                    if len(live)==2:
                        fold_st=[sb_[i]-com[i] for i in range(n)]
                        fold_st[jam_seat]=sb_[jam_seat]+sum(com[i] for i in range(n) if i!=jam_seat)
                        ids=[i for i in alive]; vec=[max(0,fold_st[i]) for i in ids]
                        pf=poker_agent_sdk.icm(vec,pay)[ids.index(me)]
                        mc=mycards[hi] if hi<len(mycards) else []
                        v=G["cls"].get(canon3(mc)) if len(mc)==3 else None
                        pct=v[0] if v else None
                        B.append((h["equity_after"][me]-pf, pct, street, sb_[me]/h["blinds"][1]))
                        done=True
                com[s]+=e["amount"]; street_tot[s]+=e["amount"]; continue
            if k=="raise":
                add=e["amount"]-street_tot[s]; com[s]+=add; street_tot[s]=e["amount"]
                if com[s]>=sb_[s] and jam_seat is None and s!=me: jam_seat=s
                if street==3 and not river_bet:
                    river_bet=True
                    if s==me and me in kept_ok(kept,h) and len(board)==5:
                        live=[i for i in alive if i not in folded and i!=me]
                        mine=eval7.evaluate([card(c) for c in kept[h["hand"]]+board])
                        beaten=[i for i in live if i in shown and eval7.evaluate([card(shown[i])]+[card(c) for c in board])>mine]
                        if beaten:
                            fwd=sa[me]-(sb_[me]-(com[me]-add))
                            A.append((len(live)==1, fwd/h["blinds"][1]))
                continue
    return A,B
def kept_ok(kept,h):
    return [0] if False else ([] if h["hand"] not in kept else None) or []
def main():
    with gzip.open(sys.argv[1],"rt") as f:
        hdr=json.loads(f.readline()); L=f.readlines()
    cls=json.load(open(sys.argv[2]))["classes"]
    pairs=[(L[i],L[i+1]) for i in range(0,len(L)-1,2) if not L[i].startswith('{"you"') and L[i+1].startswith('{"you"')]
    with Pool(8,initializer=init,initargs=(hdr["you"],cls)) as p: R=p.map(work,pairs,chunksize=32)
    A=[a for r in R for a in r[0]]; B=[b for r in R for b in r[1]]; nt=len(pairs)
    for hu in (True,False):
        sel=[x[1] for x in A if x[0]==hu]
        if sel: print(f"A) river bets into visible strength ({'heads-up' if hu else 'multiway'}): n={len(sel)} ({len(sel)/nt:.2f}/table); v3b forward {sum(sel)/len(sel):+.2f}bb each, {sum(sel)/nt:+.2f}bb/table -> v5 gain ~{-sum(sel)/nt:+.2f}bb/table")
    print(f"B) all-in calls with <=5 alive, heads-up: n={len(B)} ({len(B)/nt:.2f}/table); v3b points vs folding: avg {sum(b[0] for b in B)/max(1,len(B)):+.2f} pts per call")
    for lo,hi,lab in ((0,.10,"top10%"),(.10,.25,"10-25%"),(.25,.45,"25-45%"),(.45,1.01,"45%+")):
        sel=[b[0] for b in B if b[1] is not None and lo<=b[1]<hi and b[2]==0]
        if sel: print(f"   preflop, our hand {lab:7s}: n={len(sel):5d} call-vs-fold {sum(sel)/len(sel):+6.2f} pts each, {sum(sel)/nt:+.3f} pts/table")
    sel=[b[0] for b in B if b[2]>0]
    if sel: print(f"   postflop all-in calls: n={len(sel)} call-vs-fold {sum(sel)/len(sel):+.2f} pts each")
if __name__=="__main__": main()
