"""AI-generated opponents (lab/field_bots/<name>/agent.py, portal API) as archetypes g_<name> and fields gen_*.
field.py registers them on the first lookup of a g_* or gen_* key, so importing it stays cheap. Each bot loads once per
process as module genbot_<name>, with its folder on sys.path and as cwd; each seat is a Plat around a per-process pool of
two Agent() copies, as the platform runs them, so state kept on self behaves as in production.
The first process to register exports GEN_BOTS (the bots that loaded); pool workers it starts load exactly those and
raise if one fails. Export GEN_BOTS yourself to pin a set. Tables with a portal seat go through run.play.

usage: genfield.py [--tables 150] [--procs 10]   load report, train/hold split, then failures and latency per bot
                                                    (2 seats of the bot plus 6 typical seats per table)
"""
import gc, hashlib, importlib.util, os, random, sys, time, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
DIR = os.path.join(HERE, "field_bots")
POOLS, FAILED, LOAD_S = {}, {}, {}
MIX = 0.7  # gen_mix: share of generated seats, the rest from `typical`


def scan(d=DIR):
    return sorted(n for n in os.listdir(d) if n[0] not in "_." and os.path.isdir(os.path.join(d, n)))


def load(name, d=None):
    """Imports <d>/agent.py as genbot_<name> and returns two Agent() copies. Same-named helper modules of different
    bots don't collide: the bot's own modules leave sys.modules after the import (its module keeps them)."""
    d = os.path.abspath(d or os.path.join(DIR, name))
    f = os.path.join(d, "agent.py")
    if not os.path.isfile(f):
        raise ImportError("no agent.py")
    import platform_sim  # noqa: F401  puts fake_sdk (poker_agent_sdk) on sys.path
    local = {x[:-3] for x in os.listdir(d) if x.endswith(".py")} | {x for x in os.listdir(d) if os.path.isfile(os.path.join(d, x, "__init__.py"))}
    saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k.split(".")[0] in local}
    before, mn, cwd, gce = set(sys.modules), "genbot_" + name, os.getcwd(), gc.isenabled()
    sys.path.insert(0, d)
    os.chdir(d)
    try:
        spec = importlib.util.spec_from_file_location(mn, f)
        m = sys.modules[mn] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return [m.Agent(), m.Agent()]
    except BaseException:
        sys.modules.pop(mn, None)
        raise
    finally:
        os.chdir(cwd)
        if d in sys.path:
            sys.path.remove(d)
        if gce:
            gc.enable()
        for k in set(sys.modules) - before - {mn}:
            if (getattr(sys.modules[k], "__file__", None) or "").startswith(d + os.sep):
                del sys.modules[k]
        sys.modules.update(saved)
        gc.collect()
        gc.freeze()


def _h(n):
    return int(hashlib.sha1(n.encode()).hexdigest(), 16)


def split(names):
    """(train, hold), stratified by prefix (claude/openai): in each group the round(n/3) names with the smallest stable
    hash are held out (at least one of a group of 2+). A new bot moves at most one other bot between the sides."""
    hold = set()
    for p in {n.split("_")[0] for n in names}:
        g = sorted((n for n in names if n.split("_")[0] == p), key=_h)
        hold.update(g[:max(1, round(len(g) / 3))] if len(g) > 1 else [])
    return [n for n in names if n not in hold], [n for n in names if n in hold]


def _seat(n):
    from platform_sim import Plat

    def make():
        p = POOLS.get(n)
        if p is None:
            p = POOLS[n] = load(n)
        return Plat(p)
    return make


def register():
    from field import ARCHETYPES, FIELDS
    if dict.__contains__(FIELDS, "gen_all"):
        return
    pin = os.environ.get("GEN_BOTS")
    names = [n for n in pin.split(",") if n] if pin else scan()
    if not pin:
        for n in names:
            t = time.perf_counter()
            try:
                POOLS[n] = load(n)
                LOAD_S[n] = time.perf_counter() - t
            except (Exception, SystemExit) as e:
                FAILED[n] = "".join(traceback.format_exception_only(e)).strip().splitlines()[-1][:300]
        names = [n for n in names if n in POOLS]
        os.environ["GEN_BOTS"] = ",".join(names)  # inherited by pool workers started from here on
    if not names:
        raise RuntimeError(f"no generated bot loaded from {DIR}: {FAILED}")
    ARCHETYPES.update({"g_" + n: _seat(n) for n in names})
    eq = lambda ns: {"g_" + n: 1 for n in ns}
    train, hold = split(names)
    typ = FIELDS["typical"]
    tw = sum(typ.values())
    F = {"gen_all": eq(names), "gen_claude": eq(n for n in names if n.startswith("claude_")),
         "gen_openai": eq(n for n in names if n.startswith("openai_")), "gen_train": eq(train), "gen_hold": eq(hold),
         # stands in for weaker or buggy teams; train bots only, so gen_hold stays unseen when tuning on it
         "gen_mix": {**{"g_" + n: MIX / len(train) for n in train}, **{k: (1 - MIX) * w / tw for k, w in typ.items()}} if train else {}}
    FIELDS.update({k: v for k, v in F.items() if v})


def _check(a):
    name, tables, seed = a
    import run
    from field import ARCHETYPES, FIELDS
    from platform_sim import Stats
    random.seed(seed)
    fr, st, typ = random.Random(seed), Stats(), FIELDS["typical"]
    t0 = time.perf_counter()
    for _ in range(tables):
        bots = [ARCHETYPES[s]() for s in random.choices(list(typ), list(typ.values()), k=6)] + [ARCHETYPES["g_" + name]() for _ in range(2)]
        random.shuffle(bots)
        run.play(bots, frng=fr, stats=st)
    lat = sorted(st.lat) or [0]
    q = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))] / 1e3
    lim = run.time_limits()[0] * 1e6
    return dict(name=name, tables=tables, sec=time.perf_counter() - t0, decisions=st.decisions, fails=dict(st.fails),
                us=[q(.5), q(.99), q(.999), lat[-1] / 1e3], over=sum(x > lim for x in lat), ex=[e[0] + ": " + str(e[2])[-200:] for e in st.fail_ex if e[0] != "timeout"][:2])


if __name__ == "__main__":
    import argparse
    from multiprocessing import Pool
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", type=int, default=150); ap.add_argument("--procs", type=int, default=10); ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    t = time.perf_counter()
    register()
    from field import FIELDS
    import run
    print(f"loaded {len(POOLS)} bots in {time.perf_counter() - t:.1f}s; {len(FAILED)} skipped")
    for n, why in FAILED.items():
        print(f"  SKIP {n}: {why}")
    for n in sorted(LOAD_S, key=LOAD_S.get, reverse=True)[:5]:
        print(f"  slowest import {n}: {LOAD_S[n]:.2f}s")
    for f in ("gen_train", "gen_hold"):
        print(f"{f}: {sorted(k[2:] for k in FIELDS.get(f, {}))}")
    dm, tb = run.time_limits()
    print(f"\n{a.tables} tables per bot, decision {dm:g} ms, bank {tb:g} ms (FIELD_TIME_SCALE); load average {os.getloadavg()[0]:.0f}")
    print(f"{'bot':24} {'dec':>6} {'fail%':>6} {'tmo%':>6} {'over%':>6} {'p50us':>6} {'p99us':>7} {'p99.9':>7} {'max_ms':>7}  failures")
    with Pool(a.procs) as pool:
        for r in pool.imap_unordered(_check, [(n, a.tables, a.seed * 1000 + i) for i, n in enumerate(sorted(POOLS))]):
            d = max(1, r["decisions"])
            print(f"{r['name']:24} {r['decisions']:6} {100 * sum(r['fails'].values()) / d:6.2f} {100 * r['fails'].get('timeout', 0) / d:6.2f} "
                  f"{100 * r['over'] / d:6.2f} {r['us'][0]:6.0f} {r['us'][1]:7.0f} {r['us'][2]:7.0f} {r['us'][3] / 1e3:7.1f}  {r['fails'] or ''}", flush=True)
            for e in r["ex"]:
                print("     ", e.replace("\n", " | ")[:240])
