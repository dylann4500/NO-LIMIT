"""Independent SDK-only sparring policies for style diversity, never used by Agent."""
import marshal
import eval7
from poker_agent_sdk import Action
from baseline_v1 import CARDS,CARD_ID,POOLS,FRACS,PCT,OPEN,hand_key,eq_pre,kind

class Rival:
    style='balanced'
    def act(self,s,memory):
        legal={kind(a):a for a in s.legal_actions}
        own=next(t for t in s.seats if t.seat==s.seat)
        bb=s.blinds[1];call=min(s.to_call,own.stack);pot=s.pot
        others=[t for t in s.seats if t.seat!=s.seat and t.status in ('active','all_in')]
        def passive():return Action.check() if 'check' in legal else Action.fold()
        def raise_to(x):
            a=legal['raise'];return Action.raise_to(max(int(a.min_amount),min(int(a.max_amount),int(x))))
        a,b=[CARD_ID[x] for x in s.cards];key=hand_key(a,b)
        seed=(s.hand_number*3812015801+a*73856093+b*19349663+len(s.board)*6871)&0xffffffff
        u=seed/4294967296
        style=self.style
        tight=style=='tight';loose=style=='loose'
        if memory:
            m=marshal.loads(memory)
        else:m={'h':-1,'r':0,'pf':False}
        for e in s.events:
            k=kind(e)
            if k=='hand':m={'h':e.amount,'r':0,'pf':True}
            elif k=='board':m['pf']=False
            elif k=='raise' and m['pf']:m['r']+=1
        mem=marshal.dumps(m)
        if not s.board:
            order=sorted(t.seat for t in s.seats if t.status!='busted')
            bi=order.index(s.button);order=order[bi+1:]+order[:bi+1]
            pos=order.index(s.seat);distance=len(order)-1-pos
            opening=.17 if distance>=4 else .24 if distance==3 else .32 if distance==2 else .48
            if len(order)==2:opening=.85
            opening*=.72 if tight else 1.25 if loose else 1.
            mx=max(t.bet for t in s.seats)
            if mx<=bb:
                if 'raise' in legal and OPEN[key]<opening:
                    size=bb*(2.6 if tight else 2.3)
                    if own.stack<=14*bb:size=own.bet+own.stack
                    return raise_to(size),mem
                if 'check' in legal:return Action.check(),mem
                if loose and OPEN[key]<.70 and call<=bb:return Action.call(),mem
                return passive(),mem
            f=.15 if tight else .30 if loose else .22
            if m['r']>1:f*=.35
            q=eq_pre(key,f)
            v=eq_pre(key,.04 if tight else .12 if loose else .065)
            if 'raise' in legal and v>(.61 if tight else .56):
                return raise_to(own.bet+own.stack if own.stack<25*bb else mx*3.1),mem
            odds=call/max(1,pot+call)
            if q>=odds+(.08 if tight else .015 if loose else .045):return Action.call(),mem
            return passive(),mem
        idx=7 if loose else 4 if tight and m['r'] else 6 if m['r'] else 10
        r=[c[4] for c in POOLS[idx][::max(1,len(POOLS[idx])//180)]]
        h=[CARDS[a],CARDS[b]];board=[CARDS[CARD_ID[x]] for x in s.board]
        q=eval7.py_hand_vs_range_monte_carlo(h,r,board,512)
        q **= 1+.70*max(0,len(others)-1)
        odds=call/max(1,pot+call)
        if call:
            if 'raise' in legal and q>(.85 if tight else .77):
                size=own.bet+call+int((pot+call)*.8)
                if own.stack<=pot*1.3:size=own.bet+own.stack
                return raise_to(size),mem
            if q>=odds+(.065 if tight else .005 if loose else .035):return Action.call(),mem
            return passive(),mem
        if 'raise' in legal:
            value=q>(.69 if tight else .56 if loose else .62)+.04*max(0,len(others)-1)
            bluff=len(others)==1 and u<(.10 if tight else .48 if loose else .26)
            if value or bluff:
                return raise_to(own.bet+max(bb,int(pot*(.75 if loose else .55)))),mem
        return Action.check(),mem

class Tight(Rival):style='tight'
class Balanced(Rival):style='balanced'
class Loose(Rival):style='loose'
