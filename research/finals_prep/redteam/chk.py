import gzip,json,sys,pickle,collections
H='/Users/samuelchoi/NoLimit/NO-LIMIT/data/hands/hands-%s.jsonl.gz'
FILES=[('P1','5da6d631-2bcf-4fe2-9e7a-01b9e8ecac75'),('P2','af2a0969-cd0a-4124-875b-84ff690a2a6d'),('P3','bd8406dc-0f95-4cd3-8015-7ef8acf3898c'),('P4','4d1fe6fb-7336-4745-bfb4-cd0e565fb552'),('R1','3e3dcc02-ca4f-48c5-9acb-6c0e3a32c10e'),('R2','547666b1-3877-4bac-9925-17e1e78134da'),('P6','74eb2fd7-8ade-46fb-8e6a-6a099170b812'),('R3','260d2303-7878-4df1-867e-05f8d2a10d01'),('P7','4acb36cf-7869-47d6-b4e7-e5de8e634956'),('R4','250d256c-6794-4e24-957e-c258286fc25b'),('P8','925e7be1-31e3-4101-af96-fcb2f78bad37'),('R5','2390e159-4598-4771-a21c-3326b7a18e68'),('P9','13040f56-85d7-4be5-9421-d929abd48da8'),('R6','729b67f6-dc91-4a48-9ad7-f5f62fb79941')]
N=int(sys.argv[1]) if len(sys.argv)>1 else 1000
out={}
for lab,fid in FILES:
    f=gzip.open(H%fid,'rt'); h=json.loads(f.readline()); nm={e['entry_id']:e['team_name'] for e in h['entries']}; you=h['you']
    S=collections.defaultdict(lambda: collections.Counter()); sizes=collections.defaultdict(collections.Counter)
    nt=0; nfill=collections.Counter()
    for line in f:
        t=json.loads(line)
        if 'you' in t and 'seats' not in t: continue
        nt+=1
        if nt>N: break
        seats=t['seats']; fl=t['fillers']; nfill[sum(fl)]+=1
        names=['FILLER' if fl[i] else ('avalon*' if seats[i]==you else nm.get(seats[i],'?')) for i in range(len(seats))]
        hands=t['hands']
        last=hands[-1]['equity_after']
        for i,n in enumerate(names):
            S[n]['tables']+=1; S[n]['pts']+=last[i]
            S[n]['pts_f%d'%min(sum(fl),1)]+=last[i]; S[n]['tab_f%d'%min(sum(fl),1)]+=1
        for hd in hands:
            bb=hd['blinds'][1]; sb=hd['stacks_before']
            nr=0; acted=set(); vp=set(); pf=set(); lastraiser=None; opener=None
            for e in hd['events']:
                k=e['kind']
                if k=='board': break
                if k not in('fold','call','raise','check'): continue
                s=e['seat']; n=names[s]
                if s not in acted:
                    acted.add(s); S[n]['hands']+=1
                if nr==0 and k in('fold','call','raise'): 
                    if not any(True for _ in vp): pass
                if nr==1 and s!=lastraiser:
                    S[n]['3b_opp']+=1
                    if k=='raise': S[n]['3b']+=1
                if nr==2 and s==opener:
                    S[n]['f3b_opp']+=1
                    if k=='fold': S[n]['f3b']+=1
                if k=='call': vp.add(s)
                if k=='raise':
                    vp.add(s); pf.add(s)
                    if nr==0:
                        opener=s
                        if e['amount']>=sb[s]*0.9: S[n]['openjam']+=1
                        else: sizes[n][round(e['amount']/bb,1)]+=1
                        S[n]['open']+=1
                    nr+=1; lastraiser=s
            for s in vp: S[names[s]]['vpip']+=1
            for s in pf: S[names[s]]['pfr']+=1
            # postflop fold to bet (any)
            post=False; bet=False
            for e in hd['events']:
                k=e['kind']
                if k=='board': post=True; bet=False; continue
                if not post or k not in('fold','call','raise','check'): continue
                n=names[e['seat']]
                if bet:
                    S[n]['fb_opp']+=1
                    if k=='fold': S[n]['fb']+=1
                if k=='raise': bet=True
    out[lab]={'S':{k:dict(v) for k,v in S.items()},'sizes':{k:dict(v) for k,v in sizes.items()},'nfill':dict(nfill),'nt':nt-1 if nt>N else nt}
    print(lab,'tables',out[lab]['nt'],'fillers/table dist',dict(nfill),file=sys.stderr)
pickle.dump(out,open(sys.argv[2],'wb'))
