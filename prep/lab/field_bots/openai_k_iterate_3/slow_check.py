"""Run public play.py with this bot's CPU work padded by a chosen factor."""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile


def run():
    p = argparse.ArgumentParser()
    p.add_argument('--factor', type=float, default=2.5)
    p.add_argument('--tables', type=int, default=200)
    p.add_argument('--seed', type=int, default=401)
    p.add_argument('--seats')
    args = p.parse_args()
    if not 1 <= args.factor <= 10:
        p.error('factor must be between 1 and 10')
    here = pathlib.Path(__file__).resolve().parent
    root = here.parents[2]
    wrapper = f'''import gc
import importlib.util
import time
_spec = importlib.util.spec_from_file_location('actual_bot', {str(here / 'agent.py')!r})
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
_base_act = _module.Agent.act

class Agent(_module.Agent):
    def act(self, state, memory):
        collect = gc.isenabled()
        if collect:
            gc.disable()
        start = time.thread_time_ns()
        try:
            result = _base_act(self, state, memory)
            target = start + int({args.factor!r} * (time.thread_time_ns() - start))
            while time.thread_time_ns() < target:
                pass
            return result
        finally:
            if collect:
                gc.enable()
'''
    with tempfile.TemporaryDirectory(prefix='openai_k_slow_') as folder:
        pathlib.Path(folder, 'agent.py').write_text(wrapper)
        cmd = [sys.executable, str(root/'lab/field_kit/play.py'), folder,
               '--tables', str(args.tables), '--seed', str(args.seed)]
        if args.seats:
            cmd += ['--seats', args.seats]
        result = subprocess.run(cmd, cwd=root, text=True, capture_output=True)
        if result.returncode:
            sys.stderr.write(result.stderr)
            sys.stdout.write(result.stdout)
            raise SystemExit(result.returncode)
        report = json.loads(result.stdout)
        report['cpu_padding_factor'] = args.factor
        print(json.dumps(report, indent=1))


if __name__ == '__main__':
    run()
