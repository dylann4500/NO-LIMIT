import json, sys, math
A=json.load(open(sys.argv[1])); B=json.load(open(sys.argv[2]))  # o2, o1
def st(C,key):
    v=C["cells"].get(key)
    if not v or v[0]<2: return None
    n,s,ss,nc,sc=v; m=s/n; var=max(0,ss/n-m*m); return n,m,math.sqrt(var/n),nc/n
flag=[]
print("street HU/MW hand vis | o2: check EV | bet EV (call%) | diff±SE || o1: diff±SE   [bb, forward]")
for street in (2,3):
    for hm in ("HU","MW"):
        for hc in ("TP_weak","TP_good","overpair","2pair+","midpair","nopair"):
            for vc in ("pair","conn","miss"):
                for act in ("bet","bet<=0.5","bet0.5-0.8","bet>0.8"):
                    k=f"{street}|{hm}|{hc}|{vc}"
                    c2=st(A,k+"|check"); b2=st(A,k+"|"+act); c1=st(B,k+"|check"); b1=st(B,k+"|"+act)
                    if not (c2 and b2 and c2[0]>=60 and b2[0]>=60): continue
                    d2=b2[1]-c2[1]; e2=math.sqrt(b2[2]**2+c2[2]**2)
                    o1=""
                    if c1 and b1 and c1[0]>=30 and b1[0]>=30:
                        d1=b1[1]-c1[1]; e1=math.sqrt(b1[2]**2+c1[2]**2); o1=f"{d1:+6.2f}±{e1:4.2f}"
                    else: d1=None
                    mark=""
                    if d2<-2*e2: mark="  <== LOSES (o2)" + ("  & o1 same sign" if d1 is not None and d1<0 else "")
                    if act=="bet" or mark:
                        print(f"s{street} {hm} {hc:8s} {vc:4s} {act:10s} chk {c2[1]:+6.2f}(n{c2[0]:5d}) bet {b2[1]:+6.2f}(n{b2[0]:5d},{b2[3]:3.0%}) diff {d2:+6.2f}±{e2:4.2f} || o1 {o1}{mark}")
                    if mark: flag.append((d2*b2[0]/A['ntab'], k, act, d2, e2, b2[0], d1))
print("\nFLAGGED cells (bet worse than check by >2SE in o2), sorted by bb/table cost:")
for g,k,act,d2,e2,n,d1 in sorted(flag):
    print(f"  {k:28s} {act:10s} cost {g:+.3f} bb/table  diff {d2:+.2f}±{e2:.2f} n{n}  o1 diff {('%+.2f'%d1) if d1 is not None else 'n/a'}")
