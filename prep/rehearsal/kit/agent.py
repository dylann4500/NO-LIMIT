"""Mock starter kit for rehearsal. NOT the official interface, which is unknown until kickoff.
It is deliberately awkward so wiring practice is realistic.

Implement:
    class MyAgent(Agent):
        def reset(self, seat, n_players): ...       # called at the start of each table
        def get_action(self, state): ...            # must return within 1 ms

state is a dict:
    hand_id, street ("preflop" | "flop" | "turn" | "river"), my_seat, dealer_seat, small_blind, big_blind
    hole:       card strings, e.g. ["As", "Td"]
    community:  card strings
    players:    list by seat: {"seat", "chips", "street_bet", "status"}
                chips EXCLUDES street_bet; status: "active", "allin", "folded", "out"
    pot:        all chips committed this hand, including street bets
    legal:      {"can_check": bool, "call_cost": int, "raise_by_min": int or None, "raise_by_max": int or None}
    history:    this hand only, oldest first: {"street", "seat", "action", "amount"}
                action: "sb", "bb", "fold", "check", "call", "raise"

Return a dict:
    {"action": "fold"} | {"action": "check"} | {"action": "call"}
    {"action": "raise", "by": N}  # chips ABOVE the call, on top of matching the current bet
Anything illegal, any exception, or any overrun counts as check-else-fold.
"""


class Agent:
    def reset(self, seat, n_players):
        pass

    def get_action(self, state):
        raise NotImplementedError
