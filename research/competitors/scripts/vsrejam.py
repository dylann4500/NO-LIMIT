"""When WE open-raise (non-jam) and team X re-raises: X's re-raise rate vs our opens, our response, our forward bb.
usage: python -I vsrejam.py HANDS.jsonl.gz"""
import collections, gzip, json, sys
from multiprocessing import Pool
YOU=None
def init(y):
    global YOU; YOU=y
def proc(line):
    t=json.loads(line)
    if "hands" not in t or YOU not in t.get("seats",[]): return {}
    seats=t["seats"]; me=seats.index(YOU); out=collections.defaultdict(lambda:[0,0.0])
    for h in t["hands"]:
        sb_,sa=h["stacks_before"],h["stacks_after"]; bb=h["blinds"][1]
        if sb_[me]<=0: continue
        raises=0; opened=False; tot=collections.Counter(); faced=None; seen=set()
        for e in h["events"]:
            k,s=e["kind"],e.get("seat")
            if k=="board": break
            if k=="blind": tot[s]+=e["amount"]; continue
            if s is None or k not in("fold","check","call","raise"): continue
            if opened and raises==1 and s!=me and s not in seen:
                seen.add(s); X=seats[s]
                o=out[(X,"faced_our_open")]; o[0]+=1
                if k=="raise":
                    o=out[(X,"reraise"+("_jam" if e["amount"]>=sb_[s] else ""))]; o[0]+=1; faced=(X, e["amount"]>=sb_[s])
            elif faced and s==me and k in ("fold","call","raise"):
                X,j=faced; fwd=(sa[me]-sb_[me]+tot[me])/bb
                o=out[(X,"our_"+k+("_vsjam" if j else "_vs3b"))]; o[0]+=1; o[1]+=fwd; faced=None
            if s==me and raises==0 and k=="raise" and e["amount"]<sb_[me]: opened=True
            if k=="call": tot[s]+=e["amount"]
            if k=="raise": tot[s]=e["amount"]; raises+=1
    return {"|".join(k):v for k,v in out.items()}
def main():
    with gzip.open(sys.argv[1],"rt") as fh:
        head=json.loads(fh.readline()); lines=fh.readlines()
    nm={e["entry_id"]:e["team_name"] for e in head["entries"]}
    with Pool(8,initializer=init,initargs=(head["you"],)) as p: res=p.map(proc,lines,chunksize=32)
    T=collections.defaultdict(lambda:[0,0.0])
    for r in res:
        for k,v in r.items(): T[k][0]+=v[0]; T[k][1]+=v[1]
    teams=collections.Counter()
    for k,v in T.items():
        X,lab=k.split("|"); 
        if lab=="faced_our_open": teams[X]=v[0]
    want=[x for x in teams if nm.get(x) in ("Lemonade","TeamBallHog","AZ","Team 72","WAYS-ER TEAM","sandylikesfrogs","bill & ted","2 Curry")]
    allx=list(teams)
    def show(lab, xs):
        g=lambda l:[sum(T[f"{x}|{l}"][0] for x in xs), sum(T[f"{x}|{l}"][1] for x in xs)]
        f=g("faced_our_open")[0]; rj=g("reraise_jam"); r3=g("reraise")
        fj=g("our_fold_vsjam"); cj=g("our_call_vsjam"); f3=g("our_fold_vs3b"); c3=g("our_call_vs3b"); a3=g("our_raise_vs3b")
        nj=fj[0]+cj[0]
        print(f"{lab:16s} faced {f:6d} rejam {rj[0]/max(1,f):5.1%} 3bet {r3[0]/max(1,f):5.1%} | vs their jam: we call {cj[0]/max(1,nj):4.0%} call EV {cj[1]/max(1,cj[0]):+6.2f}bb fold EV {fj[1]/max(1,fj[0]):+5.2f} (n {nj})")
    for x in want: show(nm[x][:16],[x])
    show("ALL others", allx)
if __name__ == "__main__":
    main()
