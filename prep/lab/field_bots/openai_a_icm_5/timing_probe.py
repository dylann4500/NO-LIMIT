"""Run the public field-kit CLI with artificially slowed agent CPU work.
No simulator files are read or imported by this harness.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser()
p.add_argument('--tables',type=int,default=100)
p.add_argument('--seed',type=int,default=53)
p.add_argument('--factor',type=float,default=2.5)
a=p.parse_args()
source=Path(__file__).with_name('agent.py').resolve()
kit=source.parents[2]/'field_kit'/'play.py'
wrapper='''import importlib.util, time
s=importlib.util.spec_from_file_location("real_agent", SOURCE)
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
class Agent:
    def __init__(self): self.bot=m.Agent()
    def act(self,state,memory):
        start=time.perf_counter_ns(); cpu=time.process_time_ns()
        result=self.bot.act(state,memory)
        used=time.perf_counter_ns()-start
        cpu_used=time.process_time_ns()-cpu
        target=start+used+int(cpu_used*EXTRA)
        while time.perf_counter_ns()<target: pass
        return result
'''.replace('SOURCE',repr(str(source))).replace('EXTRA',repr(max(0.,a.factor-1)))
with tempfile.TemporaryDirectory(prefix='icm5_slow_') as folder:
    Path(folder,'agent.py').write_text(wrapper)
    subprocess.run([sys.executable,str(kit),folder,'--tables',str(a.tables),'--seed',str(a.seed)],check=True)
