"""Realized EV of first-in opens (any team, cards unknown): forward bb = (stack_after - stack_before + committed before) / bb.
Split by position (late = CO/BTN/SB when >=3 left; SB when 2 left) and players-left bucket; also immediate-win rate.
usage: python -I steal.py HANDS.jsonl.gz OUT.json"""
import collections, gzip, json, sys
from multiprocessing import Pool


def bk(n): return "8-6" if n >= 6 else ("5-4" if n >= 4 else ("3" if n == 3 else "2"))


def proc(line):
    t = json.loads(line)
    if "hands" not in t or "seats" not in t: return None
    seats = t["seats"]; N = len(seats); fill = t.get("fillers", [False] * N)
    out = collections.defaultdict(lambda: [0, 0.0, 0])  # (team, bucket, pos, act) -> n, fwd_bb, won_immediately
    for h in t["hands"]:
        bb = h["blinds"][1] or 1; sb_, sa = h["stacks_before"], h["stacks_after"]
        live = [i for i in range(N) if sb_[i] > 0]; n = len(live); B = bk(n); btn = h["button"]
        bl = [e["seat"] for e in h["events"] if e["kind"] == "blind"]
        sbs = bl[0] if bl else None; bbs = bl[1] if len(bl) > 1 else None
        order = sorted(live, key=lambda i: (i - btn - 1) % N); co = order[-2] if n >= 4 else None
        tot = collections.Counter(); raises = 0; first = None
        for idx, e in enumerate(h["events"]):
            k, s = e["kind"], e.get("seat")
            if k == "board": break
            if k == "blind": tot[s] += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if raises == 0 and k != "check" and not fill[s]:
                late = (s in (co, btn, sbs)) if n >= 3 else (s == sbs)
                pos = "late" if late else ("BB" if s == bbs else "early")
                act = "fold" if k == "fold" else ("limp" if k == "call" else ("jam" if e["amount"] >= sb_[s] else "raise"))
                if act in ("raise", "jam"):
                    rest = [x for x in h["events"][idx + 1:] if x.get("kind") in ("fold", "call", "raise", "board")]
                    won = 1 if all(x["kind"] == "fold" for x in rest) and rest else 0
                    o = out[(seats[s], B, pos, act)]; o[0] += 1; o[1] += (sa[s] - sb_[s] + tot[s]) / bb; o[2] += won
                o = out[(seats[s], B, pos, "opp")]; o[0] += 1
            if k == "call": tot[s] += e["amount"]
            if k == "raise":
                tot[s] = e["amount"]  # preflop raise-to = total street contribution
                raises += 1
    return {"|".join(k): v for k, v in out.items()}


def main():
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    with Pool(8) as p:
        res = [r for r in p.map(proc, lines, chunksize=32) if r]
    tot = collections.defaultdict(lambda: [0, 0.0, 0])
    for r in res:
        for k, v in r.items():
            o = tot[k]; o[0] += v[0]; o[1] += v[1]; o[2] += v[2]
    json.dump({"you": head["you"], "name": {e["entry_id"]: e["team_name"] for e in head["entries"]}, "t": tot}, open(sys.argv[2], "w"))
    print(len(res), "tables")


if __name__ == "__main__":
    main()
