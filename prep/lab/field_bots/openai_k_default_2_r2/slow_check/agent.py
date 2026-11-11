"""Test wrapper adding 1.5x thread CPU time, for a total 2.5x cost."""
from pathlib import Path
import importlib.util,time
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('slow_policy',str(ROOT/'agent.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class Agent(p.Agent):
 def act(self,state,memory):
  start=time.thread_time_ns();result=super().act(state,memory)
  used=time.thread_time_ns()-start;until=time.thread_time_ns()+int(used*1.5)
  while time.thread_time_ns()<until:pass
  return result
