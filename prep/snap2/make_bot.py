"""Generate one self-contained bot file with params and a preflop table inlined. Pure stdlib, no numpy.

usage: make_bot.py <tuned_json or -> <out.py>
"""
import json, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pk import PCT_LIST
from hero import DEFAULT

TEMPLATE = r'''"""Reference poker policy: anytime Monte Carlo equity vs. an estimated range, with position-based
preflop ranges, jam-or-fold when short, and an exact ICM price on big calls.

Hard safety properties, in order of importance:
  1. Never raises an exception to the platform (a crash becomes check/fold).
  2. Every Monte Carlo loop stops at a deadline (BUDGET_S) well under the 1 ms limit.
  3. Nothing is lazily loaded on the first decision; tables are prebuilt at import.
"""
import gc
import random
import time
from itertools import combinations

BUDGET_S = 0.00035  # stop rollouts here; leaves margin for slower sandboxes
PAYOUTS = __PAYOUTS__  # REPLACE with the announced points table, best place first
PARAMS = __PARAMS__
PCT_LIST = __PCT__

_pc = time.perf_counter
_R = random.random

# ---- evaluator -------------------------------------------------------------------------------
_POW5 = [5 ** r for r in range(13)]
_KEY = [(_POW5[c >> 2] << 16) + (1 << (4 * (c & 3))) for c in range(52)]
_BIT = [1 << (c >> 2) for c in range(52)]
_STR = [0b1111100000000 >> i for i in range(9)] + [0b1000000001111]

def _sh(m):
    for i, s in enumerate(_STR):
        if m & s == s:
            return 12 - i if i < 9 else 3
    return -1

_MS = [_sh(m) for m in range(8192)]

def _top(m, n):
    o = 0
    for r in range(12, -1, -1):
        if m >> r & 1:
            o = o * 13 + r
            n -= 1
            if not n:
                break
    return o * 13 ** n

_FL = [0] * 8192
for _m in range(8192):
    if bin(_m).count("1") >= 5:
        _s = _MS[_m]
        _FL[_m] = (8 << 20) + _s if _s >= 0 else (5 << 20) + _top(_m, 5)

def _rv(key):
    cnt = [(key // _POW5[r]) % 5 for r in range(13)]
    m, q, t, p = 0, [], [], []
    for r in range(12, -1, -1):
        c = cnt[r]
        if c:
            m |= 1 << r
        if c == 4:
            q.append(r)
        elif c == 3:
            t.append(r)
        elif c == 2:
            p.append(r)
    if q:
        return (7 << 20) + q[0] * 13 + _top(m & ~(1 << q[0]), 1)
    if t and (len(t) > 1 or p):
        return (6 << 20) + t[0] * 13 + max(t[1:] + p)
    s = _MS[m]
    if s >= 0:
        return (4 << 20) + s
    if t:
        return (3 << 20) + t[0] * 169 + _top(m & ~(1 << t[0]), 2)
    if len(p) >= 2:
        return (2 << 20) + p[0] * 169 + p[1] * 13 + _top(m & ~(1 << p[0]) & ~(1 << p[1]), 1)
    if p:
        return (1 << 20) + p[0] * 2197 + _top(m & ~(1 << p[0]), 3)
    return _top(m, 5)

# Prebuild the rank cache at import so a first decision never pays for it.
_RC = {}
def _fill(depth, start, key):
    if depth == 0:
        _RC[key] = _rv(key)
        return
    for r in range(start, 13):
        _fill(depth - 1, r, key + _POW5[r])
for _n in (5, 6, 7):
    _fill(_n, 0, 0)
_RC = {k: v for k, v in _RC.items() if all((k // _POW5[r]) % 5 <= 4 for r in range(13))}

def evaluate(cards):
    k = 0
    for c in cards:
        k += _KEY[c]
    if (k + 0x3333) & 0x8888:
        low = k & 0xFFFF
        for s in range(4):
            if (low >> (4 * s)) & 15 >= 5:
                m = 0
                for c in cards:
                    if c & 3 == s:
                        m |= _BIT[c]
                return _FL[m]
    return _RC[k >> 16]

def _cls(a, b):
    ra, rb = a >> 2, b >> 2
    if ra < rb:
        ra, rb = rb, ra
    if ra == rb:
        return ra * 13 + rb
    return ra * 13 + rb if (a & 3) == (b & 3) else rb * 13 + ra

_COMBOS = sorted(combinations(range(52), 2), key=lambda ab: PCT_LIST[_cls(*ab)])

def equity_vs_range(hole, board, width, max_rollouts, deadline):
    lim = max(8, int(width * 1326))
    known = set(hole)
    known.update(board)
    nb = 5 - len(board)
    wins, n, bl, combos = 0.0, 0, list(board), _COMBOS
    for i in range(max_rollouts):
        if not i & 7 and _pc() > deadline:
            break
        a, b = combos[int(_R() * lim)]
        if a in known or b in known:
            continue
        run = bl
        if nb:
            run = bl[:]
            while len(run) < 5:
                c = int(_R() * 52)
                if c not in known and c != a and c != b and c not in run:
                    run.append(c)
        n += 1
        v1, v2 = evaluate(hole + run), evaluate([a, b] + run)
        if v1 > v2:
            wins += 1
        elif v1 == v2:
            wins += 0.5
    return wins / n if n else None

def icm_me(stacks, me, pay):
    n, total, memo = len(stacks), float(sum(stacks)), {}
    def rec(mask, place, remain):
        if not mask >> me & 1:
            return 0.0
        if mask in memo:
            return memo[mask]
        if remain <= 0:
            return 0.0
        res, pp = 0.0, pay[place] if place < len(pay) else 0.0
        for i in range(n):
            if mask >> i & 1 and stacks[i] > 0:
                p = stacks[i] / remain
                res += p * pp if i == me else p * rec(mask & ~(1 << i), place + 1, remain - stacks[i])
        memo[mask] = res
        return res
    return rec((1 << n) - 1, 0, total)

# ---- policy ----------------------------------------------------------------------------------
FOLD, CALL = (0, 0), (1, 0)

class State:
    """Normalised view of one decision; `adapt_observation` is the only place that knows the API."""
    __slots__ = ("seat", "hole", "board", "street", "pot", "to_call", "min_raise_to", "max_raise_to",
                 "can_raise", "stack", "bet", "cur", "sb", "bb", "stacks", "bets", "in_hand", "n_alive",
                 "n_live", "n_behind", "raises", "aggressor", "n_callers")

class Policy:
    def __init__(self):
        self.p = PARAMS
        self.vpip, self.hands, self.seen_vp, self.seen_h = {}, {}, set(), set()

    def observe(self, seat, street, kind):
        """Call once per public action. kind: 0 fold, 1 check/call, 2 raise."""
        if street == 0:
            if seat not in self.seen_h:
                self.seen_h.add(seat)
                self.hands[seat] = self.hands.get(seat, 0) + 1
            if kind and seat not in self.seen_vp:
                self.seen_vp.add(seat)
                self.vpip[seat] = self.vpip.get(seat, 0) + 1

    def end_hand(self):
        self.seen_vp, self.seen_h = set(), set()

    def _v(self, s):
        return (self.vpip.get(s, 0) + 3.0) / (self.hands.get(s, 0) + 10.0)

    def _foldrate(self, o):
        v = [self._v(s) for s in range(len(o.stacks)) if s != o.seat and o.in_hand[s]]
        return 1.0 - sum(v) / len(v) if v else 0.0

    def _rw(self, o):
        return 1.0 if o.aggressor < 0 else max(0.7, min(2.2, self._v(o.aggressor) / 0.3))

    def _eff(self, o):
        b = 0
        for s in range(len(o.stacks)):
            if s != o.seat and o.in_hand[s]:
                v = o.stacks[s] + o.bets[s]
                if v > b:
                    b = v
        return min(b, o.stack + o.bet)

    def _req(self, o):
        v = o.aggressor
        if v < 0 or not PAYOUTS:
            return None
        seats = [s for s in range(len(o.stacks)) if s == o.seat or o.stacks[s] + o.bets[s] > 0]
        if len(seats) > 6 or v not in seats:
            return None
        pay, me, vi = PAYOUTS[:len(seats)], seats.index(o.seat), seats.index(v)
        base = [o.stacks[s] for s in seats]
        pot = o.pot
        f = base[:]
        f[vi] += pot
        m = min(base[vi], max(0, base[me] - o.to_call))
        w = base[:]
        w[me] = base[me] + pot + m
        w[vi] = base[vi] - m
        l = base[:]
        l[me] = base[me] - o.to_call - m
        l[vi] = base[vi] + pot + o.to_call + m
        F, W = icm_me(f, me, pay), icm_me(w, me, pay)
        L = icm_me(l, me, pay) if l[me] > 0 else (pay[len(seats) - 1] if len(seats) - 1 < len(pay) else 0.0)
        return None if W - L <= 1e-9 else (F - L) / (W - L)

    def decide(self, o, deadline):
        p = self.p
        if PAYOUTS and o.to_call > 0.25 * o.stack and o.to_call > 0:
            req = self._req(o)
            if req is not None:
                if o.street == 0:
                    w = max(0.03, min(0.6, 0.12 * self._rw(o) * (1.6 if o.raises <= 1 else 1.0)))
                else:
                    w = (p["range_raise"] if o.raises >= 2 else p["range_bet"]) * self._rw(o)
                eq = equity_vs_range(o.hole, o.board, w, 100, deadline)
                if eq is not None:
                    opp = max(1, o.n_live - 1)
                    if opp > 1:
                        eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
                    if eq < req:
                        return FOLD
                    if eq > 0.72 and o.can_raise:
                        return (2, o.max_raise_to)
                    return CALL
        return self._pre(o) if o.street == 0 else self._post(o, deadline)

    def _pre(self, o):
        p = self.p
        hp = PCT_LIST[_cls(o.hole[0], o.hole[1])]
        eff_m = self._eff(o) / float(o.sb + o.bb)
        margin = p["icm_margin"] if o.n_alive <= 4 else 0.0
        if o.raises == 0:
            behind = o.n_behind
            if eff_m < p["jam_m"]:
                w = p["jam_base"] + p["jam_slope"] * (p["jam_m"] - eff_m)
                w *= 1.0 + 0.45 * (o.n_alive - behind - 1) / max(1, o.n_alive - 1)
                w *= 1.0 + p["steal_fold_bonus"] * self._foldrate(o)
                if hp < w:
                    return (2, o.max_raise_to) if o.can_raise else CALL
                return CALL if o.to_call == 0 else FOLD
            late = 1.0 - behind / max(1.0, o.n_alive - 1.0)
            w = p["open_early"] + (p["open_late"] - p["open_early"]) * late
            if behind <= 2 and o.n_alive > 3:
                w += p["open_btn_bonus"]
            w *= 1.0 + p["steal_fold_bonus"] * (self._foldrate(o) - 0.6)
            if hp < w and o.can_raise:
                return (2, o.bb * (p["open_size"] + p["open_limp_add"] * o.n_callers))
            if o.to_call == 0:
                return CALL
            return CALL if o.to_call <= o.sb and hp < w * 1.6 else FOLD
        cost = o.to_call
        odds = cost / float(o.pot + cost)
        if o.cur >= 0.5 * (o.stack + o.bet) or o.max_raise_to <= o.cur:
            w = p["call_jam"] * self._rw(o) - margin * 0.5
            w += p["call_jam_short"] * max(0.0, 8.0 - eff_m) + max(0.0, odds - 0.33) * 0.5
            return CALL if hp < max(0.01, w) else FOLD
        if o.raises >= 2:
            if hp < p["fourbet"] and o.can_raise:
                return (2, o.max_raise_to)
            return CALL if hp < p["fourbet"] * 2 else FOLD
        a = self._rw(o)
        if hp < p["threebet"] * a and o.can_raise:
            return (2, o.max_raise_to) if eff_m < 25 else (2, o.cur * p["threebet_mult"])
        return CALL if hp < p["call_open"] * a + odds * 0.1 and cost < 0.2 * o.stack else FOLD

    def _post(self, o, deadline):
        p = self.p
        if o.aggressor >= 0 and o.to_call > 0:
            base = (p["range_raise"] if o.raises >= 2 else p["range_bet"]) * self._rw(o)
        else:
            base = p["range_unraised"]
        eq = equity_vs_range(o.hole, o.board, base, 100, deadline)
        if eq is None:
            return CALL if o.to_call == 0 else FOLD
        opp = max(1, o.n_live - 1)
        if opp > 1:
            eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
        spr = o.stack / float(max(1, o.pot))
        margin = p["call_margin"] + (p["icm_margin"] if o.n_alive <= 4 else 0.0)
        if o.to_call == 0:
            if not o.can_raise:
                return CALL
            if eq > p["value_eq"]:
                return (2, o.max_raise_to) if spr < p["commit_spr"] else (2, o.pot * p["bet_frac"])
            if o.n_live == 2 and _R() < p["bluff_freq"]:
                return (2, o.pot * 0.5)
            return CALL
        odds = o.to_call / float(o.pot + o.to_call)
        if eq > p["raise_eq"] and o.can_raise:
            return (2, o.max_raise_to) if spr < 2.0 else (2, o.cur + o.pot * 0.8)
        return CALL if eq > odds + margin else FOLD

    def safe_decide(self, o):
        """Never raises; always returns a legal (kind, amount)."""
        t0 = _pc()
        try:
            kind, amt = self.decide(o, t0 + BUDGET_S)
            if kind == 2:
                if not o.can_raise:
                    return CALL
                return (2, int(min(o.max_raise_to, max(o.min_raise_to, amt))))
            if kind == 0 and o.to_call == 0:
                return CALL
            return (kind, 0)
        except Exception:
            return CALL if getattr(o, "to_call", 1) == 0 else FOLD

# ---- platform adapter: rewrite these for the real Agent interface at kickoff ------------------
# The real API is unknown until the starter kit ships. Map its fields to State here and nowhere else.
def adapt_observation(obs):
    raise NotImplementedError("Map starter-kit fields to State, card ints: rank*4+suit, 2=0 .. A=12")

def to_platform_action(kind, amount, obs):
    raise NotImplementedError("Map (0,0) fold, (1,0) check/call, (2,to) raise-to onto the kit's action format")

gc.collect()
gc.freeze()
gc.disable()  # Cycle collection caused the one observed 1 ms breach. The policy creates no cycles.
'''


def build(params, payouts, out):
    p = dict(DEFAULT)
    p.update(params)
    src = TEMPLATE.replace("__PAYOUTS__", repr(payouts)).replace("__PARAMS__", repr({k: (round(v, 4) if isinstance(v, float) else v) for k, v in p.items()}))
    src = src.replace("__PCT__", repr([round(x, 4) for x in PCT_LIST]))
    open(out, "w").write(src)


if __name__ == "__main__":
    params = {} if sys.argv[1] == "-" else json.load(open(sys.argv[1]))["mu"]
    build(params, [50, 30, 20, 0, 0, 0, 0, 0], sys.argv[2])
    print("wrote", sys.argv[2])
