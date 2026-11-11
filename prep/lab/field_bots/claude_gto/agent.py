"""claude_gto: an approximately game-theory-optimal No-Limit Hold'em sit-and-go bot.

Design (see NOTES.md):
  * Preflop: a 169-class equity matrix (pf_tables.npz) and fictitious-play Nash push/fold tables
    (push_tables.npz) are built offline; at import we derive a hand ranking, equity-vs-top-x% tables,
    multiway corrections and open/3-bet/4-bet ranges by position and stack depth. Decisions mix at range
    boundaries (randomised), bluff 3-bets/4-bets use suited blockers, all-ins are evaluated by EV with the
    opponent's best-response calling range, and big calls/jams are checked against ICM.
  * Postflop: equity versus each opponent's range (preflop role, narrowed by their postflop aggression and
    scaled by observed frequencies) via eval7's C equity routines; balanced value/bluff betting with
    street-dependent, two-size (polar / merged) sizing; pot-odds + ICM defence against bets.
  * Per-table opponent frequencies (VPIP / PFR / postflop aggression) travel in `memory` (JSON, < 2 KB).
"""
import gc
import json
import os
import random

import numpy as np
import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

HERE = os.path.dirname(os.path.abspath(__file__))
RANKS = "23456789TJQKA"
SUITS = "shdc"
CARD_STR = [r + s for r in RANKS for s in SUITS]
CIDX = {s: i for i, s in enumerate(CARD_STR)}
ECARD = [eval7.Card(s) for s in CARD_STR]
_RNG = random.Random()

# ----------------------------------------------------------------------------------------------------
# Hand classes (must match build_tables.py)
# ----------------------------------------------------------------------------------------------------
CLS = [(r, r, "p") for r in range(13)]
CLS += [(h, l, "s") for h in range(13) for l in range(h)]
CLS += [(h, l, "o") for h in range(13) for l in range(h)]
_CID = {c: i for i, c in enumerate(CLS)}
CLASS2 = [[0] * 52 for _ in range(52)]
for _a in range(52):
    for _b in range(52):
        if _a == _b:
            continue
        ra, rb = _a >> 2, _b >> 2
        if ra == rb:
            CLASS2[_a][_b] = _CID[(ra, ra, "p")]
        else:
            hi, lo = (ra, rb) if ra > rb else (rb, ra)
            CLASS2[_a][_b] = _CID[(hi, lo, "s" if (_a & 3) == (_b & 3) else "o")]


def _combos(c):
    h, l, t = c
    if t == "p":
        return [(h * 4 + a, h * 4 + b) for a in range(4) for b in range(a + 1, 4)]
    if t == "s":
        return [(h * 4 + a, l * 4 + a) for a in range(4)]
    return [(h * 4 + a, l * 4 + b) for a in range(4) for b in range(4) if a != b]


COMBOS = [_combos(c) for c in CLS]
W = np.array([len(x) for x in COMBOS], dtype=float)

# ----------------------------------------------------------------------------------------------------
# Import-time precomputation
# ----------------------------------------------------------------------------------------------------
_pf = np.load(os.path.join(HERE, "pf_tables.npz"))
EQ = _pf["eq"].astype(float)          # 169x169 heads-up all-in equity
MW = _pf["mw"].astype(float)          # equity vs 2, 3, 5 random hands
_pt = np.load(os.path.join(HERE, "push_tables.npz"))
PUSH = _pt["push"].astype(float)      # [n_behind-1, stack idx, class] push probability (Nash, chip EV)
S_GRID = [float(x) for x in _pt["s_grid"]]

VR = EQ @ (W / W.sum())               # equity vs a random hand
# Ranking: blend of heads-up and multiway equity + small playability bonus (pairs, suited, connected).
_score = 0.4 * VR / VR.mean() + 0.3 * MW[:, 0] / MW[:, 0].mean() + 0.3 * MW[:, 1] / MW[:, 1].mean()
for _i, (_h, _l, _t) in enumerate(CLS):
    if _t == "p":
        _score[_i] += 0.04
    else:
        if _t == "s":
            _score[_i] += 0.03
        gap = _h - _l
        if gap == 1:
            _score[_i] += 0.02 if _t == "s" else 0.005
        elif gap == 2 and _t == "s":
            _score[_i] += 0.01
ORDER = [int(i) for i in np.argsort(-_score, kind="stable")]
_cum = np.cumsum(W[ORDER]) / W.sum()
PCT = [0.0] * 169                     # mid-percentile of each class in the ranking (0 = best)
for _k, _c in enumerate(ORDER):
    PCT[_c] = float(_cum[_k] - W[_c] / W.sum() / 2)
CUMPCT_ORDER = [float(x) for x in _cum]

# Top-x% range membership matrix on a 0.5% grid -> cumulative weighted equity tables.
NG = 200
_M = np.zeros((NG + 1, 169))
_cw = np.cumsum(W[ORDER])
for _k in range(1, NG + 1):
    t = _k / NG * W.sum()
    prev = 0.0
    for _j, _c in enumerate(ORDER):
        take = min(W[_c], max(0.0, t - prev))
        if take <= 0:
            break
        _M[_k, _c] = take
        prev += W[_c]
CUMEQ = (EQ @ _M.T).tolist()          # [class][k] = sum over top-k range of eq*weight
CWT = _M.sum(axis=1).tolist()


def eq_top(c, p):
    """Equity of class c vs the top-p fraction of hands."""
    k = int(p * NG + 0.5)
    if k < 1:
        k = 1
    elif k > NG:
        k = NG
    return CUMEQ[c][k] / CWT[k]


def eq_band(c, lo, hi):
    klo = int(lo * NG + 0.5)
    khi = int(hi * NG + 0.5)
    if khi > NG:
        khi = NG
    if klo < 0:
        klo = 0
    if khi - klo < 1:
        if khi < 1:
            khi = 1
        klo = khi - 1
    row = CUMEQ[c]
    return (row[khi] - row[klo]) / (CWT[khi] - CWT[klo])


# Multiway correction: actual equity vs n random hands / (heads-up equity)^n.
CORR = []
for _c in range(169):
    v = max(VR[_c], 1e-6)
    c2 = MW[_c, 0] / v ** 2
    c3 = MW[_c, 1] / v ** 3
    c5 = MW[_c, 2] / v ** 5
    c4 = (c3 * c5) ** 0.5
    c6 = c5 * (c5 / c4)
    c7 = c6 * (c5 / c4)
    CORR.append([1.0, 1.0, c2, c3, c4, c5, min(c6, 6.0), min(c7, 8.0)])

# Push probabilities as nested lists for fast scalar access, plus each push range's size.
PUSH_L = PUSH.tolist()
PUSH_PCT = [[float((PUSH[n, k] * W).sum() / W.sum()) for k in range(len(S_GRID))] for n in range(7)]


def s_index(s):
    lo, hi = 0, len(S_GRID) - 1
    if s <= S_GRID[0]:
        return 0
    if s >= S_GRID[hi]:
        return hi
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if S_GRID[mid] <= s:
            lo = mid
        else:
            hi = mid
    return lo if s - S_GRID[lo] <= S_GRID[hi] - s else hi


# Ranked combo list for range sampling: (eval7 pair list, bitmask)
RC = []
for _c in ORDER:
    for (_a, _b) in COMBOS[_c]:
        RC.append(([ECARD[_a], ECARD[_b]], (1 << _a) | (1 << _b), (ECARD[_a], ECARD[_b])))
NRC = len(RC)

# GTO-style opening frequencies (fraction of hands) by number of players left to act behind.
OPEN = [0.0, 0.50, 0.42, 0.29, 0.235, 0.195, 0.165, 0.145]

# Bluff candidates for 3-bets / 4-bets: suited wheel aces, suited connectors and gappers, suited Kx.
BLUFF3 = set()
BLUFF4 = set()
for _i, (_h, _l, _t) in enumerate(CLS):
    if _t != "s":
        continue
    if _h == 12 and _l <= 3:
        BLUFF3.add(_i)
        BLUFF4.add(_i)
    elif _h == 12 and _l <= 7:
        BLUFF3.add(_i)
    elif 3 <= _l and _h - _l <= 2 and _h <= 9:
        BLUFF3.add(_i)
    elif _h == 11 and _l >= 6:
        BLUFF3.add(_i)

gc.collect()
try:
    gc.freeze()
except AttributeError:
    pass


# ----------------------------------------------------------------------------------------------------
# ICM (Malmuth-Harville), my equity only
# ----------------------------------------------------------------------------------------------------
def icm_me(stacks, me, pays):
    n = len(stacks)
    np_ = min(len(pays), n)
    while np_ > 0 and pays[np_ - 1] <= 0:
        np_ -= 1
    if np_ == 0:
        return 0.0
    tot = float(sum(stacks))
    if tot <= 0:
        return 0.0
    sm = stacks[me]
    if sm <= 0:
        return 0.0
    ev = pays[0] * sm / tot
    if np_ == 1:
        return ev
    if np_ <= 3:
        p2 = 0.0
        p3 = 0.0
        for j in range(n):
            if j == me or stacks[j] <= 0:
                continue
            pj = stacks[j] / tot
            rj = tot - stacks[j]
            p2 += pj * sm / rj
            if np_ == 3:
                for k in range(n):
                    if k == me or k == j or stacks[k] <= 0:
                        continue
                    rk = rj - stacks[k]
                    p3 += pj * (stacks[k] / rj) * sm / rk
        ev += pays[1] * p2
        if np_ == 3:
            ev += pays[2] * p3
        return ev
    # general (rare): recursive with memo on remaining mask
    memo = {}

    def rec(mask, place, total):
        if place >= np_:
            return 0.0
        key = mask
        if key in memo:
            return memo[key]
        r = 0.0
        for j in range(n):
            if mask >> j & 1:
                pj = stacks[j] / total
                if j == me:
                    r += pj * pays[place]
                else:
                    r += pj * rec(mask & ~(1 << j), place + 1, total - stacks[j])
        memo[key] = r
        return r

    full = 0
    for j in range(n):
        if stacks[j] > 0:
            full |= 1 << j
    return rec(full, 0, tot)


# ----------------------------------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------------------------------
def _kind(k):
    v = getattr(k, "value", k)
    return str(v).lower()


def _clip(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


PRIOR_N = 6.0
# feature switches (kept for A/B testing)
ADAPT_STEAL = False     # widen opens when players behind over-fold
ADAPT_BLUFF = False     # scale bluffs / value sizing by observed fold-to-bet
RERAISE_RANGES = False  # widen 3bet+ ranges by observed re-raise frequency
RAISE_NARROW = False    # stronger range narrowing for postflop raises
SKILL_PREMIUM = 0.03    # extra equity demanded for stack-off decisions while many players remain
VT_SHIFT = 0.0          # shift of postflop value-bet thresholds
BLUFF_MULT = 0.7        # multiplier on balanced bluff frequencies
OPEN_MULT = 1.0         # multiplier on opening ranges
SIZE_MULT = 1.0         # multiplier on postflop bet sizes


class Ctx:
    pass


def update_stats(mem, events):
    st = mem.get("st", 0)
    bet = mem.get("b", 0)
    lvl = mem.get("l", 0)
    S = mem.setdefault("s", {})
    fl = mem.setdefault("f", {})
    for e in events:
        k = _kind(e.kind)
        if k == "hand":
            st = 0
            bet = 0
            lvl = 0
            fl.clear()
        elif k == "board":
            st += 1
            bet = 0
        elif k in ("fold", "check", "call", "raise"):
            key = str(e.seat)
            s = S.get(key)
            if s is None:
                s = S[key] = [0, 0, 0, 0, 0, 0, 0, 0, 0]
            if st > 0 and bet:
                if k == "fold":
                    s[5] += 1
                elif k != "check":
                    s[6] += 1
            if st == 0:
                f = fl.get(key, 0)
                if lvl >= 1 and k != "check":
                    s[7] += 1
                    if k == "raise":
                        s[8] += 1
                if k == "raise":
                    lvl += 1
                if not f & 1:
                    s[0] += 1
                    f |= 1
                if k == "raise" and not f & 4:
                    s[2] += 1
                    f |= 4
                if (k == "call" or k == "raise") and not f & 2:
                    s[1] += 1
                    f |= 2
                fl[key] = f
            else:
                if k == "raise":
                    s[3] += 1
                    bet = 1
                elif k == "call" or k == "check":
                    s[4] += 1
    mem["st"] = st
    mem["b"] = bet
    mem["l"] = lvl


def seat_stats(mem, seat):
    s = mem["s"].get(str(seat))
    if s is None:
        s = [0, 0, 0, 0, 0]
    n = s[0]
    vpip = (s[1] + 0.26 * PRIOR_N) / (n + PRIOR_N)
    pfr = (s[2] + 0.17 * PRIOR_N) / (n + PRIOR_N)
    agg = (s[3] + 0.35 * PRIOR_N) / (s[3] + s[4] + PRIOR_N)
    return vpip, pfr, agg


def reraise_rate(mem, seat):
    """Observed frequency of re-raising when facing a preflop raise (prior 0.07)."""
    s = mem["s"].get(str(seat))
    if s is None or len(s) < 9:
        return 0.07
    return (s[8] + 0.07 * PRIOR_N) / (s[7] + PRIOR_N)


def fold_rate(mem, seat):
    """Observed frequency of folding to a postflop bet (prior 0.45, i.e. roughly equilibrium)."""
    s = mem["s"].get(str(seat))
    if s is None or len(s) < 7:
        return 0.45
    return (s[5] + 0.45 * PRIOR_N) / (s[5] + s[6] + PRIOR_N)


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        try:
            mem = json.loads(memory.decode()) if memory else {}
            if not isinstance(mem, dict):
                mem = {}
        except Exception:
            mem = {}
        try:
            update_stats(mem, state.events or [])
            out_mem = json.dumps(mem, separators=(",", ":")).encode()
        except Exception:
            out_mem = memory or b""
            mem = {"s": {}, "f": {}, "st": 0}
        try:
            action = decide(state, mem)
        except Exception:
            action = None
        if action is None:
            action = _fallback(state)
        return action, out_mem


def _fallback(state):
    kinds = {_kind(a.kind) for a in state.legal_actions}
    if "check" in kinds:
        return Action.check()
    if "fold" in kinds:
        return Action.fold()
    if "call" in kinds:
        return Action.call()
    return Action.check()


# ----------------------------------------------------------------------------------------------------
# State parsing
# ----------------------------------------------------------------------------------------------------
def parse(state, mem):
    x = Ctx()
    x.mem = mem
    x.me = state.seat
    x.legal = {}
    for a in state.legal_actions:
        x.legal[_kind(a.kind)] = a
    seats = {}
    for s in state.seats:
        seats[s.seat] = s
    x.seats = seats
    x.order_all = sorted(seats)
    x.bb = float(state.blinds[1]) if state.blinds else 20.0
    x.sbv = float(state.blinds[0]) if state.blinds else 10.0
    me = seats[x.me]
    x.my_stack = float(me.stack)
    x.my_bet = float(me.bet)
    x.my_total = x.my_stack + x.my_bet
    x.to_call = float(state.to_call or 0)
    x.pot = float(state.pot)
    x.hole = [CIDX[c] for c in state.cards]
    x.board = [CIDX[c] for c in (state.board or [])]
    x.cls = CLASS2[x.hole[0]][x.hole[1]]
    x.button = state.button
    x.cfg = state.config
    pays = getattr(state.config, "payouts", None) or [50, 30, 20, 0, 0, 0, 0, 0]
    x.pays = [float(p) for p in pays]
    # in-hand
    x.dealt = [s for s in x.order_all if seats[s].status in ("active", "all_in", "folded")]
    x.live = [s for s in x.dealt if seats[s].status != "folded"]
    x.opps = [s for s in x.live if s != x.me]
    x.cur_bet = max(float(seats[s].bet) for s in x.dealt) if x.dealt else 0.0
    # history
    pf = []
    post = [[], [], [], []]
    blinds = []
    street = 0
    for e in state.history or []:
        k = _kind(e.kind)
        if k == "board":
            street += 1
            if street > 3:
                street = 3
        elif k == "blind":
            blinds.append((e.seat, e.amount))
        elif k in ("fold", "check", "call", "raise"):
            if street == 0:
                pf.append((e.seat, k, e.amount))
            else:
                post[street].append((e.seat, k, e.amount))
    x.street = 0 if not x.board else (len(x.board) - 2)
    x.pf = pf
    x.post = post
    if len(blinds) >= 2:
        x.sb_seat, x.bb_seat = blinds[0][0], blinds[1][0]
    elif len(blinds) == 1:
        x.sb_seat, x.bb_seat = None, blinds[0][0]
    else:
        x.sb_seat, x.bb_seat = None, None
    # preflop order (after BB clockwise)
    x.pf_order = _rotate(x.dealt, x.bb_seat if x.bb_seat is not None else x.button)
    # postflop order (after button clockwise)
    x.post_order = _rotate(x.dealt, x.button)
    return x


def _rotate(dealt, after):
    if not dealt:
        return []
    if after is None:
        return list(dealt)
    i = 0
    while i < len(dealt) and dealt[i] <= after:
        i += 1
    return dealt[i:] + dealt[:i]


# ----------------------------------------------------------------------------------------------------
# Preflop range model for each seat
# ----------------------------------------------------------------------------------------------------
def preflop_roles(x):
    """Walk preflop actions -> per seat (lo, hi) range in ranking percentiles, plus raise summary."""
    level = 0
    roles = {}
    raises = []
    n_at = {}
    order = x.pf_order
    pos = {s: i for i, s in enumerate(order)}
    for (s, k, amt) in x.pf:
        r = roles.setdefault(s, [])
        if k == "raise":
            level += 1
            r.append(("r", level))
            raises.append((s, float(amt or 0)))
            if level == 1:
                n_at[s] = len(order) - 1 - pos.get(s, 0)
        elif k == "call":
            r.append(("c", level))
        elif k == "check":
            r.append(("x", level))
        else:
            r.append(("f", level))
    x.pf_level = level
    x.pf_raises = raises
    x.pf_roles = roles
    x.open_nbehind = n_at
    x.pf_aggressor = raises[-1][0] if raises else None


def seat_range(x, s):
    """(lo, hi) percentile band for seat s's holding given preflop actions and observed frequencies."""
    vpip, pfr, agg = seat_stats(x.mem, s)
    scale = _clip(pfr / 0.17, 0.5, 6.0)
    acts = x.pf_roles.get(s, [])
    last_raise = 0
    called_after = False
    limped = False
    for (a, lvl) in acts:
        if a == "r":
            last_raise = lvl
            called_after = False
        elif a == "c":
            if last_raise:
                called_after = True
            elif lvl == 0:
                limped = True
            else:
                last_raise = -lvl  # cold call at level lvl
    st = x.seats[s]
    tot_bb = (float(st.stack) + float(st.bet)) / x.bb
    if last_raise > 0:
        if last_raise == 1:
            nb = x.open_nbehind.get(s, 4)
            hi = OPEN[_clip(nb, 1, 7)] * scale
            if limped:
                hi = 0.06 * scale
        else:
            k3 = _clip(reraise_rate(x.mem, s) / 0.07, 0.6, 40.0) ** 1.3 if RERAISE_RANGES else scale
            hi = (0.065, 0.032, 0.02)[min(last_raise, 4) - 2] * max(k3, scale if last_raise == 2 else 1.0)
        # short all-in raises are wider: at least the Nash push range for that depth
        if st.status == "all_in" and tot_bb < 30:
            nb = _clip(x.open_nbehind.get(s, 3), 1, 7)
            hi = max(hi, PUSH_PCT[nb - 1][s_index(tot_bb)] * (1.0 if last_raise == 1 else 0.6))
        hi = _clip(hi, 0.015, 1.0)
        if called_after:
            return (hi * 0.08, hi * 0.55)
        return (0.0, hi)
    if last_raise < 0:  # cold call of a raise at level -last_raise
        lvl = -last_raise
        if s == x.bb_seat and lvl == 1:
            hi = _clip(vpip * 1.7, 0.2, 0.95)
        elif lvl == 1:
            hi = _clip(vpip * 1.0, 0.08, 0.9)
        else:
            hi = _clip(vpip * 0.35, 0.04, 0.6)
        return (min(0.02, hi * 0.1), hi)
    if limped:
        if s == x.sb_seat:
            return (0.04, 0.85)
        return (0.03, _clip(vpip * 1.5, 0.15, 1.0))
    # checked BB or no voluntary action
    return (0.06, 1.0)


# ----------------------------------------------------------------------------------------------------
# Action helpers
# ----------------------------------------------------------------------------------------------------
def a_fold(x):
    if "check" in x.legal:
        return Action.check()
    return Action.fold()


def a_call(x):
    if "call" in x.legal:
        return Action.call()
    if "check" in x.legal:
        return Action.check()
    return Action.fold()


def a_raise(x, total):
    la = x.legal.get("raise")
    if la is None:
        return a_call(x)
    lo, hi = int(la.min_amount), int(la.max_amount)
    t = int(total)
    if t >= hi * 0.85 or t >= hi - x.bb:
        t = hi
    if t < lo:
        t = lo
    if t > hi:
        t = hi
    return Action.raise_to(t)


def a_jam(x):
    la = x.legal.get("raise")
    if la is None:
        return a_call(x)
    return Action.raise_to(int(la.max_amount))


def stacks_for_icm(x):
    idx = {}
    st = []
    for s in x.order_all:
        seat = x.seats[s]
        if seat.status == "busted":
            continue
        idx[s] = len(st)
        st.append(float(seat.stack))
    return idx, st


def icm_eval(x, outcomes, villain):
    """outcomes: list of (prob, my_delta, villain_delta) applied to stacks behind. Returns ICM equity."""
    idx, base = stacks_for_icm(x)
    me = idx[x.me]
    vi = idx.get(villain)
    tot = 0.0
    for (p, dm, dv) in outcomes:
        if p <= 0:
            continue
        st = base[:]
        st[me] = max(0.0, st[me] + dm)
        if vi is not None:
            st[vi] = max(0.0, st[vi] + dv)
        tot += p * icm_me(st, me, x.pays)
    return tot


def skill_premium(x):
    """ICM assumes equal skill; with an edge over the field, avoid marginal coin flips early."""
    n = len(stacks_for_icm(x)[1])
    return SKILL_PREMIUM * _clip((n - 3) / 5.0, 0.0, 1.0)


def icm_call_req(x, villain, risk, pot):
    """ICM equity needed to call `risk` more chips into `pot` (villain gets the pot if I fold or lose)."""
    excess = max(0.0, x.to_call - x.my_stack)
    final_pot = pot - excess + risk
    i_fold = icm_eval(x, [(1.0, 0.0, pot)], villain)
    i_win = icm_eval(x, [(1.0, final_pot - risk, excess)], villain)
    i_lose = icm_eval(x, [(1.0, -risk, final_pot + excess)], villain)
    den = i_win - i_lose
    if den <= 1e-12:
        return 1.0
    prem = skill_premium(x) if risk >= 0.5 * x.my_stack else 0.0
    return _clip((i_fold - i_lose) / den + prem, 0.0, 1.0)


def icm_call_value(x, villain, e_real):
    """Approximate ICM value of calling (resolving the pot at realised equity e_real)."""
    risk = min(x.to_call, x.my_stack)
    excess = max(0.0, x.to_call - x.my_stack)
    final_pot = x.pot - excess + risk
    return icm_eval(x, [(e_real, final_pot - risk, excess), (1.0 - e_real, -risk, final_pot + excess)], villain)


def players_behind_pf(x):
    """Live players with chips who still have to act this preflop round (excluding me)."""
    res = []
    cur = x.cur_bet
    lvl0 = x.pf_level == 0
    for s in x.pf_order:
        if s == x.me:
            continue
        st = x.seats[s]
        if st.status != "active" or float(st.stack) <= 0:
            continue
        b = float(st.bet)
        if b < cur or (lvl0 and s == x.bb_seat and not acted_this_round(x, s)):
            res.append(s)
    return res


def acted_this_round(x, s):
    for (ss, k, a) in x.pf:
        if ss == s:
            return True
    return False


# ----------------------------------------------------------------------------------------------------
# Decision
# ----------------------------------------------------------------------------------------------------
def decide(state, mem):
    x = parse(state, mem)
    if not x.legal:
        return None
    if len(x.legal) == 1:
        k = next(iter(x.legal))
        return {"check": Action.check, "call": Action.call, "fold": Action.fold}.get(k, Action.check)() \
            if k != "raise" else a_jam(x)
    preflop_roles(x)
    if x.street == 0:
        return decide_preflop(x)
    return decide_postflop(x)


def mixp(pct, cut, width=0.025):
    """Probability of including a hand at percentile pct in a top-`cut` range (linear mix at boundary)."""
    if cut <= 0:
        return 0.0
    return _clip((cut - pct) / width + 0.5, 0.0, 1.0)


def villain_call_range(r_hi, jam_range, req):
    """Fraction q (of all hands) of a villain's top-r_hi range that calls a jam: classes whose equity vs
    our jam range is at least `req` (their best response)."""
    q = 0.0
    k = 0
    prev = 0.0
    for c in ORDER:
        if prev >= r_hi:
            break
        cp = CUMPCT_ORDER[k]
        k += 1
        if eq_top(c, jam_range) >= req:
            q += min(cp, r_hi) - prev
        prev = cp
    return q


def decide_preflop(x):
    c = x.cls
    pc = PCT[c]
    bb = x.bb
    behind = players_behind_pf(x)
    nb = len(behind)
    level = x.pf_level
    r = _RNG.random()

    # effective stack vs everyone still able to contest
    others_tot = [float(x.seats[s].stack) + float(x.seats[s].bet) for s in x.opps]
    eff = min(x.my_total, max(others_tot)) if others_tot else x.my_total
    eff_bb = eff / bb

    if level == 0:
        limpers = [s for (s, k, a) in x.pf if k == "call"]
        n_limp = len(limpers)
        dead_bb = x.pot / bb
        if x.to_call == 0:
            # BB option after limps (or everyone folded to a completed SB)
            iso = 0.12 if n_limp <= 1 else 0.08
            if eff_bb <= 12:
                n_eff = _clip(n_limp, 1, 7)
                s_eq = eff_bb * 1.5 / max(dead_bb, 1.5)
                p = PUSH_L[n_eff - 1][s_index(s_eq)][c]
                if r < p * 0.8:
                    return a_jam(x)
                return Action.check() if "check" in x.legal else a_fold(x)
            if r < mixp(pc, iso):
                return a_raise(x, x.my_bet + (3.0 + n_limp) * bb + x.to_call)
            return Action.check()
        push_lim = 15.0 if nb == 1 else 12.0
        if n_limp == 0 and eff_bb <= push_lim or (n_limp > 0 and eff_bb <= 10):
            n_eff = _clip(nb + n_limp, 1, 7)
            s_eq = eff_bb * 1.5 / max(dead_bb, 1.5)
            p = PUSH_L[n_eff - 1][s_index(s_eq)][c]
            if r < p:
                return a_jam(x)
            return a_fold(x)
        if n_limp == 0:
            cut = OPEN[_clip(nb, 1, 7)] * OPEN_MULT
            if eff_bb < 25:
                cut *= 0.92
            # GTO ranges assume equilibrium defence; if the players behind over-fold, steal wider.
            pf_obs = 1.0
            pf_eq = 1.0
            for s_ in behind:
                vp = seat_stats(x.mem, s_)[0]
                k_ = 1.0 if s_ == x.bb_seat else 0.65
                pf_obs *= 1.0 - _clip(vp * k_, 0.02, 0.95)
                pf_eq *= 1.0 - 0.26 * k_
            if ADAPT_STEAL and pf_obs > pf_eq + 0.02:
                t_ = _clip((pf_obs - pf_eq) / max(0.05, 0.72 - pf_eq), 0.0, 1.0)
                cut = cut + (1.0 - cut) * t_
            if r < mixp(pc, cut):
                if nb == 1:
                    size = 3.0 if eff_bb >= 25 else 2.5
                else:
                    size = 2.5 if eff_bb >= 40 else (2.2 if eff_bb >= 22 else 2.0)
                return a_raise(x, size * bb)
            return a_fold(x)
        # limpers ahead: isolate or (cheaply) over-limp / complete
        cut = OPEN[_clip(nb + n_limp, 1, 7)] * 0.7
        if r < mixp(pc, cut):
            if eff_bb <= 22:
                return a_jam(x)
            return a_raise(x, (3.5 + n_limp) * bb)
        if x.me == x.sb_seat and pc < 0.45:
            return a_call(x)
        if pc < 0.30 and eff_bb >= 30 and (CLS[c][2] != "o"):
            return a_call(x)
        return a_fold(x)

    # ---------------- facing a raise ----------------
    v = x.pf_aggressor
    vlo, vhi = seat_range(x, v)
    vst = x.seats[v]
    v_total = float(vst.stack) + float(vst.bet)
    eff_v = min(x.my_total, v_total)
    effv_bb = eff_v / bb
    e_main = eq_top(c, vhi) if vlo <= 0 else eq_band(c, vlo, vhi)
    callers = [s for s in x.opps if s != v and float(x.seats[s].bet) >= x.cur_bet - 1e-9
               and acted_this_round(x, s)]
    e = e_main
    for s in callers[:3]:
        lo2, hi2 = seat_range(x, s)
        e *= eq_band(c, lo2, hi2)
    n_in = 1 + len(callers)
    if n_in > 1:
        e = min(1.0, e * CORR[c][min(n_in, 7)])
    to_call = x.to_call
    pot = x.pot
    po = to_call / (pot + to_call) if to_call > 0 else 0.0
    can_raise = "raise" in x.legal and float(vst.stack) > 0
    all_in_call = to_call >= x.my_stack or not can_raise
    ip = _in_position(x, [v] + callers)
    real = _realize(x, ip, eff_bb)

    last_amt = x.cur_bet
    if level == 1:
        std_raise = last_amt * (3.0 if ip else 3.6) + len(callers) * last_amt
        val_cut = max(0.025, vhi * 0.22)
        bluff_set, bluff_p = BLUFF3, 0.35
    elif level == 2:
        std_raise = last_amt * 2.3
        val_cut = max(0.018, vhi * 0.35)
        bluff_set, bluff_p = BLUFF4, 0.18
    else:
        std_raise = x.my_total
        val_cut = max(0.012, vhi * 0.45)
        bluff_set, bluff_p = set(), 0.0

    if all_in_call:
        risk = min(to_call, x.my_stack)
        # no further betting if the raiser is all-in and nobody else can act, or my call is all-in
        closed = to_call >= x.my_stack or (float(vst.stack) <= 0 and not players_behind_pf(x)
                                           and all(x.seats[s].status != "active" or s == x.me for s in x.opps))
        er = e if closed else e * real
        if risk >= 0.2 * x.my_stack:
            req = icm_call_req(x, v, risk, pot)
            return a_call(x) if er >= req else a_fold(x)
        return a_call(x) if er >= po else a_fold(x)

    jam_mode = std_raise >= 0.40 * x.my_total or effv_bb <= 28 or level >= 3
    if jam_mode:
        i_fold, i_jam = _jam_icm(x, c, v, vhi, level, len(callers))
        best, act = i_fold, 0
        if i_jam > best:
            best, act = i_jam, 2
        # flat call keeps postflop play (only sensible when stacks stay deep enough)
        if effv_bb > 12 or to_call < 0.15 * x.my_stack:
            i_call = icm_call_value(x, v, _clip(e * real, 0.0, 1.0))
            if i_call > best:
                best, act = i_call, 1
        if act == 2:
            return a_jam(x)
        if act == 1:
            return a_call(x)
        return a_fold(x)

    if pc <= val_cut and n_in <= 2:
        return a_raise(x, std_raise)
    if not callers and c in bluff_set and eff_bb >= 40 and r < bluff_p:
        return a_raise(x, std_raise)
    if to_call >= 0.3 * x.my_stack:
        req = icm_call_req(x, v, to_call, pot)
        return a_call(x) if e * real >= req else a_fold(x)
    nbh = len(players_behind_pf(x))
    if (e * real - 0.02 * nbh) * (pot + to_call) - to_call > 0:
        return a_call(x)
    return a_fold(x)


def _in_position(x, others):
    order = x.post_order
    pos = {s: i for i, s in enumerate(order)}
    mine = pos.get(x.me, 0)
    for s in others:
        if s is not None and pos.get(s, -1) > mine:
            return False
    return True


def _realize(x, ip, eff_bb):
    """Fraction of raw equity a flat call realises postflop (position, closing action, implied odds)."""
    h, l, t = CLS[x.cls]
    realize = 0.95 if ip else 0.78
    if x.me == x.bb_seat:
        realize += 0.04
    price_frac = x.to_call / max(1.0, x.my_stack)
    if eff_bb >= 35 and price_frac <= 0.08:
        if t == "p":
            realize += 0.12
        elif t == "s" and h - l <= 2:
            realize += 0.06
    return realize


def _jam_icm(x, c, v, vhi, level, n_callers):
    """ICM value of folding vs shoving over raiser v (top-vhi range, calling with its best response)."""
    vst = x.seats[v]
    v_bet = float(vst.bet)
    v_total = float(vst.stack) + v_bet
    eff_total = min(x.my_total, v_total)
    risk = eff_total - x.my_bet
    vcost = eff_total - v_bet
    pot = x.pot
    i_fold = icm_eval(x, [(1.0, 0.0, pot)], v)
    if vcost <= 0:
        return i_fold, -1.0
    final_pot = pot + risk + vcost
    req = vcost / final_pot
    jr = _clip(vhi * (0.6 if level == 1 else 0.5), 0.05, 0.45)
    q = villain_call_range(vhi, jr, req)
    p_call = _clip(q / vhi, 0.0, 1.0) if vhi > 0 else 1.0
    nbh = len(players_behind_pf(x))
    p_fold = (1.0 - p_call) * (0.96 ** max(0, nbh - 1)) * (0.9 ** n_callers)
    p_call = 1.0 - p_fold
    e_called = eq_top(c, max(q, 0.01)) - skill_premium(x)
    i_jam = icm_eval(x, [
        (p_fold, pot, 0.0),
        (p_call * e_called, final_pot - risk, -vcost),
        (p_call * (1.0 - e_called), -risk, final_pot - vcost),
    ], v)
    return i_fold, i_jam


# ----------------------------------------------------------------------------------------------------
# Postflop
# ----------------------------------------------------------------------------------------------------
def _range_list(x, s, dead_mask, n_max, narrow, board_e):
    lo, hi = seat_range(x, s)
    a = int(lo * NRC)
    b = int(hi * NRC + 0.999)
    if b > NRC:
        b = NRC
    if b - a < 12:
        a = max(0, b - 12)
    span = b - a
    if span <= n_max:
        idxs = range(a, b)
    else:
        idxs = _RNG.sample(range(a, b), n_max)
    lst = []
    for i in idxs:
        rc = RC[i]
        if rc[1] & dead_mask:
            continue
        lst.append(rc)
    if not lst:
        return [(RC[i][2], 1.0) for i in range(NRC) if not RC[i][1] & dead_mask][:50]
    f, step = narrow
    if f < 0.97 and len(lst) > 8:
        ev = eval7.evaluate
        scored = sorted(lst, key=lambda rc: ev(board_e + rc[0]), reverse=True)
        keep = max(3, int(len(scored) * f + 0.5))
        out = [(rc[2], 1.0) for rc in scored[:keep]]
        if step:
            out += [(rc[2], 1.0) for rc in scored[keep::step]]
        return out
    return [(rc[2], 1.0) for rc in lst]


def _narrow_factor(x, s, facing):
    """(value fraction kept, 1-in-`step` of the rest kept as bluffs/draws) from s's postflop actions."""
    _, _, agg = seat_stats(x.mem, s)
    fa = _clip(0.25 + 0.75 * agg, 0.4, 1.0)
    f = 1.0
    step = 3
    for st in (1, 2, 3):
        if st > x.street:
            break
        acts = x.post[st]
        bet_before = False
        for (ss, k, amt) in acts:
            if k == "raise":
                if ss == s:
                    if not bet_before:
                        f *= fa
                        step = (3, 4, 6)[st - 1]
                    elif RAISE_NARROW:
                        f *= fa * fa
                        step = 6 if st == 1 else 9
                    else:
                        f *= fa * 0.75
                bet_before = True
            elif k == "call" and ss == s:
                f *= 0.75
    return max(0.06, f), step


def postflop_equity(x, facing_seat):
    dead = (1 << x.hole[0]) | (1 << x.hole[1])
    for b in x.board:
        dead |= 1 << b
    board_e = [ECARD[b] for b in x.board]
    hero = [ECARD[x.hole[0]], ECARD[x.hole[1]]]
    opps = list(x.opps)
    main = facing_seat if facing_seat is not None else (x.pf_aggressor if x.pf_aggressor in opps else opps[0])
    opps.sort(key=lambda s: (s != main, _narrow_factor(x, s, False)[0]))
    eqs = []
    for i, s in enumerate(opps[:3]):
        nf = _narrow_factor(x, s, s == facing_seat)
        lst = _range_list(x, s, dead, 96 if i == 0 else 48, nf, board_e)
        if x.street == 3:
            eqv = eval7.py_hand_vs_range_exact(hero, lst, board_e)
        else:
            eqv = eval7.py_hand_vs_range_monte_carlo(hero, lst, board_e, 500 if i == 0 else 220)
        eqs.append(eqv)
    if len(opps) > 3:
        eqs += [max(eqs[1:]) if len(eqs) > 1 else eqs[0]] * (len(opps) - 3)
    if len(eqs) == 1:
        return eqs[0], eqs[0]
    prod = 1.0
    for v in eqs:
        prod *= v
    return prod ** 0.88, eqs[0]


def decide_postflop(x):
    st = x.street
    to_call = x.to_call
    pot = x.pot
    r = _RNG.random()
    n_opp = len(x.opps)
    if n_opp == 0:
        return a_call(x)
    # players who can still act (not all-in)
    actors = [s for s in x.opps if x.seats[s].status == "active"]
    facing_seat = None
    if to_call > 0:
        for (s, k, amt) in reversed(x.post[st]):
            if k == "raise":
                facing_seat = s
                break
        if facing_seat is None or facing_seat not in x.opps:
            # e.g. all-in for less / blind remnants: pick the biggest bettor
            facing_seat = max(x.opps, key=lambda s: float(x.seats[s].bet))
    E, e1 = postflop_equity(x, facing_seat)
    ip = _in_position(x, x.opps)
    was_aggr = x.pf_aggressor == x.me
    my_stack = x.my_stack
    spr = my_stack / max(pot, 1.0)

    if to_call <= 0:
        if not actors:
            return Action.check()
        # thresholds (heads-up), relaxed multiway since E is already a multiway equity
        vt = (0.60, 0.64, 0.68)[st - 1] - 0.06 * (n_opp - 1) + VT_SHIFT
        strong = (0.80, 0.83, 0.86)[st - 1]
        # we had the initiative on the previous street?
        initiative = _had_initiative(x)
        fr = min(fold_rate(x.mem, s_) for s_ in x.opps) if ADAPT_BLUFF else 0.45
        if fr < 0.3:
            vt -= 0.04  # calling stations: thinner value
        if E >= vt:
            slow = 0.12 if (E >= 0.9 and st < 3 and n_opp == 1 and fr > 0.35) else 0.0
            if r < slow:
                return Action.check()
            frac = _bet_size(x, E >= strong, n_opp, was_aggr)
            if fr < 0.3 and E >= strong:
                frac = max(frac, 1.0)
            return _bet(x, frac, value=True)
        # bluffs / semi-bluffs (balanced frequencies, mostly heads-up)
        if n_opp == 1:
            if st == 1:
                p = 0.50 if initiative else 0.18
                if E >= 0.38:
                    p = 0.40 if initiative else 0.25
            elif st == 2:
                p = 0.30 if initiative else 0.12
                if E >= 0.38:
                    p = 0.33 if initiative else 0.15
            else:
                p = 0.22 if initiative else 0.10
                if E >= 0.35:
                    p = 0.0  # showdown value: check
            if not ip and not initiative:
                p *= 0.6
        else:
            p = 0.08 if (initiative and st == 1 and n_opp == 2) else 0.0
        p *= BLUFF_MULT
        if ADAPT_BLUFF:
            p *= _bluff_mult(x)
        if r < p:
            frac = _bet_size(x, True, n_opp, was_aggr)
            return _bet(x, frac, value=False)
        return Action.check()

    # ---- facing a bet ----
    po = to_call / (pot + to_call)
    risk = min(to_call, my_stack)
    big = to_call >= 0.3 * my_stack or to_call >= my_stack
    rt = (0.72, 0.75, 0.80)[st - 1] - 0.05 * (n_opp - 1)
    can_raise = "raise" in x.legal and any(x.seats[s].status == "active" for s in x.opps if s != x.me)
    if can_raise and E >= rt and r < 0.85:
        return _raise_post(x)
    # semi-bluff raise
    if can_raise and st < 3 and n_opp == 1 and 0.30 <= E < 0.5 and spr > 2.5 and r < 0.08:
        return _raise_post(x)
    margin = (0.03, 0.02, 0.0)[st - 1]
    behind = 0
    if n_opp > 1:
        # players yet to act after me on this street may raise
        margin += 0.02
    need = po + margin
    if big:
        need = max(need, icm_call_req(x, facing_seat, risk, pot))
    if E >= need:
        return a_call(x)
    return a_fold(x)


def _bluff_mult(x):
    """Scale balanced bluff frequencies by how often the opponents actually fold to bets."""
    m = 1.0
    for s_ in x.opps:
        m *= fold_rate(x.mem, s_) / 0.45
    return _clip(m, 0.15, 2.2)


def _had_initiative(x):
    st = x.street
    if st == 1:
        return x.pf_aggressor == x.me
    last = None
    for (s, k, a) in x.post[st - 1]:
        if k == "raise":
            last = s
    return last == x.me


def _bet_size(x, polar, n_opp, was_aggr):
    st = x.street
    if st == 1:
        if n_opp == 1 and was_aggr and not polar:
            return 0.33
        return 0.66 if polar else 0.5
    if st == 2:
        return 0.75 if polar else 0.55
    return 0.85 if polar else 0.5


def _bet(x, frac, value):
    amt = x.pot * frac * SIZE_MULT
    if amt < x.bb:
        amt = x.bb
    total = x.my_bet + amt
    if total >= 0.55 * x.my_total:
        return a_jam(x)
    return a_raise(x, total)


def _raise_post(x):
    total = x.cur_bet + 0.85 * (x.pot + x.to_call)
    if total >= 0.5 * x.my_total:
        return a_jam(x)
    return a_raise(x, total)
