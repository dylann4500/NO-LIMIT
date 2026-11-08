import json, sys
T=json.load(open(sys.argv[1]))
def get(*k):
    v=T.get("|".join(map(str,k))); return v if v else [0,0,0]
print("sanity fold fwd (should be 0):", get("hu_face",1,"pair","air","fold"))
print("== facing a preflop jam: call vs fold, fwd bb / whole-hand points ==")
for b in ("6-8","45","3"):
    for eb in ("<10","10-20","20+"):
        for hc in ("pair+","A-high","QK-high","low"):
            f=get("pre_facejam",b,hc,eb,"fold"); c=get("pre_facejam",b,hc,eb,"call")
            if f[0]+c[0]<80: continue
            cr=c[0]/(f[0]+c[0])
            print(f"left {b:3s} eff {eb:5s} {hc:8s} call% {cr:4.0%} call {c[1]/max(1,c[0]):+6.2f}bb {c[2]/max(1,c[0]):+6.2f}p (n{c[0]}) | fold {f[2]/max(1,f[0]):+6.2f}p (n{f[0]})")
print("== unopened: action mix and points per hand ==")
for b in ("6-8","45","3"):
    for eb in ("<10","10-20","20+"):
        for hc in ("pair+","A-high","QK-high","low"):
            acts={a:get("pre_unopened",b,hc,eb,a) for a in ("fold","limp","raise","jam")}
            n=sum(v[0] for v in acts.values())
            if n<150: continue
            print(f"left {b:3s} eff {eb:5s} {hc:8s} "+"  ".join(f"{a} {v[0]/n:4.0%} {v[1]/max(1,v[0]):+6.2f}bb {v[2]/max(1,v[0]):+5.2f}p" for a,v in acts.items()))
