"""Reconstruct decision observations from public hand histories, using SDK only."""
import collections as C,gzip,json,pickle,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'fake_sdk'))
import poker_agent_sdk as sdk
import agent
SRC=ROOT.parent/'openai_a_iterate_3/round1/hand_history.jsonl.gz'
def states():
 memories={}; pending=C.defaultdict(list)
 for line in gzip.open(SRC,'rt'):
  h=json.loads(line); t=h['table'];hero=h['seat'];start={int(k):v for k,v in h['stacks'].items()};stack=start.copy();bets=C.Counter();folded=set();pot=0;board=[];hist=[];maxbet=0;increment=h['blinds'][1]
  for raw in h['events']:
   k,s,a,c=raw;e=sdk.Event(k,s,a,c)
   if s==hero and k in ('fold','call','raise','check') and start.get(hero,0)>0:
    cost=maxbet-bets[hero];legal=[sdk.LegalAction(sdk.ActionKind.FOLD if cost else sdk.ActionKind.CHECK)]
    if cost:legal.append(sdk.LegalAction(sdk.ActionKind.CALL))
    if stack[hero]>cost and any(x!=hero and x not in folded and stack[x]>0 for x in stack):
     legal.append(sdk.LegalAction(sdk.ActionKind.RAISE,min(maxbet+increment,bets[hero]+stack[hero]),bets[hero]+stack[hero]))
    seats=[sdk.Seat(x,stack[x],bets[x],'folded' if x in folded else 'all_in' if stack[x]<=0 else 'active') for x in sorted(stack)]
    st=sdk.State(seat=hero,cards=h['hole'],board=board[:],pot=pot,to_call=cost,legal_actions=legal,history=hist[:],phase='betting',seats=seats,button=h['button'],blind_level=0,blinds=h['blinds'],hands_until_next_level=20-h['hand']%20,hand_number=h['hand'],players_remaining=len(start),bust_order=[],time_bank_ms=100,events=pending[t][:],config=sdk.Config(table_id=t,seat=hero,variant='holdem',players=8,starting_stack=2000,blinds=[h['blinds']],hands_per_level=20,hand_cap=250,payouts=[50,30,20,0,0,0,0,0],decision_ms=1,time_bank_ms=100,memory_bytes=65536))
    m=agent._memory(st,memories.get(t,b''));pending[t]=[]
    yield st,m,(k,a),h
    memories[t]=pickle.dumps(m,protocol=4)
   if k=='board':board+=c;bets.clear();maxbet=0;increment=h['blinds'][1]
   if k=='fold':folded.add(s)
   if k in ('blind','ante','call','raise'):
    delta=max(0,a-bets[s]) if k=='raise' else a
    stack[s]-=delta;pot+=delta
    if k!='ante':bets[s]+=delta
    if k=='raise':increment=max(increment,a-maxbet)
    maxbet=max(maxbet,bets[s])
   hist.append(e);pending[t].append(e)

if __name__=='__main__':
 summary=C.defaultdict(C.Counter);examples=C.defaultdict(list);bot=agent.Agent();mismatch=0;n=0
 for st,m,actual,h in states():
  hero=next(x for x in st.seats if x.seat==st.seat);opps=[x for x in st.seats if x.seat!=st.seat and x.status in ('active','all_in')]
  if not opps:continue
  n+=1
  pred=bot._decide(st,m)
  if pred[0]!=actual[0]:mismatch+=1
  if st.board:continue
  bb=st.blinds[1];depth=(hero.stack+hero.bet)/bb;nplayers=st.players_remaining;d,_=agent._position(st,st.seat)
  key='n'+str(nplayers)+' '+('short' if depth<=15 else 'medium' if depth<=30 else 'deep')
  summary[key][actual[0]]+=1
  unopened=m['nr']==0 and max(x.bet for x in st.seats)<=bb
  if unopened:
   summary[key+' unopened'][actual[0]]+=1
  else:
   villain=next((x for x in opps if str(x.seat)==m['op']),max(opps,key=lambda x:x.bet))
   if villain.status=='all_in':
    width=agent._range_width(st,m,villain.seat);eq=agent._equity_pre(agent._key(*[agent.CID[c] for c in st.cards]),width)
    cost=min(st.to_call,hero.stack);eligible=agent._eligible_pot(st,m,hero,cost);odds=cost/(eligible+cost);risk=agent._risk(st,hero,opps,cost,eligible)
    label=key+' facing jam';summary[label][actual[0]]+=1;summary[label]['width_sum']+=width
    if len(examples[label])<15:examples[label].append(dict(hole=st.cards,actual=actual,width=round(width,3),equity=round(eq,3),odds=round(odds,3),risk=round(risk,3),raises=m['nr'],villain_revealed=next((e[3] for e in h['events'] if e[0]=='show' and e[1]==villain.seat),None),villain_stats=m['s'][str(villain.seat)],depth=round(depth,1)))
 print('DECISIONS',n,'MISMATCH',mismatch)
 for k,v in summary.items():print(k,dict(v))
 print('EXAMPLES')
 for k,v in examples.items():
  if k.startswith(('n2','n3')):print(k,json.dumps(v))
 (ROOT/'results/replay_analysis.json').write_text(json.dumps(dict(summary=summary,examples=examples,decisions=n,mismatch=mismatch),indent=2))
