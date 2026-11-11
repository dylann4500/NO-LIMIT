"""Local stand-in for the kit's `poker-agent play`: upload test, then 8-seat tables, JSON report on stdout.
usage: play.py <bot_dir> [--tables 200] [--seed 1] [--seats self,self,self,self,check_or_fold,check_or_fold,min_raiser,min_raiser]
<bot_dir>/agent.py must define Agent (portal API). Every `self` seat shares a pool of two Agent copies, like the
kit's two processes per folder, so state kept on self or in globals behaves as it does in production."""
import argparse, importlib.util, json, math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
for _p in (LAB, os.path.join(LAB, "fake_sdk")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import engine
from platform_sim import Plat, Stats, play_platform_table


class CheckOrFold:
    def act(self, o):
        return (1, 0) if o.to_call == 0 else (0, 0)


class MinRaiser:
    def act(self, o):
        return (2, o.min_raise_to) if o.can_raise else (1, 0)


EXAMPLES = {"check_or_fold": CheckOrFold, "min_raiser": MinRaiser}


def load_agent(bot_dir, name=None):
    bot_dir = os.path.abspath(bot_dir)
    if bot_dir not in sys.path:
        sys.path.insert(0, bot_dir)
    spec = importlib.util.spec_from_file_location(name or "agent_" + os.path.basename(bot_dir), os.path.join(bot_dir, "agent.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Agent


def places(elim, surv, n):
    pl, place = [0] * n, n
    for g in elim:
        for s in g:
            pl[s] = place - len(g) + 1
        place -= len(g)
    for r, s in enumerate(sorted(surv, key=lambda x: -surv[x])):
        pl[s] = r + 1
    return pl


def pct(v, q):
    return v[min(len(v) - 1, int(q * len(v)))] / 1e3 if v else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bot_dir"); ap.add_argument("--tables", type=int, default=200); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seats", default="self,self,self,self,check_or_fold,check_or_fold,min_raiser,min_raiser")
    a = ap.parse_args()
    Agent = load_agent(a.bot_dir)
    rng = random.Random(a.seed)
    out = {}
    # Upload test: heads-up, up to 20 hands, against check-or-fold, 1 ms and no bank.
    st, cap = Stats(), engine.MAX_HANDS
    engine.MAX_HANDS = 20
    try:
        play_platform_table([Plat([Agent()]), CheckOrFold()], rng=rng, stats=st, enforce_time=True, time_bank_ms=0, hand_cap=20)
        crash = None
    except Exception as e:
        crash = repr(e)
    finally:
        engine.MAX_HANDS = cap
    bad = sum(st.fails.values())
    out["upload_test"] = {"decisions": st.decisions, "failed": dict(st.fails), "crash": crash,
                          "pass": crash is None and st.decisions > 0 and bad <= 0.1 * st.decisions}
    # Tables.
    seats = a.seats.split(",")
    pool = [Agent(), Agent()]
    st = Stats()
    pts = {k: [] for k in set(seats)}
    plc = {k: [0] * len(seats) for k in set(seats)}
    for _ in range(a.tables):
        order = seats[:]
        rng.shuffle(order)
        bots = [Plat(pool) if k == "self" else EXAMPLES[k]() for k in order]
        elim, hands, surv = play_platform_table(bots, rng=rng, stats=st, enforce_time=True)
        p = engine.points_for(elim, surv, out.get("payouts") or [50, 30, 20, 0, 0, 0, 0, 0], len(order))
        pl = places(elim, surv, len(order))
        for i, k in enumerate(order):
            pts[k].append(p[i])
            plc[k][pl[i] - 1] += 1
    res = {}
    for k, v in pts.items():
        m = sum(v) / len(v)
        sd = math.sqrt(max(0.0, sum(x * x for x in v) / len(v) - m * m) / len(v))
        res[k] = {"mean_points": round(m, 2), "se": round(sd, 2), "seats": seats.count(k), "places_1_to_8": plc[k]}
    lat = sorted(st.lat)
    out.update(tables=a.tables, results=res, fair_share=12.5, decisions=st.decisions, failed=dict(st.fails),
               latency_us={"p50": round(pct(lat, .5), 1), "p99": round(pct(lat, .99), 1), "p99.9": round(pct(lat, .999), 1),
                           "max": round(lat[-1] / 1e3, 1) if lat else 0.0, "over_1ms": sum(1 for x in lat if x > 1e6)},
               memory_bytes_max=max(st.mem) if st.mem else 0)
    if st.fail_ex:
        out["first_errors"] = [str(e)[:400] for e in st.fail_ex[:3]]
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
