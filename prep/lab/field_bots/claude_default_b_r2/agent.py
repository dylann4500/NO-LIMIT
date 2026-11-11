"""claude_default_b (round 2): equity + ICM + opponent-model bot for 8-max NLHE sit-and-go tables.

Design (see NOTES.md):
  * Preflop: precomputed 169-class equity-vs-range matrix (tables.json). Villain ranges come from per-seat
    stats tracked in `memory` (open %, 3-bet %, VPIP, calls vs all-in). Short-stack and all-in spots use an
    explicit EV model over every possible caller, scored with a chips/ICM blend utility.
  * Postflop: eval7 Monte Carlo vs the villain's preflop range, filtered on the current board by how often
    that villain bets/raises/calls (frequency-based range narrowing). Bets are chosen by an EV model with a
    per-opponent fold-to-bet estimate (value sizing and bluffing fall out of the same formula).
  * Safety: every path ends in `_legal()`, which only returns offered kinds and in-range integer totals.
    Any exception falls back to check/fold *inside* act(), so the platform never sees a failure.
"""
import json
import math
import os
import random
import time

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "tables.json")) as _f:
    _T = json.load(_f)
CLASSES = _T["classes"]
CL_IDX = {c: i for i, c in enumerate(CLASSES)}
CUM = _T["cum"]
GRID = _T["grid"]
EQ = _T["eq"]
ORDER = _T["order"]

RANKS = "23456789TJQKA"
RV = {r: i for i, r in enumerate(RANKS)}
SUITS = "shdc"
CARD = {r + s: eval7.Card(r + s) for r in RANKS for s in SUITS}
EVAL = eval7.evaluate
MC = eval7.py_hand_vs_range_monte_carlo
_rng = random.Random()


def _norm_card(c):
    c = str(c).strip()
    if len(c) == 3 and c[:2] == "10":
        c = "T" + c[2]
    return c[0].upper() + c[1].lower()


def class_of(c1, c2):
    r1, r2 = c1[0], c2[0]
    if RV[r1] < RV[r2]:
        r1, r2, c1, c2 = r2, r1, c2, c1
    if r1 == r2:
        return CL_IDX[r1 + r2]
    return CL_IDX[r1 + r2 + ("s" if c1[1] == c2[1] else "o")]


def eq_pre(ci, width):
    row = EQ[ci]
    if width <= GRID[0]:
        return row[0]
    if width >= 1.0:
        return row[-1]
    for g in range(1, len(GRID)):
        if width <= GRID[g]:
            a, b = GRID[g - 1], GRID[g]
            t = (width - a) / (b - a)
            return row[g - 1] + (row[g] - row[g - 1]) * t
    return row[-1]


# ---- postflop villain range lists: top-w% of combos by preflop order, shuffled once at import ----
def _class_combos(name):
    a, b = name[0], name[1]
    out = []
    if len(name) == 2:
        for x in range(4):
            for y in range(x + 1, 4):
                out.append((a + SUITS[x], b + SUITS[y]))
    elif name[2] == "s":
        for x in range(4):
            out.append((a + SUITS[x], b + SUITS[x]))
    else:
        for x in range(4):
            for y in range(4):
                if x != y:
                    out.append((a + SUITS[x], b + SUITS[y]))
    return out


PW = [0.04, 0.07, 0.10, 0.14, 0.19, 0.25, 0.32, 0.40, 0.50, 0.62, 0.78, 1.0]
PRANGES = []
_r0 = random.Random(12345)
for _w in PW:
    _lst, _n = [], int(round(_w * 1326))
    for _ci in ORDER:
        for (_x, _y) in _class_combos(CLASSES[_ci]):
            _lst.append((_x, _y, [CARD[_x], CARD[_y]], ((CARD[_x], CARD[_y]), 1.0)))
        if len(_lst) >= _n:
            break
    _r0.shuffle(_lst)
    PRANGES.append(_lst)


def prange_for(w):
    for i, x in enumerate(PW):
        if w <= x * 1.12:
            return PRANGES[i]
    return PRANGES[-1]


# ---- tunables (A/B tested locally, see NOTES.md) ----
FTB_PRIOR = 0.48      # prior fold-to-postflop-bet rate of an unknown opponent (round-1 field: 0.49 vs small bets)
STREET_K = {1: 1.0, 2: 0.88, 3: 0.78}  # later-street aggression is stronger (round-1 showdowns)
OPEN_SCALE = 1.0      # multiplier on unopened raising ranges
PUSH_BB = 14          # effective stack (bb) at or below which unopened pots are push/fold
LAM_EARLY = 0.5       # ICM weight in the utility with 7-8 players left (rest is chip share)

# ---- per-seat statistics kept in memory ----
# index: 0 hands, 1 vpip, 2 pfr, 3 open_opp, 4 opens, 5 facing_raise, 6 threebets, 7 calls_vs_raise,
#        8 post_bet_opp, 9 post_bets, 10 post_faced, 11 post_folds, 12 post_raises, 13 faced_allin, 14 called_allin
NST = 15


def _stat(st, num, den, prior, k):
    if st is None:
        return prior
    return (st[num] + prior * k) / (st[den] + k)


def _kind(k):
    v = getattr(k, "value", k)
    s = str(v).lower()
    if "." in s:
        s = s.rsplit(".", 1)[-1]
    return s


def process_events(mem, events, cfg_stack):
    S = mem.setdefault("s", {})
    P = mem.setdefault("p", {"st": 0, "cb": 0, "b": {}, "c": {}, "nr": 0, "a": [], "v": [], "r": [], "k": {}})
    for e in events:
        k = _kind(e.kind)
        s = e.seat
        ks = str(s)
        if k == "hand":
            P["st"], P["cb"], P["b"], P["c"], P["nr"], P["a"], P["v"], P["r"] = 0, 0, {}, {}, 0, [], [], []
            continue
        if k == "board":
            P["st"] += 1
            P["cb"], P["b"] = 0, {}
            continue
        if k == "stack":
            P["k"][ks] = e.amount or 0
            continue
        if k == "ante":
            P["c"][ks] = P["c"].get(ks, 0) + (e.amount or 0)
            continue
        if k == "blind":
            amt = e.amount or 0
            P["b"][ks] = P["b"].get(ks, 0) + amt
            P["c"][ks] = P["c"].get(ks, 0) + amt
            if P["b"][ks] > P["cb"]:
                P["cb"] = P["b"][ks]
            continue
        if k not in ("fold", "check", "call", "raise") or s is None:
            continue
        st = S.get(ks)
        if st is None:
            st = [0] * NST
            S[ks] = st
        mybet = P["b"].get(ks, 0)
        facing = P["cb"] - mybet
        remaining = P["k"].get(ks, cfg_stack) - P["c"].get(ks, 0)
        if facing > 0 and facing >= remaining > 0:
            st[13] += 1
            if k == "call":
                st[14] += 1
        if P["st"] == 0:
            if ks not in P["a"]:
                P["a"].append(ks)
                st[0] += 1
            if P["nr"] == 0:
                if k != "check":
                    st[3] += 1
                    if k == "raise":
                        st[4] += 1
            elif facing > 0:
                st[5] += 1
                if k == "raise":
                    st[6] += 1
                elif k == "call":
                    st[7] += 1
            if k in ("call", "raise") and ks not in P["v"]:
                P["v"].append(ks)
                st[1] += 1
            if k == "raise" and ks not in P["r"]:
                P["r"].append(ks)
                st[2] += 1
        else:
            if facing <= 0:
                st[8] += 1
                if k == "raise":
                    st[9] += 1
            else:
                st[10] += 1
                if k == "fold":
                    st[11] += 1
                elif k == "raise":
                    st[12] += 1
        if k == "call":
            amt = e.amount or 0
            P["b"][ks] = mybet + amt
            P["c"][ks] = P["c"].get(ks, 0) + amt
        elif k == "raise":
            amt = e.amount or 0
            delta = max(0, amt - mybet)
            P["b"][ks] = amt
            P["c"][ks] = P["c"].get(ks, 0) + delta
            if amt > P["cb"]:
                P["cb"] = amt
            if P["st"] == 0:
                P["nr"] += 1


# ---- ICM ----
def icm_me(stacks, me, payouts):
    """Malmuth-Harville expected payout of index `me` (O(n^2) per paid place, up to 3 places exact)."""
    n = len(stacks)
    pays = [p for p in payouts[:n]]
    while pays and pays[-1] == 0:
        pays.pop()
    if stacks[me] <= 0:
        alive = sum(1 for x in stacks if x > 0)
        place = alive + 1
        return payouts[place - 1] if place - 1 < len(payouts) else 0.0
    T = float(sum(stacks))
    if T <= 0:
        return 0.0
    sm = stacks[me]
    res = 0.0
    if len(pays) >= 1:
        res += pays[0] * sm / T
    if len(pays) >= 2:
        p2 = 0.0
        p3 = 0.0
        for j in range(n):
            sj = stacks[j]
            if j == me or sj <= 0:
                continue
            pj = sj / T
            rem = T - sj
            p2 += pj * sm / rem
            if len(pays) >= 3:
                for k in range(n):
                    sk = stacks[k]
                    if k == me or k == j or sk <= 0:
                        continue
                    rem2 = rem - sk
                    if rem2 > 0:
                        p3 += pj * (sk / rem) * (sm / rem2)
        res += pays[1] * p2
        if len(pays) >= 3:
            res += pays[2] * p3
            if len(pays) >= 4:
                # beyond 3 paid places: approximate remaining value by chip share
                rest = sum(pays[3:])
                res += rest * sm / T
    return res


class Ctx(object):
    pass


def _legal_map(state):
    L = {}
    for a in state.legal_actions:
        L[_kind(a.kind)] = (int(a.min_amount or 0), int(a.max_amount or 0))
    return L


def _legal(c, kind, amount=None):
    """Map a desired action to a guaranteed-legal one."""
    L = c.legal
    if kind == "raise":
        if "raise" in L:
            lo, hi = L["raise"]
            a = int(amount if amount is not None else lo)
            if a >= hi * 0.9 or a >= hi:
                a = hi
            if a < lo:
                a = lo
            if a > hi:
                a = hi
            if lo <= a <= hi:
                return Action.raise_to(int(a))
        kind = "call"
    if kind == "call":
        if "call" in L:
            return Action.call()
        if "check" in L:
            return Action.check()
        kind = "fold"
    if kind == "check":
        if "check" in L:
            return Action.check()
        if "fold" in L:
            return Action.fold()
        if "call" in L:
            return Action.call()
    if kind == "fold":
        if "check" in L:
            return Action.check()
        if "fold" in L:
            return Action.fold()
        if "call" in L:
            return Action.call()
    if "check" in L:
        return Action.check()
    if "fold" in L:
        return Action.fold()
    if "call" in L:
        return Action.call()
    lo, hi = L.get("raise", (0, 0))
    return Action.raise_to(int(lo))


def build_ctx(state, mem):
    c = Ctx()
    cfg = state.config
    c.cfg = cfg
    c.me = state.seat
    c.legal = _legal_map(state)
    c.cards = [_norm_card(x) for x in state.cards]
    c.board = [_norm_card(x) for x in (state.board or [])]
    c.pot = int(state.pot or 0)
    c.to_call = int(state.to_call or 0)
    bl = state.blinds or [10, 20]
    c.sb, c.bb = int(bl[0]), int(bl[1]) if len(bl) > 1 else int(bl[0]) * 2
    if c.bb <= 0:
        c.bb = 1
    c.seats = {}
    for s in state.seats:
        c.seats[s.seat] = s
    c.ring = sorted(s.seat for s in state.seats if _kind(s.status) != "busted")
    c.button = state.button
    mys = c.seats[c.me]
    c.stack = int(mys.stack)
    c.bet = int(mys.bet)
    c.total = c.stack + c.bet
    c.opps = [s for s in state.seats if s.seat != c.me and _kind(s.status) in ("active", "all_in")]
    c.live = [s for s in c.opps if _kind(s.status) == "active" and s.stack > 0]
    c.payouts = list(getattr(cfg, "payouts", None) or [50, 30, 20, 0, 0, 0, 0, 0])
    c.start_stack = int(getattr(cfg, "starting_stack", None) or 2000)
    c.stats = mem.get("s", {})
    c.players_left = len(c.ring)
    # current-hand history
    c.pre_raises, c.pre_calls, c.blind_posts = [], [], []
    c.post_aggr, c.post_calls = {}, {}
    c.street_raises = []
    c.post_actions = []  # (seat, street, 'bet'|'raise', size as fraction of the pot before the action)
    street = 0
    hpot = 0
    sbets = {}
    cbet = 0
    for e in (state.history or []):
        k = _kind(e.kind)
        amt = e.amount or 0
        if k == "board":
            street += 1
            c.street_raises = []
            sbets, cbet = {}, 0
        elif k == "blind":
            c.blind_posts.append((e.seat, amt))
            hpot += amt
            sbets[e.seat] = sbets.get(e.seat, 0) + amt
            cbet = max(cbet, sbets[e.seat])
        elif k == "ante":
            hpot += amt
        elif k == "raise":
            prev = sbets.get(e.seat, 0)
            if street == 0:
                c.pre_raises.append((e.seat, amt))
            else:
                c.post_aggr[e.seat] = c.post_aggr.get(e.seat, 0) + 1
                c.street_raises.append((e.seat, amt))
                typ = "raise" if cbet > 0 else "bet"
                c.post_actions.append((e.seat, street, typ, (amt - prev) / float(max(1, hpot))))
            hpot += max(0, amt - prev)
            sbets[e.seat] = amt
            cbet = max(cbet, amt)
        elif k == "call":
            hpot += amt
            sbets[e.seat] = sbets.get(e.seat, 0) + amt
            if street == 0:
                c.pre_calls.append(e.seat)
            else:
                c.post_calls[e.seat] = c.post_calls.get(e.seat, 0) + 1
    c.sb_seat = c.bb_seat = None
    if c.blind_posts:
        c.bb_seat = c.blind_posts[-1][0] if len(c.blind_posts) >= 2 else c.blind_posts[0][0]
        if len(c.blind_posts) >= 2:
            c.sb_seat = c.blind_posts[0][0]
    return c


def _ring_after(c, start, end):
    """Seats strictly after `start` up to and including `end`, in table order."""
    r = c.ring
    if start not in r or end not in r:
        return []
    out = []
    i = r.index(start)
    n = len(r)
    for _ in range(n):
        i = (i + 1) % n
        out.append(r[i])
        if r[i] == end:
            break
    return out


def _st(c, seat):
    return c.stats.get(str(seat))


def villain_open_w(c, seat):
    return min(1.0, max(0.03, _stat(_st(c, seat), 4, 3, 0.20, 6)))


def villain_3b_w(c, seat):
    return min(1.0, max(0.02, _stat(_st(c, seat), 6, 5, 0.07, 6)))


def villain_vpip(c, seat):
    return min(1.0, max(0.05, _stat(_st(c, seat), 1, 0, 0.30, 6)))


def villain_ftb(c, seat):
    return min(0.97, max(0.02, _stat(_st(c, seat), 11, 10, FTB_PRIOR, 6)))


def villain_betfreq(c, seat):
    return min(1.0, max(0.05, _stat(_st(c, seat), 9, 8, 0.40, 6)))


def villain_raisefreq(c, seat):
    return min(1.0, max(0.02, _stat(_st(c, seat), 12, 10, 0.06, 6)))


def villain_pre_width(c, seat):
    """Preflop range width for an opponent still in the hand, from this hand's preflop actions."""
    idx = [i for i, (s, _) in enumerate(c.pre_raises) if s == seat]
    if idx:
        last = idx[-1]
        pf = 1.0
        if last == 0 and c.bb_seat is not None:
            nb = len(_ring_after(c, seat, c.bb_seat)) if seat != c.bb_seat else 1
            pf = POSF.get(nb, 0.7)
        if last == 0:
            w = min(1.0, villain_open_w(c, seat) * pf)
        elif last == 1:
            w = villain_3b_w(c, seat)
        else:
            w3 = villain_3b_w(c, seat)
            w = w3 if w3 > 0.4 else w3 * 0.55
        so = c.seats.get(seat)
        if so is not None and _kind(so.status) == "all_in":
            tot_bb = (c.pre_raises[last][1]) / float(c.bb)
            w = max(w, min(1.0, shove_width(tot_bb) * pf))
        return max(0.02, w)
    if seat in c.pre_calls:
        if c.pre_raises:
            return villain_vpip(c, seat)
        return min(1.0, villain_vpip(c, seat) * 1.3 + 0.1)
    return 1.0


POSF = {0: 2.0, 1: 2.0, 2: 1.5, 3: 1.2, 4: 1.0, 5: 0.85, 6: 0.75, 7: 0.7}


def shove_width(bb):
    pts = [(1.5, 0.85), (3, 0.6), (5, 0.42), (8, 0.3), (10, 0.24), (13, 0.18), (16, 0.13), (20, 0.09), (30, 0.05)]
    if bb <= pts[0][0]:
        return pts[0][1]
    for i in range(1, len(pts)):
        if bb <= pts[i][0]:
            a, wa = pts[i - 1]
            b, wb = pts[i]
            return wa + (wb - wa) * (bb - a) / (b - a)
    return 0.04


def utility_factory(c):
    """Return U(final_stack_by_seat dict) blending ICM points and chip share."""
    seats = c.ring
    n = len(seats)
    pays = c.payouts
    paysum = float(sum(pays[:n]))
    lam = 1.0 if n <= 4 else (0.8 if n == 5 else (max(0.65, LAM_EARLY) if n == 6 else LAM_EARLY))
    me_i = seats.index(c.me) if c.me in seats else 0

    def U(final):
        st = [max(0, final.get(s, 0)) for s in seats]
        tot = float(sum(st)) or 1.0
        icm = icm_me(st, me_i, pays)
        if lam >= 1.0:
            return icm
        return lam * icm + (1 - lam) * paysum * st[me_i] / tot
    return U


def base_stacks(c):
    return {s: int(c.seats[s].stack) for s in c.ring}


# CALLQ[g][i]: fraction of all hands whose equity vs the top GRID[g] range is >= NEEDS[i]
# (how often a sound caller continues vs a shove they believe comes from a top-GRID[g] range).
NEEDS = [0.20 + 0.01 * i for i in range(46)]
_NCOMB = [6 if len(n) == 2 else (4 if n[2] == "s" else 12) for n in CLASSES]
CALLQ = []
for _g in range(len(GRID)):
    _row = []
    for _need in NEEDS:
        _row.append(sum(_NCOMB[_ci] for _ci in range(169) if EQ[_ci][_g] >= _need) / 1326.0)
    CALLQ.append(_row)


def call_fraction(need, perceived_w):
    g = 0
    while g < len(GRID) - 1 and GRID[g + 1] <= perceived_w:
        g += 1
    i = int(round((need - 0.20) * 100))
    if i < 0:
        i = 0
    if i >= len(NEEDS):
        i = len(NEEDS) - 1
    return min(1.0, max(0.02, CALLQ[g][i]))


def allin_ev(c, eq_fn, my_add, fold_winner, check_share=0.0, perceived_w=0.3):
    """EV (utility) of putting `my_add` more chips in as an all-in-ish bet vs folding.
    eq_fn(width) -> my equity vs a caller range of that width. Returns (u_shove, u_fold)."""
    U = utility_factory(c)
    base = base_stacks(c)
    pot = c.pot
    my_total_commit = c.bet + my_add
    npaid = sum(1 for p in c.payouts if p > 0)
    bubble_prem = 0.03 if c.players_left <= npaid + 1 else 0.0
    # fold
    f = dict(base)
    mine = int(pot * check_share)
    f[c.me] = f[c.me] + mine
    if fold_winner is not None and fold_winner in f:
        f[fold_winner] = f[fold_winner] + pot - mine
    u_fold = U(f)
    # opponents that could call: everyone still active (not all-in already treated as callers too)
    p_none = 1.0
    u_sh = 0.0
    for s in c.opps:
        so = c.seats[s.seat]
        sbet, sstack = int(so.bet), int(so.stack)
        need_add = max(0, min(sstack, my_total_commit - sbet))
        if need_add <= 0 and _kind(so.status) != "all_in":
            continue
        w = villain_pre_width(c, s.seat) if not c.board else 0.6
        if _kind(so.status) == "all_in":
            pc = 1.0  # already all-in: it is a showdown against them
            cw = w
        else:
            need = need_add / float(pot + my_add + need_add) + bubble_prem
            q = call_fraction(need, perceived_w)
            st = _st(c, s.seat)
            pc = min(1.0, q / w) if w > 0 else q
            q = min(q, w)
            # observed behaviour vs all-ins overrides the model gradually
            if st is not None and st[13] > 0:
                obs = st[14] / float(st[13])
                kk = 3.0
                pc = (st[14] + pc * kk) / (st[13] + kk) if obs > pc else (pc * kk + obs * st[13]) / (kk + st[13])
            pc = min(1.0, max(0.0, pc))
            cw = max(0.02, w * q)
        prob = p_none * pc
        if prob > 1e-6:
            e = eq_fn(cw)
            x = my_add
            contested_extra = need_add
            excess = max(0, my_total_commit - (sbet + sstack))  # my chips the caller cannot cover
            win = dict(base)
            win[c.me] = base[c.me] - x + pot + x + contested_extra
            win[s.seat] = base[s.seat] - contested_extra
            lose = dict(base)
            lose[c.me] = base[c.me] - x + excess
            lose[s.seat] = base[s.seat] - contested_extra + pot + x + contested_extra - excess
            u_sh += prob * (e * U(win) + (1 - e) * U(lose))
        p_none *= (1 - pc)
        if p_none < 1e-4:
            break
    w_all = dict(base)
    w_all[c.me] = base[c.me] + pot
    u_sh += p_none * U(w_all)
    return u_sh, u_fold


def call_allin_ev(c, e, villain_seat):
    """Utility of calling (for at most our stack) vs folding, heads-up vs villain, equity e."""
    U = utility_factory(c)
    base = base_stacks(c)
    pot = c.pot
    x = min(c.to_call, c.stack)
    vbet = int(c.seats[villain_seat].bet) if villain_seat in c.seats else c.bet + c.to_call
    excess = max(0, vbet - (c.bet + x))
    f = dict(base)
    if villain_seat in f:
        f[villain_seat] += pot
    win = dict(base)
    win[c.me] = base[c.me] + pot - excess
    if villain_seat in win:
        win[villain_seat] = base[villain_seat] + excess
    lose = dict(base)
    lose[c.me] = base[c.me] - x
    if villain_seat in lose:
        lose[villain_seat] = base[villain_seat] + pot + x
    return e * U(win) + (1 - e) * U(lose), U(f)


# ---------------- preflop ----------------
OPEN_W = {1: 0.50, 2: 0.42, 3: 0.30, 4: 0.23, 5: 0.19, 6: 0.16, 7: 0.14}


def eff_stack(c):
    others = [int(s.stack) + int(s.bet) for s in c.opps]
    if not others:
        return c.total
    return min(c.total, max(others))


def preflop(c):
    ci = class_of(c.cards[0], c.cards[1])
    pct = CUM[ci]
    bb = c.bb
    eff = eff_stack(c)
    eff_bb = eff / float(bb)
    nraise = len(c.pre_raises)
    can_check = "check" in c.legal
    pos_ip = c.button == c.me

    if nraise == 0:
        limpers = [s for s in c.pre_calls if s != c.me]
        n_beh_seats = []
        if c.bb_seat is not None and c.me != c.bb_seat:
            n_beh_seats = [s for s in _ring_after(c, c.me, c.bb_seat)
                           if s in c.seats and _kind(c.seats[s].status) == "active" and c.seats[s].stack > 0]
        n_beh = len(n_beh_seats)
        # push/fold zone
        if eff_bb <= PUSH_BB or (eff_bb <= PUSH_BB + 4 and not limpers and n_beh <= 2):
            fold_winner = c.bb_seat if c.bb_seat != c.me else (limpers[0] if limpers else None)
            share = 0.0
            if can_check:
                share = 0.8 * eq_pre(ci, 0.6) ** (1 + 0.75 * max(0, len(limpers) - 1))
            pw = min(1.0, shove_width(eff_bb) * {1: 2.2, 2: 1.5, 3: 1.2}.get(n_beh, 1.0))
            u_sh, u_f = allin_ev(c, lambda w: eq_pre(ci, w), c.stack, fold_winner, share, pw)
            if u_sh > u_f:
                return _legal(c, "raise", c.total)
            if can_check:
                return _legal(c, "check")
            # cheap completes in SB with decent hand
            return _legal(c, "fold")
        if c.me == c.bb_seat and can_check:
            # option: raise strong hands vs limpers
            if pct <= (0.12 if limpers else 0.3):
                return _legal(c, "raise", int(bb * (3.5 + len(limpers))))
            return _legal(c, "check")
        w = OPEN_W.get(n_beh, 0.13) * OPEN_SCALE
        # fold-to-open of players behind widens steals
        if n_beh_seats:
            pf = 1.0
            for s in n_beh_seats:
                st = _st(c, s)
                fv = 1.0 - _stat(st, 6, 5, 0.07, 6) - _stat(st, 7, 5, 0.18, 6)
                pf *= min(0.98, max(0.0, fv))
            w = w * (0.75 + 0.6 * pf)
            if pf > 0.55 and n_beh <= 3:
                w = max(w, pf)
        if limpers:
            if pct <= w * 0.55:
                return _legal(c, "raise", int(bb * (3 + len(limpers))))
            if pct <= min(0.45, w * 1.1) and eff_bb > 25 and c.to_call <= bb:
                return _legal(c, "call")
            return _legal(c, "fold")
        if pct <= w:
            size = 2.2 if n_beh >= 3 else (2.5 if n_beh == 2 else 3.0)
            if eff_bb < 25:
                size = 2.1
            return _legal(c, "raise", int(bb * size))
        if c.me == c.sb_seat and n_beh == 1 and pct <= 0.62 and eff_bb > 20:
            return _legal(c, "call")
        return _legal(c, "fold")

    # ---- facing a raise ----
    vill, vto = c.pre_raises[-1]
    w_v = villain_pre_width(c, vill)
    others_in = set(s for s, _ in c.pre_raises if s != vill) | set(s for s in c.pre_calls if s != c.me and s != vill)
    others_in = [s for s in others_in if s in c.seats and _kind(c.seats[s].status) in ("active", "all_in")]
    e_v = eq_pre(ci, w_v)
    e = e_v ** (1 + 0.7 * len(others_in)) if others_in else e_v
    odds = c.to_call / float(c.pot + c.to_call) if c.to_call > 0 else 0.0
    vso = c.seats.get(vill)
    vill_allin = vso is not None and (_kind(vso.status) == "all_in" or int(vso.stack) == 0)
    commit = c.to_call >= 0.4 * c.stack or vill_allin or eff_bb <= 25

    if commit:
        # options: fold, shove, (call if villain all-in / we're covered)
        if vill_allin or "raise" not in c.legal:
            if not others_in and vso is not None:
                u_c, u_f = call_allin_ev(c, e, vill)
            else:
                u_c = e * 1.0
                u_f = odds
            if u_c > u_f:
                return _legal(c, "call")
            return _legal(c, "fold")
        pw = min(1.0, shove_width(eff_bb) * 0.7)
        u_sh, u_f = allin_ev(c, lambda w: eq_pre(ci, w) ** (1 + 0.7 * len(others_in)), c.stack, vill, 0.0, pw)
        if u_sh > u_f:
            return _legal(c, "raise", c.total)
        # deep enough to flat? only if not really committed
        if c.to_call < 0.25 * c.stack and e * 0.85 >= odds and pct <= 0.5:
            return _legal(c, "call")
        return _legal(c, "fold")

    # deep: value re-raise / call / fold
    th = 0.57 + 0.03 * (nraise - 1)
    if e_v >= th and e >= 0.5:
        mult = 3.0 if pos_ip else 3.5
        tgt = int(vto * mult + bb * len(others_in))
        if tgt >= 0.35 * c.total:
            tgt = c.total
        return _legal(c, "raise", tgt)
    # occasional light 3-bet vs folders
    if nraise == 1 and not others_in and eff_bb > 40 and 0.08 < pct < 0.22:
        st = _st(c, vill)
        fold_vs = 1.0 - _stat(st, 6, 5, 0.07, 6) - _stat(st, 7, 5, 0.18, 6)
        if fold_vs > 0.55 and _rng.random() < 0.35:
            return _legal(c, "raise", int(vto * 3.2))
    behind = 0
    if c.bb_seat is not None and c.me != c.bb_seat:
        behind = sum(1 for s in _ring_after(c, c.me, c.bb_seat)
                     if s in c.seats and _kind(c.seats[s].status) == "active" and s != vill)
    R = (0.86 if pos_ip else 0.72) - 0.04 * behind
    if eff / float(max(1, c.to_call)) >= 15 and (CLASSES[ci][0] == CLASSES[ci][1] or CLASSES[ci].endswith("s")):
        R += 0.07
    if e * R >= odds and pct <= 0.5:
        return _legal(c, "call")
    return _legal(c, "fold")


# ---------------- postflop ----------------
def post_equity(c, w, keep, n_opp, budget, iters, bluff_step=6):
    my = [CARD[c.cards[0]], CARD[c.cards[1]]]
    bl = [CARD[x] for x in c.board]
    dead = set(c.cards) | set(c.board)
    lst = prange_for(w)
    L = len(lst)
    i = _rng.randrange(L)
    cand = []
    for _ in range(L):
        t = lst[i]
        i += 1
        if i == L:
            i = 0
        if t[0] in dead or t[1] in dead:
            continue
        cand.append(t)
        if len(cand) >= budget:
            break
    if not cand:
        return 0.5
    if keep < 0.98:
        scored = sorted(cand, key=lambda t: EVAL(bl + t[2]), reverse=True)
        kn = max(6, int(len(scored) * keep + 0.5))
        top = scored[:kn]
        rest = scored[kn:]
        # keep some draws/bluffs from the remainder
        top.extend(rest[::bluff_step])
        cand = top
    e1 = MC(my, [t[3] for t in cand], bl, iters)
    if n_opp > 1:
        return e1 ** (1 + 0.75 * (n_opp - 1))
    return e1


def postflop(c, t0):
    opps = c.opps
    n_opp = len(opps)
    street = len(c.board)
    river = street >= 5
    facing = c.to_call > 0
    # main villain
    if facing and c.street_raises:
        vill = c.street_raises[-1][0]
    else:
        pre_ag = c.pre_raises[-1][0] if c.pre_raises else None
        cands = [s.seat for s in opps]
        if pre_ag in cands:
            vill = pre_ag
        else:
            vill = min(cands, key=lambda s: villain_pre_width(c, s)) if cands else None
    w = villain_pre_width(c, vill) if vill is not None else 1.0
    keep = 1.0
    bluffy = True
    if vill is not None:
        bf = villain_betfreq(c, vill)
        rf = villain_raisefreq(c, vill)
        ka = min(1.0, max(0.25, 1.15 * bf + 0.1))
        kr = min(1.0, max(0.08, 1.3 * rf + 0.05))
        for (s, stx, typ, r) in c.post_actions:
            if s != vill:
                continue
            sk = STREET_K[min(stx, 3)]
            if typ == "bet":
                size_k = 1.0 if r < 0.45 else (0.8 if r < 0.8 else (0.6 if r < 1.5 else 0.5))
                keep *= min(1.0, ka * size_k * sk)
                bluffy = r < 0.8
            else:
                keep *= min(1.0, kr * sk)
                bluffy = rf > 0.3
        ncalls = c.post_calls.get(vill, 0)
        if ncalls:
            kc = min(1.0, max(0.35, 1.0 - villain_ftb(c, vill) + 0.1))
            keep *= kc ** ncalls
    keep = max(0.06, keep)
    # time budget
    bank = getattr(c, "bank", 100)
    budget, iters = (110, 380) if bank > 30 else (60, 200)
    if time.perf_counter() - t0 > 0.00035:  # already slow (loaded machine): cheaper estimate
        budget, iters = 50, 150
    e = post_equity(c, w, keep, n_opp, budget, iters, 6 if bluffy else 25)

    pot = c.pot
    stack = c.stack
    U = None
    if facing:
        odds = c.to_call / float(pot + c.to_call)
        commit = c.to_call >= 0.4 * stack or (stack - c.to_call) < 0.3 * (pot + c.to_call)
        raise_th = (0.84 if river else 0.78) + 0.05 * (n_opp - 1)
        can_raise = "raise" in c.legal
        if commit:
            if n_opp == 1 and vill is not None:
                u_c, u_f = call_allin_ev(c, e, vill)
                ok = u_c > u_f
            else:
                ok = e >= odds + 0.03
            if ok:
                if can_raise and e >= 0.6:
                    return _legal(c, "raise", c.total)
                return _legal(c, "call")
            return _legal(c, "fold")
        if e >= raise_th and can_raise:
            tgt = int(c.bet + c.to_call + 0.85 * (pot + c.to_call))
            if tgt >= 0.55 * c.total:
                tgt = c.total
            return _legal(c, "raise", tgt)
        R = 1.0 if river else 0.9
        margin = 0.02 if river else 0.03
        if e * R >= odds + margin:
            return _legal(c, "call")
        return _legal(c, "fold")

    # not facing a bet: choose bet size (or check) by a simple EV model
    if "raise" not in c.legal:
        return _legal(c, "check")
    # fold probability of all opponents to a bet
    F = 1.0
    for s in opps:
        if _kind(s.status) != "active":
            F = 0.0
            break
        F *= villain_ftb(c, s.seat)
    aggressor = bool(c.pre_raises) and c.pre_raises[-1][0] == c.me
    if aggressor and street == 3:
        F = min(0.97, F * 1.12)
    after = 0
    if c.button in c.ring:
        for s in _ring_after(c, c.me, c.button):
            if s != c.me and s in c.seats and _kind(c.seats[s].status) == "active":
                after += 1
    R = 0.92 if after == 0 else 0.82
    ev_check = e * R * pot
    best, best_ev = 0, ev_check
    lo, hi = c.legal["raise"]
    for frac in (0.33, 0.5, 0.75, 1.0):
        if frac > 0.8 and e < 0.55:
            continue  # pot-size bets only for value; bluffs stay <= 3/4 pot
        B = int(pot * frac)
        if B < lo:
            B = lo
        if B > hi:
            B = hi
        Fb = min(0.97, F * (0.85 + 0.45 * min(1.0, B / float(pot or 1))))
        ec = e ** (1 + Fb + 0.5 * min(1.5, B / float(pot or 1)))
        ev = Fb * pot + (1 - Fb) * (ec * (pot + 2 * B) - B)
        if ev > best_ev + 0.01 * pot:
            best, best_ev = B, ev
    # shove when stack is small relative to pot and we are strong
    if stack <= 1.3 * pot and e >= 0.7:
        best = hi
    if best > 0:
        return _legal(c, "raise", c.bet + best)
    return _legal(c, "check")


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        t0 = time.perf_counter()
        mem = None
        try:
            if memory:
                mem = json.loads(memory.decode("utf-8") if isinstance(memory, (bytes, bytearray)) else memory)
        except Exception:
            mem = None
        if not isinstance(mem, dict):
            mem = {}
        try:
            cfg_stack = int(getattr(state.config, "starting_stack", None) or 2000)
            process_events(mem, state.events or [], cfg_stack)
        except Exception:
            pass
        try:
            out = json.dumps(mem, separators=(",", ":")).encode("utf-8")
            if len(out) > 60000:
                mem.pop("s", None)
                out = json.dumps(mem, separators=(",", ":")).encode("utf-8")
        except Exception:
            out = b""
        c = None
        try:
            c = build_ctx(state, mem)
            c.bank = getattr(state, "time_bank_ms", 100)
            if c.bank is None:
                c.bank = 100
            if len(c.board) == 0:
                act = preflop(c)
            else:
                act = postflop(c, t0)
            return act, out
        except Exception:
            try:
                L = c.legal if c is not None else _legal_map(state)
            except Exception:
                L = {}
            if "check" in L:
                return Action.check(), out
            return Action.fold(), out


# Move import-time objects (tables, range lists) out of the GC's scanned generations so a
# collection during play stays cheap (latency spikes were GC gen-2 passes).
try:
    import gc as _gc
    _gc.collect()
    _gc.freeze()
except Exception:
    pass
