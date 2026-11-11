"""SDK-only policy replay on recorded public states, with showdown diagnostics.
This is a decision audit, not a counterfactual tournament simulation.
"""
import sys,os,json,gzip,pickle,collections,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'fake_sdk'))
from poker_agent_sdk import State,Config,Seat,Event,LegalAction,ActionKind
import eval7

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
mods=[load('old',ROOT.parent/'openai_b_gto_3/agent.py'),load('new',ROOT/'agent.py')]
agents=[m.Agent() for m in mods];mem={};pending={};rows=[];changes=collections.Counter()
for ln in gzip.open(ROOT.parent/'openai_b_gto_3/round1/hand_history.jsonl.gz','rt'):
 h=json.loads(ln);hero=h['seat'];tab=h['table'];start={int(k):v for k,v in h['stacks'].items()}
 if not start.get(hero,0):continue
 bets=collections.Counter();spent=collections.Counter();folded=set();board=[];pot=0;maxbet=0;lastinc=h['blinds'][1];st=0
 if tab not in mem:
  initial={'h':-1,'stats':{str(i):[0]*6 for i in start},'seed':314159,'rounds':[{}, {}, {}, {}], 'pr':[], 'vp':[], 'pf':[],'st':0}
  mem[tab]=[pickle.dumps(initial),pickle.dumps(initial)];pending[tab]=[]
 revealed={e[1]:e[3] for e in h['events'] if e[0]=='show'}
 for ix,(k,seat,amt,cs) in enumerate(h['events']):
  if seat==hero and k in ('fold','check','raise','call'):
   stack=start[hero]-spent[hero];cost=min(stack,maxbet-bets[hero]);total=stack+bets[hero]
   legal=[LegalAction(ActionKind.CALL if cost else ActionKind.CHECK)]
   if cost:legal.append(LegalAction(ActionKind.FOLD))
   if total>maxbet:
    legal.append(LegalAction(ActionKind.RAISE,min(total,maxbet+lastinc),total))
   ps=[Seat(i,start[i]-spent[i],bets[i],'folded' if i in folded else 'all_in' if spent[i]>=start[i] else 'active') for i in sorted(start)]
   s=State(cards=h['hole'],board=list(board),seat=hero,button=h['button'],seats=ps,pot=pot,to_call=maxbet-bets[hero],blinds=h['blinds'],players_remaining=len(start),hand_number=h['hand'],config=Config(payouts=[50,30,20,0,0,0,0,0],time_bank_ms=100),events=pending[tab],legal_actions=legal,time_bank_ms=100)
   out=[]
   for j,(module,agent) in enumerate(zip(mods,agents)):
    action,mem[tab][j]=agent.act(s,mem[tab][j]);out.append(action.kind.value)
   changes[(st,k,out[1])]+=1
   if st and cost and len(revealed)>=2:
    eq=1.;hero_cards=[eval7.Card(c) for c in s.cards];bc=[eval7.Card(c) for c in board]
    for sid,cards in revealed.items():
     if sid!=hero:eq*=eval7.py_hand_vs_range_monte_carlo(hero_cards,[(tuple(eval7.Card(c) for c in cards),1.)],bc,2500)
    rows.append({'street':st,'actual':k,'old':out[0],'new':out[1],'evbb':(eq*(pot+cost)-cost)/h['blinds'][1], 'costbb':cost/h['blinds'][1],'table':tab,'hand':h['hand']})
   pending[tab]=[]
  pending[tab].append(Event(k,seat,amt,cs))
  if k=='board':
   board+=cs;st+=1;bets=collections.Counter();maxbet=0;lastinc=h['blinds'][1]
  elif k=='fold':folded.add(seat)
  elif k in ('blind','ante','call','raise'):
   delta=amt-bets[seat] if k=='raise' else amt;spent[seat]+=delta;pot+=delta
   if k!='ante':bets[seat]+=delta
   if k=='raise':lastinc=max(lastinc,amt-maxbet)
   maxbet=max(maxbet,bets[seat])
summary={}
for label in ('old','new'):
 for st in (1,2,3):
  r=[x for x in rows if x['street']==st and x[label] in ('call','raise')]
  summary[f'{label}_street{st}']={'showdown_labeled_continues':len(r),'fixed_hole_call_ev_bb':round(sum(x['evbb'] for x in r),2),'call_cost_bb':round(sum(x['costbb'] for x in r),2)}
summary['actual_action_vs_revised']={str(k):v for k,v in sorted(changes.items())}
summary['caveat']='Only observed paths; showdown selection bias; no tournament performance claim. Calling EV includes future free runouts and ignores future bets.'
(ROOT/'results/replay_summary.json').write_text(json.dumps(summary,indent=2));(ROOT/'results/replay_labels.json').write_text(json.dumps(rows))
print(json.dumps(summary,indent=2))
