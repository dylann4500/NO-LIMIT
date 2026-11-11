"""SDK-only stress tests. This file never reads/imports simulator internals."""
import os,sys,time,random,json,statistics,pickle
sys.path.insert(0,os.path.abspath(os.path.join(os.path.dirname(__file__),'../../fake_sdk')))
sys.path.insert(0,os.path.dirname(__file__))
import agent
from poker_agent_sdk import State,Config,Seat,Event,LegalAction,ActionKind
R=random.Random(558194)
DECK=agent.STRINGS
CFG=Config(payouts=[50,30,20,0,0,0,0,0],decision_ms=1,time_bank_ms=100,memory_bytes=65536,table_id='test')
CHECKED=0

def state(cards,board,seat=0,button=7,n=8,pot=100,cost=0,stack=2000,events=None,canraise=True,hand=1):
    seats=[Seat(i,stack if i==seat else max(0,stack-cost),0 if i==seat else cost,'active') for i in range(n)]
    legal=[LegalAction(ActionKind.CALL if cost else ActionKind.CHECK)]
    if cost:legal.append(LegalAction(ActionKind.FOLD))
    if canraise and stack>cost:legal.append(LegalAction(ActionKind.RAISE,min(stack,max(20,2*cost)),stack))
    return State(cards=cards,board=board,seat=seat,button=button%n,seats=seats,pot=pot,to_call=cost,blinds=[10,20],players_remaining=n,hand_number=hand,config=CFG,events=events or [Event('hand',amount=hand)],legal_actions=legal,time_bank_ms=100)

def legal(s,a):
    global CHECKED
    allowed={x.kind:x for x in s.legal_actions}
    assert a.kind in allowed,(s.cards,s.board,a,s.legal_actions)
    if a.kind==ActionKind.RAISE:
        assert type(a.amount)==int
        x=allowed[a.kind];assert x.min_amount<=a.amount<=x.max_amount
    CHECKED+=1

A=agent.Agent()
# Regression: an attempted raise with no legal raise must call the nuts.
s=state(['As','Ks'],['Qs','Js','Ts','2d','3c'],n=2,pot=1000,cost=100,canraise=False)
s.events += [Event('board',cards=s.board[:3]),Event('board',cards=s.board[3:4]),Event('board',cards=s.board[4:]),Event('raise',seat=1,amount=100)]
a,m=A.act(s,b'');legal(s,a);assert a.kind==ActionKind.CALL,a
# Regression: pocket pair improving a double-paired board.
s=state(['8d','8h'],['4s','Kd','4c','Kh'],n=2,pot=288)
a,m=A.act(s,b'');legal(s,a)
# Shared board nuts are a certain chop, including when the bank is empty.
s=state(['2d','3c'],['As','Ks','Qs','Js','Ts'],n=2,pot=300,cost=200,canraise=False)
s.events += [Event('board',cards=s.board[:3]),Event('board',cards=s.board[3:4]),Event('board',cards=s.board[4:]),Event('raise',seat=1,amount=200)]
a,m=A.act(s,b'');legal(s,a);assert a.kind==ActionKind.CALL,a
s.time_bank_ms=0
a,m=A.act(s,b'');legal(s,a);assert a.kind==ActionKind.CALL,a
# Equal-stack ICM and unmatched all-in overbets under winner-take-all payouts.
assert abs(agent.icm([100]*4,[50,30,20,0],0)-25)<1e-9
assert abs(agent.icm([100]*3,[50,30,20],0)-100/3)<1e-9
s=state(['7d','2c'],[],n=4,pot=2100,cost=100,stack=100,canraise=False)
s.config=Config(payouts=[100,0,0,0])
s.seats[1].bet=2000;s.seats[1].stack=0;s.seats[1].status='all_in'
for p in s.seats[2:]:p.bet=0;p.stack=200;p.status='folded'
t=agent.icm_call_threshold(s,s.seats[0],[s.seats[1]],100,200)
assert abs(t-1/3)<1e-4,t
s.seats[2].stack=20
assert agent.risk_premium(s,s.seats[0],[s.seats[1]],100)==0.
# An unmatched overshove cannot make a weak board-playing hand a cheap call.
s=state(['3s','4c'],['As','Kh','Qd','Js','9h'],n=2,pot=2100,cost=100,stack=100,canraise=False)
s.to_call=2000;s.seats[1].bet=2000;s.seats[1].stack=0;s.seats[1].status='all_in'
s.events += [Event('board',cards=s.board[:3]),Event('board',cards=s.board[3:4]),Event('board',cards=s.board[4:]),Event('raise',seat=1,amount=2000)]
a,m=A.act(s,b'');legal(s,a);assert a.kind==ActionKind.FOLD,a
# Seat IDs are labels; physical order comes from the seat list and button.
s=state(['As','Kd'],[],n=3,button=2)
for p,sid in zip(s.seats,[17,4,91]):p.seat=sid
s.seat=17;s.button=91
a,m=A.act(s,b'');legal(s,a)
for cut in (1,5,13,32,64):
    a,_=A.act(s,m[:cut]);legal(s,a)
# Non-overlapping cards with deliberately varied public states and legal menus.
wall=[];cpu=[];memmax=0
for i in range(14000):
    n=R.randrange(2,9);count=R.choice([0,0,3,4,5]);cs=R.sample(DECK,count+2)
    stack=R.choice([1,5,19,20,39,80,150,400,1000,2000,10000])
    cost=R.choice([0,0,1,10,20,50,100,200,500,2000]);cost=min(stack,cost)
    ev=[Event('hand',amount=i+1)]
    for j in range(R.randrange(4)):
        ev.append(Event('raise',seat=R.randrange(n),amount=20*(2+j)))
    if count:
        ev.append(Event('board',cards=cs[2:5]))
        if count>3:
            ev.extend([Event('call',seat=R.randrange(n),amount=20),Event('board',cards=cs[5:6])])
        if count>4:
            ev.extend([Event('raise',seat=R.randrange(n),amount=80),Event('call',seat=R.randrange(n),amount=80),Event('board',cards=cs[6:7])])
        if cost:ev.append(Event('raise',seat=R.randrange(1,n),amount=cost))
    s=state(cs[:2],cs[2:],n=n,pot=R.choice([30,80,200,500,4000,15000]),cost=cost,stack=stack,events=ev,canraise=bool(R.randrange(2)),hand=i+1,button=R.randrange(n))
    if R.random()<.3:
        for p in s.seats[1:]:
            if R.random()<.35:p.status='folded'
    c=time.process_time_ns();w=time.perf_counter_ns()
    a,m=A.act(s,b'')
    wall.append((time.perf_counter_ns()-w)/1000);cpu.append((time.process_time_ns()-c)/1000)
    legal(s,a);assert len(m)<16000
    memmax=max(memmax,len(m))
# Low-bank operation exercises the emergency policy and reduced sampling modes.
for bank in (0,5,20):
    for i in range(500):
        count=R.choice([3,4,5]);cs=R.sample(DECK,count+2)
        s=state(cs[:2],cs[2:],n=R.randrange(2,9),pot=500,cost=R.choice([0,100]),stack=2000)
        s.time_bank_ms=bank
        a,m=A.act(s,b'');legal(s,a)
# Event persistence: same table observations are transferable to a fresh copy.
s=state(['As','Kd'],[],n=2,events=[Event('hand',amount=3),Event('raise',seat=1,amount=60)],cost=40,hand=3)
a,m=A.act(s,b'');legal(s,a);s.events=[]
b,m2=agent.Agent().act(s,m);legal(s,b)
assert pickle.loads(m2)['stats']['1'][2]==1
print(json.dumps({'legal_decisions':CHECKED,'memory_max':memmax,'cpu_us':{str(q):round(sorted(cpu)[int((len(cpu)-1)*q)],1) for q in [.5,.99,.999,1.]},'wall_us':{str(q):round(sorted(wall)[int((len(wall)-1)*q)],1) for q in [.5,.99,.999,1.]}},indent=2))
