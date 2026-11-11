"""Public-history action context and calibration diagnostics."""
from replay import states,agent
import collections as C,json,statistics
out=C.defaultdict(C.Counter); examples=[]
for st,m,actual,h in states():
 hero=next(x for x in st.seats if x.seat==st.seat);opps=[x for x in st.seats if x.seat!=st.seat and x.status in ('active','all_in')]
 if not opps:continue
 n=st.players_remaining
 if st.board:
  if actual[0]=='fold' and n<=3 and len(examples)<30:
   ids=[agent.CID[x] for x in st.cards];b=tuple(agent.CARDS[agent.CID[x]] for x in st.board);ctx=agent._context([agent.CID[x]//4 for x in st.board],[agent.CID[x]%4 for x in st.board],b)
   made=agent._made(agent.eval7.evaluate(tuple(agent.CARDS[x] for x in ids)+b),ctx,ids[0]//4,ids[1]//4)
   if made>=1:examples.append(dict(n=n,hand=st.cards,board=st.board,pot=st.pot,cost=st.to_call,made=made,actions=h['events']))
  continue
 if n>4:continue
 villain=next((x for x in opps if str(x.seat)==m['op']),max(opps,key=lambda x:x.bet))
 if m['nr']>=2 and villain.status=='all_in':
  label=f'n{n} vs reshove';out[label][actual[0]]+=1
print(dict(out))
print(json.dumps(examples[:10],indent=1))
