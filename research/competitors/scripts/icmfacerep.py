import json, sys, math, statistics as S
def f(v): return f"{S.mean(v):+5.2f}±{S.pstdev(v)/math.sqrt(len(v)):4.2f}" if len(v)>=20 else " n<20 "
for path,lab in zip(sys.argv[1::2], sys.argv[2::2]):
    A=json.load(open(path)); t=A["thr"]
    b=lambda x: "?" if x is None else ("top10" if x>=t["top10"] else ("10-25" if x>=t["10-25"] else ("25-45" if x>=t["25-45"] else "45+")))
    C=[r for r in A["rows"] if r[0]=="CALL" and r[7] in ("call","raise")]; F=[r for r in A["rows"] if r[0]=="FOLD"]
    print(f"== {lab}: facing an all-in, <=5 alive: call rate | ICM pts of calls vs fold (±SE)")
    for grp,al in (("2-3 alive",(2,3)),("4-5 alive",(4,5))):
        cs=[r for r in C if r[1] in al]; fs=[r for r in F if r[1] in al]
        print(f"   {grp}: all  call {len(cs)/max(1,len(cs)+len(fs)):4.0%} (n {len(cs)+len(fs)})  calls {f([r[6] for r in cs])}")
        for bd in ("top10","10-25","25-45","45+"):
            c=[r for r in cs if b(r[3])==bd]; fo=[r for r in fs if b(r[3])==bd]
            print(f"        {bd:6s} call {len(c)/max(1,len(c)+len(fo)):4.0%} (n {len(c)+len(fo):5d})  calls {f([r[6] for r in c])}")
