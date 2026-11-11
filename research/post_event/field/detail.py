"""Mechanism of chip flow between avalon and each opponent, plus how the field treats avalon's opens.

usage: python -I detail.py HANDS.jsonl.gz OUT.pkl
Per opponent team: pairwise chip flow (same proportional split as extract.py) by how the hand ended;
our non-jam opens (RFI) and who 3-bets them, our response, our net bb in those hands.
"""
import collections
import gzip
import json
import pickle
import sys


def main(path, outp):
    F = collections.defaultdict(collections.Counter)     # team -> end-category -> chips (positive = avalon won)
    N = collections.defaultdict(collections.Counter)     # team -> end-category -> hands
    T = collections.Counter()                            # team -> tables
    O = collections.defaultdict(collections.Counter)     # 3-bettor team -> counters about our opens
    G = collections.Counter()                            # global counters about our opens
    with gzip.open(path, "rt") as fh:
        head = json.loads(fh.readline())
        YOU = head["you"]
        names = {e["entry_id"]: e["team_name"] for e in head["entries"]}
        for line in fh:
            t = json.loads(line)
            if "hands" not in t:
                continue
            seats, fill = t["seats"], t["fillers"]
            if YOU not in seats:
                continue
            me = seats.index(YOU)
            if fill[me]:
                continue
            n = len(seats)
            ent = ["FILLER" if fill[i] else names.get(seats[i], seats[i]) for i in range(n)]
            for i in range(n):
                if i != me:
                    T[ent[i]] += 1
            for h in t["hands"]:
                sb, sa = h["stacks_before"], h["stacks_after"]
                if sb[me] <= 0:
                    continue
                bb = h["blinds"][1] or 1
                live = [i for i in range(n) if sb[i] > 0]
                left = list(sb)
                committed = [0] * n
                contrib = [0] * n
                cur = 0
                street = 0
                pf_raises = 0
                opener = None
                opener_allin = False
                three = None
                our_resp = None
                limpers = 0
                showed = False
                folded_pre = set()
                allin_pre = False
                for e in h["events"]:
                    k = e["kind"]
                    s = e.get("seat")
                    a = e.get("amount") or 0
                    if k == "blind":
                        left[s] -= a; committed[s] += a; contrib[s] += a; cur = max(cur, committed[s])
                    elif k == "board":
                        street += 1
                        committed = [0] * n
                        cur = 0
                    elif k == "show":
                        showed = True
                    elif k in ("fold", "check", "call", "raise"):
                        if street == 0:
                            if k == "fold":
                                folded_pre.add(s)
                            if pf_raises == 1 and three is not None and s == me and opener == me and our_resp is None:
                                pass
                            if opener == me and pf_raises == 2 and s == me and our_resp is None:
                                our_resp = k
                            if k == "call" and pf_raises == 0:
                                limpers += 1
                        if k == "call":
                            left[s] -= a; contrib[s] += a; committed[s] += a
                        elif k == "raise":
                            inc = a - committed[s]
                            left[s] -= inc; contrib[s] += inc; committed[s] = a
                            if street == 0:
                                if pf_raises == 0:
                                    opener = s
                                    opener_allin = left[s] <= 0
                                    open_limped = limpers > 0
                                elif pf_raises == 1 and three is None:
                                    three = s
                                pf_raises += 1
                            cur = max(cur, a)
                net = [sa[i] - sb[i] for i in range(n)]
                # our opens
                if opener == me and not opener_allin and not open_limped:
                    G["opens"] += 1
                    G["open_net_bb"] += net[me] / bb
                    if three is not None:
                        x = ent[three]
                        G["got3b"] += 1
                        O[x]["got3b"] += 1
                        O[x]["resp_" + str(our_resp)] += 1
                        O[x]["net_bb"] += net[me] / bb
                        G["resp_" + str(our_resp)] += 1
                        G["net3b_bb"] += net[me] / bb
                # opportunities for each opponent to 3-bet our open: count opponents dealt in after us who were live
                if opener == me and not opener_allin and not open_limped:
                    for x in live:
                        if x != me:
                            O[ent[x]]["our_open_with_them"] += 1
                # pairwise flow by end category
                gain = sum(v for v in net if v > 0)
                if gain <= 0 or contrib[me] == 0:
                    continue
                if street == 0:
                    cat = "pre_nofold" if False else "preflop"
                else:
                    cat = "showdown" if showed else "post_noSD"
                for x in live:
                    if x == me or contrib[x] == 0:
                        continue
                    f = 0.0
                    if net[me] > 0 and net[x] < 0:
                        f = -net[x] * net[me] / gain
                    elif net[me] < 0 and net[x] > 0:
                        f = net[me] * net[x] / gain
                    c2 = cat
                    if cat == "showdown" and x not in folded_pre and h["events"]:
                        pass
                    F[ent[x]][c2] += f
                    F[ent[x]][c2 + "_bb"] += f / bb
                    N[ent[x]][c2] += 1
    with open(outp, "wb") as f:
        pickle.dump({"F": {k: dict(v) for k, v in F.items()}, "N": {k: dict(v) for k, v in N.items()},
                     "T": dict(T), "O": {k: dict(v) for k, v in O.items()}, "G": dict(G)}, f)
    print(path, "done", dict(G))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
