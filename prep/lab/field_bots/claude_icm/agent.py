"""claude_icm: ICM-aware sit-and-go bot.

Preflop: ICM-evaluated push/fold and reshove/call-all-in decisions (Malmuth-Harville equity on the
resulting stacks), opponent call/fold probabilities from a pot-odds model blended with observed table
stats; standard opening/3-bet ranges when deep. Postflop: equity vs the villain's preflop-action range
(eval7 Monte Carlo on a sub-sampled range), discounted for villain aggression, plus ICM-adjusted
calling thresholds for big calls. Per-table opponent stats travel in `memory`.
"""
import json
import marshal
import os
import random
import time

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

try:
    import gc as _gc
except Exception:  # pragma: no cover
    _gc = None

HERE = os.path.dirname(os.path.abspath(__file__))
DEBUG = bool(os.environ.get("CLAUDE_ICM_DEBUG"))

# ---------------------------------------------------------------------------------------------------
# Preflop tables (built offline by build_tables.py)
# ---------------------------------------------------------------------------------------------------
with open(os.path.join(HERE, "preflop.json")) as _f:
    _PF = json.load(_f)
CLASSES = _PF["classes"]
ORDER = _PF["order"]
GRID = _PF["grid"]
_EQG = _PF["eq"]
CI = {c: i for i, c in enumerate(CLASSES)}
NCOMBO = [6 if len(c) == 2 else (4 if c[2] == "s" else 12) for c in CLASSES]

# hand percentile (midpoint of the class in the ranking, in % of all 1326 combos)
HP = [0.0] * 169
CUMHI = [0.0] * 169
_acc = 0
for _c in ORDER:
    _i = CI[_c]
    HP[_i] = (_acc + NCOMBO[_i] / 2.0) * 100.0 / 1326.0
    CUMHI[_i] = (_acc + NCOMBO[_i]) * 100.0 / 1326.0
    _acc += NCOMBO[_i]

# EQI[ci][p] = HU all-in equity of class ci vs the top p% (p = 0..100), linear in the grid
EQI = []
for _i in range(169):
    row = [0.0] * 101
    for p in range(101):
        q = max(GRID[0], p)
        j = 0
        while j < len(GRID) - 1 and GRID[j + 1] < q:
            j += 1
        if j >= len(GRID) - 1:
            row[p] = _EQG[-1][_i]
        else:
            a, b = GRID[j], GRID[j + 1]
            t = (q - a) / float(b - a)
            row[p] = _EQG[j][_i] * (1 - t) + _EQG[j + 1][_i] * t
    EQI.append(row)


def eq_top(ci, pct):
    p = int(pct + 0.5)
    if p < 1:
        p = 1
    elif p > 100:
        p = 100
    return EQI[ci][p]


# CALLP[g][r] = % of all combos whose equity vs top GRID[g]% is >= r/100
CALLP = []
for _g in range(len(GRID)):
    pairs = sorted(((_EQG[_g][i], NCOMBO[i]) for i in range(169)), reverse=True)
    row = []
    for r in range(101):
        thr = r / 100.0
        n = 0
        for e, c in pairs:
            if e >= thr:
                n += c
            else:
                break
        row.append(n * 100.0 / 1326.0)
    CALLP.append(row)


def call_pct(req, perceived):
    """% of hands a rational caller continues with when needing equity `req` vs a top-`perceived`% range."""
    g = 0
    best = 1e9
    for j, v in enumerate(GRID):
        d = abs(v - perceived)
        if d < best:
            best, g = d, j
    r = int(req * 100 + 0.5)
    if r < 0:
        r = 0
    elif r > 100:
        r = 100
    return CALLP[g][r]


RANKS = "23456789TJQKA"
RVAL = {r: i for i, r in enumerate(RANKS)}


def hand_class(c1, c2):
    r1, r2 = c1[0], c2[0]
    if RVAL[r1] < RVAL[r2]:
        r1, r2 = r2, r1
    if r1 == r2:
        return CI[r1 + r2]
    return CI[r1 + r2 + ("s" if c1[1] == c2[1] else "o")]


# All 1326 combos in ranking order (suits shuffled within a class to avoid stride artifacts).
_rng0 = random.Random(7)
CARD = {r + s: eval7.Card(r + s) for r in RANKS for s in "cdhs"}
SORTED = []
for _c in ORDER:
    a, b = _c[0], _c[1]
    cl = []
    S = "cdhs"
    if a == b:
        for x in range(4):
            for y in range(x + 1, 4):
                cl.append((CARD[a + S[x]], CARD[b + S[y]]))
    elif _c[2] == "s":
        for s in S:
            cl.append((CARD[a + s], CARD[b + s]))
    else:
        for s in S:
            for t in S:
                if s != t:
                    cl.append((CARD[a + s], CARD[b + t]))
    _rng0.shuffle(cl)
    for cc in cl:
        SORTED.append((cc, 1.0))
_HR = eval7.HandRange("AA")
_MC = eval7.py_hand_vs_range_monte_carlo
_EX = eval7.py_hand_vs_range_exact


def range_band(lo, hi, maxn):
    i0 = int(lo * 13.26)
    i1 = int(hi * 13.26 + 0.5)
    if i1 > 1326:
        i1 = 1326
    if i1 <= i0 + 6:
        i1 = min(1326, i0 + 6)
        if i1 - i0 < 6:
            i0 = i1 - 6
    step = (i1 - i0) // maxn + 1
    return SORTED[i0:i1:step]


def equity_vs(hero, board, lo, hi, river, maxn=140, iters=300):
    hands = range_band(lo, hi, maxn)
    dead = set(hero) | set(board)
    live = [h for h in hands if h[0][0] not in dead and h[0][1] not in dead]
    if len(live) < 3:
        hands = range_band(0, 100, maxn)
        live = [h for h in hands if h[0][0] not in dead and h[0][1] not in dead]
    _HR.hands = live
    if river:
        return _EX(hero, _HR, board)
    return _MC(hero, _HR, board, iters)


# ---------------------------------------------------------------------------------------------------
# ICM
# ---------------------------------------------------------------------------------------------------
def _icm_rec(oth, s, T, pay, place, prob):
    ev = prob * s / T * pay[place]
    if place + 1 < len(pay) and prob > 1e-4:
        for j, a in enumerate(oth):
            ev += _icm_rec(oth[:j] + oth[j + 1:], s, T - a, pay, place + 1, prob * a / T)
    return ev


def icm_me(st, i, pay):
    """Our expected payout (Malmuth-Harville) given stacks `st` (all > 0) and our index i."""
    n = len(st)
    T = float(sum(st))
    s = st[i]
    k = min(len(pay), n)
    if n == 1:
        return pay[0]
    ev = pay[0] * s / T
    if k == 1:
        return ev
    oth = st[:i] + st[i + 1:]
    if k == 2:
        return ev + pay[1] * (s / T) * sum(a / (T - a) for a in oth)
    if k == 3:
        p2 = 0.0
        p3 = 0.0
        m = len(oth)
        for x in range(m):
            a = oth[x]
            Ta = T - a
            pa = a / T
            p2 += pa / Ta
            q = 0.0
            for y in range(m):
                if y != x:
                    b = oth[y]
                    q += b / (Ta - b)
            p3 += pa / Ta * q
        return ev + pay[1] * s * p2 + pay[2] * s * p3
    return _icm_rec(oth, s, T, pay[:k], 0, 1.0)


class Ctx(object):
    pass


# Tunable parameters (kept in one place so variants can be A/B tested).
P = {
    "alpha_mult": 1.0,     # scale on ICM weight early (1 = schedule as written)
    "push_margin": 0.0,    # extra EV (points) a shove must beat folding by
    "open_mult": 1.0,      # scale on opening ranges
    "shove_guess": 0.8,    # scale on the Nash-style guess of villains' shove ranges
    "postflop_k": 1.0,     # scale on the aggression discount
    "cbet": 1.0,           # scale on bluff frequencies
}


def icm_value(ctx, final, who=None):
    """Value (payout points) of `final` (seat -> chips after the hand) for seat `who` (default: us).
    Blend of ICM and chip-linear value: pure ICM ignores future blind pressure, which matters most
    when many players remain, so early on we weight chip EV more (alpha < 1)."""
    me = ctx.me if who is None else who
    mine = final.get(me, 0)
    if mine <= 0:
        place = ctx.n_alive
        return ctx.pay[place - 1] if place - 1 < len(ctx.pay) else 0.0
    seats = [s for s in ctx.alive if final.get(s, 0) > 0]
    st = [float(final[s]) for s in seats]
    v = icm_me(st, seats.index(me), ctx.pay)
    a = ctx.alpha
    if a < 1.0:
        v = a * v + (1.0 - a) * ctx.pay_sum * mine / float(sum(st))
    return v


# ---------------------------------------------------------------------------------------------------
# Opponent stats (memory)
# ---------------------------------------------------------------------------------------------------
H, VP, PR, FR, FF, TB, PA, PC, PK, PFD, FB, FFB = range(12)
NST = 12


_KC = {}


def _kind_slow(x):
    k = getattr(x, "value", x)
    k = str(k).lower()
    if "." in k:
        k = k.rsplit(".", 1)[1]
    return k


def _kind(x):
    try:
        return _KC[x]
    except KeyError:
        k = _kind_slow(x)
        if len(_KC) < 256:
            _KC[x] = k
        return k
    except TypeError:  # unhashable
        return _kind_slow(x)


def load_mem(memory):
    if memory:
        try:
            d = marshal.loads(memory)
            if isinstance(d, dict) and d.get("v") == 2 and isinstance(d.get("s"), dict) and isinstance(d.get("c"), dict):
                return d
        except Exception:
            pass
    return {"v": 2, "s": {}, "c": {"st": 0, "nr": 0, "bet": 0, "cnt": [], "vp": [], "pr": [], "fc": []}}


def update_stats(mem, events):
    S = mem["s"]
    c = mem["c"]
    for e in events or ():
        k = _kind(e.kind)
        if k == "hand":
            c = {"st": 0, "nr": 0, "bet": 0, "cnt": [], "vp": [], "pr": [], "fc": []}
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
        st = S.get(key)
        if st is None:
            st = [0] * NST
            S[key] = st
        if c["st"] == 0:
            if s not in c["cnt"]:
                c["cnt"].append(s)
                st[H] += 1
            facing = c["nr"] >= 1
            if facing and s not in c["fc"]:
                c["fc"].append(s)
                st[FR] += 1
                if k == "fold":
                    st[FF] += 1
                elif k == "raise":
                    st[TB] += 1
            if k in ("call", "raise") and s not in c["vp"]:
                c["vp"].append(s)
                st[VP] += 1
            if k == "raise":
                if s not in c["pr"]:
                    c["pr"].append(s)
                    st[PR] += 1
                c["nr"] += 1
        else:
            facing = c["bet"] > 0
            if facing:
                st[FB] += 1
            if k == "raise":
                st[PA] += 1
                c["bet"] = 1
            elif k == "call":
                st[PC] += 1
            elif k == "check":
                st[PK] += 1
            elif k == "fold":
                st[PFD] += 1
                if facing:
                    st[FFB] += 1
    mem["c"] = c


def stat(mem, seat, num, den, prior, k):
    st = mem["s"].get(str(seat))
    if st is None:
        return prior
    if isinstance(den, tuple):
        d = sum(st[x] for x in den)
    else:
        d = st[den]
    return (st[num] + prior * k) / (d + k)


def nobs(mem, seat, den):
    st = mem["s"].get(str(seat))
    return 0 if st is None else st[den]


def post_aggr(mem, seat):
    st = mem["s"].get(str(seat))
    if st is None:
        return 0.3
    d = st[PA] + st[PC] + st[PK] + st[PFD]
    return (st[PA] + 0.3 * 6) / (d + 6)


# ---------------------------------------------------------------------------------------------------
# Action helpers
# ---------------------------------------------------------------------------------------------------
def legal_map(state):
    m = {}
    for a in state.legal_actions:
        m[_kind(a.kind)] = a
    return m


def act_fold(L):
    if "check" in L:
        return Action.check()
    if "fold" in L:
        return Action.fold()
    if "call" in L:
        return Action.call()
    return Action.check()


def act_check_call(L):
    if "check" in L:
        return Action.check()
    if "call" in L:
        return Action.call()
    return act_fold(L)


def act_raise(L, total):
    a = L.get("raise")
    if a is None:
        return act_check_call(L)
    lo, hi = int(a.min_amount), int(a.max_amount)
    t = int(total)
    if t >= hi * 0.85:
        t = hi
    if t < lo:
        t = lo
    if t > hi:
        t = hi
    return Action.raise_to(t)


def act_allin(L):
    a = L.get("raise")
    if a is None:
        return act_check_call(L)
    return Action.raise_to(int(a.max_amount))


# ---------------------------------------------------------------------------------------------------
# Hand parsing
# ---------------------------------------------------------------------------------------------------
def build_ctx(state, mem):
    ctx = Ctx()
    ctx.mem = mem
    me = state.seat
    ctx.me = me
    seats = {}
    for s in state.seats:
        seats[s.seat] = s
    ctx.seats = seats
    bl = state.blinds
    ctx.sb, ctx.bb = int(bl[0]), int(bl[1])
    if ctx.bb <= 0:
        ctx.bb = 1
    stat_of = {s: _kind(o.status) for s, o in seats.items()}
    ctx.alive = sorted(s for s, st in stat_of.items() if st != "busted")
    ctx.n_alive = len(ctx.alive)
    pay = list(getattr(state.config, "payouts", None) or [50, 30, 20])
    while pay and pay[-1] == 0:
        pay.pop()
    if not pay:
        pay = [1.0]
    ctx.pay = [float(x) for x in pay]
    ctx.pay_sum = sum(ctx.pay)
    k = len(ctx.pay)
    na = ctx.n_alive
    if na <= k + 1:
        alpha = 1.0
    elif na == k + 2:
        alpha = 0.85
    elif na == k + 3:
        alpha = 0.72
    else:
        alpha = 0.6
    try:
        cfg = state.config
        left = int(cfg.hand_cap) - int(state.hand_number)
        if left < 25:
            alpha = 1.0
    except Exception:
        pass
    # blind pressure: with a small M, folding is costly in ways ICM does not see
    if na > 2:
        my_chips = int(seats[me].stack) + int(seats[me].bet or 0)
        M = my_chips / float(ctx.sb + ctx.bb)
        if M < 8.0:
            alpha *= 0.6 + 0.05 * M
    alpha *= P["alpha_mult"]
    ctx.alpha = 1.0 if alpha > 1.0 else alpha
    if me not in ctx.alive:
        ctx.alive = sorted(ctx.alive + [me])
        stat_of[me] = "active"
        ctx.n_alive = len(ctx.alive)
    ctx.behind = {s: int(seats[s].stack or 0) for s in seats}
    ctx.bet = {s: int(seats[s].bet or 0) for s in seats}
    ctx.status = {s: stat_of[s] for s in seats}
    ctx.pot = int(state.pot)
    ctx.to_call = int(state.to_call or 0)
    ctx.board = list(state.board or [])
    ctx.cards = list(state.cards)

    # history
    street = 0
    committed = {}
    sbet = {}
    blinds = []
    pf_raises = 0
    pf_aggr = None
    last_aggr = None
    acts = {}
    raise_sizes = []
    for e in state.history or ():
        k = _kind(e.kind)
        if k == "hand":
            continue
        if k == "board":
            street += 1
            sbet = {}
            continue
        s = e.seat
        amt = int(e.amount or 0)
        if k == "blind" or k == "ante":
            committed[s] = committed.get(s, 0) + amt
            if k == "blind":
                sbet[s] = sbet.get(s, 0) + amt
                blinds.append((s, amt))
            continue
        if k == "call":
            committed[s] = committed.get(s, 0) + amt
            sbet[s] = sbet.get(s, 0) + amt
        elif k == "raise":
            committed[s] = committed.get(s, 0) + amt - sbet.get(s, 0)
            sbet[s] = amt
            if street == 0:
                pf_raises += 1
                pf_aggr = s
                raise_sizes.append(amt)
            last_aggr = s
        acts.setdefault(s, []).append((street, k, amt))
    ctx.committed = committed
    ctx.acts = acts
    ctx.pf_raises = pf_raises
    ctx.pf_aggr = pf_aggr
    ctx.last_aggr = last_aggr
    ctx.raise_sizes = raise_sizes
    # blinds / positions
    bb_seat = None
    sb_seat = None
    if blinds:
        bb_seat = max(blinds, key=lambda x: x[1])[0] if len(blinds) > 1 else blinds[0][0]
        for s, a in blinds:
            if s != bb_seat:
                sb_seat = s
                break
    ctx.bb_seat = bb_seat
    ctx.sb_seat = sb_seat
    ctx.button = state.button
    al = ctx.alive
    if bb_seat in al:
        j = al.index(bb_seat)
        pf_order = al[j + 1:] + al[:j + 1]
    else:
        pf_order = al[:]
    ctx.pf_order = pf_order
    ctx.start = {s: ctx.behind[s] + committed.get(s, 0) for s in seats}
    ctx.total = {s: ctx.behind[s] + ctx.bet[s] for s in seats}  # chips available this street
    return ctx


def players_after(ctx, order):
    me = ctx.me
    if me not in order:
        return []
    j = order.index(me)
    return [s for s in order[j + 1:] if ctx.status.get(s) == "active"]


# ---------------------------------------------------------------------------------------------------
# ICM all-in EV model
# ---------------------------------------------------------------------------------------------------
def showdown_final(ctx, vills, my_total):
    """Final-stack dicts (win, lose) when we commit `my_total` this street vs villains `vills`."""
    me = ctx.me
    maxv = max(ctx.total[v] for v in vills)
    c_me = min(my_total, maxv)
    pot_f = ctx.pot - ctx.bet[me] + c_me
    cv = {}
    for v in vills:
        c = min(ctx.total[v], my_total)
        cv[v] = c
        pot_f += c - ctx.bet[v]
    base = dict(ctx.behind)
    win = dict(base)
    win[me] = ctx.behind[me] + ctx.bet[me] - c_me + pot_f
    for v in vills:
        win[v] = ctx.behind[v] + ctx.bet[v] - cv[v]
    lose = dict(base)
    lose[me] = ctx.behind[me] + ctx.bet[me] - c_me
    wv = max(vills, key=lambda v: ctx.total[v])
    for v in vills:
        lose[v] = ctx.behind[v] + ctx.bet[v] - cv[v]
    lose[wv] += pot_f
    return win, lose


def fold_final(ctx):
    me = ctx.me
    fin = dict(ctx.behind)
    # someone else collects the pot: the player with the biggest bet (raiser / big blind)
    cand = [s for s in ctx.alive if s != me and ctx.status.get(s) in ("active", "all_in")]
    if cand:
        w = max(cand, key=lambda s: (ctx.bet[s], ctx.total[s]))
        fin[w] += ctx.pot
    return fin


def n_behind_at(ctx, v):
    """Players still to act behind seat v when it made its first preflop raise (approx: seats after v)."""
    order = ctx.pf_order
    if v not in order:
        return 3
    j = order.index(v)
    return len(order) - 1 - j


def pf_range_of(ctx, v):
    """Estimated preflop range (top %) of villain v given his actions this hand."""
    mem = ctx.mem
    pfr = stat(mem, v, PR, H, 0.17, 8)
    vpip = stat(mem, v, VP, H, 0.30, 8)
    acts = [a for a in ctx.acts.get(v, ()) if a[0] == 0]
    raised = [a for a in acts if a[1] == "raise"]
    if raised:
        # how many raises happened before his last raise
        n_before = 0
        for amt in ctx.raise_sizes:
            if amt == raised[-1][2]:
                break
            n_before += 1
        if n_before == 0:
            r = pfr * 100
            if ctx.status.get(v) == "all_in" or raised[-1][2] >= 0.6 * ctx.start[v]:
                # open shove: Nash-style guess from depth and position, blended with his raise rate
                sbb = ctx.start[v] / float(ctx.bb)
                nb = n_behind_at(ctx, v)
                pos = {0: 1.0, 1: 1.6, 2: 1.3, 3: 1.1}.get(nb, 1.0) if ctx.n_alive > 2 else 1.9
                g = min(100.0, (8.0 + 220.0 / max(2.0, sbb)) * pos) * P["shove_guess"]
                n = nobs(ctx.mem, v, H)
                w = n / (n + 15.0)
                r = (1 - w) * g + w * max(r, g * 0.6)
        elif n_before == 1:
            tb = stat(mem, v, TB, FR, 0.08, 6)
            r = max(tb * 100, pfr * 100 * 0.35)
        else:
            r = max(3.0, pfr * 100 * 0.15)
        return max(2.5, min(100.0, r))
    if any(a[1] == "call" for a in acts):
        return max(8.0, min(100.0, vpip * 100))
    return 100.0


def caller_prob(ctx, v, my_total, perceived, rng_v, fresh):
    """Probability villain v calls our all-in for `my_total`, and the % of hands he calls with."""
    me = ctx.me
    Tv = ctx.total[v]
    m = min(my_total, Tv)
    need = m - ctx.bet[v]
    if need <= 0:
        return 1.0, rng_v
    pot_if = ctx.pot + (m - ctx.bet[me]) + need
    req = need / float(pot_if)
    # ICM / survival tax
    k = len(ctx.pay)
    na = ctx.n_alive
    covered = Tv <= my_total
    if na <= 2:
        tax = 0.0
    elif na <= k:
        tax = 0.02 if covered else 0.01
    elif na == k + 1:
        tax = 0.06 if covered else 0.03
    elif na <= k + 3:
        tax = 0.03 if covered else 0.015
    else:
        tax = 0.015
    c = call_pct(req + tax, perceived)
    committed = ctx.bet[v] >= 0.45 * Tv
    if committed:
        c = rng_v
    c = min(c, rng_v)
    p_model = c / rng_v if rng_v > 0 else 1.0
    # blend with observed fold-to-raise
    n = nobs(ctx.mem, v, FR)
    if n > 0 and not committed:
        f_obs = stat(ctx.mem, v, FF, FR, 1.0 - p_model, 3)
        w = n / (n + 6.0)
        p = (1 - w) * p_model + w * (1.0 - f_obs)
        c = max(c, min(rng_v, p * rng_v)) if p > p_model else max(1.0, p * rng_v)
        p_model = p
    if p_model > 1:
        p_model = 1.0
    if p_model < 0:
        p_model = 0.0
    return p_model, max(1.0, c)


def allin_ev(ctx, ci, my_total, perceived):
    """EV (ICM) of committing `my_total` chips this street. Returns (ev_allin, ev_fold)."""
    me = ctx.me
    allins = [s for s in ctx.alive if s != me and ctx.status.get(s) == "all_in" and ctx.bet[s] > 0]
    actives = [s for s in ctx.alive if s != me and ctx.status.get(s) == "active"]
    after = players_after(ctx, ctx.pf_order) if not ctx.board else []
    before = [s for s in actives if s not in after]
    pot_list = after + before
    ev_fold = icm_value(ctx, fold_final(ctx))
    base_eq = 1.0
    base_v = []
    for v in allins:
        r = pf_range_of(ctx, v)
        base_eq *= eq_top(ci, r)
        base_v.append(v)
    nb = len(base_v)
    prob_left = 1.0
    ev = 0.0
    for v in pot_list:
        if ctx.total[v] <= ctx.bet[v]:
            continue
        acted = any(a[0] == 0 and a[1] in ("call", "raise") for a in ctx.acts.get(v, ()))
        rng_v = pf_range_of(ctx, v) if acted else 100.0
        p, c = caller_prob(ctx, v, my_total, perceived, rng_v, not acted)
        if p <= 0.003:
            continue
        e = base_eq * eq_top(ci, c)
        nvil = nb + 1
        if nvil >= 2:
            e = e ** 0.85
        win, lose = showdown_final(ctx, base_v + [v], my_total)
        ev += prob_left * p * (e * icm_value(ctx, win) + (1 - e) * icm_value(ctx, lose))
        prob_left *= (1 - p)
        if prob_left < 1e-3:
            break
    if prob_left > 0:
        if base_v:
            e = base_eq ** 0.85 if nb >= 2 else base_eq
            win, lose = showdown_final(ctx, base_v, my_total)
            ev += prob_left * (e * icm_value(ctx, win) + (1 - e) * icm_value(ctx, lose))
        else:
            fin = dict(ctx.behind)
            fin[me] += ctx.pot
            ev += prob_left * icm_value(ctx, fin)
    return ev, ev_fold


# ---------------------------------------------------------------------------------------------------
# Preflop
# ---------------------------------------------------------------------------------------------------
OPEN_PCT = {1: 50.0, 2: 42.0, 3: 28.0, 4: 22.0, 5: 18.0, 6: 15.0, 7: 13.0}


def preflop(ctx, L, ci):
    me = ctx.me
    bb = ctx.bb
    hp = HP[ci]
    my_total = ctx.total[me]
    to_call = ctx.to_call
    after = players_after(ctx, ctx.pf_order)
    opps = [s for s in ctx.alive if s != me and ctx.status.get(s) in ("active", "all_in")]
    if not opps:
        return act_check_call(L)
    max_opp = max(ctx.total[s] for s in opps)
    eff = min(my_total, max_opp)
    eff_bb = eff / float(bb)
    nr = ctx.pf_raises
    pair = CLASSES[ci][0] == CLASSES[ci][1]
    suited = len(CLASSES[ci]) == 3 and CLASSES[ci][2] == "s"
    avg_stack = sum(ctx.total.values()) / float(len(ctx.total))
    big = my_total > 1.4 * avg_stack
    bubble = ctx.n_alive <= len(ctx.pay) + 1 and ctx.n_alive > 2

    if nr == 0:
        n_behind = len(after)
        limpers = [s for s in opps if any(a[0] == 0 and a[1] == "call" for a in ctx.acts.get(s, ()))]
        can_check = "check" in L
        # --- push/fold zone ---
        push_lim = 10.0 if n_behind >= 4 else 14.0
        if eff_bb <= push_lim or my_total <= 3 * bb:
            if hp <= 3.0:
                return act_allin(L)
            if ctx.n_alive == 2:
                perceived = 60.0
            elif n_behind <= 2:
                perceived = 40.0
            else:
                perceived = 25.0
            ev_s, ev_f = allin_ev(ctx, ci, my_total, perceived)
            if can_check:
                # checking keeps our stack in the hand; approximate it with a small bonus over folding
                won = dict(ctx.behind)
                won[me] = ctx.behind[me] + ctx.pot
                ev_f = ev_f + 0.075 * (icm_value(ctx, won) - ev_f)
            if ev_s > ev_f + 0.01 + P["push_margin"]:
                return act_allin(L)
            return act_fold(L)
        # --- deep: open / iso / over-limp ---
        op = OPEN_PCT.get(min(7, max(1, n_behind)), 13.0)
        if ctx.n_alive <= 3:
            op = {1: 60.0, 2: 48.0}.get(n_behind, 40.0)
        # steal adjustment from observed folding of players behind
        if after:
            fs = [stat(ctx.mem, s, FF, FR, 0.55, 4) for s in after]
            fall = 1.0
            for f in fs:
                fall *= f
            op += (fall - 0.25) * 60.0
            vp = max(stat(ctx.mem, s, VP, H, 0.3, 8) for s in after)
            if vp > 0.6:
                op *= 0.8
        if bubble:
            op *= 1.2 if big else 0.85
        op = max(6.0, min(100.0, op * P["open_mult"]))
        if not limpers:
            if hp <= op:
                size = (2.2 if eff_bb < 25 else 2.5) * bb
                if n_behind == 1 and ctx.sb_seat == me:
                    size = 3.0 * bb if eff_bb >= 25 else 2.5 * bb
                if size >= 0.4 * my_total:
                    return act_allin(L)
                return act_raise(L, size)
            if can_check:
                return Action.check()
            return act_fold(L)
        # limped pot
        iso = max(8.0, op * 0.55)
        if hp <= iso:
            size = (3.0 + len(limpers)) * bb
            if size >= 0.4 * my_total:
                return act_allin(L)
            return act_raise(L, size)
        if can_check:
            return Action.check()
        if to_call <= bb and (hp <= 40.0 or (pair and hp <= 60) or (ctx.sb_seat == me and hp <= 60)):
            return act_check_call(L)
        return act_fold(L)

    # ---------------- facing a raise ----------------
    raiser = ctx.pf_aggr
    r_rng = pf_range_of(ctx, raiser) if raiser is not None else 20.0
    eq = eq_top(ci, r_rng)
    allin_faced = any(ctx.status.get(s) == "all_in" and ctx.bet[s] > 0 for s in opps)
    call_commits = to_call >= 0.35 * my_total or (my_total - to_call) < 3 * bb
    shallow = eff_bb <= (20.0 if nr == 1 else 32.0)
    if allin_faced or call_commits or shallow:
        if hp <= 1.5:
            return act_allin(L)
        perceived = 12.0 if nr >= 1 else 20.0
        ev_s, ev_f = allin_ev(ctx, ci, my_total, perceived)
        if ev_s > ev_f + 0.01:
            # all callers committed / already all-in => calling is the same as shoving
            if "raise" in L and not (allin_faced and all(ctx.total[s] <= ctx.bet[s] for s in opps if ctx.status.get(s) == "active")):
                return act_allin(L)
            return act_check_call(L)
        return act_fold(L)

    # deep, facing a non-committing raise
    my_bet = ctx.bet[me]
    last = ctx.raise_sizes[-1] if ctx.raise_sizes else bb
    ip = bool(after) is False and ctx.bb_seat != me and ctx.sb_seat != me
    if nr == 1:
        val = eq >= 0.60 or hp <= 3.0
        if val:
            size = last * (3.0 if ip else 3.6) + 1.0 * bb * max(0, len(opps) - 1)
            if size >= 0.35 * my_total:
                return act_allin(L)
            return act_raise(L, size)
        req = to_call / float(ctx.pot + to_call)
        realize = 0.92 if ip else 0.80
        if ctx.bb_seat == me:
            realize = 0.85
        if to_call <= 0.15 * my_total:
            if eq * realize >= req + 0.03 and hp <= 55:
                return act_check_call(L)
            if pair and to_call * 15 <= eff and to_call <= 0.08 * my_total:
                return act_check_call(L)
        return act_fold(L)
    # facing 3-bet or more, deep
    if eq >= 0.56 or hp <= 2.0:
        return act_allin(L)
    req = to_call / float(ctx.pot + to_call)
    if eq * 0.85 >= req + 0.05 and to_call <= 0.25 * my_total and (pair or hp <= 8):
        return act_check_call(L)
    return act_fold(L)


# ---------------------------------------------------------------------------------------------------
# Postflop
# ---------------------------------------------------------------------------------------------------
def villain_band(ctx, v):
    mem = ctx.mem
    acts = [a for a in ctx.acts.get(v, ()) if a[0] == 0]
    pfr = stat(mem, v, PR, H, 0.17, 8) * 100
    vpip = stat(mem, v, VP, H, 0.30, 8) * 100
    if any(a[1] == "raise" for a in acts):
        r = pf_range_of(ctx, v)
        return 0.0, max(4.0, r)
    if any(a[1] == "call" for a in acts):
        if ctx.pf_raises >= 1:
            lo = min(4.0, pfr * 0.25)
            return lo, max(lo + 10.0, min(100.0, vpip))
        return 3.0, max(40.0, min(100.0, vpip * 1.2))
    return 4.0, 100.0


def postflop(ctx, L, t0):
    me = ctx.me
    bb = ctx.bb
    street = len(ctx.board)
    river = street == 5
    opps = [s for s in ctx.alive if s != me and ctx.status.get(s) in ("active", "all_in")]
    if not opps:
        return act_check_call(L)
    hero = [CARD[c] for c in ctx.cards]
    board = [CARD[c] for c in ctx.board]
    vill = sorted(opps, key=lambda s: (s != ctx.last_aggr, s != ctx.pf_aggr))[:3]
    e = 1.0
    iters = 260 if len(vill) == 1 else 160
    for v in vill:
        lo, hi = villain_band(ctx, v)
        e *= equity_vs(hero, board, lo, hi, river, 140 if len(vill) == 1 else 90, iters)
    if len(vill) >= 2:
        e = e ** 0.85
    if len(opps) > 3:
        e *= 0.9

    pot = ctx.pot
    to_call = ctx.to_call
    my_behind = ctx.behind[me]
    my_total = ctx.total[me]
    pfa = ctx.pf_aggr == me
    act_v = [s for s in opps if ctx.status.get(s) == "active"]
    eff_behind = min(my_behind, max([ctx.behind[s] for s in opps] + [0]))
    rnd = random.random()

    if to_call <= 0:
        if not act_v and "check" in L:
            return Action.check()
        # we can bet
        spr = eff_behind / float(max(1, pot))
        n = len(opps)
        vthr = 0.62 if n == 1 else (0.55 if n == 2 else 0.5)
        if river:
            vthr += 0.05
        if e >= vthr:
            frac = 0.55 if street == 3 else (0.65 if street == 4 else 0.7)
            if e >= 0.85 and river:
                frac = 0.9
            if spr <= 1.3:
                return act_allin(L)
            return act_raise(L, ctx.bet[me] + max(bb, frac * pot))
        # bluff / c-bet
        if n == 1:
            v = opps[0]
            fold_b = stat(ctx.mem, v, FFB, FB, 0.45, 5)
            agg_v = post_aggr(ctx.mem, v)
            freq = 0.0
            if street == 3 and pfa:
                freq = min(0.95, max(0.3, fold_b * 1.25))
            elif street == 3:
                freq = 0.25 if fold_b > 0.55 else 0.0
            elif street == 4:
                freq = 0.45 if (pfa and e >= 0.4) else (0.0 if fold_b < 0.6 else 0.4)
            else:
                freq = (0.35 if fold_b >= 0.6 and nobs(ctx.mem, v, FB) >= 5 and e < 0.3 else 0.0)
            freq *= P["cbet"]
            if agg_v > 0.65:
                freq *= 0.4  # maniacs raise bets; bluffing them is wasted
            if rnd < freq:
                frac = 0.5 if street == 3 else 0.6
                return act_raise(L, ctx.bet[me] + max(bb, frac * pot))
        elif n == 2 and street == 3 and pfa and e >= 0.4 and rnd < 0.5:
            return act_raise(L, ctx.bet[me] + max(bb, 0.5 * pot))
        return Action.check() if "check" in L else act_fold(L)

    # ---------------- facing a bet ----------------
    aggr = ctx.last_aggr if ctx.last_aggr in opps else opps[0]
    a_v = post_aggr(ctx.mem, aggr)
    t = (0.72 - a_v) / 0.45
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    pot_before = max(1, pot - to_call)
    b = to_call / float(pot_before)
    b = 0.2 if b < 0.2 else (1.6 if b > 1.6 else b)
    smult = {3: 0.7, 4: 0.9, 5: 1.1}.get(street, 1.0)
    k = t * (0.3 + 0.45 * b) * smult * P["postflop_k"]
    my_street_acts = [a for a in ctx.acts.get(me, ()) if a[0] == street - 2 and a[1] == "raise"]
    if my_street_acts:
        k += 0.35 * t  # he raised our bet
    # calls on earlier streets make the range stronger
    prev_calls = sum(1 for a in ctx.acts.get(aggr, ()) if 0 < a[0] < street - 2 and a[1] in ("call", "raise"))
    k += 0.1 * t * prev_calls
    ea = e ** (1.0 + k)

    req = to_call / float(pot + to_call)
    committing = to_call >= 0.4 * my_total or (my_behind - to_call) < 0.6 * (pot + to_call)
    if committing:
        # ICM-adjusted requirement for (effectively) all-in calls
        vills = [aggr] if aggr in ctx.total else opps[:1]
        win, lose = showdown_final(ctx, vills, my_total)
        ewin, elose = icm_value(ctx, win), icm_value(ctx, lose)
        efold = icm_value(ctx, fold_final(ctx))
        if ewin > elose:
            req = max(req, (efold - elose) / (ewin - elose))
    margin = 0.02 if street < 5 else 0.03
    # value raise
    raise_thr = 0.80 if len(opps) == 1 else 0.85
    if ea >= raise_thr and "raise" in L:
        spr = eff_behind / float(max(1, pot + to_call))
        if spr <= 2.0:
            return act_allin(L)
        return act_raise(L, ctx.bet[me] + to_call + 0.8 * (pot + to_call))
    if ea >= req + margin:
        if committing and "raise" in L and ea >= 0.55 and act_v:
            return act_allin(L)
        return act_check_call(L)
    return act_fold(L)


# ---------------------------------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------------------------------
def decide(state, mem, t0):
    L = legal_map(state)
    if not L:
        return Action.fold()
    if len(L) == 1:
        k = next(iter(L))
        if k == "check":
            return Action.check()
        if k == "call":
            return Action.call()
        if k == "fold":
            return Action.fold()
    ctx = build_ctx(state, mem)
    c = ctx.cards
    if not c or len(c) != 2:
        return act_check_call(L) if "check" in L else act_fold(L)
    ci = hand_class(c[0], c[1])
    if not ctx.board:
        return preflop(ctx, L, ci)
    return postflop(ctx, L, t0)


def sanitize(state, action):
    L = legal_map(state)
    k = _kind(action.kind)
    if k not in L:
        return act_fold(L)
    if k == "raise":
        a = L["raise"]
        t = int(action.amount)
        if t < int(a.min_amount) or t > int(a.max_amount):
            t = max(int(a.min_amount), min(int(a.max_amount), t))
            return Action.raise_to(t)
    return action


class _O(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _warmup():
    """Run the main code paths once at import so no timed decision pays first-call costs."""
    E = lambda k, s=None, a=None: _O(kind=k, seat=s, amount=a, cards=None)
    la = lambda k, lo=0, hi=0: _O(kind=k, min_amount=lo, max_amount=hi)
    cfg = _O(payouts=[50, 30, 20, 0, 0, 0, 0, 0], hand_cap=250, table_id="w")
    for board, to_call, legal in (
        ([], 20, [la("fold"), la("call"), la("raise", 40, 300)]),
        (["2c", "7d", "Th"], 0, [la("check"), la("raise", 20, 280)]),
        (["2c", "7d", "Th", "Js", "3h"], 60, [la("fold"), la("call"), la("raise", 120, 280)]),
    ):
        st = _O(seat=0, cards=["As", "Kd"], board=board, pot=100, to_call=to_call, legal_actions=legal,
                history=[E("hand"), E("blind", 1, 10), E("blind", 2, 20)], button=0, blinds=[10, 20],
                seats=[_O(seat=i, stack=280, bet=0, status="active", shown_cards=[]) for i in range(3)],
                config=cfg, events=[], hand_number=5)
        decide(st, load_mem(b""), time.perf_counter())


try:
    _warmup()
except Exception:
    pass

if _gc is not None:
    try:
        _gc.collect()
        _gc.freeze()
    except Exception:
        pass


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        t0 = time.perf_counter()
        mem = None
        try:
            mem = load_mem(memory)
            update_stats(mem, getattr(state, "events", None))
        except Exception:
            mem = load_mem(b"")
        try:
            action = decide(state, mem, t0)
            action = sanitize(state, action)
        except Exception:
            if DEBUG:
                raise
            try:
                action = act_fold(legal_map(state))
            except Exception:
                action = Action.fold()
        try:
            out = marshal.dumps(mem)
            if len(out) > 15000:
                mem["s"] = {}
                out = marshal.dumps(mem)
        except Exception:
            out = memory if isinstance(memory, bytes) else b""
        return action, out
