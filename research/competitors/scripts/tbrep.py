import json, sys, math, statistics as S
A=json.load(open(sys.argv[1])); lab=sys.argv[2]
nm=A["name"]; C=A["cells"]; you=A["you"]
inv={v:k for k,v in nm.items()}
def g(*k):
    v=C.get("|".join(k)); return v if v else [0,0.0,0.0,0.0]
def m(v): 
    if v[0]<20: return "   n<20       "
    mu=v[1]/v[0]; se=math.sqrt(max(0,v[2]/v[0]-mu*mu)/v[0]); return f"{mu:+6.2f}±{se:4.2f}"
teams=["2 Curry","Lemonade","sandylikesfrogs","AZ","TeamBallHog","Team 72"]
print(f"##### {lab}: facing ONE non-jam open, no cold callers. fwd bb per decision (fold = 0); pts = whole-hand points")
for t in teams+["US"]:
    e=you if t=="US" else inv.get(t)
    if not e: continue
    acts={a:g(e,"*","*","*",a) for a in ("fold","call","3bet","jam")}; n=sum(v[0] for v in acts.values())
    if not n: continue
    s=" | ".join(f"{a} {v[0]/n:4.0%} {m(v)} {v[3]/max(1,v[0]):+5.2f}p" for a,v in acts.items())
    o={a:g(e,"*","*","*","opener_"+a)[0] for a in ("fold","call","4bet")}; no=sum(o.values())
    f4={a:g(e,"*","*","*","vs4bet_"+a) for a in ("fold","call","5bet")}; n4=sum(v[0] for v in f4.values())
    print(f"  {t:15s} n={n:5d} {s}")
    if no: print(f"  {'':15s} opener vs its 3bet: fold {o['fold']/no:4.0%} call {o['call']/no:4.0%} 4bet {o['4bet']/no:4.0%} | its reply to 4bet: fold {f4['fold'][0]/max(1,n4):4.0%} call {f4['call'][0]/max(1,n4):4.0%} 5bet {f4['5bet'][0]/max(1,n4):4.0%} (n {n4})")
# 2 Curry by players alive x opener position x IP
e=inv.get("2 Curry")
print("  2 Curry 3bet vs fold by players alive / opener pos / IP:  [3bet% , 3bet fwd bb]")
for b in ("8-6","5-4","3-2"):
    for op in ("EP","CO","BTN","SB"):
        for ip in ("IP","OOP"):
            v={a:g(e,b,op,ip,a) for a in ("fold","call","3bet","jam")}; n=sum(x[0] for x in v.values())
            if n<60: continue
            print(f"     {b} open {op:3s} {ip:3s} n={n:4d} 3bet {v['3bet'][0]/n:4.0%} -> {m(v['3bet'])}  call {v['call'][0]/n:4.0%} -> {m(v['call'])}")
# field: all teams' non-jam 3bets
allv=[0,0.0,0.0,0.0]; allc=[0,0.0,0.0,0.0]
for k,v in C.items():
    p=k.split("|")
    if p[1:4]==["*","*","*"] and p[0]!="US" and p[0]!=you:
        if p[4]=="3bet": 
            for i in range(4): allv[i]+=v[i]
        if p[4]=="call":
            for i in range(4): allc[i]+=v[i]
print(f"  FIELD non-jam 3bet {m(allv)} (n {allv[0]})  | FIELD flat call {m(allc)} (n {allc[0]})")
print("  US by hand strength (our 3 cards), all spots:")
for qb in ("top15","rest"):
    v={a:g("US",qb,"*","*",a) for a in ("fold","call","3bet","jam")}; n=sum(x[0] for x in v.values())
    print(f"     {qb:5s} n={n:6d} " + " | ".join(f"{a} {x[0]/max(1,n):4.0%} {m(x)}" for a,x in v.items()))
    if qb=="top15":
        for b in ("8-6","5-4","3-2"):
            for ip in ("IP","OOP"):
                v={a:g("US",qb,b,ip,a) for a in ("fold","call","3bet","jam")}; n=sum(x[0] for x in v.values())
                if n>=100: print(f"       {b} {ip:3s} n={n:5d} " + " | ".join(f"{a} {x[0]/max(1,n):4.0%} {m(x)}" for a,x in v.items()))
