import json, sys
T=json.load(open(sys.argv[1]))
def get(*k):
    v=T.get("|".join(map(str,k))); return v if v else [0,0,0]
def row(lab, keys):
    out=[]
    for a,k in keys:
        n,s,p=get(*k); out.append(f"{a}:{(s/n if n else float('nan')):+6.2f}bb/{(p/n if n else float('nan')):+5.2f}p(n{n})")
    print(f"{lab:24s} "+"  ".join(out))
print("== HU first-in (no bet yet): forward bb / points, bet vs check ==")
for st in (1,2,3):
    for vc in ("pair","over","low"):
        for oc in ("ALL","air","fdraw","pair_mid","pair_top","strong"):
            nb=get("hu_first",st,vc,oc,"bet")[0]; nc=get("hu_first",st,vc,oc,"check")[0]
            if nb+nc<150: continue
            row(f"s{st} opp:{vc:4s} us:{oc:8s} bet%{nb/(nb+nc):4.0%}", [("bet",("hu_first",st,vc,oc,"bet")),("chk",("hu_first",st,vc,oc,"check"))])
print("\n== HU facing a bet: forward bb, call vs fold (fold=0) ==")
for st in (1,2,3):
    for vc in ("pair","over","low"):
        for oc in ("ALL","air","fdraw","pair_mid","pair_top","strong"):
            n=[get("hu_face",st,vc,oc,a)[0] for a in ("fold","call","raise")]
            if sum(n)<150: continue
            row(f"s{st} bettor:{vc:4s} us:{oc:8s} fold%{n[0]/sum(n):4.0%}", [("call",("hu_face",st,vc,oc,"call")),("raise",("hu_face",st,vc,oc,"raise"))])
