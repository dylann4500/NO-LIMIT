import pickle, numpy as np, sys, math, json
sys.path.insert(0,'.')
from common import *
from q3a import bh, pz
KIND = sys.argv[1] if len(sys.argv)>1 else "bay"
LABS = sys.argv[2].split(",") if len(sys.argv)>2 else SCORED
per=pickle.load(open(f'out/q4_{KIND}.pkl','rb'))
try:
    S=standings(); rank={t:r for r,t,_ in S}
except Exception: rank={}
if KIND!="bay": rank={}
METS=["open","3bet","f3b","calljam","btc1","btc2","fold1","fold2","fold3"]
DES={"a":"last third vs first third of the table; same players-left and own-stack(bb) bucket (blind level not controlled)",
     "b":"adjacent thirds within the same blind level, players-left and stack bucket (blind level controlled; identified by table length)",
     "c":"second half vs first half of each 20-hand blind level; same level, third, players-left, stack bucket"}
out={}
for des in "abc":
    print(f"\n### design {des}: {DES[des]}")
    print("| tendency | teams | field median drift (pp) | IQR | share of teams |z|>3 | teams with BH q<0.01 drift different from the field median and |dev|>=3pp |")
    print("|---|---|---|---|---|---|")
    for m in METS:
        pooled=[]
        teams=sorted({k[2] for k in per if k[1]==des and k[3]==m})
        for t in teams:
            if t=='avalon' and KIND=='bay': continue
            rr=[(l,per.get((l,des,t,m))) for l in LABS]; rr=[(l,r) for l,r in rr if r and r[0]!=0 and r[2]>=200]
            if not rr: continue
            se=np.array([abs(r[1]/r[0]) for _,r in rr]); e=np.array([r[1] for _,r in rr]); w=1/se**2
            pooled.append(dict(team=t,eff=100*(w*e).sum()/w.sum(),se=100/math.sqrt(w.sum()),byr={l:round(100*r[1],1) for l,r in rr},n=sum(r[2] for _,r in rr)))
        if not pooled: continue
        d=np.array([p['eff'] for p in pooled]); med=np.median(d)
        for p in pooled: p['z']=p['eff']/p['se']; p['zdev']=(p['eff']-med)/p['se']
        q=bh([pz(p['zdev']) for p in pooled])
        sig=[p for p,qq in zip(pooled,q) if qq<0.01 and abs(p['eff']-med)>=3]
        out[(des,m)]=(med,pooled,sig)
        print(f"| {m} | {len(pooled)} | {med:+.1f} | {np.percentile(d,25):+.1f}..{np.percentile(d,75):+.1f} | {np.mean(np.abs([p['z'] for p in pooled])>3):.0%} | {len(sig)} |")
# teams flagged consistently
print("\n### teams whose drift differs from the field's in design a AND design b (same sign), by tendency")
print("| tendency | team | final rank | drift a (pp) | field median a | drift b (pp) | field median b | drift c (pp) | drift a by round |")
print("|---|---|---|---|---|---|---|---|---|")
for m in METS:
    if ("a",m) not in out or ("b",m) not in out: continue
    ma,pa,sa=out[("a",m)]; mb,pb,sb=out[("b",m)]; mc,pc,sc=out.get(("c",m),(0,[],[]))
    db={p['team']:p for p in pb}; dc={p['team']:p for p in pc}
    for p in sorted(sa,key=lambda p:-abs(p['eff']-ma)):
        b=db.get(p['team'])
        if b and (b['eff']-mb)*(p['eff']-ma)>0 and abs(b['zdev'])>3:
            c=dc.get(p['team'])
            print(f"| {m} | {p['team']} | {rank.get(p['team'],'')} | {p['eff']:+.1f} | {ma:+.1f} | {b['eff']:+.1f} | {mb:+.1f} | {(c['eff'] if c else float('nan')):+.1f} | {p['byr']} |")
pickle.dump(out,open(f'out/q4b_{KIND}.pkl','wb'))
