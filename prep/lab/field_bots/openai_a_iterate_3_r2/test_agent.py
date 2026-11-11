"""SDK-only legality, equity, memory and CPU-time checks. Does not import the simulator."""
import itertools, os, pickle, random, statistics, sys, time
from types import SimpleNamespace
sys.path.insert(0,os.path.abspath(os.path.join(os.path.dirname(__file__),'../../fake_sdk')))
import poker_agent_sdk as sdk
from poker_agent_sdk import ActionKind as K
import agent

def fixture(rng, n, street, call):
    cards=rng.sample(agent.NAMES,2+([0,3,4,5][street]))
    hs=rng.randrange(40,4000); bet=rng.randrange(0,100)
    cost=min(hs,call)
    seats=[sdk.Seat(i,hs if i==0 else rng.randrange(0,4000),bet if i==0 else bet+cost,
                    'active' if i==0 or rng.random()>.12 else 'all_in') for i in range(n)]
    legal=[sdk.LegalAction(K.CHECK if not cost else K.FOLD)]
    if cost: legal.append(sdk.LegalAction(K.CALL))
    if hs>cost+20: legal.append(sdk.LegalAction(K.RAISE,bet+cost+20,bet+hs))
    events=[sdk.Event('hand',amount=1),sdk.Event('blind',seat=1,amount=20)]
    if street:
        events.extend([sdk.Event('raise',seat=i,amount=50) for i in range(1,n)])
        events.append(sdk.Event('call',seat=0,amount=50))
        events.append(sdk.Event('board',cards=cards[2:5]))
        for st in range(1,street):
            events.extend([sdk.Event('check',seat=i) for i in range(n)])
            events.append(sdk.Event('board',cards=cards[4+st:5+st]))
        if cost: events.append(sdk.Event('raise',seat=n-1,amount=bet+cost))
    elif cost>20: events.append(sdk.Event('raise',seat=n-1,amount=bet+cost))
    return sdk.State(seat=0,cards=cards[:2],board=cards[2:],pot=max(cost*n,rng.randrange(40,3000)),
        to_call=cost,legal_actions=legal,history=[],phase='betting',seats=seats,
        button=rng.randrange(n),blind_level=0,blinds=[10,20],hands_until_next_level=20,
        hand_number=1,players_remaining=n,bust_order=[],time_bank_ms=100,events=events,
        config=sdk.Config(table_id='test',seat=0,variant='holdem',players=n,starting_stack=2000,
            blinds=[[10,20]],hands_per_level=20,hand_cap=250,payouts=[50,30,20,0,0,0,0,0],
            decision_ms=1,time_bank_ms=100,memory_bytes=65536))

def check():
    if '--slow-clock' in sys.argv:
        origin=time.perf_counter_ns()
        agent.time=SimpleNamespace(perf_counter_ns=lambda:origin+int((time.perf_counter_ns()-origin)*2.5))
    def made(h,b):
        ids=[agent.CID[x] for x in h.split()]; board=tuple(agent.CARDS[agent.CID[x]] for x in b.split())
        br=[agent.CID[x]//4 for x in b.split()]; bs=[agent.CID[x]%4 for x in b.split()]
        ctx=agent._context(br,bs,board)
        return agent._made(agent.eval7.evaluate(tuple(agent.CARDS[x] for x in ids)+board),ctx,ids[0]//4,ids[1]//4)
    assert made('As Qh','Kc Kd 2s')==0
    assert made('As Qh','Kc Kd 2s 2d 7h')==0
    assert made('As Ah','Kc Kd 2s')>=1.3
    assert made('As Kh','Ac Kd 2s')==2
    assert made('2c 2h','Ac Kd 2s')==3
    for stacks in ([2000]*8,[4000,3000,2000,1000],[9999,1,10],[0,4000,2000],[4000,0,0],[0,4000]):
        p=[50,30,20]+[0]*5
        assert abs(sum(agent._icm(stacks,p,i) for i in range(len(stacks)))-sum(p[:len(stacks)]))<1e-6
    assert agent._icm([0,4000,2000],[50,30,20],0)==20
    assert agent._icm([0,4000],[50,30,20],0)==30
    side=fixture(random.Random(2),3,0,980)
    side.pot=2020;side.seats[0].stack=100;side.seats[0].bet=20
    side.events=[sdk.Event('hand',amount=1),sdk.Event('blind',seat=0,amount=20),
                 sdk.Event('raise',seat=1,amount=1000),sdk.Event('call',seat=2,amount=1000)]
    sm=agent._memory(side,b'')
    assert agent._eligible_pot(side,sm,side.seats[0],100)==260
    # A bet total is incremental, whereas a call amount is chips added.
    side.events=side.events+[sdk.Event('raise',seat=2,amount=1800)]
    sm=agent._memory(side,b'')
    assert sm['c']['2'][9]==1800
    assert agent._eligible_pot(side,sm,side.seats[0],100)==260
    side.events=[sdk.Event('stack',seat=1,amount=0),sdk.Event('stack',seat=2,amount=3000),sdk.Event('hand',amount=2)]
    prior=pickle.dumps(sm,protocol=4)
    nxt=agent._memory(side,prior)
    assert nxt['s']['1'][0]==sm['s']['1'][0]
    assert nxt['s']['2'][0]==sm['s']['2'][0]+1
    bot=agent.Agent()
    for board in ('As Ks Qs Js Ts','Ac Kd Qs Jh Tc','Ac Ad Ah As Kc','2c 2d 2h 2s Ac'):
        locked=fixture(random.Random(3),3,3,500)
        locked.cards=['8h','9d'];locked.board=board.split();locked.pot=1000
        locked.seats[0].stack=500;locked.to_call=500
        locked.legal_actions=[sdk.LegalAction(K.FOLD),sdk.LegalAction(K.CALL)]
        assert bot.act(locked,b'')[0].kind==K.CALL,board
    assert agent._legal(locked,'raise',100000).kind==K.CALL
    # Validate the pruned exact river-nut search against all legal hole combos.
    nrng=random.Random(20261106)
    for _ in range(1000):
        ids=nrng.sample(range(52),7)
        board=tuple(agent.CARDS[i] for i in ids[2:]);dead=sum(1<<i for i in ids)
        exact=max(agent.eval7.evaluate(x[0]+board) for x in agent.COMBOS if not x[1]&dead)
        assert agent._river_ceiling(board,dead)==exact,ids
    patterns=['As Ks Qs Js Ts','9s Ts Js Qs 2d','3c 4c 6c 7d 8h','Ac Ad Ah As Kc',
              '9c 9d 9h 9s 2c','Ac Ad Ah Kc Kd','2c 2d 2h As Ks','Ac Ad Kc Kd 2s',
              'As Kd Qc Jh 9h','2h 3h 4h 5h 8h','Ac 2c 3c 4d 5s']
    for text in patterns:
        bi=[agent.CID[c] for c in text.split()];board=tuple(agent.CARDS[i] for i in bi)
        for _ in range(25):
            holes=nrng.sample([i for i in range(52) if i not in bi],2)
            dead=sum(1<<i for i in bi+holes)
            exact=max(agent.eval7.evaluate(x[0]+board) for x in agent.COMBOS if not x[1]&dead)
            assert agent._river_ceiling(board,dead)==exact,(text,holes)
    bubble=fixture(random.Random(4),4,0,2000)
    bubble.seats[0].stack=2000;bubble.seats[0].bet=0
    bubble.seats[1].stack=8000;bubble.seats[1].bet=2000
    for s in bubble.seats[2:]:s.stack=1;s.bet=0;s.status='folded'
    bubble.pot=2000;bubble.to_call=2000
    assert agent._risk(bubble,bubble.seats[0],[bubble.seats[1]],2000)>.35
    rng=random.Random(19); bot=agent.Agent(); walls=[]; cpus=[]
    for i in range(10000):
        st=fixture(rng,rng.randrange(2,9),rng.randrange(4),rng.choice([0,0,20,80,500,2000]))
        st.time_bank_ms=(0,5,20,40,100)[i%5]
        m=agent._memory(st,b'')
        raw=b''
        if i%3<2 and st.board:
            # Also stress the broad ranges and conditioned ranges learned later
            # in a table, rather than testing only first-hand tight ranges.
            for sid,s in m['s'].items():
                if sid=='0': continue
                s[:]=[20,18,16,40,20,5,8,4] if i%3==0 else [20,12,3,4,7,15,8,20]
                m['c'][sid][0]=1;m['c'][sid][3]=0
            st.events=[]
            raw=pickle.dumps(m,protocol=4)
        # Uncaught decision path ensures the production safety guard cannot hide an error.
        kind,size=bot._decide(st,m)
        t=time.perf_counter_ns(); c=time.process_time_ns()
        act,mem=bot.act(st,raw)
        cpus.append((time.process_time_ns()-c)/1000); walls.append((time.perf_counter_ns()-t)/1000)
        offered={a.kind:a for a in st.legal_actions}
        assert act.kind in offered,(act,offered)
        if act.kind==K.RAISE: assert offered[K.RAISE].min_amount<=act.amount<=offered[K.RAISE].max_amount
        assert len(mem)<4096
    for name,v in [('wall_us',walls),('cpu_us',cpus)]:
        v.sort(); print(name,{k:round(v[min(len(v)-1,int(q*len(v)))],1) for k,q in [('p50',.5),('p99',.99),('p999',.999),('max',1)]})
    print('PASS: 10,000 diverse SDK states, strict decision path, legality, ICM, board texture, memory')
if __name__=='__main__':check()
