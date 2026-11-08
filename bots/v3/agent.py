"""v3 bot (v2 + 50/50 reveal) for Bay Area (3 hole cards; at the flop discard 1, expose 1).

Layers (one file so packing/imports can't break):
  PLATFORM  act(): memory envelope, opponent stats from events, legality funnel, try/except.
  STRATEGY  decide(view) -> (kind, amount): preflop by 3-card percentile + equity tables,
            postflop by equity vs each villain's {exposed card + hidden card} range,
            narrowed by their betting this hand.
  ENGINE    tables_bayarea.json (build_tables.py), eval7 evaluation / Monte Carlo.
All strategy constants live in K for quick iteration between practice rounds.
Kit conventions (verified in sdk/engine table.py/holdem.py): Seat.stack excludes the street
bet, state.pot includes it, own actions are echoed in events, kinds are lowercase strings.
"""

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import gc
import json
import random
import time
from itertools import permutations

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action, GameState

# ================================================================ KNOBS
K = {
    "push_bb": 12.0,          # unopened: push/fold at or below this effective stack
    "open_w": {1: 0.40, 2: 0.33, 3: 0.27, 4: 0.23, 5: 0.21, 6: 0.20, 7: 0.20},
    "bb_raise_w": 0.12,       # BB option raise width
    "open_prior": 0.25,       # villain open width prior (6-8 handed)
    "shove_prior_short": 0.45,  # field shove width at <= 20bb
    "shove_prior_deep": 0.20,
    "value_3bet_e": 0.57,
    "call_R": 0.80,
    "fold_to_bet_prior": 0.45,
    "bluff_min_e": 0.45,      # bets below this equity need real per-seat fold equity
    "bluff_min_F": 0.50,
    "betfreq_prior": 0.40,
    "raisefreq_prior": 0.06,
    "post_iters": 300,
    "sel_iters": 200,
    "raise_value_e": 0.78,
    "raise_value_e_river": 0.84,
    "call_margin": 0.03,
    "bet_sizes": (0.33, 0.5, 0.75, 1.0),
    "reveal_random": True,
}

# ================================================================ ENGINE
RANKS = "23456789TJQKA"
SUITS = "shdc"
RANK = {r: i for i, r in enumerate(RANKS)}
DECK = [r + s for r in RANKS for s in SUITS]
CARD = {c: eval7.Card(c) for c in DECK}
_PERMS = [dict(zip(SUITS, p)) for p in permutations(SUITS)]
_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "tables_bayarea.json")) as _f:
    _T = json.load(_f)
WIDTHS = _T["widths"]
CLASSES = _T["classes"]
del _T
_ALL2 = [(a, b) for i, a in enumerate(DECK) for b in DECK[i + 1:]]
KEEP = ((0, 1, 2), (1, 0, 2), (2, 0, 1))  # (discard, keep_i, keep_j)
_RNG = random.Random(20261106)
_CLOCK = [0.0]  # perf_counter() at the start of the current act() call (per-call only)
DEADLINE_S = 0.00030
_PRE_CACHE: dict = {}


def _sk(c):
    return (RANK[c[0]], c[1])


def canon3(cards) -> str:
    best = None
    for m in _PERMS:
        s = "".join(sorted((c[0] + m[c[1]] for c in cards), key=_sk, reverse=True))
        if best is None or s < best:
            best = s
    return best


def pre_info(cards):
    """(pct, eqs) for 3 hole cards; pct = fraction of hands at least as strong."""
    key = "".join(sorted(cards))
    hit = _PRE_CACHE.get(key)
    if hit is not None:
        return hit
    v = CLASSES.get(canon3(cards))
    res = (v[0], v[1]) if v else (0.5, [0.5] * len(WIDTHS))
    if len(_PRE_CACHE) > 20000:
        _PRE_CACHE.clear()
    _PRE_CACHE[key] = res
    return res


def eq_at(eqs, w: float) -> float:
    w = min(1.0, max(WIDTHS[0], w))
    for i in range(1, len(WIDTHS)):
        if w <= WIDTHS[i]:
            a, b = WIDTHS[i - 1], WIDTHS[i]
            t = (w - a) / (b - a)
            return eqs[i - 1] * (1 - t) + eqs[i] * t
    return eqs[-1]


def _suit_counts(cards):
    d: dict = {}
    for c in cards:
        d[c[1]] = d.get(c[1], 0) + 1
    return d


def expose_index(keep, board) -> int:
    """0/1: which kept card to expose: not pairing board, not in flush draw, else lower."""
    a, b = keep
    br = {c[0] for c in board}
    pa, pb = a[0] in br, b[0] in br
    if pa != pb:
        return 1 if pa else 0
    sc = _suit_counts(list(keep) + list(board))
    fa, fb = sc[a[1]] >= 4, sc[b[1]] >= 4
    if fa != fb:
        return 1 if fa else 0
    return 0 if RANK[a[0]] <= RANK[b[0]] else 1


def select_choice(cards, board):
    """(discard, reveal) maximizing kept-pair equity vs a best-2-of-3-like range."""
    dead = set(cards) | set(board)
    bc = [CARD[c] for c in board]
    pool = [p for p in _RNG.sample(_ALL2, 150) if p[0] not in dead and p[1] not in dead]
    pool.sort(key=lambda p: eval7.evaluate([CARD[p[0]], CARD[p[1]]] + bc), reverse=True)
    rlist = [((CARD[a], CARD[b]), 1.0) for a, b in pool[: max(20, int(len(pool) * 0.6))]]
    best = None
    for d, i, j in KEEP:
        if best is not None and time.perf_counter() - _CLOCK[0] > DEADLINE_S + 0.0001:
            break
        e = eval7.py_hand_vs_range_monte_carlo([CARD[cards[i]], CARD[cards[j]]], rlist, bc,
                                               K["sel_iters"])
        if best is None or e > best[0]:
            best = (e, d, i, j)
    _, d, i, j = best
    # Handoff §6.4: reveal either kept card 50/50 (deterministic "lower card" is a tell).
    reveal = (i, j)[_RNG.randrange(2)] if K["reveal_random"] else \
        (i, j)[expose_index((cards[i], cards[j]), board)]
    return int(d), int(reveal)


def villain_range(exposed, dead, bc, keep_frac):
    ex = CARD[exposed]
    hs = [c for c in DECK if c not in dead]
    if keep_frac < 0.999 and len(hs) > 6:
        hs.sort(key=lambda h: eval7.evaluate([ex, CARD[h]] + bc), reverse=True)
        k = max(3, int(len(hs) * keep_frac))
        step = 6 if keep_frac > 0.2 else 25
        hs = hs[:k] + hs[k::step]
    return [((ex, CARD[h]), 1.0) for h in hs]


def random_range(dead, n=120):
    pool = [p for p in _RNG.sample(_ALL2, n + 40) if p[0] not in dead and p[1] not in dead]
    return [((CARD[a], CARD[b]), 1.0) for a, b in pool[:n]]


# ================================================================ PLATFORM: memory + stats
# Memory: {"v":2,"s":{seat:[hands,vpip,pfr,faced,folded,bets,betopp,raises,raiseopp]},
#          "h":{seat:[vpip,pfr,faced,folded,bets,betopp,raises,raiseopp]}, "st":street, "bo":int}
NSTAT = 9


def load_mem(memory: bytes) -> dict:
    try:
        d = json.loads(memory) if memory else None
        if isinstance(d, dict) and d.get("v") == 2 and isinstance(d.get("s"), dict):
            return d
    except Exception:
        pass
    return {"v": 2, "s": {}, "h": {}, "st": 0, "bo": 0, "bc": 0}


def _flush(mem):
    s = mem["s"]
    for seat, f in mem["h"].items():
        row = s.get(seat)
        if not isinstance(row, list) or len(row) != NSTAT:
            row = [0] * NSTAT
        row[0] += 1
        for i in range(8):
            row[i + 1] += int(f[i])
        s[seat] = row
    mem["h"] = {}


def update_stats(mem, events, me):
    h = mem["h"]
    for ev in events:
        k = ev.kind if isinstance(ev.kind, str) else str(getattr(ev.kind, "value", ev.kind))
        seat = ev.seat
        if k == "hand":
            _flush(mem)
            h = mem["h"]
            mem["st"] = 0
            mem["bo"] = 0
            mem["bc"] = 0
            continue
        if k == "board":
            mem["bc"] = int(mem.get("bc", 0)) + len(ev.cards)
            mem["st"] = 1 if mem["bc"] <= 3 else 2 if mem["bc"] == 4 else 3
            mem["bo"] = 0
            continue
        if seat is None or seat == me or k not in ("call", "raise", "fold", "check"):
            continue
        key = str(seat)
        f = h.get(key)
        if f is None:
            f = h[key] = [0] * 8
        st = mem.get("st", 0)
        if st == 0:
            if k in ("call", "raise"):
                f[0] = 1
            if k == "raise":
                f[1] = 1
            continue
        if mem.get("bo"):
            f[2] = 1  # faced a bet
            f[6] = 1  # raise opportunity
            if k == "fold":
                f[3] = 1
            if k == "raise":
                f[7] = 1
        else:
            f[5] = 1  # bet opportunity
            if k == "raise":
                f[4] = 1
        if k == "raise":
            mem["bo"] = 1
    for seat in list(mem["s"].keys())[20:]:
        del mem["s"][seat]


def _rate(row, num, den, prior, w=6.0):
    if not row:
        return prior
    return (row[num] + w * prior) / (row[den] + w)


def seat_stats(mem, seat):
    row = mem["s"].get(str(seat))
    if not isinstance(row, list) or len(row) != NSTAT:
        row = None
    return {
        "hands": row[0] if row else 0,
        "pfr": _rate(row, 2, 0, 0.22),
        "vpip": _rate(row, 1, 0, 0.35),
        "fold_to_bet": _rate(row, 4, 3, K["fold_to_bet_prior"]),
        "betfreq": _rate(row, 5, 6, K["betfreq_prior"]),
        "raisefreq": _rate(row, 7, 8, K["raisefreq_prior"]),
    }


# ================================================================ STRATEGY helpers
def _kind(ev):
    k = ev.kind
    return k if isinstance(k, str) else str(getattr(k, "value", k))


def walk_hand(state):
    """Per-hand facts from state.history: street actions, pre raises, bb seat, sizes."""
    pot = 0
    bc = 0
    street = 0
    bets: dict = {}
    maxbet = 0
    acts = []  # (street, seat, kind, size_ratio) kind in call/bet/raise/fold/check
    blinds = []
    for ev in state.history:
        k = _kind(ev)
        s = ev.seat
        amt = int(ev.amount or 0)
        if k == "board":
            bc += len(ev.cards)
            street = 1 if bc <= 3 else 2 if bc == 4 else 3
            bets = {}
            maxbet = 0
        elif k == "ante":
            pot += amt
        elif k == "blind":
            pot += amt
            bets[s] = bets.get(s, 0) + amt
            maxbet = max(maxbet, bets[s])
            blinds.append((s, amt))
        elif k == "call":
            pot += amt
            bets[s] = bets.get(s, 0) + amt
            acts.append((street, s, "call", 0.0))
        elif k == "raise":
            prev = bets.get(s, 0)
            ratio = (amt - maxbet) / max(1, pot + max(0, maxbet - prev))
            acts.append((street, s, "bet" if maxbet == 0 else "raise", ratio))
            pot += max(0, amt - prev)
            bets[s] = amt
            maxbet = max(maxbet, amt)
        elif k in ("fold", "check"):
            acts.append((street, s, k, 0.0))
    bb_seat = None
    if blinds:
        bb_seat = max(blinds, key=lambda x: x[1])[0] if len(blinds) > 1 else blinds[-1][0]
    return acts, bb_seat


def _seat_obj(state, seat):
    for s in state.seats:
        if s.seat == seat:
            return s
    return None


def _status(s):
    st = s.status
    return st if isinstance(st, str) else str(getattr(st, "value", st))


def players_behind(state, bb_seat):
    """Active seats after us up to and including the BB (preflop, unopened)."""
    order = [s.seat for s in state.seats]
    if state.seat not in order:
        return 1
    n = len(order)
    i = order.index(state.seat)
    if bb_seat is None or bb_seat == state.seat:
        return 0
    cnt = 0
    for step in range(1, n):
        s = state.seats[(i + step) % n]
        if _status(s) == "active" and s.stack > 0:
            cnt += 1
        if s.seat == bb_seat:
            break
    return cnt


def in_position(state):
    """Postflop: no active (non-all-in) opponent acts after us (order starts left of button)."""
    order = [s.seat for s in state.seats]
    n = len(order)
    if state.button not in order or state.seat not in order:
        return False
    b = order.index(state.button)
    live = [state.seats[(b + k) % n] for k in range(1, n + 1)]
    live = [s.seat for s in live if _status(s) == "active" and s.stack > 0 or s.seat == state.seat]
    return bool(live) and live[-1] == state.seat


def shove_width(bb):
    pts = ((1.5, 0.85), (3, 0.60), (5, 0.42), (8, 0.30), (10, 0.24), (13, 0.18), (16, 0.13),
           (20, 0.09), (30, 0.05))
    if bb <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if bb <= x1:
            return y0 + (y1 - y0) * (bb - x0) / (x1 - x0)
    return 0.04


# ================================================================ STRATEGY
def decide(state: GameState, mem: dict):
    """-> (kind, amount). kind in fold/check/call/raise/allin."""
    me = _seat_obj(state, state.seat)
    bb = max(1, int(state.blinds.big_blind))
    my_stack = int(me.stack) if me else 0
    my_bet = int(me.bet) if me else 0
    to_call = int(state.to_call)
    pot = int(state.pot)
    others = [s for s in state.seats if s.seat != state.seat and _status(s) in ("active", "all_in")]
    biggest = max([int(s.stack) + int(s.bet) for s in others] or [0])
    eff_bb = min(my_stack + my_bet, biggest) / bb
    acts, bb_seat = walk_hand(state)
    if not state.board:
        return preflop(state, mem, acts, bb_seat, bb, my_stack, my_bet, to_call, pot, eff_bb, others)
    return postflop(state, mem, acts, bb, my_stack, my_bet, to_call, pot, others)


def preflop(state, mem, acts, bb_seat, bb, my_stack, my_bet, to_call, pot, eff_bb, others):
    cards = tuple(state.cards)
    pct, eqs = pre_info(cards)
    raises = [a for a in acts if a[0] == 0 and a[2] in ("raise", "bet")]
    limpers = len({a[1] for a in acts if a[0] == 0 and a[2] == "call"}) if not raises else 0
    nplayers = 1 + len(others)
    if not raises:
        behind = players_behind(state, bb_seat)
        if eff_bb <= K["push_bb"] and limpers == 0:
            fac = {0: 2.5, 1: 2.5, 2: 1.8, 3: 1.4, 4: 1.2}.get(behind, 1.0)
            if pct <= min(0.9, shove_width(eff_bb) * fac * 1.6):
                return "allin", 0
            return "fold", 0
        if to_call == 0:  # BB option
            if pct <= K["bb_raise_w"]:
                return "raise", int((3.5 + limpers) * bb)
            return "check", 0
        w = K["open_w"].get(max(1, min(7, behind)), 0.14)
        if nplayers <= 3:
            w = max(w, 0.40)
        if limpers:
            if pct <= 0.55 * w:
                return "raise", int((3 + limpers) * bb)
            return "fold", 0
        if pct <= w:
            size = 2.2 if behind >= 3 else 2.5 if behind == 2 else 3.0
            if eff_bb < 25:
                size = 2.1
            return "raise", int(size * bb)
        return "fold", 0

    # Facing raise(s).
    last = raises[-1]
    raiser = last[1]
    rs = _seat_obj(state, raiser)
    raiser_allin = rs is not None and _status(rs) == "all_in"
    st = seat_stats(mem, raiser)
    n_r = len(raises)
    raiser_bb = ((int(rs.stack) + int(rs.bet)) / bb) if rs else 20
    if raiser_allin or (rs is not None and int(rs.stack) < 0.25 * int(rs.bet)):
        w = K["shove_prior_short"] if raiser_bb <= 20 else K["shove_prior_deep"]
        w = max(w, st["pfr"])
    elif n_r == 1:
        base = K["open_prior"] if nplayers >= 6 else 0.37 if nplayers >= 4 else 0.54 if nplayers == 3 else 0.71
        w = (base * 6 + st["pfr"] * st["hands"] * 1.2) / (6 + st["hands"])
    elif n_r == 2:
        w = 0.10
    else:
        w = 0.05
    e = eq_at(eqs, w)
    in_pot = len({a[1] for a in acts if a[0] == 0 and a[2] in ("call", "raise", "bet")}) - 1
    if in_pot > 0:
        e = e ** (1 + 0.7 * in_pot)
    odds = to_call / max(1, pot + to_call)
    committed = to_call >= 0.4 * my_stack or raiser_allin or eff_bb <= 25
    if committed:
        if e >= odds + 0.02:
            return ("call", 0) if raiser_allin or not state.can("raise") else ("allin", 0)
        return "fold", 0
    if e >= K["value_3bet_e"] + 0.03 * (n_r - 1) and e >= 0.5:
        cur = int(last[3] * 0 + max(int(s.bet) for s in state.seats))
        target = int(cur * (3.0 if in_position(state) else 3.5) + bb * max(0, in_pot))
        if target > 0.35 * (my_stack + my_bet):
            return "allin", 0
        return "raise", target
    if e * K["call_R"] >= odds and to_call <= 0.12 * my_stack:
        return "call", 0
    return "fold", 0


def postflop(state, mem, acts, bb, my_stack, my_bet, to_call, pot, others):
    cards = tuple(state.cards)
    board = tuple(state.board)
    bc = [CARD[c] for c in board]
    disc = state.variant.get("discarded", []) if isinstance(state.variant, dict) else []
    exposed_all = [c for s in state.seats for c in (s.shown_cards or ())]
    dead = set(cards) | set(board) | set(disc or []) | set(exposed_all)
    street = 1 if len(board) <= 3 else 2 if len(board) == 4 else 3
    sk = {1: 1.0, 2: 0.88, 3: 0.78}
    villains = [s for s in others if _status(s) in ("active", "all_in")]
    hand = [CARD[c] for c in cards]
    e = 1.0
    pre_aggr = None
    for a in acts:
        if a[0] == 0 and a[2] in ("raise", "bet"):
            pre_aggr = a[1]
    iters = K["post_iters"] if len(villains) <= 2 else 120
    done = 0
    for v in villains:
        if time.perf_counter() - _CLOCK[0] > DEADLINE_S:  # deadline: approximate the rest
            e *= (e ** (1.0 / max(1, done))) ** 1.0 if done else 0.5
            continue
        done += 1
        st = seat_stats(mem, v.seat)
        keep = 1.0
        for a in acts:
            if a[1] != v.seat or a[0] == 0:
                continue
            if a[2] == "bet":
                ka = min(1.0, max(0.25, 1.15 * st["betfreq"] + 0.1))
                size_k = 1.0 if a[3] < 0.45 else 0.8 if a[3] < 0.8 else 0.6 if a[3] < 1.5 else 0.5
                keep *= min(1.0, ka * size_k * sk[a[0]])
            elif a[2] == "raise":
                keep *= min(1.0, max(0.08, 1.3 * st["raisefreq"] + 0.05)) * sk[a[0]]
            elif a[2] == "call":
                keep *= min(1.0, max(0.35, 1 - st["fold_to_bet"] + 0.1))
        keep = max(0.06, keep)
        shown = [c for c in (v.shown_cards or ()) if c in CARD]
        if len(shown) >= 2:
            rl = [((CARD[shown[0]], CARD[shown[1]]), 1.0)]
        elif len(shown) == 1:
            rl = villain_range(shown[0], dead, bc, keep)
        else:
            rl = random_range(dead)
        if not rl:
            continue
        e *= eval7.py_hand_vs_range_monte_carlo(hand, rl, bc, iters)
    n_opp = max(1, len(villains))
    odds = to_call / max(1, pot + to_call)
    stack_total = my_stack + my_bet
    r = state.can("raise")
    if to_call > 0:
        committed = to_call >= 0.4 * my_stack or (my_stack - to_call) < 0.3 * (pot + to_call)
        if committed:
            if e >= odds + 0.03:
                return ("allin", 0) if e >= 0.6 and r else ("call", 0)
            return "fold", 0
        thr = (K["raise_value_e_river"] if street == 3 else K["raise_value_e"]) + 0.05 * (n_opp - 1)
        if e >= thr and r:
            cur = max(int(s.bet) for s in state.seats)
            target = int(cur + 0.85 * (pot + to_call))
            if target > 0.55 * stack_total:
                return "allin", 0
            return "raise", target
        R = 1.0 if street == 3 else 0.9
        margin = 0.02 if street == 3 else K["call_margin"]
        if e * R >= odds + margin:
            return "call", 0
        return "fold", 0
    # Not facing a bet.
    if not r:
        return "check", 0
    F = 1.0
    for v in villains:
        if _status(v) == "active" and v.stack > 0:
            F *= seat_stats(mem, v.seat)["fold_to_bet"]
    if street == 1 and pre_aggr == state.seat:
        F = min(0.97, F * 1.12)
    if my_stack <= 1.3 * pot and e >= 0.7:
        return "allin", 0
    R = 0.92 if in_position(state) else 0.82
    best_kind, best_amt, best_ev = "check", 0, e * R * pot
    for frac in K["bet_sizes"]:
        B = frac * pot
        if frac >= 1.0 and e < 0.55:
            continue
        if e < K["bluff_min_e"] and F < K["bluff_min_F"]:
            continue
        Fb = min(0.97, F * (0.85 + 0.45 * min(1.0, B / max(1, pot))))
        ec = e ** (1 + Fb + 0.5 * min(1.5, B / max(1, pot)))
        ev = Fb * pot + (1 - Fb) * (ec * (pot + 2 * B) - B)
        if ev > best_ev + 0.01 * pot:
            best_kind, best_amt, best_ev = "raise", int(B), ev
    return best_kind, best_amt


# ================================================================ PLATFORM: legality funnel
def funnel(state: GameState, kind: str, amount: int) -> Action:
    can = state.can
    if kind in ("raise", "allin"):
        r = can("raise")
        if r:
            amt = int(r.max_amount) if kind == "allin" else int(amount)
            amt = max(int(r.min_amount), min(int(r.max_amount), amt))
            return Action.raise_to(amt)
        kind = "call"
    if kind == "call":
        if can("call"):
            return Action.call()
        kind = "check"
    if kind == "check":
        if can("check"):
            return Action.check()
        kind = "fold"
    if kind == "fold":
        if can("check"):
            return Action.check()
        if can("fold"):
            return Action.fold()
    return passive(state)


def passive(state: GameState) -> Action:
    try:
        if state.phase == "select":
            return Action("select", cards=(2, 0))
        if state.can("check"):
            return Action.check()
        if state.can("fold"):
            return Action.fold()
        first = state.legal_actions[0]
        return Action(first.kind, int(first.min_amount))
    except Exception:
        return Action.fold()


def _select(state: GameState) -> Action:
    try:
        cards = tuple(state.cards)
        board = tuple(state.board)
        if len(cards) != 3 or len(set(cards)) != 3 or any(c not in CARD for c in cards + board) \
                or len(board) < 3:
            return Action("select", cards=(2, 0))
        d, rv = select_choice(cards, board)
        if d == rv or not (0 <= d < 3 and 0 <= rv < 3):
            return Action("select", cards=(2, 0))
        return Action("select", cards=(d, rv))
    except Exception:
        return Action("select", cards=(2, 0))


class Agent(poker_agent_sdk.Agent):
    def act(self, state: GameState, memory: bytes) -> tuple[Action, bytes]:
        _CLOCK[0] = time.perf_counter()
        try:
            mem = load_mem(memory)
            try:
                update_stats(mem, state.events, state.seat)
            except Exception:
                mem = load_mem(b"")
            if state.phase == "select":
                action = _select(state)
            elif state.phase != "betting":
                action = passive(state)
            else:
                try:
                    kind, amount = decide(state, mem)
                    action = funnel(state, kind, int(amount))
                except Exception:
                    action = passive(state)
            out = json.dumps(mem, separators=(",", ":")).encode()
            if len(out) > 12000:
                mem["s"] = {}
                out = json.dumps(mem, separators=(",", ":")).encode()
            return action, out
        except Exception:
            return passive(state), memory


# ================================================================ warm-up + GC
def _warm():
    from poker_agent_protocol.game import (BlindLevel, Event, LegalAction, Seat, TableConfig)
    cfg = TableConfig("w", 0, 3, "flop_discard_reveal", 2000, (BlindLevel(10, 20),), 20, 250,
                      (50, 30, 20), 1, 65536, 100)
    seats = (Seat(0, 1980, 20, "active", ("Kd",)), Seat(1, 1990, 10, "active", ("7c",)),
             Seat(2, 2000, 0, "active", ()))
    hist = (Event("hand", None, 1), Event("blind", 1, 10), Event("blind", 0, 20),
            Event("call", 1, 10))
    a = Agent()
    base = dict(events=hist, hand_number=1, seat=0, cards=("As", "Ks", "7d"), board=(), pot=40,
                to_call=0, legal_actions=(LegalAction("check"), LegalAction("raise", 40, 2000)),
                history=hist, seats=seats, button=2, blind_level=1, blinds=BlindLevel(10, 20),
                hands_until_next_level=19, players_remaining=3, bust_order=(), config=cfg)
    a.act(GameState(**base), b"")
    a.act(GameState(**{**base, "board": ("Ah", "8c", "2s"), "phase": "select",
                       "legal_actions": (LegalAction("select"),)}), b"")
    a.act(GameState(**{**base, "cards": ("As", "Ks"), "board": ("Ah", "8c", "2s"),
                       "variant": {"discarded": ["7d"]}}), b"")


try:
    _warm()
except Exception:
    pass
gc.collect()
gc.freeze()
gc.set_threshold(20000, 50, 100)
