"""Field proxy: calling station. Calls bets with pair+ or a draw (~45% folds), rarely raises."""
import random
import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

R = "23456789TJQKA"
_rng = random.Random(1)


def _cat(cards):
    return eval7.evaluate([eval7.Card(c) for c in cards]) >> 24


def _made_or_draw(hole, board):
    cat = _cat(list(hole) + list(board))
    bcat = _cat(list(board)) if len(board) >= 5 else (1 if len({c[0] for c in board}) < len(board) else 0)
    if cat > bcat:
        return True, cat
    if len(board) < 5:
        suits = {}
        for c in list(hole) + list(board):
            suits[c[1]] = suits.get(c[1], 0) + 1
        if max(suits.values()) >= 4:
            return True, cat
        rk = sorted({R.index(c[0]) for c in list(hole) + list(board)})
        for lo in range(0, 10):
            if sum(1 for r in range(lo, lo + 5) if r in rk) >= 4:
                return True, cat
    return False, cat


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        try:
            return self._act(state), memory
        except Exception:
            if state.phase == "select":
                return Action("select", cards=(2, 0)), memory
            return (Action.check() if state.can("check") else Action.fold()), memory

    def _act(self, s):
        if s.phase == "select":
            return Action("select", cards=(2, 0))
        if s.phase != "betting":
            f = s.legal_actions[0]
            return Action(f.kind, f.min_amount)
        me = next(x for x in s.seats if x.seat == s.seat)
        if not s.board:
            if s.to_call == 0:
                return Action.check()
            ranks = sorted((R.index(c[0]) for c in s.cards), reverse=True)
            ok = len(set(ranks)) < 3 or ranks[0] >= 12 or ranks[1] >= 8
            if (ok or s.to_call <= 2 * s.blinds.big_blind) and s.to_call <= 0.25 * (me.stack + me.bet) and s.can("call"):
                return Action.call()
            return Action.fold()
        good, cat = _made_or_draw(s.cards, s.board)
        r = s.can("raise")
        if s.to_call > 0:
            if cat >= 2 and r and _rng.random() < 0.08:
                return Action.raise_to(int(r.min_amount))
            if good and s.can("call"):
                return Action.call()
            return Action.fold()
        if cat >= 2 and r and _rng.random() < 0.5:
            return Action.raise_to(max(int(r.min_amount), min(int(r.max_amount), int(s.pot // 2))))
        return Action.check()
