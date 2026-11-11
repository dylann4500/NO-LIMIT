import collections,json,eval7
from analyze import HANDS,ROOT
B=collections.defaultdict(collections.Counter)
for h in HANDS:
 n=len(h['stacks']); bb=h['blinds'][1];bets=collections.defaultdict(int);contrib=collections.defaultdict(int);street=0;raiser=None;raises=0;pot=0;board=[];acted=set();stacks={int(k):v for k,v in h['stacks'].items()};status={s:'active' for s in stacks};rev={e[1]:e[3] for e in h['events'] if e[0]=='show'}
 for k,s,amt,cs in h['events']:
  if k=='board':street+=len(cs);board+=cs;bets=collections.defaultdict(int);raises=0;raiser=None;acted=set()
  if k in ('fold','call','raise','check'):
   keys=['all',h['names'][str(s)],'n'+str(n),('early' if n>=5 else 'bubble' if n==4 else 'paid')]
   for key in keys:
    b=B[(key,street)];b['actions']+=1;b[k]+=1
    if raiser is not None:
     b['facing']+=1;b['facing_'+k]+=1
     if street==0 and raises==1:b['open_response_'+k]+=1
    elif k in ('check','raise'):
     b['free']+=1;b['free_'+k]+=1
   if k=='raise':
    if s in rev and street:
     hc=[eval7.Card(c) for c in rev[s]];bc=[eval7.Card(c) for c in board];rank=eval7.evaluate(hc+bc)>>24
     for key in keys:
      b=B[(key,street)];b['shown_bets']+=1;b['shown_cat'+str(rank)]+=1
      if raises:b['shown_reraises']+=1;b['shown_reraise_cat'+str(rank)]+=1
    if street==0 and raises==0:
     for key in keys:
      b=B[(key,street)];b['opens']+=1;b['open_bb_sum']+=amt/bb
    raises+=1;raiser=s
   if k=='fold':status[s]='folded'
  if k in ('blind','ante','call','raise'):
   add=amt-bets[s] if k=='raise' else amt;pot+=add;contrib[s]+=add
   if k!='ante':bets[s]+=add
   if contrib[s]>=stacks[s]:status[s]='all_in'
json.dump({str(k):dict(v) for k,v in B.items()},open(ROOT+'/field_stats.json','w'),indent=2)
for key in ('all','n8','n4','n3','n2','openai_a_default_1','ours','claude_default_b'):
 for st in (0,3,4,5):
  b=B[key,st];print(key,st,dict(b))
