"""One pass over a round file. usage: python3 -I extract.py HANDS.gz OUT.pkl NW [MAXT]
Outputs: token streams per (table, seat) for the top-20 teams (avalon included), response-by-size counters,
exploit-opportunity ledger per target team, ICM slope sums.
Semantics: blind = posted, call = increment, raise = street raise-to total."""
import json, pickle, subprocess, sys, collections
from multiprocessing import Pool
import numpy as np

TOP = ["Lemonade", "2 Curry", "avalon", "sandylikesfrogs", "Team 123", "Team 72", "AZ", "pocket rockets", "Team 82",
       "Gavilan", "TeamBallHog", "thepastaway", "stanford deviants", "Always Folds", "Curious George", "Golden Knight",
       "nik airball", "one in a krillion", "Chikerbot", "Foldemort"]
RANKS = {r: i for i, r in enumerate("23456789TJQKA", start=2)}
POS = ("EP", "MP", "CO", "BTN", "SB", "BB")
F = {}


def fid(name):
    if name not in F:
        F[name] = len(F) + 1
    return F[name]


def depth_b(bbs):
    return 0 if bbs < 8 else 1 if bbs < 15 else 2 if bbs < 25 else 3 if bbs < 40 else 4


def gran(amt, bb):
    if amt % bb == 0: return 0
    if (2 * amt) % bb == 0: return 1
    if amt % 10 == 0: return 2
    if amt % 5 == 0: return 3
    return 4


def face_b(fr):
    return 0 if fr < 0.4 else 1 if fr < 0.75 else 2 if fr < 1.1 else 3


BE = (0.28, 0.4, 0.55, 0.7, 0.9, 1.25)
OE = (2.05, 2.25, 2.45, 2.75, 3.25)


def bucket(x, edges):
    for i, e in enumerate(edges):
        if x < e: return i
    return len(edges)


def hclass(c2):
    a, b = sorted((RANKS[c2[0][0]], RANKS[c2[1][0]]), reverse=True)
    su = c2[0][1] == c2[1][1]
    if a == b: return 0 if a >= 10 else 1
    if b >= 10: return 2
    if a == 14: return 3 if su else 4
    if a >= 10: return 5 if su else 6
    if su and a - b <= 2: return 7
    return 8


_T = {}
_YOU = None


def init(names, you):
    global _T, _YOU
    _T = {eid: TOP.index(nm) for eid, nm in names.items() if nm in TOP}
    _YOU = you


def process(line):
    t = json.loads(line)
    hands = t.get("hands") or []
    if not hands: return None
    seats, fill = t["seats"], t["fillers"]
    n = len(seats)
    tm = [(-2 if fill[i] else _T.get(seats[i], -1)) for i in range(n)]  # -2 filler, -1 rest
    toks = [[] for _ in range(n)]; hids = [[] for _ in range(n)]
    nh = [0] * n
    resp = collections.Counter()   # postflop responses
    opn = collections.Counter()    # preflop open outcomes
    led = collections.Counter()    # ledger (target team, kind, alive, tb) -> [n, pot, bet]
    slope = collections.Counter()

    def emit(s, hi, name, val):
        if tm[s] >= 0:
            toks[s].append(fid(name) * 4096 + max(0, min(4095, int(val))))
            hids[s].append(hi)

    def cls(s):
        return 3 if tm[s] == -2 else 2 if tm[s] == -1 else 0 if tm[s] == 2 else 1

    for hi, h in enumerate(hands):
        bb = h["blinds"][1] or 1
        sb = h["stacks_before"]; sa = h["stacks_after"]
        live = [i for i in range(n) if sb[i] > 0]
        alive = len(live)
        tb = 0 if hi < 10 else 1 if hi < 20 else 2
        eb, ea = h.get("equity_before"), h.get("equity_after")
        if eb and ea:
            avg = sum(sb) / alive
            for i in live:
                ds = sa[i] - sb[i]
                if ds and abs(ds) < 0.25 * sb[i]:
                    k = (alive, bucket(sb[i] / avg, (0.5, 1.5)))
                    slope[k + (0,)] += ds * (ea[i] - eb[i]); slope[k + (1,)] += ds * ds
        for i in live: nh[i] += 1
        btn = h["button"]
        order = []; k = btn
        for _ in range(n):
            k = (k + 1) % n
            if sb[k] > 0: order.append(k)
        pos = {}; L = len(order)
        if L == 2:
            pos[order[-1]] = "SB"; pos[order[0]] = "BB"
        else:
            for j, s in enumerate(order):
                pos[s] = "SB" if j == 0 else "BB" if j == 1 else "BTN" if j == L - 1 else "CO" if j == L - 2 else "MP" if j == L - 3 else "EP"
        bbseat = None
        left = list(sb); committed = [0] * n
        cur_bet = 0; pot = 0; street = 0; nraise = 0; limpers = 0; callers = 0
        jam_live = False; last_raise_to = 0; opener = None; pf_aggr = None
        inhand = set(live); last_frac = 0.0; last_allin = False; cbet_done = False
        flop = []; exposed = {}; role = {}
        open_rec = None  # (key, opener) while lone open is live
        street_bets = 0; bettor = None; bet_key = None; responded = set(); acted_street = set()
        first_bet_chance = set()
        nblind = 0
        for e in h["events"]:
            k = e["kind"]; s = e.get("seat"); amt = e.get("amount") or 0
            if k == "blind":
                left[s] -= amt; pot += amt; committed[s] += amt; cur_bet = max(cur_bet, committed[s])
                nblind += 1
                if amt >= bb or nblind == 2: bbseat = s
                continue
            if k == "board":
                street += 1
                if street == 1: flop = e.get("cards") or []
                committed = [0] * n; cur_bet = 0; last_frac = 0.0; last_allin = False
                street_bets = 0; bettor = None; bet_key = None; responded = set(); acted_street = set(); first_bet_chance = set()
                continue
            if k == "reveal":
                cs = e.get("cards") or []
                if cs and s is not None and flop:
                    r = RANKS.get(cs[0][0], 0); exposed[s] = cs[0]
                    fr = [RANKS[c[0]] for c in flop]; fs = [c[1] for c in flop]
                    emit(s, hi, "VAR expose", r * 4 + (2 if r in fr else 0) + (1 if fs.count(cs[0][1]) >= 2 else 0))
                    emit(s, hi, "VAR expose_rel", (0 if r > max(fr) else 1 if r in fr else 2 if r > min(fr) else 3))
                continue
            if k == "show":
                cs = e.get("cards") or []
                if len(cs) == 2:
                    if s in exposed:
                        ex = exposed[s]; o = [c for c in cs if c != ex]
                        if len(o) == 1:
                            fr = [RANKS[c[0]] for c in flop]
                            re_, ro = RANKS[ex[0]], RANKS[o[0][0]]
                            low = 0 if re_ < ro else 1 if re_ > ro else 2
                            emit(s, hi, "VAR sd", low * 4 + (re_ in fr) * 2 + (ro in fr))
                    emit(s, hi, f"OTH show r{role.get(s, 3)}", hclass(cs))
                continue
            if k not in ("fold", "check", "call", "raise"): continue
            to_call = cur_bet - committed[s]
            stack_now = left[s] + committed[s]
            allin = k == "raise" and amt >= stack_now
            a3 = 0 if k == "fold" else 2 if k == "raise" else 1
            if street == 0:
                d = depth_b(stack_now / bb)
                if jam_live and to_call > 0:
                    if nraise == 2 and s == opener: emit(s, hi, "FQ pf_face_3bjam", a3)
                    else: emit(s, hi, f"FQ pf_face_jam d{depth_b(to_call / bb)}", a3)
                elif nraise == 0 and limpers == 0:
                    emit(s, hi, f"FQ pf_unopened {pos[s]} d{d}", a3)
                    if k != "fold" and not (k == "check"):
                        ty = 0 if k == "call" else 3 if allin else 1 if amt == 2 * bb else 2
                        emit(s, hi, f"LMS entry d{d}", ty)
                        emit(s, hi, f"LMS3 entry d{d}", min(ty, 2) if ty != 3 else 3)
                        if ty == 3: emit(s, hi, "LMS jamdepth", round(stack_now / bb * 2))
                        elif ty in (1, 2):
                            emit(s, hi, (f"SZ open {pos[s]}" if d >= 2 else "SZ open short"), round(amt / bb * 20))
                    # ledger: steal chance vs BB target
                    if bbseat is not None and bbseat != s and tm[bbseat] >= 0 and pos[s] in ("BTN", "SB") and tm[s] != -2:
                        led[(tm[bbseat], 4, alive, tb, 0)] += 1; led[(tm[bbseat], 4, alive, tb, 1)] += pot; led[(tm[bbseat], 4, alive, tb, 2)] += 2.2 * bb
                elif nraise == 0:
                    emit(s, hi, f"FQ pf_limped d{d}", a3)
                    if k == "raise":
                        emit(s, hi, "LMS iso", 1 if allin else 0)
                        if not allin: emit(s, hi, "SZ iso", round(amt / bb * 4))
                elif nraise == 1 and s != opener:
                    emit(s, hi, f"FQ pf_face_open d{d}", a3)
                    if pos[s] == "BB" and callers == 0 and pos.get(opener) in ("BTN", "SB", "CO"):
                        emit(s, hi, "FQ pf_bb_vs_steal", a3)
                    if k == "raise":
                        emit(s, hi, f"LMS reraise d{d}", 1 if allin else 0)
                        if not allin: emit(s, hi, "SZ 3b", round(amt / last_raise_to * 10))
                    if tm[opener] >= 0 and tm[s] != -2:
                        kk = (tm[opener], 0, alive, tb)
                        led[kk + (0,)] += 1; led[kk + (1,)] += pot; led[kk + (2,)] += min(3 * last_raise_to, stack_now) - committed[s]
                elif nraise == 2 and s == opener:
                    emit(s, hi, f"FQ pf_face_3b", a3)
                    if k == "raise":
                        emit(s, hi, "LMS 4b", 1 if allin else 0)
                        if not allin: emit(s, hi, "SZ 4b", round(amt / last_raise_to * 10))
                else:
                    emit(s, hi, f"FQ pf_other d{d}", a3)
                if k == "raise" and not allin: emit(s, hi, "SZ gran pre", gran(amt, bb))
                # open record
                if open_rec is not None and s != open_rec[1]:
                    ok = open_rec[0]
                    opn[ok + (4 + a3,)] += 1
                    if cls(s) == 1: opn[ok + (7 + a3,)] += 1
                    if k == "raise": opn[ok + (3,)] += 1; open_rec = None
                    elif k == "call": open_rec = (ok, open_rec[1], True)
                if k == "raise" and nraise == 0 and limpers == 0 and not allin and tm[s] != -2:
                    ok = (tm[s], pos[s], bucket(amt / bb, OE), 1 if stack_now / bb >= 25 else 0)
                    opn[ok + (0,)] += 1
                    opn[ok + (10,)] += (sa[s] - sb[s]) / bb
                    open_rec = (ok, s, False)
            else:
                agg = 1 if s == pf_aggr else 0
                hu = 1 if len(inhand) == 2 else 0
                if to_call <= 0:
                    emit(s, hi, f"FQ post_first s{street} agg{agg} hu{hu}", 2 if k == "raise" else 1)
                    if k == "raise":
                        emit(s, hi, f"LMS postbet s{street}", 1 if allin else 0)
                        if not allin and pot > 0: emit(s, hi, f"SZ bet s{street}", min(240, round(amt / pot * 40)))
                    if street == 1 and agg and not cbet_done and cur_bet == 0:
                        emit(s, hi, "FQ cbet", 1 if k == "raise" else 0)
                    # ledger: s can bet into a HU target
                    if hu and cur_bet == 0 and s not in first_bet_chance:
                        first_bet_chance.add(s)
                        o = [x for x in inhand if x != s][0]
                        if tm[o] >= 0 and tm[s] != -2:
                            kk = (tm[o], street, alive, tb)
                            led[kk + (0,)] += 1; led[kk + (1,)] += pot; led[kk + (2,)] += 0.6 * pot
                else:
                    own_in = committed[s] > 0
                    if not own_in or street_bets == 0:
                        fb = 4 if last_allin else face_b(last_frac)
                        emit(s, hi, f"FQ post_face s{street} agg{agg} hu{hu} f{fb}", a3)
                    else:
                        emit(s, hi, f"FQ post_face_r s{street}", a3)
                    if k == "raise":
                        emit(s, hi, f"LMS postraise", 1 if allin else 0)
                        if not allin and cur_bet > 0: emit(s, hi, f"SZ raise s{street}", round(amt / cur_bet * 4))
                    if bet_key is not None and street_bets == 1 and s not in responded and s != bettor and tm[s] != -2:
                        responded.add(s)
                        resp[bet_key + (cls(s), hu, a3)] += 1
                if k == "raise" and not allin: emit(s, hi, "SZ gran post", gran(amt, bb))
                if street == 1 and k == "raise" and cur_bet == 0: cbet_done = True
            # state update
            if k == "fold":
                inhand.discard(s)
            elif k == "call":
                left[s] -= amt; committed[s] += amt; pot += amt
                if street == 0:
                    if nraise == 0: limpers += 1; role.setdefault(s, 3)
                    else: callers += 1; role[s] = 1
            elif k == "raise":
                inc = amt - committed[s]; pot_before = pot
                if street > 0:
                    if cur_bet == 0:
                        fr = amt / max(1, pot_before)
                        last_frac = fr
                        street_bets = 1; bettor = s
                        bet_key = (tm[s] if tm[s] >= 0 else -1, street, 7 if allin else bucket(fr, BE), 1 if s == pf_aggr else 0) if tm[s] != -2 else None
                    else:
                        last_frac = (amt - cur_bet) / max(1, pot_before + cur_bet - committed[s])
                        street_bets += 1
                    last_allin = allin
                left[s] -= inc; pot += inc; committed[s] = amt
                if street == 0:
                    if nraise == 0: opener = s; role[s] = 0
                    else: role[s] = 2
                    nraise += 1; pf_aggr = s
                    if amt > cur_bet: jam_live = left[s] <= 0
                last_raise_to = amt; cur_bet = max(cur_bet, amt)
        if open_rec is not None:
            opn[open_rec[0] + ((2 if open_rec[2] else 1),)] += 1
    out = []
    for s in range(n):
        if tm[s] >= 0:
            out.append((tm[s], nh[s], np.array(toks[s], dtype=np.int32), np.array(hids[s], dtype=np.uint16)))
    return (t["iteration"], t["table"], out, resp, opn, led, slope, dict(F), len(hands))


def lines(path, maxt):
    p = subprocess.Popen(["gzip", "-dc", path], stdout=subprocess.PIPE, bufsize=1 << 22)
    yield p.stdout.readline()
    c = 0
    for ln in p.stdout:
        if ln.startswith(b'{"you"'): continue
        yield ln
        c += 1
        if maxt and c >= maxt: break
    p.kill()


def main(path, out, nw=8, maxt=0):
    g = lines(path, maxt)
    head = json.loads(next(g))
    names = {e["entry_id"]: e["team_name"] for e in head["entries"]}
    assert names[head["you"]] == "avalon"
    rows = []; R = collections.Counter(); O = collections.Counter(); Lg = collections.Counter(); S = collections.Counter()
    FN = {}; nt = 0; nhands = 0
    with Pool(nw, initializer=init, initargs=(names, head["you"])) as pool:
        for r in pool.imap(process, g, chunksize=16):
            if r is None: continue
            it, tb, seats, resp, opn, led, slope, Fw, nhd = r
            nt += 1; nhands += nhd
            # remap worker-local fids to global names
            inv = {v: k for k, v in Fw.items()}
            for (ti, nh, tk, hd) in seats:
                if len(tk):
                    nmz = [inv[x] for x in np.unique(tk // 4096)]
                    for nm in nmz:
                        if nm not in FN: FN[nm] = len(FN) + 1
                    mp = np.zeros(max(inv) + 1, dtype=np.int64)
                    for v, nm in inv.items():
                        if nm in FN: mp[v] = FN[nm]
                    tk = (mp[tk // 4096] * 4096 + tk % 4096).astype(np.int32)
                rows.append((it, tb, ti, nh, tk, hd))
            R.update(resp); O.update(opn); Lg.update(led); S.update(slope)
    pickle.dump({"F": FN, "rows": rows, "resp": dict(R), "opn": dict(O), "led": dict(Lg), "slope": dict(S), "TOP": TOP,
                 "ntables": nt, "nhands": nhands}, open(out, "wb"), protocol=4)
    print(path, nt, "tables", len(rows), "seats", sum(len(r[4]) for r in rows), "tokens", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8, int(sys.argv[4]) if len(sys.argv) > 4 else 0)
