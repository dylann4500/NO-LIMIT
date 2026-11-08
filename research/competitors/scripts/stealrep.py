import json, sys, statistics as S
A=json.load(open(sys.argv[1])); P=json.load(open(sys.argv[2]))  # steal.json, agg2.json (for pts)
you,name,T=A["you"],A["name"],A["t"]; pts=P["pts"]
rows=sorted(((S.mean(v),s) for s,v in pts.items() if len(v)>=30), reverse=True)
top=[s for _,s in rows if s!=you][:6]; field=[s for _,s in rows]
nm=lambda s:("US" if s==you else name.get(s,s[:8]))[:12]
def g(grp,B,pos,act):
    n=f=w=0
    for s in grp:
        v=T.get(f"{s}|{B}|{pos}|{act}")
        if v: n+=v[0]; f+=v[1]; w+=v[2]
    return n,f,w
print("late-position first-in (CO/BTN/SB; SB when heads-up): open freq, realized fwd bb per open (raise / jam), immediate-win %, EV per opportunity")
for B in ("8-6","5-4","3","2"):
    for lab,grp in [(nm(s),[s]) for s in top]+[("TOP6",top),("US",[you]),("ALL",field)]:
        o=g(grp,B,"late","opp")[0]
        rn,rf,rw=g(grp,B,"late","raise"); jn,jf,jw=g(grp,B,"late","jam")
        if not o: continue
        print(f"{B:4s} {lab:12s} opp {o:6d} raise {rn/o:4.0%} ev {rf/max(1,rn):+5.2f} win {rw/max(1,rn):4.0%} | jam {jn/o:4.0%} ev {jf/max(1,jn):+5.2f} | EV/opp {(rf+jf)/o:+5.2f}bb")
    print()
