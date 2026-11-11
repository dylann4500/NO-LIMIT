"""Offline, reproducible preflop equity asset builder. Does not use the simulator."""
import eval7, json, os, random
R='23456789TJQKA'; S='cdhs'
D=[eval7.Card(r+s) for r in R for s in S]
classes={}
for i in range(13):
 for j in range(i+1):
  for suited in ([False] if i==j else [False,True]):
   key=R[i]+R[j]+('s' if suited else 'o') if i!=j else R[i]*2
   classes[key]=[D[4*i],D[4*j+(0 if suited else 1)]]
def key(a,b):
 i,j=a//4,b//4
 if j>i:i,j=j,i
 return R[i]+R[j]+('s' if a%4==b%4 else 'o') if i!=j else R[i]*2
combos=[(a,b,key(a,b)) for a in range(52) for b in range(a+1,52)]
full=[((D[a],D[b]),1.) for a,b,k in combos]
equity={k:eval7.py_hand_vs_range_monte_carlo(h,full,[],80000) for k,h in classes.items()}
score={}
for k,e in equity.items():
 hi=R.index(k[0])+2;lo=R.index(k[1])+2
 if hi==lo: bonus=.015 if hi<9 else .0
 else:
  suited=k[-1]=='s';gap=hi-lo
  bonus=(.022 if suited else -.016)+(.032 if suited and gap==1 else .019 if suited and gap==2 else .009 if suited and gap==3 else 0)
  if hi==14 and suited:bonus+=.009
  if hi==14 and lo<9 and not suited:bonus-=.018
 score[k]=e+bonus
# Opening / reraising ranges are not ordered by equity against random cards:
# AK is much more valuable against a continuing range than a medium pair.
prefix='AA KK QQ AKs AKo JJ TT AQs AQo 99 AJs KQs 88 ATs AJo KJs QJs KQo 77 KTs A9s QTs JTs 66 ATo A8s 55 KJo K9s A7s A5s T9s Q9s J9s A6s A4s 44 KTo QJo A3s 98s A2s A9o K8s Q8s J8s T8s 33 87s K7s A8o QTo JTo K6s'.split()
for i,k in enumerate(prefix):score[k]=2-i*.001
combos.sort(key=lambda x:score[x[2]],reverse=True)
fractions=[.025,.04,.06,.08,.10,.13,.17,.22,.28,.36,.46,.60,.78,1.]
ranges=[]
for f in fractions:
 ranges.append([((D[a],D[b]),1.) for a,b,k in combos[:max(6,int(1326*f))]])
rows={}
for k,h in classes.items():
 rows[k]={'e':equity[k],'s':score[k],'eq':[round(eval7.py_hand_vs_range_monte_carlo(h,r,[],50000),5) for r in ranges]}
# Percentiles include combo frequencies and retain standard suit symmetry.
for k,v in rows.items():v['p']=sum(1 for a,b,x in combos if score[x]>score[k])/1326
charts=[
 (.15,'66+,ATs+,KJs+,QJs,JTs,AJo+,KQo'),
 (.17,'55+,A8s+,KTs+,QTs+,JTs,T9s,AJo+,KQo'),
 (.20,'44+,A5s+,K9s+,Q9s+,J9s+,T9s,98s,ATo+,KJo+,QJo'),
 (.24,'33+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+,QTo+,JTo'),
 (.31,'22+,A2s+,K5s+,Q7s+,J8s+,T8s+,97s+,86s+,76s,65s,A7o+,KTo+,QTo+,JTo'),
 (.46,'22+,A2s+,K2s+,Q4s+,J6s+,T6s+,96s+,85s+,75s+,64s+,54s,A2o+,K7o+,Q8o+,J8o+,T8o+,98o'),
 (.54,'22+,A2s+,K2s+,Q2s+,J4s+,T5s+,95s+,85s+,74s+,64s+,53s+,43s,A2o+,K5o+,Q7o+,J8o+,T8o+,98o,87o')]
cardids={str(c):i for i,c in enumerate(D)}
for k,v in rows.items():v['open']=.78 if v['p']<.78 else .90+v['p']*.099
for f,chart in reversed(charts):
 for (a,b),weight in eval7.HandRange(chart).hands:
  k=key(cardids[str(a)],cardids[str(b)])
  rows[k]['open']=f-.0001
with open(os.path.join(os.path.dirname(__file__),'preflop.json'),'w') as f:json.dump({'fractions':fractions,'hands':rows},f,separators=(',',':'))
print('Built',len(rows),'classes;',len(combos),'combos')
