import json, numpy as np, sys, math
sys.path.insert(0,'.')
from common import *
from q3a import bh, pz
KIND = sys.argv[1] if len(sys.argv)>1 else "bay"
rank={}
if KIND=="bay":
    S=standings(); rank={t:r for r,t,_ in S}
res=json.load(open(f'out/q3b2_{KIND}.json'))
DESC={"tb:f3b_hist":("re-raise more against an opener who has folded to re-raises at this table",+1),
      "tb:open_hist":("re-raise more against an opener who has opened often at this table",+1),
      "steal:bbfold_hist":("open SB/BTN more when the big blind has folded to opens at this table",+1),
      "btc:fold_hist":("bet when checked to (heads-up) more against a seat that has folded to bets at this table",+1),
      "fb:bet_hist":("fold less to a bet (heads-up) from a seat that has bet often at this table",-1),
      "cj:jam_hist":("call a shove more from a seat that has shoved often at this table",+1)}
own = "avalon" if KIND=="bay" else None
print("effect = change in the action's probability (pp) per +10pp deviation of the faced seat's in-table rate from its team's norm (shrunk with 4 pseudo-observations); controls: the seat's team norm, rest-of-table history, blind level, players left, own and faced-seat stack buckets, who covers, situation dummies")
print("| test | teams | field median effect (pp) | share of team-rounds |z|>3 | placebo: rest-of-table |z|>3 | teams: q<0.01, expected sign, |effect|>=1pp and >=1pp beyond field median |")
print("|---|---|---|---|---|---|")
pooled={}
for test,(desc,sign) in DESC.items():
    x=[r for r in res if r['test']==test and r['se']>0 and r['team']!=own]
    if not x: continue
    z=np.array([r['b']/r['se'] for r in x]); zo=np.array([r['b_o']/r['se_o'] for r in x if r['se_o']])
    pl=[]
    for t in sorted({r['team'] for r in x}):
        rr=[r for r in x if r['team']==t]; w=np.array([1/r['se']**2 for r in rr]); b=np.array([r['b'] for r in rr])
        bp=(w*b).sum()/w.sum(); sp=1/math.sqrt(w.sum()); pbar=np.mean([r['p'] for r in rr])
        pl.append(dict(team=t,test=test,z=bp/sp,eff=100*bp*pbar*(1-pbar)*0.10,n=sum(r['n'] for r in rr),p=pbar,
                       byr={r['round'][:8]:round(100*r['b']*r['p']*(1-r['p'])*0.1,1) for r in rr}))
    med=np.median([p['eff'] for p in pl])
    q=bh([pz(p['z']) for p in pl])
    for p,qq in zip(pl,q): p['q']=float(qq); p['flag']= bool(qq<0.01 and sign*p['eff']>=1.0 and sign*(p['eff']-med)>=1.0); p['strong']=bool(abs(p['z'])>=10 and sign*(p['eff']-med)>=3.0)
    pooled[test]=pl
    print(f"| {desc} | {len(pl)} | {med:+.2f} | {np.mean(np.abs(z)>3):.0%} | {np.mean(np.abs(zo)>3):.0%} | {sum(p['flag'] for p in pl)} |")
if own:
    print("\npositive control, avalon (its bots tracked each seat's raise frequency, fold-to-bet and bet frequency in memory):")
    for test in DESC:
        rr=[r for r in res if r['team']==own and r['test']==test]
        print(f"  {test}: "+", ".join(f"{r['round']} {100*r['b']*r['p']*(1-r['p'])*0.1:+.1f}pp (z {r['b']/r['se']:+.0f})" for r in rr))
print("\n| test | team | final rank | effect per +10pp (pp) | base rate | z | n | effect by round |")
print("|---|---|---|---|---|---|---|---|")
for test,(desc,sign) in DESC.items():
    for p in sorted(pooled.get(test,[]),key=lambda p:-sign*p['eff']):
        if p['flag']: print(f"| {test} | {p['team']} | {rank.get(p['team'],'')} | {p['eff']:+.1f} | {100*p['p']:.0f}% | {p['z']:+.0f} | {p['n']} | {p['byr']} |")
flag={}
for test,pl in pooled.items():
    for p in pl:
        if p['flag']: flag.setdefault(p['team'],[]).append(test.split(':')[1])
print("\nteams with at least one flagged seat-level response:",len(flag),"of",len({p['team'] for pl in pooled.values() for p in pl}))
if rank:
    for nm,lo,hi in (("top 5",1,5),("6-20",6,20),("21-60",21,60),("61+",61,200)):
        tt=[t for t in rank if lo<=rank[t]<=hi and t!=own and any(p['team']==t for pl in pooled.values() for p in pl)]
        print(f"  {nm}: {sum(t in flag for t in tt)} of {len(tt)} teams; with 2+ kinds: {sum(len(flag.get(t,[]))>=2 for t in tt)}")
    print({t:(rank[t],v) for t,v in sorted(flag.items(),key=lambda kv:rank.get(kv[0],999))})
else:
    print(flag)
json.dump(pooled,open(f'out/q3b2_pooled_{KIND}.json','w'))
strong={}
for test,pl in pooled.items():
    for p in pl:
        if p.get('strong'): strong.setdefault(p['team'],[]).append(test.split(':')[1])
print("\nSTRONG flags (|z|>=10 and effect >=3pp beyond the field median):",len(strong),"teams")
if rank:
    for nm,lo,hi in (("top 5",1,5),("6-20",6,20),("21-60",21,60),("61+",61,200)):
        tt=[t for t in rank if lo<=rank[t]<=hi and t!=own and any(p['team']==t for pl in pooled.values() for p in pl)]
        print(f"  {nm}: {sum(t in strong for t in tt)} of {len(tt)} teams")
    print({t:(rank[t],v) for t,v in sorted(strong.items(),key=lambda kv:rank.get(kv[0],999))})
else: print(strong)
# diffusion by round
print("\nby round: number of teams with a per-round effect >=3pp (expected sign) and |z|>=6")
rounds=sorted({r['round'] for r in res}, key=lambda x: (SCORED.index(x) if x in SCORED else 0)) if KIND=="bay" else None
if KIND!="bay":
    rounds=["690def26","de7ac5d3","188fa79b","516b7309","b009537f","3425f351"]
for test,(desc,sign) in DESC.items():
    cnt=[]
    for l in rounds:
        cnt.append(sum(1 for r in res if r['test']==test and r['round']==l and r['team']!=own and r['se']>0 and abs(r['b']/r['se'])>=6 and sign*100*r['b']*r['p']*(1-r['p'])*0.1>=3))
    print(f"  {test}: "+" ".join(map(str,cnt)))
