"""usage: arena.py --agent me=<dir> [--agent old=<dir>] --seats me,tag,lag,... --tables N --procs 8 --seed 1
Seats are shuffled per table. Labels not given via --agent come from opponents.OPPS."""
import argparse
import importlib.util
import math
import multiprocessing as mp
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "fake_sdk"))
sys.path.insert(0, HERE)
import sim  # noqa: E402
import opponents  # noqa: E402

AGENTS = {}


def load(label, d):
    d = os.path.abspath(d)
    spec = importlib.util.spec_from_file_location("agent_" + label, os.path.join(d, "agent.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m.Agent


def make(label):
    if label in AGENTS:
        return AGENTS[label]()
    return opponents.OPPS[label]()


def work(args):
    seed, seats, ntab = args
    rng = random.Random(seed)
    out = []
    for _ in range(ntab):
        order = seats[:]
        rng.shuffle(order)
        bots = [make(k) for k in order]
        pts, places, P, hands = sim.play_table(bots, order, rng)
        fails = {}
        maxlat = {}
        for k, p in zip(order, P):
            fails[k] = fails.get(k, 0) + p.fails
            maxlat[k] = max(maxlat.get(k, 0), max(p.lat) if p.lat else 0)
        out.append((order, pts, places, fails, maxlat, hands))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", action="append", default=[])
    ap.add_argument("--seats", required=True)
    ap.add_argument("--tables", type=int, default=200)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    for s in a.agent:
        k, d = s.split("=", 1)
        AGENTS[k] = load(k, d)
    seats = a.seats.split(",")
    per = max(1, a.tables // a.procs)
    jobs = [(a.seed * 1000 + i, seats, per) for i in range(a.procs)]
    with mp.get_context("fork").Pool(a.procs) as pool:
        res = [r for chunk in pool.map(work, jobs) for r in chunk]
    pts = {}
    plc = {}
    fails = {}
    lat = {}
    for order, p, pl, f, ml, hands in res:
        for k, v, q in zip(order, p, pl):
            pts.setdefault(k, []).append(v)
            plc.setdefault(k, [0] * len(order))[q - 1] += 1
        for k, v in f.items():
            fails[k] = fails.get(k, 0) + v
        for k, v in ml.items():
            lat[k] = max(lat.get(k, 0), v)
    print("tables", len(res), "avg hands", round(sum(r[5] for r in res) / len(res), 1))
    for k in sorted(pts, key=lambda k: -sum(pts[k]) / len(pts[k])):
        v = pts[k]
        m = sum(v) / len(v)
        sd = math.sqrt(max(0.0, sum(x * x for x in v) / len(v) - m * m) / len(v))
        print("%-8s mean %6.2f  se %5.2f  n %5d  places %s  fails %d  maxlat_ms %.2f" % (
            k, m, sd, len(v), plc[k], fails.get(k, 0), lat.get(k, 0) * 1e3))


if __name__ == "__main__":
    main()
