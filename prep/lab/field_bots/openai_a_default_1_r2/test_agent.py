"""Public-SDK regression and randomized legality tests; no simulator imports."""
import gc,os,random,sys,time,unittest,pickle
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'../../fake_sdk'))
from poker_agent_sdk import State,Seat,Config,Event,LegalAction,ActionKind
from agent import (Agent,icm_value,CARD_NAMES,new_memory,risk_premium,update_memory,
                   street_foldrate,features,board_meta,CARD_ID,COMBO_INDEX,
                   villain_range,profile)


def state(cards=('As','Ad'),board=(),n=2,stack=2000,cost=0,pot=100,can_raise=True,minimum=None):
    hero=0
    villain=1
    bb=20
    seats=[Seat(i,stack,0,'active') for i in range(n)]
    seats[1].bet=cost
    hist=[Event('hand',amount=1),Event('blind',0,10),Event('blind',1,20)]
    for k in (3,4,5):
        if len(board)>=k:
            hist.append(Event('board',cards=list(board[:3] if k==3 else board[k-1:k])))
    if cost:
        hist.append(Event('raise',1,cost))
    kinds=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)] if cost else [LegalAction(ActionKind.CHECK)]
    if can_raise and stack>cost:
        kinds.append(LegalAction(ActionKind.RAISE,minimum or min(stack,cost+20),stack))
    return State(seat=0,cards=list(cards),board=list(board),pot=pot,to_call=cost,
       legal_actions=kinds,history=hist,phase='betting',seats=seats,button=n-1,
       blind_level=1,blinds=[10,20],hands_until_next_level=20,hand_number=1,
       players_remaining=n,bust_order=[],config=Config(table_id='test',seat=0,variant='holdem',players=n,
        starting_stack=2000,blinds=[[10,20]],hands_per_level=20,hand_cap=250,payouts=[50,30,20,0,0,0,0,0],
        decision_ms=1,time_bank_ms=100,memory_bytes=65536),time_bank_ms=100,events=hist)


class Tests(unittest.TestCase):
    def legal(self,s,m=b''):
        a,m=Agent().act(s,m)
        offered=next((x for x in s.legal_actions if x.kind==a.kind),None)
        self.assertIsNotNone(offered)
        if a.kind==ActionKind.RAISE:
            self.assertIs(type(a.amount),int)
            self.assertLessEqual(a.amount,offered.max_amount)
            self.assertGreaterEqual(a.amount,offered.min_amount)
        self.assertLessEqual(len(m),16000)
        return a,m
    def test_nuts_call_allin(self):
        s=state(('As','Ks'),('Qs','Js','Ts','2d','3c'),n=5,cost=2000,pot=10000)
        self.assertEqual(self.legal(s)[0].kind,ActionKind.CALL)
    def test_board_nuts_cheap_split(self):
        s=state(('2s','3d'),('As','Ks','Qs','Js','Ts'),n=8,cost=20,pot=1000)
        self.assertNotEqual(self.legal(s)[0].kind,ActionKind.FOLD)
    def test_board_nuts_large_split(self):
        s=state(('2s','3d'),('As','Ks','Qs','Js','Ts'),n=8,cost=2000,pot=2010)
        self.assertEqual(self.legal(s)[0].kind,ActionKind.CALL)
    def test_unbeatable_hole_cards(self):
        s=state(cost=2000,pot=2010)
        self.assertEqual(self.legal(s)[0].kind,ActionKind.CALL)
    def test_trash_folds_deep_shove(self):
        s=state(('7s','2d'),cost=2000,pot=2010)
        self.assertEqual(self.legal(s)[0].kind,ActionKind.FOLD)
    def test_dominated_ace_folds_deep_shove(self):
        s=state(('As','Qd'),cost=2000,pot=2010)
        self.assertEqual(self.legal(s)[0].kind,ActionKind.FOLD)
    def test_short_raise_boundary(self):
        s=state(stack=27,cost=20,minimum=27)
        self.legal(s)
    def test_same_board_cache(self):
        s=state(('Ac','Kd'),('Ks','7h','2d'),n=3)
        a,m=self.legal(s)
        s.events=[]
        self.legal(s,m)
        s.board.append('3s'); s.history.append(Event('board',cards=['3s']));s.events=[s.history[-1]]
        self.legal(s,m)
    def test_folder_exploit(self):
        s=state(('7s','2d'),cost=10,pot=30)
        s.history=s.events=s.history[:3]
        s.seats[0].bet=10;s.seats[1].bet=20
        s.legal_actions[-1].min_amount=40
        d=new_memory(s)
        d['s'][1][0]=10
        self.assertEqual(self.legal(s,pickle.dumps(d))[0].kind,ActionKind.RAISE)
    def test_short_blind_and_float_icm(self):
        s=state(('2c','3c'),n=3,stack=1535,cost=200,pot=170)
        s.seats[1].stack=14295;s.seats[1].bet=100
        s.seats[2].stack=0;s.seats[2].bet=70;s.seats[2].status='all_in'
        s.blinds=[100,200]
        s.history=s.events=[Event('hand',amount=1),Event('blind',1,100),Event('blind',2,70)]
        self.legal(s)
    def test_memory_limits_and_recovery(self):
        s=state()
        s.config.memory_bytes=128
        a,m=Agent().act(s,b'')
        self.assertLessEqual(len(m),128)
        self.legal(state(),b'broken memory')
    def test_gc_restored(self):
        before=gc.isenabled()
        self.legal(state())
        self.assertEqual(gc.isenabled(),before)
    def test_bubble_risk(self):
        s=state(n=4,cost=2000,pot=2010)
        self.assertGreater(risk_premium(s,s.seats[0],s.seats[1],2010,2000),.08)
    def test_icm(self):
        self.assertAlmostEqual(icm_value([2000]*8,0,[50,30,20,0,0,0,0,0]),12.5)
        self.assertAlmostEqual(icm_value([2000]*3,0,[50,30,20]),100/3)
        self.assertAlmostEqual(icm_value([1000,3000],0,[50,30]),35)
        self.assertEqual(icm_value([0,3000,1000],0,[50,30,20]),20)
        self.assertEqual(icm_value([2.2e-13,16000,0],0,[50,30,20]),20)
        self.assertAlmostEqual(icm_value([1000]*8,0,[40,25,20,15,0,0,0,0]),12.5)
    def test_first_bets_do_not_count_as_responses(self):
        s=state(n=3)
        d=new_memory(s)
        s.events=[]
        for hand in range(1,13):
            s.events.extend([Event('hand',amount=hand),Event('board',cards=['2c','7d','Jh']),
                             Event('raise',1,100),Event('fold',0)])
        for hand in range(13,17):
            s.events.extend([Event('hand',amount=hand),Event('board',cards=['2c','7d','Jh']),
                             Event('raise',0,100),Event('fold',1)])
        update_memory(d,s)
        self.assertEqual(d['s'][1][24],0)
        self.assertEqual(d['s'][1][21],4)
        self.assertGreater(street_foldrate(d['s'][1],3),.70)

    def test_late_open_range_heads_up(self):
        s=state(n=2)
        prior=profile(new_memory(s)['s'][1],2)
        width=villain_range(1,s,[(1,44,20)],{},prior,[1,0])
        self.assertGreater(width,.75)

    def test_flushes_have_distinct_raise_strength(self):
        meta=board_meta(tuple(CARD_ID[c] for c in ('Th','6d','7h','4d','5h')))
        nut=features(CARD_ID['Ah'],CARD_ID['Jh'],meta)[0]
        queen=features(CARD_ID['Qh'],CARD_ID['6h'],meta)[0]
        self.assertGreater(nut,.99)
        self.assertLess(queen,.93)

    def test_new_board_keeps_nut_flush_support(self):
        s=state(('Qh','6h'),('Th','6d','7h'),n=2)
        _,memory=self.legal(s)
        s.board+=['4d','5h']
        s.history.extend([Event('board',cards=['4d']),Event('board',cards=['5h'])])
        s.events=s.history[-2:]
        _,memory=self.legal(s,memory)
        d=pickle.loads(memory)
        nut=COMBO_INDEX[CARD_ID['Ah']][CARD_ID['Jh']]
        self.assertTrue(any(nut in record[1] for record in d['r'].values()))

    def test_randomized_legality(self):
        rng=random.Random(127)
        for i in range(2000):
            cs=rng.sample(CARD_NAMES,7)
            k=rng.choice([0,3,4,5]); n=rng.randrange(2,9);stack=rng.randrange(1,10000)
            cost=rng.choice([0,rng.randrange(1,12000)])
            s=state(cs[:2],cs[2:2+k],n,stack,cost,rng.randrange(30,40000),bool(i%3))
            self.legal(s)

if __name__=='__main__':unittest.main(verbosity=2)
