"""Run field-kit play with 2.5x the agent's measured decision CPU cost."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tables',type=int,default=200)
    parser.add_argument('--seed',type=int,default=876)
    args=parser.parse_args()
    folder=Path(__file__).resolve().parent
    play=folder.parents[1]/'field_kit'/'play.py'
    source='''import importlib.util
import time
spec=importlib.util.spec_from_file_location('equity_timing_target',BOT_PATH)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class Agent(module.Agent):
    def act(self,state,memory):
        start=time.thread_time_ns()
        result=super().act(state,memory)
        used=time.thread_time_ns()-start
        target=time.thread_time_ns()+int(used*1.5)
        while time.thread_time_ns()<target:
            pass
        return result
'''.replace('BOT_PATH',repr(str(folder/'agent.py')))
    with tempfile.TemporaryDirectory(prefix='equity_timing_') as tmp:
        (Path(tmp)/'agent.py').write_text(source)
        return subprocess.call([sys.executable,str(play),tmp,'--tables',str(args.tables),'--seed',str(args.seed)])


if __name__=='__main__':
    raise SystemExit(main())
