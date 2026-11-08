#!/usr/bin/env python3
"""Fast hand-history analyzer: our results/leaks + per-opponent tendencies.

Usage: python tests/analyze_hh.py FILE [--top N]
FILE: participant download (.jsonl.gz, concatenated gzip members OK) or .jsonl.
Stdlib only; uses eval7 for showdown categories when importable.
"""

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict

try:
    import eval7  # type: ignore

    def hand_category(cards):
        try:
            return eval7.handtype(eval7.evaluate([eval7.Card(c) for c in cards]))
        except Exception:
            return _simple_category(cards)
except Exception:  # pragma: no cover
    eval7 = None

    def hand_category(cards):
        return _simple_category(cards)


RANKS = {r: i for i, r in enumerate("23456789TJQKA", start=2)}
CAT_ORDER = ["High Card", "Pair", "Two Pair", "Trips", "Straight", "Flush",
             "Full House", "Quads", "Straight Flush"]


def _simple_category(cards):
    rs = [RANKS.get(c[0], 0) for c in cards if c]
    ss = [c[1] for c in cards if len(c) > 1]
    cnt = Counter(rs)
    mult = sorted(cnt.values(), reverse=True)
    suit_cnt = Counter(ss)
    flush_suit = next((s for s, n in suit_cnt.items() if n >= 5), None)

    def has_straight(ranks):
        u = set(ranks)
        if 14 in u:
            u.add(1)
        run = 0
        for r in range(1, 15):
            run = run + 1 if r in u else 0
            if run >= 5:
                return True
        return False

    if flush_suit and has_straight([RANKS.get(c[0], 0) for c in cards if c[1:] == flush_suit]):
        return "Straight Flush"
    if mult and mult[0] >= 4:
        return "Quads"
    if len(mult) > 1 and mult[0] >= 3 and mult[1] >= 2:
        return "Full House"
    if flush_suit:
        return "Flush"
    if has_straight(rs):
        return "Straight"
    if mult and mult[0] == 3:
        return "Trips"
    if len(mult) > 1 and mult[0] == 2 and mult[1] == 2:
        return "Two Pair"
    if mult and mult[0] == 2:
        return "Pair"
    return "High Card"


def cat_bucket(cat):
    """0 = two pair or better, 1 = one pair, 2 = worse."""
    c = (cat or "").lower()
    if c in ("pair", "one pair"):
        return 1
    if c in ("high card", ""):
        return 2
    return 0


def rank(card):
    return RANKS.get(card[0], 0) if card else 0


# ---------------------------------------------------------------- reading

def open_any(path):
    with open(path, "rb") as fh:
        magic = fh.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "rt", encoding="utf-8")


def read_history(path):
    """Yield (header, table, own) leniently; pairs public/private lines by (iteration, table)."""
    header = None
    pending = {}
    with open_any(path) as src:
        for line in src:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                print(f"warning: skipping unparsable line", file=sys.stderr)
                continue
            if not isinstance(obj, dict):
                continue
            if header is None and "entries" in obj:
                header = obj
                continue
            if "hands" in obj:
                pending[(obj.get("iteration"), obj.get("table"))] = obj
                continue
            own = obj.get("you")
            if isinstance(own, dict):
                key = (own.get("iteration"), own.get("table"))
                table = pending.pop(key, None)
                if table is None:
                    print(f"warning: private line without table {key}", file=sys.stderr)
                    continue
                yield header or {}, table, own
    for key in pending:
        print(f"warning: table {key} has no private line; skipped", file=sys.stderr)


# ---------------------------------------------------------------- stats containers

def new_opp():
    return defaultdict(int)


PF, FLOP, TURN, RIVER = 0, 1, 2, 3
STREET_NAMES = ["preflop", "flop", "turn", "river"]
STREET_ABBR = ["P", "F", "T", "R"]
ACT_ABBR = {"fold": "f", "check": "x", "call": "c", "raise": "r"}


def bb_bucket(bb):
    if bb <= 10:
        return "<=10bb"
    if bb <= 20:
        return "10-20bb"
    if bb <= 40:
        return "20-40bb"
    return "40+bb"


def finish_places(table):
    """Return list place (1-based) per seat using bust order and final stacks."""
    hands = table.get("hands") or []
    n = len(table.get("seats") or [])
    if not hands:
        return [None] * n
    bust = {}  # seat -> (hand index, stack before)
    for hi, h in enumerate(hands):
        sb, sa = h.get("stacks_before") or [], h.get("stacks_after") or []
        for s in range(min(n, len(sb), len(sa))):
            if sb[s] > 0 and sa[s] == 0 and s not in bust:
                bust[s] = (hi, sb[s])
    final = hands[-1].get("stacks_after") or [0] * n
    keys = []
    for s in range(n):
        if s in bust:
            keys.append((0, bust[s][0], bust[s][1], s))
        else:
            keys.append((1, final[s] if s < len(final) else 0, 0, s))
    order = sorted(range(n), key=lambda s: keys[s][:3], reverse=True)
    places = [None] * n
    for p, s in enumerate(order, start=1):
        places[s] = p
    return places


# ---------------------------------------------------------------- main analysis

def analyze(path, top_n):
    header_seen = None
    names = {}
    me = None
    opp = defaultdict(new_opp)           # entry -> counters
    opp_cats = defaultdict(Counter)      # entry -> showdown buckets after big T/R bet
    opp_sd_all = defaultdict(Counter)    # entry -> showdown buckets overall
    exp_ranks = defaultdict(list)        # entry -> exposed ranks
    tables = 0
    filler_tables = 0
    hands_played = 0
    points = []
    payouts_avg = []
    places = Counter()
    auto_kinds = Counter()
    auto_total = 0
    by_end = defaultdict(lambda: [0, 0, 0.0])      # key -> [hands, chips, bb]
    by_final = defaultdict(lambda: [0, 0, 0.0])
    by_depth = defaultdict(lambda: [0, 0, 0.0])
    sd_n = sd_won = sd_chips = 0
    total_chips = 0
    total_bb = 0.0
    leaks = []  # (chips, desc)

    for header, table, own in read_history(path):
        if header_seen is None:
            header_seen = header
            names = {e.get("entry_id"): e.get("team_name", e.get("entry_id"))
                     for e in header.get("entries") or [] if isinstance(e, dict)}
            me = header.get("you")
        seats = table.get("seats") or []
        fillers = table.get("fillers") or [False] * len(seats)
        my_seat = own.get("seat")
        if my_seat is None:
            continue
        tables += 1
        is_filler = bool(fillers[my_seat]) if my_seat < len(fillers) else False
        hands = table.get("hands") or []
        own_cards = own.get("cards") or []
        autos = own.get("automatic") or []
        auto_total += len(autos)
        hand_by_no = {h.get("hand"): h for h in hands}
        for ref in autos:
            try:
                ev = hand_by_no[ref[0]]["events"][ref[1]]
                auto_kinds[ev.get("kind", "?")] += 1
            except Exception:
                auto_kinds["?"] += 1
        priv = defaultdict(dict)
        for pe in own.get("private_events") or []:
            priv[pe.get("hand")][pe.get("kind")] = pe.get("cards")

        # points and finish
        if hands:
            if is_filler:
                filler_tables += 1
            else:
                eq = hands[-1].get("equity_after")
                pls = finish_places(table)
                place = pls[my_seat] if my_seat < len(pls) else None
                pay = table.get("payouts") or []
                if eq and my_seat < len(eq) and eq[my_seat] is not None:
                    points.append(float(eq[my_seat]))
                elif place and place <= len(pay):
                    points.append(float(pay[place - 1]))
                else:
                    points.append(0.0)
                if seats:
                    payouts_avg.append(sum(pay) / len(seats))
                if place:
                    places[place] += 1

        tname = f"{table.get('iteration')}/{table.get('table')}"
        for hi, hand in enumerate(hands):
            sb = hand.get("stacks_before") or []
            sa = hand.get("stacks_after") or []
            n = len(seats)
            if len(sb) < n:
                sb = list(sb) + [0] * (n - len(sb))
            if len(sa) < n:
                sa = list(sa) + [0] * (n - len(sa))
            blinds = hand.get("blinds") or [0, 1, 0]
            bb = blinds[1] if len(blinds) > 1 and blinds[1] else 1
            events = hand.get("events") or []

            # replay
            left = list(sb)
            committed = [0] * n
            cur_bet = 0
            pot = 0
            street = PF
            pf_raises = 0
            board = []
            flop = []
            vpip = set()
            pfr = set()
            big_tr = set()
            exposed = {}
            showed = {}
            winners = set()
            actions = defaultdict(list)  # seat -> list of strings per street
            last_act = {}
            for ev in events:
                k = ev.get("kind")
                s = ev.get("seat")
                amt = ev.get("amount") or 0
                valid = isinstance(s, int) and 0 <= s < n
                if k == "ante" and valid:
                    pot += amt
                    left[s] -= amt
                elif k == "blind" and valid:
                    pot += amt
                    left[s] -= amt
                    committed[s] += amt
                    cur_bet = max(cur_bet, committed[s])
                elif k == "board":
                    cs = ev.get("cards") or []
                    board.extend(cs)
                    if street == PF:
                        flop = list(cs)
                    street = min(street + 1, RIVER)
                    committed = [0] * n
                    cur_bet = 0
                elif k == "reveal" and valid:
                    cs = ev.get("cards") or []
                    if cs:
                        exposed[s] = cs[0]
                elif k == "show" and valid:
                    showed[s] = ev.get("cards") or []
                elif k == "win" and valid:
                    winners.add(s)
                elif k in ("fold", "check", "call", "raise") and valid:
                    ent = seats[s]
                    o = opp[ent]
                    to_call = cur_bet - committed[s]
                    facing = to_call > 0
                    last_act[s] = (k, street)
                    if k == "call":
                        o["calls"] += 1
                    o["decisions"] += 1
                    if street == PF:
                        if pf_raises >= 1:
                            o["pf_face_raise"] += 1
                            if k == "fold":
                                o["pf_fold_raise"] += 1
                        if pf_raises == 1:
                            o["3b_opp"] += 1
                            if k == "raise":
                                o["3b"] += 1
                        if k in ("call", "raise"):
                            vpip.add(s)
                        if k == "raise":
                            pfr.add(s)
                    else:
                        o["post_acts"] += 1
                        if facing:
                            o["post_face"] += 1
                            if k == "fold":
                                o["post_fold"] += 1
                        if k == "raise":
                            o["post_agg"] += 1
                        if street >= TURN:
                            o["tr_acts"] += 1
                    if k == "call":
                        pot += amt
                        left[s] -= amt
                        committed[s] += amt
                        actions[s].append((street, f"c{amt}"))
                    elif k == "raise":
                        inc = amt - committed[s]
                        over = amt - cur_bet
                        pot_ref = pot + max(to_call, 0)
                        pot += inc
                        left[s] -= inc
                        committed[s] = amt
                        cur_bet = max(cur_bet, amt)
                        allin = left[s] <= 0
                        if street == PF:
                            if allin:
                                o["pf_allin"] += 1
                                if pf_raises == 0:
                                    o["pf_openshove"] += 1
                            pf_raises += 1
                        else:
                            if allin:
                                o["post_allin"] += 1
                            if street >= TURN and pot_ref > 0 and over >= 0.66 * pot_ref:
                                o["tr_big"] += 1
                                big_tr.add(s)
                        actions[s].append((street, ("R" if allin else "r") + str(amt)))
                    else:
                        actions[s].append((street, ACT_ABBR[k]))
                # unknown kinds (select, stack, prize_*, muck...) are ignored

            # per-seat hand-level counters
            for s in range(n):
                if sb[s] <= 0:
                    continue
                o = opp[seats[s]]
                o["hands"] += 1
                if s in vpip:
                    o["vpip"] += 1
                if s in pfr:
                    o["pfr"] += 1
                if s in exposed:
                    r = rank(exposed[s])
                    exp_ranks[seats[s]].append(r)
                    if flop and any(rank(c) == r for c in flop):
                        o["exp_pairs_flop"] += 1
                    o["exposures"] += 1
                sc = showed.get(s)
                if sc and len(sc) >= 2:
                    o["sd"] += 1
                    cat = hand_category(list(sc) + board)
                    b = cat_bucket(cat)
                    opp_sd_all[seats[s]][b] += 1
                    if s in big_tr:
                        opp_cats[seats[s]][b] += 1
                    if s in exposed:
                        ex = exposed[s]
                        other = [c for c in sc if c != ex]
                        if len(other) == 1:
                            o["exp_cmp"] += 1
                            if rank(ex) > rank(other[0]):
                                o["exp_hi"] += 1
                            elif rank(ex) == rank(other[0]):
                                o["exp_eq"] += 1

            # our results
            if my_seat >= n or sb[my_seat] <= 0:
                continue
            hands_played += 1
            net = sa[my_seat] - sb[my_seat]
            netbb = net / bb
            total_chips += net
            total_bb += netbb
            if showed:
                end = "showdown"
            else:
                end = STREET_NAMES[street]
            for d, key in ((by_end, end),
                           (by_depth, bb_bucket(sb[my_seat] / bb))):
                d[key][0] += 1
                d[key][1] += net
                d[key][2] += netbb
            la = last_act.get(my_seat)
            fkey = f"{la[0]}@{STREET_ABBR[la[1]]}" if la else "no action"
            by_final[fkey][0] += 1
            by_final[fkey][1] += net
            by_final[fkey][2] += netbb
            if my_seat in showed:
                sd_n += 1
                sd_chips += net
                if my_seat in winners:
                    sd_won += 1
            if net < 0:
                mine = own_cards[hi] if hi < len(own_cards) else []
                pv = priv.get(hand.get("hand"), {})
                kept = pv.get("kept")
                parts = []
                for st in range(4):
                    acts = [a for (x, a) in actions[my_seat] if x == st]
                    if acts:
                        parts.append(STREET_ABBR[st] + ":" + ",".join(acts))
                # main villain = biggest winner this hand
                vil = max((x for x in range(n) if x != my_seat),
                          key=lambda x: sa[x] - sb[x], default=None)
                vdesc = ""
                if vil is not None:
                    vc = showed.get(vil) or ([exposed[vil]] if vil in exposed else [])
                    vname = names.get(seats[vil], seats[vil])
                    vdesc = f"vs {vname[:16]}[{''.join(vc)}]"
                    if vil in big_tr:
                        vdesc += " bigTR"
                desc = (f"t{tname:<5} h{hand.get('hand'):<3} {net:>7} ({netbb:>6.1f}bb) "
                        f"me {''.join(mine)}{'>' + ''.join(kept) if kept else ''}"
                        f"{'*' + exposed[my_seat] if my_seat in exposed else ''} "
                        f"bd {''.join(board) or '-'} | {' '.join(parts) or '-'} | {vdesc}")
                leaks.append((net, netbb, desc))

    # ------------------------------------------------------------ report
    if header_seen is None:
        print("No tables found.")
        return
    myname = names.get(me, me)
    pct = lambda a, b: f"{100.0 * a / b:5.1f}" if b else "    -"

    print(f"=== OVERVIEW  file={path}")
    print(f"tournament={header_seen.get('tournament_id')}  me={myname}  entries={len(names)}")
    print(f"tables={tables} (filler-seat tables={filler_tables})  hands we were dealt={hands_played}")
    if points:
        base = sum(payouts_avg) / len(payouts_avg) if payouts_avg else 0
        print(f"avg points/table={sum(points)/len(points):.2f} over {len(points)} scored tables "
              f"(even-share baseline {base:.2f})  total={sum(points):.1f}")
        print("finish places: " + "  ".join(f"{p}:{places[p]}" for p in sorted(places)))
    print(f"automatic (failed) actions={auto_total}  "
          + (" ".join(f"{k}:{v}" for k, v in auto_kinds.most_common()) if auto_kinds else ""))
    print(f"net chips={total_chips}  net bb={total_bb:.1f}  "
          f"bb/100={100 * total_bb / hands_played:.1f}" if hands_played else "")

    def table3(title, d, order=None):
        print(f"\n--- {title}")
        print(f"{'bucket':<14}{'hands':>7}{'chips':>10}{'bb':>9}{'bb/hand':>9}")
        keys = order if order else sorted(d, key=lambda k: d[k][1])
        for k in keys:
            if k in d:
                h, c, b = d[k]
                print(f"{k:<14}{h:>7}{c:>10}{b:>9.1f}{b / h if h else 0:>9.2f}")

    print("\n=== OUR CHIPS")
    table3("by street hand ended", by_end, ["preflop", "flop", "turn", "river", "showdown"])
    table3("by our final action", by_final)
    table3("by stack depth at hand start", by_depth, ["<=10bb", "10-20bb", "20-40bb", "40+bb"])
    print(f"\nshowdowns={sd_n}  won (got a win award)={sd_won} ({pct(sd_won, sd_n).strip()}%)  "
          f"net chips at showdown={sd_chips}")

    print("\n=== PLAYERS (by entry, all tables; * = us)")
    ents = sorted(opp, key=lambda e: (e != me, -opp[e]["hands"]))
    print(f"{'team':<20}{'hands':>6}{'VPIP':>6}{'PFR':>6}{'3B':>6}{'F2PFR':>6}{'PFAI':>6}"
          f"{'oShv':>5}{'F2B':>6}{'Agg':>6}{'pAI':>5}{'TRbig':>6}{'Call%':>6}")
    for e in ents:
        o = opp[e]
        nm = ("*" if e == me else " ") + str(names.get(e, e))[:18]
        print(f"{nm:<20}{o['hands']:>6}{pct(o['vpip'], o['hands']):>6}{pct(o['pfr'], o['hands']):>6}"
              f"{pct(o['3b'], o['3b_opp']):>6}{pct(o['pf_fold_raise'], o['pf_face_raise']):>6}"
              f"{pct(o['pf_allin'], o['hands']):>6}{o['pf_openshove']:>5}"
              f"{pct(o['post_fold'], o['post_face']):>6}{pct(o['post_agg'], o['post_acts']):>6}"
              f"{o['post_allin']:>5}{pct(o['tr_big'], o['tr_acts']):>6}"
              f"{pct(o['calls'], o['decisions']):>6}")
    print("VPIP/PFR/PFAI(pre-flop all-in raise) % of hands dealt; 3B % of chances facing 1 raise; "
          "F2PFR fold vs PF raise; oShv open-shove count;\nF2B fold to postflop bet; Agg postflop "
          "bet+raise share of actions; pAI postflop all-in bets; TRbig turn/river bets/raises "
          ">=0.66 pot as % of T/R actions; Call% calling-station share.")

    print(f"\n{'team':<20}{'SD':>5}{'SD 2p+/1p/hc':>15}{'bigTR->SD 2p+/1p/hc':>22}"
          f"{'expN':>6}{'expAvgRk':>9}{'expHi%':>8}{'expEq':>6}{'expPairFlop%':>13}")
    for e in ents:
        o = opp[e]
        nm = ("*" if e == me else " ") + str(names.get(e, e))[:18]
        a = opp_sd_all[e]
        c = opp_cats[e]
        rk = exp_ranks[e]
        avg = f"{sum(rk) / len(rk):.2f}" if rk else "-"
        print(f"{nm:<20}{o['sd']:>5}{f'{a[0]}/{a[1]}/{a[2]}':>15}{f'{c[0]}/{c[1]}/{c[2]}':>22}"
              f"{o['exposures']:>6}{avg:>9}"
              f"{pct(o['exp_hi'], o['exp_cmp'] - o['exp_eq']):>8}{o['exp_eq']:>6}"
              f"{pct(o['exp_pairs_flop'], o['exposures']):>13}")
    print("bigTR->SD: showdown hand class after making a big turn/river bet/raise. expHi%: share of "
          "showdowns where the exposed card outranked the hidden one\n(pairs excluded, n=expEq). "
          "~50% suggests no rank preference; expPairFlop%: exposed card pairs a flop card.")

    print(f"\n=== BIGGEST LOSSES (top {top_n})  [cards: dealt>kept*exposed; R=all-in raise]")
    leaks.sort(key=lambda x: x[0])
    for _, _, d in leaks[:top_n]:
        print(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()
    analyze(args.path, args.top)


if __name__ == "__main__":
    main()
