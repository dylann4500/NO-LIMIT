"""Read only supplied public histories; reconstruct SDK snapshots without simulator imports."""
import sys,os,gzip,json,pickle,collections,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'fake_sdk'))
import poker_agent_sdk as sdk
spec=importlib.util.spec_from_file_location('policy',str(ROOT.parent/'openai_k_default_2'/'agent.py'))
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
import eval7

def snapshots():
 memories={}
 for line in gzip.open(ROOT.parent/'openai_k_default_2'/'round1'/'hand_history.jsonl.gz','rt'):
  hand=json.loads(line);hero=hand['seat'];table=hand['table']
  stacks={int(s):x for s,x in hand['stacks'].items()}
  if stacks.get(hero,0)<=0:continue
  n=len(stacks);bets={s:0 for s in stacks};status={s:'active' for s in stacks};pot=0;board=[];history=[];pending=[];maxbet=0;last_raise=hand['blinds'][1]
  shows={e[1]:e[3] for e in hand['events'] if e[0]=='show'}
  start=stacks[hero];end=next((e[2] for e in hand['events'] if e[0]=='stack' and e[1]==hero),start)
  first=None;raises=0
  for k,s,a,c in hand['events']:
   if s==hero and k in ('fold','check','call','raise'):
    if not board and first is None:first=('raised_' if raises else 'unopened_')+k
    cost=min(stacks[hero],maxbet-bets[hero]);legal=[]
    legal.append(sdk.LegalAction(sdk.ActionKind.FOLD if cost else sdk.ActionKind.CHECK))
    if cost:legal.append(sdk.LegalAction(sdk.ActionKind.CALL))
    if stacks[hero]>cost:legal.append(sdk.LegalAction(sdk.ActionKind.RAISE,min(bets[hero]+stacks[hero],maxbet+last_raise),bets[hero]+stacks[hero]))
    cfg=sdk.Config(table_id=table,seat=hero,variant='holdem',players=8,starting_stack=2000,blinds=[hand['blinds']],hands_per_level=20,hand_cap=250,payouts=[50,30,20,0,0,0,0,0],decision_ms=1,time_bank_ms=100,memory_bytes=65536)
    state=sdk.State(seat=hero,cards=hand['hole'],board=board[:],pot=pot,to_call=cost,legal_actions=legal,history=history[:],phase='betting',seats=[sdk.Seat(i,stacks.get(i,0),bets.get(i,0),status.get(i,'busted')) for i in range(8)],button=hand['button'],blind_level=0,blinds=hand['blinds'],hands_until_next_level=20-hand['hand']%20,hand_number=hand['hand'],players_remaining=n,bust_order=[],config=cfg,time_bank_ms=100,events=pending[:])
    model=policy.update(state,memories.get(table,b''));memories[table]=pickle.dumps(model,protocol=4);pending=[]
    yield state,model,{'actual':k,'amount':a,'shows':shows,'first':first,'net':end-start,'table':table,'hand':hand['hand'],'start':start,'end':end,'names':hand['names']}
   event=sdk.Event(k,s,a,c);history.append(event);pending.append(event)
   if k=='board':board+=c;bets={s:0 for s in stacks};maxbet=0;last_raise=hand['blinds'][1]
   elif k in ('blind','ante','call','raise'):
    amount=(a-bets[s]) if k=='raise' else a
    amount=min(stacks[s],amount);stacks[s]-=amount;pot+=amount
    if k!='ante':bets[s]+=amount
    if k=='raise':last_raise=max(last_raise,bets[s]-maxbet);raises+=not board
    maxbet=max(maxbet,bets[s])
    if stacks[s]==0:status[s]='all_in'
   elif k=='fold':status[s]='folded'
  # Deliver the tail exactly once on the next decision, including other hands.
  if table in memories:
   tail=state
   tail.events=pending
   memories[table]=pickle.dumps(policy.update(tail,memories[table]),protocol=4)

def main():
 records=[];groups=collections.defaultdict(lambda:collections.Counter());cal=collections.defaultdict(lambda:[0,0.,0.,0.]);shown=collections.defaultdict(lambda:collections.Counter())
 for state,m,meta in snapshots():
  board=state.board;hero=state.seat;h=m['hand'];stats=m['stats'];opps=[s for s in state.seats if s.seat!=hero and s.status in ('active','all_in')]
  rec={'state':state,'memory':pickle.dumps(m,protocol=4),'meta':meta};records.append(rec)
  if not board:
   if len([e for e in state.history if e.seat==hero and e.kind in ('call','raise','fold','check')])==0:
    hk=policy.hand_key(*(policy.CARD_INDEX[c] for c in state.cards));g=meta['first'];net=meta['net']/state.blinds[1]
    groups[g]['hands']+=1;groups[g]['net_bb']+=net
    if g=='raised_call':
     key=('pair' if len(hk)==2 else 'suited' if hk[-1]=='s' else 'offsuit')+'_'+('blind' if policy.seat_position(state,hero)>=state.players_remaining-2 else 'other')
     groups[key]['hands']+=1;groups[key]['net_bb']+=net
   continue
  if not state.to_call or not opps:continue
  eq,q,draw,wet,cat,ag=policy.equity(state,h,opps,stats,[policy.CARD_INDEX[c] for c in state.cards],state.hand_number*923+hero)
  man=policy.profile(stats[ag.seat])[-1];street=len(board)-3
  if ag.seat not in meta['shows']:continue
  villain=[eval7.Card(c) for c in meta['shows'][ag.seat]];cards=[eval7.Card(c) for c in state.cards];bc=[eval7.Card(c) for c in board]
  truth=eval7.py_hand_vs_range_exact(cards,[(villain,1.)],bc) if street==2 else eval7.py_hand_vs_range_monte_carlo(cards,[(villain,1.)],bc,1500)
  key=f'{street}_{"maniac" if man>.35 else "normal"}_{meta["actual"]}'
  row=cal[key];row[0]+=1;row[1]+=eq;row[2]+=truth;row[3]+=state.to_call*(eq-truth)
  if street==2:
   val=eval7.evaluate(villain+bc);vc=val>>24;shown[f'river_{"maniac" if man>.35 else "normal"}'][str(vc)]+=1
  if meta['actual']=='call' and eq-truth>.35 and state.to_call>300:
   rec['bad_call']={'eq':eq,'truth':truth,'q':q,'man':man,'opp':ag.seat,'acts':h['acts'].get(ag.seat),'range':policy.opponent_range(state,h,ag.seat,stats)}
 out={'first_action':dict(groups),'showdown_calibration':{k:{'n':v[0],'predicted_equity':v[1]/v[0],'actual_hand_equity':v[2]/v[0],'weighted_equity_error_chips':v[3]} for k,v in cal.items()},'river_shown_categories':dict(shown),'snapshots':len(records)}
 (ROOT/'results'/'history_analysis.json').write_text(json.dumps(out,indent=2))
 with (ROOT/'results'/'snapshots.pkl').open('wb') as f:pickle.dump(records,f)
 print(json.dumps(out,indent=2))
 print('LARGE OVERCONFIDENT CALLS')
 for r in sorted([r for r in records if 'bad_call' in r],key=lambda r:-r['state'].to_call)[:20]:
  s=r['state'];print(s.cards,s.board,s.to_call,r['meta']['net'],r['bad_call'],r['meta']['names'][str(r['bad_call']['opp'])])
if __name__=='__main__':main()
