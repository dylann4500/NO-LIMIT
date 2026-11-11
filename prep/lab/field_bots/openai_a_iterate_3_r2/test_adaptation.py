"""Regression checks for leaks found in round 1, using only the SDK."""
import pickle,random
from test_agent import fixture,agent,sdk,K

def run():
 # Reraises at 20 BB must not reuse the 8% full-table premium prior.
 st=fixture(random.Random(4),2,0,4550)
 st.blinds=[250,500];st.seats[0].stack=9500;st.seats[0].bet=500
 st.seats[1].stack=0;st.seats[1].bet=10000;st.seats[1].status='all_in'
 st.cards=['As','Jh'];st.pot=10500;st.to_call=9500
 st.events=[sdk.Event('hand',amount=1),sdk.Event('blind',seat=0,amount=250),sdk.Event('blind',seat=1,amount=500),sdk.Event('raise',seat=0,amount=1125),sdk.Event('raise',seat=1,amount=10000)]
 st.seats[0].bet=1125;st.seats[0].stack=8875;st.to_call=8875;st.pot=11125
 st.legal_actions=[sdk.LegalAction(K.FOLD),sdk.LegalAction(K.CALL)]
 m=agent._memory(st,b'')
 width=agent._range_width(st,m,1)
 assert width>=.35,width
 assert agent.Agent()._decide(st,m)[0]=='call'
 # Only an actual response to an existing raise counts as a reraise.
 q=m['q']['1'][2];assert q[3]==1 and q[4]==1 and q[5]==0,q
 assert m['q']['0'][2][5]==1 and m['q']['0'][2][6]==1
 # New heads-up observations cannot alter the stored full-table statistics.
 assert not any(m['q']['1'][0])
 # Weak revealed reraises increase the range estimate; no seat identity is used.
 before=width
 st.events=[sdk.Event('show',seat=1,cards=['9c','5d'])]
 m=agent._memory(st,pickle.dumps(m,protocol=4))
 assert m['q']['1'][2][10]==1
 assert agent._range_width(st,m,1)>before
 # Short effective stacks remain short when hero covers by a large amount.
 st=fixture(random.Random(7),2,0,0);st.blinds=[250,500]
 st.seats[0].stack=14500;st.seats[0].bet=250
 st.seats[1].stack=750;st.seats[1].bet=500;st.button=0;st.cards=['8s','6s']
 st.events=[sdk.Event('hand',amount=1),sdk.Event('blind',seat=0,amount=250),sdk.Event('blind',seat=1,amount=500)]
 st.to_call=250;st.pot=750
 m=agent._memory(st,b'')
 assert agent.Agent()._decide(st,m)[0]=='raise'
 # A third live player invalidates the heads-up resteal EV calculation.
 st=fixture(random.Random(8),3,0,50)
 m=agent._memory(st,b'')
 assert not agent._resteal(st,m,st.seats[0],st.seats[1],'A5s')
 print('PASS: short-handed reraises, stage isolation, showdown learning, effective-stack opening, multiway resteal guard')
if __name__=='__main__':run()
