"""Offline preflop abstraction. Run with eval7 installed; not used at decision time."""
import eval7, json, itertools, pathlib
RANKS='23456789TJQKA'
CARDS={r+s:eval7.Card(r+s) for r in RANKS for s in 'cdhs'}
classes=[]
for i,a in enumerate(RANKS):
 for j in range(i+1):
  b=RANKS[j]
  classes.extend([a+b] if i==j else [a+b+'s',a+b+'o'])
allhands=list(itertools.combinations(CARDS.values(),2))
uniform=[(h,1.) for h in allhands]
tight=eval7.HandRange('88+,ATs+,KQs,AJo+').hands
raw={}; score={}
for h in classes:
 hero=[CARDS[h[0]+'c'],CARDS[h[1]+('c' if h.endswith('s') else 'd')]]
 a=eval7.py_hand_vs_range_monte_carlo(hero,uniform,[],150000)
 b=eval7.py_hand_vs_range_monte_carlo(hero,tight,[],100000)
 raw[h]=a
 # Ranking is an abstraction for ranges, not the value used for all-in decisions.
 gap=abs(RANKS.index(h[0])-RANKS.index(h[1]))
 score[h]=.72*a+.28*b+(.012 if h.endswith('s') else 0)+(.006 if gap==1 and h.endswith('s') else 0)
order=sorted(classes,key=score.get,reverse=True)
percent={}; combo=0
for h in order:
 n=6 if len(h)==2 else 4 if h[-1]=='s' else 12
 percent[h]=(combo+n*.5)/1326
 combo+=n
pcts=[.025,.04,.06,.085,.12,.16,.22,.30,.42,.60,.80,1.0]
ranges=[]
for p in pcts:
 ranges.append([(h,1.) for h in allhands if percent[str(h[0])[0]+str(h[1])[0]]<0] if False else None)
# Canonical high rank first.
def key(h):
 a,b=str(h[0]),str(h[1])
 if RANKS.index(a[0])<RANKS.index(b[0]): a,b=b,a
 return a[0]+b[0]+('' if a[0]==b[0] else 's' if a[1]==b[1] else 'o')
for i,p in enumerate(pcts):
 ranges[i]=[(h,1.) for h in allhands if percent[key(h)]<=p or key(h)=='AA']
equity={}
for n,h in enumerate(classes):
 hero=[CARDS[h[0]+'c'],CARDS[h[1]+('c' if h.endswith('s') else 'd')]]
 equity[h]=[round(eval7.py_hand_vs_range_monte_carlo(hero,r,[],120000),6) for r in ranges]
 if n%30==0: print(n,h,flush=True)
out={'percent':percent,'raw':raw,'pcts':pcts,'equity':equity,'order':order}
pathlib.Path(__file__).with_name('preflop.json').write_text(json.dumps(out,separators=(',',':')))
print('Top 15%', [h for h in order if percent[h]<.15])
