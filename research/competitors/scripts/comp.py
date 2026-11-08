"""Competitor study. usage: python -I comp.py HANDS.jsonl.gz OUTDIR
Per-team: open size, 3-bet, players-left buckets (VPIP/jam/callJam), c-bet/barrels, bet sizing,
fold-to-bet by bettor's visible card class, pairwise chip transfers, points CIs, maniac/seat effects."""
import collections, gzip, json, math, os, sys
from multiprocessing import Pool

RANKS = "23456789TJQKA"
YOU = None


def rk(c):
    return RANKS.index(c[0])


def vis_class(card, board):
    """class of a visible card against the board: pair (pairs a board card), over (above every board card), low."""
    if card is None or not board:
        return "na"
    r = rk(card); br = [rk(b) for b in board]
    if r in br:
        return "pair"
    if r > max(br):
        return "over"
    return "low"


def bucket(n):
    return "8-6" if n >= 6 else ("5-4" if n >= 4 else "3-2")


def table_stats(line):
    t = json.loads(line)
    if "hands" not in t or "seats" not in t:
        return None
    seats, fill = t["seats"], t.get("fillers", [False] * len(t["seats"]))
    N = len(seats)
    team = lambda s: seats[s]
    pts = {seats[i]: t["hands"][-1]["equity_after"][i] for i in range(N) if not fill[i]}
    st = collections.defaultdict(collections.Counter)
    sizes = collections.defaultdict(lambda: collections.defaultdict(list))  # team -> key -> list
    pair = collections.Counter()  # (winner, loser, phase) -> chips/2000
    hu = collections.Counter()  # (team, opp) -> bb in HU-flop hands ; (team,'*')
    hucount = collections.Counter()
    bust_hand = {}
    me = seats.index(YOU) if YOU in seats else None
    for h in t["hands"]:
        bb = h["blinds"][1] or 1
        sb_, sa = h["stacks_before"], h["stacks_after"]
        live = [i for i in range(N) if sb_[i] > 0]
        nl = len(live); B = bucket(nl)
        for i in live:
            st[team(i)]["hands"] += 1
            st[team(i)]["hands_" + B] += 1
            if sa[i] == 0 and team(i) not in bust_hand:
                bust_hand[team(i)] = h["hand"]
        # pairwise chip transfer
        gains = {i: sa[i] - sb_[i] for i in live}
        tg = sum(v for v in gains.values() if v > 0)
        if tg > 0:
            ph = "early" if h["hand"] <= 15 else "late"
            for l, lv in gains.items():
                if lv < 0:
                    for w, wv in gains.items():
                        if wv > 0:
                            pair[(team(w), team(l), ph)] += (-lv) * wv / tg / 2000.0
        street = 0; pot = 0; contrib = collections.Counter(); total = collections.Counter()
        folded = set(); raises = 0; raiser = None; jam_by = None; aggressor = None
        vp, pr, jm = set(), set(), set()
        bet_on = False; last_bettor = None; street_pot = 0
        vis = {}; board = []
        cbet_done = {}  # street -> bool aggressor bet
        acted_street = set()
        flop_players = None
        limped = False
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board":
                board = board + e["cards"]
                street += 1; bet_on = False; last_bettor = None
                contrib = collections.Counter(); street_pot = pot; acted_street = set()
                if street == 1:
                    flop_players = [i for i in live if i not in folded]
                continue
            if k == "reveal":
                vis[s] = e["cards"][0]; continue
            if k == "blind":
                contrib[s] += e["amount"]; total[s] += e["amount"]; pot += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"):
                continue
            T = team(s); c = st[T]
            stack_left = sb_[s] - total[s]
            if k == "call":
                contrib[s] += e["amount"]; total[s] += e["amount"]; pot += e["amount"]
            delta = 0
            if k == "raise":
                delta = e["amount"] - contrib[s]
                contrib[s] = e["amount"]; total[s] += delta; pot += delta
            is_allin = k == "raise" and total[s] >= sb_[s]
            if street == 0:
                eff = stack_left / bb
                if jam_by is not None and s != jam_by and k in ("fold", "call", "raise"):
                    c["face_jam"] += 1; c["face_jam_" + B] += 1
                    if k != "fold":
                        c["call_jam"] += 1; c["call_jam_" + B] += 1
                if raises == 0:
                    c["unopened"] += 1; c["unopened_" + B] += 1
                    if k == "raise":
                        if is_allin:
                            c["open_jam"] += 1; c["open_jam_" + B] += 1
                            sizes[T]["openjam_eff"].append(round(eff, 1))
                        else:
                            c["open_raise"] += 1; c["open_raise_" + B] += 1
                            sizes[T]["open_bb" + ("_limped" if limped else "")].append(e["amount"] / bb)
                            sizes[T]["open_bb_" + B].append(e["amount"] / bb)
                    elif k == "call":
                        c["limp"] += 1; limped = True
                elif raises == 1 and s != raiser:
                    c["face_open"] += 1; c["face_open_" + B] += 1
                    if k == "raise":
                        c["threebet"] += 1; c["threebet_" + B] += 1
                        if is_allin:
                            c["threebet_jam"] += 1
                        else:
                            sizes[T]["3bet_x"].append(e["amount"] / max(1, contrib_open))
                    elif k == "fold":
                        c["fold_open"] += 1
                if k == "raise":
                    if raises == 0:
                        contrib_open = e["amount"]
                    raises += 1; raiser = s; aggressor = s; pr.add(s)
                    if is_allin:
                        jm.add(s)
                        if jam_by is None:
                            jam_by = s
                if k in ("raise", "call"):
                    vp.add(s)
            else:
                # postflop
                active = [i for i in live if i not in folded]
                hu_now = len(active) == 2
                if not bet_on:
                    # first-in opportunity on this street
                    if s == aggressor and street == 1 and stack_left > 0:
                        c["cbet_opp"] += 1; c["cbet_opp_" + ("hu" if hu_now else "mw")] += 1
                        if k == "raise":
                            c["cbet"] += 1; c["cbet_" + ("hu" if hu_now else "mw")] += 1
                        cbet_done[1] = k == "raise"
                    if s == aggressor and street == 2 and cbet_done.get(1) and stack_left > 0:
                        c["barrel2_opp"] += 1; c["barrel2"] += k == "raise"; cbet_done[2] = k == "raise"
                    if s == aggressor and street == 3 and cbet_done.get(2) and stack_left > 0:
                        c["barrel3_opp"] += 1; c["barrel3"] += k == "raise"
                    if stack_left > 0:
                        c["firstin_opp"] += 1
                        if hu_now:
                            o = [i for i in active if i != s][0]
                            vc = vis_class(vis.get(o), board)
                            c["hu_firstin_" + vc] += 1
                            if k == "raise":
                                c["hu_bet_" + vc] += 1
                    if k == "raise":
                        c["bets"] += 1
                        frac = delta / max(1, street_pot)
                        sizes[T]["bet_frac_s%d" % street].append(round(frac, 3))
                        if is_allin:
                            c["bet_allin"] += 1
                        bet_on = True; last_bettor = s
                else:
                    if k in ("fold", "call", "raise") and last_bettor is not None and s != last_bettor:
                        vc = vis_class(vis.get(last_bettor), board)
                        c["face_bet"] += 1; c["face_bet_" + vc] += 1
                        c[k + "_bet"] += 1; c[k + "_bet_" + vc] += 1
                        if last_bettor == me:
                            c["face_ourbet_" + vc] += 1; c[k + "_ourbet_" + vc] += 1
                        if street == 1 and last_bettor == aggressor:
                            c["face_cbet"] += 1; c[k + "_cbet"] += 1
                    if k == "raise":
                        c["post_raise_vs_bet"] += 1; last_bettor = s
                        if is_allin:
                            c["raise_allin"] += 1
                c["post_act"] += 1
            if k == "fold":
                folded.add(s)
        for s in vp: st[team(s)]["vpip"] += 1; st[team(s)]["vpip_" + bucket(nl)] += 1
        for s in pr: st[team(s)]["pfr"] += 1
        for s in jm: st[team(s)]["jam"] += 1; st[team(s)]["jam_" + bucket(nl)] += 1
        if flop_players is not None:
            for s in flop_players:
                st[team(s)]["saw_flop"] += 1
            if len(flop_players) == 2:
                a, b = flop_players
                for x, y in ((a, b), (b, a)):
                    d = (sa[x] - sb_[x]) / bb
                    hu[(team(x), team(y))] += d; hucount[(team(x), team(y))] += 1
                    hu[(team(x), "*")] += d; hucount[(team(x), "*")] += 1
    seatpts = [(seats[i], i, t["hands"][-1]["equity_after"][i]) for i in range(N) if not fill[i]]
    return (pts, {k: dict(v) for k, v in st.items()}, {k: dict(v) for k, v in sizes.items()},
            dict(pair), dict(hu), dict(hucount), bust_hand, seatpts, len(t["hands"]))


def init(you):
    global YOU
    YOU = you


def main():
    path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    with gzip.open(path, "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    you = head["you"]; name = {e["entry_id"]: e["team_name"] for e in head["entries"]}
    with Pool(8, initializer=init, initargs=(you,)) as p:
        res = [r for r in p.map(table_stats, lines, chunksize=32) if r]
    pts = collections.defaultdict(list); st = collections.defaultdict(collections.Counter)
    sizes = collections.defaultdict(lambda: collections.defaultdict(list))
    pair = collections.Counter(); hu = collections.Counter(); hucount = collections.Counter()
    tables = []
    for P, S, Z, PR, HU, HC, BH, SP, n in res:
        for s, v in P.items(): pts[s].append(v)
        for s, c in S.items(): st[s].update(c)
        for s, d in Z.items():
            for k, v in d.items(): sizes[s][k].extend(v)
        pair.update(PR); hu.update(HU); hucount.update(HC)
        tables.append((P, BH, SP))
    json.dump({"you": you, "name": name, "pts": pts, "st": st,
               "sizes": {s: dict(d) for s, d in sizes.items()},
               "pair": [[a, b, ph, v] for (a, b, ph), v in pair.items()],
               "hu": [[a, b, v, hucount[(a, b)]] for (a, b), v in hu.items()],
               "tables": tables}, open(os.path.join(outdir, "agg.json"), "w"))
    print(f"{len(res)} tables -> {outdir}/agg.json")


if __name__ == "__main__":
    main()
