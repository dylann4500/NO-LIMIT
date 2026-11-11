"""SDK contract, edge-case and production-speed checks (no simulator imports)."""
import os,sys,random,time,pickle,statistics
sys.path.insert(0,os.path.abspath(os.path.join(os.path.dirname(__file__),'../../fake_sdk')))
from poker_agent_sdk import State,Seat,Config,Event,LegalAction,ActionKind
import agent as bot
rng=random.Random(1043)

def run(count=3000):
    elapsed=[];m=b'';slow=[];empty=0
    b=bot.Agent()
    for i in range(count):
        n=rng.choice([2,3,4,5,8]);hero=rng.randrange(n);stage=rng.randrange(4)
        cards=rng.sample(list(bot._CMAP),2+[0,3,4,5][stage]);hand=cards[:2];board=cards[2:]
        bb=rng.choice([20,100,400]);stack=rng.choice([1,3,8,20,60])*bb
        call=rng.choice([0,0,1,2,6,12])*bb;call=min(stack,call)
        bet=rng.choice([0,1,2])*bb;pot=rng.randrange(2,50)*bb+call
        seats=[Seat(j,stack if j==hero else rng.randint(1,100)*bb,bet if j==hero else bet+call,'active') for j in range(n)]
        if i%7==0 and n>2:seats[(hero+1)%n].status='all_in';seats[(hero+1)%n].stack=0
        if call:
            legal=[LegalAction(ActionKind.FOLD),LegalAction(ActionKind.CALL)]
        else:legal=[LegalAction(ActionKind.CHECK)]
        if i%4!=0 and stack>call:
            # Exercise a non-integer blind, strict minimum and short all-in raise.
            lo=min(bet+stack,bet+call+bb);hi=bet+stack
            legal.append(LegalAction(ActionKind.RAISE,lo,hi))
        config=Config(payouts=[50,30,20,0,0,0,0,0],decision_ms=1,time_bank_ms=100,memory_bytes=65536)
        ev=[Event('hand',amount=i)]
        for j in range(n):ev.append(Event('blind',j,bb//2 if j==0 else bb))
        if board:ev.append(Event('board',cards=board[:3]))
        if stage>1:ev.append(Event('board',cards=board[3:4]))
        if stage>2:ev.append(Event('board',cards=board[4:]))
        for j in range(n):
            if j!=hero and rng.random()<.6:ev.append(Event('raise',j,bet+call if call else bb))
        state=State(seat=hero,cards=hand,board=board,pot=pot,to_call=call,legal_actions=legal,history=[],phase='betting',seats=seats,
                    button=rng.randrange(n),blinds=[bb//2,bb],hand_number=i,players_remaining=n,config=config,time_bank_ms=100,events=ev)
        # Exercise the decision core without the defensive exception guard.
        mm=bot._fresh(state);bot._update(state,mm)
        ll={x.kind.value:x for x in legal}
        def passive():
            return bot.Action.check() if 'check' in ll else bot.Action.fold()
        action=b._decide(state,mm,ll,passive)
        assert action.kind.value in ll,(i,action,ll)
        if action.kind.value=='raise':
            r=ll['raise'];assert isinstance(action.amount,int) and r.min_amount<=action.amount<=r.max_amount
        # End-to-end timing includes event ingestion, serialization and legality.
        start=time.perf_counter_ns();a,mem=b.act(state,b'');dt=(time.perf_counter_ns()-start)/1000
        elapsed.append(dt)
        assert mem,(i,'caught exception')
        if dt>350:slow.append((round(dt,1),stage,n,call))
        # Truncated memory recovery returns a legal action and starts fresh.
        if i%101==0:
            a,_=b.act(state,b'broken');assert a.kind.value in ll
    elapsed.sort()
    print({'decisions':count,'local_us':{'p50':elapsed[count//2],'p99':elapsed[int(count*.99)],'p999':elapsed[int(count*.999)],'max':max(elapsed)},'slowest':sorted(slow,reverse=True)[:12]})

if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 3000)
