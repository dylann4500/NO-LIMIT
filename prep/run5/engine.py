"""Eight-seat SNG engine following rules section 4: 2000 chips, 10/20, level every 25 hands,
200-hand cap, finishing-position points, ICM at the cap.

Bot API: bot.act(o) -> (0,0) fold | (1,0) check/call | (2,to) raise to `to` total this street.
Optional bot.observe(seat, street, kind, amount) for table events (kind: 0 fold, 1 call/check, 2 raise).
"""
import json, os, random
import pk
from pk import icm

FOLD, CALL, RAISE = 0, 1, 2

# Assumed: the real schedule ships with the starter kit. Swap at kickoff.
SCHEDULE_DEFAULT = [(10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500)]
HANDS_PER_LEVEL = 25
MAX_HANDS = 200
START = 2000
# event_config.json holds the real announced rules: {"blinds": [[10,20],...], "points": [...], "hands_per_level": 25, "max_hands": 200, "start": 2000}
_CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "event_config.json")
EVENT = json.load(open(_CFG)) if os.path.exists(_CFG) else {}
if EVENT.get("blinds"):
    SCHEDULE_DEFAULT = [tuple(x) for x in EVENT["blinds"]]
HANDS_PER_LEVEL = EVENT.get("hands_per_level", HANDS_PER_LEVEL)
MAX_HANDS = EVENT.get("max_hands", MAX_HANDS)
START = EVENT.get("start", START)


class Obs:
    __slots__ = (
        "seat", "hole", "board", "street", "pot", "to_call", "min_raise_to", "max_raise_to", "can_raise",
        "stack", "bet", "cur", "sb", "bb", "hand_no", "button", "stacks", "bets", "in_hand", "allin",
        "n_alive", "n_live", "n_behind", "raises", "total_chips", "aggressor", "first_in", "n_callers",
    )


def play_table(bots, schedule=SCHEDULE_DEFAULT, rng=random):
    """Plays one table. Returns (finish_groups, hands, survivors) where finish_groups lists
    (list of seats, place index) as eliminated and survivors is the dict of live stacks at the end."""
    n = len(bots)
    stacks = [START] * n
    button = rng.randrange(n)
    eliminated = []  # list of lists of seats, in elimination order
    total = START * n
    deck = pk.DECK
    NH = pk.N_HOLE
    showdown = pk.showdown
    wants = [hasattr(b, "observe") for b in bots]
    o = Obs()
    o.total_chips = total
    hand_no = 0
    while hand_no < MAX_HANDS:
        alive = [i for i in range(n) if stacks[i] > 0]
        if len(alive) <= 1:
            break
        lvl = min(hand_no // HANDS_PER_LEVEL, len(schedule) - 1)
        sb, bb = schedule[lvl]
        # move button to next live seat
        button = (button + 1) % n
        while stacks[button] <= 0:
            button = (button + 1) % n
        bi = alive.index(button)
        rot = alive[bi:] + alive[:bi]  # button first
        m = len(rot)
        if m == 2:
            sb_seat, bb_seat = rot[0], rot[1]
            pre_order = [rot[0], rot[1]]
            post_order = [rot[1], rot[0]]
        else:
            sb_seat, bb_seat = rot[1], rot[2]
            pre_order = rot[3:] + rot[:3]
            post_order = rot[1:] + rot[:1]
        start_stack = stacks[:]
        cards = rng.sample(deck, 5 + NH * m)
        full_board = cards[:5]
        holes = {s: cards[5 + NH * j : 5 + NH * (j + 1)] for j, s in enumerate(rot)}
        in_hand = [stacks[i] > 0 for i in range(n)]
        bets = [0] * n
        contrib = [0] * n

        def post(s, a):
            a = min(a, stacks[s])
            stacks[s] -= a
            bets[s] += a
            contrib[s] += a

        post(sb_seat, sb)
        post(bb_seat, bb)
        live = m
        for street, nb in ((0, 0), (1, 3), (2, 4), (3, 5)):
            if live <= 1:
                break
            board = full_board[:nb]
            order = pre_order if street == 0 else post_order
            if street == 0:
                cur = bb
                last_raise = bb
            else:
                cur = 0
                last_raise = bb
                for i in range(n):
                    bets[i] = 0
                can_bet = sum(1 for s in order if in_hand[s] and stacks[s] > 0)
                if can_bet < 2:
                    continue
            raises = 0
            aggressor = -1
            to_act = len(order)
            idx = 0
            callers = 0
            first_in = True
            while to_act > 0 and live > 1:
                s = order[idx % len(order)]
                idx += 1
                to_act -= 1
                if not in_hand[s] or stacks[s] <= 0:
                    continue
                to_call = min(cur - bets[s], stacks[s])
                others = sum(1 for x in order if x != s and in_hand[x] and stacks[x] > 0)
                if to_call == 0 and others == 0:
                    continue
                o.seat = s
                o.hole = holes[s]
                o.board = board
                o.street = street
                o.pot = sum(contrib)
                o.to_call = to_call
                o.cur = cur
                o.stack = stacks[s]
                o.bet = bets[s]
                o.max_raise_to = bets[s] + stacks[s]
                o.min_raise_to = min(cur + last_raise, o.max_raise_to)
                o.can_raise = others > 0 and stacks[s] > to_call
                o.sb, o.bb = sb, bb
                o.hand_no = hand_no
                o.button = button
                o.stacks = stacks
                o.bets = bets
                o.in_hand = in_hand
                o.n_alive = m
                o.n_live = live
                o.raises = raises
                o.aggressor = aggressor
                o.first_in = first_in
                o.n_callers = callers
                # Number of active seats still to act after this one (includes re-acting aggressors).
                nbh = 0
                L = len(order)
                for j in range(idx, idx + to_act):
                    x = order[j % L]
                    if in_hand[x] and stacks[x] > 0:
                        nbh += 1
                o.n_behind = nbh
                try:
                    kind, amt = bots[s].act(o)
                except Exception:
                    kind, amt = (CALL, 0) if to_call == 0 else (FOLD, 0)
                if kind == FOLD and to_call == 0:
                    kind = CALL
                if kind == RAISE and not o.can_raise:
                    kind = CALL
                if kind == FOLD:
                    in_hand[s] = False
                    live -= 1
                    ev = (s, street, 0, 0)
                elif kind == CALL:
                    stacks[s] -= to_call
                    bets[s] += to_call
                    contrib[s] += to_call
                    if to_call > 0:
                        callers += 1
                    ev = (s, street, 1, to_call)
                else:
                    to = int(amt)
                    if to < o.min_raise_to:
                        to = o.min_raise_to
                    if to > o.max_raise_to:
                        to = o.max_raise_to
                    add = to - bets[s]
                    stacks[s] -= add
                    bets[s] = to
                    contrib[s] += add
                    if to - cur >= last_raise:
                        last_raise = to - cur
                    cur = max(cur, to)
                    raises += 1
                    aggressor = s
                    first_in = False
                    to_act = len(order) - 1
                    idx = idx  # continue ring from next seat
                    ev = (s, street, 2, to)
                for j in range(n):
                    if wants[j]:
                        bots[j].observe(*ev)
        # settle
        settle_contrib = contrib
        if live == 1:
            w = next(i for i in rot if in_hand[i])
            stacks[w] += sum(settle_contrib)
        else:
            vals = {}
            for s in rot:
                if in_hand[s]:
                    vals[s] = showdown(holes[s], full_board)
            remaining = settle_contrib[:]
            while True:
                pos = [c for c in remaining if c > 0]
                if not pos:
                    break
                lv = min(pos)
                pot = 0
                elig = []
                for i in range(n):
                    if remaining[i] > 0:
                        pot += lv
                        remaining[i] -= lv
                        if i in vals:
                            elig.append(i)
                if not elig:
                    # Dead money whose contributors all folded goes to the best live hand.
                    elig = list(vals)
                best = max(vals[i] for i in elig)
                winners = [i for i in elig if vals[i] == best]
                share = pot // len(winners)
                for w in winners:
                    stacks[w] += share
                for w in winners[: pot - share * len(winners)]:
                    stacks[w] += 1
        for b in bots:
            if hasattr(b, "hand_result"):
                b.hand_result(stacks, start_stack)
            if hasattr(b, "end_hand"):
                b.end_hand(hand_no)
        hand_no += 1
        busted = [i for i in alive if stacks[i] <= 0]
        if busted:
            # Bust order inside one hand: larger starting stack finishes higher.
            busted.sort(key=lambda i: start_stack[i])
            groups = {}
            for i in busted:
                groups.setdefault(start_stack[i], []).append(i)
            for k in sorted(groups):
                eliminated.append(groups[k])
    survivors = {i: stacks[i] for i in range(n) if stacks[i] > 0}
    return eliminated, hand_no, survivors


def points_for(eliminated, survivors, payouts, n=8):
    """Convert a table result to per-seat points. Ties split place points; survivors get ICM."""
    pts = [0.0] * n
    pay = list(payouts) + [0.0] * (n - len(payouts))
    place = n  # next place from the bottom (1-indexed count)
    for grp in eliminated:
        k = len(grp)
        slice_ = pay[place - k : place]
        val = sum(slice_) / k
        for s in grp:
            pts[s] = val
        place -= k
    seats = list(survivors)
    if len(seats) == 1:
        pts[seats[0]] = pay[0]
    elif seats:
        vals = icm([survivors[s] for s in seats], pay[: len(seats)])
        for s, v in zip(seats, vals):
            pts[s] = v
    return pts
