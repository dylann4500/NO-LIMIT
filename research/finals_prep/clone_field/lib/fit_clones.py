"""Fit clone parameter tables from ONE hand-history download and write a clone field.

usage: python -I fit_clones.py HANDS.jsonl.gz OUTDIR [--hero avalon] [--min-tables 100]
           [--workers 10] [--max-tables N] [--k 20]
Writes OUTDIR/acc.pkl (raw counts), OUTDIR/field.json (team, folder, weight = tables met) and
OUTDIR/teams/<slug>/{agent.py, clonecore.py, pre3.json, params.json}.
"""
import argparse, gzip, json, multiprocessing, os, pickle, re, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fitlib  # noqa: E402

NAMES = {}


def init(names):
    global NAMES
    NAMES = names


def work(lines):
    acc = fitlib.new_acc()
    for ln in lines:
        fitlib.add_table(acc, json.loads(ln), NAMES)
    return acc, len(lines)


def batches(fh, size, limit):
    buf, n = [], 0
    for line in fh:
        if line.startswith('{"you"'):
            continue
        buf.append(line)
        n += 1
        if len(buf) >= size:
            yield buf
            buf = []
        if limit and n >= limit:
            break
    if buf:
        yield buf


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "team"


def shrink(cnt, prior, k):
    n = sum(cnt)
    tot = sum(prior) or 1
    v = [(cnt[i] + k * prior[i] / tot) / (n + k) for i in range(4)]
    return [round(x, 4) for x in v]


def quantiles(hist, m=21):
    items = sorted((int(v), c) for v, c in hist.items())
    tot = sum(c for _, c in items)
    out, accn, i = [], 0, 0
    for j in range(m):
        target = (j + 0.5) / m * tot
        while i < len(items) - 1 and accn + items[i][1] < target:
            accn += items[i][1]
            i += 1
        out.append(items[i][0] / 20.0)
    return out


def build_params(cells, sizes, stats, pool, k):
    P = {"cells": {}, "sizes": {}}
    for key, prior in pool["cells"].items():
        P["cells"][key] = shrink(cells.get(key, [0, 0, 0, 0]), prior, k)
    for sk, ph in pool["sizes"].items():
        h = sizes.get(sk, {})
        P["sizes"][sk] = quantiles(h if sum(h.values()) >= 30 else ph)
    pl = pool["stats"]["ex_low"] / max(1, pool["stats"]["ex_n"])
    P["ex_low"] = round((stats.get("ex_low", 0) + 10 * pl) / (stats.get("ex_n", 0) + 10), 4)
    P["n_tables"] = stats.get("tables", 0)
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hands")
    ap.add_argument("out")
    ap.add_argument("--hero", default="avalon")
    ap.add_argument("--min-tables", type=int, default=100)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--max-tables", type=int, default=0)
    ap.add_argument("--k", type=float, default=20)
    a = ap.parse_args()
    t0 = time.perf_counter()
    acc = fitlib.new_acc()
    ntab = 0
    with gzip.open(a.hands, "rt") as fh:
        head = json.loads(fh.readline())
        names = {e["entry_id"]: e["team_name"] for e in head["entries"]}
        with multiprocessing.Pool(a.workers, init, (names,)) as pool:
            for part, n in pool.imap_unordered(work, batches(fh, 40, a.max_tables)):
                fitlib.merge(acc, part)
                ntab += n
    t1 = time.perf_counter()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "acc.pkl"), "wb") as f:
        pickle.dump(acc, f)
    # pooled field (everyone but the hero)
    teams = [t for t in acc["stats"] if t != a.hero]
    pool = fitlib.new_acc()
    sub = {"cells": {t: acc["cells"][t] for t in teams}, "sizes": {t: acc["sizes"].get(t, {}) for t in teams},
           "stats": {t: acc["stats"][t] for t in teams}}
    P = {"cells": {}, "sizes": {}, "stats": {}}
    for t in teams:
        fitlib.merge(pool, {"cells": {"*": sub["cells"][t]}, "sizes": {"*": sub["sizes"][t]},
                            "stats": {"*": sub["stats"][t]}})
    pooled = {"cells": pool["cells"]["*"], "sizes": pool["sizes"]["*"], "stats": pool["stats"]["*"]}
    big = [t for t in teams if acc["stats"][t]["tables"] >= a.min_tables]
    small = [t for t in teams if t not in big]
    groups = [(t, [t]) for t in big]
    if small:
        small.sort(key=lambda t: acc["stats"][t]["vpip"] / max(1, acc["stats"][t]["hands"]))
        m = (len(small) + 2) // 3
        for i, nm in enumerate(("rest tight", "rest medium", "rest loose")):
            g = small[i * m:(i + 1) * m]
            if g:
                groups.append((nm, g))
    tdir = os.path.join(a.out, "teams")
    if os.path.isdir(tdir):
        shutil.rmtree(tdir)
    field, used = [], set()
    for name, members in groups:
        g = fitlib.new_acc()
        for t in members:
            fitlib.merge(g, {"cells": {"*": acc["cells"][t]}, "sizes": {"*": acc["sizes"].get(t, {})},
                             "stats": {"*": acc["stats"][t]}})
        params = build_params(g["cells"]["*"], g["sizes"].get("*", {}), g["stats"]["*"], pooled, a.k)
        params["team"] = name
        params["members"] = members
        sl = slug(name)
        while sl in used:
            sl += "_"
        used.add(sl)
        d = os.path.join(tdir, sl)
        os.makedirs(d)
        with open(os.path.join(d, "params.json"), "w") as f:
            json.dump(params, f)
        for fn in ("agent.py", "clonecore.py", "pre3.json"):
            shutil.copy(os.path.join(HERE, fn), d)
        field.append({"team": name, "folder": os.path.join("teams", sl), "weight": params["n_tables"],
                      "members": members})
    with open(os.path.join(a.out, "field.json"), "w") as f:
        json.dump({"source": os.path.basename(a.hands), "hero": a.hero, "tables": ntab, "entries": field}, f, indent=1)
    t2 = time.perf_counter()
    print(f"{ntab} tables parsed in {t1 - t0:.1f}s; params for {len(field)} clones "
          f"({len(big)} teams + {len(field) - len(big)} tiers) written in {t2 - t1:.1f}s -> {a.out}")
    hs = fitlib.style(acc, a.hero)
    print("hero", a.hero, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in hs.items() if k != "places"})


if __name__ == "__main__":
    main()
