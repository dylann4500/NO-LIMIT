"""Range equity / tournament EV agent. All mutable information is in memory."""
import bisect
import json
import math
import os
import random
import time

import eval7
import numpy as np
import poker_agent_sdk
from poker_agent_sdk import Action

_RANKS = '23456789TJQKA'
_SUITS = 'cdhs'
_CARD_STR = [r+s for r in _RANKS for s in _SUITS]
_CARDS = [eval7.Card(c) for c in _CARD_STR]
_CI = {c:i for i,c in enumerate(_CARD_STR)}
with open(os.path.join(os.path.dirname(__file__), 'equity.json')) as _f:
    _DATA = json.load(_f)
_WIDTHS = _DATA['widths']
_PERCENT = _DATA['percentile']
_EQ = _DATA['equity']
_MULTI = _DATA['multiway']
_CORR_WIDTHS=(.05,.18,.5,1.0)
_CORR_EXP={}
for _key,_random_multi in _MULTI.items():
    _curves=[]
    for _width in _CORR_WIDTHS:
        _values=_DATA.get('multiway_ranges',{}).get(str(_width),{}).get(_key,_random_multi)
        _curves.append(tuple(math.log(max(.0005,q))/math.log(max(.01,min(.99,_values[0])))/(i+1) for i,q in enumerate(_values)))
    _CORR_EXP[_key]=tuple(_curves)
_EVAL = eval7.evaluate
_STRAIGHTS = tuple(sum(1 << r for r in range(k,k+5)) for k in range(9)) + (4111,)
_STRAIGHT_COVER=[]
for _r in range(8192):
    _cover=0
    for _window in _STRAIGHTS:
        if (_r&_window).bit_count()>=4:_cover|=_r&_window
    _STRAIGHT_COVER.append(_cover)


def _key_ids(i,j):
    a,b=max(i//4,j//4),min(i//4,j//4)
    return _RANKS[a]+_RANKS[b]+('' if a==b else ('s' if i%4==j%4 else 'o'))


# Immutable combinations and random schedules are safe across tables/copies.
_COMBOS=[]
for _i in range(52):
    for _j in range(_i):
        _COMBOS.append((_i,_j,(1<<_i)|(1<<_j),(_CARDS[_i],_CARDS[_j]),(1<<(_i//4))|(1<<(_j//4)),_PERCENT.get(_key_ids(_i,_j),.5)))
_rng=random.Random(94701281)
_rng.shuffle(_COMBOS)
_RANGES=[]
for _w in _WIDTHS:
    _RANGES.append(tuple(c for c in _COMBOS if c[5]<=_w))
_BY_CODE={c[0]*52+c[1]:c for c in _COMBOS}
_FAST_POOL=tuple(tuple(source[::max(1,len(source)//96)][:96]) for source in _RANGES)

_NP_RANGES=tuple((
    np.array([c[2] for c in source],dtype=np.uint64),
    np.array([c[4] for c in source],dtype=np.uint16),
    np.array([c[0]%4 for c in source],dtype=np.int8),
    np.array([c[1]%4 for c in source],dtype=np.int8),
) for source in _RANGES)
_NP_STRAIGHT=np.array(_STRAIGHT_COVER,dtype=np.uint16)
_NP_TARGET=(np.arange(96)+.5)/96

_SCHEDULE=[]
for _ in range(2048):
    _deck=list(range(52))
    _rng.shuffle(_deck)
    _SCHEDULE.append((tuple(_rng.getrandbits(30) for _ in range(10)),tuple(_deck)))
del _rng, _deck


def _eq_pre(key,width):
    i=bisect.bisect_left(_WIDTHS,width)
    if i==0:return _EQ[key][0]
    if i>=len(_WIDTHS):return _EQ[key][-1]
    t=(width-_WIDTHS[i-1])/(_WIDTHS[i]-_WIDTHS[i-1])
    return _EQ[key][i-1]*(1-t)+_EQ[key][i]*t


def _correlation(key,n,width):
    if n<=1:return 1.0
    i=bisect.bisect_left(_CORR_WIDTHS,width)
    curves=_CORR_EXP[key]
    if i==0:return curves[0][n-1]
    if i>=len(_CORR_WIDTHS):return curves[-1][n-1]
    t=(width-_CORR_WIDTHS[i-1])/(_CORR_WIDTHS[i]-_CORR_WIDTHS[i-1])
    return curves[i-1][n-1]*(1-t)+curves[i][n-1]*t


def _joint_pre(key,widths):
    if not widths:return 1.0
    eqs=[_eq_pre(key,w) for w in widths]
    if len(eqs)==1:return eqs[0]
    # Calibrate the independence approximation to actual multiway simulations.
    n=min(7,len(eqs))
    return math.prod(eqs)**_correlation(key,n,sum(widths)/n)


def _stats(memory,events):
    try:m=json.loads(memory) if memory else {}
    except (ValueError,TypeError):m={}
    if not isinstance(m,dict):m={}
    ss=m.setdefault('s',{})
    seen=m.get('seen',0);vp=m.get('vp',0);pf=m.get('pf',0);street=m.get('st',0)
    for e in events:
        kind=e.kind
        if kind=='hand':seen=vp=pf=street=0;continue
        if kind=='board':street+=len(e.cards or ());continue
        if e.seat is None:continue
        k=str(e.seat);a=ss.get(k)
        if a is None:a=ss[k]=[0]*14
        elif len(a)<14:a.extend([0]*(14-len(a)))
        bit=1<<int(e.seat)
        if kind in ('blind','ante','fold','check','call','raise'):
            if not seen&bit:a[0]+=1;seen|=bit
        if kind in ('fold','check','call','raise'):
            a[3]+=1
            if kind=='fold':a[4]+=1
            elif kind=='raise':a[5]+=1
            elif kind=='call':a[6]+=1
            else:a[7]+=1
        if kind in ('call','raise'):
            if street==0:
                if not vp&bit:a[1]+=1;vp|=bit
                if kind=='raise' and not pf&bit:a[2]+=1;pf|=bit
            elif kind=='raise':a[8]+=1
            else:a[9]+=1
        if street and kind=='fold':a[10]+=1
        elif street and kind=='check':a[11]+=1
        if kind=='show' and pf&bit and e.cards and len(e.cards)==2:
            try:
                pct=_PERCENT[_key_ids(_CI[e.cards[0]],_CI[e.cards[1]])]
                a[12]+=1;a[13]+=pct
            except (KeyError,ValueError):pass
    m.update(seen=seen,vp=vp,pf=pf,st=street)
    return m,ss


def _profile(a):
    if not a:return False,False,.42,.28,.50
    h,v,p,d,f,r,c,k,pr,pc,pf,pk,shown,showrank=a
    maniac=(h>=3 and r>=8 and r/max(1,d)>.85) or (h>=4 and p==h) or (h>=9 and p/h>.82)
    if shown>=2 and showrank/shown<.15 and h<12:maniac=False
    folder=h>=4 and v==0 and f>=3
    fold=(f-pf+3.0)/(f-pf+c-pc+r-pr+7.0)
    postfold=(pf+3.0)/(pf+pr+pc+6.0)
    vp=(v+2.4)/(h+8.0)
    return maniac,folder,fold,vp,postfold


def _history(state):
    infos={s.seat:[0,0,0,0.0,0,0,0] for s in state.seats}
    # info: preflop raises, preflop calls, current raises, bet/pot, previous postflop aggression, previous calls
    street=0;pot=0;bets={};contrib={};raises=[];preacted=set();first=None
    for e in state.history:
        kind=e.kind;s=e.seat
        if kind=='board':
            street+=len(e.cards or ())
            bets={}
            for a in infos.values():
                a[4]+=a[2];a[2]=0;a[3]=0.0
            continue
        if s is None or s not in infos:continue
        a=infos[s]
        if kind in ('blind','ante','call'):
            amt=int(e.amount or 0)
            pot+=amt;contrib[s]=contrib.get(s,0)+amt
            if kind!='ante':bets[s]=bets.get(s,0)+amt
        if kind=='raise':
            total=int(e.amount or 0);old=bets.get(s,0);delta=max(0,total-old)
            high=max(bets.values(),default=0)
            frac=max(0,total-high)/max(1,pot+max(0,high-old))
            pot+=delta;contrib[s]=contrib.get(s,0)+delta;bets[s]=total
            if street==0:
                a[0]+=1;a[6]=max(a[6],total);raises.append(s)
                if first is None:first=s
            else:a[2]+=1;a[3]=max(a[3],frac)
        if street==0 and kind in ('fold','call','raise','check'):
            preacted.add(s)
            if kind=='call':a[1]+=1
        elif kind=='call':a[5]+=1
    return infos,raises,preacted,contrib,first


def _opening_width(behind):
    return (.70,.62,.43,.30,.24,.20,.17,.145)[min(7,max(0,behind))]


def _range_width(opp,info,ss,raises,nstart,button,seat_order,bb):
    maniac,folder,fold,vpip,postfold=_profile(ss.get(str(opp.seat)))
    if maniac:return 1.0
    a=info
    if a[0]:
        # Position-aware open; subsequent raises are substantially narrower.
        try:behind=len(seat_order)-1-seat_order.index(opp.seat)
        except ValueError:behind=3
        w=_opening_width(behind)
        if len(raises)>=2:
            if raises[-1]==opp.seat:w=.065 if len(raises)==2 else .028
            else:w=min(w,.20)
        observed=ss.get(str(opp.seat))
        pfr=(observed[2]+1.7)/(observed[0]+8.) if observed else .2125
        w*=max(.55,min(1.7,pfr/.22))
        if len(raises)==1 and a[6]>5*bb and opp.stack+a[6]>25*bb:
            w*=max(.22,(4*bb/a[6])**.5)
            if a[6]>25*bb:w=min(w,.045)
        return max(.018,min(.65,w))
    if a[1]:return min(.75,max(.18,vpip*1.6))
    return .85 if nstart>2 else 1.0


def _pot_layers(contrib,hero,cost,opps):
    paid=dict(contrib)
    paid[hero]=paid.get(hero,0)+cost
    cap=paid[hero]
    levels=sorted(set(min(v,cap) for v in paid.values() if v>0))
    out=[];prev=0
    for level in levels:
        amount=sum(max(0,min(v,level)-prev) for v in paid.values())
        eligible=tuple(s.seat for s in opps if paid.get(s.seat,0)>=level)
        if amount>0:out.append((amount,eligible))
        prev=level
    return out


def _draw(meta,board_ranks,board_suits):
    i,j,mask,cards,ranks,pct=meta
    si,sj=i%4,j%4
    fd=board_suits[si]+1+(si==sj)>=4 or board_suits[sj]+1+(si==sj)>=4
    rd=ranks|board_ranks
    sd=False
    if ranks & ~board_ranks:
        sd=bool(ranks & ~board_ranks & _STRAIGHT_COVER[rd])
    return fd,sd


def _make_pool(width,info,maniac,board,boardmask,knownmask,seed,ncand,need_cont=True):
    ri=min(len(_WIDTHS)-1,bisect.bisect_left(_WIDTHS,width))
    source=_RANGES[ri]
    n=len(source)
    step=max(1,n//ncand)
    offset=seed%n
    sample=[]
    # Evenly spaced samples of a shuffled source, with exact card removal.
    for t in range(min(n,ncand+24)):
        c=source[(offset+t*step)%n]
        if c[2]&knownmask:continue
        sample.append((_EVAL(board+c[3]),c))
        if len(sample)>=ncand:break
    if not sample:
        sample=[(_EVAL(board+c[3]),c) for c in _COMBOS if not c[2]&knownmask][:32]
    sample.sort(key=lambda z:z[0])
    br=0;bs=[0]*4
    for idx in boardmask:
        br|=1<<(idx//4);bs[idx%4]+=1
    street=len(board)
    nr,frac,prior,pc=info[2],info[3],info[4],info[5]
    pressure=bool(nr or prior or pc)
    threshold=.15
    bluff=.30
    if nr:
        threshold=(.24 if street==3 else .36 if street==4 else .48)+min(.22,max(0,frac-.25)*.20)+(.17 if nr>1 else 0)
        bluff=.20 if street==3 else .15 if street==4 else .11
    elif prior or pc:
        threshold=.15+min(.18,prior*.07+pc*.03)
        bluff=.35
    if maniac:threshold=.0;bluff=1.0;pressure=False
    full=[];cont=[];cum=[];cumc=[];total=totalc=0.0
    size=max(1,len(sample)-1)
    for j,(score,c) in enumerate(sample):
        q=j/size
        fd,sd=_draw(c,br,bs) if street<5 else (False,False)
        w=bluff+(1-bluff)*max(0.,(q-threshold)/(1-threshold)) if pressure else 1.0
        if fd:w=max(w,.70 if street==3 else .52)
        elif sd:w=max(w,.42 if street==3 else .30)
        # Calling range for a moderate value bet, separate from current range.
        if need_cont:
            cw=w*(.06+.94*max(0.,min(1.,(q-.25)/.55)))
            if fd:cw=max(cw,w*.88)
            elif sd:cw=max(cw,w*.50)
            if maniac:cw=w
            totalc+=cw;cumc.append(totalc);cont.append(c)
        total+=w
        cum.append(total);full.append(c)
    count=80 if ncand>=80 else 48
    pool=[full[min(len(full)-1,bisect.bisect_left(cum,(j+.5)*total/count))] for j in range(count)]
    cp=[cont[min(len(cont)-1,bisect.bisect_left(cumc,(j+.5)*totalc/count))] for j in range(count)] if need_cont else pool
    return pool,cp


def _make_pool_vector(width,info,maniac,board,boardmask,knownmask,seed,ncand,need_cont=True):
    ri=min(len(_WIDTHS)-1,bisect.bisect_left(_WIDTHS,width));source=_RANGES[ri];n=len(source)
    masks,ranks,s1,s2=_NP_RANGES[ri];step=max(1,n//ncand)
    idx=(seed%n+np.arange(min(n,ncand+32))*step)%n
    idx=idx[(masks[idx]&np.uint64(knownmask))==0][:ncand]
    if len(idx)<2:return _make_pool(width,info,maniac,board,boardmask,knownmask,seed,64,need_cont)
    vals=np.fromiter((_EVAL(board+source[int(i)][3]) for i in idx),dtype=np.int32,count=len(idx))
    idx=idx[np.argsort(vals,kind='stable')]
    br=0;bs=np.zeros(4,dtype=np.int8)
    for c in boardmask:br|=1<<(c//4);bs[c%4]+=1
    street=len(board);nr,frac,prior,pc=info[2:6];pressure=nr or prior or pc
    threshold=.15;bluff=.3
    if nr:
        threshold=(.24 if street==3 else .36 if street==4 else .48)+min(.22,max(0,frac-.25)*.20)+(.17 if nr>1 else 0)
        bluff=.20 if street==3 else .15 if street==4 else .11
    elif prior or pc:threshold=.15+min(.18,prior*.07+pc*.03);bluff=.35
    if maniac:pressure=False
    q=np.arange(len(idx))/max(1,len(idx)-1)
    w=bluff+(1-bluff)*np.maximum(0,(q-threshold)/(1-threshold)) if pressure else np.ones(len(idx))
    if street<5:
        si=s1[idx];sj=s2[idx];same=(si==sj)
        fd=(bs[si]+1+same>=4)|(bs[sj]+1+same>=4)
        r=ranks[idx];sd=(r&(8191^br)&_NP_STRAIGHT[r|br])!=0
        w=np.maximum(w,np.where(fd,.70 if street==3 else .52,np.where(sd,.42 if street==3 else .3,0)))
    cum=np.cumsum(w);pidx=idx[np.searchsorted(cum,_NP_TARGET*cum[-1])]
    pool=[source[i] for i in pidx.tolist()]
    if not need_cont:return pool,pool
    cw=w*(.06+.94*np.clip((q-.25)/.55,0,1))
    if street<5:cw=np.maximum(cw,w*np.where(fd,.88,np.where(sd,.50,0)))
    if maniac:cw=w
    cum=np.cumsum(cw);cidx=idx[np.searchsorted(cum,_NP_TARGET*cum[-1])]
    return pool,[source[i] for i in cidx.tolist()]

def _hu_equity(hero,pool,board,iters):
    vr=[(c[3],1.0) for c in pool]
    if len(board)==5:return eval7.py_hand_vs_range_exact(hero,vr,board)
    return eval7.py_hand_vs_range_monte_carlo(hero,vr,board,iters)


def _multi_equity(hero,pools,board,known,seed,trials,deadline=0,layers=None):
    wins=0.0;n=len(pools);missing=5-len(board)
    # Stop a trial as soon as an opponent beats the hero.
    done=0
    for t in range(trials):
        if deadline and t>=8 and t%4==0 and time.perf_counter_ns()>deadline:break
        done+=1
        draws,deck=_SCHEDULE[(seed+t*31)&2047]
        used=known;holes=[]
        for j,pool in enumerate(pools):
            k=draws[j]%len(pool);c=pool[k];tries=0
            while c[2]&used and tries<min(20,len(pool)):
                k=(k+7)%len(pool);c=pool[k];tries+=1
            if c[2]&used:
                # Rare narrow-range collisions: find a legal combination.
                c=next((c for c in _COMBOS if not c[2]&used),None)
            used|=c[2];holes.append(c[3])
        if missing:
            extra=[]
            for i in deck:
                if not (1<<i)&used:
                    extra.append(_CARDS[i])
                    if len(extra)==missing:break
            runout=board+tuple(extra)
        else:runout=board
        hv=_EVAL(hero+runout);ties=1
        if layers:
            beat=tied=0
            for j,h in enumerate(holes):
                v=_EVAL(h+runout)
                if v>hv:beat|=1<<j
                elif v==hv:tied|=1<<j
            wins+=sum(weight/(1+(tied&mask).bit_count()) for weight,mask in layers if not beat&mask)
            continue
        for h in holes:
            v=_EVAL(h+runout)
            if v>hv:break
            if v==hv:ties+=1
        else:wins+=1.0/ties
    return wins/max(1,done)


def _icm(stacks,hero,payouts):
    """Exact independent-chip-model prize equity, including already paid places."""
    h=stacks[hero]
    other=[v for i,v in enumerate(stacks) if i!=hero and v>0]
    if h<=0:return payouts[len(other)] if len(other)<len(payouts) else 0.0
    total=h+sum(other)
    if not other:return payouts[0]
    paid=sum(p>0 for p in payouts)
    if paid<=3:
        result=payouts[0]*h/total
        if paid>=2:
            p2=sum(v/total*h/(total-v) for v in other)
            result+=payouts[1]*p2
        if paid>=3:
            p3=0.0
            for i,a in enumerate(other):
                for b in other[:i]:
                    p3+=(a/total*b/(total-a)+b/total*a/(total-b))*h/(total-a-b)
            result+=payouts[2]*p3
        return result
    # Generic payouts are allowed by the API; memoize subsets for those tables.
    memo={}
    def rec(mask,tot,depth):
        if depth>=len(payouts):return 0.0
        if not mask:return float(payouts[depth])
        if mask in memo:return memo[mask]
        value=h/tot*payouts[depth]
        for i,v in enumerate(other):
            if mask&(1<<i):value+=v/tot*rec(mask^(1<<i),tot-v,depth+1)
        memo[mask]=value
        return value
    return rec((1<<len(other))-1,total,0)


def _prize_value(stacks,hero,payouts,starting):
    # Simultaneous busts rank by stacks at the start of this hand. A zero
    # stack in a hypothetical multiway outcome is not an earlier elimination.
    if stacks[hero]>0:return _icm(stacks,hero,payouts)
    ahead=sum(v>0 or (i!=hero and starting[i]>starting[hero]) for i,v in enumerate(stacks))
    tied=sum(i!=hero and v<=0 and starting[i]==starting[hero] for i,v in enumerate(stacks))
    return sum(payouts[r] if r<len(payouts) else 0. for r in range(ahead,ahead+tied+1))/(tied+1)


def _utility_context(state,me,contrib):
    payouts=getattr(state.config,'payouts',None) or [50,30,20,0]
    if state.players_remaining>5 or state.players_remaining<=2 or sum(p>0 for p in payouts)<=1:return None
    seats=[s for s in state.seats if s.status!='busted']
    index={s.seat:i for i,s in enumerate(seats)}
    base=[float(s.stack) for s in seats]
    hero=index[me.seat]
    starting=[s.stack+contrib.get(s.seat,0) for s in seats]
    cache={}
    def utility(stacks):
        k=tuple(stacks)
        if k not in cache:cache[k]=_prize_value(stacks,hero,payouts,starting)
        return cache[k]
    return base,hero,index,utility


def _icm_call_price(state,me,opps,cost,pot,contrib):
    payouts=getattr(state.config,'payouts',None) or [50,30,20,0]
    if len(payouts)<2 or sum(p>0 for p in payouts)<2 or state.players_remaining<=2:return 0.0
    if sum(p>0 for p in payouts)>3 and state.players_remaining>5:return 0.0
    if cost<me.stack*.20 or (state.players_remaining>5 and cost<me.stack*.70):return 0.0
    seats=[s for s in state.seats if s.status!='busted']
    indexes={s.seat:i for i,s in enumerate(seats)}
    hero=indexes[me.seat]
    villain=indexes[max(opps,key=lambda s:s.bet).seat]
    base=[float(s.stack) for s in seats]
    base[villain]+=max(0,state.pot-pot)
    fold=base[:];fold[villain]+=pot
    win=base[:];win[hero]+=pot
    lose=base[:];lose[hero]-=cost;lose[villain]+=pot+cost
    starting=[s.stack+contrib.get(s.seat,0) for s in seats]
    f=_prize_value(fold,hero,payouts,starting);w=_prize_value(win,hero,payouts,starting);l=_prize_value(lose,hero,payouts,starting)
    if w<=l:return 1.0
    return max(0.,min(.99,(f-l)/(w-l)))


def _risk(state,me,opps,cost,pot):
    payouts=getattr(state.config,'payouts',None) or [50,30,20,0]
    paid=sum(1 for p in payouts if p>0)
    n=state.players_remaining
    frac=cost/max(1,me.stack)
    if n==2:return .006*frac
    risk=.012*frac
    if n==paid+1 and paid>=2:
        smallest=min((s.stack+s.bet for s in state.seats if s.status!='busted' and s.seat!=me.seat),default=me.stack)
        risk+=(.025+.075*max(0,1-smallest/max(1,me.stack)))*frac
    elif n<=paid:risk+=.018*frac
    return risk


def _finish(action,m,state):
    data=json.dumps(m,separators=(',',':')).encode()
    limit=getattr(state.config,'memory_bytes',65536) or 65536
    return action,data[:limit]


class Agent(poker_agent_sdk.Agent):
    def act(self,state,memory):
        started=time.perf_counter_ns()
        bank=float(getattr(state,'time_bank_ms',100) or 0)
        low_bank=bank<30
        deadline=started+int(min(.74,float(state.config.decision_ms or 1)*.74)*1000000)
        legal={a.kind.value:a for a in state.legal_actions}
        m,ss=_stats(memory,state.events)
        free='check' in legal
        default=Action.check() if free else Action.fold() if 'fold' in legal else Action.call()
        me=next(s for s in state.seats if s.seat==state.seat)
        opponents=[s for s in state.seats if s.seat!=state.seat and s.status in ('active','all_in')]
        if not opponents:return _finish(default,m,state)
        raisable=[s for s in opponents if s.status=='active' and s.stack>0]
        raise_legal=legal.get('raise') if raisable else None
        def raise_to(total):
            if raise_legal is None:return default
            total=max(int(raise_legal.min_amount),min(int(raise_legal.max_amount),int(total)))
            return Action.raise_to(total)
        bb=max(1,int(state.blinds[1]))
        pot=max(1,int(state.pot));cost=min(me.stack,max(0,int(state.to_call)))
        infos,raises,acted,contrib,first=_history(state)
        # Remove unreachable side-pot money from the price of an all-in call.
        if cost>=me.stack and contrib:
            cap=contrib.get(me.seat,0)+cost
            reachable=sum(min(v,cap) for v in contrib.values())
            if reachable>0:pot=min(pot,reachable)
        risk=max(_risk(state,me,opponents,cost,pot),_icm_call_price(state,me,opponents,cost,pot,contrib)-cost/(pot+cost))
        live=sorted(s.seat for s in state.seats if s.status!='busted')
        after=[s for s in live if s>state.button]+[s for s in live if s<=state.button]
        order=(after[2:]+after[:2]) if len(after)>2 else [state.button]+[s for s in live if s!=state.button]
        profiles={s.seat:_profile(ss.get(str(s.seat))) for s in opponents}
        widths={s.seat:_range_width(s,infos[s.seat],ss,raises,len(live),state.button,order,bb) for s in opponents}
        folders=all(profiles[s.seat][1] for s in opponents)
        # An empirically deterministic fold-to-bet opponent needs no simulation.
        if folders and raise_legal and len(raisable)==len(opponents):
            return _finish(raise_to(max(me.bet+cost+bb,raise_legal.min_amount)),m,state)
        ids=[_CI[c] for c in state.cards]
        key=_key_ids(*ids)
        pct=_PERCENT[key]
        eff=min(me.stack+me.bet,max(s.stack+s.bet for s in opponents))
        position=all(after.index(s.seat)<after.index(me.seat) for s in raisable) if raisable else True
        seed=(state.hand_number*101+ids[0]*71+ids[1]*37+state.seat*29+len(state.history)*13)&2047
        if not state.board:
            action=self._preflop(state,me,opponents,raisable,legal,raise_to,raise_legal,default,free,bb,pot,cost,risk,infos,raises,acted,order,profiles,widths,key,pct,eff,position,ss,contrib)
            return _finish(action,m,state)
        board_ids=[_CI[c] for c in state.board]
        board=tuple(_CARDS[i] for i in board_ids)
        known=sum(1<<i for i in ids+board_ids)
        hero=tuple(_CARDS[i] for i in ids)
        n=len(opponents)
        low_bank=low_bank or time.perf_counter_ns()>deadline-300000
        ncand=88 if n==1 else max(14,84//n)
        pools=[];continuing=[];discounts=[]
        cached=m.get('cache',{})
        cached_pools={row[0]:row for row in cached.get('p',[])} if cached.get('h')==state.hand_number else {}
        for j,s in enumerate(opponents):
            if low_bank:
                old=cached_pools.get(s.seat)
                if old:
                    pool=[_BY_CODE[k] for k in old[2] if not _BY_CODE[k][2]&known]
                    extra_pressure=max(0,infos[s.seat][2]-(old[1] if cached.get('b')==len(board) else 0))
                    discount=.055*extra_pressure
                else:
                    ri=min(len(_WIDTHS)-1,bisect.bisect_left(_WIDTHS,widths[s.seat]))
                    pool=[c for c in _FAST_POOL[ri] if not c[2]&known]
                    discount=.075*infos[s.seat][2]+.035*min(2,infos[s.seat][4])
                if not pool:pool=[c for c in _COMBOS if not c[2]&known][:48]
                cp=pool
                discounts.append(0. if profiles[s.seat][0] else min(.25,discount))
            else:
                if j and time.perf_counter_ns()>deadline-200000:ncand=min(ncand,12)
                builder=_make_pool_vector if n==1 else _make_pool
                pool,cp=builder(widths[s.seat],infos[s.seat],profiles[s.seat][0],board,board_ids,known,seed+j*127,192 if n==1 else ncand,n==1 and raise_legal is not None)
            pools.append(pool);continuing.append(cp)
        if not low_bank:
            m['cache']={'h':state.hand_number,'b':len(board),'p':[[s.seat,infos[s.seat][2],[c[0]*52+c[1] for c in pools[j]]] for j,s in enumerate(opponents)]}
        if n==1:
            eq=_hu_equity(hero,pools[0],board,192 if low_bank else 512 if time.perf_counter_ns()<deadline-150000 else 128)
            if low_bank:eq=max(0.,eq-discounts[0])
            ceq=max(0.,eq-(0. if profiles[opponents[0].seat][0] else .08)) if low_bank else _hu_equity(hero,continuing[0],board,320) if raise_legal and time.perf_counter_ns()<deadline-100000 else eq
        else:
            layers=None
            if any(s.status=='all_in' for s in opponents):
                raw_layers=_pot_layers(contrib,me.seat,cost,opponents)
                total=sum(a for a,_ in raw_layers)
                if total:
                    indexes={s.seat:i for i,s in enumerate(opponents)}
                    layers=[(amount/total,sum(1<<indexes[i] for i in ids)) for amount,ids in raw_layers]
            eq=_multi_equity(hero,pools,board,known,seed,16 if low_bank else max(20,96//n),deadline-70000,layers)
            if low_bank:eq=max(0.,eq-max(discounts,default=0)*.8)
            ceq=max(0.,eq-.10)
        odds=cost/(pot+cost)
        realization=1.0 if len(board)==5 or cost>=me.stack else .92 if len(board)==3 else .97
        if not position and cost<me.stack:realization-=.025
        call_ev=eq*realization*(pot+cost)-cost-risk*(pot+cost)
        can_call=free or ('call' in legal and eq*realization>=odds+risk+.008)
        action=Action.check() if free else Action.call() if can_call else default
        if not raise_legal:return _finish(action,m,state)
        active_n=len(raisable)
        has_allin=active_n<n
        max_total=min(int(raise_legal.max_amount),int(max(s.stack+s.bet for s in raisable)),int(me.stack+me.bet))
        # Never bluff into an all-in player's protected main pot.
        if has_allin and eq<.64:return _finish(action,m,state)
        fold_all=1.0
        for s in raisable:
            maniac,folder,fold,vp,postfold=profiles[s.seat]
            fp=.015 if maniac else min(.80,max(.23,postfold))
            if infos[s.seat][2]:fp*=.48
            if cost:fp*=.70
            if folder:fp=.995
            fold_all*=fp
        if has_allin:fold_all=0.0
        # Compare bets to checking/calling, with equity against continuing hands.
        baseline=eq*pot*realization if free else max(0.,call_ev)
        best=baseline+max(1,pot*.018)
        ctx=_utility_context(state,me,contrib) if n==1 and not low_bank and time.perf_counter_ns()<deadline-200000 else None
        if ctx:
            stacks,hi,index,utility=ctx
            vi=index[opponents[0].seat]
            stacks[vi]+=max(0,state.pot-pot)
            won=stacks[:];won[hi]+=pot
            lost=stacks[:];lost[vi]+=pot
            u_won=utility(won);u_lost=utility(lost)
            if free:baseline_u=eq*realization*u_won+(1-eq*realization)*u_lost
            else:
                cl=stacks[:];cl[hi]-=cost;cl[vi]+=pot+cost
                baseline_u=max(u_lost,eq*realization*u_won+(1-eq*realization)*utility(cl))
            best_u=baseline_u+.012*max(0,u_won-u_lost)
        raise_risk=max(risk,_risk(state,me,opponents,min(me.stack,eff-me.bet),pot))
        fractions=(.33,.65,1.0) if free else (.60,1.0)
        if ceq>.80 or (eff-me.bet<=pot*1.5 and ceq>.62):fractions=fractions+(2.5,)
        for fraction in fractions:
            if time.perf_counter_ns()>deadline:break
            if free:target=me.bet+max(bb,int(pot*fraction))
            else:target=me.bet+cost+int((pot+cost)*fraction)
            target=max(int(raise_legal.min_amount),min(max_total,target))
            if target<raise_legal.min_amount:continue
            extra=target-me.bet
            # Avoid constructing a practically committed small bet.
            if me.stack-extra<max(bb,extra*.22) and max_total>=me.stack+me.bet:target=me.stack+me.bet;extra=me.stack
            additions=[min(s.stack,max(0,target-s.bet)) for s in raisable]
            mean_add=sum(additions)/max(1,len(additions))
            fp=min(.94,fold_all*(.80+.30*fraction)) if not has_allin else 0.0
            # Larger sizes are called by a stronger subset of the range.
            q=max(0.,ceq-max(0.,fraction-.65)*.035)
            if n>1:q=max(0.,eq-.045*len(raisable))
            ev=fp*pot+(1-fp)*(q*(pot+extra+mean_add)-extra)-raise_risk*(extra+pot)*min(1.,extra/max(1,me.stack))
            if q<.49 and extra>pot*1.25:continue
            # Restrict bluffs to heads-up, where fold estimates are meaningful.
            if q<.49 and (n>1 or has_allin or (seed%100)>36):continue
            if ctx:
                bw=stacks[:];bw[hi]+=pot+additions[0];bw[vi]-=additions[0]
                bl=stacks[:];bl[hi]-=extra;bl[vi]+=pot+extra
                point_ev=fp*u_won+(1-fp)*(q*utility(bw)+(1-q)*utility(bl))
                if point_ev>best_u:
                    best_u=point_ev;action=raise_to(target)
            elif ev>best:
                best=ev;action=raise_to(target)
        return _finish(action,m,state)

    @staticmethod
    def _preflop(state,me,opps,active,legal,raise_to,rl,default,free,bb,pot,cost,risk,infos,raises,acted,order,profiles,widths,key,pct,eff,position,ss,contrib):
        # Distinguish opponents already committed to this pot from players yet to act.
        committed=[s for s in opps if infos[s.seat][0] or infos[s.seat][1] or s.status=='all_in']
        behind=[s for s in active if s.seat not in acted]
        open_width=_opening_width(len(behind))
        if not raises and not any(s.status=='all_in' for s in opps):
            if not rl:return Action.check() if free else Action.call() if cost/(pot+cost)<.2 and pct<.65 else default
            limpers=sum(bool(infos[s.seat][1]) for s in opps)
            if not limpers:
                folds=[profiles[s.seat][2] for s in active]
                if active and all(profiles[s.seat][1] for s in active):open_width=1.0
                elif len(active)<=3 and sum(folds)/len(folds)>.60:open_width=min(.95,open_width+.18)
            else:open_width=min(.45,open_width*.82)
            if eff<=12*bb:
                # Independent call events; actual joint showdown equity is calibrated
                # to the precomputed multiway simulation for this exact hand class.
                probs=[];cwidth=[];amounts=[]
                target=min(me.bet+me.stack,max(s.bet+s.stack for s in active)) if active else eff
                for s in active:
                    maniac,folder,fold,vp,postfold=profiles[s.seat]
                    cw=min(.43,.12+.8*bb/max(2*bb,target-s.bet))
                    if maniac:cw=1.0
                    if folder:cw=.001
                    probs.append(cw);cwidth.append(max(.015,cw));amounts.append(min(s.stack,max(0,target-s.bet)))
                ev=0.0
                ctx=_utility_context(state,me,contrib) if state.players_remaining<=4 and len(active)<=2 else None
                point_ev=0.0
                if ctx:
                    stacks,hi,index,utility=ctx
                    stolen=stacks[:];stolen[hi]+=pot
                    u_stolen=utility(stolen)
                    folded=stacks[:];folded[index[max(active,key=lambda s:s.bet).seat]]+=pot
                    u_folded=utility(folded)
                    if free:
                        q0=_joint_pre(key,[widths[s.seat] for s in committed])
                        u_folded=q0*u_stolen+(1-q0)*u_folded
                push_risk=max(risk,_risk(state,me,opps,min(me.stack,target-me.bet),pot))
                # Build the call/fold distribution once; reuse equity products,
                # contributions and effective risk rather than rescanning subsets.
                cases=[(1.,0,1.,0,0,0,0.)]
                for i,p in enumerate(probs):
                    qe=_eq_pre(key,cwidth[i]);next_cases=[]
                    for prob,nc,prod,called,top,mask,total_width in cases:
                        if prob*(1-p)>1e-9:next_cases.append((prob*(1-p),nc,prod,called,top,mask,total_width))
                        if prob*p>1e-9:next_cases.append((prob*p,nc+1,prod*qe,called+amounts[i],max(top,active[i].bet+active[i].stack),mask|(1<<i),total_width+cwidth[i]))
                    cases=next_cases
                for prob,nc,prod,called,top,mask,total_width in cases:
                    if not nc:
                        ev+=prob*pot
                        if ctx:point_ev+=prob*u_stolen
                    else:
                        q=prod**_correlation(key,nc,total_width/nc)
                        actual_risk=min(target,top)-me.bet
                        ev+=prob*(q*(pot+actual_risk+called)-actual_risk-push_risk*(pot+actual_risk))
                        if ctx:
                            callers=[i for i in range(len(active)) if mask&(1<<i)]
                            bw=stacks[:]
                            for i in callers:bw[index[active[i].seat]]-=amounts[i]
                            bw[hi]+=pot+called
                            uw=utility(bw)
                            bl=stacks[:];bl[hi]-=actual_risk
                            for i in callers:bl[index[active[i].seat]]-=amounts[i]
                            ul=0.0
                            for i in callers:
                                lose=bl[:];lose[index[active[i].seat]]+=pot+actual_risk+called
                                ul+=utility(lose)/len(callers)
                            point_ev+=prob*(q*uw+(1-q)*ul)
                baseline_check=_joint_pre(key,[widths[s.seat] for s in committed])*pot*.90 if free else 0.0
                profitable=(point_ev>u_folded+max(.0001,.01*(u_stolen-u_folded))) if ctx else ev>max(bb*.05,pot*.035,baseline_check)
                if profitable and (pct<max(open_width,.55) or ev>pot*.45):return raise_to(target)
                return Action.check() if free else default
            if pct<open_width:
                size=(2.25+.8*limpers)*bb
                if limpers and any(profiles[s.seat][0] for s in opps):size=3.5*bb
                return raise_to(size)
            # Cheap completion with suited hands / pairs, particularly multiway.
            if free:return Action.check()
            if cost<=bb*.55 and pct<.60 and len(behind)<=1:return Action.call()
            return default
        if not committed:committed=opps
        eq=_joint_pre(key,[widths[s.seat] for s in committed])
        if len(committed)>1 and any(s.status=='all_in' for s in committed):
            layers=_pot_layers(contrib,me.seat,cost,committed)
            total=sum(a for a,_ in layers)
            if total:eq=sum(a*_joint_pre(key,[widths[i] for i in seats]) for a,seats in layers)/total
        odds=cost/(pot+cost)
        allin=cost>=me.stack or eff-me.bet<=cost
        # Account for the possibility of a player behind entering the pot.
        unacted=[s for s in behind if s not in committed]
        if unacted:eq*=max(.76,1-.035*len(unacted))
        suited=len(key)==3 and key[-1]=='s'
        pair=len(key)==2
        realization=1.0 if allin else (.92 if position else .82)+(.04 if suited else 0)
        if pair:realization=max(realization,.89)
        if eff<18*bb:realization=max(realization,.96)
        value_cut=.60 if len(committed)==1 else .48 if len(committed)==2 else .40
        maniac=any(profiles[s.seat][0] for s in committed)
        if maniac:value_cut-=.015
        if rl and eq>value_cut+risk and (pct<.12 or (maniac and pct<.46)):
            high=max(s.bet for s in opps)
            if eff<24*bb or (maniac and eq>.63) or high>eff*.26:
                return raise_to(eff)
            size=max(high*(3.0 if position else 3.6),me.bet+cost+(pot+cost)*.85)
            return raise_to(min(size,eff))
        if free:return Action.check()
        if 'call' not in legal:return default
        margin=.012 if allin else .025
        if eq*realization>=odds+risk+margin:return Action.call()
        # Set mining is a separate implied-odds investment, not a raw-equity call.
        if pair and cost<=min(me.stack,eff-me.bet)*.045 and cost<=4*bb and len(committed)<=2:return Action.call()
        return default
