import sys, os, enum
from types import SimpleNamespace as NS
os.environ["CDD_DEBUG"] = "1"
sys.argv = sys.argv[:1]
import sim
me_cls = sim.load_agent(sim.BOT, "me_agent")
class K(enum.Enum):
    FOLD="fold"; CHECK="check"; CALL="call"; RAISE="raise"
class St(enum.Enum):
    ACTIVE="active"; FOLDED="folded"; ALL_IN="all_in"; BUSTED="busted"
def run(cards, board, hist, legal, to_call, pot, seats):
    st = NS(seat=2, cards=cards, board=board, pot=pot, to_call=to_call, legal_actions=legal, history=hist, phase="betting",
            seats=seats, button=0, blind_level=1, blinds=[10,20], hands_until_next_level=19, hand_number=1, players_remaining=4,
            bust_order=[], config=NS(payouts=[50,30,20,0], decision_ms=1, time_bank_ms=100), time_bank_ms=100, events=hist, variant="holdem")
    return me_cls().act(st, b"")
# dict seats/events, enum kinds and statuses, string legal kinds
seats = [dict(seat=i, stack=1980 if i!=2 else 2000, bet=(10 if i==1 else 20 if i==2 else 0), status=St.ACTIVE, shown_cards=[]) for i in range(4)]
seats[2]["bet"] = 0; seats[2]["stack"]=2000
seats[1]["bet"]=10; seats[0]["bet"]=0
hist = [dict(kind=K.FOLD if False else "hand", seat=None, amount=1, cards=None), dict(kind="blind", seat=1, amount=10, cards=None), dict(kind="blind", seat=3, amount=20, cards=None)]
seats[3]["bet"]=20
legal = [NS(kind="fold", min_amount=0, max_amount=0), NS(kind="call", min_amount=0, max_amount=0), NS(kind="raise", min_amount=40, max_amount=2000)]
print("dict/str:", run(["Ah","Ad"], [], hist, legal, 20, 30, seats)[0])
hist2 = [NS(kind=K.CALL if False else K.FOLD, seat=0, amount=None, cards=None)]
legal2 = [NS(kind=K.FOLD, min_amount=0, max_amount=0), NS(kind=K.CALL, min_amount=0, max_amount=0), NS(kind=K.RAISE, min_amount=40, max_amount=2000)]
print("enum events:", run(["Ah","Ad"], [], hist + hist2, legal2, 20, 30, seats)[0])
