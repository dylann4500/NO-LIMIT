import sys
sys.argv = sys.argv[:1]
import sim
from sim import *
me_cls = sim.load_agent(sim.BOT, "me_agent")
A = sys.modules["me_agent"]
ag = me_cls()
E = Event
def mkstate(n_alive, me, btn, sb, bb, stacks, hist, cards, to_call, pot, legal, bets, status=None, bl=(50,100)):
    seats = []
    for i in range(8):
        if i < n_alive:
            seats.append(Seat(i, stacks[i], bets.get(i,0), (status or {}).get(i, "active")))
        else:
            seats.append(Seat(i, 0, 0, "busted"))
    cfg = Config(table_id="x", seat=me, variant="holdem", players=8, starting_stack=2000, blinds=SCHEDULE, hands_per_level=20, hand_cap=250, payouts=PAYOUTS, decision_ms=1, time_bank_ms=100, memory_bytes=65536)
    return State(seat=me, cards=cards, board=[], pot=pot, to_call=to_call, legal_actions=legal, history=hist, phase="betting", seats=seats, button=btn, blind_level=5, blinds=list(bl), hands_until_next_level=5, hand_number=100, players_remaining=n_alive, bust_order=[], config=cfg, time_bank_ms=100, events=[])
def classes():
    out = []
    for c in A._CLASSES:
        if len(c) == 2: out.append((c, [c[0]+"s", c[1]+"h"]))
        elif c[2] == "s": out.append((c, [c[0]+"s", c[1]+"s"]))
        else: out.append((c, [c[0]+"s", c[1]+"h"]))
    return out
def frac(acts):
    tot = sum(A._NCOMBO[A._CIDX[c]] for c, a in acts if a)
    return tot / 1326.0
def sb_push(bbs, n_alive=2, others=None):
    # HU: seat0 = button/SB, seat1 = BB
    acts = []
    for c, cards in classes():
        st0 = bbs*100
        stacks = [st0-50, st0-100] + ([4000]*(n_alive-2))
        hist = [E("hand",None,100), E("blind",0,50), E("blind",1,100)]
        legal = [LegalAction(ActionKind.FOLD), LegalAction(ActionKind.CALL), LegalAction(ActionKind.RAISE, 200, st0)]
        st = mkstate(n_alive, 0, 0, 0, 1, stacks, hist, cards, 50, 150, legal, {0:50,1:100})
        a, m = ag.act(st, b"")
        acts.append((c, a.kind.value == "raise" and a.amount >= st0*0.9))
    return acts
def bb_call(bbs, n_alive=2):
    acts = []
    for c, cards in classes():
        st0 = bbs*100
        stacks = [0, st0-100] + ([4000]*(n_alive-2))
        hist = [E("hand",None,100), E("blind",0,50), E("blind",1,100), E("raise",0,st0)]
        legal = [LegalAction(ActionKind.FOLD), LegalAction(ActionKind.CALL)]
        st = mkstate(n_alive, 1, 0, 0, 1, stacks, hist, cards, st0-100, st0+100, legal, {0:st0,1:100}, status={0:"all_in"})
        a, m = ag.act(st, b"")
        acts.append((c, a.kind.value == "call"))
    return acts
for b in (5, 10, 15, 20):
    p = sb_push(b); c = bb_call(b)
    print("HU %2dBB: SB pushes %.0f%%  BB calls %.0f%%" % (b, 100*frac(p), 100*frac(c)), " push-fold edge:", [x for x,a in p if not a][:6], " calls:", [x for x,a in c if a][-6:])
for b in (8, 12):
    p = sb_push(b, n_alive=4)
    print("4-handed (bubble) SB vs BB %dBB pushes %.0f%%" % (b, 100*frac(p)))
