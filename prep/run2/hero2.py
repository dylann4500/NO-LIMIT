"""Candidate + exact-ICM required equity for big decisions. Point-table agnostic.

Rule: for a call that risks a large share of the stack, compare equity vs. the villain range against
    req = (ICM_fold - ICM_lose) / (ICM_win - ICM_lose)
computed from the actual stacks and the actual point table. It replaces plain pot odds.
"""
import random
from hero import Hero, FOLD, CALL
from pk import equity_vs_range


def icm_me(stacks, me, pay):
    """Expected points for index `me`. Malmuth-Harville with a mask memo; only called with <= 6 players."""
    n = len(stacks)
    total = float(sum(stacks))
    memo = {}

    def rec(mask, place, remain):
        # P-weighted payout for `me` given `mask` still unplaced.
        if not mask >> me & 1:
            return 0.0
        k = mask
        if k in memo:
            return memo[k]
        if remain <= 0:
            return 0.0
        res = 0.0
        pp = pay[place] if place < len(pay) else 0.0
        for i in range(n):
            if mask >> i & 1:
                si = stacks[i]
                if si <= 0:
                    continue
                p = si / remain
                if i == me:
                    res += p * pp
                else:
                    res += p * rec(mask & ~(1 << i), place + 1, remain - si)
        memo[k] = res
        return res

    return rec((1 << n) - 1, 0, total)


class HeroICM(Hero):
    def __init__(self, payouts=None, big_call=0.25, **kw):
        super().__init__(**kw)
        self.pay = payouts
        self.big_call = big_call

    def req_equity(self, o, risk):
        """ICM price for risking `risk` chips against the current aggressor."""
        v = o.aggressor
        if v < 0 or not self.pay:
            return None
        n_eliminated_bonus = 0
        seats = [s for s in range(len(o.stacks)) if s == o.seat or o.stacks[s] + o.bets[s] > 0]
        if len(seats) > 6:
            return None
        # Places already paid out are below the survivors, so the top len(seats) places remain.
        pay = self.pay[: len(seats)]
        me = seats.index(o.seat)
        vi = seats.index(v) if v in seats else None
        if vi is None:
            return None
        base = [o.stacks[s] for s in seats]
        pot = o.pot
        # Fold: the aggressor takes the pot.
        f = base[:]
        f[vi] += pot
        # Win: the aggressor's remaining chips are matched against ours.
        matched = min(base[vi], max(0, base[me] - o.to_call))
        w = base[:]
        w[me] = base[me] + pot + matched
        w[vi] = base[vi] - matched
        l = base[:]
        l[me] = base[me] - o.to_call - matched
        l[vi] = base[vi] + pot + o.to_call + matched
        F = icm_me(f, me, pay)
        W = icm_me(w, me, pay)
        L = icm_me(l, me, pay) if l[me] > 0 else self._busted_value(pay, seats, base, me)
        if W - L <= 1e-9:
            return None
        return (F - L) / (W - L)

    @staticmethod
    def _busted_value(pay, seats, base, me):
        # We finish last among the current survivors.
        return pay[len(seats) - 1] if len(seats) - 1 < len(pay) else 0.0

    def act(self, o):
        # Big decision: faced with a call that risks a quarter of the stack or more.
        if self.pay and o.to_call > self.big_call * o.stack and o.to_call > 0:
            req = self.req_equity(o, o.to_call)
            if req is not None:
                p = self.p
                if o.street == 0:
                    w = max(0.03, min(0.6, 0.12 * self._raiser_width(o) * (1.6 if o.raises <= 1 else 1.0)))
                else:
                    w = (p["range_raise"] if o.raises >= 2 else p["range_bet"]) * self._raiser_width(o)
                board = o.board
                eq = equity_vs_range(o.hole, board, w, int(p["rollouts"]))
                opp = max(1, o.n_live - 1)
                if opp > 1:
                    eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
                if eq < req:
                    return FOLD
                # Very strong: re-raise all-in when possible, otherwise call.
                if eq > 0.72 and o.can_raise:
                    return (2, o.max_raise_to)
                return CALL
        return super().act(o)
