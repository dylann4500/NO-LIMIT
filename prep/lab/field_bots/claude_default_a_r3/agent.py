"""claude_default_a: tight-aggressive, ICM-aware NLHE sit-and-go bot.

Design (see NOTES.md):
  * Preflop: precomputed 169-class ranking + equity-vs-top-X% tables (tables.json).
    Position-based opens, equity-vs-estimated-range calls / 3-bets, and an ICM
    expected-value model for every all-in decision (shove, re-shove, call-off).
  * Postflop: eval7 equity against the opponent's range, estimated from preflop
    action, table-level stats (kept in `memory`) and postflop aggression.
  * Opponent model: per-seat VPIP / PFR / fold-to-raise / aggression / fold-to-bet
    counted from public events, carried in `memory` as compact JSON.
Everything is wrapped so a failure falls back to check/fold, and the work per
decision is bounded (one small Monte Carlo call at most).
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

ORDER = _T["order"]
PCT = _T["pct"]                 # class -> cumulative combo fraction (strength percentile, 0 = best)
BUCKETS = _T["buckets"]
EQTOP = _T["eqtop"]             # class -> equity vs top-b range for each bucket
EQR = _T["eqr"]                 # class -> equity vs [1, 2, 3, 5, 7] random hands
NB = len(BUCKETS)
RANKS = "23456789TJQKA"
RV = {r: i for i, r in enumerate(RANKS)}
CARD = {r + s: eval7.Card(r + s) for r in RANKS for s in "shdc"}


def _nc(c):
    return 6 if len(c) == 2 else (4 if c[2] == "s" else 12)


def _range_classes(b):
    out, cum = [], 0
    for c in ORDER:
        if cum >= b * 1326 - 1e-9:
            break
        out.append(c)
        cum += _nc(c)
    return out


# For "what fraction of hands calls a shove needing equity x vs range bucket b".
_CALLCURVE = []
for _bi in range(NB):
    _l = sorted(((EQTOP[c][_bi], _nc(c)) for c in ORDER), reverse=True)
    _cum, _pts = 0, []
    for _e, _n in _l:
        _cum += _n
        _pts.append((_e, _cum / 1326.0))
    _CALLCURVE.append(_pts)


def call_frac(need, bi):
    """Fraction of all hands with equity >= need against bucket bi."""
    pts = _CALLCURVE[bi]
    lo = 0.0
    for e, f in pts:
        if e < need:
            return lo
        lo = f
    return lo


def bucket_idx(p):
    for i, b in enumerate(BUCKETS):
        if p <= b + 1e-9:
            return i
    return NB - 1


def pre_eq(cls, p):
    """Preflop equity of class vs top-p range (linear interpolation)."""
    row = EQTOP[cls]
    if p <= BUCKETS[0]:
        return row[0]
    for i in range(1, NB):
        if p <= BUCKETS[i]:
            b0, b1 = BUCKETS[i - 1], BUCKETS[i]
            w = (p - b0) / (b1 - b0)
            return row[i - 1] * (1 - w) + row[i] * w
    return row[-1]


def hand_class(c1, c2):
    r1, r2 = c1[0], c2[0]
    if RV[r1] < RV[r2]:
        r1, r2 = r2, r1
    if r1 == r2:
        return r1 + r2
    return r1 + r2 + ("s" if c1[1] == c2[1] else "o")


def _ckey(c1, c2):
    a, b = str(c1), str(c2)
    return hand_class(a, b)


def _sub_range(hr, maxn=360):
    """Stratified, re-weighted subsample of a wide range: same class mix, ~3x faster equity calls."""
    hs = list(hr.hands)
    if len(hs) <= maxn:
        return hr
    groups = {}
    for h, w in hs:
        groups.setdefault(_ckey(h[0], h[1]), []).append((h, w))
    frac = maxn / float(len(hs))
    rnd = random.Random(12345)
    out = []
    for kk in sorted(groups):
        lst = groups[kk]
        rnd.shuffle(lst)
        k = max(1, int(round(len(lst) * frac)))
        out += [(h, w * len(lst) / float(k)) for h, w in lst[:k]]
    try:
        n = eval7.HandRange("AA")
        n.hands = out
        return n
    except Exception:
        return hr


HR = [_sub_range(eval7.HandRange(",".join(_range_classes(b)))) for b in BUCKETS]


def icm_me(st, i, pay):
    """ICM equity of player i (exact for up to 3 paid places)."""
    n = len(st)
    T = float(sum(st))
    s = st[i]
    if s <= 0 or T <= 0:
        return 0.0
    ev = pay[0] * s / T if pay else 0.0
    if n > 1 and len(pay) > 1 and pay[1]:
        e2 = 0.0
        for j in range(n):
            sj = st[j]
            if j != i and sj > 0:
                e2 += sj / (T - sj)
        ev += pay[1] * e2 * s / T
    if n > 2 and len(pay) > 2 and pay[2]:
        e3 = 0.0
        for j in range(n):
            sj = st[j]
            if j == i or sj <= 0:
                continue
            Tj = T - sj
            a = sj / Tj
            for k in range(n):
                sk = st[k]
                if k == i or k == j or sk <= 0:
                    continue
                e3 += a * sk / (Tj - sk)
        ev += pay[2] * e3 * s / T
    if n > 3 and len(pay) > 3:
        rest = sum(pay[3:n])
        if rest:
            ev += rest * s / T  # rough beyond 3 places
    return ev


def kname(k):
    v = getattr(k, "value", None)
    if isinstance(v, str):
        return v.lower()
    n = getattr(k, "name", None)
    if isinstance(n, str):
        return n.lower()
    return str(k).lower().split(".")[-1]


# ---------------------------------------------------------------- opponent model
# per seat: [hands, vpip, pfr, fr_opp, fr_fold, agg, pas, fb_opp, fb_fold]
def _new_ctx():
    return {"st": 0, "nr": 0, "bet": 0, "lc": 0, "sp": 0, "ac": [], "vp": [], "pr": [], "fr": []}


NROW = 13


def update_stats(mem, events):
    S = mem["S"]
    c = mem["c"]
    for e in events:
        k = kname(e.kind)
        if k == "hand":
            if c.get("sp", 0) > 1:
                mem["np"] = c["sp"]
            c = _new_ctx()
            continue
        if k == "stack":
            if (e.amount or 0) > 0:
                c["sp"] = c.get("sp", 0) + 1
            continue
        if k == "board":
            c["st"] += 1
            c["bet"] = 0
            continue
        if k not in ("fold", "check", "call", "raise"):
            continue
        s = e.seat
        if s is None:
            continue
        key = str(s)
        row = S.get(key)
        if row is None:
            row = S[key] = [0] * NROW
        elif len(row) < NROW:
            row.extend([0] * (NROW - len(row)))
        if c["st"] == 0:
            if s not in c["ac"]:
                if c["nr"] == 0 and c.get("lc", 0) == 0:
                    # first-in opportunity: split by how many players are left to act behind
                    pb = mem.get("np", 8) - 1 - len(c["ac"])
                    if pb >= 1:
                        late = 1 if pb <= 3 else 0
                        row[11 if late else 9] += 1
                        if k == "raise":
                            row[12 if late else 10] += 1
                c["ac"].append(s)
                row[0] += 1
            if k == "call" and c["nr"] == 0:
                c["lc"] = c.get("lc", 0) + 1
            if c["nr"] > 0 and s not in c["fr"]:
                c["fr"].append(s)
                row[3] += 1
                if k == "fold":
                    row[4] += 1
            if k in ("call", "raise") and s not in c["vp"]:
                c["vp"].append(s)
                row[1] += 1
            if k == "raise":
                if s not in c["pr"]:
                    c["pr"].append(s)
                    row[2] += 1
                c["nr"] += 1
        else:
            if k == "raise":
                row[5] += 1
            elif k in ("call", "check"):
                row[6] += 1
            if c["bet"]:
                row[7] += 1
                if k == "fold":
                    row[8] += 1
            if k == "raise":
                c["bet"] = 1
    mem["c"] = c


class Opp:
    __slots__ = ("vpip", "pfr", "f2r", "af", "ftb", "n", "open_e", "open_l")

    def __init__(self, row):
        if row is None:
            row = [0] * NROW
        if len(row) < NROW:
            row = list(row) + [0] * (NROW - len(row))
        h = row[0]
        # first-in open-raise frequency, early (4+ behind) and late (1-3 behind)
        self.open_e = (row[10] + 0.17 * 4) / (row[9] + 4)
        self.open_l = (row[12] + 0.40 * 4) / (row[11] + 4)
        self.n = h
        self.vpip = (row[1] + 0.28 * 8) / (h + 8)
        self.pfr = (row[2] + 0.17 * 8) / (h + 8)
        self.f2r = (row[4] + 0.70 * 5) / (row[3] + 5)
        self.af = (row[5] + 0.35 * 8) / (row[5] + row[6] + 8)
        self.ftb = (row[8] + 0.45 * 6) / (row[7] + 6)


# ---------------------------------------------------------------- action helpers
class Ctx:
    pass


def legal_map(state):
    m = {}
    for la in state.legal_actions:
        k = kname(la.kind)
        if k == "bet":
            k = "raise"
        m[k] = la
    return m


def safe_fallback(state):
    try:
        m = legal_map(state)
        if "check" in m:
            return Action.check()
        return Action.fold()
    except Exception:
        return Action.fold()


def mk_raise(m, total):
    la = m.get("raise")
    if la is None:
        if "call" in m:
            return Action.call()
        return Action.check()
    lo, hi = int(la.min_amount), int(la.max_amount)
    t = int(total)
    if t < lo:
        t = lo
    if t > hi:
        t = hi
    if hi < lo:
        t = hi
    return Action.raise_to(t)


def mk_call(m):
    if "call" in m:
        return Action.call()
    if "check" in m:
        return Action.check()
    return Action.fold()


def mk_fold(m):
    if "check" in m:
        return Action.check()
    return Action.fold()


# ---------------------------------------------------------------- the agent
class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        t0 = time.perf_counter()
        try:
            mem = None
            if memory:
                try:
                    mem = json.loads(memory)
                except Exception:
                    mem = None
            if not isinstance(mem, dict) or not isinstance(mem.get("S"), dict) or not isinstance(mem.get("c"), dict):
                mem = {"S": {}, "c": _new_ctx(), "np": len(state.seats or []) or 8}
            try:
                update_stats(mem, state.events or [])
            except Exception:
                pass
            out = json.dumps(mem, separators=(",", ":")).encode()
            if len(out) > 15000:
                mem = {"S": mem["S"], "c": _new_ctx(), "np": mem.get("np", 8)}
                out = json.dumps(mem, separators=(",", ":")).encode()
        except Exception:
            mem = {"S": {}, "c": _new_ctx(), "np": 8}
            out = memory if isinstance(memory, (bytes, bytearray)) else b""
        try:
            a = decide(state, mem, t0)
            if a is None:
                a = safe_fallback(state)
        except Exception:
            a = safe_fallback(state)
        return a, out


def decide(state, mem, t0=0.0):
    m = legal_map(state)
    if len(m) == 1:
        k = next(iter(m))
        if k == "check":
            return Action.check()
        if k == "fold":
            return Action.fold()
        if k == "call":
            return Action.call()
    x = Ctx()
    x.t0 = t0 or time.perf_counter()
    x.m = m
    x.me = state.seat
    x.cards = list(state.cards)
    x.board = list(state.board or [])
    x.pot = int(state.pot)
    x.to_call = int(state.to_call or 0)
    bl = state.blinds or [10, 20]
    x.bb = max(1, int(bl[1]))
    seats = {}
    for s in state.seats:
        seats[s.seat] = s
    x.seats = seats
    mys = seats[x.me]
    x.my_stack = int(mys.stack)
    x.my_bet = int(mys.bet)
    x.my_total = x.my_stack + x.my_bet
    x.cfg = state.config
    pay = list(getattr(x.cfg, "payouts", None) or [50, 30, 20])
    x.alive = [s for s in seats.values() if kname(s.status) != "busted"]
    x.n_alive = len(x.alive)
    x.pay_all = [float(v) for v in pay]
    x.cfg_button = state.button
    x.opps = [s for s in seats.values() if s.seat != x.me and kname(s.status) in ("active", "all_in")]
    S = mem["S"]
    x.model = {s.seat: Opp(S.get(str(s.seat))) for s in seats.values() if s.seat != x.me}
    parse_history(x, state.history or [])
    x.order_pre = preflop_order(x)
    max_opp = max([s.stack + s.bet for s in x.opps] or [x.my_total])
    x.cap = min(x.my_total, max_opp)
    tb = getattr(state, "time_bank_ms", None)
    x.fast = tb is not None and tb < 30
    x.cls = hand_class(x.cards[0], x.cards[1])
    if not x.board:
        return preflop(x)
    return postflop(x)


def parse_history(x, hist):
    st = 0
    x.blind_seats = []
    x.pre_raises = []          # (seat, total)
    x.pre_calls = []           # (seat, after_n_raises)
    x.post_agg = {}            # seat -> list of ('b'|'r', street)
    x.post_calls = {}
    x.street_raises = 0
    x.street_bet_open = False
    x.my_post_agg = 0
    for e in hist:
        k = kname(e.kind)
        if k == "board":
            st += 1
            x.street_raises = 0
            continue
        if k == "blind":
            x.blind_seats.append((e.seat, e.amount))
            continue
        s = e.seat
        if st == 0:
            if k == "raise":
                x.pre_raises.append((s, e.amount))
            elif k == "call":
                x.pre_calls.append((s, len(x.pre_raises)))
        else:
            if k == "raise":
                typ = "r" if x.street_raises > 0 else "b"
                x.street_raises += 1
                x.post_agg.setdefault(s, []).append((typ, st))
            elif k == "call":
                x.post_calls[s] = x.post_calls.get(s, 0) + 1
    x.street = st
    x.bb_seat = None
    if x.blind_seats:
        x.bb_seat = x.blind_seats[-1][0]
    x.last_raiser = x.pre_raises[-1][0] if x.pre_raises else None




# ---------------------------------------------------------------- ICM helpers
def _st_now(s):
    v = s.stack
    if v <= 0 and kname(s.status) == "all_in":
        v = 1  # all-in from an earlier street: still alive, chips are in the pot
    return v


def icm_val(x, ov):
    """My ICM equity when stacks are as now (chips behind) except the overrides {seat: final stack}."""
    st, i = [], -1
    for s in x.alive:
        v = ov[s.seat] if s.seat in ov else _st_now(s)
        if s.seat == x.me:
            if v <= 0:
                n = len(x.alive)
                return x.pay_all[n - 1] if n - 1 < len(x.pay_all) else 0.0
            i = len(st)
        if v > 0:
            st.append(v)
    if i < 0:
        return 0.0
    return icm_me(st, i, x.pay_all[:len(st)])


def hu_outcomes(x, o):
    """(fold, win, lose) override dicts for an all-in confrontation between me and seat o."""
    os_ = x.seats[o]
    me_tot = x.my_stack + x.my_bet
    o_tot = os_.stack + os_.bet
    matched = min(me_tot, o_tot)
    prev = x.pot - x.my_bet - os_.bet
    pot_final = prev + 2 * matched
    f = {x.me: x.my_stack, o: os_.stack + x.pot}
    w = {x.me: me_tot - matched + pot_final, o: o_tot - matched}
    l = {x.me: me_tot - matched, o: o_tot - matched + pot_final}
    return f, w, l


def call_allin_ev(x, o, eq):
    """(EV_call, EV_fold) in ICM points, heads-up against seat o."""
    f, w, l = hu_outcomes(x, o)
    uf = icm_val(x, f)
    return eq * icm_val(x, w) + (1 - eq) * icm_val(x, l), uf


def perceived_bucket(x):
    """How wide opponents probably think our shove is (bucket index)."""
    eff = x.eff_bb
    if eff <= 6:
        p = 0.5
    elif eff <= 10:
        p = 0.35
    elif eff <= 16:
        p = 0.24
    else:
        p = 0.15
    return bucket_idx(p)


def shove_ev(x, responders, fold_winner):
    """EV (ICM) of shoving all-in now vs folding.

    responders: list of (seat, p_call_cap) for players who must respond, in order.
    p_call_cap: for a player who already raised, the fraction of their range they continue with
    is call_frac / their range pct (capped at 1).
    """
    cls = x.cls
    pb = perceived_bucket(x)
    me_tot = x.my_total
    p_none = 1.0
    ev_called = 0.0
    for seat, rng_pct in responders:
        s = x.seats[seat]
        o_tot = s.stack + s.bet
        risk = min(me_tot, o_tot) - s.bet           # chips they must add to call
        if risk <= 0:
            continue
        pot_after = x.pot + (min(me_tot, o_tot) - x.my_bet)
        need = risk / float(pot_after + risk)
        cf = call_frac(need, pb)
        o = x.model.get(seat)
        if o is not None:
            # looser players (VPIP) and players who rarely fold to raises call shoves more often
            cf *= ((o.vpip / 0.28) ** P["sh_vpip"]) * (((1.0 - o.f2r) / 0.3) ** P["sh_f2r"])
        cf = max(0.02, min(0.95, cf))
        if rng_pct < 1.0:
            pc = min(1.0, cf / max(rng_pct, 0.02))
            cp = min(cf, rng_pct)
        else:
            pc = cf
            cp = cf
        pj = p_none * pc
        if pj > 0:
            eq = pre_eq(cls, cp)
            f, w, l = hu_outcomes(x, seat)
            ev_called += pj * (eq * icm_val(x, w) + (1 - eq) * icm_val(x, l))
        p_none *= (1 - pc)
    # everyone folds: I win the pot
    ev_nc = icm_val(x, {x.me: x.my_stack + x.pot})
    ev_shove = p_none * ev_nc + ev_called
    fo = {x.me: x.my_stack}
    if fold_winner is not None and fold_winner in x.seats:
        fo[fold_winner] = x.seats[fold_winner].stack + x.pot
    ev_fold = icm_val(x, fo)
    return ev_shove, ev_fold


# ---------------------------------------------------------------- position helpers
def preflop_order(x):
    seats = sorted(s.seat for s in x.alive)
    if not seats:
        return []
    bb = x.bb_seat if x.bb_seat in seats else seats[0]
    i = seats.index(bb)
    return seats[i + 1:] + seats[:i + 1]


def postflop_order(x, button):
    seats = sorted(s.seat for s in x.alive)
    after = [s for s in seats if s > button] + [s for s in seats if s <= button]
    return after


def can_act(s):
    return kname(s.status) == "active"


# ---------------------------------------------------------------- preflop
OPEN = {1: 0.58, 2: 0.42, 3: 0.29, 4: 0.22, 5: 0.18, 6: 0.15, 7: 0.13}
# tunable strategy parameters
P = {
    "open_mult": 1.0, "steal_k": 1.2, "push_bb": 13, "v3": 0.585, "v4": 0.56,
    "R_ip": 0.9, "R_oop": 0.72, "R_bb": 0.78, "impl_pair": 0.06, "impl_suit": 0.03,
    "nb_b": 0.15, "nb_r": 0.12, "nb_r_af": 0.7, "mw_exp": 0.75,
    "vb_hi": 0.70, "vb_lo": 0.60, "vb_riv": 0.64, "vb_frac": 0.75, "vb_lo_frac": 0.55,
    "cbet_base": 0.65, "cbet_frac": 0.45, "raise_thr": 0.80, "raise_thr_riv": 0.86,
    "m_ip": 0.09, "m_oop": 0.13, "m_riv": 0.03, "semi": 0.3, "rbluff": 0.4, "steal_ftb": 0.45,
    "sh_vpip": 0.5, "sh_f2r": 0.3, "pos_k": 0.7, "R_mult": 0.5, "ss_R": 0.6,
    # round-2 additions (field defends/3-bets/steals far more than the local proxies)
    "R_bb_mult": 0.85, "R_sb_mult": 0.5, "R_3b": 0.65, "k3": 0.7, "reshove3_bb": 40,
    "l3_p": 0.55, "riv_passive": 0.04, "l3_lo": 0.04, "l3_hi": 0.45, "l3_rpct": 0.2,
}


def raiser_range(x, seat, k, total):
    o = x.model.get(seat)
    pfr = o.pfr if o else 0.17
    if k <= 1:
        # opening ranges widen with fewer players left to act behind the raiser
        order = getattr(x, "order_pre", None) or []
        if seat in order and o is not None and P["pos_k"] > 0:
            pb_r = len(order) - 1 - order.index(seat)
            if pb_r <= 3:
                base = o.open_l * (OPEN.get(pb_r, 0.29) / 0.43) ** 0.5
            else:
                base = o.open_e * (OPEN.get(pb_r, 0.13) / 0.17) ** 0.5
            pct = base * 1.05
        else:
            pct = pfr * 1.05
    elif k == 2:
        pct = pfr * P["k3"]
    else:
        pct = pfr * 0.2
    s = x.seats.get(seat)
    if s is not None and s.stack == 0:
        rb = (s.bet) / float(x.bb)
        if pfr > 0.5:
            pct = max(pct, pfr)
        elif rb <= 8:
            pct = max(pct, 0.35)
        elif rb <= 15:
            pct = max(pct, 0.2)
        elif rb <= 25:
            pct = max(pct * 0.8, 0.1)
        else:
            pct = pct * 0.6
    return max(0.02, min(1.0, pct))


def preflop(x):
    m = x.m
    bb = x.bb
    cls = x.cls
    p = PCT[cls]
    order = preflop_order(x)
    me = x.me
    myi = order.index(me) if me in order else 0
    after = order[myi + 1:]
    active_after = [s for s in after if can_act(x.seats[s])]
    opp_tot = [s.stack + s.bet for s in x.opps]
    x.eff = min(x.my_total, max(opp_tot) if opp_tot else x.my_total)
    x.eff_bb = x.eff / float(bb)
    nr = len(x.pre_raises)
    rnd = random.random()

    if nr == 0:
        limpers = [s for s, n in x.pre_calls if n == 0 and s != me]
        if x.to_call == 0:
            # big blind option (limped pot)
            iso = 0.10 if len(limpers) <= 1 else 0.07
            if p <= iso:
                if x.eff_bb <= 15:
                    return mk_raise(m, x.cap)
                return mk_raise(m, (4 + len(limpers)) * bb)
            return Action.check() if "check" in m else mk_fold(m)
        # push / fold zone
        if x.eff_bb <= P["push_bb"] or (limpers and x.eff_bb <= P["push_bb"] + 3):
            resp = [(s, 1.0) for s in order if s != me and can_act(x.seats[s]) and (s in after or s in limpers)]
            evs, evf = shove_ev(x, resp, x.bb_seat)
            if evs > evf:
                return mk_raise(m, x.cap)
            return mk_fold(m)
        pb = max(1, len(active_after))
        op = OPEN.get(pb, 0.13) * P["open_mult"]
        if active_after:
            f2r = sum(x.model[s].f2r for s in active_after if s in x.model) / len(active_after)
            mult = 1.0 + P["steal_k"] * (f2r - 0.7)
            op *= max(0.65, min(1.45, mult))
        if limpers:
            loose = sum(x.model[s].vpip for s in limpers if s in x.model) / len(limpers)
            op = min(op, 0.06 + 0.25 * loose) * (0.85 if len(limpers) > 1 else 1.0)
        if p <= op:
            if x.eff_bb >= 40:
                size = 2.5
            elif x.eff_bb >= 20:
                size = 2.25
            else:
                size = 2.0
            if pb == 1 and not limpers:
                size = 3.0 if x.eff_bb > 20 else 2.5
            size += len(limpers) * 1.0
            tot = int(size * bb)
            if tot >= 0.4 * x.cap:
                tot = x.cap
            return mk_raise(m, tot)
        return mk_fold(m)

    # ---- facing a raise
    rseat, ramt = x.pre_raises[-1]
    rs = x.seats.get(rseat)
    r_pct = raiser_range(x, rseat, nr, ramt)
    callers_after = sum(1 for s, n in x.pre_calls if n == nr and s != me)
    eq = pre_eq(cls, r_pct)
    eqm = eq ** (1 + 0.65 * callers_after) if callers_after else eq
    need = x.to_call / float(x.pot + x.to_call)
    r_allin = rs is not None and rs.stack == 0
    commit = x.to_call >= 0.4 * x.my_total

    # all-in decision: raiser is all-in or calling commits us
    if r_allin or commit:
        # option 1: call (ICM, heads-up vs raiser; extra callers reduce equity)
        ev_c, ev_f = call_allin_ev(x, rseat, eqm)
        best, act = ev_f, "fold"
        if ev_c > best:
            best, act = ev_c, "call"
        if not r_allin and "raise" in m and x.my_total > x.my_bet + x.to_call:
            resp = [(rseat, r_pct)] + [(s, 1.0) for s in order if s != me and s != rseat and can_act(x.seats[s])]
            evs, _ = shove_ev(x, resp, rseat)
            if evs > best:
                best, act = evs, "shove"
        if act == "call":
            return mk_call(m)
        if act == "shove":
            return mk_raise(m, x.cap)
        return mk_fold(m)

    # short-stack re-shove zone
    if ((x.eff_bb <= 25 and nr <= 2) or (nr == 2 and x.eff_bb <= P["reshove3_bb"])) and "raise" in m:
        resp = [(rseat, r_pct)] + [(s, 1.0) for s in order if s != me and s != rseat and can_act(x.seats[s])]
        evs, evf = shove_ev(x, resp, rseat)
        # a flat call is only considered for strong-but-not-shove hands when deep enough
        if evs > evf and (eq >= 0.5 or evs - evf > 0.15):
            return mk_raise(m, x.cap)
        if eqm * P["ss_R"] >= need + 0.03 and x.to_call <= 0.15 * x.my_total:
            return mk_call(m)
        return mk_fold(m)

    # deep: value re-raise / call / fold
    ip = rseat in order and myi > order.index(rseat) and me != x.bb_seat
    if nr == 1:
        v_thr = P["v3"]
    elif nr == 2:
        v_thr = P["v4"]
    else:
        v_thr = 0.6
    if eqm >= v_thr and "raise" in m:
        mult = 3.0 if ip else 3.6
        if nr >= 2:
            mult = 2.3
        tot = int(ramt * mult + callers_after * ramt)
        if tot >= 0.35 * x.cap or nr >= 3:
            tot = x.cap
        return mk_raise(m, tot)
    # light 3-bet vs wide openers that fold a lot
    if nr == 1 and "raise" in m and r_pct >= P["l3_rpct"] and callers_after == 0 and x.eff_bb > 25:
        o = x.model.get(rseat)
        if (o is not None and o.f2r >= 0.55 and P["l3_lo"] < p <= P["l3_hi"] and (cls[-1] == "s" or p <= 0.25)
                and rnd < P["l3_p"] * min(1.0, (o.f2r - 0.45) / 0.3)):
            tot = int(ramt * (3.0 if ip else 3.5))
            return mk_raise(m, tot)
    R = P["R_ip"] if ip else P["R_oop"]
    blind_seats = [s for s, _a in x.blind_seats]
    if me == x.bb_seat and nr == 1:
        R = P["R_bb"] * P["R_bb_mult"]
    elif me in blind_seats and nr == 1:
        R = P["R_oop"] * P["R_sb_mult"]
    elif nr >= 2:
        R *= P["R_3b"]
    else:
        R *= P["R_mult"]
    # implied odds for pairs / suited hands when deep
    impl = 0.0
    if x.eff_bb >= 40 and x.to_call <= 0.08 * x.eff:
        if len(cls) == 2:
            impl = P["impl_pair"]
        elif cls[2] == "s":
            impl = P["impl_suit"]
    if eqm * R + impl >= need and x.to_call <= 0.25 * x.my_total:
        return mk_call(m)
    return mk_fold(m)


# ---------------------------------------------------------------- postflop
def opp_range_pct(x, seat):
    o = x.model.get(seat)
    vpip = o.vpip if o else 0.28
    pfr = o.pfr if o else 0.17
    af = o.af if o else 0.35
    pct = 1.0
    # preflop role
    kr = 0
    for i, (s, amt) in enumerate(x.pre_raises):
        if s == seat:
            kr = i + 1
    if kr:
        pct = raiser_range(x, seat, kr, 0)
    else:
        called = [n for s, n in x.pre_calls if s == seat]
        if called:
            n = max(called)
            if n == 0:
                pct = min(1.0, vpip * 1.1)
            elif n == 1:
                pct = max(0.06, min(1.0, vpip * 0.85))
            else:
                pct = max(0.04, min(1.0, vpip * 0.4))
        else:
            pct = 1.0  # checked the big blind
    # postflop aggression this hand
    for typ, st in x.post_agg.get(seat, []):
        if typ == "b":
            pct *= min(1.0, 0.1 + 1.25 * af ** 1.3)
        else:
            pct *= min(1.0, P["nb_r"] + P["nb_r_af"] * af)
    nc = x.post_calls.get(seat, 0)
    if nc:
        pct *= 0.88 ** nc
    return max(0.02, min(1.0, pct))


def equity_vs(x, pct, iters):
    hero = [CARD[x.cards[0]], CARD[x.cards[1]]]
    board = [CARD[c] for c in x.board]
    hr = HR[bucket_idx(pct)]
    if len(board) == 5:
        return eval7.py_hand_vs_range_exact(hero, hr, board)
    return eval7.py_hand_vs_range_monte_carlo(hero, hr, board, iters)


def postflop(x):
    m = x.m
    me = x.me
    opps = x.opps
    n_opp = len(opps)
    if n_opp == 0:
        return mk_call(m) if "check" not in m else Action.check()
    pcts = {s.seat: opp_range_pct(x, s.seat) for s in opps}
    main = min(pcts, key=lambda k: pcts[k])
    iters = 100 if x.fast else 260
    if time.perf_counter() - x.t0 > 0.0003:
        iters = 50
    eq1 = equity_vs(x, pcts[main], iters)
    eqm = eq1 ** (1 + P["mw_exp"] * (n_opp - 1)) if n_opp > 1 else eq1
    x.eff_bb = 0
    pot = x.pot
    tc = x.to_call
    street = {3: 1, 4: 2, 5: 3}.get(len(x.board), x.street)
    river = len(x.board) >= 5
    # position: am I last to act among players who can still act?
    order = postflop_order(x, x.cfg_button)
    acting = [s for s in order if s == me or can_act(x.seats[s])]
    ip = bool(acting) and acting[-1] == me
    i_was_pfa = x.last_raiser == me
    rnd = random.random()
    ftb = sum(x.model[s.seat].ftb for s in opps if s.seat in x.model) / max(1, n_opp)
    max_opp_tot = max((s.stack + s.bet) for s in opps)
    eff = min(x.my_total, max_opp_tot)

    if tc == 0:
        if "raise" not in m:
            return Action.check()
        bet = None
        if eqm >= P["vb_hi"]:
            frac = P["vb_frac"]
            if eqm >= 0.85 and ftb < 0.5:
                frac = 0.95
            bet = frac * pot
        elif eqm >= (P["vb_lo"] if not river else P["vb_riv"]):
            bet = P["vb_lo_frac"] * pot
        elif n_opp == 1 and ftb >= P["steal_ftb"] and rnd < min(0.9, ftb):
            bet = 0.5 * pot
        elif i_was_pfa and street == 1 and n_opp <= 2 and not x.post_agg:
            pc = P["cbet_base"] + 0.8 * (ftb - 0.45)
            if n_opp == 2:
                pc *= 0.5
            if eqm >= 0.35:
                pc += 0.15
            if rnd < max(0.15, min(0.95, pc)):
                bet = P["cbet_frac"] * pot
        elif not river and n_opp == 1 and 0.30 <= eqm < 0.55 and ip and rnd < P["semi"]:
            bet = 0.5 * pot
        elif river and n_opp == 1 and eqm < 0.2 and ftb >= 0.5 and rnd < P["rbluff"] * (ftb / 0.5):
            bet = 0.6 * pot
        if bet is None:
            return Action.check()
        tot = x.my_bet + int(max(bet, x.bb))
        if tot >= 0.45 * x.cap or (eff - tot) < 0.3 * pot:
            tot = x.cap
        return mk_raise(m, tot)

    # facing a bet
    need = tc / float(pot + tc)
    aggressor = None
    for s in opps:
        if s.bet > x.my_bet and (aggressor is None or s.bet > x.seats[aggressor].bet):
            aggressor = s.seat
    a_allin = aggressor is not None and x.seats[aggressor].stack == 0
    commit = tc >= 0.5 * x.my_stack or a_allin
    if commit and aggressor is not None and n_opp == 1:
        ev_c, ev_f = call_allin_ev(x, aggressor, eqm)
        if ev_c > ev_f:
            if not a_allin and eqm >= 0.6 and "raise" in m:
                return mk_raise(m, x.cap)
            return mk_call(m)
        return mk_fold(m)
    raise_thr = P["raise_thr"] if not river else P["raise_thr_riv"]
    if eqm >= raise_thr and "raise" in m:
        cur = x.my_bet + tc
        tot = cur + int(0.8 * (pot + tc))
        if tot >= 0.4 * x.cap:
            tot = x.cap
        return mk_raise(m, tot)
    margin = P["m_riv"] if river else (P["m_ip"] if ip else P["m_oop"])
    if commit:
        margin += 0.04
    if river and aggressor is not None and aggressor in x.model and x.model[aggressor].af < 0.35:
        margin += P["riv_passive"]
    if eqm >= need + margin:
        return mk_call(m)
    return mk_fold(m)


# ---------------------------------------------------------------- warm-up at import
def _warm():
    try:
        h = [CARD["As"], CARD["Kd"]]
        for b in (["7s", "2c", "Jd"], ["7s", "2c", "Jd", "3h"], ["7s", "2c", "Jd", "3h", "9c"]):
            bc = [CARD[c] for c in b]
            for hr in HR:
                if len(bc) == 5:
                    eval7.py_hand_vs_range_exact(h, hr, bc)
                else:
                    eval7.py_hand_vs_range_monte_carlo(h, hr, bc, 20)
        icm_me([1000, 2000, 3000, 4000], 1, [50.0, 30.0, 20.0])
        json.loads(json.dumps({"S": {"1": [0] * 9}, "c": _new_ctx()}))
    except Exception:
        pass


_warm()
gc.collect()
try:
    gc.freeze()
except Exception:
    pass
