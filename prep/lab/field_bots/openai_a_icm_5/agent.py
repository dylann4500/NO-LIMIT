"""Tournament hold'em: range equity, opponent adaptation, and prize-equity risk."""
import itertools
import json
import math
from pathlib import Path
import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

_DATA=json.loads(Path(__file__).with_name('preflop.json').read_text())
_ORDER=_DATA['order']; _WIDTHS=_DATA['widths']; _EQ=_DATA['equity']
_R='23456789TJQKA'
_CARDS={r+s:eval7.Card(r+s) for r in _R for s in 'shdc'}
_RANK={c:_R.index(c[0])+2 for c in _CARDS}
_SUIT={c:c[1] for c in _CARDS}
def handkey(a,b):
    if _RANK[a]<_RANK[b]: a,b=b,a
    return a[0]+b[0]+('' if a[0]==b[0] else 's' if a[1]==b[1] else 'o')
_COMBOS={k:[] for k in _ORDER}
for a,b in itertools.combinations(_CARDS,2):
    _COMBOS[handkey(a,b)].append((a,b))
_PERCENT={}; _ALL=[]
for k in _ORDER:
    _PERCENT[k]=(len(_ALL)+len(_COMBOS[k])*.5)/1326
    _ALL.extend(_COMBOS[k])
# Fixed stratified range samples: balanced at import, no table information in globals.
_POOLS=[]
# Four-to-a-straight detection is a 13-bit lookup, never a Python loop per hand.
_DRAW=[False]*8192
for _mask in range(8192):
    _bits=(_mask<<1) | (1 if _mask & (1<<12) else 0)
    _DRAW[_mask]=any((_bits & (31<<lo)).bit_count()>=4 for lo in range(10))
for w in _WIDTHS:
    end=max(6,int(w*1326))
    pool=_ALL[:end]
    # Coprime permutation spreads suits and hand classes through every sample.
    perm=sorted(pool,key=lambda h:((_RANK[h[0]]*53+ord(h[0][1])*29+_RANK[h[1]]*97+ord(h[1][1])*17)%997,h))
    n=min(112,len(perm))
    _sample=[perm[min(len(perm)-1,int((i+.5)*len(perm)/n))] for i in range(n)]
    _POOLS.append([(a,b,(_CARDS[a],_CARDS[b]),_RANK[a],_RANK[b],(1<<(_RANK[a]-2))|(1<<(_RANK[b]-2))) for a,b in _sample])

def width_index(w):
    return min(range(10),key=lambda i:abs(_WIDTHS[i]-w))

def pre_equity(k,w):
    if w<=_WIDTHS[0]: return _EQ[k][0]
    for i in range(1,10):
        if w<=_WIDTHS[i]:
            f=(w-_WIDTHS[i-1])/(_WIDTHS[i]-_WIDTHS[i-1])
            return _EQ[k][i-1]*(1-f)+_EQ[k][i]*f
    return _EQ[k][-1]

def icm(stacks,hero,payout):
    """Exact hero ICM for arbitrary payouts; fast path for three paid places."""
    n=len(stacks); total=sum(stacks); h=stacks[hero]
    pay=list(payout[:n])+[0]*max(0,n-len(payout))
    floor=pay[n-1]
    if h<=0: return floor
    if total<=0: return floor
    if n==1: return pay[0]
    if n<=3 or all(x==0 for x in pay[3:]):
        p1=h/total; p2=0.; p3=0.
        for j,s in enumerate(stacks):
            if j==hero or s<=0: continue
            d=total-s
            if d<=0: continue
            q=s/total
            p2+=q*h/d
            if n>2 and pay[2]!=0:
                for k,t in enumerate(stacks):
                    if k!=hero and k!=j and t>0 and d>t:
                        p3+=q*t/d*h/(d-t)
        return pay[0]*p1+pay[1]*p2+(pay[2]*p3 if n>2 else 0)
    # Subset dynamic programming bounds work even if every place is paid.
    others=[s for i,s in enumerate(stacks) if i!=hero]
    size=1<<len(others); sums=[0.]*size; values=[0.]*size
    values[0]=pay[n-1]
    for mask in range(1,size):
        bit=mask & -mask; j=bit.bit_length()-1
        sums[mask]=sums[mask^bit]+others[j]
        t=h+sums[mask]; rank=n-1-mask.bit_count()
        v=h*pay[rank]; left=mask
        while left:
            bit=left & -left; j=bit.bit_length()-1
            v+=others[j]*values[mask^bit]; left^=bit
        values[mask]=v/t
    return values[-1]


def observe(state,memory):
    try: m=json.loads(memory) if memory else {}
    except (ValueError,TypeError): m={}
    stats=m.setdefault('s',{})
    for s in state.seats:
        q=stats.setdefault(str(s.seat),[0]*12)
        if len(q)<12: q.extend([0]*(12-len(q)))
    for ev in state.events:
        kind=ev.kind
        if kind=='hand':
            m['h']=ev.amount; m['street']=0; m['v']=[]; m['p']=[]; m['r']=[0]*4
            m['last']=[None]*4; m['own']=[0]*4; m['hp']={}; m['hc']={}; m['c']={}; m['b']={}
            for s in state.seats:
                if s.status!='busted': stats[str(s.seat)][0]+=1
        elif kind=='board':
            m['street']=min(3,m.get('street',0)+1); m['b']={}
        elif ev.seat is not None and kind in ('blind','ante'):
            sid=str(ev.seat); amount=int(ev.amount or 0)
            m.setdefault('c',{})[sid]=m.get('c',{}).get(sid,0)+amount
            if kind=='blind': m.setdefault('b',{})[sid]=m.get('b',{}).get(sid,0)+amount
        elif ev.seat is not None and kind in ('raise','call','check','fold'):
            sid=str(ev.seat); q=stats.setdefault(sid,[0]*12); st=m.get('street',0)
            if kind in ('raise','call'):
                previous=m.setdefault('b',{}).get(sid,0)
                amount=max(0,int(ev.amount or 0)-previous) if kind=='raise' else int(ev.amount or 0)
                m['b'][sid]=previous+amount
                m.setdefault('c',{})[sid]=m.get('c',{}).get(sid,0)+amount
            if st>0:
                previous=m.get('last',[None]*4)[st]
                if kind=='raise': q[7]+=1
                elif kind=='call': q[8]+=1
                elif kind=='check': q[9]+=1
                if previous is not None and previous!=ev.seat and kind in ('call','raise','fold'):
                    q[11]+=1
                    if kind=='fold': q[10]+=1
            if kind=='raise':
                q[3]+=1
                if ev.amount and ev.amount<=state.blinds[1]*2.1: q[6]+=1
                m.setdefault('r',[0]*4)[st]+=1
                m.setdefault('last',[None]*4)[st]=ev.seat
                if st==0:
                    m.setdefault('hp',{})[sid]=m.get('hp',{}).get(sid,0)+1
                    if ev.seat not in m.setdefault('p',[]): q[2]+=1; m['p'].append(ev.seat)
            elif kind=='call':
                q[4]+=1
                if st==0: m.setdefault('hc',{})[sid]=1
            elif kind=='fold': q[5]+=1
            if st==0 and kind in ('raise','call') and ev.seat not in m.setdefault('v',[]):
                q[1]+=1; m['v'].append(ev.seat)
    if m.get('h')!=state.hand_number:
        m.update(h=state.hand_number,street=max(0,len(state.board)-2),v=[],p=[],r=[0]*4,last=[None]*4,own=[0]*4,hp={},hc={},c={},b={})
    return m


def tendency(m,seat):
    q=m['s'].get(str(seat),[0]*7)
    hands=q[0]
    vp=(q[1]+2.8)/(hands+10)
    pf=(q[2]+1.8)/(hands+10)
    wild=hands>=3 and pf>.49
    passive=(q[5]+2)/(q[3]+q[4]+q[5]+5)
    return vp,pf,wild,passive


def opponent_width(m,seat,street,raised,depth):
    vp,pf,wild,fold=tendency(m,seat)
    if wild: return min(1.,max(.55,pf*1.1))
    nr=m.get('hp',{}).get(str(seat),0)
    if nr:
        w=max(.10,min(.55,pf*1.1))
        if nr>1: w*=.38**(nr-1)
    elif m.get('hc',{}).get(str(seat)):
        w=max(.17,min(.85,vp*1.3))
    else: w=max(.25,min(1.,vp*1.7))
    if street==0 and raised and depth>8:
        w=min(w,.15 if depth<20 else .055)
    return max(.025,w)


def call_threshold(state,seats,hero,villain,cost,pot,payout):
    """Prize-EV break-even equity; folded chips stay in the pot."""
    ss=[float(s.stack) for s in seats]; vi=seats.index(villain)
    fullpot=max(pot,state.pot)
    ss[vi]+=fullpot; base=icm(ss,hero,payout)
    win=[float(s.stack) for s in seats]; win[hero]+=pot; win[vi]+=fullpot-pot
    lose=[float(s.stack) for s in seats]; lose[hero]-=cost; lose[vi]+=fullpot+cost
    uw=icm(win,hero,payout); ul=icm(lose,hero,payout)
    return max(cost/(pot+cost),min(.96,(base-ul)/max(1e-10,uw-ul)))


def post_equity(cards,board,width,pressure,wild,nopp,iterations=224,barrels=0):
    hero=[_CARDS[c] for c in cards]; bc=[_CARDS[c] for c in board]
    dead=set(cards+board); pool=_POOLS[width_index(width)]
    top=max(_RANK[c] for c in board); br=[_RANK[c] for c in board]
    bs=[c[1] for c in board]
    suitcounts={s:bs.count(s) for s in 'shdc'}
    bmask=0
    for r in br: bmask |= 1<<(r-2)
    boardcat=(eval7.evaluate(bc)>>24) if len(board)==5 else 0
    hands=[]
    for a,b,hole,ar,bb,hmask in pool:
        if a in dead or b in dead: continue
        n=1
        if pressure:
            cat=eval7.evaluate(list(hole)+bc)>>24
            pair=(ar==bb or ar in br or bb in br)
            tp=(ar==bb and ar>=top) or (ar in br and ar>=top) or (bb in br and bb>=top)
            # Do not count a paired/flush/straight board as a made hole-card hand.
            strong=cat>=2 and (len(board)<5 or cat>boardcat)
            draw=False
            if len(board)<5:
                draw=(suitcounts[a[1]]+1+(a[1]==b[1])>=4 or suitcounts[b[1]]+1>=4 or _DRAW[bmask|hmask])
            if strong: n=8
            elif tp: n=6 if pressure<.7 else 4
            elif pair: n=3 if len(board)==3 or wild else 1
            elif draw: n=4 if len(board)==3 else 3
            else:
                # Keep a bluff component for unknown opponents, including the river.
                n=2 if wild or barrels==0 else 1
                if len(board)==3 and not wild: n=1
            if pressure>1 and not strong and not tp and not draw and not wild:
                n=1 if (ar*17+bb*31+ord(a[1]))%4==0 else 0
            if strong and barrels>=2: n=12
        if n: hands.extend([(hole,1)]*n)
    if not hands: return .45
    if len(board)==5:
        eq=float(eval7.py_hand_vs_range_exact(hero,hands,bc))
    else:
        eq=float(eval7.py_hand_vs_range_monte_carlo(hero,hands,bc,iterations))
    return max(0.,min(1.,eq))**(max(1,nopp)**.84)


class Agent(poker_agent_sdk.Agent):
    def act(self,state,memory):
        m=observe(state,memory)
        legal={getattr(a.kind,'value',a.kind):a for a in state.legal_actions}
        hero=next(s for s in state.seats if s.seat==state.seat)
        live=[s for s in state.seats if s.status!='busted' and (s.stack>0 or s.status=='all_in' or s.seat==state.seat)]
        hi=live.index(hero)
        ids=sorted(s.seat for s in live)
        bpos=ids.index(state.button) if state.button in ids else 0
        clockwise=ids[bpos+1:]+ids[:bpos+1]
        opp=[s for s in live if s.seat!=state.seat and s.status in ('active','all_in')]
        if not opp: return (Action.check() if 'check' in legal else Action.call() if 'call' in legal else Action.fold()),json.dumps(m,separators=(',',':')).encode()
        bb=max(1,state.blinds[1]); stack=hero.stack; pot=max(1,state.pot)
        call=min(stack,max(0,state.to_call)); depth=(stack+hero.bet)/bb
        contributed=m.get('c',{})
        # Excess contributions in other side pots cannot improve our calling odds.
        if abs(sum(contributed.values())-state.pot)<=max(1,bb//10):
            cap=contributed.get(str(state.seat),hero.bet)+stack
            pot=max(1,min(pot,sum(min(v,cap) for v in contributed.values())))
        street=max(0,len(state.board)-2)
        payout=list(state.config.payouts or [50,30,20])
        paid=sum(p>0 for p in payout)
        prize_scale=max(1e-9,sum(payout)/100)
        villain=max(opp,key=lambda s:(s.bet,s.status=='all_in',s.stack))
        vp,pf,wild,foldrate=tendency(m,villain.seat)
        raised=street==0 and max(s.bet for s in opp)>bb
        if street>0:
            q=m['s'].get(str(villain.seat),[0]*12)
            wild=wild or (q[7]>=8 and q[7]/(q[7]+q[8]+q[9]+3)>.54)
        width=opponent_width(m,villain.seat,street,raised,max(s.bet for s in opp)/bb)
        inposition=clockwise.index(state.seat)>max(clockwise.index(s.seat) for s in opp)
        lowbank=getattr(state,'time_bank_ms',100)<25
        passive=Action.check() if 'check' in legal else Action.fold()
        action=passive
        def raise_to(amount):
            if 'raise' not in legal: return Action.call() if 'call' in legal else passive
            r=legal['raise']; return Action.raise_to(max(int(r.min_amount),min(int(r.max_amount),int(amount))))
        def threshold():
            req=call/(pot+call)
            if call>=max(3*bb,stack*.16) and len(live)>2:
                req=call_threshold(state,live,hi,villain,call,pot,payout)
            return req
        if street==0:
            key=handkey(*state.cards); percentile=_PERCENT[key]
            # Clockwise order through the blinds, independent of anonymized seat ids.
            order=(clockwise[2:]+clockwise[:2]) if len(ids)>2 else clockwise[::-1]
            behind=[s for sid in order[order.index(state.seat)+1:] for s in opp if s.seat==sid and s.stack>0]
            nb=len(behind)
            limpers=sum(1 for s in opp if s.bet==bb and m.get('hc',{}).get(str(s.seat)))
            if raised and (villain.status=='all_in' or villain.bet>=(villain.stack+villain.bet)*.75) and villain.bet/bb<=18 and not wild:
                vb=len(order)-1-order.index(villain.seat)
                pushdepth=max(2,villain.bet/bb)
                if m.get('own',[0]*4)[0] or m.get('r',[0]*4)[0]>1:
                    width=max(.065,min(.25,.13*(10/pushdepth)**.4))
                else:
                    width=min(.9,[.7,.55,.38,.28,.23,.19,.16,.14][min(vb,7)]*(10/pushdepth)**.45)
            unopened=not raised
            if unopened:
                # Push/fold below 12BB. Solve prize EV against plausible calling ranges.
                callers=behind+[s for s in opp if s not in behind and s.stack>0 and m.get('hc',{}).get(str(s.seat))]
                if depth<=12 and 'raise' in legal and callers:
                    probs=[]; widths=[]
                    for s in callers:
                        v,p,w,f=tendency(m,s.seat)
                        cw=[.4,.32,.21,.16,.125,.105,.09,.08][min(nb,7)]*(10/max(2,depth))**.48
                        if len(live)==2: cw*=1.12
                        cw=max(.07,min(.75,cw))
                        if w: cw=max(.45,v)
                        elif f>.70: cw*=.40
                        elif f>.62: cw*=.75
                        if len(live)==paid+1 and s.stack>stack and min(t.stack for t in live if t.stack>0)<stack*.38: cw*=.7
                        widths.append(cw); probs.append(cw)
                    fe=math.prod(1-p for p in probs)
                    target=max(callers,key=lambda s:s.stack)
                    vi=live.index(target)
                    cw=sum(widths)/len(widths)
                    eq=pre_equity(key,cw)*(1-.09*max(0,sum(probs)-.5))
                    cost=min(stack,max(0,target.stack+target.bet-hero.bet))
                    vc=min(target.stack,max(0,hero.bet+cost-target.bet))
                    base=[float(s.stack) for s in live]; base[vi]+=pot
                    ub=icm(base,hi,payout)
                    steal=[float(s.stack) for s in live]; steal[hi]+=pot
                    win=[float(s.stack) for s in live]; win[hi]+=pot+vc; win[vi]-=vc
                    lose=[float(s.stack) for s in live]; lose[hi]-=cost; lose[vi]+=pot+cost
                    ev=fe*(icm(steal,hi,payout)-ub)+(1-fe)*(eq*icm(win,hi,payout)+(1-eq)*icm(lose,hi,payout)-ub)
                    if ev>0.008*prize_scale: action=raise_to(stack+hero.bet)
                else:
                    opens=[.65,.48,.40,.30,.25,.22,.19,.17]
                    ow=opens[min(nb,7)]
                    if len(live)==2 and state.seat==state.button: ow=.73
                    if behind and all(tendency(m,s.seat)[3]>.70 and m['s'][str(s.seat)][0]>=5 for s in behind): ow=min(.94,ow*1.7)
                    if nb==1 and state.seat!=state.button: ow=.54
                    if limpers: ow*=.70
                    if len(live)==paid+1:
                        smallest=min(s.stack for s in live if s.stack>0)
                        if smallest<stack*.35 and any(s.stack>stack*1.1 for s in behind): ow*=.68
                        elif all(s.stack<stack*.75 for s in behind): ow*=1.17
                    if percentile<ow and 'raise' in legal:
                        size=bb*(2.15+limpers*.9)
                        if any(tendency(m,s.seat)[2] for s in opp): size=bb*(2.7+limpers)
                        if size-hero.bet>stack*.40 or (depth<18 and limpers and percentile<.11): size=stack+hero.bet
                        action=raise_to(size)
                    elif 'check' in legal: action=Action.check()
                    elif limpers and call<=bb and percentile<.28 and depth>18 and (len(key)==2 or key[-1]=='s'):
                        action=Action.call()
            else:
                eq=pre_equity(key,width)
                contenders=sum(1 for s in opp if s.bet>bb or s.status=='all_in')
                if contenders>1: eq=eq**(contenders**.7)
                req=threshold()
                committed=call>=stack*.65 or villain.status=='all_in' or depth<=13
                # Value 3-bets; premiums do not repeatedly min-raise into a war.
                nr=m.get('r',[0]*4)[0]
                ourraises=m.get('own',[0]*4)[0]
                value=(eq>.65 and percentile<.045) or (key in ('AKs','AKo') and eq>.61) or (wild and eq>.63 and percentile<.13)
                if 'raise' in legal and value and (not committed or eq>req+.07):
                    if depth<24 or max(s.bet for s in opp)>stack*.22 or ourraises:
                        action=raise_to(stack+hero.bet)
                    elif nr<=1 or wild:
                        action=raise_to(max(s.bet for s in opp)*(3.0 if nb==0 else 3.5)+limpers*bb)
                    elif eq>req+.035: action=Action.call()
                elif committed:
                    if eq>req+.018: action=Action.call()
                else:
                    # Realization discount: weak offsuit hands cannot profitably defend on raw equity alone.
                    realization=.92 if inposition else .77
                    if key[-1:]=='s' or len(key)==2: realization+=.05
                    if key[-1:]=='o' and key[0]=='A' and _R.index(key[1])<8: realization-=.07
                    req=max(req,.28 if max(s.bet for s in opp)>bb*2.6 else .23)
                    if eq*realization>req+.035 and percentile<min(.55,width*1.7+.10):
                        action=Action.call()
                    elif len(key)==2 and call<stack*.055 and call/(pot+call)<.24 and nr<=1:
                        action=Action.call()
        else:
            nopp=len(opp)
            pressure=call/max(1,pot-call) if call else 0.
            barrels=sum(m.get('last',[None]*4)[i]==villain.seat for i in range(1,street))
            eq=post_equity(state.cards,state.board,width,0 if lowbank else pressure,wild,nopp,128 if lowbank else 224,barrels)
            if lowbank and call: eq=max(0.,eq-.10)
            req=threshold() if call else 0.
            actionable=[s for s in opp if s.stack>0 and s.status=='active']
            own=m.get('own',[0]*4)[street]
            if call:
                margin=.025 if street==1 else .013 if street==2 else .008
                if eq>req+margin:
                    action=Action.call() if 'call' in legal else passive
                    if 'raise' in legal and actionable and eq>(.81 if nopp==1 else .88) and (own==0 or eq>.94):
                        size=hero.bet+call+(pot+call)*(.72 if street<3 else .86)
                        if size-hero.bet>stack*.58: size=stack+hero.bet
                        action=raise_to(size)
            elif actionable and 'raise' in legal:
                # Bet enough to get called by worse, while retaining an inexpensive c-bet.
                value=eq>((.61 if street==1 else .64 if street==2 else .66) if nopp==1 else .70)
                if len(live)==paid+1 and stack>0 and min(s.stack for s in live if s.stack>0)<stack*.3 and any(s.stack>stack for s in actionable):
                    value=value and (eq>.75 or pot<stack*.20)
                seed=(state.hand_number*37+sum(ord(c[0])*7+ord(c[1]) for c in state.cards)+street*17)%100/100
                preraise=state.seat in m.get('p',[])
                position=inposition
                fe=sum((m['s'][str(s.seat)][10]+2.5)/(m['s'][str(s.seat)][11]+5) for s in actionable)/len(actionable)
                bluff=nopp==1 and not wild and ((street==1 and preraise and eq>(.20 if fe>.65 else .30) and fe>.28 and seed<(.78 if fe>.65 else .52)) or (street==3 and eq<.28 and position and fe>.55 and seed<.26))
                if value or bluff:
                    fraction=(.38 if bluff else .50 if street==1 else .65 if street==2 else .72)
                    if eq>.87: fraction=.82
                    size=hero.bet+max(bb,pot*fraction)
                    if size-hero.bet>stack*.62 and value: size=stack+hero.bet
                    action=raise_to(size)
        # One legality gate covers short all-in raises and every passive branch.
        ak=getattr(action.kind,'value',action.kind)
        if ak not in legal: action=Action.check() if 'check' in legal else Action.fold() if 'fold' in legal else Action.call()
        if getattr(action.kind,'value',action.kind)=='raise':
            r=legal['raise']; action=Action.raise_to(max(int(r.min_amount),min(int(r.max_amount),int(action.amount))))
            m.setdefault('own',[0]*4)[street]+=1
        return action,json.dumps(m,separators=(',',':')).encode()
