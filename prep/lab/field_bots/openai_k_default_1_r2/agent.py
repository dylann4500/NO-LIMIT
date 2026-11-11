"""Range poker, opponent adaptation and tournament-aware risk, within a 1ms budget.

All mutable table information is serialized into the SDK's memory. The global
objects below are immutable card/range/equity lookup tables only.
"""
import bisect
import gc
import json
import math
import os
import pickle
import random
import time

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action


RANKS = "23456789TJQKA"
_CARDS = {r + s: eval7.Card(r + s) for r in RANKS for s in "cdhs"}
_INFO = {c: (RANKS.index(c[0]), "cdhs".index(c[1])) for c in _CARDS}
with open(os.path.join(os.path.dirname(__file__), "preflop.json")) as _f:
    _DATA = json.load(_f)
with open(os.path.join(os.path.dirname(__file__), "draws.bin"), "rb") as _f:
    _STRAIGHT_DRAWS = _f.read()
_FRACS = tuple(_DATA["fractions"])
_PCT = _DATA["percentile"]
_EQUITY = _DATA["equity"]
_RANDOM_EQ = _DATA["random_equity"]


def _class(a, b):
    ra, rb = _INFO[a][0], _INFO[b][0]
    if ra < rb:
        ra, rb = rb, ra
    return RANKS[ra] + RANKS[rb] + ("" if ra == rb else "s" if a[1] == b[1] else "o")


def _make_banks():
    rng = random.Random(793183)
    banks, native = [], []
    for rr in _DATA["ranges"]:
        bank = []
        for a, b in rr:
            ca, cb = _CARDS[a], _CARDS[b]
            ra, sa = _INFO[a]
            rb, sb = _INFO[b]
            mask = ca.mask | cb.mask
            bank.append(((ca, cb), mask, ra, rb, sa, sb))
        rng.shuffle(bank)
        banks.append(tuple(bank))
        native.append(tuple((c[0], 1.0) for c in bank[:256]))
    return tuple(banks), tuple(native)


_BANKS, _NATIVE = _make_banks()
del _DATA


def _kind(k):
    v = getattr(k, "value", k)
    return v.lower() if isinstance(v, str) else getattr(k, "name", str(k)).lower()


def _clamp(x, low, high):
    return max(low, min(high, x))


def _range_index(fraction):
    return min(len(_FRACS) - 1, max(0, bisect.bisect_left(_FRACS, fraction)))


def _pf_equity(key, fraction):
    i = bisect.bisect_left(_FRACS, fraction)
    eq = _EQUITY[key]
    if i <= 0:
        return eq[0]
    if i >= len(_FRACS):
        return eq[-1]
    w = (fraction - _FRACS[i - 1]) / (_FRACS[i] - _FRACS[i - 1])
    return eq[i - 1] * (1 - w) + eq[i] * w


def _new_player():
    # PF flags, raises, largest raise (BB), calls, street masks, bet sizes,
    # first raise ordinal (open/3-bet/4-bet), first call's raise ordinal.
    return [0, 0, 0, 0, [0, 0, 0], [0.0, 0.0, 0.0], 0, 0]


def _memory(state, blob):
    if blob:
        try:
            m = pickle.loads(blob)
            if m.get("v") != 3:
                m = None
        except Exception:
            m = None
    else:
        m = None
    if m is None:
        m = {"v": 3, "s": {}, "live": {}, "h": None}
        for s in state.seats:
            m["s"][s.seat] = [0] * 21
            m["live"][s.seat] = _kind(s.status) != "busted"
    stats = m["s"]
    h = m["h"]
    for e in state.events:
        k = _kind(e.kind)
        sid = e.seat
        if k == "hand":
            h = {"n": int(e.amount), "st": 0, "p": {}, "b": [], "pot": 0,
                 "bets": {}, "invest": {}, "mx": 0, "nr": 0, "last": None, "open": None,
                 "bb": None, "sb": None, "bl": 0}
            for seat, live in m["live"].items():
                if live:
                    stats.setdefault(seat, [0] * 21)[0] += 1
            continue
        if k == "stack":
            m["live"][sid] = bool(e.amount)
            continue
        if h is None:
            continue
        if k == "board":
            h["b"].extend(e.cards or ())
            h["st"] = len(h["b"]) - 2
            h["bets"] = {}
            h["mx"] = 0
            continue
        if k in ("win", "show"):
            if k == "show" and sid != state.seat and e.cards and len(e.cards) == 2:
                st = stats.setdefault(sid, [0] * 21)
                st[12] += 1
                st[13] += _PCT.get(_class(*e.cards), 0.5)
            continue
        if sid is None:
            continue
        st = stats.setdefault(sid, [0] * 21)
        p = h["p"].setdefault(sid, _new_player())
        street = h["st"]
        amount = int(e.amount or 0)
        if k in ("blind", "ante"):
            h["pot"] += amount
            h["invest"][sid] = h["invest"].get(sid, 0) + amount
            if k == "blind":
                h["bets"][sid] = h["bets"].get(sid, 0) + amount
                h["mx"] = max(h["mx"], h["bets"][sid])
                if h["bl"] == 0:
                    h["sb"] = sid
                else:
                    h["bb"] = sid
                h["bl"] += 1
            continue
        if k not in ("fold", "check", "call", "raise"):
            continue
        oldbet = h["bets"].get(sid, 0)
        facing = max(0, h["mx"] - oldbet)
        ratio = 0.0
        true_raise = k == "raise" and h["mx"] > 0
        if k == "raise":
            ratio = max(0, amount - h["mx"]) / max(1, h["pot"])
            h["pot"] += max(0, amount - oldbet)
            h["invest"][sid] = h["invest"].get(sid, 0) + max(0, amount - oldbet)
            h["bets"][sid] = amount
            h["mx"] = max(h["mx"], amount)
            h["last"] = sid
        elif k == "call":
            ratio = amount / max(1, h["pot"])
            h["pot"] += amount
            h["invest"][sid] = h["invest"].get(sid, 0) + amount
            h["bets"][sid] = oldbet + amount
        if street == 0:
            if facing > 0 and h["nr"] > 0:
                st[10] += 1
                st[9] += k == "fold"
            if k in ("call", "raise") and not p[0]:
                st[1] += 1
            if k == "raise":
                if not (p[0] & 2):
                    st[2] += 1
                st[14] += 1
                if p[1] == 0:
                    p[6] = h["nr"] + 1
                p[0] |= 2
                p[1] += 1
                p[2] = max(p[2], amount / max(1, state.blinds[1]))
                if h["nr"] == 0:
                    h["open"] = sid
                    ring = [s.seat for s in state.seats]
                    bbpos = ring.index(h["bb"]) if h["bb"] in ring else 1
                    rpos = (ring.index(sid) - bbpos - 1) % len(ring)
                    after = sum(bool(live) and (ring.index(other) - bbpos - 1) % len(ring) > rpos
                                for other, live in m["live"].items())
                    h["of"] = (0.75, 0.49, 0.39, 0.30, 0.25, 0.21, 0.18, 0.16)[min(7, after)]
                    if sum(m["live"].values()) == 2:
                        h["of"] = 0.86
                    elif h["sb"] == sid:
                        h["of"] = 0.60
                h["nr"] += 1
            elif k == "call":
                if p[3] == 0:
                    p[7] = h["nr"]
                p[0] |= 1
                p[3] += 1
            elif k == "fold":
                st[3] += 1
        else:
            street = min(2, street - 1)
            code = {"check": 1, "call": 2, "raise": 8 if true_raise else 4, "fold": 0}[k]
            p[4][street] |= code
            p[5][street] = max(p[5][street], ratio)
            if k == "raise":
                st[4] += 1
            elif k == "check":
                st[6] += 1
            elif k == "call":
                st[5] += 1
            elif k == "fold":
                st[7] += 1
            if facing > 0:
                st[11] += 1
                st[15 + street * 2] += 1
                st[16 + street * 2] += k == "fold"
    if h is None or h["n"] != state.hand_number:
        h = {"n": state.hand_number, "st": max(0, len(state.board) - 2), "p": {},
             "b": list(state.board), "pot": state.pot, "bets": {}, "invest": {}, "mx": 0,
             "nr": 0, "last": None, "open": None, "bb": None, "sb": None, "bl": 0}
    m["h"] = h
    return m


def _profile(st, hp=None):
    n = st[0]
    vpip = (3.0 + st[1]) / (10.0 + n)
    pfr = (2.0 + st[2]) / (10.0 + n)
    aggression = (2.0 + st[4]) / (4.0 + st[4] + st[6])
    fold = (2.0 + st[7]) / (5.0 + st[7] + st[5] + st[4] * 0.3)
    habitual = n >= 5 and pfr > 0.58 and (
        st[14] >= max(4, st[2] * 1.6) or (st[4] >= 6 and aggression > 0.88))
    clicking = hp is not None and hp[1] >= 3 and hp[2] <= hp[1] * 6 + 3
    maniac = habitual or clicking
    rock = n >= 7 and st[1] == 0 and st[4] == 0 and st[5] == 0
    if st[12] >= 2 and st[13] / st[12] > 0.65 and pfr > 0.35 and aggression > 0.75:
        maniac = True
    if maniac:
        aggression = max(aggression, 0.92)
        vpip = max(vpip, 0.85)
        pfr = max(pfr, 0.78)
        fold = min(fold, 0.13)
    if rock:
        fold = max(fold, 0.82)
    return vpip, pfr, aggression, fold, maniac, rock


def _prior_fraction(sid, m, default_open=0.23):
    p = m["h"]["p"].get(sid)
    st = m["s"].get(sid, [0] * 15)
    prof = _profile(st, p)
    if prof[4]:
        return 1.0
    if p and p[0] & 2:
        n = st[0]
        empirical = prof[1]
        if m["h"].get("open") == sid:
            default_open = m["h"].get("of", default_open)
            empirical = _clamp(empirical * default_open / 0.27, 0.025, 0.95)
        blend = min(0.85, n / 22.0)
        fraction = default_open * (1 - blend) + empirical * blend
        ordinal = p[6] if len(p) > 6 else 1
        if ordinal >= 2:
            fraction *= (0.30 if prof[1] < 0.35 else 0.45) if ordinal == 2 else 0.17
        if p[1] >= 2:
            fraction *= 0.33 if empirical < 0.4 else 0.7
        if p[2] > 0 and p[1] >= 3:
            fraction *= 0.5
        return _clamp(fraction, 0.025, 0.85)
    if p and p[0]:
        called_raise = p[7] if len(p) > 7 else 0
        if called_raise:
            return _clamp((prof[0] * 0.8 + 0.04) * (0.5 if called_raise >= 2 else 1), 0.08, 0.8)
        return _clamp(prof[0] * 1.4 + 0.08, 0.2, 0.95)
    return 1.0


def _fold_probability(st, street, prof):
    """Shrink table-local responses toward the observed field's street rates."""
    if prof[4]:
        return 0.08
    if prof[5]:
        return 0.95
    prior = (0.48, 0.54, 0.65)[street]
    if len(st) < 21:
        return prior
    faced, folded = st[15 + 2 * street:17 + 2 * street]
    return (prior * 7 + folded) / (7 + faced)


def _icm(stacks, hero, payouts):
    """Exact hero ICM: fast top-three expression, otherwise subset DP."""
    own = stacks[hero]
    if own <= 0:
        return 0.0
    others = [v for s, v in stacks.items() if s != hero and v > 0]
    n = len(others)
    total = own + sum(others)
    if not any(payouts[3:]):
        first = own / total
        second, third = 0.0, 0.0
        for i, si in enumerate(others):
            pfirst = si / total
            second += pfirst * own / (total - si)
            if len(payouts) > 2 and payouts[2]:
                for j, sj in enumerate(others):
                    if j != i:
                        third += pfirst * sj / (total - si) * own / (total - si - sj)
        return first * payouts[0] + second * (payouts[1] if len(payouts) > 1 else 0) + third * (payouts[2] if len(payouts) > 2 else 0)
    p = [0.0] * (1 << n)
    removed = [0.0] * (1 << n)
    p[0] = 1.0
    value = 0.0
    for mask in range(1 << n):
        if mask:
            bit = mask & -mask
            removed[mask] = removed[mask ^ bit] + others[bit.bit_length() - 1]
        rank = mask.bit_count()
        rem = total - removed[mask]
        if rank < len(payouts):
            value += p[mask] * own / rem * payouts[rank]
        if rank + 1 >= len(payouts):
            continue
        for j, stack in enumerate(others):
            if not mask & (1 << j):
                p[mask | (1 << j)] += p[mask] * stack / rem
    return value


def _call_threshold(state, me, opp, cost, pot):
    odds = cost / max(1, pot + cost)
    alive = [s for s in state.seats if _kind(s.status) != "busted"]
    configured_payouts = list(state.config.payouts or [50, 30, 20])
    if (len(alive) > 5 and any(configured_payouts[3:])) or cost < me.stack * 0.18 or opp is None:
        return odds
    stacks = {s.seat: float(s.stack) for s in alive}
    if opp.seat not in stacks:
        return odds
    # A short caller cannot win the side pot. Keep those chips in every ICM
    # scenario rather than accidentally treating a main-pot win as a table win.
    stacks[opp.seat] += max(0, state.pot - pot)
    payouts = configured_payouts[:len(alive)]
    folded = stacks.copy()
    folded[opp.seat] += pot
    won = stacks.copy()
    won[me.seat] += pot
    lost = stacks.copy()
    lost[me.seat] = max(0.0, lost[me.seat] - cost)
    lost[opp.seat] += pot + cost
    f, w, l = (_icm(x, me.seat, payouts) for x in (folded, won, lost))
    if w <= l + 1e-9:
        return odds
    return _clamp((f - l) / (w - l), odds, 0.995)


def _bubble(state, me, opponents):
    payouts = list(state.config.payouts or [50, 30, 20])
    paid = sum(p > 0 for p in payouts)
    n = state.players_remaining
    if paid == 0 or n <= 2:
        return 0.0
    covered = any(s.stack + s.bet > (me.stack + me.bet) * 1.02 for s in opponents)
    if not covered:
        return 0.008
    stacks = [s.stack + s.bet for s in state.seats if _kind(s.status) != "busted"]
    small = min(stacks) if stacks else me.stack
    relative = _clamp(1 - small / max(1, me.stack + me.bet), 0.0, 0.85)
    if n == paid + 1:
        return 0.035 + relative * 0.12
    if n == paid + 2:
        return 0.02 + relative * 0.045
    if n <= paid:
        return 0.012 + relative * 0.02
    return 0.01


def _eligible_pot(state, m, me, cost):
    if cost < me.stack or not cost:
        return max(1, state.pot)
    invested = m["h"].get("invest", {})
    ours = invested.get(me.seat, me.bet)
    cap = ours + cost
    eligible = ours + sum(min(v, cap) for s, v in invested.items() if s != me.seat)
    return max(1, min(state.pot, eligible))


def _locked_board(board):
    """All live hands tie on these boards; a raise can only win dead money."""
    if len(board) != 5:
        return False
    value = eval7.evaluate([_CARDS[c] for c in board])
    category = value >> 24
    top, kicker = (value >> 16) & 15, (value >> 12) & 15
    if category == 8 and top == 12:
        return True
    if category == 7 and kicker == (11 if top == 12 else 12):
        return True
    if category == 4 and top == 12:
        return max(sum(c[1] == suit for c in board) for suit in "cdhs") <= 2
    return False


def _draw(combo, board):
    """Whether a candidate has a real flush/straight draw on this street."""
    _, _, a, b, sa, sb = combo
    suits, straight = board
    return straight[a * 13 + b] or suits[sa] + 1 + (sa == sb) == 4 or suits[sb] + 1 + (sa == sb) == 4


def _posterior_eq(state, m, sid, hero, board, limit=160, rollouts=384):
    """Bayesian likelihood on up to three streets, then native equity."""
    hp = m["h"]["p"].get(sid, _new_player())
    prof = _profile(m["s"].get(sid, [0] * 15), hp)
    idx = _range_index(_prior_fraction(sid, m))
    history = hp[4]
    evidence = [i for i in range(min(3, len(board) - 2)) if history[i]]
    low_bank = state is not None and state.time_bank_ms < max(10, (state.config.time_bank_ms or 0) * 0.5)
    # Native evaluation incorporates checks, all three streets, and the much
    # stronger reraising ranges observed in round one. The old neural model was
    # trained on different likelihoods and must not be used with this model.
    if prof[4] or not evidence:
        rr = _NATIVE[idx]
        if len(board) == 5:
            eq = eval7.py_hand_vs_range_exact(hero, rr, board)
        else:
            eq = eval7.py_hand_vs_range_monte_carlo(hero, rr, board, rollouts)
        return float(eq)
    if low_bank:
        evidence = evidence[-1:]
        limit = min(limit, 48)
        rollouts = min(rollouts, 192)
    else:
        evidence = evidence[-3:]
        if state is not None:
            limit = min(limit, 128)
    dead = hero[0].mask | hero[1].mask
    for c in board:
        dead |= c.mask
    candidates = []
    for combo in _BANKS[idx]:
        if not combo[1] & dead:
            candidates.append(combo)
            if len(candidates) >= limit:
                break
    if not candidates:
        return 0.5
    weights = [1.0] * len(candidates)
    current_scores = None
    for street in evidence:
        streetboard = board[:3 + street]
        suits = [0, 0, 0, 0]
        rankmask = 0
        for c in streetboard:
            rank, suit = _INFO[str(c)]
            suits[suit] += 1
            rankmask |= 1 << rank
        info = (suits, _STRAIGHT_DRAWS[rankmask * 169:(rankmask + 1) * 169])
        scores = [eval7.evaluate(list(c[0]) + streetboard) for c in candidates]
        ordered = sorted(scores)
        code, size = history[street], hp[5][street]
        ag = prof[2]
        if code & 12:
            width = (0.22 + 0.65 * ag) * (1.0 - 0.18 * street)
            if size > 0.55:
                width /= 1.0 + 0.35 * (size - 0.55)
            if code & 8:
                width *= 0.20 if street == 0 else 0.15
            width = _clamp(width, 0.035, 0.92)
            bluff = 0.035 + 0.20 * ag ** 3
            if code & 8:
                bluff *= 0.18 if street == 0 else 0.08
        elif code & 2:
            width = _clamp(0.82 - size * 0.55 + (0.4 - prof[3]) * 0.3, 0.22, 0.9)
            bluff = 0.02
        else:
            # A free check by a frequent bettor caps their range. In round one
            # ignoring checks left prior callers implausibly strong forever.
            width = _clamp(0.25 + ag * 0.35, 0.25, 0.60)
            bluff = 0.85
        cutoff = ordered[min(len(ordered) - 1, int((1 - width) * len(ordered)))]
        soft = ordered[min(len(ordered) - 1, int(max(0, 0.7 - width) * len(ordered)))]
        for j, (combo, value) in enumerate(zip(candidates, scores)):
            if not code & 14:
                likelihood = (0.72 - 0.64 * ag) if value >= cutoff else 0.86
            elif value >= cutoff:
                likelihood = 0.88
            elif street < 2 and _draw(combo, info):
                likelihood = (0.24 if code & 8 else 0.65) if size < 0.8 else (0.14 if code & 8 else 0.4)
            elif value >= soft:
                likelihood = 0.045 if code & 8 else 0.24
            else:
                likelihood = bluff
            weights[j] *= likelihood
        if len(streetboard) == len(board):
            current_scores = scores
    total = sum(weights)
    if len(board) == 5:
        if current_scores is None:
            current_scores = [eval7.evaluate(list(c[0]) + board) for c in candidates]
        own = eval7.evaluate(hero + board)
        return sum(w * ((v < own) + 0.5 * (v == own))
                   for w, v in zip(weights, current_scores)) / total
    # Systematic resampling implements weights (eval7 itself ignores weights).
    rr = []
    particles = 40 if low_bank else 80
    step = total / particles
    threshold = step * 0.5
    cumulative = 0.0
    for c, w in zip(candidates, weights):
        cumulative += w
        while cumulative >= threshold and len(rr) < particles:
            rr.append((c[0], 1.0))
            threshold += step
    return float(eval7.py_hand_vs_range_monte_carlo(hero, rr, board, rollouts))


def _features(cards, board):
    hole = [_INFO[c] for c in cards]
    bi = [_INFO[c] for c in board]
    br = [r for r, s in bi]
    hs = [r for r, s in hole]
    top = max(br)
    cat = eval7.evaluate([_CARDS[c] for c in (*cards, *board)]) >> 24
    ownpair = hs[0] == hs[1] or any(r in br for r in hs)
    overpair = hs[0] == hs[1] and hs[0] > top
    toppair = top in hs and br.count(top) == 1
    true_two = cat == 2 and hs[0] != hs[1] and all(r in br for r in hs)
    sc = [0, 0, 0, 0]
    for r, s in bi:
        sc[s] += 1
    wet = max(sc) >= 2 or (max(br) - min(br) <= len(set(br)) + 1)
    outs, nutdraw = 0, False
    if len(board) < 5:
        for suit in range(4):
            ours = [r for r, s in hole if s == suit]
            if ours and sc[suit] + len(ours) == 4 and cat < 5:
                outs = 9
                missing = max(r for r in range(13) if (r, suit) not in bi)
                nutdraw = max(ours) >= missing
        rankset = set(br + hs)
        if 12 in rankset:
            rankset.add(-1)
        straightouts = set()
        for start in range(-1, 9):
            window = set(range(start, start + 5))
            if len(window & rankset) == 4 and len(window & set(br)) < 4:
                straightouts |= window - rankset
        sd = min(8, len(straightouts) * 4)
        outs += sd - (2 if sd and outs else 0)
    return cat, ownpair, overpair, toppair, true_two, wet, outs, nutdraw


def _preflop(state, m, me, opponents, legal, noise):
    bb = max(1, int(state.blinds[1]))
    stack = me.stack
    total = stack + me.bet
    cost = min(stack, max(0, state.to_call))
    pot = _eligible_pot(state, m, me, cost)
    h = m["h"]
    key = _class(*state.cards)
    pct = _PCT[key]
    pair = len(key) == 2
    suited = key.endswith("s")
    a, b = _INFO[state.cards[0]][0], _INFO[state.cards[1]][0]
    high, low = max(a, b), min(a, b)
    risk = _bubble(state, me, opponents)
    effective = min(total, max((s.stack + s.bet for s in opponents), default=total))
    depth = effective / bb
    live = [s.seat for s in state.seats if _kind(s.status) != "busted"]
    ring = [s.seat for s in state.seats]
    pos = {sid: (ring.index(sid) - ring.index(state.button)) % len(ring) for sid in live}
    pre_order = sorted(live, key=lambda sid: (pos[sid] - (pos.get(h["bb"], 2) + 1)) % len(ring))
    hero_order = pre_order.index(state.seat)
    later = sum(1 for s in opponents if _kind(s.status) == "active" and pre_order.index(s.seat) > hero_order)
    profiles = {s.seat: _profile(m["s"].get(s.seat, [0] * 15), h["p"].get(s.seat)) for s in opponents}
    rocks = sum(p[5] for p in profiles.values())
    # Opening ranges by players yet to act; short-handed play widens naturally.
    opens = [0.82, 0.58, 0.45, 0.34, 0.28, 0.23, 0.20, 0.18]
    open_fraction = opens[min(7, later)]
    if len(live) == 2:
        open_fraction = 0.92
    if h["sb"] == state.seat and len(live) > 2:
        open_fraction = 0.60
    open_fraction += 0.07 * rocks
    open_fraction -= risk * 0.7
    if opponents and rocks == len(opponents):
        open_fraction = 1.01
    limpers = sum(1 for sid, p in h["p"].items() if sid != state.seat and p[0] & 1)
    if h["nr"] == 0:
        if depth <= 11.5 and "raise" in legal:
            shove_fraction = open_fraction * (0.72 if depth > 8 else 0.92 if depth > 5 else 1.2)
            if pct < min(0.95, shove_fraction) and (later <= 2 or pct < 0.22):
                return "raise", total
        if pct < open_fraction and "raise" in legal:
            if limpers:
                isolation = min(open_fraction, 0.23 + 0.025 * rocks)
                if pct > isolation and (pair or suited):
                    return ("call", 0) if cost else ("check", 0)
                if pct > isolation:
                    return ("call", 0) if pct < 0.34 and cost <= bb and later <= 1 else (("fold", 0) if cost else ("check", 0))
            size = (2.15 if depth > 18 else 2.0) * bb
            if limpers:
                size = (3.0 + 0.8 * limpers) * bb
            if rocks == len(opponents):
                size = 2 * bb
            if size > effective * 0.32 and pct < 0.17:
                size = total
            return "raise", int(size)
        if not cost:
            return "check", 0
        if limpers and depth > 15 and cost <= bb:
            if pair or (suited and high >= 7 and high - low <= 3) or (suited and high == 12):
                return "call", 0
        # Complete the small blind with reasonable connected/suited hands.
        if cost <= 0.5 * bb and later == 1 and pct < 0.76 and depth > 8:
            return "call", 0
        return "fold", 0
    raiser = next((s for s in opponents if s.seat == h["last"]), None)
    if raiser is None:
        raiser = max(opponents, key=lambda s: s.bet, default=None)
    if raiser is None:
        return ("check", 0) if not cost else ("call", 0)
    prof = profiles[raiser.seat]
    fraction = _prior_fraction(raiser.seat, m, 0.24 if later <= 2 else 0.19)
    maxbet = max(s.bet for s in state.seats)
    short_open_shove = raiser.stack == 0 and maxbet <= 15 * bb and h["nr"] == 1
    if short_open_shove and not prof[4]:
        after_raiser = len(live) - pre_order.index(raiser.seat) - 1
        pushwidth = opens[min(7, after_raiser)] * _clamp(1.30 - maxbet / bb * 0.035, .65, 1.2)
        if len(live) == 2:
            pushwidth = 0.75 - maxbet / bb * 0.012
        observed = m["s"].get(raiser.seat, [0] * 15)
        if observed[0] >= 12 and prof[1] < 0.12:
            pushwidth *= 0.6
        fraction = max(fraction, pushwidth)
    elif maxbet > 5 * bb and not prof[4]:
        # Unusual opens and jams have stronger priors than a normal open.
        fraction *= _clamp(1.1 - math.log(maxbet / bb) * 0.14, 0.4, 1.0)
    fraction = max(0.025, fraction)
    eq = _pf_equity(key, fraction)
    committed = sum(1 for s in opponents if s.bet >= maxbet * 0.8 and s.seat != raiser.seat)
    callers = sum(1 for s in opponents if h["p"].get(s.seat, [0])[0] and s.seat != raiser.seat)
    if committed:
        eq2 = _pf_equity(key, min(1.0, fraction * 1.5))
        product = eq * eq2 ** committed
        correlated = min(eq, eq2) ** (1 + 0.65 * committed)
        eq = 0.6 * product + 0.4 * correlated
    threshold = _call_threshold(state, me, raiser, cost, pot)
    allin = raiser.stack == 0 or cost >= stack * 0.8
    if prof[4]:
        if "raise" in legal and eq >= 0.565 + risk + max(0, later - 1) * 0.009:
            return "raise", total
        if allin:
            return ("call", 0) if eq >= threshold + 0.012 else ("fold", 0)
        if "raise" in legal and depth <= 15 and eq > 0.52 + risk:
            return "raise", total
    premium = eq >= ((0.59 if h["nr"] == 1 else 0.615) + risk * 0.7) and pct < (0.105 if not prof[4] else 0.28)
    if "raise" in legal and premium:
        size = maxbet * (2.8 if later == 0 else 3.25) + callers * maxbet * 0.6
        if size >= effective * 0.32 or depth < 18:
            size = total
        return "raise", int(size)
    # Low-frequency blocker 3-bets when the original raise can still fold.
    own_p = h["p"].get(state.seat, _new_player())
    if ("raise" in legal and h["nr"] == 1 and not own_p[1] and depth > 28 and
            later <= 1 and fraction >= 0.22 and not prof[4] and risk < 0.06 and
            suited and high == 12 and low in (2, 3, 4) and noise < 0.22):
        return "raise", int(maxbet * 3.0)
    if not cost:
        return "check", 0
    if allin:
        return ("call", 0) if eq >= threshold + 0.012 else ("fold", 0)
    realization = 0.91 if later == 0 else 0.81
    if pair:
        realization += 0.07
    if suited:
        realization += 0.05
    if high == 12 and low < 7 and not suited:
        realization -= 0.08
    if cost < 0.06 * stack and depth > 25 and (pair or (suited and high - low <= 2)):
        realization += 0.08
    # Expensive cold calls out of position suffer reverse implied odds.
    extra = risk * min(1.0, cost / max(1, stack) * 4) + 0.015 + later * 0.008
    if cost > 0.22 * stack:
        extra += 0.035
    if eq * min(1.06, realization) > threshold + extra:
        if cost >= 0.30 * stack and "raise" in legal and eq > 0.53 + risk and pct < 0.13:
            return "raise", total
        return "call", 0
    return "fold", 0


def _postflop(state, m, me, opponents, legal, noise, deadline):
    cost = min(me.stack, max(0, state.to_call))
    pot = _eligible_pot(state, m, me, cost)
    bb = max(1, state.blinds[1])
    hero = [_CARDS[c] for c in state.cards]
    board = [_CARDS[c] for c in state.board]
    street = len(board) - 3
    h = m["h"]
    profiles = {s.seat: _profile(m["s"].get(s.seat, [0] * 15), h["p"].get(s.seat)) for s in opponents}
    can_contest = [s for s in opponents if s.stack > 0 and _kind(s.status) == "active"]
    if not opponents:
        return ("check", 0) if not cost else ("call", 0)
    if not cost and ("raise" not in legal or not can_contest):
        return "check", 0
    all_rocks = bool(can_contest) and all(profiles[s.seat][5] for s in can_contest)
    if not cost and all_rocks and "raise" in legal:
        return "raise", int(me.bet + max(bb, pot * 0.30))
    cat, made, overpair, toppair, true_two, wet, outs, nutdraw = _features(state.cards, state.board)
    # Prioritize the bettor, then opponents whose action most narrows a range.
    def priority(s):
        p = h["p"].get(s.seat, _new_player())
        return (100 if cost and s.bet == max(x.bet for x in opponents) else 0) + sum(
            4 if x & 8 else 2 if x & 4 else 1 if x & 2 else 0 for x in p[4]) - 3 * profiles[s.seat][4]
    ranked = sorted(opponents, key=priority, reverse=True)
    keyopp = ranked[0]
    eq = _posterior_eq(state, m, keyopp.seat, hero, board, 160 if street == 2 else 104)
    n = len(opponents)
    if n > 1:
        eq2 = _posterior_eq(state, m, ranked[1].seat, hero, board, 64)
        prod = eq * eq2 ** (n - 1)
        correlated = min(eq, eq2) ** (1.0 + 0.65 * (n - 1))
        eq = 0.72 * prod + 0.28 * correlated
    if n > 1 and outs >= 8 and cat < 4 and street < 2:
        hit = 1 - (1 - outs / 47.0) * (1 - outs / 46.0) if street == 0 else outs / 46.0
        drawfloor = hit * (0.80 if nutdraw else 0.52) / (1 + 0.07 * (n - 2))
        eq = max(eq, drawfloor)
    prof = profiles[keyopp.seat]
    risk = _bubble(state, me, opponents)
    total = me.stack + me.bet
    effective = min(me.stack, max((s.stack for s in opponents), default=me.stack))
    station = any(profiles[s.seat][4] or profiles[s.seat][3] < 0.2 for s in can_contest)
    ring = [s.seat for s in state.seats]
    btn = ring.index(state.button)
    order = {sid: (ring.index(sid) - btn - 1) % len(ring) for sid in ring}
    in_position = all(order[state.seat] > order[s.seat] for s in can_contest)
    # Exclude pots we cannot win when short-stacked into a large side pot.
    if cost:
        threshold = _call_threshold(state, me, keyopp, cost, pot)
        future_tax = (0.018 if street == 0 else 0.008 if street == 1 else 0.0)
        if cost >= me.stack * 0.8 or not can_contest:
            future_tax = 0.0
        if not in_position and street < 2 and cost < me.stack * 0.5:
            future_tax += 0.012
        threshold += future_tax + 0.008 * (n - 1)
        if eq < threshold:
            return "fold", 0
        if "raise" in legal:
            strong = cat >= 3 or true_two or (overpair and street == 0 and n == 1)
            required = (0.72 if street == 0 else 0.77 if street == 1 else 0.83) + risk * 0.65
            if prof[4]:
                required -= 0.10
            if strong and eq > required:
                size = me.bet + cost + (pot + cost) * (0.72 if wet else 0.60)
                if size - me.bet >= effective * 0.55 or effective < 1.5 * (pot + cost):
                    size = total
                return "raise", int(size)
            # Semibluff only with strong draws and a credible chance of folds.
            if (street < 2 and outs >= 12 and n == 1 and prof[3] > 0.32 and
                    risk < 0.06 and eq > 0.41 and cost < pot * 0.45 and noise < 0.35):
                size = me.bet + cost + 0.8 * (pot + cost)
                return "raise", int(total if size > effective * 0.5 else size)
        return "call", 0
    if "raise" not in legal or not can_contest:
        return "check", 0
    if all_rocks:
        return "raise", int(me.bet + max(bb, pot * 0.30))
    strong = made and (cat >= 3 or true_two or overpair or toppair)
    value_threshold = (0.60 if n == 1 else 0.64) + risk * 0.25
    if street == 2:
        value_threshold += 0.04
    if eq > value_threshold and (made or cat >= 4):
        if cat >= 3 or true_two:
            fraction = 0.72 if wet else 0.63
            if station:
                fraction = 0.90
        elif strong:
            fraction = 0.62 if wet else 0.43
        else:
            fraction = 0.38
        if street == 2:
            fraction = 0.72 if eq > 0.85 else 0.48
        size = me.bet + max(bb, int(pot * fraction))
        if eq > 0.76 and (effective < pot * 1.25 or size - me.bet > effective * 0.60):
            size = total
        return "raise", int(size)
    # Build a coherent bluffing range: range advantage, draws and blockers.
    if not station and n <= 2 and risk < 0.09:
        own_p = h["p"].get(state.seat, _new_player())
        pfa = h["last"] == state.seat if not any(p[4][0] & 12 for p in h["p"].values()) else own_p[1] > 0
        highboard = max(_INFO[c][0] for c in state.board) >= 10
        foldchance = math.prod(_fold_probability(m["s"].get(s.seat, (0,) * 21), street, profiles[s.seat]) for s in can_contest)
        if street == 0:
            chance = 0.0
            if pfa and (highboard or not wet) and n == 1:
                chance = 0.85 if in_position else 0.58
            if outs >= 8:
                chance = max(chance, 0.8 if nutdraw else 0.55)
            if in_position and all(not h["p"].get(s.seat, _new_player())[4][0] & 14 for s in can_contest):
                chance = max(chance, 0.68)
            if noise < chance and (eq > 0.23 or foldchance > 0.5):
                return "raise", int(me.bet + max(bb, pot * (0.48 if wet else 0.33)))
        elif street == 1 and outs >= 8 and n == 1 and noise < 0.65 and prof[3] > 0.3:
            return "raise", int(me.bet + max(bb, pot * 0.60))
        elif (street == 1 and n == 1 and in_position and eq < 0.60 and foldchance > 0.47
              and not h["p"].get(keyopp.seat, _new_player())[4][street] & 14 and noise < 0.58):
            return "raise", int(me.bet + max(bb, pot * 0.45))
        elif street == 2 and n == 1 and eq < 0.32 and in_position:
            blocker = any(c[0] == "A" for c in state.cards)
            if noise < (0.82 if blocker else 0.67) and foldchance > 0.46:
                return "raise", int(me.bet + max(bb, pot * 0.52))
    return "check", 0


def _reserve_policy(state, legal, blob):
    """Tiny, bounded policy when little bank remains (also the no-bank upload).

    Keep the old memory unchanged: the emergency policy reads only accumulated
    opponent statistics, never a potentially outdated hand ledger. No rollouts,
    range filtering or ICM recursion run on this path.
    """
    try:
        stats = pickle.loads(blob).get("s", {}) if blob else {}
    except Exception:
        stats = {}
    me = next(s for s in state.seats if s.seat == state.seat)
    opps = [s for s in state.seats if s.seat != state.seat and _kind(s.status) in ("active", "all_in")]
    n = len(opps)
    if not n:
        return ("check", 0) if not state.to_call else ("call", 0)
    cost = min(me.stack, state.to_call)
    pot = max(1, state.pot)
    if cost == me.stack and cost:
        pot = max(1, pot - sum(max(0, s.bet - me.bet - cost) for s in opps))
    bb = max(1, state.blinds[1])
    profs = [_profile(stats.get(s.seat, (0,) * 15)) for s in opps]
    bettor_index = max(range(n), key=lambda i: opps[i].bet)
    prof = profs[bettor_index]
    all_rocks = all(p[5] for p in profs)
    risk = 0.06 if state.players_remaining in (4, 5) else 0.025
    if state.players_remaining <= 2:
        risk = 0.0
    total = me.stack + me.bet
    if _locked_board(state.board):
        return ("raise", int(legal["raise"].max_amount)) if "raise" in legal else (("call", 0) if cost else ("check", 0))
    if not state.board:
        key = _class(*state.cards)
        pct = _PCT[key]
        raises = sum(_kind(e.kind) == "raise" for e in state.history)
        depth = total / bb
        if not raises and cost <= bb:
            width = (0.90 if n == 1 else 0.40 if n == 2 else 0.28 if n <= 4 else 0.19)
            if all_rocks:
                width = 1.01
            if pct < width and "raise" in legal:
                return "raise", int(total if depth < 11 else 2.1 * bb)
            return ("check", 0) if not cost else ("fold", 0)
        fraction = 1.0 if prof[4] else max(0.06, min(0.45, prof[1] * 1.2))
        if raises >= 2 and not prof[4]:
            fraction *= 0.35
        eq = _pf_equity(key, fraction)
        if prof[4] and eq > 0.59 + risk and "raise" in legal:
            return "raise", total
        if pct < 0.045 and eq > 0.57 + risk and "raise" in legal:
            return "raise", int(total if depth < 22 or raises >= 2 else max(bb * 5, (me.bet + cost) * 3.0))
        odds = cost / max(1, pot + cost)
        eq *= 1.0 if cost >= me.stack else 0.88
        return ("call", 0) if cost and eq >= odds + risk + 0.025 else (("check", 0) if not cost else ("fold", 0))
    if not cost and ("raise" not in legal or not any(s.stack for s in opps)):
        return "check", 0
    if all_rocks and not cost:
        return "raise", int(me.bet + max(bb, pot * 0.3))
    street = len(state.board) - 3
    cat, made, overpair, top, two, wet, outs, nut = _features(state.cards, state.board)
    if cat >= 6:
        eq = 0.98
    elif cat == 5:
        eq = 0.93
    elif cat == 4:
        eq = 0.91 - 0.04 * street
    elif cat == 3:
        eq = 0.93 - 0.05 * street
    elif two:
        eq = 0.88 - 0.055 * street
    elif overpair:
        eq = 0.82 - 0.06 * street
    elif top:
        eq = 0.72 - 0.055 * street
    elif made:
        eq = 0.43 - 0.07 * street
    else:
        eq = (0.20 if any(c[0] == "A" for c in state.cards) else 0.12) * (1 - 0.35 * street)
    if len(state.board) == 5:
        value = eval7.evaluate([_CARDS[c] for c in (*state.cards, *state.board)])
        boardvalue = eval7.evaluate([_CARDS[c] for c in state.board])
        if value == boardvalue:
            eq = 0.30
        elif boardvalue >> 24 >= 3:
            eq = min(eq, 0.72)
        if cost and not prof[4] and cat == 5:
            suit = max("cdhs", key=lambda s: sum(c[1] == s for c in state.board))
            suited_board = [_INFO[c][0] for c in state.board if c[1] == suit]
            ours = [_INFO[c][0] for c in state.cards if c[1] == suit]
            if len(suited_board) >= 4 and ours:
                lower = sum(r < max(ours) and r not in suited_board and r not in ours for r in range(13))
                missing = max(1, 13 - len(suited_board) - len(ours))
                eq = min(eq, 0.12 + 0.82 * lower / missing)
    if street < 2:
        hit = 1 - (1 - outs / 47) * (1 - outs / 46) if street == 0 else outs / 46
        eq = max(eq, hit * (0.9 if nut else 0.68))
    if cost and not prof[4]:
        ratio = cost / max(1, pot - cost)
        eq -= 0.06 + 0.035 * street + min(0.12, max(0, ratio - 0.5) * 0.12)
    eq = _clamp(eq, 0.0, 1.0)
    if n > 1:
        eq **= 1 + 0.65 * (n - 1)
    if cost:
        if eq < cost / max(1, pot + cost) + risk:
            return "fold", 0
        if cat >= 3 and made and eq > 0.80 + risk and "raise" in legal:
            size = me.bet + cost + (pot + cost) * .7
            return "raise", int(total if size > me.stack * .6 else size)
        return "call", 0
    if "raise" in legal and eq > 0.64 and (made or cat >= 4):
        return "raise", int(me.bet + max(bb, pot * .60))
    return "check", 0


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        # Our decision objects are acyclic and refcounted. Avoid an unrelated
        # process-wide cyclic collection being charged to this tiny time slot;
        # restore the caller's GC setting before returning.
        enabled = gc.isenabled()
        if enabled:
            gc.disable()
        try:
            return self._decide(state, memory)
        finally:
            if enabled:
                gc.enable()

    def _decide(self, state, memory):
        deadline = time.perf_counter_ns() + 330000
        legal = {_kind(a.kind): a for a in state.legal_actions}
        bank_cap = state.config.time_bank_ms or 0
        reserve = bank_cap == 0 or state.time_bank_ms < min(65, bank_cap * 0.65)
        m = None if reserve else _memory(state, memory)
        # Stable, table-local mixing; independent of which worker handles a turn.
        x = (int(state.hand_number) * 2654435761 + int(state.seat) * 2246822519 +
             sum(_CARDS[c].mask for c in state.cards) * 3266489917 + len(state.history) * 668265263)
        x ^= x >> 17
        noise = (x & 65535) / 65536.0
        if reserve or time.perf_counter_ns() > deadline:
            kind, amount = _reserve_policy(state, legal, memory)
        elif _locked_board(state.board):
            kind = "raise" if "raise" in legal else "check" if "check" in legal else "call"
            amount = int(legal["raise"].max_amount) if "raise" in legal else 0
        elif len(state.board) == 0:
            me = next(s for s in state.seats if s.seat == state.seat)
            opponents = [s for s in state.seats if s.seat != state.seat and _kind(s.status) in ("active", "all_in")]
            kind, amount = _preflop(state, m, me, opponents, legal, noise)
        else:
            me = next(s for s in state.seats if s.seat == state.seat)
            opponents = [s for s in state.seats if s.seat != state.seat and _kind(s.status) in ("active", "all_in")]
            kind, amount = _postflop(state, m, me, opponents, legal, noise, deadline)
        if kind not in legal:
            kind = "check" if "check" in legal else "call" if kind == "raise" and "call" in legal else "fold"
        if kind not in legal:
            kind = next(iter(legal))
        if kind == "raise":
            offered = legal[kind]
            amount = max(int(offered.min_amount), min(int(offered.max_amount), int(amount)))
            action = Action.raise_to(amount)
        elif kind == "call":
            action = Action.call()
        elif kind == "check":
            action = Action.check()
        else:
            action = Action.fold()
        return action, memory if reserve else pickle.dumps(m, protocol=4)
