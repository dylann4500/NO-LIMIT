"""Tournament hold'em: fast range equity, table-local reads, legal action adapter."""
import bisect
import gc
import itertools
import json
import os
import random

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action


ACTION_NAMES = {Action.fold().kind: 'fold', Action.check().kind: 'check',
                Action.call().kind: 'call', Action.raise_to(1).kind: 'raise'}

with open(os.path.join(os.path.dirname(__file__), 'equity.json')) as _f:
    _DATA = json.load(_f)
PREFLOP = _DATA['hands']
FRACTIONS = _DATA['fractions']
RANKS = '23456789TJQKA'
DECK = tuple(eval7.Deck().cards)
CARDS = {str(c): c for c in DECK}
CONDITION_RANGES = True


def hand_code(a, b):
    hi, lo = max(a.rank, b.rank), min(a.rank, b.rank)
    return RANKS[hi] + RANKS[lo] + ('' if hi == lo else 's' if a.suit == b.suit else 'o')


# Immutable models are built before the process pool forks. No table state lives here.
_COMBOS = []
for _i, (_a, _b) in enumerate(itertools.combinations(DECK, 2)):
    _COMBOS.append((_a, _b, _a.rank, _b.rank, _a.suit, _b.suit,
                    (1 << _a.rank) | (1 << _b.rank), _i,
                    PREFLOP[hand_code(_a, _b)][0]))
_COMBOS.sort(key=lambda c: c[8])
BASE_RANGES, FAST_RANGES, SAMPLES = [], [], []
_rng = random.Random(192771)
for _fraction in FRACTIONS:
    _pool = [c for c in _COMBOS if c[8] <= _fraction + .005]
    _range = eval7.HandRange('AA')
    _range.hands = [((c[0], c[1]), 1.0) for c in _pool]
    BASE_RANGES.append(_range)
    SAMPLES.append(tuple(tuple(_rng.sample(_pool, min(128, len(_pool)))) for _ in range(8)))
    _fast = []
    for _sample in SAMPLES[-1]:
        _hr = eval7.HandRange('AA')
        _hr.hands = [((c[0], c[1]), 1.0) for c in _sample]
        _fast.append(_hr)
    FAST_RANGES.append(tuple(_fast))
CALL_FRACTIONS = []
for _i in range(len(FRACTIONS)):
    _entries = [(v[1][_i], 6 if len(k) == 2 else 4 if k[-1] == 's' else 12) for k, v in PREFLOP.items()]
    CALL_FRACTIONS.append(tuple(sum(w for e, w in _entries if e >= j / 200) / 1326 for j in range(201)))
STRAIGHT_MASKS = tuple(31 << i for i in range(9)) + ((1 << 12) | 15,)
DRAW_OUTS = [0] * 8192
for _mask in range(8192):
    _missing = 0
    for _straight in STRAIGHT_MASKS:
        _x = _straight & ~_mask
        if _x and _x & (_x - 1) == 0:
            _missing |= _x
    DRAW_OUTS[_mask] = _missing.bit_count()


def value(x):
    v = getattr(x, 'value', x)
    if isinstance(v, str):
        return v.lower()
    name = getattr(x, 'name', None)
    return name.lower() if name else v


def range_index(fraction):
    i = bisect.bisect_left(FRACTIONS, fraction)
    if i == len(FRACTIONS):
        return i - 1
    if i and fraction - FRACTIONS[i-1] < FRACTIONS[i] - fraction:
        i -= 1
    return i


def preflop_order(seats, button):
    ids = sorted(s.seat for s in seats)
    b = ids.index(button)
    clockwise = sorted((s.seat for s in seats if value(s.status) != 'busted'),
                       key=lambda s: (ids.index(s) - b - 1) % len(ids))
    if len(clockwise) == 2:
        return clockwise[-1:] + clockwise[:-1]
    return clockwise[2:] + clockwise[:2]


def pre_equity(code, fraction):
    vals = PREFLOP[code][1]
    i = bisect.bisect_left(FRACTIONS, fraction)
    if i == 0:
        return vals[0]
    if i == len(FRACTIONS):
        return vals[-1]
    t = (fraction - FRACTIONS[i-1]) / (FRACTIONS[i] - FRACTIONS[i-1])
    return vals[i-1] * (1-t) + vals[i] * t


def profile(row):
    # Hands, VPIP, PFR, postflop raises/calls/checks/folds, showdowns,
    # last VPIP hand, last PFR hand, latest public stack.
    h = row[0]
    vpip = (row[1] + 1.5) / (h + 5)
    pfr = (row[2] + 1.0) / (h + 6)
    a, c, k = row[3:6]
    aggression = (a + 2) / (a + c + k + 7)
    maniac = (h >= 3 and row[2] >= 3 and pfr > .43) or (a >= 6 and aggression > .72)
    nit = h >= 10 and row[1] == 0
    return vpip, pfr, aggression, maniac, nit


def update_memory(state, memory):
    if memory:
        try:
            m = json.loads(memory)
        except (ValueError, TypeError):
            m = {'p': {}, 'h': 0, 'b': len(state.board), 'a': [], 'r': 87123}
    else:
        m = {'p': {}, 'h': 0, 'b': 0, 'a': [], 'r': 87123}
    players = m['p']
    for s in state.seats:
        key = str(s.seat)
        if key not in players:
            players[key] = [0, 0, 0, 0, 0, 0, 0, 0, -1, -1, state.config.starting_stack or 2000]
    for e in state.events:
        kind = value(e.kind)
        if kind == 'hand':
            m['h'] = int(e.amount)
            m['b'] = 0
            m['a'] = []
            for row in players.values():
                if row[10] > 0:
                    row[0] += 1
            continue
        if kind == 'board':
            m['b'] += len(e.cards or [])
            continue
        key = str(e.seat)
        row = players.get(key)
        if row is None:
            continue
        if kind == 'stack':
            row[10] = int(e.amount)
        elif kind == 'show':
            row[7] += 1
        elif kind in ('raise', 'call', 'fold', 'check'):
            street = m['b']
            m['a'].append([street, e.seat, 'k' if kind == 'check' else kind[0], int(e.amount or 0)])
            if street == 0:
                if kind in ('raise', 'call') and row[8] != m['h']:
                    row[1] += 1
                    row[8] = m['h']
                if kind == 'raise' and row[9] != m['h']:
                    row[2] += 1
                    row[9] = m['h']
            elif kind == 'raise':
                row[3] += 1
            elif kind == 'call':
                row[4] += 1
            elif kind == 'check':
                row[5] += 1
            else:
                row[6] += 1
    # Portable table-local random stream; Agent instances can be freely interchanged.
    r = m['r']
    r ^= (r << 13) & 0xffffffff
    r ^= r >> 17
    r ^= (r << 5) & 0xffffffff
    m['r'] = r & 0xffffffff
    if len(m['a']) > 160:
        m['a'] = m['a'][:32] + m['a'][-96:]
    return m


def texture(board):
    ranks = [c.rank for c in board]
    suits = [0, 0, 0, 0]
    counts = [0] * 13
    mask = 0
    for c in board:
        suits[c.suit] += 1
        counts[c.rank] += 1
        mask |= 1 << c.rank
    unique = sorted(set(ranks), reverse=True)
    paired = max(counts) >= 2
    return counts, suits, mask, unique, paired


def made_tier(a, b, board, tex, score=None):
    counts, suits, mask, ranks, paired = tex
    if score is None:
        score = eval7.evaluate(board + [a, b])
    cat = score >> 24
    r1, r2 = a.rank, b.rank
    if cat >= 4:
        tier = 7
    elif cat == 3:
        tier = 6 if counts[r1] or counts[r2] or r1 == r2 else 1
    elif cat == 2:
        if not paired or (r1 == r2 and r1 > ranks[0]):
            tier = 5
        else:
            hits = [r for r in (r1, r2) if counts[r] == 1]
            tier = 4 if hits and max(hits) == ranks[0] else 2 if hits else 1
    elif cat == 1:
        if r1 == r2:
            tier = 4 if r1 > ranks[0] else 2 if len(ranks) > 1 and r1 > ranks[1] else 1
        else:
            hits = [r for r in (r1, r2) if counts[r] == 1]
            if not hits:
                tier = 0
            elif max(hits) == ranks[0]:
                kicker = r2 if r1 == ranks[0] else r1
                tier = 4 if kicker >= 9 else 3
            else:
                tier = 2 if len(ranks) > 1 and max(hits) == ranks[1] else 1
    else:
        tier = 0
    draw = 0
    if len(board) < 5:
        s1, s2 = a.suit, b.suit
        flush = (suits[s1] + 1 + (s1 == s2) == 4) or (s1 != s2 and suits[s2] + 1 == 4)
        straight = DRAW_OUTS[mask | (1 << r1) | (1 << r2)]
        draw = (8 if flush else 0) + min(8, 4 * straight)
    return tier, draw


def conditioned_range(index, board, cards, tex, strength, maniac, seed, quick=False):
    if not CONDITION_RANGES or strength <= 0 or maniac:
        return FAST_RANGES[index][seed & 7] if quick else BASE_RANGES[index]
    # A stratified, fixed-size support bounds latency even for a 100% preflop range.
    sample = SAMPLES[index][seed & 7]
    if quick and len(sample) > 64:
        sample = sample[::2]
    known = set(board + cards)
    if strength == 1:
        weights = (.22, .55, .76, .90, .98, 1., 1., 1.)
    elif strength == 2:
        weights = (.09, .20, .40, .72, .94, 1., 1., 1.)
    elif strength == 3:
        weights = (.045, .08, .16, .38, .67, .96, 1., 1.)
    else:
        weights = (.025, .025, .04, .12, .32, .70, .97, 1.)
    hands = []
    for c in sample:
        a, b = c[:2]
        if a in known or b in known:
            continue
        tier, draw = made_tier(a, b, board, tex)
        w = weights[tier]
        if draw and len(board) < 5:
            w = max(w, .70 if draw >= 8 else .30)
        # Deterministic thinning gives weights without allocating many duplicate combos.
        u = ((c[7] * 2654435761 + seed * 17431) & 65535) / 65536
        if u <= w:
            hands.append(((a, b), 1.0))
    if not hands:
        return BASE_RANGES[index]
    hr = object.__new__(eval7.HandRange)
    hr.hands = hands
    return hr


def risk_premium(state, me, opponents, cost):
    n = state.players_remaining
    if n <= 2:
        return 0.0
    payouts = state.config.payouts or [50, 30, 20]
    paid = sum(1 for p in payouts if p > 0)
    if paid <= 1:
        return 0.0
    own = me.stack + me.bet
    covered = max((s.stack + s.bet for s in opponents), default=0) >= own * .9
    pressure = .025
    if n == paid + 1:
        pressure = .115
    elif n <= paid:
        pressure = .065
    elif n == paid + 2:
        pressure = .055
    if not covered:
        pressure *= .45
    # Short stacks have less equity to protect and more urgency to gather chips.
    alive = [s.stack + s.bet for s in state.seats if value(s.status) != 'busted']
    if own < min((x for x in alive if x > own), default=own) * .55:
        pressure *= .7
    return pressure * min(1., cost / max(1, me.stack))


def icm_value(own, others, payouts):
    """Exact marginal ICM for up to three prizes; only O(players squared)."""
    others = [x for x in others if x > 0]
    n = len(others) + 1
    if own <= 0:
        return payouts[n-1] if n <= len(payouts) else 0.
    total = own + sum(others)
    if not others:
        return payouts[0]
    p1 = own / total
    p2 = p3 = 0.
    if len(payouts) > 1 and payouts[1]:
        for a in others:
            first = a / total
            rem = total - a
            p2 += first * own / rem
            if len(payouts) > 2 and payouts[2]:
                for b in others:
                    # Duplicate stack sizes are distinct opponents; avoid identity tests.
                    p3 += first * b / rem * own / (rem - b) if rem > b else 0.
                p3 -= first * a / rem * own / (rem - a) if rem > a else 0.
    result = payouts[0] * p1
    if len(payouts) > 1:
        result += payouts[1] * p2
    if len(payouts) > 2:
        result += payouts[2] * p3
    return result


def call_requirement(state, me, opponents, main, pot, cost, m=None):
    odds = cost / (pot + cost)
    if not cost or state.players_remaining <= 2:
        return odds
    payouts = state.config.payouts or [50, 30, 20]
    if cost < me.stack * .22 or any(p > 0 for p in payouts[3:]):
        return odds + risk_premium(state, me, opponents, cost)
    # Freeze uninvolved stacks and award the contested pot to the aggressor in
    # the losing/folding branches. Accurate for heads-up pots, conservative in
    # multiway pots. The whole current pot has already left these stacks.
    others = [s.stack for s in state.seats if s.seat not in (me.seat, main.seat) and value(s.status) != 'busted']
    uf = icm_value(me.stack, others + [main.stack + pot], payouts)
    ul = icm_value(me.stack - cost, others + [main.stack + pot + cost], payouts)
    uw = icm_value(me.stack + pot, others + [main.stack], payouts)
    if cost >= me.stack:
        # Other all-in players are still competing. Losing beside them pays by
        # starting-stack order, rather than automatically locking up second place.
        simultaneous = [s for s in state.seats if s.seat not in (me.seat, main.seat) and value(s.status) == 'all_in']
        if simultaneous:
            def initial(s):
                return m['p'][str(s.seat)][10] if m else s.stack + s.bet
            start = initial(me)
            bigger = sum(initial(s) > start for s in simultaneous)
            tied = 1 + sum(initial(s) == start for s in simultaneous)
            survivors = sum(s.seat != me.seat and (s.stack > 0 or s.seat == main.seat) and value(s.status) != 'busted' for s in state.seats)
            first = survivors + bigger
            ul = sum(payouts[i] if i < len(payouts) else 0. for i in range(first, first+tied)) / tied
    if uw <= ul:
        return 1.
    return max(odds, min(.98, (uf - ul) / (uw - ul)))


def equity_layers(state, m, me, opponents, cost, heads_up):
    """Equity in the pot we can win, splitting off short all-in side pots."""
    contributed = [(s, max(0, m['p'][str(s.seat)][10] - s.stack)) for s in state.seats]
    total = sum(x for s, x in contributed)
    pot = max(1, state.pot)
    if abs(total - pot) > max(3, pot * .015):
        # Recovery from a truncated memory, or a nonstandard forced-bet setting.
        n = len(opponents)
        return heads_up ** (n ** .78), pot
    hero_inv = next(x for s, x in contributed if s.seat == me.seat)
    cap = hero_inv + cost
    if cap <= 0:
        return heads_up ** (len(opponents) ** .78), pot
    levels = sorted(set(min(cap, x + (cost if s.seat == me.seat else 0)) for s, x in contributed))
    previous = 0
    equity_sum = 0.
    eligible = 0
    for level in levels:
        if level <= previous:
            continue
        funders = 0
        contenders = 0
        for s, x in contributed:
            x += cost if s.seat == me.seat else 0
            if x >= level:
                funders += 1
                if s.seat != me.seat and value(s.status) in ('active', 'all_in'):
                    contenders += 1
        chips = (level - previous) * funders
        equity_sum += chips * (heads_up ** (contenders ** .78) if contenders else 1.)
        eligible += chips
        previous = level
    if eligible <= cost:
        return heads_up, pot
    return equity_sum / eligible, eligible - cost


def jam_value(state, me, opponents, profiles, code, opening, pot, bb):
    """Chip EV of an open shove, including folds and a multi-caller penalty."""
    ri = range_index(max(.03, opening))
    no_call = 1.
    cases = []
    own = me.stack + me.bet
    for s in opponents:
        if value(s.status) != 'active':
            continue
        vpip, pfr, aggression, maniac, nit = profiles[s.seat]
        effective = min(own, s.stack + s.bet)
        call_cost = min(s.stack, max(0, effective - s.bet))
        our_risk = min(me.stack, max(0, effective - me.bet))
        required = call_cost / max(1, pot + our_risk + call_cost)
        if state.players_remaining > 2:
            required += risk_premium(state, s, [me], call_cost) * .70
        fraction = CALL_FRACTIONS[ri][min(200, max(0, int(required * 200)))]
        fraction *= min(1.3, .78 + vpip * .8)
        if maniac:
            fraction = .95
        elif nit:
            fraction = .02
        fraction = min(.98, max(.025, fraction))
        eq = pre_equity(code, fraction)
        eq = max(0., eq - risk_premium(state, me, [s], our_risk))
        ev = eq * (pot + call_cost) - (1-eq) * our_risk
        cases.append((fraction, ev, eq, our_risk, call_cost))
        no_call *= 1-fraction
    single_probability = 0.
    ev = no_call * pot
    for fraction, called_ev, eq, our_risk, call_cost in cases:
        p = no_call * fraction / (1-fraction)
        single_probability += p
        ev += p * called_ev
    multi = max(0., 1 - no_call - single_probability)
    if multi and cases:
        eq = sum(c[2] * c[0] for c in cases) / sum(c[0] for c in cases)
        eq **= 1.72
        risk = max(c[3] for c in cases)
        winnings = pot + 2 * sum(c[4] * c[0] for c in cases) / sum(c[0] for c in cases)
        ev += multi * (eq * winnings - (1-eq) * risk)
    return ev


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        # The decision allocates only acyclic data. Postpone cyclic collection to
        # the host between decisions, avoiding millisecond GC sweeps in our budget.
        collect = gc.isenabled()
        if collect:
            gc.disable()
        try:
            return self._act(state, memory)
        finally:
            if collect:
                gc.enable()

    def _act(self, state, memory):
        legal = {ACTION_NAMES.get(a.kind, value(a.kind)): a for a in state.legal_actions}
        m = update_memory(state, memory)
        kind, amount = self.decide(state, m, legal)
        if kind == 'raise' and 'raise' in legal:
            offer = legal['raise']
            amount = max(int(offer.min_amount), min(int(offer.max_amount), int(amount)))
            action = Action.raise_to(amount)
        elif kind == 'call' and 'call' in legal:
            action = Action.call()
        elif kind == 'fold' and 'fold' in legal:
            action = Action.fold()
        elif 'check' in legal:
            action = Action.check()
        elif 'fold' in legal:
            action = Action.fold()
        elif 'call' in legal:
            action = Action.call()
        elif 'raise' in legal:
            action = Action.raise_to(int(legal['raise'].min_amount))
        else:
            raise ValueError('No standard legal action was offered')
        data = json.dumps(m, separators=(',', ':')).encode()
        memory_limit = min(16000, state.config.memory_bytes or 65536)
        if len(data) > memory_limit:
            m['a'] = m['a'][:24] + m['a'][-24:]
            data = json.dumps(m, separators=(',', ':')).encode()
            if len(data) > memory_limit:
                data = b''
        return action, data

    def decide(self, state, m, legal):
        seat = state.seat
        me = next(s for s in state.seats if s.seat == seat)
        opponents = [s for s in state.seats if s.seat != seat and value(s.status) in ('active', 'all_in')]
        if not opponents:
            return 'check', 0
        cards = [CARDS[c] for c in state.cards]
        code = hand_code(*cards)
        bb = max(1, int(state.blinds[1]))
        cost = min(int(state.to_call), me.stack)
        pot = max(1, int(state.pot))
        own = me.stack + me.bet
        depth = own / bb
        maxbet = max(s.bet for s in state.seats)
        path = m['a']
        pre = [a for a in path if a[0] == 0]
        raises = [a for a in pre if a[2] == 'r']
        profiles = {s.seat: profile(m['p'][str(s.seat)]) for s in opponents}
        all_ids = sorted(s.seat for s in state.seats)
        nseats = len(all_ids)
        button_i = all_ids.index(state.button)
        seat_i = all_ids.index(seat)
        post_order = (seat_i - button_i - 1) % nseats
        in_position = all(post_order > (all_ids.index(s.seat) - button_i - 1) % nseats for s in opponents)
        rand = m['r'] / 4294967296
        if not state.board:
            return self.preflop(state, m, legal, cards, code, me, opponents, profiles,
                                pre, raises, bb, cost, pot, own, depth, maxbet,
                                in_position, rand)
        return self.postflop(state, m, legal, cards, me, opponents, profiles,
                             pre, raises, bb, cost, pot, own, in_position, rand)

    def preflop(self, state, m, legal, cards, code, me, opponents, profiles,
                pre, raises, bb, cost, pot, own, depth, maxbet,
                in_position, rand):
        rank = PREFLOP[code][0]
        pair = cards[0].rank == cards[1].rank
        suited = cards[0].suit == cards[1].suit
        n = len(opponents)
        order = {s: i for i, s in enumerate(preflop_order(state.seats, state.button))}
        my_order = order[state.seat]
        behind = sum(1 for s in opponents if value(s.status) == 'active' and
                     order[s.seat] > my_order)
        limps = sum(1 for a in pre if a[2] == 'c' and a[1] != state.seat)
        unopened = maxbet <= bb and not raises
        if unopened:
            if 'raise' not in legal:
                if not cost:
                    return 'check', 0
                eq, eligible = equity_layers(state, m, me, opponents, cost, pre_equity(code, 1.0))
                main = max(opponents, key=lambda s: s.bet)
                needed = call_requirement(state, me, opponents, main, eligible, cost, m)
                return ('call', 0) if eq > needed + .012 else ('fold', 0)
            if state.players_remaining == 2:
                opening = .78 if cost else .70
            else:
                opening = (.57, .50, .37, .28, .225, .19, .165, .15)[min(7, behind)]
            if limps:
                opening *= .78 ** min(2, limps)
            nit_count = sum(p[4] for p in profiles.values())
            if nit_count == n:
                opening = 1.0
            elif nit_count:
                opening = min(.90, opening * (1 + .22 * nit_count))
            if depth <= 14:
                # Short-stack aggression; wider late, tighter on the bubble.
                opening = min(.85, opening + max(0., 12-depth) * .014)
                opening -= risk_premium(state, me, opponents, me.stack) * .7
                if rank <= opening and 'raise' in legal:
                    if jam_value(state, me, opponents, profiles, code, opening, pot, bb) > .08 * bb:
                        return 'raise', own
            elif rank <= opening and 'raise' in legal:
                size = int((2.15 + .85 * limps + (.30 if not in_position else 0)) * bb)
                if size >= own * .36:
                    size = own
                return 'raise', size
            if cost == 0:
                return 'check', 0
            # Complete a discounted small blind behind limpers with useful implied odds.
            odds = cost / (pot + cost)
            if limps and cost <= .55 * bb and rank <= .72 and odds < .17:
                return 'call', 0
            return 'fold', 0

        aggressor = raises[-1][1] if raises else max(opponents, key=lambda s: s.bet).seat
        ag = next((s for s in opponents if s.seat == aggressor), opponents[0])
        prof = profiles[ag.seat]
        frac = self.pre_range(ag.seat, prof, pre, bb, ag.stack + ag.bet, state.players_remaining)
        equity = pre_equity(code, frac)
        # One other caller is meaningful; tiny all-in stacks should not freeze the action.
        others = [s for s in opponents if s.seat != ag.seat and
                  (s.bet >= maxbet * .7 or value(s.status) == 'all_in') and s.bet > bb]
        equity, eligible_pot = equity_layers(state, m, me, opponents, cost, equity)
        odds = cost / (pot + cost)
        required = call_requirement(state, me, opponents, ag, eligible_pot, cost, m)
        committed = cost >= me.stack * .65 or depth <= 7
        shove_edge = .54 + risk_premium(state, me, opponents, me.stack)
        if committed:
            if equity > required + .012:
                if equity > max(.63, shove_edge) and 'raise' in legal and me.stack <= pot * 1.4:
                    return 'raise', own
                return 'call', 0
            return 'fold', 0

        reraise = len(raises) >= 2
        effective = min(own, ag.stack + ag.bet)
        # Value first; a few blocker 3-bets keep steals from being free.
        value_raise = equity > (.67 if reraise else .615) and (rank < .08 or prof[3])
        if prof[3] and state.players_remaining > 3 and depth > 15:
            value_raise = equity > .80
        force_shove = n == 1 and prof[3] and effective <= 20 * bb and equity > max(.56, shove_edge)
        value_raise |= force_shove
        if n > 2 and others:
            value_raise = equity > .69
        bluff = (not reraise and not prof[3] and frac >= .20 and in_position and
                 effective > 35 * bb and maxbet <= 4 * bb and suited and
                 max(c.rank for c in cards) == 12 and rank < .43 and rand < .13)
        if (value_raise or bluff) and 'raise' in legal:
            size = int(maxbet * (3.0 if in_position else 3.6) + len(others) * maxbet)
            if force_shove or effective <= max(20 * bb, maxbet * 5) or size >= own * .36:
                size = own
            if size != own or equity > shove_edge:
                return 'raise', size

        realization = .88 if in_position else .77
        if pair or suited:
            realization += .06
        if prof[3]:
            realization = .99
        if effective < 18 * bb:
            realization = max(realization, .94)
        future_cost = .025 if cost > 1.5 * bb else .005
        if reraise and not prof[3]:
            future_cost += .025
        if equity * realization > required + future_cost:
            # Avoid defending disconnected trash just because a deep open offers good odds.
            if rank < .70 or cost <= bb or prof[3] or odds < .16:
                return 'call', 0
        if pair and effective >= 16 * cost and len(raises) <= 2 and cost < .10 * own:
            return 'call', 0
        return ('check', 0) if not cost else ('fold', 0)

    @staticmethod
    def pre_range(seat, prof, pre, bb, stack, players=8):
        vpip, pfr, aggression, maniac, nit = prof
        raises = [a for a in pre if a[2] == 'r']
        ownraises = [a for a in raises if a[1] == seat]
        if len(ownraises) >= 3:
            maniac = True
        called = any(a[1] == seat and a[2] == 'c' for a in pre)
        if maniac:
            return min(1., max(.65, pfr * 1.3)) if ownraises else min(1., max(.65, vpip * 1.2))
        if ownraises:
            index = next(i for i, a in enumerate(raises) if a is ownraises[-1])
            if index >= 2:
                return max(.03, min(.09, pfr * .23))
            if index == 1:
                return max(.04, min(.14, pfr * .32))
            before = pre[:pre.index(ownraises[0])]
            left = max(1, players - sum(a[2] == 'f' for a in before) - 1)
            base = .78 if players == 2 else (.50, .37, .28, .225, .19, .165, .15)[min(6, left-1)]
            frac = max(.05, min(.85, base * (pfr / .18) ** .65))
            total = ownraises[-1][3]
            if total > 8 * bb and stack > 25 * bb:
                frac = min(frac, .07)
            elif total > 5 * bb and stack <= 20 * bb:
                frac = min(.45, max(frac, .20))
            return frac
        if called:
            return min(.85, max(.16, vpip * 1.10))
        return 1.0

    def postflop(self, state, m, legal, cards, me, opponents, profiles,
                 pre, raises, bb, cost, pot, own, in_position, rand):
        board = [CARDS[c] for c in state.board]
        street = len(board)
        tex = texture(board)
        hero_score = eval7.evaluate(cards + board)
        tier, draw = made_tier(*cards, board, tex, hero_score)
        now = [a for a in m['a'] if a[0] == street]
        bets = [a for a in now if a[2] == 'r']
        agg_seat = bets[-1][1] if bets else None
        if cost:
            main = next((s for s in opponents if s.seat == agg_seat), max(opponents, key=lambda s: s.bet))
        else:
            main = max(opponents, key=lambda s: s.stack + s.bet)
        prof = profiles[main.seat]
        frac = self.pre_range(main.seat, prof, pre, bb, main.stack + main.bet, state.players_remaining)
        index = range_index(frac)
        pressure = 0
        if cost:
            fraction = cost / max(1, pot - cost)
            pressure = 1 if street == 3 and fraction < .65 and len(bets) < 2 else 2
            if fraction > .85 or len(bets) >= 2:
                pressure = 3
            if len(bets) >= 3 or (len(bets) >= 2 and street >= 4):
                pressure = 4
        else:
            # Previous streets' calls/raises put more pairs in a continuing range.
            past = [a for a in m['a'] if 0 < a[0] < street and a[1] == main.seat and a[2] in ('c', 'r')]
            if past:
                pressure = 1
        quick = state.time_bank_ms is not None and state.time_bank_ms < 25
        auto = prof[3] and prof[2] > .62
        hr = conditioned_range(index, board, cards, tex, pressure, auto, m['r'], quick)
        if street == 5:
            equity = eval7.py_hand_vs_range_exact(cards, hr, board)
        else:
            iterations = 200 if quick else 1000 if cost >= me.stack * .30 and cost else 400
            equity = eval7.py_hand_vs_range_monte_carlo(cards, hr, board, iterations)
        equity, eligible_pot = equity_layers(state, m, me, opponents, cost, equity)
        if not CONDITION_RANGES and cost and not prof[3]:
            equity = max(0., equity - (.08 if street == 3 else .13))
        required = call_requirement(state, me, opponents, main, eligible_pot, cost, m)
        odds = cost / (pot + cost)
        maniac = auto
        all_nits = all(p[4] for p in profiles.values())
        effective = min(me.stack, max(s.stack for s in opponents if value(s.status) == 'active') if any(value(s.status) == 'active' for s in opponents) else 0)
        active = sum(value(s.status) == 'active' for s in opponents)
        if cost:
            future = 0.0 if street == 5 or cost >= me.stack * .8 or main.stack == 0 else .022
            if not in_position and tier < 3 and not draw:
                future += .022
            if equity < required + future:
                return 'fold', 0
            value_raise = equity > (.73 if maniac else .79)
            if tier >= 6 and equity > .67:
                value_raise = True
            if maniac and tier >= 3 and equity > .64:
                value_raise = True
            if maniac and state.players_remaining > 3 and own > 15 * bb:
                value_raise = equity > .86
            if len(opponents) >= 3 and tier < 5:
                value_raise = False
            if value_raise and active and 'raise' in legal:
                size = me.bet + cost + int((pot + cost) * (.72 if street < 5 else .85))
                if size - me.bet >= me.stack * .48 or effective < (pot + cost) * .85:
                    size = own
                return 'raise', size
            # Semi-bluff a strong draw when a small bet leaves a profitable fold component.
            if street < 5 and draw >= 12 and equity > .42 and not maniac and len(opponents) == 1 and cost < pot * .30 and rand < .24 and 'raise' in legal:
                return 'raise', me.bet + cost + int((pot + cost) * .70)
            return 'call', 0

        if not active or 'raise' not in legal:
            return 'check', 0
        fraction = .58 if street == 3 else .65 if street == 4 else .75
        value_bet = equity > (.59 if len(opponents) == 1 else .65) and (tier >= 2 or equity > .76)
        if street == 5 and tier < 2:
            value_bet = False
        if value_bet:
            if equity < .70:
                fraction = .38
            elif equity > .87:
                fraction = .82
            size = me.bet + int(max(bb, pot * fraction))
            if size - me.bet >= me.stack * .48 or effective < pot * .8:
                size = own
            return 'raise', size
        if all_nits:
            return 'raise', me.bet + max(bb, int(pot * .3))
        hero_opened = bool(raises and raises[-1][1] == state.seat)
        wet = max(tex[1]) >= 3 or DRAW_OUTS[tex[2]] >= 2
        if len(opponents) == 1 and not maniac:
            bluff = False
            if street == 3:
                bluff = hero_opened and not wet and rand < (.62 if in_position else .44) and equity > .19
                bluff |= draw >= 8 and equity > .31 and rand < .55
            elif street == 4:
                bluff = draw >= 8 and equity > .27 and rand < .48
            elif street == 5:
                blocker = max(c.rank for c in cards) == 12 or any(tex[1][c.suit] >= 3 and c.rank >= 10 for c in cards)
                bluff = tier == 0 and blocker and rand < .18 and in_position
            if bluff:
                return 'raise', me.bet + max(bb, int(pot * (.38 if street == 3 else .62)))
        return 'check', 0


