import json, sys, statistics as S
OUT=sys.argv[1]
print("our non-jam 3-bet facing a 4-bet: predicted ICM pts of a called 5-bet jam vs folding (no fold equity -> conservative), by our band and action taken")
for r in ("o1","o2","o3"):
    rows=json.load(open(f"{OUT}/{r}/fourbet.json"))["rows"]  # (False, band, k, 0, ev, eq, eff)
    print("==", r)
    for bd in ("top5","top10","10-25","25+"):
        for k in ("fold","call","raise"):
            R=[x for x in rows if x[1]==bd and x[2]==k]
            if len(R)<20: continue
            for lo,hi in ((0,40),(40,999)):
                Q=[x for x in R if lo<=x[6]<hi]
                if len(Q)<20: continue
                ev=[x[4] for x in Q]
                print(f"   {bd:6s} we {k:5s} eff {lo:>2}-{hi:<3}bb n={len(Q):4d}  jam-vs-fold {S.mean(ev):+5.2f} pts  >0 in {sum(1 for e in ev if e>0)/len(ev):4.0%}  equity {S.mean(x[5] for x in Q):.2f}")
