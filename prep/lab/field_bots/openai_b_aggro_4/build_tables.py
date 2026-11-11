"""Offline, card-only preflop equity generation. Never run during decisions."""
import json, os, eval7
RANGES = [
 'AA,KK,QQ,AKs,AKo',
 '99+,AJs+,KQs,AQo+',
 '66+,A9s+,KTs+,QTs+,JTs,ATo+,KQo',
 '22+,A2s+,K9s+,Q9s+,J9s+,T9s,98s,87s,76s,ATo+,KJo+,QJo',
 '22+,A2s+,K5s+,Q7s+,J7s+,T7s+,97s+,86s+,75s+,65s,54s,A7o+,K9o+,Q9o+,J9o+,T9o',
 '22+,A2s+,K2s+,Q2s+,J4s+,T5s+,95s+,85s+,74s+,64s+,54s,53s,43s,A2o+,K5o+,Q7o+,J8o+,T8o+,98o,87o',
 '22+,A2s+,K2s+,Q2s+,J2s+,T2s+,92s+,82s+,72s+,62s+,52s+,42s+,32s,A2o+,K2o+,Q2o+,J2o+,T2o+,92o+,82o+,72o+,62o+,52o+,42o+,32o']
ranges=[eval7.HandRange(r).hands for r in RANGES]
ranks='23456789TJQKA'; out={}
for hi in range(13):
 for lo in range(hi+1):
  for suited in ([False] if hi==lo else [False,True]):
   key=ranks[hi]+ranks[lo]+('' if hi==lo else 's' if suited else 'o')
   cards=[eval7.Card(ranks[hi]+'s'),eval7.Card(ranks[lo]+('s' if suited else 'h'))]
   out[key]=[round(eval7.py_hand_vs_range_monte_carlo(cards,r,[],60000),5) for r in ranges]
# Percentile with card-combination weighting; mix domination resistance and raw equity.
ordered=sorted(out,key=lambda k:out[k][6]*.55+out[k][3]*.30+out[k][1]*.15,reverse=True)
acc=0
for k in ordered:
 w=6 if len(k)==2 else 4 if k[-1]=='s' else 12
 out[k].append((acc+w*.5)/1326); acc+=w
with open(os.path.join(os.path.dirname(__file__),'preflop.json'),'w') as f: json.dump({'ranges':RANGES,'hands':out},f,separators=(',',':'))
print('Built',len(out),'hands;',acc,'combinations')
