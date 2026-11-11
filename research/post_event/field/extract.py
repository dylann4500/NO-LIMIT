"""Extract per-team style counters and per-table rows from one No Limit 2026 round file.

usage: python -I extract.py HANDS.jsonl.gz OUT.pkl
Streams the file (one process). Event semantics (checked against stacks in this script):
  blind amount = chips posted; call amount = chips added; raise amount = raise-to total for
  the street (committed resets on each board event); win amount = chips awarded.
Outputs a pickle with team counters, bet-size histograms, and per-table rows incl. pairwise
chip flow between avalon and every other seat (proportional winner/loser allocation per hand).
"""
import collections
import gzip
import json
import pickle
import sys

RANKS = {r: i for i, r in enumerate("23456789TJQKA", start=2)}
ACTS = ("fold", "check", "call", "raise")


def rk(c):
    return RANKS.get(c[0], 0) if c else 0


def places_of(hands, n):
    bust = {}
    for hi, h in enumerate(hands):
        sb, sa = h["stacks_before"], h["stacks_after"]
        for s in range(n):
            if sb[s] > 0 and sa[s] == 0 and s not in bust:
                bust[s] = (hi, sb[s])
    final = hands[-1]["stacks_after"]
    keys = []
    for s in range(n):
        if s in bust:
            keys.append((0, bust[s][0], bust[s][1]))
        else:
            keys.append((1, final[s], 0))
    order = sorted(range(n), key=lambda s: keys[s], reverse=True)
    pl = [0] * n
    for p, s in enumerate(order, 1):
        pl[s] = p
    alive_end = sum(1 for s in range(n) if final[s] > 0)
    return pl, alive_end, bust


def main(path, out):
    C = collections.defaultdict(collections.Counter)          # team -> counters
    H = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))  # team -> metric -> hist
    rows = []
    V = collections.Counter()  # validation
    with gzip.open(path, "rt") as fh:
        head = json.loads(fh.readline())
        YOU = head["you"]
        names = {e["entry_id"]: e["team_name"] for e in head["entries"]}
        pending = None
        for line in fh:
            o = json.loads(line)
            if "hands" in o:
                pending = o
                continue
            own = o.get("you")
            if not isinstance(own, dict) or pending is None:
                V["orphan_private"] += 1
                continue
            t = pending
            pending = None
            if (own.get("iteration"), own.get("table")) != (t.get("iteration"), t.get("table")):
                V["pair_mismatch"] += 1
                continue
            process_table(t, own, YOU, C, H, rows, V)
    res = {"you": YOU, "names": names, "C": {k: dict(v) for k, v in C.items()},
           "H": {k: {m: dict(h) for m, h in v.items()} for k, v in H.items()},
           "rows": rows, "V": dict(V), "tournament_id": head.get("tournament_id")}
    with open(out, "wb") as f:
        pickle.dump(res, f, protocol=4)
    print(path, len(rows), "tables", dict(V))


def process_table(t, own, YOU, C, H, rows, V):
    seats, fill = t["seats"], t["fillers"]
    n = len(seats)
    hands = t["hands"]
    if not hands:
        V["empty_table"] += 1
        return
    me = own.get("seat")
    if me is None or seats[me] != YOU:
        V["no_me"] += 1
        return
    ent = [("FILLER" if fill[i] else seats[i]) for i in range(n)]
    kept_priv = {}
    for pe in own.get("private_events") or []:
        if pe.get("kind") == "kept":
            kept_priv[pe.get("hand")] = pe.get("cards")
    flow = [0.0] * n        # chips from seat i to avalon (positive = avalon won)
    flow_bb = [0.0] * n
    flow_v = [0.0] * n      # only hands where both voluntarily entered
    nboth = [0] * n
    nbothv = [0] * n
    for h in hands:
        bb = h["blinds"][1] or 1
        sb, sa = h["stacks_before"], h["stacks_after"]
        live = [i for i in range(n) if sb[i] > 0]
        btn = h["button"]
        left = list(sb)
        committed = [0] * n
        contrib = [0] * n
        won = [0] * n
        cur_bet = 0
        pot = 0
        street = 0
        pf_raises = 0
        opener = None
        opener_allin = False
        pf_aggr = None
        limpers = 0
        jam_live = False   # current preflop bet set by an all-in raise
        folded = set()
        vp, pr, jm, oj = set(), set(), set(), set()
        acted_street = set()
        flop = []
        exposed = {}
        showed = {}
        nflop = 0
        cbet_done = False
        for e in h["events"]:
            k = e["kind"]
            s = e.get("seat")
            amt = e.get("amount") or 0
            if k == "blind" or k == "ante":
                left[s] -= amt
                contrib[s] += amt
                pot += amt
                if k == "blind":
                    committed[s] += amt
                    cur_bet = max(cur_bet, committed[s])
                continue
            if k == "board":
                street += 1
                if street == 1:
                    flop = list(e.get("cards") or [])
                    nflop = len(live) - len([x for x in folded if x in live])
                committed = [0] * n
                cur_bet = 0
                acted_street = set()
                continue
            if k == "reveal":
                cs = e.get("cards") or []
                if cs:
                    exposed[s] = cs[0]
                continue
            if k == "show":
                showed[s] = e.get("cards") or []
                continue
            if k == "win":
                won[s] += amt
                continue
            if k not in ACTS:
                continue
            c = C[ent[s]]
            to_call = cur_bet - committed[s]
            if street == 0:
                if k in ("call", "raise"):
                    vp.add(s)
                if pf_raises == 0 and limpers == 0:
                    c["rfi_opp"] += 1
                    if k == "raise":
                        c["rfi"] += 1
                    elif k == "call" and to_call > 0:
                        c["limp_first"] += 1
                if pf_raises == 1 and not opener_allin and s != opener:
                    c["3b_opp"] += 1
                    if k == "raise":
                        c["3b"] += 1
                    if opener == btn:
                        c["3bbtn_opp"] += 1
                        if k == "raise":
                            c["3bbtn"] += 1
                    if k == "fold":
                        c["f2open"] += 1
                if pf_raises == 2 and s == opener:
                    c["f3b_opp"] += 1
                    if k == "fold":
                        c["f3b"] += 1
                if jam_live and to_call > 0 and k in ("fold", "call"):
                    c["face_jam"] += 1
                    if k == "call":
                        c["call_jam"] += 1
                if k == "call" and pf_raises == 0:
                    limpers += 1
            else:
                c["post_act"] += 1
                c[f"s{street}_act"] += 1
                if to_call > 0:
                    c["face_bet"] += 1
                    c[f"{k}_bet"] += 1
                    c[f"s{street}_face"] += 1
                    c[f"s{street}_{k}"] += 1
                    if committed[s] == 0 and s not in acted_street or (committed[s] == 0):
                        if street == 1:
                            c["ff_face"] += 1
                            if k == "fold":
                                c["ff_fold"] += 1
                if k == "raise":
                    c["post_agg"] += 1
                    c[f"s{street}_agg"] += 1
                if k == "call":
                    c["post_call"] += 1
                # c-bet
                if street == 1 and s == pf_aggr and s not in acted_street and cur_bet == 0 and not cbet_done:
                    hu = nflop == 2
                    c["cb_opp"] += 1
                    c["cb_opp_hu" if hu else "cb_opp_mw"] += 1
                    if k == "raise":
                        c["cb"] += 1
                        c["cb_hu" if hu else "cb_mw"] += 1
                if street == 1 and cur_bet == 0 and k == "raise":
                    cbet_done = True
                # first-in bet size (bet into no bet)
                if k == "raise" and cur_bet == 0 and pot > 0:
                    allin = amt >= left[s] + committed[s]
                    frac = amt / pot
                    if not allin:
                        H[ent[s]][f"bet_s{street}"][min(60, round(frac * 20))] += 1
                    else:
                        c[f"betjam_s{street}"] += 1
                    c[f"bets_s{street}"] += 1
            acted_street.add(s)
            if k == "fold":
                folded.add(s)
            elif k == "call":
                left[s] -= amt
                contrib[s] += amt
                committed[s] += amt
                pot += amt
            elif k == "raise":
                inc = amt - committed[s]
                left[s] -= inc
                contrib[s] += inc
                pot += inc
                committed[s] = amt
                is_allin = left[s] <= 0
                if street == 0:
                    pr.add(s)
                    pf_aggr = s
                    if is_allin:
                        jm.add(s)
                        if pf_raises == 0:
                            oj.add(s)
                    if pf_raises == 0:
                        opener = s
                        opener_allin = is_allin
                        if not is_allin:
                            H[ent[s]]["open_bb"][round(amt / bb * 10)] += 1
                    pf_raises += 1
                    jam_live = is_allin if amt > cur_bet else jam_live
                cur_bet = max(cur_bet, amt)
        # validation: replayed stacks + wins == stacks_after
        bad = any(left[i] + won[i] != sa[i] for i in live)
        V["hands"] += 1
        if bad:
            V["stack_mismatch"] += 1
        # per-seat hand counters
        for s in live:
            c = C[ent[s]]
            c["hands"] += 1
            if s in vp:
                c["vpip"] += 1
            if s in pr:
                c["pfr"] += 1
            if s in jm:
                c["jam"] += 1
            if s in oj:
                c["openjam"] += 1
            if street >= 1 and s not in folded and s in live:
                # saw flop if not folded preflop: approximate via folded before flop
                pass
        # saw flop / showdown: recompute preflop folds
        pre_folded = set()
        st = 0
        for e in h["events"]:
            if e["kind"] == "board":
                break
            if e["kind"] == "fold":
                pre_folded.add(e["seat"])
        if flop:
            for s in live:
                if s not in pre_folded:
                    c = C[ent[s]]
                    c["saw_flop"] += 1
                    if s in showed and len(showed[s]) >= 2:
                        c["wtsd"] += 1
                        if won[s] > 0:
                            c["wsd"] += 1
        # exposure (showdown-known kept cards)
        fr = {rk(x) for x in flop}
        for s, ex in exposed.items():
            kept = showed.get(s)
            tag = "sd"
            if s == me and kept_priv.get(h["hand"]):
                kept_all = kept_priv[h["hand"]]
                expo_stats(C[ent[s]], "all", ex, kept_all, fr)
            if kept and len(kept) == 2:
                expo_stats(C[ent[s]], tag, ex, kept, fr)
        # pairwise chip flow with avalon
        if sb[me] > 0:
            net = [sa[i] - sb[i] for i in range(n)]
            gain = sum(x for x in net if x > 0)
            if gain > 0:
                for x in live:
                    if x == me or contrib[x] == 0 or contrib[me] == 0:
                        continue
                    f = 0.0
                    if net[me] > 0 and net[x] < 0:
                        f = -net[x] * net[me] / gain
                    elif net[me] < 0 and net[x] > 0:
                        f = net[me] * net[x] / gain
                    nboth[x] += 1
                    flow[x] += f
                    flow_bb[x] += f / bb
                    if x in vp and me in vp:
                        nbothv[x] += 1
                        flow_v[x] += f
    pts = hands[-1]["equity_after"]
    pl, alive_end, bust = places_of(hands, n)
    seat_rows = []
    for i in range(n):
        seat_rows.append((ent[i], float(pts[i] or 0.0), pl[i], round(flow[i], 1), round(flow_bb[i], 2),
                          round(flow_v[i], 1), nboth[i], nbothv[i], bust.get(i, (None,))[0]))
    rows.append((t["iteration"], t["table"], len(hands), alive_end, me, seat_rows))


def expo_stats(c, tag, ex, kept, fr):
    other = [x for x in kept if x != ex]
    if len(other) != 1:
        return
    o = other[0]
    c[f"ex_{tag}_n"] += 1
    if rk(ex) != rk(o):
        c[f"ex_{tag}_np"] += 1
        if rk(ex) < rk(o):
            c[f"ex_{tag}_low"] += 1
    pe, po = rk(ex) in fr, rk(o) in fr
    if pe != po:
        c[f"ex_{tag}_onepair"] += 1
        if pe:
            c[f"ex_{tag}_pairing"] += 1
    if ex[1:] == o[1:]:
        c[f"ex_{tag}_suited"] += 1


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
