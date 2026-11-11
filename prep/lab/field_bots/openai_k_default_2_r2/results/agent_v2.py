"""Tournament Hold'em: bounded range inference, native equity, and payout-aware decisions."""
import os
import gc
gc.disable()  # Bound decision latency: cyclic collection is unnecessary here.
import math
import pickle
import itertools
from bisect import bisect_left
import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

ROOT = os.path.dirname(__file__)
with open(os.path.join(ROOT, 'preflop.pkl'), 'rb') as _f:
    WIDTHS, PERCENTILE, RANDOM_EQUITY, PREFLOP_EQUITY, ORDER = pickle.load(_f)
_STRAIGHT_WINDOWS = [(31 << i) for i in range(9)]+[(1<<12)|15]
STRAIGHT_DRAW = tuple(any((m & w).bit_count() == 4 for w in _STRAIGHT_WINDOWS) for m in range(8192))
RANKS = '23456789TJQKA'
SUITS = 'cdhs'
CARD_NAMES = [r+s for r in RANKS for s in SUITS]
CARDS = [eval7.Card(c) for c in CARD_NAMES]
CARD_INDEX = {c:i for i,c in enumerate(CARD_NAMES)}

def hand_key(a, b):
    x, y = a//4, b//4
    if x < y: x, y = y, x
    return RANKS[x]+RANKS[y]+('' if x == y else 's' if a%4 == b%4 else 'o')

# Immutable, suit-balanced range samples. Import-time work is outside decision clocks.
_COMBOS = {}
for _a, _b in itertools.combinations(range(52), 2):
    _k = hand_key(_a, _b)
    _COMBOS.setdefault(_k, []).append((([CARDS[_a], CARDS[_b]], 1.0), _a, _b,
                                      (1 << _a) | (1 << _b),
                                      ((_a*2654435761 ^ _b*2246822519) & 0xffffffff)))
RANGES = []
for _w in WIDTHS:
    _c = []
    for _k in ORDER:
        if len(_c) >= 1326*_w: break
        _c.extend(sorted(_COMBOS[_k],key=lambda x:x[4]))
    # Stratify by preflop strength, with independently shuffled suit combinations.
    # This reduces river posterior error versus a purely random combo sample.
    if len(_c) > 120:
        _c = [_c[int((i+.5)*len(_c)/120)] for i in range(120)]
    RANGES.append(tuple(_c))
del _COMBOS, _c

# Persistent stats: hands, VPIP, PFR, post actions, post raises, faced bets, folds,
# raises, small raises, showdowns, stack, calls, preflop folds facing a raise.
H, VP, PR, PA, PB, FACE, FOLD, NR, MR, SHOW, STACK, CALLS, PFOLD, PFOP, PFRR, BBFOLD, BBPLAY, RSHOW, RBLUFF, XSHOW, XWEAK = range(21)
SFACE, SFOLD = 21, 24
STAT_COUNT = 27

def kind(x):
    k = x.kind
    return getattr(k, 'value', k)

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def width_index(p):
    return min(len(WIDTHS)-1, bisect_left(WIDTHS, p))

def pf_equity(k, p):
    i = width_index(p)
    if i == 0: return PREFLOP_EQUITY[k][0]
    a, b = WIDTHS[i-1], WIDTHS[i]
    t = clamp((p-a)/(b-a), 0., 1.)
    return PREFLOP_EQUITY[k][i-1]*(1-t)+PREFLOP_EQUITY[k][i]*t

def new_hand(number):
    return {'n':number, 'street':0, 'board':[], 'vp':[], 'pr':[], 'pf':{},
            'raises':[], 'limps':[], 'bets':{}, 'maxbet':0, 'pot':0, 'contrib':{},
            'acts':{}, 'ag':None, 'nb':0, 'acted':[], 'fold':[]}

def update(state, memory):
    try:
        m = pickle.loads(memory) if memory else None
    except Exception:
        m = None
    fresh = not isinstance(m, dict) or m.get('v') != 1
    if fresh:
        m = {'v':1, 'stats':{}, 'hand':new_hand(state.hand_number), 'seq':0}
    stats = m['stats']
    for s in state.seats:
        if s.seat not in stats:
            v = [0]*STAT_COUNT
            v[STACK] = s.stack+s.bet
            stats[s.seat] = v
        elif len(stats[s.seat]) < STAT_COUNT: stats[s.seat].extend([0]*(STAT_COUNT-len(stats[s.seat])))
    h = m['hand']
    events = state.events
    if fresh and not any(kind(e) == 'hand' for e in events):
        history = getattr(state,'history',None)
        if history and all(hasattr(e,'kind') for e in history): events = history
    for e in events:
        k = kind(e)
        if k == 'hand':
            h = new_hand(e.amount)
            for v in stats.values():
                if v[STACK] > 0: v[H] += 1
            continue
        if k == 'board':
            h['board'].extend(e.cards or [])
            h['street'] = 1 if len(h['board']) == 3 else len(h['board'])-2
            h['bets'] = {}; h['maxbet'] = 0; h['ag'] = None
            h['nb'] = 0; h['acted'] = []
            continue
        sid = e.seat
        if sid not in stats: continue
        v = stats[sid]
        amt = e.amount or 0
        if k == 'stack':
            v[STACK] = amt
            continue
        if k == 'show':
            v[SHOW] += 1
            row = h['acts'].get(sid)
            if row and any(x[0] == 4 for x in row) and len(h['board']) >= 3 and e.cards and len(e.cards) == 2:
                v[XSHOW] += 1
                ids = [CARD_INDEX[c] for c in h['board']]
                ci = [CARD_INDEX[c] for c in e.cards]
                value = eval7.evaluate([CARDS[i] for i in ci+ids])
                if made_quality(*ci,value,board_context(ids)) < .63: v[XWEAK] += 1
            if row and row[2][0] >= 3 and len(h['board']) == 5 and e.cards and len(e.cards) == 2:
                v[RSHOW] += 1
                ids = [CARD_INDEX[c] for c in h['board']]
                val = eval7.evaluate([CARDS[CARD_INDEX[c]] for c in e.cards]+[CARDS[i] for i in ids])
                cat, pair = val >> 24, (val >> 16)&15
                br = [i//4 for i in ids]
                if cat == 0 or cat == 1 and (br.count(pair) >= 2 or pair < sorted(set(br))[-2]): v[RBLUFF] += 1
            continue
        if k in ('blind', 'ante'):
            h.setdefault('contrib',{})[sid] = h.get('contrib',{}).get(sid,0)+amt
            h['pot'] += amt
            if k == 'blind':
                h['bets'][sid] = h['bets'].get(sid, 0)+amt
                h['maxbet'] = max(h['maxbet'], h['bets'][sid])
            continue
        if k not in ('fold', 'check', 'call', 'raise'): continue
        old = h['bets'].get(sid, 0)
        facing = h['maxbet'] > old
        street = h['street']
        if street == 0:
            if facing and h['raises']:
                v[PFOP] += 1
                if k == 'raise': v[PFRR] += 1
                if seat_position(state,sid) == state.players_remaining-1:
                    v[BBFOLD if k == 'fold' else BBPLAY] += 1
            if k in ('call', 'raise') and sid not in h['vp']:
                h['vp'].append(sid); v[VP] += 1
            if k == 'raise':
                if sid not in h['pr']:
                    h['pr'].append(sid); v[PR] += 1
                nr = len(h['raises'])
                h['pf'][sid] = max(h['pf'].get(sid, 0), 3+nr)
                h['raises'].append((sid, amt))
                if len(h['raises']) > 24: del h['raises'][:-24]
                v[NR] += 1
                if amt <= max(state.blinds[1]*2.3, h['maxbet']*2.05): v[MR] += 1
            elif k == 'call':
                if not h['raises']:
                    h['limps'].append(sid)
                    h['pf'][sid] = 1
                else: h['pf'][sid] = max(2, h['pf'].get(sid, 0))
            elif k == 'fold' and h['raises']:
                v[PFOLD] += 1
        else:
            v[PA] += 1
            if facing:
                v[FACE] += 1
                v[SFACE+street-1] += 1
                if k == 'fold':
                    v[FOLD] += 1
                    v[SFOLD+street-1] += 1
            code = {'check':1, 'fold':0, 'call':2, 'raise':3}[k]
            fraction = 0.
            if k == 'raise':
                code = 4 if h['maxbet'] else 3
                v[PB] += 1; v[NR] += 1
                inc = max(0, amt-old)
                fraction = max(0., amt-h['maxbet'])/max(1, h['pot']+h['maxbet']-old)
                if fraction <= .26: v[MR] += 1
                h['ag'] = sid; h['nb'] += 1
            row = h['acts'].setdefault(sid, [[0,0.],[0,0.],[0,0.]])
            if code >= row[street-1][0]: row[street-1] = [code, fraction]
        if k == 'fold': h['fold'].append(sid)
        if k == 'call':
            v[CALLS] += 1
            h['pot'] += amt
            h.setdefault('contrib',{})[sid] = h.get('contrib',{}).get(sid,0)+amt
            h['bets'][sid] = old+amt
        elif k == 'raise':
            h['pot'] += max(0, amt-old)
            h.setdefault('contrib',{})[sid] = h.get('contrib',{}).get(sid,0)+max(0,amt-old)
            h['bets'][sid] = amt
            h['maxbet'] = max(h['maxbet'], amt)
        if sid not in h['acted']: h['acted'].append(sid)
    if h['n'] != state.hand_number:
        h = new_hand(state.hand_number)
    m['hand'] = h
    m['seq'] += 1
    return m

def profile(v):
    n = v[H]
    vp = (v[VP]+3.0)/(n+10.)
    pr = (v[PR]+1.7)/(n+10.)
    ag = (v[PB]+2.)/(v[PA]+6.)
    fold = (v[FOLD]+2.2)/(v[FACE]+4.)
    maniac = clamp((ag-.46)*2.6, 0., .9)*min(1., v[PA]/9.)
    return vp, pr, ag, fold, maniac

def seat_position(state, sid):
    live = [s.seat for s in state.seats if s.status != 'busted']
    live.sort()
    # Seat numbers identify the circular table order, with the button rotating.
    after = [x for x in live if x > state.button]+[x for x in live if x <= state.button]
    n = len(after)
    if n == 2:
        return 0 if sid == state.button else 1
    order = after[2:]+after[:2]
    try: return order.index(sid)
    except ValueError: return n-1

def post_position(state, sid):
    live = sorted(s.seat for s in state.seats if s.status != 'busted')
    after = [x for x in live if x > state.button]+[x for x in live if x <= state.button]
    if len(after) == 2: return 1 if sid == state.button else 0
    try: return after.index(sid)
    except ValueError: return 0

def icm_value(stacks, hero, payouts, n):
    """Hero's exact ICM equity for the common top-three payout structure."""
    total = sum(stacks)
    sh = stacks[hero]
    floor = payouts[n-1] if n <= len(payouts) else 0.
    if sh <= 0 or total <= 0: return floor
    ps = list(payouts[:n])+[0.]*max(0, n-len(payouts))
    if n == 1: return ps[0]
    p1 = sh/total
    if all(x == ps[-1] for x in ps[3:]):
        p2 = p3 = 0.
        for j, sj in enumerate(stacks):
            if j == hero or sj <= 0: continue
            rem = total-sj
            p2 += sj/total*sh/rem
            if n > 2:
                for k, sk in enumerate(stacks):
                    if k == hero or k == j or sk <= 0: continue
                    p3 += sj/total*sk/rem*sh/max(1e-12, rem-sk)
        base = ps[3] if n > 3 else floor
        return base+(ps[0]-base)*p1+(ps[1]-base)*p2+((ps[2]-base)*p3 if n > 2 else 0.)
    # Exponential-race inclusion/exclusion gives the same Plackett-Luce
    # placement distribution in O(2**(n-1)), without a permutation tree.
    others = [x for i,x in enumerate(stacks) if i != hero]
    coeff = []
    for k in range(n):
        coeff.append(sum((ps[r]-floor)*(-1 if (r-k)&1 else 1)*math.comb(n-1-k,r-k) for r in range(k,n)))
    sums = [0.]*(1 << len(others))
    result = coeff[0]*sh/total
    for mask in range(1,len(sums)):
        bit = mask & -mask
        sums[mask] = sums[mask^bit]+others[bit.bit_length()-1]
        c = coeff[mask.bit_count()]
        if c: result += c*sh/max(sh,total-sums[mask])
    return floor+result


def eligible_pot(h, sid, cost, pot):
    contrib = h.get('contrib',{})
    if abs(sum(contrib.values())-pot) > 1: return pot
    cap = contrib.get(sid,0)+cost
    return max(0,min(pot,sum(min(c,cap) for c in contrib.values())))

def passive_folder(v):
    return v[H] >= 14 and v[VP] <= .025*v[H] and v[PB] <= 1


def skill_stacks(stacks, live, stats, hero):
    # A demonstrated automatic folder has much less tournament winning power
    # than the ICM assumption of equally skilled players gives it. Discounting
    # its future equity avoids gifting it prizes through unnecessary collisions.
    if stats is None: return stacks
    return [x*(.12 if s.seat != hero and passive_folder(stats[s.seat]) else 1.) for x,s in zip(stacks,live)]

def multiway_call_odds(state, live, opponents, me, cost, h, stats, fallback):
    """Approximate payout odds, including other players busting when we fold.

    Settle side pots under representative opponent winning orders. This is
    bounded (at most seven ICM calls), and preserves simultaneous-bust order.
    """
    contrib = h.get('contrib',{})
    if abs(sum(contrib.values())-state.pot) > 1: return fallback
    if sum(s.status == 'all_in' for s in opponents) < 2: return fallback
    if sum(s.status == 'active' for s in opponents) > 1: return fallback
    n = len(live)
    hi = next(i for i,s in enumerate(live) if s.seat == me.seat)
    ix = {s.seat:i for i,s in enumerate(live)}
    oi = [ix[s.seat] for s in opponents]
    base = [float(s.stack) for s in live]
    starts = [s.stack+contrib.get(s.seat,0) for s in live]
    pay = list(state.config.payouts[:n])+[0.]*max(0,n-len(state.config.payouts))
    order = sorted(oi,key=lambda i:contrib.get(live[i].seat,0),reverse=True)
    candidates = order if len(order)<=3 else [order[0],order[len(order)//2],order[-1]]
    def layers(calling):
        cc = dict(contrib)
        if calling: cc[me.seat] = cc.get(me.seat,0)+cost
        eligible = oi+[hi] if calling else oi
        levels = sorted(set(x for x in cc.values() if x > 0))
        result=[];previous=0
        for level in levels:
            amount = (level-previous)*sum(x>=level for x in cc.values())
            allowed = tuple(i for i in eligible if cc.get(live[i].seat,0)>=level)
            result.append((amount,allowed));previous=level
        return result
    fold_layers,call_layers = layers(False),layers(True)
    def utility(priority,calling):
        stacks = base[:]
        if calling: stacks[hi]-=cost
        for amount,allowed in (call_layers if calling else fold_layers):
            winner = next((i for i in priority if i in allowed),priority[0])
            stacks[winner]+=amount
        if stacks[hi] > 0:
            return icm_value(skill_stacks(stacks,live,stats,me.seat),hi,pay,n)
        alive = sum(x>0 for x in stacks)
        higher = sum(starts[i]>starts[hi] for i,x in enumerate(stacks) if x<=0)
        equal = sum(starts[i]==starts[hi] for i,x in enumerate(stacks) if x<=0)
        rank = alive+higher
        return sum(pay[rank:rank+equal])/max(1,equal)
    uf=ul=0.
    for first in candidates:
        priority = [first]+[i for i in order if i != first]+[hi]
        uf += utility(priority,False)
        ul += utility(priority,True)
    uf/=len(candidates);ul/=len(candidates)
    uw = utility([hi]+order,True)
    return clamp((uf-ul)/max(1e-9,uw-ul),fallback,.95)

def payout_odds(state, opponents, cost, pot, fallback, stats=None, h=None):
    me = next(s for s in state.seats if s.seat == state.seat)
    if cost < .20*max(1, me.stack):
        return fallback
    payouts = state.config.payouts
    if not payouts or len(payouts) < 2 or not any(payouts[1:]): return fallback
    live = [s for s in state.seats if s.status != 'busted']
    n = len(live)
    if n < 2: return fallback
    if len(opponents) != 1:
        return multiway_call_odds(state,live,opponents,me,cost,h,stats,fallback) if h else fallback
    hi = next(i for i,s in enumerate(live) if s.seat == state.seat)
    oi = next(i for i,s in enumerate(live) if s.seat == opponents[0].seat)
    stacks = [float(s.stack) for s in live]
    stacks[oi] += max(0,state.pot-pot)  # money outside hero's eligible side pots
    cost = min(cost, me.stack)
    fold = stacks[:]; fold[oi] += pot
    win = stacks[:]; win[hi] += pot
    lose = stacks[:]; lose[hi] -= cost; lose[oi] += pot+cost
    f = icm_value(skill_stacks(fold,live,stats,state.seat), hi, payouts, n)
    w = icm_value(skill_stacks(win,live,stats,state.seat), hi, payouts, n)
    l = icm_value(skill_stacks(lose,live,stats,state.seat), hi, payouts, n)
    return clamp((f-l)/max(1e-9, w-l), fallback, .92)

def pressure(state, me):
    live = [s for s in state.seats if s.status != 'busted']
    n = len(live)
    pay = state.config.payouts or []
    paid = sum(x > 0 for x in pay)
    if paid <= 1 or n <= 2 or n > paid+2: return 0.
    chips = me.stack+me.bet
    shorter = sum(0 < s.stack+s.bet < chips*.45 for s in live if s.seat != me.seat)
    cover = sum(s.stack+s.bet >= chips*.95 for s in live if s.seat != me.seat)
    p = (.018 if n == paid+2 else .045 if n == paid+1 else .025)
    return p*(1+.45*shorter)*(.5+.5*min(2,cover))

def opponent_range(state, h, sid, stats):
    vp, pr, ag, fold, maniac = profile(stats[sid])
    n = state.players_remaining
    pos = seat_position(state, sid)
    if n == 2: default = .75 if sid == state.button else .44
    elif pos == n-1: default = .34
    elif pos == n-2: default = .60
    else:
        left = n-pos-1
        default = {2:.48,3:.34,4:.26,5:.21,6:.175,7:.15}.get(left,.16)
    role = h['pf'].get(sid, 0)
    nr = len(h['raises'])
    if role >= 4:
        base = .055 if role == 4 else .033
        p = (base*25+stats[sid][PFRR]*(1. if role == 4 else .65))/(25+stats[sid][PFOP])
        p = p*(1-maniac)+max(.10,pr*.8)*maniac
        repeated = sum(seat == sid for seat,_ in h['raises'])
        if repeated >= 2 and len(h['raises']) >= 4:
            amounts = [x[1] for x in h['raises']]
            small = sum(b-a <= 1.1*state.blinds[1] for a,b in zip(amounts,amounts[1:]))
            if small >= len(amounts)-2: p = max(p,.30 if repeated == 2 else .65)
    elif role == 3:
        p = clamp(default*(.6+.4*pr/.18), .06, .95)
    elif role == 2:
        p = clamp(vp*.85+.035, .10, .65)
    elif role == 1:
        p = clamp(vp*1.35+.10, .28, 1.)
    else:
        p = .85 if not nr else clamp(vp+.12, .18, 1.)
    if h['raises'] and role >= 3:
        last = next((amt for seat,amt in reversed(h['raises']) if seat == sid), state.blinds[1]*2)
        bb = state.blinds[1]
        s = next(s for s in state.seats if s.seat == sid)
        if last > 5*bb and maniac < .35:
            if s.stack == 0 and last < 15*bb:
                left = n-pos-1
                pushwidth = {1:.62,2:.45,3:.32,4:.25,5:.20,6:.17,7:.15}.get(left,.35)
                pushwidth *= clamp((10/(last/bb+1))**.5,.70,1.4)
                p = pushwidth*.75+p*.25
            elif role >= 4 and s.stack == 0 and last < 25*bb:
                p = max(p,.06+.0035*max(0,20-last/bb)+.015*max(0,pos-(n-4)))
                if stats[sid][H] > 20 and pr < .09: p *= .7
            else: p *= .65 if last < 12*bb else .43
    return clamp(p, .025, 1.)

def texture(boardids):
    ranks = [i//4 for i in boardids]
    counts = [0]*4
    for i in boardids: counts[i%4] += 1
    distinct = set(ranks)
    mask = sum(1 << r for r in distinct)
    if 12 in distinct: mask |= 1 << 13  # used only for coarse connectedness below
    connected = max((sum(r in distinct for r in range(lo,lo+5)) for lo in range(9)), default=0)
    wet = max(counts) >= 2 and len(boardids) == 3 or max(counts) >= 3 or connected >= 3
    return ranks, counts, distinct, connected, wet

def made_quality(a, b, value, context):
    counts, top, second, bcat, bsuits, boardmask, bvalue, topflush, maxstraight = context
    r1, r2 = a//4, b//4
    cat = value >> 24
    if cat >= 4:
        if value == bvalue: return .24  # playing a completed board
        if cat == 4:
            if max(bsuits) >= 4: return .55
            if max(bsuits) >= 3: return .83
            high = (value >> 16)&15
            return .95 if high >= maxstraight else .83
        if cat == 5:
            fs = next((i for i,x in enumerate(bsuits) if x >= 3),-1)
            if fs >= 0 and bsuits[fs] >= 4:
                r = max(r1 if a%4 == fs else -1,r2 if b%4 == fs else -1)
                return .985 if r == topflush[0] else .92 if r == topflush[1] else .80 if r == topflush[2] else .64
            return .87 if bcat >= 1 else .97
        if cat == 6 and bcat >= 2:
            tr = (value >> 16)&15
            return .99 if tr >= top else .88
        return .99
    if cat == 3:
        if max(bsuits) >= 4: return .50
        if max(bsuits) >= 3: return .80
        tr = (value >> 16) & 15
        return .90 if counts[tr] < 3 else .25+.012*max(r1,r2)
    if cat == 2:
        if max(bsuits) >= 4: return .45
        if max(bsuits) >= 3: return .70
        p1, p2 = (value >> 16)&15, (value >> 12)&15
        if counts[p1] >= 2 and counts[p2] >= 2:
            return .22+.012*max(r1,r2)
        if bcat >= 1:
            if r1 == r2: return .74 if r1 > top else .58
            own = r1 if r1 in (p1,p2) and counts[r1] == 1 else r2 if r2 in (p1,p2) and counts[r2] == 1 else -1
            return .75 if own == top else .62 if own >= 0 else .32
        return .86
    if cat == 1:
        pair = (value >> 16)&15
        if r1 == r2:
            return .76 if r1 > top else .55 if r1 >= second else .40
        if counts[pair] == 1:
            kicker = r2 if r1 == pair else r1
            return (.64+.006*kicker) if pair == top else .49 if pair >= second else .34
        return .16+.008*max(r1,r2)
    return .09+.008*max(r1,r2)


def shove_ev(state, me, opponent, risk_chips, pot, eq, fold_equity, stats=None):
    """Expected chip gain, or exact ICM gain near the money, for a shove."""
    risk_chips = min(me.stack, risk_chips, max(0,opponent.stack+opponent.bet-me.bet))
    their_call = min(opponent.stack, max(0,risk_chips+me.bet-opponent.bet))
    if risk_chips <= 0: return -1.
    pay = state.config.payouts or []
    live = [s for s in state.seats if s.status != 'busted']
    n = len(live)
    if n > sum(x > 0 for x in pay)+2 or n == 2 or len(pay)<2 or not any(pay[1:]):
        return fold_equity*pot+(1-fold_equity)*(eq*(pot+their_call+risk_chips)-risk_chips)
    hi = next(i for i,s in enumerate(live) if s.seat == me.seat)
    oi = next(i for i,s in enumerate(live) if s.seat == opponent.seat)
    base = [float(s.stack) for s in live]
    fold = base[:]; fold[oi] += pot
    steal = base[:]; steal[hi] += pot
    win = base[:]; win[hi] += pot+their_call; win[oi] -= their_call
    lose = base[:]; lose[hi] -= risk_chips; lose[oi] += pot+risk_chips
    uf = icm_value(skill_stacks(fold,live,stats,me.seat),hi,pay,n)
    us = icm_value(skill_stacks(steal,live,stats,me.seat),hi,pay,n)
    uw = icm_value(skill_stacks(win,live,stats,me.seat),hi,pay,n)
    ul = icm_value(skill_stacks(lose,live,stats,me.seat),hi,pay,n)
    # Normalize to chip units so callers can use a common small EV margin.
    return (fold_equity*(us-uf)+(1-fold_equity)*(eq*uw+(1-eq)*ul-uf))*sum(base)/max(1,sum(pay))


def open_shove(state, me, actionable, stats, hk, pot, bb, n):
    stackbb = (me.stack+me.bet)/bb
    fes = 1.; call_sum = 0.; weighted_width = 0.
    biggest = max(actionable,key=lambda s:s.stack+s.bet)
    threat = -1.
    for opp in actionable:
        v = stats[opp.seat]
        vp,pr,ag,ff,man = profile(v)
        # Calling ranges widen when the shover has fewer players behind.
        cp = (.27 if len(actionable)==1 else .17 if len(actionable)==2 else .11)
        cp *= clamp((10/(stackbb+2))**.55,.65,1.7)
        if n == 4 and pressure(state,opp) > .04: cp *= .72
        # Empirical participation distinguishes stations and automatic folders.
        empirical = clamp((vp-.30)*1.45+.20,.035,.95)
        reliability = min(.85,v[H]/22.)
        cp = clamp(cp*(1-reliability)+empirical*reliability,.025,.92)
        t = cp*min(me.stack,opp.stack+opp.bet)
        if t > threat: biggest = opp; threat = t
        fes *= 1-cp
        call_sum += cp; weighted_width += cp*cp
    if not call_sum:return False
    width = weighted_width/call_sum
    eq = pf_equity(hk,width)
    if call_sum > .6 and len(actionable)>1: eq *= .94
    ev = shove_ev(state,me,biggest,me.stack,pot,eq,fes,stats)
    return ev > bb*.025

def board_context(ids):
    branks, suits, bset, conn, wet = texture(ids)
    bv = eval7.evaluate([CARDS[i] for i in ids])
    sr = sorted(bset)
    mask = sum(1 << r for r in bset)
    fs = next((i for i,x in enumerate(suits) if x >= 3),-1)
    tf = [r for r in range(12,-1,-1) if r*4+fs not in ids][:3] if fs >= 0 else [-1]*3
    ms = max((i+4 for i in range(9) if (mask & (31 << i)).bit_count() >= 3),default=3)
    return ([branks.count(r) for r in range(13)],sr[-1],sr[-2] if len(sr)>1 else sr[-1],bv>>24,suits,mask,bv,tf,ms)


def has_draw(a,b,ctx):
    suits=ctx[4]; sa,sb=a%4,b%4
    flushn=max(suits[sa]+1+(sa==sb),suits[sb]+1+(sa==sb))
    return (flushn==4 and max(suits)<4 or STRAIGHT_DRAW[ctx[5] | (1 << (a//4)) | (1 << (b//4))])


def action_weight(code,fraction,q,draw,street,af,man,bluff,raise_bluff):
    if code == 4:
        # A raise is much stronger evidence than an opening bet. High c-bet
        # frequency alone does not imply that an opponent raises as a bluff.
        w = 1. if q >= .95 else .70 if q >= .85 else .24 if q >= .73 else .08 if q >= .63 else .018 if q >= .45 else .004
        if fraction >= 1. and q < .85: w *= .45
        if draw: w=max(w,.15 if street==0 else .055)
        return w*(1-raise_bluff)+raise_bluff*.8
    if code >= 3:
        if q >= .85: w=1.
        elif q >= .63: w=.85 if fraction<.55 else .65 if street<2 else .42
        elif q >= .45: w=.50 if fraction<.4 else .20 if street<2 else .10
        else: w=.22 if fraction<.4 else .09
        if draw: w=max(w,.65)
        if street==2 and fraction>=.5 and q<.45: w*=.50
        if q<.45 and not draw:
            w*=clamp(af/.33,.22,1.4)
            if street==2: w*=bluff
        # Preserve an observed aggressive bettor's air without erasing
        # previous-street evidence or flattening the range of a raise.
        return w*(1-man*.70)+man*.70*.90
    if code==2: return (1. if q>=.45 or draw else .22)*(1-man*.4)+man*.4
    return 1.


def equity(state,h,opponents,stats,heroids,rngseed):
    ids=[CARD_INDEX[c] for c in state.board]; board=[CARDS[i] for i in ids]
    hero=[CARDS[i] for i in heroids]; dead=sum(1 << i for i in ids+heroids)
    ctx=board_context(ids); hv=eval7.evaluate(hero+board)
    quality=made_quality(*heroids,hv,ctx)
    draws=len(ids)<5 and has_draw(*heroids,ctx)
    wet=texture(ids)[-1]; street=len(ids)-3
    ag=h['ag']
    opp=max(opponents,key=lambda s:(s.seat==ag,h['acts'].get(s.seat,[[0,0]]*3)[street][0],s.bet))
    sid=opp.seat; v=stats[sid]
    p=opponent_range(state,h,sid,stats)
    vp,pr,af,ff,man=profile(v)
    acts=h['acts'].get(sid,[[0,0.],[0,0.],[0,0.]])
    bluff=clamp((v[RBLUFF]+1.5)/(v[RSHOW]+6.)/.25,.35,2.5)
    # Only revealed weak raises or an unmistakable serial minraiser justify
    # treating a raise as broadly as an ordinary bet.
    raise_bluff=clamp((v[XWEAK]+.25)/(v[XSHOW]+6.),0.,.60)
    if v[NR]>8 and v[MR]/v[NR]>.85 and man>.45: raise_bluff=max(raise_bluff,man*.75)
    decision_ms=state.config.decision_ms or 1
    sample=RANGES[width_index(p)]
    if state.time_bank_ms<80 or decision_ms<.8: sample=sample[::2]
    if decision_ms<.4: sample=sample[::2]
    # Condition each candidate on the board that was visible for each action.
    # This avoids keeping random turn air after a large flop bet or call.
    previous=[]
    if state.time_bank_ms>=40 and decision_ms>=.5:
        for st in range(street):
            code,frac=acts[st]
            if code>=2:
                oldids=ids[:3+st]
                previous.append((st,code,frac,[CARDS[i] for i in oldids],board_context(oldids)))
    code,frac=acts[street]; weighted=[]; total=won=0.; raw=[]
    for entry,a,b,mask,noise in sample:
        if mask & dead: continue
        raw.append(entry)
        val=eval7.evaluate(entry[0]+board)
        q=made_quality(a,b,val,ctx)
        draw=len(ids)<5 and has_draw(a,b,ctx)
        w=action_weight(code,frac,q,draw,street,af,man,bluff,raise_bluff)
        for st,pc,pf,oldboard,oldctx in previous:
            ov=eval7.evaluate(entry[0]+oldboard)
            oq=made_quality(a,b,ov,oldctx)
            od=has_draw(a,b,oldctx)
            # Temper historical evidence: some strategies barrel independent
            # of their cards, and action likelihoods are approximations.
            w*=max(.025,action_weight(pc,pf,oq,od,st,af,man,bluff,raise_bluff))**.70
        if len(opponents)>2 and code>=3 and q<.85: w*=.70
        total+=w; weighted.append((total,entry))
        if len(ids)==5: won+=w*(1. if hv>val else .5 if hv==val else 0.)
    if total<=0 or not weighted:
        filtered=raw or [entry for entry,a,b,mask,noise in RANGES[-1] if not mask&dead]
    else:
        # Systematic resampling keeps small posterior ranges represented,
        # unlike independent rejection, which could leave only a few hands.
        filtered=[];j=0;count=96 if len(sample)>60 else 64
        offset=((rngseed*1103515245+sum(ids)*12345)&65535)/65536.
        for i in range(count):
            target=(i+offset)*total/count
            while j<len(weighted)-1 and weighted[j][0]<target:j+=1
            filtered.append(weighted[j][1])
    if len(ids)==5 and total>0:eq=won/total
    elif len(ids)==5:eq=float(eval7.py_hand_vs_range_exact(hero,filtered,board))
    else:eq=float(eval7.py_hand_vs_range_monte_carlo(hero,filtered,board,96 if state.time_bank_ms<80 or decision_ms<.8 else 160))
    if len(opponents)>1:eq=eq**(1+.63*(len(opponents)-1))
    return clamp(eq,0.,1.),quality,draws,wet,hv>>24,opp

class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        try:
            return self._act(state,memory)
        except Exception:
            for k,fn in (('check',Action.check),('fold',Action.fold),('call',Action.call)):
                if any(kind(a) == k for a in state.legal_actions): return fn(),memory
            r = next(a for a in state.legal_actions if kind(a) == 'raise')
            return Action.raise_to(int(r.min_amount)),memory

    def _act(self, state, memory):
        legal = {kind(a):a for a in state.legal_actions}
        # Centralize every return through this legality guard.
        def finish(k, amount=0):
            if k == 'raise' and 'raise' in legal:
                r = legal['raise']; amount = int(clamp(int(amount),int(r.min_amount),int(r.max_amount)))
                action = Action.raise_to(amount)
            elif k == 'call' and 'call' in legal: action = Action.call()
            elif k == 'fold' and 'fold' in legal: action = Action.fold()
            elif 'check' in legal: action = Action.check()
            elif 'fold' in legal: action = Action.fold()
            elif 'call' in legal: action = Action.call()
            else:
                r = legal['raise']; action = Action.raise_to(int(r.min_amount))
            data = pickle.dumps(m,protocol=4)
            memory_limit = state.config.memory_bytes
            if memory_limit is not None and len(data) > memory_limit: data = b''
            return action,data
        m = update(state,memory)
        h = m['hand']; stats = m['stats']
        me = next(s for s in state.seats if s.seat == state.seat)
        opponents = [s for s in state.seats if s.seat != state.seat and s.status in ('active','all_in')]
        if not opponents: return finish('check')
        actionable = [s for s in opponents if s.status == 'active' and s.stack > 0]
        bb = max(1, state.blinds[1]); pot = max(1,state.pot)
        cost = min(state.to_call,me.stack)
        callpot = eligible_pot(h,state.seat,cost,pot) if cost else pot
        heroids = [CARD_INDEX[c] for c in state.cards]
        hk = hand_key(*heroids)
        pct = PERCENTILE[hk]
        seed = (state.hand_number*2654435761+state.seat*2246822519+m['seq']*3266489917+heroids[0]*101+heroids[1]*19)&0xffffffff
        rnd = ((seed ^ (seed >> 16))*2246822519 & 0xffffffff)/4294967296.
        risk = pressure(state,me)
        paid = sum(x > 0 for x in (state.config.payouts or []))
        folders = sum(passive_folder(stats[s.seat]) for s in state.seats if s.seat != state.seat and s.status != 'busted')
        if paid > 1 and state.players_remaining-folders <= paid+1 and folders:
            risk = max(risk,min(.15,.025*folders+.025*max(0,paid+1-state.players_remaining+folders)))
        pos = seat_position(state,state.seat)
        n = state.players_remaining
        postpos = post_position(state,state.seat)
        ip = all(post_position(state,s.seat) < postpos for s in actionable)
        effective = min(me.stack+me.bet,max(s.stack+s.bet for s in opponents))
        spr = me.stack/max(1,pot)
        if not state.board:
            raises = h['raises']; limps = [x for x in h['limps'] if x != state.seat]
            nr = len(raises)
            own_raise = any(sid == state.seat for sid,_ in raises)
            behind = [s for s in actionable if s.seat not in h['acted']]
            if nr == 0:
                if not actionable and cost:
                    eq = pf_equity(hk,1.)**(1+.60*max(0,len(opponents)-1))
                    need = payout_odds(state,opponents,cost,callpot,cost/(callpot+cost),stats,h)
                    return finish('call' if eq >= need+.005 else 'fold')
                # Late position grows naturally as folded players disappear.
                left = len(actionable)
                if n == 2: opening = .80 if state.seat == state.button else .60
                else:
                    opening = {1:.65,2:.46,3:.33,4:.26,5:.21,6:.175,7:.15}.get(left,.15)
                    if pos == n-2: opening = max(opening,.58)  # small blind
                opening *= 1-risk*2
                tight = 1.
                for s in actionable:
                    v = stats[s.seat]
                    vp,pr,ag,ff,man = profile(v)
                    op = seat_position(state,s.seat)
                    if op == n-1 and v[BBFOLD]+v[BBPLAY] > 0:
                        defense = (v[BBPLAY]+3.)/(v[BBFOLD]+v[BBPLAY]+6.)
                    else: defense = vp*(1.55 if op == n-1 else 1.20 if op == n-2 else 1.)
                    tight *= 1-clamp(defense,.04,.85)
                if not limps and tight > .66: opening = max(opening,.90)
                if limps: opening *= .80
                stackbb = effective/bb
                if not limps and stackbb <= 12 and 'raise' in legal:
                    opening *= 1.10 if stackbb < 8 else .92
                    if pct < min(.98,opening*1.35) and open_shove(state,me,actionable,stats,hk,pot,bb,n):
                        return finish('raise',me.bet+me.stack)
                    return finish('check' if not cost else 'fold')
                if pct < opening and 'raise' in legal:
                    size = (2.6 if n > 2 and pos == n-2 else 2.15)*bb+len(limps)*bb
                    if stackbb < 18 and pct < .08: size = me.bet+me.stack
                    return finish('raise',max(size,legal['raise'].min_amount))
                if not cost: return finish('check')
                # Completing a small blind or joining a cheap multiway pot.
                odds = cost/(callpot+cost)
                if cost <= bb and limps and pct < .60 and odds < .23 and me.stack > 12*bb:
                    return finish('call')
                return finish('fold')
            aggressor = next((s for sid,_ in reversed(raises) for s in opponents if s.seat == sid),opponents[0])
            p = opponent_range(state,h,aggressor.seat,stats)
            vp,pr,ag,ff,man = profile(stats[aggressor.seat])
            av = stats[aggressor.seat]
            man = max(man,clamp(((av[PFRR]+1.5)/(av[PFOP]+20)-.15)*2.,0.,.85))
            if sum(sid == aggressor.seat for sid,_ in raises) >= 2 and len(raises) >= 4:
                amounts = [x[1] for x in raises]
                if sum(b-a <= 1.1*bb for a,b in zip(amounts,amounts[1:])) >= len(amounts)-2: man = max(man,.85)
            eq = pf_equity(hk,p)
            callers = sum(s.bet >= max(aggressor.bet,bb*2) and s.seat != aggressor.seat for s in opponents)
            if callers: eq = eq ** (1+.46*callers)
            odds = cost/(callpot+cost)
            allin_call = cost >= me.stack*.90 or not actionable or effective <= max(me.bet+cost,aggressor.bet)*1.25
            if allin_call:
                threshold = payout_odds(state,opponents,cost,callpot,odds,stats,h)+.012
                if len(behind)>1: threshold += .013*(len(behind)-1)
                return finish('call' if eq > threshold else 'fold')
            # Value reraises versus the inferred opening range. Loose serial
            # minraisers require substantially wider value ranges.
            raise_threshold = .57 if nr == 1 else .61 if nr == 2 else .66
            can_value = eq > raise_threshold+risk and pct < (.19 if man > .5 or p > .55 else .14 if nr == 1 and p > .32 and not callers else .08 if nr == 1 else .045)
            if hk == 'AA' or hk == 'KK' and (nr <= 2 or p > .05 or risk < .035): can_value = True
            if can_value and 'raise' in legal:
                amount = (3.0 if ip else 3.6)*max(s.bet for s in opponents)+callers*max(s.bet for s in opponents)
                if effective <= 24*bb or amount >= effective*.38: amount = me.bet+me.stack
                return finish('raise',amount)
            # Short-stack reshoves capture dead chips without having to realize
            # marginal equity in a shallow pot out of position.
            if nr == 1 and not own_raise and not callers and effective <= 22*bb and pct < .23 and p > .17 and 'raise' in legal:
                cp = min(p,.075+.003*max(0,20-effective/bb))
                cp = cp*(1-man)+p*man
                fe = clamp(1-cp/p,.02,.70)
                fe *= .93**max(0,len(behind)-1)
                shoveeq = pf_equity(hk,cp)
                if shove_ev(state,me,aggressor,me.stack,pot,shoveeq,fe,stats) > .12*bb:
                    return finish('raise',me.bet+me.stack)
            # Sparse blocker bluffs when deep, in position, against a genuine
            # opening range. No multiway or repeated-raise bluff wars.
            a,b = sorted([i//4 for i in heroids],reverse=True)
            suited = heroids[0]%4 == heroids[1]%4
            bluff = nr == 1 and not callers and not own_raise and effective > 32*bb and risk < .04
            if bluff and a == 12 and suited and b <= 3 and rnd < .15 and p < .40 and 'raise' in legal:
                return finish('raise',max(s.bet for s in opponents)*(3.0 if ip else 3.6))
            # Cheap pot odds do not compensate for dominated offsuit holdings
            # and poor position. Keep broad big-blind defense versus steals.
            pair = a == b
            small_blind = n > 2 and pos == n-2
            big_blind = pos == n-1
            if not own_raise and n > 2 and not pair:
                if small_blind and pct > (.20 if suited else .095): return finish('fold' if cost else 'check')
                if not big_blind and not suited and pct > (.14 if p > .35 else .09): return finish('fold' if cost else 'check')
                if big_blind and not suited and p < .25 and pct > .37: return finish('fold' if cost else 'check')
            realization = .94 if ip else .82
            if small_blind: realization -= .07
            if not suited and not pair and not big_blind: realization -= .05
            if effective/bb < 15: realization += .04
            if len(opponents) > 2: realization -= .04
            if suited: realization += .025
            if a-b <= 2: realization += .015
            required = odds+risk*.7+.015*(max(0,len(behind)-1))
            if eq*realization > required and cost < me.stack*.30:
                return finish('call')
            # Small pairs can profitably set-mine in deep pots.
            if len(hk) == 2 and cost < effective/19 and cost < 4*bb and nr <= 2 and risk < .05:
                return finish('call')
            return finish('fold' if cost else 'check')
        if not actionable and not cost: return finish('check')
        if len(state.board) == 5:
            bv = eval7.evaluate([CARDS[CARD_INDEX[c]] for c in state.board])
            bc = bv >> 24
            shared_nuts = bc == 8 and ((bv >> 16)&15) == 12
            shared_nuts |= bc == 7 and ((bv >> 12)&15) == 12
            if bc == 4 and ((bv >> 16)&15) == 12:
                shared_nuts |= max(sum(c[1] == su for c in state.board) for su in SUITS) < 3
            if shared_nuts: return finish('call' if cost else 'check')
        eq,q,draw,wet,cat,aggressor = equity(state,h,opponents,stats,heroids,seed)
        street = len(state.board)-3
        vp,pr,ag,ff,man = profile(stats[aggressor.seat])
        odds = cost/(callpot+cost)
        own_pre = bool(h['raises'] and h['raises'][-1][0] == state.seat)
        last_ag = h['ag']
        if cost:
            required = payout_odds(state,opponents,cost,callpot,odds,stats,h)
            required += risk*.6 if cost < me.stack*.20 else 0.
            if street < 2 and cost < me.stack*.85:
                required += .035 if not draw else .008
                if not ip: required += .015
            # Raising needs equity versus a continuing range, not just versus
            # all hands in the bettor's original range.
            raise_eq = .81 if street < 2 else .86
            if man > .45: raise_eq -= .09
            if cost < pot*.16: raise_eq -= .06
            if len(opponents) > 1: raise_eq += .035
            if eq > raise_eq+risk*.5 and q >= (.62 if man > .4 else .73) and 'raise' in legal:
                amount = me.bet+cost+(.80 if wet else .65)*(pot+cost)
                if amount >= .48*(me.bet+me.stack) or spr < 1.6: amount = me.bet+me.stack
                return finish('raise',amount)
            # Semi-bluff strong draws with enough fold equity and a useful SPR.
            if draw and street < 2 and len(opponents) == 1 and h['nb'] == 1 and cost < pot*.45 and spr > 2.8 and ff > .55 and man < .45 and eq > .38 and rnd < .16 and risk < .045 and 'raise' in legal:
                return finish('raise',me.bet+cost+.8*(pot+cost))
            if eq >= required: return finish('call')
            return finish('fold')
        if 'raise' not in legal: return finish('check')
        # When the entire continuing range is very weak, bet smaller and wider;
        # against calling stations, increase value sizing and suppress bluffs.
        value_threshold = .64 if street == 2 else .66
        if len(opponents) > 1: value_threshold += .055*min(3,len(opponents)-1)
        if man > .40: value_threshold -= .05
        value = eq > value_threshold and q >= (.46 if street < 2 else .55)
        if value:
            fraction = .65 if wet else .50
            if eq > .88: fraction = .85 if wet or street == 2 else .70
            if man > .45: fraction = .85
            amount = me.bet+max(bb,int(pot*fraction))
            if spr < 1.5 and eq > .76: amount = me.bet+me.stack
            elif amount >= me.stack*.60 and eq > .83: amount = me.bet+me.stack
            # Some medium hands are better as bluff catchers out of position.
            if not ip and not own_pre and q < .75 and street == 0 and len(opponents)>1:
                return finish('check')
            return finish('raise',amount)
        if len(opponents) == 1 and spr > 1.5 and man < .65:
            checked = aggressor.seat in h['acted']
            av = stats[aggressor.seat]
            # Use street-specific responses, with a modest field-informed
            # prior. Only public observations at this table update this rate.
            prior_fold = (.48,.55,.60)[street]
            fold_est = (av[SFOLD+street]+8*prior_fold)/(av[SFACE+street]+8)
            previous_hero = h['acts'].get(state.seat,[[0,0.]]*3)
            barrel = street > 0 and previous_hero[street-1][0] >= 3
            frequency = .0
            if street == 0 and own_pre:
                frequency = .65 if not wet else .36
                if q > .40 and not draw: frequency *= .45
            elif ip and checked:
                frequency = .35 if street == 0 else .22
            if draw and street < 2: frequency = max(frequency,.55 if ip else .32)
            if street == 1 and barrel and q < .45 and fold_est > .48:
                frequency = max(frequency,.48 if ip else .30)
            if street == 1 and ip and checked and q < .40 and fold_est > .52:
                frequency = max(frequency,.42)
            if street == 2:
                frequency = .0
                if ip and checked and q < .45 and eq < .38 and fold_est > .49:
                    frequency = .58 if barrel else .45
                if ff > .72 and q < .45: frequency = max(frequency,.50)
                if fold_est < .40: frequency *= .25
            if ff < .40: frequency *= .35
            if man > .45: frequency *= .65
            if risk > .05: frequency *= .75
            if rnd < frequency:
                fraction = .34 if street == 0 and own_pre and not wet else .55
                return finish('raise',me.bet+max(bb,int(pot*fraction)))
        return finish('check')
