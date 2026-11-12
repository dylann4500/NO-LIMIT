"""Metagame runner: many jobs, one process pool, paired seeds, resumable.

usage (kit Python, repo root):  python mrun.py JOBS.json [--workers 8]
JOBS.json: list of jobs. Each job:
  {"name": "...", "mode": "hero"|"tourney", "tables": N, "seed": "s1", "eps": 0.1, "beta": [0.06,0.08,0.12],
   hero mode:    "hero": SPEC, "base": [SPEC...], "mix": [[SPEC, share], ...]
   tourney mode: "entries": [SPEC...]   (tables = iterations; kit seat_iteration; fillers do not score)}
SPEC: "team:<field>:<Team>" | "arch:<field>:<name>" | "bot:/abs/dir" (hero only)
Opponents of table n depend only on (seed, n): 7 distinct base teams and 7 uniforms are drawn; seat i plays
a mix spec if its uniform falls under the cumulative shares, else its base team. So runs are paired across
heroes AND coupled across mix shares. Output: out/<name>.pkl
"""
import asyncio, json, multiprocessing, os, pickle, random, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
FIELDS = os.path.join(HERE, "fields")
OUT = os.path.join(HERE, "out")
JOBS = []
_CACHE = {}
_FC = {}


def fieldinfo(field):
    if field not in _FC:
        d = os.path.join(FIELDS, field)
        F = json.load(open(os.path.join(d, "field.json")))
        _FC[field] = {"dir": d, "folder": {e["team"]: e["folder"] for e in F["entries"]},
                      "cdf": json.load(open(os.path.join(d, "cdf.json"))),
                      "adj": json.load(open(os.path.join(d, "adj.json")))}
    return _FC[field]


def load_params(spec):
    kind, field, name = spec.split(":", 2)
    fi = fieldinfo(field)
    if kind == "team":
        p = json.load(open(os.path.join(fi["dir"], fi["folder"][name], "params.json")))
        if name in fi["adj"]:
            p["cells"] = dict(p["cells"], **fi["adj"][name])
    else:
        p = json.load(open(os.path.join(fi["dir"], "arch", name + ".json")))
    p["cdf"] = fi["cdf"]
    return p


def get_clone(spec, eps, beta):
    import clonecore as cc
    from poker_agent_protocol.game import Action
    from poker_agent_protocol.runner import BotError, Reply

    class InProc:
        def __init__(self, clone):
            self.clone = clone

        async def act(self, state, memory):
            try:
                act, mem = self.clone.act(state, memory)
            except Exception as e:
                raise BotError(repr(e))
            return Reply(act, mem)

    k = (spec, eps, tuple(beta))
    if k not in _CACHE:
        p = load_params(spec)
        p["eps"] = eps
        p["beta"] = [0.0] + list(beta)
        _CACHE[k] = InProc(cc.Clone(p, Action))
    return _CACHE[k]


def lab(spec):
    return spec.split(":", 2)[2]


async def run(job, first, count):
    import fitlib
    from poker_agent_protocol.process import BotPool
    from poker_engine.play import play_table
    from poker_engine.scoring import table_places, table_points
    from poker_engine.seating import seat_iteration
    from poker_engine.table import SitAndGo, TableRules
    from poker_engine.variant import load_variant

    eps, beta, seed = job.get("eps", 0.1), job.get("beta", [0.06, 0.08, 0.12]), job.get("seed", "m1")
    rules = TableRules(variant="flop_discard_reveal", players=8, decision_ms=1, time_bank_ms=100,
                       hand_cap=250, hands_per_level=20)
    variant = load_variant(rules.variant)
    acc = fitlib.new_acc()
    rows = []
    if job["mode"] == "tourney":
        ents = job["entries"]
        names = [lab(s) for s in ents]
        bots = {lab(s): get_clone(s, eps, beta) for s in ents}
        for it in range(first, first + count):
            for k, seating in enumerate(seat_iteration(names, seed=seed, iteration=it)):
                sn = [s.entry for s in seating]
                table = SitAndGo(rules=rules, variant=variant, table_id=f"t{it}_{k}", seed=f"{seed}:{it}:{k}")
                result = await play_table(table, [bots[x] for x in sn])
                pts = table_points(result, table.payouts)
                # fillers logged under another name so their stats do not count
                fitlib.add_table(acc, {"seats": [x if not s.filler else "~" + x for x, s in zip(sn, seating)],
                                       "hands": table.log}, {})
                for i, s in enumerate(seating):
                    if not s.filler:
                        rows.append((it, s.entry, pts[i]))
        return rows, acc
    hero = job["hero"]
    pool = None
    if hero.startswith("bot:"):
        d = hero[4:]
        if not os.path.isabs(d):
            d = os.path.join(os.environ.get("MG_BOTS", "/Users/samuelchoi/NoLimit/NO-LIMIT/bots"), d)
        pool = BotPool([sys.executable, "-m", "poker_agent_sdk.guest", d], copies=1, cwd=d)
        hb = pool
    else:
        hb = get_clone(hero, eps, beta)
    base, mix = job.get("base", []), job.get("mix", [])
    try:
        for n in range(first, first + count):
            rng = random.Random(f"{seed}:opps:{n}")
            hero_seat = rng.randrange(8)
            us = [rng.random() for _ in range(7)]
            bo = rng.sample(base, 7) if base else [None] * 7
            specs = []
            for i in range(7):
                c, pick = 0.0, bo[i]
                for sp, sh in mix:
                    c += sh
                    if us[i] < c:
                        pick = sp
                        break
                specs.append(pick)
            seat_names = [lab(s) for s in specs]
            seats = [get_clone(s, eps, beta) for s in specs]
            seat_names.insert(hero_seat, "HERO")
            seats.insert(hero_seat, hb)
            table = SitAndGo(rules=rules, variant=variant, table_id=f"t{n}", seed=f"{seed}:{n}")
            result = await play_table(table, seats)
            pts = table_points(result, table.payouts)
            places = table_places(result)
            fitlib.add_table(acc, {"seats": seat_names, "hands": table.log}, {})
            rows.append((n, hero_seat, pts[hero_seat], places[hero_seat], result.hands_played,
                         result.failures[hero_seat], result.decisions[hero_seat]))
    finally:
        if pool:
            await pool.stop()
    return rows, acc


def worker(task):
    ji, first, count = task
    try:
        r, a = asyncio.run(run(JOBS[ji], first, count))
        return ji, r, a, None
    except Exception as e:
        import traceback
        return ji, [], None, traceback.format_exc()


def init(jobs):
    global JOBS
    JOBS = jobs


def main():
    import fitlib
    jf = sys.argv[1]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    jobs = json.load(open(jf))
    todo = [j for j in jobs if not os.path.exists(os.path.join(OUT, j["name"] + ".pkl"))]
    print(f"{len(jobs)} jobs, {len(todo)} to run", flush=True)
    tasks = []
    for ji, j in enumerate(todo):
        per = 10 if j["mode"] == "tourney" else 25
        for f in range(0, j["tables"], per):
            tasks.append((ji, f, min(per, j["tables"] - f)))
    # interleave so jobs finish in order but chunks spread
    res = {ji: ([], fitlib.new_acc(), [0]) for ji in range(len(todo))}
    left = {ji: sum(1 for t in tasks if t[0] == ji) for ji in range(len(todo))}
    t0 = time.perf_counter()
    with multiprocessing.Pool(workers, init, (todo,), maxtasksperchild=40) as pool:
        for ji, r, a, err in pool.imap_unordered(worker, tasks, chunksize=1):
            if err:
                print("ERROR in", todo[ji]["name"], err, flush=True)
                left[ji] -= 1
                continue
            rows, acc, _ = res[ji]
            rows += r
            fitlib.merge(acc, a)
            left[ji] -= 1
            if left[ji] == 0:
                j = todo[ji]
                rows.sort(key=lambda x: (x[0], str(x[1])))
                with open(os.path.join(OUT, j["name"] + ".pkl"), "wb") as f:
                    pickle.dump({"job": j, "rows": rows, "acc": acc}, f)
                if j["mode"] == "hero" and rows:
                    n = len(rows)
                    m = sum(x[2] for x in rows) / n
                    se = (sum((x[2] - m) ** 2 for x in rows) / (n - 1) / n) ** 0.5
                    fl = sum(x[5] for x in rows)
                    print(f"{j['name']:40s} n={n} pts={m:6.2f} se={se:.2f} fail={fl} t={time.perf_counter() - t0:.0f}s", flush=True)
                else:
                    print(f"{j['name']:40s} done t={time.perf_counter() - t0:.0f}s", flush=True)
                res[ji] = None


if __name__ == "__main__":
    main()
