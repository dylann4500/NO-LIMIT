"""Independent check: heads-up fold rate on a seat's first decision facing a bet, per street, by team."""
import gzip, json, sys, collections
f=gzip.open(sys.argv[1],'rt'); hdr=json.loads(f.readline()); you=hdr['you']
name={e['entry_id']:e['team_name'] for e in hdr['entries']}
want={'avalon','2 Curry','thepastaway','Lemonade','Team 82'}
N=collections.Counter(); F=collections.Counter()
for line in f:
    t=json.loads(line)
    if 'hands' not in t: continue
    seats=t['seats']
    for h in t['hands']:
        sb=h['stacks_before']; folded=set(); street=0
        raised_this=set(); facing_by=None; done=set()
        for e in h['events']:
            k,s=e['kind'],e.get('seat')
            if k=='board':
                street+=1; raised_this=set(); facing_by=None; done=set(); continue
            if street==0 or s is None or k not in ('fold','call','raise','check'):
                if k=='fold' and s is not None: folded.add(s)
                continue
            if facing_by is not None and s!=facing_by and s not in raised_this and s not in done:
                live=sum(1 for i in range(8) if sb[i]>0 and i not in folded)
                done.add(s)
                if live==2:
                    team=name.get(seats[s],'?'); key=team if team in want else 'field'
                    N[key,street]+=1; F[key,street]+= k=='fold'
                    if key!='field': N['field',street]+=0
            if k=='fold': folded.add(s)
            if k=='raise':
                if not raised_this: facing_by=s
                raised_this.add(s); facing_by=s
for key in ['avalon','2 Curry','thepastaway','Lemonade','Team 82','field']:
    print(f"{key:12s}", '  '.join(f"st{st}: {F[key,st]/max(1,N[key,st]):.0%} (n={N[key,st]})" for st in (1,2,3)))
