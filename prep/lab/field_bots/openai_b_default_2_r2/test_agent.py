"""SDK-only correctness, numerical checks, and CPU-budget stress tests.
No simulator internals are imported or inspected.
"""
import itertools
import json
import marshal
import os
import random
import statistics
import sys
import time
from types import SimpleNamespace as NS

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'../../..'))
sys.path.insert(0,os.path.join(ROOT,'lab/fake_sdk'))
sys.path.insert(0,os.path.dirname(__file__))
import agent as bot
from poker_agent_sdk import State,Seat,Event,Config,LegalAction,ActionKind


def icm_reference(stacks,hero,payouts):
    if stacks[hero] <= 0:
        place=sum(x>0 for i,x in enumerate(stacks) if i!=hero)
        return payouts[place] if place<len(payouts) else 0
    def rec(remaining,place,prob):
        total=sum(stacks[i] for i in remaining)
        ans=0
        for i in remaining:
            p=prob*stacks[i]/total
            if i==hero:
                ans+=p*(payouts[place] if place<len(payouts) else 0)
            else:
                ans+=rec([j for j in remaining if j!=i],place+1,p)
        return ans
    return rec([i for i,x in enumerate(stacks) if x>0],0,1.)


def test_icm():
    rng=random.Random(172)
    for n in range(2,9):
        for payouts in ([50,30,20],[100],[50,25,15,7,3],[1]*8):
            stacks=[rng.randrange(100,6000) for _ in range(n)]
            for i in range(n):
                actual=bot.icm(stacks,i,payouts)
                expected=icm_reference(stacks,i,payouts)
                assert abs(actual-expected)<1e-8,(n,stacks,payouts,i,actual,expected)
    assert bot.icm([0,4000,6000],0,[50,30,20])==20
    assert bot.icm([0,4000,6000,1000],0,[50,30,20])==0
    assert abs(bot.joint_equity([.5,.5],True)-1/3)<1e-10
    assert abs(bot.sidepot_equity({1:.5,2:.8},[1000,100,1000],0,0)-(.4*300+.8*1800)/2100)<.03
    assert bot.joint_equity([.37,.37],draw_p=.32)>.32
    ids=bot.CARD_ID
    assert .34<bot.shared_draw_probability([ids['As'],ids['Ks']],[ids['2s'],ids['7s'],ids['Td']])<.36
    assert bot.shared_draw_probability([ids['Ac'],ids['Kh']],[ids['2s'],ids['7s'],ids['Td']])==0
    seats=[Seat(0,5000,0,'active'),Seat(1,5000,0,'active'),Seat(2,1,0,'active'),Seat(3,1,0,'active')]
    assert bot.shove_threshold(seats,0,1,30,[50,30,20])>.78
    assert abs(bot.shove_threshold(seats,0,1,30,[100])-5000/10030)<.001
    c=bot.eval7.Card
    hero=[c('Ks'),c('Kh')];board=[c(x) for x in ['2c','7d','8h','9s','Jc']]
    stronger=((c('As'),c('Ah')),1.);weaker=((c('3s'),c('3h')),1.)
    assert abs(bot.eval7.py_hand_vs_range_exact(hero,[stronger]*9+[weaker],board)-.1)<1e-6


def test_events():
    seats=[Seat(i,2000,0,'active') for i in range(3)]
    cfg=Config(payouts=[50,30,20],decision_ms=1,time_bank_ms=100,memory_bytes=65536)
    st=State(seat=0,seats=seats,cards=['As','Ah'],board=['3c','7s','Th'],pot=280,to_call=0,button=2,
             hand_number=1,blinds=[10,20],players_remaining=3,config=cfg,events=[
                 Event('hand',amount=1),Event('blind',0,10),Event('blind',1,20),
                 Event('raise',2,60),Event('call',0,50),Event('call',1,40),
                 Event('board',cards=['3c','7s','Th']),Event('check',0),Event('raise',1,100),
                 Event('fold',2)])
    m,ix=bot.update_memory(st,b'')
    assert m['d']['in']==[60,160,60],m
    assert m['d']['rc']==[1,1,0,0]
    assert m['stats'][2][1:3]==[1,1]
    st.events=[]
    old=marshal.dumps(m)
    m2,_=bot.update_memory(st,old)
    assert m2['stats']==m['stats']


def test_decisions():
    cfg=Config(payouts=[50,30,20],decision_ms=1,time_bank_ms=100,memory_bytes=65536)
    # Equal leaders on the bubble, with two almost-busted players: AK folds to
    # the other leader's shove despite having good chip equity.
    seats=[Seat(0,4000,1000,'active'),Seat(1,0,5000,'all_in'),
           Seat(2,1,0,'folded'),Seat(3,1,0,'folded')]
    d=bot.fresh_hand(4,1);d['rc'][0]=2;d['lr'][0]=1
    d['pr'][1]=2;d['v']=3;d['in']=[1000,5000,0,0]
    m={'ids':[0,1,2,3],'stats':[[30,30,30]+[0]*9 for _ in range(4)],'d':d}
    st=State(seat=0,cards=['As','Kh'],board=[],pot=6000,to_call=4000,seats=seats,
             button=0,hand_number=1,blinds=[250,500],players_remaining=4,config=cfg,
             events=[],legal_actions=[LegalAction(ActionKind.CALL),LegalAction(ActionKind.FOLD)],time_bank_ms=100)
    a=bot.Agent()
    action,_=a.act(st,marshal.dumps(m))
    assert bot.kind(action)=='fold',action
    # A royal flush on the board is a three-way split, not 0.5 squared.
    st.cards=['2c','3d'];st.board=['Ts','Js','Qs','Ks','As']
    st.seats=[Seat(i,1000,0,'active') for i in range(3)]
    st.pot=600;st.to_call=100;st.players_remaining=3;st.button=2
    d=bot.fresh_hand(3,1);d['st']=3;d['in']=[100,200,200];d['lr'][3]=1
    m={'ids':[0,1,2],'stats':[[30,10,5]+[0]*9 for _ in range(3)],'d':d}
    action,_=a.act(st,marshal.dumps(m))
    assert bot.kind(action)=='call',action
    for bank in (0,5,30,100):
        st.time_bank_ms=bank
        action,_=a.act(st,marshal.dumps(m))
        assert bot.kind(action)=='call',action


def stress(count=6000,scale=1.,short=False):
    rng=random.Random(77331)
    a=bot.Agent()
    cpu=[];wall=[];stage_cpu={i:[] for i in [0,3,4,5]}
    actions={}
    errors=[]
    original=a.decide
    if scale != 1:
        anchor=time.perf_counter_ns()
        bot.time=NS(perf_counter_ns=lambda:anchor+int((time.perf_counter_ns()-anchor)*scale))
    def checked(*args,**kw):
        try:return original(*args,**kw)
        except Exception as e:
            errors.append(repr(e));raise
    a.decide=checked
    for k in range(count):
        n=rng.randrange(2,9)
        bb=rng.choice([80,120,200,300,400,600]) if short else 20
        stage=rng.choice([0,0,0,3,4,5])
        cards=rng.sample(list(bot.CARD_ID),stage+2)
        # Nonconsecutive IDs test that IDs are not mistaken for list indexes.
        ids=sorted(rng.sample(range(20),n))
        me=rng.randrange(n)
        stacks=[rng.randrange(1,20*bb if short else 12000) for _ in ids]
        bets=[rng.randrange(0,5)*bb if stage==0 else rng.randrange(0,5)*bb*5 for _ in ids]
        maxbet=max(bets)
        call=min(stacks[me],maxbet-bets[me])
        legal=[LegalAction(ActionKind.CALL),LegalAction(ActionKind.FOLD)] if call else [LegalAction(ActionKind.CHECK)]
        if rng.random()<.85:
            top=stacks[me]+bets[me]
            low=min(top,maxbet+max(bb,maxbet//2))
            legal.append(LegalAction(ActionKind.RAISE,low,top))
        seats=[Seat(sid,stacks[i],bets[i],'active') for i,sid in enumerate(ids)]
        for i in range(n):
            if i!=me and rng.random()<.13:
                seats[i].status='all_in';seats[i].stack=0
            elif i!=me and rng.random()<.2:
                seats[i].status='folded'
        if not any(t.status in ('active','all_in') for i,t in enumerate(seats) if i!=me):
            seats[(me+1)%n].status='active'
        d=bot.fresh_hand(n,k)
        d['st']=0 if stage==0 else stage-2
        d['in']=[max(bb,x)+rng.randrange(0,5)*bb*2 for x in bets]
        d['bet']=bets[:];d['mx']=maxbet
        d['board']=cards[2:]
        for street in range(d['st']+1):
            for j in range(n):
                ac=rng.choice([0,1,2,4])
                d['a'][street][j]=ac
                if ac==4:
                    d['rc'][street]+=1;d['r'][street][j]+=1
                    d['lr'][street]=j
                    if street==0:
                        d['pr'][j]=d['rc'][0]
                        d['jam'][j]=bets[j]
                if street==0 and ac in (2,4):
                    d['v']|=1<<j
                    if ac==2:d['pc'][j]=max(1,d['rc'][0])
        stats=[]
        for i in ids:
            nh=rng.randrange(1,100)
            vp=rng.randrange(nh+1);pr=rng.randrange(vp+1)
            stats.append([nh,vp,pr]+[rng.randrange(10) for _ in range(7)])
        m={'ids':ids,'stats':stats,'d':d}
        s=State(seat=ids[me],cards=cards[:2],board=cards[2:],seats=seats,pot=sum(d['in']),
                to_call=call,button=rng.choice(ids),hand_number=k,players_remaining=n,
                blinds=[bb//2,bb],config=Config(payouts=rng.choice([[50,30,20],[100],[50,25,15,10]]),
                memory_bytes=65536,decision_ms=1,time_bank_ms=100),events=[],legal_actions=legal,
                time_bank_ms=100)
        mem=marshal.dumps(m)
        t=time.perf_counter_ns();ct=time.thread_time_ns()
        action,memory=a.act(s,mem)
        dt=time.perf_counter_ns()-t;cd=time.thread_time_ns()-ct
        wall.append(dt/1000);cpu.append(cd/1000);stage_cpu[stage].append(cd/1000)
        la={bot.kind(x):x for x in legal};ka=bot.kind(action)
        assert ka in la,(ka,la)
        if ka=='raise':
            assert isinstance(action.amount,int)
            assert la[ka].min_amount<=action.amount<=la[ka].max_amount
        assert len(memory)<16000
        assert marshal.loads(memory)['d']['h']==k
        actions[ka]=actions.get(ka,0)+1
    assert not errors,errors[:10]
    def summary(v):
        v=sorted(v)
        return {'p50':round(statistics.median(v),1),'p99':round(v[int(len(v)*.99)],1),
                'p999':round(v[int(len(v)*.999)],1),'max':round(max(v),1)}
    return {'cases':count,'errors':errors,'actions':actions,'speed_factor':scale,
            'cpu_us':summary(cpu),'scaled_cpu_us':summary([x*scale for x in cpu]),
            'wall_us':summary(wall),'cpu_by_board_length':{k:summary(v) for k,v in stage_cpu.items()}}


if __name__=='__main__':
    test_icm();test_events();test_decisions()
    result=stress(int(sys.argv[1]) if len(sys.argv)>1 else 6000,
                  float(sys.argv[2]) if len(sys.argv)>2 else 1.,len(sys.argv)>3 and sys.argv[3]=='short')
    print(json.dumps(result,indent=2))
