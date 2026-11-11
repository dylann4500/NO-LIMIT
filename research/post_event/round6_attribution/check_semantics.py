"""Verify event amount semantics by replaying chips: blind=posted, call=increment, raise=street raise-to total, win=pot share.
usage: python -I check_semantics.py HANDS.gz NTABLES"""
import gzip, json, sys, collections
kinds=collections.Counter(); bad=0; n=0; antes=collections.Counter(); seats_n=collections.Counter(); nh=collections.Counter()
with gzip.open(sys.argv[1],"rt") as f:
    hdr=json.loads(f.readline()); cnt=0
    for line in f:
        t=json.loads(line)
        if "hands" not in t: continue
        cnt+=1
        if cnt>int(sys.argv[2]): break
        seats_n[len(t["seats"])]+=1; nh[len(t["hands"])//25*25]+=1
        for h in t["hands"]:
            n+=1; N=len(h["stacks_before"]); com=[0]*N; st=[0]*N; win=[0]*N
            antes[tuple(h["blinds"])]+=1
            for e in h["events"]:
                k=e["kind"]; s=e.get("seat"); kinds[k]+=1
                if k=="board": st=[0]*N; continue
                if k in ("blind","ante"): com[s]+=e["amount"]; st[s]+=e["amount"] if k=="blind" else 0
                elif k=="call": com[s]+=e["amount"]; st[s]+=e["amount"]
                elif k=="raise": com[s]+=e["amount"]-st[s]; st[s]=e["amount"]
                elif k=="win": win[s]+=e["amount"]
            calc=[h["stacks_before"][i]-com[i]+win[i] for i in range(N)]
            if calc!=h["stacks_after"]:
                bad+=1
                if bad<=3: print("MISMATCH", h["hand"], h["blinds"], calc, h["stacks_after"], [e for e in h["events"] if e["kind"] in ("blind","ante")])
print("hands",n,"mismatch",bad); print(kinds.most_common()); print(sorted(antes.items())[:40]); print(seats_n, sorted(nh.items()))
