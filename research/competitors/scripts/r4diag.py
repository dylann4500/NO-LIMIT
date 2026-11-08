"""Diagnose our raises facing a raise/bet (preflop and postflop): size vs previous bet, and automatic actions."""
import gzip, json, sys, collections
path=sys.argv[1]
pre=collections.Counter(); post=collections.Counter(); auto=0; autok=collections.Counter(); ntab=0
ex=[]
with gzip.open(path,"rt") as fh:
    head=json.loads(fh.readline()); you=head["you"]
    for line in fh:
        t=json.loads(line)
        if "you" in t:
            a=t["you"].get("automatic",[]); auto+=len(a)
            for x in a[:3]: autok[str(x)[:80]]+=1
            continue
        if "hands" not in t: continue
        ntab+=1
        me=t["seats"].index(you)
        for h in t["hands"]:
            bb=h["blinds"][1]; sb=h["stacks_before"]
            street=0; contrib=collections.Counter(); last=0; prevlast=0; tot=collections.Counter()
            for e in h["events"]:
                k=e["kind"]; s=e.get("seat")
                if k=="board": street+=1; contrib=collections.Counter(); last=0; continue
                if k=="blind": contrib[s]+=e["amount"]; tot[s]+=e["amount"]; last=max(last,e["amount"]); continue
                if k=="call": contrib[s]+=e["amount"]; tot[s]+=e["amount"]; continue
                if k=="raise":
                    if s==me and ((street==0 and last>bb) or (street>0 and last>0)):
                        ratio=e["amount"]/last; allin=tot[s]+e["amount"]-contrib[s]>=sb[s]
                        key=("allin" if allin else f"x{min(ratio,6):.1f}" if ratio<2.6 else ">=2.6x")
                        (pre if street==0 else post)[key]+=1
                        if len(ex)<6 and street>0 and not allin: ex.append((h["hand"],street,last,e["amount"],sb[s]))
                    tot[s]+=e["amount"]-contrib[s]; contrib[s]=e["amount"]; last=e["amount"]
print("tables",ntab,"automatic actions",auto, autok.most_common(5))
print("pre re-raise sizes:",sorted(pre.items(),key=lambda x:-x[1])[:12])
print("post raise sizes:",sorted(post.items(),key=lambda x:-x[1])[:12])
print("examples (hand,street,facing,raise_to,stack):",ex)
