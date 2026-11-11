"""claude_aggro: aggressive, exploit-aware No-Limit Hold'em sit-and-go bot.

Design (see NOTES.md):
  * Preflop: wide position-based opens/steals widened by the observed fold-to-raise rates of the players behind,
    equity-vs-range calls and 3-bets from precomputed tables (pf.json), push/fold when short, ICM for all-ins.
  * Postflop: the villain range is a slice of preflop hands, narrowed by his line using *his own* observed
    aggression/fold frequencies; equity by eval7 Monte Carlo (river: exact count). Every option (check, bet sizes,
    call, raise, fold) is scored with a simple fold-equity EV model, so bluffs appear exactly where opponents fold.
  * Per-table opponent stats live in `memory` (compact JSON), rebuilt from `state.events`.
"""
import json
import marshal
import os
import random
import time

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "pf.json")) as _f:
    _PF = json.load(_f)

GRID = _PF["grid"]
EQR = _PF["eqr"]          # class -> equity vs top-x% ranges (x in GRID)
EQK = _PF["eqk"]          # class -> equity vs 1..7 random hands
ORDER = _PF["order"]      # classes, strongest first
RANKS = "23456789TJQKA"
SUITS = "shdc"
CARD = {r + s: eval7.Card(r + s) for r in RANKS for s in SUITS}


def _combos(cls):
    a, b = cls[0], cls[1]
    if a == b:
        return [(a + SUITS[x], b + SUITS[y]) for x in range(4) for y in range(x + 1, 4)]
    if cls[2] == "s":
        return [(a + s, b + s) for s in SUITS]
    return [(a + s, b + t) for s in SUITS for t in SUITS if s != t]


PCT = {}           # class -> percentile (midpoint of its combos in the ranking)
SORTED = []        # all 1326 combos as (Card, Card), strongest class first
_cum = 0
for _c in ORDER:
    _cb = _combos(_c)
    PCT[_c] = (_cum + len(_cb) / 2.0) / 1326.0
    _cum += len(_cb)
    SORTED.extend((CARD[x], CARD[y]) for x, y in _cb)
NSORT = len(SORTED)
try:  # keep the import-time tables out of later garbage-collection passes (latency spikes)
    import gc as _gc
    _gc.collect()
    _gc.freeze()
except Exception:
    pass

_rng = random.Random()
_DEBUG = bool(os.environ.get("AGGRO_DEBUG"))
# Tunables (defaults are the submitted values; the env override exists only for local A/B tests).
TUNE = {"open": 1.0, "push": 1.0, "fto": 0.74, "ftb": 0.45, "v3b": 0.58, "b3b": 0.55, "rip": 0.92, "roop": 0.76,
        "chk_oop": 0.82, "chk_ip": 0.95, "icmw": 0.75, "bsz": 1.0, "slow": 1.0, "jm": 0.01, "pm": 0.0, "fdecay": 0.65}
try:
    TUNE.update(json.loads(os.environ.get("AGGRO_TUNE", "{}")))
except Exception:
    pass

# stat indices (per seat, per table)
N, VP, PR, OO, OP, FSO, FS, F3O, F3, BO, BT, FBO, FB, RB, JA, TO, TB, PRO, PRF = range(19)
NST = 19

PUSH_BASE = {1: 0.62, 2: 0.42, 3: 0.31, 4: 0.25, 5: 0.21, 6: 0.18, 7: 0.16}
OPEN_BASE = {1: 0.60, 2: 0.50, 3: 0.36, 4: 0.27, 5: 0.21, 6: 0.17, 7: 0.15}


# ----------------------------------------------------------------------------- helpers
def ga(o, name, default=None):
    if isinstance(o, dict):
        return o.get(name, default)
    return getattr(o, name, default)


_KN = {}


def kname(k):
    if type(k) is str:
        return k if k.islower() else k.lower()
    try:
        return _KN[k]
    except (KeyError, TypeError):
        pass
    v = getattr(k, "value", k)
    if isinstance(v, str):
        r = v.lower()
    else:
        n = getattr(k, "name", None)
        r = n.lower() if isinstance(n, str) else str(k).lower().split(".")[-1]
    try:
        _KN[k] = r
    except TypeError:
        pass
    return r


def ef(e):
    """(kind, seat, amount) of an event, whether it is an object or a dict."""
    if type(e) is dict:
        k, s, a = e.get("kind"), e.get("seat"), e.get("amount")
    else:
        k, s, a = getattr(e, "kind", None), getattr(e, "seat", None), getattr(e, "amount", None)
    k = kname(k)
    if k == "bet":
        k = "raise"
    return k, s, a or 0


def norm_card(c):
    c = str(c)
    if c.startswith("10"):
        c = "T" + c[2:]
    return c[0].upper() + c[1].lower()


def hclass(c1, c2):
    r1, r2 = c1[0], c2[0]
    i1, i2 = RANKS.index(r1), RANKS.index(r2)
    if i1 < i2:
        r1, r2 = r2, r1
    if r1 == r2:
        return r1 + r2
    return r1 + r2 + ("s" if c1[1] == c2[1] else "o")


def eq_top(cls, x):
    row = EQR[cls]
    g = GRID
    if x <= g[0]:
        return row[0]
    for i in range(1, len(g)):
        if x <= g[i]:
            t = (x - g[i - 1]) / (g[i] - g[i - 1])
            return row[i - 1] + t * (row[i] - row[i - 1])
    return row[-1]


def eq_band(cls, lo, hi):
    """Equity of class vs the range slice [lo, hi] of the ranking (fractions of all combos)."""
    hi = max(min(hi, 1.0), 0.01)
    lo = max(0.0, min(lo, hi - 0.01))
    if lo < 0.015:
        return eq_top(cls, hi)
    a = eq_top(cls, hi) * hi - eq_top(cls, lo) * lo
    return min(0.99, max(0.01, a / (hi - lo)))


def freq(st, x, n, prior, w):
    return (st[x] + prior * w) / (st[n] + w)


def icm_me(stacks, i, pay):
    """Malmuth-Harville ICM equity of player i (only the paid places that remain)."""
    T = float(sum(stacks))
    if T <= 0 or stacks[i] <= 0:
        return 0.0
    n = len(stacks)
    pay = pay[:n]
    si = stacks[i]
    tot = pay[0] * si / T if pay else 0.0
    if len(pay) > 1 and pay[1]:
        for j in range(n):
            if j == i or stacks[j] <= 0:
                continue
            pj = stacks[j] / T
            T1 = T - stacks[j]
            tot += pay[1] * pj * si / T1
            if len(pay) > 2 and pay[2]:
                for k in range(n):
                    if k == i or k == j or stacks[k] <= 0:
                        continue
                    pk = pj * stacks[k] / T1
                    T2 = T1 - stacks[k]
                    tot += pay[2] * pk * si / T2
                    if len(pay) > 3 and pay[3]:
                        for l in range(n):
                            if l in (i, j, k) or stacks[l] <= 0:
                                continue
                            T3 = T2 - stacks[l]
                            tot += pay[3] * pk * stacks[l] / T2 * si / T3
    return tot


# ----------------------------------------------------------------------------- memory / tracking
def new_ctx(n, sk):
    return {"st": 0, "nr": 0, "lp": 0, "lv": 0, "cb": [0] * n, "sn": [0] * n, "vp": [0] * n, "pr": [0] * n,
            "fr": [0] * n, "an": [0] * n, "ag": [0] * n, "rs": [], "sk": sk}


def track(events, M, n):
    S = M["s"]
    c = M["c"]
    for e in events:
        k, s, a = ef(e)
        if k == "hand":
            c = new_ctx(n, c["sk"])
            continue
        if s is None or not (0 <= s < n):
            if k == "board":
                c["st"] += 1
                c["cb"] = [0] * n
                c["ag"] = [0] * n
                c["lv"] = 0
            continue
        if k == "stack":
            c["sk"][s] = a
            continue
        if k == "ante":
            c["an"][s] += a
            continue
        if k == "blind":
            c["cb"][s] += a
            if c["cb"][s] > c["lv"]:
                c["lv"] = c["cb"][s]
            continue
        if k not in ("fold", "check", "call", "raise"):
            continue
        st = S[s]
        cb = c["cb"]
        if c["st"] == 0:
            if not c["sn"][s]:
                c["sn"][s] = 1
                st[N] += 1
                if c["nr"] == 0 and c["lp"] == 0:
                    st[OO] += 1
                    if k == "raise":
                        st[OP] += 1
            nr = c["nr"]
            if nr == 0:
                if k == "call":
                    c["lp"] += 1
            elif s in c["rs"]:
                st[F3O] += 1
                if k == "fold":
                    st[F3] += 1
            elif not c["fr"][s]:
                c["fr"][s] = 1
                st[TO] += 1
                if k == "raise":
                    st[TB] += 1
                if nr == 1:
                    st[FSO] += 1
                    if k == "fold":
                        st[FS] += 1
            if k in ("call", "raise") and not c["vp"][s]:
                c["vp"][s] = 1
                st[VP] += 1
            if k == "raise":
                if not c["pr"][s]:
                    c["pr"][s] = 1
                    st[PR] += 1
                c["rs"].append(s)
                c["nr"] += 1
                if a >= 0.97 * (c["sk"][s] - c["an"][s]) and c["nr"] == 1:
                    st[JA] += 1
        else:
            if c["lv"] > cb[s]:
                st[FBO] += 1
                if k == "fold":
                    st[FB] += 1
                elif k == "raise":
                    st[RB] += 1
                if c["ag"][s]:
                    st[PRO] += 1
                    if k == "fold":
                        st[PRF] += 1
            else:
                st[BO] += 1
                if k == "raise":
                    st[BT] += 1
        if k == "call":
            cb[s] += a
        elif k == "raise":
            cb[s] = a
            if c["st"] > 0:
                c["ag"][s] = 1
            if a > c["lv"]:
                c["lv"] = a
    M["c"] = c


MEM_TAG = b"CA1"


def load_mem(memory, n, start):
    try:
        if memory and bytes(memory[:3]) == MEM_TAG:
            M = marshal.loads(bytes(memory[3:]))
            if len(M["s"]) == n and len(M["s"][0]) == NST:
                return M
    except Exception:
        pass
    return {"s": [[0] * NST for _ in range(n)], "c": new_ctx(n, [start] * n)}


# ----------------------------------------------------------------------------- the bot
class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        t0 = time.perf_counter()
        mem_out = memory
        try:
            cfg = state.config
            n = int(ga(cfg, "players") or len(state.seats))
            n = max(n, max(ga(x, "seat") for x in state.seats) + 1)
            M = load_mem(memory, n, ga(cfg, "starting_stack") or 2000)
            track(state.events or [], M, n)
            mem_out = MEM_TAG + marshal.dumps(M)
            if len(mem_out) > 60000:
                M = {"s": M["s"], "c": new_ctx(n, M["c"]["sk"])}
                mem_out = MEM_TAG + marshal.dumps(M)
        except Exception:
            M = None
        try:
            act = Decider(state, M, t0).decide()
            if act is not None:
                return act, mem_out
        except Exception:
            pass
        return self._fallback(state), mem_out

    @staticmethod
    def _fallback(state):
        for la in state.legal_actions:
            if kname(la.kind) == "check":
                return Action.check()
        return Action.fold()


class Decider:
    def __init__(self, state, M, t0):
        self.s = state
        self.t0 = t0
        try:
            dms = float(ga(state.config, "decision_ms") or 1)
        except Exception:
            dms = 1.0
        # wall-clock budget. Guards below are fractions of it measured on the machine we run on; "slow" > 1 only
        # emulates the ~2.5x slower tournament machines in local tests.
        self.budget = max(0.001, dms / 1000.0) / TUNE["slow"]
        # Lite mode: if the per-table time bank is running low, use only cheap estimates until it recovers.
        try:
            bank = state.time_bank_ms
            full = ga(state.config, "time_bank_ms")
            self.lite = bank is not None and full and float(bank) < 0.4 * float(full)
        except Exception:
            self.lite = False
        self.M = M
        self.legal = {kname(la.kind): la for la in state.legal_actions}
        self.me = state.seat
        cfg = state.config
        self.pay = list(ga(cfg, "payouts") or [50, 30, 20])
        bl = state.blinds or [10, 20]
        self.bb = max(1, bl[1] if len(bl) > 1 else bl[0])
        self.seats = {}
        self.status = {}
        self.stk = {}
        self.sbet = {}
        for x in state.seats:
            if type(x) is dict:
                sn, stt, sk, bt = x.get("seat"), x.get("status"), x.get("stack"), x.get("bet")
            else:
                sn, stt, sk, bt = x.seat, x.status, x.stack, x.bet
            self.seats[sn] = x
            self.status[sn] = kname(stt) if stt is not None else "active"
            self.stk[sn] = sk or 0
            self.sbet[sn] = bt or 0
        self.stack = self.stk[self.me]
        self.mybet = self.sbet[self.me]
        self.to_call = state.to_call or 0
        self.pot = state.pot or 0
        cap = self.stack + self.mybet
        self.pot_eff = self.pot - sum(max(0, b - cap) for sn, b in self.sbet.items() if sn != self.me)
        self.cards = [norm_card(c) for c in state.cards]
        self.board = [norm_card(c) for c in (state.board or [])]
        self.street = {0: 0, 3: 1, 4: 2, 5: 3}.get(len(self.board), 3)
        self.opps_in = [s for s, x in self.status.items() if s != self.me and x in ("active", "all_in")]
        self.opps_act = [s for s in self.opps_in if self.status[s] == "active"]
        self.n = len(self.seats)
        self.stats = M["s"] if M else [[0] * NST for _ in range(max(self.seats) + 1)]
        self._parse_history()

    # ------------------------------------------------------------------ history of this hand
    def _parse_history(self):
        st = 0
        cb = {}
        lv = 0
        pot = 0
        self.blind_seats = []
        self.pf_nr = 0
        self.pf_raisers = []
        self.pf_last_amt = 0
        self.limpers = []
        self.act = {}       # seat -> list of (street, kind, nr_before/facing, size_frac, allin)
        self.street_aggr = [None, None, None, None]
        self.street_nr = [0, 0, 0, 0]
        self.street_bet = 0
        stacks0 = None
        status = self.status
        for e in (self.s.history or []):
            k, s, a = ef(e)
            if k == "board":
                st += 1
                cb = {}
                lv = 0
                continue
            if k == "ante":
                pot += a
                continue
            if k == "blind":
                self.blind_seats.append(s)
                cb[s] = cb.get(s, 0) + a
                lv = max(lv, cb[s])
                pot += a
                continue
            if k not in ("fold", "check", "call", "raise") or s is None:
                continue
            facing = lv > cb.get(s, 0)
            frac = 0.0
            if k == "raise":
                add = a - cb.get(s, 0)
                frac = (a - lv) / max(1.0, pot + (lv - cb.get(s, 0)))
                pot += add
                cb[s] = a
                lv = a
                self.street_aggr[min(st, 3)] = s
                self.street_nr[min(st, 3)] += 1
                if st == 0:
                    self.pf_nr += 1
                    self.pf_raisers.append(s)
                    self.pf_last_amt = a
            elif k == "call":
                pot += a
                cb[s] = cb.get(s, 0) + a
                if st == 0 and self.pf_nr == 0:
                    self.limpers.append(s)
            allin = k != "fold" and k != "check" and status.get(s) == "all_in"
            nrb = self.pf_nr - (1 if k == "raise" else 0) if st == 0 else (1 if facing else 0)
            self.act.setdefault(s, []).append((st, k, nrb, frac, allin))
        self.cur_lv = lv
        self.pf_aggr = self.pf_raisers[-1] if self.pf_raisers else None
        live = sorted(s for s, x in self.status.items() if x != "busted")
        btn = self.s.button
        # postflop order: first live seat after button
        post = sorted(live, key=lambda s: (s - btn - 1) % max(self.n, 1))
        self.post_order = post
        bbs = self.blind_seats[-1] if self.blind_seats else post[min(1, len(post) - 1)]
        self.bb_seat = bbs
        self.pre_order = sorted(live, key=lambda s: (s - bbs - 1) % max(self.n, 1))
        self.stacks0 = stacks0

    # ------------------------------------------------------------------ action builders
    def a_fold(self):
        if "check" in self.legal:
            return Action.check()
        if "fold" in self.legal:
            return Action.fold()
        return Action.call()

    def a_call(self):
        if "check" in self.legal:
            return Action.check()
        if "call" in self.legal:
            return Action.call()
        return self.a_fold()

    def a_raise(self, total):
        la = self.legal.get("raise")
        if la is None:
            return self.a_call()
        lo, hi = int(la.min_amount), int(la.max_amount)
        t = int(total)
        if t >= hi * 0.8 or (hi - t) < 2.5 * self.bb:
            t = hi
        t = max(lo, min(hi, t))
        return Action.raise_to(t)

    def a_jam(self):
        la = self.legal.get("raise")
        if la is None:
            return self.a_call()
        return Action.raise_to(int(la.max_amount))

    # ------------------------------------------------------------------ opponent model helpers
    def st(self, s):
        try:
            return self.stats[s]
        except Exception:
            return [0] * NST

    def fold_to_open(self, s):
        return freq(self.st(s), FS, FSO, TUNE["fto"], 6)

    def fold_to_3b(self, s):
        return freq(self.st(s), F3, F3O, 0.55, 4)

    def fold_to_bet(self, s):
        return freq(self.st(s), FB, FBO, TUNE["ftb"], 6)

    def agg_freq(self, s):
        x = self.st(s)
        return (x[BT] + x[RB] + 0.30 * 6) / (x[BO] + x[FBO] + 6)

    def raise_freq(self, s):
        return freq(self.st(s), RB, FBO, 0.10, 6)

    def total(self, s):
        return self.stk[s] + self.sbet[s]

    def pf_range(self, s):
        """(lo, hi) slice of the preflop ranking that seat s holds, from his preflop actions this hand."""
        x = self.st(s)
        vpip = freq(x, VP, N, 0.30, 8)
        opf = freq(x, OP, OO, 0.22, 8)
        tbf = freq(x, TB, TO, 0.08, 8)
        jam = freq(x, JA, N, 0.03, 10)
        lo, hi = 0.0, 1.0
        acts = [a for a in self.act.get(s, []) if a[0] == 0]
        for (_, k, nrb, _, allin) in acts:
            if k == "raise":
                if nrb == 0:
                    h = max(0.04, min(1.0, opf * 1.1))
                    if allin:
                        h = max(0.03, min(1.0, max(jam * 1.2, 0.5 * h)))
                elif nrb == 1:
                    h = max(0.025, min(0.7, tbf * 1.2))
                    if allin:
                        h = max(h, 0.04)
                else:
                    h = max(0.015, min(0.4, tbf * 0.6))
                hi = min(hi, h)
                lo = 0.0
            elif k == "call":
                if nrb == 0:
                    l, h = 0.03, max(0.12, min(1.0, vpip * 1.1))
                elif nrb == 1:
                    l, h = min(0.03, tbf * 0.4), max(0.10, min(1.0, vpip * 1.0 + (0.15 if s == self.bb_seat else 0)))
                    if allin:
                        l, h = 0.0, max(0.05, min(1.0, vpip * 0.5))
                else:
                    l, h = 0.0, max(0.05, min(0.5, vpip * 0.45))
                hi = min(hi, h)
                lo = max(lo, l) if lo < hi * 0.5 else lo
        if lo >= hi - 0.02:
            lo = 0.0
        return lo, hi

    # ------------------------------------------------------------------ main
    def decide(self):
        if not self.legal:
            return None
        if len(self.legal) == 1:
            k = next(iter(self.legal))
            return {"check": Action.check, "call": Action.call, "fold": Action.fold}.get(k, self.a_fold)()
        if self.street == 0:
            return self.preflop()
        return self.postflop()

    # ------------------------------------------------------------------ ICM helpers
    def stack_vec(self):
        order = sorted(s for s, x in self.status.items() if x != "busted")
        return order, [self.stacks_now(s) for s in order]

    def stacks_now(self, s):
        return self.stk[s]

    def icm_allin_req(self, vill, call_amt):
        """Equity needed to call an all-in from `vill` for call_amt (ICM, blended with chip EV)."""
        chip_req = call_amt / float(self.pot_eff + call_amt)
        order, stacks = self.stack_vec()
        if len(order) <= 2 or len(self.pay) < 2:
            return chip_req
        i = order.index(self.me)
        my_behind = self.stack
        call = min(call_amt, my_behind)
        excess = max(0, self.to_call - my_behind)
        pot_final = self.pot + call - excess
        fold_v = stacks[:]
        j = order.index(vill) if vill in order else None
        if j is not None:
            fold_v[j] += self.pot
        win_v = stacks[:]
        win_v[i] = my_behind - call + pot_final
        if j is not None:
            win_v[j] = stacks[j] + excess
        lose_v = stacks[:]
        lose_v[i] = my_behind - call
        if j is not None:
            lose_v[j] += pot_final
        pay = self.pay
        ef, ew, el = icm_me(fold_v, i, pay), icm_me(win_v, i, pay), icm_me(lose_v, i, pay)
        if ew - el <= 1e-9:
            return chip_req
        icm_req = (ef - el) / (ew - el)
        w = 1.0 if len(order) <= 4 else TUNE["icmw"]
        return chip_req + w * (icm_req - chip_req)

    def icm_jam_ev(self, fe, eq_c, vill):
        """ICM EV of jamming (relative to folding now) vs a single main villain who folds with prob fe."""
        order, stacks = self.stack_vec()
        i = order.index(self.me)
        my_total = self.stack
        j = order.index(vill) if vill in order else None
        vbehind = stacks[j] if j is not None else my_total
        vbet = self.sbet.get(vill, 0)
        risk = min(my_total, vbehind + vbet - self.mybet)  # chips I add that can be matched
        risk = max(risk, 0)
        fold_v = stacks[:]
        if j is not None:
            fold_v[j] += self.pot
        steal_v = stacks[:]
        steal_v[i] = my_total + self.pot
        pot_called = self.pot + risk + max(0, risk + self.mybet - vbet)
        win_v = stacks[:]
        win_v[i] = my_total - risk + pot_called
        lose_v = stacks[:]
        lose_v[i] = my_total - risk
        if j is not None:
            v_add = max(0, risk + self.mybet - vbet)
            win_v[j] = stacks[j] - v_add
            lose_v[j] = stacks[j] - v_add + pot_called
        pay = self.pay if len(order) > 2 else [1.0, 0.0]
        if len(order) <= 2:
            # heads-up: chip EV (winner takes the rest of the points proportionally)
            ef = fold_v[i]
            ev = fe * steal_v[i] + (1 - fe) * (eq_c * win_v[i] + (1 - eq_c) * lose_v[i])
            return ev - ef
        ef = icm_me(fold_v, i, pay)
        ev = fe * icm_me(steal_v, i, pay) + (1 - fe) * (eq_c * icm_me(win_v, i, pay) + (1 - eq_c) * icm_me(lose_v, i, pay))
        return ev - ef

    # ------------------------------------------------------------------ preflop
    def n_behind(self):
        order = self.pre_order
        if self.me not in order:
            return 0
        i = order.index(self.me)
        return sum(1 for s in order[i + 1:] if self.status[s] == "active")

    def eff_stack(self):
        my_total = self.stack + self.mybet
        others = [self.total(s) for s in self.opps_in]
        if not others:
            return my_total
        return min(my_total, max(others))

    def preflop(self):
        cls = hclass(self.cards[0], self.cards[1])
        pct = PCT[cls]
        bb = self.bb
        eff = self.eff_stack()
        effbb = eff / float(bb)
        nb = self.n_behind()
        behind = self.pre_order[self.pre_order.index(self.me) + 1:] if self.me in self.pre_order else []
        behind = [s for s in behind if self.status[s] == "active"]

        if self.pf_nr == 0:
            nlimp = len(self.limpers)
            if self.to_call == 0:
                # BB option after limps / SB complete
                if "raise" not in self.legal:
                    return self.a_call()
                thr = 0.30 if (nlimp <= 1 and self.limpers and self.limpers[0] in self.blind_seats) else 0.16
                thr *= 0.75 ** max(0, nlimp - 1)
                if effbb <= 12:
                    if pct <= min(0.5, thr * 1.2):
                        return self.a_jam()
                    return self.a_call()
                if pct <= thr:
                    return self.a_raise(self.cur_lv + bb * (2.5 + nlimp))
                return self.a_call()
            # first in (or facing limpers)
            pf_all = 1.0
            pf_exp = 1.0
            for s in behind:
                pf_all *= self.fold_to_open(s)
                pf_exp *= TUNE["fto"]
            if effbb <= 13.5:
                k = max(1, min(7, nb))
                thr = PUSH_BASE[k] * TUNE["push"] * (10.0 / max(effbb, 1.0)) ** 0.85
                thr *= 0.65 ** nlimp
                thr += max(0.0, pf_all - pf_exp) * 1.2
                if pct <= min(1.0, thr):
                    return self.a_jam()
                if self.to_call == 0:
                    return self.a_call()
                return self.a_fold()
            k = max(1, min(7, nb))
            thr = OPEN_BASE[k] * TUNE["open"]
            ratio = pf_all / max(pf_exp, 1e-6)
            thr = thr * max(0.6, min(1.0, ratio)) + max(0.0, pf_all - pf_exp) * 1.6
            if nlimp:
                thr = min(thr, 0.22) * 0.75 ** (nlimp - 1)
            if effbb < 25:
                thr *= 0.9
            if pct <= min(1.0, thr):
                size = bb * (2.2 if nb <= 3 else 2.4)
                if nb == 1:
                    size = bb * 2.6
                size += nlimp * bb
                if effbb < 22:
                    size = bb * 2.0 + nlimp * bb
                return self.a_raise(size)
            # SB: complete with decent hands when BB is passive and cheap
            if nb == 1 and self.to_call <= bb * 0.5 + 1 and pct <= 0.75:
                bbs = behind[0] if behind else None
                if bbs is not None and freq(self.st(bbs), TB, TO, 0.08, 8) < 0.15:
                    return self.a_call()
            return self.a_fold()

        # ---------------- facing a raise
        rz = self.pf_aggr
        lo, hi = self.pf_range(rz) if rz is not None else (0.0, 0.3)
        eq_r = eq_band(cls, lo, hi)
        others = [s for s in self.opps_in if s != rz and any(a[0] == 0 and a[1] in ("call", "raise") for a in self.act.get(s, []))]
        eq_m = eq_r ** (1 + 0.65 * len(others))
        eq_m *= 0.985 ** len(behind)
        call_amt = min(self.to_call, self.stack)
        rz_allin = rz is not None and self.status[rz] == "all_in"
        odds = call_amt / float(self.pot_eff + call_amt)
        ip = nb == 0 or (self.me == self.post_order[-1] if self.post_order else False)
        my_total = self.stack + self.mybet
        commit = (call_amt >= 0.38 * self.stack) or effbb <= 16 or (self.pf_last_amt >= 0.33 * eff)
        all_others_allin = not self.opps_act or (len(self.opps_act) == 0)

        if rz_allin or call_amt >= self.stack or ("raise" not in self.legal) or all_others_allin:
            # pure call / fold
            req = self.icm_allin_req(rz, call_amt) if (call_amt >= 0.3 * self.stack) else odds
            if eq_m >= req + TUNE["jm"]:
                return self.a_call()
            return self.a_fold()

        if commit:
            # jam or fold (or call when the price is tiny)
            fe0 = 1.0 - min(1.0, max(0.03, 0.07 / max(hi, 0.01)) * (1.0 if self.pf_nr == 1 else 1.6))
            fe = (self.st(rz)[F3] + fe0 * 3) / (self.st(rz)[F3O] + 3) if self.pf_nr >= 1 else fe0
            if len(others) > 0:
                fe *= 0.6 ** len(others)
            fe *= 0.9 ** len(behind)
            cont_hi = max(0.015, hi * (1 - fe0))
            eq_c = eq_band(cls, 0.0, cont_hi) ** (1 + 0.65 * len(others))
            ev_jam = self.icm_jam_ev(fe, eq_c, rz)
            ev_call_ok = eq_m * 0.85 >= odds and call_amt <= 0.2 * self.stack
            if ev_jam > 0 and (eq_m >= 0.40 or fe >= 0.5):
                return self.a_jam()
            if ev_call_ok:
                return self.a_call()
            if ev_jam > 0:
                return self.a_jam()
            return self.a_fold()

        # deep: 3-bet for value / bluff, call, fold
        lv = self.cur_lv
        if self.pf_nr == 1:
            size = lv * (3.0 if ip else 3.7) + len(others) * lv
        else:
            size = lv * (2.3 if ip else 2.6) + len(others) * lv
        value_thr = TUNE["v3b"] if self.pf_nr == 1 else TUNE["v3b"] + 0.02
        if eq_r >= value_thr or pct <= 0.012:
            if size >= 0.33 * my_total:
                return self.a_jam()
            return self.a_raise(size)
        # bluff 3-bet vs wide openers who fold to 3-bets
        if self.pf_nr == 1 and hi >= 0.20 and not others and rz is not None:
            f3 = self.fold_to_3b(rz)
            suited = len(cls) == 3 and cls[2] == "s"
            if f3 >= 0.5 and (suited or cls[0] == "A") and 0.06 < pct < 0.40 and _rng.random() < TUNE["b3b"]:
                if f3 * self.pot - (1 - f3) * (size - self.mybet) * 0.55 > 0:
                    return self.a_raise(size)
        real = TUNE["rip"] if ip else TUNE["roop"]
        bonus = 0.0
        if effbb > 40 and (cls[0] == cls[1] or (len(cls) == 3 and cls[2] == "s")):
            bonus = 0.03
        if (eq_m + bonus) * real >= odds and (call_amt <= 0.22 * self.stack or eq_r >= 0.5):
            return self.a_call()
        return self.a_fold()

    # ------------------------------------------------------------------ postflop
    def villain_keep(self, s):
        """Fraction of his preflop slice that seat s still holds after his postflop line, calls made, raises made."""
        keep = 1.0
        af = self.agg_freq(s)
        ff = self.fold_to_bet(s)
        rf = self.raise_freq(s)
        ncalls = 0
        nraise = 0
        agg_st = -1
        for (stt, k, facing, frac, allin) in self.act.get(s, []):
            if stt == 0:
                continue
            if k == "raise":
                if facing and agg_st == stt:
                    m = max(0.06, min(0.6, rf * 0.8 + 0.02))
                    nraise += 1
                elif facing:
                    m = max(0.08, min(0.9, rf * 1.2 + 0.04))
                    nraise += 1
                else:
                    m = max(0.15, min(0.95, af * 1.05 + 0.06))
                agg_st = stt
                if frac >= 0.9:
                    m *= 0.85
                if allin:
                    m *= 0.9
                keep *= m
            elif k == "call":
                keep *= max(0.3, 1 - ff * 0.8)
                ncalls += 1
        return max(0.05, keep), ncalls, nraise

    def villain_range(self, s, K, deadc, board):
        """Sorted (strength desc) list of (value, combo) approximating seat s's current range."""
        lo, hi = self.pf_range(s)
        keep, ncalls, nraise = self.villain_keep(s)
        if keep * K < 10:
            K = min(150, int(10 / max(keep, 0.01)) + 1)
        a0 = int(lo * NSORT)
        a1 = min(NSORT, max(a0 + 8, int(hi * NSORT)))
        span = a1 - a0
        samp = []
        rr = _rng.random
        tries = 0
        while len(samp) < K and tries < K * 4:
            tries += 1
            cb = SORTED[a0 + int(rr() * span)]
            if cb[0] in deadc or cb[1] in deadc:
                continue
            samp.append(cb)
        if len(samp) < 6:
            samp = [cb for cb in SORTED if cb[0] not in deadc and cb[1] not in deadc][:K]
        ev7 = eval7.evaluate
        scored = sorted(((ev7([c[0], c[1]] + board), c) for c in samp), key=lambda t: -t[0])
        self._raw = scored
        nk = max(8, int(round(keep * len(scored))))
        if nk >= len(scored):
            return scored
        # most of the kept range is the strongest part; a slice of random hands stands for draws and bluffs
        bl = max(0.05, min(0.3, self.agg_freq(s) - 0.12))
        if nraise:
            bl *= 0.5
        ntop = max(5, int(round(nk * (1 - bl))))
        out = scored[:ntop]
        rest = scored[ntop:]
        if rest and nk > ntop:
            out = out + _rng.sample(rest, min(len(rest), nk - ntop))
            out.sort(key=lambda t: -t[0])
        return out

    def fold_to_reraise(self, s):
        return freq(self.st(s), PRF, PRO, 0.30, 5)

    def postflop(self):
        hero = [CARD[c] for c in self.cards]
        board = [CARD[c] for c in self.board]
        deadc = set(hero + board)
        vills = self.opps_in
        if not vills:
            return self.a_call()
        street = self.street
        main = self.street_aggr[street]
        if main is None or main not in vills:
            main = self.pf_aggr if self.pf_aggr in vills else max(vills, key=lambda s: self.total(s))
        others = [s for s in vills if s != main]
        hv = eval7.evaluate(hero + board)

        def equity(sub, it):
            if not sub:
                return 0.5
            if street == 3:
                w = 0.0
                for v, _ in sub:
                    if hv > v:
                        w += 1
                    elif hv == v:
                        w += 0.5
                return w / len(sub)
            lst = [(c, 1.0) for _, c in sub]
            if len(lst) > 48:  # eval7's sampler is biased on long ordered lists
                _rng.shuffle(lst)
            return eval7.py_hand_vs_range_monte_carlo(hero, lst, board, it)

        rng_m = self.villain_range(main, 24 if self.lite else 56, deadc, board)
        raw = self._raw
        beat = sum(1 for v, _ in raw if v < hv) + 0.5 * sum(1 for v, _ in raw if v == hv)
        pct_raw = beat / max(1, len(raw))  # made-hand percentile vs his unnarrowed range
        it_main = 60 if self.lite else (200 if street == 1 else 160)
        eq_main = equity(rng_m, it_main)
        # robustness floor: never treat a near-nut hand as dead because the range model got too narrow
        eq_main = max(eq_main, 0.35 * pct_raw ** 4)
        eq_oth = 1.0
        for s in (others[:3] if not self.lite else []):
            if (time.perf_counter() - self.t0) > 0.45 * self.budget:
                eq_oth *= eq_main ** 0.8
                continue
            r = self.villain_range(s, 32, deadc, board)
            eq_oth *= equity(r, 120)
        for s in (others[3:] if not self.lite else others):
            eq_oth *= eq_main ** 0.8
        eq = eq_main * eq_oth
        pot = float(self.pot_eff)
        stack = self.stack
        act_order = [s for s in self.post_order if s == self.me or s in self.opps_act]
        ip = bool(act_order) and self.me == act_order[-1]
        lim = 0.60 * self.budget
        t0 = self.t0
        pc = time.perf_counter

        def fe_of(size_frac):
            f = 1.0
            for s in vills:
                if self.status[s] == "all_in":
                    return 0.0
                base = self.fold_to_bet(s)
                _, nc, _ = self.villain_keep(s)
                base *= TUNE["fdecay"] ** nc  # a player who already called postflop is much less likely to fold
                base *= {1: 1.0, 2: 0.93, 3: 0.88}[street]
                f *= max(0.0, min(0.92, base * (0.72 + 0.42 * min(size_frac, 1.5))))
            return f

        def eq_vs_top(frac_continue):
            if self.lite or pc() - t0 > lim:
                return max(0.0, eq - 0.12 * (1 - frac_continue))
            m = max(3, int(round(len(rng_m) * frac_continue)))
            return equity(rng_m[:m], 140) * eq_oth

        to_call = self.to_call
        if to_call <= 0:
            r_check = 1.0 if street == 3 else (TUNE["chk_ip"] if ip else TUNE["chk_oop"])
            best = ("check", eq * pot * r_check, 0)
            if "raise" in self.legal and any(self.status[s] == "active" for s in vills):
                sizes = {1: (0.33, 0.6), 2: (0.5, 0.8), 3: (0.5, 0.85)}[street]
                spr = stack / max(pot, 1.0)
                cand = list(sizes)
                if spr <= 1.6:
                    cand.append(spr)
                for fr in cand:
                    b = min(stack, max(self.bb, fr * TUNE["bsz"] * pot))
                    fe = fe_of(b / pot)
                    # his calling range tightens with the size: continue fraction shrinks a bit more for big bets
                    cont = max(0.12, (1 - fe) * (1.0 if fr <= 0.7 else 0.85))
                    eqc_b = eq_vs_top(cont)
                    ev = fe * pot + (1 - fe) * (eqc_b * (pot + 2 * b) - b)
                    if ev > best[1]:
                        best = ("bet", ev, b)
            if best[0] == "bet":
                return self.a_raise(self.mybet + best[2])
            return self.a_call()

        # ---- facing a bet
        call_amt = min(to_call, stack)
        odds = call_amt / (pot + call_amt)
        r_call = 1.0 if street == 3 else (0.97 if ip else 0.9)
        ev_call = eq * r_call * (pot + call_amt) - call_amt
        if call_amt >= 0.35 * stack and len(self.stack_vec()[0]) > 2:
            req_icm = self.icm_allin_req(main, call_amt)
            req = req_icm if call_amt >= 0.9 * stack else odds + 0.6 * (req_icm - odds)
            ev_call = (eq * r_call - req - TUNE["pm"]) * (pot + call_amt)
        best = ("fold", 0.0, 0)
        if ev_call > 0:
            best = ("call", ev_call, 0)
        can_raise = "raise" in self.legal and any(self.status[s] == "active" for s in vills)
        nr_street = self.street_nr[street]
        if can_raise and stack > call_amt:
            lv = self.cur_lv
            la = self.legal["raise"]
            r_to = max(int(la.min_amount), int(lv * 2.6 + (pot - lv - self.mybet) * 0.3))
            r_to = min(r_to, int(la.max_amount))
            add = r_to - self.mybet
            if add >= 0.6 * stack:
                r_to = int(la.max_amount)
                add = r_to - self.mybet
            # the bettor folds only the weak part of his betting range
            fe = 1.0
            for s in vills:
                if self.status[s] != "active":
                    fe = 0.0
                    break
                _, nc_s, nr_s = self.villain_keep(s)
                if s == main:
                    f = self.fold_to_reraise(s) if nr_street <= 1 else 0.12
                else:
                    f = self.fold_to_bet(s) * 1.1
                f *= 0.6 ** (nc_s + nr_s)
                f *= 0.8 + 0.25 * min(1.5, add / max(pot, 1.0))
                fe *= max(0.0, min(0.85, f))
            eqc = eq_vs_top(max(0.15, 1 - fe))
            vcall = r_to - lv
            ev_r = fe * pot + (1 - fe) * (eqc * (pot + add + vcall) - add)
            value_ok = eq >= 0.58 and eqc >= 0.55
            semi_ok = (nr_street <= 1 and street == 1 and eq >= 0.33 and fe >= 0.40 and not others)
            if nr_street >= 2:
                value_ok = eq >= 0.62 and eqc >= 0.55
                semi_ok = False
            if ev_r > best[1] and (value_ok or semi_ok):
                best = ("raise", ev_r, r_to)
        if _DEBUG and best[0] == "raise" and nr_street >= 1:
            print("DBG", self.cards, self.board, "nr", nr_street, "eq %.2f eqm %.2f eqc %.2f fe %.2f" % (eq, eq_main, eqc, fe),
                  "rng", [(str(c[0]) + str(c[1])) for _, c in rng_m][:12], len(rng_m), "keep", self.villain_keep(main), "pf", self.pf_range(main))
        if best[0] == "raise":
            return self.a_raise(best[2])
        if best[0] == "call":
            return self.a_call()
        return self.a_fold()


def _warmup():
    """Run a couple of synthetic decisions at import so the first real decision is not a cold one."""
    from types import SimpleNamespace as NS
    cfg = NS(table_id="w", seat=0, variant="holdem", players=3, starting_stack=2000, blinds=[[10, 20]],
             hands_per_level=20, hand_cap=250, payouts=[50, 30, 20], decision_ms=1, time_bank_ms=100,
             memory_bytes=65536)
    ev = lambda k, s=None, a=None, c=None: NS(kind=k, seat=s, amount=a, cards=c)
    la = lambda k, lo=0, hi=0: NS(kind=k, min_amount=lo, max_amount=hi)
    h0 = [ev("hand", None, 1), ev("blind", 1, 10), ev("blind", 2, 20)]
    seats = [NS(seat=0, stack=2000, bet=0, status="active", shown_cards=[]),
             NS(seat=1, stack=1990, bet=10, status="active", shown_cards=[]),
             NS(seat=2, stack=1980, bet=20, status="active", shown_cards=[])]
    st = NS(seat=0, cards=["As", "Kd"], board=[], pot=30, to_call=20, history=h0, phase="betting", seats=seats,
            button=0, blind_level=1, blinds=[10, 20], hands_until_next_level=19, hand_number=1, players_remaining=3,
            bust_order=[], config=cfg, time_bank_ms=100, events=h0,
            legal_actions=[la("fold"), la("call"), la("raise", 40, 2000)])
    a = Agent()
    _, mem = a.act(st, b"")
    h1 = h0 + [ev("raise", 0, 50), ev("fold", 1), ev("call", 2, 30), ev("board", None, None, ["Kh", "7c", "2d"]),
               ev("raise", 2, 40)]
    seats2 = [NS(seat=0, stack=1950, bet=0, status="active", shown_cards=[]),
              NS(seat=1, stack=1990, bet=0, status="folded", shown_cards=[]),
              NS(seat=2, stack=1910, bet=40, status="active", shown_cards=[])]
    st2 = NS(seat=0, cards=["As", "Kd"], board=["Kh", "7c", "2d"], pot=150, to_call=40, history=h1, phase="betting",
             seats=seats2, button=0, blind_level=1, blinds=[10, 20], hands_until_next_level=19, hand_number=1,
             players_remaining=3, bust_order=[], config=cfg, time_bank_ms=100, events=h1[3:],
             legal_actions=[la("fold"), la("call"), la("raise", 80, 1950)])
    a.act(st2, mem)


try:
    _warmup()
except Exception:
    pass
