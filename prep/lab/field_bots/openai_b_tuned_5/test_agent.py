"""SDK-only legality, poker invariants, memory, and CPU budget checks."""
import importlib.util
import json
import marshal
from pathlib import Path
import random
import statistics
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'fake_sdk'))
import poker_agent_sdk as sdk
spec = importlib.util.spec_from_file_location('tested_agent', ROOT/'agent.py')
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)

def state(cards=('As','Ah'), board=(), cost=20, stack=1980, pot=60, seat=0, n=2, lo=60, hi=None):
    hi = stack if hi is None else hi
    legal = [sdk.LegalAction(sdk.ActionKind.FOLD),sdk.LegalAction(sdk.ActionKind.CALL)] if cost else [sdk.LegalAction(sdk.ActionKind.CHECK)]
    if hi >= lo:
        legal.append(sdk.LegalAction(sdk.ActionKind.RAISE,lo,hi))
    seats = [sdk.Seat(i, stack if i == seat else 2000,0 if i == seat else cost,'active') for i in range(n)]
    events = [sdk.Event('hand',amount=1)]
    if board:
        events += [sdk.Event('board',cards=list(board[:3]))]
        if len(board)>3: events += [sdk.Event('board',cards=[board[3]])]
        if len(board)>4: events += [sdk.Event('board',cards=[board[4]])]
    if cost:
        events += [sdk.Event('raise',seat=(seat+1)%n,amount=cost)]
    return sdk.State(seat=seat,cards=list(cards),board=list(board),pot=pot,to_call=cost,
                     legal_actions=legal,seats=seats,button=n-1,blinds=[10,20],hand_number=1,
                     config=sdk.Config(payouts=[50,30,20,0,0,0,0,0],memory_bytes=65536,decision_ms=1),
                     events=events,history=events,players_remaining=n,phase='betting',time_bank_ms=100)

def legal_action(s,a):
    offered = next((x for x in s.legal_actions if x.kind==a.kind),None)
    return offered is not None and (a.kind != sdk.ActionKind.RAISE or
        isinstance(a.amount,int) and offered.min_amount<=a.amount<=offered.max_amount)

class Tests(unittest.TestCase):
    def setUp(self): self.bot=bot.Agent()

    def test_nuts_never_fold(self):
        s=state(('As','Ks'),('Qs','Js','Ts','2h','3d'),cost=1900,pot=2000)
        a,_=self.bot.act(s,b'')
        self.assertNotEqual(a.kind,sdk.ActionKind.FOLD)

    def test_aces_reraise(self):
        a,_=self.bot.act(state(),b'')
        self.assertEqual(a.kind,sdk.ActionKind.RAISE)

    def test_no_free_folds(self):
        for board in [[],['As','Ks','Qs'],['As','Ks','Qs','Js','Ts']]:
            s=state(('2c','3d'),board,cost=0,hi=0)
            a,_=self.bot.act(s,b'')
            self.assertEqual(a.kind,sdk.ActionKind.CHECK)

    def test_exact_raise_bound(self):
        s=state(lo=57,hi=57)
        a,_=self.bot.act(s,b'')
        self.assertTrue(legal_action(s,a))
        self.assertEqual(a.amount,57)

    def test_pool_memory(self):
        s=state()
        a,mem=self.bot.act(s,b'')
        s.events=[]
        b,mem2=bot.Agent().act(s,mem)
        self.assertEqual(marshal.loads(mem),marshal.loads(mem2))
        self.assertLess(len(mem),16384)
        self.assertTrue(legal_action(s,b))

    def test_maniac_learning(self):
        s=state()
        s.events=[sdk.Event('hand',amount=1)] + [sdk.Event('raise',seat=1,amount=v) for v in [40,80,120,160,200,240]]
        m=bot.update(s,b'')
        self.assertTrue(bot.maniac(m['p'][1]))
        self.assertEqual(bot.width(m,1),1.0)

    def test_icm(self):
        for stacks in [[2000]*8,[7000,5000,2500,1500],[400,600,1000],[100,100]]:
            values=[bot.icm_value(stacks,i,[50,30,20]) for i in range(len(stacks))]
            self.assertAlmostEqual(sum(values),sum([50,30,20][:len(stacks)]))
        self.assertEqual(bot.icm_value([0,1000,1000],0,[50,30,20]),20)

    def test_royal_board_call(self):
        s=state(('2c','3d'),('As','Ks','Qs','Js','Ts'),cost=1900,pot=1905,hi=0)
        a,_=self.bot.act(s,b'')
        self.assertEqual(a.kind,sdk.ActionKind.CALL)

    def test_locked_board_call(self):
        for board in [('As','Ah','Ac','Ad','Kc'),('2s','2h','2c','2d','Ac'),('As','Kh','Qd','Jc','Ts')]:
            s=state(('3c','4d'),board,cost=1900,pot=1905,hi=0)
            a,_=self.bot.act(s,b'')
            self.assertEqual(a.kind,sdk.ActionKind.CALL)
        board=[bot.CARDS[c] for c in ('As','Ks','Qs','Jh','Td')]
        self.assertFalse(bot.locked_board(board))

    def test_single_offered_action(self):
        for k in sdk.ActionKind:
            s=state(('7c','2d'),cost=5,stack=13,lo=13,hi=13)
            s.legal_actions=[sdk.LegalAction(k,13,13)]
            a,_=self.bot.act(s,b'')
            self.assertTrue(legal_action(s,a))

    def test_icm_bubble_risk(self):
        s=state(cost=5000,stack=5000,pot=5020,n=4,hi=0)
        s.seats[1].stack=5000
        for seat in s.seats[2:]:
            seat.stack=500
            seat.status='folded'
        q=bot.icm_call_threshold(s,s.seats[0],s.seats[1],5000)
        self.assertGreater(q,.65)
        self.assertLess(q,1)

    def test_threebet_ranges(self):
        s=state(n=8)
        s.events=[sdk.Event('hand',amount=1),sdk.Event('raise',seat=3,amount=50)]
        m=bot.update(s,b'')
        open_width=bot.width(m,3)
        s.events=[sdk.Event('raise',seat=4,amount=160)]
        m=bot.update(s,marshal.dumps(m))
        self.assertEqual(m['rl'][4],2)
        self.assertEqual(m['p'][4][14],1)
        self.assertLess(bot.width(m,4),open_width*.65)
        s.events=[sdk.Event('raise',seat=3,amount=410)]
        m=bot.update(s,marshal.dumps(m))
        self.assertLess(bot.width(m,3),.10)

    def test_calls_are_not_threebets(self):
        s=state(n=8)
        s.events=[sdk.Event('hand',amount=1),sdk.Event('raise',seat=3,amount=50),
                  sdk.Event('call',seat=4,amount=50)]
        m=bot.update(s,b'')
        self.assertEqual(m['p'][4][14],0)
        self.assertEqual(m['p'][4][15],1)

    def test_normal_heads_up_opens_are_not_maniac(self):
        s=state(n=2)
        s.events=[]
        for hand in range(10):
            s.events += [sdk.Event('hand',amount=hand+1),
                sdk.Event('raise' if hand < 8 else 'fold',seat=1,amount=40)]
        m=bot.update(s,b'')
        self.assertFalse(bot.maniac(m['p'][1]))
        self.assertEqual(m['p'][1][16],10)
        self.assertEqual(m['p'][1][17],8)

    def test_short_heads_up_shove_range(self):
        s=state(n=2,cost=160)
        s.seats[1].stack=0
        s.seats[1].status='all_in'
        m=bot.update(s,b'')
        self.assertGreater(bot.width(m,1),.70)

    def test_large_event_batch(self):
        s=state(n=8,cost=20)
        s.events=[sdk.Event('hand',amount=1)]
        s.events += [sdk.Event('raise',seat=1+i%2,amount=20*(i+2)) for i in range(400)]
        t=time.process_time_ns()
        a,mem=self.bot.act(s,b'')
        elapsed=(time.process_time_ns()-t)/1000
        self.assertTrue(legal_action(s,a))
        self.assertLess(elapsed*2.5,1000)
        print(json.dumps({'400_events_cpu_us':elapsed,'scaled_2.5':elapsed*2.5}))

    def test_randomized_legal_and_timing(self):
        rng=random.Random(724903)
        cpu=[]
        for i in range(12000):
            cards=rng.sample(list(bot.CARDS),7)
            length=rng.choice([0,0,0,3,4,5])
            stack=rng.randint(1,16000)
            cost=rng.choice([0,rng.randint(1,stack)])
            n=rng.randint(2,8)
            seat=rng.randrange(n)
            s=state(cards[:2],cards[2:2+length],cost,stack,max(cost+10,rng.randint(20,16000)),
                    seat=seat,n=n,lo=rng.randint(1,stack),hi=stack)
            for other in s.seats:
                if other.seat != seat and other.seat != (seat+1)%n:
                    other.status=rng.choice(['active','active','folded','all_in'])
            if i%3==0: s.legal_actions=[a for a in s.legal_actions if a.kind!=sdk.ActionKind.RAISE]
            t=time.process_time_ns()
            a,mem=self.bot.act(s,b'')
            cpu.append((time.process_time_ns()-t)/1000)
            self.assertTrue(legal_action(s,a),(s.cards,s.board,a,s.legal_actions))
            self.assertLess(len(mem),16384)
        cpu.sort()
        print(json.dumps({'decisions':len(cpu),'cpu_us':{'p50':cpu[len(cpu)//2],
              'p99':cpu[int(len(cpu)*.99)],'max':max(cpu)},
              'p99_scaled_2.5':cpu[int(len(cpu)*.99)]*2.5}))
        self.assertLess(cpu[int(len(cpu)*.999)]*2.5,1000)

if __name__=='__main__': unittest.main()
