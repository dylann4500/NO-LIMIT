import gzip,json,sys,collections
f=gzip.open(sys.argv[1],"rt")
h=json.loads(f.readline()); you=h["you"]
N=int(sys.argv[2])
kinds=collections.Counter(); seq=collections.Counter(); nt=0; nyou=0; ours=0; auto=collections.Counter(); autoex=[]
antes=collections.Counter(); pts_ctx=collections.Counter(); prev=None; lines=0; pairs=0
for i,line in enumerate(f):
    o=json.loads(line); lines+=1
    if "hands" in o:
        nt+=1; t=o
        if you in t["seats"]: ours+=1
        for hh in t["hands"]:
            antes[tuple(hh["blinds"])]+=0
            antes[hh["blinds"][2]]+=1
            ev=hh["events"]; sb=hh["stacks_before"]
            street=0
            for j,e in enumerate(ev):
                kinds[e["kind"]]+=1
                if e["kind"]=="board": street+=1
                if e["kind"]=="prize_the_shover":
                    p=ev[j-1]; s=e.get("seat")
                    allin = p["kind"]=="raise" and p.get("seat")==s and p["amount"]>=sb[s]
                    pts_ctx[(street,p["kind"],allin, p.get("seat")==s)]+=1
                    # is it first all-in raise of hand?
                if e["kind"]=="raise" and e["amount"]>=sb[e["seat"]]:
                    nxt=ev[j+1]["kind"] if j+1<len(ev) else None
                    seq[("allin_raise_street",street,"next_is_prize",nxt=="prize_the_shover")]+=1
                if e["kind"]=="call" :
                    pass
    else:
        nyou+=1
        y=o["you"]
        for a in y.get("automatic",[]):
            auto[json.dumps(a)[:80]]+=1
            if len(autoex)<5: autoex.append(a)
    if nt>=N: break
print("lines",lines,"tables",nt,"you-lines",nyou,"our tables",ours)
print(kinds)
print("antes", {k:v for k,v in antes.items() if not isinstance(k,tuple)})
print("prize ctx (street, prevkind, prev is allin raise, same seat)", pts_ctx)
print(seq)
print("auto", auto.most_common(10)); print(autoex)
