"""SDK-only contract, event-memory and latency regression tests."""
import os,sys,random,time,marshal,statistics,argparse,types
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0,os.path.join(ROOT,'lab','fake_sdk'))
from poker_agent_sdk import State,Seat,Event,Config,ActionKind,LegalAction
from agent import Agent,CARDS,read_memory,icm,call_threshold,IDS,board_texture,made_info
import eval7
import agent as bot
args=argparse.ArgumentParser()
args.add_argument("--cpu-scale",type=float,default=1.)
opts=args.parse_args()
if opts.cpu_scale!=1.:
 original_clock=time.process_time_ns
 bot.time=types.SimpleNamespace(process_time_ns=lambda:int(original_clock()*opts.cpu_scale))
rng=random.Random(492)
agent=Agent()
def fixture(cards=('As','Kh'), board=(), cost=0, stack=1800, pot=150, n=2, events=None, hand=1, maximum=None):
 me=0; seats=[Seat(i,stack,0,'active') for i in range(n)]
 seats[1].bet=cost
 legal=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)] if cost else [LegalAction(ActionKind.CHECK)]
 if maximum is None:maximum=stack
 if maximum>cost:legal.append(LegalAction(ActionKind.RAISE,max(cost*2,20),maximum))
 ev=events if events is not None else [Event('hand',amount=hand),Event('blind',0,10),Event('blind',1,20)]+([Event('board',cards=list(board))] if board else [])
 return State(seat=me,cards=list(cards),board=list(board),pot=pot,to_call=cost,legal_actions=legal,history=[],phase='betting',seats=seats,button=n-1,blind_level=0,blinds=[10,20],hands_until_next_level=10,hand_number=hand,players_remaining=n,bust_order=[],time_bank_ms=100,events=ev,config=Config(table_id='test',seat=me,variant='holdem',players=n,starting_stack=2000,payouts=[50,30,20,0,0,0,0,0],decision_ms=1,time_bank_ms=100,memory_bytes=65536))

def legal_action(action,state):
 options={x.kind:x for x in state.legal_actions}
 assert action.kind in options,action
 if action.kind==ActionKind.RAISE:
  la=options[action.kind];assert isinstance(action.amount,int) and la.min_amount<=action.amount<=la.max_amount,(action,la)

lat=[];cpu=[];maxmem=0
for i in range(2500):
 n=rng.randrange(2,9);nb=rng.choice([0,0,3,3,4,5]);deck=rng.sample([str(x) for x in CARDS],2+nb)
 stack=rng.randrange(40,8000);cost=rng.choice([0,0,10,20,40,100,stack]);cost=min(cost,stack)
 pot=rng.randrange(max(30,cost),max(31,cost+6000))
 board=deck[2:]
 ev=[Event('hand',amount=1),Event('blind',0,10),Event('blind',1,20)]
 for j in range(1,n):ev.append(Event('raise',j,60+20*j))
 if nb:
  ev.append(Event('board',cards=board[:3]))
  for j in range(1,n):ev.append(Event('raise',j,50+j*10))
 if nb>=4:
  ev.append(Event('board',cards=board[3:4]))
  for j in range(1,n):ev.append(Event('call',j,20))
 if nb==5:
  ev.append(Event('board',cards=board[4:]))
  ev.append(Event('raise',1,max(cost,20)))
 s=fixture(deck[:2],board,cost,stack,pot,n,ev)
 s.time_bank_ms=(0,10,24,25,100)[i%5]
 t=time.perf_counter_ns();ct=time.process_time_ns();ac,mem=agent.act(s,b'');cpu.append((time.process_time_ns()-ct)/1000);lat.append((time.perf_counter_ns()-t)/1000)
 legal_action(ac,s);assert len(mem)<=16384
 assert not marshal.loads(mem).get('guard_errors'),marshal.loads(mem).get('last_error')
 maxmem=max(maxmem,len(mem))
# Enum contract, strict min and max, absent raise and zero price.
for c in [0,20,1800]:
 s=fixture(cost=c,maximum=c)
 ac,mem=agent.act(s,b'');legal_action(ac,s)
# Regression: a dealer who is all-in has zero street bet and stack, but
# still participates in the hand. A dead button must be safe as well.
for button_status in ('all_in','busted'):
 s=fixture(board=['9d','Qh','Tc'],n=3)
 s.seats[2].status=button_status;s.seats[2].stack=0;s.seats[2].bet=0
 ac,mem=agent.act(s,b'');legal_action(ac,s)
 assert not marshal.loads(mem).get('guard_errors'),marshal.loads(mem)
# Boundary ranges: premiums and opening charts; check is always free.
s=fixture(cards=['As','Ad'],n=8,cost=20)
a,mem=agent.act(s,b'');assert a.kind==ActionKind.RAISE,a
s=fixture(cards=['7s','2d'],n=8,cost=20)
a,mem=agent.act(s,b'');assert a.kind==ActionKind.FOLD,a
# Every hand makes the same royal flush: a priced-in call cannot be folded.
for n in (2,4,8):
 s=fixture(cards=['2c','3d'],board=['As','Ks','Qs','Js','Ts'],cost=20,pot=1000,n=n)
 a,mem=agent.act(s,b'');assert a.kind==ActionKind.CALL,a
# Event replay carries information across copies, not self.
s=fixture(n=2)
m=read_memory(s,b'')
assert m['p']['1'][0]==1
s.events=[Event('raise',1,100),Event('fold',0),Event('show',1,cards=['7s','2d']),Event('stack',0,1990),Event('stack',1,2010),Event('hand',amount=2),Event('blind',0,10),Event('blind',1,20)]
s.hand_number=2
m=read_memory(s,marshal.dumps(m))
assert m['p']['1'][0]==2 and m['p']['1'][2]==1 and m['p']['1'][10]==1
assert m['c']['1']['pr']==0
# ICM conservation / symmetry and heads-up payouts.
assert abs(icm([100,100,100],0,[50,30,20])-100/3)<1e-8
assert abs(icm([100,100],0,[50,30])-40)<1e-8
assert icm([0,100,100],0,[50,30,20])==0
# Paired-board classification must not turn bottom pair into top pair.
board=['Qs','Qh','9c','4d','2h'];bi=[IDS[x] for x in board];tex=board_texture(bi)
for hole,expected in [(['As','2d'],.36),(['As','4c'],.58),(['As','9d'],1.12),(['As','Ad'],1.12)]:
 aa,bb=[IDS[x] for x in hole]
 rank=eval7.evaluate([CARDS[x] for x in bi+[aa,bb]])
 value,fd,sd=made_info(aa,bb,rank,tex)
 assert value==expected,(hole,value)
# A short fourth player creates a material ICM risk premium; winner-take-all
# reduces exactly to chip pot odds. Nondefault payouts must stay supported.
s=fixture(n=4,cost=1900,stack=2000,pot=2000)
s.seats[1].stack=10000;s.seats[2].stack=50;s.seats[3].stack=3950
threshold=call_threshold(s,s.seats[0],s.seats[1],1900)
assert threshold>.60,threshold
s.config.payouts=[100,0,0,0]
assert abs(call_threshold(s,s.seats[0],s.seats[1],1900)-1900/3900)<1e-8
s.config.payouts=[40,30,20,10]
a,mem=agent.act(s,b'');legal_action(a,s)
assert not marshal.loads(mem).get('guard_errors')
# Corrupt/truncated memory must recover within the protocol.
for bad in (b'x', b'\x00'*16, marshal.dumps([1,2,3])):
 a,mem=agent.act(fixture(),bad);legal_action(a,fixture())
 assert not marshal.loads(mem).get('guard_errors')
lat.sort();cpu.sort()
print({'cpu_scale':opts.cpu_scale,'cases':len(lat),'p50_us':lat[len(lat)//2],'p99_us':lat[int(.99*len(lat))],'max_us':max(lat),'max_memory':maxmem,'cpu_p50_us':cpu[len(cpu)//2],'cpu_p99_us':cpu[int(.99*len(cpu))],'cpu_max_us':max(cpu),'cpu_p99_at_2_5x_us':2.5*cpu[int(.99*len(cpu))]})
