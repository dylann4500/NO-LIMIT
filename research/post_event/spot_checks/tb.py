"""Independent check: our first-in preflop raises, how often re-raised, our response; our pts at tables with a given team."""
import gzip, json, sys
f=gzip.open(sys.argv[1],'rt'); hdr=json.loads(f.readline()); you=hdr['you']
name={e['entry_id']:e['team_name'] for e in hdr['entries']}
target=[k for k,v in name.items() if v==sys.argv[2]][0]
opens=rr=rr_fold=0; pts=[]; pts_t=[]
for line in f:
    t=json.loads(line)
    if 'hands' not in t: continue
    me=t['seats'].index(you); last=None
    for h in t['hands']:
        sb=h['stacks_before']
        if sb[me]<=0: break
        last=h
        raised=False; opened=False; reraised=False
        for e in h['events']:
            k,s=e['kind'],e.get('seat')
            if k=='board': break
            if k=='raise':
                if s==me and not raised: opened=True; raised=True; opens+=1; continue
                if s==me and opened and reraised: break
                if s!=me:
                    if opened and not reraised: reraised=True; rr+=1
                    raised=True; continue
            if opened and reraised and s==me and k in ('fold','call','raise'):
                rr_fold+= k=='fold'; break
    p=last['equity_after'][me]; pts.append(p)
    if target in t['seats']: pts_t.append(p)
m=sum(pts)/len(pts); mt=sum(pts_t)/len(pts_t)
print(sys.argv[1][-22:], f"opens {opens} re-raised {rr/opens:.1%} we fold {rr_fold/rr:.1%} | {sys.argv[2]}: tables {len(pts_t)} our pts there {mt:.2f} vs avg {m:.2f} diff {mt-m:+.2f}")
