"""Independent spot-check: points/table, 2-3 alive call rate facing a preflop all-in, flop fold-to-bet (first decision facing a flop bet)."""
import gzip, json, sys, collections
path=sys.argv[1]
f=gzip.open(path,'rt'); hdr=json.loads(f.readline()); you=hdr['you']
pts=[]; kinds=collections.Counter()
fa=collections.Counter()  # alive -> [n, calls]
fc=collections.Counter()
f2b_n=f2b_f=0; hu_n=hu_f=0
for line in f:
    t=json.loads(line)
    if 'hands' not in t: continue
    if you not in t['seats']: continue
    me=t['seats'].index(you)
    last=None
    for h in t['hands']:
        if h['stacks_before'][me]<=0: break
        last=h
        sb=h['stacks_before']; alive=sum(1 for x in sb if x>0)
        ev=h['events']
        for e in ev: kinds[e['kind']]+=1
        # preflop all-in facing
        jam=None; street=0
        for e in ev:
            k,s=e['kind'],e.get('seat')
            if k=='board': break
            if k=='raise' and s!=me and jam is None and e['amount']>=sb[s]: jam=s; continue
            if jam is not None and s==me and k in ('call','fold','raise'):
                fa[alive]+=1; fc[alive]+= k!='fold'; break
        # flop: first decision facing a bet
        street=0; facing=False; done=False; inhand=set(i for i in range(8) if sb[i]>0); folded=set()
        for e in ev:
            k,s=e['kind'],e.get('seat')
            if k=='board':
                street+=1; facing=False
                if street>1: break
                continue
            if k=='fold' and s is not None: folded.add(s)
            if street!=1: continue
            if k in ('raise','bet') and s!=me: facing=True; continue
            if s==me and k in ('call','fold','raise','check','bet'):
                if facing:
                    live=[i for i in range(8) if sb[i]>0 and i not in folded]
                    f2b_n+=1; f2b_f+= k=='fold'
                    if len(live)==2: hu_n+=1; hu_f+= k=='fold'
                    break
    if last is not None: pts.append(last['equity_after'][me])
n2=fa[2]+fa[3]; c2=fc[2]+fc[3]
print(path[-20:], f"tables {len(pts)} pts/table {sum(pts)/len(pts):.3f} | facing preflop all-in: 2 alive {fc[2]}/{fa[2]}={fc[2]/fa[2]:.1%}, 3 alive {fc[3]/fa[3]:.1%}, 2-3 {c2}/{n2}={c2/n2:.1%} | flop F2B {f2b_f/f2b_n:.1%} (n={f2b_n}), HU {hu_f/hu_n:.1%}")
print('kinds', dict(kinds.most_common(14)))
