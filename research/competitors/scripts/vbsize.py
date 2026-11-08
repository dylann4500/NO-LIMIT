import json, sys, math
OUT=sys.argv[1]
A=json.load(open(f"{OUT}/o2/valuebets.json")); B=json.load(open(f"{OUT}/o1/valuebets.json"))
def st(C,key):
    v=C["cells"].get(key)
    if not v or v[0]<40: return None
    n,s,ss,nc,sc=v; m=s/n; return m, math.sqrt(max(0,ss/n-m*m)/n), n, nc/n
print("HU value bets into a visible card that does NOT pair the board: forward bb by size (o2 | o1)")
for street in (2,3):
    for hc in ("TP_weak","TP_good","midpair","overpair","2pair+","nopair"):
        for vc in ("conn","miss"):
            row=[]
            for sz in ("<=0.5","0.5-0.8",">0.8"):
                a=st(A,f"{street}|HU|{hc}|{vc}|bet{sz}"); b=st(B,f"{street}|HU|{hc}|{vc}|bet{sz}")
                row.append(f"{sz:>7s}: " + (f"{a[0]:+6.2f}±{a[1]:4.2f}(n{a[2]:5d},call {a[3]:3.0%})" if a else "        -               ") + " | " + (f"{b[0]:+6.2f}" if b else "  -   "))
            print(f"s{street} {hc:8s} {vc:4s}  " + "   ".join(row))
