"""One mock scored round: every entrant plays one 8-seat table per iteration, like the real rounds.
usage: league.py [--iters 1500] [--entrants DIR ...] [--ours submission/upload] [--out ../league/r1] [--procs 8]
                 [--seed 1] [--time-scale 0.7] [--schedule slow|mid|fast|event] [--hh-iters 150]
Entrants are folders holding a portal-API agent.py: by default every lab/field_bots/<name>, plus our submission bot as
"ours" (the generated policy with lab/adapter.py, so it plays exactly as it would upload). Short tables get fillers whose
finishes don't count. Decisions are timed at decision_ms and time_bank_ms scaled by --time-scale (this Mac is ~2.5x
faster than the build box: tools/calibrate.py measures 1.2-1.3x; 0.7 leaves margin), so slow bots time out as in production.
Writes <out>/leaderboard.json and <out>/hh/<name>.jsonl.gz: each hand of the first --hh-iters iterations that entrant
played, with its own hole cards, others' only when shown, seats named, and its failed decisions. Prints the board."""
import argparse, gzip, json, math, os, random, sys, time
from multiprocessing import get_context
HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "fake_sdk"), os.path.join(HERE, "field_kit")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import engine
from platform_sim import Plat, Stats, play_platform_table

SCHEDULES = {
    "slow": [[10, 20], [15, 30], [25, 50], [40, 80], [60, 120], [100, 200], [150, 300], [250, 500]],
    "mid": [[10, 20], [15, 30], [20, 40], [30, 60], [40, 80], [50, 100], [75, 150], [100, 200], [150, 300], [200, 400],
            [300, 600], [400, 800], [500, 1000]],
    "fast": [[10, 20], [20, 40], [30, 60], [50, 100], [75, 150], [100, 200], [150, 300], [200, 400], [300, 600], [400, 800],
             [600, 1200], [800, 1600], [1000, 2000]],
}
PAY = [50, 30, 20, 0, 0, 0, 0, 0]
if engine.EVENT.get("blinds"):  # the kit's real schedule, once it's in event_config.json: --schedule event
    SCHEDULES["event"] = [list(x) for x in engine.EVENT["blinds"]]
_E = {}


def _init(entrants, scale):
    from play import load_agent
    for name, d in entrants:
        try:
            A = load_agent(d, "lg_" + name)
            _E[name] = [A(), A()]  # two copies per entrant, like the kit's two processes per folder
        except Exception as e:
            _E[name] = repr(e)
    _E["_scale"] = scale


def _work(a):
    names, iters, seed, sched, hh_iters = a
    rng = random.Random(seed)
    sc = _E["_scale"]
    live = [n for n in names if not isinstance(_E.get(n), str)]
    pts = {n: [] for n in live}
    plc = {n: [0] * 8 for n in live}
    stats = {n: [0, 0, {}] for n in live}  # decisions, over decision_ms, failures by kind
    hh = {n: [] for n in live}
    for it in range(iters):
        order = live[:]
        rng.shuffle(order)
        for t in range(0, len(order), 8):
            seat = order[t:t + 8]
            real = len(seat)
            if real < 8:  # fillers: entrants not at this table; their finishes don't count
                seat += rng.sample([x for x in live if x not in seat], 8 - real)
            rng.shuffle(seat)
            st = Stats()
            rec = [] if it < hh_iters else None
            elim, hands, surv = play_platform_table([Plat(_E[n]) for n in seat], schedule=sched, rng=rng, stats=st,
                                                    enforce_time=True, hh=rec, decision_ms=sc, time_bank_ms=100 * sc)
            p = engine.points_for(elim, surv, PAY, 8)
            pl = [0] * 8
            place = 8
            for g in elim:
                for s in g:
                    pl[s] = place - len(g) + 1
                place -= len(g)
            for r, s in enumerate(sorted(surv, key=lambda x: -surv[x])):
                pl[s] = r + 1
            counted = set(order[t:t + 8])
            for i, n in enumerate(seat):
                if n in counted:
                    pts[n].append(p[i])
                    plc[n][pl[i] - 1] += 1
            if rec is not None:
                tid = f"s{seed}i{it}t{t // 8}"
                names_by_id = {i: n for i, n in enumerate(seat)}
                for i, n in enumerate(seat):
                    if n not in counted:
                        continue
                    for h in rec:
                        hh[n].append({"table": tid, "seat": i, "names": names_by_id, "hand": h["hand"], "button": h["button"],
                                      "blinds": h["blinds"], "stacks": h["stacks"], "hole": h["holes"].get(i),
                                      "events": h["events"], "failed": [f for f in h["failed"] if f[0] == i]})
            for i, n in enumerate(seat):  # seat ids are table indexes (default conventions)
                if n in counted:
                    c = stats[n]
                    c[0] += st.seat_n[i]
                    c[1] += st.seat_slow[i]
                    for (sid, why), k in st.seat_fails.items():
                        if sid == i:
                            c[2][why] = c[2].get(why, 0) + k
    return pts, plc, stats, hh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=1500); ap.add_argument("--entrants", nargs="*")
    ap.add_argument("--ours", default=os.path.join(HERE, "..", "submission", "upload"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "league", "r1")); ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1); ap.add_argument("--time-scale", type=float, default=0.7)
    ap.add_argument("--schedule", default="slow"); ap.add_argument("--hh-iters", type=int, default=150)
    a = ap.parse_args()
    fb = os.path.join(HERE, "field_bots")
    dirs = a.entrants or sorted(os.path.join(fb, d) for d in os.listdir(fb) if os.path.exists(os.path.join(fb, d, "agent.py")))
    entrants = [(os.path.basename(os.path.normpath(d)), d) for d in dirs]
    if a.ours and os.path.exists(os.path.join(a.ours, "agent.py")):
        entrants.append(("ours", a.ours))
    os.makedirs(os.path.join(a.out, "hh"), exist_ok=True)
    t0 = time.time()
    per = [a.iters // a.procs + (i < a.iters % a.procs) for i in range(a.procs)]
    hh_per = [a.hh_iters // a.procs + (i < a.hh_iters % a.procs) for i in range(a.procs)]
    names = [n for n, _ in entrants]
    with get_context("fork").Pool(a.procs, initializer=_init, initargs=(entrants, a.time_scale)) as pool:
        res = pool.map(_work, [(names, per[i], a.seed * 1000 + i, SCHEDULES[a.schedule], hh_per[i]) for i in range(a.procs) if per[i]])
        broken = pool.apply(_broken)
    board = {}
    hh = {}
    for pts, plc, st, h in res:
        for n in pts:
            b = board.setdefault(n, {"pts": [], "places": [0] * 8, "decisions": 0, "slow": 0, "failed": {}})
            b["pts"] += pts[n]
            b["places"] = [x + y for x, y in zip(b["places"], plc[n])]
            d, slow, f = st[n]
            b["decisions"] += d
            b["slow"] += slow
            for k, v in f.items():
                b["failed"][k] = b["failed"].get(k, 0) + v
            hh.setdefault(n, []).extend(h[n])
    rows = []
    for n, b in board.items():
        v = b["pts"]
        m = sum(v) / len(v)
        se = math.sqrt(max(0.0, sum(x * x for x in v) / len(v) - m * m) / len(v))
        nf = sum(b["failed"].values())
        rows.append({"name": n, "mean": round(m, 2), "se": round(se, 2), "tables": len(v), "places": b["places"],
                     "win%": round(100 * b["places"][0] / len(v), 1), "top3%": round(100 * sum(b["places"][:3]) / len(v), 1),
                     "decisions": b["decisions"], "failed": b["failed"], "fail%": round(100 * nf / max(1, b["decisions"]), 2),
                     "over_limit%": round(100 * b["slow"] / max(1, b["decisions"]), 2), "hh_hands": len(hh.get(n, []))})
    rows.sort(key=lambda r: -r["mean"])
    json.dump({"iters": a.iters, "schedule": a.schedule, "time_scale": a.time_scale, "seconds": round(time.time() - t0),
               "broken": broken, "board": rows}, open(os.path.join(a.out, "leaderboard.json"), "w"), indent=1)
    for n, recs in hh.items():
        with gzip.open(os.path.join(a.out, "hh", n + ".jsonl.gz"), "wt") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
    print(f"{len(rows)} entrants, {a.iters} iterations, {time.time() - t0:.0f}s, schedule {a.schedule}, time scale {a.time_scale}")
    if broken:
        print("failed to load:", broken)
    print(f"{'#':>3} {'entrant':<26} {'points':>7} {'se':>5} {'win%':>6} {'top3%':>6} {'fail%':>6} {'>limit%':>8}  failures")
    for i, r in enumerate(rows):
        print(f"{i + 1:>3} {r['name']:<26} {r['mean']:>7.2f} {r['se']:>5.2f} {r['win%']:>6.1f} {r['top3%']:>6.1f} {r['fail%']:>6.2f} {r['over_limit%']:>8.2f}  {r['failed'] or ''}")


def _broken():
    return {n: v for n, v in _E.items() if isinstance(v, str) and n != "_scale"}


if __name__ == "__main__":
    main()
