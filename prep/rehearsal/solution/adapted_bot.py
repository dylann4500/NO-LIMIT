"""Worked adapter: rebuilds the reference policy's inputs from the mock kit's minimal state.
Rewrite this one file for the real kit. The policy itself should not change."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reference_bot"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
from agent import Agent
import bot as ref

RK, SU = "23456789TJQKA", "shdc"
CARD = {r + s: i * 4 + j for i, r in enumerate(RK) for j, s in enumerate(SU)}
STREET = {"preflop": 0, "flop": 1, "turn": 2, "river": 3}
KIND = {"fold": 0, "check": 1, "call": 1, "raise": 2}


class MyAgent(Agent):
    def __init__(self):
        self.p = ref.Policy()
        self.last_hand, self.seen = -1, 0

    def hand_over(self, hist):
        # Only used if the kit reveals the actions that followed our last decision.
        for ev in hist[self.seen:]:
            if ev["action"] in KIND:
                self.p.observe(ev["seat"], STREET[ev["street"]], KIND[ev["action"]])
        self.seen = len(hist)

    def get_action(self, s):
        p = self.p
        leg = s["legal"]
        try:
            if s["hand_id"] != self.last_hand:
                p.end_hand()
                self.last_hand, self.seen = s["hand_id"], 0
            h = s["history"]
            for ev in h[self.seen:]:
                if ev["action"] in KIND:
                    p.observe(ev["seat"], STREET[ev["street"]], KIND[ev["action"]])
            self.seen = len(h)
            o = ref.State()
            pl = s["players"]
            me = s["my_seat"]
            street = s["street"]
            o.seat = me
            o.hole = [CARD[c] for c in s["hole"]]
            o.board = [CARD[c] for c in s["community"]]
            o.street = STREET[street]
            o.pot = s["pot"]
            o.to_call = leg["call_cost"]
            o.stack = pl[me]["chips"]
            o.bet = pl[me]["street_bet"]
            o.sb, o.bb = s["small_blind"], s["big_blind"]
            o.stacks = [x["chips"] for x in pl]
            o.bets = [x["street_bet"] for x in pl]
            o.in_hand = [x["status"] in ("active", "allin") for x in pl]
            # Not max(bets): a big blind all-in for less still sets the full amount to call.
            o.cur = max(max(o.bets), o.bet + o.to_call)
            o.can_raise = leg["raise_by_min"] is not None
            o.max_raise_to = o.bet + o.stack
            o.min_raise_to = o.cur + (leg["raise_by_min"] or 0)
            o.n_alive = sum(1 for x in pl if x["status"] != "out")
            o.n_live = sum(o.in_hand)
            this = [e for e in h if e["street"] == street]
            acted = {e["seat"] for e in this if e["action"] in KIND}
            o.n_behind = sum(1 for x in pl if x["seat"] != me and x["status"] == "active" and (x["seat"] not in acted or x["street_bet"] < o.cur))
            raises = [e for e in this if e["action"] == "raise"]
            o.raises = len(raises)
            o.aggressor = raises[-1]["seat"] if raises else -1
            last = this.index(raises[-1]) if raises else -1
            o.n_callers = sum(1 for e in this[last + 1:] if e["action"] == "call")
            k, a = p.safe_decide(o)
            if k == 2:
                return {"action": "raise", "by": int(a) - o.cur}
            if k == 1:
                return {"action": "check"} if leg["can_check"] else {"action": "call"}
            return {"action": "fold"}
        except Exception:
            return {"action": "check"} if leg["can_check"] else {"action": "fold"}
