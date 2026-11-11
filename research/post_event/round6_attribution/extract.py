"""Extract every decision of ours with its forward ICM value vs folding at that moment, plus field-wide
heads-up facing-bet counters (Q2) and bettor showdown strength.

Semantics (verified by check_semantics.py / validate_icm.py): blind = posted, call = increment,
raise = street raise-to total, uncalled excess returned silently; server equity_* = our MH ICM with bust places paid.

Forward value of a decision: d_fwd = U(after hand) - U(fold counterfactual at that moment).
Fold counterfactual: our stack = before - committed; the aggressor (seat whose bet we face; else BB preflop;
else last aggressor / first live opponent) gets our committed chips + folded players' dead money (+ own chips back);
other live opponents keep their pre-hand stacks. In heads-up spots identical to xjam/xbb.

usage: python -I extract.py HANDS.gz OUTPREFIX [nproc] [maxtables]
writes OUTPREFIX_dec.csv.gz (our decisions), OUTPREFIX_field.pkl (counters)"""
import collections, gzip, json, os, pickle, sys
from itertools import permutations
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from icm import icm_one, u_after  # noqa: E402

import eval7  # noqa: E402

RANKS = "23456789TJQKA"; SUITS = "shdc"; RK = {r: i for i, r in enumerate(RANKS)}
PERMS = [dict(zip(SUITS, p)) for p in permutations(SUITS)]
CC = {}
G = {}


def card(c):
    if c not in CC:
        CC[c] = eval7.Card(c)
    return CC[c]


def canon3(cards):
    best = None
    for m in PERMS:
        s = "".join(sorted((c[0] + m[c[1]] for c in cards), key=lambda c: (RK[c[0]], c[1]), reverse=True))
        if best is None or s < best:
            best = s
    return best


def hand_class(keep, board):
    """Our 2 kept cards vs board: air, fd (flush draw, no pair), weak (mid/bottom/under pair), top (top pair),
    over (overpair), strong (two pair using a hole card, trips/set, straight+)."""
    if len(keep) != 2 or len(board) < 3:
        return "na"
    a, b = keep
    br = [c[0] for c in board]
    top = max(RK[r] for r in br)
    cat = eval7.handtype(eval7.evaluate([card(c) for c in list(keep) + list(board)]))
    if cat in ("Straight", "Flush", "Full House", "Quads", "Straight Flush"):
        if len(board) == 5:
            bcat = eval7.handtype(eval7.evaluate([card(c) for c in board]))
            if bcat == cat:
                pass  # board plays; fall through to pair logic
            else:
                return "strong"
        else:
            return "strong"
    ra, rb = a[0], b[0]
    if ra == rb:
        if ra in br:
            return "strong"
        return "over" if RK[ra] > top else "weak"
    pa, pb = ra in br, rb in br
    if pa and pb:
        return "strong"
    if pa or pb:
        r = ra if pa else rb
        if br.count(r) >= 2:
            return "strong"  # trips
        return "top" if RK[r] == top else "weak"
    if len(board) < 5:
        sc = collections.Counter(c[1] for c in list(keep) + list(board))
        if any(sc[c[1]] >= 4 for c in keep):
            return "fd"
    return "air"


def size_bucket(x):
    if x is None:
        return "na"
    for lim, lab in ((0.4, "<.4"), (0.6, ".4-.6"), (0.85, ".6-.85"), (1.2, ".85-1.2")):
        if x < lim:
            return lab
    return ">1.2"


def init(you, cls):
    G.update(you=you, cls=cls)


def cf_util(me, agg, alive, folded, com, sb_, pay):
    st = {}
    dead = 0
    for i in alive:
        if i == me or i in folded:
            st[i] = sb_[i] - com[i]
            dead += com[i]
        elif i != agg:
            st[i] = sb_[i]
    st[agg] = sb_[agg] + dead
    return icm_one(st, me, pay)


def work(pair):
    tl, yl = pair
    t = json.loads(tl)
    y = json.loads(yl)["you"]
    assert y["iteration"] == t["iteration"] and y["table"] == t["table"]
    me = y["seat"]; pay = t["payouts"]; seats = t["seats"]; N = len(seats)
    tid = t["iteration"] * 10000 + t["table"]
    mycards = y["cards"]
    kept = {e["hand"]: e["cards"] for e in y["private_events"] if e["kind"] == "kept"}
    auto = set((a[0], a[1]) for a in (y.get("automatic") or []))
    cls = G["cls"]
    rows = []
    fieldA = collections.Counter()   # (target, street, sizeb, resp) -> n
    fieldR = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0])  # (target, street, sizeb) -> n, sumR/P, sumsq, sumRbb
    sdB = collections.Counter()      # (bettor, street, class_at_bet, caller_is_us) for HU bets called -> showdown
    final_pts = t["hands"][-1]["equity_after"][me]
    for hi, h in enumerate(t["hands"]):
        sb_, sa = h["stacks_before"], h["stacks_after"]
        bb = h["blinds"][1] or 1
        alive = [i for i in range(N) if sb_[i] > 0]
        ev = h["events"]
        # blinds / positions
        blinds = [(e["seat"], e["amount"]) for e in ev if e["kind"] == "blind"]
        bb_seat = sb_seat = None
        if len(blinds) >= 2:
            (s1, a1), (s2, a2) = blinds[0], blinds[1]
            if a1 > a2:
                bb_seat, sb_seat = s1, s2
            else:
                bb_seat, sb_seat = s2, s1
        elif len(blinds) == 1:
            bb_seat = blinds[0][0]
        btn = h["button"]
        order = [(btn + k) % N for k in range(1, N + 1) if sb_[(btn + k) % N] > 0]
        co = order[-2] if len(order) >= 4 else None

        def pos_of(s):
            if s == bb_seat:
                return "BB"
            if s == sb_seat:
                return "SB"
            if s == btn:
                return "BTN"
            if s == co:
                return "CO"
            return "EP/MP"

        inhand = sb_[me] > 0
        U_before = icm_one({i: v for i, v in enumerate(sb_) if v > 0}, me, pay) if inhand else None
        U_aft = u_after(sb_, sa, me, pay) if inhand else None
        mc = mycards[hi] if hi < len(mycards) else []
        pct = None
        if inhand and len(mc) == 3:
            v = cls.get(canon3(mc))
            pct = v[0] if v else None
        kc = kept.get(h["hand"])
        com = [0] * N; st = [0] * N; cur = 0; street = 0; board = []; folded = set(); exposed = {}
        lr_street = None; last_aggr = None; pf_raises = 0; limpers = 0; acted_pf = False; checked_street = False
        shown = {}
        for e in ev:
            if e["kind"] == "show" and e.get("cards"):
                shown[e["seat"]] = e["cards"]
        pending = None   # field HU facing-bet record waiting for the target's response
        hu_bets = []     # (bettor, target, street, board_at_bet, called?) for showdown strength
        dec_i = 0
        nalive = len(alive)
        myrows = []
        for ei, e in enumerate(ev):
            k = e["kind"]; s = e.get("seat")
            if k == "board":
                street += 1; board = board + (e.get("cards") or []); st = [0] * N; cur = 0
                lr_street = None; checked_street = False; pending = None
                continue
            if k == "reveal" and s is not None and e.get("cards"):
                exposed[s] = e["cards"][0]; continue
            if k == "blind":
                com[s] += e["amount"]; st[s] += e["amount"]; cur = max(cur, st[s]); continue
            if k not in ("fold", "check", "call", "raise") or s is None:
                continue
            live = [i for i in alive if i not in folded]
            # ---- field: response of a HU target to a bet
            if pending is not None and s == pending[1]:
                bettor, target, stv, P, b, bcards = pending
                resp = "fold" if k == "fold" else ("call" if k == "call" else "raise")
                if k != "check":
                    sbk = size_bucket(b / P if P > 0 else None)
                    fieldA[(seats[target], stv, sbk, resp)] += 1
                    R = sa[bettor] - (sb_[bettor] - P_bettor_com)
                    rr = fieldR[(seats[target], stv, sbk)]
                    rr[0] += 1; rr[1] += R / P; rr[2] += (R / P) ** 2; rr[3] += R / bb
                    if resp == "call":
                        hu_bets.append((bettor, target, stv, list(bcards)))
                pending = None
            # ---- our decision
            if s == me:
                to_call = cur - st[me]
                remaining = sb_[me] - com[me]
                facing = to_call > 0
                pot = sum(com)
                agg = None
                if facing:
                    agg = lr_street if lr_street is not None else (bb_seat if street == 0 else None)
                if agg is None or agg == me or agg in folded:
                    cand = [i for i in live if i != me]
                    if last_aggr is not None and last_aggr in cand:
                        agg = last_aggr
                    elif street == 0 and bb_seat in cand:
                        agg = bb_seat
                    else:
                        agg = cand[0] if cand else None
                if agg is None:
                    continue
                V = cf_util(me, agg, alive, folded, com, sb_, pay)
                amt = e.get("amount") or 0
                agg_allin = facing and com[agg] >= sb_[agg]
                act = k
                if k == "raise":
                    act = "jam" if amt - st[me] >= remaining else "raise"
                call_allin = k == "call" and amt >= remaining
                nopp = len(live) - 1
                if street == 0:
                    if pf_raises == 0:
                        ctx = "unopened" if limpers == 0 else "limped"
                        if me == bb_seat and not facing:
                            ctx = "bboption"
                    elif not acted_pf:
                        ctx = ("bb_vs1" if me == bb_seat else "vs1") if pf_raises == 1 else "cold_vs2"
                    else:
                        ctx = "reraised"
                    facing_jam = facing and (agg_allin or to_call >= remaining)
                    if facing_jam and k in ("call", "fold"):
                        ctx2 = "vsjam"
                    else:
                        ctx2 = ctx
                    label = f"pf_{ctx2}_{act}"
                    hcl = None
                else:
                    facing_jam = facing and (agg_allin or to_call >= remaining)
                    sn = "FTR"[street - 1]
                    if not facing:
                        a2 = "check" if k == "check" else "bet"
                    else:
                        a2 = {"fold": "fold", "call": "call"}.get(k) or ("xr" if checked_street else "raise")
                    label = f"{sn}_{a2}"
                    hcl = hand_class(kc, board) if kc else "na"
                vexp = -1
                vbeat = -1
                if street > 0 and nopp == 1:
                    v = [i for i in live if i != me][0]
                    if v in exposed:
                        vexp = int(exposed[v][0] in [c[0] for c in board])
                        if len(board) == 5 and kc:
                            vbeat = int(eval7.evaluate([card(exposed[v])] + [card(c) for c in board]) >
                                        eval7.evaluate([card(c) for c in kc + board]))
                myexp = exposed.get(me)
                exp_pairs = -1
                if street > 0 and myexp:
                    exp_pairs = int(myexp[0] in [c[0] for c in board[:3]])
                betfrac = None
                if facing:
                    betfrac = last_inc / last_P if last_P > 0 else None
                elif k == "raise":
                    betfrac = (amt - st[me]) / pot if pot > 0 else None
                myrows.append([tid, h["hand"], dec_i, street, label, act, pos_of(me), nalive, round(sb_[me] / bb, 2),
                               -1 if pct is None else round(pct, 4), hcl or "", nopp, int(facing),
                               round(to_call / bb, 2), round(pot / bb, 2),
                               round(to_call / (pot + to_call), 4) if facing else 0.0,
                               "" if betfrac is None else round(betfrac, 3), vexp, vbeat, exp_pairs,
                               int(facing_jam), int(call_allin or act == "jam"), seats[agg], round(V, 5),
                               int(checked_street), int((h["hand"], ei) in auto), int(len(board) == 5 and kc is not None)])
                dec_i += 1
                if street == 0 and k != "blind":
                    acted_pf = True
            # ---- apply action
            if k == "fold":
                folded.add(s)
            elif k == "check":
                if s == me:
                    checked_street = True
            elif k == "call":
                if street == 0 and pf_raises == 0:
                    limpers += 1
                com[s] += e["amount"]; st[s] += e["amount"]
            elif k == "raise":
                P_before = sum(com)
                inc = e["amount"] - st[s]
                last_inc, last_P = e["amount"] - cur, P_before + (cur - st[s])  # bet size over pot incl. the call part
                P_bettor_com = com[s]
                com[s] += inc; st[s] = e["amount"]; cur = max(cur, e["amount"])
                lr_street = s; last_aggr = s
                if street == 0:
                    pf_raises += 1
                # field HU facing-bet record: first bet of a postflop street, exactly two live players
                live2 = [i for i in alive if i not in folded]
                if street > 0 and len(live2) == 2 and pf_street_bets(st, s) == 0:
                    target = [i for i in live2 if i != s][0]
                    if com[target] < sb_[target]:
                        pending = (s, target, street, P_before, inc, board)
        # showdown strength of HU bettors that got called
        for bettor, target, stv, bcards in hu_bets:
            if bettor in shown and len(shown[bettor]) == 2:
                c = hand_class(shown[bettor], bcards)
                sdB[(seats[bettor], stv, c, int(target == me))] += 1
        # no-decision hands (walks, all-in from blinds) -> pseudo row
        if inhand:
            if not myrows:
                myrows.append([tid, h["hand"], 0, 0, "nodecision", "", pos_of(me), nalive, round(sb_[me] / bb, 2),
                               -1 if pct is None else round(pct, 4), "", 0, 0, 0, 0, 0, "", -1, -1, -1, 0, 0, "",
                               round(U_before, 5), 0, 0, 0])
            for r in myrows:
                r += [round(U_before, 5), round(U_aft, 5), round((sa[me] - sb_[me]) / bb, 3), final_pts]
            rows.extend(myrows)
    return tid, rows, fieldA, {k: v for k, v in fieldR.items()}, sdB


def pf_street_bets(st, s):
    """Number of other seats with chips in on this street before s's raise (0 => s made the first bet)."""
    return sum(1 for i, v in enumerate(st) if i != s and v > 0)


COLS = ["tid", "hand", "dec", "street", "label", "act", "pos", "alive", "stack_bb", "pct", "hcls", "nopp", "facing",
        "tocall_bb", "pot_bb", "odds", "betfrac", "vexp", "vbeat", "exp_pairs", "facing_jam", "allin", "agg", "V",
        "checked", "auto", "river_kc", "U_before", "U_after", "chips_bb", "final_pts"]


def pairs(path, maxt):
    with gzip.open(path, "rt") as f:
        f.readline()
        prev = None; n = 0
        for line in f:
            if line.startswith('{"you"'):
                if prev is not None:
                    yield prev, line
                    n += 1
                    if maxt and n >= maxt:
                        return
                prev = None
            else:
                prev = line


def main():
    path, out = sys.argv[1], sys.argv[2]
    nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    maxt = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    with gzip.open(path, "rt") as f:
        hdr = json.loads(f.readline())
    cls = json.load(open("/Users/dylan/Documents/GitHub/nolimit-live/bots/v3/tables_bayarea.json"))["classes"]
    FA = collections.Counter(); FR = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0]); SD = collections.Counter()
    nt = 0
    with gzip.open(out + "_dec.csv.gz", "wt") as fo, Pool(nproc, initializer=init, initargs=(hdr["you"], cls)) as p:
        fo.write(",".join(COLS) + "\n")
        for tid, rows, fa, fr, sd in p.imap_unordered(work, pairs(path, maxt), chunksize=8):
            nt += 1
            for r in rows:
                fo.write(",".join(str(x) for x in r) + "\n")
            FA.update(fa); SD.update(sd)
            for k2, v in fr.items():
                a = FR[k2]
                for j in range(4):
                    a[j] += v[j]
    names = {e["entry_id"]: e["team_name"] for e in hdr["entries"]}
    with open(out + "_field.pkl", "wb") as fp:
        pickle.dump({"you": hdr["you"], "names": names, "ntables": nt, "FA": dict(FA), "FR": dict(FR), "SD": dict(SD)}, fp)
    print("tables", nt)


if __name__ == "__main__":
    main()
