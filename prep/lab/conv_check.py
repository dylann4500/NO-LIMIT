"""How a portal bot holds up under every platform convention the portal leaves open (platform_sim.conv_grid).
usage: conv_check.py <bot_dir> [--tables 150] [--procs 8] [--field dir,dir,...] [--lab-field typical]
Seats the bot once per table with 7 field bots and reports its points and failed decisions per convention. A bot that
assumes one convention shows it as lost points or failures in the other rows."""
import argparse, math, os, random, sys
from multiprocessing import get_context
HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "fake_sdk"), os.path.join(HERE, "field_kit")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import engine
from platform_sim import Plat, Stats, conv_grid, play_platform_table

_A = {}
_BAD = [0, 0, 0]  # hero decisions, exceptions, illegal returns


class Watch:
    """Counts the hero's own exceptions and illegal returns; the platform's counters mix every seat."""
    def __init__(self, a):
        self.a = a

    def act(self, state, memory):
        _BAD[0] += 1
        try:
            r = self.a.act(state, memory)
        except Exception:
            _BAD[1] += 1
            raise
        try:
            act = r[0]
            la = next((x for x in state.legal_actions if x.kind == act.kind), None)
            if la is None or (getattr(act.kind, "value", act.kind) == "raise" and not la.min_amount <= int(act.amount) <= la.max_amount):
                _BAD[2] += 1
        except Exception:
            _BAD[2] += 1
        return r


def _init(dirs):
    from play import load_agent
    for i, d in enumerate(dirs):
        A = load_agent(d, "cc_" + os.path.basename(os.path.normpath(d)))
        _A[d] = [Watch(A()), Watch(A())] if i == 0 else [A(), A()]


def _work(a):
    hero, field, conv, tables, seed, lab = a
    rng = random.Random(seed)
    pts, st = [], Stats()
    _BAD[:] = [0, 0, 0]
    if lab:
        from field import ARCHETYPES, FIELDS
        names = list(FIELDS[lab]); w = [FIELDS[lab][k] for k in names]
    for _ in range(tables):
        pos = rng.randrange(8)
        if lab:  # lab bots read the engine's own state, so the convention can't affect them
            bots = [ARCHETYPES[k]() for k in rng.choices(names, w, k=7)]
            bots.insert(pos, Plat(_A[hero]))
        else:
            seat = rng.sample(field, 7)
            seat.insert(pos, hero)
            bots = [Plat(_A[d]) for d in seat]
        elim, hands, surv = play_platform_table(bots, rng=rng, conv=conv, stats=st, enforce_time=True,
                                                decision_ms=0.7, time_bank_ms=70)
        pts.append(engine.points_for(elim, surv, [50, 30, 20, 0, 0, 0, 0, 0], 8)[pos])
    return pts, list(_BAD), dict(st.fails)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bot"); ap.add_argument("--tables", type=int, default=150); ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--field", default=""); ap.add_argument("--lab-field", default="", help="e.g. typical: lab bots, unaffected by conventions")
    a = ap.parse_args()
    fb = os.path.join(HERE, "field_bots")
    field = [x for x in a.field.split(",") if x] or [os.path.join(fb, d) for d in sorted(os.listdir(fb))
                                                    if os.path.exists(os.path.join(fb, d, "agent.py"))
                                                    and os.path.abspath(os.path.join(fb, d)) != os.path.abspath(a.bot)]
    hero = a.bot
    grid = conv_grid() + [{"base": 0}, {"event_kind": "enum"}]
    if a.lab_field:
        field = []
    jobs = [(hero, field, c, a.tables, 77, a.lab_field) for c in grid]  # same seed per row: rows differ only by convention
    with get_context("fork").Pool(a.procs, initializer=_init, initargs=([hero] + field,)) as p:
        res = p.map(_work, jobs)
    print(f"{os.path.basename(os.path.normpath(hero))}: {a.tables} tables per row vs {len(field)} field bots")
    print(f"  {'convention':<104} {'points':>6} {'se':>5}  hero: decisions exceptions illegal | all seats' failures")
    for c, (pts, bad, fails) in zip(grid, res):
        m = sum(pts) / len(pts)
        se = math.sqrt(max(0.0, sum(x * x for x in pts) / len(pts) - m * m) / len(pts))
        print(f"  {str(c):<104} {m:6.2f} {se:5.2f}  {bad[0]:>9} {bad[1]:>10} {bad[2]:>7} | {fails or ''}")


if __name__ == "__main__":
    main()
