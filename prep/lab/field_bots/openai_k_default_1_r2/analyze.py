"""Replay the supplied public histories using only the documented SDK."""
import collections, gzip, importlib.util, json, os, pickle, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'fake_sdk'))
if '--candidate' in sys.argv:
    import agent as bot
else:
    path=os.path.join(os.path.dirname(__file__), '..', 'openai_k_default_1', 'agent.py')
    spec=importlib.util.spec_from_file_location('round_one_analysis',path)
    bot=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bot)
from poker_agent_sdk import State, Seat, Config, Event, LegalAction, ActionKind

SOURCE=os.path.join(os.path.dirname(__file__), '..', 'openai_k_default_1', 'round1', 'hand_history.jsonl.gz')

def replay():
    memories={}; pending=collections.defaultdict(list)
    for line in gzip.open(SOURCE,'rt'):
        hand=json.loads(line); table=hand['table']; hero=hand['seat']
        if hand['stacks'].get(str(hero),0)<=0: continue
        seats=[Seat(i,hand['stacks'].get(str(i),0),0,'active' if hand['stacks'].get(str(i),0)>0 else 'busted') for i in range(8)]
        board=[]; pot=0; history=[]; mx=0; increment=hand['blinds'][1]
        shown={s:c for k,s,a,c in hand['events'] if k=='show'}
        for k,s,a,c in hand['events']:
            if s==hero and k in ('fold','check','call','raise'):
                me=seats[hero]; cost=min(me.stack,max(0,mx-me.bet)); legal=[]
                if cost: legal=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)]
                else: legal=[LegalAction(ActionKind.CHECK)]
                if me.stack>cost and any(v.seat!=hero and v.status=='active' and v.stack>0 for v in seats):
                    maximum=me.stack+me.bet; minimum=min(maximum,mx+increment)
                    legal.append(LegalAction(ActionKind.RAISE,minimum,maximum))
                state=State(seat=hero,cards=hand['hole'],board=board[:],pot=pot,to_call=cost,
                    legal_actions=legal,history=history[:],events=pending[table][:],seats=seats,button=hand['button'],
                    hand_number=hand['hand'],blinds=hand['blinds'],players_remaining=len(hand['stacks']),
                    time_bank_ms=100,config=Config(time_bank_ms=100,payouts=[50,30,20,0,0,0,0,0],decision_ms=1,hand_cap=250))
                m=bot._memory(state,memories.get(table,b'')); memories[table]=pickle.dumps(m,protocol=4); pending[table].clear()
                yield hand,state,m,k,a,shown
            event=Event(k,s,a,c); pending[table].append(event); history.append(event)
            if k=='board':
                board+=c; mx=0; increment=hand['blinds'][1]
                for v in seats: v.bet=0
            elif k in ('blind','ante','call','raise'):
                v=seats[s]; add=a-v.bet if k=='raise' else a
                if k!='ante':
                    v.bet+=add
                    if v.bet>mx:
                        if k=='raise': increment=max(increment,v.bet-mx)
                        mx=v.bet
                v.stack-=add; pot+=add
                if v.stack==0: v.status='all_in'
            elif k=='fold': seats[s].status='folded'

def main():
    sums=collections.defaultdict(collections.Counter); rows=[]; large=[]
    for hand,s,m,action,amount,shown in replay():
        me=s.seats[s.seat]; opp=[v for v in s.seats if v.seat!=s.seat and v.status in ('active','all_in')]
        street=len(s.board)-2 if s.board else 0
        if street==0: continue
        pot=bot._eligible_pot(s,m,me,s.to_call)
        if not opp: continue
        ranked=sorted(opp,key=lambda v:(100 if s.to_call and v.bet==max(x.bet for x in opp) else 0)+sum(4 if x&8 else 2 if x&4 else 1 if x&2 else 0 for x in m['h']['p'].get(v.seat,bot._new_player())[4]),reverse=True)
        key=ranked[0]; hp=m['h']['p'].get(key.seat,bot._new_player()); prof=bot._profile(m['s'][key.seat],hp)
        eq=bot._posterior_eq(s,m,key.seat,[bot._CARDS[c] for c in s.cards],[bot._CARDS[c] for c in s.board])
        threshold=bot._call_threshold(s,me,key,s.to_call,pot) if s.to_call else 0
        feature=bot._features(s.cards,s.board)
        record=dict(table=hand['table'],hand=s.hand_number,hole=s.cards,board=s.board,action=action,amount=amount,
                    cost=s.to_call,pot=pot,stack=me.stack,eq=round(eq,3),threshold=round(threshold,3),
                    opponent=hand['names'][str(key.seat)],shown=shown.get(key.seat),prof=[round(x,3) for x in prof],
                    hp=hp,cat=feature[0],made=feature[1],n=len(opp),range=round(bot._prior_fraction(key.seat,m),3))
        rows.append(record)
        if shown.get(key.seat):
            hero=[bot._CARDS[c] for c in s.cards]; villain=[(tuple(bot._CARDS[c] for c in shown[key.seat]),1.)]; board=[bot._CARDS[c] for c in s.board]
            true=bot.eval7.py_hand_vs_range_exact(hero,villain,board) if street==3 else bot.eval7.py_hand_vs_range_monte_carlo(hero,villain,board,2000)
            record['revealed_equity']=round(float(true),3)
            group=f's{street}_{action}'
            for g in (group,group+f'_cat{feature[0]}'):
                sums[g]['n']+=1; sums[g]['estimate']+=eq; sums[g]['revealed']+=true; sums[g]['cost']+=s.to_call
        if s.to_call>200 and action in ('call','raise') or action=='raise' and (amount or 0)>500:
            large.append(record)
    out=os.path.join(os.path.dirname(__file__),'results')
    prefix='candidate_' if '--candidate' in sys.argv else ''
    with open(os.path.join(out,prefix+'replay.jsonl'),'w') as f:
        for r in rows: f.write(json.dumps(r)+'\n')
    with open(os.path.join(out,prefix+'replay_summary.json'),'w') as f: json.dump(sums,f,indent=1)
    print(json.dumps({k:{kk:round(vv/v['n'],3) if kk!='n' else vv for kk,vv in v.items()} for k,v in sums.items()},indent=1))
    print('EXPENSIVE')
    for r in sorted(large,key=lambda r:r['cost'],reverse=True)[:35]: print(json.dumps(r))

if __name__=='__main__': main()
