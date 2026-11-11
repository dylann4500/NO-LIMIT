"""Range-based tournament NLHE agent. All persistent observations travel in memory."""
import json
import os
import pickle
import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

with open(os.path.join(os.path.dirname(__file__), 'preflop.json')) as _f:
    _TABLE = json.load(_f)
CUTS = _TABLE['cuts']
PERCENTILE = _TABLE['rank']
EQUITY = _TABLE['equity']
with open(os.path.join(os.path.dirname(__file__), 'pushfold.json')) as _f:
    PUSHFOLD = {int(k):v for k,v in json.load(_f).items()}
PUSH_DEPTHS=tuple(sorted(PUSHFOLD))

def push_hand(depth, hand):
    lo=PUSH_DEPTHS[0];hi=lo
    for d in PUSH_DEPTHS:
        hi=d
        if d>=depth:break
        lo=d
    w=max(0.,min(1.,(depth-lo)/max(1,hi-lo)))
    a=PUSHFOLD[lo];b=PUSHFOLD[hi]
    return tuple(a[f][hand]*(1-w)+b[f][hand]*w for f in ('shove','ev','equity_call'))

RANKS = '23456789TJQKA'
SUITS = 'cdhs'
STRINGS = [r+s for r in RANKS for s in SUITS]
CARDS = {s: eval7.Card(s) for s in STRINGS}
IDS = {s:i for i,s in enumerate(STRINGS)}
RANK = [i//4 for i in range(52)]
SUIT = [i%4 for i in range(52)]
EVAL = eval7.evaluate
MC = eval7.py_hand_vs_range_monte_carlo

def key(a, b):
    if a//4 < b//4: a,b=b,a
    return RANKS[a//4]+RANKS[b//4]+('' if a//4==b//4 else 's' if a%4==b%4 else 'o')

# Uniform physical combinations, with disjoint-card masks and canonical ranks.
COMBOS=[]
for _a in range(52):
    for _b in range(_a):
        _k=key(_a,_b)
        COMBOS.append((_a,_b,(CARDS[STRINGS[_a]],CARDS[STRINGS[_b]]),
                       (1<<_a)|(1<<_b), (1<<(_a//4))|(1<<(_b//4)), PERCENTILE[_k]))
# Use all combinations in C for raw preflop ranges; a fixed stratified sample for
# action-conditioned postflop ranges. Lists are built only at import.
RANGES=[]
SAMPLES=[]
SAMPLE_RANGES=[]
for _cut in CUTS:
    _r=[c for c in COMBOS if c[5] <= _cut]
    RANGES.append([(c[2],1.0) for c in _r])
    # Pseudorandom, deterministic order prevents suit/rank bias in a prefix.
    _r.sort(key=lambda c: ((c[0]*53+c[1]+1)*2654435761)&0xffffffff)
    SAMPLES.append(tuple(_r))
    SAMPLE_RANGES.append([(c[2],1.) for c in _r[::max(1,len(_r)//192)]][:224])
STRAIGHTS=[sum(1<<r for r in range(i,i+5)) for i in range(9)]+[(1<<12)|15]
# Number of distinct rank outs to a straight, and whether a backdoor is possible.
DRAW=[]
for _mask in range(8192):
    _outs=0
    for _s in STRAIGHTS:
        _missing=_s & ~_mask
        if _missing and _missing & (_missing-1)==0: _outs|=_missing
    DRAW.append(_outs.bit_count())

# Unopened ranges by seats dealt, physical position, and effective stack. Each
# entry is a physical-combination percentile; the edge is mixed over 3.5%.
OPEN_FREQ={}
for _n in range(2,9):
    for _pos in range(_n):
        _behind=1 if _pos==0 else 0 if _pos==1 else _n+1-_pos
        _base=.55 if _pos==0 else .47 if _behind==2 else .31 if _behind==3 else .25 if _behind==4 else .20 if _behind==5 else .16
        for _d in (20,40,100):
            _adjust=(-.035 if _behind<=3 else .01) if _d==20 else 0.
            OPEN_FREQ[_n,_pos,_d]=_base+_adjust


def bucket(frac):
    for i,c in enumerate(CUTS):
        if frac<=c:return i
    return len(CUTS)-1


def eq_pre(k, frac):
    row=EQUITY[k]
    if frac<=CUTS[0]:return row[0]
    for i in range(1,len(CUTS)):
        if frac<=CUTS[i]:
            w=(frac-CUTS[i-1])/(CUTS[i]-CUTS[i-1])
            return row[i-1]*(1-w)+row[i]*w
    return row[-1]


def kind(obj):
    k=obj.kind
    return getattr(k,'value',k)


def new_stats():
    # hands, VPIP, PFR, postflop actions, postflop bets, folds facing bet
    return [0,0,0,0,0,0]


def observe(s, memory):
    try: m=pickle.loads(memory) if memory else {}
    except (ValueError,TypeError,EOFError,pickle.UnpicklingError): m={}
    if not m:
        m={'h':-1,'stats':{str(p.seat):new_stats() for p in s.seats},'seed':int.from_bytes(os.urandom(4),'little'),'rounds':[{}, {}, {}, {}], 'pr':[], 'vp':[], 'pf':[],'st':0}
    stats=m['stats']
    for e in s.events:
        k=kind(e)
        if k=='hand':
            m['h']=e.amount
            m['rounds']=[{}, {}, {}, {}]; m['pr']=[];m['vp']=[];m['pf']=[];m['st']=0
            for p in s.seats:
                if p.status!='busted': stats[str(p.seat)][0]+=1
        elif k=='board':
            m['st']=min(3,m['st']+1)
        elif k in ('fold','check','call','raise'):
            sid=str(e.seat); st=m['st']; ps=stats.get(sid)
            if ps is None:ps=new_stats();stats[sid]=ps
            rd=m['rounds'][st]
            prev=rd.get(sid,['',0,0])
            rd[sid]=[k,e.amount or 0,prev[2]+(k=='raise')]
            if st==0:
                if k in ('call','raise') and sid not in m['vp']:
                    m['vp'].append(sid);ps[1]+=1
                if k=='raise':
                    m['pr'].append([sid,e.amount or 0])
                    if sid not in m['pf']: m['pf'].append(sid);ps[2]+=1
            else:
                ps[3]+=1
                if k=='raise':ps[4]+=1
                if k=='fold' and any(v[0]=='raise' for v in rd.values()):ps[5]+=1
    # Fallback for an SDK whose first event batch omits a hand marker.
    if m['h']!=s.hand_number:
        m['h']=s.hand_number;m['rounds']=[{}, {}, {}, {}];m['pr']=[];m['vp']=[];m['pf']=[]
    m['st']=0 if not s.board else len(s.board)-2
    x=m['seed'] ^ ((s.hand_number+1)*747796405) ^ (IDS[s.cards[0]]*277+IDS[s.cards[1]])
    x^=(x<<13)&0xffffffff;x^=x>>17;x^=(x<<5)&0xffffffff
    m['seed']=x&0xffffffff
    return m,(x&0xffffffff)/4294967296.0


def tendencies(m, sid):
    a=m['stats'].get(str(sid),[0]*6)
    n=a[0]
    vp=(a[1]+5.5)/(n+20)
    pfr=(a[2]+3.8)/(n+20)
    ag=(a[4]+2.5)/(a[3]+7)
    return vp,pfr,ag


def is_folder(m, sid):
    a=m['stats'].get(str(sid))
    # A tight positional player must not be mistaken for a check-or-fold bot.
    return bool(a and a[0]>=12 and a[1]<=a[0]*.035)


def live_order(s):
    players=[p for p in s.seats if p.status!='busted']
    ids=[p.seat for p in players]
    try: b=ids.index(s.button)
    except ValueError:b=len(ids)-1
    return players[b+1:]+players[:b+1]


def risk_premium(s, me, opponents, amount):
    n=s.players_remaining
    if n<=2 or amount<=0:return 0.0
    total=me.stack+me.bet
    if total<=0:return 0.0
    frac=min(1,amount/total)
    otherstacks=sorted(p.stack+p.bet for p in s.seats if p.status!='busted' and p.seat!=s.seat)
    shorter=sum(x<total*.5 for x in otherstacks)
    cover=any(p.stack+p.bet>=total*.95 for p in opponents)
    pay=s.config.payouts or [50,30,20]
    scale=min(1.5,sum(pay[1:min(n,len(pay))])/max(1,pay[0])/.9)
    if scale==0:return 0.
    base=(.025 if n>5 else .045 if n==5 else .075 if n==4 else .035)*scale
    if shorter and cover:base+=min(.07,.025*shorter)
    if otherstacks and total<otherstacks[len(otherstacks)//2]*.4:base*=.5
    return base*frac


def icm(stacks, payouts, hero):
    # Closed-form ICM for the <=4-player states where this function is used.
    total=sum(stacks); n=len(stacks); h=stacks[hero]
    pay=list(payouts)+[0.]*(n-len(payouts))
    p1=h/total; p2=0.; p3=0.
    others=[x for i,x in enumerate(stacks) if i!=hero]
    for i,x in enumerate(others):
        first=x/total
        p2+=first*h/(total-x)
        if n==4:
            for j,y in enumerate(others):
                if i!=j:p3+=first*y/(total-x)*h/max(.000001,total-x-y)
    if n==2:return pay[1]+(pay[0]-pay[1])*p1
    if n==3:return pay[2]+(pay[0]-pay[2])*p1+(pay[1]-pay[2])*p2
    return pay[3]+(pay[0]-pay[3])*p1+(pay[1]-pay[3])*p2+(pay[2]-pay[3])*p3


def icm_call_threshold(s, me, opponents, cost, contest_pot):
    if not (2<len([p for p in s.seats if p.status!='busted'])<=4 and len(opponents)==1):return None
    if cost<.65*me.stack or cost<=0:return None
    opp=opponents[0]
    if opp.stack>0 and cost<me.stack:return None
    ps=[p for p in s.seats if p.status!='busted']
    hi=next(i for i,p in enumerate(ps) if p.seat==s.seat)
    vi=next(i for i,p in enumerate(ps) if p.seat==opp.seat)
    # Bets beyond our possible contribution are returned to their owners and
    # cannot improve our pot odds or our ICM outcome when we win.
    cap=me.bet+me.stack
    stacks=[float(p.stack) for p in ps]
    stacks[vi]+=sum(max(0,p.bet-cap) for p in ps if p.seat!=s.seat)
    pay=list(s.config.payouts or [50,30,20])[:len(ps)]
    # Ties in a zero-stack state can be settled by the limit of an epsilon stack.
    win=stacks[:];win[hi]+=contest_pot
    lose=stacks[:];lose[hi]-=cost;lose[vi]+=contest_pot+cost
    fold=stacks[:];fold[vi]+=contest_pot
    win=[max(.001,x) for x in win];lose=[max(.001,x) for x in lose];fold=[max(.001,x) for x in fold]
    a=icm(win,pay,hi);b=icm(lose,pay,hi);c=icm(fold,pay,hi)
    return max(0.,min(.95,(c-b)/max(.0001,a-b)))


def made_info(a,b, boardids, boardcards, boardmask, ranks, suits):
    v=EVAL([CARDS[STRINGS[a]],CARDS[STRINGS[b]]]+boardcards)
    cat=v>>24; top=(v>>16)&15
    brmax=max(ranks); boardpairs={r for r in ranks if ranks.count(r)>=2}
    if cat==0: made=0
    elif cat==1:
        if top in boardpairs: made=0
        elif top>=brmax: made=4 if a//4==b//4 and top>brmax else 3
        elif top>=sorted(set(ranks),reverse=True)[min(1,len(set(ranks))-1)]:made=2
        else:made=1
    elif cat==2:
        second=(v>>12)&15
        if top in boardpairs and second in boardpairs:made=0
        elif top in boardpairs or second in boardpairs:
            own=second if top in boardpairs else top
            made=3 if own>=max((r for r in ranks if r not in boardpairs),default=brmax) else 2
        else:made=5
    elif cat==3:
        made=1 if ranks.count(top)>=3 else 6
    else:made=cat+3
    mask=(1<<(a//4))|(1<<(b//4))|boardmask
    outs=DRAW[mask] if cat<4 and len(boardids)<5 else 0
    fd=False;nut=False
    if len(boardids)<5:
        for su in set((a%4,b%4)):
            n=suits[su]+(a%4==su)+(b%4==su)
            if n==4:
                fd=True
                best=max(a//4 if a%4==su else -1,b//4 if b%4==su else -1)
                nut=best>=11
    draw=(2 if fd else 0)+(2 if outs>=2 else 1 if outs else 0)
    if len(boardids)==5:
        nut=any(suits[i%4]>=3 and i//4>=11 for i in (a,b))
    return made,draw,nut,cat,v


def range_class(h, ca, cb, rm, ctx):
    bc,counts,brmax,brmid,suits,bm,drawallowed=ctx
    v=EVAL([h[0],h[1]]+bc);ct=v>>24;pair=(v>>16)&15
    if ct==0:q=0
    elif ct==1:q=0 if counts[pair]>=2 else 3 if pair>=brmax else 2 if pair>=brmid else 1
    elif ct==2:q=2 if counts[pair]>=2 else 4
    elif ct==3:q=1 if counts[pair]>=3 else 5
    else:q=6
    d=0
    if drawallowed:
        if ct<4 and DRAW[rm|bm]:d=1
        if suits[ca%4]+1+(cb%4==ca%4)==4 or suits[cb%4]+1+(ca%4==cb%4)==4:d=2
    return q,d


def range_context(bid,bc):
    rs=[i//4 for i in bid]; suits=[0]*4; mask=0
    for i in bid:suits[i%4]+=1;mask|=1<<(i//4)
    return bc,[rs.count(i) for i in range(13)],max(rs),sorted(rs)[len(rs)//2],suits,mask,len(bid)<5


def post_equity(s,m, hero, opponents, primary, pressure, r):
    st=len(s.board)-2
    bank=getattr(s,'time_bank_ms',100) or 0
    effort=128 if bank>60 else 96 if bank>25 else 64 if bank>8 else 32
    iterations=640 if bank>60 else 384 if bank>8 else 192
    bid=[IDS[x] for x in s.board]; bc=[CARDS[x] for x in s.board]
    a,b=hero; blocked=(1<<a)|(1<<b)
    bm=0;suits=[0]*4;ranks=[]
    for i in bid:blocked|=1<<i;bm|=1<<(i//4);suits[i%4]+=1;ranks.append(i//4)
    made,draw,nut,cat,hv=made_info(a,b,bid,bc,bm,ranks,suits)
    wet=max(suits)>=2 or DRAW[bm]>0
    boardvalue=EVAL(bc) if st==3 else 0
    if st==3 and hv==boardvalue:
        bcat=boardvalue>>24;br=(boardvalue>>16)&15;bk=(boardvalue>>12)&15
        if (bcat==8 and br==12) or (bcat==7 and (bk==12 or br==12 and bk==11)):
            return 1/(len(opponents)+1),.5,made,draw,nut,wet,-1
    # For these free-check hands the betting policy depends only on draws,
    # position, and initiative. Equity sampling cannot change its decision.
    if not pressure and st<3 and made<2 and draw<3:
        return .3,.3,made,draw,nut,wet,cat
    # Protect the bank from cumulative overruns. This path uses only one hand
    # evaluation, and still distinguishes draws, relative pairs, and monsters.
    configured_bank=getattr(s.config,'time_bank_ms',100)
    reserve=max(8,min(60,.6*(100 if configured_bank is None else configured_bank)))
    if bank<reserve:
        raw=(.16,.32,.46,.62,.71,.83,.91,.95,.97,.985,.995)[min(made,10)]
        if st<3 and draw:raw=max(raw,.29+.055*draw)
        if made==0 and max(a//4,b//4)==12:raw+=.10
        if st==3 and hv==boardvalue:raw=min(raw,.5)
        return raw**(1+.78*(len(opponents)-1)),raw,made,draw,nut,wet,cat
    vp,pfr,ag=tendencies(m,primary.seat)
    sid=str(primary.seat)
    pr=m['pr']; nr=len(pr)
    if sid in m['pf']:
        order=live_order(s);ids=[p.seat for p in order];nplayers=len(ids)
        pos=ids.index(primary.seat)
        behind=1 if pos==0 else 0 if pos==1 else nplayers+1-pos
        base=.82 if nplayers==2 and primary.seat==s.button else .56 if behind==1 else .47 if behind==2 else .31 if behind==3 else .25 if behind==4 else .20 if behind==5 else .16
        frac=max(.12,min(.8,base*.65+pfr*.55))
        if nr>1:frac=max(.05,min(.55,pfr*.55))
    elif sid in m['vp']:frac=max(.15,min(.85,vp*1.65))
    else:frac=.85
    pfaction=m['rounds'][0].get(sid)
    if nr>=2 and pfaction and pfaction[0]=='call':frac=min(frac,.16)
    if vp>.55:frac=max(frac,.65)
    idx=bucket(frac)
    samples=SAMPLES[idx]
    rounds=m['rounds']
    # Retain the latest relevant previous-street investment. Current bets receive
    # a polarized distribution; minbets and habitual aggression stay much wider.
    prior=0;priorstreet=0
    for t in range(1,st):
        act=rounds[t].get(sid)
        if act and act[0] in ('call','raise'):
            prior=2 if act[0]=='raise' or act[2] else 1
            priorstreet=t
    current=rounds[st].get(sid)
    isbet=pressure and current and current[0]=='raise'
    if pressure and not current:isbet=True
    aggression=max(0.,(ag-.38)*1.8)
    # Board-dependent conditioning in a bounded stratified sample. eval7 runs
    # the final runouts and comparisons in C, not in a Python simulation loop.
    if not prior and not isbet:
        raw=MC([CARDS[s.cards[0]],CARDS[s.cards[1]]],SAMPLE_RANGES[idx],bc,iterations if st<3 else 256)
        return raw**(1+.78*(len(opponents)-1)),raw,made,draw,nut,wet,cat
    currentctx=range_context(bid,bc)
    priorctx=range_context(bid[:priorstreet+2],bc[:priorstreet+2]) if prior else None
    if prior and isbet:effort=min(effort,96)
    n=min(effort,len(samples)); offset=((m['seed']>>8)%len(samples))
    step=max(1,len(samples)//n)
    cond=[]
    big=s.to_call/max(1,s.pot-s.to_call)
    if big<.23:betweights=(.35,.6,.8,1.,1.,1.,1.)
    elif st==3:betweights=(.12*min(2,big/(1+big)/.43),.10,.18,.42,.85,1.,1.)
    else:betweights=(.16,.22,.4,.8,1.,1.,1.)
    priorweights=(.10,.34,.62,.9,1.,1.,1.) if prior==1 else (.055,.12,.24,.55,.9,1.,1.)
    for j in range(n):
        c=samples[(offset+j*step)%len(samples)]
        if c[3]&blocked:continue
        ca,cb,h,_,rm,_=c
        w=1.
        if prior:
            q,d=range_class(h,ca,cb,rm,priorctx)
            w=priorweights[q]
            if d:w=max(w,.58 if prior==1 else .42)
        if isbet:
            q,d=range_class(h,ca,cb,rm,currentctx)
            w*=betweights[q]
            if st==3 and q==0 and (ca//4==12 or cb//4==12):w*=1.5
            if st<3 and d:w=max(w,.5 if big<1 else .4)
            if q==0:w*=max(.25,1-max(0,.38-ag)*2)
            w=min(1.,w+aggression*.65)
        # Fixed acceptance randomness independent of equity RNG and strategy mix.
        u=(((ca*53+cb+1)*2246822519+(m['seed']&65535)*3266489917)&0xffff)/65536.
        if u<w:cond.append((h,1.))
    if not cond:
        for j in range(n):
            c=samples[(offset+j*step)%len(samples)]
            if not c[3]&blocked:cond.append((c[2],1.))
    raw=MC([CARDS[s.cards[0]],CARDS[s.cards[1]]],cond,bc,iterations if st<3 else 256)
    # Multiway hands require strength against several ranges. Correlation through
    # shared runouts makes a softened product preferable to naive independence.
    eq=raw**(1+.78*(len(opponents)-1))
    return eq,raw,made,draw,nut,wet,cat


class Agent(poker_agent_sdk.Agent):
    def act(self,state,memory):
        s=state
        legal={kind(a):a for a in s.legal_actions}
        # Every path is projected onto the legal menu; amounts are integers.
        def finish(k,amount=0):
            if k=='raise' and 'raise' not in legal:
                k='call' if 'call' in legal else 'check'
            if k=='raise' and 'raise' in legal:
                a=legal['raise']; amount=max(int(a.min_amount),min(int(a.max_amount),int(amount)))
                action=Action.raise_to(amount)
            elif k=='call' and 'call' in legal:action=Action.call()
            elif k=='check' and 'check' in legal:action=Action.check()
            elif k=='fold' and 'fold' in legal:action=Action.fold()
            elif 'check' in legal:action=Action.check()
            elif 'fold' in legal:action=Action.fold()
            elif 'call' in legal:action=Action.call()
            else:
                a=legal['raise'];action=Action.raise_to(int(a.min_amount))
            return action,pickle.dumps(m,protocol=4)
        m,r=observe(s,memory)
        me=next(p for p in s.seats if p.seat==s.seat)
        opp=[p for p in s.seats if p.seat!=s.seat and p.status in ('active','all_in')]
        if not opp:return finish('check')
        order=live_order(s); ids=[p.seat for p in order]; n=len(order)
        pos=ids.index(s.seat)
        bb=max(1,s.blinds[1]); stack=me.stack; total=stack+me.bet; depth=total/bb
        cost=min(s.to_call,stack)
        pot=max(1,s.pot-sum(max(0,p.bet-total) for p in s.seats if p.seat!=s.seat))
        h=[IDS[x] for x in s.cards]; k=key(*h); pct=PERCENTILE[k]
        if not s.board:
            pr=m['pr'];nr=len(pr)
            sb=(pos==0 and n>2) or (n==2 and s.seat==s.button)
            big=(pos==1 and n>2) or (n==2 and s.seat!=s.button)
            # Number still to act in the natural preflop order. At heads-up the
            # button/small blind opens first, unlike the multiway blind order.
            behind=(1 if sb else 0 if big else n+1-pos)
            pending=[p for p in opp if p.status=='active' and (sb and (n==2 or p.seat==ids[1]) or not sb and not big and (ids.index(p.seat)>pos or ids.index(p.seat)<2))]
            effective=min(total,max(p.stack+p.bet for p in opp))/bb
            limpers=sum(1 for sid in m['vp'] if sid not in m['pf'] and sid!=str(s.seat))
            if not nr:
                # Smooth position and stack-depth chart, with mixed boundaries.
                opening=.82 if n==2 and sb else OPEN_FREQ.get((n,pos,20 if effective<25 else 40 if effective<60 else 100),.14)
                if big and cost==0:
                    # Isolate weak limpers with a linear value range.
                    iso=.30 if len(opp)==1 else .19
                    if limpers and pct<iso:return finish('raise',max(3.2+limpers,3)*bb)
                    return finish('check')
                foldiness=sum(is_folder(m,p.seat) for p in opp)
                opening=min(.97,opening+.08*foldiness+.07*(n==2))
                if pending and all(is_folder(m,p.seat) for p in pending):opening=.98
                opening/=1+.22*limpers
                openmix=max(0.,min(1.,(opening-pct)/.035+.5))
                if effective<=12 and sb and len(pending)==1 and not limpers and pot/bb<1.85:
                    shove,shove_ev,_=push_hand(effective,k)
                    premium=risk_premium(s,me,opp,min(stack,effective*bb))*effective
                    folder=is_folder(m,pending[0].seat)
                    if folder or (r<shove and shove_ev>premium):return finish('raise',total)
                    return finish('check' if cost==0 else 'fold')
                if effective<=11:
                    # Nash-style push/fold: fold equity + equity against plausible
                    # calling ranges, taking all remaining players into account.
                    risk=max(1.,min(depth,effective))
                    remaining=max(1,len(pending))
                    callfrac=(.19+1.6/(risk+3)) if remaining==1 else (.14+.8/(risk+3)) if remaining==2 else (.08+.7/(risk+3))
                    callfrac=min(.6,callfrac)
                    eq=eq_pre(k,callfrac)
                    fe=(1-callfrac)**remaining
                    ev=fe*(pot/bb)+(1-fe)*(eq*(pot/bb+2*risk)-risk)
                    premium=risk_premium(s,me,opp,min(stack,effective*bb))*risk
                    if ev>premium+.12 and pct<min(.95,opening*1.5):return finish('raise',me.bet+stack)
                    return finish('check' if cost==0 else 'fold')
                if r<openmix:
                    size=2.15 if depth<35 else 2.4
                    if sb:size=2.3 if depth<25 else 2.8
                    size+=limpers*.9
                    return finish('raise',size*bb)
                # Completing the small blind protects a limping range and keeps
                # marginal hands out of expensive raise/fold sequences.
                if sb and not limpers and effective>16 and pct<(.97 if n==2 else .85) and r<(.75 if n==2 else .65):return finish('call')
                # Suited playable overlimps are reserved for small multiway pots.
                if limpers and cost<=bb and k.endswith('s') and pct<.40 and depth>22 and r<.55:return finish('call')
                return finish('check' if cost==0 else 'fold')
            raiserid=pr[-1][0]
            raiser=next((p for p in s.seats if str(p.seat)==raiserid),opp[0])
            vp,pfr,ag=tendencies(m,raiser.seat)
            ownraised=any(x[0]==str(s.seat) for x in pr)
            raise_size=max(x[1] for x in pr)/bb
            loose=pfr>(.70 if n==2 else .40) or (vp>.52 and ag>.5)
            # Range estimate accounts for opener position, observed frequency,
            # raise depth, and price. Tiny repeated raises from maniacs stay wide.
            ridx=ids.index(raiser.seat) if raiser.seat in ids else 2
            ahead=(1 if ridx==0 else 0 if ridx==1 else n+1-ridx) if n>2 else 1
            base=.82 if n==2 and raiser.seat==s.button else .56 if ahead==1 else .47 if ahead==2 else .31 if ahead==3 else .25 if ahead==4 else .20 if ahead==5 else .16
            frac=max(.10,min(.8,base*.65+pfr*.55))
            if nr>=2 and not loose:
                if effective<=22 and nr==2:frac=max(.065,frac*(.55 if ownraised else .45))
                else:frac=max(.025,frac*(.26 if ownraised else .34))
            if raise_size>5 and nr==1 and not loose and effective>18:frac*=.65
            if loose:frac=max(.45,frac)
            equity=eq_pre(k,frac)
            raiser_sb=(n==2 and raiser.seat==s.button) or (n>2 and raiser.seat==ids[0])
            if big and raiser_sb and len(opp)==1 and nr==1 and effective<=20 and not loose and (cost>=stack*.85 or raiser.status=='all_in'):
                # These equities use the solved shove range, including its
                # composition and card removal rather than just range width.
                equity=push_hand(effective,k)[2]
            opponents_in=sum(1 for p in opp if p.bet>=max(bb,s.to_call+me.bet)*.8)
            if opponents_in>1:equity=equity**(1+.65*(opponents_in-1))
            odds=cost/(pot+cost)
            premium=risk_premium(s,me,opp,cost)
            icmt=icm_call_threshold(s,me,opp,cost,pot)
            threshold=max(odds+premium,icmt if icmt is not None else 0.)
            allin=cost>=stack*.9 or raiser.status=='all_in'
            if allin:
                if equity>threshold+.018:return finish('call')
                return finish('check' if cost==0 else 'fold')
            # Linear value 3bets; suited wheel aces supply a small blocker bluff
            # component against opponents whose opening range can still fold.
            value= .047 if nr==1 else .018
            if loose:value=.15 if nr<3 else .085
            if effective<=20:value+=.025
            if pct<value and equity>.56:
                amt=max(raise_size*(3 if pos>ridx else 3.7),raise_size+2.5)*bb
                if effective<=22 or amt>total*.45:amt=total
                return finish('raise',amt)
            if nr==1 and not loose and k in ('A5s','A4s','A3s','KTs') and r<.16 and effective>32 and len(opp)<=4:
                return finish('raise',raise_size*3.3*bb)
            # Position/realization corrections prevent profitable-looking but
            # dominated deep-stack calls. The big blind receives the best price.
            realize=.89 if big else .85 if pos>ridx else .77
            if k.endswith('s') or len(k)==2:realize+=.04
            if depth<20:realize+=.04
            if nr>=2:realize-=.06
            needed=threshold+.035+(0 if big else .025)
            cap=.60 if big and nr==1 else .32 if nr==1 else .12 if loose else .14 if nr==2 and cost<stack*.1 and pos>ridx else .07
            if equity*min(.99,realize)>needed and pct<cap:return finish('call')
            return finish('check' if cost==0 else 'fold')
        # Postflop: choose the range most strongly representing current action.
        st=len(s.board)-2; rd=m['rounds'][st]
        bettors=[p for p in opp if rd.get(str(p.seat),[''])[0]=='raise']
        primary=max(bettors,key=lambda p:p.bet) if bettors else next((p for p in opp if m['pr'] and str(p.seat)==m['pr'][-1][0]),opp[0])
        eq,raw,made,draw,nut,wet,cat=post_equity(s,m,h,opp,primary,cost>0,r)
        if cat==-1:return finish('call' if cost else 'check')
        premium=risk_premium(s,me,opp,cost)
        spr=min(stack,max(p.stack for p in opp))/pot
        vp,pfr,ag=tendencies(m,primary.seat)
        maniac=ag>.69 or (pfr>(.70 if n==2 else .4) and ag>.52)
        passive=ag<.23 and m['stats'][str(primary.seat)][3]>=12
        ownpf=bool(m['pr'] and m['pr'][-1][0]==str(s.seat))
        hu=len(opp)==1
        inpos=pos==n-1 or (n==2 and s.seat==s.button)
        if cost:
            odds=cost/(pot+cost)
            icmt=icm_call_threshold(s,me,opp,cost,pot)
            needed=max(odds+premium,icmt if icmt is not None else 0.)
            if st<3:
                needed+=.018 if hu else .035
                if not inpos and made<3:needed+=.02
            elif passive and s.to_call>pot*.35:needed+=.06
            # High equity value raises and occasional strong semibluffs.
            raiseth=.78 if st<3 else .86
            if maniac:raiseth-=.06
            if eq>raiseth and (made>=3 or spr<1) and r<(.98 if st==3 and made>=7 else .84):
                frac=.72 if wet or st>=2 else .6
                amount=me.bet+cost+(pot+cost)*frac
                if amount>=total*.62 or spr<1.15:amount=total
                return finish('raise',amount)
            if hu and st<3 and draw>=3 and raw>.39 and not maniac and spr>2 and r<.14:
                return finish('raise',me.bet+cost+(pot+cost)*.8)
            if eq>needed:return finish('call')
            return finish('fold')
        # Value and bluff ranges share the same sizes. Low showdown-value hands
        # prefer nut blockers and live draws; multiway pure bluffs are rare.
        valuecut=.66 if st==1 else .70 if st==2 else .75
        if not hu:valuecut+=.05
        if maniac:valuecut-=.035
        value=eq>valuecut and (made>=2 or (draw>=3 and st<3))
        betfreq=.88 if value else 0.
        if value and made>=6 and not wet and st==1:betfreq=.72
        if not value and st<3:
            if draw>=2 and hu:betfreq=.66 if ownpf or inpos else .38
            elif draw and ownpf and hu:betfreq=.40
            elif made==0 and hu:
                if st==1 and ownpf:betfreq=.50 if not wet else .26
                elif st==2 and (ownpf or inpos):betfreq=.19 if nut or max(RANK[i] for i in h)>=11 else .09
            elif made<2 and st==1 and ownpf and hu and not wet:betfreq=.30
        if not value and st==3 and hu and made==0 and eq<.42:
            # Polar bluff component; ace/king blockers remove strong calls.
            maxsuit=max(sum(c[-1]==su for c in s.board) for su in SUITS)
            blocker=nut or (maxsuit<3 and any(RANK[i]==12 for i in h))
            prev=m['rounds'][2].get(str(s.seat),[''])[0]
            betfreq=.38 if blocker and prev=='raise' else .22 if blocker or prev=='raise' else .13
            if maniac:betfreq*=.25
        if not hu and not value:betfreq*=.18
        folders=all(is_folder(m,p.seat) for p in opp if p.status=='active')
        if folders and any(p.status=='active' for p in opp):
            return finish('raise',me.bet+bb)
        if r<betfreq:
            frac=.33 if st==1 and hu and ownpf and not wet else .60 if st==1 else .67 if st==2 else .75
            if made>=6 and eq>.88:frac=.78 if st<3 else .95
            # Avoid wasting a large bet into an uncalled all-in side pot.
            if not any(p.status=='active' and p.stack>0 for p in opp):return finish('check')
            amount=me.bet+max(bb,pot*frac)
            if value and (amount>=total*.65 or spr<1):amount=total
            if not value and stack<pot*.5:return finish('check')
            return finish('raise',amount)
        return finish('check')
