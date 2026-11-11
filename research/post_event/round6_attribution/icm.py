"""Malmuth-Harville ICM with bust places paid properly (our own; not poker_agent_sdk.icm, which scores a busted stack 0)."""


def icm_one(stacks, me, pay):
    """Expected points of seat `me` given dict/list-index stacks of ALIVE players (>0) competing for places 1..m.
    pay = payouts for places 1.. (list); places beyond len(pay) pay 0. Only top-3 terms computed (pay has <=3 entries here)."""
    ids = [i for i in stacks if stacks[i] > 0]
    m = len(ids)
    if me not in ids:
        return 0.0
    p = list(pay[:m]) + [0.0] * max(0, 3 - min(m, len(pay)))
    T = float(sum(stacks[i] for i in ids))
    s = stacks[me]
    u = p[0] * s / T
    if m >= 2 and len(pay) >= 2 and p[1]:
        others = [stacks[i] for i in ids if i != me]
        p2 = 0.0
        p3 = 0.0
        for a, sj in enumerate(others):
            pj = sj / T
            Tj = T - sj
            p2 += pj * s / Tj
            if m >= 3 and len(pay) >= 3 and p[2]:
                for b, sk in enumerate(others):
                    if b == a:
                        continue
                    pk = sk / Tj
                    p3 += pj * pk * s / (Tj - sk)
        u += p[1] * p2 + p[2] * p3
    return u


def icm_all(stack_list, pay):
    """Points for every seat of a list (0 = not alive -> returns None for them)."""
    st = {i: v for i, v in enumerate(stack_list) if v > 0}
    return [icm_one(st, i, pay) if stack_list[i] > 0 else None for i in range(len(stack_list))]


def u_after(sb_, sa, me, pay):
    """Our points after a hand: ICM if alive, else payout of the place we busted into (ties split)."""
    if sa[me] > 0:
        st = {i: v for i, v in enumerate(sa) if v > 0}
        return icm_one(st, me, pay)
    if sb_[me] <= 0:
        return None
    m = sum(1 for v in sa if v > 0)
    busted = [i for i in range(len(sb_)) if sb_[i] > 0 and sa[i] == 0]
    higher = sum(1 for i in busted if i != me and sb_[i] > sb_[me])
    ties = sum(1 for i in busted if i != me and sb_[i] == sb_[me])
    places = [m + 1 + higher + t for t in range(ties + 1)]
    return sum((pay[pl - 1] if pl - 1 < len(pay) else 0.0) for pl in places) / len(places)
