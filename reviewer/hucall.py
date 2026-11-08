import gzip, json, sys
for path in sys.argv[1:]:
    f=gzip.open(path,'rt'); you=json.loads(f.readline())['you']; c=n=0
    for line in f:
        t=json.loads(line)
        if 'hands' not in t or you not in t['seats']: continue
        me=t['seats'].index(you)
        for h in t['hands']:
            sb=h['stacks_before']; alive=sum(1 for x in sb if x>0)
            if alive>3 or sb[me]<=0: continue
            jam=None
            for e in h['events']:
                k,s=e['kind'],e.get('seat')
                if k=='board': break
                if k=='raise' and s is not None and s!=me and e['amount']>=sb[s] and jam is None: jam=s; continue
                if jam is not None and s==me and k in ('call','fold','raise'):
                    n+=1; c+= k!='fold'; break
    print(path[-12:], f"facing an all-in preflop with 2-3 alive: call {c}/{n} = {c/max(1,n):.0%}")
