"""Tournament hold'em: range equity, position, adaptation and ICM, within 1 ms."""
import json
import marshal
import math
import os
import itertools
import gc
from time import perf_counter_ns
import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

with open(os.path.join(os.path.dirname(__file__), 'preflop.json')) as _source:
    _DATA = json.load(_source)
EQ = _DATA['equity']
MULTI = _DATA['multi_random']
PCT = _DATA['percentile']
FRAC = _DATA['fractions']
RANKS = '23456789TJQKA'
CARDS = {r+s: eval7.Card(r+s) for r in RANKS for s in 'cdhs'}

def hand_key(a, b):
    if RANKS.index(a[0]) < RANKS.index(b[0]): a, b = b, a
    return a[0]+b[0]+('' if a[0]==b[0] else 's' if a[1]==b[1] else 'o')

_COMBOS = list(itertools.combinations(CARDS.values(), 2))
_COMBOS.sort(key=lambda c: PCT[hand_key(str(c[0]), str(c[1]))])
# Mix suits and adjacent strength classes in each fixed quadrature sample.
def sample_indices(n, k):
    count=min(n,k)
    return [min(n-1, (i*n + n//2)//count) for i in range(count)]
RANGE_COMBOS = []
RANGES = []
FAST_RANGES = []
for f in FRAC:
    cs = _COMBOS[:round(f*1326)]
    RANGE_COMBOS.append(cs)
    hr = eval7.HandRange('')
    hr.hands = [(cs[i], 1.) for i in sample_indices(len(cs), 320)]
    RANGES.append(hr)
    FAST_RANGES.append([hr.hands[i] for i in sample_indices(len(hr.hands),128)])
ALL = RANGES[-1]
WINDOWS = [(31 << i) for i in range(9)] + [0x100F]
DRAWCOUNT = [max((m&w).bit_count() for w in WINDOWS) for m in range(8192)]
SUBSET_SIZE=[m.bit_count() for m in range(128)]
SUBSET_PREV=[(m^(m&-m),(m&-m).bit_length()-1) for m in range(1,128)]
ICM_NEXT=[[[((m|(1<<j)),j) for j in range(n) if not m&(1<<j)]
           for m in range(1<<n)] for n in range(8)]

# Deep-stack opening order emphasizes realizable equity and small-pair implied odds.
_TIERS = [
 'AA KK QQ JJ AKs AKo',
 'TT AQs AQo AJs KQs 99',
 'ATs KJs QJs 88 AJo KQo JTs 77',
 'A9s KTs QTs ATo 66 A8s A5s KJo T9s 55 A4s',
 'A7s A6s K9s Q9s J9s A3s 44 KTo QJo 98s A2s',
 'K8s QTo JTo T8s 33 A9o K7s Q8s 87s A8o K9o J8s 22',
 'K6s A7o Q9o 76s 97s K5s A5o A6o Q7s T9o K8o K4s 65s J7s',
 'K3s A4o T7s Q6s 86s J9o 54s Q8o K2s A3o K7o Q5s 75s T8o J6s A2o',
]
OPEN = {}; _count=0
for tier in _TIERS:
    for k in tier.split():
        n=6 if len(k)==2 else 4 if k[-1]=='s' else 12
        OPEN[k]=(_count+n/2)/1326;_count+=n
for k in _DATA['order']:
    if k not in OPEN:
        n=6 if len(k)==2 else 4 if k[-1]=='s' else 12
        OPEN[k]=(_count+n/2)/1326;_count+=n


def equity_pre(key, fraction):
    row = EQ[key]
    if fraction <= FRAC[0]: return row[0]
    for i in range(1, 9):
        if fraction <= FRAC[i]:
            t=(fraction-FRAC[i-1])/(FRAC[i]-FRAC[i-1])
            return row[i-1]+t*(row[i]-row[i-1])
    return row[-1]


def pre_multi(key, fractions):
    if not fractions:return 1.
    if len(fractions)==1:return equity_pre(key,fractions[0])
    count=min(7,len(fractions))
    raw=MULTI[key][0]
    # Offline joint deals capture the strong correlation of multiway outcomes:
    # e.g. a small pair often wins by making the same set against every player.
    correction=MULTI[key][count-1]/max(.0001,raw**count)
    looseness=sum(min(1.,f/.7) for f in fractions)/len(fractions)
    value=math.prod(equity_pre(key,f) for f in fractions)
    return min(1.,value*correction**(.45+.55*looseness))


def pot_weighted(values, opponents, data, pre_key=None):
    """Prize the main pot and side pots against their eligible opponents."""
    def combine(seats):
        if not seats:return 1.
        vs=[values[x] for x in seats]
        if pre_key:return pre_multi(pre_key,vs)
        vs.sort()
        return vs[0]*math.prod(vs[1:])**.72
    ids=list(values)
    full=combine(ids)
    if not any(p.status=='all_in' for p in opponents):return full
    con=data.get('con',{}).copy()
    hero=data.get('hero')
    if hero is None:return full
    cap=con.get(hero,0)+data.get('call',0)
    if cap<=0:return full
    con[hero]=cap
    levels=sorted(set(min(cap,x) for x in con.values() if x>0))
    weighted=0.;total=0.;prev=0
    for level in levels:
        chips=(level-prev)*sum(c>=level for c in con.values())
        eligible=[p.seat for p in opponents if p.seat in values and
                  (p.status=='active' or con.get(p.seat,0)>=level)]
        weighted+=chips*combine(eligible);total+=chips;prev=level
    return weighted/total if total else full


def kind(k):
    return k.value if hasattr(k, 'value') else k


def new_memory():
    return {'s': {}, 'hand': -1, 'street': 0, 'line': {}, 'rc': [0]*4,
            'last': [-1]*4, 'bet': {}, 'con': {}, 'alive': {}, 'acts': [0]*4}


def update(state, data):
    stats=data['s']
    for p in state.seats:
        if p.seat not in stats: stats[p.seat]=[0]*24
        elif len(stats[p.seat])<24: stats[p.seat].extend([0]*(24-len(stats[p.seat])))
        data['alive'].setdefault(p.seat, True)
    for e in state.events:
        k=kind(e.kind); s=e.seat
        if k=='hand':
            data['hand']=e.amount;data['street']=0
            data['line']={};data['rc']=[0]*4;data['last']=[-1]*4
            data['bet']={};data['con']={};data['acts']=[0]*4
            data['board']=[]
            data['short']=sum(data['alive'].values())<=3
            for seat, alive in data['alive'].items():
                if alive:
                    stats[seat][0]+=1
                    if data['short']: stats[seat][11]+=1
            continue
        if k=='board':
            data['street']=min(3,data['street']+1);data['bet']={}
            data.setdefault('board',[]).extend(e.cards or [])
            continue
        if s is None: continue
        if s not in stats: stats[s]=[0]*24
        st=stats[s]
        street=data['street']
        # [voluntary, preflop raises, preflop raise amount, latest raise number,
        #  streets bet/raised, streets called, streets checked, last action]
        line=data['line'].setdefault(s,[0]*8)
        # Count actual responses to bets, rather than all actions.  Free checks
        # and opening bets are not opportunities to fold to a bet.
        if k in ('fold','call','raise'):
            price=max(data['bet'].values(),default=0)-data['bet'].get(s,0)
            if price>0 and (street or max(data['bet'].values(),default=0)>state.blinds[1]):
                st[16+street*2]+=1
                st[17+street*2]+=int(k=='fold')
        if k=='stack':
            data['alive'][s]=(e.amount>0)
        elif k in ('blind','ante','call','raise'):
            amount=e.amount or 0
            if k=='raise':
                add=max(0, amount-data['bet'].get(s,0));data['bet'][s]=amount
            else:
                add=amount
                if k!='ante': data['bet'][s]=data['bet'].get(s,0)+amount
            data['con'][s]=data['con'].get(s,0)+add
            if k in ('call','raise'):
                if street==0 and not line[0]:
                    st[1]+=1;line[0]=1
                    if data.get('short'):st[12]+=1
                if k=='raise':
                    data['rc'][street]+=1;data['last'][street]=s
                    line[4]|=1<<street
                    if street==0:
                        if not line[1]:
                            st[2]+=1
                            if data.get('short'):st[13]+=1
                        elif amount<12*state.blinds[1]:st[9]+=1
                        line[1]+=1;line[2]=amount;line[3]=data['rc'][0]
                    else: st[3]+=1
                    line[7]=3
                else:
                    line[5]|=1<<street
                    if street: st[4]+=1
                    line[7]=2
                if s==state.seat: data['acts'][street]+=1
        elif k=='fold':
            if street: st[5]+=1
            else: st[8]+=1
            line[7]=0
        elif k=='check':
            if street: st[6]+=1
            line[6]|=1<<street;line[7]=1
            if s==state.seat: data['acts'][street]+=1
        elif k=='show':
            st[7]+=1
            bets=line[4]&14
            if bets and e.cards and len(e.cards)==2:
                ss=bets.bit_length()-1
                public=data.get('board',[])[:ss+2]
                if len(public)>=3:
                    a,b=(CARDS[c] for c in e.cards)
                    q,draw,cat=quality(a,b,board_info([CARDS[c] for c in public]))
                    st[14]+=int(q<.35)
                    st[15]+=1
    return data


def profile(st):
    h=max(1,st[0])
    # A wide heads-up opening range is normal. Repeated small reraises identify
    # the genuinely indiscriminate raiser without confusing the two styles.
    maniac=(st[9]>=5 and st[9]>st[2]*1.1) or (h>=8 and st[2]/h>.78 and st[3]>st[4]+st[6]+5)
    folder=h>=7 and st[1]/h<.055 and st[2]==0
    station=h>=7 and st[1]/h>.55 and st[2]/h<.25
    return maniac,folder,station


def range_fraction(seat, data, n, bb):
    st=data['s'][seat]; h=st[0]
    mani,folder,station=profile(st)
    line=data['line'].get(seat,[0]*8)
    if mani: return 1.
    if line[1]:
        pos=data.get('positions',{}).get(seat,.24)
        if n<=3 and len(st)>=14:
            f=(st[13]+.48*8)/(st[11]+8)*pos/.48
        else:
            f=(st[2]+.21*12)/(h+12)*pos/.24
        # Raising multiple times is strong evidence unless the player is demonstrably wild.
        if line[1]>=2 or line[3]>=3: f*=.30
        elif line[3]==2: f*=.50
        initial=data.get('starting',{}).get(seat,100*bb)
        shortjam=(line[2]>=initial*.8 and initial<=16*bb and line[3]==1)
        if shortjam:
            # A short-stack open shove is a different range from a deep overbet.
            # Round 1 reveals were much wider than the old size discount assumed.
            f=max(f,pos*(.9 if initial<8*bb else .68))
        else:
            if line[2]>7*bb: f*=.6
            if line[2]>16*bb: f*=.65
        return max(.025,min(.65,f))
    if line[0]:
        return max(.16,min(.85,(st[1]+4)/(h+10)*1.35))
    return 1.


def board_info(board):
    ranks=[c.rank for c in board]
    suits=[c.suit for c in board]
    mask=0
    for r in ranks: mask|=1<<r
    top=max(ranks)
    counts=[suits.count(i) for i in range(4)]
    pairs=[r for r in set(ranks) if ranks.count(r)>=2]
    return (board,top,mask,counts,pairs,sorted(set(ranks),reverse=True))


def quality(a,b,info):
    board,top,mask,sc,paired,distinct=info
    val=eval7.evaluate([a,b]+board)
    cat=val>>24; r=(val>>16)&15
    if cat>=4: q=.98
    elif cat==3: q=.94 if (a.rank==r or b.rank==r) else .46
    elif cat==2:
        r2=(val>>12)&15
        if r in paired and r2 in paired: q=.2
        elif r in paired or r2 in paired:
            ownpair=r2 if r in paired else r
            q=.84 if ownpair>top else .77 if ownpair==top else .48
        else: q=.9
    elif cat==1:
        if r in paired: q=.12+.05*((a.rank==12)+(b.rank==12))
        elif r>top: q=.86
        elif r==top: q=.77
        elif len(distinct)>1 and r==distinct[1]: q=.48
        else: q=.28
    else: q=.07+.045*((a.rank>top)+(b.rank>top))
    draw=False
    if len(board)<5:
        if sc[a.suit]+1+(a.suit==b.suit)==4 or sc[b.suit]+1+(a.suit==b.suit)==4:
            q=max(q,.49);draw=True
        union=mask|(1<<a.rank)|(1<<b.rank)
        if DRAWCOUNT[union]==4 and union!=mask:
            q=max(q,.35);draw=True
    return q,draw,cat


def range_index(frac):
    return min(range(9),key=lambda i:abs(FRAC[i]-frac))


def fold_probability(seat,data,street):
    """Shrunk, anonymous per-table response model, fitted to round 1 frequencies."""
    prior=(.74,.59,.60,.73)[street]
    st=data['s'][seat]
    if profile(st)[0] or profile(st)[2]:prior=.20
    if profile(st)[1]:prior=.96
    if len(st)<24:return prior
    return (st[17+street*2]+prior*10)/(st[16+street*2]+10)


def post_equity(cards, board, opponents, data, n, bb, seed, deadline):
    # Condition the most threatening opponent on public actions; account for the
    # rest using their individually estimated unconditional showdown equity.
    street=len(board)-2
    threat=[]
    for p in opponents:
        line=data['line'].get(p.seat,[0]*8)
        st=data['s'][p.seat]
        mani=profile(st)[0]
        frac=range_fraction(p.seat,data,n,bb)
        signal=0;sigstreet=0
        if not mani:
            for ss in range(1,street+1):
                if line[4]&(1<<ss): signal=2;sigstreet=ss
                elif line[5]&(1<<ss): signal=1;sigstreet=ss
            if line[6]&(1<<street) and line[7]==1 and not line[4]&(1<<street):
                signal=3;sigstreet=street
        priority=(3 if p.bet>0 else 0)+signal*2+(1-frac)
        threat.append((priority,p,frac,signal,sigstreet))
    threat.sort(key=lambda x:x[0],reverse=True)
    _,main,frac,signal,sigstreet=threat[0]
    ix=range_index(frac)
    fast=data.get('fast',False)
    emergency=data.get('emergency',False)
    hr=FAST_RANGES[ix] if fast else RANGES[ix]
    if signal:
        cs=RANGE_COMBOS[ix]
        inf=board_info(board[:sigstreet+2])
        stats=data['s'][main.seat]
        aggression=(stats[3]+2)/(stats[3]+stats[4]+stats[6]+6)
        airscale=max(.4,min(2.,aggression/.36))
        if len(stats)>15:airscale*=max(.3,min(2.5,(stats[14]+1)/(stats[15]+5)*5))
        if len(opponents)>1:airscale*=.65
        multiple=sigstreet==street and data['rc'][street]>1
        large=(sigstreet==street and main.bet>bb and
               main.bet>sum(p.bet for p in opponents)*.65 and
               main.bet>data.get('pot',1)*.32)
        known=0
        for c in cards+board: known|=c.mask
        candidates=[];cumulative=[];totalweight=0.
        prior_call=(signal==3 and sigstreet>1 and
                    bool(data['line'].get(main.seat,[0]*8)[5]&(1<<(sigstreet-1))))
        previnfo=board_info(board[:sigstreet+1]) if prior_call else None
        count=min(16 if emergency else 32 if fast else 88 if frac<.18 else 72,len(cs));offset=seed%len(cs)
        for j in range(count):
            if j%16==0 and j>=32 and perf_counter_ns()>deadline:break
            pair=cs[((j*len(cs))//count+offset)%len(cs)]
            a,b=pair
            if (a.mask|b.mask)&known: continue
            q,draw,cat=quality(a,b,inf)
            if signal==2:
                w=10 if q>=.9 else 7 if q>=.7 else 4 if q>=.45 else 2 if q>=.3 else 1
                if sigstreet==3: w=14 if q>=.9 else 5 if q>=.7 else 2 if q>=.45 else 1
                # Multiple bets on a street normally represent a polarized range.
                if multiple:
                    w=20 if q>=.9 else 5 if q>=.75 else 2 if draw else 1
                elif large:
                    # Large bets carry stronger evidence than routine continuation bets.
                    w=20 if q>=.9 else 6 if q>=.75 else 2 if draw else 1
            elif signal==3:
                # Checking caps a range, especially after two opportunities to
                # value bet. Retain traps instead of deleting strong hands.
                w=.45 if q>=.9 else .65 if q>=.7 else 1.1 if q>=.4 else 1.4
                if prior_call:
                    pq,pdraw,pcat=quality(a,b,previnfo)
                    w*=2.3 if pq>=.7 else 1.8 if pq>=.4 else 1.
            else: w=7 if q>=.7 else 5 if q>=.4 else 2 if q>=.25 else 1
            if q<.3 and signal!=3:w*=airscale if signal==2 else .55
            candidates.append(pair);totalweight+=w;cumulative.append(totalweight)
        if candidates:
            hands=[];j=0;last=len(cumulative)-1
            # eval7 ignores input weights, so explicitly resample the posterior.
            start=(seed%997)/997
            particles=64 if emergency else 160
            for i in range(particles):
                target=(i+start)*totalweight/particles
                while j<last and cumulative[j]<target:j+=1
                hands.append((candidates[j],1.))
            hr=hands
    eq=(eval7.py_hand_vs_range_exact(cards,hr,board) if len(board)==5 else
        eval7.py_hand_vs_range_monte_carlo(cards,hr,board,160 if emergency else 320 if fast else 640))
    equities={main.seat:eq}
    # Equity against additional players is correlated through the runout.
    # A fractional exponent avoids the excessive pessimism of independence.
    for _,p,f,sg,ss in threat[1:]:
        other=FAST_RANGES[range_index(f)]
        eq_other=(eval7.py_hand_vs_range_exact(cards,other,board) if len(board)==5 else
                  eval7.py_hand_vs_range_monte_carlo(cards,other,board,80 if emergency else 160))
        equities[p.seat]=max(.001,eq_other)
    return max(0.,min(1.,pot_weighted(equities,opponents,data)))


def icm(hero, stacks, payouts):
    """Exact prize equity for the paid finishing positions (up to eight players)."""
    total=sum(stacks)
    if total<=0:return 0.
    hs=stacks[hero]
    others=[x for i,x in enumerate(stacks) if i!=hero and x>0]
    if hs<=0:
        return sum(payouts[len(others):len(stacks)])/max(1,len(stacks)-len(others))
    positive=[i for i,p in enumerate(payouts[:len(others)+1]) if p]
    if not positive:return 0.
    last=max(positive)
    if all(p==payouts[0] for p in payouts[:len(others)+1]):return payouts[0]
    first=hs/total
    if last<=2:
        result=payouts[0]*first
        if last>=1:
            second=0.;third=0.
            for i,x in enumerate(others):
                factor=x/(total-x)
                second+=factor
                if last==2:
                    third+=factor*sum(y/(total-x-y) for j,y in enumerate(others) if j!=i)
            result+=payouts[1]*first*second
            if last==2:result+=payouts[2]*first*third
        return result
    # Subset dynamic programming also supports rounds with different payouts.
    n=len(others);length=1<<n
    removed=[0.]*length;prob=[0.]*length;prob[0]=1.
    for mask in range(1,length):
        prev,j=SUBSET_PREV[mask-1]
        removed[mask]=removed[prev]+others[j]
    result=0.
    for mask in range(length):
        place=SUBSET_SIZE[mask]
        if place>last:continue
        left=total-removed[mask];factor=prob[mask]/left
        result+=payouts[place]*factor*hs
        if place<last:
            for nxt,j in ICM_NEXT[n][mask]:prob[nxt]+=factor*others[j]
    return result


def call_threshold(state, me, opponents, pot, call):
    odds=call/max(1,pot+call)
    if len(opponents)!=1 or call<me.stack*.28:return odds
    if state.players_remaining<=2 or sum(x>0 for x in (state.config.payouts or [50,30,20]))==1:return odds
    villain=opponents[0]
    seats=[p for p in state.seats if p.status!='busted' and (p.stack>0 or p.seat==me.seat or p.seat==villain.seat)]
    stacks=[p.stack for p in seats];hero=next(i for i,p in enumerate(seats) if p.seat==me.seat)
    vi=next(i for i,p in enumerate(seats) if p.seat==villain.seat)
    payouts=list(state.config.payouts or [50,30,20])
    payouts=(payouts+[0]*len(seats))[:len(seats)]
    fold=stacks[:];fold[vi]+=pot
    lose=stacks[:];lose[hero]-=call;lose[vi]+=pot+call
    win=stacks[:];win[hero]+=pot
    uf=icm(hero,fold,payouts);ul=icm(hero,lose,payouts);uw=icm(hero,win,payouts)
    return max(odds,min(.9,(uf-ul)/max(1e-9,uw-ul)))


def legalize(state, desired, amount=0):
    legal={kind(x.kind):x for x in state.legal_actions}
    if desired=='raise' and 'raise' in legal:
        r=legal['raise'];v=max(int(r.min_amount),min(int(r.max_amount),int(amount)))
        return Action.raise_to(v)
    if desired in legal:
        if desired=='check':return Action.check()
        if desired=='call':return Action.call()
        if desired=='fold':return Action.fold()
    if 'check' in legal:return Action.check()
    if 'fold' in legal:return Action.fold()
    if 'call' in legal:return Action.call()
    r=legal['raise'];return Action.raise_to(int(r.min_amount))


class Agent(poker_agent_sdk.Agent):
    def act(self,state,memory):
        started=perf_counter_ns()
        collecting=gc.isenabled()
        if collecting:gc.disable()
        try:
            try:data=marshal.loads(memory) if memory else new_memory()
            except (ValueError,EOFError,TypeError):data=new_memory()
            update(state,data)
            action,amount=self.decide(state,data,started)
            return legalize(state,action,amount),marshal.dumps(data)
        finally:
            if collecting:gc.enable()

    def decide(self,s,d,started):
        me=next(p for p in s.seats if p.seat==s.seat)
        opp=[p for p in s.seats if p.seat!=s.seat and p.status in ('active','all_in')]
        if not opp:return 'check',0
        live=[p for p in s.seats if p.status!='busted' and (p.stack>0 or p.status=='all_in')]
        n=len(live);bb=max(1,s.blinds[1]);stack=me.stack
        call=min(stack,max(0,s.to_call));pot=max(1,s.pot)
        legal={kind(a.kind):a for a in s.legal_actions}
        order=sorted(p.seat for p in live)
        bi=order.index(s.button) if s.button in order else 0
        order=order[bi+1:]+order[:bi+1]
        pre=order[-1:]+order[:-1] if n==2 else order[2:]+order[:2]
        widths=[.75,.56,.43,.31,.245,.205,.175,.15]
        d['positions']={seat:widths[min(7,n-i-1)] for i,seat in enumerate(pre)}
        if pre:d['positions'][pre[-1]]=.25
        d['pot']=pot
        d['starting']={p.seat:p.stack+d['con'].get(p.seat,p.bet) for p in s.seats}
        d['fast']=(s.time_bank_ms is not None and s.time_bank_ms<15)
        d['emergency']=(s.time_bank_ms is not None and s.time_bank_ms<7)
        paid=sum(x>0 for x in (s.config.payouts or [50,30,20]))
        bubble=(n==paid+1 and paid>1)
        own=d['line'].get(s.seat,[0]*8)
        key=hand_key(*s.cards)
        # Stable randomization is independent of process identity and other tables.
        seed=(s.hand_number*193+sum(CARDS[x].rank*31+CARDS[x].suit*7 for x in s.cards)+len(s.board)*73+s.seat*47+d['acts'][d['street']]*29)
        rnd=(seed*2654435761&65535)/65536
        profiles={p.seat:profile(d['s'][p.seat]) for p in opp}
        active=[p for p in opp if p.status=='active']
        seating=sorted(p.seat for p in s.seats)
        bi=seating.index(s.button) if s.button in seating else 0
        post=seating[bi+1:]+seating[:bi+1]
        inpos=not any(post.index(p.seat)>post.index(s.seat) for p in active)
        eff=min(stack,max(p.stack+p.bet for p in opp))
        # A short all-in blind can leave a nominal call above the contestable
        # amount. Unmatched chips come back: never surrender a free showdown.
        owncon=d['con'].get(s.seat,me.bet)
        if not active:
            contest=max(d['con'].get(p.seat,p.bet) for p in opp)
            call=min(call,max(0,contest-owncon))
            if call==0:return ('call' if 'call' in legal else 'check'),0
        if call>=stack and stack>0:
            cap=owncon+call
            pot=max(1,pot-sum(max(0,c-cap) for c in d['con'].values()))
        d['hero']=s.seat;d['call']=call
        if not s.board:
            ranks=sorted([RANKS.index(x[0]) for x in s.cards],reverse=True)
            pair=ranks[0]==ranks[1];suited=s.cards[0][1]==s.cards[1][1]
            # Clockwise action order, with the heads-up button acting first.
            behind=sum(1 for x in pre[pre.index(s.seat)+1:] if any(p.seat==x for p in active)) if s.seat in pre else len(active)
            raisers=[p for p in opp if d['line'].get(p.seat,[0]*8)[1]]
            limpers=[p for p in opp if d['line'].get(p.seat,[0]*8)[0] and not d['line'].get(p.seat,[0]*8)[1]]
            if not active:
                eq=pot_weighted({p.seat:range_fraction(p.seat,d,n,bb) for p in opp},opp,d,key)
                threshold=call_threshold(s,me,opp,pot,call)
                return ('call' if eq>=threshold+.012 else 'fold'),0
            if not raisers and d['rc'][0]==0:
                width=[.8,.60,.44,.32,.25,.21,.18,.155][min(7,behind)]
                if n==2:width=.82 if s.seat==s.button else .65
                if limpers:width=min(width*.78,.32/(1+.25*(len(limpers)-1)))
                folders=sum(profiles[p.seat][1] for p in active)
                maniacs=sum(profiles[p.seat][0] for p in active)
                if active and folders==len(active): width=1.
                elif folders:width=min(.95,width+.12*folders)
                if maniacs:width*=.8
                # The field releases its blinds frequently. Widen late steals
                # when the observed players behind us confirm that tendency.
                if not limpers and behind<=3 and n>2:
                    release=math.prod(fold_probability(p.seat,d,0) for p in active)
                    if release>.39:width=min(.9,width+.10)
                    if release>.58:width=min(.98,width+.12)
                if eff<12*bb:
                    # Push/fold: estimate fold equity and prize-adjusted showdown value.
                    foldprob=1.;eq=equity_pre(key,.16)
                    eqn=0.;callmass=0.;sum_cf=0.
                    for p in active:
                        mani,folder,station=profiles[p.seat]
                        cf=1. if mani else .015 if folder else min(.48,.10+bb/max(bb,min(stack,p.stack))*.9)
                        cf*=.8 if bubble else 1.
                        foldprob*=1-cf
                        eqn+=cf*equity_pre(key,1. if mani else max(.06,cf))
                        callmass+=cf
                        sum_cf+=cf
                    if callmass:eq=eqn/callmass
                    conditional=sum_cf/max(.001,1-foldprob)
                    if conditional>1.05:
                        row=MULTI[key];lo=min(6,max(0,int(conditional)-1));hi=min(6,lo+1)
                        frac=conditional-int(conditional)
                        joint=row[lo]*(1-frac)+row[hi]*frac
                        eq*=joint/max(.01,row[0])
                    risk=.04 if bubble else .02
                    ev=foldprob*pot+(1-foldprob)*(eq*(pot+eff)-(1-eq)*eff)
                    shortwidth=width*(1.05 if eff<7*bb else .88)
                    if 'raise' in legal and (ev>eff*risk and (OPEN[key]<shortwidth or eff<5*bb)):
                        return 'raise',me.bet+stack
                    if call==0:return 'check',0
                    return 'fold',0
                if OPEN[key]<width and 'raise' in legal:
                    amount=max(bb*2.2,legal['raise'].min_amount)+len(limpers)*bb
                    if maniacs and equity_pre(key,1.)>.6 and OPEN[key]<.20:
                        amount=max(amount,bb*5)
                    return 'raise',me.bet+stack if amount>stack*.37 else amount
                # Limp behind small pairs and suited connectors when speculative cost is tiny.
                if limpers and eff>20*bb and call<=bb and ((pair and eff>18*call) or (suited and ranks[0]-ranks[1]<=2 and ranks[0]>=5)):
                    return 'call',0
                return ('check' if call==0 else 'fold'),0
            # Raised pot. Use the actual raiser, with posterior range and price.
            main=max(raisers or opp,key=lambda p:(p.bet,d['line'].get(p.seat,[0]*8)[3]))
            frac=range_fraction(main.seat,d,n,bb)
            eq=equity_pre(key,frac)
            committed=[p for p in opp if p.status=='all_in' or p.bet>=max(bb*1.5,me.bet+call)]
            # Additional callers matter most in all-in pots.
            multi=max(0,len(committed)-1)
            factors={main.seat:frac}
            factors.update({p.seat:range_fraction(p.seat,d,n,bb) for p in committed if p.seat!=main.seat})
            eqmulti=pot_weighted(factors,opp,d,key)
            odds=call_threshold(s,me,opp,pot,call)
            rcount=d['rc'][0]
            mani=profiles[main.seat][0]
            strong=eq>.60 and (PCT[key]<.09 or mani)
            if rcount>=2 and not mani:strong=eq>.57 and PCT[key]<.018
            if multi:strong=strong and eqmulti>.49
            if strong and 'raise' in legal:
                amount=max(legal['raise'].min_amount,(me.bet+call)*(2.7 if inpos else 3.2)+len(limpers)*bb)
                if eff<=17*bb or (mani and eqmulti>.58) or amount>stack*.36:
                    amount=me.bet+stack
                return 'raise',amount
            realization=.94 if inpos else .82
            if suited or pair:realization+=.04
            if eff<=call*1.5:realization=1.
            premium=.035 if bubble else .015
            # Avoid stacking off deep with a marginal range edge; defend cheap prices.
            if eqmulti*realization>odds+premium and (call<=4*bb or eqmulti>odds+.055 or call>=stack):
                return 'call',0
            if pair and rcount==1 and call<=4*bb and eff>=call*17 and len(opp)<=4:
                return 'call',0
            return ('check' if call==0 else 'fold'),0

        cards=[CARDS[x] for x in s.cards];board=[CARDS[x] for x in s.board]
        if len(board)==5:
            bv=eval7.evaluate(board);bc=bv>>24;br=(bv>>16)&15;bk=(bv>>12)&15
            if (bc==8 and br==12) or (bc==7 and bk==(11 if br==12 else 12)):
                return ('call' if 'call' in legal else 'check'),0
        # The work cap is measured on the machine actually answering the turn.
        # This automatically reduces sampling on a slower tournament worker.
        limit=max(50000,int((s.config.decision_ms or 1)*1e6*(.18 if d['fast'] else .40)))
        eq=post_equity(cards,board,opp,d,n,bb,seed,started+limit)
        info=board_info(board)
        q,draw,cat=quality(cards[0],cards[1],info)
        street=len(board)-2
        folders=bool(active) and all(profiles[p.seat][1] for p in active)
        maniac=any(profiles[p.seat][0] for p in opp)
        station=any(profiles[p.seat][2] for p in opp)
        ownraise=bool(own[4]&(1<<street))
        if call==0:
            if 'raise' not in legal:return 'check',0
            if folders and not any(p.status=='all_in' for p in opp):return 'raise',legal['raise'].min_amount
            value=eq>(.62 if len(opp)>1 else .65)
            # On the river, use thinner value with strong top pair against a caller.
            if street==3:value=eq>(.64 if len(opp)>1 else .61) and q>.36
            release=math.prod(fold_probability(p.seat,d,street) for p in active) if active else 0.
            dry=max(info[3])<3 and not (info[2].bit_count()>=3 and DRAWCOUNT[info[2]]>=4)
            cbet=(street==1 and own[1] and len(opp)==1 and not station and
                  (eq>.42 or (release>.48 and (dry or draw) and rnd<.72)))
            probe=(street<3 and len(opp)==1 and inpos and not station and not maniac and
                   (eq>.40 and rnd<.48 or release>.53 and eq>.15 and rnd<.58 and not ownraise))
            semibluff=street<3 and draw and eq>.32 and len(opp)<=2 and rnd<.60
            bluff=(street==3 and len(opp)<=2 and inpos and not station and not maniac and
                   not any(p.status=='all_in' for p in opp) and eq<.36 and release>.48 and
                   rnd<(.76 if len(opp)==1 else .40))
            if value or cbet or probe or semibluff or bluff:
                size=(.70 if q>=.85 else .55) if value else .52 if cbet else .55
                if value and eq>.84:size=.92
                if street==3 and value:size=.78 if eq<.86 else 1.
                amount=me.bet+max(bb,pot*size)
                if value and ((eff<pot*(1.4 if q>=.85 else .8) and eq>.74) or (maniac and eq>.80)):
                    amount=me.bet+stack
                elif value and amount>stack*.65 and eq>.79:amount=me.bet+stack
                return 'raise',amount
            return 'check',0
        threshold=call_threshold(s,me,opp,pot,call)
        # Preserve equity realization on tiny bets; require a margin on large uncertain calls.
        margin=.025 if street<3 else .018
        if call>pot*.7:margin+=.025
        if bubble and call>stack*.35:margin+=.015
        if street<3 and len(opp)>1:margin+=.02
        if 'raise' in legal:
            value=eq>(.83 if ownraise else .77)
            if street==3:value=eq>.85
            if value and (q>.85 or eq>.91):
                amount=me.bet+call+max(bb,(pot+call)*.78)
                if street==3 and eq>.95:amount=me.bet+call+(pot+call)*1.15
                if eff<pot*2 or amount>stack*.43 or (maniac and eq>.69): amount=me.bet+stack
                return 'raise',amount
            if draw and street<3 and len(opp)==1 and not ownraise and not station and not maniac and eq>.46 and rnd<.13:
                return 'raise',me.bet+call+(pot+call)*.8
        if eq>=threshold+margin:return 'call',0
        return 'fold',0


# Clean up temporary range-parser graphs before the host forks its workers.
gc.collect()
