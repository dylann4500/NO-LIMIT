"""Regressions for public-event statistics and table-local transferable memory."""
import os,sys,pickle
sys.path.insert(0,os.path.abspath(os.path.join(os.path.dirname(__file__),'../../fake_sdk')))
sys.path.insert(0,os.path.dirname(__file__))
from types import SimpleNamespace as NS
from poker_agent_sdk import Event,Seat
import agent
s=NS(seats=[Seat(17,2000,0,'active'),Seat(91,2000,0,'active')],hand_number=1,cards=['As','Kh'],board=['Qc','7d','2s'],events=[Event('hand',amount=1),Event('raise',91,60),Event('call',17,60),Event('board',cards=['Qc','7d','2s']),Event('check',17),Event('raise',91,80)])
m,_=agent.observe(s,b'')
assert m['stats']['91'][6:10]==[1,1,0,0]
assert m['stats']['17'][6:10]==[1,0,0,0]
s.events=[Event('call',17,80),Event('board',cards=['3h']),Event('check',17),Event('check',91),Event('board',cards=['4h']),Event('check',17),Event('raise',91,200),Event('fold',17)]
s.board+=['3h','4h'];m,_=agent.observe(s,pickle.dumps(m))
assert m['stats']['17'][6:10]==[1,0,1,0]
assert m['stats']['17'][14:18]==[1,0,1,1]
assert m['stats']['91'][10:14]==[1,0,0,0]
assert m['stats']['91'][14:18]==[1,1,0,0]
# An old six-counter memory migrates without discarding preflop observations.
for v in m['stats'].values():del v[6:]
s.events=[];m,_=agent.observe(s,pickle.dumps(m));assert all(len(v)==18 for v in m['stats'].values())
assert m['stats']['91'][:3]==[1,1,1]
# A fresh hand must forget the previous river's outstanding bet.
s.hand_number=2;s.board=[];s.events=[Event('hand',amount=2),Event('board',cards=['Ac','8d','2h']),Event('check',17),Event('check',91)]
m,_=agent.observe(s,pickle.dumps(m));assert m['lastbet']==[None]*4
assert m['stats']['91'][6:10]==[1,0,0,0]
print('Passed: incremental event batches, street separation, old-memory migration, new-hand reset, non-contiguous seat labels.')
