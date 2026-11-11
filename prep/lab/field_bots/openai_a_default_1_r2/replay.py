"""Replay public logs using only the documented SDK; collect decision diagnostics."""
import os,sys,json,collections,types,time
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'../../fake_sdk'))
from poker_agent_sdk import State,Seat,Config,Event,LegalAction,ActionKind
from analyze import HANDS,ROOT
import eval7

def load(path):
    src=open(path).read().replace("            blob=pickle.dumps(d,protocol=4)","            self.debug = {k:v for k,v in __import__('sys')._getframe(1).f_locals.items() if k in ('q','eq','need','odds','risk','realize','realized','rpct','range_pct','quality','draw','continuation','strength','looseness','spr','in_position','nopp','depth','base','pct','maniac','pfold','ev','own_pre')}\n            blob=pickle.dumps(d,protocol=4)",1)
    m=types.ModuleType('replay_agent');m.__file__=path;exec(compile(src,path,'exec'),m.__dict__)
    if os.environ.get('SCALED_CLOCK'):
        class ScaledClock:
            def perf_counter_ns(self):return int(time.perf_counter_ns()*2.5)
        m.time=ScaledClock()
    return m.Agent()

def replay(path,out):
    agent=load(path);memory=b'';pending=[];lasttable=None;rows=[];cpu_times=[]
    for h in HANDS:
        if h['hole'] is None:continue
        if h['table']!=lasttable:memory=b'';pending=[];lasttable=h['table']
        hero=h['seat'];bb=h['blinds'][1];board=[];hist=[];pot=0;mx=0;inc=bb
        seats=[Seat(s,h['stacks'].get(str(s),0),0,'active' if str(s) in h['stacks'] else 'busted') for s in range(8)]
        config=Config(table_id=h['table'],seat=hero,variant='holdem',players=8,starting_stack=2000,blinds=[],hands_per_level=20,hand_cap=250,payouts=[50,30,20,0,0,0,0,0],decision_ms=1,time_bank_ms=100,memory_bytes=65536)
        for ei,(k,s,amt,cs) in enumerate(h['events']):
            if s==hero and k in ('raise','call','check','fold'):
                me=seats[hero];cost=min(me.stack,max(0,mx-me.bet))
                legal=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)] if cost else [LegalAction(ActionKind.CHECK)]
                if me.stack>cost and any(p.seat!=hero and p.status=='active' and p.stack>0 for p in seats):legal.append(LegalAction(ActionKind.RAISE,min(me.bet+me.stack,mx+inc),me.bet+me.stack))
                st=State(seat=hero,cards=h['hole'],board=board[:],pot=pot,to_call=max(0,mx-me.bet),legal_actions=legal,history=hist[:],phase='betting',seats=seats,button=h['button'],blind_level=1,blinds=h['blinds'],hands_until_next_level=20,hand_number=h['hand'],players_remaining=len(h['stacks']),bust_order=[],config=config,time_bank_ms=100,events=pending[:])
                tick=time.process_time_ns();action,memory=agent.act(st,memory);cpu_times.append((time.process_time_ns()-tick)*2.5/1000);pending=[]
                dbg=agent.debug.copy();row={'table':h['table'],'hand':h['hand'],'event':ei,'street':len(board),'n':len(h['stacks']),'hole':h['hole'],'board':board[:],'pot':pot,'cost':cost,'stack':me.stack,'bb':bb,'recorded':k,'chosen':action.kind.value,'amount':action.amount,'debug':dbg}
                # Revealed opposing cards, with actual equity at this decision.
                reveals={e[1]:e[3] for e in h['events'] if e[0]=='show' and e[1]!=hero}
                opponents=[p for p in seats if p.seat!=hero and p.status in ('active','all_in')]
                if len(reveals)==1 and len(opponents)==1 and cost and len(board)>=3:
                    vv=next(iter(reveals.values())); hc=[eval7.Card(c) for c in h['hole']];vc=[eval7.Card(c) for c in vv];bc=[eval7.Card(c) for c in board]
                    actual=eval7.py_hand_vs_range_exact(hc,[(vc,1.)],bc) if len(board)==5 else eval7.py_hand_vs_range_monte_carlo(hc,[(vc,1.)],bc,4000)
                    row['shown_equity']=actual;row['shown']=vv
                rows.append(row)
            ev=Event(k,s,amt,cs);hist.append(ev);pending.append(ev)
            if k=='board':
                board+=cs;mx=0;inc=bb
                for p in seats:p.bet=0
            elif k in ('blind','ante','call','raise'):
                p=seats[s];added=amt-p.bet if k=='raise' else amt
                if k=='raise':inc=max(inc,amt-mx)
                p.stack-=added;pot+=added
                if k!='ante':p.bet+=added;mx=max(mx,p.bet)
                if p.stack<=0:p.status='all_in'
            elif k=='fold':seats[s].status='folded'
            elif k=='stack':seats[s].stack=amt
    cpu_times.sort()
    print('full_history_scaled_cpu_us',{'decisions':len(cpu_times),'p99':cpu_times[int(len(cpu_times)*.99)],'p999':cpu_times[int(len(cpu_times)*.999)],'max':cpu_times[-1],'over_1ms':sum(x>1000 for x in cpu_times)})
    json.dump(rows,open(out,'w'))
    print('decisions',len(rows),'action agreement',sum(x['chosen']==x['recorded'] for x in rows)/len(rows))
    for n in (8,7,6,5,4,3,2):
        rs=[r for r in rows if r['n']==n]
        print(n,len(rs),dict(collections.Counter((r['street'],r['recorded']) for r in rs)))
    for street in (3,4,5):
        rs=[r for r in rows if r['street']==street and r['cost'] and 'shown_equity' in r]
        for kind in ('call','raise','fold'):
            xs=[r for r in rs if r['recorded']==kind]
            if xs:print('shown',street,kind,len(xs),'estimate',round(sum(r['debug'].get('q',0) for r in xs)/len(xs),3),'actual',round(sum(r['shown_equity'] for r in xs)/len(xs),3))
if __name__=='__main__':replay(sys.argv[1],sys.argv[2])
