"""SDK-contract and poker edge-case checks; run with PYTHONPATH=lab/fake_sdk."""
import itertools,json,random,time,statistics
from types import SimpleNamespace as NS
from poker_agent_sdk import State,Seat,LegalAction,ActionKind,Event
from agent import Agent,_icm,_hand_key,_relative_category,PREFLOP,CARD
import eval7

def run():
 rng=random.Random(710331)
 bot=Agent()
 # Known ICM solutions, scale invariance, tied stacks and winner-take-all.
 assert abs(_icm([100,100,100],0,[50,30,20])-100/3)<1e-9
 assert abs(_icm([80,20],0,[100,0])-80)<1e-9
 for n in range(2,9):
  stacks=[rng.randrange(1,20000) for _ in range(n)]
  for payout in ([50,30,20]+[0]*(n-3) if n>=3 else [50,30], [100]+[0]*(n-1),[10]*n):
   values=[_icm(stacks,i,payout) for i in range(n)]
   assert abs(sum(values)-sum(payout[:n]))<1e-7,(n,values)
   assert abs(_icm(stacks,0,payout)-_icm([x*19 for x in stacks],0,payout))<1e-8
 # Unmatched overbets are excluded from the pot we can actually win.
 assert bot._eligible_pot(NS(pot=1100),NS(bet=0,stack=100),[NS(bet=1000)])==200
 for hole,board,expected in [('As Kh','Qs Qd Qh',0),('As Ah','Qs Qd Qh',6),('As Qh','Qs Qd Qc',7),('As Kh','Qs Qd 7h 7s 2c',0),('As Ah','Qs Qd 7h 7s 2c',2),('2c 3h','As Ks Qs Js Ts',0)]:
  h=[CARD[c] for c in hole.split()];b=[CARD[c] for c in board.split()]
  counts=[0]*15
  for c in b:counts[c.rank+2]+=1
  bv=eval7.evaluate(b) if len(b)==5 else -1
  assert _relative_category(eval7.evaluate(h+b),counts,bv)==expected,(hole,board)
 def edge_state(hole,board):
  events=[Event('hand',amount=1),Event('blind',seat=0,amount=10),Event('blind',seat=1,amount=20)]
  if board:events.append(Event('board',cards=board))
  return State(seat=0,cards=hole,board=board,pot=30,to_call=10,legal_actions=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)],history=events,seats=[Seat(0,1990,10,'active'),Seat(1,0,20,'all_in')],button=0,blinds=[10,20],hand_number=1,config=NS(payouts=[50,30],decision_ms=1),time_bank_ms=100,events=events)
 assert bot.act(edge_state(['As','Ah'],[]),b'')[0].kind==ActionKind.CALL
 for board in [['As','Ks','Qs','Js','Ts'],['As','Kd','Qh','Jc','Ts'],['Ks','Kd','Kh','Kc','As'],['As','Ad','Ah','Ac','Ks']]:
  state=edge_state(['2c','3h'],board)
  state.pot=100;state.to_call=50000;state.seats[0].stack=50000;state.seats[1].bet=50000
  assert bot.act(state,b'')[0].kind==ActionKind.CALL,board
 # All 1,326 starting combinations map to the same suit-invariant 169 keys.
 deck=[r+s for r in '23456789TJQKA' for s in 'cdhs']
 keys={_hand_key(c) for c in itertools.combinations(deck,2)}
 assert keys==set(PREFLOP) and len(keys)==169
 lat=[]; size=0
 for trial in range(6000):
  n=rng.randrange(2,9); hero=rng.randrange(n); button=rng.randrange(n)
  boardlen=rng.choice([0,0,3,4,5]); cs=rng.sample(deck,2+boardlen)
  bb=rng.choice([2,20,40,100,200]); sb=bb//2
  seats=[Seat(i,rng.choice([1,bb//2,bb*3,bb*10,bb*50,bb*200]),0,'active') for i in range(n)]
  me=seats[hero]; opp=[x for x in seats if x.seat!=hero]
  for x in opp:
   if rng.random()<.2:x.status='folded'
  opp[0].status='active'
  h=[Event('hand',amount=trial+1)]
  h += [Event('blind',seat=(button+1)%n,amount=sb),Event('blind',seat=(button+2)%n,amount=bb)]
  for e in h[1:]:seats[e.seat].bet+=e.amount
  if boardlen:
   if rng.random()<.6:h.append(Event('raise',seat=opp[0].seat,amount=3*bb))
   h.append(Event('board',cards=cs[2:5]))
   if boardlen>=4:h.append(Event('board',cards=cs[5:6]))
   if boardlen==5:h.append(Event('board',cards=cs[6:7]))
   for x in seats:x.bet=0
  if rng.random()<.65:
   amount=rng.choice([bb,bb*2,bb*5,me.stack+me.bet+bb*30])
   opp[0].bet=amount
   h.append(Event('raise',seat=opp[0].seat,amount=amount))
   if rng.random()<.35:opp[0].stack=0;opp[0].status='all_in'
  cost=max(0,max(x.bet for x in seats)-me.bet)
  legal=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)] if cost else [LegalAction(ActionKind.CHECK)]
  if rng.random()<.75:
   mx=me.stack+me.bet
   mn=min(mx,max(bb,max(x.bet for x in seats)*2))
   legal.append(LegalAction(ActionKind.RAISE,mn,mx))
  config=NS(payouts=rng.choice([[50,30,20,0,0,0,0,0],[100,0,0,0,0,0,0,0],[25,25,25,25,0,0,0,0]]),decision_ms=1,memory_bytes=65536)
  state=State(seat=hero,cards=cs[:2],board=cs[2:],pot=sum(x.bet for x in seats)+rng.randrange(bb,bb*40),to_call=cost,legal_actions=legal,history=h,phase='betting',seats=seats,button=button,blind_level=1,blinds=[sb,bb],hands_until_next_level=10,hand_number=trial+1,players_remaining=n,bust_order=[],config=config,time_bank_ms=100,events=h)
  start=time.thread_time_ns();a,m=bot.act(state,b'');lat.append((time.thread_time_ns()-start)/1000)
  offered=next((x for x in legal if x.kind==a.kind),None)
  assert offered is not None,(trial,a,legal)
  if a.kind==ActionKind.RAISE:assert type(a.amount)==int and offered.min_amount<=a.amount<=offered.max_amount
  assert len(m)<16384
  size=max(size,len(m))
  if trial%71==0:
   # A retry starts from the same old memory and replays the same events.
   a2,m2=bot.act(state,b''); assert m2==m
   # Next turn with no fresh events must not double-count observations.
   state.events=[]
   a3,m3=bot.act(state,m); assert m3==m
 lat.sort()
 print(json.dumps({'sdk_contract_cases':6000,'all_169_hands':True,'ICM_checks':'passed','side_pot_check':'passed','memory_retry_checks':'passed','max_memory_bytes':size,'cpu_us':{'p50':lat[len(lat)//2],'p99':lat[int(len(lat)*.99)],'p999':lat[int(len(lat)*.999)],'max':lat[-1]}},indent=2))
if __name__=='__main__':run()
