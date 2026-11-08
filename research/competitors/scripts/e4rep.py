import json, sys, math, statistics as S
A=json.load(open(sys.argv[1])); rows=A["rows"]  # (freq, bucket, k, real, ev_pred, eq, eff)
def f(v): return f"{S.mean(v):+5.2f}±{1.96*S.pstdev(v)/math.sqrt(len(v)):4.2f}" if len(v)>=20 else " n<20 "
print("CALIBRATION on spots we CALLED: predicted ICM gain vs realized")
for bk in ("top10","10-25","25-45"):
    C=[r for r in rows if r[1]==bk and r[2]=="call"]
    if C: print(f"  {bk:6s} n={len(C):5d} predicted {S.mean(r[4] for r in C):+5.2f}  realized {f([r[3] for r in C])}  mean equity {S.mean(r[5] for r in C):.2f}")
print("\nSpots we FOLDED: predicted ICM gain if we had called (pts), share predicted > 0")
for fq,lab in ((True,"frequent re-jammers"),(False,"others")):
    print(" ==",lab)
    for bk in ("top10","10-25","25-45"):
        for lo,hi in ((0,15),(15,25),(25,999)):
            F=[r for r in rows if r[0]==fq and r[1]==bk and r[2]=="fold" and lo<=r[6]<hi]
            if len(F)<20: continue
            print(f"   {bk:6s} eff {lo:>2}-{hi:<3} folds {len(F):5d}  predicted call gain {S.mean(r[4] for r in F):+5.2f} pts  >0 in {sum(1 for r in F if r[4]>0)/len(F):4.0%}  equity {S.mean(r[5] for r in F):.2f}")
