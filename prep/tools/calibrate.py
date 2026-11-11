"""Speed of this machine relative to the team build box, which is set up like the tournament machines.
usage: python tools/calibrate.py   ->  prints the --time-scale to pass to lab/league.py and FIELD_TIME_SCALE.
A bot timing out at 1 ms there times out at about (this machine's time / box time) ms here. Takes the best of
several runs, so a busy machine still calibrates close to its idle speed."""
import time

BOX_MS = 26.4  # this workload on the team build box (2 vCPU Xeon 8488C), best of 9; eval7 Monte Carlo is 1.3x slower there too


def work():
    """Interpreter-bound mix of what bots do per decision: integer maths, dict and list traffic, small loops."""
    d, s, a = {}, 0, []
    for i in range(200000):
        k = (i * 2654435761) & 0xFFFF
        d[k] = d.get(k, 0) + 1
        s += k % 7
        if not i & 15:
            a.append(k)
    a.sort()
    return s + len(d) + a[len(a) // 2]


def bench():
    best = 1e9
    for _ in range(9):
        t = time.perf_counter()
        work()
        best = min(best, (time.perf_counter() - t) * 1e3)
    return best


if __name__ == "__main__":
    ms = bench()
    print(f"{ms:.2f} ms per workload" + (f"; build box {BOX_MS:.2f}; time scale {ms / BOX_MS:.2f}" if BOX_MS else ""))
