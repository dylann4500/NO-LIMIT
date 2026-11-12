import json, numpy as np, sys, math
sys.path.insert(0,'.')
from common import *
o=json.load(open('out/q1_pairs.json'))
R=api_results(); S=standings(); rank={t:r for r,t,_ in S}
def get(a,b): return {k.split('|')[2]:v for k,v in o.items() if k.startswith(f"{a}|{b}|")}
def feats(v):
    xs=[]; maxsig=0.0; nsig5=0
    for m,(p1,p2,z,n1,n2) in v['rates'].items():
        d=p2-p1; se=abs(d/z) if z else 0.0
        xs.append(max(d*d-se*se,0))
        if abs(z)>=5:
            maxsig=max(maxsig,abs(d))
            if abs(d)>=0.05: nsig5+=1
    tvm=max(v['tvs'].values()) if v['tvs'] else 0.0
    rm=math.sqrt(sum(xs)/len(xs))
    changed = v['meanz2']>=5 or tvm>=0.15
    if not changed: c='unchanged'
    elif maxsig>=0.05 or tvm>=0.30: c='rewrite' if (rm>=0.10 or nsig5>=8) else 'jump'
    else: c='tweak'
    return dict(cls=c, rmsx=rm, maxsig=maxsig, tvm=tvm, nsig5=nsig5, meanz2=v['meanz2'])
def classify(a,b):
    g=get(a,b); return {t:feats(v) for t,v in g.items()}
if __name__=="__main__":
    TR=[("R1","R2"),("R2","R3"),("R3","R4"),("R4","R5"),("R5","R6")]
    act=[t for t in R["R1"] if not any(R[l][t]["forfeited"] for l in SCORED)]
    def rk(l):
        s=sorted(act,key=lambda t:-R[l][t]['avg']); return {t:i+1 for i,t in enumerate(s)}
    print("null check (same file, odd vs even tables): share classified changed")
    for l in SCORED:
        c=classify(l,l); c.pop('avalon',None); print(' ',l,len(c),{k:sum(v['cls']==k for v in c.values()) for k in ('unchanged','tweak','jump','rewrite')})
    print("\n## Q1a bot changes between consecutive scored rounds (126 teams excl. avalon)")
    print("| transition | unchanged | small tweak | clear jump | rewrite-scale | median RMS rate change (pp) among changers |")
    print("|---|---|---|---|---|---|")
    rows=[]
    for a,b in TR:
        c=classify(a,b); c.pop('avalon',None); ra,rb=rk(a),rk(b)
        n={k:sum(v['cls']==k for v in c.values()) for k in ('unchanged','tweak','jump','rewrite')}
        med=np.median([v['rmsx'] for v in c.values() if v['cls']!='unchanged'])
        print(f"| {a}→{b} | {n['unchanged']} | {n['tweak']} | {n['jump']} | {n['rewrite']} | {100*med:.1f} |")
        for t,v in c.items():
            if t in ra: rows.append(dict(tr=a+b,team=t,**v,prev=R[a][t]['avg'],d=R[b][t]['avg']-R[a][t]['avg'],rprev=ra[t],dr=ra[t]-rb[t],final=rank[t]))
    json.dump(rows,open('out/q1_rows.json','w'))
    cl=('unchanged','tweak','jump','rewrite')
    print("\n## Q1b by final standing (team-transitions, 5 per team)")
    print("| final rank | team-transitions | unchanged | tweak | jump | rewrite-scale | mean RMS change (pp) |")
    print("|---|---|---|---|---|---|---|")
    for nm,lo,hi in (("1-5",1,5),("6-20",6,20),("21-60",21,60),("61-100",61,100),("101-127",101,127)):
        x=[r for r in rows if lo<=r['final']<=hi]
        print(f"| {nm} | {len(x)} | "+" | ".join(f"{sum(r['cls']==k for r in x)/len(x):.0%}" for k in cl)+f" | {100*np.mean([r['rmsx'] for r in x]):.1f} |")
    print("\nby rank in the round just played (rank in round n → change before n+1):")
    for nm,lo,hi in (("1-5",1,5),("6-20",6,20),("21-60",21,60),("61-100",61,100),("101-127",101,127)):
        x=[r for r in rows if lo<=r['rprev']<=hi]
        print(f"| {nm} | {len(x)} | "+" | ".join(f"{sum(r['cls']==k for r in x)/len(x):.0%}" for k in cl)+f" | {100*np.mean([r['rmsx'] for r in x]):.1f} |")
    # did changes help
    prev=np.array([r['prev'] for r in rows]); d=np.array([r['d'] for r in rows]); 
    # expected change given previous score, fitted on all (regression to the mean)
    sl,ic=np.polyfit(prev,d,1); res=d-(sl*prev+ic)
    print(f"\nregression to the mean: Δscore = {ic:.2f} + {sl:.3f}×prev score (all {len(rows)} team-transitions); sd of Δscore {d.std():.2f}")
    print("\n## Q1c did changes help? (official scores; SE of one team's Δscore ≈ 0.21)")
    print("| class | n | mean Δscore | mean Δscore adjusted for previous score | SE | SD of Δscore | share improved | mean Δrank (+ = up) | share gaining 5+ places | share losing 5+ places |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for k in cl:
        ix=np.array([r['cls']==k for r in rows]); dr=np.array([r['dr'] for r in rows])[ix]
        print(f"| {k} | {ix.sum()} | {d[ix].mean():+.2f} | {res[ix].mean():+.2f} | {res[ix].std()/math.sqrt(ix.sum()):.2f} | {d[ix].std():.2f} | {np.mean(d[ix]>0):.0%} | {dr.mean():+.1f} | {np.mean(dr>=5):.0%} | {np.mean(dr<=-5):.0%} |")
    rm=np.array([r['rmsx'] for r in rows])
    print(f"\ncorr(size of behaviour change, Δscore) = {np.corrcoef(rm,d)[0,1]:+.2f}; with adjusted Δscore {np.corrcoef(rm,res)[0,1]:+.2f}; with |Δscore| {np.corrcoef(rm,np.abs(d))[0,1]:+.2f}; with |Δrank| {np.corrcoef(rm,np.abs([r['dr'] for r in rows]))[0,1]:+.2f}")
    print("by size of change (RMS pp):")
    for lo,hi in ((0,.01),(.01,.02),(.02,.04),(.04,.08),(.08,.15),(.15,1)):
        ix=(rm>=lo)&(rm<hi)
        if ix.sum(): print(f"| {100*lo:.0f}-{100*hi:.0f} pp | {ix.sum()} | mean Δ {d[ix].mean():+.2f} | adj {res[ix].mean():+.2f} ± {res[ix].std()/math.sqrt(ix.sum()):.2f} | SD {d[ix].std():.2f} | improved {np.mean(d[ix]>0):.0%} | P(Δ>+1) {np.mean(d[ix]>1):.0%} | P(Δ<-1) {np.mean(d[ix]<-1):.0%} |")
    print("\nby tier and class: mean adjusted Δscore (n)")
    for nm,lo,hi in (("top 20 in round n",1,20),("21-60",21,60),("61-127",61,127)):
        s=[]
        for k in cl:
            ix=np.array([r['cls']==k and lo<=r['rprev']<=hi for r in rows])
            s.append(f"{k} {d[ix].mean():+.2f} raw / {res[ix].mean():+.2f} adj (n={ix.sum()})" if ix.sum() else f"{k} -")
        print(f"  {nm}: "+"; ".join(s))
    print("\nby transition: unchanged teams' mean Δscore (what standing still cost):")
    for a,b in TR:
        ix=np.array([r['cls']=='unchanged' and r['tr']==a+b for r in rows]); iy=np.array([r['cls']!='unchanged' and r['tr']==a+b for r in rows])
        print(f"  {a}→{b}: unchanged n={ix.sum()} mean Δ {d[ix].mean():+.2f} (SD {d[ix].std():.2f}); changers n={iy.sum()} mean Δ {d[iy].mean():+.2f} (SD {d[iy].std():.2f})")
    # top 20 detail
    print("\n## top-20 teams: class per transition and score per round")
    TRn=[a+b for a,b in TR]
    print("| rank | team | R1→R2 | R2→R3 | R3→R4 | R4→R5 | R5→R6 | scores R1..R6 |")
    print("|---|---|---|---|---|---|---|---|")
    for r_,t,_ in S[:20]:
        cells=[]
        for tr in TRn:
            x=[r for r in rows if r['team']==t and r['tr']==tr]
            cells.append(f"{x[0]['cls']} ({100*x[0]['rmsx']:.0f}pp, {x[0]['d']:+.1f})" if x else "avalon" if t=='avalon' else "-")
        print(f"| {r_} | {t} | "+" | ".join(cells)+" | "+" ".join(f"{R[l][t]['avg']:.1f}" for l in SCORED)+" |")
    # number of changes per team
    nch={}
    for r in rows: nch.setdefault(r['team'],[]).append(r['cls']!='unchanged')
    k=np.array([sum(v) for v in nch.values()]); print("\nnumber of the 5 gaps in which a team changed its bot:",{i:int((k==i).sum()) for i in range(6)})
    fin=np.array([rank[t] for t in nch]); print("corr(number of changes, final rank) =",round(float(np.corrcoef(k,fin)[0,1]),2))
    for i in range(6):
        if (k==i).sum(): print(f"  changed {i}x: n={int((k==i).sum())}, median final rank {np.median(fin[k==i]):.0f}")
