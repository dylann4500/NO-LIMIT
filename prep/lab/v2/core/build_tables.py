"""Build tables_<variant>.json for the v2 core: preflop hand classes and equity vs. range width under that variant's
rules (engine.py, RULES section). Offline only: the bot reads the JSON and never imports this file.

usage (from lab/):  ../.venv/bin/python v2/core/build_tables.py <variant> [--procs 8] [--scale 1.0] [--out PATH]
                    ../.venv/bin/python v2/core/build_tables.py holdem --legacy field_bots/claude_default_b/tables.json
--scale multiplies the sample counts (0.25 for a rough table in a quarter of the time). --legacy converts the eval7
table the hold'em core shipped with (field_bots/claude_default_b/build_tables.py) into this format, values unchanged;
that is the shipped tables_holdem.json, so hold'em plays exactly as before.

Format (per-class lists are indexed by class id):
  variant, n_hole, total   the variant, hole cards per player, number of starting hands
  classes                  names: "AA", "AKs", "AKo" for two hole cards, else rank + suit label ("AaKaQb") per card
  keys                     engine.canon key of each class: card ints with suits relabelled 0.. in order of appearance
  ncomb                    starting hands in each class
  order                    class ids, best first, by 0.5 * equity vs. a random hand + 0.5 * equity vs. the top 15%
  cum                      per class, the fraction of all hands ranked at or above it (its percentile)
  grid                     range widths (fractions of all hands)
  eq                       eq[class][g]: heads-up all-in equity vs. a hand drawn from the top grid[g] of hands by order
  ps                       1 if two hole cards share a rank or a suit, else 0 (the core's implied-odds bonus)
  build                    how and how fast it was built

Method: Monte Carlo under the variant's showdown(). Each sampled board serves several villain hands, and the grid pass
draws one villain hand per board from each slice of the order between neighbouring grid widths, so every board feeds
every width (stratified). "Top w" is whole classes in order until they hold w of all hands, as the core reads it. A
villain hand that collides with the hero or the board is skipped; every board draws the same number per slice and each
slice is weighted by its size, so card removal is exact and the estimate unbiased. Passes: equity vs. random -> order0,
equity vs. the top 15% of order0 -> order, then the grid under the final order.
Noise (two independent builds, mean difference over dealt hands): two hole cards about 0.005 in equity; hole3 0.015;
Omaha 0.05 in equity and 0.16 in percentile at --scale 1, falling as 1/sqrt(scale). Omaha hands are close in equity,
so ordering them takes many samples: use a large --scale when there is time.
"""
import argparse, importlib.util, json, os, random, sys, time
from bisect import bisect_right
from itertools import combinations
from multiprocessing import get_context

HERE = os.path.dirname(os.path.abspath(__file__))
GRID = [0.01, 0.02, 0.03, 0.045, 0.06, 0.08, 0.10, 0.13, 0.16, 0.20, 0.25, 0.30, 0.36, 0.43, 0.50, 0.60, 0.72, 0.85, 1.0]
RANKS = "23456789TJQKA"
# Boards per class: (order passes, grid pass). A grid board costs one villain evaluation per grid slice (19).
BOARDS = {2: (4000, 6000), 3: (600, 700), 4: (120, 64)}
PER_ORDER = 4  # villain hands per board in the order passes
E = None
_G = {}


def load_engine(variant):
    os.environ["POKER_VARIANT"] = variant
    os.environ.pop("V2_STDLIB", None)
    spec = importlib.util.spec_from_file_location("v2_build_engine", os.path.join(HERE, "engine.py"))
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
    """Inverse of class_name for two hole cards."""
    a, b = RANKS.index(n[0]) * 4, RANKS.index(n[1]) * 4
    return (a, b + 1) if len(n) == 2 or n[2] == "o" else (a, b)


def pair_or_suited(key):
    return int(any(x >> 2 == y >> 2 or x & 3 == y & 3 for x, y in combinations(key, 2)))


def _work(a):
    """(ci, edges, boards, per, seed) -> per-slice (wins, count) of class ci vs. `per` hands drawn per board from each
    slice [edges[i], edges[i+1]) of _G['order']'s hand positions."""
    ci, edges, boards, per, seed = a
    keys, order, cum, perms = _G["keys"], _G["order"], _G["cum"], _G["perms"]
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
            for _ in range(per if span > 0 else 0):
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


def run_pass(name, order, edges, boards, per, procs, ncomb, variant, seed=""):
    """Sets the order the workers sample from, then runs every class in a fresh fork pool."""
    cum, t = [], 0
    for ci in order:
        t += ncomb[ci]
        cum.append(t)
    _G["order"], _G["cum"] = order, cum
    jobs = [(ci, edges, boards, per, f"{variant}:{name}:{ci}{seed}") for ci in range(len(ncomb))]
    t0 = time.time()
    with get_context("fork").Pool(procs) as pool:
        res = pool.map(_work, jobs, chunksize=max(1, len(jobs) // (procs * 16)))
    print(f"  pass {name}: {len(jobs)} classes x {boards} boards, {time.time() - t0:.1f}s", flush=True)
    return res


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
    _G["keys"], _G["perms"] = keys, E._PERMS
    nb_order, nb_grid = (max(4, int(x * scale)) for x in BOARDS[min(E.N_HOLE, 4)])
    print(f"{variant}: {len(keys)} classes, {total} hands, boards {nb_order}/{nb_grid}, {procs} procs", flush=True)
    by_id = list(range(len(keys)))
    # pass A: vs. a random hand -> order0; pass B: vs. the top 15% of order0 -> order; pass C: the grid under order
    ra = run_pass("random", by_id, [0, total], nb_order, PER_ORDER, procs, ncomb, variant, seed)
    e_rand = [w[0] / max(1, c[0]) for w, c in ra]
    order0 = sorted(by_id, key=lambda i: -e_rand[i])
    n15, k = 0, 0
    while n15 < round(0.15 * total):
        n15 += ncomb[order0[k]]
        k += 1
    rb = run_pass("top15", order0, [0, n15], nb_order, PER_ORDER, procs, ncomb, variant, seed)
    e15 = [w[0] / max(1, c[0]) for w, c in rb]
    order = sorted(by_id, key=lambda i: -(0.5 * e_rand[i] + 0.5 * e15[i]))
    edges, pos, k = [0], 0, 0  # top w = whole classes in order until they hold round(w * total) hands (as the core)
    for g in GRID:
        n = max(1, round(g * total))
        while pos < n:
            pos += ncomb[order[k]]
            k += 1
        edges.append(pos)
    sizes = [edges[i + 1] - edges[i] for i in range(len(GRID))]
    rc = run_pass("grid", order, edges, nb_grid, 1, procs, ncomb, variant, seed)
    eq = []
    for w, c in rc:
        row, sw, sc = [], 0.0, 0.0
        for i, s in enumerate(sizes):  # each slice weighted by its size: card removal comes from its hit rate
            sw += s * w[i]
            sc += s * c[i]
            row.append(round(sw / sc, 4) if sc else (row[-1] if row else 0.5))
        eq.append(row)
    cum, t = [0.0] * len(keys), 0
    for ci in order:
        t += ncomb[ci]
        cum[ci] = round(t / total, 5)
    secs = round(time.time() - t0, 1)
    tab = {"variant": variant, "n_hole": E.N_HOLE, "total": total, "classes": [class_name(k) for k in keys],
           "keys": [list(k) for k in keys], "ncomb": ncomb, "order": order, "cum": cum, "grid": GRID, "eq": eq,
           "ps": [pair_or_suited(k) for k in keys],
           "build": {"method": "stratified Monte Carlo, build_tables.py", "boards_order": nb_order, "boards_grid": nb_grid,
                     "per_order": PER_ORDER, "procs": procs, "seconds": secs}}
    with open(out, "w") as f:
        json.dump(tab, f, separators=(",", ":"))
    print(f"wrote {out} in {secs}s ({os.path.getsize(out) // 1024} KB). best: "
          + " ".join(class_name(keys[i]) for i in order[:12]), flush=True)


def convert_legacy(src, out):
    L = json.load(open(src))
    keys = [key_of_name(n) for n in L["classes"]]
    ncomb = [6 if len(n) == 2 else (4 if n[2] == "s" else 12) for n in L["classes"]]
    assert sum(ncomb) == 1326 and len(set(keys)) == 169
    tab = {"variant": "holdem", "n_hole": 2, "total": 1326, "classes": L["classes"], "keys": [list(k) for k in keys],
           "ncomb": ncomb, "order": L["order"], "cum": L["cum"], "grid": L["grid"], "eq": L["eq"],
           "ps": [int(n[0] == n[1] or n.endswith("s")) for n in L["classes"]],
           "build": {"method": "eval7 Monte Carlo, field_bots/claude_default_b/build_tables.py (converted, values unchanged)"}}
    with open(out, "w") as f:
        json.dump(tab, f, separators=(",", ":"))
    print(f"wrote {out} from {src}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant")
    ap.add_argument("--procs", type=int, default=min(8, os.cpu_count() or 8))
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--out", default="")
    ap.add_argument("--seed", default="", help="a different seed gives an independent table (for measuring noise)")
    ap.add_argument("--legacy", default="", help="convert this eval7-built hold'em table instead of building")
    a = ap.parse_args()
    out = a.out or os.path.join(HERE, f"tables_{a.variant}.json")
    if a.legacy:
        convert_legacy(a.legacy, out)
    else:
        build(a.variant, a.procs, a.scale, out, a.seed)


if __name__ == "__main__":
    main()
