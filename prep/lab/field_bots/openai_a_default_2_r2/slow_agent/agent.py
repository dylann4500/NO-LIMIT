"""Local-only 2.5x CPU stress wrapper; not used by the submitted agent."""
import importlib.util
from pathlib import Path
from time import process_time_ns

path=Path(__file__).resolve().parents[1]/'agent.py'
spec=importlib.util.spec_from_file_location('slow_target',path)
target=importlib.util.module_from_spec(spec);spec.loader.exec_module(target)

class Agent(target.Agent):
    def act(self,s,memory):
        original=s.config.decision_ms
        s.config.decision_ms=(original or 1)/2.5
        tick=process_time_ns()
        try:result=super().act(s,memory)
        finally:s.config.decision_ms=original
        cpu=process_time_ns()-tick
        until=process_time_ns()+int(1.5*cpu)
        while process_time_ns()<until:pass
        return result
