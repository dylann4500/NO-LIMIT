"""Sum robust gains: (a) HU first-in bets with negative forward EV -> check (gain = check EV - bet EV, floored at -bet EV);
(b) HU calls with negative forward EV -> fold (gain = -call EV). Per our table."""
import json, sys
T=json.load(open(sys.argv[1])); ntab=float(sys.argv[2])
def get(*k):
    v=T.get("|".join(map(str,k))); return v if v else [0,0,0]
tot_a=tot_b=0; rows=[]
for st in (1,2,3):
    for vc in ("pair","over","low"):
        for oc in ("air","fdraw","pair_mid","pair_top","strong"):
            b=get("hu_first",st,vc,oc,"bet"); c=get("hu_first",st,vc,oc,"check")
            if b[0]>=100:
                eb=b[1]/b[0]; ec=c[1]/c[0] if c[0]>=50 else 0.0
                if eb<0 or (c[0]>=100 and ec>eb+0.5):
                    g=b[0]*(max(ec,0)-eb); tot_a+=g; rows.append((g/ntab,f"BET s{st} oppvis {vc} us {oc}: bet {eb:+.2f} vs check {ec:+.2f} n{b[0]}"))
            cl=get("hu_face",st,vc,oc,"call")
            if cl[0]>=100 and cl[1]<0:
                g=-cl[1]; tot_b+=g; rows.append((g/ntab,f"CALL s{st} bettorvis {vc} us {oc}: call {cl[1]/cl[0]:+.2f} n{cl[0]}"))
for g,s in sorted(rows,reverse=True): print(f"{g:5.2f} bb/table  {s}")
print(f"TOTAL bet->check {tot_a/ntab:.2f} bb/table, call->fold {tot_b/ntab:.2f} bb/table")
