"""Compare preflop actions on identical public observations; no outcome claims."""
import collections as C,importlib.util,json
from pathlib import Path
from replay import states,agent,ROOT
spec=importlib.util.spec_from_file_location('round1_agent',ROOT.parent/'openai_a_iterate_3/agent.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
out=C.defaultdict(C.Counter);examples=[]
for st,m,actual,h in states():
 if st.board:continue
 hero=next(x for x in st.seats if x.seat==st.seat);opps=[x for x in st.seats if x.seat!=st.seat and x.status in ('active','all_in')]
 if not opps:continue
 a=old.Agent()._preflop(st,m,hero,opps)[0];b=agent.Agent()._preflop(st,m,hero,opps)[0]
 label='heads_up' if st.players_remaining==2 else '3_or_4' if st.players_remaining<=4 else '5_to_8'
 out[label][a+' -> '+b]+=1
 if a=='fold' and b=='call' and st.players_remaining<=3 and len(examples)<20:
  examples.append(dict(hole=st.cards,players=st.players_remaining,bb=st.blinds[1],stack=hero.stack,cost=st.to_call,raises=m['nr'],table=h['table'],hand=h['hand']))
report=dict(transitions=out,examples=examples)
(ROOT/'results/action_comparison.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=1))
