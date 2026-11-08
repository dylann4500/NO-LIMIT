"""Lower-card exposure rate (75% = least-leak v3b; 50% = v3/v4/v5) and automatic decisions. usage: python -I whichbot.py HANDS.gz"""
import gzip, json, sys
R="23456789TJQKA"
f=gzip.open(sys.argv[1],'rt'); you=json.loads(f.readline())['you']; lower=n=auto=0; pend={}
for line in f:
    t=json.loads(line)
    if 'you' in t:
        y=t['you']; auto+=len(y.get('automatic') or []); k=(y['iteration'],y['table'])
        if k in pend:
            hands,me=pend.pop(k); kept={e['hand']:e['cards'] for e in y['private_events'] if e['kind']=='kept'}
            for h in hands:
                kc=kept.get(h['hand'])
                if not kc or kc[0][0]==kc[1][0]: continue
                for e in h['events']:
                    if e['kind']=='reveal' and e.get('seat')==me and e.get('cards'):
                        c=e['cards'][0]; o=kc[0] if kc[1]==c else kc[1]; n+=1; lower+=R.index(c[0])<R.index(o[0])
    elif 'hands' in t and you in t['seats']: pend[(t['iteration'],t['table'])]=(t['hands'],t['seats'].index(you))
print(f"lower-card exposure {lower/max(1,n):.0%} (75%=v3b, 50%=v3/v4/v5); automatic decisions {auto}")
