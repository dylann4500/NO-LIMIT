import json, sys
A=json.load(open(sys.argv[1])); B=json.load(open(sys.argv[2])); la,lb=sys.argv[3],sys.argv[4]
ta,tb=A["ntab"],B["ntab"]
print(f"our showdown bb/table: {la} vs {lb}  (n hands)")
keys=sorted(set(A["cat"])|set(B["cat"]))
for k in keys:
    a=A["cat"].get(k,[0,0]); b=B["cat"].get(k,[0,0])
    print(f"  {k:28s} {a[1]/ta:+7.2f} ({a[0]:6d}) -> {b[1]/tb:+7.2f} ({b[0]:6d})   diff {b[1]/tb-a[1]/ta:+6.2f}   per hand {a[1]/max(1,a[0]):+5.2f} -> {b[1]/max(1,b[0]):+5.2f}")
na={A["name"].get(k,k):v for k,v in A["opp"].items()}; nb={B["name"].get(k,k):v for k,v in B["opp"].items()}; rows=[]
for s in set(na)&set(nb):
    a=na[s]; b=nb[s]
    if a[0]>=150 and b[0]>=150: rows.append((b[1]/b[0]-a[1]/a[0], s[:16], a[1]/a[0], b[1]/b[0], a[0], b[0]))
rows.sort()
import statistics as S
print(f"HU showdowns per opponent team: median change {S.median(r[0] for r in rows):+.2f} bb/hand over {len(rows)} teams; worst 6:")
import math
print(f"  share of teams where our HU showdown bb/hand fell: {sum(1 for r in rows if r[0]<0)/len(rows):.0%}")
for r in rows[:6]: print(f"  {r[1]:16s} {r[2]:+6.2f} -> {r[3]:+6.2f} bb/hand  (n {r[4]} -> {r[5]})")
