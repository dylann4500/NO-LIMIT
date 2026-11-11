"""Legality and CPU-budget stress test using only documented SDK states.
A scaled soft clock emulates the tournament's 2.5x slower CPUs. Wall-clock
preemption is reported separately; it is not multiplied as if it were work.
"""
import gc,random,statistics,time
import agent
from test_agent import state
from poker_agent_sdk import Event,ActionKind

class Clock:
    def perf_counter_ns(self):
        return int(time.perf_counter_ns()*2.5)

def run():
    rng=random.Random(200031)
    original=agent.time
    agent.time=Clock()
    times=[];wall=[];fail=0;largest=0;slow=[]
    bot=agent.Agent()
    try:
        for i in range(6000):
            cs=rng.sample(agent.CARD_NAMES,7)
            k=rng.choice([0,0,0,3,3,4,5]);n=rng.randrange(2,9)
            chips=rng.randrange(20,20000)
            cost=rng.choice([0,20,rng.randrange(1,chips+1),chips])
            s=state(cs[:2],cs[2:2+k],n=n,stack=chips,cost=cost,pot=rng.randrange(40,40000),can_raise=i%3!=0)
            s.time_bank_ms=[0,5,20,50,100][i%5]
            if i%10==0:
                s.config.payouts=[40,25,20,10,5,0,0,0]
            t=time.process_time_ns();w=time.perf_counter_ns()
            action,m=bot.act(s,b'')
            wall.append((time.perf_counter_ns()-w)/1000)
            times.append((time.process_time_ns()-t)*2.5/1000)
            if times[-1]>750:
                slow.append((round(times[-1],1),i,k,n,cost,chips,s.config.payouts))
            largest=max(largest,len(m))
            legal=next((a for a in s.legal_actions if a.kind==action.kind),None)
            if legal is None or action.kind==ActionKind.RAISE and not legal.min_amount<=action.amount<=legal.max_amount:
                fail+=1
    finally:
        agent.time=original
    times.sort();wall.sort()
    print({'decisions':len(times),'illegal':fail,'memory_bytes_max':largest,
       'slower_cpu_us':{'p50':round(times[len(times)//2],1),'p99':round(times[int(len(times)*.99)],1),
       'p999':round(times[int(len(times)*.999)],1),'max':round(times[-1],1), 'over_1ms':sum(t>1000 for t in times)},
       'local_wall_us':{'p99':round(wall[int(len(wall)*.99)],1),'max':round(wall[-1],1)}})
    print('slowest cases:',sorted(slow,reverse=True)[:8])

if __name__=='__main__':run()
