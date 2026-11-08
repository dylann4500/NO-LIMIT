import json, sys, math, statistics as S
A=json.load(open(sys.argv[1])); thr=A["thr"]; rows=A["rows"]
def b(x):
    if x is None: return "?"
    return "top10" if x>=thr["top10"] else ("10-25" if x>=thr["10-25"] else ("25-45" if x>=thr["25-45"] else "45-100"))
def line(lab, v):
    if len(v)<20: print(f"  {lab:34s} n={len(v):5d}"); return
    m=S.mean(v); h=1.96*S.pstdev(v)/math.sqrt(len(v)); print(f"  {lab:34s} n={len(v):5d}  call-minus-fold {m:+5.2f} ±{h:4.2f} pts")
for kind in ("call","rejam"):
    R=[r for r in rows if r[6]==kind]
    print(f"== {kind} (facing an all-in or putting us all-in), HU pots, <=5 alive ==")
    line("ALL", [r[5] for r in R])
    for st,lab in ((0,"preflop"),(1,"postflop")):
        P=[r for r in R if (r[1]==0)==(st==0)]
        line(lab, [r[5] for r in P])
        if st==0:
            for bk in ("top10","10-25","25-45","45-100"):
                line(f"  {bk}", [r[5] for r in P if b(r[2])==bk])
    print(" by alive x covered (preflop):")
    P=[r for r in R if r[1]==0]
    for al in (5,4,3,2):
        for cov in (True,False):
            line(f"  alive {al} {'jammer covers us' if cov else 'we cover jammer'}", [r[5] for r in P if r[0]==al and r[3]==cov])
    print(" bubble (alive 4-5), jammer covers us, by strength x eff stack:")
    for bk in ("top10","10-25","25-45","45-100"):
        for lo,hi in ((0,10),(10,20),(20,999)):
            line(f"  {bk} eff {lo}-{hi}bb", [r[5] for r in P if r[0] in (4,5) and r[3] and b(r[2])==bk and lo<=r[4]<hi])
