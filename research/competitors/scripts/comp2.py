"""Per-team: VPIP/open/steal by players left, fold facing one raise, flop first-in bet & c-bet by #opponents and
villain-visible-card connect class, postflop bet-size histogram, chips won with/without showdown.
usage: python -I comp2.py HANDS.jsonl.gz OUT.json"""
import collections, gzip, json, sys
from multiprocessing import Pool

R = "23456789TJQKA"


def rk(c): return R.index(c[0])


def connect(card, board):
    """pair: pairs a flop card; draw: shares suit with >=2 board cards or makes a 3-card straight window with 2 board ranks; miss."""
    if card is None: return "na"
    r = rk(card); br = [rk(b) for b in board]
    if r in br: return "pair"
    if sum(1 for b in board if b[1] == card[1]) >= 2: return "draw"
    rs = set(br)
    for lo in range(-1, 9):  # window lo..lo+4, ace low as -1
        win = set(range(lo, lo + 5))
        rr = r if not (lo == -1 and r == 12) else -1
        bb = {x if not (lo == -1 and x == 12) else -1 for x in rs}
        if rr in win and len(bb & win) >= 2:
            return "draw"
    return "miss"


def nl_key(n): return str(n)


def proc(line):
    t = json.loads(line)
    if "hands" not in t or "seats" not in t: return None
    seats = t["seats"]; N = len(seats); fill = t.get("fillers", [False] * N)
    st = collections.defaultdict(collections.Counter)
    sz = collections.defaultdict(collections.Counter)
    for h in t["hands"]:
        bb = h["blinds"][1] or 1; sb_, sa = h["stacks_before"], h["stacks_after"]
        live = [i for i in range(N) if sb_[i] > 0]; n = len(live); NK = nl_key(n)
        btn = h["button"]
        # position labels from blind events
        sbs = [e["seat"] for e in h["events"] if e["kind"] == "blind"]
        sbseat = sbs[0] if sbs else None; bbseat = sbs[1] if len(sbs) > 1 else None
        order = sorted(live, key=lambda i: (i - btn - 1) % N)  # SB first ... button last
        co = order[-2] if n >= 4 else None
        def pos(i):
            if i == sbseat: return "SB"
            if i == bbseat: return "BB"
            if i == btn: return "BTN"
            if i == co: return "CO"
            return "EP"
        showdown = any(e["kind"] == "show" for e in h["events"])
        for i in live:
            if fill[i]: continue
            T = seats[i]; c = st[T]; c["hands"] += 1; c["hands_" + NK] += 1
            d = sa[i] - sb_[i]
            c["chips_sd" if showdown else "chips_nosd"] += d
            c["bb_sd" if showdown else "bb_nosd"] += d / bb
        street = 0; raises = 0; folded = set(); vp = set(); board = []; vis = {}
        con = collections.Counter(); tot = collections.Counter(); pot = 0; street_pot = 0
        bet_on = False; aggressor = None; flop_first_done = set()
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board":
                board = board + e["cards"]; street += 1; bet_on = False; con = collections.Counter(); street_pot = pot; continue
            if k == "reveal": vis[s] = e["cards"][0]; continue
            if k == "blind": con[s] += e["amount"]; tot[s] += e["amount"]; pot += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            T = seats[s]; c = st[T]; P = pos(s)
            if street == 0:
                if raises == 0 and k != "check":
                    c["unop_" + NK] += 1; c["unop"] += 1; c["unop_" + P] += 1
                    if k == "raise":
                        c["open_" + NK] += 1; c["open"] += 1; c["open_" + P] += 1
                        if e["amount"] >= sb_[s]:
                            c["openjam_" + NK] += 1
                        else:
                            sz[T]["open%.1f" % (e["amount"] / bb)] += 1
                    if P in ("CO", "BTN", "SB") and n >= 3:
                        c["steal_opp_" + NK] += 1; c["steal_opp"] += 1
                        if k == "raise": c["steal_" + NK] += 1; c["steal"] += 1
                elif raises == 1 and k in ("fold", "call", "raise"):
                    c["face1"] += 1; c["face1_" + k] += 1
            else:
                active = [i for i in live if i not in folded]
                if not bet_on and street == 1 and sb_[s] - tot[s] > 0:
                    opps = [i for i in active if i != s]
                    no = "1" if len(opps) == 1 else ("2" if len(opps) == 2 else "3+")
                    cls = [connect(vis.get(o), board[:3]) for o in opps]
                    cc = "pair" if "pair" in cls else ("draw" if "draw" in cls else "miss")
                    c["ff_opp"] += 1; c["ff_opp_" + no] += 1; c["ff_opp_" + cc] += 1; c["ff_opp_%s_%s" % (no, cc)] += 1
                    if k == "raise":
                        c["ff_bet"] += 1; c["ff_bet_" + no] += 1; c["ff_bet_" + cc] += 1; c["ff_bet_%s_%s" % (no, cc)] += 1
                    if s == aggressor:
                        c["cb_opp_" + no] += 1; c["cb_opp_" + cc] += 1; c["cb_opp"] += 1; c["cb_opp_%s_%s" % (no, cc)] += 1
                        if k == "raise":
                            c["cb_" + no] += 1; c["cb_" + cc] += 1; c["cb"] += 1; c["cb_%s_%s" % (no, cc)] += 1
                if not bet_on and k == "raise":
                    frac = (e["amount"] - con[s]) / max(1, street_pot)
                    sz[T]["bet%.2f" % (round(frac * 20) / 20)] += 1
            if k == "call":
                con[s] += e["amount"]; tot[s] += e["amount"]; pot += e["amount"]
            if k == "raise":
                d = e["amount"] - con[s]; con[s] = e["amount"]; tot[s] += d; pot += d
                if street == 0: raises += 1; aggressor = s
                else: bet_on = True
            if street == 0 and k in ("call", "raise"): vp.add(s)
            if k == "fold": folded.add(s)
        for s in vp:
            if not fill[s]: st[seats[s]]["vpip_" + NK] += 1; st[seats[s]]["vpip"] += 1
    return {k: dict(v) for k, v in st.items()}, {k: dict(v) for k, v in sz.items()}, \
        {seats[i]: t["hands"][-1]["equity_after"][i] for i in range(N) if not fill[i]}


def main():
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    with Pool(8) as p:
        res = [r for r in p.map(proc, lines, chunksize=32) if r]
    st = collections.defaultdict(collections.Counter); sz = collections.defaultdict(collections.Counter)
    pts = collections.defaultdict(list)
    for S_, Z, P in res:
        for k, v in S_.items(): st[k].update(v)
        for k, v in Z.items(): sz[k].update(v)
        for k, v in P.items(): pts[k].append(v)
    json.dump({"you": head["you"], "name": {e["entry_id"]: e["team_name"] for e in head["entries"]},
               "st": st, "sz": sz, "pts": pts}, open(sys.argv[2], "w"))
    print(len(res), "tables")


if __name__ == "__main__":
    main()
