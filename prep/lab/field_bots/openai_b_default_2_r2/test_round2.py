"""Regression cases for the range and preflop leaks found in round one."""
import marshal
from test_agent import bot, State, Seat, Event, Config, LegalAction, ActionKind


def state(cards, seat, events, seats, pot, call, button=7, board=None):
    legal=[LegalAction(ActionKind.CALL),LegalAction(ActionKind.FOLD)] if call else [LegalAction(ActionKind.CHECK)]
    own=next(x for x in seats if x.seat==seat)
    legal.append(LegalAction(ActionKind.RAISE,min(own.bet+own.stack,max(x.bet for x in seats)+20),own.bet+own.stack))
    return State(seat=seat,cards=cards,board=board or [],seats=seats,pot=pot,to_call=call,button=button,
                 hand_number=1,blinds=[10,20],players_remaining=len(seats),config=Config(payouts=[50,30,20],
                 decision_ms=1,time_bank_ms=100,memory_bytes=65536),events=events,legal_actions=legal,time_bank_ms=100)


def run():
    assert bot.OPEN['AA']<bot.OPEN['AKs']<bot.OPEN['AJs']
    assert not bot.profile([3,3,3]+[0]*9)[2]
    assert bot.profile([10,10,10]+[0]*9)[2]
    assert not bot.post_maniac([10,10,10,1,3,4]+[0]*6)
    assert bot.post_maniac([20,20,20,15,1,0]+[0]*6)
    assert not bot.post_maniac([20,5,3,4,0,0]+[0]*6)
    # A board pair does not turn a private overpair into genuine two pair.
    hc=[bot.eval7.Card(x) for x in ['As','Ah']]
    bc=[bot.eval7.Card(x) for x in ['7c','5h','7s','Th','4c']]
    combo=bot.COMBO_BY_MASK[(1<<bot.CARD_ID['As'])|(1<<bot.CARD_ID['Ah'])]
    bm=bp=0;bs=[0]*4
    for c in bc:
        if bm>>c.rank&1:bp|=1<<c.rank
        bm|=1<<c.rank;bs[c.suit]+=1
    strength,_=bot.made_class(combo,bot.eval7.evaluate(hc+bc),bm.bit_length()-1,bm,bp,bs,3,bot.eval7.evaluate(bc))
    assert strength==3,strength
    # A normal button open does not justify defending the weakest offsuit hands.
    seats=[Seat(i,2000,0,'folded') for i in range(8)]
    seats[0]=Seat(0,1990,10,'folded');seats[1]=Seat(1,1980,20,'active');seats[7]=Seat(7,1956,44,'active')
    events=[Event('hand',amount=1),Event('blind',0,10),Event('blind',1,20),Event('raise',7,44)]
    s=state(['7c','2d'],1,events,seats,74,24)
    a,memory=bot.Agent().act(s,b'')
    assert bot.kind(a)=='fold',a
    s.cards=['Ah','Jc'];a,_=bot.Agent().act(s,b'')
    assert bot.kind(a) in ('call','raise'),a
    # AK now three-bets an ordinary open without a deep-stack shove.
    seats=[Seat(i,2000,0,'active') for i in range(8)]
    seats[0]=Seat(0,1990,10,'active');seats[1]=Seat(1,1980,20,'active');seats[2]=Seat(2,1956,44,'active')
    events=[Event('hand',amount=1),Event('blind',0,10),Event('blind',1,20),Event('raise',2,44)]
    s=state(['As','Kh'],5,events,seats,74,44)
    a,_=bot.Agent().act(s,b'')
    assert bot.kind(a)=='raise' and 100<=a.amount<500,a
    # A raise of a flop bet carries a different action level and pot fraction.
    events += [Event('call',5,44),Event('board',cards=['Kd','Jh','2c']),Event('raise',2,60),Event('raise',5,200)]
    s.events=events;s.board=['Kd','Jh','2c']
    m,_=bot.update_memory(s,b'')
    assert m['d']['rl'][1][2]==1 and m['d']['rl'][1][5]==2
    assert m['d']['sz'][1][2]>0 and m['d']['sz'][1][5]>0
    # A deep top pair remains a call against a river lead even if a sparse
    # sampled range overestimates how many weaker hands would call a raise.
    seats=[Seat(0,3000,0,'active'),Seat(1,2750,250,'active')]
    s=state(['As','Kh'],0,[],seats,750,250,button=1,board=['Jh','Kd','2d','7s','3h'])
    d=bot.fresh_hand(2,1);d['st']=3;d['in']=[250,500];d['rc'][3]=1;d['lr'][3]=1
    d['a'][3][1]=4;d['r'][3][1]=1;d['rl'][3][1]=1
    m={'ids':[0,1],'stats':[[20,5,3]+[0]*9 for _ in range(2)],'d':d}
    old=bot.post_equity
    try:
        bot.post_equity=lambda *a,**kw:(.90,.85,.1) if kw.get('model') else .90
        action=bot.Agent().decide(s,m,{0:0,1:1},{bot.kind(x):x for x in s.legal_actions})
        assert bot.kind(action)=='call',action
    finally:bot.post_equity=old
    print('Round-two strategy regressions passed.')

if __name__=='__main__':run()
