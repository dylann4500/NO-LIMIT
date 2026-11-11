"""Recorded-state regressions and sequential posterior properties, SDK only."""
import os,sys,marshal
from replay import states
import agent as bot
import eval7
# A low pair on the board does not downgrade two higher, private pairs.
ids=[bot.IDS[c] for c in ['Ac','8h','3c','3d','Js']]
a,b=[bot.IDS[c] for c in ['Ad','8s']]
val,_,_=bot.made_info(a,b,eval7.evaluate([bot.CARDS[c] for c in ids+[a,b]]),bot.board_texture(ids))
assert val==2.,val
# Multiple value actions must reduce the mass of unpaired hands. eval7's
# numeric range weights are ignored, so duplicated samples must carry mass.
ids=[bot.IDS[c] for c in ['Ac','7d','5h','5c','Ts']]
a,b=[bot.IDS[c] for c in ['Ad','Jd']];tex=bot.board_texture(ids);st=bot.fresh_stats(2000)
st[0]=12;st[5]=8;st[6]=15
base=bot.posterior_range(a,b,ids,tex,st,{'pa':[]},.3,3)
seq=bot.posterior_range(a,b,ids,tex,st,{'pa':[(1,'raise',.6,False),(2,'raise',.6,False),(3,'raise',1.3,False)]},.3,3)
def air(rng):
 return sum(bot.made_info(bot.IDS[str(h[0])],bot.IDS[str(h[1])],eval7.evaluate(list(h)+[bot.CARDS[i] for i in ids]),tex)[0]<.35 for h,w in rng)/len(rng)
assert air(seq)<air(base)*.35,(air(seq),air(base))
assert len(set(h for h,w in seq))<len(seq),'posterior must preserve weighted mass'
# Replay complete per-table event streams through independent Agent copies.
# The target decisions were three of the largest avoidable river payoffs.
targets={('s1002i1t1',8,18),('s1003i1t0',10,19),('s1007i8t0',29,21)}
found=set();memory=b'';table=None;copies=[bot.Agent(),bot.Agent()];n=0
for h,i,state in states():
 if h['table']!=table:table=h['table'];memory=b''
 action,memory=copies[n%2].act(state,memory);n+=1
 assert not marshal.loads(memory).get('guard_errors'),marshal.loads(memory)
 legal={x.kind:x for x in state.legal_actions};assert action.kind in legal
 if action.kind.value=='raise':
  la=legal[action.kind];assert isinstance(action.amount,int) and la.min_amount<=action.amount<=la.max_amount
 key=(h['table'],h['hand'],i)
 if key in targets:
  assert action.kind.value=='fold',(key,action)
  found.add(key)
assert found==targets,found
print({'recorded_decisions':n,'river_regressions':len(found),'posterior_air_base':round(air(base),3),'posterior_air_sequential':round(air(seq),3),'illegal':0,'guard_errors':0})
