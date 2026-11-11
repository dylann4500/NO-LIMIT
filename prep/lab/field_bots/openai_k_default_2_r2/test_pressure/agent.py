"""SDK-only stress opponent: baseline with frequent bets into unbet pots.
Constructed from aggregate public field betting tendencies, not opponent code.
"""
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[2]/'openai_k_default_2'
spec=importlib.util.spec_from_file_location('pressure_base',str(ROOT/'agent.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class Agent(p.Agent):
 def _act(self,state,memory):
  action,data=super()._act(state,memory)
  if state.board and not state.to_call and p.kind(action)=='check':
   legal=next((r for r in state.legal_actions if p.kind(r)=='raise'),None)
   opponents=[s for s in state.seats if s.seat!=state.seat and s.status=='active' and s.stack>0]
   if legal and opponents:
    ids=[p.CARD_INDEX[c] for c in state.cards];bids=[p.CARD_INDEX[c] for c in state.board]
    cards=[p.CARDS[i] for i in ids+bids];val=p.eval7.evaluate(cards);cat=val>>24
    street=len(state.board)-3
    freq=(.85,.48,.26)[street] if cat==0 else (.90,.72,.55)[street] if cat==1 else .97
    seed=(state.hand_number*2654435761+state.seat*101+sum(ids)*2246822519)&0xffffffff
    if seed/4294967296.<freq:
     total=next(s.bet for s in state.seats if s.seat==state.seat)+int(state.pot*(.65 if street<2 else .75))
     return p.Action.raise_to(int(p.clamp(total,legal.min_amount,legal.max_amount))),data
  return action,data
