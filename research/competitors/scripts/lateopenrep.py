import json, sys, math, statistics as S
A=json.load(open(sys.argv[1])); thr=A["thr"]; rows=A["rows"]
labs=["top10","10-25","25-45","45-60","60-75","75-100"]
def b(x):
    for t,l in zip(thr,labs):
        if x>=t: return l
    return labs[-1]
def f(v): return f"{S.mean(v):+5.2f}±{1.96*S.pstdev(v)/math.sqrt(len(v)):4.2f}" if len(v)>=30 else "  n<30   "
for nb,lab in (((6,7,8),"8-6"),((4,5),"5-4"),((3,),"3")):
    print(f"== players left {lab}, late position first-in, stacks >=15bb (non-jam opens)")
    for bk in labs:
        R=[r for r in rows if r[0] in nb and b(r[1])==bk and r[5]>=15]
        O=[r for r in R if r[2]=="raise"]
        if not R: continue
        print(f"  {bk:7s} spots {len(R):6d} open {len(O)/len(R):4.0%} | open fwd bb {f([r[3] for r in O])} (n {len(O)}) | whole-hand pts open {f([r[4] for r in O])} fold {f([r[4] for r in R if r[2]=='fold'])}")
