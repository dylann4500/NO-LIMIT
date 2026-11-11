"""Fast range poker with per-table opponent learning and tournament risk control."""
import itertools
import gc
import json
import marshal
import os
import random
from pathlib import Path

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / 'preflop.json').read_text())
P = {
    'open': 1.0, 'threebet': .615, 'call_edge': .025,
    'risk': .075, 'value': .585, 'cbet': .62, 'bluff': .28,
    'dry_size': .36, 'wet_size': .62, 'raise_size': 3.1,
    'samples': 144, 'iterations': 320, 'range_filter': 1.0,
    'range_weight': .35, 'history_filter': .84, 'adaptive_open': .16,
    'hu_call_scale': .60,
}
if (ROOT / 'params.json').exists():
    P.update(json.loads((ROOT / 'params.json').read_text()))
# Only for the offline search runner; production has no environment override.
if os.environ.get('POKERBOT_PARAMS'):
    P.update(json.loads(os.environ['POKERBOT_PARAMS']))

RANKS = '23456789TJQKA'
CARDS = {r+s: eval7.Card(r+s) for r in RANKS for s in 'cdhs'}
CID = {s:i for i,s in enumerate(CARDS)}
DECK = list(CARDS.values())

def hand_key(a, b):
    x, y = max(a.rank, b.rank), min(a.rank, b.rank)
    return RANKS[x]+RANKS[y]+('' if x == y else 's' if a.suit == b.suit else 'o')

def playable(k):
    a, b = RANKS.index(k[0]), RANKS.index(k[1])
    w = float(P['range_weight'])
    value = (1-w)*DATA['strength'][k] + w*DATA['equity'][k][DATA['tiers'].index(.17)]
    return value + (.022 if k.endswith('s') else 0) + (
        .012 if a == b else .008 if a-b <= 2 and a >= 6 else 0) + (
        .018 if k.endswith('s') and a-b == 1 and a <= 8 else 0) + (
        .008 if k.endswith('s') and a == 12 and b <= 3 else 0)

COMBOS = list(itertools.combinations(DECK, 2))
COMBOS.sort(key=lambda c: playable(hand_key(*c)), reverse=True)
PCT = {}
for i, c in enumerate(COMBOS):
    PCT[hand_key(*c)] = (i + 1) / 1326
TIERS = DATA['tiers']
RANGES = []
_rng = random.Random(79371)
for _w in TIERS:
    # Keep complete narrow ranges; sample wide ranges uniformly at import.
    if str(_w) in DATA.get('tight_ranges', {}):
        _r = [c for c, _ in eval7.HandRange(DATA['tight_ranges'][str(_w)]).hands]
    else:
        _r = COMBOS[:max(16, round(1326 * _w))]
    if len(_r) > int(P['samples']):
        _r = _rng.sample(_r, int(P['samples']))
    RANGES.append([(list(c), 1.0, (1 << CID[str(c[0])]) | (1 << CID[str(c[1])])) for c in _r])
del _rng

def kind(x):
    return (getattr(x, 'name', None) or getattr(x, 'value', x)).lower()

def new_memory(n):
    # Profile fields: hands, VPIP, PFR, post checks/bets/calls, folds/faced,
    # pre raises/actions/minraises, shows/strength/loose, 3bets/opportunities,
    # heads-up hands/PFR/3bets/opportunities.
    return {'version': 4, 'h': -1, 'st': 0, 'p': [[0]*20 for _ in range(n)],
            'v': 0, 'r': 0, 'b': [0]*n, 'c': [0]*n, 'e': [0]*n,
            'nr': [0]*n, 'bar': [0]*n, 'cl': [0]*n, 'rl': [0]*n,
            'pos': [0]*n, 'short': [0.0]*n, 'live': n, 'o': 0, 'mx': 0, 'pr': 0, 'sr': 0, 'ag': -1}

def update(state, memory):
    n = max(s.seat for s in state.seats) + 1
    try:
        m = marshal.loads(memory) if memory else new_memory(n)
    except (ValueError, EOFError, TypeError):
        m = new_memory(n)
    if not isinstance(m,dict) or m.get('version') != 4 or len(m['p']) < n:
        m = new_memory(n)
    profiles = m['p']
    bb = max(1, state.blinds[1])
    for ev in state.events:
        k = kind(ev.kind)
        if k == 'hand':
            m['h'] = ev.amount
            m['st'] = m['v'] = m['r'] = m['pr'] = m['sr'] = 0
            m['mx'] = 0
            m['ag'] = -1
            m['b'] = [0]*n
            m['c'] = [0]*n
            m['e'] = [0]*n
            m['nr'] = [0]*n
            m['bar'] = [0]*n
            m['cl'] = [0]*n
            m['rl'] = [0]*n
            m['short'] = [0.0]*n
            m['o'] = 0
            live = sorted(s.seat for s in state.seats if s.status != 'busted')
            m['live'] = len(live)
            if state.button in live:
                button = live.index(state.button)
                for i,s in enumerate(live):
                    m['pos'][s] = (i-button)%len(live)
            for s in state.seats:
                if s.status != 'busted':
                    profiles[s.seat][0] += 1
                    if len(live) == 2:
                        profiles[s.seat][16] += 1
            continue
        if k == 'board':
            m['st'] += 1
            m['sr'] = 0
            m['mx'] = 0
            m['ag'] = -1
            m['b'] = [0]*n
            continue
        seat = ev.seat
        if seat is None or seat >= n:
            continue
        p = profiles[seat]
        amount = ev.amount or 0
        pre = m['st'] == 0
        if k == 'blind':
            m['b'][seat] += amount
            m['mx'] = max(m['mx'],m['b'][seat])
            m['c'][seat] += amount
        elif k == 'ante':
            m['c'][seat] += amount
        elif k in ('call', 'raise', 'fold', 'check'):
            oldmax = m['mx']
            if oldmax > m['b'][seat]:
                p[7] += 1
                if k == 'fold':
                    p[6] += 1
            if pre:
                p[9] += 1
                if m['pr'] and oldmax > m['b'][seat] and not m['nr'][seat] and not (m['o'] & (1 << seat)):
                    p[15] += 1
                    if m['live'] == 2:
                        p[19] += 1
                    m['o'] |= 1 << seat
                if k in ('call', 'raise') and not (m['v'] & (1 << seat)):
                    p[1] += 1
                    m['v'] |= 1 << seat
            if k == 'call':
                m['b'][seat] += amount
                m['c'][seat] += amount
                if pre:
                    m['e'][seat] = max(m['e'][seat], 2 if m['pr'] else 1)
                else:
                    p[5] += 1
                    m['cl'][seat] |= 1 << m['st']
            elif k == 'raise':
                m['c'][seat] += max(0, amount-m['b'][seat])
                m['b'][seat] = amount
                m['mx'] = amount
                m['ag'] = seat
                m['sr'] += 1
                if pre:
                    if not m['nr'][seat]:
                        m['rl'][seat] = m['pr']+1
                        if m['pr']:
                            p[14] += 1
                            if m['live'] == 2:
                                p[18] += 1
                    p[8] += 1
                    if amount-oldmax <= max(bb, oldmax*.55):
                        p[10] += 1
                    m['pr'] += 1
                    m['e'][seat] = 3
                    m['nr'][seat] += 1
                    if not (m['r'] & (1 << seat)):
                        p[2] += 1
                        if m['live'] == 2:
                            p[17] += 1
                        m['r'] |= 1 << seat
                else:
                    p[4] += 1
                    m['bar'][seat] |= 1 << m['st']
            elif k == 'check' and not pre:
                p[3] += 1
        elif k == 'show' and len(ev.cards or []) == 2:
            try:
                hk = hand_key(CARDS[ev.cards[0]], CARDS[ev.cards[1]])
                p[11] += 1
                p[12] += DATA['strength'][hk]
                p[13] += int(PCT[hk] > .5)
            except (KeyError, TypeError):
                pass
    if not state.board:
        for s in state.seats:
            if s.status == 'all_in' and m['rl'][s.seat] == 1 and 0 < s.bet <= 12*bb:
                pos, count = m['pos'][s.seat], m['live']
                left = count-pos if pos >= 3 else 0
                ow = .18+.032*max(0,6-count)+.035*max(0,min(5,5-left))
                if pos == 1:
                    ow = .51
                if count == 2:
                    ow = .78
                limpers = sum(e == 1 for e in m['e'])
                m['short'][s.seat] = ow*(1.10 if s.bet < 7*bb else .95)*(.8**min(2,limpers))
    return m

def maniac(p):
    repeated = p[8] > 1.2*max(1,p[0])
    loose_full = p[0] >= 5 and p[2]/p[0] > .75 and p[10]/max(1,p[8]) > .8 and (len(p) <= 16 or p[16] < .5*p[0])
    return ((p[8] >= 5 and p[8] / max(1, p[9]) > .69 and (repeated or loose_full))
            or (p[4] >= 9 and p[4] > 3*(p[3]+p[5]+1)))

def width(m, seat):
    p = m['p'][seat]
    if maniac(p):
        return 1.0
    vp = (p[1]+3.5)/(p[0]+11)
    pf = (p[2]+2.3)/(p[0]+13)
    entry = m['e'][seat]
    if entry == 3:
        w = max(.075, min(.60, pf*1.15))
        pos = m['pos'][seat]
        if m['live'] == 2:
            w = max(.08,min(.90,(p[17]+3.2)/(p[16]+5)))
        elif pos == 0:
            w *= 1.40
        elif pos == 1:
            w *= 1.50
        elif pos >= 3 and m['live']-pos >= 4:
            w *= .82
        if m['rl'][seat] >= 2:
            w = max(.025,min(.5,(p[18]+2.4)/(p[19]+14) if m['live'] == 2 else (p[14]+2.0)/(p[15]+30)))
            if pos in (0,1,2):
                w *= 1.15
        if m['rl'][seat] >= 3 or m['nr'][seat] >= 2:
            w *= .40
    elif entry == 2:
        w = max(.12, min(.65, vp*.85))
    elif entry == 1:
        w = max(.28, min(.85, vp*1.65))
    else:
        w = .85
    # Revealed weak holdings are strong evidence of a loose continuing range.
    if p[11] >= 3 and p[13]/p[11] > .45:
        w = max(w, .60)
    return max(.015, min(1.0, max(w,m['short'][seat])))

def tier(w):
    return min(range(len(TIERS)), key=lambda i: abs(TIERS[i]-w))

def pf_equity(k, w):
    values = DATA['equity'][k]
    if w <= TIERS[0]:
        return values[0]
    for i in range(1, len(TIERS)):
        if w <= TIERS[i]:
            f = (w-TIERS[i-1])/(TIERS[i]-TIERS[i-1])
            return values[i-1]*(1-f)+values[i]*f
    return values[-1]

def draw_info(hole, board):
    cards = hole+board
    suits = [0]*4
    bits = 0
    for c in cards:
        suits[c.suit] += 1
        bits |= 1 << c.rank
    fd = max(suits) == 4 and any(suits[c.suit] == 4 for c in hole)
    # Ace also plays low. Four ranks within five gives a straight draw.
    mask = (bits << 1) | ((bits >> 12) & 1)
    sd = any(((mask >> j) & 31).bit_count() == 4 for j in range(10))
    return fd, sd

def icm_value(stacks, hero, payouts):
    """Exact hero ICM for the first three prizes, O(players squared)."""
    h = stacks[hero]
    if h <= 0:
        return payouts[len(stacks)-1] if len(stacks) <= len(payouts) else 0.0
    total = sum(stacks)
    result = payouts[0]*h/total
    other = [v for i,v in enumerate(stacks) if i != hero and v > 0]
    if len(payouts) > 1:
        result += payouts[1]*sum(v/total*h/(total-v) for v in other)
    if len(payouts) > 2:
        third = 0.0
        for i,v in enumerate(other):
            for j,u in enumerate(other):
                if i != j:
                    third += v/total*u/(total-v)*h/(total-v-u)
        result += payouts[2]*third
    return result

def icm_call_threshold(state, me, villain, call):
    payouts = list(state.config.payouts or [50,30,20])
    if any(x > 0 for x in payouts[3:]):
        return 0.0
    alive = [s for s in state.seats if s.status != 'busted']
    hero = next(i for i,s in enumerate(alive) if s.seat == me.seat)
    enemy = next(i for i,s in enumerate(alive) if s.seat == villain.seat)
    stacks = [s.stack for s in alive]
    folded = stacks[:]
    folded[enemy] += state.pot
    won = stacks[:]
    won[hero] += state.pot
    lost = stacks[:]
    lost[hero] -= call
    lost[enemy] += state.pot+call
    f, w, l = (icm_value(x,hero,payouts) for x in (folded,won,lost))
    return max(0.0,min(1.0,(f-l)/max(.000001,w-l)))

def locked_board(board):
    """Board-only nuts that force every remaining player to split."""
    value = eval7.evaluate(board)
    if value == 135004160:
        return True
    category = value >> 24
    if category == 7:
        quads, kicker = (value >> 16) & 15, (value >> 12) & 15
        return kicker == (11 if quads == 12 else 12)
    if category == 4 and ((value >> 16) & 15) == 12:
        return max(sum(c.suit == s for c in board) for s in range(4)) <= 2
    return False

def post_equity(hole, board, mask, w, profile, pressure, fraction, barrels, continued=0):
    rr = RANGES[tier(w)]
    if (not pressure and not continued) or maniac(profile):
        rng = [(c, wt) for c, wt, cm in rr if not cm & mask]
        if not rng:
            return .5
        if len(board) == 5:
            return float(eval7.py_hand_vs_range_exact(hole,rng,board))
        return float(eval7.py_hand_vs_range_monte_carlo(hole, rng, board, int(P['iterations'])))
    ranked = [(eval7.evaluate(c+board), c, cm) for c, _, cm in rr if not cm & mask]
    if not ranked:
        return .5
    ranked.sort(key=lambda x: x[0], reverse=True)
    aggression = (profile[4]+3.0)/(profile[3]+profile[4]+profile[5]+7.5)
    if pressure:
        keep = (.64 if len(board) == 3 else .51 if len(board) == 4 else .36)
        keep *= .60 + aggression
        keep *= 1.12 if fraction < .3 else .90 if fraction > .8 else 1.0
        keep *= .86 ** max(0, barrels-1)
        keep *= float(P['range_filter'])
    else:
        keep = .97
    keep *= float(P['history_filter']) ** continued
    keep = min(.95, max(.16, keep))
    take = max(5, int(len(ranked)*keep))
    selected = ranked[:take]
    # A small polarized bluff tail; flush draws continue on earlier streets.
    flush_suit = -1
    if len(board) < 5:
        counts = [0]*4
        for c in board:
            counts[c.suit] += 1
        if max(counts) >= 2:
            flush_suit = counts.index(max(counts))
    stride = 5 if len(board) == 3 else 9 if len(board) == 4 else 13
    for i, row in enumerate(ranked[take:]):
        c = row[1]
        if i % stride == 0 or (flush_suit >= 0 and c[0].suit == flush_suit and c[1].suit == flush_suit):
            selected.append(row)
    if len(board) == 5:
        rank = eval7.evaluate(hole+board)
        return sum((rank > v) + .5*(rank == v) for v,_,_ in selected)/len(selected)
    rng = [(c, 1.0) for _, c, _ in selected]
    return float(eval7.py_hand_vs_range_monte_carlo(hole, rng, board, int(P['iterations'])))

class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        # A collection can otherwise charge unrelated SDK garbage to this turn.
        enabled = gc.isenabled()
        if enabled:
            gc.disable()
        try:
            return self._act(state, memory)
        finally:
            if enabled:
                gc.enable()

    def _act(self, state, memory):
        m = update(state, memory)
        legal = {kind(a.kind): a for a in state.legal_actions}
        me = next(s for s in state.seats if s.seat == state.seat)
        opponents = [s for s in state.seats if s.seat != state.seat and s.status in ('active', 'all_in')]
        bb = max(1, state.blinds[1])
        call = min(state.to_call, me.stack)
        pot = max(1, state.pot)
        hole = [CARDS[c] for c in state.cards]
        board = [CARDS[c] for c in state.board]
        key = hand_key(*hole)
        pct = PCT[key]
        nopp = max(1, len(opponents))
        live = sorted(s.seat for s in state.seats if s.status != 'busted')
        n = len(live)
        pos = (live.index(state.seat)-live.index(state.button)) % n if state.button in live else 0
        late = pos == 0 or (pos >= 3 and n-pos <= 1)
        sb = pos == 1
        effective = min(me.stack+me.bet, max((s.stack+s.bet for s in opponents), default=me.stack))
        depth = effective/bb
        ag = m['ag']
        villain = next((s for s in opponents if s.seat == ag), None)
        if villain is None and opponents:
            villain = max(opponents, key=lambda s: s.bet)
        vp = m['p'][villain.seat] if villain else [0]*20
        vw = width(m, villain.seat) if villain else .4
        wild = maniac(vp)
        # Approximate tournament risk premium, concentrated on bubble call-offs.
        paid = sum(1 for x in (state.config.payouts or [50,30,20]) if x > 0)
        risk = 0.0
        if n > 2 and paid > 0:
            risk = float(P['risk']) * (.95 if n == paid+1 else .45 if n <= paid else .22)
            smaller = sum(s.stack+s.bet < .55*(me.stack+me.bet) for s in state.seats if s.status != 'busted' and s.seat != me.seat)
            if smaller and n == paid+1:
                risk *= 1.4
            if (me.stack+me.bet) < 7*bb:
                risk *= .55
        odds = call/(pot+call)
        if call and sum(m['c']) >= .95*pot:
            cap = m['c'][state.seat]+call
            eligible = sum(min(c, cap) for c in m['c']) + call
            odds = call/max(call+1, min(pot+call, eligible))
        icm_odds = 0.0
        if call >= .60*me.stack and nopp == 1 and villain is not None and n > 2:
            icm_odds = icm_call_threshold(state,me,villain,call)
        # Stable mixing without a mutable random generator or cross-table state.
        mix = ((state.hand_number*2654435761 + state.seat*2246822519 +
                CID[state.cards[0]]*3266489917 + CID[state.cards[1]]*668265263 +
                len(board)*374761393) & 0xffff)/65536

        def passive():
            if 'check' in legal:
                return Action.check()
            if 'fold' in legal:
                return Action.fold()
            if 'call' in legal:
                return Action.call()
            a = next(iter(legal.values()))
            return Action.raise_to(int(a.min_amount))

        def raise_to(total):
            a = legal.get('raise')
            if a is None:
                return Action.call() if 'call' in legal else passive()
            lo, hi = int(a.min_amount), int(a.max_amount)
            return Action.raise_to(max(lo, min(hi, int(total))))

        action = None
        if not board:
            opening = m['pr'] == 0 and max((s.bet for s in opponents), default=0) <= bb
            if opening:
                left = n-pos if pos >= 3 else 0
                ow = (.18 + .032*max(0, 6-n) + .035*max(0, min(5, 5-left))) * float(P['open'])
                if sb:
                    ow = .51*float(P['open'])
                if n == 2:
                    ow = .78*float(P['open'])
                tight = sum(m['p'][s.seat][7] >= 8 and m['p'][s.seat][6]/m['p'][s.seat][7] > .88 for s in opponents)
                ow += float(P['adaptive_open'])*tight/max(1,len(opponents))
                if tight == len(opponents) and tight:
                    ow = .99
                limpers = sum(m['e'][s.seat] == 1 for s in opponents)
                if limpers:
                    ow *= .78**min(2,limpers)
                if depth < 10.5:
                    ow *= 1.10 if depth < 7 else .95
                if pct <= ow:
                    if depth <= 10.5:
                        action = raise_to(me.stack+me.bet)
                    else:
                        size = (2.15 + .9*limpers)*bb
                        if not late and depth > 40:
                            size += .25*bb
                        action = raise_to(size)
                elif call == 0:
                    action = passive()
                elif sb and limpers and pct < .65 and call < .025*effective:
                    action = Action.call() if 'call' in legal else passive()
            else:
                # Current contributors matter; unacted players mostly fold to a raise.
                committed = [s for s in opponents if s.bet > bb or s.status == 'all_in']
                count = max(1,len(committed))
                if not wild and villain is not None and not m['short'][villain.seat]:
                    mult = max((s.bet for s in opponents), default=bb)/bb
                    if mult >= 10 and m['rl'][villain.seat] <= 1:
                        vw *= .55
                    elif mult >= 5 and m['rl'][villain.seat] <= 1:
                        vw *= .80
                eq = pf_equity(key, max(.015,vw)) ** (1+.76*(count-1))
                commit = call/max(1,me.stack)
                edge = float(P['call_edge'])*(float(P['hu_call_scale']) if n == 2 else 1) + risk*min(1.0,commit*2)
                if depth > 16 and commit < .65:
                    edge += (.025 if late else .05)
                if count > 1:
                    edge += .015
                # Deep calls need equity realization; pocket pairs retain set value.
                threshold = max(odds + edge, icm_odds+.005 if icm_odds else 0)
                value = eq >= float(P['threebet']) + .035*(count-1)
                if pct <= .014 and count <= 2:
                    value = True
                if value and eq >= threshold and 'raise' in legal:
                    mx = max((s.bet for s in opponents), default=bb)
                    size = float(P['raise_size'])*mx + .5*max(0,pot-mx-me.bet)
                    if wild or size-me.bet > .31*effective or depth < 16:
                        size = me.stack+me.bet
                    action = raise_to(size)
                elif eq >= threshold and 'call' in legal:
                    # Avoid donating repeated tiny calls to an obvious min-raise war
                    # with a holding that cannot continue when stacks go in.
                    if wild and m['pr'] >= 4 and eq < .50 + risk:
                        action = passive()
                    else:
                        action = Action.call()
                elif key[0] == key[1] and count <= 2 and call < .045*effective and depth > 25 and m['pr'] <= 2:
                    action = Action.call() if 'call' in legal else passive()
        else:
            mask = 0
            for c in state.cards+state.board:
                mask |= 1 << CID[c]
            fraction = call/max(1,pot-call)
            barrels = m['bar'][villain.seat].bit_count() if villain else 0
            prior = (1 << (len(board)-2)) - 1
            continued = ((m['cl'][villain.seat] | m['bar'][villain.seat]) & prior).bit_count() if villain else 0
            eq = post_equity(hole, board, mask, vw, vp, call > 0, fraction, barrels,continued)
            # Equity events against different opponents are correlated.
            if nopp > 1:
                other = min((s for s in opponents if villain is None or s.seat != villain.seat),key=lambda s:width(m,s.seat))
                ow = width(m,other.seat)
                if abs(ow-vw) >= .20 or wild:
                    oc = ((m['cl'][other.seat] | m['bar'][other.seat]) & prior).bit_count()
                    eq2 = post_equity(hole,board,mask,ow,m['p'][other.seat],False,0,0,oc)
                    eq *= eq2 ** (.78*(nopp-1))
                else:
                    eq **= 1+.78*(nopp-1)
            fd, sd = draw_info(hole,board) if len(board) < 5 else (False,False)
            ranks = [c.rank for c in board]
            suits = [sum(c.suit == s for c in board) for s in range(4)]
            rank_bits = sum(1 << r for r in set(ranks))
            rank_bits = (rank_bits << 1) | ((rank_bits >> 12) & 1)
            connected = any(((rank_bits >> j) & 31).bit_count() >= (3 if len(board)==3 else 4) for j in range(10))
            wet = (max(suits) >= 2 and len(board) == 3) or max(suits) >= 3 or connected
            spr = effective/max(1,pot)
            if call:
                edge = float(P['call_edge'])*(float(P['hu_call_scale']) if n == 2 else 1) + risk*min(1,call/max(1,me.stack)*2)
                if len(board) < 5:
                    edge += .015 if late else .035
                # Raises need a much stronger hand than calls, especially on river.
                raise_eq = (.82 if len(board) == 5 else .76) + .025*max(0,nopp-1)
                if wild:
                    raise_eq -= .055
                if eq >= max(raise_eq,icm_odds+.005 if icm_odds else 0) and 'raise' in legal:
                    size = me.bet+call+(pot+call)*(.8 if wet else .68)
                    if spr < 2 or size-me.bet > .45*effective:
                        size = me.stack+me.bet
                    action = raise_to(size)
                elif (fd or sd) and eq > max(.46,icm_odds) and nopp == 1 and not wild and len(board) == 3 and mix < .12 and spr < 5 and 'raise' in legal:
                    action = raise_to(me.bet+call+.75*(pot+call))
                elif eq >= max(odds+edge,icm_odds+.005 if icm_odds else 0) and 'call' in legal:
                    action = Action.call()
                elif len(board) == 5 and locked_board(board) and 'call' in legal:
                    # A guaranteed split has no tournament risk premium.
                    action = Action.call()
            else:
                value_threshold = float(P['value']) + .025*max(0,nopp-1)
                value = eq >= value_threshold
                nit = all((m['p'][s.seat][6]+1)/(m['p'][s.seat][7]+3) > .73 and m['p'][s.seat][7] >= 5 for s in opponents)
                pre_aggressor = m['e'][state.seat] == 3
                bluff = False
                if nopp == 1:
                    if len(board) == 3 and pre_aggressor:
                        rate = float(P['cbet'])*(1 if not wet else .60)
                        bluff = mix < rate and not wild
                    elif late and len(board) >= 4:
                        bluff = mix < float(P['bluff'])*(1.3 if fd or sd else 1.0) and not wild
                if value or bluff or nit:
                    size = pot*(float(P['wet_size']) if wet or nopp > 1 else float(P['dry_size']))
                    if len(board) == 5 and value and eq > .80:
                        size = pot*.78
                    if nit and not value:
                        size = max(bb, pot*.24)
                    if value and spr < 1.35 and eq > .66:
                        size = me.stack+me.bet
                    action = raise_to(me.bet+size)
        if action is None:
            action = passive()
        return action, marshal.dumps(m)
