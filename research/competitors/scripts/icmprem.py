import json, sys, math, statistics as S
rows=[]; thr=None
for f in sys.argv[1:]:
    A=json.load(open(f)); thr=A["thr"]; rows+=[r for r in A["rows"] if r[6]=="call" and r[7] is not None]
b=lambda x: "top10" if x>=thr["top10"] else ("10-25" if x>=thr["10-25"] else ("25-45" if x>=thr["25-45"] else "45-100"))
def L(lab,v):
    if len(v)<20: print(f"{lab:44s} n={len(v)}"); return
    print(f"{lab:44s} n={len(v):5d} call-minus-fold {S.mean(v):+5.2f} ±{1.96*S.pstdev(v)/math.sqrt(len(v)):4.2f} pts")
print("calls at <=5 alive (HU pots), by ICM premium = ICM break-even equity - chip pot odds")
for lo,hi in ((-1,0.02),(0.02,0.05),(0.05,0.10),(0.10,1)):
    R=[r for r in rows if lo<=r[7]-r[8]<hi]
    L(f"premium {lo:+.2f}..{hi:.2f} (all)", [r[5] for r in R])
    for st,lab in ((0,"pre"),(1,"post")):
        P=[r for r in R if (r[1]==0)==(st==0)]
        if st==0:
            for bk in ("top10","10-25","25-45","45-100"):
                L(f"    pre {bk}", [r[5] for r in P if r[2] is not None and b(r[2])==bk])
        else:
            L("    postflop", [r[5] for r in P])
