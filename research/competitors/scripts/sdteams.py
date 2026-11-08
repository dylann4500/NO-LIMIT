import json, sys, statistics as S
OUT=sys.argv[1]
A=json.load(open(f"{OUT}/o1/sd.json")); B=json.load(open(f"{OUT}/o2/sd.json"))
G1=json.load(open(f"{OUT}/o1/agg.json")); G2=json.load(open(f"{OUT}/o2/agg.json"))
def fstats(G):
    out={}
    for s,c in G["st"].items():
        n=G["name"].get(s,s)
        out[n]=(c.get("fold_bet",0)/max(1,c.get("face_bet",0)), c.get("call_bet",0)/max(1,c.get("face_bet",0)), S.mean(G["pts"][s]) if s in G["pts"] else None)
    return out
f1,f2=fstats(G1),fstats(G2)
na={A["name"].get(k,k):v for k,v in A["opp"].items()}; nb={B["name"].get(k,k):v for k,v in B["opp"].items()}
ta,tb=A["ntab"],B["ntab"]
rows=[]
for s in set(na)&set(nb)&set(f1)&set(f2):
    a=na[s]; b=nb[s]
    if a[0]<150 or b[0]<150: continue
    contrib=(b[1]/b[0]-a[1]/a[0])*b[0]/tb   # bb/table of our showdown change attributable to this team (per-hand change x volume)
    rows.append((contrib,s,a[1]/a[0],b[1]/b[0],f1[s][0],f2[s][0],f1[s][2],f2[s][2]))
rows.sort()
tot=sum(r[0] for r in rows)
print(f"sum of per-team contributions {tot:+.2f} bb/table (total showdown change -7.95)")
neg=sum(r[0] for r in rows[:20]); print(f"worst 20 teams contribute {neg:+.2f} bb/table")
print("team             our HU-SD bb/hand o1->o2 | their foldToBet o1->o2 | their pts o1->o2")
for r in rows[:12]:
    print(f"  {r[1][:16]:16s} {r[2]:+6.2f} -> {r[3]:+6.2f} | {r[4]:4.0%} -> {r[5]:4.0%} | {r[6]:5.2f} -> {r[7]:5.2f}")
w=rows[:20]; rest=rows[20:]
print(f"worst-20 teams: mean foldToBet change {S.mean(r[5]-r[4] for r in w)*100:+.1f} pts, pts change {S.mean(r[7]-r[6] for r in w):+.2f}")
print(f"other teams:    mean foldToBet change {S.mean(r[5]-r[4] for r in rest)*100:+.1f} pts, pts change {S.mean(r[7]-r[6] for r in rest):+.2f}")

json.dump([r[1] for r in rows[:20]], open(f"{OUT}/o2/fixed_stations.json","w"))
