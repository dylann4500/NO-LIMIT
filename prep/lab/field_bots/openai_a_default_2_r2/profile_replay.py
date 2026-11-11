"""Measure full SDK calls on reconstructed round-1 states, including serialization."""
import json
import marshal
import time
from analyze import ROOT
from replay import observations
import agent

lat=[];cpu=[];memory=b'';table=None;errors=[];maxmem=0;counts={}
bot=agent.Agent()
for s,r in observations():
    if s is None:continue
    if r['h']['table']!=table:table=r['h']['table'];memory=b''
    # Feed all public events since the previous decision, independent of which
    # action this revision would have taken in the historical hand.
    start=time.perf_counter_ns();tick=time.process_time_ns()
    a,memory=bot.act(s,memory)
    cpu.append(time.process_time_ns()-tick);lat.append(time.perf_counter_ns()-start)
    legal={x.kind:x for x in s.legal_actions}
    if a.kind not in legal or (agent.kind(a.kind)=='raise' and not legal[a.kind].min_amount<=a.amount<=legal[a.kind].max_amount):errors.append((table,s.hand_number,str(a)))
    maxmem=max(maxmem,len(memory))
    key=f'{r["street"]}:{agent.kind(a.kind)}';counts[key]=counts.get(key,0)+1
def quant(v):
    v=sorted(v)
    return {k:round(v[min(len(v)-1,int(q*len(v)))]/1000,3) for k,q in [('p50',.5),('p99',.99),('p99.9',.999),('max',1.)]}
report=dict(decisions=len(lat),illegal=errors,memory_bytes_max=maxmem,cpu_us=quant(cpu),wall_us=quant(lat),policy_actions=counts)
(ROOT/'validation/replay_profile.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
