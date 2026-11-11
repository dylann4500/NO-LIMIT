"""Test-only SDK observer. No simulator imports. Agents do not share observations."""
import importlib.util,os,atexit,json
from pathlib import Path
ROOT=str(Path(__file__).resolve().parents[4])
def load(name,folder):
 p=ROOT+'/lab/field_bots/'+folder+'/agent.py';sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
OLD=load('old','openai_a_default_1');NEW=load('new','openai_a_default_1_r2')
TABLES={}
class Agent:
 def __init__(self):self.old=OLD.Agent();self.new=NEW.Agent()
 def act(self,state,memory):
  b=self.new if state.seat%2==0 else self.old
  a,m=b.act(state,memory)
  key=str(state.config.table_id)
  d=TABLES.setdefault(key,{'holes':{}})
  if d.get('hand')!=state.hand_number:d['holes']={}
  d.update(hand=state.hand_number,board=state.board[:],bust=state.bust_order,pot=state.pot,history=[[getattr(e.kind,'value',e.kind),e.seat,e.amount,e.cards] for e in state.history],seat=state.seat,cost=state.to_call,seats=[[s.seat,s.stack,s.bet,s.status] for s in state.seats],action=[a.kind.value,a.amount])
  d['holes'][state.seat]=state.cards[:]
  return a,m
@atexit.register
def save():json.dump(TABLES,open(str(Path(__file__).with_name('observations.json')),'w'))
