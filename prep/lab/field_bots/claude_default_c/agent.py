"""claude_default_c: ICM-aware TAG pokerbot for 8-seat NLHE sit-and-go tables.

Design (see NOTES.md):
  * Preflop: precomputed 169-class tables (tables.json). Position-based open ranges when deep,
    ICM shove/fold EV (with estimated calling ranges of the players behind) when short, ICM call
    decisions against all-ins, equity-vs-estimated-range for 3-bets/calls.
  * Postflop: villain ranges are built from their preflop action + per-seat VPIP/PFR stats, then
    narrowed by their postflop aggression (top fraction by current hand value, plus a bluff weight
    learned from their aggression frequency). Equity via eval7 (C) Monte Carlo / exact river.
  * Per-table opponent stats travel in `memory` (compact JSON, < 1 KB).
  * Hard latency budget: every decision is a few hundred microseconds; a guard falls back to cheap
    paths if time or the time bank runs low. Any exception -> safe legal action.
"""
import gc
import json
import os
import random
import time

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "tables.json")) as _f:
    _T = json.load(_f)

RANKS = "23456789TJQKA"
SUITS = "shdc"
CLASSES = _T["classes"]
NCOMB = _T["ncomb"]
EQ1 = _T["eq1"]
GRID = _T["grid"]
EQ_TOP = _T["eq_top"]
NG = len(GRID)

CARD = {}
CID = {}
for _r in RANKS:
    for _s in SUITS:
        CARD[_r + _s] = eval7.Card(_r + _s)
        CID[_r + _s] = len(CID)
CLASS_IDX = {c: i for i, c in enumerate(CLASSES)}


def _class_of(c1, c2):
    r1, r2 = RANKS.index(c1[0]), RANKS.index(c2[0])
    if r1 < r2:
        r1, r2 = r2, r1
        c1, c2 = c2, c1
    if r1 == r2:
        return CLASS_IDX[RANKS[r1] * 2]
    return CLASS_IDX[RANKS[r1] + RANKS[r2] + ("s" if c1[1] == c2[1] else "o")]


HCLASS = {}
for _a in CARD:
    for _b in CARD:
        if _a != _b:
            HCLASS[(_a, _b)] = _class_of(_a, _b)


def _pct_table(order):
    pct, mid, cum = [0.0] * 169, [0.0] * 169, 0
    for k in order:
        mid[k] = (cum + NCOMB[k] / 2.0) / 1326.0
        cum += NCOMB[k]
        pct[k] = cum / 1326.0
    return pct, mid


SHOVE_PCT, SHOVE_MID = _pct_table(_T["shove_order"])
OPEN_PCT, OPEN_MID = _pct_table(_T["open_order"])

# For each grid bucket: equities of all classes vs that top-p range, sorted descending, with
# cumulative combo counts (for "what fraction of hands has >= x equity against a top-p range").
import bisect as _bisect
_FRAC_NEG = []
_FRAC_CUM = []
for _b in range(NG):
    _l = sorted(((EQ_TOP[k][_b], NCOMB[k]) for k in range(169)), key=lambda t: -t[0])
    _neg, _cum, _acc = [], [], 0
    for _e, _n in _l:
        _acc += _n
        _neg.append(-_e)
        _cum.append(_acc)
    _FRAC_NEG.append(_neg)
    _FRAC_CUM.append(_cum)


def frac_ge(b, x):
    i = _bisect.bisect_right(_FRAC_NEG[b], -x)
    return (_FRAC_CUM[b][i - 1] / 1326.0) if i > 0 else 0.0


def _bucket(p):
    if p <= GRID[0]:
        return 0, 0, 0.0
    if p >= GRID[-1]:
        return NG - 1, NG - 1, 0.0
    lo = 0
    while GRID[lo + 1] < p:
        lo += 1
    t = (p - GRID[lo]) / (GRID[lo + 1] - GRID[lo])
    return lo, lo + 1, t


def eq_vs_top(h, p):
    lo, hi, t = _bucket(p)
    row = EQ_TOP[h]
    return row[lo] * (1 - t) + row[hi] * t


def call_width(need, p_me):
    """Fraction of hands with equity >= need against a top-p_me range."""
    lo, hi, t = _bucket(p_me)
    b = lo if t < 0.5 else hi
    return frac_ge(b, need)


# Postflop range sampling: all 1326 combos ordered by the open ranking, cut into chunks,
# each chunk pre-shuffled. Entry = (((CardA, CardB), 1.0), mask, CardA, CardB)
NCH = 40
_all = []
for _k in _T["open_order"]:
    _lab = CLASSES[_k]
    _ra, _rb = _lab[0], _lab[1]
    if len(_lab) == 2:
        _cs = [(_ra + SUITS[x], _rb + SUITS[y]) for x in range(4) for y in range(x + 1, 4)]
    elif _lab[2] == "s":
        _cs = [(_ra + s, _rb + s) for s in SUITS]
    else:
        _cs = [(_ra + x, _rb + y) for x in SUITS for y in SUITS if x != y]
    _rnd = random.Random(_k)
    _rnd.shuffle(_cs)
    for a, b in _cs:
        _all.append((((CARD[a], CARD[b]), 1.0), (1 << CID[a]) | (1 << CID[b]), CARD[a], CARD[b]))
CHUNKS = []
for _i in range(NCH):
    _ch = _all[_i * 1326 // NCH:(_i + 1) * 1326 // NCH]
    random.Random(1000 + _i).shuffle(_ch)
    CHUNKS.append(_ch)
del _all

EVAL = eval7.evaluate
MC = eval7.py_hand_vs_range_monte_carlo
EXACT = eval7.py_hand_vs_range_exact

# tunables
PUSH_LIMIT = 8.5
PUSH_LIMIT_HU = 11.0
VT = (0.0, 0.50, 0.53, 0.55)
STATION_BONUS = 0.2
BLUFF_MARGIN = 0.04
RAISE_T = (0.72, 0.78)
OPEN_SCALE = 1.35
PREMIUM = {"AA", "KK", "QQ", "JJ", "TT", "AKs", "AKo", "AQs"}
# priors for opponent stats
PRIOR_VPIP, PRIOR_PFR, PRIOR_N = 0.34, 0.17, 8.0
RNG = random.Random()

# ---------------------------------------------------------------------------- helpers


_KN = {}


def _kind_name_slow(k):
    v = getattr(k, "value", k)
    if isinstance(v, str):
        return v.lower()
    n = getattr(k, "name", str(k))
    return str(n).lower()


def kind_name(k):
    """Normalise an action kind / seat status (Enum member or string) to a lowercase string."""
    try:
        return _KN[k]
    except KeyError:
        v = _kind_name_slow(k)
        if len(_KN) < 256:
            _KN[k] = v
        return v
    except TypeError:
        return _kind_name_slow(k)


def legal_map(state):
    m = {}
    for la in state.legal_actions:
        m[kind_name(la.kind)] = la
    return m


def safe_action(lm):
    if "check" in lm:
        return Action.check()
    if "fold" in lm:
        return Action.fold()
    if "call" in lm:
        return Action.call()
    la = lm.get("raise")
    if la is not None:
        return Action.raise_to(int(la.min_amount))
    return Action.fold()


def icm_me(me, others, pays):
    """Malmuth-Harville expected payout for a player with `me` chips vs `others` (all > 0).
    Exact for up to 4 paid places; deeper structures get the remaining probability spread
    over the remaining payouts."""
    n = 1 + len(others)
    if me <= 0:
        return pays[n - 1] if n - 1 < len(pays) else 0.0
    pl = list(pays[:n]) + [0.0] * max(0, n - len(pays))
    k = 0
    for i, p in enumerate(pl):
        if p > 0:
            k = i + 1
    if k == 0:
        return 0.0
    S = float(me + sum(others))
    q = me / S
    v = pl[0] * q
    if k == 1 or not others:
        return v
    m = len(others)
    p1, p2, p3 = pl[1], (pl[2] if n > 2 else 0.0), (pl[3] if n > 3 else 0.0)
    for i in range(m):
        a = others[i]
        pa = a / S
        S1 = S - a
        t = pa * me / S1
        q += t
        v += p1 * t
        if k >= 3:
            for j in range(m):
                if j == i:
                    continue
                b = others[j]
                pb = pa * b / S1
                S2 = S1 - b
                t = pb * me / S2
                q += t
                v += p2 * t
                if k >= 4 and pb > 0.002:
                    for l in range(m):
                        if l == i or l == j:
                            continue
                        cc = others[l]
                        t = pb * (cc / S2) * me / (S2 - cc)
                        q += t
                        v += p3 * t
    if k > 4 and n > 4:
        # remaining probability over places 5..n, skewed toward the bottom for short stacks
        tail = pl[4:n]
        rho = (S / n) / me
        rho = 0.3 if rho < 0.3 else (3.0 if rho > 3.0 else rho)
        w, num, den = 1.0, 0.0, 0.0
        for pay in tail:
            num += w * pay
            den += w
            w *= rho
        v += max(0.0, 1.0 - q) * (num / den)
    return v


class Ctx:
    """Everything derived from the state for one decision."""
    pass


# ---------------------------------------------------------------------------- memory / stats
# per-seat stats: [hands, vpip, pfr, rr, rr_opp, agg, pas, fold_vs_bet, faced_bet]


def load_mem(memory):
    if memory:
        try:
            return json.loads(memory.decode() if isinstance(memory, (bytes, bytearray)) else memory)
        except Exception:
            pass
    return {"s": {}, "c": None}


def process_events(mem, events):
    S = mem["s"]
    cur = mem.get("c")
    for ev in events:
        k = kind_name(ev.kind)
        seat = ev.seat
        if k == "hand":
            if cur:
                for sk, fl in cur["f"].items():
                    st = S.get(sk)
                    if st is None:
                        st = S[sk] = [0, 0, 0, 0, 0, 0, 0, 0, 0]
                    st[0] += 1
                    st[1] += fl[0]
                    st[2] += fl[1]
            cur = {"st": 0, "bo": 1, "nr": 0, "f": {}}
            continue
        if cur is None or seat is None:
            if k == "board" and cur is not None:
                cur["st"] += 1
                cur["bo"] = 0
            continue
        sk = str(seat)
        fl = cur["f"].get(sk)
        if fl is None:
            fl = cur["f"][sk] = [0, 0]
        st = S.get(sk)
        if st is None:
            st = S[sk] = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        street = cur["st"]
        if k == "call":
            if street == 0:
                fl[0] = 1
                if cur["nr"] >= 1:
                    st[4] += 1
            else:
                st[6] += 1
                if cur["bo"]:
                    st[8] += 1
        elif k == "raise":
            if street == 0:
                fl[0] = 1
                fl[1] = 1
                if cur["nr"] >= 1:
                    st[3] += 1
                    st[4] += 1
                cur["nr"] += 1
            else:
                st[5] += 1
                if cur["bo"]:
                    st[8] += 1
                cur["bo"] = 1
        elif k == "check":
            if street > 0:
                st[6] += 1
        elif k == "fold":
            if street == 0:
                if cur["nr"] >= 1:
                    st[4] += 1
            elif cur["bo"]:
                st[7] += 1
                st[8] += 1
    mem["c"] = cur
    return mem


def seat_stats(mem, seat):
    st = mem["s"].get(str(seat)) or [0] * 9
    h = st[0]
    vpip = (st[1] + PRIOR_VPIP * PRIOR_N) / (h + PRIOR_N)
    pfr = (st[2] + PRIOR_PFR * PRIOR_N) / (h + PRIOR_N)
    rr = (st[3] + 0.08 * 6) / (st[4] + 6)
    agg = (st[5] + 1.2) / (st[5] + st[6] + 4.0)
    fvb = (st[7] + 2.0) / (st[8] + 4.5)
    return vpip, pfr, rr, agg, fvb, h


# ---------------------------------------------------------------------------- hand parsing


def parse_hand(state, me):
    """Return per-street action lists and preflop structure from state.history."""
    streets = [[]]
    blinds = []
    for ev in (state.history or []):
        k = kind_name(ev.kind)
        if k == "board":
            streets.append([])
        elif k in ("blind", "ante"):
            if k == "blind":
                blinds.append((ev.seat, ev.amount or 0))
        elif k in ("fold", "check", "call", "raise"):
            streets[-1].append((ev.seat, k, ev.amount or 0))
    return streets, blinds


# ---------------------------------------------------------------------------- the agent


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        t0 = time.perf_counter()
        try:
            lm = legal_map(state)
        except Exception:
            return Action.fold(), memory
        mem = None
        try:
            mem = load_mem(memory)
            process_events(mem, state.events or [])
        except Exception:
            mem = {"s": {}, "c": None}
        try:
            action = self.decide(state, lm, mem, t0)
            action = self.legalize(action, lm)
        except Exception:
            action = safe_action(lm)
        try:
            out = json.dumps(mem, separators=(",", ":")).encode()
            if len(out) > 15000:
                out = json.dumps({"s": mem["s"], "c": None}, separators=(",", ":")).encode()
        except Exception:
            out = memory if isinstance(memory, (bytes, bytearray)) else b""
        return action, out

    # ------------------------------------------------------------------ legality
    def legalize(self, action, lm):
        kn = kind_name(action.kind)
        if kn == "raise":
            la = lm.get("raise")
            if la is None:
                return Action.call() if "call" in lm else safe_action(lm)
            amt = int(action.amount)
            lo, hi = int(la.min_amount), int(la.max_amount)
            if amt < lo:
                amt = lo
            if amt > hi:
                amt = hi
            if amt < lo:
                return Action.call() if "call" in lm else safe_action(lm)
            return Action.raise_to(amt)
        if kn in lm:
            return action
        if kn == "fold" and "check" in lm:
            return Action.check()
        if kn == "check" and "call" in lm:
            return Action.fold() if "fold" in lm else Action.call()
        if kn == "call" and "check" in lm:
            return Action.check()
        return safe_action(lm)

    # ------------------------------------------------------------------ decision
    def decide(self, state, lm, mem, t0):
        cards = list(state.cards or [])
        if len(cards) != 2 or str(getattr(state.config, "variant", "holdem") or "holdem").lower().replace("-", "_") not in ("holdem", "nlhe", "texas_holdem", "nl_holdem", "no_limit_holdem"):
            return self.fallback(state, lm)
        c = Ctx()
        c.t0 = t0
        c.state = state
        c.lm = lm
        c.mem = mem
        c.me = state.seat
        c.cards = cards
        c.board = list(state.board or [])
        bl = state.blinds or [10, 20]
        c.sb, c.bb = float(bl[0]), float(max(bl[1], 1))
        c.seats = {}
        for s in state.seats:
            c.seats[s.seat] = s
        mys = c.seats[c.me]
        c.stack = float(mys.stack)
        c.mybet = float(mys.bet or 0)
        c.pot = float(state.pot)
        c.to_call = float(state.to_call or 0)
        c.alive = [s for s in state.seats if kind_name(s.status) != "busted"]
        c.inhand = [s for s in state.seats if kind_name(s.status) in ("active", "all_in") and s.seat != c.me]
        c.can_act_opp = [s for s in c.inhand if kind_name(s.status) == "active"]
        c.payouts = list(getattr(state.config, "payouts", None) or [50, 30, 20])
        c.streets, c.blinds = parse_hand(state, c.me)
        c.street = len(c.board) and (len(c.board) - 2)  # 0 pre, 1 flop, 2 turn, 3 river
        if len(c.board) == 0:
            c.street = 0
        c.button = state.button
        c.order = sorted(c.seats)
        c.bank = getattr(state, "time_bank_ms", 100) or 0
        if c.street == 0:
            return self.preflop(c)
        return self.postflop(c)

    def fallback(self, state, lm):
        if "check" in lm:
            return Action.check()
        tc = state.to_call or 0
        bb = (state.blinds or [10, 20])[1]
        if "call" in lm and tc <= bb:
            return Action.call()
        return Action.fold() if "fold" in lm else safe_action(lm)

    # ------------------------------------------------------------------ utilities
    def cyc_after(self, c, start):
        """Seats in clockwise order after `start` (exclusive), full circle excluding start."""
        o = c.order
        i = o.index(start) if start in o else 0
        return o[i + 1:] + o[:i]

    def total_chips(self, s):
        return float(s.stack) + float(s.bet or 0)

    def icm_outcome(self, c, deltas, bust_extra=None):
        """My ICM value after applying chip deltas {seat: delta} to current stacks (stack+bet)."""
        me_val = None
        others = []
        for s in c.alive:
            v = float(s.stack)
            v += deltas.get(s.seat, 0.0)
            if s.seat == c.me:
                me_val = v
            elif v > 0.5:
                others.append(v)
        n_alive = len(c.alive)
        if me_val is None:
            return 0.0
        if me_val <= 0.5:
            # I bust now: place = n_alive minus nothing (others busting same hand ignored)
            idx = len(others)  # number of others still alive -> my place = len(others)+1
            return c.payouts[idx] if idx < len(c.payouts) else 0.0
        # players busted in this outcome take the lowest places -> remaining pays top slice
        return icm_me(me_val, others, c.payouts)

    def pot_owner(self, c, callers):
        """Who most plausibly takes the pot if I fold: last raiser, else big blind, else a caller."""
        owner = None
        for (sd, k, a) in c.streets[0]:
            if k == "raise" and sd != c.me:
                owner = sd
        if owner is None and c.blinds:
            bbs = max(c.blinds, key=lambda t: t[1])[0]
            if bbs != c.me:
                owner = bbs
        if owner is None and callers:
            owner = callers[-1].seat
        return owner

    # ------------------------------------------------------------------ preflop
    def preflop(self, c):
        st = c.state
        lm = c.lm
        h = HCLASS[(c.cards[0], c.cards[1])]
        c.h = h
        p_shove = SHOVE_PCT[h]
        p_open = OPEN_PCT[h]
        bb = c.bb
        acts = c.streets[0]
        my_total = c.stack + c.mybet
        # opponents still in hand with chips totals
        opp_tot = [self.total_chips(s) for s in c.inhand]
        max_opp = max(opp_tot) if opp_tot else 0.0
        eff = min(my_total, max_opp)
        eff_bb = eff / bb
        my_bb = my_total / bb
        n_alive = len(c.alive)

        # blind seats
        bb_seat = None
        if c.blinds:
            bb_seat = max(c.blinds, key=lambda t: t[1])[0] if len(c.blinds) >= 2 else c.blinds[-1][0]
        # raise structure
        raises = [(s, k, a) for (s, k, a) in acts if k == "raise"]
        nraise = len(raises)
        last_raiser = raises[-1][0] if raises else None
        cur_bet = max([float(s.bet or 0) for s in c.seats.values()] + [bb])
        # who acted already this street
        acted = set(s for (s, k, a) in acts)
        # players behind me (clockwise up to and including BB in an unopened pot)
        behind = []
        after = self.cyc_after(c, c.me)
        for sid in after:
            s = c.seats[sid]
            if kind_name(s.status) != "active":
                continue
            behind.append(s)
            if sid == bb_seat and nraise == 0:
                break
        # in an unopened pot, players behind = those not yet acted (+ blinds); stop at bb
        if nraise == 0:
            behind = [s for s in behind if s.seat not in acted or s.seat == bb_seat]
            # trim anything after bb (already done)
        limpers = [s for (s, k, a) in acts if k == "call"] if nraise == 0 else []
        n_behind = len([s for s in behind if s.seat != c.me])

        any_allin = any(kind_name(s.status) == "all_in" for s in c.inhand)
        hu = n_alive == 2

        if nraise == 0:
            return self.pf_unopened(c, h, p_shove, p_open, behind, limpers, bb_seat, eff_bb, my_bb, hu)
        # facing raise(s)
        r_seat = last_raiser
        rs = c.seats.get(r_seat)
        r_total = float(rs.bet or 0) if rs else cur_bet
        r_allin = rs is not None and kind_name(rs.status) == "all_in"
        return self.pf_facing(c, h, p_shove, p_open, raises, r_seat, r_total, r_allin, any_allin, eff_bb, my_bb, behind, hu, bb_seat)

    def perceived_shove_range(self, eff_bb):
        return max(0.12, min(1.0, 1.8 / max(eff_bb, 1.0) ** 0.75))

    def shove_ev(self, c, h, callers, extra_tight=0.0):
        """ICM EV of shoving all-in now vs folding. callers: list of seat objects that may call."""
        my_in = c.mybet
        my_all = c.stack + c.mybet
        pot = c.pot
        # fold value: I lose what I've put in (already out of my stack); pot goes to someone else
        owner = self.pot_owner(c, callers)
        v_fold = self.icm_outcome(c, {owner: pot} if owner is not None else {})
        # steal
        v_steal = self.icm_outcome(c, {c.me: pot})
        pf = 1.0
        ev = 0.0
        cand = []
        for s in callers:
            j_in = float(s.bet or 0)
            j_all = float(s.stack) + j_in
            x = min(my_all, j_all)
            dead = pot - my_in - j_in
            cost = x - j_in
            if cost <= 0:
                continue
            need = cost / (dead + 2 * x)
            p_me = self.perceived_shove_range(x / c.bb)
            vp, pfr, rr, agg, fvb, nh = seat_stats(c.mem, s.seat)
            # tighter when the call risks a big part of their stack; looser for loose players
            risk = cost / max(j_all, 1.0)
            need += 0.03 + 0.05 * risk * min(1.0, (len(c.alive) - 2) / 3.0) + extra_tight
            need -= 0.12 * (vp - PRIOR_VPIP)
            cw = call_width(max(0.05, min(0.95, need)), p_me)
            cw = max(0.015, min(0.95, cw))
            # condition on the range this player has already shown this hand
            p_j = self.pf_range_width(c, s.seat)
            if cw >= p_j:
                pc, wid = 1.0, p_j
            else:
                pc, wid = cw / p_j, cw
            q = pf * pc
            pf *= (1 - pc)
            cand.append((q, s, x, dead, wid))
        cand.sort(key=lambda t: -t[0])
        for i, (q, s, x, dead, cw) in enumerate(cand):
            e = eq_vs_top(h, cw)
            j_in = float(s.bet or 0)
            if i < 3:
                vw = self.icm_outcome(c, {c.me: my_in + x + dead, s.seat: j_in - x})
                vl = self.icm_outcome(c, {c.me: my_in - x, s.seat: x + dead + j_in})
                ev += q * (e * vw + (1 - e) * vl)
            else:
                ev += q * (e * v_steal + (1 - e) * v_fold * 0.6)
        ev += pf * v_steal
        return ev, v_fold, pf

    def pf_range_width(self, c, seat):
        """Width (top fraction) of the range a seat has represented preflop this hand."""
        raised_idx = -1
        called = False
        nr = 0
        for (sd, k, a) in c.streets[0]:
            if k == "raise":
                if sd == seat:
                    raised_idx = nr
                nr += 1
            elif k == "call" and sd == seat:
                called = True
        if raised_idx >= 0:
            s = c.seats.get(seat)
            allin = s is not None and kind_name(s.status) == "all_in"
            return self.raiser_range(c, seat, float(s.bet or 0) if s else 0.0, raised_idx, allin)
        if called:
            vp = seat_stats(c.mem, seat)[0]
            return max(0.12, min(1.0, vp * 1.1))
        return 1.0

    def pf_unopened(self, c, h, p_shove, p_open, behind, limpers, bb_seat, eff_bb, my_bb, hu):
        lm = c.lm
        bb = c.bb
        n_behind = len(behind)
        nl = len(limpers)
        am_bb = (c.me == bb_seat)
        push_limit = PUSH_LIMIT_HU if hu else PUSH_LIMIT
        # --- push / fold zone
        if eff_bb <= push_limit or my_bb <= push_limit:
            if am_bb and nl == 0 and "check" in lm:
                # walk to BB: just check (nobody to shove at)
                return Action.check()
            callers = [s for s in behind if s.seat != c.me] + [c.seats[s] for s in limpers if s in c.seats]
            # limpers re-act: include them
            seen = set()
            cl = []
            for s in callers:
                if s.seat in seen or kind_name(s.status) != "active":
                    continue
                seen.add(s.seat)
                cl.append(s)
            if not cl:
                return Action.check() if "check" in lm else Action.call() if "call" in lm else Action.fold()
            ev, v_fold, pf = self.shove_ev(c, h, cl)
            # option: complete / check value
            if ev > v_fold + 0.002 * (c.payouts[0] if c.payouts else 50) * 0.0 + 1e-9:
                return self.raise_to(c, 1e12)
            if am_bb and "check" in lm:
                return Action.check()
            # completing the small blind with a decent hand beats folding it
            if "call" in lm and c.to_call <= bb * 0.5 + 1e-9 and p_open <= (0.6 if hu else 0.4):
                return Action.call()
            return Action.fold() if "fold" in lm else Action.check()
        # --- deeper: raise / limp / fold
        open_tab = {1: 0.50, 2: 0.42, 3: 0.28, 4: 0.21, 5: 0.17, 6: 0.14, 7: 0.12}
        nb = max(1, n_behind)
        thr = open_tab.get(nb, 0.11) * OPEN_SCALE
        if hu:
            thr = 0.80 if not am_bb else 0.0
        # adapt to tightness of players behind
        vps = [seat_stats(c.mem, s.seat)[0] for s in behind if s.seat != c.me]
        if vps:
            avg = sum(vps) / len(vps)
            if avg < 0.22:
                thr = min(0.85, thr * 1.35)
            elif avg > 0.55:
                thr *= 0.85
        size_bb = 2.5 if eff_bb >= 40 else 2.2
        if hu:
            size_bb = 2.5 if eff_bb >= 40 else 2.1
        if nl > 0:
            thr_iso = thr * 0.7
            if am_bb:
                if p_open <= 0.10:
                    return self.raise_to(c, bb * (4 + nl))
                return Action.check() if "check" in lm else Action.fold()
            if p_open <= thr_iso:
                return self.raise_to(c, bb * (3 + nl))
            # limp behind with speculative hands when deep
            lab = CLASSES[h]
            spec = (len(lab) == 2) or (lab[2] == "s" and (lab[0] == "A" or abs(RANKS.index(lab[0]) - RANKS.index(lab[1])) <= 2))
            if eff_bb >= 35 and spec and p_open <= 0.55 and "call" in lm and c.to_call <= bb:
                return Action.call()
            if c.me in [s for s, k in c.blinds] and c.to_call <= bb / 2 + 1e-9 and p_open <= 0.5 and "call" in lm:
                return Action.call()
            return Action.check() if "check" in lm else Action.fold()
        # unopened, no limpers
        if am_bb:
            # everyone folded / limped to me? (no limpers -> walk). Just check.
            return Action.check() if "check" in lm else Action.fold()
        if p_open <= thr:
            return self.raise_to(c, bb * size_bb)
        # SB completes cheaply when deep with medium hands
        if n_behind == 1 and not hu and eff_bb >= 30 and p_open <= 0.68 and "call" in lm:
            return Action.call()
        return Action.fold() if "fold" in lm else Action.check()

    def raiser_range(self, c, seat, r_total, nraise_before, allin):
        vp, pfr, rr, agg, fvb, nh = seat_stats(c.mem, seat)
        s = c.seats.get(seat)
        tot_bb = (self.total_chips(s) / c.bb) if s else 20.0
        if allin:
            base = max(0.04, min(0.8, 1.6 / max(tot_bb, 1.0) ** 0.8))
            p = base * (pfr / PRIOR_PFR) ** 0.6
            if nraise_before >= 1:
                p *= 0.6
            return max(0.03, min(1.0, p))
        if nraise_before == 0:
            p = pfr * 1.05
            size = r_total / c.bb
            if size >= 5:
                p *= 0.75
            return max(0.04, min(1.0, p))
        if nraise_before == 1:
            return max(0.025, min(1.0, rr * 1.0))
        return max(0.02, min(1.0, rr * 0.55))

    def pf_facing(self, c, h, p_shove, p_open, raises, r_seat, r_total, r_allin, any_allin, eff_bb, my_bb, behind, hu, bb_seat):
        lm = c.lm
        bb = c.bb
        nr = len(raises)
        p_r = self.raiser_range(c, r_seat, r_total, nr - 1, r_allin)
        # widen for heads-up/short-handed raisers
        e_r = eq_vs_top(h, p_r)
        to_call = c.to_call
        my_total = c.stack + c.mybet
        pot = c.pot
        po = to_call / (pot + to_call) if to_call > 0 else 0.0
        others_in = [s for s in c.inhand if s.seat != r_seat]
        n_other_live = len([s for s in others_in if kind_name(s.status) == "active"])
        # players who could still act after me (not folded, active)
        can_raise = "raise" in lm
        commit = to_call >= 0.4 * c.stack or r_allin or any_allin or (c.stack - to_call) < 3 * bb

        # ---- all-in / commitment decisions: call or fold by ICM
        if r_allin or any_allin or (not can_raise) or to_call >= 0.85 * c.stack:
            # equity vs all all-in / raiser ranges
            e = e_r
            for s in c.inhand:
                if s.seat == r_seat:
                    continue
                if kind_name(s.status) == "all_in" or any(a[0] == s.seat for a in raises):
                    pr2 = self.raiser_range(c, s.seat, float(s.bet or 0), 0, kind_name(s.status) == "all_in")
                    e *= eq_vs_top(h, pr2) ** 0.85
            if "call" not in lm:
                return Action.check() if "check" in lm else Action.fold()
            ok = self.icm_call_ok(c, e, to_call, r_seat, extra=0.03 * n_other_live)
            if ok:
                # with a monster and more live players behind, jam to isolate
                if can_raise and p_shove <= 0.03 and n_other_live > 0 and not r_allin:
                    return self.raise_to(c, 1e12)
                return Action.call()
            return Action.fold()

        # ---- short / medium: reshove or fold (re-steal), else continue
        if eff_bb <= 30 or my_bb <= 30:
            callers = [c.seats[r_seat]] + [s for s in c.inhand if s.seat != r_seat and kind_name(s.status) == "active"]
            ev, v_fold, pf = self.shove_ev(c, h, callers, extra_tight=0.0)
            if ev > v_fold:
                # value hands that also beat the range: shove
                return self.raise_to(c, 1e12)
            # cheap calls with good pot odds (e.g. BB vs min-raise)
            if to_call <= 0.12 * c.stack and e_r * (0.85 if self.in_position_pf(c, bb_seat) else 0.72) >= po and p_open <= 0.5:
                return Action.call()
            return Action.fold()

        # ---- deep
        ip = self.in_position_pf(c, bb_seat)
        real = 0.85 if ip else 0.70
        if n_other_live > 0:
            real -= 0.07
        if nr == 1:
            value = e_r >= 0.6 or CLASSES[h] in PREMIUM
            if value and can_raise:
                mult = 3.0 if ip else 3.6
                n_call = len([a for a in c.streets[0] if a[1] == "call" and a[0] != c.me])
                tgt = r_total * mult + n_call * r_total
                if tgt >= 0.4 * my_total:
                    return self.raise_to(c, 1e12)
                return self.raise_to(c, tgt)
            lab = CLASSES[h]
            if len(lab) == 2 and to_call <= eff_bb * bb / 14.0 and p_open <= 0.8:
                return Action.call()
            if e_r * real >= po and p_open <= 0.42:
                return Action.call()
            return Action.fold()
        # facing 3-bet or more
        if e_r >= 0.56 or p_shove <= 0.02:
            if eff_bb <= 70 or nr >= 3:
                return self.raise_to(c, 1e12)
            return self.raise_to(c, r_total * 2.3)
        if to_call <= 0.15 * c.stack and e_r * real >= po and p_open <= 0.25:
            return Action.call()
        return Action.fold()

    def in_position_pf(self, c, bb_seat):
        # postflop position: last to act among players in hand = closest before button inclusive
        seats_in = [s.seat for s in c.inhand] + [c.me]
        order = self.cyc_after(c, c.button) + [c.button]
        pos = [sd for sd in order if sd in seats_in]
        return pos and pos[-1] == c.me

    def icm_call_ok(self, c, e, to_call, villain_seat, extra=0.0):
        """Call an (effectively) all-in bet if equity beats the ICM-required equity."""
        vs = c.seats.get(villain_seat)
        add = min(to_call, c.stack)
        v_bet = float(vs.bet or 0) if vs else c.mybet + to_call
        refund = max(0.0, v_bet - (c.mybet + add))
        vd = {} if vs is None else None
        v_fold = self.icm_outcome(c, {villain_seat: c.pot} if vs else {})
        v_win = self.icm_outcome(c, {c.me: c.pot - refund, villain_seat: refund} if vs else {c.me: c.pot - refund})
        v_lose = self.icm_outcome(c, {c.me: -add, villain_seat: c.pot + add} if vs else {c.me: -add})
        if v_win - v_lose <= 1e-9:
            return False
        req = (v_fold - v_lose) / (v_win - v_lose)
        return e >= req + extra

    # ------------------------------------------------------------------ postflop
    def postflop(self, c):
        lm = c.lm
        st = c.street
        P = c.pot
        C = c.to_call
        opps = c.inhand
        k = len(opps)
        if k == 0:
            return Action.check() if "check" in lm else Action.call() if "call" in lm else Action.fold()
        bb = c.bb
        # preflop roles
        pre = c.streets[0]
        raises_pre = [a for a in pre if a[1] == "raise"]
        pf_aggr = raises_pre[-1][0] if raises_pre else None
        # build range spec for each opponent
        dead = (1 << CID[c.cards[0]]) | (1 << CID[c.cards[1]])
        for b in c.board:
            dead |= 1 << CID[b]
        mine = [CARD[c.cards[0]], CARD[c.cards[1]]]
        board = [CARD[b] for b in c.board]
        # main villain: last aggressor on this street, else last aggressor on any street, else first
        aggr_seq = []
        for si in range(1, len(c.streets)):
            for (s, kk, a) in c.streets[si]:
                if kk == "raise" and s != c.me:
                    aggr_seq.append(s)
        live_ids = [s.seat for s in opps]
        ordered = []
        for s in reversed(aggr_seq):
            if s in live_ids and s not in ordered:
                ordered.append(s)
        if pf_aggr in live_ids and pf_aggr not in ordered:
            ordered.append(pf_aggr)
        for s in live_ids:
            if s not in ordered:
                ordered.append(s)
        budget_low = c.bank < 25
        M = 60 if budget_low else 110
        eqs = []
        for i, sid in enumerate(ordered):
            el = (time.perf_counter() - c.t0) * 1e3
            if el > (0.45 if not budget_low else 0.2) and eqs:
                # out of time: assume remaining opponents like the average
                eqs.append(sum(eqs) / len(eqs))
                continue
            segs = self.pre_range(c, sid, pre, raises_pre)
            f_keep, beta = self.post_narrow(c, sid)
            eqs.append(self.equity_vs(c, mine, board, dead, segs, f_keep, beta, M if i < 2 else 50))
        if k == 1:
            e = eqs[0]
        else:
            prod = 1.0
            for x in eqs:
                prod *= x
            e = prod ** 0.88
        c.e = e
        # position
        order_post = self.cyc_after(c, c.button) + [c.button]
        act_ids = [s.seat for s in c.can_act_opp] + [c.me]
        pos_list = [sd for sd in order_post if sd in act_ids]
        ip = bool(pos_list) and pos_list[-1] == c.me
        stack = c.stack
        opp_eff = max([float(s.stack) + float(s.bet or 0) - c.mybet for s in c.can_act_opp] + [0.0])
        eff = min(stack, opp_eff) if c.can_act_opp else 0.0
        spr = eff / max(P, 1.0)

        if C <= 0:
            if not c.can_act_opp or "raise" not in lm:
                return Action.check()
            vt = VT[st]
            if e >= vt:
                frac = 0.5 + 0.4 * (e - vt) / (1 - vt)
                if st == 3 and e >= 0.85:
                    frac = 0.85
                if STATION_BONUS and min(seat_stats(c.mem, s.seat)[4] for s in c.can_act_opp) < 0.33:
                    frac += STATION_BONUS
                B = frac * P
                if B >= 0.5 * eff or spr <= 1.3:
                    if e >= 0.66 or spr <= 0.6:
                        return self.raise_to(c, c.mybet + stack)
                return self.raise_to(c, c.mybet + B)
            # bluff / semi-bluff
            if k <= 2:
                fprod = 1.0
                for s in c.can_act_opp:
                    fprod *= seat_stats(c.mem, s.seat)[4]
                f = fprod
                if pf_aggr == c.me and st == 1:
                    f = min(0.9, f + 0.06)
                B = (0.45 if st == 1 else 0.55) * P
                if B > 0.5 * eff:
                    B = eff
                f = min(0.92, f * (0.85 + 0.3 * B / max(P, 1)))
                ec = e * (0.75 if st < 3 else 0.3)
                ev_bet = f * P + (1 - f) * (ec * (P + 2 * B) - B)
                ev_chk = e * P * (0.92 if ip else 0.8)
                if ev_bet > ev_chk + BLUFF_MARGIN * P and RNG.random() < 0.85:
                    return self.raise_to(c, c.mybet + B)
            return Action.check()

        # facing a bet
        po = C / (P + C)
        margin = (0.0, 0.02, 0.02, 0.0)[st]
        if k >= 2:
            margin += 0.02
        # who bet: aggressor stats -> nothing extra; equity already narrowed
        req = po
        if C >= 0.3 * stack or (stack - C) < 0.3 * P:
            bettor = ordered[0]
            vs = c.seats.get(bettor)
            if vs is not None:
                commit_all = (stack - C) < 0.6 * (P + C)
                extra = min(stack - C, float(vs.stack)) if commit_all else 0.0
                v_fold = self.icm_outcome(c, {bettor: P})
                v_win = self.icm_outcome(c, {c.me: P + extra, bettor: -extra})
                v_lose = self.icm_outcome(c, {c.me: -(C + extra), bettor: P + C + extra})
                if v_win - v_lose > 1e-9:
                    req_icm = (v_fold - v_lose) / (v_win - v_lose)
                    if commit_all:
                        req = max(req, req_icm)
                    else:
                        req = max(req, 0.5 * (req + req_icm))
        can_raise = "raise" in lm and bool(c.can_act_opp) and not all(kind_name(s.status) == "all_in" for s in opps)
        rt = RAISE_T[0] if st < 3 else RAISE_T[1]
        if e >= rt and can_raise and e >= req + 0.1:
            facing_total = c.mybet + C
            tgt = facing_total + (P + C) * 0.85
            if tgt >= 0.45 * (stack + c.mybet) or spr <= 2.0:
                return self.raise_to(c, 1e12)
            return self.raise_to(c, tgt)
        if e >= req + margin:
            return Action.call() if "call" in lm else Action.check()
        return Action.fold() if "fold" in lm else Action.check()

    def pre_range(self, c, sid, pre, raises_pre):
        vp, pfr, rr, agg, fvb, nh = seat_stats(c.mem, sid)
        acts = [(k, a) for (s, k, a) in pre if s == sid]
        raised = any(k == "raise" for k, a in acts)
        # raise index of this seat's last raise
        if raised:
            idx = max(i for i, a in enumerate(raises_pre) if a[0] == sid)
            if idx == 0:
                return [(0.0, max(0.05, min(1.0, pfr * 1.05)), 1.0)]
            if idx == 1:
                return [(0.0, max(0.03, min(1.0, rr)), 1.0)]
            return [(0.0, max(0.025, min(1.0, rr * 0.55)), 1.0)]
        called = any(k == "call" for k, a in acts)
        if called and raises_pre:
            hi = max(0.12, min(1.0, vp * 1.0))
            top = max(0.02, min(hi * 0.5, rr))
            return [(0.0, top, 0.35), (top, hi, 1.0)]
        if called:
            hi = max(0.2, min(1.0, vp))
            top = max(0.03, min(hi * 0.6, pfr))
            return [(0.0, top, 0.3), (top, hi, 1.0)]
        # checked (BB option) or no voluntary action
        top = max(0.03, min(0.5, pfr))
        return [(0.0, top, 0.3), (top, 1.0, 1.0)]

    def post_narrow(self, c, sid):
        vp, pfr, rr, agg, fvb, nh = seat_stats(c.mem, sid)
        keep_bet = max(0.3, min(0.9, 0.25 + 0.7 * agg))
        keep_raise = max(0.12, min(0.75, 0.1 + 0.5 * agg))
        f = 1.0
        for si in range(1, len(c.streets)):
            bet_open = False
            for (s, kk, a) in c.streets[si]:
                if kk == "raise":
                    if s == sid:
                        f *= keep_raise if bet_open else keep_bet
                    bet_open = True
                elif kk == "call" and s == sid:
                    f *= 0.72
        beta = max(0.05, min(0.6, 0.06 + 0.6 * (agg - 0.25)))
        if f >= 0.999:
            beta = 1.0
        return f, beta

    def equity_vs(self, c, mine, board, dead, segs, f_keep, beta, M):
        # sample combos
        mass = 0.0
        for lo, hi, w in segs:
            mass += (hi - lo) * w
        if mass <= 1e-9:
            segs = [(0.0, 1.0, 1.0)]
            mass = 1.0
        scale = M / (mass * 1326.0)
        out = []
        r = RNG.random
        for lo, hi, w in segs:
            k0 = int(lo * NCH)
            k1 = min(NCH - 1, int(hi * NCH - 1e-9))
            for kk in range(k0, k1 + 1):
                clo = kk / NCH
                chi = (kk + 1) / NCH
                ov = (min(hi, chi) - max(lo, clo)) * NCH
                if ov <= 0:
                    continue
                ch = CHUNKS[kk]
                n = len(ch)
                want = n * ov * w * scale
                take = int(want)
                if r() < want - take:
                    take += 1
                if take <= 0:
                    continue
                if take >= n:
                    out.extend(ch)
                else:
                    st0 = int(r() * n)
                    seg = ch[st0:st0 + take]
                    if len(seg) < take:
                        seg = seg + ch[:take - len(seg)]
                    out.extend(seg)
        out = [x for x in out if not (x[1] & dead)]
        if not out:
            return 0.5
        river = len(board) == 5
        if f_keep >= 0.999:
            lst = [x[0] for x in out]
            if river:
                return float(EXACT(mine, lst, board))
            return float(MC(mine, lst, board, max(200, min(500, 3 * len(lst)))))
        # narrowing by current hand value
        vals = []
        bl = board
        for x in out:
            vals.append((EVAL([x[2], x[3]] + bl), x))
        vals.sort(key=lambda t: -t[0])
        n = len(vals)
        ntop = max(1, int(round(n * f_keep)))
        if river:
            my = EVAL(mine + bl)
            num = 0.0
            den = 0.0
            for i, (v, x) in enumerate(vals):
                w = 1.0 if i < ntop else beta
                den += w
                if my > v:
                    num += w
                elif my == v:
                    num += 0.5 * w
            return num / den if den > 0 else 0.5
        lst = [x[0] for v, x in vals[:ntop]]
        if beta > 0 and ntop < n:
            acc = RNG.random()
            for v, x in vals[ntop:]:
                acc += beta
                if acc >= 1.0:
                    acc -= 1.0
                    lst.append(x[0])
        return float(MC(mine, lst, board, max(200, min(500, 3 * len(lst)))))

    # ------------------------------------------------------------------ action helpers
    def raise_to(self, c, total):
        la = c.lm.get("raise")
        if la is None:
            if "call" in c.lm:
                return Action.call()
            return Action.check() if "check" in c.lm else Action.fold()
        lo, hi = int(la.min_amount), int(la.max_amount)
        t = int(total)
        if t < lo:
            t = lo
        if t > hi:
            t = hi
        # if the raise leaves a tiny remainder, just go all-in
        if hi - t < 0.25 * t:
            t = hi
        return Action.raise_to(t)


# ---------------------------------------------------------------------------- warm-up at import
def _warm():
    try:
        from poker_agent_sdk import Seat, State, Config, LegalAction, Event
        K = getattr(poker_agent_sdk, "ActionKind", None)
        if K is None:
            return
        cfg = Config(table_id="w", seat=0, variant="holdem", players=3, starting_stack=2000,
                     blinds=[[10, 20]], hands_per_level=20, hand_cap=250, payouts=[50, 30, 20],
                     decision_ms=1, time_bank_ms=100, memory_bytes=65536)
        seats = [Seat(0, 1960, 0, "active"), Seat(1, 1960, 0, "active"), Seat(2, 1960, 0, "active")]
        hist = [Event("hand", None, 1), Event("blind", 1, 10), Event("blind", 2, 20), Event("raise", 0, 60),
                Event("call", 1, 50), Event("call", 2, 40), Event("board", None, None, ["Qh", "7c", "2d"]),
                Event("check", 1), Event("raise", 2, 60)]
        st = State(seat=0, cards=["As", "Kd"], board=["Qh", "7c", "2d"], pot=240, to_call=60,
                   legal_actions=[LegalAction(K.FOLD), LegalAction(K.CALL), LegalAction(K.RAISE, 120, 1960)],
                   history=hist, phase="betting", variant="holdem", seats=seats, button=0, blind_level=1,
                   blinds=[10, 20], hands_until_next_level=10, hand_number=1, players_remaining=3,
                   bust_order=[], time_bank_ms=100, config=cfg, events=hist)
        a = Agent()
        for _ in range(3):
            a.act(st, b"")
    except Exception:
        pass


_warm()
gc.collect()
try:
    gc.freeze()
except Exception:
    pass
