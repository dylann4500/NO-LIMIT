"""Generate one self-contained bot file with params and a preflop table inlined. Pure stdlib, no numpy.

usage: make_bot.py <tuned_json or -> <out.py>
"""
import json, os, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import pk
from hero import DEFAULT


def pct_list():
    out = []
    for x in range(13):
        for y in range(13):
            if x == y:
                h = [4 * x, 4 * x + 1]
            elif x > y:
                h = [4 * x, 4 * y]
            else:
                h = [4 * y, 4 * x + 1]
            out.append(pk.pct(h))
    return out


TEMPLATE = r'''"""Reference poker policy: postflop equity vs. an estimated range, from a small lookup table or from
deadline-guarded rollouts with the lookup as fallback (see POSTFLOP_MC). Position-based preflop ranges,
and jam-or-fold when short. Exact ICM pricing and observed-range jam calls exist but are off.

Hard safety properties, in order of importance:
  1. Never raises an exception to the platform (a crash becomes check/fold).
  2. Every Monte Carlo loop stops at a deadline (BUDGET_S) well under the 1 ms limit.
  3. Tables are built at import, except a small rank cache whose misses cost microseconds.
"""
import gc
import random
import time
from itertools import combinations

BUDGET_S = 0.00035  # stop rollouts here; leaves margin for slower sandboxes
MAX_ROLLOUTS = 40  # tested: 40 about matches 100 on score, and costs about 60 us
PAYOUTS = __PAYOUTS__  # REPLACE with the announced points table, best place first
POSTFLOP_MC = __MC__  # True: deadline-guarded rollouts, falling back to the lookup. False: lookup only.
MIN_ROLLOUTS = 12  # with fewer finished rollouts than this, the Monte Carlo estimate is too noisy to use
USE_ICM_PRICE = False  # Tested: small gain on flat tables, large loss on top-heavy ones. Off unless the table is flat.
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

# Filled on demand: a miss costs a few microseconds, while prebuilding added about 300 ms to import.
_RC = {}

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
    r = k >> 16
    v = _RC.get(r)
    if v is None:
        v = _RC[r] = _rv(r)
    return v

def _cls(a, b):
    ra, rb = a >> 2, b >> 2
    if ra < rb:
        ra, rb = rb, ra
    if ra == rb:
        return ra * 13 + rb
    return ra * 13 + rb if (a & 3) == (b & 3) else rb * 13 + ra

_COMBOS = sorted(combinations(range(52), 2), key=lambda ab: PCT_LIST[_cls(*ab)])

def equity_vs_range(hole, board, width, max_rollouts, deadline, min_n=1):
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
    if n < min_n:
        return None
    return wins / n

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

# ---- small strength model: feature cell -> equity at each villain range width --------------------
_WIDTHS = [0.08, 0.2, 0.4, 1.0]
_RAW = __STRENGTH__
_TAB = {tuple(int(x) for x in k.split(",")): v for k, v in _RAW.items()}
_BACK = {}  # rare cells back off to the first well-sampled cell with the same hand features
for _k, _v in _TAB.items():
    if _v[-1] >= 5:
        _BACK.setdefault(_k[:5], _v)

def feature(hole, board):
    a = hole + board
    v = evaluate(a)
    cat = v >> 20
    bcat = evaluate(board) >> 20
    ranks = sorted((c >> 2 for c in board), reverse=True)
    top = ranks[0]
    hi = max(hole[0] >> 2, hole[1] >> 2)
    sub = 0
    if cat == 1:
        pr = (v - (1 << 20)) // 2197
        if bcat == 1:
            sub = 5 if hi >= 11 else 6 if hi >= 8 else 7
        elif pr > top:
            sub = 0 if pr >= 8 else 1
        elif pr == top:
            sub = 2 if hi >= 10 and hi != pr or pr >= 11 else 3
        elif len(ranks) > 1 and pr >= ranks[1]:
            sub = 4
        else:
            sub = 8
    elif cat == 0:
        sub = 0 if hi > top and hi == 12 else 1 if hi > top else 2
    else:
        sub = 1 if cat > bcat else 0
    fd = sd = 0
    if len(board) < 5:
        cnt = [0, 0, 0, 0]
        for c in a:
            cnt[c & 3] += 1
        ms, s = cnt[0], 0
        for i in range(1, 4):
            if cnt[i] > ms:
                ms, s = cnt[i], i
        if ms == 4 and ((hole[0] & 3) == s or (hole[1] & 3) == s):
            fd = 1
        m = 0
        for c in a:
            m |= 1 << (c >> 2)
        m = (m << 1) | (m >> 12 & 1)
        for i in range(10):
            b = (m >> i) & 31
            if b in (0b11110, 0b01111):
                sd = 2
                break
            if b in (0b11101, 0b11011, 0b10111):
                sd = max(sd, 1)
    c2 = [0, 0, 0, 0]
    for c in board:
        c2[c & 3] += 1
    w = max(c2)
    return (len(board), cat, sub, fd, sd, 1 if bcat >= 1 else 0, 2 if w >= 3 else 1 if w == 2 else 0)

def table_equity(hole, board, width):
    k = feature(hole, board)
    r = _TAB.get(k)
    if r is None or r[-1] < 5:
        r = _BACK.get(k[:5], r)
        if r is None:
            return 0.5
    if width <= _WIDTHS[0]:
        return r[0]
    for i in range(1, 4):
        if width <= _WIDTHS[i]:
            f = (width - _WIDTHS[i - 1]) / (_WIDTHS[i] - _WIDTHS[i - 1])
            return r[i - 1] * (1 - f) + r[i] * f
    return r[3]

# ---- policy ----------------------------------------------------------------------------------
FOLD, CALL = (0, 0), (1, 0)
JAM_CHART = [1.0, 0.69, 0.44, 0.34, 0.27, 0.22, 0.20, 0.18]

class State:
    """Normalised view of one decision; `adapt_observation` is the only place that knows the API."""
    __slots__ = ("seat", "hole", "board", "street", "pot", "to_call", "min_raise_to", "max_raise_to",
                 "can_raise", "stack", "bet", "cur", "sb", "bb", "stacks", "bets", "in_hand", "n_alive",
                 "n_live", "n_behind", "raises", "aggressor", "n_callers")

class Policy:
    def __init__(self):
        self.p = PARAMS
        self.vpip, self.hands, self.seen_vp, self.seen_h = {}, {}, set(), set()
        self.pf_raise, self.seen_pf = {}, set()

    def observe(self, seat, street, kind):
        """Call once per public action. kind: 0 fold, 1 check/call, 2 raise."""
        if street == 0:
            if seat not in self.seen_h:
                self.seen_h.add(seat)
                self.hands[seat] = self.hands.get(seat, 0) + 1
            if kind and seat not in self.seen_vp:
                self.seen_vp.add(seat)
                self.vpip[seat] = self.vpip.get(seat, 0) + 1
            if kind == 2 and seat not in self.seen_pf:
                self.seen_pf.add(seat)
                self.pf_raise[seat] = self.pf_raise.get(seat, 0) + 1

    def end_hand(self):
        self.seen_vp, self.seen_h, self.seen_pf = set(), set(), set()

    def _v(self, s):
        return (self.vpip.get(s, 0) + 3.0) / (self.hands.get(s, 0) + 10.0)

    def _foldrate(self, o):
        v = [self._v(s) for s in range(len(o.stacks)) if s != o.seat and o.in_hand[s]]
        return 1.0 - sum(v) / len(v) if v else 0.0

    def _rw(self, o):
        return 1.0 if o.aggressor < 0 else max(0.7, min(self.p["width_cap"], self._v(o.aggressor) / 0.3))

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
        if USE_ICM_PRICE and PAYOUTS and o.to_call > 0.25 * o.stack and o.to_call > 0:
            req = self._req(o)
            if req is not None:
                if o.street == 0:
                    w = max(0.03, min(0.6, 0.12 * self._rw(o) * (1.6 if o.raises <= 1 else 1.0)))
                else:
                    w = (p["range_raise"] if o.raises >= 2 else p["range_bet"]) * self._rw(o)
                eq = equity_vs_range(o.hole, o.board, w, MAX_ROLLOUTS, deadline)
                if eq is not None:
                    opp = max(1, o.n_live - 1)
                    if opp > 1:
                        eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
                    if eq < req:
                        return FOLD
                    if eq > 0.72 and o.can_raise:
                        return (2, o.max_raise_to)
                    return CALL
        return self._pre(o, deadline) if o.street == 0 else self._post(o, deadline)

    def _pre(self, o, deadline):
        p = self.p
        hp = PCT_LIST[_cls(o.hole[0], o.hole[1])]
        eff_m = self._eff(o) / float(o.sb + o.bb)
        margin = p["icm_margin"] if o.n_alive <= 4 else 0.0
        hu = o.n_alive == 2
        sh = 1.0 + p["sh_widen"] * (8 - o.n_alive) / 6.0
        if o.raises == 0:
            behind = o.n_behind
            fr = 1.0 + p["steal_fold_bonus"] * (self._foldrate(o) - 0.6)
            if eff_m < p["jam_m"]:
                w = p["jam_scale"] * JAM_CHART[min(behind, 7)] * max(0.25, 1.0 + p["jam_slope"] * (6.67 - eff_m))
                if hu:
                    w = max(w, p["hu_jam"])
                w *= fr
                if hp < w:
                    return (2, o.max_raise_to) if o.can_raise else CALL
                return CALL if o.to_call == 0 else FOLD
            w = (p["hu_open"] if hu else p["open_a"] + p["open_b"] / (behind + 0.5)) * fr
            if hp < w and o.can_raise:
                return (2, o.bb * (p["open_size"] + p["open_limp_add"] * o.n_callers))
            if o.to_call == 0:
                return CALL
            return CALL if o.to_call <= o.sb and hp < w * 1.6 else FOLD
        cost = o.to_call
        odds = cost / float(o.pot + cost)
        if p.get("hu_eqcall") and hu and o.aggressor >= 0 and (o.cur >= 0.5 * (o.stack + o.bet) or o.max_raise_to <= o.cur) and (self.pf_raise.get(o.aggressor, 0) + 1.2) / (self.hands.get(o.aggressor, 0) + 10.0) >= p["hu_gate"]:
            # Heads-up there is no ICM to protect. Against a seat raising most hands, call on price.
            v = o.aggressor
            rate = (self.pf_raise.get(v, 0) + 1.2) / (self.hands.get(v, 0) + 10.0)
            eq = equity_vs_range(o.hole, [], max(0.03, min(1.0, rate * p["hu_vwidth"])), MAX_ROLLOUTS, deadline)
            if eq is not None:
                return CALL if eq > odds + p["hu_margin"] else FOLD
        if p.get("eqcall") and o.aggressor >= 0 and (o.cur >= 0.5 * (o.stack + o.bet) or o.max_raise_to <= o.cur):
            # Equity vs. this seat's observed raising range, not a fixed tight assumption.
            v = o.aggressor
            rate = (self.pf_raise.get(v, 0) + 1.2) / (self.hands.get(v, 0) + 10.0)
            eq = equity_vs_range(o.hole, [], max(0.03, min(1.0, rate * p["vwidth_mult"])), MAX_ROLLOUTS, deadline)
            if eq is not None:
                opp = max(1, o.n_live - 1)
                if opp > 1:
                    eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
                return CALL if eq > odds + p["eqcall_margin"] + margin else FOLD
        if o.cur >= 0.5 * (o.stack + o.bet) or o.max_raise_to <= o.cur:
            w = p["call_jam"] * self._rw(o) * sh - margin * 0.5
            w += p["call_jam_short"] * max(0.0, 8.0 - eff_m) + max(0.0, odds - 0.33) * 0.5
            return CALL if hp < max(0.01, w) else FOLD
        if o.raises >= 2:
            if hp < p["fourbet"] and o.can_raise:
                return (2, o.max_raise_to)
            return CALL if hp < p["fourbet"] * 2 else FOLD
        a = self._rw(o) * sh
        if hp < p["threebet"] * a and o.can_raise:
            return (2, o.max_raise_to) if eff_m < 25 else (2, o.cur * p["threebet_mult"])
        wd = p["call_open"] * a + odds * p["call_odds"]
        if hu:
            wd = max(wd, p["hu_defend"] * (odds / 0.25) if odds >= 0.1 else 0.0)
        return CALL if hp < wd and cost < 0.2 * o.stack else FOLD

    def _post(self, o, deadline):
        p = self.p
        if o.aggressor >= 0 and o.to_call > 0:
            base = (p["range_raise"] if o.raises >= 2 else p["range_bet"]) * self._rw(o)
        else:
            base = p["range_unraised"]
        base = min(1.0, base * (1.0 + p["sh_range"] * (8 - o.n_alive) / 6.0))
        eq = None
        if POSTFLOP_MC:
            eq = equity_vs_range(o.hole, o.board, base, MAX_ROLLOUTS, deadline, MIN_ROLLOUTS)
        if eq is None:
            eq = table_equity(o.hole, o.board, base)
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


def build(params, payouts, out, mc=False):
    p = dict(DEFAULT)
    p.update(params)
    src = TEMPLATE.replace("__MC__", repr(mc)).replace("__PAYOUTS__", repr(payouts)).replace("__PARAMS__", repr({k: (round(v, 4) if isinstance(v, float) else v) for k, v in p.items()}))
    src = src.replace("__STRENGTH__", repr(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "strength_holdem.json")))))
    src = src.replace("__PCT__", repr([round(x, 4) for x in pct_list()]))
    open(out, "w").write(src)


if __name__ == "__main__":
    # usage: make_bot.py <tuned_json or -> <out.py> [lookup|mc] [points as JSON]
    params = {} if sys.argv[1] == "-" else json.load(open(sys.argv[1]))["mu"]
    mode = sys.argv[3] if len(sys.argv) > 3 else "lookup"
    pts = json.loads(sys.argv[4]) if len(sys.argv) > 4 else [100, 60, 40, 25, 15, 10, 5, 0]
    build(params, pts, sys.argv[2], mc=mode == "mc")
    print("wrote", sys.argv[2], mode)
