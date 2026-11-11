"""Reconstruct SDK observations from our supplied histories for diagnostic replay.
Only the documented SDK and the team's own code are imported.
"""
import collections, gzip, importlib.util, json, marshal, os, sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.abspath(os.path.join(HERE,'../../fake_sdk')))
from poker_agent_sdk import State, Seat, Event, Config, LegalAction, ActionKind
import eval7

def run(path,output):
    spec=importlib.util.spec_from_file_location('replay_bot',path)
    bot=importlib.util.module_from_spec(spec);spec.loader.exec_module(bot)
    agent=bot.Agent(); memories={};pending=collections.defaultdict(list)
    diagnostics=[];contexts=[];rows=[];aggression=collections.defaultdict(collections.Counter)
    original=bot.post_equity
    def diagnostic(*args,**kwargs):
        v=original(*args,**kwargs);diagnostics.append(v);contexts.append((args[3],ids[args[4]]));return v
    bot.post_equity=diagnostic
    source=os.path.join(HERE,'../openai_b_default_2/round1/hand_history.jsonl.gz')
    for line in gzip.open(source,'rt'):
        h=json.loads(line);table=h['table'];me=h['seat'];ids=sorted(map(int,h['names']))
        if str(me) not in h['stacks']:continue
        stacks={i:h['stacks'].get(str(i),0) for i in ids}
        status={i:'active' if stacks[i]>0 else 'busted' for i in ids}
        bets={i:0 for i in ids};board=[];pot=0;mx=0;inc=h['blinds'][1]
        reveals={e[1]:e[3] for e in h['events'] if e[0]=='show'}
        hero_start=stacks[me]
        end=next((e[2] for e in h['events'] if e[0]=='stack' and e[1]==me),hero_start)
        street_raises=0;lastaggr=None
        for k,s,a,c in h['events']:
            if k=='board':board+=c;bets={i:0 for i in ids};mx=0;inc=h['blinds'][1];street_raises=0;lastaggr=None
            stage=0 if not board else len(board)-2
            if s==me and k in ('fold','check','call','raise') and h.get('hole'):
                cost=min(stacks[me],mx-bets[me])
                legal=[LegalAction(ActionKind.CALL),LegalAction(ActionKind.FOLD)] if cost else [LegalAction(ActionKind.CHECK)]
                if stacks[me]>cost and any(i!=me and status[i]=='active' and stacks[i]>0 for i in ids):
                    legal.append(LegalAction(ActionKind.RAISE,min(bets[me]+stacks[me],mx+inc),bets[me]+stacks[me]))
                state=State(seat=me,cards=h['hole'],board=board[:],seats=[Seat(i,stacks[i],bets[i],status[i]) for i in ids],
                            pot=pot,to_call=cost,button=h['button'],hand_number=h['hand'],blinds=h['blinds'],
                            players_remaining=sum(v!='busted' for v in status.values()),config=Config(payouts=[50,30,20],
                            decision_ms=1,time_bank_ms=100,memory_bytes=65536),events=pending[table],
                            legal_actions=legal,time_bank_ms=100)
                diagnostics.clear();contexts.clear()
                memory=memories.get(table,b'')
                m,ix=bot.update_memory(state,memory)
                action=agent.decide(state,m,ix,{bot.kind(x):x for x in legal},0)
                memories[table]=marshal.dumps(m);pending[table]=[]
                row=dict(table=table,hand=h['hand'],stage=stage,hole=h['hole'],board=board[:],
                         stack=stacks[me],pot=pot,call=cost,bb=h['blinds'][1],actual=k,
                         predicted=bot.kind(action),amount=action.amount,eq=diagnostics[:],
                         net=end-hero_start,aggressor=lastaggr,raises=street_raises,
                         ownbet=bets[me],reveals=reveals,ranges=contexts[:],initial_stack=hero_start)
                if stage and lastaggr in reveals and me in reveals:
                    hc=[eval7.Card(x) for x in h['hole']];bc=[eval7.Card(x) for x in board]
                    vr=[((eval7.Card(reveals[lastaggr][0]),eval7.Card(reveals[lastaggr][1])),1.)]
                    row['actual_equity']=(eval7.py_hand_vs_range_exact(hc,vr,bc) if stage==3 else eval7.py_hand_vs_range_monte_carlo(hc,vr,bc,3000))
                rows.append(row)
            if k=='raise' and stage and s in reveals and s!=me:
                hc=[eval7.Card(x) for x in reveals[s]];bc=[eval7.Card(x) for x in board]
                cm=sum(1<<bot.CARD_ID[x] for x in reveals[s]);bm=bp=0;bs=[0]*4
                for x in bc:
                    if bm>>x.rank&1:bp|=1<<x.rank
                    bm|=1<<x.rank;bs[x.suit]+=1
                strength,draw=bot.made_class(bot.COMBO_BY_MASK[cm],eval7.evaluate(hc+bc),bm.bit_length()-1,bm,bp,bs,stage,eval7.evaluate(bc) if stage==3 else -1)
                aggression[(stage,'raise' if street_raises else 'bet')][str(strength)+('d' if draw else '')]+=1
            pending[table].append(Event(k,s,a,c))
            if k in ('blind','ante','call','raise'):
                add=a-bets[s] if k=='raise' else a
                if k!='ante':bets[s]+=add
                stacks[s]-=add;pot+=add
                if stacks[s]<=0:status[s]='all_in'
                if k=='raise':inc=max(inc,a-mx);mx=max(mx,a);street_raises+=1;lastaggr=s
                elif k=='blind':mx=max(mx,bets[s])
            elif k=='fold':status[s]='folded'
    with open(output,'w') as f:json.dump({'rows':rows,'showdown_aggression':{str(k):dict(v) for k,v in aggression.items()}},f)
    print('decisions',len(rows),'action match',sum(r['actual']==r['predicted'] for r in rows)/len(rows))
    print('showdown aggression',dict(aggression))
    for st in range(1,4):
        rr=[r for r in rows if r['stage']==st and r['actual']=='call' and 'actual_equity' in r and r['eq']]
        def eq(r):return r['eq'][0][0] if isinstance(r['eq'][0],list) or isinstance(r['eq'][0],tuple) else r['eq'][0]
        print('calls',st,len(rr),'model',sum(eq(r) for r in rr)/max(1,len(rr)),'actual',sum(r['actual_equity'] for r in rr)/max(1,len(rr)))

if __name__=='__main__':run(sys.argv[1],sys.argv[2])
