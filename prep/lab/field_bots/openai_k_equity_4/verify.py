"""Independent API, legality, equity and performance checks (no simulator imports)."""
import importlib.util
import os
import random
import sys
import time
from types import SimpleNamespace as NS
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0,os.path.join(ROOT,'fake_sdk'))
sys.path.insert(0,os.path.dirname(__file__))
import agent as bot
from poker_agent_sdk import State, Seat, Config, Event, LegalAction, ActionKind


def state(rng,n=2,street=3,stack=1500,bet=0,call=0,hand=1):
    cards=rng.sample(bot._CARD_STR,2+street)
    seats=[Seat(i,stack,bet if i==0 else bet+call,'active') for i in range(n)]
    hist=[Event('hand',amount=hand),Event('blind',seat=0,amount=10),Event('blind',seat=1,amount=20)]
    for i in range(2,n):hist.append(Event('call',seat=i,amount=20))
    hist.append(Event('call',seat=0,amount=10))
    if street:hist.append(Event('board',cards=cards[2:5]))
    if street>3:hist.append(Event('board',cards=cards[5:6]))
    if street>4:hist.append(Event('board',cards=cards[6:7]))
    if call:hist.append(Event('raise',seat=1,amount=bet+call))
    legal=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)] if call else [LegalAction(ActionKind.CHECK)]
    if stack>call:legal.append(LegalAction(ActionKind.RAISE,bet+max(20,2*call),bet+stack))
    cfg=Config(table_id='test',seat=0,variant='holdem',players=n,starting_stack=2000,blinds=[[10,20]],hands_per_level=20,hand_cap=250,payouts=[50,30,20,0,0,0,0,0],decision_ms=1,time_bank_ms=100,memory_bytes=65536)
    return State(seat=0,cards=cards[:2],board=cards[2:],pot=40+20*(n-2)+call,legal_actions=legal,to_call=call,history=hist,phase='betting',variant='holdem',seats=seats,button=n-1,blind_level=1,blinds=[10,20],hands_until_next_level=20,hand_number=hand,players_remaining=n,bust_order=[],config=cfg,time_bank_ms=100,events=hist)


def legal(action,s):
    matches=[a for a in s.legal_actions if a.kind==action.kind]
    assert matches,(action,s.legal_actions)
    if action.kind==ActionKind.RAISE:
        assert type(action.amount)==int
        assert matches[0].min_amount<=action.amount<=matches[0].max_amount,(action,matches)


def main():
    rng=random.Random(64127);a=bot.Agent()
    c=next(c for c in bot._COMBOS if {c[0],c[1]}=={bot._CI['7c'],bot._CI['2d']})
    br=sum(1<<bot._RANKS.index(r) for r in 'TJQK')
    assert bot._draw(c,br,[1,1,1,1])==(False,False)
    c=next(c for c in bot._COMBOS if {c[0],c[1]}=={bot._CI['Tc'],bot._CI['2d']})
    br=sum(1<<bot._RANKS.index(r) for r in 'JQK')
    assert bot._draw(c,br,[1,1,1,0])[1]

    # Fixed hands establish the evaluator's direction and fractional split handling.
    bd=tuple(bot._CARDS[bot._CI[c]] for c in ['As','Ks','Qs','Js','Ts'])
    hero=tuple(bot._CARDS[bot._CI[c]] for c in ['2c','3d'])
    known=sum(1<<bot._CI[c] for c in ['As','Ks','Qs','Js','Ts','2c','3d'])
    pool=[c for c in bot._COMBOS if not c[2]&known]
    assert bot._hu_equity(hero,pool,bd,100)==.5
    assert abs(bot._multi_equity(hero,[pool,pool],bd,known,22,128)-1/3)<1e-8
    assert abs(bot._prize_value([0,8000,0,0],0,[50,30,20,0],[2000]*4)-50/3)<1e-9
    assert bot._prize_value([0,8000,0,0],0,[50,30,20,0],[3000,2000,1000,2000])==30
    assert bot._prize_value([0,8000,0,0],0,[50,30,20,0],[1000,2000,3000,2000])==0
    assert abs(bot._icm([2000]*4,0,[50,30,20,0])-25)<1e-9
    assert abs(sum(bot._icm([1000,4000,200,800],i,[50,30,20,0]) for i in range(4))-100)<1e-9
    assert bot._icm([0,10,10,10],0,[50,30,20,0])==0
    assert bot._icm([0,10,10],0,[50,30,20,0])==20
    assert bot._icm([10,0,0],0,[50,30,20,0])==50
    assert abs(sum(bot._icm([1,2,3,4,5],i,[50,30,20,10,5]) for i in range(5))-115)<1e-9
    # A folded player's money remains in each layer; only live contributors contest it.
    o=[NS(seat=1),NS(seat=2)]
    layers=bot._pot_layers({0:100,1:1000,2:40,3:50},0,100,o)
    assert sum(v for v,_ in layers)==490
    assert layers==[(160,(1,2)),(30,(1,)),(300,(1,))]
    # Winning the side pot can have value even when the short all-in wins the main pot.
    board=tuple(bot._CARDS[bot._CI[c]] for c in ['As','Ad','7c','5d','2h'])
    hero=tuple(bot._CARDS[bot._CI[c]] for c in ['Kc','Kd'])
    allin=next(c for c in bot._COMBOS if {c[0],c[1]}=={bot._CI['Ah'],bot._CI['Ac']})
    deep=next(c for c in bot._COMBOS if {c[0],c[1]}=={bot._CI['Qc'],bot._CI['Qd']})
    known=sum(1<<bot._CI[c] for c in ['As','Ad','7c','5d','2h','Kc','Kd'])
    assert abs(bot._multi_equity(hero,[[allin],[deep]],board,known,1,8,layers=[(.3,3),(.7,2)])-.7)<1e-12
    for width,table in bot._DATA.get('multiway_ranges',{}).items():
        for k in ['AA','22','JTs','72o']:
            for n in range(2,8):
                assert abs(bot._joint_pre(k,[float(width)]*n)-table[k][n-1])<1e-5
    for k in ['AA','KK','AKs','22','72o']:
        assert .05<bot._eq_pre(k,1)<.95
        assert 0<bot._joint_pre(k,[.18,.18])<bot._eq_pre(k,.18)
    times={};worst=0
    for n in range(2,9):
        for street in [0,3,4,5]:
            ts=[];cs=[]
            for j in range(120):
                st=state(rng,n,street,stack=rng.choice([5,20,120,1500,10000]),call=rng.choice([0,0,10,20,100]),hand=j+1)
                # Valid short all-ins also offer a raise below the full minraise.
                if st.to_call>=st.seats[0].stack:st.legal_actions=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)]
                for l in st.legal_actions:
                    if l.kind==ActionKind.RAISE:l.min_amount=min(l.min_amount,l.max_amount)
                start=time.perf_counter_ns();cpu=time.process_time_ns();action,m=a.act(st,b'');ct=time.process_time_ns()-cpu;t=time.perf_counter_ns()-start
                legal(action,st)
                assert len(m)<16000
                ts.append(t/1000);cs.append(ct/1000)
            ts.sort();cs.sort();times[f'{n}p_{street}board']=[round(ts[len(ts)//2],1),round(ts[int(.99*len(ts))],1),round(max(ts),1),round(cs[len(cs)//2],1),round(cs[int(.99*len(cs))],1)]
            worst=max(worst,max(ts))
    # The degraded time-bank path must remain legal with both a cold cache
    # and the previous decision's ranges, including a newly dealt board card.
    for n in range(2,9):
        for j in range(40):
            s=state(rng,n,3,call=rng.choice([0,20,100]),hand=777+j)
            _,cached=a.act(s,b'')
            s.time_bank_ms=0;s.events=[]
            for memory in (b'',cached):
                action,m=a.act(s,memory);legal(action,s)
            nxt=rng.choice([c for c in bot._CARD_STR if c not in s.cards+s.board])
            s.board.append(nxt);s.history.append(Event('board',cards=[nxt]));s.events=[s.history[-1]]
            action,m=a.act(s,cached);legal(action,s)
            assert len(m)<16000
    # A habitual folder's all-in blind is protected; another folder cannot
    # make that player surrender the main pot. Do not auto-steal with 72o.
    s=state(rng,3,0,hand=909)
    s.cards=['7c','2d'];s.button=0;s.pot=30;s.to_call=20
    s.seats=[Seat(0,2000,0,'active'),Seat(1,1990,10,'active'),Seat(2,0,20,'all_in')]
    s.history=[Event('hand',amount=909),Event('blind',seat=1,amount=10),Event('blind',seat=2,amount=20)]
    s.events=s.history
    s.legal_actions=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL),LegalAction(ActionKind.RAISE,40,2000)]
    stats=[4,0,0,4,4,0,0,0,0,0,0,0,0,0]
    memory=bot.json.dumps({'s':{'1':stats,'2':stats}}).encode()
    action,m=a.act(s,memory)
    assert action.kind==ActionKind.FOLD
    # Memory must produce the same answer in interchangeable agent instances.
    s=state(rng,2,0,hand=99)
    _,m=a.act(s,b'')
    s.events=[]
    x,m1=bot.Agent().act(s,m);y,m2=bot.Agent().act(s,m)
    assert (x.kind,x.amount,m1)==(y.kind,y.amount,m2)
    print('PASS: 3,360 randomized states + 840 low-bank/cache decisions; ties, draws, side pots, ICM, memory isolation')
    print('Latency us [wall median,p99,max; CPU median,p99]:',times)

if __name__=='__main__':main()
