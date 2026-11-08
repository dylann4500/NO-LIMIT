"""Field proxy: tight-aggressive. Opens ~top 20%, bets made hands, folds weak hands to bets."""
from itertools import combinations
import eval7
import poker_agent_sdk
from poker_agent_sdk import Action

R = "23456789TJQKA"


def _pre(cards):
    """(open, premium) on the best 2-card subset."""
    op = prem = False
    for a, b in combinations(cards, 2):
        ra, rb = R.index(a[0]), R.index(b[0])
        hi, lo = max(ra, rb), min(ra, rb)
        if ra == rb and ra >= 6:
            op = True
            prem |= ra >= 9
        if hi == 12 and lo >= 9:
            op = True
            prem |= lo >= 11
        if hi == 11 and lo >= 10:
            op = True
        if hi == 12 and a[1] == b[1] and lo >= 8:
            op = True
    return op, prem


def _toppair(hole, board):
    v = eval7.evaluate([eval7.Card(c) for c in list(hole) + list(board)])
    cat = v >> 24
    if cat >= 2:
        bc = {}
        for c in board:
            bc[c[0]] = bc.get(c[0], 0) + 1
        return max(bc.values()) < 2 or cat >= 3
    if cat == 1:
        top = max(R.index(c[0]) for c in board)
        hr = [R.index(c[0]) for c in hole]
        br = [R.index(c[0]) for c in board]
        return any(r == top and r in br for r in hr) or (hr[0] == hr[-1] and hr[0] > top)
    return False


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        s = state
        try:
            return self._act(s), memory
        except Exception:
            if s.phase == "select":
                return Action("select", cards=(2, 0)), memory
            return (Action.check() if s.can("check") else Action.fold()), memory

    def _act(self, s):
        if s.phase == "select":
            best = None
            for d, i, j in ((0, 1, 2), (1, 0, 2), (2, 0, 1)):
                v = eval7.evaluate([eval7.Card(c) for c in (s.cards[i], s.cards[j]) + tuple(s.board)])
                if best is None or v > best[0]:
                    best = (v, d, i, j)
            _, d, i, j = best
            lo = i if R.index(s.cards[i][0]) <= R.index(s.cards[j][0]) else j
            return Action("select", cards=(d, lo))
        if s.phase != "betting":
            f = s.legal_actions[0]
            return Action(f.kind, f.min_amount)
        me = next(x for x in s.seats if x.seat == s.seat)
        bb = s.blinds.big_blind
        r = s.can("raise")
        if not s.board:
            op, prem = _pre(s.cards)
            if s.to_call <= bb - me.bet or s.to_call == 0:
                if op and r:
                    return Action.raise_to(max(int(r.min_amount), min(int(r.max_amount), int(2.5 * bb))))
                return Action.check() if s.can("check") else Action.fold()
            if prem and r:
                return Action.raise_to(max(int(r.min_amount), min(int(r.max_amount), int(3 * (me.bet + s.to_call)))))
            if op and s.to_call <= 0.08 * me.stack and s.can("call"):
                return Action.call()
            return Action.check() if s.can("check") else Action.fold()
        tp = _toppair(s.cards, s.board)
        if s.to_call > 0:
            return Action.call() if tp and s.can("call") else Action.fold()
        if tp and r:
            return Action.raise_to(max(int(r.min_amount), min(int(r.max_amount), int(s.pot * 2 // 3))))
        return Action.check()
