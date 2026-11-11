"""Public play.py test with the guard disabled and explicit CPU-time inflation.
The proxy only imports our own bot; simulator code is never inspected/imported.
"""
import argparse,json,os,subprocess,sys,tempfile,hashlib
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
parser=argparse.ArgumentParser()
parser.add_argument('--tables',type=int,default=200)
parser.add_argument('--scale',type=float,default=2.5)
parser.add_argument('--seed',type=int,default=509)
args=parser.parse_args()
# Slow the deadline clock as well as the execution charge, allowing the bot's
# work limiter to make the same adaptations it would on a slower CPU.
source='''import importlib.util,time,types,array,json,atexit,gc
spec=importlib.util.spec_from_file_location('strict_core',MAIN)
core=importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
clock=time.process_time_ns
cpu_samples=array.array('Q');wall_samples=array.array('Q');thread_samples=array.array('Q');over_cpu=[]
in_call=False;gc_started=0;gc_cpu=0
def gc_probe(phase,info):
 global gc_started,gc_cpu
 if phase=='start' and in_call:gc_started=clock()
 elif phase=='stop' and gc_started:
  gc_cpu+=clock()-gc_started;gc_started=0
gc.callbacks.append(gc_probe)
def save_probe():
 c=sorted(cpu_samples);w=sorted(wall_samples);th=sorted(thread_samples);n=len(c)
 with open(PROBE,'w') as f:
  json.dump({'decisions':n,'cpu_us':{'p50':c[n//2]/1000,'p99':c[int(n*.99)]/1000,'max':c[-1]/1000,'over_1ms':sum(x>1000000 for x in c)},'thread_cpu_us':{'p99':th[int(n*.99)]/1000,'max':th[-1]/1000,'over_1ms':sum(x>1000000 for x in th)},'wall_us':{'p99':w[int(n*.99)]/1000,'max':w[-1]/1000},'over_cpu_examples':over_cpu[:12]},f)
atexit.register(save_probe)
core.time=types.SimpleNamespace(process_time_ns=lambda:int(clock()*SCALE))
class Agent(core.Agent):
 def act(self,state,memory):
  global in_call,gc_cpu
  gc_cpu=0;in_call=True
  # The extra timing loop is a test artifact. Keep cyclic GC disabled through
  # that loop, just as the real bot does through its own decision work.
  enabled=gc.isenabled()
  if enabled:gc.disable()
  start=clock();thread_start=time.thread_time_ns();wall_start=time.perf_counter_ns()
  try:
   result=self._act(state,memory)
   used=clock()-start
   until=clock()+int(used*(SCALE-1))
   while clock()<until:pass
  finally:
   if enabled:gc.enable()
  cpu=clock()-start;wall=time.perf_counter_ns()-wall_start;thread=time.thread_time_ns()-thread_start
  in_call=False
  cpu_samples.append(cpu);wall_samples.append(wall);thread_samples.append(thread)
  if cpu>1000000:over_cpu.append({'cpu_us':cpu/1000,'work_cpu_us':used/1000,'thread_us':thread/1000,'gc_in_core_us':gc_cpu/1000,'wall_us':wall/1000,'hand':state.hand_number,'board_n':len(state.board),'events_n':len(state.events),'memory_n':len(memory)})
  return result
'''.replace('MAIN',repr(os.path.join(HERE,'agent.py'))).replace('SCALE',repr(args.scale))
with tempfile.TemporaryDirectory(prefix='poker_strict_slow_') as td:
 probe_path=os.path.join(td,'probe.json')
 with open(os.path.join(td,'agent.py'),'w') as f:f.write(source.replace('PROBE',repr(probe_path)))
 cmd=[sys.executable,os.path.join(ROOT,'lab','field_kit','play.py'),td,'--tables',str(args.tables),'--seed',str(args.seed)]
 p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=True)
 report=json.loads(p.stdout)
 with open(probe_path) as f:report['timing_probe']=json.load(f)
 report['seed']=args.seed
 report['agent_sha256']=hashlib.sha256(open(os.path.join(HERE,'agent.py'),'rb').read()).hexdigest()
 report['cpu_scale']=args.scale
 report['exception_guard_disabled']=True
 with open(os.path.join(HERE,'results_release_slow_machine.json'),'w') as f:json.dump(report,f,indent=1)
 print(json.dumps(report,indent=1))
 assert report['upload_test']['pass'],report['upload_test']
 assert not report['failed'].get('illegal',0),report['failed']
 assert not report['failed'].get('error',0),report['failed']
