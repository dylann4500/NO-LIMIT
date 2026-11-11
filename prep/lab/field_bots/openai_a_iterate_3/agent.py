"""Range-based, stack-aware tournament hold'em. Only public table state is retained."""
import json
import os
import pickle
import random as _random
import time
from bisect import bisect_left
import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

with open(os.path.join(os.path.dirname(__file__), 'preflop.json')) as _f:
    _DATA = json.load(_f)
PREF = _DATA['hands']
BOUNDS = _DATA['bounds']
MIDPOINTS=[(a+b)/2 for a,b in zip(BOUNDS,BOUNDS[1:])]
RANKS = '23456789TJQKA'
NAMES = [r+s for r in RANKS for s in 'cdhs']
CARDS = [eval7.Card(c) for c in NAMES]
CID = {c:i for i,c in enumerate(NAMES)}

def _key(a,b):
    x,y=a//4,b//4
    if x<y: x,y=y,x
    return RANKS[x]+RANKS[y]+('' if x==y else 's' if a%4==b%4 else 'o')

# Immutable, import-time data is shared safely; no information crosses tables.
COMBOS = []
for _a in range(52):
    for _b in range(_a):
        COMBOS.append(((CARDS[_a],CARDS[_b]), (1<<_a)|(1<<_b), _a//4, _b//4,
                       _a%4, _b%4, PREF[_key(_a,_b)][1]))
RANGES = [[c for c in COMBOS if c[6] <= bound] for bound in BOUNDS]
_shuffle=_random.Random(239)
for _r in RANGES: _shuffle.shuffle(_r)
RAW_RANGES=[[(c[0],1.0) for c in r] for r in RANGES]
FAST_RANGES=[r[:224] for r in RAW_RANGES]
_WINDOWS = [0x100f]+[31<<i for i in range(9)]
DRAW_MASK = [0]*8192
DRAW_OUTS = [0]*8192
for _mask in range(8192):
    for _window in _WINDOWS:
        if (_mask&_window).bit_count()==4:
            DRAW_MASK[_mask]|=_window
            DRAW_OUTS[_mask]|=_window&~_mask

def _kind(x):
    return getattr(x, 'value', x)

def _bucket(width):
    return bisect_left(MIDPOINTS,width)

def _equity_pre(key, width):
    data=PREF[key]
    i=bisect_left(BOUNDS,width)
    if i==0: return data[2]
    if i==len(BOUNDS): return data[-1]
    t=(width-BOUNDS[i-1])/(BOUNDS[i]-BOUNDS[i-1])
    return data[i+1]*(1-t)+data[i+2]*t

def _legal(state, kind, amount=0):
    actions = {_kind(a.kind):a for a in state.legal_actions}
    if kind == 'raise' and 'raise' in actions:
        a = actions['raise']
        return Action.raise_to(max(int(a.min_amount), min(int(a.max_amount), int(amount))))
    if kind == 'raise' and 'call' in actions: return Action.call()
    if kind == 'call' and 'call' in actions: return Action.call()
    if 'check' in actions: return Action.check()
    if 'fold' in actions: return Action.fold()
    if 'call' in actions: return Action.call()
    a = actions['raise']
    return Action.raise_to(int(a.min_amount))

# Stats: dealt hands, VPIP hands, PFR hands, preflop raises, postflop raises,
# postflop calls, postflop folds, postflop checks.
# Current hand: VPIP, PFR, raise count, preflop raise level, bet streets,
# call streets, check streets, folded.
def _memory(state, raw):
    try: m=pickle.loads(raw) if raw else {}
    except (ValueError,TypeError,EOFError,pickle.UnpicklingError): m={}
    ids=[str(s.seat) for s in state.seats]
    if not m or m.get('v')!=3:
        m={'v':3,'h':-1,'st':0,'nr':0,'nb':0,'op':None,'last':None,'s':{},'c':{},'live':ids,'rng':7919,'eq':{}}
    stats=m['s']; cur=m['c']
    for sid in ids:
        if sid not in stats: stats[sid]=[0]*8
        if sid not in cur: cur[sid]=[0]*11
    for event in state.events:
        kind=_kind(event.kind)
        if kind=='hand':
            m['h']=event.amount; m['st']=0; m['nr']=0; m['nb']=0; m['op']=None; m['last']=None; m['eq']={}
            cur={sid:[0]*11 for sid in ids}; m['c']=cur
            for sid in m['live']:
                if sid in stats: stats[sid][0]+=1
        elif kind=='board':
            m['st']+=1; m['last']=None; m['nb']=0; m['eq']={}
            for c in cur.values(): c[10]=0
        elif event.seat is not None:
            sid=str(event.seat)
            if sid not in cur: continue
            c=cur[sid]; s=stats[sid]; st=m['st']
            if kind=='stack':
                if (event.amount or 0)>0 and sid not in m['live']: m['live'].append(sid)
                elif not event.amount and sid in m['live']: m['live'].remove(sid)
            if kind in ('blind','ante','call','raise'):
                amount=int(event.amount or 0)
                delta=max(0,amount-c[10]) if kind=='raise' else amount
                c[9]+=delta
                if kind!='ante': c[10]+=delta
            if kind in ('call','raise'):
                if not st:
                    if not c[0]: s[1]+=1; c[0]=1
                    if kind=='raise':
                        if not c[1]: s[2]+=1; c[1]=1
                        s[3]+=1; c[2]+=1; m['nr']+=1; c[3]=m['nr']
                        m['op']=sid; m['last']=sid
                elif kind=='raise':
                    s[4]+=1; c[4]|=1<<st; m['last']=sid
                    m['nb']+=1; c[8]|=min(15,m['nb'])<<(st*4)
                else:
                    s[5]+=1; c[5]|=1<<st
            elif kind=='fold':
                c[7]=1
                if st: s[6]+=1
            elif kind=='check':
                if st: s[7]+=1; c[6]|=1<<st
    m['live']=[str(s.seat) for s in state.seats if s.status!='busted' and (s.stack+s.bet)>0]
    private=CID[state.cards[0]]*257+CID[state.cards[1]]*65537
    m['rng']=(m['rng']*1664525+1013904223+private)&0xffffffff
    return m

def _maniac(s,c):
    return (s[0]>=3 and s[1]/max(1,s[0])>.62 and s[3]/max(1,s[0])>1.15) or c[2]>=4

def _wild_post(s,c):
    return _maniac(s,c) or (s[4]>=10 and s[4]>2.5*(s[5]+s[7]+1))

def _nit(s):
    return s[0]>=6 and s[1]/s[0]<.12

def _position(state, seat, live=None):
    ss=[s.seat for s in state.seats if s.status!='busted'] if live is None else live
    if seat not in ss or state.button not in ss: return 0,len(ss)
    n=len(ss); d=(ss.index(seat)-ss.index(state.button))%n
    return d,n

def _open_width(state, seat):
    d,n=_position(state,seat)
    if n==2: return .76 if d==0 else .55
    if d==0: return .52 if n==3 else .49 if n==4 else .46
    if d==1: return .48
    if d==2: return .40
    # Count seats between the player and the button (excluding the blinds).
    before_button=n-d
    return .30 if before_button==1 else .24 if before_button==2 else .19 if before_button==3 else .155

def _range_width(state,m,seat):
    sid=str(seat); s=m['s'][sid]; c=m['c'][sid]
    if _maniac(s,c): return 1.0
    if c[3]>=3: width=.05
    elif c[3]==2: width=.08
    elif c[3]==1: width=max(.16,_open_width(state,seat)*.8)
    elif c[0]: width=.50
    else: width=.85
    if s[0]>=8:
        vp=s[1]/s[0]; pfr=s[2]/s[0]
        if c[1]:
            # Overall opening frequency must not turn a tight 4-bet range into
            # an opening range. Shrink the population-relative multiplier.
            pfr=(s[2]+3)/(s[0]+15)
            relative=max(.5,min(2.5,pfr/.20))
            width*=.75+.25*relative if c[3]>=2 else .65+.35*relative
        elif vp>.65: width=max(width,.70)
        elif vp<.16 and c[0]: width=min(width,.22)
    return min(1.0,max(.05,width))

def _context(br,bs,board):
    counts=tuple(br.count(i) for i in range(13))
    suits=tuple(bs.count(i) for i in range(4))
    mask=0
    for r in br: mask|=1<<r
    return (max(br), sorted(br)[len(br)//2], counts, suits, mask,
            len(set(br))<len(br), eval7.evaluate(board) if len(board)==5 else 0)

def _made(value, ctx, a,b):
    cat=value>>24
    high,median,counts,suits,mask,paired,boardvalue=ctx
    if cat==0: return 0.0
    if cat==1:
        pair=(value>>16)&15
        if counts[pair]>=2: return 0.0
        return 1.35 if pair>=high else 1.0 if pair>=median else .7
    if cat==2:
        if not paired: return 2.0
        if boardvalue>>24==2 and value>>12==boardvalue>>12: return 0.0
        private=max(a if (a==b or counts[a]==1) else -1,
                    b if (a==b or counts[b]==1) else -1)
        return 1.4 if private>=high else 1.0
    if cat==3:
        trip=(value>>16)&15
        return 0.0 if counts[trip]>=3 else 3.0
    if boardvalue and (value==boardvalue or (cat==7 and value>>16==boardvalue>>16)):
        return 0.0
    return float(cat)

def _draw(a,b,sa,sb,ctx):
    # 1: flush draw, .7: open-ended/gutshot draw. Hole cards must participate.
    suits=ctx[3]
    flush=(suits[sa]+1+(sa==sb)==4 or suits[sb]+1+(sa==sb)==4)
    hole=(1<<a)|(1<<b)
    straight=DRAW_MASK[hole|ctx[4]] & hole & ~ctx[4]
    return 1.0 if flush else .7 if straight else 0.0

def _range(state,m,opp,board,dead,ctx,seed,pressure,deadline=0):
    sid=str(opp.seat); s=m['s'][sid]; c=m['c'][sid]
    bucket=_bucket(_range_width(state,m,opp.seat))
    base=RANGES[bucket]
    maniac=_wild_post(s,c)
    bets=c[4].bit_count(); calls=c[5].bit_count()
    if not bets and not calls or maniac:
        # C code filters blockers; cap range size to avoid repeated conversion work.
        return FAST_RANGES[bucket] if deadline and time.perf_counter_ns()>deadline-300000 else RAW_RANGES[bucket]
    sample=min(len(base),160)
    offset=seed%len(base)
    out=[]
    street=len(board)-2
    current_bet=bool(c[4]&(1<<street))
    tough=current_bet and pressure>.65
    reraised=((c[8]>>(street*4))&15)>=2
    for j in range(sample):
        if deadline and j>=32 and j%16==0 and time.perf_counter_ns()>deadline-120000:
            break
        x=base[(j+offset)%len(base)]
        if x[1]&dead: continue
        value=eval7.evaluate(x[0]+board)
        made=_made(value,ctx,x[2],x[3])
        draw=_draw(x[2],x[3],x[4],x[5],ctx) if street<3 else 0
        if made>=3: weight=100
        elif made>=2: weight=95
        elif made>=1.3: weight=85 if not tough else 65
        elif made>=1: weight=65 if not tough else 32
        elif made>0: weight=43 if not tough else 18
        elif draw: weight=65 if street==1 else 48
        else: weight=19 if current_bet else 30
        if bets>=2:
            weight=weight if made>=1.3 else max(7,int(weight*.5))
        if street==3 and current_bet and made<1.3: weight=max(5,int(weight*.55))
        if reraised:
            if made<1.3 and not draw: weight=max(3,int(weight*.35))
            elif made<2: weight=int(weight*(.35 if street==3 else .65))
        if pressure>1.5 and current_bet:
            if made<1.3 and not draw: weight=max(2,int(weight*.4))
            elif made<2: weight=max(3,int(weight*(.35 if pressure>3 else .7)))
        if ((j*73+seed*31)%101)<weight: out.append((x[0],1.0))
    if not out:
        return FAST_RANGES[bucket]
    return out

def _icm(stacks,payouts,hero):
    # Exact finishing-place probabilities for the actual payout structure.
    total=sum(stacks)
    # A busted player still receives their finishing-place payout. In particular,
    # losing a three-handed all-in earns third prize; it does not earn zero.
    if stacks[hero]<=0:
        alive=sum(s>0 for s in stacks)
        remaining=[payouts[i] if i<len(payouts) else 0 for i in range(alive,len(stacks))]
        return sum(remaining)/max(1,len(remaining))
    if total<=0: return 0.0
    if not any(payouts[3:]):
        h=stacks[hero]
        value=h/total*payouts[0]
        p2=payouts[1] if len(payouts)>1 else 0
        p3=payouts[2] if len(payouts)>2 else 0
        for i,si in enumerate(stacks):
            if i==hero or si<=0 or total<=si: continue
            rem=total-si
            prob=si/total*h/rem
            value+=prob*p2
            if p3:
                for j,sj in enumerate(stacks):
                    if j!=hero and j!=i and sj>0 and rem>sj:
                        value+=si/total*sj/rem*h/(rem-sj)*p3
        return value
    n=len(stacks); value=0.0
    def rec(left,remaining,prob,place):
        nonlocal value
        if place>=len(payouts) or not remaining: return
        for i in remaining:
            if left<=0: continue
            p=prob*max(0,stacks[i])/left
            if i==hero: value+=p*payouts[place]
            elif p and place+1<len(payouts): rec(left-stacks[i], [j for j in remaining if j!=i],p,place+1)
    rec(total,list(range(n)),1.0,0)
    return value

def _risk(state, hero, opponents, cost,eligible=None):
    n=state.players_remaining
    if n<=2 or cost<=0: return 0.0
    payouts=list(state.config.payouts or [50,30,20])
    paid=sum(1 for x in payouts if x>0)
    if paid<=1: return 0.0
    if len(opponents)==1 and n<=8 and cost>=hero.stack*.18 and paid<=3:
        if eligible is None: eligible=state.pot
        live=[s for s in state.seats if s.status!='busted']
        hi=next(i for i,s in enumerate(live) if s.seat==hero.seat)
        vi=next(i for i,s in enumerate(live) if s.seat==opponents[0].seat)
        base=[s.stack for s in live]
        fold=base[:]; fold[vi]+=state.pot
        win=base[:]; win[hi]+=eligible; win[vi]+=state.pot-eligible
        lose=base[:]; lose[hi]-=cost; lose[vi]+=state.pot+cost
        f=_icm(fold,payouts,hi); w=_icm(win,payouts,hi); l=_icm(lose,payouts,hi)
        return max(0,min(1.0,(f-l)/max(1e-9,w-l))-cost/max(1,eligible+cost))
    if n>paid+2: return .025
    ratio=cost/max(1,hero.stack)
    premium=(.025 if n==paid+1 else .018)*min(2.5,ratio*3)
    if n==paid+1:
        shorts=[s.stack+s.bet for s in state.seats if s.status!='busted' and s.seat!=hero.seat]
        if shorts and min(shorts)<hero.stack*.35: premium+=.05*min(1,ratio*2)
    return min(.14,premium)

def _eligible_pot(state,m,hero,cost):
    limit=m['c'][str(hero.seat)][9]+cost
    if limit<=0: return state.pot
    pot=sum(min(c[9],limit) for c in m['c'].values())
    return min(state.pot,pot) if pot else state.pot

def _jam_threshold(state,hero,villain):
    commit=min(hero.stack,max(0,villain.stack+villain.bet-hero.bet))
    extra=min(villain.stack,max(0,hero.stack+hero.bet-villain.bet))
    chip=commit/max(1,state.pot+commit+extra)
    payouts=list(state.config.payouts or [50,30,20])
    if state.players_remaining<=2: return chip
    if state.players_remaining>8 or sum(x>0 for x in payouts)>3: return chip+.035
    live=[s for s in state.seats if s.status!='busted']
    hi=next(i for i,s in enumerate(live) if s.seat==hero.seat)
    vi=next(i for i,s in enumerate(live) if s.seat==villain.seat)
    stacks=[s.stack for s in live]
    fold=stacks[:]; fold[vi]+=state.pot
    win=stacks[:]; win[hi]+=state.pot+extra; win[vi]-=extra
    lose=stacks[:]; lose[hi]-=commit; lose[vi]+=state.pot+commit
    f=_icm(fold,payouts,hi); w=_icm(win,payouts,hi); l=_icm(lose,payouts,hi)
    return max(chip,(f-l)/max(1e-9,w-l))

def _hu_equity(state,m,opp,board,dead,ctx,pressure,hand,deadline):
    sid=str(opp.seat); c=m['c'][sid]
    width=_bucket(_range_width(state,m,opp.seat))
    maniac=_wild_post(m['s'][sid],c)
    pclass=3 if pressure>3 else 2 if pressure>1.5 else 1 if pressure>.65 else 0
    key=f'{sid}:{width}:{c[4]}:{c[5]}:{min(2,(c[8]>>(m["st"]*4))&15)}:{pclass}:{int(maniac)}'
    cache=m['eq']
    if key in cache: return cache[key]
    seed=(m['h']*7919+sum(ord(x) for x in sid)*127+ctx[4]*13)&65535
    vr=_range(state,m,opp,board,dead,ctx,seed,pressure,deadline)
    if len(board)==5:
        eq=eval7.py_hand_vs_range_exact(hand,vr,list(board))
    else:
        iterations=256 if time.perf_counter_ns()>deadline-100000 else 900
        eq=eval7.py_hand_vs_range_monte_carlo(hand,vr,list(board),iterations)
    cache[key]=round(eq,5)
    return eq

def _draw_credit(ids,ctx,street,made):
    if street==3 or made>=3: return 0.0
    a,b=ids[0]//4,ids[1]//4; sa,sb=ids[0]%4,ids[1]%4
    suits=ctx[3]
    flush=suits[sa]+1+(sa==sb)==4 or suits[sb]+1+(sa==sb)==4
    fd=0.0
    if flush:
        fr=max(a if suits[sa]+1+(sa==sb)==4 else -1,b if suits[sb]+1+(sa==sb)==4 else -1)
        fd=(.32 if street==1 else .18)*(.75+.25*fr/12)
    mask=(1<<a)|(1<<b)|ctx[4]
    missing=0
    for window in _WINDOWS:
        if (mask&window).bit_count()==4 and window&((1<<a)|(1<<b))&~ctx[4]:
            missing|=window&~mask
    outs=missing.bit_count()*4
    sd=(1-((47-outs)/47)*((46-outs)/46))*.75 if street==1 else outs/46*.75
    # Clean overcard improvements are also shared across all opponents.
    overs=int(a>ctx[0])+int(b>ctx[0]) if made==0 else 0
    over=(.065 if street==1 else .035)*overs
    return min(.48,fd+sd*(1-fd)*.75+over*(1-fd-sd*.5))

def _river_ceiling(board,dead):
    """Exact best possible opposing river hand, using ~100 representatives.

    Rank-only hands need one representative for each unordered rank pair.
    Flushes need the two highest available suited cards. Straight flushes
    need each feasible five-rank window. This covers every possible category.
    """
    available=[i for i in range(52) if not dead&(1<<i)]
    byrank=[[] for _ in range(13)]
    for i in available: byrank[i//4].append(CARDS[i])
    best=0
    for r in range(13):
        if not byrank[r]: continue
        if len(byrank[r])>=2:
            best=max(best,eval7.evaluate((byrank[r][0],byrank[r][1])+board))
        for s in range(r):
            if byrank[s]:
                best=max(best,eval7.evaluate((byrank[r][0],byrank[s][0])+board))
    for suit in range(4):
        boardmask=0
        for card in board:
            ci=CID[str(card)]
            if ci%4==suit: boardmask|=1<<(ci//4)
        if boardmask.bit_count()<3: continue
        suited=[i for i in available if i%4==suit]
        if len(suited)>=2:
            best=max(best,eval7.evaluate((CARDS[suited[-1]],CARDS[suited[-2]])+board))
        for window in _WINDOWS:
            missing=window&~boardmask
            if missing.bit_count()>2: continue
            needed=[r*4+suit for r in range(13) if missing&(1<<r)]
            if any(dead&(1<<i) for i in needed): continue
            for i in available:
                if len(needed)>=2: break
                if i not in needed: needed.append(i)
            if len(needed)==2:
                best=max(best,eval7.evaluate((CARDS[needed[0]],CARDS[needed[1]])+board))
    return best

class Agent(poker_agent_sdk.Agent):
    def act(self,state,memory):
        try:
            budget=int(min(.42,float(state.config.decision_ms or 1)*.42)*1000000)
            if state.time_bank_ms<10: budget=min(budget,80000)
            elif state.time_bank_ms<35: budget=min(budget,150000)
            deadline=time.perf_counter_ns()+budget
            m=_memory(state,memory)
            kind,size=self._decide(state,m,deadline)
            return _legal(state,kind,size), pickle.dumps(m,protocol=4)
        except Exception:
            return _legal(state,'fold'), memory

    def _decide(self,state,m,deadline=0):
        if not deadline: deadline=time.perf_counter_ns()+420000
        if not state.to_call and not any(_kind(a.kind)=='raise' for a in state.legal_actions): return 'check',0
        hero=next(s for s in state.seats if s.seat==state.seat)
        opponents=[s for s in state.seats if s.seat!=state.seat and s.status in ('active','all_in')]
        if not opponents: return 'raise',state.pot+hero.bet+state.blinds[1]
        if not state.board: return self._preflop(state,m,hero,opponents)
        return self._postflop(state,m,hero,opponents,deadline)

    def _preflop(self,state,m,hero,opps):
        bb=max(1,state.blinds[1]); cost=min(state.to_call,hero.stack)
        depth=(hero.stack+hero.bet)/bb
        a,b=[CID[c] for c in state.cards]
        key=_key(a,b); data=PREF[key]; percentile=data[1]
        pair=a//4==b//4; suited=a%4==b%4
        cutoff=_open_width(state,hero.seat)
        active=[s for s in state.seats if s.status!='busted']
        d,n=_position(state,hero.seat)
        paid=sum(x>0 for x in (state.config.payouts or [50,30,20]))
        others=[s.stack+s.bet for s in active if s.seat!=hero.seat]
        if n==paid+1 and others:
            if min(others)<(hero.stack+hero.bet)*.4 and max(others)>hero.stack+hero.bet: cutoff*=.73
            elif hero.stack+hero.bet>max(others)*1.3: cutoff=min(.85,cutoff*1.15)
        inpos=d==0 or (d>1 and all(_position(state,s.seat)[0]<d for s in opps))
        raises=m['nr']; own=m['c'][str(hero.seat)]
        maxbet=max(s.bet for s in state.seats)
        unopened=maxbet<=bb and raises==0
        if unopened:
            limpers=sum(m['c'][str(s.seat)][0] for s in opps)
            # Tight players are reliable blind-steal targets, discovered from public hands.
            ahead=[s for s in opps if s.status=='active']
            if ahead and all(_nit(m['s'][str(s.seat)]) for s in ahead): cutoff=.98
            if depth<=10:
                if n==2: cutoff=min(cutoff,.65)
                cutoff=min(.85,cutoff+.018*(10-depth))
                if percentile<cutoff and (not limpers or data[0]>.53): return 'raise',hero.stack+hero.bet
                return ('check',0) if not cost else ('fold',0)
            if limpers: cutoff=min(cutoff,.44 if n==2 else .27)
            playable=percentile<cutoff or (pair and depth>28 and (a//4>=3 or cutoff>.23))
            if playable:
                size=bb*(2.25+limpers)+(bb*.4 if d==1 else 0)
                if depth<=15 and percentile<min(cutoff,.23): size=hero.stack+hero.bet
                return 'raise',size
            if limpers>=2 and cost<=bb and depth>35 and (pair or (suited and abs(a//4-b//4)<=2)):
                return 'call',0
            return ('check',0) if not cost else ('fold',0)
        # Use the latest opponent aggressor as the primary range.
        candidates=[s for s in opps if str(s.seat)==m['op']]
        villain=candidates[0] if candidates else max(opps,key=lambda s:s.bet)
        vs=m['s'][str(villain.seat)]; vc=m['c'][str(villain.seat)]
        maniac=_maniac(vs,vc)
        width=_range_width(state,m,villain.seat)
        eq=_equity_pre(key,width)
        other_committed=sum(s.seat!=villain.seat and s.bet>bb for s in opps)
        if other_committed: eq*=max(.45,data[0])**(.72*other_committed)
        eligible=_eligible_pot(state,m,hero,cost) if cost>=hero.stack*.8 else state.pot
        odds=cost/max(1,eligible+cost)
        risk=_risk(state,hero,opps,cost,eligible)
        eff=min(hero.stack+hero.bet, max(s.stack+s.bet for s in opps))
        allin=cost>=hero.stack*.8 or villain.status=='all_in' or maxbet>=eff*.55
        if allin:
            if eq>odds+risk+.018: return 'call',0
            return 'fold',0
        # Punish repeated, indiscriminate minimum raises with a value shove.
        if maniac and eq>max(.53,_jam_threshold(state,hero,villain)+.018) and percentile<.55:
            return 'raise',hero.stack+hero.bet
        # Value 3-bets, with tighter requirements as the betting is reopened.
        value_cut=.575 if raises<=1 else .55
        if own[1] and raises>=2: value_cut=.54
        if eq>value_cut+risk and (percentile<.13 or maniac or depth<25):
            size=max(maxbet*(3.0 if inpos else 3.6), maxbet+state.pot*.8)
            if size>eff*.32 or depth<24: size=hero.stack+hero.bet
            return 'raise',size
        # Price and realization matter: cheap blind defense differs from facing a 4-bet.
        penalty=.055 if inpos else .095
        if depth>45: penalty+=.025
        if pair or suited: penalty-=.025
        if maniac: penalty=.025
        if raises>=3 and not maniac: penalty+=.045
        if maxbet<2.5*bb and not maniac: penalty-=.035
        if pair and raises==1 and cost<min(hero.stack,villain.stack)*.055 and cost<state.pot*.40:
            return 'call',0
        if eq>odds+max(.015,penalty)+risk and (percentile<max(.15,width*.95) or maniac or odds<.18):
            return 'call',0
        return ('check',0) if not cost else ('fold',0)

    def _postflop(self,state,m,hero,opps,deadline):
        board=tuple(CARDS[CID[c]] for c in state.board)
        ids=[CID[c] for c in state.cards]; hand=[CARDS[i] for i in ids]
        dead=0
        for c in (*state.board,*state.cards): dead|=1<<CID[c]
        br=[CID[c]//4 for c in state.board]; bs=[CID[c]%4 for c in state.board]
        ctx=_context(br,bs,board)
        street=len(board)-2; cost=min(state.to_call,hero.stack); pot=state.pot
        value=eval7.evaluate(tuple(hand)+board)
        if not cost and state.time_bank_ms<35:
            # Protect the reserve from repeated scheduler stalls. Free checks
            # need no rollout; retain straightforward value bets with made hands.
            made=_made(value,ctx,ids[0]//4,ids[1]//4)
            if made>=2 or (made>=1.35 and len(opps)==1):
                return 'raise',hero.bet+max(state.blinds[1],int(pot*.5))
            return 'check',0
        if street==3 and cost and value>>24>=3:
            ceiling=m['eq'].get('ceiling')
            if ceiling is None:
                ceiling=_river_ceiling(board,dead);m['eq']['ceiling']=ceiling
            if value>=ceiling:
                size=hero.bet+cost+.70*(pot+cost)
                if size-hero.bet>hero.stack*.40: size=hero.bet+hero.stack
                return 'raise',size
        pressure=cost/max(1,pot-cost)
        seed=m['rng']; random=(seed>>8)/16777216
        level=max(1,m['c'][str(hero.seat)][9]+cost)
        coverage={s.seat:min(1.0,(m['c'][str(s.seat)][9]+s.stack)/level) for s in opps}
        order=sorted(opps,key=lambda s:(coverage[s.seat]<.6,str(s.seat)!=m['last'], _range_width(state,m,s.seat)))
        villain=order[0]
        eq=_hu_equity(state,m,villain,board,dead,ctx,pressure,hand,deadline)
        if len(opps)>1:
            second=order[1]
            eq2=_hu_equity(state,m,second,board,dead,ctx,pressure*.5,hand,deadline)
        # On a locked board no player can improve: folding a shared nut hand is always a loss.
        bv=ctx[6]; cat=bv>>24
        locked=(cat==8 and (bv>>16)&15==12) or (cat==4 and (bv>>16)&15==12 and max(ctx[3])<=2)
        locked=locked or (cat==7 and (((bv>>12)&15)==12 or (((bv>>16)&15)==12 and ((bv>>12)&15)==11)))
        if locked: return ('raise',hero.stack+hero.bet) if any(s.status=='active' for s in opps) else ('call',0)
        made=_made(value,ctx,ids[0]//4,ids[1]//4)
        draw=_draw(ids[0]//4,ids[1]//4,ids[0]%4,ids[1]%4,ctx) if street<3 else 0
        if len(opps)>1:
            shared=min(eq,eq2,_draw_credit(ids,ctx,street,made))
            other_weight=sum(coverage[s.seat] for s in order[1:])
            eq=shared+(1-shared)*max(0,(eq-shared)/(1-shared))**coverage[villain.seat]*max(0,(eq2-shared)/(1-shared))**(other_weight*.88)
        vs=m['s'][str(villain.seat)]
        maniac=_wild_post(vs,m['c'][str(villain.seat)])
        folds=(vs[6]+2)/(vs[6]+vs[5]+4)
        station=vs[5]>=6 and folds<.23
        d,n=_position(state,hero.seat)
        postorder=lambda seat: (_position(state,seat)[0]-1)%n
        inpos=all(postorder(s.seat)<postorder(hero.seat) for s in opps if s.status=='active')
        eff=min(hero.stack,max(s.stack for s in opps))
        eligible=_eligible_pot(state,m,hero,cost) if cost>=hero.stack*.8 else pot
        risk=_risk(state,hero,opps,cost,eligible)
        if cost:
            odds=cost/max(1,eligible+cost)
            margin=(.025 if street<3 else .035)+risk
            if street<3 and not inpos and eff>pot*2: margin+=.025
            if draw and eff>pot*2: margin-=.015
            if eq>max(.68 if len(opps)==1 else .58,odds+.20)+risk and (made>=1.3 or draw):
                size=hero.bet+cost+.70*(pot+cost)
                if size-hero.bet>hero.stack*.40 or eff<1.4*(pot+cost): size=hero.bet+hero.stack
                return 'raise',size
            if eq>odds+margin: return 'call',0
            return 'fold',0
        # Value, denial, and selective positional continuation bets.
        last_pre=m['op']==str(hero.seat)
        dry=len(set(bs))==3 and max(br)-min(br)>5 and len(set(br))==len(br)
        value_threshold=(.63 if station else .68) if street==3 and len(opps)==1 and not maniac else (.59 if street==3 and not maniac else .57 if len(opps)==1 else .48)
        value_bet=eq>value_threshold and (made>=.7 or draw or street==1)
        bluff=False
        if len(opps)==1 and not maniac and not station:
            if _nit(m['s'][str(villain.seat)]) and not m['c'][str(villain.seat)][0]: bluff=True
            elif street==1 and last_pre and (dry or eq>.42) and random<.70: bluff=True
            elif inpos and street==1 and eq>.34 and random<.40: bluff=True
            elif inpos and street==2 and draw and eq>.32 and random<.40: bluff=True
            elif inpos and street==3 and made==0 and (ids[0]//4==12 or ids[1]//4==12) and random<.18: bluff=True
        if value_bet or bluff:
            fraction=.65 if value_bet else .38
            if dry and street==1 and len(opps)==1: fraction=.36
            if value_bet and eq>.82: fraction=.80
            size=hero.bet+max(state.blinds[1],int(pot*fraction))
            if value_bet and eq>.66 and size-hero.bet>hero.stack*.42: size=hero.bet+hero.stack
            return 'raise',size
        return 'check',0
