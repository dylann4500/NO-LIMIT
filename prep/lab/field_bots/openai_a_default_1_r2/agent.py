"""Fast, range-based no-limit tournament player. All persistent state is in memory."""
import bisect
import gc
import itertools
import json
import math
import os
import pickle
import random
import time

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

RANKS = '23456789TJQKA'
SUITS = 'cdhs'
with open(os.path.join(os.path.dirname(__file__), 'preflop.json')) as _f:
    TABLE = json.load(_f)
PCTS = TABLE['pcts']
PERCENT = TABLE['percent']
RAW = TABLE['raw']
EQUITY = TABLE['equity']
CARD_NAMES = [r+s for r in RANKS for s in SUITS]
CARDS = [eval7.Card(s) for s in CARD_NAMES]
CARD_ID = {s: i for i,s in enumerate(CARD_NAMES)}
CARD_LOOKUP = dict(zip(CARD_NAMES, CARDS))


def hand_key(a, b):
    if a//4 < b//4:
        a,b = b,a
    return RANKS[a//4]+RANKS[b//4]+('' if a//4 == b//4 else 's' if a%4 == b%4 else 'o')


COMBOS = list(itertools.combinations(range(52), 2))
COMBO_CARDS = [(CARDS[a], CARDS[b]) for a,b in COMBOS]
COMBO_MASK = [(1 << a) | (1 << b) for a,b in COMBOS]
COMBO_PERCENT = [PERCENT[hand_key(a,b)] for a,b in COMBOS]
COMBO_INDEX=[[0]*52 for _ in range(52)]
for _i,(_a,_b) in enumerate(COMBOS):
    COMBO_INDEX[_a][_b]=COMBO_INDEX[_b][_a]=_i
RANGE_PCTS = [.025,.04,.06,.085,.12,.16,.22,.30,.42,.60,.80,1.0]
RANGE_IDS = []
RANGE_DEGREES=[]
_rng = random.Random(809127)
for _p in RANGE_PCTS:
    _ids = [i for i,p in enumerate(COMBO_PERCENT) if p <= _p or p < .003]
    # An even prefix over preflop hand classes reduces sampling variance.
    _ids.sort(key=lambda i:(COMBO_PERCENT[i],_rng.random()))
    _bits=(len(_ids)-1).bit_length()
    _order=sorted(range(1<<_bits),key=lambda i:int(f'{i:0{_bits}b}'[::-1],2))
    RANGE_IDS.append(tuple(_ids[i] for i in _order if i<len(_ids)))
    _degrees=[0]*52
    for _i in _ids:
        _a,_b=COMBOS[_i]
        _degrees[_a]+=1
        _degrees[_b]+=1
    RANGE_DEGREES.append(tuple(_degrees))
del _rng
WINDOWS = [sum(1 << r for r in range(i, i+5)) for i in range(9)] + [0x100f]
STRAIGHT = [False]*8192
DRAW_OUTS = [0]*8192
for _m in range(8192):
    _out = 0
    for _w in WINDOWS:
        _missing = _w & ~_m
        if not _missing:
            STRAIGHT[_m] = True
        elif not _missing & (_missing-1):
            _out |= _missing
    DRAW_OUTS[_m] = 0 if STRAIGHT[_m] else _out.bit_count()*4


def pf_equity(key, pct):
    """Linear interpolation of offline Monte Carlo equities."""
    e = EQUITY[key]
    i = bisect.bisect_left(PCTS, pct)
    if i == 0:
        return e[0]
    if i >= len(PCTS):
        return e[-1]
    t = (pct-PCTS[i-1])/(PCTS[i]-PCTS[i-1])
    return e[i-1]*(1-t)+e[i]*t


def population_prior(n):
    return ((.55,.70) if n<=2 else (.38,.50) if n==3 else (.30,.42) if n==4
            else (.25,.36) if n==5 else (.22,.32) if n==6 else (.20,.30) if n==7 else (.18,.28))


def new_memory(state):
    # hands, VPIP hands, PFR hands, PF raises, post bets, post calls,
    # post checks, PF folds, post folds, minimum raises, showdowns, loose shows
    return {'v': 4, 's': {p.seat:[0]*27 for p in state.seats},
            'live': {p.seat:state.config.starting_stack or 2000 for p in state.seats},
            'h':0, 'st':0, 'vp':0, 'pr':0, 'mx':0, 'bets':{}, 'inc':state.blinds[1]}


def update_memory(d, state):
    stats = d['s']
    for e in state.events:
        k = e.kind
        if hasattr(k, 'value'):
            k = k.value
        s = e.seat
        if k == 'hand':
            d['h'] = e.amount
            d['st'] = d['vp'] = d['pr'] = d['mx'] = 0
            d['r'] = {}
            d['bets'] = {}
            d['inc'] = state.blinds[1]
            nlive=sum(v>0 for v in d['live'].values())
            ep,ev=population_prior(nlive)
            for seat,st in stats.items():
                if len(st)<14:
                    st.extend([st[0]*.18,st[0]*.28])
                if d['live'].get(seat,0) > 0:
                    st[0] += 1
                    st[12] += ep
                    st[13] += ev
        elif k == 'board':
            d['st'] += len(e.cards)
            d['bets'] = {}
            d['mx'] = 0
            d['inc'] = state.blinds[1]
        elif k == 'stack':
            d['live'][s] = e.amount
        elif s in stats:
            st = stats[s]
            # Count responses only when this seat faces a wager. A first bet
            # must not be mistaken for evidence that the player refuses to fold.
            oldbet = d['bets'].get(s, 0)
            facing = d['mx'] > oldbet
            street_index = d['st']-3
            if 0 <= street_index <= 2:
                if k == 'fold' and facing:
                    st[21+street_index] += 1
                elif k in ('call','raise') and facing:
                    st[24+street_index] += 1
                    if k == 'raise':
                        st[14] += 1
                elif k in ('check','raise') and not facing:
                    st[15+street_index] += 1
                    if k == 'raise':
                        st[18+street_index] += 1
            if k in ('blind','call'):
                d['bets'][s] = oldbet+(e.amount or 0)
            elif k == 'raise':
                d['bets'][s] = e.amount or 0
            if k == 'blind':
                d['mx'] = max(d['mx'],e.amount or 0)
            elif k == 'raise':
                amount = e.amount or 0
                if amount <= d['mx']+d['inc']+1:
                    st[9] += 1
                delta = amount-d['mx']
                d['inc'] = max(d['inc'],delta)
                d['mx'] = max(d['mx'],amount)
                if not d['st']:
                    bit = 1 << s
                    if not d['vp'] & bit:
                        st[1] += 1
                        d['vp'] |= bit
                    if not d['pr'] & bit:
                        st[2] += 1
                        d['pr'] |= bit
                    st[3] += 1
                else:
                    st[4] += 1
            elif k == 'call':
                if not d['st']:
                    bit = 1 << s
                    if not d['vp'] & bit:
                        st[1] += 1
                        d['vp'] |= bit
                else:
                    st[5] += 1
            elif k == 'check' and d['st']:
                st[6] += 1
            elif k == 'fold':
                st[8 if d['st'] else 7] += 1
            elif k == 'show' and e.cards and len(e.cards) == 2:
                st[10] += 1
                a,b = [CARD_ID[c] for c in e.cards]
                if PERCENT[hand_key(a,b)] > .42:
                    st[11] += 1
    return d


def profile(st,n=8):
    h,v,r,nr,pb,pc,ck,pf,ff,mr,sh,loose = st[:12]
    ep,ev=population_prior(n)
    expected_p=st[12] if len(st)>12 else h*.18
    expected_v=st[13] if len(st)>13 else h*.28
    pfr = min(.98,ep*(r+1.8)/(expected_p+1.8))
    vpip = min(.99,ev*(v+2.8)/(expected_v+2.8))
    # Repeated automatic minraising is recognizable within a few hands.
    maniac = ((r >= 8 and r/max(1,h) > min(.97,max(.82,1.8*expected_p/max(1,h))) and mr/max(1,nr+pb)>.70) or
              (r >= 2 and nr >= 6 and nr/max(1,r) > 2.3 and mr/max(1,nr+pb) > .80) or
              (pb >= 6 and pb/max(1,pb+pc+ck) > .90 and mr/max(1,nr+pb) > .95 and v/max(1,h) > .7) or
              (n>3 and sh >= 3 and loose/sh > .65 and pfr > .4))
    folder = h >= 5 and v == 0 and nr == 0 and pb == 0
    passive = r == 0 and h >= 8
    responses = sum(st[24:27]) if len(st)>=27 else pc
    foldrate = (ff+3.6)/(ff+responses+6.0)
    return pfr,vpip,maniac,folder,passive,foldrate


def street_foldrate(st, street):
    i=street-3
    if len(st)<27 or not 0<=i<=2:
        return .60
    # Shrink small samples toward the observed field; identities are never used.
    prior=(.52,.56,.65)[i]
    f,c=st[21+i],st[24+i]
    return (f+6*prior)/(f+c+6)


def opening_prior(behind, n):
    if n==2:
        return .82
    return (.82,.65,.50,.35,.25,.20,.17,.15)[min(7,behind)]


def history_info(state):
    """Only documented public events. Reconstruct pot contributions and action signals."""
    street = 0
    bets = {}
    totals = {p.seat:0 for p in state.seats}
    pre = []
    calls = {}
    signals = {}
    boards = {}
    board = []
    mx = 0
    pot = 0
    for e in state.history:
        k = e.kind
        if hasattr(k,'value'):
            k = k.value
        s = e.seat
        if k == 'board':
            board.extend(e.cards)
            street = len(board)
            boards[street] = tuple(CARD_ID[c] for c in board)
            mx = 0
            bets = {}
        elif k in ('blind','ante','call','raise'):
            amt = e.amount or 0
            old = bets.get(s,0)
            if k == 'raise':
                added = max(0,amt-old)
                ratio = max(0,amt-mx)/max(1,pot+max(0,mx-old))
                if not street:
                    pre.append((s,amt,mx))
                else:
                    key=(s,street)
                    prev=signals.get(key,(0,0,0))
                    severity=3 if mx else 2
                    signals[key]=(max(prev[0],severity),max(prev[1],ratio),prev[2]+1)
                bets[s] = amt
                mx = max(mx,amt)
            else:
                added = amt
                if k != 'ante':
                    bets[s] = old+amt
                    mx = max(mx,old+amt)
                if k == 'call':
                    if not street:
                        calls[s] = calls.get(s,0)+1
                    else:
                        key=(s,street)
                        prev=signals.get(key,(0,0,0))
                        ratio=amt/max(1,pot)
                        signals[key]=(max(prev[0],1),max(prev[1],ratio),prev[2])
            totals[s] = totals.get(s,0)+added
            pot += added
        elif k == 'check' and street:
            signals.setdefault((s,street),(0,0,0))
    return pre,calls,signals,boards,totals


def board_meta(ids):
    ranks = [c//4 for c in ids]
    sc = [0,0,0,0]
    mask=0
    for c in ids:
        sc[c%4] += 1
        mask |= 1 << (c//4)
    unique=sorted(set(ranks),reverse=True)
    pairs=[r for r in unique if ranks.count(r)>=2]
    trips=any(ranks.count(r)>=3 for r in unique)
    return (tuple(CARDS[c] for c in ids),sc,mask,unique[0],unique[1] if len(unique)>1 else -1,
            len(pairs),trips,tuple(ranks),len(ids))


def features(a,b,meta,value=None):
    bc,sc,bmask,top,second,npair,btrips,branks,street = meta
    ra,rb = a//4,b//4
    if value is None:
        value = eval7.evaluate(COMBO_CARDS_BY_IDS(a,b)+bc)
    cat = value >> 24
    match_a = ra in branks
    match_b = rb in branks
    quality = 0.0
    if ra == rb:
        if ra > top:
            quality = 1.2
        elif ra >= second:
            quality = .64
        else:
            quality = .34
    if match_a:
        quality = max(quality,1.0 if ra == top else .62 if ra == second else .35)
    if match_b:
        quality = max(quality,1.0 if rb == top else .62 if rb == second else .35)
    if cat >= 4:
        strength = .985
    elif cat == 3 and not btrips:
        strength = .975
    elif cat == 2 and not npair:
        strength = .94
    elif cat >= 1 and quality:
        strength = .40+.38*min(1.25,quality)+.025*max(ra,rb)/12
    else:
        strength = .10+.17*max(ra,rb)/12
    # Board-only hands should not be mistaken for private monsters.
    if btrips and cat == 3:
        strength = .20+.25*max(ra,rb)/12
    if cat == 5:
        suit=max(range(4),key=lambda s:sc[s])
        private=[c for c in (a,b) if c%4==suit]
        if private:
            high_flush=max(c//4 for c in private)
            # Only cards of this suit on the board block better flush ranks.
            higher=12-high_flush-sum(c.suit==suit and c.rank>high_flush for c in bc)
            strength=max(.75,.998-.045*higher)
        else:
            strength=.35
    elif cat == 4:
        top_straight=3
        for i in range(8,-1,-1):
            if (WINDOWS[i]&~bmask).bit_count()<=2:
                top_straight=i+4
                break
        made_high=(value>>16)&15
        strength=.985 if made_high>=top_straight else .90
        if max(sc)>=3:
            strength=min(strength,.85)
    if street==5 and cat<=3:
        if max(sc)>=4:
            strength*=.75
        elif max(sc)==3:
            strength*=.87
    fd=0
    if street < 5:
        sa,sb=a%4,b%4
        if sc[sa]+1+(sa==sb) == 4:
            fd=1
        elif sb!=sa and sc[sb]+1 == 4:
            fd=1
    outs=0 if street>=5 else DRAW_OUTS[bmask | (1<<ra) | (1<<rb)]
    draw = min(1.5,fd*.85+outs*.075)
    return strength,quality,draw,cat,fd,outs


def COMBO_CARDS_BY_IDS(a,b):
    return (CARDS[a],CARDS[b])


def likelihood(strength,draw,signal,looseness,street=3):
    kind,size,nraises=signal
    if kind == 0:
        return 1-.20*strength
    if kind == 1:
        w = .025 + strength**3 + draw*.48
        if size > .50:
            w *= .20+.80*strength
    elif kind == 2:
        if street==3 and size<=.45:
            w = .19 + strength**3 + draw*.48
        else:
            w = .04 + 1.3*strength**4 + draw*.58
        if size > .85:
            w *= .25+.75*strength
    else:
        # The logs show very few bluff raises, especially after the flop.
        # First-bet aggression must not wash out this much stronger signal.
        power=8 if street==3 else 14 if street==4 else 26
        w = .004 + 1.7*strength**power + draw*(.22 if street==3 else .12)
        if size>1.0:
            w *= .12+.88*strength**4
        if nraises>1:
            w *= .06+.94*strength**6
        looseness=min(looseness,.055)
    return looseness + (1-looseness)*min(1.5,w)


def villain_range(seat, state, pre, calls, prof, alive_order):
    pfr,vpip,maniac,folder,passive,foldrate = prof
    if maniac:
        return 1.0
    raises = [(i,e) for i,e in enumerate(pre) if e[0]==seat]
    if raises:
        i,e = raises[0]
        # A small reraise remains a reraise, except against identified automatic raisers.
        earlier = [x for x in pre[:i] if x[0]!=seat]
        real_earlier = [x for x in earlier if x[1]>state.blinds[1]]
        if real_earlier:
            pct=.07 if len(real_earlier)==1 else .035
            pct *= max(.7,min(2.5,pfr/.18))
        else:
            pos = alive_order.index(seat) if seat in alive_order else 0
            behind=max(1,len(alive_order)-pos-1)
            nominal = opening_prior(behind,len(alive_order))
            pct=nominal*max(.55,min(1.55,.65+.35*pfr/population_prior(len(alive_order))[0]))
            if e[1]>4*state.blinds[1]:
                pct *= .7
        if len(raises)>1:
            pct = min(.12,.045*max(1,pfr/.18),pct*.35)
        effective=min(next(s.stack+s.bet for s in state.seats if s.seat==seat),
                      next(s.stack+s.bet for s in state.seats if s.seat==state.seat))
        depth=effective/max(1,state.blinds[1])
        # A deep-stack open shove is a very different range from a 2 BB open.
        if e[1]>=max(9*state.blinds[1],effective*.35):
            jamrange=.38 if depth<7 else .24 if depth<12 else .15 if depth<20 else .085 if depth<35 else .05 if depth<60 else .035
            pct=min(pct,jamrange)
        return max(.025,min(.8,pct))
    if seat in calls:
        return max(.10,min(.7,vpip*1.4))
    if next(s for s in state.seats if s.seat==seat).status=='all_in':
        # A player all-in from posting a blind has not selected their hand.
        return 1.0
    return max(.28,min(1.0,vpip*2.0))


def icm_value(stacks, hero, payouts):
    n=len(stacks)
    if n==1:
        return float(payouts[0])
    floor=float(payouts[n-1]) if n<=len(payouts) else 0.0
    total=sum(stacks)
    hs=stacks[hero]
    if hs<1.e-7 or total<=0:
        return floor
    if any(p>floor for p in payouts[3:n-1]):
        # Exact subset dynamic program for nonstandard deeper payout schedules.
        others=[s for i,s in enumerate(stacks) if i!=hero]
        size=1<<len(others)
        sums=[0.0]*size
        probs=[0.0]*size
        probs[0]=1.0
        value=floor
        for mask in range(size):
            if mask:
                bit=mask&-mask
                sums[mask]=sums[mask^bit]+others[bit.bit_length()-1]
            place=mask.bit_count()
            prize=payouts[place]-floor
            rem=total-sums[mask]
            if prize<=0 or rem<=0 or probs[mask]<=0:
                continue
            factor=probs[mask]/rem
            value+=factor*hs*prize
            available=(size-1)^mask
            while available:
                bit=available&-available
                probs[mask|bit]+=factor*others[bit.bit_length()-1]
                available^=bit
        return value
    p1=hs/total
    p2=p3=0.0
    for i,si in enumerate(stacks):
        if i==hero or si<=0:
            continue
        rem=total-si
        if rem<1.e-7:
            continue
        pi=si/total
        p2 += pi*hs/rem
        if n>2:
            for j,sj in enumerate(stacks):
                if j==hero or j==i or sj<=0:
                    continue
                r=rem-sj
                if r>0:
                    p3 += pi*sj/rem*hs/r
    val=floor+(payouts[0]-floor)*p1
    if n>=2 and len(payouts)>1:
        val+=(payouts[1]-floor)*p2
    if n>=3 and len(payouts)>2:
        val+=(payouts[2]-floor)*p3
    return val


def risk_premium(state, me, villain, pot, cost, future=0.0):
    cost=min(float(me.stack),float(cost))
    if me.stack-cost<1.e-7:
        cost=float(me.stack)
    if cost <= me.stack*.04 or state.players_remaining<=2:
        return 0.0
    living=[s for s in state.seats if s.status!='busted' and (s.stack+s.bet)>0]
    if len(living)<3 or villain is None:
        return 0.0
    hi=next(i for i,s in enumerate(living) if s.seat==me.seat)
    vi=next((i for i,s in enumerate(living) if s.seat==villain.seat),None)
    if vi is None or hi==vi:
        return 0.0
    payouts=list(state.config.payouts or [50,30,20,0,0,0,0,0])
    while len(payouts)<len(living):
        payouts.append(0)
    stacks=[float(s.stack) for s in living]
    stacks[vi]=max(0.,stacks[vi]-future)+max(0.,state.pot-(pot-future))
    fold=stacks[:]
    fold[vi]+=pot
    win=stacks[:]
    win[hi]+=pot
    lose=fold[:]
    lose[hi]=max(0.,lose[hi]-cost)
    lose[vi]+=cost
    f=icm_value(fold,hi,payouts)
    w=icm_value(win,hi,payouts)
    l=icm_value(lose,hi,payouts)
    if w<=l:
        return .15
    need=(f-l)/(w-l)
    return max(0.0,min(.22,need-cost/max(1,pot+cost)))


class Agent(poker_agent_sdk.Agent):
    def act(self,state,memory):
        # Our transient objects are acyclic. Defer cyclic GC until outside the
        # timed decision, and restore the caller's setting even on exceptions.
        enabled=gc.isenabled()
        if enabled:
            gc.disable()
        try:
            return self._act(state,memory)
        finally:
            if enabled:
                gc.enable()

    def _act(self,state,memory):
        start=time.perf_counter_ns()
        legal={getattr(a.kind,'value',a.kind):a for a in state.legal_actions}
        me=next(s for s in state.seats if s.seat==state.seat)
        try:
            d=pickle.loads(memory) if memory else new_memory(state)
            if d.get('v')!=4:
                d=new_memory(state)
        except (pickle.UnpicklingError,EOFError,ValueError,TypeError,AttributeError):
            d=new_memory(state)
        update_memory(d,state)
        # A single legality gateway covers short all-ins and incomplete raises.
        def finish(kind,amount=0):
            if kind=='raise' and 'raise' in legal:
                l=legal['raise']
                amount=max(int(l.min_amount),min(int(l.max_amount),int(amount)))
                act=Action.raise_to(amount)
            elif kind=='call' and 'call' in legal:
                act=Action.call()
            elif kind=='check' and 'check' in legal:
                act=Action.check()
            elif 'check' in legal:
                act=Action.check()
            elif 'fold' in legal:
                act=Action.fold()
            elif 'call' in legal:
                act=Action.call()
            else:
                l=legal['raise']
                act=Action.raise_to(int(l.min_amount))
            blob=pickle.dumps(d,protocol=4)
            maximum=min(16000,int(state.config.memory_bytes or 65536))
            if len(blob)>maximum:
                d.pop('r',None)
                blob=pickle.dumps(d,protocol=4)
            if len(blob)>maximum:
                blob=b''
            return act,blob
        if len(legal)==1:
            return finish(next(iter(legal)))
        a,b=[CARD_ID[c] for c in state.cards]
        key=hand_key(a,b)
        pct=PERCENT[key]
        pair=a//4==b//4
        suited=a%4==b%4
        high=max(a//4,b//4)
        low=min(a//4,b//4)
        bb=max(1,state.blinds[1])
        pot=max(1,state.pot)
        cost=min(state.to_call,me.stack)
        maxbet=max(s.bet for s in state.seats)
        opponents=[s for s in state.seats if s.seat!=me.seat and s.status in ('active','all_in')]
        active=[s for s in state.seats if s.status!='busted' and s.stack+s.bet>0]
        active_order=sorted([s.seat for s in active],key=lambda s:(s-state.button-1)%len(state.seats))
        # Preflop action order is after the big blind (or button first heads-up).
        pre_order=active_order[2:]+active_order[:2] if len(active_order)>2 else active_order[::-1]
        profs={s.seat:profile(d['s'][s.seat],state.players_remaining) for s in opponents}
        seed=(a*937+b*347+state.hand_number*191+state.seat*73)&0xffff
        u=(seed%1009)/1009.0
        pre,calls,signals,boards,contrib=history_info(state)
        # Remove inaccessible side pots, and any unmatched part of an overbet.
        cap=contrib.get(me.seat,0)+cost
        if cap and cost>=me.stack:
            eligible=sum(min(x,cap) for x in contrib.values())
            if eligible>0:
                pot=min(pot,eligible)
        if not opponents:
            return finish('check')
        # Default most relevant opponent is the largest live wager.
        villain=max(opponents,key=lambda s:s.bet)
        if state.board:
            now=len(state.board)
            def threat(s):
                pr=profs[s.seat]
                score=-5.0 if pr[2] else .3/max(.08,pr[0])
                if cost and s.bet==maxbet:
                    score+=3
                for st in (3,4,5):
                    kind,size,nr=signals.get((s.seat,st),(0,0,0))
                    score+=(0.,.7,1.4,3.0)[kind]*(1+min(1.,size))
                return score
            villain=max(opponents,key=threat)
        else:
            if pre:
                villain=next((s for s in opponents if s.seat==pre[-1][0]),villain)
        vprof=profs[villain.seat]
        eff=min(me.stack+me.bet,max(s.stack+s.bet for s in opponents))
        depth=eff/bb
        nopp=len(opponents)
        all_folders=all(profs[s.seat][3] for s in opponents if s.status=='active') and all(s.status=='active' for s in opponents)
        # Price tournament risk only when it can change a call. Clear folds and
        # overwhelming favorites do not need three ICM evaluations.
        risk=0.0
        if not state.board:
            own_raises=sum(1 for e in pre if e[0]==me.seat)
            other_raises=[e for e in pre if e[0]!=me.seat]
            maniac=vprof[2]
            # Within-hand evidence speeds up discovery of an automatic minraiser.
            vr=[e for e in pre if e[0]==villain.seat]
            if len(vr)>=3 and all(e[1]-e[2]<=2*bb for e in vr):
                maniac=True
            range_pct=1.0 if maniac else villain_range(villain.seat,state,pre,calls,vprof,pre_order)
            eq=pf_equity(key,range_pct)
            live_callers=sum(1 for s in opponents if s.bet>bb and s.seat!=villain.seat)
            q=eq**(1+.80*live_callers)
            odds=cost/(pot+cost) if cost else 0
            unopened=not pre and not any(s.status=='all_in' for s in opponents)
            # Take free pots against established folders at the smallest legal price.
            if all_folders and 'raise' in legal:
                return finish('raise',legal['raise'].min_amount)
            if unopened:
                mypos=pre_order.index(me.seat) if me.seat in pre_order else 0
                behind=[s for s in opponents if s.status=='active' and s.seat in pre_order and pre_order.index(s.seat)>mypos]
                nb=len(behind)
                late=(len(active)<=3 or nb<=2)
                limpers=sum(calls.values())
                base=opening_prior(nb,len(active))
                if nb==1 and len(active)>2:
                    base=.70
                if limpers:
                    base=max(.16,base-.04*limpers)
                folders=sum(profs[s.seat][3] for s in behind)
                base=min(.98,base+.12*folders)
                if any(profs[s.seat][2] for s in behind):
                    base=min(base,.28 if nb<=2 else .19)
                if depth<=13 and 'raise' in legal:
                    # Push/fold EV over per-opponent calling ranges.
                    pfold=1.0
                    eqsum=weight=effsum=winsum=0.0
                    relevant=behind or opponents
                    for s in relevant:
                        pr=profs[s.seat]
                        dep=min(me.stack+me.bet,s.stack+s.bet)/bb
                        # Shove responses in round 1 depend strongly on the
                        # payout stage. HU calls were much wider than bubble calls.
                        intercept,slope=(.12,1.50) if len(active)==2 else (.045,1.2) if len(active)==3 else (.02,1.0) if len(active)==4 else (.015,.90)
                        cp=min(.80,intercept+slope/max(2.,dep))
                        if s.bet>=bb:
                            cp=min(.90,cp*1.15)
                        elif s.bet==0:
                            cp*=.85
                        # Retain online adaptation and the reference-opponent exploits.
                        nominal=population_prior(len(active))[0]
                        cp*=max(.70,min(1.4,.8+.2*pr[0]/nominal))
                        cp=1.0 if pr[2] else .012 if pr[3] else min(.95,cp)
                        pfold*=1-cp
                        eqsum+=cp*pf_equity(key,cp)
                        weight+=cp
                        exposed=min(me.stack,max(0,s.stack+s.bet-me.bet))
                        future_call=min(s.stack,max(0,me.bet+exposed-s.bet))
                        effsum+=cp*exposed
                        winsum+=cp*future_call
                    qe=eqsum/max(.001,weight)
                    avgeff=effsum/max(.001,weight)
                    avgwin=winsum/max(.001,weight)
                    # Some extra penalty for simultaneous calls and tournament survival.
                    qe**=1+max(0,weight-.5)*.30
                    risk_villain=max(relevant,key=lambda s:s.stack)
                    rp=risk_premium(state,me,risk_villain,pot+avgwin,avgeff,future=avgwin)
                    ev=pfold*pot+(1-pfold)*(qe*(pot+avgwin)-(1-qe)*avgeff-rp*(pot+avgwin+avgeff))
                    if ev>bb*(.03 if late else .15) and (pct<base*1.55 or nb<=1):
                        return finish('raise',legal['raise'].max_amount)
                    if cost==0:
                        return finish('check')
                    # Avoid leaking a short stack through speculative open limps.
                    return finish('fold')
                if pct < base and 'raise' in legal:
                    size=2.10*bb + limpers*1.0*bb
                    if any(profs[s.seat][2] for s in opponents) and pct<.12:
                        size=max(size,3*bb)
                    if size-me.bet>=me.stack*.32:
                        size=legal['raise'].max_amount
                    return finish('raise',size)
                if cost==0:
                    return finish('check')
                # Complete the small blind or overlimp with hands that realize equity.
                if cost<=bb and depth>=20 and (limpers or len(active)==2):
                    if (pair or suited and high-low<=4 or high>=10 and low>=7) and cost/(pot+cost)<.22:
                        return finish('call')
                return finish('fold')
            # Facing aggression, distinguish commitment from an ordinary open.
            committed=cost>=me.stack*.46 or cost>=eff*.40 or 'raise' not in legal
            if committed:
                if odds+.008<=q<odds+.23:
                    risk=risk_premium(state,me,villain,pot,cost)
                need=odds+risk+.008
                if q>=need:
                    return finish('call')
                return finish('check' if cost==0 else 'fold')
            value_threshold=.595 if maniac else .56 if len(other_raises)<=1 else .59
            value = eq>value_threshold and (pct<(.28 if maniac else .095 if len(other_raises)<=1 else .035))
            if value and 'raise' in legal:
                if maniac or depth<=22 or maxbet>=eff*.20:
                    return finish('raise',legal['raise'].max_amount)
                in_position=(active_order.index(me.seat)>active_order.index(villain.seat))
                size=maxbet*(3.0 if in_position else 3.65)+max(0,pot-maxbet*2)*.65
                if size-me.bet>=me.stack*.31:
                    size=legal['raise'].max_amount
                return finish('raise',size)
            in_position=active_order.index(me.seat)>active_order.index(villain.seat)
            realize=.84 if in_position else .73
            realize+=.07 if suited else 0
            realize+=.06 if pair else 0
            realize+=.025 if high-low<=2 else 0
            if high==12 and low<8 and not suited:
                realize-=.07
            if len(other_raises)>=2 and not maniac:
                realize-=.06
            realized=q*min(.98,realize)
            if odds+.018<realized<odds+.24:
                risk=risk_premium(state,me,villain,pot,cost)
            # Paying with the bottom of a dominated range is costly even with deep stacks.
            max_pct=.56 if maniac else .82 if len(active)==2 and len(other_raises)==1 else .42 if len(other_raises)==1 else .42 if len(active)==2 else .21
            if len(other_raises)==1 and me.bet>=bb and maxbet<=3*bb and range_pct>.24:
                max_pct=max(max_pct,.68)
            if nopp>=3:
                max_pct*=.85
            if cost<=bb*.65 and odds<.16:
                max_pct=max(max_pct,.7)
            if pct<max_pct and realized>odds+risk+.018 and cost<eff*.22:
                return finish('call')
            if pair and cost<=eff/17 and cost<=bb*4 and len(other_raises)<=2 and not maniac:
                return finish('call')
            if cost==0:
                return finish('check')
            return finish('fold')
        # POSTFLOP: sampled Bayesian ranges, C-backed showdown equity, then
        # value / draw / position-aware betting with ICM-adjusted calling odds.
        street=len(state.board)
        if all_folders and 'raise' in legal:
            return finish('raise',legal['raise'].min_amount)
        metas={st:board_meta(ids) for st,ids in boards.items()}
        if street not in metas:
            metas[street]=board_meta(tuple(CARD_ID[c] for c in state.board))
        meta=metas[street]
        hero_cards=(CARDS[a],CARDS[b])
        hero_rank=eval7.evaluate(hero_cards+meta[0])
        if street==5 and hero_rank==eval7.evaluate(meta[0]):
            bv=hero_rank>>24
            first=(hero_rank>>16)&15
            second=(hero_rank>>12)&15
            tied_nuts=(bv==8 and first==12 or bv==4 and first==12 and max(meta[1])<=2 or
                       bv==7 and (second==12 or first==12 and second==11))
            if tied_nuts:
                return finish('call' if cost else 'check')
        strength,quality,draw,cat,fd,outs=features(a,b,meta,hero_rank)
        maniac=vprof[2]
        rpct=villain_range(villain.seat,state,pre,calls,vprof,pre_order)
        ri=min(len(RANGE_IDS)-1,bisect.bisect_left(RANGE_PCTS,rpct))
        ids=RANGE_IDS[ri]
        used=(1<<a)|(1<<b)
        used_ids=[a,b]
        for c in state.board:
            cid=CARD_ID[c]
            used |= 1<<cid
            used_ids.append(cid)
        # Count legal combinations in O(known_cards**2), using inclusion-exclusion.
        population=len(ids)-sum(RANGE_DEGREES[ri][c] for c in used_ids)
        for j,x in enumerate(used_ids):
            for y in used_ids[:j]:
                population+=COMBO_PERCENT[COMBO_INDEX[x][y]]<=RANGE_PCTS[ri]
        relsignals=[(st,signals[(villain.seat,st)]) for st in (3,4,5) if (villain.seat,st) in signals]
        # Maniacs have ranges selected by cards they were dealt, not by their bets.
        vst=d['s'][villain.seat]
        aggr=(vst[4]+2)/(vst[4]+vst[5]+vst[6]+8)
        nominal=population_prior(state.players_remaining)[0]
        looseness=.98 if maniac else min(.45,max(.025,(vprof[0]/nominal-1)*.15+(aggr-.30)*.60))
        offset=seed%len(ids)
        bank=float(state.time_bank_ms or 0)
        target=64 if bank>=45 else 32 if bank>=12 else 16
        cache=d.setdefault('r',{})
        cachekey=(villain.seat,ri,maniac)
        rec=cache.get(cachekey)
        # Refresh particles when a new board changes which rare hands matter.
        # Carrying only flop particles to the river can delete every nut flush.
        if rec is not None and rec[0]!=street:
            rec=None
        if rec is not None:
            previous_st,candidate_ids,base_weights,old_weights,cached_features,protected=rec
            if previous_st!=street:
                base_weights=old_weights
                cached_features=None
        else:
            # Always include board-matching pocket pairs. These rare sets carry
            # large posterior mass; sampling them by chance wastes precision.
            protected=set()
            for rank in set(meta[7]):
                available=[c for c in range(rank*4,rank*4+4) if not used&(1<<c)]
                for j,x in enumerate(available):
                    for y in available[:j]:
                        idx=COMBO_INDEX[x][y]
                        if COMBO_PERCENT[idx]<=RANGE_PCTS[ri]:
                            protected.add(idx)
            # On a three-flush board, explicitly include every legal nut-flush
            # combination. These were absent in a costly round-1 overflush.
            for suit,number in enumerate(meta[1]):
                if number==3:
                    available=[c for c in range(suit,52,4) if not used&(1<<c)]
                    if available:
                        nut=available[-1]
                        for other in available[:-1]:
                            idx=COMBO_INDEX[nut][other]
                            if COMBO_PERCENT[idx]<=RANGE_PCTS[ri]:
                                protected.add(idx)
            # Nut straights requiring two private ranks form another small,
            # high-impact stratum that random sampling can otherwise miss.
            if street==5 and max(meta[1])<=2:
                for window in reversed(WINDOWS[:-1]):
                    missing=window & ~meta[2]
                    if missing.bit_count()==2:
                        ranks=[r for r in range(13) if missing & (1<<r)]
                        for x in range(ranks[0]*4,ranks[0]*4+4):
                            for y in range(ranks[1]*4,ranks[1]*4+4):
                                idx=COMBO_INDEX[x][y]
                                if not COMBO_MASK[idx]&used and COMBO_PERCENT[idx]<=RANGE_PCTS[ri]:
                                    protected.add(idx)
                        break
                    if missing.bit_count()<2:
                        break
            candidate_ids=sorted(protected)
            count=0
            for j in range(len(ids)):
                idx=ids[(offset+j)%len(ids)]
                if idx not in protected and not COMBO_MASK[idx]&used:
                    candidate_ids.append(idx)
                    count+=1
                    if count>=target:
                        break
            base_weights=None
            cached_features=None
        sampled=[]
        saved_ids=[]
        saved_base=[]
        saved_weights=[]
        saved_features=[]
        cumulative=[]
        totalweight=0.0
        weighted_win=0.0
        weighted_tie=0.0
        current_win=0.0
        current_weight=0.0
        # Soft deadline leaves ample time for C evaluation, action selection and encoding.
        budget=260000 if bank>=45 else 140000 if bank>=12 else 65000
        budget=min(budget,int(float(state.config.decision_ms or 1)*260000))
        deadline=start+budget
        current_signal=signals.get((villain.seat,street))
        for j,idx in enumerate(candidate_ids):
            if COMBO_MASK[idx]&used:
                continue
            x,y=COMBOS[idx]
            cc=COMBO_CARDS[idx]
            if cached_features is not None:
                fs_strength,fs_draw,rank=cached_features[j]
            else:
                rank=eval7.evaluate(cc+meta[0])
                fs=features(x,y,meta,rank)
                fs_strength,fs_draw=fs[0],fs[2]
            base=base_weights[j] if base_weights is not None else 1.0
            if not maniac and base_weights is None:
                for st,sig in relsignals:
                    if st!=street:
                        bm=metas.get(st)
                        if bm is None:
                            continue
                        f=features(x,y,bm,eval7.evaluate(cc+bm[0]))
                        base*=likelihood(f[0],f[2],sig,looseness,st)
            w=base
            if not maniac and current_signal is not None:
                w*=likelihood(fs_strength,fs_draw,current_signal,looseness,street)
            # Prune essentially impossible hands without deleting bluff support.
            w=max(.0003,w)
            sampled.append(cc)
            saved_ids.append(idx)
            saved_base.append(base)
            saved_weights.append(w)
            saved_features.append((fs_strength,fs_draw,rank))
            if len(sampled)%16==0 and len(sampled)>=len(protected)+8 and time.perf_counter_ns()>deadline:
                break
        if len(cache)>=2 and cachekey not in cache:
            del cache[next(iter(cache))]
        cache[cachekey]=(street,saved_ids,saved_base,saved_weights,saved_features,protected)
        if not sampled:
            # Card removal can empty a narrow range, but never the legal action set.
            return finish('call' if strength>.9 and cost else 'check' if cost==0 else 'fold')
        protected_count=sum(i in protected for i in saved_ids)
        other_mass=max(1.,(population-protected_count)/max(1,len(saved_ids)-protected_count))
        for idx,w,f in zip(saved_ids,saved_weights,saved_features):
            # Horvitz-Thompson stratum weights keep the protected sets from
            # distorting the range. The remainder is a uniform sample.
            w*=1. if idx in protected else other_mass
            fs_strength,fs_draw,rank=f
            totalweight+=w
            cumulative.append(totalweight)
            result=1. if hero_rank>rank else .5 if hero_rank==rank else 0.
            if street==5:
                weighted_win+=w*result
                if hero_rank==rank:
                    weighted_tie+=w
            cont=.06+fs_strength**2+fs_draw*.30
            cw=w*cont
            current_weight+=cw
            current_win+=cw*result
        if street==5:
            eq=weighted_win/totalweight
        else:
            # Deterministic stratified importance resampling; eval7 ignores input weights.
            rr=[]
            k=0
            count=96 if bank>=45 else 64 if bank>=12 else 32
            step=totalweight/count
            for j in range(count):
                target=(j+.5)*step
                while k<len(cumulative)-1 and cumulative[k]<target:
                    k+=1
                rr.append((sampled[k],1.0))
            iterations=640 if bank>=45 else 256 if bank>=12 else 128
            eq=eval7.py_hand_vs_range_monte_carlo(list(hero_cards),rr,list(meta[0]),iterations)
        # Other opponents are typically less filtered, but still compete for the pot.
        q=eq**(1+.78*(nopp-1))
        if street==5 and weighted_tie>0:
            # Split pots are shared among all tied players, rather than treated
            # as a succession of independent heads-up coin flips.
            tie=weighted_tie/totalweight
            win=max(0.,eq-.5*tie)
            tied_share=((win+tie)**(nopp+1)-win**(nopp+1))/((nopp+1)*tie)-win**nopp
            q=min(1.,win**(1+.78*(nopp-1))+max(0.,tied_share))
        odds=cost/(pot+cost) if cost else 0.0
        spr=max(0,min(me.stack,max(s.stack for s in opponents)))/max(1,pot+cost)
        in_position=all(active_order.index(me.seat)>active_order.index(s.seat) for s in opponents if s.status=='active')
        checked_to=not cost
        can_raise='raise' in legal
        facing_raise=signals.get((villain.seat,street),(0,0,0))[0]>=3
        if cost:
            # Realization falls when a weak hand must survive two more betting rounds.
            realize=1.0 if street==5 or cost>=me.stack else .95 if street==4 else .91
            if draw>.5:
                realize=max(realize,.96)
            if spr>3 and quality<.65 and draw<.6:
                realize-=.07
            edge=.01 if street==5 else .015
            if odds+edge<=q*realize<odds+edge+.22:
                risk=risk_premium(state,me,villain,pot,cost)
            need=odds+risk+edge
            if q*realize<need:
                return finish('fold')
            if can_raise:
                strong=(q>(.72 if maniac else .79) and (quality>.8 or cat>=2))
                if not maniac and strength<.90 and spr>2.5:
                    strong=strong and q>.88
                if nopp>1:
                    strong=q>.69 and (cat>=2 or quality>1.1)
                if facing_raise and not maniac:
                    strong=strong and q>.84
                if strong:
                    size=me.bet+cost+.80*(pot+cost)
                    if size-me.bet>me.stack*.40 or spr<1.2 or maniac:
                        size=legal['raise'].max_amount
                    return finish('raise',size)
                # Semi-bluff selectively; a range that just raised rarely folds enough.
                if street<5 and draw>=1.05 and nopp==1 and not maniac and not facing_raise and spr>1.6 and u<.24 and q>.40 and risk<.04 and cost<me.stack*.15:
                    return finish('raise',me.bet+cost+.80*(pot+cost))
            return finish('call')
        if not can_raise:
            return finish('check')
        live_opps=[s for s in opponents if s.status=='active']
        if not live_opps:
            return finish('check')
        continuation=current_win/max(.000001,current_weight)
        # At showdown, use value against the hands that can actually pay a bet.
        if street==5:
            value=(q>.65 and continuation**(1+.65*(nopp-1))>.53)
            # A smaller bet can be paid by pairs that fold to a large bet.
            thin_value=(nopp==1 and q>.76 and continuation>.46 and (quality>=.95 or cat>=2))
            value=value or thin_value
        else:
            value=q>(.57 if nopp==1 else .55) and (quality>.5 or cat>=2)
        if value:
            value_equity=continuation if street==5 else q
            fraction=.66 if value_equity>.82 else .48 if value_equity>.67 else .34
            if street==5 and q<.88:
                fraction=.30
            if maniac:
                fraction=.75
            if street<5 and (max(meta[1])>=2 or len(set(c//4 for c in boards.get(street,())))<=street-1):
                fraction=max(fraction,.55)
            size=me.bet+max(bb,pot*fraction)
            if size-me.bet>me.stack*.45 and q>.72 and (street<5 or continuation>.70 or maniac):
                size=legal['raise'].max_amount
            return finish('raise',size)
        own_pre=bool(pre and pre[-1][0]==me.seat)
        foldrate=sum(street_foldrate(d['s'][s.seat],street) for s in live_opps)/len(live_opps)
        no_maniacs=not any(profs[s.seat][2] for s in live_opps)
        dry=max(meta[1])<=2 and (meta[2].bit_count()>=street-1)
        # Profitable small continuation bets and position probes, with restrained barrels.
        bluff=False
        if nopp==1 and no_maniacs:
            if street==3:
                freq=.80 if own_pre and dry and meta[3]>=9 else .62 if own_pre else .48 if in_position else .10
                if foldrate>.65:
                    freq=max(freq,.82 if own_pre else .55 if in_position else .25)
                bluff=(draw>.5 and q>.30 and u<.72) or (u<freq and q>.22)
            elif street==4:
                prev=signals.get((me.seat,3),(0,0,0))[0]
                bluff=draw>.5 and q>.28 and (in_position or own_pre) and u<.48
                if prev<2 and in_position and q>.22 and u<.48:
                    bluff=True
            else:
                # Small fraction of low-showdown hands, favoring nut-flush blockers.
                suit=max(range(4),key=lambda s:meta[1][s])
                nutblock=(a//4==12 and a%4==suit or b//4==12 and b%4==suit) and meta[1][suit]>=3
                freq=.72 if foldrate>.67 else .52 if foldrate>.57 else .32 if nutblock else .12
                if not in_position:
                    freq*=.45
                # Prefer low-showdown hands; let medium pairs realize their equity.
                bluff=q<.30 and u<freq and foldrate>.50 and pot>=2*bb
        if nopp==2 and no_maniacs and own_pre and street==3 and draw>.8 and q>.25 and u<.24:
            bluff=True
        if bluff:
            frac=.32 if street==3 else .48 if street==4 else .50
            return finish('raise',me.bet+max(bb,pot*frac))
        return finish('check')
