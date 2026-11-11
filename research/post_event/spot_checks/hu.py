import gzip, json, sys, collections
f=gzip.open(sys.argv[1],'rt'); you=json.loads(f.readline())['you']
c=collections.Counter(); shown=0; nt=0
for line in f:
    t=json.loads(line)
    if 'hands' not in t: continue
    nt+=1
    if nt>3000: break
    me=t['seats'].index(you)
    for h in t['hands']:
        sb=h['stacks_before']
        if sb[me]<=0: break
        ev=h['events']; folded=set(); street=0; facing=False
        for e in ev:
            k,s=e['kind'],e.get('seat')
            if k=='board':
                street+=1; facing=False
                if street>1: break
                continue
            if k=='fold': folded.add(s)
            if street!=1: continue
            if k=='raise' and s!=me: facing=True; continue
            if s==me and k in ('call','fold','raise','check'):
                if facing:
                    live=[i for i in range(8) if sb[i]>0 and i not in folded]
                    # NOTE: our own fold is already in folded when k=='fold'
                    key='HU' if len(live)-(1 if k=='fold' else 0)==2 else 'multi'
                    c[key,k]+=1
                    if key=='HU' and shown<3 and k=='fold': shown+=1; print([ (e['kind'],e.get('seat'),e.get('amount')) for e in ev][:30], 'me',me)
                    break
for key in ('HU','multi'):
    n=sum(v for (a,b),v in c.items() if a==key); fo=c[key,'fold']
    print(key, n, f"fold {fo/n:.1%}")
