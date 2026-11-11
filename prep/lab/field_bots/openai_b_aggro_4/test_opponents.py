"""Independent SDK opponents for sensitivity checks, no simulator imports."""
import agent as a
from poker_agent_sdk import Action
import eval7
class Simple:
 width=.20; callwidth=.18; station=False
 def act(self,s,m):
  legal={x.kind.value:x for x in s.legal_actions}
  me=next(x for x in s.seats if x.seat==s.seat)
  def fold():return Action.check() if not s.to_call else Action.fold()
  def call():return Action.call() if s.to_call else Action.check()
  def raise_(v):
   if 'raise' not in legal:return call()
   r=legal['raise'];return Action.raise_to(max(r.min_amount,min(r.max_amount,int(v))))
  bb=s.blinds[1]
  if not s.board:
   rank=a.PREFLOP[a._hand_key(s.cards)][7]
   raised=any(e.kind=='raise' for e in s.history)
   if rank<.025:return raise_(me.bet+me.stack if s.to_call>12*bb else max(3*bb,3*(me.bet+s.to_call))) ,b''
   if not raised and rank<self.width:return (call() if self.station else raise_(3*bb)),b''
   if raised and rank<self.callwidth and s.to_call<me.stack*.25:return call(),b''
   return fold(),b''
  cs=[a.CARD[c] for c in s.cards+s.board]
  value=eval7.evaluate(cs);cat=value>>24
  ranks=[a.RANK[c[0]] for c in s.cards];br=[a.RANK[c[0]] for c in s.board]
  ownpair=ranks[0]==ranks[1] or any(r in br for r in ranks)
  top=ownpair and max(ranks)>=max(br)
  serious=cat>=2 and ownpair or cat>=4
  draw=len(s.board)<5 and any(sum(c.suit==i for c in cs)==4 and any(c.suit==i for c in cs[:2]) for i in range(4))
  if s.to_call:
   if serious:return raise_(me.bet+s.to_call+(s.pot+s.to_call)*.8),b''
   if top and s.to_call<s.pot*.8 or self.station and ownpair and s.to_call<s.pot*.65 or draw and s.to_call<s.pot*.45:return call(),b''
   return fold(),b''
  if serious or top and not self.station:return raise_(me.bet+max(bb,s.pot*.65)),b''
  return call(),b''
class Rock(Simple):pass
class Station(Simple):
 width=.48;callwidth=.48;station=True
class Nit(Simple):
 width=.13;callwidth=.10
