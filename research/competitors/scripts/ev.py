"""Decision-forward EV of OUR decisions, using our private kept cards.
forward_bb = (stack_after - stack_before + chips committed before the decision) / bb  (fold => 0).
usage: python -I ev.py HANDS.jsonl.gz OUT.json"""
import collections, gzip, json, sys
from multiprocessing import Pool
import eval7

R = "23456789TJQKA"
YOU = None
STRONG = {"Two Pair", "Trips", "Straight", "Flush", "Full House", "Quads", "Straight Flush"}


def rk(c): return R.index(c[0])


def vis_class(card, board):
    if card is None or not board: return "na"
    r = rk(card); br = [rk(b) for b in board]
    return "pair" if r in br else ("over" if r > max(br) else "low")


def our_class(kept, board):
    k = [rk(c) for c in kept]; B = [rk(c) for c in board]
    ht = eval7.handtype(eval7.evaluate([eval7.Card(c) for c in kept + board]))
    uses = k[0] == k[1] or k[0] in B or k[1] in B
    if ht in STRONG and (ht not in ("Straight", "Flush") or len(board) < 5 or True):
        # require a kept card to matter: compare with board-only when 5 board cards
        if len(board) == 5:
            bt = eval7.evaluate([eval7.Card(c) for c in board])
            if eval7.evaluate([eval7.Card(c) for c in kept + board]) > bt and (ht != "Two Pair" or uses):
                return "strong"
        elif ht != "Two Pair" or uses:
            return "strong"
    if uses:
        top = max(B)
        if k[0] == k[1]:
            return "pair_top" if k[0] > top else "pair_mid"
        return "pair_top" if top in k else "pair_mid"
    suits = [c[1] for c in kept + board]
    if len(board) < 5 and any(suits.count(s) >= 4 and (kept[0][1] == s or kept[1][1] == s) for s in "shdc"):
        return "fdraw"
    return "air"


def connect(card, board):
    if card is None: return "na"
    r = rk(card); br = [rk(b) for b in board]
    if r in br: return "pair"
    if sum(1 for b in board if b[1] == card[1]) >= 2: return "draw"
    rs = set(br)
    for lo in range(-1, 9):
        win = set(range(lo, lo + 5))
        rr = r if not (lo == -1 and r == 12) else -1
        bb_ = {x if not (lo == -1 and x == 12) else -1 for x in rs}
        if rr in win and len(bb_ & win) >= 2:
            return "draw"
    return "miss"


def hc3(c3):
    rs = sorted((rk(c) for c in c3), reverse=True)
    if len(set(rs)) < 3: return "pair+"
    if rs[0] == 12: return "A-high"
    if rs[0] >= 10: return "QK-high"
    return "low"


def proc(args):
    tl, yl = args
    t = json.loads(tl); y = json.loads(yl).get("you")
    if "hands" not in t or not y: return None
    me = y["seat"]
    kept = {p["hand"]: p["cards"] for p in y.get("private_events", []) if p["kind"] == "kept"}
    out = collections.defaultdict(lambda: [0, 0.0, 0.0])  # key -> [n, sum_fwd_bb, sum_pts]
    N = len(t["seats"])
    for hi, h in enumerate(t["hands"]):
        sb_, sa = h["stacks_before"], h["stacks_after"]
        if sb_[me] <= 0: continue
        bb = h["blinds"][1]; delta = sa[me] - sb_[me]
        dpts = h["equity_after"][me] - h["equity_before"][me]
        live = [i for i in range(N) if sb_[i] > 0]; nl = len(live)
        my3 = y["cards"][hi] if hi < len(y["cards"]) else None
        kp = kept.get(h["hand"])
        street = 0; board = []; vis = {}; folded = set(); tot = collections.Counter(); con = collections.Counter()
        bet_on = False; last_bettor = None; raises = 0; jam_on = False; street_pot = 0; pot = 0; lastamt = 0

        def rec(key):
            fwd = (delta + tot[me]) / bb
            o = out[key]; o[0] += 1; o[1] += fwd; o[2] += dpts

        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board":
                board = board + e["cards"]; street += 1; bet_on = False; last_bettor = None
                con = collections.Counter(); street_pot = pot; lastamt = 0; continue
            if k == "reveal": vis[s] = e["cards"][0]; continue
            if k == "blind":
                tot[s] += e["amount"]; con[s] += e["amount"]; pot += e["amount"]; continue
            if s is None or k not in ("fold", "check", "call", "raise"): continue
            if s == me:
                active = [i for i in live if i not in folded]
                if street == 0 and my3:
                    hc = hc3(my3)
                    if jam_on:
                        b = "45" if nl in (4, 5) else ("3" if nl <= 3 else "6-8")
                        eff = min(sb_[me], max(sb_[i] for i in active if i != me)) / bb
                        eb = "<10" if eff < 10 else ("10-20" if eff < 20 else "20+")
                        rec(("pre_facejam", b, hc, eb, "fold" if k == "fold" else "call"))
                    elif raises == 0:
                        b = "45" if nl in (4, 5) else ("3" if nl <= 3 else "6-8")
                        eff = (sb_[me]) / bb
                        eb = "<10" if eff < 10 else ("10-20" if eff < 20 else "20+")
                        if k != "check":
                            act = "fold" if k == "fold" else "limp" if k == "call" else ("jam" if e["amount"] >= sb_[me] else "raise")
                            rec(("pre_unopened", b, hc, eb, act))
                if street == 1 and kp and len(active) >= 2 and not bet_on and sb_[me] - tot[me] > 0:
                    opps = [i for i in active if i != me]
                    no = "1" if len(opps) == 1 else ("2" if len(opps) == 2 else "3+")
                    cl_ = [connect(vis.get(o), board[:3]) for o in opps]
                    cc = "pair" if "pair" in cl_ else ("draw" if "draw" in cl_ else "miss")
                    oc2 = our_class(kp, board)
                    act2 = "bet" if k == "raise" else "check"
                    rec(("ff", no, cc, oc2, act2)); rec(("ff", no, cc, "ALL", act2))
                if street > 0 and kp and len(active) == 2 and sb_[me] - tot[me] > 0:
                    opp = [i for i in active if i != me][0]
                    oc = our_class(kp, board); vc = vis_class(vis.get(opp), board)
                    rel = None
                    if vc == "pair":
                        if oc in ("strong", "fdraw", "air"):
                            rel = oc
                        else:
                            kr = [rk(c) for c in kp]; Bs = [rk(c) for c in board]
                            ours = kr[0] if kr[0] == kr[1] else max(r_ for r_ in kr if r_ in Bs)
                            vr = rk(vis[opp])
                            rel = "pair>vis" if ours > vr else ("pair=vis" if ours == vr else "pair<vis")
                    if not bet_on:
                        act = "bet" if k == "raise" else "check"
                        if rel: rec(("hu_first2", street, rel, act))
                        rec(("hu_first", street, vc, oc, act))
                        rec(("hu_first", street, vc, "ALL", act))
                    elif last_bettor == opp:
                        frac = lastamt / max(1, street_pot)
                        fb = "<0.5" if frac < 0.5 else ("0.5-1" if frac <= 1.0 else ">1")
                        rec(("hu_face", street, vc, oc, k))
                        if rel: rec(("hu_face2", street, rel, k))
                        rec(("hu_face", street, vc, "ALL", k))
                        rec(("hu_face_size", street, fb, oc, k))
            if k == "call":
                tot[s] += e["amount"]; con[s] += e["amount"]; pot += e["amount"]
            if k == "raise":
                d = e["amount"] - con[s]; tot[s] += d; con[s] = e["amount"]; pot += d
                if street == 0:
                    raises += 1
                    if tot[s] >= sb_[s]: jam_on = True
                else:
                    if not bet_on: lastamt = d
                    else: lastamt = d
                    bet_on = True; last_bettor = s
            if k == "fold": folded.add(s)
    return {"|".join(map(str, k)): v for k, v in out.items()}


def init(you):
    global YOU
    YOU = you


def main():
    with gzip.open(sys.argv[1], "rt") as fh:
        head = json.loads(fh.readline()); lines = fh.readlines()
    pairs = []
    i = 0
    while i < len(lines) - 1:
        if '"hands"' in lines[i][:400] or lines[i].startswith('{"variant"'):
            pairs.append((lines[i], lines[i + 1])); i += 2
        else:
            i += 1
    with Pool(8, initializer=init, initargs=(head["you"],)) as p:
        res = p.map(proc, pairs, chunksize=32)
    tot = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for r in res:
        if not r: continue
        for k, v in r.items():
            o = tot[k]; o[0] += v[0]; o[1] += v[1]; o[2] += v[2]
    json.dump(tot, open(sys.argv[2], "w"))
    print(len(pairs), "tables")


if __name__ == "__main__":
    main()
