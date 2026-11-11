"""Offline equity asset builder. Not used during decisions."""
import eval7
import json
import os
import random
import time

RANKS = '23456789TJQKA'
SUITS = 'cdhs'
CARDS = [eval7.Card(r+s) for r in RANKS for s in SUITS]
WIDTHS = [0.015, 0.03, 0.05, 0.08, 0.12, 0.18, 0.25, 0.35, 0.5, 0.7, 1.0]


def key(a, b):
    x, y = sorted((RANKS.index(a[0]), RANKS.index(b[0])), reverse=True)
    return RANKS[x]+RANKS[y]+('' if x == y else ('s' if a[1] == b[1] else 'o'))


def build():
    start=time.perf_counter()
    groups={}
    for i, a in enumerate(CARDS):
        for b in CARDS[:i]:
            groups.setdefault(key(str(a),str(b)), []).append(((a,b),1.0))
    random_range=[c for cs in groups.values() for c in cs]
    reps={k:list(v[0][0]) for k,v in groups.items()}
    raw={k:eval7.py_hand_vs_range_monte_carlo(h,random_range,[],100000) for k,h in reps.items()}
    def score(k):
        a,b=RANKS.index(k[0]),RANKS.index(k[1])
        return raw[k]+(0.025 if len(k)==2 else (0.019 if k[-1]=='s' else 0))+(0.012 if 0<a-b<=2 else 0)
    # The ordering of playable opening hands differs from raw heads-up equity:
    # AK blocks premium continuations; small pairs need substantial implied odds.
    priority='AA KK QQ AKs JJ AKo TT AQs AQo AJs KQs 99 ATs KJs AJo 88 KQo ATo QJs KTs 77 A9s QTs KJo JTs A8s 66 A5s A4s A7s A6s K9s QJo KTo 55 A3s A2s Q9s J9s T9s K8s A9o 44 K7s A8o Q8s J8s 98s K6s A7o T8s K9o QTo 33 K5s A6o Q7s 87s K4s JTo A5o 22'.split()
    order=priority+[k for k in sorted(groups,key=score,reverse=True) if k not in priority]
    pct={};n=0
    for k in order:
        pct[k]=(n+len(groups[k])/2)/1326
        n+=len(groups[k])
    ranges=[[c for k in order if pct[k]<=w for c in groups[k]] for w in WIDTHS]
    eq={k:[round(eval7.py_hand_vs_range_monte_carlo(reps[k],r,[],80000),5) for r in ranges] for k in order}
    # Nested, genuinely multiway simulations preserve the correlation between
    # winning against different hands (especially sets and suited connectors).
    rng=random.Random(584012)
    multi={}
    for k in order:
        hero=reps[k]
        deck=[c for c in CARDS if c not in hero]
        totals=[0.0]*7
        for _ in range(8000):
            sample=rng.sample(deck,19)
            board=sample[:5]
            hv=eval7.evaluate(hero+board)
            best=hv;ties=1
            for j in range(7):
                v=eval7.evaluate(sample[5+2*j:7+2*j]+board)
                if v>best:best=v;ties=1
                elif v==best:ties+=1
                if best==hv:totals[j]+=1.0/ties
                else:break
        multi[k]=[round(t/8000,5) for t in totals]
    out={'widths':WIDTHS,'percentile':pct,'equity':eq,'multiway':multi}
    path=os.path.join(os.path.dirname(__file__),'equity.json')
    with open(path,'w') as f:json.dump(out,f,separators=(',',':'))
    print('Built',path,'in',round(time.perf_counter()-start,2),'seconds')

if __name__=='__main__':build()
