"""Pressure-oriented tournament hold'em. All learned state travels in memory."""
import json
import os
import pickle
from time import perf_counter_ns
import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

with open(os.path.join(os.path.dirname(__file__), 'preflop.json')) as _f:
    _DATA = json.load(_f)
PREFLOP = _DATA['hands']
RANGES = [eval7.HandRange(r).hands for r in _DATA['ranges']]
CARD = {r+s: eval7.Card(r+s) for r in '23456789TJQKA' for s in 'cdhs'}
RANK = {r: i+2 for i, r in enumerate('23456789TJQKA')}
# Immutable import-time data, shared by all copies; no table state here.
RANGE_CARDS = [[(a, b, a.mask | b.mask, a.rank+2, b.rank+2,
                 (1 << a.rank) | (1 << b.rank), a.suit, b.suit, ((a,b),1.0))
                for (a, b), w in rr] for rr in RANGES]
_STRAIGHTS = [31 << i for i in range(9)] + [4111]
# Rank-mask lookup for every possible set of ranks: no per-sample set building.
_STRAIGHT_OUTS = []
for _mask in range(8192):
    _outs = 0
    for _window in _STRAIGHTS:
        if (_mask & _window).bit_count() == 4:
            _outs |= _window & ~_mask
    _STRAIGHT_OUTS.append(_outs)
FOLD, CHECK, CALL = Action.fold(), Action.check(), Action.call()


def _profile(row):
    # first preflop decisions, folds, VPIP hands, raising hands,
    # postflop facing-bet decisions, folds, raises, calls, checks.
    n = row[0]
    vpip = (row[2]+2.0)/(n+7.0)
    pfr = (row[3]+1.1)/(n+7.0)
    nit = n >= 6 and row[2] == 0
    wild = (n >= 5 and row[3]/n > .90) or (n >= 10 and row[3]/n > .72)
    fold = (row[1]+4.5)/(n+7.0)
    postfold = (row[5]+2.0)/(row[4]+4.0)
    return vpip, pfr, nit, wild, fold, postfold


def _update(s, memory):
    if memory:
        m = pickle.loads(memory)
    else:
        m = {'rows': {}, 'street': 0, 'first': 0, 'vp': 0, 'pr': 0, 'bet': False, 'pf_raise': False}
    rows = m['rows']
    for seat in s.seats:
        rows.setdefault(seat.seat, [0]*13)
    for e in s.events:
        k = e.kind
        if k == 'hand':
            m['street'] = 0
            m['first'] = m['vp'] = m['pr'] = 0
            m['bet'] = False
            m['pf_raise'] = False
        elif k == 'board':
            m['street'] += len(e.cards or [])
            m['bet'] = False
        elif k in ('fold', 'call', 'raise', 'check') and e.seat in rows:
            row = rows[e.seat]
            bit = 1 << e.seat
            if m['street'] == 0:
                if m['pf_raise'] and k != 'check':
                    row[9] += 1
                    row[10] += k == 'fold'
                    if m['pr'] & bit:
                        row[11] += 1
                        row[12] += k == 'fold'
                if not m['first'] & bit:
                    row[0] += 1
                    row[1] += k == 'fold'
                    m['first'] |= bit
                if k in ('call', 'raise') and not m['vp'] & bit:
                    row[2] += 1
                    m['vp'] |= bit
                if k == 'raise' and not m['pr'] & bit:
                    row[3] += 1
                    m['pr'] |= bit
                if k == 'raise': m['pf_raise'] = True
            else:
                if m['bet'] and k != 'check':
                    row[4] += 1
                    row[5] += k == 'fold'
                row[6] += k == 'raise'
                row[7] += k == 'call'
                row[8] += k == 'check'
                if k == 'raise':
                    m['bet'] = True
    return m


def _range_index(width):
    if width < .045: return 0
    if width < .09: return 1
    if width < .16: return 2
    if width < .27: return 3
    if width < .43: return 4
    if width < .72: return 5
    return 6


def _hand_key(cards):
    a, b = cards
    if RANK[a[0]] < RANK[b[0]]:
        a, b = b, a
    return a[0]+b[0]+('' if a[0] == b[0] else 's' if a[1] == b[1] else 'o')


def _relative_category(value, board_counts, board_value):
    """A pair/trips/quads on the board alone is a bluff-catcher, not a monster."""
    cat = value >> 24
    primary = ((value >> 16) & 15)+2
    if cat == 1 and board_counts[primary] >= 2: return 0
    if cat == 3 and board_counts[primary] >= 3: return 0
    if cat == 7 and board_counts[primary] >= 4: return 0
    if cat == 2 and board_counts[primary] >= 2 and board_counts[((value >> 12) & 15)+2] >= 2: return 0
    if value == board_value: return 0
    return cat


def _icm(stacks, hero, payouts):
    """Exact hero ICM, used only for short-handed all-in calls."""
    hs = stacks[hero]
    if hs <= 0:
        return payouts[sum(x > 0 for x in stacks)] if sum(x > 0 for x in stacks) < len(payouts) else 0.0
    alive = [i for i, x in enumerate(stacks) if x > 0 and i != hero]
    total = sum(stacks)
    answer = 0.0
    frontier = [(0, total, 1.0)]
    for place in range(min(len(payouts), len(alive)+1)):
        if payouts[place]:
            answer += payouts[place] * sum(prob*hs/t for mask, t, prob in frontier)
        nxt = {}
        for mask, t, prob in frontier:
            for j, i in enumerate(alive):
                bit = 1 << j
                if not mask & bit:
                    nm = mask | bit
                    np = prob*stacks[i]/t
                    if nm in nxt:
                        nxt[nm] = (t-stacks[i], nxt[nm][1]+np)
                    else:
                        nxt[nm] = (t-stacks[i], np)
        frontier = [(mask, t, prob) for mask, (t, prob) in nxt.items()]
    return answer


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        # Reserve most of the nominal millisecond for the slower tournament CPU,
        # SDK overhead and occasional pauses. This guard reduces samples rather
        # than abandoning an action or consuming the table's entire time bank.
        start = perf_counter_ns()
        allowance = max(80000, int((state.config.decision_ms or 1)*250000))
        if state.time_bank_ms < 20: allowance = min(allowance,125000)
        deadline = start+allowance
        m = _update(state, memory)
        legal = {a.kind.value: a for a in state.legal_actions}
        me = next(x for x in state.seats if x.seat == state.seat)
        opponents = [x for x in state.seats if x.seat != state.seat and x.status in ('active', 'all_in')]
        if not opponents:
            action = CHECK if 'check' in legal else CALL if 'call' in legal else FOLD
        elif not state.board:
            action = self._preflop(state, m, me, opponents, legal)
        else:
            action = self._postflop(state, m, me, opponents, legal, deadline)
        # One final legality gate; no unchecked Action.raise_to escapes this path.
        kind = action.kind.value
        if kind not in legal:
            action = CHECK if 'check' in legal else FOLD if 'fold' in legal else CALL
        elif kind == 'raise':
            a = legal[kind]
            action = Action.raise_to(max(int(a.min_amount), min(int(a.max_amount), int(action.amount))))
        return action, pickle.dumps(m, protocol=4)

    @staticmethod
    def _raise(legal, total):
        a = legal.get('raise')
        if a is None:
            return CALL if 'call' in legal else CHECK if 'check' in legal else FOLD
        return Action.raise_to(max(int(a.min_amount), min(int(a.max_amount), int(total))))

    @staticmethod
    def _risk(s, me, opponents):
        alive = [x for x in s.seats if x.status != 'busted' and x.stack+x.bet > 0]
        paid = sum(p > 0 for p in (s.config.payouts or [50, 30, 20]))
        n = len(alive)
        risk = .012
        if paid > 1 and n <= paid+2 and n > 2:
            covered = any(x.stack+x.bet >= me.stack+me.bet for x in opponents)
            shorter = sum(x.stack+x.bet < (me.stack+me.bet)*.55 for x in alive if x.seat != me.seat)
            if covered:
                risk += (.055 if n == paid+1 else .025) + min(.045, shorter*.02)
        return risk

    @staticmethod
    def _eligible_pot(s, me, opponents):
        # Bets beyond our complete stack are returned or form a side pot that
        # we cannot win. Never count those chips in our calling price.
        cap = me.bet+me.stack
        return max(0, s.pot-sum(max(0,x.bet-cap) for x in opponents))

    def _preflop(self, s, m, me, opponents, legal):
        bb = max(1, s.blinds[1])
        stack = me.stack + me.bet
        cost = min(s.to_call, me.stack)
        key = _hand_key(s.cards)
        equities = PREFLOP[key]
        rank = equities[7]
        hr = max(RANK[c[0]] for c in s.cards)
        lr = min(RANK[c[0]] for c in s.cards)
        suited = s.cards[0][1] == s.cards[1][1]
        pair = hr == lr
        # Suited connected hands realize more than their all-in equity when
        # stacks are deep. Use that benefit for opening, not for stack-off calls.
        open_rank = rank
        hist = [e for e in s.history if e.kind in ('raise', 'call', 'fold', 'check')]
        raises = [e for e in hist if e.kind == 'raise']
        limps = sum(e.kind == 'call' for e in hist) if not raises else 0
        ring = sorted(x.seat for x in s.seats if x.status != 'busted')
        # Seat numbers retain their circular table order; heads-up button acts first.
        if s.button in ring:
            ix = ring.index(s.button)
            order = ring[ix:]+ring[:ix] if len(ring) == 2 else ring[(ix+3) % len(ring):]+ring[:(ix+3) % len(ring)]
        else:
            order = ring
        pos = order.index(s.seat)
        behind = [x for x in opponents if order.index(x.seat) > pos and x.status == 'active']
        profiles = {x.seat: _profile(m['rows'][x.seat]) for x in opponents}
        risk = self._risk(s, me, opponents)
        eff = min(stack, max(x.stack+x.bet for x in opponents))
        if suited and eff > 25*bb:
            open_rank -= .10 if hr-lr == 1 and hr >= 6 else .045 if hr-lr == 2 or lr >= 10 else 0
        fold_action = CHECK if 'check' in legal else FOLD

        if not raises:
            if 'raise' not in legal:
                if 'check' in legal: return CHECK
                # A short big blind can be all-in without making a voluntary
                # raise. Its hand is random, and premium hands must still call.
                odds = cost/max(1,self._eligible_pot(s,me,opponents)+cost)
                eq = equities[6] ** (1+.57*max(0,len(opponents)-1))
                threshold = self._allin_threshold(s,me,opponents,risk)
                return CALL if eq > max(odds+risk,threshold) else fold_action
            width = [0.38, .68, .53, .39, .30, .25, .21, .18][min(7, len(behind))]
            if limps:
                width = min(width, .29 + (.09 if len(opponents) <= 2 else 0))
            if behind and not limps:
                avg_fold = sum(profiles[x.seat][4] for x in behind)/len(behind)
                width += max(-.10, min(.35, (avg_fold-.64)*1.4))
                if all(profiles[x.seat][2] for x in behind):
                    width = 1.0
                if any(profiles[x.seat][3] for x in behind):
                    width *= .82
            if risk > .07 and any(x.stack+x.bet > stack for x in opponents):
                width *= .82
            # Push/fold at low effective stacks. Fold equity is estimated for all
            # players still live; a known automatic folder is almost never a caller.
            if eff <= 12*bb and 'raise' in legal:
                fprob = 1.0
                call_width = .13 + max(0, 10-eff/bb)*.012
                if len(opponents) == 1: call_width += .08
                if risk > .06: call_width *= .8
                for x in opponents:
                    p = profiles[x.seat]
                    cw = .01 if p[2] else .95 if p[3] else call_width
                    if x.status == 'all_in': cw = 1.0
                    fprob *= 1-cw
                eq = equities[_range_index(call_width)]
                if any(p[3] for p in profiles.values()): eq = equities[6]
                multi = max(0, len(opponents)-2)*.015
                eq = max(0, eq-multi)
                wager = max(0, eff-me.bet)
                ev = fprob*s.pot+(1-fprob)*(eq*(s.pot+2*wager-cost)-wager)
                if ev > risk*wager and (rank < max(width, .26) or len(opponents) <= 2 or fprob > .93):
                    return self._raise(legal, me.bet+me.stack)
                if eff <= 7*bb:
                    return fold_action
            if open_rank < min(1, width) and 'raise' in legal:
                size = bb*(2.15+limps) + (bb*.6 if limps else 0)
                if any(p[3] for p in profiles.values()) and rank < .08:
                    size = bb*(3.5+limps)
                if size > .33*eff and eff < 22*bb:
                    size = me.bet+me.stack
                return self._raise(legal, size)
            # Cheap small-blind completion and implied-odds overlimps.
            if limps and cost <= bb and cost < .035*stack and (pair or suited and hr-lr <= 3 or rank < .30):
                return CALL if 'call' in legal else CHECK
            if len(opponents) == 1 and cost <= bb*.5 and rank < .86 and eff > 12*bb:
                return CALL if 'call' in legal else CHECK
            return fold_action

        aggressor = next((x for x in opponents if x.seat == raises[-1].seat), max(opponents, key=lambda x:x.bet))
        profile = profiles[aggressor.seat]
        own_raised = any(e.seat == s.seat for e in raises)
        enemy_raises = sum(e.seat != s.seat for e in raises)
        ai = order.index(aggressor.seat)
        remaining_behind = len(order)-ai-1
        open_width = [0.40, .60, .44, .33, .26, .22, .19, .17][min(7, remaining_behind)]
        samples = m['rows'][aggressor.seat][0]
        if samples > 10:
            observed = min(.85, profile[1]*1.55)
            blend = min(.55, (samples-10)/60)
            open_width = open_width*(1-blend)+observed*blend
        if profile[0] > .55: open_width = max(open_width, profile[1]*1.6)
        if profile[2]: open_width = .065
        if profile[3]: open_width = 1.0
        if enemy_raises >= 2 and not profile[3]:
            open_width *= .22 if own_raised else .38
        if raises[-1].amount > 9*bb and not profile[3] and stack > 25*bb:
            open_width = min(open_width, .095)
        ri = _range_index(open_width)
        eq = equities[ri]
        multi = max(0, len(opponents)-1)
        if multi: eq = eq ** (1+.57*multi)
        in_pos = s.seat == s.button or all((x.seat-s.button) % max(2,len(s.seats)) < (s.seat-s.button) % max(2,len(s.seats)) for x in opponents)
        pot = self._eligible_pot(s, me, opponents)
        odds = cost/max(1, pot+cost)
        facing_allin = cost >= me.stack*.7 or aggressor.status == 'all_in' or aggressor.bet >= stack*.65
        if facing_allin:
            # A deep, unobserved open jam is much tighter than a routine open.
            if enemy_raises == 1 and eff > 22*bb and not profile[3]:
                eq = equities[1 if eff > 35*bb else 2] ** (1+.57*multi)
            threshold = self._allin_threshold(s, me, opponents, risk)
            if eq > max(odds+risk, threshold):
                return CALL if 'call' in legal else fold_action
            return fold_action
        value_cut = .61 + .025*multi
        if own_raised and not profile[3]: value_cut = .57 + risk*.4
        if eq > value_cut and 'raise' in legal:
            total = raises[-1].amount*(3.0 if in_pos else 3.6)
            total += max(0, s.pot-raises[-1].amount-me.bet-1.5*bb)*.55
            if total > eff*.38 or enemy_raises >= 2 or eff <= 22*bb:
                total = me.bet+me.stack
            return self._raise(legal, total)
        # Small, blocker-rich three-bet bluff component against players who fold.
        ar = m['rows'][aggressor.seat]
        folds_reraise = (ar[12]+2.5)/(ar[11]+5)
        if not own_raised and enemy_raises == 1 and len(opponents) <= 2 and eff > 30*bb and folds_reraise > .48 and not profile[3] and hr == 14 and suited and lr <= 5:
            mix = (s.hand_number*37 + s.seat*11 + lr*13) % 100
            if mix < 27 and risk < .065:
                return self._raise(legal, raises[-1].amount*(3.0 if in_pos else 3.6))
        realization = .94 if in_pos else .82
        if pair or suited: realization += .05
        if cost > .12*stack: realization -= .05
        if profile[3]: realization = 1.0
        playable = rank < max(.12, min(.76, open_width*(1.25 if in_pos else 1.05)))
        if me.bet >= bb and cost <= bb*1.2 and enemy_raises == 1:
            playable = rank < .82
        setmine = pair and cost < .055*eff and enemy_raises <= 2
        suited_mine = suited and hr-lr <= 2 and hr >= 8 and cost < .035*eff and in_pos
        if (playable and eq*realization > odds+risk+.025) or setmine or suited_mine:
            return CALL if 'call' in legal else fold_action
        return fold_action

    def _allin_threshold(self, s, me, opponents, risk):
        cost = min(me.stack, s.to_call)
        pot = self._eligible_pot(s, me, opponents)
        odds = cost/max(1, pot+cost)
        living = [x for x in s.seats if x.status != 'busted']
        if len(opponents) != 1 or len(living) > 5 or len(living) <= 2:
            return odds+risk
        villain = opponents[0]
        if cost < .6*me.stack and villain.stack > .2*cost:
            return odds+risk
        stacks = [float(x.stack) for x in living]
        hi = next(i for i,x in enumerate(living) if x.seat == me.seat)
        vi = next(i for i,x in enumerate(living) if x.seat == villain.seat)
        fold, win, lose = stacks[:], stacks[:], stacks[:]
        fold[vi] += s.pot
        win[hi] += pot
        win[vi] += s.pot-pot
        lose[hi] -= cost
        lose[vi] += s.pot+cost
        payouts = list(s.config.payouts or [50,30,20])
        uf, uw, ul = _icm(fold,hi,payouts), _icm(win,hi,payouts), _icm(lose,hi,payouts)
        return max(0, min(.98, (uf-ul)/max(1e-9, uw-ul)))

    def _postflop(self, s, m, me, opponents, legal, deadline=None):
        bb = max(1, s.blinds[1])
        n = len(opponents)
        street = len(s.board)
        if street == 5:
            br = [RANK[c[0]] for c in s.board]
            bs = [c[1] for c in s.board]
            # An unbeatable shared board cannot lose: call any wager, including
            # an overbet, rather than applying a risk premium to a certain chop.
            royal = set(br) == {10,11,12,13,14}
            locked_straight = royal and (len(set(bs)) == 1 or max(bs.count(c) for c in set(bs)) < 3)
            locked_quads = any(br.count(r) == 4 and (14 if r != 14 else 13) in br for r in set(br))
            if locked_straight or locked_quads:
                return CALL if 'call' in legal else CHECK
        rows = m['rows']
        street_events = []
        pre_raises = []
        pre_calls = set()
        for e in s.history:
            if e.kind == 'board': break
            if e.kind == 'raise': pre_raises.append(e)
            if e.kind == 'call': pre_calls.add(e.seat)
        # Current street is the tail after the last board event.
        for j in range(len(s.history)-1, -1, -1):
            if s.history[j].kind == 'board':
                street_events = s.history[j+1:]
                break
        bets = [e for e in street_events if e.kind == 'raise']
        previous_aggressor = pre_raises[-1].seat if pre_raises else None
        villain = next((x for x in opponents if bets and x.seat == bets[-1].seat),
                       max(opponents, key=lambda x:(x.bet, x.seat == previous_aggressor, _profile(rows[x.seat])[2])))
        prof = _profile(rows[villain.seat])
        pre_v = [e for e in pre_raises if e.seat == villain.seat]
        pre_width = 1.0
        if pre_v:
            pre_width = .32
            if len(pre_raises) >= 2: pre_width = .075 if pre_raises[-1].seat == villain.seat else .15
        elif villain.seat in pre_calls:
            pre_width = .42 if pre_raises else .65
        if prof[2]: pre_width = min(pre_width, .10)
        if prof[3]: pre_width = 1.0
        if prof[0] > .55: pre_width = max(pre_width, prof[0])
        ri = _range_index(pre_width)
        facing = s.to_call > 0
        # Detect previous-street pressure as well, so a river barrel isn't
        # evaluated against an untouched preflop range.
        past_aggression = sum(e.kind == 'raise' and e.seat == villain.seat for e in s.history)-len(pre_v)
        strength_level = 0
        if facing:
            strength_level = 1 if street == 3 else 2 if street == 4 else 3
            if len(bets) >= 2 or s.to_call > s.pot*.75: strength_level += 1
        elif past_aggression:
            strength_level = 1
        hero = [CARD[c] for c in s.cards]
        board = [CARD[c] for c in s.board]
        seed = (s.hand_number*2654435761 + s.seat*174763 + int(s.pot)*97) & 0xffffffff
        vr = rows[villain.seat]
        post_actions = vr[6]+vr[7]+vr[8]
        post_wild = post_actions >= 5 and vr[6]/post_actions > .56
        eq, current, category, draw, top_pair = self._equity(hero, board, ri, strength_level, post_wild, seed, s.cards, s.board, deadline)
        if n > 1:
            eq = eq ** (1+.70*(n-1))
            current = current ** (1+.70*(n-1))
        cost = min(s.to_call, me.stack)
        risk = self._risk(s, me, opponents)
        pot = self._eligible_pot(s, me, opponents)
        odds = cost/max(1, pot+cost)
        active = [x for x in opponents if x.status == 'active' and x.stack > 0]
        can_pressure = bool(active) and 'raise' in legal
        own_pre = bool(pre_raises and pre_raises[-1].seat == s.seat)
        own_street_bet = any(e.seat == s.seat for e in bets)
        in_pos = all(any(e.kind == 'check' and e.seat == x.seat for e in street_events) for x in active)
        eff = min(me.stack, max((x.stack for x in active), default=0))
        spr = eff/max(1,s.pot)
        mix = ((seed >> 8) % 1000)/1000
        passive = all(_profile(rows[x.seat])[2] for x in active) if active else False

        if facing:
            if can_pressure and eq > (.78 if n == 1 else .84)+risk*.45 and (category >= 2 or eq > .86 or spr < 1.1):
                total = me.bet+cost+(s.pot+cost)*(.75 if eq < .91 else 1.05)
                if total-me.bet > me.stack*.58 or spr < 1.1:
                    total = me.stack+me.bet
                return self._raise(legal,total)
            if can_pressure and draw >= 8 and street < 5 and n == 1 and not own_street_bet and len(bets) <= 1 and eq > .40 and prof[5] > .53 and spr > 2 and mix < .23 and risk < .06:
                return self._raise(legal, me.bet+cost+(s.pot+cost)*.8)
            margin = .018 + risk
            if street == 3: margin += .025
            if street == 4: margin += .015
            if n > 1: margin += .02*(n-1)
            if post_wild: margin *= .4
            if cost >= me.stack*.7 or villain.status == 'all_in':
                threshold = self._allin_threshold(s, me, opponents, risk)
                margin = max(margin, threshold-odds)
            # Reverse implied odds: a naked bluff-catcher versus a big turn/river
            # raise is not rescued just by superficially attractive pot odds.
            if street >= 4 and len(bets) >= 2 and category < 2 and not post_wild: margin += .055
            if eq > odds+margin:
                return CALL if 'call' in legal else CHECK
            return FOLD if 'fold' in legal else CHECK

        if not can_pressure: return CHECK
        # Value bet with a substantial advantage. Multiway pots require more.
        value_cut = .64 if street < 5 else .60
        if n > 1: value_cut += .06
        if eq > value_cut and (category >= 1 or street < 5 and eq > .73):
            fraction = .62
            if category >= 2 or eq > .86: fraction = .82
            if street == 3 and n == 1 and category <= 1: fraction = .38
            if street == 5 and eq < .75: fraction = .43
            amount = max(bb, int(s.pot*fraction))
            if amount > eff*.55 and eq > .72: amount = me.stack
            return self._raise(legal, me.bet+amount)
        if passive:
            return self._raise(legal, me.bet+max(bb, int(s.pot*.30)))
        # Range and positional pressure: cheap flop c-bets; selective barrels.
        foldrate = sum(_profile(rows[x.seat])[5] for x in active)/max(1,len(active))
        bluff = False
        fraction = .36
        if n == 1 and not own_street_bet:
            if street == 3:
                frequency = (.70 if own_pre else .45 if in_pos else .18)
                frequency += (foldrate-.5)*.6
                bluff = mix < frequency and (eq > .25 or top_pair or draw >= 4)
                if draw >= 8: bluff = mix < .86
            elif street == 4:
                frequency = .40 if draw >= 8 else .22 if eq > .30 and in_pos else .08
                if foldrate > .60: frequency += min(.40,(foldrate-.60)*2)
                bluff = mix < frequency and eq < .59
                fraction = .62
            elif street == 5:
                # Give up most showdown value; retain occasional blocker bluffs.
                ace = any(c[0] == 'A' for c in s.cards)
                frequency = (.23 if ace else .11) + max(0,foldrate-.57)*1.6
                bluff = eq < .27 and mix < frequency and foldrate > .42
                fraction = .70
        elif n == 2 and street == 3 and own_pre and eq > .38 and mix < .26:
            bluff = True
        if bluff and risk < .095 and spr > .65:
            return self._raise(legal, me.bet+max(bb,int(s.pot*fraction)))
        return CHECK

    @staticmethod
    def _equity(hero, board, ri, level, wild, seed, hole_strings, board_strings, deadline=None):
        mask = 0
        for c in hero+board: mask |= c.mask
        hv = eval7.evaluate(hero+board)
        board_ranks = [RANK[c[0]] for c in board_strings]
        board_counts = [0]*15
        for r in board_ranks: board_counts[r] += 1
        board_value = eval7.evaluate(board) if len(board) == 5 else -1
        category = _relative_category(hv, board_counts, board_value)
        high = max(board_ranks)
        top_pair = category == 1 and (any(RANK[c[0]] == high for c in hole_strings) or
                   hero[0].rank == hero[1].rank and hero[0].rank+2 > high)
        board_mask = 0
        board_suits = [0,0,0,0]
        for c in board:
            board_mask |= 1 << c.rank
            board_suits[c.suit] += 1
        hero_ranks = board_mask | (1 << hero[0].rank) | (1 << hero[1].rank)
        fd = (board_suits[hero[0].suit]+1+(hero[0].suit == hero[1].suit) == 4 or
              board_suits[hero[1].suit]+1+(hero[0].suit == hero[1].suit) == 4)
        so = (_STRAIGHT_OUTS[hero_ranks] & ~_STRAIGHT_OUTS[board_mask]).bit_count()
        draw = ((9 if fd else 0)+min(8,4*so)) if len(board) < 5 else 0
        if len(board) == 5 and (not level or wild):
            eq = eval7.py_hand_vs_range_exact(hero,RANGES[ri],board)
            return eq,eq,category,draw,top_pair
        source = RANGE_CARDS[ri]
        count = len(source)
        # Sample evenly across the entire preflop range with a hand-dependent
        # offset. Fixed prime stride avoids taking a single rank/suit slice.
        step = 97
        if count % step == 0: step = 101
        idx = seed % count
        chosen = []
        ahead = equal = total = 0.0
        limit = min(count, 176 if level else 128)
        board_category = board_value >> 24 if len(board) == 5 else 0
        villain_cards = board+[None,None]
        for j in range(limit):
            if j >= 48 and j % 16 == 0 and deadline is not None and perf_counter_ns() > deadline-50000:
                break
            idx = (idx+step) % count
            a,b,cm,ar,br,rm,ac,bc,range_hand = source[idx]
            if cm & mask: continue
            villain_cards[-2] = a
            villain_cards[-1] = b
            vv = eval7.evaluate(villain_cards)
            cat = _relative_category(vv, board_counts, board_value) if level and not wild else vv >> 24
            weight = 1.0
            if level and not wild:
                pair_rank = (vv >> 16) & 15
                # Evaluator packs ranks zero-based. Paired boards alone are air.
                contributes = ar in board_ranks or br in board_ranks or ar == br
                if cat == 0 or cat == 1 and not contributes or vv == board_value:
                    weight = .23 if level == 1 else .075 if level == 2 else .055
                elif cat == 1:
                    strong = pair_rank+2 >= high
                    weight = .95 if strong else .58 if level == 1 else .24 if level == 2 else .12
                elif cat == 2: weight = 1.0 if board_category < 2 else .45
                if len(board) < 5 and cat < 2:
                    fd = (board_suits[ac]+(ac==bc)+1 >= 4 or board_suits[bc]+1+(ac==bc) >= 4)
                    sd = (_STRAIGHT_OUTS[board_mask | rm] & ~_STRAIGHT_OUTS[board_mask]) != 0
                    if fd or sd: weight = max(weight,.72 if level <= 2 else .35)
                if level >= 4 and cat < 2: weight *= .25
            total += weight
            ahead += weight*(hv > vv)
            equal += weight*(hv == vv)
            # Deterministic acceptance converts likelihoods to an unweighted
            # range for eval7's fast C Monte Carlo evaluator.
            z = (seed+j*2246822519) & 0xffffffff
            z ^= z >> 13
            if z % 1000 < weight*1000:
                chosen.append(range_hand)
        if not chosen:
            # No valid sampled hands is possible only for an extremely narrow,
            # heavily blocked range; the original range is a safe fallback.
            chosen = RANGES[ri]
        if len(board) == 5:
            eq = (ahead+.5*equal)/max(.001,total)
        else:
            eq = eval7.py_hand_vs_range_monte_carlo(hero,chosen,board,384)
        current = (ahead+.5*equal)/max(.001,total)
        return eq, current, category, draw, top_pair
