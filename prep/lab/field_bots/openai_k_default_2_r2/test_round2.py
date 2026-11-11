"""Focused regression checks for changes justified by round-one histories."""
import pickle
import validate as v
p=v.agent;sdk=v.sdk

def context(cards):return p.board_context([p.CARD_INDEX[c] for c in cards])

def test_public_statistics():
 s=v.state_for(hole=['Ac','Qh'],board=['Js','8c','2d','5h','9s'],n=3)
 s.events=[sdk.Event('hand',amount=7),sdk.Event('board',cards=['Js','8c','2d']),sdk.Event('raise',seat=1,amount=100),sdk.Event('fold',seat=2),sdk.Event('call',seat=0,amount=100),sdk.Event('board',cards=['5h']),sdk.Event('raise',seat=1,amount=200),sdk.Event('fold',seat=0)]
 m=p.update(s,b'');st=m['stats']
 assert st[2][p.SFACE]==1 and st[2][p.SFOLD]==1
 assert st[0][p.SFACE]==1 and st[0][p.SFOLD]==0
 assert st[0][p.SFACE+1]==1 and st[0][p.SFOLD+1]==1
 assert st[0][p.SFACE+2]==0
 # An older compatible memory must extend its stats without changing them.
 m['stats'][1]=m['stats'][1][:19];s.events=[]
 m2=p.update(s,pickle.dumps(m));assert len(m2['stats'][1])==p.STAT_COUNT
 assert m2['stats'][1][:19]==m['stats'][1]


def test_raise_evidence():
 for street in range(3):
  bet=p.action_weight(3,.75,.20,False,street,.60,.50,1.,.04)
  raise_=p.action_weight(4,1.5,.20,False,street,.60,.50,1.,.04)
  value=p.action_weight(4,1.5,.98,False,street,.60,.50,1.,.04)
  assert value>15*raise_ and bet>5*raise_
  assert p.action_weight(4,1.5,.20,False,street,.60,.50,1.,.5)>raise_


def test_monotone_straight():
 ids=[p.CARD_INDEX[c] for c in ['Td','Qs']]
 mono=['9d','Jd','8d'];rain=['9d','Jc','8h']
 def quality(board):
  val=p.eval7.evaluate([p.CARDS[i] for i in ids]+[p.eval7.Card(c) for c in board])
  return p.made_quality(*ids,val,context(board))
 assert quality(mono)<quality(rain)


def test_recorded_small_blind_call():
 # QJo against a cutoff open: round one paid to see a flop out of position.
 s=v.state_for(hole=['Qh','Jc'],board=[],n=8,cost=40,hero=0)
 s.pot=110;s.to_call=40;s.button=7
 s.seats=[sdk.Seat(i,1950,10 if i==0 else 20 if i==1 else 50 if i==5 else 0,'active' if i in (0,1,5) else 'folded') for i in range(8)]
 s.events=[sdk.Event('hand',amount=7),sdk.Event('blind',seat=0,amount=10),sdk.Event('blind',seat=1,amount=20),sdk.Event('fold',seat=2),sdk.Event('fold',seat=3),sdk.Event('fold',seat=4),sdk.Event('raise',seat=5,amount=50),sdk.Event('fold',seat=6),sdk.Event('fold',seat=7)]
 s.legal_actions=[sdk.LegalAction(sdk.ActionKind.FOLD),sdk.LegalAction(sdk.ActionKind.CALL),sdk.LegalAction(sdk.ActionKind.RAISE,80,1960)]
 action,_=p.Agent()._act(s,b'');assert action.kind==sdk.ActionKind.FOLD,action

def test_board_hand_quality():
 # A flush threat must cap quality, never promote a hand playing the board.
 for board in (['As','Ac','Ks','Kh','2s'],['2s','2h','2d','As','Ks']):
  ids=[p.CARD_INDEX[c] for c in ['Qh','Jd']]
  value=p.eval7.evaluate([p.CARDS[i] for i in ids]+[p.eval7.Card(c) for c in board])
  q=p.made_quality(*ids,value,context(board))
  assert q<.45,(board,q)

if __name__=='__main__':
 test_public_statistics();test_raise_evidence();test_monotone_straight();test_recorded_small_blind_call();test_board_hand_quality()
 print('5 round-two regression checks passed')
