"""claude_equity: equity-vs-range EV bot for the No Limit SNG.

Per decision:
  1. Update per-seat opponent statistics from state.events (kept in `memory`, marshal-encoded).
  2. Rebuild this hand's action sequence from state.history.
  3. Model each live opponent's range: a preflop band of the strength-ordered 1326 combos (width from
     that seat's VPIP/PFR/3-bet stats and its preflop action), then narrowed street by street by its
     postflop actions (bets keep the top of the range by made-hand strength + draws, calls drop the
     weakest part, ...).
  4. Equity vs those ranges: preflop from precomputed tables (tables.json), postflop with eval7's
     Monte Carlo on a sampled range (river: exact comparison over the sampled combos).
  5. Score fold / check / call / several bet-raise sizes by chip EV (fold equity from the seats' observed
     fold rates, equity vs the calling part of the range, realization factors), minus a risk premium
     for stack-risking actions (tournament payouts are convex), and play the best one.
Everything is bounded to keep each decision well under 1 ms on the production machines.
"""
import gc
import json
import marshal
import os
import random
from bisect import bisect_left
from time import perf_counter

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

_evaluate = eval7.evaluate
_mc = eval7.py_hand_vs_range_monte_carlo

# ----------------------------------------------------------------------------------------------- tables
_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "tables.json")) as _f:
    _T = json.load(_f)

RANKS = "23456789TJQKA"
SUITS = "cdhs"
CARD = {}
CARD_IDX = {}
for _ri, _r in enumerate(RANKS):
    for _si, _s in enumerate(SUITS):
        CARD[_r + _s] = eval7.Card(_r + _s)
        CARD_IDX[_r + _s] = _ri * 4 + _si
CARDS = [None] * 52
for _k, _i in CARD_IDX.items():
    CARDS[_i] = CARD[_k]

BUCKETS = _T["buckets"]
EQB = _T["eqb"]          # class -> HU equity vs top-p ranges (BUCKETS)
EQK = _T["eqk"]          # class -> equity vs k random hands, k = 1..7
PCT = _T["pct"]          # class -> percentile in the strength order (0 = best)
ORDER = _T["order"]


def _class_of(r0, r1, suited):
    if r0 < r1:
        r0, r1 = r1, r0
    if r0 == r1:
        return RANKS[r0] * 2
    return RANKS[r0] + RANKS[r1] + ("s" if suited else "o")


# All 1326 combos ordered by preflop strength: (card0, card1, rank0, rank1, suit0, suit1, bitmask)
RANKED = []
for _c in ORDER:
    a, b = RANKS.index(_c[0]), RANKS.index(_c[1])
    if a == b:
        pairs = [(a * 4 + s1, b * 4 + s2) for s1 in range(4) for s2 in range(s1 + 1, 4)]
    elif _c[2] == "s":
        pairs = [(a * 4 + s, b * 4 + s) for s in range(4)]
    else:
        pairs = [(a * 4 + s1, b * 4 + s2) for s1 in range(4) for s2 in range(4) if s1 != s2]
    for i0, i1 in pairs:
        RANKED.append((CARDS[i0], CARDS[i1], i0 >> 2, i1 >> 2, i0 & 3, i1 & 3, (1 << i0) | (1 << i1),
                       [CARDS[i0], CARDS[i1]]))
NCOMBO = len(RANKED)

# open-ended straight draw lookup over 13-bit rank masks (4 consecutive ranks, open at both ends)
OESD = bytearray(1 << 13)
for _m in range(1 << 13):
    for _lo in range(1, 9):
        if (_m >> _lo) & 15 == 15:
            OESD[_m] = 1
            break
    if (_m & 0b1000000001111) == 0b1000000001111:  # A-2-3-4 is a one-ended draw; ignore
        pass

PAIR_BASE = 1 << 24
KEY_FD = PAIR_BASE | (7 << 16)      # flush draw ~ a middle pair
KEY_SD = PAIR_BASE | (4 << 16)      # OESD ~ a small pair
KEY_COMBO = 2 << 24                 # flush + straight draw ~ two pair

# --------------------------------------------------------------------------------------------- stats
# per-seat counters
(HANDS, VPIP, PFR, PFF, PFFOLD, PF3B, PACT, POPEN, PBET, PFACED, PFOLD, PRAISE, PCALL, BIGF, BIGC, F3F, F3FOLD,
 PJAM, NSTAT) = range(19)


def _new_stats():
    return [0] * NSTAT


def _ratio(st, num, den, prior, w):
    if st is None:
        return prior
    return (st[num] + prior * w) / (st[den] + w)


def process_events(mem, events, start_stack):
    """Incremental per-seat statistics. mem['h'] = [hand_no, street, cur_bet, raises_this_street].
    Counts from the hand in progress go to mem['p'] and are merged into mem['s'] when the next hand starts,
    so a seat's current action never widens the range we attribute to it."""
    H = mem["h"]
    C = mem["c"]
    K = mem["k"]
    F = mem["f"]
    S = mem["s"]
    P = mem["p"]
    for e in events:
        kind = e.kind
        s = e.seat
        a = e.amount
        if kind == "hand":
            for ps, pl in P.items():
                st = S.get(ps)
                if st is None:
                    S[ps] = pl
                else:
                    for i in range(NSTAT):
                        st[i] += pl[i]
            P.clear()
            H[0] = a or 0
            H[1] = 0
            H[2] = 0
            H[3] = 0
            C.clear()
            F.clear()
        elif kind == "fold" or kind == "check" or kind == "call" or kind == "raise":
            st = P.get(s)
            if st is None:
                st = P[s] = _new_stats()
            fl = F.get(s, 0)
            contrib = C.get(s, 0)
            to_call = H[2] - contrib
            stack = K.get(s, start_stack)
            facing = to_call > 0
            if not fl & 1:
                st[HANDS] += 1
                fl |= 1
            if H[1] == 0:
                if (kind == "call" or kind == "raise") and not fl & 2:
                    st[VPIP] += 1
                    fl |= 2
                if kind == "raise" and not fl & 4:
                    st[PFR] += 1
                    fl |= 4
                if kind == "raise" and not fl & 32 and stack > 0 and ((a or 0) - contrib) * 2 >= stack:
                    st[PJAM] += 1
                    fl |= 32
                if H[3] >= 1 and facing and not fl & 8:
                    fl |= 8
                    st[PFF] += 1
                    if kind == "fold":
                        st[PFFOLD] += 1
                    elif kind == "raise":
                        st[PF3B] += 1
                elif fl & 4 and facing and H[3] >= 2 and not fl & 16:
                    fl |= 16
                    st[F3F] += 1
                    if kind == "fold":
                        st[F3FOLD] += 1
            else:
                st[PACT] += 1
                if facing:
                    st[PFACED] += 1
                    if kind == "fold":
                        st[PFOLD] += 1
                    elif kind == "raise":
                        st[PRAISE] += 1
                    elif kind == "call":
                        st[PCALL] += 1
                else:
                    st[POPEN] += 1
                    if kind == "raise":
                        st[PBET] += 1
            if facing and stack > 0 and to_call * 2 >= stack:
                st[BIGF] += 1
                if kind != "fold":
                    st[BIGC] += 1
            if kind == "call":
                a = a or 0
                C[s] = contrib + a
                K[s] = stack - a
            elif kind == "raise":
                a = a or 0
                K[s] = stack - (a - contrib)
                C[s] = a
                if a > H[2]:
                    H[2] = a
                H[3] += 1
            F[s] = fl
        elif kind == "blind":
            a = a or 0
            C[s] = C.get(s, 0) + a
            K[s] = K.get(s, start_stack) - a
            if C[s] > H[2]:
                H[2] = C[s]
        elif kind == "ante":
            K[s] = K.get(s, start_stack) - (a or 0)
        elif kind == "board":
            H[1] += 1
            H[2] = 0
            H[3] = 0
            C.clear()
        elif kind == "stack":
            K[s] = a or 0


def load_mem(memory):
    if memory:
        try:
            m = marshal.loads(memory)
            if type(m) is dict and m.get("v") == 5:
                return m
        except Exception:
            pass
    return {"v": 5, "h": [0, 0, 0, 0], "c": {}, "k": {}, "f": {}, "s": {}, "p": {}}


# ------------------------------------------------------------------------------------------- helpers
def _kname(k):
    v = getattr(k, "value", k)
    if not isinstance(v, str):
        v = str(getattr(k, "name", v))
    v = v.lower()
    if "fold" in v:
        return "fold"
    if "check" in v:
        return "check"
    if "call" in v:
        return "call"
    if "raise" in v or "bet" in v:
        return "raise"
    return v


def _legal(state):
    out = {}
    for la in state.legal_actions:
        out[_kname(la.kind)] = la
    return out


def _bucket_eq(cls, p):
    """HU equity of class vs top-p range (interpolated)."""
    row = EQB[cls]
    if p <= BUCKETS[0]:
        return row[0]
    if p >= 1.0:
        return row[-1]
    for i in range(1, len(BUCKETS)):
        if p <= BUCKETS[i]:
            lo, hi = BUCKETS[i - 1], BUCKETS[i]
            t = (p - lo) / (hi - lo)
            return row[i - 1] * (1 - t) + row[i] * t
    return row[-1]


def _committed(their_add, pot_final):
    """Scale on fold probability: players getting a good price on the rest of their stack rarely fold."""
    if pot_final <= 0:
        return 1.0
    need = their_add / pot_final
    x = (need - 0.17) / 0.2
    return 0.0 if x <= 0 else (1.0 if x >= 1 else x)


def icm_value(me, others, pay):
    """Malmuth-Harville tournament equity of `me` chips vs the other live stacks (top 3 places)."""
    others = [x for x in others if x > 0]
    n_o = len(others)
    if me <= 0:
        place = n_o + 1
        return pay[place - 1] if place - 1 < len(pay) else 0.0
    if n_o == 0:
        return pay[0] if pay else 0.0
    T = me + sum(others)
    v = me / T * pay[0]
    p1 = pay[1] if len(pay) > 1 else 0.0
    p2 = pay[2] if len(pay) > 2 else 0.0
    if p1 or p2:
        a2 = 0.0
        a3 = 0.0
        for j in range(n_o):
            sj = others[j]
            tj = T - sj
            pj = sj / T
            a2 += pj / tj
            if p2 and n_o >= 2:
                for k in range(n_o):
                    if k != j:
                        sk = others[k]
                        a3 += pj * sk / tj / (tj - sk)
        v += me * (a2 * p1 + a3 * p2)
    return v


class Icm:
    """ICM conversion of all-in style outcomes into chip-equivalents relative to folding now."""
    __slots__ = ("ok", "me", "others", "pay", "pot", "u_base", "u_win", "du")

    def __init__(self, state, me, my_stack, pot, pot_owner, pay):
        self.me = my_stack
        self.pay = pay
        self.pot = pot
        self.others = {s.seat: s.stack for s in state.seats if s.seat != me and s.status != "busted"}
        self.ok = False
        if pot <= 0 or not self.others or not any(pay[1:3]):
            return
        if pot_owner not in self.others:
            pot_owner = max(self.others, key=self.others.get)
        base = dict(self.others)
        base[pot_owner] += pot
        self.u_base = icm_value(my_stack, list(base.values()), pay)
        self.u_win = icm_value(my_stack + pot, list(self.others.values()), pay)
        self.du = (self.u_win - self.u_base) / pot
        self.ok = self.du > 1e-9

    def equiv(self, F, eq, my_add, their_add, villain):
        """Chip-equivalent EV of: everyone folds (prob F) else showdown vs `villain` with equity eq."""
        if not self.ok:
            return F * self.pot + (1 - F) * (eq * (self.pot + my_add + their_add) - my_add)
        u = F * self.u_win
        if F < 1.0:
            pot_f = self.pot + my_add + their_add
            o = self.others
            if villain not in o:
                villain = max(o, key=o.get)
            vs = o[villain]
            rest = [v for k, v in o.items() if k != villain]
            u_w = icm_value(self.me - my_add + pot_f, rest + [vs - their_add], self.pay)
            u_l = icm_value(self.me - my_add, rest + [vs - their_add + pot_f], self.pay)
            u += (1 - F) * (eq * u_w + (1 - eq) * u_l)
        return (u - self.u_base) / self.du

    def jam(self, outcomes, p_none):
        """outcomes: list of (prob_first_caller, eq, my_add, their_add, villain)."""
        if not self.ok:
            ev = p_none * self.pot
            for p, eq, ma, ta, v in outcomes:
                ev += p * (eq * (self.pot + ma + ta) - ma)
            return ev
        u = p_none * self.u_win
        o = self.others
        for p, eq, ma, ta, v in outcomes:
            pot_f = self.pot + ma + ta
            vs = o.get(v, 0)
            rest = [x for k, x in o.items() if k != v]
            u_w = icm_value(self.me - ma + pot_f, rest + [vs - ta], self.pay)
            u_l = icm_value(self.me - ma, rest + [vs - ta + pot_f], self.pay)
            u += p * (eq * u_w + (1 - eq) * u_l)
        return (u - self.u_base) / self.du


# ---------------------------------------------------------------------------------- hand reconstruction
class HandInfo:
    __slots__ = ("sb", "bb", "bb_amt", "acts", "pf_raises", "pf_last_raiser", "street_aggr", "limpers",
                 "street", "cur_bet", "contrib", "raises_street", "pf_raise_amts")


def parse_history(hist):
    h = HandInfo()
    h.sb = h.bb = None
    h.bb_amt = 0
    h.acts = {}
    h.pf_raises = 0
    h.pf_last_raiser = None
    h.street_aggr = None
    h.limpers = 0
    h.street = 0
    h.cur_bet = 0
    h.contrib = {}
    h.raises_street = 0
    h.pf_raise_amts = []
    blinds = []
    for e in hist:
        k = e.kind
        s = e.seat
        if k == "blind":
            blinds.append((s, e.amount or 0))
            h.contrib[s] = h.contrib.get(s, 0) + (e.amount or 0)
            if h.contrib[s] > h.cur_bet:
                h.cur_bet = h.contrib[s]
        elif k == "board":
            h.street += 1
            h.cur_bet = 0
            h.contrib = {}
            h.raises_street = 0
            h.street_aggr = None
        elif k == "fold" or k == "check" or k == "call" or k == "raise":
            facing = h.cur_bet > h.contrib.get(s, 0)
            lst = h.acts.get(s)
            if lst is None:
                lst = h.acts[s] = []
            lst.append((h.street, k, facing, h.raises_street))
            if k == "call":
                h.contrib[s] = h.contrib.get(s, 0) + (e.amount or 0)
                if h.street == 0 and h.pf_raises == 0:
                    h.limpers += 1
            elif k == "raise":
                a = e.amount or 0
                h.contrib[s] = a
                if a > h.cur_bet:
                    h.cur_bet = a
                h.raises_street += 1
                h.street_aggr = s
                if h.street == 0:
                    h.pf_raises += 1
                    h.pf_last_raiser = s
                    h.pf_raise_amts.append(a)
    if blinds:
        if len(blinds) >= 2:
            h.sb = blinds[0][0]
            h.bb = blinds[1][0]
            h.bb_amt = blinds[1][1]
        else:
            h.bb = blinds[0][0]
            h.bb_amt = blinds[0][1]
    return h


# ------------------------------------------------------------------------------------------- ranges
def _preflop_band(seat_acts, st, bb_check_ok=True):
    """(lo, hi) percentile band of a seat's preflop range from its preflop actions and stats."""
    vpip = _ratio(st, VPIP, HANDS, 0.28, 6)
    pfr = _ratio(st, PFR, HANDS, 0.14, 6)
    pf3 = _ratio(st, PF3B, PFF, 0.07, 4)
    pff = _ratio(st, PFFOLD, PFF, 0.62, 4)
    best = None
    called_after = False
    for (street, k, facing, rb) in seat_acts:
        if street != 0:
            break
        if k == "raise":
            lvl = 1 + rb
            if best is None or best[0] != "r" or lvl > best[1]:
                best = ("r", lvl)
        elif k == "call":
            if best is not None and best[0] == "r":
                called_after = True
            elif best is None or best[0] != "r":
                best = ("c", rb)
    if best is None:
        return 0.0, 1.0
    if best[0] == "r":
        if best[1] == 1:
            hi = max(0.03, pfr)
        elif best[1] == 2:
            hi = max(0.02, min(pfr, pf3 if pf3 > 0.0 else 0.05))
        else:
            hi = max(0.015, min(pfr, pf3) * 0.6)
        if called_after:
            hi = max(0.015, hi * max(0.35, 1.0 - pff))
        return 0.0, min(1.0, hi)
    rb = best[1]
    if rb == 0:  # limp / complete
        hi = max(0.12, vpip)
        lo = min(pfr * 0.5, hi * 0.5)
        return lo, min(1.0, hi)
    hi = max(0.06, min(1.0, 1.0 - pff))
    if rb >= 2:
        hi *= 0.6
    lo = min(pf3 * 0.6, hi * 0.4)
    return lo, max(0.03, hi)


def _board_feats(board):
    sc = [0, 0, 0, 0]
    bm = 0
    for c in board:
        sc[c.suit] += 1
        bm |= 1 << c.rank
    return sc, bm


def _keys(cands, board, river):
    """Strength key per candidate on this board: made-hand value, bumped up for strong draws."""
    ev = _evaluate
    b = list(board)
    if river:
        return [ev(c[7] + b) for c in cands]
    out = []
    sc, bm = _board_feats(board)
    boesd = OESD[bm]
    fd_two = [x == 2 for x in sc]
    fd_one = [x == 3 for x in sc]
    for c in cands:
        v = ev(c[7] + b)
        if v < KEY_COMBO:
            s0 = c[4]
            if s0 == c[5]:
                fd = fd_two[s0]
            else:
                fd = fd_one[s0] or fd_one[c[5]]
            sd = (not boesd) and OESD[bm | (1 << c[2]) | (1 << c[3])]
            if fd:
                if sd:
                    v = KEY_COMBO
                elif v < KEY_FD:
                    v = KEY_FD
            elif sd and v < KEY_SD:
                v = KEY_SD
        out.append(v)
    return out


def _abs_pct(keys, ref):
    """Fraction of random hands each key beats on this board (ref = sorted keys of random hands)."""
    inv = 1.0 / len(ref)
    bl = bisect_left
    return [bl(ref, k) * inv for k in keys]


def _filter(cands, keys, pcts, lo, hi_drop=2.0, tail=8):
    """Keep combos with absolute strength pct >= lo (and < hi_drop), plus every `tail`-th excluded combo."""
    n = len(cands)
    sel = [i for i in range(n) if lo <= pcts[i] < hi_drop]
    if tail and len(sel) < n:
        out = [i for i in range(n) if not (lo <= pcts[i] < hi_drop)]
        sel += out[tail - 1::tail]
    kc = [cands[i] for i in sel]
    kk = [keys[i] for i in sel]
    kp = [pcts[i] for i in sel]
    if len(kc) < 5:
        order = sorted(range(len(cands)), key=keys.__getitem__, reverse=True)[:5]
        return [cands[i] for i in order], [keys[i] for i in order], [pcts[i] for i in order]
    return kc, kk, kp


class RefCache:
    """Sorted strength keys of random hands per board length, shared by all opponents in a decision."""
    __slots__ = ("board", "dead", "rng", "ref")

    def __init__(self, board, dead, rng):
        self.board = board
        self.dead = dead
        self.rng = rng
        self.ref = {}

    def get(self, blen):
        r = self.ref.get(blen)
        if r is None:
            sample = _strat(0, NCOMBO, 26, self.dead, self.rng.random)
            r = sorted(_keys(sample, self.board[:blen], blen == 5))
            self.ref[blen] = r
        return r


def _strat(i0, i1, m, dead, rr):
    """Jittered stratified sample of m combos from RANKED[i0:i1] (sorted by preflop strength), minus dead cards."""
    step = (i1 - i0) / m
    R = RANKED
    return [c for c in [R[i0 + int((j + rr()) * step)] for j in range(m)] if not (c[6] & dead)]


def build_range(seat_acts, st, board, dead, m, rng, refc):
    """Sampled range for one opponent; a second, independent sample is merged in when the action filters
    leave too few combos for a stable equity estimate."""
    cands, keys, pcts = _build_range(seat_acts, st, board, dead, m, rng, refc)
    if board and len(cands) < 10:
        c2, k2, p2 = _build_range(seat_acts, st, board, dead, max(16, m * 2 // 3), rng, refc)
        cands = cands + c2
        keys = keys + k2
        pcts = pcts + p2
    return cands, keys, pcts


def _build_range(seat_acts, st, board, dead, m, rng, refc):
    """Sampled, action-narrowed range for one opponent. Returns (cands, keys_on_current_board).
    Postflop actions are modelled as absolute-strength thresholds (bots compare their hand strength /
    equity vs random hands to fixed cut-offs), calibrated by the seat's observed frequencies."""
    lo, hi = _preflop_band(seat_acts, st)
    i0 = int(lo * NCOMBO)
    i1 = max(i0 + 8, int(hi * NCOMBO))
    if i1 > NCOMBO:
        i1 = NCOMBO
        i0 = min(i0, NCOMBO - 8)
    span = i1 - i0
    R = RANKED
    if span <= m:
        cands = [R[i] for i in range(i0, i1) if not (R[i][6] & dead)]
    else:
        cands = _strat(i0, i1, m, dead, rng.random)
    if not cands:
        cands = _strat(0, NCOMBO, m, dead, rng.random)
    if not board:
        return cands, None, None
    bet_f = _ratio(st, PBET, POPEN, 0.36, 5)
    fold_f = _ratio(st, PFOLD, PFACED, 0.45, 5)
    raise_f = _ratio(st, PRAISE, PFACED, 0.10, 5)
    nb = len(board)
    keys = None
    pcts = None
    kb = -1
    for (street, k, facing, rb) in seat_acts:
        if street == 0 or k == "fold":
            continue
        blen = 2 + street if street < 3 else 5
        if blen > nb:
            break
        if kb != blen:
            keys = _keys(cands, board[:blen], blen == 5)
            pcts = _abs_pct(keys, refc.get(blen))
            kb = blen
        if k == "raise":
            if facing:
                q = min(0.6, max(0.06, raise_f * 1.5 + 0.03))
                if rb >= 2:
                    q *= 0.6
            else:
                q = min(1.0, max(0.15, bet_f * 1.1))
            if q < 0.97:
                cands, keys, pcts = _filter(cands, keys, pcts, 1.0 - q, 2.0, 9)
        elif k == "call":
            thr = min(0.8, fold_f * 0.85)
            if rb >= 2:
                thr = min(0.9, thr + 0.15)
            if thr > 0.03:
                cands, keys, pcts = _filter(cands, keys, pcts, thr, 2.0, 8)
        elif k == "check" and not facing:
            top = 1.0 - 0.5 * bet_f
            if bet_f > 0.15:
                cands, keys, pcts = _filter(cands, keys, pcts, -1.0, top, 3)
    if kb != nb:
        keys = _keys(cands, board, nb == 5)
        pcts = _abs_pct(keys, refc.get(nb))
    return cands, keys, pcts


def eq_vs(hero, board, cands, keys, my_val, n_iter):
    """Hero equity vs a sampled range. keys sorted desc not required."""
    n = len(cands)
    if n == 0:
        return 0.5
    if my_val is not None:  # river: exact vs the sampled combos
        w = 0.0
        for v in keys:
            if my_val > v:
                w += 1.0
            elif my_val == v:
                w += 0.5
        return w / n
    k = max(2, n_iter // n)
    return _mc(hero, [((c[0], c[1]), 1.0) for c in cands], board, k * n)


# ------------------------------------------------------------------------------------------ the agent
ERRORS = []  # swallowed exceptions (inspected by the dev harness)
UNC_RAISE = 0.03   # model-uncertainty premium per chip risked (x losing share) for big bets / raises / jams
UNC_CALL = 0.01    # same for big calls


class Agent(poker_agent_sdk.Agent):
    def __init__(self):
        self.rng = random.Random()

    last = None

    def act(self, state, memory):
        t0 = perf_counter()
        self.last = None
        try:
            mem = load_mem(memory)
        except Exception:
            mem = load_mem(b"")
        cfg = getattr(state, "config", None)
        start_stack = getattr(cfg, "starting_stack", 2000) or 2000
        try:
            process_events(mem, state.events or [], start_stack)
        except Exception as ex:
            ERRORS.append("events " + repr(ex)[:200])
        try:
            out_mem = marshal.dumps(mem)
        except Exception:
            out_mem = b""
        try:
            action = self.decide(state, mem, t0)
        except Exception as ex:  # never let a bug cost the decision: fall back to check / fold
            ERRORS.append(repr(ex)[:200])
            if len(ERRORS) > 50:
                del ERRORS[:25]
            action = None
        action = self.legalize(state, action)
        return action, out_mem

    # -------------------------------------------------------------------------------- legality guard
    def legalize(self, state, action):
        legal = _legal(state)
        if action is not None:
            kind, amt = action
            if kind == "raise" and "raise" in legal:
                la = legal["raise"]
                lo, hi = int(la.min_amount), int(la.max_amount)
                amt = int(amt)
                if amt < lo:
                    amt = lo
                if amt > hi:
                    amt = hi
                if lo <= amt <= hi:
                    return Action.raise_to(amt)
                kind = "call"
            if kind == "raise":
                kind = "call"
            if kind == "call" and "call" not in legal:
                kind = "check"
            if kind == "check" and "check" not in legal:
                kind = "fold" if "fold" in legal else "call"
            if kind == "fold" and "fold" not in legal:
                kind = "check"
            if kind in legal:
                return {"fold": Action.fold, "check": Action.check, "call": Action.call}[kind]()
        if "check" in legal:
            return Action.check()
        if "fold" in legal:
            return Action.fold()
        return Action.call()

    # ------------------------------------------------------------------------------------- decision
    def decide(self, state, mem, t0):
        legal = _legal(state)
        cards = state.cards
        if not cards or len(cards) < 2:
            return None
        me = state.seat
        seats = {s.seat: s for s in state.seats}
        my = seats[me]
        pot = int(state.pot)
        to_call = int(state.to_call or 0)
        my_stack = int(my.stack)
        my_bet = int(my.bet)
        blinds = state.blinds or [10, 20]
        bb = max(1, int(blinds[1]))
        board_s = state.board or []
        hero = [CARD[cards[0]], CARD[cards[1]]]
        board = [CARD[c] for c in board_s]
        dead = 0
        for c in cards:
            dead |= 1 << CARD_IDX[c]
        for c in board_s:
            dead |= 1 << CARD_IDX[c]
        hist = state.history or []
        hi = parse_history(hist)
        cfg = state.config
        payouts = getattr(cfg, "payouts", None) or [50, 30, 20]
        players_left = int(getattr(state, "players_remaining", 0) or sum(1 for s in state.seats if s.status != "busted"))
        pay = [float(x) for x in payouts[:max(1, players_left)]]

        opps = [s for s in state.seats if s.seat != me and s.status in ("active", "all_in")]
        if not opps:
            return ("check", 0) if "check" in legal else ("call", 0)
        n_players = len(state.seats)
        btn = state.button
        # postflop order (first to act after button)
        live = [s for s in state.seats if s.status != "busted"]
        order = sorted((s.seat for s in live), key=lambda x: (x - btn - 1) % n_players)
        stats = mem["s"]
        bank = getattr(state, "time_bank_ms", None)
        dms = getattr(cfg, "decision_ms", 1) or 1
        fast = (bank is not None and bank < 40 and dms <= 2) or perf_counter() - t0 > 0.0002
        ctx = dict(state=state, legal=legal, me=me, seats=seats, pot=pot, to_call=to_call, my_stack=my_stack, fast=fast,
                   my_bet=my_bet, bb=bb, hero=hero, board=board, dead=dead, hi=hi, opps=opps,
                   order=order, stats=stats, cards=cards, live=live, t0=t0, players_left=players_left, pay=pay)
        if not board:
            return self.preflop(ctx)
        return self.postflop(ctx)

    # -------------------------------------------------------------------------------------- preflop
    def preflop(self, c):
        legal, hi, stats = c["legal"], c["hi"], c["stats"]
        me, seats, bb = c["me"], c["seats"], c["bb"]
        pot, to_call, my_stack, my_bet = c["pot"], c["to_call"], c["my_stack"], c["my_bet"]
        cards = c["cards"]
        r0, r1 = RANKS.index(cards[0][0]), RANKS.index(cards[1][0])
        cls = _class_of(r0, r1, cards[0][1] == cards[1][1])
        pct = PCT[cls]
        live = c["live"]
        n_live = len(live)

        # preflop action order: after the big blind
        bbs = hi.bb if hi.bb is not None else c["order"][min(1, len(c["order"]) - 1)]
        ring = sorted((s.seat for s in live), key=lambda x: (x - bbs - 1) % len(c["state"].seats))
        pos = ring.index(me) if me in ring else 0
        behind = [s for s in ring[pos + 1:] if seats[s].status == "active"]
        n_behind = len(behind)
        opps = c["opps"]
        max_opp_total = max(seats[o.seat].stack + seats[o.seat].bet for o in opps)
        eff = min(my_stack + my_bet, max_opp_total)
        eff_bb = eff / bb
        cur_bet = my_bet + to_call
        raise_la = legal.get("raise")

        def raise_to(total):
            if raise_la is None:
                return None
            lo, hi_ = int(raise_la.min_amount), int(raise_la.max_amount)
            t = int(total)
            if t >= hi_ * 0.8 or (hi_ - t) < 2 * bb:
                t = hi_
            if t < lo:
                t = lo
            return min(t, hi_)

        def st(s):
            return stats.get(s)

        # ---------------------------------------------------------------- unopened (no raise yet)
        if hi.pf_raises == 0:
            limpers = hi.limpers
            # probability everyone behind folds to a raise
            pf_all = 1.0
            for s in behind:
                pf_all *= _ratio(st(s), PFFOLD, PFF, 0.62, 4)
            heads_up = n_live == 2
            base = {1: 0.82 if heads_up else 0.48, 2: 0.40, 3: 0.27, 4: 0.20, 5: 0.16, 6: 0.13}.get(n_behind, 0.11)
            if n_behind == 0:
                # BB with limpers / SB completed: free check, raise for value
                if raise_la is None:
                    return ("check", 0)
                if eff_bb <= 12 and pct <= 0.10:
                    return ("raise", raise_to(raise_la.max_amount))
                if pct <= 0.09 or (pct <= 0.22 and limpers <= 1 and pf_all > 0.45):
                    return ("raise", raise_to(bb * (3.5 + limpers)))
                return ("check", 0)
            # short stack: jam or fold
            if eff_bb <= 13 and raise_la is not None:
                ev = self._jam_ev(c, cls, behind, raise_la.max_amount)
                self.last = ("jam", cls, eff_bb, ev)
                if ev > 0:
                    return ("raise", raise_to(raise_la.max_amount))
                if to_call == 0:
                    return ("check", 0)
                if heads_up and to_call * 2 <= bb and pct <= 0.35:
                    return ("call", 0)
                return ("fold", 0)
            thr = base
            if limpers:
                thr = base * 0.55
            open_size = bb * ((2.2 if eff_bb < 30 else 2.5) + limpers)
            if n_behind == 1 and not heads_up:
                open_size = bb * 3.0
            if raise_la is not None and pct <= thr:
                return ("raise", raise_to(open_size))
            # steal when the players behind fold a lot
            if raise_la is not None and pf_all >= 0.35 and limpers == 0:
                r_in = open_size - my_bet
                p_cont = 0.0
                for s in behind:
                    p_cont = max(p_cont, 1.0 - _ratio(st(s), PFFOLD, PFF, 0.62, 4))
                eqc = _bucket_eq(cls, max(0.02, p_cont))
                realize = 0.88 if n_behind <= 2 else 0.8
                ev = pf_all * pot + (1 - pf_all) * (eqc * realize * (pot + r_in + open_size) - r_in)
                if ev > 0.15 * bb:
                    return ("raise", raise_to(open_size))
            # complete small blind cheaply with decent hands
            if to_call > 0 and to_call * 2 <= bb and n_behind == 1 and pct <= 0.62:
                return ("call", 0)
            if to_call == 0:
                return ("check", 0)
            return ("fold", 0)

        # ---------------------------------------------------------------- facing a raise
        raiser = hi.pf_last_raiser
        rst = st(raiser)
        racts = hi.acts.get(raiser, [])
        lo_b, hi_b = _preflop_band(racts, rst)
        r_seat = seats.get(raiser)
        r_allin = r_seat is not None and (r_seat.status == "all_in" or r_seat.stack == 0)
        p_r = hi_b
        r_total = (r_seat.bet if r_seat is not None else cur_bet)
        r_bb = r_total / bb
        if r_allin or (r_seat is not None and r_seat.stack < r_total * 0.5):
            # all-in (or nearly): range from the seat's observed jam frequency, wider when short
            pj = _ratio(rst, PJAM, HANDS, 0.035, 8)
            if r_bb > 30:
                p_r = min(p_r, max(0.025, pj))
            elif r_bb > 15:
                p_r = min(max(p_r, 0.06), max(0.04, pj * 1.6))
            else:
                p_r = max(0.12 if r_bb > 8 else 0.2, min(1.0, pj * 2.6), min(p_r, 0.3))
        eq = _bucket_eq(cls, p_r)
        # other players who already put money in voluntarily (callers) reduce our equity
        others = []
        for o in opps:
            if o.seat == raiser:
                continue
            acts = hi.acts.get(o.seat)
            if acts and any(a[1] in ("call", "raise") for a in acts if a[0] == 0):
                others.append(o.seat)
        ek = EQK[cls]
        e_rand = EQB[cls][-1]
        for i, s in enumerate(others[:5]):
            lo2, hi2 = _preflop_band(hi.acts.get(s, []), st(s))
            e2 = _bucket_eq(cls, hi2)
            eq *= min(1.0, (ek[i + 1] / ek[i]) * (e2 / e_rand))
        eq = min(eq, 0.95)
        n_beh_act = n_behind  # players still to act who could wake up
        icm = Icm(c["state"], me, my_stack, pot, raiser, c["pay"])
        options = [("fold", 0.0)]
        call_amt = min(to_call, my_stack)
        allin_call = to_call >= my_stack
        # call EV
        if "call" in legal or "check" in legal:
            if allin_call:
                realize = 1.0
            else:
                ip = n_behind == 0 and False
                realize = 0.86 if c["me"] == hi.bb else 0.82
                if r_allin:
                    realize = 1.0
            squeeze_pen = 0.97 ** n_beh_act
            e_call = eq * realize * squeeze_pen
            pot_after = pot + call_amt
            # implied odds for pairs / suited when deep
            implied = 0.0
            if not r_allin and not allin_call and eff > 15 * to_call:
                if r0 == r1:
                    implied = 0.04 * min(eff - to_call, 5 * pot_after)
                elif cards[0][1] == cards[1][1] and abs(r0 - r1) <= 2:
                    implied = 0.015 * min(eff - to_call, 5 * pot_after)
            if call_amt >= 0.3 * (my_stack + my_bet) or r_allin:
                ev_call = icm.equiv(0.0, e_call, call_amt, 0, raiser) + implied - UNC_CALL * call_amt * (1 - eq)
            else:
                ev_call = e_call * pot_after - call_amt + implied
            options.append(("call", ev_call))
        # raise EV (3-bet / 4-bet / jam)
        if raise_la is not None and not r_allin:
            ip_mult = 3.0 if n_behind == 0 else 3.5
            n_raises = hi.pf_raises
            target = cur_bet * (ip_mult if n_raises == 1 else 2.4) + len(others) * cur_bet
            total = raise_to(target)
            if total is not None:
                if total >= 0.4 * (my_stack + my_bet) or eff_bb <= 22:
                    total = raise_to(raise_la.max_amount)
                inv = total - my_bet
                if n_raises == 1:
                    f_r = _ratio(rst, F3FOLD, F3F, 0.5, 3)
                else:
                    f_r = _ratio(rst, F3FOLD, F3F, 0.5, 3) * 0.55
                if total == int(raise_la.max_amount):
                    # facing a jam, the raiser continues roughly with what it would call off with
                    f_r = min(0.95, f_r * 1.1 + 0.05)
                r_total_opp = seats[raiser].stack + seats[raiser].bet if raiser in seats else total
                opp_add = min(total, r_total_opp) - (seats[raiser].bet if raiser in seats else cur_bet)
                my_add = min(total, r_total_opp) - my_bet if r_total_opp < total else inv
                f_r *= _committed(opp_add, pot + my_add + opp_add)
                F = f_r
                for s in others:
                    so = seats[s]
                    o_add = min(total, so.stack + so.bet) - so.bet
                    F *= 0.85 * _committed(o_add, pot + my_add + o_add)
                p_cont = max(0.015, p_r * (1.0 - f_r))
                eq_c = _bucket_eq(cls, p_cont)
                realize3 = 1.0 if total >= int(raise_la.max_amount) else 0.9
                if inv >= 0.3 * (my_stack + my_bet):
                    ev_r = icm.equiv(F, eq_c * realize3, my_add, opp_add, raiser) - UNC_RAISE * my_add * (1 - eq_c)
                else:
                    ev_r = F * pot + (1 - F) * (eq_c * realize3 * (pot + my_add + opp_add) - my_add)
                options.append(("raise", ev_r, total))
        best = max(options, key=lambda x: x[1])
        self.last = ("pre", eq, p_r, options)
        if best[0] == "raise":
            return ("raise", best[2])
        if best[0] == "call":
            return ("call", 0) if "call" in legal else ("check", 0)
        return ("check", 0) if "check" in legal else ("fold", 0)

    def _jam_ev(self, c, cls, behind, jam_total):
        """Chip-equivalent EV (vs folding, ICM-adjusted) of jamming: all fold, or the first caller calls."""
        seats, stats, pot, my_bet = c["seats"], c["stats"], c["pot"], c["my_bet"]
        hi = c["hi"]
        jam_total = int(jam_total)
        p_reach = 1.0
        outs = []
        for s in behind:
            seat = seats[s]
            pc = _ratio(stats.get(s), BIGC, BIGF, 0.22, 3)
            if s == hi.bb:
                pc += 0.06
            their_total = seat.stack + seat.bet
            my_add = min(jam_total, their_total) - my_bet
            their_add = min(jam_total, their_total) - seat.bet
            if their_add / max(1.0, pot + my_add + their_add) < 0.35:
                pc *= 1.4  # good price: wider calls
            pc = max(0.03, min(1.0, pc))
            eq = _bucket_eq(cls, pc)
            outs.append((p_reach * pc, eq, my_add, their_add, s))
            p_reach *= (1 - pc)
        owner = hi.bb if hi.bb is not None else (behind[-1] if behind else None)
        icm = Icm(c["state"], c["me"], c["my_stack"], pot, owner, c["pay"])
        pen = sum(p * ma * (1 - eq) for p, eq, ma, ta, v in outs) * UNC_RAISE
        return icm.jam(outs, p_reach) - pen

    # ------------------------------------------------------------------------------------- postflop
    def postflop(self, c):
        legal, hi, stats = c["legal"], c["hi"], c["stats"]
        me, seats, bb = c["me"], c["seats"], c["bb"]
        pot, to_call, my_stack, my_bet = c["pot"], c["to_call"], c["my_stack"], c["my_bet"]
        hero, board, dead = c["hero"], c["board"], c["dead"]
        rng = self.rng
        opps = c["opps"]
        river = len(board) == 5
        t0 = c["t0"]
        # model up to 3 opponents (aggressor first); all-in players can't fold
        aggr = hi.street_aggr
        opp_seats = [o.seat for o in opps]
        opp_seats.sort(key=lambda s: (s != aggr, -(seats[s].bet)))
        n_opp = len(opp_seats)
        modeled = opp_seats[:3]
        fast = c["fast"]
        m = {1: 50, 2: 36}.get(len(modeled), 24)
        n_iter = {1: 300, 2: 220}.get(len(modeled), 160)
        if fast:
            m = m * 2 // 3
            n_iter //= 2
            modeled = modeled[:2]
        my_val = _evaluate(hero + board) if river else None
        ranges = []
        refc = RefCache(board, dead, rng)
        for s in modeled:
            if ranges and perf_counter() - t0 > 0.0003:
                break  # time guard: remaining opponents approximated below
            cands, keys, pcts = build_range(hi.acts.get(s, []), stats.get(s), board, dead, m, rng, refc)
            ranges.append((s, cands, keys, pcts))
            if perf_counter() - t0 > 0.00025:
                n_iter = 120
        eqs = [eq_vs(hero, board, r[1], r[2], my_val, n_iter) for r in ranges]
        n_extra = n_opp - len(ranges)
        eq = 1.0
        for e in eqs:
            eq *= e
        if n_extra:
            eq *= min(eqs) ** n_extra
        # position: last to act among active players
        actors = [s for s in c["order"] if seats[s].status == "active"]
        ip = bool(actors) and actors[-1] == me
        eff_behind = max((seats[s].stack for s in opp_seats), default=0)
        raise_la = legal.get("raise")
        slow = perf_counter() - t0 > 0.0003
        owner = aggr if (aggr is not None and to_call > 0) else max(opp_seats, key=lambda s: seats[s].stack)
        big_v = max(opp_seats, key=lambda s: seats[s].stack)
        icm = Icm(c["state"], me, my_stack, pot, owner, c["pay"])
        it_small = 150 if not (slow or fast) else 70
        memo = {}

        def response(total, pot_now):
            """Fold probability of everyone and our equity vs the hands that continue, for a bet/raise to `total`.
            Each opponent folds the part of its (modelled) range below its observed fold threshold, scaled by
            bet size; players getting a good price on their remaining stack do not fold."""
            F = 1.0
            eqc = 1.0
            for (s, cands, keys, pcts) in ranges:
                so = seats[s]
                add = min(total - so.bet, so.stack)
                if so.status != "active" or add <= 0:
                    eqc *= eq_vs(hero, board, cands, keys, my_val, it_small)
                    continue
                size = (total - so.bet) / max(1, pot_now)
                thr = min(0.9, _ratio(stats.get(s), PFOLD, PFACED, 0.45, 5) * 0.85)
                thr *= 0.75 + 0.35 * (size if size < 1.5 else 1.5)
                n = len(cands)
                cont = [i for i in range(n) if pcts[i] >= thr]
                f = 1.0 - len(cont) / n
                f *= _committed(add, pot_now + (total - my_bet) + add)
                mk = (s, len(cont)) if (f >= 0.02 and len(cont) >= 3) else (s, -1)
                ec = memo.get(mk)
                if ec is None:
                    if mk[1] < 0:
                        ec = eq_vs(hero, board, cands, keys, my_val, it_small)
                    else:
                        ec = eq_vs(hero, board, [cands[i] for i in cont], [keys[i] for i in cont], my_val, it_small)
                    memo[mk] = ec
                F *= f
                eqc *= ec
            if n_extra:
                F *= 0.45 ** n_extra
                eqc *= min(eqs) ** n_extra
            return F, eqc

        def legal_total(total):
            lo, hi_ = int(raise_la.min_amount), int(raise_la.max_amount)
            t = int(total)
            if t >= 0.85 * hi_ or hi_ - t < pot * 0.25:
                t = hi_
            if t < lo:
                t = lo
            return min(t, hi_)

        options = []
        if to_call == 0:
            r_chk = 1.0 if river else (0.93 if len(board) == 4 else 0.88)
            if ip:
                r_chk += 0.04
            options.append(("check", eq * pot * r_chk, 0))
            if raise_la is not None:
                fracs = (0.4, 0.75) if not (slow or fast) else (0.6,)
                totals = [legal_total(my_bet + max(bb, fr * pot)) for fr in fracs]
                if my_stack <= 1.6 * pot:
                    totals.append(int(raise_la.max_amount))
                seen = set()
                for total in totals:
                    if total in seen:
                        continue
                    seen.add(total)
                    b = total - my_bet
                    F, eqc = response(total, pot)
                    allin = total >= int(raise_la.max_amount)
                    r_bet = 1.0 if (river or allin) else 0.95
                    called = min(b, eff_behind)
                    if b >= 0.3 * (my_stack + my_bet):
                        ev = icm.equiv(F, eqc * r_bet, b, called, big_v) - UNC_RAISE * b * (1 - eqc)
                    else:
                        ev = F * pot + (1 - F) * (eqc * r_bet * (pot + b + called) - b)
                    options.append(("raise", ev, total))
        else:
            options.append(("fold", 0.0, 0))
            call_amt = min(to_call, my_stack)
            allin_call = to_call >= my_stack
            if river or allin_call:
                r_call = 1.0
            else:
                r_call = 0.9 if len(board) == 3 else 0.95
                if ip:
                    r_call += 0.04
            # drawing hands get some implied odds when stacks are deep
            implied = 0.0
            if not river and not allin_call:
                hk = _keys([(hero[0], hero[1], hero[0].rank, hero[1].rank, hero[0].suit, hero[1].suit, 0, hero)], board, False)[0]
                raw = _evaluate(hero + board)
                if hk > raw and raw < KEY_COMBO:
                    implied = 0.12 * min(eff_behind, pot) * (1.0 if len(board) == 3 else 0.7)
            if call_amt >= 0.3 * (my_stack + my_bet):
                ev_call = icm.equiv(0.0, eq * r_call, call_amt, 0, owner) + implied - UNC_CALL * call_amt * (1 - eq)
            else:
                ev_call = eq * r_call * (pot + call_amt) - call_amt + implied
            options.append(("call", ev_call, 0))
            if raise_la is not None and not allin_call:
                cur = my_bet + to_call
                totals = [legal_total(cur + max(cur - my_bet, 0) + 0.8 * (pot + to_call))]
                if my_stack <= 2.5 * (pot + to_call) or slow:
                    totals.append(int(raise_la.max_amount))
                seen = set()
                for total in totals:
                    if total in seen:
                        continue
                    seen.add(total)
                    F, eqc = response(total, pot)
                    a_seat = seats.get(aggr) if aggr is not None else None
                    a_bet = a_seat.bet if a_seat is not None else cur
                    a_total = (a_seat.stack + a_seat.bet) if a_seat is not None else total
                    my_add = min(total, max(a_total, my_bet)) - my_bet
                    opp_add = max(0, min(total, a_total) - a_bet)
                    allin = total >= int(raise_la.max_amount)
                    r_r = 1.0 if (river or allin) else 0.95
                    if my_add >= 0.3 * (my_stack + my_bet):
                        ev = icm.equiv(F, eqc * r_r, my_add, opp_add, owner) - UNC_RAISE * my_add * (1 - eqc)
                    else:
                        ev = F * pot + (1 - F) * (eqc * r_r * (pot + my_add + opp_add) - my_add)
                    options.append(("raise", ev, total))
        best = max(options, key=lambda x: x[1])
        self.last = ("post", eq, [len(r[1]) for r in ranges], options)
        if best[0] == "raise":
            return ("raise", best[2])
        return (best[0], 0)


# keep the import-time tables out of the cyclic GC's way
gc.collect()
try:
    gc.freeze()
except AttributeError:
    pass
