"""Practice-round analysis, new format (table lines + per-table 'you' lines). Parallel over tables.
usage: python -I hh2.py HANDS.jsonl.gz"""
import collections, gzip, json, sys
from multiprocessing import Pool

YOU = None


def table_stats(line):
    t = json.loads(line)
    if "hands" not in t:
        return None
    seats, fill = t["seats"], t["fillers"]
    pts = {seats[i]: t["hands"][-1]["equity_after"][i] for i in range(len(seats)) if not fill[i]}
    st = collections.defaultdict(collections.Counter)
    me = seats.index(YOU) if YOU in seats else None
    ours = collections.defaultdict(list)  # category -> list of bb deltas
    bust_hand = {}
    for h in t["hands"]:
        bb = h["blinds"][1] or 1
        sb_, sa = h["stacks_before"], h["stacks_after"]
        live = [i for i in range(len(seats)) if sb_[i] > 0]
        for i in live:
            st[seats[i]]["hands"] += 1
            if sa[i] == 0 and seats[i] not in bust_hand:
                bust_hand[seats[i]] = h["hand"]
        street, bet_on, jam_by = 0, False, None
        vp, pr, jm, folded_at, showdown, my_allin_pre = set(), set(), set(), {}, False, False
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board":
                street += 1; bet_on = False; continue
            if k == "show":
                showdown = True
            if s is None or k not in ("fold", "check", "call", "raise"):
                continue
            c = st[seats[s]]
            if street == 0:
                if jam_by is not None and s != jam_by and k in ("fold", "call"):
                    c["face_jam"] += 1
                    c["call_jam"] += k == "call"
                    if s == me and k == "call":
                        my_allin_pre = True
                if k == "raise":
                    pr.add(s)
                    if e["amount"] >= sb_[s]:
                        jm.add(s)
                        if jam_by is None:
                            jam_by = s
                        if s == me:
                            my_allin_pre = True
                if k in ("raise", "call"):
                    vp.add(s)
            else:
                if bet_on and k in ("fold", "call", "raise"):
                    c["face_bet"] += 1; c[f"{k}_bet"] += 1
                if k == "raise":
                    c["post_raise"] += 1; bet_on = True
                c["post_act"] += 1
            if k == "fold":
                folded_at[s] = street
        for s in vp: st[seats[s]]["vpip"] += 1
        for s in pr: st[seats[s]]["pfr"] += 1
        for s in jm: st[seats[s]]["jam"] += 1
        if me is not None and sb_[me] > 0:
            d = (sa[me] - sb_[me]) / bb
            if me in folded_at:
                cat = f"fold_street{folded_at[me]}"
            elif showdown:
                cat = "showdown"
            else:
                cat = "won_no_showdown"
            ours[cat].append(d)
            if my_allin_pre:
                ours["allin_preflop"].append(d)
            if me in vp:
                ours["vpip_hands"].append(d)
    places = {}
    for s, p in pts.items():
        places[s] = p
    return pts, {k: dict(v) for k, v in st.items()}, dict(ours), bust_hand, len(t["hands"])


def init(you):
    global YOU
    YOU = you


def main():
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    you = head["you"]; name = {e["entry_id"]: e["team_name"] for e in head["entries"]}
    with Pool(8, initializer=init, initargs=(you,)) as p:
        res = [r for r in p.map(table_stats, lines, chunksize=64) if r]
    pts = collections.defaultdict(list); st = collections.defaultdict(collections.Counter)
    ours = collections.defaultdict(list); bust = collections.defaultdict(list); nh = []
    for P, S, O, B, n in res:
        nh.append(n)
        for s, v in P.items(): pts[s].append(v)
        for s, c in S.items(): st[s].update(c)
        for k, v in O.items(): ours[k].extend(v)
        for s in P:
            bust[s].append(B.get(s))
    m = lambda v: sum(v) / len(v) if v else 0.0
    rows = sorted(((m(v), len(v), s) for s, v in pts.items() if len(v) >= 30), reverse=True)
    print(f"{len(res)} tables, avg hands/table {m(nh):.0f}, teams with >=30 tables: {len(rows)}")

    def line(s):
        c = st[s]; h = max(1, c["hands"])
        busts = [b for b in bust[s] if b is not None]
        pv = pts[s]
        pl = collections.Counter(round(x) for x in pv)
        return (f"pts {m(pv):5.2f} n={len(pv):4d} | VPIP {c['vpip']/h:4.0%} PFR {c['pfr']/h:4.0%} "
                f"jam {c['jam']/h:5.1%} callJam {c['call_jam']/max(1,c['face_jam']):4.0%} | "
                f"post: foldToBet {c['fold_bet']/max(1,c['face_bet']):4.0%} raise% {c['post_raise']/max(1,c['post_act']):4.0%} | "
                f"1st {pl[50]/len(pv):4.0%} 2nd {pl[30]/len(pv):4.0%} 3rd {pl[20]/len(pv):4.0%} | "
                f"bust {len(busts)/len(pv):4.0%} at hand {m(busts):4.0f}")
    us = [r for r in rows if r[2] == you]
    if us:
        print(f"\nUS rank {rows.index(us[0]) + 1}/{len(rows)}:  {line(you)}")
    print("\nTOP 12:")
    for p_, n, s in rows[:12]:
        print(f"  {name.get(s, s)[:18]:18s} {line(s)}")
    print("MIDDLE 3 / BOTTOM 5:")
    mid = len(rows) // 2
    for p_, n, s in rows[mid - 1:mid + 2] + rows[-5:]:
        print(f"  {name.get(s, s)[:18]:18s} {line(s)}")

    # Which style traits go with points (Pearson r over teams with >= 30 tables)
    def feat(s):
        c = st[s]; h = max(1, c["hands"])
        return {"VPIP": c["vpip"] / h, "PFR": c["pfr"] / h, "jam": c["jam"] / h,
                "callJam": c["call_jam"] / max(1, c["face_jam"]),
                "foldToBet": c["fold_bet"] / max(1, c["face_bet"]),
                "postRaise": c["post_raise"] / max(1, c["post_act"])}
    import math
    ys = [r[0] for r in rows]; F = [feat(r[2]) for r in rows]
    print("\ncorrelation with points (teams):", end=" ")
    for k in F[0]:
        xs = [f[k] for f in F]; mx, my = m(xs), m(ys)
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        vx = math.sqrt(sum((x - mx) ** 2 for x in xs)); vy = math.sqrt(sum((y - my) ** 2 for y in ys))
        print(f"{k} {cov / (vx * vy + 1e-12):+.2f}", end="  ")
    print()
    # Top-quartile style averages vs ours
    q = rows[: max(1, len(rows) // 4)]
    avg = {k: m([feat(r[2])[k] for r in q]) for k in F[0]}
    print("top-quartile avg:", {k: round(v, 3) for k, v in avg.items()})
    print("ours:            ", {k: round(v, 3) for k, v in feat(you).items()})

    print("\nOUR chips by how the hand ended (bb):")
    for k in sorted(ours):
        v = ours[k]
        print(f"  {k:18s} n={len(v):6d} total {sum(v):9.0f}bb  avg {m(v):6.2f}bb")


if __name__ == "__main__":
    main()
