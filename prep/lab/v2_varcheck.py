"""Variant check for a portal bot (v2 by default): points, failures and speed at 8-seat tables against lab bots.
usage: POKER_VARIANT=omaha ../.venv/bin/python v2_varcheck.py [bot_dir] [--field typical] [--tables 200] [--procs 8]
The lab engine and v2's core both read POKER_VARIANT, so the bot and the lab field play the same variant.
Reports, for the bot only: points per table (fair share 12.5), exceptions the core swallowed internally (its act()
turns them into check/fold, so the platform and conv_check never see them), exceptions and illegal actions that reached
the platform, platform failures (timeouts), and wall latency and thread CPU time per decision (preflop and postflop).
Platform defaults for conventions; decision_ms 0.7 and a 70 ms bank, as conv_check uses."""
import argparse, importlib.util, math, os, random, sys, time, traceback
from multiprocessing import get_context
HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "fake_sdk"), os.path.join(HERE, "field_kit")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import engine, pk
from platform_sim import Plat, Stats, play_platform_table

PAY = [50, 30, 20, 0, 0, 0, 0, 0]
_S = {}


def _load(d):
    d = os.path.abspath(d)
    if d not in sys.path:
        sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location("vc_" + os.path.basename(d), os.path.join(d, "agent.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Hero:
    """Times the bot (wall and thread CPU) and checks every returned action against the legal ones."""
    def __init__(self, a, rec):
        self.a, self.r = a, rec

    def act(self, state, memory):
        r = self.r
        t0, c0 = time.perf_counter_ns(), time.thread_time_ns()
        try:
            out = self.a.act(state, memory)
        except Exception:
            r["raised"] += 1
            raise
        c1, t1 = time.thread_time_ns(), time.perf_counter_ns()
        k = "disc" if str(getattr(getattr(state, "phase", "betting"), "value", getattr(state, "phase", "betting"))) != "betting" else "post" if state.board else "pre"
        r["wall_" + k].append(t1 - t0)
        r["cpu_" + k].append(c1 - c0)
        try:
            act = out[0]
            la = next((x for x in state.legal_actions if x.kind == act.kind), None)
            if la is None or (getattr(act.kind, "value", act.kind) in ("raise", "discard") and not la.min_amount <= int(act.amount) <= la.max_amount):
                r["illegal"] += 1
        except Exception:
            r["illegal"] += 1
        return out


def _init(bot):
    mod = _load(bot)
    core = getattr(mod, "_core", mod)
    rec = {"raised": 0, "illegal": 0, "swallowed": 0, "ex": [], "wall_pre": [], "wall_post": [], "cpu_pre": [], "cpu_post": [],
           "wall_disc": [], "cpu_disc": []}

    def wrap(fn):
        def w(*a, **k):
            try:
                return fn(*a, **k)
            except Exception:
                rec["swallowed"] += 1
                if len(rec["ex"]) < 3:
                    rec["ex"].append(traceback.format_exc(limit=4))
                raise
        return w
    for name in ("build_ctx", "preflop", "postflop", "process_events"):
        if hasattr(core, name):
            setattr(core, name, wrap(getattr(core, name)))
    dmod = getattr(core, "D", None)  # discard variants: v2's discard.py swallows its own exceptions too
    for name in ("discard_choice", "discard_to_come"):
        if dmod is not None and hasattr(dmod, name):
            setattr(dmod, name, wrap(getattr(dmod, name)))
    _S["agents"] = [Hero(mod.Agent(), rec), Hero(mod.Agent(), rec)]
    _S["rec"] = rec
    _S["engine"] = getattr(getattr(core, "E", None), "ENGINE", "eval7 (original core)")


def _work(a):
    field, tables, seed = a
    from field import ARCHETYPES, FIELDS
    rng = random.Random(seed)
    names = list(FIELDS[field]); w = [FIELDS[field][k] for k in names]
    rec = _S["rec"]
    for k in rec:
        rec[k] = [] if isinstance(rec[k], list) else 0
    pts, st = [], Stats()
    for _ in range(tables):
        pos = rng.randrange(8)
        bots = [ARCHETYPES[k]() for k in rng.choices(names, w, k=7)]
        bots.insert(pos, Plat(_S["agents"]))
        elim, hands, surv = play_platform_table(bots, rng=rng, stats=st, enforce_time=True, decision_ms=0.7, time_bank_ms=70)
        pts.append(engine.points_for(elim, surv, PAY, 8)[pos])
    return pts, dict(rec), dict(st.fails), _S["engine"]


def q(v, p):
    return v[min(len(v) - 1, int(p * len(v)))] / 1e3 if v else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bot", nargs="?", default=os.path.join(HERE, "v2"))
    ap.add_argument("--field", default="typical"); ap.add_argument("--tables", type=int, default=200)
    ap.add_argument("--procs", type=int, default=8); ap.add_argument("--seed", type=int, default=77)
    a = ap.parse_args()
    t0 = time.time()
    per = [a.tables // a.procs + (i < a.tables % a.procs) for i in range(a.procs)]
    with get_context("fork").Pool(a.procs, initializer=_init, initargs=(a.bot,)) as p:
        res = p.map(_work, [(a.field, n, a.seed * 1000 + i) for i, n in enumerate(per) if n])
    pts, fails, tot = [], {}, {}
    for r_pts, rec, f, eng in res:
        pts += r_pts
        for k, v in f.items():
            fails[k] = fails.get(k, 0) + v
        for k, v in rec.items():
            tot[k] = tot.get(k, [] if isinstance(v, list) else 0) + v
    m = sum(pts) / len(pts)
    se = math.sqrt(max(0.0, sum(x * x for x in pts) / len(pts) - m * m) / len(pts))
    print(f"{os.path.basename(os.path.normpath(a.bot))} variant={pk.VARIANT} engine={eng} field={a.field} tables={len(pts)} "
          f"({time.time() - t0:.0f}s)")
    nd = len(tot["wall_pre"]) + len(tot["wall_post"]) + len(tot["wall_disc"])
    print(f"  points {m:.2f} +- {se:.2f} (fair 12.5) | decisions {nd} swallowed {tot['swallowed']} raised {tot['raised']} "
          f"illegal {tot['illegal']} | platform failures {fails or 0}")
    for k in ("pre", "post", "disc", "all"):
        if k == "disc" and not tot["wall_disc"]:
            continue
        wv = sorted(tot["wall_pre"] + tot["wall_post"] + tot["wall_disc"]) if k == "all" else sorted(tot["wall_" + k])
        cv = sorted(tot["cpu_pre"] + tot["cpu_post"] + tot["cpu_disc"]) if k == "all" else sorted(tot["cpu_" + k])
        print(f"  {k:<4} n={len(wv):>6}  wall us p50 {q(wv, .5):6.0f} p99 {q(wv, .99):6.0f} p99.9 {q(wv, .999):6.0f} max {q(wv, 1):7.0f}"
              f"  | cpu us p50 {q(cv, .5):6.0f} p99 {q(cv, .99):6.0f} p99.9 {q(cv, .999):6.0f} max {q(cv, 1):7.0f}")
    for e in tot["ex"][:3]:
        print("  swallowed exception:\n" + e)


if __name__ == "__main__":
    main()
