"""Correct Malmuth-Harville ICM that pays bust places properly."""


def mh(stacks, pay):
    """MH expected payout for players with stack>0; players with 0 stack get 0 here.
    pay: payouts for places 1..len(pay) among the players with chips."""
    idx = [i for i, s in enumerate(stacks) if s > 0]
    out = [0.0] * len(stacks)
    places = min(len(pay), len(idx))
    if not idx:
        return out
    chance = {0: 1.0}
    for place in range(places):
        nxt = {}
        for mask, pr in chance.items():
            rem = sum(stacks[p] for k, p in enumerate(idx) if not mask >> k & 1)
            for k, p in enumerate(idx):
                if mask >> k & 1:
                    continue
                sh = pr * stacks[p] / rem
                out[p] += sh * pay[place]
                nxt[mask | 1 << k] = nxt.get(mask | 1 << k, 0.0) + sh
        chance = nxt
    return out


def value(before, after, pay):
    """Points for every seat after a hand that started with stacks `before` and ended with `after`.
    Seats dead before the hand get 0 here (their result was fixed earlier). Seats that bust in
    this hand take the bottom places among those alive at the start, larger starting stack =
    better place; exact ties split the tied places' payouts. The rest split the top places by MH."""
    n = len(before)
    alive = [i for i in range(n) if before[i] > 0]
    na = len(alive)
    payfull = list(pay) + [0.0] * max(0, na - len(pay))
    out = [0.0] * n
    busted = [i for i in alive if after[i] <= 0]
    surv = [i for i in alive if after[i] > 0]
    m = len(surv)
    # busted players: places m+1 .. na, ordered by starting stack desc
    busted.sort(key=lambda i: -before[i])
    k = 0
    while k < len(busted):
        j = k
        while j + 1 < len(busted) and before[busted[j + 1]] == before[busted[k]]:
            j += 1
        grp = busted[k:j + 1]
        pl = [m + 1 + q for q in range(k, j + 1)]  # 1-based places
        v = sum(payfull[p - 1] for p in pl) / len(grp)
        for i in grp:
            out[i] = v
        k = j + 1
    sv = mh([after[i] for i in surv], payfull[:m])
    for q, i in enumerate(surv):
        out[i] = sv[q]
    return out
