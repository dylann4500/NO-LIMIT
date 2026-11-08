"""Does the field call preflop jams wide, and do our strong hands make more by jamming than raising?
usage: python -I hh4.py HANDS.jsonl.gz TABLES.json"""
import collections, gzip, json, sys
from itertools import permutations
from multiprocessing import Pool

RANKS = "23456789TJQKA"; SUITS = "shdc"; RANK = {r: i for i, r in enumerate(RANKS)}
PERMS = [dict(zip(SUITS, p)) for p in permutations(SUITS)]
G = {}


def canon3(cards):
    best = None
    for m in PERMS:
        s = "".join(sorted((c[0] + m[c[1]] for c in cards), key=lambda c: (RANK[c[0]], c[1]), reverse=True))
        if best is None or s < best:
            best = s
    return best


def init(you, mine, classes):
    G.update(you=you, mine=mine, classes=classes)


def dbucket(d):
    return "<10bb" if d < 10 else "10-20bb" if d < 20 else "20-40bb" if d < 40 else "40bb+"


def sbucket(p):
    return "top5%" if p <= 0.05 else "5-15%" if p <= 0.15 else "15-30%" if p <= 0.30 else "30%+"


def tbl(pair):
    t = json.loads(pair[0]); you = G["you"]
    if "hands" not in t:
        return None
    seats = t["seats"]; me = seats.index(you) if you in seats else None
    mycards = G["mine"].get((t["iteration"], t["table"]), [])
    jams, mine, teamjam = [], [], collections.Counter()
    for hi, h in enumerate(t["hands"]):
        bb = h["blinds"][1] or 1; sb_, sa = h["stacks_before"], h["stacks_after"]
        live = sum(1 for x in sb_ if x > 0)
        jam = None; callers = []; my_first = None; street = 0; opened = False; my_open = None
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board":
                street += 1; continue
            if street or s is None or k not in ("fold", "call", "raise", "check"):
                continue
            teamjam[(seats[s], "act")] += 0
            if k == "raise" and e["amount"] >= sb_[s] and jam is None:
                jam = s
                if s == me and my_first is None:
                    my_first = "jam"
                    if my_open is None: my_open = not opened
            elif k == "raise" and e["amount"] >= sb_[s] and jam is not None:
                callers.append(s)  # re-jam over a jam counts as a call of it
            elif k == "call" and jam is not None:
                callers.append(s)
            if s == me and my_first is None and k in ("raise", "call", "fold", "check"):
                my_first = "raise" if k == "raise" else k
            if s == me and my_open is None:
                my_open = not opened
            if k == "raise":
                opened = True
        if jam is not None:
            jams.append((seats[jam], sb_[jam] / bb, bool(callers), (sa[jam] - sb_[jam]) / bb,
                         [seats[c] for c in callers], live))
        if me is not None and sb_[me] > 0 and hi < len(mycards) and len(mycards[hi]) == 3 and my_first in ("jam", "raise"):
            v = G["classes"].get(canon3(mycards[hi]))
            if v:
                mine.append((my_first, v[0], sb_[me] / bb, (sa[me] - sb_[me]) / bb,
                             jam == me and bool(callers), my_open))
    return jams, mine


def main():
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    classes = json.load(open(sys.argv[2]))["classes"]
    mine = {}
    for l in lines:
        if l.startswith('{"you"'):
            y = json.loads(l)["you"]; mine[(y["iteration"], y["table"])] = y["cards"]
    you = head["you"]; name = {e["entry_id"]: e["team_name"] for e in head["entries"]}
    with Pool(8, initializer=init, initargs=(you, mine, classes)) as p:
        R = [r for r in p.map(tbl, [(l,) for l in lines if not l.startswith('{"you"')], chunksize=64) if r]
    jams = [j for r in R for j in r[0]]; ours = [m for r in R for m in r[1]]
    # team jam frequency, to split "maniac" jammers (>40% of their jams... use jam count share)
    jc = collections.Counter(j[0] for j in jams)
    tot = sum(jc.values())
    maniacs = {s for s, n in jc.items() if n > 0.02 * tot}
    print(f"{len(jams)} preflop jams. 'maniac' jammers (>2% of all jams each): {[name.get(s, s)[:14] for s in maniacs]}")
    m = lambda v: sum(v) / len(v) if v else 0.0
    print("\nP(jam gets called) and jammer result, by jammer depth:")
    for who in ("maniac", "normal", "us"):
        for b in ("<10bb", "10-20bb", "20-40bb", "40bb+"):
            sel = [j for j in jams if dbucket(j[1]) == b and
                   ((who == "us" and j[0] == you) or (who == "maniac" and j[0] in maniacs) or
                    (who == "normal" and j[0] not in maniacs and j[0] != you))]
            if not sel:
                continue
            called = [j for j in sel if j[2]]
            print(f"  {who:6s} {b:8s} n={len(sel):6d}  called {len(called)/len(sel):4.0%}  "
                  f"jammer avg {m([j[3] for j in sel]):+6.1f}bb  when called {m([j[3] for j in called]):+6.1f}bb  "
                  f"(pot won uncalled {m([j[3] for j in sel if not j[2]]):+.1f}bb)")
    # who calls: share of calls of NORMAL jams made by teams that call nearly everything
    callers = collections.Counter(c for j in jams for c in j[4])
    print("\ntop jam-callers:", [(name.get(s, s)[:14], n) for s, n in callers.most_common(8)])
    for UNOPENED in (True, False):
        print(f"\nOUR hands, jam vs raise, {'UNOPENED pot' if UNOPENED else 'FACING a raise'}:")
        for b in ("top5%", "5-15%", "15-30%", "30%+"):
            for d in ("10-20bb", "20-40bb", "40bb+"):
                row = []
                for act in ("jam", "raise"):
                    sel = [o for o in ours if o[0] == act and sbucket(o[1]) == b and dbucket(o[2]) == d and o[5] == UNOPENED]
                    row.append(f"{act}: n={len(sel):5d} avg {m([o[3] for o in sel]):+6.2f}bb"
                               + (f" called {m([o[4] for o in sel]):3.0%}" if act == "jam" else ""))
                print(f"  {b:7s} {d:8s} " + " | ".join(row))


if __name__ == "__main__":
    main()
