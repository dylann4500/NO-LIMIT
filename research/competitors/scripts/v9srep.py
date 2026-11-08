import json, sys, math, statistics as S
def f(v): return f"{S.mean(v):+5.2f}±{S.pstdev(v)/math.sqrt(len(v)):4.2f}" if len(v)>=15 else (" n<15 " if v else "  -   ")
for path,lab in zip(sys.argv[1::2], sys.argv[2::2]):
    A=json.load(open(path)); rows=A["rows"]
    print(f"===== {lab} ({A['ntab']} tables): action share and ICM pts vs fold counterfactual (±SE)")
    # 1. HU jam widening: 2 alive, SB first in, eff 10-20bb, by band (pct<=0.75 ~ top75%)
    print(" [1] HU SB first-in, 10-20 bb eff: jam% / jam pts | raise% / raise pts | fold%")
    for bd in ("top25","25-50","50-75","75-100"):
        R=[r for r in rows if r[0]=="HU_SB_firstin" and r[2]==bd and 10<=r[4]<20]
        if not R: continue
        J=[r[5] for r in R if r[1]=="jam"]; Rz=[r[5] for r in R if r[1]=="raise"]; F=[r for r in R if r[1]=="fold"]; Lm=[r[5] for r in R if r[1]=="call"]
        print(f"     {bd:6s} n={len(R):4d} jam {len(J)/len(R):4.0%} {f(J)} | raise {len(Rz)/len(R):4.0%} {f(Rz)} | limp {len(Lm)/len(R):4.0%} {f(Lm)} | fold {len(F)/len(R):4.0%}")
    # 2. HU opens with an ace / two broadway, eff 10-40bb (non-jam raise)
    print(" [2] HU SB first-in, 10-40 bb, ace or two T+ (3 cards): raise% / pts | jam% / pts | limp/fold%")
    for q in (True, False):
        R=[r for r in rows if r[0]=="HU_SB_firstin" and r[3]==q and 10<=r[4]<40]
        if not R: continue
        J=[r[5] for r in R if r[1]=="jam"]; Rz=[r[5] for r in R if r[1]=="raise"]; L=[r for r in R if r[1] in ("call","fold")]
        print(f"     {'qualifies' if q else 'other    '} n={len(R):4d} raise {len(Rz)/len(R):4.0%} {f(Rz)} | jam {len(J)/len(R):4.0%} {f(J)} | limp/fold {len(L)/len(R):4.0%}")
    fz=[r[5] for r in rows if r[1]=="fold"]
    print(f" sanity: fold rows vs counterfactual {S.mean(fz):+.3f} (should be ~0), n={len(fz)}")
    # 3. BB jams vs CO/BTN/SB open, 5-8 alive, < 40 bb, ace or two T+
    print(" [3] BB vs single CO/BTN/SB open, 5-8 alive, <40 bb: jam% / jam pts | call% / pts | fold%")
    for q in (True, False):
        R=[r for r in rows if r[0]=="BB_vs_late_open" and r[3]==q and r[4]<40]
        if not R: continue
        J=[r[5] for r in R if r[1]=="jam"]; C=[r[5] for r in R if r[1]=="call"]; F=[r for r in R if r[1]=="fold"]
        print(f"     {'qualifies' if q else 'other    '} n={len(R):4d} jam {len(J)/len(R):4.0%} {f(J)} | call {len(C)/len(R):4.0%} {f(C)} | fold {len(F)/len(R):4.0%}")
