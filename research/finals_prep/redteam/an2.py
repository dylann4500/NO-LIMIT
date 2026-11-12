import pickle,sys,math
o=pickle.load(open(sys.argv[1],'rb'))
R=['R1','R2','R3','R4','R5','R6']
def rank(v):
    s=sorted(range(len(v)),key=lambda i:v[i]); r=[0]*len(v)
    for j,i in enumerate(s): r[i]=j
    return r
def corr(a,b):
    n=len(a); ma=sum(a)/n; mb=sum(b)/n
    c=sum((x-ma)*(y-mb) for x,y in zip(a,b)); va=sum((x-ma)**2 for x in a); vb=sum((y-mb)**2 for y in b)
    return c/math.sqrt(va*vb) if va*vb>0 else float('nan')
teams=[k for k in o['R1']['S'] if k not in('FILLER','?') and all(k in o[r]['S'] and o[r]['S'][k]['tables']>300 for r in R)]
P={k:[o[r]['S'][k]['pts']/o[r]['S'][k]['tables'] for r in R] for k in teams}
ntab={k:o['R1']['S'][k]['tables'] for k in teams}
tot={k:sum(P[k]) for k in teams}
top=sorted(teams,key=lambda k:-tot[k])[:20]
print('teams',len(teams),'median tables/team/round',sorted(ntab.values())[len(ntab)//2])
for name,g in (('all',teams),('top20 by total',top)):
    print(name,'SD of true-ish points (R-mean):',round((sum((tot[k]/6-sum(tot[x] for x in g)/6/len(g))**2 for k in g)/len(g))**.5,2))
    print('  spearman consecutive:',[round(corr(rank([P[k][i] for k in g]),rank([P[k][i+1] for k in g])),2) for i in range(5)])
# top20 chosen by R1 only (no selection on later rounds)
top1=sorted(teams,key=lambda k:-P[k][0])[:20]
print('top20 by R1 alone: spearman R2-R3..R5-R6:',[round(corr(rank([P[k][i] for k in top1]),rank([P[k][i+1] for k in top1])),2) for i in range(1,5)])
print('top20 by total, pts by round:'); 
for k in top: print('  ',k[:22].ljust(23),' '.join(f'{x:5.1f}' for x in P[k]))
# rank moves in top20
for i in range(5):
    g=top; ra=rank([-P[k][i] for k in g]); rb=rank([-P[k][i+1] for k in g])
    mv=[abs(a-b) for a,b in zip(ra,rb)]
    print(f'R{i+1}->R{i+2} top20: mean |rank move| {sum(mv)/20:.1f}; in top3 both rounds: {sum(1 for a,b in zip(ra,rb) if a<3 and b<3)}/3')
# trend autocorrelation
def rate(s,a,b): return 100*s.get(a,0)/s[b] if s.get(b) else float('nan')
for a,b,lab in (('pfr','hands','PFR'),('3b','3b_opp','3bet'),('fb','fb_opp','fold-to-bet'),('f3b','f3b_opp','fold-to-3bet')):
    d1=[];d2=[]
    for k in teams:
        if k=='avalon*': continue
        v=[rate(o[r]['S'][k],a,b) for r in R]
        for i in range(4):
            x,y=v[i+1]-v[i],v[i+2]-v[i+1]
            if x==x and y==y: d1.append(x); d2.append(y)
    big=[(x,y) for x,y in zip(d1,d2) if abs(x)>3]
    same=sum(1 for x,y in big if x*y>0)
    print(f'{lab}: corr(change k, change k+1) = {corr(d1,d2):+.2f} (n={len(d1)}); after a move >3 pts, next move same direction {100*same/max(len(big),1):.0f}% (n={len(big)}), mean next move as share of move {sum(y/x for x,y in big)/max(len(big),1):+.2f}')
