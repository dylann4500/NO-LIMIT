import json, sys
T=json.load(open(sys.argv[1]))
def get(*k):
    v=T.get("|".join(map(str,k))); return v if v else [0,0,0]
f=lambda v: f"{v[1]/v[0]:+6.2f}(n{v[0]:5d})" if v[0] else "     -       "
print("our flop first-in: bet% | forward bb bet vs check, by #opps x villain-visible connect x our hand")
for no in ("1","2","3+"):
    for cc in ("pair","draw","miss"):
        for oc in ("ALL","air","fdraw","pair_mid","pair_top","strong"):
            b=get("ff",no,cc,oc,"bet"); c=get("ff",no,cc,oc,"check")
            if b[0]+c[0]<100: continue
            print(f"opps {no:2s} vis {cc:4s} us {oc:8s} bet% {b[0]/(b[0]+c[0]):4.0%}  bet {f(b)}  check {f(c)}  diff {(b[1]/max(1,b[0]) - c[1]/max(1,c[0])):+6.2f}")
