"""One streaming pass over a hand-history download -> counters for the adaptation study.

usage: python3 -I extract.py HANDS.jsonl.gz OUT.pkl [maxtables]
Teams are keyed by team_name (Boston entry ids change per tournament). Fillers are team None.
Event semantics: blind = chips posted; call = chips added; raise = raise-to total for the street.
"""
import gzip, json, pickle, sys
from array import array
from collections import defaultdict

ACT = ("fold", "check", "call", "raise")
RK = {r: i for i, r in enumerate("23456789TJQKA")}


def bk(x, edges):
    for i, e in enumerate(edges):
        if x < e:
            return i
    return len(edges)


STK = (10, 20, 40)            # own stack in bb
PLB = {8: 0, 7: 0, 6: 1, 5: 1, 4: 2, 3: 3, 2: 4}
OPSZ = (2.05, 2.3, 2.6, 3.1)  # open raise-to in bb
TBR = (2.6, 3.2, 4.0)         # 3-bet to / open to
FR = (0.22, 0.30, 0.37, 0.45, 0.55)  # to_call / pot (pot includes the bet)
SPR = (1, 3, 8)
POTBB = (5, 10, 25)
JAMBB = (6, 10, 15, 25)
ODDS = (0.3, 0.4, 0.45)


def main(path, out, maxtables=None):
    A = defaultdict(lambda: [0, 0])     # (team, metric, parity) -> n,k
    SZ = defaultdict(int)               # (team, kind, parity, bucket) -> count
    T = defaultdict(lambda: [0, 0])     # (team, metric, third, lvl, plb, stkb) -> n,k
    Q3 = defaultdict(lambda: [0, 0, 0, 0])  # (team, metric, stratum) -> n_other,k_other,n_av,k_av
    EXP = defaultdict(lambda: [0, 0])   # (target team, metric) -> n,k  (how others respond to target)
    PT = defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0.0])  # team -> tables, their pts, our pts, our pts^2, their pts^2
    REC = {k: array("h") for k in ("tb", "fb", "btc", "steal", "cj")}
    rows = array("f")
    V = defaultdict(int)
    fh = gzip.open(path, "rt")
    head = json.loads(fh.readline())
    YOU = head["you"]
    name = {e["entry_id"]: e["team_name"] for e in head["entries"]}
    teams = sorted(set(name.values()))
    tix = {t: i for i, t in enumerate(teams)}
    AV = name[YOU]
    ntab = 0
    for line in fh:
        if '"hands"' not in line[:400] and line.startswith('{"you"'):
            continue
        t = json.loads(line)
        if "hands" not in t:
            continue
        hands = t["hands"]
        if not hands:
            V["empty"] += 1
            continue
        ntab += 1
        if maxtables and ntab > maxtables:
            break
        seats, fill = t["seats"], t["fillers"]
        n = len(seats)
        tm = [None if fill[i] else name.get(seats[i]) for i in range(n)]
        ti = [(-1 if tm[i] is None else tix[tm[i]]) for i in range(n)]
        isav = [tm[i] == AV for i in range(n)]
        par = t["iteration"] & 1
        nh = len(hands)
        fin = hands[-1]["equity_after"]
        ours = [fin[i] for i in range(n) if isav[i]]
        op = ours[0] if ours else float("nan")
        rows.append(op); rows.append(nh)
        for i in range(n):
            if tm[i] is not None:
                p = PT[tm[i]]
                p[0] += 1; p[1] += fin[i]; p[2] += op; p[3] += op * op; p[4] += fin[i] * fin[i]
        # per-seat in-table history
        h_dealt = [0] * n; h_open = [0] * n; h_oopp = [0] * n
        h_f3n = [0] * n; h_f3k = [0] * n
        h_bbn = [0] * n; h_bbk = [0] * n
        h_pfn = [0] * n; h_pfk = [0] * n
        h_pbn = [0] * n; h_pbk = [0] * n
        h_jam = [0] * n
        tot = [0] * 11  # table totals: f3n f3k bbn bbk pfn pfk pbn pbk jam dealt open
        boston = "flop_chips_before" in hands[0]
        for hi, h in enumerate(hands):
            third = 3 * hi // nh
            bb = h["blinds"][1] or 1
            lvl = min((h["hand"] - 1) // 20, 7)
            half = ((h["hand"] - 1) % 20) >= 10
            late = 2 * hi >= nh
            sb = h["stacks_before"]
            pl = sum(1 for x in sb if x > 0)
            plb = PLB.get(pl, 0)
            left = list(sb)
            committed = [0] * n
            cur_bet = 0; pot = 0; street = 0
            pf_raises = 0; limpers = 0; callers = 0
            opener = -1; open_to = 0; open_behind = 0; opener_allin = False
            tbettor = -1; tb_allin = False; tb_ratio = 0.0
            last_raiser = -1; jam_live = False; pfa = -1
            bbseat = -1
            folded = set(); allin = set()
            vp = set(); pr = set(); jm = set()
            checks = 0; nbets = 0; last_bettor = -1; bettor_allin = False
            flop_r = (); exposed = {}; shown = {}
            for e in h["events"]:
                k = e["kind"]
                if k == "blind":
                    s = e["seat"]; amt = e["amount"]
                    left[s] -= amt; committed[s] += amt; pot += amt
                    if committed[s] > cur_bet:
                        cur_bet = committed[s]
                    bbseat = s
                    if left[s] <= 0:
                        allin.add(s)
                    continue
                if k == "board":
                    street += 1
                    if street == 1:
                        flop_r = tuple(c[0] for c in e["cards"])
                        flop_s = [c[1] for c in e["cards"]]
                    committed = [0] * n
                    cur_bet = 0; checks = 0; nbets = 0; last_bettor = -1; bettor_allin = False
                    continue
                if k == "reveal":
                    cs = e.get("cards")
                    if cs:
                        s = e["seat"]; c = cs[0]
                        exposed[s] = c
                        if tm[s] is not None:
                            a = A[(tm[s], "exp_hi", par)]; a[0] += 1; a[1] += RK[c[0]] >= 8   # T or better
                            a = A[(tm[s], "exp_pair", par)]; a[0] += 1; a[1] += c[0] in flop_r
                            a = A[(tm[s], "exp_ace", par)]; a[0] += 1; a[1] += c[0] == "A"
                            SZ[(tm[s], "exprank", par, RK[c[0]])] += 1
                    continue
                if k == "show":
                    shown[e["seat"]] = e.get("cards") or []
                    continue
                if k not in ACT:
                    continue
                s = e["seat"]; amt = e.get("amount") or 0
                team = tm[s]
                to_call = cur_bet - committed[s]
                stack = left[s] + committed[s]
                stkb = bk(stack / bb, STK)
                if street == 0:
                    if k == "call" or k == "raise":
                        vp.add(s)
                    is_allin = False
                    if k == "raise":
                        add = amt - committed[s]
                        if add >= left[s]:
                            is_allin = True
                        pr.add(s)
                        if is_allin:
                            jm.add(s)
                    # --- open opportunity
                    if pf_raises == 0 and limpers == 0 and not (s == bbseat and to_call <= 0):
                        behind = pl - len(folded) - 1
                        kk = k == "raise"
                        h_oopp[s] += 1
                        if kk:
                            h_open[s] += 1; tot[10] += 1
                        if team is not None:
                            a = A[(team, "open", par)]; a[0] += 1; a[1] += kk
                            a = A[(team, "limp", par)]; a[0] += 1; a[1] += k == "call"
                            a = A[(team, "openjam", par)]; a[0] += 1; a[1] += is_allin
                            a = T[(team, "open", third, lvl, half, plb, stkb)]; a[0] += 1; a[1] += kk
                            if lvl == 0 and pl == 8:
                                a = A[(team, "open_l1", par)]; a[0] += 1; a[1] += kk
                            if stack / bb < 15:
                                a = A[(team, "openjam_short", par)]; a[0] += 1; a[1] += is_allin
                            if kk:
                                if is_allin:
                                    SZ[(team, "open", par, 99)] += 1
                                else:
                                    b = min(int(amt / bb * 4 + 0.5), 28)
                                    SZ[(team, "open", par, b)] += 1
                                    if lvl == 0:
                                        SZ[(team, "open0", par, b)] += 1
                            if behind <= 3 and bbseat != s and bbseat >= 0:
                                o = bbseat
                                bstk = bk((left[o] + committed[o]) / bb, STK)
                                q = Q3[(team, "steal", (behind, stkb, plb, bstk, late))]
                                if isav[o]:
                                    q[2] += 1; q[3] += kk
                                else:
                                    q[0] += 1; q[1] += kk
                                if h_bbn[o] >= 1 and behind <= 2:
                                    REC["steal"].extend((ti[s], ti[o], kk, h_bbn[o], h_bbk[o], tot[2] - h_bbn[o] - h_bbn[s],
                                                         tot[3] - h_bbk[o] - h_bbk[s], lvl, pl, stkb, behind, bstk, hi, min(nh, 30000)))
                    # --- 3-bet opportunity (one raise so far, opener not all-in)
                    elif pf_raises == 1 and s != opener and not opener_allin:
                        kk = k == "raise"
                        osz = bk(open_to / bb, OPSZ)
                        blind = committed[s] > 0 and s not in vp or s == bbseat
                        if team is not None:
                            a = A[(team, "3bet", par)]; a[0] += 1; a[1] += kk
                            a = A[(team, "3betjam", par)]; a[0] += 1; a[1] += is_allin
                            a = A[(team, "coldcall", par)]; a[0] += 1; a[1] += k == "call"
                            a = T[(team, "3bet", third, lvl, half, plb, stkb)]; a[0] += 1; a[1] += kk
                            if kk:
                                SZ[(team, "3bet", par, 99 if is_allin else min(int(amt / open_to * 2 + 0.5), 14))] += 1
                            if s == bbseat and callers == 0:
                                a = A[(team, "bbfold", par)]; a[0] += 1; a[1] += k == "fold"
                            o = opener
                            ostk = bk((left[o] + committed[o]) / bb, STK)
                            q = Q3[(team, "3bet", (stkb, osz, min(open_behind, 4), min(callers, 1), blind, plb, ostk, late))]
                            if isav[o]:
                                q[2] += 1; q[3] += kk
                            else:
                                q[0] += 1; q[1] += kk
                            if tm[o] is not None:
                                x = EXP[(tm[o], "3bet_vs_me")]; x[0] += 1; x[1] += kk
                                if s == bbseat and callers == 0:
                                    x = EXP[(tm[o], "bbfold_vs_me")]; x[0] += 1; x[1] += k == "fold"
                            if h_f3n[o] >= 1:
                                REC["tb"].extend((ti[s], ti[o], kk, h_f3n[o], h_f3k[o], tot[0] - h_f3n[o] - h_f3n[s],
                                                  tot[1] - h_f3k[o] - h_f3k[s], lvl, pl, stkb, osz, min(open_behind, 4), hi, min(nh, 30000),
                                                  h_open[o], h_dealt[o], min(callers, 1) + 2 * blind, is_allin, ostk, h_oopp[o]))
                        if s == bbseat and callers == 0:
                            h_bbn[s] += 1; tot[2] += 1
                            if k == "fold":
                                h_bbk[s] += 1; tot[3] += 1
                    # --- opener facing a 3-bet
                    elif pf_raises == 2 and s == opener and to_call > 0:
                        kk = k == "fold"
                        o = tbettor
                        if team is not None:
                            a = A[(team, "f3b", par)]; a[0] += 1; a[1] += kk
                            a = A[(team, "4bet", par)]; a[0] += 1; a[1] += k == "raise"
                            a = T[(team, "f3b", third, lvl, half, plb, stkb)]; a[0] += 1; a[1] += kk
                            if not tb_allin:
                                a = A[(team, "f3b_nonjam", par)]; a[0] += 1; a[1] += kk
                            q = Q3[(team, "f3b", (stkb, 9 if tb_allin else bk(tb_ratio, TBR), plb, o == bbseat, late))]
                            if isav[o]:
                                q[2] += 1; q[3] += kk
                            else:
                                q[0] += 1; q[1] += kk
                            if tm[o] is not None:
                                x = EXP[(tm[o], "f3b_vs_me")]; x[0] += 1; x[1] += kk
                        h_f3n[s] += 1; tot[0] += 1
                        if kk:
                            h_f3k[s] += 1; tot[1] += 1
                    # --- facing an all-in
                    if jam_live and to_call > 0 and team is not None:
                        kk = k != "fold"
                        o = last_raiser
                        a = A[(team, "calljam", par)]; a[0] += 1; a[1] += kk
                        a = T[(team, "calljam", third, lvl, half, plb, stkb)]; a[0] += 1; a[1] += kk
                        jb = bk(cur_bet / bb, JAMBB)
                        ob = bk(to_call / (pot + to_call), ODDS)
                        q = Q3[(team, "calljam", (jb, ob, plb, min(pf_raises, 3), stkb, late))]
                        if isav[o]:
                            q[2] += 1; q[3] += kk
                        else:
                            q[0] += 1; q[1] += kk
                        if tm[o] is not None:
                            x = EXP[(tm[o], "calljam_vs_me")]; x[0] += 1; x[1] += kk
                        if h_dealt[o] >= 5:
                            REC["cj"].extend((ti[s], ti[o], kk, h_dealt[o], h_jam[o], tot[9] - h_dealt[o] - h_dealt[s],
                                              tot[8] - h_jam[o] - h_jam[s], lvl, pl, stkb, jb, ob, hi, min(nh, 30000)))
                else:
                    nact = pl - len(folded)
                    if to_call <= 0:
                        kk = k == "raise"
                        if team is not None:
                            a = A[(team, "bet%d" % street, par)]; a[0] += 1; a[1] += kk
                            if checks > 0:
                                a = A[(team, "btc%d" % street, par)]; a[0] += 1; a[1] += kk
                                a = T[(team, "btc%d" % street, third, lvl, half, plb, stkb)]; a[0] += 1; a[1] += kk
                            if street == 1 and s == pfa:
                                a = A[(team, "cbet", par)]; a[0] += 1; a[1] += kk
                            if kk:
                                if amt >= left[s]:
                                    SZ[(team, "bet%d" % street, par, 99)] += 1
                                else:
                                    SZ[(team, "bet%d" % street, par, min(int(amt / pot * 10 + 0.5), 20))] += 1
                        if nact == 2:
                            o = -1
                            for j in range(n):
                                if sb[j] > 0 and j != s and j not in folded:
                                    o = j
                            if o >= 0 and o not in allin:
                                eff = min(left[s], left[o])
                                role = 0 if s == pfa else (1 if o == pfa else 2)
                                if team is not None:
                                    q = Q3[(team, "btc", (street, checks > 0, bk(eff / pot, SPR), bk(pot / bb, POTBB), min(plb, 2), role, late))]
                                    if isav[o]:
                                        q[2] += 1; q[3] += kk
                                    else:
                                        q[0] += 1; q[1] += kk
                                    if h_pfn[o] >= 2:
                                        REC["btc"].extend((ti[s], ti[o], kk, h_pfn[o], h_pfk[o], tot[4] - h_pfn[o] - h_pfn[s],
                                                           tot[5] - h_pfk[o] - h_pfk[s], lvl, pl, stkb, street, role, hi, min(nh, 30000),
                                                           bk(eff / pot, SPR), checks > 0))
                        h_pbn[s] += 1; tot[6] += 1
                        if kk:
                            h_pbk[s] += 1; tot[7] += 1
                    else:
                        kk = k == "fold"
                        if team is not None:
                            a = A[(team, "fold%d" % street, par)]; a[0] += 1; a[1] += kk
                            a = A[(team, "xraise%d" % street, par)]; a[0] += 1; a[1] += k == "raise"
                            a = T[(team, "fold%d" % street, third, lvl, half, plb, stkb)]; a[0] += 1; a[1] += kk
                        if nact == 2 and last_bettor >= 0 and last_bettor != s:
                            o = last_bettor
                            fr = 9 if (bettor_allin or to_call >= left[s]) else bk(to_call / pot, FR)
                            c = exposed.get(o)
                            if c is None:
                                eb = 0
                            else:
                                r = RK[c[0]]
                                eb = (1 if r < 8 else (2 if r < 12 else 3)) + 3 * (c[0] in flop_r)
                            if team is not None:
                                a = A[(team, "fold%dhu" % street, par)]; a[0] += 1; a[1] += kk
                                q = Q3[(team, "foldbet", (street, fr, nbets >= 2, min(plb, 2), bk(pot / bb, POTBB), eb, late))]
                                if isav[o]:
                                    q[2] += 1; q[3] += kk
                                else:
                                    q[0] += 1; q[1] += kk
                                if tm[o] is not None:
                                    x = EXP[(tm[o], "fold%d_vs_me" % street)]; x[0] += 1; x[1] += kk
                                if h_pbn[o] >= 3:
                                    REC["fb"].extend((ti[s], ti[o], kk, h_pbn[o], h_pbk[o], tot[6] - h_pbn[o] - h_pbn[s],
                                                      tot[7] - h_pbk[o] - h_pbk[s], lvl, pl, stkb, street, fr, hi, min(nh, 30000), eb, nbets >= 2))
                        h_pfn[s] += 1; tot[4] += 1
                        if kk:
                            h_pfk[s] += 1; tot[5] += 1
                # ---- apply the action
                if k == "fold":
                    folded.add(s)
                elif k == "check":
                    checks += 1
                elif k == "call":
                    left[s] -= amt; committed[s] += amt; pot += amt
                    if left[s] <= 0:
                        allin.add(s)
                    if street == 0:
                        if pf_raises == 0:
                            limpers += 1
                        elif pf_raises == 1:
                            callers += 1
                elif k == "raise":
                    add = amt - committed[s]
                    ai = False
                    if add >= left[s]:
                        add = left[s]; ai = True; allin.add(s)
                    to = committed[s] + add
                    left[s] -= add; committed[s] = to; pot += add
                    if to > cur_bet:
                        cur_bet = to
                    if street == 0:
                        pf_raises += 1
                        if pf_raises == 1:
                            opener = s; open_to = to; open_behind = pl - len(folded) - 1; opener_allin = ai
                        elif pf_raises == 2:
                            tbettor = s; tb_allin = ai; tb_ratio = to / max(open_to, 1)
                        last_raiser = s; jam_live = ai; pfa = s
                    else:
                        nbets += 1; last_bettor = s; bettor_allin = ai
            # ---- end of hand
            sa = h["stacks_after"]
            V["hands"] += 1
            for i in folded:
                if left[i] != sa[i]:
                    V["bad_fold_stack"] += 1
                    break
            for i in range(n):
                if sb[i] > 0:
                    h_dealt[i] += 1; tot[9] += 1
                    if i in jm:
                        h_jam[i] += 1; tot[8] += 1
                    team = tm[i]
                    if team is not None:
                        a = A[(team, "vpip", par)]; a[0] += 1; a[1] += i in vp
                        a = A[(team, "pfr", par)]; a[0] += 1; a[1] += i in pr
                        a = A[(team, "jam", par)]; a[0] += 1; a[1] += i in jm
            for s, cs in shown.items():
                c = exposed.get(s)
                if c is not None and len(cs) == 2 and cs[0][0] != cs[1][0] and tm[s] is not None and c in cs:
                    o = cs[0] if cs[1] == c else cs[1]
                    a = A[(tm[s], "explow", par)]; a[0] += 1; a[1] += RK[c[0]] < RK[o[0]]
            if boston:
                fb_, fa_ = h["flop_chips_before"], h["flop_chips_after"]
                bidders = {e["seat"] for e in h["events"] if e["kind"] == "bid"}
                for s in bidders:
                    if tm[s] is None:
                        continue
                    spent = fb_[s] - fa_[s]
                    a = A[(tm[s], "bid_any", par)]; a[0] += 1; a[1] += spent > 0
                    if fb_[s] > 0:
                        fr = spent / fb_[s]
                        a = A[(tm[s], "bid_big", par)]; a[0] += 1; a[1] += fr >= 0.2
                        SZ[(tm[s], "bidfrac", par, bk(fr, (1e-9, 0.05, 0.1, 0.2, 0.4, 0.7)))] += 1
                    SZ[(tm[s], "bidabs", par, min(spent // 25, 40))] += 1
    res = dict(path=path, av=AV, teams=teams, ntab=ntab, V=dict(V),
               A={k: tuple(v) for k, v in A.items()}, SZ=dict(SZ), T={k: tuple(v) for k, v in T.items()},
               Q3={k: tuple(v) for k, v in Q3.items()}, EXP={k: tuple(v) for k, v in EXP.items()},
               PT={k: tuple(v) for k, v in PT.items()}, rows=rows.tobytes(),
               REC={k: v.tobytes() for k, v in REC.items()})
    with open(out, "wb") as f:
        pickle.dump(res, f, protocol=4)
    print(path.split("hands-")[-1][:8], ntab, "tables", {k: len(v) for k, v in REC.items()}, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
