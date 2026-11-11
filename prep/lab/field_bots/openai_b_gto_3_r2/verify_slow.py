"""Run the public play.py with extra CPU work per decision (no simulator imports)."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser()
p.add_argument('--tables',type=int,default=200)
p.add_argument('--seed',type=int,default=211)
p.add_argument('--factor',type=float,default=2.5)
a=p.parse_args()
if a.factor<1:p.error('--factor must be at least one')
here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='gto3-slow-') as folder:
    wrapper=Path(folder)/'agent.py'
    wrapper.write_text('''import importlib.util,time
spec=importlib.util.spec_from_file_location('gto3_verify',SOURCE)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class Agent(module.Agent):
    def act(self,state,memory):
        start=time.process_time_ns()
        result=super().act(state,memory)
        done=time.process_time_ns()
        until=done+int(EXTRA*(done-start))
        while time.process_time_ns()<until:pass
        return result
'''.replace('SOURCE',repr(str(here/'agent.py'))).replace('EXTRA',repr(a.factor-1)))
    subprocess.run([sys.executable,str(here.parents[1]/'field_kit'/'play.py'),folder,'--tables',str(a.tables),'--seed',str(a.seed)],cwd=here.parents[2],check=True)
