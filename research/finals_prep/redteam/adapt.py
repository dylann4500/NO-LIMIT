import gzip,json,sys,collections
H='/Users/samuelchoi/NoLimit/NO-LIMIT/data/hands/hands-%s.jsonl.gz'
fid=sys.argv[1]; N=int(sys.argv[2])
f=gzip.open(H%fid,'rt'); h=json.loads(f.readline()); nm={e['entry_id']:e['team_name'] for e in h['entries']}
fillid=collections.Counter()
C=collections.defaultdict(lambda:[0,0])  # (group,handband,kbucket)->[folds,n]
nt=0
for line in f:
    t=json.loads(line)
    if 'seats' not in t: continue
    nt+=1
    if nt>N: break
    seats=t['seats']; fl=t['fillers']
    for i,x in enumerate(fl):
        if x: fillid[nm.get(seats[i],'NOT-AN-ENTRY:'+str(seats[i])[:8])]+=1
    names=[nm.get(s,'?') for s in seats]
    prior=[0]*len(seats); prior_open=[0]*len(seats)
    for hd in t['hands']:
        bb=hd['blinds'][1]; sb=hd['stacks_before']; alive=sum(1 for x in sb if x>0)
        nr=0; opener=None; tb=None; resp=None; tbamt=0
        for e in hd['events']:
            k=e['kind']
            if k=='board': break
            if k not in('fold','call','raise'): continue
            s=e['seat']
            if k=='raise':
                if nr==0: opener=s
                elif nr==1 and s!=opener: tb=s; tbamt=e['amount']
                elif nr==2 and s==opener and resp is None: resp='raise'
                nr+=1
            elif nr==2 and tb is not None and s==opener and resp is None: resp=k
            elif nr>=3: pass
        if tb is not None and resp is not None and alive>=6 and tbamt<0.5*sb[tb] and sb[opener]>=25*bb:
            hb='h1-30' if hd['hand']<=30 else ('h31-60' if hd['hand']<=60 else 'h61+')
            kb='k0' if prior[tb]==0 else('k1-2' if prior[tb]<=2 else('k3-5' if prior[tb]<=5 else 'k6+'))
            for g in ('ALL','3bettor=2 Curry' if names[tb]=='2 Curry' else None):
                if g:
                    c=C[(g,hb,kb)]; c[1]+=1; c[0]+= resp=='fold'
        if tb is not None: prior[tb]+=1
print('filler seat identities:',fillid.most_common(8))
for g in ('ALL','3bettor=2 Curry'):
    print(g)
    for hb in('h1-30','h31-60','h61+'):
        print('  ',hb,'  '.join(f"{kb}: {100*C[(g,hb,kb)][0]/C[(g,hb,kb)][1]:.1f}% (n={C[(g,hb,kb)][1]})" for kb in('k0','k1-2','k3-5','k6+') if C[(g,hb,kb)][1]>30))
