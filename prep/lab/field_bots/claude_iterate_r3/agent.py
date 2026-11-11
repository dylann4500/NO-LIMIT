"""claude_iterate: EV-driven NLHE sit-and-go bot.

Preflop: precomputed equity tables (preflop.json) vs top-x% ranges; opponent ranges and fold/call
frequencies come from per-seat stats kept in `memory`; all-in decisions are scored with ICM.
Postflop: eval7 Monte Carlo equity vs each opponent's estimated range, then an EV comparison of
check/bet sizes or fold/call/raise using modelled fold/call/raise frequencies.
Everything is wrapped so that any error falls back to a legal check/fold.
"""
import gc
import json
import marshal
import os
import random

import eval7
DEBUG = bool(os.environ.get("CI_DEBUG"))
TRACE = [] if os.environ.get("CI_TRACE") else None
import poker_agent_sdk
from poker_agent_sdk import Action

HERE = os.path.dirname(os.path.abspath(__file__))
_P = json.load(open(os.path.join(HERE, "preflop.json")))
ORDER = _P["order"]
PCT = _P["pct"]
EQR = _P["eqr"]
BUCKETS = [b / 100.0 for b in _P["buckets"]]
EQTOP = _P["eqtop"]

RANKS = "23456789TJQKA"
RV = {r: i for i, r in enumerate(RANKS)}
DECK = [r + s for r in RANKS for s in "shdc"]
CARD = {c: eval7.Card(c) for c in DECK}


def _cls(a, b):
    ra, rb = a[0], b[0]
    if RV[ra] < RV[rb]:
        ra, rb = rb, ra
    if ra == rb:
        return ra + rb
    return ra + rb + ("s" if a[1] == b[1] else "o")


CLS = {(a, b): _cls(a, b) for a in DECK for b in DECK if a != b}


def _combos(c):
    S = "shdc"
    if len(c) == 2:
        return [(c[0] + S[i], c[1] + S[j]) for i in range(4) for j in range(i + 1, 4)]
    if c[2] == "s":
        return [(c[0] + s, c[1] + s) for s in S]
    return [(c[0] + x, c[1] + y) for x in S for y in S if x != y]


# Postflop villain ranges: top-x% of ORDER, subsampled so eval7's per-call range conversion stays cheap.
RB = [0.03, 0.06, 0.10, 0.15, 0.22, 0.30, 0.40, 0.55, 0.75, 1.0]
_rng0 = random.Random(12345)
RANGES = []
for _p in RB:
    _hands, _cum = [], 0
    for _c in ORDER:
        if _cum >= _p * 1326 and _hands:
            break
        _cb = _combos(_c)
        _hands.extend(_cb)
        _cum += len(_cb)
    if len(_hands) > 240:
        _hands = _rng0.sample(_hands, 240)
    _hr = eval7.HandRange("AA")
    _hr.hands = [((CARD[a], CARD[b]), 1.0) for a, b in _hands]
    RANGES.append(_hr)


def range_obj(p):
    for i, b in enumerate(RB):
        if p <= b * 1.15:
            return RANGES[i]
    return RANGES[-1]


def eq_top(cls, p):
    """HU preflop equity of class vs top-p range (interpolated)."""
    row = EQTOP[cls]
    if p <= BUCKETS[0]:
        return row[0]
    for i in range(1, len(BUCKETS)):
        if p <= BUCKETS[i]:
            lo, hi = BUCKETS[i - 1], BUCKETS[i]
            t = (p - lo) / (hi - lo)
            return row[i - 1] * (1 - t) + row[i] * t
    return row[-1]


def clip(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


# ---------------------------------------------------------------- opponent stats
# per-seat counters
(PF_OPP, VPIP, PFR, UNOP_OPP, UNOP_RAISE, FR_OPP, FR_FOLD, FR_RAISE, BIG_RAISE, FB_OPP, FB_CONT,
 P_BET, P_CALL, P_CHECK, P_FB_OPP, P_FB_FOLD, P_FB_RAISE, P_UNB_OPP, P_UNB_BET,
 SZ_OPP0, SZ_OPP1, SZ_OPP2, SZ_OPP3, SZ_RAISE0, SZ_RAISE1, SZ_RAISE2, SZ_RAISE3, NSTAT) = range(28)


def size_bucket(n):
    """0: 6+ players, 1: 4-5, 2: 3-handed, 3: heads-up."""
    if not n or n >= 6:
        return 0
    return 1 if n >= 4 else (2 if n == 3 else 3)


# Round-2 field: first-in raise frequency by table size bucket.
OPEN_PRIOR = (0.26, 0.37, 0.54, 0.71)


def rate(st, num, den, prior, k=8.0):
    if st is None:
        return prior
    return (st[num] + prior * k) / (st[den] + k)


def update_stats(mem, events, me, start_stack):
    S = mem["s"]
    h = mem["h"]  # [street, cur_bet, raises, bets{}, flags{}, bb, committed{}, startstk{}]
    for e in events:
        k = e.kind
        k = getattr(k, "value", k)
        sid = e.seat
        if k == "hand":
            h[0] = 0; h[1] = 0; h[2] = 0; h[3] = {}; h[4] = {}; h[5] = 0; h[6] = {}
            nal = sum(1 for v in h[7].values() if v and v > 0)
            if len(h) < 9:
                h.append(0)
            h[8] = size_bucket(nal)
            continue
        if k == "board":
            h[0] += 1; h[1] = 0; h[2] = 0; h[3] = {}
            continue
        if k == "stack":
            if sid is not None and e.amount is not None:
                h[7][sid] = e.amount
            continue
        if k == "ante":
            if sid is not None and e.amount:
                h[6][sid] = h[6].get(sid, 0) + e.amount
            continue
        if k == "blind":
            a = e.amount or 0
            h[3][sid] = h[3].get(sid, 0) + a
            h[6][sid] = h[6].get(sid, 0) + a
            if h[3][sid] > h[1]:
                h[1] = h[3][sid]
            if a > h[5]:
                h[5] = a
            continue
        if k not in ("fold", "check", "call", "raise") or sid is None:
            continue
        bets = h[3]
        mybet = bets.get(sid, 0)
        facing = h[1] - mybet
        stk0 = h[7].get(sid, start_stack)
        if sid != me:
            st = S.get(sid)
            if st is None:
                st = S[sid] = [0] * NSTAT
            elif len(st) < NSTAT:
                st.extend([0] * (NSTAT - len(st)))
            if h[0] == 0:
                fl = h[4].get(sid, 0)  # bit1 acted, bit2 vpip, bit4 pfr, bit8 faced raise, bit16 faced big
                if not fl & 1:
                    st[PF_OPP] += 1
                    if h[2] == 0:
                        st[UNOP_OPP] += 1
                        b_ = h[8] if len(h) > 8 else 0
                        st[SZ_OPP0 + b_] += 1
                        if k == "raise":
                            st[UNOP_RAISE] += 1
                            st[SZ_RAISE0 + b_] += 1
                    fl |= 1
                if h[2] >= 1 and not fl & 8:
                    fl |= 8
                    st[FR_OPP] += 1
                    if k == "fold":
                        st[FR_FOLD] += 1
                    elif k == "raise":
                        st[FR_RAISE] += 1
                remaining = stk0 - h[6].get(sid, 0)
                if h[2] >= 1 and not fl & 16 and facing > 0 and (facing >= 0.4 * remaining or facing >= 12 * max(h[5], 1)):
                    fl |= 16
                    st[FB_OPP] += 1
                    if k != "fold":
                        st[FB_CONT] += 1
                if k in ("call", "raise") and not fl & 2:
                    st[VPIP] += 1
                    fl |= 2
                if k == "raise" and not fl & 4:
                    st[PFR] += 1
                    fl |= 4
                    if (e.amount or 0) - mybet + h[6].get(sid, 0) >= 0.5 * stk0:
                        st[BIG_RAISE] += 1
                h[4][sid] = fl
            else:
                if facing > 0:
                    st[P_FB_OPP] += 1
                    if k == "fold":
                        st[P_FB_FOLD] += 1
                    elif k == "raise":
                        st[P_FB_RAISE] += 1
                else:
                    st[P_UNB_OPP] += 1
                    if k == "raise":
                        st[P_UNB_BET] += 1
                if k == "raise":
                    st[P_BET] += 1
                elif k == "call":
                    st[P_CALL] += 1
                elif k == "check":
                    st[P_CHECK] += 1
        if k == "call":
            a = e.amount or 0
            bets[sid] = mybet + a
            h[6][sid] = h[6].get(sid, 0) + a
        elif k == "raise":
            a = e.amount or 0
            h[6][sid] = h[6].get(sid, 0) + max(0, a - mybet)
            bets[sid] = a
            if a > h[1]:
                h[1] = a
            h[2] += 1


# ---------------------------------------------------------------- ICM
def icm_value(stacks, i, pay):
    """Malmuth-Harville value of player i. stacks: list (<=0 = busted/excluded)."""
    si = stacks[i]
    if si <= 0:
        return 0.0
    others = [s for j, s in enumerate(stacks) if j != i and s > 0]
    k = min(len(pay), len(others) + 1)
    while k > 0 and pay[k - 1] == 0:
        k -= 1
    if k == 0:
        return 0.0
    T = float(si + sum(others))
    v = pay[0] * si / T
    if k == 1:
        return v
    if k > 3:
        return _icm_rec(si, others, pay, k, T)
    p1 = pay[1]
    p2 = pay[2] if k == 3 else 0.0
    no = len(others)
    for a in range(no):
        sa = others[a]
        pa = sa / T
        Ta = T - sa
        v += pa * p1 * si / Ta
        if p2:
            acc = 0.0
            for b in range(no):
                if b != a:
                    sb = others[b]
                    acc += sb / (Ta - sb)
            v += pa * p2 * si / Ta * acc
    return v


def _icm_rec(si, others, pay, k, T):
    def rec(tot, used, depth):
        v = pay[depth] * si / tot
        if depth + 1 < k:
            for idx, s in enumerate(others):
                if not (used >> idx) & 1:
                    v += s / tot * rec(tot - s, used | (1 << idx), depth + 1)
        return v
    return rec(T, 0, 0)


# ---------------------------------------------------------------- helpers
def kname(k):
    k = getattr(k, "value", k)
    if isinstance(k, str):
        k = k.lower()
        if k.startswith("raise") or k == "bet":
            return "raise"
        return k
    return str(k).lower()


class Ctx:
    pass


def legal_map(state):
    m = {}
    for la in state.legal_actions:
        m[kname(la.kind)] = la
    return m


def finalize(choice, amount, lm):
    """Turn an intended action into a legal SDK Action."""
    if choice == "raise" and "raise" in lm:
        la = lm["raise"]
        lo, hi = int(la.min_amount), int(la.max_amount)
        amt = int(amount)
        if amt >= hi * 0.9 or amt > hi:
            amt = hi
        if amt < lo:
            amt = lo
        if amt > hi:
            amt = hi
        return Action.raise_to(amt)
    if choice == "raise":
        choice = "call"
    if choice == "call":
        if "call" in lm:
            return Action.call()
        if "check" in lm:
            return Action.check()
        return Action.fold()
    if choice == "check":
        if "check" in lm:
            return Action.check()
        return Action.fold() if "fold" in lm else Action.call()
    # fold
    if "check" in lm:
        return Action.check()
    if "fold" in lm:
        return Action.fold()
    return Action.call()


def safe_action(state):
    try:
        lm = legal_map(state)
        if "check" in lm:
            return Action.check()
        if "fold" in lm:
            return Action.fold()
        return Action.call()
    except Exception:
        return Action.fold()


# ---------------------------------------------------------------- context
def build_ctx(state, mem):
    c = Ctx()
    c.me = state.seat
    c.cards = list(state.cards)
    c.board = list(state.board)
    c.pot = state.pot
    c.to_call = state.to_call or 0
    c.blinds = state.blinds
    c.bb = max(1, state.blinds[1]) if state.blinds else 20
    seats = list(state.seats)
    c.seat_order = [s.seat for s in seats]
    c.stack = {}
    c.bet = {}
    c.status = {}
    for s in seats:
        c.stack[s.seat] = s.stack or 0
        c.bet[s.seat] = s.bet or 0
        c.status[s.seat] = kname(s.status)
    c.mystack = c.stack[c.me]
    c.mybet = c.bet[c.me]
    c.alive = [s for s in c.seat_order if c.status[s] != "busted"]
    c.widen_m = WIDEN_M.get(len(c.alive), 1.0)
    c.size_b = size_bucket(len(c.alive))
    c.inhand = [s for s in c.alive if c.status[s] in ("active", "all_in") and s != c.me]
    c.button = state.button
    cfg = state.config
    pay = list(getattr(cfg, "payouts", None) or [50, 30, 20])
    c.pay = pay
    c.start_stack = getattr(cfg, "starting_stack", None) or 2000
    c.time_bank = getattr(state, "time_bank_ms", None)
    c.stats = mem["s"]
    # parse this hand's history
    street = 0
    pf = {}  # seat -> (kind, level)
    pf_raises = 0
    last_pf_raiser = None
    post_aggr = {}
    prev_bets = {}
    prev_calls = {}
    st_actions = {}
    st_aggr = None
    st_raises = 0
    st_bettors = []
    bb_seat = None
    sb_seat = None
    big_blind_amt = 0
    for e in state.history:
        k = kname(e.kind)
        if k == "board":
            street += 1
            for s_, v_ in st_actions.items():
                if "r" in v_:
                    prev_bets[s_] = prev_bets.get(s_, 0) + v_.count("r")
                elif "c" in v_:
                    prev_calls[s_] = prev_calls.get(s_, 0) + 1
            st_actions = {}
            st_aggr = None
            st_raises = 0
            st_bettors = []
        elif k == "blind":
            if (e.amount or 0) >= big_blind_amt:
                if bb_seat is not None:
                    sb_seat = bb_seat
                big_blind_amt = e.amount or 0
                bb_seat = e.seat
            else:
                sb_seat = e.seat
        elif k == "raise":
            if street == 0:
                pf_raises += 1
                pf[e.seat] = ("r", pf_raises, e.amount or 0)
                last_pf_raiser = e.seat
            else:
                st_raises += 1
                st_aggr = e.seat
                post_aggr[e.seat] = post_aggr.get(e.seat, 0) + 1
                st_bettors.append(e.seat)
                st_actions[e.seat] = st_actions.get(e.seat, "") + "r"
        elif k == "call":
            if street > 0:
                st_actions[e.seat] = st_actions.get(e.seat, "") + "c"
            if street == 0 and (e.seat not in pf or pf[e.seat][0] != "r"):
                pf[e.seat] = ("c", pf_raises, 0)
        elif k == "check":
            if street == 0 and e.seat not in pf:
                pf[e.seat] = ("k", 0, 0)
    c.street = len(c.board) and (len(c.board) - 2)  # 0 pre, 1 flop, 2 turn, 3 river
    c.pf = pf
    c.pf_raises = pf_raises
    c.last_pf_raiser = last_pf_raiser
    c.post_aggr = post_aggr
    c.prev_bets = prev_bets
    c.prev_calls = prev_calls
    c.st_aggr = st_aggr
    c.st_raises = st_raises
    c.bb_seat = bb_seat
    c.sb_seat = sb_seat
    return c


# Round-2 data: first-in raise frequency is 0.26 at 6-8 players, 0.37 at 4-5, 0.54 3-handed, 0.71 heads-up.
# Stats are mostly collected full-ring, so widen ranges for the current table size: 1-(1-p)^M.
WIDEN_M = {2: 4.1, 3: 2.6, 4: 1.6, 5: 1.45}


def widen(p, m):
    if m <= 1.0:
        return p
    return 1.0 - (1.0 - clip(p, 0.0, 1.0)) ** m


def opp_range_pct(c, s):
    st = c.stats.get(s)
    M = c.widen_m
    a = c.pf.get(s)
    if a is None:
        return 1.0
    kind, lvl, amt = a
    if kind == "r":
        tot = c.stack.get(s, 0) + c.bet.get(s, 0)
        shove = c.status.get(s) == "all_in" or (tot > 0 and amt >= 0.9 * tot)
        sbb = tot / c.bb
        if lvl <= 1:
            if shove:
                # round-1 field: open-shoves are wide (shown median ~ top 25-45%)
                prior = 0.42 if sbb <= 12 else 0.32 if sbb <= 25 else 0.28
                p = max(rate(st, UNOP_RAISE, UNOP_OPP, prior, 10.0), rate(st, BIG_RAISE, PF_OPP, 0.05))
            else:
                b_ = c.size_b
                if b_ == 0:
                    p = rate(st, UNOP_RAISE, UNOP_OPP, 0.24)
                else:
                    # measured open rate at this table size, prior from the field (widened own full-ring rate)
                    pr_ = 0.5 * OPEN_PRIOR[b_] + 0.5 * widen(rate(st, UNOP_RAISE, UNOP_OPP, 0.24), M)
                    p = rate(st, SZ_RAISE0 + b_, SZ_OPP0 + b_, pr_, 8.0) if st is not None and len(st) >= NSTAT else pr_
        elif lvl == 2:
            if shove:
                prior = 0.3 if sbb <= 12 else 0.16 if sbb <= 25 else 0.05
                p = rate(st, FR_RAISE, FR_OPP, prior, 12.0)
            else:
                p = rate(st, FR_RAISE, FR_OPP, 0.07)
        else:
            p = rate(st, FR_RAISE, FR_OPP, 0.07) * 0.45
        return clip(p, 0.025, 1.0)
    if kind == "c":
        if lvl == 0:
            return clip(rate(st, VPIP, PF_OPP, 0.3), 0.08, 1.0)
        p = 1.0 - rate(st, FR_FOLD, FR_OPP, 0.62)
        if lvl >= 2:
            p *= 0.5
        return clip(p, 0.04, 1.0)
    return 1.0


# ---------------------------------------------------------------- ICM wrappers
def icm_stacks(c):
    """Return (list of seats, base stack list) using stacks behind (chips in pot are 'pending')."""
    seats = c.alive
    return seats, [c.stack[s] for s in seats]


def icm_outcomes(c, outcomes):
    """outcomes: list of (prob, {seat: delta_from_base}) -> expected ICM value for me."""
    seats, base = icm_stacks(c)
    idx = {s: i for i, s in enumerate(seats)}
    n = len(seats)
    pay = c.pay[:n]
    mi = idx[c.me]
    tot = 0.0
    for p, delta in outcomes:
        if p <= 0:
            continue
        st = base[:]
        for s, d in delta.items():
            st[idx[s]] += d
        for j in range(n):
            if st[j] < 0:
                st[j] = 0
        if st[mi] <= 0:
            # busted this hand: place = number of players still alive after (approx)
            others_alive = sum(1 for j in range(n) if j != mi and st[j] > 0)
            v = pay[others_alive] if others_alive < len(pay) else 0.0
        else:
            v = icm_value(st, mi, pay)
        tot += p * v
    return tot


# ---------------------------------------------------------------- preflop
def call_prob_vs_shove(c, s, shove_total):
    """Probability seat s continues vs our all-in to shove_total, and the pct range it continues with."""
    st = c.stats.get(s)
    a = c.pf.get(s)
    if a is not None and a[0] == "r":
        # a raiser continues with roughly its top-X% hands (X ~ 6-9% of all hands), i.e. X/rp of its range
        rp = opp_range_pct(c, s)
        X = widen(0.075 if a[1] <= 1 else 0.06, c.widen_m ** 0.5)
        prior = clip(X / max(rp, 0.01), 0.2, 1.0)
        p = max(prior, rate(st, FB_CONT, FB_OPP, prior, 5.0))
        return p, clip(rp * p, 0.02, 1.0)
    vp = rate(st, VPIP, PF_OPP, 0.3)
    pr = rate(st, PFR, PF_OPP, 0.18)
    base = clip(0.3 * vp + 0.8 * pr, 0.02, 1.0)
    their_total = c.stack[s] + c.bet[s]
    bbs = min(shove_total, their_total) / c.bb
    size_f = clip((12.0 / max(bbs, 1.0)) ** 0.5, 0.55, 1.6)
    prior = clip(base * size_f, 0.02, 1.0)
    p = rate(st, FB_CONT, FB_OPP, prior, 4.0)
    if a is not None and a[0] == "c":
        p = clip(p * 1.3, 0.0, 1.0)
    return p, clip(p, 0.02, 1.0)


def shove_ev(c, hcls):
    """ICM value of shoving all-in now (relative to folding)."""
    my_total = c.mystack + c.mybet
    opps = [s for s in c.inhand if c.status[s] == "active" or c.status[s] == "all_in"]
    pot = c.pot
    fold_v = icm_outcomes(c, [(1.0, {})])
    p_none = 1.0
    outs = []
    callers = []
    for s in opps:
        if c.status[s] == "all_in":
            pc, rp = 1.0, opp_range_pct(c, s)
        elif c.stack[s] <= 0:
            continue
        else:
            pc, rp = call_prob_vs_shove(c, s, my_total)
        callers.append((s, pc, rp))
    for s, pc, rp in callers:
        p_this = p_none * pc
        p_none *= (1 - pc)
        if p_this <= 0:
            continue
        their_total = c.stack[s] + c.bet[s]
        E = min(my_total, their_total)
        dead = pot - c.mybet - c.bet[s]
        eq = eq_top(hcls, rp)
        n_other = sum(1 for o in opps if o != s and c.status[o] != "folded")
        # multiway penalty when more players remain to act / in pot (rough)
        if n_other and len(callers) > 1:
            eq *= 0.97
        # behind-stack accounting: I add (E - mybet) from behind, then receive the pot 2E + dead
        win = {c.me: -(E - c.mybet) + 2 * E + dead, s: -(E - c.bet[s])}
        lose = {c.me: -(E - c.mybet), s: -(E - c.bet[s]) + 2 * E + dead}
        outs.append((p_this * eq, win))
        outs.append((p_this * (1 - eq), lose))
    outs.append((p_none, {c.me: pot}))
    return icm_outcomes(c, outs) - fold_v, p_none


def call_allin_ev(c, eq):
    """ICM value of calling (we or villain are effectively all-in) vs folding."""
    my_total = c.mystack + c.mybet
    agg = None
    best = -1
    for s in c.inhand:
        b = c.bet[s]
        if b > best:
            best, agg = b, s
    their_total = c.stack[agg] + c.bet[agg]
    E = min(my_total, their_total)
    dead = c.pot - c.mybet - c.bet[agg]
    fold_v = icm_outcomes(c, [(1.0, {})])
    win = {c.me: -(E - c.mybet) + 2 * E + dead, agg: -(E - c.bet[agg])}
    lose = {c.me: -(E - c.mybet), agg: -(E - c.bet[agg]) + 2 * E + dead}
    return icm_outcomes(c, [(eq, win), (1 - eq, lose)]) - fold_v


def players_behind_pf(c):
    """Opponents still to act preflop after me (unopened pot logic)."""
    order = c.seat_order
    n = len(order)
    try:
        bi = order.index(c.bb_seat) if c.bb_seat is not None else order.index(c.button)
    except ValueError:
        bi = 0
    seq = [order[(bi + 1 + i) % n] for i in range(n)]
    seq = [s for s in seq if c.status[s] == "active" or s == c.me]
    if c.me not in seq:
        return []
    i = seq.index(c.me)
    return [s for s in seq[i + 1:] if c.pf.get(s) is None and c.status[s] == "active"]


def preflop(c, lm, mem):
    hcls = CLS[(c.cards[0], c.cards[1])]
    bb = c.bb
    my_total = c.mystack + c.mybet
    opp_totals = [c.stack[s] + c.bet[s] for s in c.inhand]
    eff = min(my_total, max(opp_totals) if opp_totals else my_total)
    eff_bb = eff / bb
    to_call = c.to_call
    can_raise = "raise" in lm
    behind = players_behind_pf(c)
    n_in = len(c.inhand)

    # --- unopened (blinds / limpers only)
    if c.pf_raises == 0:
        limpers = [s for s, a in c.pf.items() if a[0] == "c" and s != c.me]
        if not can_raise:
            return ("check", 0) if to_call == 0 else (("call", 0) if eq_top(hcls, 1.0) > 0.5 else ("fold", 0))
        if eff_bb <= 15 or my_total <= 15 * bb:
            ev, _ = shove_ev(c, hcls)
            if ev > 0:
                return ("raise", lm["raise"].max_amount)
            if to_call == 0:
                return ("check", 0)
            # SB complete when cheap and BB is passive
            if to_call <= 0.5 * bb and len(behind) == 1 and eq_top(hcls, 1.0) >= 0.5:
                return ("call", 0)
            return ("fold", 0)
        # open-raise EV (steal model)
        size = bb * (2.3 if len(behind) <= 2 else 2.5) + bb * len(limpers)
        if c.me == c.sb_seat and len(behind) == 1:
            size = bb * 3.0
        if eff_bb < 25:
            size = bb * 2.1 + bb * len(limpers)
        size = max(size, lm["raise"].min_amount)
        risk = size - c.mybet
        f_all = 1.0
        conts = []
        for s in behind:
            st = c.stats.get(s)
            ff = rate(st, FR_FOLD, FR_OPP, 0.62)
            if s == c.bb_seat:
                ff *= 0.9
            f_all *= ff
            conts.append((s, 1 - ff, rate(st, FR_RAISE, FR_OPP, 0.07)))
        for s in limpers:
            st = c.stats.get(s)
            ff = rate(st, FR_FOLD, FR_OPP, 0.62) * 0.8
            f_all *= ff
            conts.append((s, 1 - ff, rate(st, FR_RAISE, FR_OPP, 0.07)))
        ev_raise = f_all * (c.pot - c.mybet)
        p_cont = 1 - f_all
        if p_cont > 0 and conts:
            tot_c = sum(x[1] for x in conts) or 1.0
            ip = len(behind) <= 2 and c.me != c.sb_seat and c.me != c.bb_seat
            R = 0.92 if ip else 0.78
            v = 0.0
            for s, pc, p3 in conts:
                w = pc / tot_c
                rng = clip(pc, 0.05, 1.0)
                eq = eq_top(hcls, rng)
                p3b = clip(p3 / max(pc, 0.05), 0.0, 0.6)
                # called: postflop pot ~ 2*size + dead
                pot_called = 2 * size + (c.pot - c.mybet - c.bet.get(s, 0))
                called_val = eq * R * pot_called - risk
                if eq >= 0.6:
                    threebet_val = eq * (pot_called * 2.5) - (size * 3 - c.mybet)
                else:
                    threebet_val = -risk
                v += w * ((1 - p3b) * called_val + p3b * threebet_val)
            ev_raise += p_cont * v
        if to_call == 0:
            ev_alt = eq_top(hcls, 1.0 if not limpers else 0.4) * 0.8 * (c.pot) - 0.0
            ev_alt = ev_alt * 0.5  # checking realizes less in multiway limped pots
            if ev_raise > ev_alt and ev_raise > 0.03 * bb:
                return ("raise", size)
            return ("check", 0)
        # SB / limp-call option: completing vs folding
        if ev_raise > 0.03 * bb:
            return ("raise", size)
        if c.me == c.sb_seat and to_call <= 0.5 * bb and not limpers and len(behind) == 1:
            if eq_top(hcls, 1.0) >= 0.47:
                return ("call", 0)
        return ("fold", 0)

    # --- facing a raise
    agg = c.last_pf_raiser
    rp = opp_range_pct(c, agg) if agg is not None else 0.2
    eq = eq_top(hcls, rp)
    others = [s for s in c.inhand if s != agg and c.pf.get(s) is not None and c.pf[s][0] in ("c", "r")]
    for s in others:
        eq *= clip(0.25 + 0.75 * eq_top(hcls, opp_range_pct(c, s)), 0.3, 0.92)
    eq = clip(eq, 0.0, 1.0)
    pot_after = c.pot + to_call
    call_commit = to_call / max(1, c.mystack)
    agg_allin = c.status.get(agg) == "all_in" or c.stack.get(agg, 1) == 0
    remaining_after_call = c.mystack - to_call

    # effectively all-in decisions
    if not can_raise or agg_allin or call_commit >= 0.45 or remaining_after_call <= 3 * bb:
        if to_call == 0:
            return ("check", 0)
        if "call" not in lm and "check" not in lm:
            return ("fold", 0)
        ev_call = call_allin_ev(c, eq)
        if can_raise and not agg_allin and len(behind) == 0 and call_commit < 1:
            ev_sh, _ = shove_ev(c, hcls)
            if ev_sh > ev_call and ev_sh > 0:
                return ("raise", lm["raise"].max_amount)
        return ("call", 0) if ev_call > 0 else ("fold", 0)

    # shove-or-fold zone for re-raises
    if eff_bb <= 22 or (c.pf_raises >= 2 and eff_bb <= 45):
        ev_sh, _ = shove_ev(c, hcls)
        ip = len(behind) == 0
        R = 0.9 if ip else 0.75
        ev_call = eq * R * pot_after - to_call
        if c.pf_raises >= 2:
            ev_call -= 0.1 * to_call
        if ev_sh > 0 and ev_sh * 1.0 >= 0:
            # compare in rough chip terms: shove ICM gain is in points; convert chip EV with ICM slope
            slope = icm_slope(c)
            if ev_sh >= ev_call * slope or ev_call <= 0:
                return ("raise", lm["raise"].max_amount)
        if ev_call > 0.05 * bb and eff_bb > 12 and c.pf_raises == 1:
            return ("call", 0)
        return ("fold", 0)

    # deep: 3bet / call / fold
    ip = len(behind) == 0 and c.me != c.sb_seat and c.me != c.bb_seat
    R = 0.92 if ip else 0.78
    implied = 0.0
    if hcls[0] == hcls[1] and RV[hcls[0]] <= RV["9"]:
        implied = 0.11 * min(eff - to_call, 15 * to_call) * 0.5
    elif len(hcls) == 3 and hcls[2] == "s":
        implied = 0.05 * min(eff - to_call, 12 * to_call) * 0.3
    if c.pf_raises >= 2:
        R -= 0.1 * min(2, c.pf_raises - 1)
        implied *= 0.5
    ev_call = eq * R * pot_after - to_call + implied
    last_raise = max(c.bet[s] for s in c.inhand) if c.inhand else c.bb
    premium = hcls in ("AA", "KK", "QQ", "AKs", "AKo") and c.pf_raises == 1
    if eq >= 0.56 or premium or (hcls in ("AA", "KK") and c.pf_raises <= 3):
        # value re-raise
        target = last_raise * (3.0 if ip else 3.6) + sum(c.bet[s] for s in others)
        if target >= 0.4 * my_total:
            ev_sh, _ = shove_ev(c, hcls)
            if ev_sh > 0:
                return ("raise", lm["raise"].max_amount)
            return ("call", 0) if ev_call > 0 else ("fold", 0)
        return ("raise", target)
    if ev_call > 0.02 * bb:
        return ("call", 0)
    if to_call == 0:
        return ("check", 0)
    return ("fold", 0)


def icm_slope(c):
    """ICM points per chip around my current stack (for comparing chip-EV with ICM-EV)."""
    seats, base = icm_stacks(c)
    idx = {s: i for i, s in enumerate(seats)}
    mi = idx[c.me]
    pay = c.pay[:len(seats)]
    d = max(c.bb * 2, 1)
    st = base[:]
    v0 = icm_value(st, mi, pay)
    st[mi] += d
    v1 = icm_value(st, mi, pay)
    return max(1e-9, (v1 - v0) / d)


# ---------------------------------------------------------------- postflop
def equity_vs(c, opps, iters):
    hand = [CARD[c.cards[0]], CARD[c.cards[1]]]
    board = [CARD[x] for x in c.board]
    eqs = {}
    rs = sorted(opps, key=lambda s: opp_range_pct(c, s))[:3]
    for s in rs:
        r = range_obj(opp_range_pct(c, s))
        e = eval7.py_hand_vs_range_monte_carlo(hand, r, board, iters)
        # earlier-street aggression / calls narrow the range
        for _ in range(min(2, c.prev_bets.get(s, 0))):
            e = polar_adj(e, 0.45, 0.45)
        if c.prev_calls.get(s, 0):
            e = polar_adj(e, 0.6, 0.3)
        eqs[s] = e
    if len(opps) > len(rs):
        m = sum(eqs.values()) / len(eqs)
        for s in opps:
            if s not in eqs:
                eqs[s] = min(0.95, m + 0.08)
    return eqs


def polar_adj(e, q, w):
    """Equity vs the top-q part of a range, blended with the whole-range equity."""
    q = clip(q, 0.03, 1.0)
    top = max(0.0, e - (1 - q)) / q
    return w * top + (1 - w) * e


def fold_prob(c, s, bet_frac):
    st = c.stats.get(s)
    base = rate(st, P_FB_FOLD, P_FB_OPP, 0.58, 6.0)
    cont = (1 - base) * clip((0.66 / max(0.15, bet_frac)) ** 0.4, 0.45, 1.8)
    return clip(1 - cont, 0.0, 0.97)


def postflop(c, lm, mem):
    opps = c.inhand
    n = len(opps)
    if n == 0:
        return ("check", 0) if "check" in lm else ("call", 0)
    iters = 300 if n == 1 else 220
    bank = c.time_bank
    if bank is not None and bank < 60:
        iters = iters // 2 if bank >= 20 else iters // 4
    eqs = equity_vs(c, opps, iters)
    street = c.street
    pot = c.pot
    to_call = c.to_call
    S = c.mystack
    can_raise = "raise" in lm
    W_CALL = (0.0, 0.45, 0.6, 0.8)[street]
    W_BET = (0.0, 0.35, 0.5, 0.65)[street]
    # in position?
    order = c.seat_order
    nn = len(order)
    bi = order.index(c.button) if c.button in order else 0
    seq = [order[(bi + 1 + i) % nn] for i in range(nn)]
    live = [s for s in seq if s == c.me or s in opps]
    ip = live and live[-1] == c.me
    R = 1.0 if street == 3 else (0.95 if ip else 0.86)
    active_opps = [s for s in opps if c.status[s] == "active" and c.stack[s] > 0]
    max_opp_total = max([c.stack[s] + c.bet[s] for s in opps] or [0])
    eff_behind = min(S, max([c.stack[s] for s in opps] or [0]) + (max(c.bet[s] for s in opps) - c.mybet if opps else 0))

    # risk aversion (ICM) factor: losing chips hurts more than winning them helps
    lam = icm_lambda(c, min(S + c.mybet, max_opp_total))

    if to_call <= 0:
        E = 1.0
        for s in opps:
            E *= eqs[s]
        ev_check = E * pot * (R if n == 1 else R * 0.95)
        best = ("check", 0, ev_check)
        if can_raise and active_opps:
            la = lm["raise"]
            sizes = [0.33, 0.5, 0.75, 1.0]
            cands = set()
            for f in sizes:
                cands.add(int(max(la.min_amount, min(la.max_amount, c.mybet + f * pot))))
            cands.add(int(la.max_amount))
            for X in sorted(cands):
                B = X - c.mybet
                if B <= 0:
                    continue
                bf = B / max(pot, 1)
                if bf > 1.05 and not (X >= la.max_amount and (bf <= 1.5 or eqs[active_opps[0]] >= 0.85)):
                    continue
                F = 1.0
                callers = []
                for s in active_opps:
                    f = fold_prob(c, s, bf)
                    F *= f
                    callers.append((s, 1 - f))
                # assume a single caller: the most likely one
                callers.sort(key=lambda t: -t[1])
                s1, pc1 = callers[0]
                e1 = eqs[s1]
                for s in opps:
                    if s != s1 and c.status[s] == "all_in":
                        e1 *= eqs[s]
                Ec = polar_adj(e1, pc1, W_CALL + (1 - W_CALL) * (1 - pc1) ** 2)
                allin = X >= la.max_amount or B >= 0.85 * S
                Rc = 1.0 if allin else R
                st1 = c.stats.get(s1)
                rho = 0.0 if allin else clip(rate(st1, P_FB_RAISE, P_FB_OPP, 0.06, 6.0), 0.0, 0.6)
                Er = polar_adj(e1, rho if rho > 0 else 0.05, W_CALL + 0.1)
                B_eff = min(B, c.stack[s1] + c.bet[s1] - c.mybet) if c.stack[s1] + c.bet[s1] > c.mybet else B
                win_called = Ec * Rc * (pot + B_eff)
                lose_called = (1 - Ec * Rc) * B_eff
                lb = lam_for(lam, B_eff, S + c.mybet)
                v_called = win_called - lb * lose_called
                if rho > 0:
                    lr = lam_for(lam, 3 * B, S + c.mybet)
                    v_raised = max(-lb * B, Er * (pot + 4 * B) - lr * (1 - Er) * 3 * B)
                    v_called = (1 - rho) * v_called + rho * v_raised
                ev = F * pot + (1 - F) * v_called
                if ev > best[2]:
                    best = ("raise", X, ev)
        if TRACE is not None:
            TRACE.append(("nobet", c.street, {s: round(eqs[s], 3) for s in eqs}, "rng", {s: round(opp_range_pct(c, s), 3) for s in opps}, "best", best))
        return best[0], best[1]

    # facing a bet
    agg = c.st_aggr
    if agg is None or agg not in opps:
        agg = max(opps, key=lambda s: c.bet[s])
    st = c.stats.get(agg)
    agg_bet = c.bet[agg]
    bet_amt = agg_bet - min(c.mybet, agg_bet)
    pot_before = max(1, pot - bet_amt)
    bf = to_call / max(1, pot - to_call)
    if c.st_raises >= 2 and c.mybet > 0:
        q = rate(st, P_FB_RAISE, P_FB_OPP, 0.1, 6.0)
    elif c.st_raises >= 2:
        q = rate(st, P_FB_RAISE, P_FB_OPP, 0.12, 6.0)
    else:
        q = rate(st, P_UNB_BET, P_UNB_OPP, 0.38, 6.0)
    q = clip(q * clip((0.6 / max(0.1, bf)) ** 0.3, 0.6, 1.6), 0.04, 1.0)
    Ea = polar_adj(eqs[agg], q, W_BET)
    E = Ea
    for s in opps:
        if s != agg:
            E *= eqs[s] if c.bet[s] >= agg_bet or c.status[s] == "all_in" else (eqs[s] ** 0.6)
    call_amt = min(to_call, S)
    allin_call = call_amt >= S or c.status.get(agg) == "all_in" or c.stack.get(agg, 0) == 0
    Rc = 1.0 if allin_call else R
    ev_call = E * Rc * (pot + call_amt) - lam_for(lam, call_amt, S + c.mybet) * (1 - E * Rc) * call_amt
    ev_call -= (1 - E * Rc) * 0.0
    # big all-in calls: ICM directly
    if call_amt >= 0.5 * S and n == 1:
        icm_ev = call_allin_ev(c, E)
        slope = icm_slope(c)
        ev_call = icm_ev / slope
    best = ("fold", 0, 0.0)
    if ev_call > best[2]:
        best = ("call", 0, ev_call)
    if TRACE is not None:
        TRACE.append(("facebet", c.street, {s: round(eqs[s], 3) for s in eqs}, "rng", {s: round(opp_range_pct(c, s), 3) for s in opps}, "q", round(q, 3), "Ea", round(Ea, 3), "E", round(E, 3), "lam", round(lam, 2), "evcall", round(ev_call, 1)))
    if can_raise and not allin_call and active_opps:
        la = lm["raise"]
        cands = set()
        for mult in (2.6, 3.5):
            cands.add(int(max(la.min_amount, min(la.max_amount, agg_bet * mult + (pot - agg_bet - c.mybet) * 0.3))))
        cands.add(int(la.max_amount))
        fr_base = rate(st, P_FB_FOLD, P_FB_OPP, 0.54, 6.0) * 0.75
        fr_base *= clip(opp_range_pct(c, agg) / 0.3, 0.25, 1.0)
        fr_base *= 0.7 ** min(2, c.prev_bets.get(agg, 0))
        reliable_folder = st is not None and st[P_FB_OPP] >= 6 and fr_base >= 0.45
        for X in sorted(cands):
            A = X - c.mybet
            if A <= to_call:
                continue
            allin = X >= la.max_amount
            if E < 0.4 and not reliable_folder:
                continue
            if allin and A > 1.3 * (pot + to_call) and Ea < 0.8:
                continue
            fr = clip(fr_base * (1.15 if allin else 1.0), 0.0, 0.9)
            Ecc = polar_adj(E, 1 - fr, W_CALL + 0.15)
            their_add = min(X, c.stack[agg] + agg_bet) - agg_bet
            Rr = 1.0 if allin else R
            pot_final = pot + A + their_add
            win = Ecc * Rr * pot_final
            lose = (1 - Ecc * Rr) * A
            v_cont = win - lam_for(lam, A, S + c.mybet) * lose
            ev = fr * pot + (1 - fr) * v_cont
            if ev > best[2]:
                best = ("raise", X, ev)
    if TRACE is not None:
        TRACE.append(("facebet-best", best))
    return best[0], best[1]


def lam_for(lam, risk, stack):
    """ICM risk factor for risking `risk` of `stack`: full lambda only for all-in sized risks."""
    if stack <= 0:
        return lam
    return 1.0 + (lam - 1.0) * clip(risk / stack, 0.0, 1.0)


def icm_lambda(c, risk):
    """Ratio of ICM loss to ICM gain for losing/winning `risk` chips (>=1)."""
    try:
        seats, base = icm_stacks(c)
        idx = {s: i for i, s in enumerate(seats)}
        mi = idx[c.me]
        pay = c.pay[:len(seats)]
        if len(seats) <= 1:
            return 1.0
        r = max(1, min(risk, base[mi] + c.mybet))
        v0 = icm_value(base, mi, pay)
        up = base[:]
        up[mi] += r
        # take chips from the others proportionally
        tot_o = sum(base) - base[mi]
        for j in range(len(base)):
            if j != mi and tot_o > 0:
                up[j] -= r * base[j] / tot_o
        dn = base[:]
        dn[mi] = max(0, dn[mi] - r)
        for j in range(len(base)):
            if j != mi and tot_o > 0:
                dn[j] += r * base[j] / tot_o
        vu = icm_value(up, mi, pay)
        if dn[mi] <= 0:
            others_alive = len(seats) - 1
            vd = pay[others_alive] if others_alive < len(pay) else 0.0
        else:
            vd = icm_value(dn, mi, pay)
        g = vu - v0
        l = v0 - vd
        if g <= 1e-9:
            return 3.0
        return clip(l / g, 1.0, 3.0)
    except Exception:
        return 1.2


# ---------------------------------------------------------------- agent
def load_mem(memory, start_stack):
    if memory:
        try:
            m = marshal.loads(memory)
            if isinstance(m, dict) and m.get("v") == 1:
                return m
        except Exception:
            pass
    return {"v": 1, "s": {}, "h": [0, 0, 0, {}, {}, 0, {}, {}]}


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        try:
            cfg = state.config
            start_stack = getattr(cfg, "starting_stack", None) or 2000
            mem = load_mem(memory, start_stack)
            try:
                update_stats(mem, state.events or [], state.seat, start_stack)
            except Exception:
                if DEBUG:
                    raise
            lm = legal_map(state)
            c = build_ctx(state, mem)
            if not c.board:
                choice, amt = preflop(c, lm, mem)
            else:
                choice, amt = postflop(c, lm, mem)
            act = finalize(choice, amt, lm)
            try:
                out = marshal.dumps(mem)
            except Exception:
                out = memory
            return act, out
        except Exception:
            if DEBUG:
                raise
            return safe_action(state), memory


gc.collect()
try:
    gc.freeze()
except Exception:
    pass
