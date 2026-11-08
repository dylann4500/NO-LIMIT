"""How/when we bust: players left at bust, bust cause, place distribution. usage: python -I hh3.py HANDS.gz"""
import collections, gzip, json, sys
from multiprocessing import Pool
YOU = None
def init(y):
    global YOU; YOU = y
def tbl(line):
    t = json.loads(line)
    if "hands" not in t or YOU not in t["seats"]: return None
    me = t["seats"].index(YOU); out = {}
    for h in t["hands"]:
        sb_, sa = h["stacks_before"], h["stacks_after"]
        if sb_[me] > 0 and sa[me] == 0:
            left = sum(1 for x in sb_ if x > 0); bb = h["blinds"][1]
            street = 0; cause = "postflop"; jam_by = None; jam_bb = 0
            for e in h["events"]:
                k, s = e["kind"], e.get("seat")
                if k == "board": street += 1; continue
                if street == 0 and k == "raise" and s is not None and e["amount"] >= sb_[s]:
                    if s == me: cause = "we_jam_pre"; break
                    if jam_by is None: jam_by = s; jam_bb = sb_[s] / bb
                if street == 0 and k == "call" and s == me and jam_by is not None:
                    cause = "we_call_jam_pre"; break
                if street == 0 and k == "call" and s == me:
                    cause = "we_call_pre"; break
            out = {"left": left, "cause": cause, "my_bb": sb_[me] / bb, "hand": h["hand"],
                   "max_other_bb": max(x for i, x in enumerate(sb_) if i != me) / bb}
            break
    pts = round(t["hands"][-1]["equity_after"][me])
    return out, pts
def main():
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    with Pool(8, initializer=init, initargs=(head["you"],)) as p:
        R = [r for r in p.map(tbl, lines, chunksize=64) if r]
    place = collections.Counter(); left = collections.Counter(); cause = collections.Counter()
    by = collections.defaultdict(collections.Counter); depth = collections.defaultdict(list)
    for b, pts in R:
        if pts in (50, 30, 20): place[{50: 1, 30: 2, 20: 3}[pts]] += 1
        if b:
            left[b["left"]] += 1; cause[b["cause"]] += 1; by[b["left"]][b["cause"]] += 1
            depth[b["cause"]].append(b["my_bb"])
    n = len(R)
    print(f"{n} tables. places 1/2/3: {place[1]/n:.1%} {place[2]/n:.1%} {place[3]/n:.1%}")
    print("players left when we bust (=our place):", {k: f"{v/n:.1%}" for k, v in sorted(left.items())})
    print("bust cause:", {k: f"{v/n:.1%}" for k, v in cause.most_common()})
    for k in sorted(by): print(f"  {k} left:", dict(by[k].most_common()))
    for k, v in depth.items(): print(f"  avg our stack at bust, {k}: {sum(v)/len(v):.0f}bb")
if __name__ == "__main__":
    main()
