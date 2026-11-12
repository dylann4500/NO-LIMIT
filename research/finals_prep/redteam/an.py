import pickle,sys,math
o=pickle.load(open(sys.argv[1],'rb'))
labs=list(o)
def r(s,a,b): return 100*s.get(a,0)/s[b] if s.get(b) else float('nan')
print('== field aggregates (non-filler, non-us), fillers, us')
print('rnd  teams  dead(<3%vpip) passive(pfr<5) | field VPIP PFR 3bet f3b foldbet | FILLER vpip pfr pts | us pts  us pts@fillertables/n')
for l in labs:
    S=o[l]['S']; T=[k for k in S if k not in('FILLER','avalon*','?')]
    agg={}
    for k in T:
        for a,b in S[k].items(): agg[a]=agg.get(a,0)+b
    act=[k for k in T if S[k].get('hands',0)>300]
    dead=sum(1 for k in act if r(S[k],'vpip','hands')<3); pas=sum(1 for k in act if r(S[k],'pfr','hands')<5)
    F=S.get('FILLER',{}); U=S['avalon*']
    print(f"{l:3} {len(act):5} {dead:6} {pas:8}      | {r(agg,'vpip','hands'):5.1f} {r(agg,'pfr','hands'):5.1f} {r(agg,'3b','3b_opp'):5.1f} {r(agg,'f3b','f3b_opp'):5.1f} {r(agg,'fb','fb_opp'):5.1f} | {r(F,'vpip','hands'):5.1f} {r(F,'pfr','hands'):5.1f} {F.get('pts',0)/max(F.get('tables',1),1):5.2f} | {U['pts']/U['tables']:5.2f}  {U.get('pts_f1',0)/max(U.get('tab_f1',1),1):5.2f}/{U.get('tab_f1',0)}  nofill {U.get('pts_f0',0)/max(U.get('tab_f0',1),1):5.2f}")
# per-team change: practice vs neighbours
def vec(S,sz,k):
    s=S[k]; z=sz.get(k,{}); tot=sum(z.values())
    mode=max(z,key=z.get) if z else None
    return dict(h=s.get('hands',0),vpip=r(s,'vpip','hands'),pfr=r(s,'pfr','hands'),tb=r(s,'3b','3b_opp'),mode=mode,modeshare=(z[mode]/tot if tot else 0),jam=r(s,'openjam','open'))
def changed(a,b):
    # bot-change proxy: PFR moved >4 pts (≈4+ SE) or VPIP >5 or modal open size changed with both shares>.4
    if a['h']<1500 or b['h']<1500: return None
    c=abs(a['pfr']-b['pfr'])>4 or abs(a['vpip']-b['vpip'])>5 or (a['mode']!=b['mode'] and a['modeshare']>.4 and b['modeshare']>.4)
    return c
# top teams by mean scored points
pts={}
for l in labs:
    if l[0]=='R':
        for k,s in o[l]['S'].items(): pts.setdefault(k,[]).append(s['pts']/s['tables'])
top=sorted([k for k in pts if len(pts[k])==6 and k not in('FILLER','avalon*')],key=lambda k:-sum(pts[k]))[:20]
print('\n== share of teams whose bot changed (proxy), all teams with >=1500 hands / top20')
seq=labs
for i in range(len(seq)-1):
    a,b=seq[i],seq[i+1]
    for name,grp in (('all',[k for k in o[a]['S'] if k in o[b]['S'] and k not in('FILLER','avalon*')]),('top20',top)):
        res=[changed(vec(o[a]['S'],o[a]['sizes'],k),vec(o[b]['S'],o[b]['sizes'],k)) for k in grp if k in o[a]['S'] and k in o[b]['S']]
        res=[x for x in res if x is not None]
        print(f"{a}->{b} {name:5} n={len(res):3} changed={100*sum(res)/max(len(res),1):5.1f}%",end='   ')
    print()
print('\n== scored->scored skipping practice')
R=[l for l in labs if l[0]=='R']
for a,b in zip(R,R[1:]):
    for name,grp in (('all',[k for k in o[a]['S'] if k in o[b]['S'] and k not in('FILLER','avalon*')]),('top20',top)):
        res=[changed(vec(o[a]['S'],o[a]['sizes'],k),vec(o[b]['S'],o[b]['sizes'],k)) for k in grp if k in o[a]['S'] and k in o[b]['S']]
        res=[x for x in res if x is not None]
        print(f"{a}->{b} {name:5} n={len(res):3} changed={100*sum(res)/max(len(res),1):5.1f}%",end='   ')
    print()
print('\n== challenger signature: practice differs from BOTH neighbours while neighbours match each other; and "practice=preview of next" (P!=prev, P==next)')
for (a,p,b) in (('R2','P6','R3'),('R3','P7','R4'),('R4','P8','R5'),('R5','P9','R6')):
    for name,grp in (('all',[k for k in o[a]['S'] if k not in('FILLER','avalon*')]),('top20',top)):
        c=dict(same=0,preview=0,late=0,chall=0,three=0,n=0)
        for k in grp:
            if not(k in o[a]['S'] and k in o[p]['S'] and k in o[b]['S']): continue
            va,vp,vb=[vec(o[x]['S'],o[x]['sizes'],k) for x in (a,p,b)]
            ap,pb,ab=changed(va,vp),changed(vp,vb),changed(va,vb)
            if None in(ap,pb,ab): continue
            c['n']+=1
            if not ap and not pb: c['same']+=1
            elif ap and not pb: c['preview']+=1
            elif not ap and pb: c['late']+=1
            elif not ab: c['chall']+=1
            else: c['three']+=1
        print(a,p,b,name,c,end='  ')
    print()
print('\ntop20:',top)
print('\n== top-20 PFR by round'); print('team'.ljust(24),' '.join(l.rjust(5) for l in labs))
for k in top[:20]:
    print(k[:23].ljust(24),' '.join((f"{vec(o[l]['S'],o[l]['sizes'],k)['pfr']:5.1f}" if k in o[l]['S'] else '   - ') for l in labs))
print('\n== top-20 modal open size'); 
for k in top[:20]:
    print(k[:23].ljust(24),' '.join((f"{str(vec(o[l]['S'],o[l]['sizes'],k)['mode']):>5}" if k in o[l]['S'] else '   - ') for l in labs))
