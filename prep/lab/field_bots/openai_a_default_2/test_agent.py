"""Independent contract and strategy regression tests. No simulator imports."""
import itertools
import gc
import marshal
import math
import random
import time
import unittest
from types import SimpleNamespace as NS
from poker_agent_sdk import ActionKind, LegalAction, Seat, State, Event, Config
import agent


def state(cards=('As','Kh'), board=(), call=20, seats=None, button=0, hero=0, hand=1):
    if seats is None:seats=[Seat(0,1980,0,'active'),Seat(1,1960,40,'active')]
    return State(seat=hero,cards=list(cards),board=list(board),pot=60,to_call=call,
                 legal_actions=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL),LegalAction(ActionKind.RAISE,80,1980)],
                 history=[],phase='betting',seats=seats,button=button,blind_level=1,blinds=[10,20],
                 hands_until_next_level=20,hand_number=hand,players_remaining=len(seats),bust_order=[],
                 config=Config(players=len(seats),starting_stack=2000,payouts=[50,30,20,0,0,0,0,0],decision_ms=1,
                               time_bank_ms=100,memory_bytes=65536),events=[],time_bank_ms=100)


class BotTests(unittest.TestCase):
    def assert_legal(self,s,a):
        legal={x.kind:x for x in s.legal_actions}
        self.assertIn(a.kind,legal)
        if a.kind==ActionKind.RAISE:
            self.assertIsInstance(a.amount,int)
            self.assertGreaterEqual(a.amount,legal[a.kind].min_amount)
            self.assertLessEqual(a.amount,legal[a.kind].max_amount)

    def test_all_169_hands_and_equities(self):
        self.assertEqual(len(agent.EQ),169)
        self.assertEqual(set(agent.OPEN),set(agent.EQ))
        for k,row in agent.EQ.items():
            self.assertEqual(len(row),9)
            self.assertTrue(all(0<=x<=1 for x in row))
            self.assertEqual(len(agent.MULTI[k]),7)
            self.assertTrue(all(a>=b for a,b in zip(agent.MULTI[k],agent.MULTI[k][1:])))
        self.assertGreater(agent.MULTI['AA'][6],.25)
        self.assertLess(agent.MULTI['72o'][6],.12)
        self.assertLess(agent.EQ['QQ'][0],.46) # QQ against QQ+/AK is no favorite.
        self.assertEqual(agent.sample_indices(34,320),list(range(34)))
        self.assertEqual(len(set(agent.sample_indices(1326,320))),320)
        for combos,hr in zip(agent.RANGE_COMBOS,agent.RANGES):
            self.assertEqual(len(hr.hands),min(320,len(combos)))
            self.assertEqual(len({(a.mask,b.mask) for (a,b),w in hr.hands}),len(hr.hands))

    def test_icm_prize_conservation_and_guaranteed_money(self):
        for stacks in ([2000]*8,[10000,2000,500],[4000,2000],[0,3000,500],[2500,0,0]):
            payouts=[50,30,20,0,0,0,0,0][:len(stacks)]
            self.assertAlmostEqual(sum(agent.icm(i,list(stacks),payouts) for i in range(len(stacks))),sum(payouts),places=8)
        self.assertEqual(agent.icm(0,[0,1000],[50,30]),30)
        self.assertEqual(agent.icm(0,[0,1000,2000],[50,30,20]),20)
        self.assertAlmostEqual(agent.icm(0,[1000]*8,[50,30,20,0,0,0,0,0]),12.5)

    def test_bubble_requires_more_equity(self):
        ss=[Seat(0,1000,0,'active'),Seat(1,0,1000,'all_in'),Seat(2,50,0,'folded'),Seat(3,2000,0,'folded')]
        s=state(seats=ss,call=1000);s.pot=1100
        th=agent.call_threshold(s,ss[0],[ss[1]],1100,1000)
        self.assertGreater(th,1000/2100+.10)
        s.config.payouts=[100,0,0,0]
        self.assertAlmostEqual(agent.call_threshold(s,ss[0],[ss[1]],1100,1000),1000/2100)

    def test_short_blind_is_free_showdown(self):
        ss=[Seat(0,15730,250,'active'),Seat(1,0,20,'all_in')]
        s=state(cards=('2c','7d'),seats=ss,call=250)
        s.pot=270;s.blinds=[250,500]
        s.events=[Event('hand',amount=1),Event('blind',seat=0,amount=250),Event('blind',seat=1,amount=20)]
        s.legal_actions=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)]
        a,m=agent.Agent().act(s,b'')
        self.assertEqual(a.kind,ActionKind.CALL)

    def test_equity_nuts_and_chopped_board(self):
        ss=[Seat(0,1000,0,'active'),Seat(1,1000,0,'active')]
        s=state(seats=ss)
        d=agent.new_memory();agent.update(s,d)
        d['positions']={0:.5,1:.5}
        hero=[agent.CARDS[c] for c in ('As','Ks')]
        board=[agent.CARDS[c] for c in ('Qs','Js','Ts','2d','3c')]
        q=agent.post_equity(hero,board,[ss[1]],d,2,20,1,time.perf_counter_ns()+1000000)
        self.assertEqual(q,1.)
        hero=[agent.CARDS[c] for c in ('2c','3d')]
        board=[agent.CARDS[c] for c in ('As','Ks','Qs','Js','Ts')]
        q=agent.post_equity(hero,board,[ss[1]],d,2,20,1,time.perf_counter_ns()+1000000)
        self.assertEqual(q,.5)

    def test_paired_boards_and_uncallable_shared_nuts(self):
        board=[agent.CARDS[c] for c in ['Qs','Qd','2c']]
        q,draw,cat=agent.quality(agent.CARDS['As'],agent.CARDS['Qc'],agent.board_info(board))
        self.assertEqual(cat,3);self.assertGreater(q,.9)
        s=state(cards=('2c','3d'),board=('As','Ks','Qs','Js','Ts'),call=1000)
        s.pot=1010
        s.legal_actions=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)]
        a,m=agent.Agent().act(s,b'')
        self.assertEqual(a.kind,ActionKind.CALL)

    def test_side_pot_equity(self):
        opponents=[Seat(1,0,0,'all_in'),Seat(2,1000,0,'active')]
        d={'hero':0,'call':0,'con':{0:1000,1:100,2:1000}}
        result=agent.pot_weighted({1:.3,2:.6},opponents,d)
        expected=(300*(.3*.6**.72)+1800*.6)/2100
        self.assertAlmostEqual(result,expected)
        self.assertGreater(result,.5)

    def test_memory_tracks_events_and_multiple_instances(self):
        s=state();s.events=[Event('hand',amount=1),Event('blind',seat=0,amount=10),Event('blind',seat=1,amount=20),Event('raise',seat=1,amount=40)]
        bot=agent.Agent();a,m=bot.act(s,b'');self.assert_legal(s,a)
        data=marshal.loads(m)
        self.assertEqual(data['con'][1],40)
        self.assertEqual(data['s'][1][2],1)
        s.events=[Event('call',seat=0,amount=30),Event('board',cards=['Ks','8d','2c']),Event('raise',seat=1,amount=100)]
        s.board=['Ks','8d','2c'];s.pot=180;s.to_call=100
        a,m=agent.Agent().act(s,m);self.assert_legal(s,a)
        data=marshal.loads(m)
        self.assertEqual(data['con'][0],40)
        self.assertEqual(data['con'][1],140)
        self.assertEqual(data['rc'],[1,1,0,0])
        self.assertLess(len(m),16000)

    def test_gc_restored_on_exit(self):
        gc.enable()
        agent.Agent().act(state(),b'')
        self.assertTrue(gc.isenabled())
        class Broken(agent.Agent):
            def decide(self,*args):raise RuntimeError('test restoration')
        with self.assertRaises(RuntimeError):Broken().act(state(),b'')
        self.assertTrue(gc.isenabled())
        try:
            gc.disable()
            agent.Agent().act(state(),b'')
            self.assertFalse(gc.isenabled())
        finally:gc.enable()

    def test_general_payout_icm(self):
        stacks=[3500,2500,2000,1800,1600,1500,1200,900]
        for payouts in ([40,25,15,10,5,3,2,0],[50,25,15,10,0,0,0,0],[15,14,13,12,11,10,9,8]):
            self.assertAlmostEqual(sum(agent.icm(i,stacks,payouts) for i in range(8)),sum(payouts),places=8)

    def test_legalizer_all_offered_combinations(self):
        rng=random.Random(15)
        for _ in range(300):
            s=state();free=rng.random()<.5
            s.legal_actions=[LegalAction(ActionKind.CHECK)] if free else [LegalAction(ActionKind.CALL),LegalAction(ActionKind.FOLD)]
            if rng.random()<.8:
                lo=rng.randint(1,100000);hi=lo+rng.randint(0,100000)
                s.legal_actions.append(LegalAction(ActionKind.RAISE,lo,hi))
            for desired in ['fold','check','call','raise']:
                for amount in (-1,0,.99,lo if 'lo' in locals() else 1,10**10):
                    self.assert_legal(s,agent.legalize(s,desired,amount))

    def test_randomized_states_legal_and_small_memory(self):
        rng=random.Random(415)
        deck=list(agent.CARDS)
        for _ in range(1800):
            n=rng.randrange(2,9);ids=sorted(rng.sample(range(30),n));hero=rng.choice(ids)
            boardlen=rng.choice([0,0,0,3,4,5]);cs=rng.sample(deck,2+boardlen)
            stacks=[rng.randrange(1,20000) for i in ids]
            free=rng.random()<.4;call=0 if free else rng.randint(1,stacks[ids.index(hero)])
            ss=[Seat(i,stack,0,'active' if i==hero or rng.random()<.65 else 'folded') for i,stack in zip(ids,stacks)]
            if all(p.status=='folded' for p in ss if p.seat!=hero):next(p for p in ss if p.seat!=hero).status='active'
            s=state(cards=cs[:2],board=cs[2:],call=call,seats=ss,hero=hero,button=rng.choice(ids))
            s.pot=rng.randrange(20,12000)
            s.time_bank_ms=rng.choice([0,5,50,100])
            s.config.decision_ms=rng.choice([.4,1,2])
            s.blinds=[rng.choice([10,20,50,100,200]),rng.choice([20,40,100,200,400])]
            s.legal_actions=[LegalAction(ActionKind.CHECK)] if free else [LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)]
            stack=next(p.stack for p in ss if p.seat==hero)
            if rng.random()<.85:s.legal_actions.append(LegalAction(ActionKind.RAISE,min(stack,max(1,call*2)),stack))
            s.events=[Event('hand',amount=1)]
            actors=[p for p in ss if p.seat!=hero and p.status=='active']
            if rng.random()<.65:
                for j in range(rng.randint(1,4)):
                    p=rng.choice(actors)
                    s.events.append(Event('raise',seat=p.seat,amount=(j+2)*s.blinds[1]))
            if boardlen:s.events.append(Event('board',cards=cs[2:5]))
            if boardlen>3:s.events.append(Event('board',cards=cs[5:6]))
            if boardlen>4:s.events.append(Event('board',cards=cs[6:7]))
            if boardlen and rng.random()<.75:
                for p in actors:
                    k=rng.choice(['raise','call','check'])
                    p.bet=0 if k=='check' else rng.randint(1,max(1,s.pot//2))
                    s.events.append(Event(k,seat=p.seat,amount=p.bet))
            s.config.payouts=rng.choice([[100,0,0,0,0,0,0,0],[50,30,20,0,0,0,0,0],[70,30,0,0,0,0,0,0]])
            a,m=agent.Agent().act(s,b'');self.assert_legal(s,a);self.assertLess(len(m),16000)

if __name__=='__main__':unittest.main()
