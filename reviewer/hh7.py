"""Our chip result by preflop line when facing a single raise. usage: python -I hh7.py HANDS.gz [maxlines]"""
import collections, gzip, json, sys
from multiprocessing import Pool
YOU=None
def init(y):
    global YOU; YOU=y
def work(line):
    t=json.loads(line)
    if "hands" not in t or YOU not in t["seats"]: return None
    me=t["seats"].index(YOU); out=collections.defaultdict(list); tot=[]
    for h in t["hands"]:
        sb_,sa=h["stacks_before"],h["stacks_after"]
        if sb_[me]<=0: continue
        bb=h["blinds"][1] or 1; d=(sa[me]-sb_[me])/bb; tot.append(d)
        street=0; raises=0; line_=None; sawflop=False; folded_pre=False
        for e in h["events"]:
            k,s=e["kind"],e.get("seat")
            if k=="board":
                street+=1
                if street==1: sawflop=True
                continue
            if s is None or k not in ("fold","check","call","raise"): continue
            if street==0 and s==me:
                if line_ is None and raises==1:
                    line_="3bet" if (k=="raise" and e["amount"]<sb_[me]) else ("jam" if k=="raise" else k)
                if k=="fold": folded_pre=True
            if street==0 and k=="raise": raises+=1
        if line_ in ("3bet",):
            key="3bet->folded preflop" if folded_pre else ("3bet->saw flop" if sawflop else "3bet->won preflop")
            out[key].append(d)
        elif line_:
            out[f"faced raise: {line_}"].append(d)
    return out, sum(tot), len(tot)
def main():
    with gzip.open(sys.argv[1],"rt") as f:
        hdr=json.loads(f.readline()); L=[]
        for i,l in enumerate(f):
            if len(sys.argv)>2 and i>int(sys.argv[2]): break
            if not l.startswith('{"you"'): L.append(l)
    with Pool(8,initializer=init,initargs=(hdr["you"],)) as p: R=[r for r in p.map(work,L,chunksize=32) if r]
    O=collections.defaultdict(list); T=0; N=0
    for o,t,n in R:
        T+=t; N+=n
        for k,v in o.items(): O[k]+=v
    print(sys.argv[1][-40:], f"tables={len(R)} all hands net {T:+.0f}bb over {N} hands ({T/len(R):+.1f}bb/table)")
    for k in sorted(O):
        v=O[k]; print(f"  {k:26s} n={len(v):6d}  total {sum(v):+9.0f}bb  ({sum(v)/len(R):+6.1f}bb/table)  avg {sum(v)/len(v):+6.2f}bb")
if __name__=="__main__": main()
