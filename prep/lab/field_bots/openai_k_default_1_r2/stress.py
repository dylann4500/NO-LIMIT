"""Run the kit with a CPU-cost multiplier, without importing simulator code."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", type=int, default=200)
    ap.add_argument("--seed", type=int, default=117)
    ap.add_argument("--multiplier", type=float, default=2.5)
    ap.add_argument("--seats")
    ap.add_argument("--report-prefix", type=Path)
    args = ap.parse_args()
    if args.multiplier < 1:
        ap.error("--multiplier must be at least 1")
    source = Path(__file__).with_name("agent.py").resolve()
    repo = Path(__file__).resolve().parents[3]
    prefix = (args.report_prefix or source.parent / "results" / "slow_retest").resolve()
    prefix.parent.mkdir(parents=True, exist_ok=True)
    cpu_path = str(prefix) + "_cpu.json"
    report_path = str(prefix) + ".json"
    wrapper = f'''
import atexit
import importlib.util
import json
import time
spec = importlib.util.spec_from_file_location("real_agent", {str(source)!r})
real = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real)
TIMES = []
class Agent(real.Agent):
    def act(self, state, memory):
        start = time.thread_time_ns()
        result = super().act(state, memory)
        elapsed = time.thread_time_ns() - start
        TIMES.append(elapsed)
        target = int(elapsed * {args.multiplier!r})
        while time.thread_time_ns() - start < target:
            pass
        return result
@atexit.register
def report():
    ss = sorted(TIMES)
    if ss:
        data = {{"decisions": len(ss), "multiplier": {args.multiplier!r},
                "cpu_us_p50": round(ss[len(ss)//2]/1000, 1),
                "cpu_us_p99": round(ss[int(len(ss)*.99)]/1000, 1),
                "cpu_us_p99_9": round(ss[int(len(ss)*.999)]/1000, 1),
                "cpu_us_max": round(ss[-1]/1000, 1),
                "over_400us": sum(t > 400000 for t in ss),
                "scaled_cpu_ms_max": round(ss[-1]*{args.multiplier!r}/1e6, 3)}}
        with open({cpu_path!r}, "w") as out:
            json.dump(data, out, indent=2)
'''
    with tempfile.TemporaryDirectory(prefix="pokerbot_slow_") as tmp:
        Path(tmp, "agent.py").write_text(wrapper)
        cmd = [sys.executable, str(repo / "lab" / "field_kit" / "play.py"), tmp,
               "--tables", str(args.tables), "--seed", str(args.seed)]
        if args.seats:
            cmd.extend(["--seats", args.seats])
        with open(report_path, "w") as out:
            subprocess.run(cmd, cwd=repo, stdout=out, check=True)
    result = json.loads(Path(report_path).read_text())
    print(json.dumps({"upload_test": result["upload_test"], "self": result["results"]["self"],
                      "failed": result["failed"], "report": report_path,
                      "cpu_report": cpu_path}, indent=2))


if __name__ == "__main__":
    main()
