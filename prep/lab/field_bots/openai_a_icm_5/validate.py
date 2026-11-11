"""Independent SDK contract, ICM, tournament-risk and timing checks.
Run with PYTHONPATH=lab/fake_sdk using the supplied Python interpreter.
"""
import importlib.util
import itertools
import math
import random
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'fake_sdk'))
from poker_agent_sdk import State, Seat, Config, LegalAction, ActionKind, Event
import agent as bot


def brute(stacks,hero,payout):
    out=0.
    for order in itertools.permutations(range(len(stacks))):
        prob=1.; total=sum(stacks)
        for s in order:
            prob*=stacks[s]/total; total-=stacks[s]
        place=order.index(hero)
        out+=prob*(payout[place] if place<len(payout) else 0)
    return out

rng=random.Random(523)
checks=0
for n in range(2,7):
    for _ in range(8):
        stacks=[rng.randrange(1,10000) for _ in range(n)]
        for payout in [[50,30,20],[70,20,10],[100],[45,25,15,10,5,0]]:
            for h in range(n):
                assert math.isclose(bot.icm(stacks,h,payout),brute(stacks,h,payout),abs_tol=1e-8)
                checks+=1
print('Independent exact ICM comparisons:',checks)


def state(n=4,cards=('As','Kd'),board=(),stacks=None,bets=None,to_call=0,bb=100,button=0,seat=0,payout=None,bank=100):
    stacks=stacks or [2000]*n; bets=bets or [0]*n
    seats=[Seat(i,stacks[i],bets[i],'active' if stacks[i] else 'all_in') for i in range(n)]
    la=[LegalAction(ActionKind.CHECK)] if not to_call else [LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)]
    if stacks[seat]>to_call:
        la.append(LegalAction(ActionKind.RAISE,min(stacks[seat]+bets[seat],max(bets)+max(bb,to_call)),stacks[seat]+bets[seat]))
    return State(seat=seat,cards=list(cards),board=list(board),pot=sum(bets)+bb*2,to_call=to_call,legal_actions=la,history=[],phase='betting',seats=seats,button=button,blind_level=0,blinds=[bb//2,bb],hands_until_next_level=10,hand_number=20,players_remaining=n,bust_order=[],config=Config(payouts=payout or [50,30,20],decision_ms=1,time_bank_ms=100,memory_bytes=65536),time_bank_ms=bank,events=[Event('hand',amount=20)])

# Same pot odds; a medium stack on the bubble must demand substantially more equity.
a=state(stacks=[2000,2000,2000,2000],bets=[0,2000,0,0],to_call=2000)
b=state(stacks=[2000,2000,2000,100],bets=[0,2000,0,0],to_call=2000)
ra=bot.call_threshold(a,a.seats,0,a.seats[1],2000,a.pot,[50,30,20])
rb=bot.call_threshold(b,b.seats,0,b.seats[1],2000,b.pot,[50,30,20])
assert rb>ra+.02, (ra,rb)
print('Bubble all-in thresholds:',round(ra,4),round(rb,4))

# Standard board equity invariants, sampled on every suit.
for suit in 'shdc':
    board=['A'+suit,'K'+suit,'Q'+suit,'J'+suit,'T'+suit]
    eq=bot.post_equity(['2'+('h' if suit!='h' else 's'),'3'+('c' if suit!='c' else 'd')],board,.35,.8,False,1)
    assert abs(eq-.5)<1e-8,eq
print('Shared royal-flush equity: passed')

agent=bot.Agent(); timings=[]; cpus=[]; memories=[]
deck=list(bot._CARDS)
for i in range(10000):
    n=rng.randrange(2,9); bl=rng.choice([0,0,0,3,4,5]); deal=rng.sample(deck,bl+2)
    bb=rng.choice([10,20,50,100,400]); stacks=[rng.randrange(1,20000) for _ in range(n)]
    seat=rng.randrange(n); bets=[rng.randrange(0,3000) for _ in range(n)]
    bets[seat]=rng.randrange(0,min(1000,max(bets)+1))
    tc=max(bets)-bets[seat]
    s=state(n,deal[:2],deal[2:],stacks,bets,tc,bb,rng.randrange(n),seat,rng.choice([[50,30,20],[100],[40,25,15,10,5,3,2,0]]),rng.choice([0,20,100]))
    # Exercise unavailable raises, short all-ins, and memory continuity.
    if i%3==0: s.legal_actions=[a for a in s.legal_actions if a.kind!=ActionKind.RAISE]
    mem=b'' if i%5==0 or not memories else memories[-1]
    start=time.perf_counter_ns(); cpu=time.process_time_ns()
    action,memory=agent.act(s,mem)
    cpus.append((time.process_time_ns()-cpu)/1000); timings.append((time.perf_counter_ns()-start)/1000)
    offered={a.kind:a for a in s.legal_actions}
    assert action.kind in offered,(action,s.__dict__)
    if action.kind==ActionKind.RAISE:
        assert isinstance(action.amount,int)
        assert offered[action.kind].min_amount<=action.amount<=offered[action.kind].max_amount
    assert isinstance(memory,bytes) and len(memory)<16384
    memories.append(memory)
print('Legal randomized SDK decisions:',len(timings),'max memory:',max(map(len,memories)))
for name,data in [('wall_us',timings),('cpu_us',cpus)]:
    data.sort(); print(name,{k:round(data[min(len(data)-1,int(q*len(data)))],1) for k,q in [('p50',.5),('p99',.99),('p999',.999),('max',1)]})

# Public-event accounting: raises are street totals, calls are chip increments.
s=state(n=3,stacks=[500,500,100],bets=[200,200,0],to_call=0)
s.pot=1300
s.events=[Event('hand',amount=20),Event('blind',seat=0,amount=50),Event('blind',seat=1,amount=100),Event('raise',seat=2,amount=300),Event('call',seat=0,amount=250),Event('call',seat=1,amount=200),Event('board',cards=['Ah','Kd','3c']),Event('raise',seat=0,amount=200),Event('call',seat=1,amount=200),Event('fold',seat=2)]
m=bot.observe(s,b'')
assert m['c']=={'0':500,'1':500,'2':300},m
assert m['b']=={'0':200,'1':200},m
# Heads-up winner-take-all ICM must reduce exactly to eligible-pot chip odds.
s=state(n=2,stacks=[100,1000],bets=[0,1000],to_call=100,payout=[100])
s.pot=1100
req=bot.call_threshold(s,s.seats,0,s.seats[1],100,300,[100])
assert math.isclose(req,.25,abs_tol=1e-10),req
print('Contribution and side-pot accounting: passed')
