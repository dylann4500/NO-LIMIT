import json, sys, statistics as S, math
OUT=sys.argv[1]
fixed=set(json.load(open(f"{OUT}/o2/fixed_stations.json")))
for r in ("o1","o2"):
    V=json.load(open(f"{OUT}/{r}/valuebets.json")); nm=V["name"]
    agg={"fixed":{},"other":{}}
    for k,v in V["callers"].items():
        team,street,hc=k.split("|"); g="fixed" if nm.get(team,team) in fixed else "other"
        a=agg[g].setdefault(hc,[0,0.0,0]); a[0]+=v[0]; a[1]+=v[1]; a[2]+=v[2]
    print(f"== {r}: our HU turn/river bets that got CALLED, by caller group: fwd bb per called bet / our showdown-win share")
    for hc in ("nopair","midpair","TP_weak","TP_good","overpair","2pair+"):
        f=agg["fixed"].get(hc,[0,0,0]); o=agg["other"].get(hc,[0,0,0])
        print(f"   {hc:9s} fixed stations {f[1]/max(1,f[0]):+6.2f} win {f[2]/max(1,f[0]):4.0%} (n{f[0]:5d}) | others {o[1]/max(1,o[0]):+6.2f} win {o[2]/max(1,o[0]):4.0%} (n{o[0]:6d})")
# adaptation speed: bets faced per team-table (all bettors), and the prior's weight
G=json.load(open(f"{OUT}/o2/agg.json"))
per=[c.get("face_bet",0)/len(G["pts"][s]) for s,c in G["st"].items() if s in G["pts"] and len(G["pts"][s])>=30]
print(f"\nbets faced per opponent per table (o2): median {S.median(per):.1f}; prior weight w=6 -> after n faced bets the estimate moves n/(n+6) of the way")
for n in (3,6,12,20): print(f"   n={n:2d}: {n/(n+6):.0%} of the way from 0.45")
fx=[(G["name"].get(s),c.get("fold_bet",0)/max(1,c.get("face_bet",1)), c.get("face_bet",0)/len(G["pts"][s])) for s,c in G["st"].items() if G["name"].get(s) in fixed and s in G["pts"]]
print(f"fixed stations in o2: mean fold-to-bet {S.mean(x[1] for x in fx):.0%} (prior 45%), bets faced per table {S.mean(x[2] for x in fx):.1f}")
