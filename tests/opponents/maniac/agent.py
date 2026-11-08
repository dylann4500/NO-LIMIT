"""Field proxy: maniac. Jams 95% of hands preflop; bets pot or jams postflop."""
import random
import poker_agent_sdk
from poker_agent_sdk import Action

_rng = random.Random(2)


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        s = state
        try:
            if s.phase == "select":
                return Action("select", cards=(2, 0)), memory
            if s.phase != "betting":
                f = s.legal_actions[0]
                return Action(f.kind, f.min_amount), memory
            r = s.can("raise")
            if not s.board:
                if _rng.random() < 0.95:
                    if r:
                        return Action.raise_to(int(r.max_amount)), memory
                    if s.can("call"):
                        return Action.call(), memory
                return (Action.check() if s.can("check") else Action.fold()), memory
            if r and _rng.random() < 0.5:
                return Action.raise_to(int(r.max_amount)), memory
            return (Action.call() if s.can("call") else Action.check()), memory
        except Exception:
            return (Action.check() if s.can("check") else Action.fold()), memory
