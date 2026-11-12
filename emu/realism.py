"""How realistic is a synthetic field? Compare per-team playing profiles with the real regional field.

Both sides are measured the same way: research/post_event/field/extract.py on a hand-history
download (avalon's view, as on the night), then the same per-team rates. The real reference is
split the way a model would be validated:
  train = scored rounds 1-3 (what the steering/persona mix is tuned to)
  test  = scored rounds 4-6 (held out: does the synthetic field match a field it was not tuned on?)
and restricted to the real field's top-N teams by weighted total (the Finals invite the strongest).

  starter-kit/.venv/bin/python emu/realism.py real                 # build the reference (once)
  starter-kit/.venv/bin/python emu/realism.py compare RUN [--teams 'A,B,...']
RUN is an emu/runs/<run> folder; its scored-round downloads for avalon are extracted on demand.
"""

import argparse
import json
import pickle
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REAL = ROOT / "emu" / "runs" / "real_field"
EXTRACT = ROOT / "research" / "post_event" / "field" / "extract.py"
KITPY = str(ROOT / "starter-kit" / ".venv" / "bin" / "python")

# metric: (numerator, denominator), all from extract.py's per-team counters
METRICS = {
    "vpip": ("vpip", "hands"), "pfr": ("pfr", "hands"), "open_rate": ("rfi", "rfi_opp"),
    "three_bet": ("3b", "3b_opp"), "fold_to_3bet": ("f3b", "f3b_opp"), "jam_rate": ("jam", "hands"),
    "flop_fold_to_bet": ("s1_fold", "s1_face"), "turn_fold_to_bet": ("s2_fold", "s2_face"),
    "flop_aggression": ("s1_agg", "s1_act"), "cbet": ("cb", "cb_opp"),
    "wtsd": ("wtsd", "saw_flop"), "won_at_showdown": ("wsd", "wtsd"),
}
MIN_DEN = 30


def profiles(pkl: Path) -> dict:
    """{team name: {metric: rate, 'points': avg points per scored table, 'tables': n}}"""
    d = pickle.load(open(pkl, "rb"))
    names = d["names"]
    out = {}
    for entry, c in d["C"].items():
        if entry == "FILLER" or entry not in names:
            continue
        prof = {m: (c.get(n, 0) / c[den] if c.get(den, 0) >= MIN_DEN else None) for m, (n, den) in METRICS.items()}
        out[names[entry]] = prof
    pts: dict[str, list] = {}
    for row in d["rows"]:
        for seat in row[5]:
            if seat[0] in names:
                pts.setdefault(names[seat[0]], []).append(seat[1])
    for t, v in pts.items():
        if t in out:
            out[t]["points"], out[t]["tables"] = statistics.fmean(v), len(v)
    return out


def quant(vals: list[float]) -> tuple[float, float, float]:
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return (float("nan"),) * 3
    q = lambda p: vals[min(len(vals) - 1, int(p * (len(vals) - 1) + 0.5))]  # noqa: E731
    return q(0.1), q(0.5), q(0.9)


def build_real(top: int) -> dict:
    rounds = {k: profiles(REAL / f"r{k}.pkl") for k in range(1, 7)}
    teams = set.intersection(*(set(r) for r in rounds.values()))
    total = {t: sum(k * rounds[k][t].get("points", 0) for k in rounds) for t in teams}
    best = sorted(teams, key=lambda t: -total[t])[:top]
    ref = {"top": top, "teams": best, "weighted_total": {t: round(total[t], 2) for t in best}, "rounds": {}}
    for k, r in rounds.items():
        ref["rounds"][k] = {t: r[t] for t in best}
    (REAL / "reference.json").write_text(json.dumps(ref, indent=1))
    return json.loads((REAL / "reference.json").read_text())  # round keys as stored (strings)


def split(ref: dict, rounds: list[int]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {m: [] for m in [*METRICS, "points"]}
    for k in rounds:
        for prof in ref["rounds"][str(k)].values():
            for m in out:
                if prof.get(m) is not None:
                    out[m].append(prof[m])
    return out


def synthetic(run: Path, only: set[str] | None) -> dict[int, dict]:
    """Per scored round: profiles of the synthetic teams, from avalon's download."""
    res = {}
    for rdir in sorted((run / "rounds").glob("scored*")) + sorted(run.glob("round[0-9]*")):
        k = int("".join(ch for ch in rdir.name if ch.isdigit()))
        dl = sorted(p for p in (rdir / "downloads" / "avalon").glob("hands-*.jsonl.gz") if "first" not in p.name)
        if not dl:
            continue
        pkl = rdir / "avalon_view.pkl"
        if not pkl.exists():
            subprocess.run([KITPY, "-I", str(EXTRACT), str(dl[0]), str(pkl)], check=True, capture_output=True)
        prof = profiles(pkl)
        res[k] = {t: p for t, p in prof.items() if t != "avalon" and (only is None or t in only)}
    return res


def compare(run: Path, only: set[str] | None) -> str:
    ref = json.loads((REAL / "reference.json").read_text())
    train, test = split(ref, [1, 2, 3]), split(ref, [4, 5, 6])
    syn = synthetic(run, only)
    if not syn:
        return f"No scored-round downloads for avalon under {run}."
    pooled: dict[str, list[float]] = {m: [] for m in [*METRICS, "points"]}
    for prof in syn.values():
        for p in prof.values():
            for m in pooled:
                if p.get(m) is not None:
                    pooled[m].append(p[m])
    lines = [f"Synthetic field: {run.name}, rounds {sorted(syn)}, {len(next(iter(syn.values())))} teams compared",
             f"Real reference: top {ref['top']} regional teams; train = R1-R3, test = R4-R6 (held out)", "",
             f"{'metric':18s} {'real train p10/p50/p90':>24s} {'real test p10/p50/p90':>24s} "
             f"{'synthetic p10/p50/p90':>24s} {'in test band':>12s}"]
    for m in METRICS:
        lo, mid, hi = quant(test[m])
        inside = [v for v in pooled[m] if lo <= v <= hi]
        f = lambda q: "/".join(f"{x:5.2f}" for x in q)  # noqa: E731
        share = f"{len(inside) / len(pooled[m]):.0%}" if pooled[m] else "-"
        lines.append(f"{m:18s} {f(quant(train[m])):>24s} {f(quant(test[m])):>24s} {f(quant(pooled[m])):>24s} {share:>12s}")
    lines += ["", "Field drift (median across teams, by round): real top teams vs synthetic"]
    for m in ("three_bet", "fold_to_3bet", "flop_fold_to_bet", "open_rate", "vpip"):
        real = [statistics.median([p[m] for p in ref["rounds"][str(k)].values() if p.get(m) is not None]) for k in range(1, 7)]
        s = [statistics.median([p[m] for p in syn[k].values() if p.get(m) is not None] or [float("nan")]) for k in sorted(syn)]
        lines.append(f"  {m:18s} real R1-R6: {' '.join(f'{x:.2f}' for x in real)} | synthetic: {' '.join(f'{x:.2f}' for x in s)}")
    return "\n".join(lines)


def spearman(a: dict, b: dict) -> float:
    common = [t for t in a if t in b]
    ra = {t: i for i, t in enumerate(sorted(common, key=lambda t: a[t]))}
    rb = {t: i for i, t in enumerate(sorted(common, key=lambda t: b[t]))}
    n = len(common)
    return 1 - 6 * sum((ra[t] - rb[t]) ** 2 for t in common) / (n * (n * n - 1)) if n > 2 else float("nan")


def dynamics(run: Path) -> str:
    """Rank persistence between consecutive scored rounds (exact round scores from round.json), and
    how often a team moves 5+ places. Regional reference: Bay Area r = 0.76-0.83 (competitor report),
    Boston median 0.68 (range 0.47-0.91, estimated from one team's tables, so noisier)."""
    rounds = []
    for f in sorted((run / "rounds").glob("scored*/round.json")) + sorted(run.glob("round[0-9]*/round.json")):
        d = json.loads(f.read_text())
        rounds.append({t: v["points"] for t, v in d["scores"].items()})
    if len(rounds) < 2:
        return "Rank dynamics: need at least two scored rounds."
    rs, jumps, moves = [], 0, 0
    for x, y in zip(rounds, rounds[1:]):
        rs.append(spearman(x, y))
        rx = {t: i for i, t in enumerate(sorted(x, key=lambda t: -x[t]))}
        ry = {t: i for i, t in enumerate(sorted(y, key=lambda t: -y[t]))}
        for t in rx:
            if t in ry:
                moves += 1
                jumps += abs(rx[t] - ry[t]) >= 5
    return (f"Rank dynamics: consecutive-round Spearman {', '.join(f'{r:.2f}' for r in rs)} "
            f"(regionals: Bay Area 0.76-0.83, Boston median 0.68); moves of 5+ places: {jumps}/{moves}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("real")
    r.add_argument("--top", type=int, default=20)
    c = sub.add_parser("compare")
    c.add_argument("run")
    c.add_argument("--teams", default=None, help="comma-separated team names to compare (default: all but avalon)")
    a = p.parse_args()
    if a.cmd == "real":
        ref = build_real(a.top)
        print(f"reference: top {a.top} of {len(ref['teams'])} teams: {', '.join(ref['teams'])}")
        train, test = split(ref, [1, 2, 3]), split(ref, [4, 5, 6])
        for m in METRICS:
            print(f"  {m:18s} train p10/p50/p90 {quant(train[m])}  test {quant(test[m])}")
    elif a.cmd == "compare":
        run = Path(a.run) if Path(a.run).is_absolute() else ROOT / a.run
        only = set(a.teams.split(",")) if a.teams else None
        print(compare(run, only))
        print(dynamics(run))
    else:
        p.print_help()


if __name__ == "__main__":
    main()
