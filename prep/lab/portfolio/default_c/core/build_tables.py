"""Build tables_<variant>.json for this core (claude_default_c_r3's preflop tables) under a variant's rules (engine.py,
RULES section). Offline only: the bot reads the JSON and never imports this file.

usage (from lab/):  ../.venv/bin/python portfolio/default_c/core/build_tables.py <variant> [--procs 6] [--scale 1.0]
                    ../.venv/bin/python portfolio/default_c/core/build_tables.py holdem --legacy field_bots/claude_default_c_r3/tables.json
--legacy copies the eval7 table the hold'em bot shipped with (field_bots/claude_default_c_r3/build_tables.py), every
original field unchanged, and adds the engine's metadata (variant, n_hole, total, keys). That is tables_holdem.json.

Fields (per-class lists are indexed by class id), as in the original tables.json:
  classes, ncomb      class names ("AA", "AKs", "AKo"; rank + suit label per card for 3+ hole cards), hands per class
  eq1                 equity vs. one random hand
  eq3                 share of the pot vs. three random hands
  shove_order         class ids by eq1, best first ("top p" ranges)
  open_order          class ids by 0.55 * z(eq1) + 0.45 * z(eq3), best first (opening / playability ranking)
  grid                range widths (fractions of all hands)
  eq_top              eq_top[h][b]: heads-up equity of class h vs. a hand from the top grid[b] of shove_order
plus engine metadata: variant, n_hole, total, keys (engine.canon key per class), build.

Method: Monte Carlo under the variant's showdown(). eq1 and eq3 deal the board and the villain hands at random from the
cards left (exact card removal). eq_top is stratified as in lab/v2/core/build_tables.py: each board draws one villain
hand from every slice of shove_order between neighbouring grid widths; a slice is weighted by its size. "Top p" is
whole classes in order until they hold p of all hands (the original cut the last hold'em class to hit p exactly).
"""
import argparse, importlib.util, json, os, random, sys, time
from bisect import bisect_right
from itertools import combinations
from multiprocessing import get_context

HERE = os.path.dirname(os.path.abspath(__file__))
GRID = [0.02, 0.03, 0.045, 0.06, 0.08, 0.10, 0.125, 0.15, 0.18, 0.21, 0.25, 0.30, 0.35, 0.40, 0.47, 0.55, 0.65, 0.77, 0.90, 1.0]
RANKS = "23456789TJQKA"
# Boards per class at --scale 1: (eq1, eq3, grid). eq1 scores PER1 villain hands per board; a grid board one per slice.
BOARDS = {2: (4000, 6000, 6000), 3: (600, 700, 700), 4: (120, 120, 64)}
PER1 = 4
E = None
_G = {}


def load_engine(variant):
    os.environ["POKER_VARIANT"] = variant
    os.environ.pop("V2_STDLIB", None)
    spec = importlib.util.spec_from_file_location("dc_build_engine", os.path.join(HERE, "engine.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def class_name(key):
    if len(key) == 2:
        a, b = key
        if a >> 2 == b >> 2:
            return RANKS[a >> 2] * 2
        return RANKS[a >> 2] + RANKS[b >> 2] + ("s" if a & 3 == b & 3 else "o")
    return "".join(RANKS[c >> 2] + "abcd"[c & 3] for c in key)


def key_of_name(n):
    a, b = RANKS.index(n[0]) * 4, RANKS.index(n[1]) * 4
    return (a, b + 1) if len(n) == 2 or n[2] == "o" else (a, b)


def _work_eq(a):
    """(ci, n1, n3, seed) -> (eq1, eq3) of class ci."""
    ci, n1, n3, seed = a
    prep, val, N = E.prep, E.val, E.N_HOLE
    rng = random.Random(seed)
    hero = list(_G["keys"][ci])
    rest = [c for c in E.DECK if c not in hero]
    w1 = c1 = 0.0
    for _ in range(n1):
        smp = rng.sample(rest, 5 + PER1 * N)
        p = prep(smp[:5])
        hv = val(hero, p)
        for j in range(PER1):
            x = val(smp[5 + j * N:5 + (j + 1) * N], p)
            c1 += 1
            if hv > x:
                w1 += 1.0
            elif hv == x:
                w1 += 0.5
    tot = 0.0
    for _ in range(n3):
        smp = rng.sample(rest, 5 + 3 * N)
        p = prep(smp[:5])
        hv = val(hero, p)
        ties, win = 1, True
        for k in range(3):
            x = val(smp[5 + k * N:5 + (k + 1) * N], p)
            if x > hv:
                win = False
                break
            if x == hv:
                ties += 1
        if win:
            tot += 1.0 / ties
    return w1 / max(1.0, c1), tot / max(1, n3)


def _work_grid(a):
    """(ci, edges, boards, seed) -> per-slice (wins, count) of class ci vs. one hand per board drawn from each slice
    [edges[i], edges[i+1]) of shove_order's hand positions (as lab/v2/core/build_tables.py's _work)."""
    ci, edges, boards, seed = a
    keys, order, cum, perms = _G["keys"], _G["order"], _G["cum"], E._PERMS
    prep, val = E.prep, E.val
    rng = random.Random(seed)
    R = rng.random
    hero = list(keys[ci])
    hs = set(hero)
    rest = [c for c in E.DECK if c not in hs]
    ns = len(edges) - 1
    wins, cnt = [0.0] * ns, [0] * ns
    for _ in range(boards):
        board = rng.sample(rest, 5)
        bs = hs.union(board)
        p = prep(board)
        hv = val(hero, p)
        for i in range(ns):
            lo, span = edges[i], edges[i + 1] - edges[i]
            if span <= 0:
                continue
            k = keys[order[bisect_right(cum, lo + int(R() * span))]]
            pm = perms[int(R() * 24)]
            v = [(c & ~3) | pm[c & 3] for c in k]
            if not bs.isdisjoint(v):
                continue
            x = val(v, p)
            cnt[i] += 1
            if hv > x:
                wins[i] += 1.0
            elif hv == x:
                wins[i] += 0.5
    return wins, cnt


def _pool_map(fn, jobs, procs):
    with get_context("fork").Pool(procs) as pool:
        return pool.map(fn, jobs, chunksize=max(1, len(jobs) // (procs * 16)))


def build(variant, procs, scale, out, seed=""):
    global E
    E = load_engine(variant)
    t0 = time.time()
    counts = {}
    for h in combinations(E.DECK, E.N_HOLE):
        k = E.canon(h)
        counts[k] = counts.get(k, 0) + 1
    if E.N_HOLE == 2:  # hold'em order of names: AA, AKs, AKo, AQs, ...
        ranks = sorted({c >> 2 for c in E.DECK}, reverse=True)
        keys = []
        for i in ranks:
            for j in ranks:
                if i == j:
                    keys.append((i * 4, i * 4 + 1))
                elif i > j:
                    keys += [(i * 4, j * 4), (i * 4, j * 4 + 1)]
        assert set(keys) == set(counts)
    else:
        keys = sorted(counts, reverse=True)
    ncomb = [counts[k] for k in keys]
    total = sum(ncomb)
    assert total == E.TOTAL
    _G["keys"] = keys
    n1, n3, ng = (max(4, int(x * scale)) for x in BOARDS[min(E.N_HOLE, 4)])
    print(f"{variant}: {len(keys)} classes, {total} hands, boards eq1 {n1} x {PER1} / eq3 {n3} / grid {ng}, {procs} procs",
          flush=True)
    t1 = time.time()
    res = _pool_map(_work_eq, [(ci, n1, n3, f"{variant}:eq:{ci}{seed}") for ci in range(len(keys))], procs)
    eq1 = [round(a, 4) for a, b in res]
    eq3 = [round(b, 4) for a, b in res]
    print(f"  eq1/eq3: {time.time() - t1:.1f}s", flush=True)
    nk = len(keys)
    shove_order = sorted(range(nk), key=lambda k: -eq1[k])

    def z(v):
        m = sum(v) / len(v)
        sd = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5
        return [(x - m) / sd for x in v]
    z1, z3 = z(eq1), z(eq3)
    blend = [0.55 * z1[k] + 0.45 * z3[k] for k in range(nk)]
    open_order = sorted(range(nk), key=lambda k: -blend[k])
    cum, t = [], 0
    for ci in shove_order:
        t += ncomb[ci]
        cum.append(t)
    _G["order"], _G["cum"] = shove_order, cum
    edges, pos, k = [0], 0, 0
    for g in GRID:
        n = max(1, round(g * total))
        while pos < n:
            pos += ncomb[shove_order[k]]
            k += 1
        edges.append(pos)
    sizes = [edges[i + 1] - edges[i] for i in range(len(GRID))]
    t1 = time.time()
    rc = _pool_map(_work_grid, [(ci, edges, ng, f"{variant}:grid:{ci}{seed}") for ci in range(nk)], procs)
    print(f"  grid: {time.time() - t1:.1f}s", flush=True)
    eq_top = []
    for w, c in rc:
        row, sw, sc = [], 0.0, 0.0
        for i, s in enumerate(sizes):
            sw += s * w[i]
            sc += s * c[i]
            row.append(round(sw / sc, 4) if sc else (row[-1] if row else 0.5))
        eq_top.append(row)
    secs = round(time.time() - t0, 1)
    tab = {"variant": variant, "n_hole": E.N_HOLE, "total": total, "classes": [class_name(k) for k in keys],
           "keys": [list(k) for k in keys], "ncomb": ncomb, "eq1": eq1, "eq3": eq3, "shove_order": shove_order,
           "open_order": open_order, "grid": GRID, "eq_top": eq_top,
           "build": {"method": "Monte Carlo, portfolio/default_c/core/build_tables.py", "boards": [n1, n3, ng],
                     "per1": PER1, "scale": scale, "procs": procs, "seconds": secs}}
    with open(out, "w") as f:
        json.dump(tab, f, separators=(",", ":"))
    print(f"wrote {out} in {secs}s ({os.path.getsize(out) // 1024} KB). shove top: "
          + " ".join(class_name(keys[i]) for i in shove_order[:10]) + " | open top: "
          + " ".join(class_name(keys[i]) for i in open_order[:10]), flush=True)


def convert_legacy(src, out):
    L = json.load(open(src))
    keys = [key_of_name(n) for n in L["classes"]]
    assert sum(L["ncomb"]) == 1326 and len(set(keys)) == 169
    tab = dict(L)  # every original field, values unchanged
    tab.update(variant="holdem", n_hole=2, total=1326, keys=[list(k) for k in keys],
               build={"method": "eval7 Monte Carlo, field_bots/claude_default_c_r3/build_tables.py (copied, values unchanged)"})
    with open(out, "w") as f:
        json.dump(tab, f, separators=(",", ":"))
    back = json.load(open(out))
    assert all(back[k] == L[k] for k in L), "legacy fields changed"
    print(f"wrote {out} from {src}; original fields identical: {sorted(L)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant")
    ap.add_argument("--procs", type=int, default=min(6, os.cpu_count() or 6))
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--out", default="")
    ap.add_argument("--seed", default="", help="a different seed gives an independent table (for measuring noise)")
    ap.add_argument("--legacy", default="", help="copy this eval7-built hold'em table instead of building")
    a = ap.parse_args()
    out = a.out or os.path.join(HERE, f"tables_{a.variant}.json")
    if a.legacy:
        convert_legacy(a.legacy, out)
    else:
        build(a.variant, min(6, a.procs), a.scale, out, a.seed)


if __name__ == "__main__":
    main()
