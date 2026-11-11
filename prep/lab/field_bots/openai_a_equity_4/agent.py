"""Range equity, position, opponent adaptation, and tournament-aware sizing."""
import os
import json
import pickle
import math
import bisect
import random
from time import perf_counter_ns
import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

with open(os.path.join(os.path.dirname(__file__), 'preflop.json')) as _f:
    _DATA = json.load(_f)
_Q = _DATA['q']
_EQ = _DATA['equity']
_PCT = _DATA['percent']
_R = '23456789TJQKA'
_C = [eval7.Card(r+s) for r in _R for s in 'cdhs']
_CMAP = {str(c): c for c in _C}
_CID = {str(c): i for i,c in enumerate(_C)}
_COMBOS = []
for _k in _DATA['order']:
    _a = _R.index(_k[0]); _b = _R.index(_k[1])
    for _s in range(4):
        for _t in range(4):
            if _a == _b:
                if _t >= _s: continue
            elif ((_s == _t) != _k.endswith('s')): continue
            _i = _a*4+_s; _j = _b*4+_t
            _COMBOS.append((_C[_i],_C[_j],(1<<_i)|(1<<_j),_a,_b,_s,_t,_i*53+_j))
# Immutable representative ranges; all expensive setup happens before forking.
_SAMPLES = []
_rng = random.Random(59173)
for _q in _Q:
    _rr = _COMBOS[:round(_q*1326)]
    _SAMPLES.append(_rr if len(_rr)<=144 else _rng.sample(_rr,144))
del _rng
_BASE_RANGES=[]
for _rr in _SAMPLES:
    _hr=eval7.HandRange('');_hr.hands=[((x[0],x[1]),1.0) for x in _rr]
    _BASE_RANGES.append(_hr)
# 13-bit rank masks make straight draw detection one table lookup.
_WINDOWS = [31<<i for i in range(9)]+[(1<<12)|15]
_STRAIGHT4 = bytes(any((m&w).bit_count()>=4 for w in _WINDOWS) for m in range(8192))


def _kind(x):
    return getattr(x,'value',x)


def _key(cards):
    a,b=cards
    if _R.index(a[0])<_R.index(b[0]): a,b=b,a
    return a[0]+b[0]+('' if a[0]==b[0] else 's' if a[1]==b[1] else 'o')


def _lookup(key,q,n=1):
    q=max(.05,min(1.,q)); n=max(1,min(7,n))
    j=bisect.bisect_left(_Q,q)
    if j==0: return _EQ[key][0][n]
    if j>=len(_Q): return _EQ[key][-1][n]
    w=(q-_Q[j-1])/(_Q[j]-_Q[j-1])
    return _EQ[key][j-1][n]*(1-w)+_EQ[key][j][n]*w


def _fresh(state):
    ids=[s.seat for s in state.seats]
    return {'v':3,'s':{i:[0]*14 for i in ids}, 'h':-1,'st':0,
            'b':{},'i':{},'p':{},'pot':0,'inc':state.blinds[1],
            'alive':ids,'last':-1,'hero_raises':0}


def _update(state,m):
    """Fold all newly delivered public events into compact, table-local memory."""
    stats=m['s']; bb=max(1,state.blinds[1])
    for ev in state.events:
        kind=_kind(ev.kind); seat=ev.seat
        if kind=='hand':
            m['h']=int(ev.amount);m['st']=0;m['b']={};m['i']={};m['p']={}
            m['pot']=0;m['inc']=bb;m['last']=-1;m['hero_raises']=0
            for i in m['alive']:
                if i in stats: stats[i][0]+=1
            continue
        if kind=='board':
            m['st']+=1;m['b']={};m['inc']=bb;m['last']=-1
            continue
        if seat is None or seat not in stats: continue
        s=stats[seat]
        if kind=='stack':
            if not ev.amount and seat in m['alive']: m['alive'].remove(seat)
            continue
        if kind in ('show','win'):
            if kind=='show' and ev.cards and len(ev.cards)==2:
                if _PCT.get(_key(ev.cards),.5)>.6: s[11]+=1
            continue
        st=min(3,m['st']); hp=m['p'].setdefault(seat,[0]*11)
        if kind in ('blind','ante','call','raise'):
            amount=int(ev.amount or 0)
            if kind=='raise':
                previous=max(m['b'].values(),default=0)
                added=max(0,amount-m['b'].get(seat,0))
                inc=amount-previous
                if inc<=max(bb,m['inc'])*1.05: s[9]+=1
                else: s[10]+=1
                m['inc']=max(m['inc'],inc);m['last']=seat
                m['b'][seat]=amount
                if seat==state.seat: m['hero_raises']+=1
            else:
                added=amount
                if kind!='ante':m['b'][seat]=m['b'].get(seat,0)+amount
            if kind in ('call','raise'):
                if st==0:
                    s[3]+=1
                    if not hp[0]: s[1]+=1;hp[0]=1
                    if kind=='raise':
                        s[4]+=1
                        if not hp[1]:s[2]+=1
                        hp[1]+=1;hp[3]=max(hp[3],amount/bb)
                    else:hp[2]+=1
                else:
                    s[5]+=1
                    if kind=='raise':
                        s[6]+=1;hp[3+st]+=1
                        hp[6+st]=max(hp[6+st],added/max(bb,m['pot']))
                    else:s[7]+=1
            m['pot']+=added;m['i'][seat]=m['i'].get(seat,0)+added
        elif kind in ('check','fold'):
            if st==0:
                s[3]+=1
                if kind=='fold':s[12]+=1
            else:
                s[5]+=1
                if kind=='fold':s[8]+=1
                else:s[13]+=1;hp[10]+=1
    # Safe initialization if a host omits an initial hand event.
    if m['h']!=state.hand_number:
        m['h']=state.hand_number;m['st']=0 if not state.board else len(state.board)-2
        m['b']={x.seat:x.bet for x in state.seats};m['pot']=state.pot
    return m


def _maniac(s):
    return s[3]>=5 and (s[4]+.5)/(s[3]+1)>.64 and (s[9]+1)/(s[4]+s[6]+2)>.65


def _nit(s):
    return s[0]>=5 and s[1]<=.075*s[0] and s[6]==0


def _range(s,hp,stack,bb,open_q=.17):
    if _maniac(s):return 1.0
    if hp[1]:
        q=(s[2]+13*open_q)/(s[0]+13)
        q=max(.085,min(.52,q))
        size=hp[3]
        if size>6:
            if (stack+size*bb)/bb<17:q=max(q,min(.65,open_q*1.35))
            else:q*=max(.34,1.-(size-4)*.055)
        q*=.52**min(3,hp[1]-1)
        return max(.035,q)
    if hp[2]:
        return max(.18,min(.75,(s[1]+4.0)/(s[0]+13)))
    return 1.0


def _draw(a,b,board):
    counts=[0,0,0,0];mask=(1<<a.rank)|(1<<b.rank)
    counts[a.suit]+=1;counts[b.suit]+=1
    for c in board:counts[c.suit]+=1;mask|=1<<c.rank
    fd=(counts[a.suit]==4 or counts[b.suit]==4)
    return fd,bool(_STRAIGHT4[mask])


def _strength(v,a,b,branks):
    cat=v>>24
    if cat>=2:return 3
    if cat==1:
        pair=(v>>16)&15
        top=max(branks)
        if pair>=top:return 2
        return 1
    return 0


def _post_equity(state,m,opps,qs,hero,key,bb,deadline):
    board=[_CMAP[x] for x in state.board]
    stage=len(board)-2; hv=eval7.evaluate(hero+board);cat=hv>>24
    ranks=[c.rank for c in board]; top=max(ranks)
    fd,sd=_draw(hero[0],hero[1],board) if stage<3 else (False,False)
    # One representative range aggregates opponents' preflop and betting evidence.
    # Use the most threatening bettor, otherwise the geometric mean of ranges.
    threat=max(range(len(opps)),key=lambda j:sum(m['p'].get(opps[j].seat,[0]*11)[4:7])*.6-math.log(max(.04,qs[j]))*.35)
    villain=opps[threat]; hp=m['p'].get(villain.seat,[0]*11);ss=m['s'][villain.seat]
    q=qs[threat] if any(hp[4:7]) else math.exp(sum(math.log(max(.04,x)) for x in qs)/len(qs))
    ri=min(range(len(_Q)),key=lambda j:abs(_Q[j]-q))
    blocked=0
    for x in (*state.cards,*state.board):blocked|=1<<_CID[x]
    bets=hp[3+stage]; earlier=sum(hp[4:3+stage]);loose=_maniac(ss)
    weights=[];wins=0.;den=0.
    bmask=0;counts=[0,0,0,0]
    for c in board:bmask|=1<<c.rank;counts[c.suit]+=1
    # Hoist all action-likelihood arithmetic out of the candidate loop.
    wbase=(.20,.50,.95,1.0) if stage==1 else (.10,.36,.85,1.0) if stage==2 else (.055,.22,.68,1.0)
    size=hp[6+stage];af=(ss[6]+2)/(ss[5]+7)
    mix=min(.25,max(0.,af-.30)*.35)
    if bets>=2:mix*=.25
    if bets>=3:mix*=.25
    condition=(bets or earlier) and not loose
    candidates=_SAMPLES[ri] if condition or stage==3 else ()
    for ci,(a,b,mask,ar,br,asu,bsu,tag) in enumerate(candidates):
        if ci>=32 and ci%16==0 and perf_counter_ns()>deadline-220000:break
        if mask&blocked:continue
        v=eval7.evaluate([a,b]+board)
        vc=v>>24
        strength=3 if vc>=2 else (2 if ((v>>16)&15)>=top else 1) if vc==1 else 0
        w=1.
        if bets and not loose:
            w=wbase[strength]
            if stage<3 and strength<3:
                vf=(counts[asu]+(2 if asu==bsu else 1)==4 or counts[bsu]+(2 if asu==bsu else 1)==4)
                if vf:w=max(w,.78)
                elif _STRAIGHT4[bmask|(1<<ar)|(1<<br)]:w=max(w,.48)
            if size>1.1 and strength<2:w*=.7
            if bets>=2:
                if strength<2:w*=.10
                elif strength==2:w*=.42 if ((v>>16)&15)>top else .20
                if bets>=3 and strength<3:w*=.18

            w=w*(1-mix)+mix
        elif earlier and not loose:
            # Earlier bets keep made hands and busted draws in the range.
            w=(.48,.78,1.,1.)[strength]
        elif hp[10] and strength==3:w=.85
        if stage==3:
            den+=w
            wins+=w*(1. if hv>v else .5 if hv==v else 0.)
        else:
            copies=int(w*4)
            if (tag*17+state.hand_number*13)%100 < (w*4-copies)*100:copies+=1
            if copies:weights.extend([((a,b),1.0)]*copies)
    if stage==3:
        eq=wins/den if den else .5
    elif not condition:
        eq=eval7.py_hand_vs_range_monte_carlo(hero,_BASE_RANGES[ri],board,384)
    elif weights:
        hr=eval7.HandRange.__new__(eval7.HandRange);hr.hands=weights
        eq=eval7.py_hand_vs_range_monte_carlo(hero,hr,board,384)
    else: eq=_lookup(key,q)
    n=len(opps)
    if n>1:
        # The bettor's conditioned range must not be assigned to every other
        # player. Estimate the remaining ranges separately when time permits.
        others=[j for j in range(n) if j!=threat]
        qother=math.exp(sum(math.log(max(.04,qs[j])) for j in others)/len(others))
        other_eq=eq
        if perf_counter_ns()<deadline-160000:
            oi=min(range(len(_Q)),key=lambda j:abs(_Q[j]-qother))
            if stage==3:
                other_eq=eval7.py_hand_vs_range_exact(hero,_BASE_RANGES[oi],board)
            else:other_eq=eval7.py_hand_vs_range_monte_carlo(hero,_BASE_RANGES[oi],board,192)
        es=[eq]
        for j in others:
            oh=m['p'].get(opps[j].seat,[0]*11)
            # Another current bettor is also representing a selected range.
            es.append(min(eq,other_eq) if oh[3+stage] and not _maniac(m['s'][opps[j].seat]) else other_eq)
        es.sort()
        if stage==3:
            if hv==eval7.evaluate(board):
                # With the board playing, every opponent either ties or wins.
                # Half-pot heads-up ties cannot be multiplied as outright wins.
                eq=math.prod(min(1.,2*e) for e in es)/(n+1)
            else:eq=math.prod(es)
        else:
            concentration=(5.0 if cat>=1 else 2.6) if stage==1 else (10.0 if cat>=1 else 4.5)
            if fd or sd:concentration*=.65
            joint=es[0]
            for j,e in enumerate(es[1:],1):joint*=(e*concentration+j)/(concentration+j)
            eq=joint
    return eq,cat,fd,sd,hv


def _icm(stacks,payouts,hero):
    """Exact ICM. The usual three paid places have a small closed-form tree."""
    total=sum(stacks);h=stacks[hero]
    if total<=0 or h<=0:return 0.
    others=[x for i,x in enumerate(stacks) if i!=hero and x>0]
    p1=h/total
    ans=p1*payouts[0]
    if len(payouts)>1:
        ans+=p1*payouts[1]*sum(x/(total-x) for x in others)
    if len(payouts)>2:
        third=0.
        for j,x in enumerate(others):
            rest=total-x
            third+=x/rest*sum(y/(rest-y) for k,y in enumerate(others) if k!=j and rest>y)
        ans+=p1*payouts[2]*third
    if len(payouts)>3:
        # DP over the subsets of opponents finishing ahead of us.
        k=len(others);mass=[0.]*(1<<k);mass[0]=1.;sums=[0.]*(1<<k)
        for mask in range(1,1<<k):
            bit=mask&-mask;sums[mask]=sums[mask^bit]+others[bit.bit_length()-1]
        for mask,p in enumerate(mass):
            place=mask.bit_count();left=total-sums[mask]
            if place>=len(payouts) or left<=0:continue
            if place>=3:ans+=p*h/left*payouts[place]
            for j,x in enumerate(others):
                if not mask&(1<<j):mass[mask|(1<<j)]+=p*x/left
    return ans


def _risk(state,me,opps,call,m=None):
    if state.players_remaining<3 or call<.23*max(1,me.stack):return 0.
    payouts=list(getattr(state.config,'payouts',None) or [50,30,20,0,0,0,0,0])
    while payouts and payouts[-1]==0:payouts.pop()
    if not payouts:return 0.
    live=[x for x in state.seats if _kind(x.status)!='busted' and (x.stack+x.bet>0 or _kind(x.status)=='all_in')]
    hi=next(i for i,x in enumerate(live) if x.seat==state.seat)
    st=[float(x.stack) for x in live]
    participants=[i for i,x in enumerate(live) if x.seat!=state.seat and any(o.seat==x.seat for o in opps)]
    if not participants:return 0.
    start=me.stack+(m['i'].get(me.seat,me.bet) if m else me.bet)
    def utility(z):
        if z[hi]>0:return _icm(z,payouts,hi)
        # Simultaneous busts rank by chips at the beginning of this hand.
        rank=1+sum(x>0 for x in z)
        for j,x in enumerate(live):
            if j!=hi and z[j]<=0:
                initial=x.stack+(m['i'].get(x.seat,x.bet) if m else x.bet)
                if initial>=start:rank+=1
        return payouts[rank-1] if rank<=len(payouts) else 0.
    won=st[:];won[hi]+=state.pot
    uw=utility(won);uf=ul=0.
    # Average the identity of the winning opponent. This also accounts for the
    # survival value of folding while several opponents are already all-in.
    if len(payouts)>3:participants=[max(participants,key=lambda j:live[j].bet)]
    weights=[max(1,live[j].bet) for j in participants];sw=sum(weights)
    for j,w in zip(participants,weights):
        folded=st[:];folded[j]+=state.pot
        lost=st[:];lost[hi]=max(0.,lost[hi]-call);lost[j]+=state.pot+call
        uf+=w/sw*utility(folded);ul+=w/sw*utility(lost)
    if uw<=ul:return 0.
    needed=(uf-ul)/(uw-ul);raw=call/max(1,state.pot+call)
    return max(0.,min(.45,needed-raw))


class Agent(poker_agent_sdk.Agent):
    def act(self,state,memory):
        deadline=perf_counter_ns()+750000
        legal={_kind(a.kind):a for a in state.legal_actions}
        def passive():
            if 'check' in legal:return Action.check()
            if 'fold' in legal:return Action.fold()
            if 'call' in legal:return Action.call()
            r=legal.get('raise');return Action.raise_to(int(r.min_amount))
        try:
            m=pickle.loads(memory) if memory else _fresh(state)
            if m.get('v')!=3:m=_fresh(state)
            _update(state,m)
            action=self._decide(state,m,legal,passive,deadline)
            # Centralize integer sizing and offered-kind validation.
            kind=_kind(action.kind)
            if kind not in legal:action=passive()
            elif kind=='raise':
                r=legal['raise'];action=Action.raise_to(max(int(r.min_amount),min(int(r.max_amount),int(action.amount))))
            return action,pickle.dumps(m,protocol=4)
        except Exception:
            # A corrupt/truncated memory must not turn into an SDK failure.
            return passive(),b''

    def _decide(self,state,m,legal,passive,deadline=None):
        if deadline is None:deadline=perf_counter_ns()+750000
        me=next(x for x in state.seats if x.seat==state.seat)
        opps=[x for x in state.seats if x.seat!=state.seat and _kind(x.status) in ('active','all_in')]
        if not opps:return passive()
        bb=max(1,state.blinds[1]); pot=max(bb,state.pot);call=min(me.stack,max(0,state.to_call))
        eligible_pot=pot
        if call>=me.stack and m['i']:
            cap=m['i'].get(me.seat,me.bet)+call
            eligible_pot=min(pot,sum(min(cap,x) for x in m['i'].values()))
            eligible_pot=max(bb,eligible_pot)
        pot=eligible_pot
        r=legal.get('raise');key=_key(state.cards);pct=_PCT[key]
        hero=[_CMAP[c] for c in state.cards]
        loose=[_maniac(m['s'][x.seat]) for x in opps]
        nits=[_nit(m['s'][x.seat]) for x in opps]
        # Seat order is clockwise; button is last to act after the flop.
        ids=[x.seat for x in state.seats if _kind(x.status)!='busted']
        bi=ids.index(state.button) if state.button in ids else 0
        order=ids[bi+1:]+ids[:bi+1]
        post_order=[i for i in order if i==me.seat or any(x.seat==i and _kind(x.status)=='active' for x in opps)]
        position=not post_order or post_order[-1]==me.seat
        if len(ids)==2:pf_order=[state.button]+[i for i in ids if i!=state.button]
        else:pf_order=order[2:]+order[:2]
        after=pf_order[pf_order.index(me.seat)+1:] if me.seat in pf_order else []
        behind=sum(any(x.seat==i and _kind(x.status)=='active' for x in opps) for i in after)
        open_priors=[.65,.50,.40,.30,.24,.20,.17,.15]
        qs=[]
        for x in opps:
            remaining=len(pf_order)-1-pf_order.index(x.seat) if x.seat in pf_order else 5
            prior=open_priors[min(7,max(0,remaining))]
            qs.append(_range(m['s'][x.seat],m['p'].get(x.seat,[0]*11),x.stack,bb,prior))
        rand=((state.hand_number*214013+state.seat*2531011+sum(_CID[c]*7919 for c in state.cards))&65535)/65536
        own=m['p'].get(me.seat,[0]*11)
        risk=_risk(state,me,opps,call,m) if call and pot>=state.pot else (.03 if call and state.players_remaining<=5 else 0.)
        odds=call/max(1,pot+call)
        def raise_to(x):
            if not r:return Action.call() if 'call' in legal else passive()
            total=int(round(x));total=max(int(r.min_amount),min(int(r.max_amount),total))
            if total-me.bet>.65*me.stack:total=int(r.max_amount)
            return Action.raise_to(total)
        if not state.board:
            committed=[j for j,x in enumerate(opps) if m['p'].get(x.seat,[0]*11)[0] or _kind(x.status)=='all_in']
            qlist=[qs[j] for j in committed] or [1.]
            n=max(1,len(committed));q=math.exp(sum(math.log(max(.04,x)) for x in qlist)/n)
            eq=_lookup(key,q,n)
            raisers=[x for x in opps if m['p'].get(x.seat,[0]*11)[1]]
            unraised=not raisers
            limpers=len(committed)
            depth=me.stack/bb
            # Push/fold accounts for the equity of the range that will CALL us.
            if r and unraised and depth<=12 and not own[1]:
                callerange=min(.55,.16+2.0/max(3.,depth))
                call_eq=_lookup(key,callerange)
                count=max(1,behind+limpers)
                fp=(1-callerange)**count
                if any(loose):fp*=.20;call_eq=_lookup(key,.65)
                eff=min(me.stack,max(x.stack+x.bet for x in opps))
                ev=fp*pot+(1-fp)*(call_eq*(pot+2*eff)-eff)
                if ev>bb*(.12+min(.7,risk*6)) and (call_eq>.30 or fp>.6):return raise_to(r.max_amount)
            if r and unraised and not own[1]:
                thresholds=[.5,.66,.46,.33,.26,.215,.18,.15]
                threshold=thresholds[min(7,behind)]
                if all(nits):threshold=min(.95,threshold*1.6)
                elif sum(nits)>=len(opps)/2:threshold=min(.80,threshold*1.25)
                if any(loose):threshold=min(threshold,.25 if sum(loose)==1 else .18)
                if limpers:threshold*=.80
                if pct<threshold:
                    size=max(me.bet+call+bb,(2.25+limpers*.85)*bb)
                    return raise_to(size)
            if raisers:
                strongest=min(qs[j] for j in range(len(opps)) if m['p'].get(opps[j].seat,[0]*11)[1])
                hu=_lookup(key,strongest)
                # Punish truly indiscriminate raising, without assuming an unknown
                # small raise is weak. Multiple opponents still need real equity.
                if r and any(loose) and all(qs[j]>.45 for j in committed):
                    target=.68 if n==1 else .51 if n==2 else .43 if n==3 else 1/(n+1)+.20
                    if n>=5:target=max(target,.48)
                    if n==1 and depth>22:target=.82
                    if eq>target+risk*.7:return raise_to(r.max_amount)
                if r and not any(loose) and hu>(.60 if len(raisers)==1 else .67)+risk and pct<(.15 if strongest>.35 else .055):
                    return raise_to(me.bet+call+max(3*bb,pot*.95+call*.3))
            # Deep stacks reward pairs and suited hands with cheap implied odds.
            pair=state.cards[0][0]==state.cards[1][0]
            suited=state.cards[0][1]==state.cards[1][1]
            realization=.88+(.06 if position else 0.)
            if depth<15:realization=.98
            penalty=.015*min(3,max(0,behind-len(committed)))
            implied=0.
            if call<.07*me.stack and call>0 and (pair or suited):
                implied=min(.055,(.035 if pair else .018)*min(2.,me.stack/max(1,call)/20))
            # Avoid buying many tiny raises with a hand that cannot stand the next
            # raises from an already identified compulsive opponent.
            if any(loose) and n>=2 and r and depth>8 and eq<(.68 if n==1 else .51 if n==2 else .43):
                if call>.02*me.stack:return passive()
            if 'call' in legal and eq*realization+implied>odds+risk+penalty+.012:
                return Action.call()
            return passive()

        eq,cat,fd,sd,hv=_post_equity(state,m,opps,qs,hero,key,bb,deadline)
        stage=len(state.board)-2;n=len(opps)
        draw=fd or sd;made=(hv>>24)>=1
        boardr=[_CMAP[c].rank for c in state.board]
        pairs=cat==1 and ((hv>>16)&15)>=max(boardr) and any(c.rank==((hv>>16)&15) for c in hero)
        wet=len(set(c[1] for c in state.board))<=2 or max(boardr)-min(boardr)<=5
        # Equity must pay for position, future pressure, and tournament survival.
        margin=(.018 if stage==1 else .012 if stage==2 else .005)
        if not position and stage<3:margin+=.012
        if draw and stage<3 and call<.18*me.stack:margin-=.025
        if call:
            value=(.72 if n==1 else .57 if n==2 else .48)
            if any(loose):value=(.79 if n==1 else .59 if n==2 else .49)
            if r and eq>value+risk and (cat>=2 or pairs or (draw and eq>.59)):
                return raise_to(me.bet+call+max(bb,(pot+call)*.78))
            if eq>odds+risk+margin:
                return Action.call() if 'call' in legal else passive()
            return passive()
        if not r:return passive()
        # Free checks are retained for medium showdown hands. Strong value and
        # selective draw/continuation bets build pots and deny free equity.
        target=.61 if n==1 else .46 if n==2 else max(.30,1/(n+1)+.14)
        if any(loose):target=max(target,.79 if n==1 else .58 if n==2 else .46)
        value=eq>target and (cat>=1 or draw)
        bluff=False
        if all(nits):bluff=True
        elif n==1 and not any(loose):
            if stage==1 and own[1] and not made and eq>.30:bluff=rand<(.58 if not wet else .32)
            elif draw and eq>.34:bluff=rand<.48
            elif stage==3 and cat==0 and eq<.18 and position:bluff=rand<.10
        if value or bluff:
            fraction=(.66 if wet else .50) if stage==1 else .66 if stage==2 else .72
            if all(nits):fraction=.36
            if any(loose) and value:fraction=.90
            return raise_to(me.bet+max(bb,pot*fraction))
        return passive()
