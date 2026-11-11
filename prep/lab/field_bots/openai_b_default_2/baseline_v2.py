"""Tournament poker agent. Runtime state is exclusively the SDK's per-table memory."""
import bisect
import json
import math
import marshal
import os
import random
import time

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

with open(os.path.join(os.path.dirname(__file__), 'preflop.json')) as _f:
    _DATA = json.load(_f)
PCT = _DATA['rank']
EQ = _DATA['equity']
FRACS = _DATA['fractions']
RANKS = '23456789TJQKA'
CARDS = tuple(eval7.Card(r + s) for r in RANKS for s in 'cdhs')
CARD_ID = {str(c): i for i, c in enumerate(CARDS)}

def hand_key(a, b):
    x, y = a // 4, b // 4
    if x == y:
        return RANKS[x] * 2
    return RANKS[max(x, y)] + RANKS[min(x, y)] + ('s' if a % 4 == b % 4 else 'o')

# The equity ordering and an opening ordering have different objectives. Reward
# hands which realize their equity well in deep pots (suited and connected).
_OPEN_ORDER = sorted(PCT, key=lambda k: PCT[k] - (.065 if k[-1:] == 's' else 0)
                     - (.035 if len(k) == 3 and abs(RANKS.index(k[0])-RANKS.index(k[1])) == 1 else 0)
                     + (.065 if k[-1:] == 'o' and k[0] == 'A' and k[1] in '23456789' else 0))
OPEN = {}
_cum = 0
for _k in _OPEN_ORDER:
    _n = 6 if len(_k) == 2 else 4 if _k[-1] == 's' else 12
    OPEN[_k] = (_cum + _n/2) / 1326
    _cum += _n
COMBOS = []
for _a in range(52):
    for _b in range(_a):
        _k = hand_key(_a, _b)
        COMBOS.append((_a, _b, (1 << _a) | (1 << _b), PCT[_k],
                       ((CARDS[_a], CARDS[_b]), 1.0), _a//4, _b//4, _a%4, _b%4))
# Fixed shuffled enumeration: immutable, independent of the tournament's tables.
random.Random(771831).shuffle(COMBOS)
POOLS = tuple(tuple(c for c in COMBOS if c[3] <= f) for f in FRACS)
STRAIGHT_DRAW = bytearray(8192)
for _m in range(8192):
    _r = _m | ((_m >> 12) & 1) << 13
    # Standard windows plus the wheel; the wheel uses a separate ace-low mask.
    STRAIGHT_DRAW[_m] = int(any((_m & (31 << i)).bit_count() >= 4 for i in range(9))
                            or (_m & 0x100f).bit_count() >= 4)

FOLD, CHECK, CALL = Action.fold(), Action.check(), Action.call()

def kind(x):
    k = x.kind
    return getattr(k, 'value', k)


def eq_pre(key, fraction):
    i = bisect.bisect_left(FRACS, fraction)
    row = EQ[key]
    if i == 0:
        return row[0]
    if i >= len(FRACS):
        return row[-1]
    w = (fraction-FRACS[i-1])/(FRACS[i]-FRACS[i-1])
    return row[i-1]*(1-w)+row[i]*w


def joint_equity(values, board_tie=False):
    if not values:
        return 1.0
    if len(values) == 1:
        return values[0]
    if board_tie:
        return math.prod(min(1.,2*q) for q in values)/(len(values)+1)
    # Runouts correlate the heads-up outcomes. A fractional exponent captures
    # some of that correlation instead of assuming independent outcomes.
    return math.prod(values)**(1/(1+.10*(len(values)-1)))


def sidepot_equity(qs, committed, me, call, board_tie=False):
    cap = committed[me]+call
    amounts = [min(x+(call if i == me else 0),cap) for i,x in enumerate(committed)]
    levels = sorted(set(x for x in amounts if x > 0))
    prev = total = weighted = 0.
    for level in levels:
        layer = (level-prev)*sum(x >= level for x in amounts)
        contenders = [q for j,q in qs.items() if amounts[j] >= level]
        weighted += layer*joint_equity(contenders,board_tie)
        total += layer
        prev = level
    return weighted/total if total else joint_equity(list(qs.values()),board_tie)


def icm(stacks, hero, payouts):
    """Exact ICM for the standard three prizes; subset DP for other schedules."""
    h = stacks[hero]
    if h <= 0:
        place = sum(s > 0 for i,s in enumerate(stacks) if i != hero)
        return float(payouts[place]) if place < len(payouts) else 0.0
    total = sum(stacks)
    opp = [s for i, s in enumerate(stacks) if i != hero and s > 0]
    p = list(payouts) + [0.0]*len(stacks)
    # The prize for the last remaining player is constant, so remove it.
    alive = len(opp)+1
    base = p[alive-1]
    p = [x-base for x in p]
    result = base + p[0]*h/total
    if alive == 1:
        return base+p[0]
    if not any(p[3:alive]):
        for j, s in enumerate(opp):
            a = s/total
            rem = total-s
            result += p[1]*a*h/rem
            if p[2] and alive > 2:
                for k, t in enumerate(opp):
                    if j != k:
                        result += p[2]*a*(t/rem)*h/(rem-t)
        return result
    dp = {0: 1.0}
    sums = {0: 0.0}
    for mask in range(1 << len(opp)):
        prob = dp.get(mask, 0.)
        if not prob:
            continue
        used = mask.bit_count()
        rem = total-sums[mask]
        if mask:
            result += p[used]*prob*h/rem
        for i, s in enumerate(opp):
            bit = 1 << i
            if not mask & bit:
                new = mask | bit
                dp[new] = dp.get(new, 0.)+prob*s/rem
                sums[new] = sums[mask]+s
    return result


def fresh_hand(n, number):
    return {'h': number, 'st': 0, 'rc': [0]*4, 'lr': [-1]*4,
            'a': [[0]*n for _ in range(4)], 'r': [[0]*n for _ in range(4)],
            'v': 0, 'p': 0, 'pc': [0]*n, 'pr': [0]*n, 'jam': [0]*n,
            'bet': [0]*n, 'in': [0]*n, 'mx': 0, 'op': -1, 'os': 0,
            'board': [], 'cache': {}}


def update_memory(state, memory):
    ids = [s.seat for s in state.seats]
    # Seat order and IDs remain fixed at a table; no assumptions about their values.
    if memory:
        m = marshal.loads(memory)
    else:
        m = {'ids': ids, 'stats': [[0]*10 for _ in ids], 'd': fresh_hand(len(ids), -1)}
    ids = m['ids']
    ix = {s:i for i,s in enumerate(ids)}
    n = len(ids)
    d = m['d']
    stats = m['stats']
    for e in state.events:
        k = kind(e)
        if k == 'hand':
            d = fresh_hand(n, e.amount)
            for i, s in enumerate(state.seats):
                # Public end-of-hand stacks are not needed: count a hand only
                # for seats which are currently still in the tournament.
                if s.status != 'busted':
                    stats[ix[s.seat]][0] += 1
            continue
        if k == 'board':
            d['board'].extend(e.cards or [])
            d['st'] = min(3, len(d['board'])-2)
            d['bet'] = [0]*n
            d['mx'] = 0
            continue
        if e.seat is None or e.seat not in ix:
            continue
        j = ix[e.seat]
        st = d['st']
        s = stats[j]
        if k in ('ante', 'blind'):
            amount = int(e.amount or 0)
            d['in'][j] += amount
            if k == 'blind':
                d['bet'][j] += amount
                d['mx'] = max(d['mx'], d['bet'][j])
            continue
        if k not in ('fold','check','call','raise'):
            continue
        facing = d['mx'] > d['bet'][j]
        if facing:
            s[6 if st == 0 else 8] += 1
            if k == 'fold':
                s[7 if st == 0 else 9] += 1
        if k == 'fold':
            d['a'][st][j] |= 8
            continue
        if k == 'check':
            d['a'][st][j] |= 1
            if st:
                s[5] += 1
            continue
        if st == 0 and not (d['v'] >> j) & 1:
            d['v'] |= 1 << j
            s[1] += 1
        amount = int(e.amount or 0)
        if k == 'call':
            d['a'][st][j] |= 2
            d['in'][j] += amount
            d['bet'][j] += amount
            if st == 0:
                d['pc'][j] = max(d['pc'][j], d['rc'][0])
            else:
                s[4] += 1
        elif k == 'raise':
            added = max(0, amount-d['bet'][j])
            d['in'][j] += added
            d['bet'][j] = amount
            d['mx'] = max(d['mx'], amount)
            d['rc'][st] += 1
            d['r'][st][j] += 1
            d['lr'][st] = j
            d['a'][st][j] |= 4
            if st == 0:
                d['pr'][j] = d['rc'][0]
                d['jam'][j] = max(d['jam'][j], amount)
                if d['op'] < 0:
                    d['op'], d['os'] = j, amount
                if not (d['p'] >> j) & 1:
                    d['p'] |= 1 << j
                    s[2] += 1
            else:
                s[3] += 1
    # Events are authoritative, but tolerate a new SDK delivering the board as
    # one board event or restoring only its latest public state.
    d['st'] = 0 if len(state.board) == 0 else min(3,len(state.board)-2)
    d['board'] = list(state.board)
    m['d'] = d
    return m, ix


def profile(stats):
    n, vp, pr = stats[:3]
    maniac = n >= 3 and pr >= .74*n
    rock = n >= 6 and vp <= .055*n
    v = (vp+5)/(n+22)
    p = (pr+3)/(n+22)
    if maniac:
        v, p = max(.80, vp/max(1,n)), max(.75,pr/max(1,n))
    if rock:
        v, p = min(v,.10), min(p,.065)
    return v,p,maniac,rock


def range_fraction(j, d, stats, seats, bb):
    v,p,maniac,rock = profile(stats[j])
    if maniac:
        return min(1., max(v, .85))
    pr,pc = d['pr'][j],d['pc'][j]
    if pr:
        if pr >= 3:
            f = .025 if p < .24 else .07
        elif pr >= 2:
            f = max(.035,min(.16,p*.42))
        else:
            f = max(.10,min(.65,p*1.65))
        start = seats[j].stack+d['in'][j]
        if d['jam'][j] >= .70*start and start > 18*bb:
            f *= .55
        return max(.025,f)
    if pc:
        return min(.70,max(.10,v*(.90 if pc == 1 else .5)))
    if (d['v'] >> j) & 1:
        return max(.2,min(.9,v*1.6))
    return 1.0


def made_class(c, value, bmax, bmask, bpairs, bsuits, stage, boardvalue):
    """Coarse relative hand class and draw status for Bayesian range weighting."""
    a,b,_,_,_,r1,r2,s1,s2 = c
    cat = value >> 24
    pair = (value >> 16) & 15
    rm = bmask | (1 << r1) | (1 << r2)
    fd = stage < 3 and ((bsuits[s1] + 1 + int(s1 == s2) >= 4 and bsuits[s1] < 4)
                       or (s1 != s2 and bsuits[s2]+1 >= 4 and bsuits[s2] < 4))
    draw = stage < 3 and (fd or (STRAIGHT_DRAW[rm] and rm != bmask))
    if cat >= 4:
        strength = 4
        if stage == 3 and value == boardvalue:
            strength = 0
        elif cat == 5 and max(bsuits) >= 4:
            fs = bsuits.index(max(bsuits))
            high = max(r1 if s1 == fs else -1, r2 if s2 == fs else -1)
            strength = 2 if high < 8 else 3 if high < 11 else 4
        return strength,draw
    if cat == 3:
        return (1 if (bpairs >> pair) & 1 and not (r1 == pair or r2 == pair) else 4),draw
    if cat == 2:
        second = (value >> 12) & 15
        if (bpairs >> pair) & 1:
            return (1 if (bpairs >> second) & 1 else 2),draw
        return 3,draw
    if cat == 1:
        if (bpairs >> pair) & 1:
            return 0,draw
        return (3 if pair >= bmax else 2 if pair >= bmax-3 else 1),draw
    return 0,draw


def post_equity(hero, board, blocked, fraction, j, d, stats, seed, count=72, deadline=0):
    st = len(board)-2
    cachekey = str(j)+':'+str(len(board))+':'+str(d['a'][st][j])+':'+str(min(2,d['r'][st][j]))
    if cachekey in d['cache']:
        return d['cache'][cachekey]
    idx = min(len(POOLS)-1,bisect.bisect_left(FRACS,fraction))
    pool = POOLS[idx]
    maniac = profile(stats[j])[2]
    # Condition on the latest public action, including a previous street's bet.
    action = d['a'][st][j]
    condstage = st
    if not action:
        for old in range(st-1,0,-1):
            if d['a'][old][j] & 6:
                condstage,action = old,d['a'][old][j]
                break
    cb = board[:condstage+2]
    bmask = bpairs = 0
    bsuits = [0]*4
    for card in cb:
        r = card.rank
        if (bmask >> r) & 1:
            bpairs |= 1 << r
        bmask |= 1 << r
        bsuits[card.suit] += 1
    bmax = bmask.bit_length()-1
    bv = eval7.evaluate(cb) if len(cb) == 5 else -1
    # Relative likelihoods of air, weak pair, medium pair, top pair, strong made hand.
    if maniac or not action:
        weights = (1.,1.,1.,1.,1.)
    elif action & 4:
        weights = (.075,.22,.46,.76,1.) if condstage == 1 else (.055,.15,.38,.70,1.)
        if d['r'][condstage][j] >= 2:
            weights = (.025,.07,.20,.50,1.)
    elif action & 2:
        weights = (.10,.50,.80,.90,.85) if condstage < 3 else (.05,.35,.72,.90,.9)
    else:
        weights = (1.,1.,.9,.72,.55)
    villain = []
    stride = max(1,len(pool)//count)
    offset = (seed+j*23) % stride
    # A deterministic low-discrepancy subset keeps Python work bounded. Every
    # combo is legal before eval7 sees it; eval7's range weights are not used.
    accepted = 0
    for k in range(offset,len(pool),stride):
        c = pool[k]
        if c[2] & blocked:
            continue
        if d['pc'][j] and not d['pr'][j] and c[3] < .025 and not maniac:
            continue
        if maniac or not action:
            w = 1.
        else:
            value = eval7.evaluate(list(c[4][0])+cb)
            strength,draw = made_class(c,value,bmax,bmask,bpairs,bsuits,condstage,bv)
            w = weights[strength]
            if draw and condstage < 3:
                w = max(w,.66 if action & 6 else .95)
        # Stochastic rounding represents likelihoods despite eval7 ignoring the
        # numeric weights in a HandRange. The rounding itself is deterministic.
        copies = int(w*5)
        rand = ((c[2] ^ (c[2] >> 23) ^ seed)*2654435761 & 65535)/65536
        if rand < w*5-copies:
            copies += 1
        if copies:
            villain.extend([c[4]]*copies)
        accepted += 1
        if accepted >= count or (deadline and accepted % 16 == 0 and time.perf_counter_ns() > deadline):
            break
    if not villain:
        villain = [c[4] for c in pool if not c[2] & blocked][:32]
    if not villain:
        return .5
    if len(board) == 5:
        equity = eval7.py_hand_vs_range_exact(hero,villain,board)
    else:
        iterations = 192 if deadline and time.perf_counter_ns() > deadline else 384
        equity = eval7.py_hand_vs_range_monte_carlo(hero,villain,board,iterations)
    d['cache'][cachekey] = equity
    return equity


class Agent(poker_agent_sdk.Agent):
    def act(self,state,memory):
        # No state is stored on self: production may route each turn to a new copy.
        deadline = time.perf_counter_ns()+int(float(state.config.decision_ms or 1)*650000)
        legal = {kind(a):a for a in state.legal_actions}
        default = CHECK if 'check' in legal else FOLD if 'fold' in legal else CALL
        try:
            m,ix = update_memory(state,memory)
            action = self.decide(state,m,ix,legal,deadline)
            k = kind(action)
            if k not in legal:
                action = default
            elif k == 'raise':
                a = legal[k]
                action = Action.raise_to(max(int(a.min_amount),min(int(a.max_amount),int(action.amount))))
            return action,marshal.dumps(m)
        except Exception:
            # Defensive compatibility fallback; tests also exercise the core
            # directly so this boundary cannot conceal implementation failures.
            return default,memory

    def decide(self,s,m,ix,legal,deadline=0):
        d,stats = m['d'],m['stats']
        seats = [next(t for t in s.seats if t.seat == sid) for sid in m['ids']]
        me = ix[s.seat]
        own = seats[me]
        bb = max(1,int(s.blinds[1]))
        stack = int(own.stack)
        call = min(stack,max(0,int(s.to_call)))
        pot = max(1,int(s.pot))
        live = [i for i,t in enumerate(seats) if i != me and t.status in ('active','all_in')]
        active = [i for i in live if seats[i].status == 'active' and seats[i].stack > 0]
        alive = [i for i,t in enumerate(seats) if t.status != 'busted']
        n = len(alive)
        if not live:
            return CHECK if 'check' in legal else CALL
        a,b = [CARD_ID[c] for c in s.cards]
        key = hand_key(a,b)
        percentile = PCT[key]
        seed = (int(s.hand_number)*1103515245 + a*73856093 + b*19349663 + len(s.board)*83492791) & 0xffffffff
        u = ((seed*2654435761) & 0xffffffff)/4294967296
        rlegal = legal.get('raise')
        def raise_to(amount):
            if rlegal is None:
                return CHECK if 'check' in legal else CALL if 'call' in legal else FOLD
            return Action.raise_to(max(int(rlegal.min_amount),min(int(rlegal.max_amount),int(amount))))
        def passive():
            return CHECK if 'check' in legal else FOLD
        # The current pot may contain side pots above our maximum contribution.
        eligible = sum(min(x,d['in'][me]+call) for x in d['in'])
        if 0 < eligible < pot and d['in'][me]+call > 0:
            pot = eligible
        odds = call/(pot+call) if call else 0.
        street = d['st']
        opp_profiles = {j:profile(stats[j]) for j in live}
        fractions = {j:range_fraction(j,d,stats,seats,bb) for j in live}
        order = sorted(t.seat for t in seats if t.status != 'busted')
        if s.button in order:
            bi = order.index(s.button)
            order = order[bi+1:]+order[:bi+1]
        for j in live:
            if d['pr'][j] == 1 and not opp_profiles[j][2]:
                pos = order.index(seats[j].seat)
                factor = 1.6 if pos == len(order)-1 else 1.3 if pos == 0 else max(.68,1.4-.14*(len(order)-1-pos))
                fractions[j] = min(.85,max(.025,fractions[j]*factor))
        # Last aggressor, then the tightest continuing range.
        primary = d['lr'][street]
        if primary not in live:
            primary = min(live,key=lambda j:fractions[j])
        eff = min(stack,max(seats[j].stack+seats[j].bet-own.bet for j in live))
        spr = eff/max(1,pot)
        pressure = 0.
        payouts = list(s.config.payouts or [50,30,20])
        paid = sum(p > 0 for p in payouts)
        if n > 2 and n <= paid+2:
            short = min((t.stack+t.bet for i,t in enumerate(seats) if i in alive),default=stack)
            # Used only for proactive aggression. Big calls use exact ICM below.
            if stack > short*1.5 and stack < max(t.stack+t.bet for t in seats)*.85:
                pressure = .035 if n <= paid else .065
        premium = pressure
        if call > stack*.18 and n > 2 and n <= 6:
            # Assign the contested pot to the main aggressor in the fold/loss
            # branches. This is exact heads-up and conservative multiway.
            ss = [float(t.stack) for t in seats]
            f = ss[:]; f[primary] += pot
            w = ss[:]; w[me] += pot
            l = ss[:]; l[me] -= call; l[primary] += pot+call
            vf = icm(f,me,payouts)
            vw = icm(w,me,payouts)
            vl = icm(l,me,payouts)
            if vw > vl:
                premium = max(pressure,min(.28,(vf-vl)/(vw-vl)-odds))
        if street == 0:
            return self.preflop(s,d,stats,seats,me,live,active,n,bb,stack,call,pot,odds,
                                premium,pressure,fractions,opp_profiles,key,percentile,eff,
                                raise_to,passive,legal,u)
        hero = [CARDS[a],CARDS[b]]
        board = [CARDS[CARD_ID[c]] for c in s.board]
        blocked = (1 << a)|(1 << b)
        for c in s.board:
            blocked |= 1 << CARD_ID[c]
        eq = post_equity(hero,board,blocked,fractions[primary],primary,d,stats,seed,deadline=deadline)
        qs = {primary:eq}
        value = eval7.evaluate(hero+board)
        board_tie = len(board) == 5 and value == eval7.evaluate(board)
        # Joint equity uses a second explicit range in small multiway pots, then
        # a conservative correlation correction for additional opponents.
        if len(live) > 1:
            candidates = [j for j in live if j != primary]
            other = min(candidates,key=lambda j:(j not in active,fractions[j]))
            if not deadline or time.perf_counter_ns() < deadline:
                eq2 = post_equity(hero,board,blocked,fractions[other],other,d,stats,seed,40,deadline)
            else:
                eq2 = max(.01,min(.99,eq+.10*(fractions[other]-fractions[primary])))
            qs[other] = eq2
            for j in candidates:
                if j not in qs:
                    qs[j] = max(.01,min(.99,eq2+.10*(fractions[j]-fractions[other])))
            eq = sidepot_equity(qs,d['in'],me,call,board_tie)
        eq_active = joint_equity([qs[j] for j in active],board_tie)
        cat = value >> 24
        board_ids = [CARD_ID[c] for c in s.board]
        bsuits = [sum(x%4 == suit for x in board_ids) for suit in range(4)]
        ranks = [x//4 for x in board_ids]
        wet = max(bsuits) >= 2 and street == 1 or max(bsuits) >= 3
        wet = wet or (max(ranks)-min(ranks) <= 4 and len(set(ranks)) >= 3)
        maniac = opp_profiles[primary][2]
        rocks = all(opp_profiles[j][3] for j in active) if active else False
        all_station = all(opp_profiles[j][2] for j in active) if active else False
        if call:
            realization = .035 if street == 1 else .018 if street == 2 else 0.
            required = odds+premium+realization
            if call <= max(bb*.6,pot*.08):
                required -= .025
            # Value raises account for the stronger range which continues.
            vthreshold = (.69 if maniac else .80) + .04*(len(active)-1)+pressure
            if rlegal and active and eq_active >= vthreshold:
                size = own.bet+call+int((pot+call)*(.85 if wet else .67))
                if spr < 1.6 or (maniac and eq > .69) or size >= own.bet+stack*.64:
                    size = own.bet+stack
                return raise_to(size)
            if eq >= required:
                return CALL
            return passive()
        if not rlegal or not active:
            return CHECK
        value_threshold = (.57 if all_station else .64)+.055*(len(active)-1)+pressure
        # Value and protection bets, with larger sizes against inelastic callers.
        if eq_active >= value_threshold:
            frac = .72 if wet or all_station else .48
            if street == 3:
                frac = .75 if eq > .84 else .5
            size = own.bet+max(bb,int(pot*frac))
            if spr <= 1.1 and eq > .73:
                size = own.bet+stack
            return raise_to(size)
        if len(live) == 1 and not all_station:
            pfr = d['lr'][0] == me
            lastaggr = d['lr'][street-1] == me if street > 1 else pfr
            oppaction = d['a'][street][primary]
            foldrate = (stats[primary][9]+2)/(stats[primary][8]+5)
            if opp_profiles[primary][3]:
                foldrate = max(.85,foldrate)
            # Small continuation bets on favorable textures; polar river bluffs
            # use blockers and a deliberately modest baseline frequency.
            blufffreq = 0.
            if rocks:
                blufffreq = 1.
            elif street == 1 and pfr and not wet:
                blufffreq = .55 if eq < .5 else .35
            elif street == 1 and pfr and eq > .34:
                blufffreq = .32
            elif street == 2 and lastaggr and eq > .25:
                blufffreq = .25
            elif street == 3 and oppaction & 1 and eq < .28:
                blocker = a//4 == 12 or b//4 == 12
                blufffreq = .22 if blocker else .10
            elif oppaction & 1 and eq < .45 and street < 3:
                blufffreq = .25
            if foldrate > .64:
                blufffreq = max(blufffreq,.8)
            if u < blufffreq and eq < .58:
                return raise_to(own.bet+max(bb,int(pot*(.35 if street == 1 else .55))))
        return CHECK

    def preflop(self,s,d,stats,seats,me,live,active,n,bb,stack,call,pot,odds,
                premium,pressure,fractions,profiles,key,percentile,eff,raise_to,passive,legal,u):
        own = seats[me]
        raises = d['rc'][0]
        maxbet = max(t.bet for t in seats)
        # Position is computed from the public button and clockwise seat IDs.
        order = sorted((t.seat for t in seats if t.status != 'busted'))
        if s.button in order:
            bi = order.index(s.button)
            order = order[bi+1:]+order[:bi+1]
        mypos = order.index(s.seat) if s.seat in order else len(order)//2
        buttondist = len(order)-1-mypos
        behind = [j for j in active if seats[j].bet <= own.bet and not d['a'][0][j]&8]
        # Use all unacted seats for an unopened pot, including the blinds.
        unacted = [j for j in active if not d['a'][0][j]&6]
        in_blind = own.bet > 0
        sb = bool(in_blind and own.bet < bb)
        if raises == 0:
            if n == 2:
                opening = .82 if sb else 1.
            elif buttondist == 0:
                opening = .49
            elif mypos == 0:  # Small blind after the button.
                opening = .46
            elif mypos == 1:  # Big blind gets a free option in limped pots.
                opening = .23
            else:
                opening = max(.15,.35-.045*(buttondist-1))
            limpers = [j for j in live if (d['v'] >> j)&1]
            if limpers:
                opening *= .72
            rocks = sum(profiles[j][3] for j in unacted)
            maniacs = sum(profiles[j][2] for j in live)
            if unacted:
                opening += .42*rocks/len(unacted)
            if maniacs:
                opening = min(opening,.28 if maniacs == 1 else .19)
            opening = max(.05,opening-pressure)
            depth = eff/bb
            # Fold-equity model for open shoves. Call ranges widen for short
            # shoves and in blinds; observed maniacs/folders override priors.
            if 'raise' in legal and depth <= 15 and active:
                fp = 1.
                weights = 0.
                eqsum = 0.
                callers = 0.
                for j in active:
                    cdepth = min(stack,seats[j].stack)/bb
                    f = .40 if cdepth <= 4 else .29 if cdepth <= 7 else .21 if cdepth <= 10 else .14
                    if seats[j].bet >= bb:
                        f *= 1.35
                    if d['v'] >> j & 1:
                        f *= 1.3
                    if profiles[j][2]:
                        f = .97
                    elif profiles[j][3]:
                        f *= .40
                    f = min(.99,f)
                    fp *= 1-f
                    weights += f
                    callers += f
                    eqsum += f*eq_pre(key,f)
                q = eqsum/max(.001,weights)
                conditional = callers/max(.001,1-fp)
                q **= 1+.72*max(0.,conditional-1)
                risk = 1+4*pressure
                ev = fp*pot+(1-fp)*(q*(pot+eff)-(1-q)*eff*risk)
                if ev > max(bb*.08,eff*.008) and (OPEN[key] < max(opening,.62) or depth < 6):
                    return raise_to(own.bet+stack)
                if depth <= 10 and OPEN[key] > opening*.6:
                    return passive()
            if OPEN[key] <= opening and 'raise' in legal:
                size = bb*(2.2 if n > 2 else 2.1)+len(limpers)*bb
                if maniacs and percentile < .09:
                    size = max(size,bb*4)
                if size-own.bet > eff*.32:
                    # Avoid building an awkward pot with a weak short-stack open.
                    if OPEN[key] < opening*.65:
                        size = own.bet+stack
                    elif 'check' in legal:
                        return CHECK
                    else:
                        return passive()
                return raise_to(size)
            if 'check' in legal:
                return CHECK
            # Completing a small blind is useful against wide ranges, and cheap
            # suited/pocket-pair overlimps retain multiway implied odds.
            if sb and call <= bb*.55 and (OPEN[key] < .66 or key[-1:] == 's'):
                return CALL
            if limpers and call <= bb and (len(key) == 2 or key[-1:] == 's') and OPEN[key] < .55:
                return CALL
            return passive()
        primary = d['lr'][0]
        if primary not in live:
            primary = min(live,key=lambda j:fractions[j])
        f = fractions[primary]
        q = eq_pre(key,f)
        # Count voluntary opponents: an unacted blind is not yet a caller.
        involved = [j for j in live if (d['v'] >> j)&1]
        others = [j for j in involved if j != primary]
        if others:
            for j in sorted(others,key=lambda j:fractions[j])[:2]:
                q *= eq_pre(key,fractions[j])**.73
        maniac = profiles[primary][2]
        rlegal = legal.get('raise')
        deep = eff/bb
        # Three-bet a linear value range. Against a raising station, get the
        # money in while ahead instead of gifting unlimited cheap realization.
        continue_f = f if maniac else max(.025,f*.35)
        veq = eq_pre(key,continue_f)
        if len(involved) > 1:
            veq *= .87**(len(involved)-1)
        value3 = veq > (.60+pressure) or key == 'AA' or (key == 'KK' and f > .035)
        if rlegal and active and value3:
            size = max(maxbet*(3.1 if mypos != len(order)-1 else 2.8),pot+call+own.bet)
            if deep <= 22 or maniac or size-own.bet >= eff*.40:
                size = own.bet+stack
            return raise_to(size)
        # Rare blocker three-bets in position, only when the opener has shown
        # folds. They disappear as ICM or stack commitment becomes material.
        foldrate = (stats[primary][7]+2)/(stats[primary][6]+5)
        if (rlegal and raises == 1 and deep > 30 and len(involved) == 1 and not maniac
                and pressure == 0 and buttondist == 0 and key in ('A5s','A4s','A3s','KTs')
                and foldrate > .5 and u < .28):
            return raise_to(maxbet*2.8)
        if call == 0:
            return CHECK
        # Equity realization taxes prevent cheap but dominated cold calls.
        tax = .06 if deep > 18 else .025
        if key[-1:] == 's' or len(key) == 2:
            tax -= .018
        if len(involved) > 1:
            tax += .025
        if raises >= 2 and not maniac:
            tax += .025
        if call >= stack*.60:
            tax = .008
        if maniac and call <= pot*.13:
            tax = .005
        required = odds+premium+max(0,tax)
        if q >= required:
            # Do not cold-call most of a stack and then fold the flop.
            if rlegal and active and call > stack*.30 and q > required+.055 and q > .48:
                return raise_to(own.bet+stack)
            return CALL
        if (len(key) == 2 and call <= eff*.045 and raises <= 1 and eff > 25*bb
                and premium < .05):
            return CALL
        return passive()
