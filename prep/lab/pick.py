"""Pick the best library bot for a variant: every candidate plays the same seeded tables in that variant, then ranked.
usage: pick.py <variant> [--tables 600] [--procs 8] [--cands v2,portfolio/exploit,...] [--extra dir,dir] [--no-planb]
Each candidate sits once per table with 7 lab bots from the `typical` and `strong` fields (both variant-aware), on the
same seeds as every other candidate, so differences come from the bots. Plan B (the rule policy with lab/adapter.py,
tuned_gen1.json) is built for the variant and included unless --no-planb. --extra adds bots built for the variant at
kickoff (e.g. regenerated opponents) as candidates too. Prints two rankings with standard errors: A, each candidate alone against lab bots (weak; it rewards exploiting
them), and B, all candidates at every table with lab strong bots in the other seats (the closer stand-in for a strong
field, used for the pick)."""
import argparse, math, os, random, subprocess, sys
from multiprocessing import get_context
HERE = os.path.dirname(os.path.abspath(__file__))

_A = {}


def _init(dirs, variant):
    os.environ["POKER_VARIANT"] = variant
    for p in (HERE, os.path.join(HERE, "fake_sdk"), os.path.join(HERE, "field_kit")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from play import load_agent
    for d in dirs:
        try:
            A = load_agent(d, "pk_" + os.path.basename(os.path.normpath(d)) + str(abs(hash(d)) % 10 ** 6))
            _A[d] = [A(), A()]
        except Exception as e:
            _A[d] = repr(e)


def _work(a):
    cand, field, tables, seed = a
    import engine
    from platform_sim import Plat, Stats, play_platform_table
    from field import ARCHETYPES, FIELDS
    if isinstance(_A[cand], str):
        return cand, [], {"load": _A[cand]}
    names = list(FIELDS[field]); w = [FIELDS[field][k] for k in names]
    rng = random.Random(seed)
    pts, st = [], Stats()
    for _ in range(tables):
        pos = rng.randrange(8)
        bots = [ARCHETYPES[k]() for k in rng.choices(names, w, k=7)]
        bots.insert(pos, Plat(_A[cand]))
        elim, hands, surv = play_platform_table(bots, rng=rng, stats=st, enforce_time=True, decision_ms=0.7, time_bank_ms=70)
        pts.append(engine.points_for(elim, surv, [50, 30, 20, 0, 0, 0, 0, 0], 8)[pos])
    return cand, pts, dict(st.fails)


def _work_mixed(a):
    """Every candidate at the same table, lab `strong` bots in the remaining seats: the candidates are the strongest
    variant-capable opponents we have, so this is the closer stand-in for a strong field."""
    cands, tables, seed = a
    import engine
    from platform_sim import Plat, Stats, play_platform_table
    from field import ARCHETYPES, FIELDS
    live = [c for c in cands if not isinstance(_A[c], str)][:8]
    names = list(FIELDS["strong"]); w = [FIELDS["strong"][k] for k in names]
    rng = random.Random(seed)
    pts, st = {c: [] for c in live}, Stats()
    for _ in range(tables):
        seats = live + [None] * (8 - len(live))
        rng.shuffle(seats)
        bots = [Plat(_A[c]) if c else ARCHETYPES[rng.choices(names, w)[0]]() for c in seats]
        elim, hands, surv = play_platform_table(bots, rng=rng, stats=st, enforce_time=True, decision_ms=0.7, time_bank_ms=70)
        p = engine.points_for(elim, surv, [50, 30, 20, 0, 0, 0, 0, 0], 8)
        for i, c in enumerate(seats):
            if c:
                pts[c].append(p[i])
    return pts


def _show(title, agg):
    rows = []
    for c, (pts, fails) in agg.items():
        if not pts:
            rows.append((-1, 0, c, fails)); continue
        m = sum(pts) / len(pts)
        se = math.sqrt(max(0.0, sum(x * x for x in pts) / len(pts) - m * m) / len(pts))
        rows.append((m, se, c, fails))
    rows.sort(key=lambda r: -r[0])
    print(title)
    for i, (m, se, c, fails) in enumerate(rows):
        name = os.path.relpath(c, HERE) if c.startswith(HERE) else ("planB" if "pick_planb" in c else c)
        print(f"  {i + 1}. {name:<28} {m:6.2f} ± {se:.2f}   failures {fails or 0}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant"); ap.add_argument("--tables", type=int, default=600); ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--cands", default=""); ap.add_argument("--extra", default=""); ap.add_argument("--no-planb", action="store_true")
    a = ap.parse_args()
    cands = [x for x in a.cands.split(",") if x]
    if not cands:  # the library: v2 plus every finished portfolio entry
        pd = os.path.join(HERE, "portfolio")
        cands = ["v2"] + (sorted(os.path.join("portfolio", d) for d in os.listdir(pd) if os.path.exists(os.path.join(pd, d, "agent.py")))
                          if os.path.isdir(pd) else [])
    cands = [os.path.join(HERE, c) if not os.path.isabs(c) else c for c in cands] + [os.path.abspath(x) for x in a.extra.split(",") if x]
    if not a.no_planb:  # the rule policy, generated for this variant with the adapter appended
        d = os.path.join(HERE, "..", "league", "pick_planb_" + a.variant)
        os.makedirs(d, exist_ok=True)
        r = subprocess.run([sys.executable, "make_bot.py", "tuned_gen1.json", os.path.join(d, "agent.py"), "lookup", "[50,30,20,0,0,0,0,0]"],
                           cwd=HERE, env=dict(os.environ, POKER_VARIANT=a.variant), capture_output=True, text=True)
        if r.returncode == 0:
            cands.append(os.path.abspath(d))
        else:
            print("Plan B build failed:", r.stderr[-300:])
    jobs, per = [], max(1, a.tables // 2 // a.procs)
    for c in cands:
        for field in ("typical", "strong"):
            for i in range(a.procs):  # same seeds for every candidate: paired comparison
                jobs.append((c, field, per, 1000 * i + (7 if field == "typical" else 8)))
    with get_context("fork").Pool(a.procs, initializer=_init, initargs=(cands, a.variant)) as p:
        res = p.map(_work, jobs)
    agg = {}
    for c, pts, fails in res:
        g = agg.setdefault(c, [[], {}])
        g[0] += pts
        for k, v in fails.items():
            g[1][k] = g[1].get(k, 0) + v if isinstance(v, int) else v
    _show(f"variant {a.variant}, A: each candidate alone vs lab typical+strong, {per * a.procs * 2} tables each, same seeds "
          f"(lab bots are weak and reward exploiting them)", agg)
    with get_context("fork").Pool(a.procs, initializer=_init, initargs=(cands, a.variant)) as p:
        mres = p.map(_work_mixed, [(cands, max(1, a.tables // a.procs), 500 + i) for i in range(a.procs)])
    magg = {}
    for d in mres:
        for c, v in d.items():
            magg.setdefault(c, [[], {}])[0].extend(v)
    rows = _show(f"variant {a.variant}, B: all candidates at every table plus lab strong bots, {max(1, a.tables // a.procs) * a.procs} tables "
                 f"(closer to a strong field; use this one)", magg)
    best = rows[0][2]
    print("pick:", os.path.relpath(best, HERE) if best.startswith(HERE) else best)


if __name__ == "__main__":
    main()
