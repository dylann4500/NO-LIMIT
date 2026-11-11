"""SDK-only replay of recorded decision states. Outcomes remain the recorded ones."""
import os,sys,json,gzip,importlib.util,collections as C,marshal,time
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0,os.path.join(ROOT,'lab','fake_sdk'))
from poker_agent_sdk import State,Seat,Event,Config,LegalAction,ActionKind

def states():
 pending=[];table=None
 for line in gzip.open(os.path.join(HERE,'../openai_b_default_1/round1/hand_history.jsonl.gz'),'rt'):
  h=json.loads(line);hero=h['seat']
  if h['table']!=table:table=h['table'];pending=[]
  stacks={int(s):v for s,v in h['stacks'].items()};bets=C.Counter();total=C.Counter();status={i:('active' if i in stacks else 'busted') for i in range(8)};board=[];mx=0;increment=h['blinds'][1];history=[]
  for i,(k,s,amt,cs) in enumerate(h['events']):
   ev=Event(k,s,amt,cs)
   if s==hero and k in ('fold','check','call','raise') and h['hole']:
    cost=max(0,mx-bets[s]);maximum=bets[s]+stacks[s]
    legal=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)] if cost else [LegalAction(ActionKind.CHECK)]
    if maximum>mx and any(v=='active' and j!=s and stacks.get(j,0)>0 for j,v in status.items()):
     legal.append(LegalAction(ActionKind.RAISE,min(maximum,mx+increment),maximum))
    state=State(seat=hero,cards=h['hole'],board=board[:],pot=sum(total.values()),to_call=cost,legal_actions=legal,history=history[:],phase='betting',seats=[Seat(j,stacks.get(j,0),bets[j],status[j]) for j in range(8)],button=h['button'],blind_level=0,blinds=h['blinds'],hands_until_next_level=20-(h['hand']%20),hand_number=h['hand'],players_remaining=len(h['stacks']),bust_order=[],time_bank_ms=100,events=pending[:],config=Config(table_id=table,seat=hero,variant='holdem',players=8,starting_stack=2000,payouts=[50,30,20,0,0,0,0,0],decision_ms=1,time_bank_ms=100,memory_bytes=65536))
    yield h,i,state
    pending=[]
   if k=='board':board+=cs;bets=C.Counter();mx=0;increment=h['blinds'][1]
   elif k in ('blind','ante','raise','call'):
    add=max(0,amt-bets[s]) if k=='raise' else amt
    stacks[s]-=add;total[s]+=add
    if k!='ante':bets[s]+=add
    if k=='raise':increment=max(increment,bets[s]-mx)
    mx=max(mx,bets[s])
    if stacks[s]==0:status[s]='all_in'
   elif k=='fold':status[s]='folded'
   pending.append(ev);history.append(ev)

def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
if __name__=='__main__':
 paths=sys.argv[1:] or [os.path.join(HERE,'../openai_b_default_1/agent.py'),os.path.join(HERE,'agent.py')]
 bots=[load(p,'bot'+str(i)) for i,p in enumerate(paths)];agents=[b.Agent() for b in bots];mem=[b'']*len(bots);tab=None;counts=C.Counter();changed=[];lat=[]
 for h,i,s in states():
  if h['table']!=tab:tab=h['table'];mem=[b'']*len(bots)
  ac=[]
  for j,(b,a) in enumerate(zip(bots,agents)):
   start=time.process_time_ns();action,mem[j]=a.act(s,mem[j]);lat.append((time.process_time_ns()-start)/1000)
   assert not marshal.loads(mem[j]).get('guard_errors'),marshal.loads(mem[j])
   ac.append((action.kind.value,action.amount))
  counts['decisions']+=1
  counts['original_match']+=ac[0][0]==h['events'][i][0]
  if len(ac)>1 and ac[0]!=ac[1]:
   key=str(len(s.board))+':'+ac[0][0]+'->'+ac[1][0];counts[key]+=1
   changed.append(dict(table=tab,hand=h['hand'],i=i,cards=s.cards,board=s.board,pot=s.pot,cost=s.to_call,actions=ac))
 lat.sort();print(dict(counts));print('CPU p99',lat[int(.99*len(lat))],'max',max(lat))
 with open(os.path.join(HERE,'replay_changes.json'),'w') as f:json.dump(changed,f)
