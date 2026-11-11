"""Reconstruct documented SDK observations from public histories, without the engine."""
import collections as C
import importlib.util
import json
import time
from types import SimpleNamespace as NS
import eval7
from poker_agent_sdk import State,Seat,Event,Config,LegalAction,ActionKind
from analyze import HANDS,ROOT

def observations():
    pending=[];table=None
    for h in HANDS:
        if h['table']!=table:
            table=h['table'];pending=[]
        stacks={int(s):v for s,v in h['stacks'].items()}
        bets=C.Counter();con=C.Counter();board=[];status={s:'active' for s in stacks};history=[]
        last_raise=h['blinds'][1];maximum=0;pot=0
        for j,(k,s,a,c) in enumerate(h['events']):
            if k in ('fold','check','call','raise'):
                to_call=max(0,maximum-bets[s])
                active=sum(v in ('active','all_in') for v in status.values())
                record=dict(h=h,j=j,street=max(0,len(board)-2),pot=pot,call=min(stacks[s],to_call),seat=s,action=k,amount=a,
                            n=len(stacks),active=active,board=board[:],stack=stacks[s],bet=bets[s],status=status.copy())
                state=None
                if s==h['seat']:
                    legal=[LegalAction(ActionKind.CHECK)] if to_call==0 else [LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)]
                    if stacks[s]>to_call and sum(v=='active' for v in status.values())>1:
                        mx=bets[s]+stacks[s];mn=min(mx,maximum+last_raise)
                        legal.append(LegalAction(ActionKind.RAISE,mn,mx))
                    state=State(seat=s,cards=h['hole'],board=board[:],pot=pot,to_call=to_call,legal_actions=legal,
                        history=history[:],phase='betting',seats=[Seat(x,stacks[x],bets[x],status[x]) for x in sorted(stacks)],
                        button=h['button'],blind_level=0,blinds=h['blinds'],hand_number=h['hand'],players_remaining=len(stacks),
                        bust_order=[],hands_until_next_level=20-h['hand']%20,
                        config=Config(players=8,starting_stack=2000,payouts=[50,30,20,0,0,0,0,0],decision_ms=1,time_bank_ms=100,memory_bytes=65536),
                        events=pending[:],time_bank_ms=100)
                    pending=[]
                yield state,record
            if k=='board':board+=c;bets.clear();last_raise=h['blinds'][1];maximum=0
            if k in ('blind','ante','call','raise'):
                add=max(0,a-bets[s]) if k=='raise' else a
                stacks[s]-=add;con[s]+=add;pot+=add
                if k!='ante':bets[s]+=add
                if stacks[s]==0:status[s]='all_in'
                if k=='raise':last_raise=max(last_raise,a-maximum)
                maximum=max(maximum,bets[s])
            elif k=='fold':status[s]='folded'
            e=Event(k,s,a,c);pending.append(e);history.append(e)

def diagnostics():
    import agent
    response=C.defaultdict(C.Counter);our=C.defaultdict(C.Counter);cal=C.defaultdict(lambda:[0,0.,0.,0.]);examples=[]
    data=None;table=None
    for state,r in observations():
        h=r['h'];st=r['street'];name=h['names'][str(r['seat'])]
        if st:
            price=r['call']/max(1,r['pot'])
            label='free' if r['call']==0 else 'small' if price<.35 else 'medium' if price<.8 else 'large'
            response[(name,st,label)][r['action']]+=1
            response[('FIELD',st,label)][r['action']]+=1
            if state:our[(st,label)][r['action']]+=1
        if state is None:continue
        if h['table']!=table:table=h['table'];data=agent.new_memory()
        agent.update(state,data)
        # decide populates positions and other input to equity, as in production.
        action,amt=agent.Agent().decide(state,data,time.perf_counter_ns())
        if not st:continue
        reveals={s:c for k,s,a,c in h['events'] if k=='show' and s!=state.seat}
        opponents=[p for p in state.seats if p.seat!=state.seat and p.status in ('active','all_in')]
        if len(opponents)!=1 or opponents[0].seat not in reveals:continue
        cards=[agent.CARDS[x] for x in state.cards];board=[agent.CARDS[x] for x in state.board]
        seed=state.hand_number*193+sum(agent.CARDS[x].rank*31+agent.CARDS[x].suit*7 for x in state.cards)+len(board)*73+state.seat*47+data['acts'][st]*29
        eq=agent.post_equity(cards,board,opponents,data,len(state.seats),state.blinds[1],seed,time.perf_counter_ns()+1000000)
        hr=[(tuple(agent.CARDS[x] for x in reveals[opponents[0].seat]),1.)]
        true=eval7.py_hand_vs_range_exact(cards,hr,board) if st==3 else eval7.py_hand_vs_range_monte_carlo(cards,hr,board,3000)
        threshold=agent.call_threshold(state,next(p for p in state.seats if p.seat==state.seat),opponents,state.pot,min(state.to_call,r['stack']))
        k=(st,r['action'],round(eq*5)/5)
        v=cal[k];v[0]+=1;v[1]+=eq;v[2]+=true;v[3]+=r['call']
        if r['action']=='raise' and eq>.7 and true<.3:examples.append(dict(table=h['table'],hand=h['hand'],st=st,eq=eq,true=true,hole=h['hole'],board=r['board'],villain=hr[0][0].__str__(),pot=r['pot'],call=r['call'],amount=r['amount']))
    print('OUR RESPONSE',dict(our))
    print('FIELD RESPONSE')
    for key,counts in response.items():
        if key[0]=='FIELD':print(key,counts)
    print('CALIBRATION ON SHOWDOWNS (selection biased)')
    for k,(n,e,t,c) in sorted(cal.items()):print(k,n,round(e/n,3),round(t/n,3),round(c/n,1))
    print('OPTIMISTIC VALUE RAISES')
    for e in examples:print(e)
    (ROOT/'validation/postflop_diagnostics.json').write_text(json.dumps(dict(response={str(k):v for k,v in response.items()},calibration={str(k):v for k,v in cal.items()},optimistic_raises=examples),indent=2))

if __name__=='__main__':diagnostics()
