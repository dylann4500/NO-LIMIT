import json, sys, math
OUT=sys.argv[1]
def m(v):
    if v[0]<30: return "    n<30     "
    mu=v[1]/v[0]; se=math.sqrt(max(0,v[2]/v[0]-mu*mu)/v[0]); return f"{mu:+5.2f}±{se:4.2f}"
print("OUR decisions facing one non-jam open, by our 3-card strength band: share and forward bb per action (fold = 0)")
for r in ("o1","o2","o3"):
    C=json.load(open(f"{OUT}/{r}/threebet2.json"))["cells"]
    g=lambda *k: C.get("|".join(k),[0,0.0,0.0,0.0])
    print(f"== {r}")
    for qb in ("top5","5-10","10-15","15-25"):
        for b,ip in (("*","*"),("8-6","IP"),("8-6","OOP"),("5-4","IP"),("5-4","OOP")):
            v={a:g("US",qb,b,ip,a) for a in ("fold","call","3bet","jam")}; n=sum(x[0] for x in v.values())
            if n<150: continue
            print(f"  {qb:5s} {b:3s} {ip:3s} n={n:5d} " + " | ".join(f"{a} {x[0]/n:4.0%} {m(x)}" for a,x in v.items()))
