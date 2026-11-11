"""Independent API, economic, replay, and CPU-budget checks. Run from any directory."""
import itertools
import json
import math
import os
import pickle
import random
import statistics
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'fake_sdk'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import poker_agent_sdk as sdk
import agent

RNG = random.Random(20261106)

def state_for(hole=None, board=None, n=8, cost=0, hero=0, payouts=None, bank=100, forced=None):
    if hole is None or board is None:
        ids=RNG.sample(agent.CARD_NAMES,7)
        hole=ids[:2] if hole is None else hole
        board=ids[2:5] if board is None else board
    base=RNG.randrange(300,6000)
    stacks=[RNG.randrange(100,6000) for _ in range(n)]
    stacks[hero]=base
    villain=(hero+1)%n
    events=[sdk.Event('hand',amount=7),sdk.Event('blind',seat=0,amount=10),sdk.Event('blind',seat=1,amount=20)]
    # One 2BB opening raise and calls, then the public runout and prior checks.
    events.append(sdk.Event('raise',seat=2%n,amount=40))
    for i in range(n):
        if i==2%n:continue
        old=10 if i==0 else 20 if i==1 else 0
        events.append(sdk.Event('call',seat=i,amount=40-old))
    pot=40*n
    if board:
        events.append(sdk.Event('board',cards=board[:3]))
        for card in board[3:]:
            events.extend(sdk.Event('check',seat=i) for i in range(n))
            events.append(sdk.Event('board',cards=[card]))
        events.extend(sdk.Event('check',seat=i) for i in range(n) if i not in (hero,villain))
        if cost:events.append(sdk.Event('raise',seat=villain,amount=cost));pot+=cost
    else:
        # Preflop fixtures use an actual open raise, hero has already matched 2BB.
        if cost:events.append(sdk.Event('raise',seat=villain,amount=40+cost));pot+=cost
    seats=[sdk.Seat(i,stacks[i],(cost if i==villain else 0) if board else 40+(cost if i==villain else 0),'active') for i in range(n)]
    if forced is not None:
        legal=forced
    elif cost:
        legal=[sdk.LegalAction(sdk.ActionKind.FOLD),sdk.LegalAction(sdk.ActionKind.CALL)]
        if base>cost:
            minimum=min(base,2*cost+(0 if board else 40))
            legal.append(sdk.LegalAction(sdk.ActionKind.RAISE,minimum,base+(0 if board else 40)))
    else:
        legal=[sdk.LegalAction(sdk.ActionKind.CHECK),sdk.LegalAction(sdk.ActionKind.RAISE,20,base+(0 if board else 40))]
    cfg=sdk.Config(table_id='validation',seat=hero,variant='holdem',players=n,starting_stack=2000,blinds=[[10,20]],hands_per_level=20,hand_cap=250,payouts=payouts or [50,30,20]+[0]*5,decision_ms=1,time_bank_ms=100,memory_bytes=65536)
    return sdk.State(seat=hero,cards=hole,board=board,pot=pot,to_call=min(cost,base),legal_actions=legal,history=events,phase='betting',seats=seats,button=n-1,blind_level=0,blinds=[10,20],hands_until_next_level=13,hand_number=7,players_remaining=n,bust_order=[],config=cfg,time_bank_ms=bank,events=events)

def legal(action,state):
    offered={a.kind:a for a in state.legal_actions}
    assert action.kind in offered,(action,state.legal_actions)
    if action.kind==sdk.ActionKind.RAISE:
        r=offered[action.kind]
        assert type(action.amount) is int and r.min_amount<=action.amount<=r.max_amount,(action,r)


def test_icm():
    count=0
    for n in range(2,8):
        for _ in range(7):
            chips=[RNG.randrange(20,5000) for _ in range(n)]
            pay=sorted([RNG.randrange(0,80) for _ in range(n)],reverse=True)
            exact=[0.]*n
            for order in itertools.permutations(range(n)):
                prob=1.;remaining=sum(chips)
                for i in order:prob*=chips[i]/remaining;remaining-=chips[i]
                for rank,i in enumerate(order):exact[i]+=prob*pay[rank]
            got=[agent.icm_value(chips,i,pay,n) for i in range(n)]
            assert max(abs(a-b) for a,b in zip(exact,got))<1e-6,(chips,pay,exact,got)
            assert abs(sum(got)-sum(pay))<1e-6
            count+=1
    assert agent.icm_value([0,1,1,1],0,[50,30,20,0],4)==0
    assert agent.icm_value([0,1],0,[50,30],2)==30
    return count


def test_semantics():
    # Preflop: UTG acts first, button last before the blinds; postflop: SB first.
    s=state_for(n=8)
    assert [agent.seat_position(s,i) for i in range(8)]==[6,7,0,1,2,3,4,5]
    assert [agent.post_position(s,i) for i in range(8)]==list(range(8))
    s=state_for(n=2)
    assert agent.seat_position(s,1)==0 and agent.post_position(s,1)==1
    # Three different shared nuts: every legal call wins at least a split pot.
    for board in [['As','Ks','Qs','Js','Ts'],['7s','7h','7d','7c','As'],['As','Kd','Qh','Jc','Ts']]:
        s=state_for(hole=['2c','3c'],board=board,n=4,cost=1000)
        action,_=agent.Agent()._act(s,b'')
        assert action.kind==sdk.ActionKind.CALL,(board,action)
    # A forced blind all-in has a random range; even 32o calls these pot odds.
    s=state_for(hole=['3c','2d'],board=[],n=2,cost=300,hero=0)
    s.button=0;s.blinds=[500,1000];s.pot=1300;s.to_call=300
    s.seats=[sdk.Seat(0,500,500,'active'),sdk.Seat(1,0,800,'all_in')]
    s.events=[sdk.Event('hand',amount=7),sdk.Event('blind',seat=0,amount=500),sdk.Event('blind',seat=1,amount=800)]
    s.legal_actions=[sdk.LegalAction(sdk.ActionKind.FOLD),sdk.LegalAction(sdk.ActionKind.CALL)]
    a,_=agent.Agent()._act(s,b'');assert a.kind==sdk.ActionKind.CALL,a
    # Contribution caps prevent using a large side pot to justify a short call.
    h={'contrib':{0:10,1:1000,2:1000}}
    assert agent.eligible_pot(h,0,10,2010)==50
    # Timeout replay starts from identical prior memory, so public stats must not double.
    s=state_for(n=6,cost=100)
    a,m1=agent.Agent()._act(s,b'')
    b,m2=agent.Agent()._act(s,b'')
    assert pickle.loads(m1)==pickle.loads(m2)
    # A fresh copy must be able to continue a table using only returned bytes.
    s.events=[]
    _,m3=agent.Agent()._act(s,m1)
    assert pickle.loads(m3)['stats']==pickle.loads(m1)['stats']
    # Unknown/corrupted memory is safe to discard.
    for mem in (b'',b'invalid',pickle.dumps({'v':99})):
        a,m=agent.Agent()._act(s,mem);legal(a,s);assert isinstance(m,bytes)
    # A changed memory cap must produce valid bytes rather than truncated pickle.
    s=state_for(n=8,cost=150)
    s.config.memory_bytes=64
    a,mem=agent.Agent()._act(s,b'');legal(a,s);assert len(mem)<=64
    s.events=[]
    a,mem=agent.Agent()._act(s,mem);legal(a,s)
    s.config.memory_bytes=0
    a,mem=agent.Agent()._act(s,mem);legal(a,s);assert mem==b''
    # Exact quads and a royal flush never disappear into a generic free-check fallback.
    s=state_for(hole=['As','Ks'],board=['Qs','Js','Ts','2h','4d'],n=3)
    a,_=agent.Agent()._act(s,b'');assert a.kind==sdk.ActionKind.RAISE


def test_multiway():
    cases=[(3,[2000,2000],.4666666666666667),(8,[2000]*7,.5916666666666667),(3,[1000,3000],.46153846153846156),(3,[3000,1000],.46153846153846156)]
    for n,amounts,want in cases:
        s=state_for(n=n,hero=0)
        s.seats=[sdk.Seat(0,2000,0,'active')]+[sdk.Seat(i,0,c,'all_in') for i,c in enumerate(amounts,1)]
        s.pot=sum(amounts);s.to_call=2000
        h=agent.new_hand(7);h['contrib']={i:c for i,c in enumerate(amounts,1)}
        got=agent.payout_odds(s,s.seats[1:],2000,s.pot,2000/(s.pot+2000),None,h)
        assert abs(got-want)<1e-6,(n,got,want)
    return len(cases)

def test_decisions(count=6000):
    times=[];maxmem=0;by_street={0:[],3:[],4:[],5:[]}
    for i in range(count):
        n=RNG.randrange(2,9);hero=RNG.randrange(n)
        ids=RNG.sample(agent.CARD_NAMES,7)
        blen=[0,3,4,5][i%4]
        cost=RNG.choice([0,0,1,20,50,150,700,1800])
        pay=RNG.choice([[50,30,20,0,0,0,0,0],[100,0,0,0,0,0,0,0],[40,25,15,9,6,3,2,0],[25]*4+[0]*4])
        forced=None
        if i%31==0:forced=[sdk.LegalAction(sdk.ActionKind.RAISE,137,137)]
        elif i%29==0:forced=[sdk.LegalAction(sdk.ActionKind.CALL)]
        elif i%23==0:forced=[sdk.LegalAction(sdk.ActionKind.CHECK)]
        s=state_for(ids[:2],ids[2:2+blen],n,cost,hero,pay,0 if i%3==0 else 100,forced)
        # Exercise an established table model, not just the initial priors.
        model=agent.update(s,b'')
        s.events=[]
        for sid,v in model['stats'].items():
            hands=RNG.randrange(8,100);v[agent.H]=hands
            v[agent.VP]=RNG.randrange(hands+1);v[agent.PR]=RNG.randrange(v[agent.VP]+1)
            v[agent.PA]=RNG.randrange(1,100);v[agent.PB]=RNG.randrange(v[agent.PA]+1)
        mem=pickle.dumps(model,protocol=4)
        t=time.thread_time_ns()
        action,result=agent.Agent()._act(s,mem)
        elapsed=(time.thread_time_ns()-t)/1000
        legal(action,s)
        assert isinstance(result,bytes) and len(result)<16384
        maxmem=max(maxmem,len(result));times.append(elapsed);by_street[blen].append(elapsed)
    quant=lambda ts:{'p50':round(statistics.median(ts),1),'p99':round(sorted(ts)[int(.99*len(ts))],1),'max':round(max(ts),1)}
    return {'decisions':count,'illegal_or_exception':0,'cpu_us':quant(times),'cpu_us_by_board':{str(k):quant(v) for k,v in by_street.items()},'memory_bytes_max':maxmem}

if __name__=='__main__':
    schedules=test_icm()
    test_semantics()
    multiway=test_multiway()
    result=test_decisions()
    result['exhaustive_icm_schedules']=schedules
    result['semantic_checks']='passed'
    result['multiway_payout_cases']=multiway
    print(json.dumps(result,indent=2))
