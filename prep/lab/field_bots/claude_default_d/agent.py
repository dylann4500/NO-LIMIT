"""claude_default_d: No-Limit Hold'em sit-and-go bot.

Design (see NOTES.md):
  * Preflop: precomputed 169x169 heads-up equity matrix (preflop.json) -> equity of our hand vs the
    top-x% range we attribute to each opponent from their observed VPIP/PFR/3-bet/jam rates.
    Deep stacks: positional open ranges + equity-vs-range call/3-bet logic.
    Short stacks: ICM (Malmuth-Harville) expected-value push/fold and all-in calls.
  * Postflop: one eval7 Monte Carlo (in C, ~40us) vs the main villain's preflop range, then a
    rank-model correction for the villain's betting/calling frequency, draw floors, and an EV
    comparison of bet sizes vs checking that uses each seat's observed fold-to-bet rate.
  * Per-table opponent statistics live in `memory` (marshal, a few hundred bytes).
  * Every decision is wrapped: any exception falls back to a legal check/fold; raise totals are
    clamped to the legal interval as ints.
"""
import gc
import json
import marshal
import os
import random
import sys
import time
import traceback

import eval7
import numpy as np

import poker_agent_sdk
from poker_agent_sdk import Action

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEBUG = bool(os.environ.get("CDD_DEBUG"))
_TRACE = bool(os.environ.get("CDD_TRACE"))
_RANKS = "23456789TJQKA"
_SUITS = "shdc"
_RV = {r: i for i, r in enumerate(_RANKS)}
_CARD = {r + s: eval7.Card(r + s) for r in _RANKS for s in _SUITS}

with open(os.path.join(_HERE, "preflop.json")) as _f:
    _D = json.load(_f)
_CLASSES = _D["classes"]
_CIDX = {c: i for i, c in enumerate(_CLASSES)}
_NCOMBO = _D["combos"]
_HU = np.array(_D["hu"], dtype=float)
_MULTI = _D["multi"]


def _class_name(c1, c2):
    r1, r2 = c1[0], c2[0]
    if _RV[r1] < _RV[r2]:
        r1, r2 = r2, r1
    if r1 == r2:
        return r1 + r2
    return r1 + r2 + ("s" if c1[1] == c2[1] else "o")


_HCLS = {}
for _a in _CARD:
    for _b in _CARD:
        if _a != _b:
            _HCLS[(_a, _b)] = _CIDX[_class_name(_a, _b)]

# Ranking by heads-up equity vs a random hand (how most bots rank hands).
_W = np.array(_NCOMBO, dtype=float)
_VR = (_HU @ _W) / _W.sum()
_ORDER = sorted(range(169), key=lambda i: -_VR[i])
_PCT = [0.0] * 169  # midpoint percentile of each class (0 = best)
_acc = 0.0
for _i in _ORDER:
    _PCT[_i] = (_acc + _NCOMBO[_i] / 2.0) / 1326.0
    _acc += _NCOMBO[_i]

# EQR[h][b]: equity of class h vs the top (b+1)% of hands.
_NB = 100
_EQR_np = np.zeros((169, _NB))
for _b in range(_NB):
    _x = (_b + 1) / _NB * 1326.0
    _wt = np.zeros(169)
    _acc = 0.0
    for _i in _ORDER:
        if _acc >= _x:
            break
        _take = min(_NCOMBO[_i], _x - _acc)
        _wt[_i] = _take
        _acc += _take
    _EQR_np[:, _b] = (_HU @ _wt) / _wt.sum()
_EQR = _EQR_np.tolist()


def _eqv(h, pct):
    b = int(pct * _NB + 0.5) - 1
    if b < 0:
        b = 0
    elif b >= _NB:
        b = _NB - 1
    return _EQR[h][b]


# Villain ranges for postflop Monte Carlo: top-x% combos, shuffled (eval7 cycles through the list),
# subsampled to keep the per-call conversion cost low.
_RB = (0.04, 0.07, 0.10, 0.14, 0.18, 0.23, 0.28, 0.35, 0.43, 0.52, 0.64, 0.80, 1.0)
_MAXC = 300


def _combos_of(cls):
    a, b = cls[0], cls[1]
    res = []
    if len(cls) == 2:
        for x in range(4):
            for y in range(x + 1, 4):
                res.append((a + _SUITS[x], b + _SUITS[y]))
    elif cls[2] == "s":
        for x in range(4):
            res.append((a + _SUITS[x], b + _SUITS[x]))
    else:
        for x in range(4):
            for y in range(4):
                if x != y:
                    res.append((a + _SUITS[x], b + _SUITS[y]))
    return res


_rng0 = random.Random(20261106)
_RANGES = []
for _p in _RB:
    _lst = []
    _acc = 0.0
    for _i in _ORDER:
        if _acc >= _p * 1326.0 - 0.5:
            break
        for _x, _y in _combos_of(_CLASSES[_i]):
            _lst.append(((_CARD[_x], _CARD[_y]), 1.0))
        _acc += _NCOMBO[_i]
    _rng0.shuffle(_lst)
    _RANGES.append(_lst[:_MAXC])


def _range_for(pct):
    for i, p in enumerate(_RB):
        if pct <= p + 1e-9:
            return _RANGES[i]
    return _RANGES[-1]


# ---------------------------------------------------------------- per-seat statistics
# counters: 0 hands, 1 vpip, 2 pfr, 3 faced-pf-raise, 4 folded-to-pf-raise, 5 reraised, 6 post bet-opps,
#           7 post bets, 8 post faced-bet, 9 post folds, 10 post raises, 11 big pf raises (>=12bb), 12 post calls
_NS = 13


def _new_mem():
    return {"v": 1, "s": {}, "p": [0, 0, 0, 0, 0, 0, 0]}


def _load(memory):
    if not memory:
        return _new_mem()
    m = marshal.loads(memory)
    if not isinstance(m, dict) or m.get("v") != 1:
        return _new_mem()
    return m


def _ingest(mem, events):
    if not events:
        return
    st = mem["s"]
    street, curbet, nr, cm, vm, pm, bba = mem["p"]
    for e in events:
        k = e.kind
        if k == "hand":
            street = 0
            curbet = 0
            nr = 0
            cm = vm = pm = 0
            continue
        if k == "blind":
            a = e.amount or 0
            if a > curbet:
                curbet = a
                bba = a
            continue
        if k == "board":
            street += 1
            curbet = 0
            continue
        if k not in ("fold", "check", "call", "raise"):
            continue
        s = e.seat
        if s is None:
            continue
        row = st.get(s)
        if row is None:
            row = [0] * _NS
            st[s] = row
        bit = 1 << (s & 63)
        if street == 0:
            if not cm & bit:
                cm |= bit
                row[0] += 1
            if k == "fold":
                if nr > 0:
                    row[3] += 1
                    row[4] += 1
            elif k == "call":
                if nr > 0:
                    row[3] += 1
                if not vm & bit:
                    vm |= bit
                    row[1] += 1
            elif k == "raise":
                if nr > 0:
                    row[3] += 1
                    row[5] += 1
                if not vm & bit:
                    vm |= bit
                    row[1] += 1
                if not pm & bit:
                    pm |= bit
                    row[2] += 1
                a = e.amount or 0
                if bba and a >= 12 * bba:
                    row[11] += 1
                nr += 1
                if a > curbet:
                    curbet = a
        else:
            if k == "check":
                row[6] += 1
            elif k == "raise":
                if curbet == 0:
                    row[6] += 1
                    row[7] += 1
                else:
                    row[8] += 1
                    row[10] += 1
                a = e.amount or 0
                if a > curbet:
                    curbet = a
            elif k == "call":
                row[8] += 1
                row[12] += 1
            elif k == "fold":
                row[8] += 1
                row[9] += 1
    mem["p"] = [street, curbet, nr, cm, vm, pm, bba]


def _rate(row, num, den, prior, k):
    if row is None:
        return prior
    return (row[num] + prior * k) / (row[den] + k)


def _name(v):
    """Normalize an SDK enum/str value to a lower-case plain string."""
    if v.__class__ is str:
        return v
    v = getattr(v, "value", v)
    v = str(v).lower()
    if "." in v:
        v = v.rsplit(".", 1)[-1]
    return v


def _get(o, k, d=None):
    try:
        return getattr(o, k)
    except AttributeError:
        try:
            return o[k]
        except Exception:
            return d


class _Ev:
    """Plain event record (accepts SDK objects or dicts)."""
    __slots__ = ("kind", "seat", "amount", "cards")

    def __init__(self, e):
        self.kind = _name(_get(e, "kind", ""))
        self.seat = _get(e, "seat")
        self.amount = _get(e, "amount")
        self.cards = _get(e, "cards")


def _norm_events(evs):
    if not evs:
        return []
    e0 = evs[0]
    if getattr(e0, "kind", None).__class__ is str:
        return evs  # fast path: SDK objects with plain-string kinds
    return [_Ev(e) for e in evs]


class _St:
    """Plain seat record."""
    __slots__ = ("seat", "stack", "bet", "status")

    def __init__(self, s):
        self.seat = _get(s, "seat")
        self.stack = int(_get(s, "stack", 0) or 0)
        self.bet = int(_get(s, "bet", 0) or 0)
        self.status = _name(_get(s, "status", "active"))


class _Opp:
    """Regularized tendencies of one seat."""
    __slots__ = ("vpip", "pfr", "f2r", "rr", "bet", "f2b", "rz", "jam", "n")

    def __init__(self, row):
        self.n = row[0] if row else 0
        self.vpip = _rate(row, 1, 0, 0.30, 6)
        self.pfr = _rate(row, 2, 0, 0.17, 6)
        self.f2r = _rate(row, 4, 3, 0.55, 5)
        self.rr = _rate(row, 5, 3, 0.08, 6)
        self.bet = _rate(row, 7, 6, 0.40, 5)
        self.f2b = _rate(row, 9, 8, 0.42, 5)
        self.rz = _rate(row, 10, 8, 0.12, 5)
        self.jam = _rate(row, 11, 0, 0.03, 10)


# ---------------------------------------------------------------- ICM
def _icm(stacks, i, pay):
    """Malmuth-Harville equity of player i. stacks: list of chips (>0 for live players)."""
    n = len(stacks)
    k = len(pay)
    if k > n:
        k = n
    if k > 3 and n > 6:
        k = 3
    total = 0.0
    for s in stacks:
        total += s
    si = stacks[i]
    if si <= 0:
        return 0.0
    if total <= 0:
        return 0.0

    def rec(rem, used, p):
        res = si / rem * pay[p]
        if p + 1 < k:
            for j in range(n):
                if j == i or (used >> j) & 1:
                    continue
                sj = stacks[j]
                if sj <= 0:
                    continue
                r2 = rem - sj
                if r2 <= 0:
                    continue
                res += sj / rem * rec(r2, used | (1 << j), p + 1)
        return res

    return rec(total, 0, 0)


# ---------------------------------------------------------------- helpers
def _legal(state):
    m = {}
    for la in state.legal_actions:
        k = la.kind
        name = getattr(k, "value", k)
        name = str(name).lower()
        if "." in name:
            name = name.rsplit(".", 1)[-1]
        m[name] = la
    return m


def _safe(L):
    if "check" in L:
        return Action.check()
    if "fold" in L:
        return Action.fold()
    if "call" in L:
        return Action.call()
    return Action.check()


def _passive(L):
    if "check" in L:
        return Action.check()
    return Action.fold() if "fold" in L else _safe(L)


def _call_or_check(L):
    if "call" in L:
        return Action.call()
    if "check" in L:
        return Action.check()
    return _safe(L)


def _raise(L, total, allin_frac=0.80):
    la = L.get("raise")
    if la is None:
        return _call_or_check(L)
    lo = int(la.min_amount)
    hi = int(la.max_amount)
    t = int(total)
    if t >= hi * allin_frac:
        t = hi
    if t < lo:
        t = lo
    if t > hi:
        t = hi
    return Action.raise_to(t)


def _draw_eq(hole, board):
    """Rough equity floor from draws (flush / straight) when cards are still to come."""
    nb = len(board)
    if nb >= 5:
        return 0.0
    cards = hole + board
    suits = {}
    for c in cards:
        suits[c[1]] = suits.get(c[1], 0) + 1
    fd = False
    for s, cnt in suits.items():
        if cnt == 4 and (hole[0][1] == s or hole[1][1] == s):
            fd = True
    ranks = 0
    for c in cards:
        r = _RV[c[0]] + 1
        ranks |= 1 << r
        if r == 13:
            ranks |= 1  # wheel ace
    hr = 0
    for c in hole:
        r = _RV[c[0]] + 1
        hr |= 1 << r
        if r == 13:
            hr |= 1
    oesd = gut = False
    for lo in range(0, 10):
        win = ((1 << 5) - 1) << lo
        have = ranks & win
        cnt = bin(have).count("1")
        if cnt == 4 and (have & hr):
            missing = win & ~have
            if missing == 1 << lo or missing == 1 << (lo + 4):
                oesd = True
            else:
                gut = True
    if nb == 3:
        e = 0.0
        if fd:
            e = 0.35
        if oesd:
            e = 0.50 if fd else max(e, 0.31)
        elif gut:
            e = max(e, 0.45 if fd else 0.16)
        return e
    e = 0.0
    if fd:
        e = 0.19
    if oesd:
        e = 0.33 if fd else max(e, 0.17)
    elif gut:
        e = max(e, 0.09)
    return e


with open(os.path.join(_HERE, "cond.json")) as _f:
    _CD = json.load(_f)
_CBS = _CD["bs"]
_CNE = _CD["ne"]
_CT = {int(k): v for k, v in _CD["cond"].items()}


def _cond(E, b, street, w=0.55):
    """Equity vs the strongest b-fraction of a range, given equity E vs the whole range.
    Calibrated offline (gen_cond.py) for strength-ranked betting/calling ranges, blended with E."""
    if b >= 0.999:
        return E
    tab = _CT.get(street) or _CT[1]
    if b <= _CBS[0]:
        r0, r1, t = tab[0], tab[0], 0.0
    elif b >= _CBS[-1]:
        r0, r1 = tab[-1], None
        t = (b - _CBS[-1]) / (1.0 - _CBS[-1])
    else:
        i = int(b * 10) - 1
        if i < 0:
            i = 0
        if i > len(_CBS) - 2:
            i = len(_CBS) - 2
        r0, r1 = tab[i], tab[i + 1]
        t = (b - _CBS[i]) / (_CBS[i + 1] - _CBS[i])
    x = E * _CNE - 0.5
    if x < 0.0:
        x = 0.0
    j = int(x)
    if j >= _CNE - 1:
        j = _CNE - 2
        f = 1.0
    else:
        f = x - j
    v0 = r0[j] + (r0[j + 1] - r0[j]) * f
    if r1 is None:
        v = v0 + (E - v0) * t
    else:
        v1 = r1[j] + (r1[j + 1] - r1[j]) * f
        v = v0 + (v1 - v0) * t
    if v > E:
        v = E
    return w * v + (1.0 - w) * E


# ---------------------------------------------------------------- hand parsing
class _Hand:
    __slots__ = ("sb", "bb", "pf_raises", "limpers", "pf_callers", "aggr", "calls", "acted",
                 "contrib", "street", "pot_before_bet", "last_bet")


def _parse(history):
    H = _Hand()
    H.sb = H.bb = None
    H.pf_raises = []
    H.limpers = []
    H.pf_callers = []
    H.aggr = [[], [], [], []]   # per street list of (seat, total, pot_before)
    H.calls = [[], [], [], []]  # per street list of seats that called a bet
    H.acted = [set(), set(), set(), set()]
    contrib = {}
    street = 0
    pot = 0
    curbet = 0
    blinds = []
    for e in history:
        k = e.kind
        s = e.seat
        if k == "board":
            street += 1
            if street > 3:
                street = 3
            contrib = {}
            curbet = 0
            continue
        if k == "ante":
            pot += e.amount or 0
            continue
        if k == "blind":
            a = e.amount or 0
            blinds.append((s, a))
            contrib[s] = contrib.get(s, 0) + a
            pot += a
            if contrib[s] > curbet:
                curbet = contrib[s]
            continue
        if k == "call":
            a = e.amount or 0
            contrib[s] = contrib.get(s, 0) + a
            pot += a
            H.acted[street].add(s)
            if street == 0:
                if not H.pf_raises:
                    H.limpers.append(s)
                else:
                    H.pf_callers.append(s)
            else:
                H.calls[street].append(s)
        elif k == "raise":
            a = e.amount or 0
            prev = contrib.get(s, 0)
            H.aggr[street].append((s, a, pot, curbet))
            pot += a - prev
            contrib[s] = a
            if a > curbet:
                curbet = a
            H.acted[street].add(s)
            if street == 0:
                H.pf_raises.append((s, a))
        elif k in ("check", "fold"):
            H.acted[street].add(s)
    if blinds:
        if len(blinds) >= 2:
            H.sb = blinds[0][0]
            H.bb = blinds[1][0]
            if blinds[0][1] > blinds[1][1]:
                H.sb, H.bb = H.bb, H.sb
        else:
            H.bb = blinds[0][0]
    H.contrib = contrib
    H.street = street
    return H


# ---------------------------------------------------------------- agent
class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        t0 = time.perf_counter()
        try:
            mem = _load(memory)
        except Exception:
            mem = _new_mem()
        try:
            _ingest(mem, _norm_events(state.events))
        except Exception:
            if _DEBUG:
                traceback.print_exc(file=sys.stderr)
        L = None
        action = None
        try:
            L = _legal(state)
            action = _Decider(state, mem, L, t0).decide()
        except Exception:
            if _DEBUG:
                traceback.print_exc(file=sys.stderr)
            action = None
        if action is None:
            try:
                action = _safe(L if L is not None else _legal(state))
            except Exception:
                action = Action.fold()
        try:
            out = marshal.dumps(mem)
        except Exception:
            out = b""
        return action, out


class _Decider:
    def __init__(self, state, mem, L, t0):
        self.st = state
        self.mem = mem
        self.L = L
        self.t0 = t0
        self.me = state.seat
        self.seats = {}
        norm = [_St(s) for s in state.seats]
        for s in norm:
            self.seats[s.seat] = s
        bl = state.blinds or [10, 20]
        self.bb = max(1, int(bl[1]))
        self.sbv = int(bl[0])
        cfg = getattr(state, "config", None)
        pay = None
        if cfg is not None:
            pay = getattr(cfg, "payouts", None)
        if not pay:
            pay = [50, 30, 20]
        self.pay_full = [float(x or 0) for x in pay]
        self.payouts = [float(x) for x in pay if x and x > 0] or [1.0]
        self.my = self.seats[self.me]
        self.my_total = self.my.stack + self.my.bet
        self.to_call = int(state.to_call or 0)
        self.pot = int(state.pot or 0)
        self.H = _parse(_norm_events(state.history or []))
        self.alive = [s for s in norm if s.status != "busted"]
        self.alive.sort(key=lambda s: s.seat)
        self.opps_in = [s for s in self.alive if s.seat != self.me and s.status in ("active", "all_in")]
        bank = getattr(state, "time_bank_ms", None)
        self.bank = bank if isinstance(bank, (int, float)) else 0

    # -------------------------------------------------- utilities
    def opp(self, seat):
        return _Opp(self.mem["s"].get(seat))

    def total(self, s):
        return s.stack + s.bet

    def order_from(self, start_after):
        """Alive seats in clockwise order starting after seat `start_after`."""
        seats = [s.seat for s in self.alive]
        if not seats:
            return []
        idx = 0
        for i, x in enumerate(seats):
            if x > start_after:
                idx = i
                break
        else:
            idx = 0
        return seats[idx:] + seats[:idx]

    def icm_stacks(self, deltas):
        """ICM equity for me after applying chip deltas {seat: final_total_chips}."""
        stacks = []
        mi = 0
        for s in self.alive:
            v = deltas.get(s.seat)
            if v is None:
                v = s.stack
            if s.seat == self.me:
                mi = len(stacks)
            stacks.append(max(0.0, float(v)))
        if stacks[mi] <= 0:
            # busting now finishes us in the last remaining place
            place = sum(1 for x in stacks if x > 0) + 1
            return self.pay_full[place - 1] if place - 1 < len(self.pay_full) else 0.0
        return _icm(stacks, mi, self.payouts)

    def decide(self):
        L = self.L
        if not L:
            return None
        if len(L) == 1:
            k = next(iter(L))
            if k == "raise":
                return _raise(L, L[k].min_amount)
            return {"fold": Action.fold, "check": Action.check, "call": Action.call}.get(k, Action.fold)()
        cards = self.st.cards
        if not cards or len(cards) < 2:
            return None
        self.hole = [cards[0], cards[1]]
        self.h = _HCLS[(cards[0], cards[1])]
        if not self.st.board:
            return self.preflop()
        return self.postflop()

    # -------------------------------------------------- preflop
    def preflop(self):
        L, H, bb = self.L, self.H, self.bb
        h = self.h
        pct = _PCT[h]
        to_call = self.to_call
        pot = self.pot
        me = self.me
        opps = self.opps_in
        if not opps:
            return _call_or_check(L)
        max_opp_total = max(self.total(o) for o in opps)
        eff = min(self.my_total, max_opp_total)
        eff_bb = eff / bb
        raises = H.pf_raises
        bb_seat = H.bb if H.bb is not None else -1
        # preflop action order: after BB around to BB
        order = self.order_from(bb_seat) if bb_seat >= 0 else self.order_from(self.st.button)
        if me in order:
            pos = order.index(me)
            after = order[pos + 1:]
        else:
            after = []
        behind = [self.seats[x] for x in after if self.seats[x].status == "active" and x != me]
        n_behind = len(behind)

        if not raises:
            return self.pf_unopened(h, pct, eff_bb, behind, n_behind, bb_seat)
        return self.pf_facing_raise(h, pct, eff_bb, behind)

    def steal_fold_prob(self, behind, size_bb):
        p = 1.0
        for o in behind:
            od = self.opp(o.seat)
            f = od.f2r
            # bigger raises fold more often; shoves fold more than min-raises
            f = f + (1.0 - f) * min(0.5, max(0.0, (size_bb - 2.5) * 0.04))
            if o.seat == self.H.bb:
                f *= 0.92  # BB defends a bit more (price)
            p *= min(0.97, max(0.03, f))
        return p

    def pf_unopened(self, h, pct, eff_bb, behind, n_behind, bb_seat):
        L, bb, H = self.L, self.bb, self.H
        me = self.me
        limpers = [x for x in H.limpers if x != me and self.seats.get(x) is not None and self.seats[x].status != "folded"]
        can_check = "check" in L
        # ---- short stack: push / fold by ICM EV
        if eff_bb <= 13.0 or self.my_total <= 13 * bb:
            ev_push, ev_fold = self.push_ev(h, behind, limpers)
            if can_check:
                # BB option: checking keeps our equity in a cheap pot
                ev_check = ev_fold + 0.35 * self.icm_gain_small(self.pot * _MULTI[h][min(6, max(0, len(self.opps_in) - 1))])
                if ev_push > ev_check:
                    return _raise(L, self.my_total + 1)
                return Action.check()
            # small-blind complete option is skipped (raise-or-fold play is stronger vs bots)
            if ev_push > ev_fold:
                return _raise(L, self.my_total + 1)
            return _passive(L)

        # ---- deeper: positional opening ranges
        open_tbl = {0: 0.40, 1: 0.45, 2: 0.42, 3: 0.29, 4: 0.22, 5: 0.18, 6: 0.15, 7: 0.13}
        thr = open_tbl.get(n_behind, 0.11)
        if limpers:
            # isolate limpers: tighter, but limpers are usually weak
            lv = sum(self.opp(x).pfr for x in limpers) / len(limpers)
            thr = max(0.07, thr * (0.55 if lv > 0.25 else 0.7)) - 0.01 * (len(limpers) - 1)
            size = 3.5 * bb + bb * len(limpers)
        else:
            size = 2.5 * bb if eff_bb >= 25 else 2.2 * bb
            if H.sb == me and n_behind == 1:
                size = 3.0 * bb
            pf = self.steal_fold_prob(behind, size / bb)
            # pure steal: profitable when everyone behind folds often enough
            if pf >= 0.62:
                thr = max(thr, 0.75)
            elif pf >= 0.50:
                thr = max(thr, thr + (pf - 0.45) * 1.2)
        if pct <= thr:
            return _raise(L, size)
        if can_check:
            return Action.check()
        # cheap limp / complete with speculative hands when deep
        if limpers and eff_bb >= 30 and self.to_call <= bb and pct <= 0.38:
            return _call_or_check(L)
        if H.sb == me and self.to_call <= bb * 0.5 + 1 and limpers and pct <= 0.55:
            return _call_or_check(L)
        return _passive(L)

    def icm_gain_small(self, chips):
        # cheap linear approximation of the ICM value of a small chip gain
        return chips * (self.payouts[0] / max(1.0, sum(self.total(s) for s in self.alive))) * 0.8

    def behind_count(self, seat):
        """Players left to act behind `seat` in preflop order (blinds last), counted at the start of the hand."""
        bb_seat = self.H.bb if self.H.bb is not None else -1
        order = self.order_from(bb_seat) if bb_seat >= 0 else self.order_from(self.st.button)
        if seat not in order:
            return 3
        return max(1, len(order) - 1 - order.index(seat))

    def jam_width(self, o, total_bb):
        """Shove range width: Nash-like by stack depth and players behind, floored by observed jam rate."""
        od = self.opp(o.seat)
        k = self.behind_count(o.seat)
        nash = 4.6 / (max(1.0, total_bb) ** 0.9) / (k ** 0.7)
        w = max(od.jam * 1.1, nash)
        return min(0.95, max(0.03, w))

    def caller_pct(self, o, call_bb, n_left):
        """Fraction of hands opponent o calls a shove with (needs call_bb more big blinds)."""
        od = self.opp(o.seat)
        base = 2.0 / (max(1.0, call_bb) ** 0.8)
        base *= 0.85 ** max(0, n_left - 1)
        loos = od.vpip / 0.30
        c = base * (0.6 + 0.4 * loos)
        if od.n >= 8 and od.f2r > 0.9:
            c *= 0.4
        return min(0.95, max(0.02, c))

    def push_ev(self, h, behind, limpers):
        """ICM EV of shoving vs folding (unopened or limped pot)."""
        me = self.me
        my_total = self.my_total
        my_bet = self.my.bet
        pot = self.pot
        base = {}
        for s in self.alive:
            base[s.seat] = s.stack
        # fold: we keep our stack behind; the pot goes to the BB (approximation)
        fold_to = self.H.bb if (self.H.bb is not None and self.H.bb != me) else (behind[-1].seat if behind else None)
        d = dict(base)
        if fold_to is not None and fold_to in d:
            d[fold_to] = d[fold_to] + pot
        ev_fold = self.icm_stacks(d)
        # all fold: we win the pot
        d = dict(base)
        d[me] = base[me] + pot
        u_steal = self.icm_stacks(d)
        callers = list(behind) + [self.seats[x] for x in limpers if self.seats[x].status == "active"]
        pnone = 1.0
        cand = []
        nleft = len(callers)
        for i, o in enumerate(callers):
            R = min(my_total, self.total(o))
            call_bb = (R - o.bet) / self.bb
            c = self.caller_pct(o, call_bb, nleft - i)
            w = pnone * c
            cand.append((w, o, c, R))
            pnone *= (1.0 - c)
        ev = pnone * u_steal
        cand.sort(key=lambda x: -x[0])
        rest_w = 0.0
        for w, o, c, R in cand[2:]:
            rest_w += w
        top = cand[:2]
        tw = sum(x[0] for x in top)
        for w, o, c, R in top:
            if tw <= 0:
                break
            w = w + rest_w * (w / tw)
            E = _eqv(h, c)
            if len(callers) > 1 and c > 0.3:
                E *= 0.97
            pot_final = pot - my_bet - o.bet + 2 * R
            dw = dict(base)
            dw[me] = my_total - R + pot_final
            dw[o.seat] = self.total(o) - R
            dl = dict(base)
            dl[me] = my_total - R
            dl[o.seat] = self.total(o) - R + pot_final
            ev += w * (E * self.icm_stacks(dw) + (1.0 - E) * self.icm_stacks(dl))
        return ev, ev_fold

    def raiser_pct(self, seat, nth, amount):
        """Estimated range width for the nth (0-based) preflop raise by seat to `amount`."""
        o = self.seats[seat]
        od = self.opp(seat)
        if nth == 0:
            k = self.behind_count(seat)
            p = od.pfr * {1: 1.8, 2: 1.7, 3: 1.3, 4: 1.0, 5: 0.85, 6: 0.75}.get(k, 0.7)
        elif nth == 1:
            p = od.rr
        else:
            p = od.rr * 0.5
        tot = self.total(o)
        allin = o.status == "all_in" or o.stack <= 0 or amount >= 0.6 * tot
        if allin or amount >= 12 * self.bb:
            p = min(p, max(od.jam * 1.2, 0.025)) if nth == 0 else p
            p = max(p, self.jam_width(o, tot / self.bb)) if allin else p
        # bigger opens are usually stronger
        if nth == 0 and amount > 4 * self.bb and not allin:
            p *= 0.8
        floor = 0.05 if nth == 0 else (0.035 if nth == 1 else 0.025)
        return min(1.0, max(floor, p))

    def pf_facing_raise(self, h, pct, eff_bb, behind):
        L, H, bb, me = self.L, self.H, self.bb, self.me
        to_call = self.to_call
        pot = self.pot
        raises = H.pf_raises
        vseat, vamt = raises[-1]
        if vseat == me or vseat not in self.seats:
            return _call_or_check(L)
        v = self.seats[vseat]
        nth = len(raises) - 1
        vp = self.raiser_pct(vseat, nth, vamt)
        E = _eqv(h, vp)
        # other opponents that put voluntary chips in and are still in the hand
        others = set()
        for s, a in raises[:-1]:
            if s != me and s != vseat:
                others.add(s)
        for s in H.pf_callers:
            if s != me and s != vseat:
                others.add(s)
        others = [s for s in others if self.seats.get(s) is not None and self.seats[s].status in ("active", "all_in")]
        n_others = len(others)
        Em = E * (0.80 ** n_others) if n_others else E
        if n_others:
            # equity vs the other callers' ranges shrinks multiway equity further for weak hands
            Em = min(Em, E ** (1.0 + 0.6 * n_others))
        my_total = self.my_total
        call_amt = min(to_call, self.my.stack)
        # does calling put (nearly) everything in?
        commit = (call_amt >= 0.45 * self.my.stack) or (self.my.stack - call_amt) < 4 * bb
        v_allin = v.status == "all_in" or v.stack <= 0
        n_active_behind = len([o for o in behind if o.status == "active"])

        # ---- all-in or commit decisions use ICM
        if v_allin or commit:
            Ereq = self.req_allin(vseat, call_amt)
            n_live_behind = len([o for o in behind if o.status == "active" and o.seat != vseat])
            if n_others or n_live_behind:
                Ereq += 0.02 * (n_others + n_live_behind)
            if pct <= 0.012 and Ereq < 0.85:
                Ereq = min(Ereq, 0.0)  # AA/KK: never fold preflop short of extreme ICM spots
            if Em >= Ereq:
                if not v_allin and "raise" in L and Em >= 0.5:
                    return _raise(L, self.my_total + 1)
                return _call_or_check(L)
            # reshove for fold equity when the raiser is not all-in and we are short
            if not v_allin and "raise" in L and n_others == 0:
                if self.reshove_ok(h, vseat, vp):
                    return _raise(L, self.my_total + 1)
            return _passive(L)

        # ---- short-ish: reshove or fold
        if eff_bb <= 22 and "raise" in L:
            if n_others == 0 and self.reshove_ok(h, vseat, vp):
                return _raise(L, self.my_total + 1)
            if E >= 0.60 and n_others <= 1:
                return _raise(L, self.my_total + 1)

        # ---- value re-raise
        thr3 = 0.60 if nth == 0 else 0.62
        if nth == 0 and vp >= 0.4:
            thr3 = 0.57
        if Em >= thr3 and "raise" in L:
            ip = self.in_position_pf(vseat)
            mult = 3.0 if ip else 3.6
            size = vamt * mult + bb * len(H.pf_callers)
            if nth >= 1:
                size = vamt * 2.3
            if size >= 0.33 * my_total:
                size = my_total
            return _raise(L, size)
        if nth >= 1 and Em < 0.5 and pct > 0.03:
            # facing a 3-bet+: only continue with premium-ish holdings or great price
            req = to_call / float(pot + to_call)
            if Em * 0.85 >= req + 0.08:
                return _call_or_check(L)
            return _passive(L)

        # ---- flat call with price + implied odds
        req = to_call / float(pot + to_call)
        ip = self.in_position_pf(vseat)
        realize = 0.92 if ip else 0.78
        if H.bb == me:
            realize = max(realize, 0.82)
        bonus = 0.0
        cname = _CLASSES[h]
        is_pair = len(cname) == 2
        suited = cname.endswith("s")
        stack_ratio = eff_bb * bb / max(1, to_call)
        if is_pair and stack_ratio >= 15:
            bonus += 0.05
        elif suited and stack_ratio >= 20 and abs(_RV[cname[0]] - _RV[cname[1]]) <= 2:
            bonus += 0.03
        if Em * realize + bonus >= req and (to_call <= 0.2 * self.my.stack or Em >= 0.5):
            return _call_or_check(L)
        return _passive(L)

    def in_position_pf(self, vseat):
        # postflop order starts after the button; whoever is later acts last
        order = self.order_from(self.st.button)
        try:
            return order.index(self.me) > order.index(vseat)
        except ValueError:
            return False

    def reshove_ok(self, h, vseat, vp):
        """Re-shove over a raise: villain calls with the top part of their raising range."""
        v = self.seats[vseat]
        od = self.opp(vseat)
        my_total = self.my_total
        R = min(my_total, self.total(v))
        need = (R - v.bet) / float(max(1, self.pot + R - v.bet))
        # villain continues with the part of their range that has enough equity
        cfrac = 0.45 if need > 0.38 else 0.6
        if od.n >= 8 and od.f2r < 0.2:
            cfrac = 0.85
        call_pct = max(0.02, vp * cfrac)
        E = _eqv(h, call_pct)
        pf = 1.0 - cfrac
        base = {s.seat: s.stack for s in self.alive}
        d = dict(base)
        d[self.me] = self.my.stack + self.pot
        u_win_now = self.icm_stacks(d)
        pot_final = self.pot - self.my.bet - v.bet + 2 * R
        dw = dict(base)
        dw[self.me] = my_total - R + pot_final
        dw[vseat] = self.total(v) - R
        dl = dict(base)
        dl[self.me] = my_total - R
        dl[vseat] = self.total(v) - R + pot_final
        ev = pf * u_win_now + (1 - pf) * (E * self.icm_stacks(dw) + (1 - E) * self.icm_stacks(dl))
        d = dict(base)
        d[vseat] = base[vseat] + self.pot
        ev_fold = self.icm_stacks(d)
        return ev > ev_fold * 1.01 + 1e-9

    def req_allin(self, vseat, call_amt):
        """ICM required equity to call `call_amt` against seat vseat (treated as heads-up all-in)."""
        v = self.seats[vseat]
        me = self.me
        pot = self.pot
        base = {s.seat: s.stack for s in self.alive}
        # villain's total commitment this hand is their bet; if we call for less, they get the excess back
        excess = max(0, self.to_call - call_amt)
        # also cap by villain's remaining stack (if villain not all-in, remaining stack may go in later; ignore)
        d_fold = dict(base)
        d_fold[vseat] = base[vseat] + pot
        u_fold = self.icm_stacks(d_fold)
        d_win = dict(base)
        d_win[me] = base[me] + pot - excess
        d_win[vseat] = base[vseat] + excess
        u_win = self.icm_stacks(d_win)
        d_lose = dict(base)
        d_lose[me] = base[me] - call_amt
        d_lose[vseat] = base[vseat] + pot + call_amt
        u_lose = self.icm_stacks(d_lose)
        den = u_win - u_lose
        if den <= 1e-12:
            return 1.0
        r = (u_fold - u_lose) / den
        return min(0.99, max(0.0, r))

    # -------------------------------------------------- postflop
    def postflop(self):
        L, H, bb, me = self.L, self.H, self.bb, self.me
        board = list(self.st.board)
        street = len(board) - 2  # 1 flop, 2 turn, 3 river
        if street < 1:
            street = 1
        if street > 3:
            street = 3
        opps = self.opps_in
        if not opps:
            return _call_or_check(L)
        to_call = self.to_call
        pot = self.pot
        n = len(opps)
        # main villain: current street aggressor, else last aggressor, else preflop raiser, else first opp
        vseat = None
        for s_ in range(street, -1, -1):
            for (s, a, pb, cb) in reversed(H.aggr[s_]):
                if s != me and self.seats.get(s) is not None and self.seats[s].status in ("active", "all_in"):
                    vseat = s
                    break
            if vseat is not None:
                break
        if vseat is None:
            vseat = opps[0].seat
        vp = self.pf_range_of(vseat)
        # Monte Carlo vs villain preflop range
        iters = 500 if self.bank >= 40 else 300
        el = time.perf_counter() - self.t0
        if el > 0.0004:
            iters = 150
        hole_c = [_CARD[self.hole[0]], _CARD[self.hole[1]]]
        board_c = [_CARD[c] for c in board]
        rng = _range_for(vp)
        E = eval7.py_hand_vs_range_monte_carlo(hole_c, rng, board_c, iters)
        # multiway: other opponents (wider ranges) reduce equity
        if n > 1:
            E = E ** (1.0 + 0.75 * (n - 1))
        # conditioning on villain's prior-street actions
        od = self.opp(vseat)
        btot = 1.0
        for s_ in range(1, street):
            vb = [x for x in H.aggr[s_] if x[0] == vseat]
            if vb:
                btot *= max(0.25, min(0.95, od.bet * 1.1)) ** 0.75
            elif vseat in H.calls[s_]:
                btot *= max(0.45, 1.0 - od.f2b) ** 0.6
        Eprior = _cond(E, btot ** 0.8, street)
        deq = _draw_eq(self.hole, board)
        if n > 1:
            deq *= 0.9
        if to_call <= 0:
            return self.post_unbet(E, Eprior, deq, btot, street, opps, vseat)
        return self.post_facing(E, deq, btot, street, opps, vseat)

    def pf_range_of(self, seat):
        H = self.H
        od = self.opp(seat)
        rs = [i for i, (s, a) in enumerate(H.pf_raises) if s == seat]
        if rs:
            nth = rs[-1]
            return self.raiser_pct(seat, nth, H.pf_raises[nth][1])
        if seat in H.pf_callers:
            p = od.vpip
            if H.pf_raises and len(H.pf_raises) >= 2:
                p *= 0.5
            return min(1.0, max(0.06, p))
        if seat in H.limpers:
            return min(1.0, max(0.15, od.vpip * 1.1))
        return 1.0

    def fold_prob(self, opps, size_frac):
        p = 1.0
        for o in opps:
            if o.status != "active":
                continue
            od = self.opp(o.seat)
            f = od.f2b
            f = f * (0.85 + 0.30 * min(1.5, size_frac))
            p *= min(0.95, max(0.03, f))
        return p

    def post_unbet(self, E, Eprior, deq, btot, street, opps, vseat):
        L, pot = self.L, self.pot
        if "raise" not in L:
            return _call_or_check(L)
        active = [o for o in opps if o.status == "active"]
        if not active:
            return Action.check()
        my_stack = self.my.stack
        ip = self.in_position_post(opps)
        e0 = max(Eprior, deq * 0.9)
        rz = (0.97 if ip else 0.88) if street < 3 else 1.0
        ev_check = e0 * pot * rz
        best = ("check", ev_check, 0)
        sizes = (0.5, 0.75) if street < 3 else (0.5, 0.8, 1.1)
        if len(active) >= 3:
            sizes = (0.66,)
        for sf in sizes:
            B = int(pot * sf)
            B = max(B, self.L["raise"].min_amount - self.my.bet)
            if B > my_stack:
                B = my_stack
            if B <= 0:
                continue
            pf = self.fold_prob(active, B / float(max(1, pot)))
            # equity when called: vs the calling part of the range
            Ec = _cond(Eprior, max(0.08, 1.0 - pf), street, 0.7)
            Ec = max(Ec, deq * 0.95)
            rc = 1.0 if street == 3 else (0.93 if ip else 0.86)
            ev = pf * pot + (1.0 - pf) * (Ec * rc * (pot + 2 * B) - B)
            # risk of being raised off our equity
            vr = self.opp(vseat).rz
            ev -= (1.0 - pf) * vr * B * (0.6 if Ec < 0.6 else 0.1)
            if ev > best[1]:
                best = ("bet", ev, B)
        if best[0] == "check":
            return Action.check()
        B = best[2]
        # value-heavy with strong hands and shallow stacks: shove
        if Eprior >= 0.75 and my_stack <= 1.3 * (pot + B):
            return _raise(self.L, self.my.bet + my_stack)
        return _raise(self.L, self.my.bet + B)

    def in_position_post(self, opps):
        order = self.order_from(self.st.button)
        live = [o.seat for o in opps if o.status == "active"] + [self.me]
        pos = [order.index(x) for x in live if x in order]
        if not pos or self.me not in order:
            return False
        return order.index(self.me) == max(pos)

    def post_facing(self, E, deq, btot, street, opps, vseat):
        L, H, pot, bb = self.L, self.H, self.pot, self.bb
        to_call = self.to_call
        od = self.opp(vseat)
        # current-street aggression from villain
        cur = [x for x in H.aggr[street] if x[0] == vseat]
        b = 1.0
        if cur:
            s, amt, pot_before, cb = cur[-1]
            bet_add = max(1, amt - cb)
            frac = bet_add / float(max(1, pot_before))
            if cb > 0:  # villain raised a bet
                b = min(0.9, max(0.05, od.rz * 1.6))
            else:
                b = min(0.95, max(0.08, od.bet * 1.05))
            b *= min(1.1, max(0.5, 1.12 - 0.28 * min(2.5, frac)))
            nb = len(H.aggr[street])
            if nb >= 3:
                b *= 0.6
        else:
            # facing a bet from someone else (not main villain): treat generically
            b = 0.45
        bt = max(0.05, (btot ** 0.8) * b)
        Ec = _cond(E, bt, street)
        Ec = max(Ec, deq * 0.92)
        call_amt = min(to_call, self.my.stack)
        req = call_amt / float(pot + call_amt)
        if _TRACE:
            sys.stderr.write("   [facing] v=%s vp=%.2f E=%.3f btot=%.2f b=%.2f Ec=%.3f deq=%.2f req=%.3f od.bet=%.2f od.rz=%.2f od.n=%d\n" % (
                vseat, self.pf_range_of(vseat), E, btot, b, Ec, deq, req, od.bet, od.rz, od.n))
        my_stack = self.my.stack
        commit = call_amt >= 0.5 * my_stack or (my_stack - call_amt) < 0.3 * (pot + call_amt)
        v = self.seats.get(vseat)
        v_allin = v is not None and (v.status == "all_in" or v.stack <= 0)
        n_act = len([o for o in opps if o.status == "active"])
        if commit or v_allin:
            Ereq = self.req_allin(vseat, call_amt) if v is not None else req
            if Ec >= Ereq:
                if not v_allin and "raise" in L and Ec >= 0.55 and n_act <= 1:
                    return _raise(L, self.my_total + 1)
                return _call_or_check(L)
            return _passive(L)
        # value raise
        rthr = 0.70 if street < 3 else 0.75
        if Ec >= rthr and "raise" in L:
            cur_bet = max([x[1] for x in H.aggr[street]] or [0])
            size = cur_bet * 2.7 + (pot - cur_bet) * 0.3
            return _raise(L, size)
        rz = {1: 0.86, 2: 0.92, 3: 1.0}[street]
        implied = 0.0
        if deq > 0 and street < 3 and my_stack > 3 * (pot + call_amt):
            implied = 0.04
        if Ec * rz + implied >= req:
            return _call_or_check(L)
        return _passive(L)


def _warmup():
    try:
        h = [_CARD["As"], _CARD["Kd"]]
        b = [_CARD["7h"], _CARD["8h"], _CARD["2c"]]
        for r in _RANGES:
            eval7.py_hand_vs_range_monte_carlo(h, r, b, 20)
        _icm([1000.0, 2000.0, 3000.0, 1500.0], 0, [50.0, 30.0, 20.0])
        _draw_eq(["As", "Kd"], ["7h", "8h", "2c"])
        _parse([])
        marshal.loads(marshal.dumps(_new_mem()))
    except Exception:
        pass


_warmup()

# Move import-time objects out of the GC's young generations: fewer, cheaper collections mid-decision.
gc.collect()
try:
    gc.freeze()
except AttributeError:
    pass
