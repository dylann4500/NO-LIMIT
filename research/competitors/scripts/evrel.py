import json, sys
T=json.load(open(sys.argv[1]))
def get(*k):
    v=T.get("|".join(map(str,k))); return v if v else [0,0,0]
f=lambda v: f"{v[1]/v[0]:+6.2f}bb(n{v[0]})" if v[0] else "   -   "
print("opp visible card pairs board, HU. first-in bet vs check | facing their bet: fold% call raise")
for st in (1,2,3):
    for rel in ("air","fdraw","pair<vis","pair=vis","pair>vis","strong"):
        b=get("hu_first2",st,rel,"bet"); c=get("hu_first2",st,rel,"check")
        fo=get("hu_face2",st,rel,"fold"); ca=get("hu_face2",st,rel,"call"); ra=get("hu_face2",st,rel,"raise")
        n=fo[0]+ca[0]+ra[0]
        print(f"s{st} {rel:9s} bet {b[0]/max(1,b[0]+c[0]):4.0%} bet {f(b)} chk {f(c)} | fold {fo[0]/max(1,n):4.0%} call {f(ca)} raise {f(ra)}")
