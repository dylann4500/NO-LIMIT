"""Tournament hold'em: range equity, position, opponent adaptation and ICM.
All mutable information is serialized in the per-table memory. Import-time
objects below are immutable card/range/equity assets, shared by all tables.
"""
import json
import gc
import marshal
import math
import os
import time
import eval7
from poker_agent_sdk import Agent as BaseAgent, Action

RANKS = '23456789TJQKA'
SUITS = 'cdhs'
with open(os.path.join(os.path.dirname(__file__), 'preflop.json')) as _f:
    _DATA = json.load(_f)
HANDS = _DATA['hands']
FRACTIONS = _DATA['fractions']
CARDS = tuple(eval7.Card(r+s) for r in RANKS for s in SUITS)
IDS = {r+s: i*4+j for i,r in enumerate(RANKS) for j,s in enumerate(SUITS)}
WINDOWS = tuple(31 << i for i in range(9)) + (0x100F,)
NEAR = bytes(max((m & w).bit_count() for w in WINDOWS) for m in range(8192))
STRAIGHT_OUTS=bytes(sum(NEAR[m|(1<<r)]==5 for r in range(13) if not m&(1<<r)) if NEAR[m]<5 else 0 for m in range(8192))

def hand_key(a, b):
    x,y = a//4,b//4
    if x<y: x,y=y,x
    return RANKS[x]*2 if x==y else RANKS[x]+RANKS[y]+('s' if a%4==b%4 else 'o')

# Range samples preserve the frequency of pairs, suited and offsuit hands.
# Dense narrow ranges are exact; wide ranges use stratified, deterministic samples.
_ALL = []
for _a in range(52):
    for _b in range(_a+1,52):
        _key = hand_key(_a,_b)
        _ALL.append((_a,_b,(CARDS[_a],CARDS[_b]),(1<<(_a//4))|(1<<(_b//4)),HANDS[_key]['p']))
_ALL.sort(key=lambda x: (x[4], ((x[0]*113+x[1]*71)%167)))
RANGES = []
for _frac in FRACTIONS:
    _n = max(6,int(1326*_frac))
    _r = _ALL[:_n]
    if len(_r)>128:
        _r = [_r[int((i+.5)*len(_r)/128)] for i in range(128)]
    RANGES.append(tuple(_r))
RANGES = tuple(RANGES)
del _ALL, _DATA

# Stats: hands, voluntary preflop, preflop raise, faced preflop raise,
# preflop fold, postflop aggression, postflop passive action, faced post bet,
# post fold, showdowns, weak showdown, last stack.
def fresh_stats(stack):
    return [0,0,0,0,0,0,0,0,0,0,0,stack]

def kind(v):
    return getattr(v, 'value', v)

def index_range(f):
    return min(range(len(FRACTIONS)), key=lambda i: abs(FRACTIONS[i]-f))

def pre_equity(h, f):
    es = h['eq']
    for i,x in enumerate(FRACTIONS):
        if f<=x:
            if i==0: return es[0]
            t=(f-FRACTIONS[i-1])/(x-FRACTIONS[i-1])
            return es[i-1]*(1-t)+es[i]*t
    return es[-1]

def orbit(state):
    live = sorted(s.seat for s in state.seats if s.status!='busted' and (s.stack+s.bet>0 or s.status=='all_in'))
    after=[s for s in live if s>state.button]+[s for s in live if s<=state.button]
    if len(live)==2:
        return [state.button, next(s for s in live if s!=state.button)] if state.button in live else after
    return after[2:]+after[:2]

def position_fraction(seat, order):
    try: behind=len(order)-order.index(seat)-1
    except ValueError: behind=4
    return (1.,.54,.46,.31,.24,.20,.17,.15)[min(7,max(0,behind))]

def is_maniac(st):
    return st[0]>=4 and (st[2]/max(1,st[0])>.62 or (st[1]/st[0]>.80 and st[5]>=4 and st[5]/max(1,st[5]+st[6])>.62))

def is_nit(st):
    return (st[0]>=6 and st[1]==0) or (st[3]>=4 and st[4]/st[3]>.90 and st[1]/max(1,st[0])<.13)

def fold_rate(st):
    if is_nit(st): return .96
    if is_maniac(st): return .03
    return (st[8]+2.2)/(st[7]+4.5)

def read_memory(state, memory):
    try:
        m=marshal.loads(memory) if memory else None
        if not isinstance(m,dict) or m.get('v')!=4: m=None
    except Exception:
        m=None
    if m is None:
        m={'v':4,'h':-1,'street':0,'pot':0,'mx':0,'nr':0,'p':{},'c':{},'bd':[],'t':0}
    stats=m['p']; bb=max(1,int(state.blinds[1]))
    for s in state.seats:
        k=str(s.seat)
        if k not in stats: stats[k]=fresh_stats(state.config.starting_stack or 2000)
    for ev in state.events:
        knd=kind(ev.kind)
        if knd=='hand':
            m['h']=ev.amount; m['street']=0; m['pot']=0; m['mx']=0; m['nr']=0; m['bd']=[]
            m['c']={k:{'bet':0,'total':0,'vp':0,'pr':0,'role':0,'size':0,'op':0,'vs':0,'callsize':0,'pa':[],'all':0} for k in stats}
            for st in stats.values():
                if st[11]>0: st[0]+=1
            continue
        if knd=='board':
            m['bd'].extend(ev.cards or [])
            m['street']=len(m['bd'])-2
            m['mx']=0
            for c in m['c'].values(): c['bet']=0
            continue
        if ev.seat is None: continue
        k=str(ev.seat)
        if k not in stats: stats[k]=fresh_stats(2000)
        st=stats[k]
        amt=ev.amount or 0
        if knd=='stack': st[11]=amt; continue
        if knd=='show':
            if ev.cards and len(ev.cards)==2:
                st[9]+=1
                try:
                    hk=hand_key(IDS[ev.cards[0]],IDS[ev.cards[1]])
                    if HANDS[hk]['p']>.5: st[10]+=1
                except (KeyError,TypeError): pass
            continue
        c=m['c'].get(k)
        if c is None:
            c={'bet':0,'total':0,'vp':0,'pr':0,'role':0,'size':0,'op':0,'vs':0,'callsize':0,'pa':[],'all':0}
            m['c'][k]=c
        if knd in ('blind','ante'):
            m['pot']+=amt
            c['total']=c.get('total',0)+amt
            if knd=='blind':
                c['bet']+=amt; m['mx']=max(m['mx'],c['bet'])
            continue
        if knd not in ('fold','check','call','raise'): continue
        street=m['street']
        facing=m['mx']>c['bet']
        added=max(0,amt-c['bet']) if knd=='raise' else amt if knd=='call' else 0
        ratio=added/max(bb,m['pot'])
        if street==0:
            if facing and m['mx']>bb and not c['op']:
                c['op']=1;st[3]+=1
                if knd=='fold':st[4]+=1
            if knd in ('call','raise') and not c['vp']:
                c['vp']=1; st[1]+=1
            if knd=='raise':
                if not c['pr']: st[2]+=1
                c['pr']+=1
                c['role']=2 if m['nr'] else 1
                c['size']=amt/bb
                m['nr']+=1
            elif knd=='call':
                c['vs']=m['nr'];c['callsize']=amt/bb
                if not c['role']:c['role']=3 if m['nr'] else 4
        else:
            if knd=='raise':st[5]+=1
            elif knd in ('check','call'):st[6]+=1
            if facing:
                st[7]+=1
                if knd=='fold':st[8]+=1
            c['pa'].append((street,knd,min(8.,ratio),knd=='raise' and m['mx']>0))
            # Memory stays bounded even in pathological min-raise wars.
            if len(c['pa'])>12:c['pa']=c['pa'][-12:]
        if knd=='raise':c['bet']=amt;m['mx']=max(m['mx'],amt)
        elif knd=='call':c['bet']+=amt
        m['pot']+=added
        c['total']=c.get('total',0)+added
    # The first turn can be supplied with an empty event list by an SDK adapter.
    if m['h']!=state.hand_number:
        m['h']=state.hand_number;m['street']=max(0,len(state.board)-2)
        m['c']={str(s.seat):{'bet':s.bet,'total':s.bet,'vp':0,'pr':0,'role':0,'size':0,'op':0,'vs':0,'callsize':0,'pa':[],'all':0} for s in state.seats}
        m['bd']=list(state.board);m['pot']=state.pot;m['nr']=0
    m['t']+=1
    return m

def villain_fraction(st,c,seat,order,depth):
    base=position_fraction(seat,order)
    if base==1.:base=.32
    n=st[0]
    maniac=is_maniac(st)
    observed=(st[2]+2.5)/(n+13)
    f=base*(1-min(.65,n/(n+15)))+observed*min(.65,n/(n+15))
    if maniac:f=max(.78,st[2]/n)
    role=c['role']
    if role==2:
        f=max(.025,f*.26)
        if c['pr']>=2:f*=.65
        if maniac:f=.78
    elif role==3:
        f=max(.12,min(.50,(st[1]+5)/(n+15)*1.25))
        if maniac:f=.95
    elif role==4:
        f=max(.25,min(.85,(st[1]+7)/(n+12)))
    elif role==0:
        f=1.
    if c.get('vs',0)>=2 and c.get('callsize',0)>=2 and not maniac:
        f*=.55
        if c['vs']>=3 and c['callsize']>=4:f*=.55
    if c['size']>6 and not maniac and role in (1,2):
        if depth>18:f*=.65
        elif depth<12 and role==1:f=max(f,.18)
    return max(.025,min(1.,f))

def board_texture(ids):
    br=[x//4 for x in ids]
    bc=[0]*13;sc=[0]*4;bmask=0
    for x in ids:
        bc[x//4]+=1;sc[x%4]+=1;bmask|=1<<(x//4)
    sr=sorted(br)
    return bc,sc,bmask,sr[-1],sr[-2],sum(x>=2 for x in bc),len(ids)<5

def made_info(a,b,rank,tex):
    bc,sc,bmask,top,second,bpairs,drawstreet=tex
    cat=rank>>24;r=(rank>>16)&15
    if cat==0:val=0.
    elif cat==1:
        if bc[r]>=2:val=.12
        else:val=1.15 if r>top else 1. if r==top else .58 if r>=second else .36
    elif cat==2:
        if not bpairs:val=2.0
        else:
            r2=(rank>>12)&15
            ownpair=r if bc[r]<2 else r2 if bc[r2]<2 else -1
            # Two pair made by matching a paired board is still a one-pair
            # value hand. Distinguish top pair from a weak bottom pair.
            if ownpair<0:val=.25
            else:
                unpaired=[i for i,n in enumerate(bc) if n==1]
                utop=unpaired[-1] if unpaired else -1
                usecond=unpaired[-2] if len(unpaired)>1 else -1
                val=1.12 if ownpair>=utop else .58 if ownpair>=usecond else .36
    elif cat==3:val=.45 if bc[r]>=3 else 2.7
    else:val=cat+.2
    sa,sb=a%4,b%4
    fd=drawstreet and ((sc[sa]+(2 if sa==sb else 1)==4) or (sa!=sb and sc[sb]+1==4))
    sd=STRAIGHT_OUTS[bmask|(1<<(a//4))|(1<<(b//4))] if drawstreet and NEAR[bmask]<4 and cat<4 else 0
    return val,fd,sd

def posterior_range(a,b,boardids,tex,st,c,f,street,filter_actions=True,deadline=0,limit=128):
    candidates=RANGES[index_range(f)]
    if len(candidates)>limit:candidates=candidates[::2]
    dead=(1<<a)|(1<<b)
    for x in boardids:dead|=1<<x
    board=tuple(CARDS[x] for x in boardids)
    pa=[x for x in c['pa'] if x[1] in ('call','raise')]
    if not pa or is_maniac(st) or not filter_actions:
        return [(h,1.) for x,y,h,mask,p in candidates if not ((1<<x|1<<y)&dead)]
    last=pa[-1];action=last[1];size=last[2]
    agg=(st[5]+2)/(st[5]+st[6]+6)
    aggs=sum(x[1]=='raise' for x in pa)
    out=[]
    for ri,(x,y,h,mask,p) in enumerate(candidates):
        if deadline and ri%32==0 and time.process_time_ns()>deadline:
            break
        if ((1<<x|1<<y)&dead):continue
        rank=eval7.evaluate(board+h)
        val,fd,sd=made_info(x,y,rank,tex)
        draw=fd or sd
        if action=='raise':
            if val>=2.5:w=1.
            elif val>=1.0:w=.90 if size<.9 else .70
            elif val>=.35:w=.57 if size<.65 else .26
            elif draw:w=.62 if last[0]<3 else .12
            else:w=(.28 if last[0]==1 else .14 if last[0]==2 else .09)*(.65+agg)
            if len(last)>3 and last[3]:
                # Raising an existing bet represents a substantially stronger
                # range than making the first bet on a street.
                if val>=2.7:w=1.
                elif val>=2.:w=.88
                elif draw:w=.70 if last[0]<3 else .06
                elif val>=1.:w=.38 if last[0]==1 else .23 if last[0]==2 else .15
                elif val>=.35:w=.16 if last[0]==1 else .08
                else:w=.11 if last[0]==1 else .075
            if aggs>=2 and val<1.:w*=.60 if draw else .50
            if last[0]==3 and size>.8 and val<2.:w*=.6 if val>=.35 else 1.3
        else:
            if val>=1.:w=.98
            elif val>=.35:w=.76
            elif draw:w=.85
            else:w=.19 if last[0]==1 else .085 if last[0]==2 else .035
        u=((x*109+y*241+street*47)%997)/997.
        if u<w:out.append((h,1.))
    if len(out)<5:
        return [(h,1.) for x,y,h,mask,p in candidates if not ((1<<x|1<<y)&dead)]
    return out

def icm(stacks, hero, payouts):
    total=sum(stacks)
    s=stacks[hero]
    if s<=0 or total<=0:return 0.
    ps=list(payouts)+[0.,0.,0.]
    val=ps[0]*s/total
    if len(stacks)<2:return val
    for j,sj in enumerate(stacks):
        if j==hero or sj<=0:continue
        rem=total-sj
        if rem<=0:continue
        q=sj/total*s/rem
        val+=ps[1]*q
        if len(stacks)>2 and ps[2]:
            for k,sk in enumerate(stacks):
                if k==hero or k==j or sk<=0:continue
                rem2=rem-sk
                if rem2>0:val+=ps[2]*(sj/total)*(sk/rem)*(s/rem2)
    return val

def call_threshold(state, me, villain, cost):
    odds=cost/max(1,state.pot+cost)
    if state.players_remaining<=2 or cost<me.stack*.24:return odds
    payouts=state.config.payouts or [50,30,20]
    # Exact ICM for the standard three-paid event, with the contested pot
    # assigned to the principal opponent. Other payout schedules use a
    # conservative, small risk adjustment rather than the wrong ICM model.
    if any(payouts[3:]):return min(.95,odds+.025*cost/max(1,me.stack))
    seats=[s for s in state.seats if s.stack+s.bet>0 and s.status!='busted']
    hero=next(i for i,s in enumerate(seats) if s.seat==me.seat)
    v=next((i for i,s in enumerate(seats) if s.seat==villain.seat),None)
    if v is None:return odds
    stacks=[s.stack for s in seats]
    fold=stacks[:];fold[v]+=state.pot
    win=stacks[:];win[hero]+=state.pot
    lose=stacks[:];lose[hero]-=cost;lose[v]+=state.pot+cost
    base=icm(fold,hero,payouts);wv=icm(win,hero,payouts);lv=icm(lose,hero,payouts)
    req=(base-lv)/max(1e-9,wv-lv)
    return max(odds,min(.95,req))

class Agent(BaseAgent):
    def act(self,state,memory):
        try:
            return self._act(state,memory)
        except Exception as exc:
            # Last-resort protocol guard; normal play is tested with this counter
            # asserted at zero. An unexpected adapter variation must stay legal.
            try: m=marshal.loads(memory) if memory else {}
            except Exception:m={}
            if not isinstance(m,dict):m={}
            m['guard_errors']=m.get('guard_errors',0)+1
            m['last_error']=type(exc).__name__+': '+str(exc)[:160]
            legal={kind(x.kind):x for x in state.legal_actions}
            if 'check' in legal:act=Action.check()
            elif 'fold' in legal:act=Action.fold()
            elif 'call' in legal:act=Action.call()
            else:act=Action.raise_to(int(legal['raise'].min_amount))
            return act,marshal.dumps(m)

    def _act(self,state,memory):
        # Our memory and temporary ranges are acyclic. Refcounts free them
        # immediately; defer unrelated cyclic heap scans until after returning.
        enabled=gc.isenabled()
        if enabled:gc.disable()
        try:
            return self._decide(state,memory)
        finally:
            if enabled:gc.enable()

    def _decide(self,state,memory):
        decision_ms=max(.05,float(state.config.decision_ms or 1.))
        lowbank=(state.config.time_bank_ms or 0)>0 and state.time_bank_ms<25
        deadline=time.process_time_ns()+int(decision_ms*(450000 if lowbank else 650000))
        # Derive offered kinds from the actual SDK enums, never assumed strings.
        legal={kind(x.kind):x for x in state.legal_actions}
        me=next(s for s in state.seats if s.seat==state.seat)
        m=read_memory(state,memory)
        stats=m['p'];cur=m['c'];k=str(state.seat)
        m['deadline']=deadline
        m['lowbank']=lowbank
        a,b=(IDS[x] for x in state.cards)
        h=HANDS[hand_key(a,b)]
        bb=max(1,int(state.blinds[1]));P=max(1,state.pot)
        cost=min(me.stack,max(0,state.to_call))
        order=orbit(state)
        opps=[s for s in state.seats if s.seat!=me.seat and s.status in ('active','all_in')]
        # A reproducible random variate using only this table's public state/cards.
        seed=(a*15485863+b*32452843+state.hand_number*49979687+m['t']*67867967+P*86028121+me.seat*104395301)&0xffffffff
        seed^=seed>>16;seed=(seed*0x7feb352d)&0xffffffff;seed^=seed>>15
        u=seed/4294967296.
        def finish(what,amount=0):
            if what=='raise' and 'raise' in legal:
                r=legal['raise']; amount=max(int(r.min_amount),min(int(r.max_amount),int(amount)))
                act=Action.raise_to(amount)
            elif what=='call' and 'call' in legal:act=Action.call()
            elif what=='check' and 'check' in legal:act=Action.check()
            elif what=='fold' and 'fold' in legal:act=Action.fold()
            elif 'check' in legal:act=Action.check()
            elif 'fold' in legal:act=Action.fold()
            elif 'call' in legal:act=Action.call()
            else:
                r=legal['raise'];act=Action.raise_to(int(r.min_amount))
            m.pop('deadline',None)
            m.pop('lowbank',None)
            return act,marshal.dumps(m)
        if not opps:return finish('check')
        if time.process_time_ns()>deadline-100000:return finish('check')
        depth=(me.stack+me.bet)/bb
        fs={s.seat:villain_fraction(stats[str(s.seat)],cur[str(s.seat)],s.seat,order,(s.stack+s.bet)/bb) for s in opps}
        if len(state.board)==0:
            return self.preflop(state,m,me,opps,h,fs,order,depth,P,cost,bb,u,legal,finish)
        return self.postflop(state,m,me,opps,a,b,fs,order,depth,P,cost,bb,u,legal,finish)

    def preflop(self,state,m,me,opps,h,fs,order,depth,P,cost,bb,u,legal,finish):
        stats=m['p'];cur=m['c'];my=cur[str(me.seat)]
        maxbet=max(s.bet for s in state.seats)
        raised=maxbet>bb or m['nr']>0
        frac=position_fraction(me.seat,order)
        limps=sum(c['role']==4 for k,c in cur.items() if k!=str(me.seat))
        try:behind=len(order)-order.index(me.seat)-1
        except ValueError:behind=len(opps)
        postorder=order[-2:]+order[:-2] if len(order)>2 else [s for s in order if s!=state.button]+[state.button]
        inpos=all(postorder.index(me.seat)>postorder.index(s.seat) for s in opps if s.status=='active')
        if not raised:
            targets=[s for s in opps if s.status=='active']
            nitshare=sum(is_nit(stats[str(s.seat)]) for s in targets)/max(1,len(targets))
            frac=min(1.,frac+nitshare*.55)
            if me.seat==state.button and len(opps)==1:frac=max(frac,.78)
            if state.players_remaining==4:
                short=min(s.stack+s.bet for s in opps)
                if short<(me.stack+me.bet)*.3:frac*=.8
            openfrac=frac*(.84**min(limps,3))
            if cost==0 and my['role']==0:openfrac=min(.32,openfrac)
            if depth<=11 and 'raise' in legal and nitshare<.75:
                # Chip EV of a push against plausible calling ranges, with a
                # tournament risk premium. Calls from maniacs are modeled wide.
                foldprob=1.;eqsum=0.;callsum=0.;risk=min(me.stack,max(s.stack+s.bet for s in opps))
                for s in targets:
                    st=stats[str(s.seat)]
                    cf=max(.07,min(.42,.08+.85/(depth+2)))
                    if cur[str(s.seat)]['role'] in (3,4):cf=min(.8,cf/max(.25,fs[s.seat]))
                    if is_maniac(st):cf=.90
                    elif is_nit(st):cf=.025
                    foldprob*=1-cf
                    eqsum+=cf*pre_equity(h,cf);callsum+=cf
                eq=eqsum/max(.01,callsum)
                riskprem=.02
                if state.players_remaining==4:
                    short=min(s.stack+s.bet for s in opps)
                    riskprem=.09 if short<(me.stack+me.bet)*.4 else .045
                ev=foldprob*P+(1-foldprob)*(eq*(P+2*risk)-risk-riskprem*2*risk)
                if ev>bb*.08 and (h['p']<max(openfrac,.48) or depth<5 or behind<2):
                    return finish('raise',me.bet+me.stack)
                if cost and depth<7:return finish('fold')
            if h['open']<openfrac and 'raise' in legal:
                size=(2.2 if depth>25 else 2.05)*bb+limps*bb
                if frac==.54:size=2.6*bb+limps*bb
                if any(is_maniac(stats[str(s.seat)]) for s in opps) and h['p']<.065:
                    size=max(size,4.5*bb+limps*bb)
                    if depth<22:return finish('raise',me.bet+me.stack)
                return finish('raise',size)
            if cost==0:return finish('check')
            suited=state.cards[0][-1]==state.cards[1][-1]
            pair=state.cards[0][0]==state.cards[1][0]
            callfrac=.28+(.12 if inpos else 0)+(.08 if limps>1 and suited else 0)
            if frac==.54 and limps and depth>12:callfrac=.65
            if limps and depth>16 and (h['p']<callfrac or pair or (suited and h['p']<.66 and limps>1)):
                return finish('call')
            return finish('fold')
        raisers=[s for s in opps if cur[str(s.seat)]['role'] in (1,2)]
        villain=max(raisers or opps,key=lambda s:s.bet)
        f=fs[villain.seat]
        maniac=is_maniac(stats[str(villain.seat)])
        eq=pre_equity(h,f)
        others=[s for s in opps if s.seat!=villain.seat and s.bet>bb and cur[str(s.seat)]['vp']]
        if others:
            eq*=max(.58,1-.16*len(others))
        req=call_threshold(state,me,villain,cost)
        allin=cost>=me.stack*.80 or villain.status=='all_in' or maxbet>=min(me.stack+me.bet,villain.stack+villain.bet)*.72
        if allin:
            if eq>req+.012:
                if maniac and eq>.61 and 'raise' in legal:return finish('raise',me.stack+me.bet)
                return finish('call')
            return finish('fold')
        ra,rb=(IDS[x]//4+2 for x in state.cards)
        hi,lo=max(ra,rb),min(ra,rb);pair=ra==rb
        premium=(pair and hi>=12) or (hi==14 and lo==13)
        if f>.34:premium=(pair and hi>=9) or (hi==14 and lo>=11) or (hi==13 and lo==12 and state.cards[0][-1]==state.cards[1][-1])
        if m['nr']>=2 and not maniac:premium=eq>.55 and ((pair and hi>=12) or (hi==14 and lo==13))
        if m['nr']>=3 and not maniac:premium=pair and hi>=13 and eq>.48
        if maniac:premium=eq>.585
        if premium and 'raise' in legal:
            target=max(maxbet*(3.35 if not inpos else 2.9),me.bet+cost+.78*(P+cost))
            if maniac or target>=(me.stack+me.bet)*.33:target=me.stack+me.bet
            return finish('raise',target)
        # Reshoves exploit the dead money in a late-position open. Requiring
        # positive modeled EV also prevents committing a middling hand just
        # because its normal three-bet would use most of a short stack.
        if 8<depth<24 and m['nr']==1 and not maniac and 'raise' in legal and villain.bet<(me.stack+me.bet)*.35:
            cf=max(.075,min(.18,.085+.65/(depth+3)))
            foldp=max(0.,1-cf/max(.025,f))
            foldp*=.93**len(others)
            risk=min(me.stack,max(0,villain.stack+villain.bet-me.bet))
            extra=max(0,risk+me.bet-villain.bet)
            ce=pre_equity(h,cf)
            rp=.025 if state.players_remaining>2 else 0.
            if state.players_remaining==4:
                short=min(s.stack+s.bet for s in opps)
                rp=.105 if short<(me.stack+me.bet)*.40 else .055
            ev=foldp*P+(1-foldp)*(ce*(P+risk+extra)-risk-rp*(risk+extra))
            if ce>.31 and h['p']<.34 and ev>bb*.40:
                return finish('raise',me.stack+me.bet)
        # A small blocker bluff range is used only after observing substantial
        # folding. The default is to preserve chips with speculative hands.
        if depth>26 and m['nr']==1 and f>.28 and 'raise' in legal:
            vst=stats[str(villain.seat)]
            pf_fold=(vst[4]+2)/(vst[3]+4)
            suited=state.cards[0][-1]==state.cards[1][-1]
            if suited and hi==14 and lo in (4,5) and vst[3]>=6 and pf_fold>.72 and u<.45:
                return finish('raise',maxbet*(3.25 if not inpos else 2.9))
        realization=.86 if inpos else .77
        if state.cards[0][-1]==state.cards[1][-1]:realization+=.055
        pair=state.cards[0][0]==state.cards[1][0]
        if pair:realization+=.04
        if cost<bb*1.1:realization+=.08
        if maniac:realization+=.05
        effective=min(me.stack,villain.stack)
        setmine=pair and cost<effective/17 and m['nr']<3
        if (eq*min(1.,realization)>req+.012 and (h['p']<max(.22,f*1.4) or cost<bb*1.1)) or setmine:
            return finish('call')
        return finish('fold')

    def postflop(self,state,m,me,opps,a,b,fs,order,depth,P,cost,bb,u,legal,finish):
        ids=[IDS[x] for x in state.board];board=[CARDS[x] for x in ids]
        tex=board_texture(ids)
        bc,sc,bmask,top,second,bpairs,drawstreet=tex
        br=[x//4 for x in ids]
        street=len(ids)-2
        hero=[CARDS[a],CARDS[b]]
        rank=eval7.evaluate(board+hero)
        val,fd,sd=made_info(a,b,rank,tex)
        # Start with the player whose action conveys the strongest range.
        def priority(s):
            c=m['c'][str(s.seat)]
            pa=c['pa'];last=pa[-1][1] if pa else ''
            return (s.status=='active',s.bet,1 if last=='raise' else 0,-fs[s.seat])
        ordered=sorted(opps,key=priority,reverse=True)
        villain=ordered[0]
        es=[]
        for oi,s in enumerate(ordered[:2]):
            st=m['p'][str(s.seat)];c=m['c'][str(s.seat)]
            rng=posterior_range(a,b,ids,tex,st,c,fs[s.seat],street,filter_actions=(oi==0),deadline=m.get('deadline',0)-120000,limit=64 if m.get('lowbank') else 128)
            if not rng:
                dead=set(ids+[a,b])
                rng=[(h,1.) for x,y,h,mask,p in RANGES[-1] if x not in dead and y not in dead]
            if street==3:e=eval7.py_hand_vs_range_exact(hero,rng,board)
            else:e=eval7.py_hand_vs_range_monte_carlo(hero,rng,board,160 if m.get('lowbank') else 512 if len(opps)==1 else 320)
            es.append(e)
        eq=es[0]
        if len(es)>1:eq*=es[1]
        if len(opps)>2:eq*=max(.15,(min(es)*.94)**(len(opps)-2))
        if street==3 and rank==eval7.evaluate(board):
            # Playing the board means a tie or loss, never an outright win.
            # Independent HU equities would count each tie as another 1/2.
            tieprob=math.prod(min(1.,2*x) for x in es)
            if len(opps)>2:tieprob*=min(1.,2*min(es))**(len(opps)-2)
            eq=tieprob/(len(opps)+1)
            if rank>>24==8 and ((rank>>16)&15)==12:
                return finish('call' if cost else 'check')
        # Draw outcomes are correlated across opponents. Preserve equity from
        # making a strong flush/straight rather than multiplying it away.
        if len(opps)>1 and street<3 and (fd or sd):
            dp=(.32 if fd else .27 if sd>=2 else .15) if street==1 else (.175 if fd else .16 if sd>=2 else .085)
            if fd and sd:dp*=1.28
            if fd:
                sa,sb=a%4,b%4
                fsuit=sa if sc[sa]+(2 if sa==sb else 1)==4 else sb
                fr=max(a//4 if sa==fsuit else -1,b//4 if sb==fsuit else -1)
                if fr<10:dp*=.80
            eq=max(eq,min(es)*.68,dp*.83)
        # A short all-in only contests its eligible main pot. New bets are
        # valued against active opponents, rather than against the short stack.
        call_eq=eq
        active=[s for s in opps if s.status=='active']
        allins=[s for s in opps if s.status=='all_in']
        if allins and active:
            active_eq=es[0]
            if len(active)>1 and len(es)>1:active_eq*=es[1]
            if len(active)>2:active_eq*=max(.15,(min(es)*.94)**(len(active)-2))
            cap=max(m['c'][str(s.seat)].get('total',0) for s in allins)
            locked=sum(min(c.get('total',0),cap) for c in m['c'].values())
            w=min(1.,locked/max(1,P+cost))
            call_eq=eq*w+active_eq*(1-w)
            eq=active_eq
        st=m['p'][str(villain.seat)]
        maniac=is_maniac(st)
        foldp=1.
        for s in opps:foldp*=fold_rate(m['p'][str(s.seat)])
        active=[s for s in opps if s.status=='active']
        spr=me.stack/max(1,P)
        own=m['c'][str(me.seat)]
        preagg=own['role'] in (1,2)
        mypast=own['pa']
        lastmine=mypast[-1][1] if mypast else ''
        postorder=[s for s in order[-2:]+order[:-2]] if len(order)>2 else [s for s in order if s!=state.button]+[state.button]
        inpos=all(postorder.index(me.seat)>postorder.index(s.seat) for s in opps if s.status=='active')
        def bet(frac):
            amount=me.bet+cost+frac*(P+cost)
            if amount-me.bet>me.stack*.70 and eq>.64:amount=me.bet+me.stack
            return finish('raise',amount)
        if cost:
            req=call_threshold(state,me,villain,cost)
            terminal=street==3 or cost>=me.stack*.75 or villain.status=='all_in'
            haircut=0. if terminal else .018+(.012 if not inpos and val<1. else 0)
            if fd or sd:haircut-=.015 if spr>1.5 else 0
            if call_eq<req+haircut:return finish('fold')
            if 'raise' in legal and active:
                value=(eq>.755 and val>=1.) or (eq>.65 and val>=2. and len(opps)>1)
                if maniac and eq>.64 and val>=.58:value=True
                if value:
                    if spr<2.2 or (maniac and eq>.70):return finish('raise',me.stack+me.bet)
                    return bet(.78 if val>=2. else .62)
                if street<3 and (fd or sd) and eq>.34 and foldp>.42 and u<.16 and lastmine!='raise' and spr>2.:
                    return bet(.68)
            return finish('call')
        if 'raise' not in legal or not active:return finish('check')
        # Thin value is reduced multiway; strong hands charge draws and callers.
        value=(eq>(.61 if street<3 else .59) and val>=.58)
        if len(opps)>1:value=eq>.49 and val>=1.
        if street==3 and val<1. and not maniac:value=False
        if val>=4. and eq>.50:value=True
        if value:
            if spr<1.35 and eq>.64:return finish('raise',me.stack+me.bet)
            if maniac and eq>.69:
                if spr<4:return finish('raise',me.stack+me.bet)
                return bet(1.05)
            size=.52 if street==1 else .65 if street==2 else .74
            if val>=2.7 and eq>.82:size=.82 if street<3 else .95
            if val<1.1 and eq<.72:size=.42 if street<3 else .48
            return bet(size)
        # Fold-heavy players can be profitably attacked without much equity.
        if foldp>.76 and spr>.45 and not any(s.status=='all_in' for s in opps):
            return bet(.30 if street<3 else .40)
        if len(opps)==1:
            scary=max(bc)>=2 or (max(br)>=10 and sum(x>=9 for x in br)<=2)
            if street==1 and preagg and eq>.29 and not maniac and u<(.66 if scary else .43):
                return bet(.34)
            if street<3 and (fd or sd) and eq>.34 and foldp>.30 and u<.57:
                return bet(.52)
            # River bluffs carry a blocker and target opponents who can fold.
            blocker=max(a//4,b//4)>=11 or (max(sum(x%4==s for x in ids) for s in range(4))>=3 and max(a//4,b//4)==12)
            if street==3 and eq<.25 and blocker and foldp>.50 and u<.18 and not maniac:
                return bet(.72)
        return finish('check')
