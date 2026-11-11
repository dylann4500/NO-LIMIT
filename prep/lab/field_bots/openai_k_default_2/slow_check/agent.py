"""Test wrapper only: simulate 2.5 times the candidate's CPU cost.

Run play.py with this directory as bot_dir. The tournament entry point remains
../agent.py; this wrapper is never imported by the tournament policy.
"""
import importlib.util
from pathlib import Path
import time

_path = Path(__file__).resolve().parents[1] / 'agent.py'
_spec = importlib.util.spec_from_file_location('cpu_slowness_test', _path)
_policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_policy)

class Agent:
    def act(self, state, memory):
        start = time.thread_time_ns()
        result = _policy.Agent().act(state, memory)
        elapsed = time.thread_time_ns() - start
        end = time.thread_time_ns() + int(elapsed * 1.5)
        while time.thread_time_ns() < end:
            pass
        return result
