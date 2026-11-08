import json, sys, math, statistics as S
A=json.load(open(sys.argv[1])); thr=A["thr"]; rows=[r for r in A["rows"] if r[1] is not None]
b=lambda x: "top10" if x>=thr["top10"] else ("10-25" if x>=thr["10-25"] else ("25-45" if x>=thr["25-45"] else "45-100"))
for fq,lab in ((True,"frequent re-jammers (Lemonade, AZ, BallHog, sandylikesfrogs)"),(False,"everyone else")):
    print("==",lab)
    for bk in ("top10","10-25","25-45","45-100"):
        R=[r for r in rows if r[0]==fq and b(r[1])==bk]; C=[r for r in R if r[2]!="fold"]
        if not R: continue
        cb=[r[3] for r in C]; ci=[r[4] for r in C]
        f=lambda v: f"{S.mean(v):+6.2f}±{1.96*S.pstdev(v)/math.sqrt(len(v)):4.2f}" if len(v)>=20 else "   n<20    "
        print(f"  {bk:7s} spots {len(R):5d} we call {len(C)/len(R):4.0%} | call fwd bb {f(cb)} | call ICM pts vs fold {f(ci)} (n {len(C)})")
print("== by effective stack (bb), all re-jammers: call rate, call ICM pts vs fold")
for bk in ("top10","10-25","25-45"):
    for lo,hi in ((0,15),(15,25),(25,40),(40,999)):
        R=[r for r in rows if b(r[1])==bk and lo<=r[7]<hi]; C=[r[4] for r in R if r[2]!="fold"]
        if not R: continue
        s=f"{S.mean(C):+5.2f}±{1.96*S.pstdev(C)/math.sqrt(len(C)):4.2f}" if len(C)>=20 else " n<20 "
        print(f"  {bk:6s} eff {lo:>2}-{hi:<3} spots {len(R):5d} call {len(C)/len(R):4.0%} ICM {s} (n {len(C)})")
