"""Own tournament simulator for parameter tuning (independent of the lab simulator).

Implements 8-seat NLHE sit-and-go tables with the portal State/Event objects from lab/fake_sdk, rising
blinds, side pots, bust order and ICM points at the hand cap. Bots are SDK Agents: act(state, memory).
"""
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BOT = os.path.dirname(HERE)
LAB = os.path.dirname(os.path.dirname(BOT))
for p in (os.path.join(LAB, "fake_sdk"), BOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import eval7  # noqa: E402
from poker_agent_sdk import ActionKind, LegalAction, Event, Seat, Config, State  # noqa: E402

DEFAULT_BLINDS = [[10, 20], [15, 30], [25, 50], [40, 80], [60, 120], [100, 200], [150, 300], [250, 500]]
CARDS = [r + s for r in "23456789TJQKA" for s in "shdc"]
E7 = {c: eval7.Card(c) for c in CARDS}


def icm_all(stacks, pays):
    """ICM for every player (exact recursion, n <= 8)."""
    n = len(stacks)
    out = [0.0] * n
    S = float(sum(stacks))

    def rec(depth, S, used, prob):
        if depth >= len(pays) or prob <= 0:
            return
        for i in range(n):
            if i in used or stacks[i] <= 0:
                continue
            p = prob * stacks[i] / S
            out[i] += p * pays[depth]
            rec(depth + 1, S - stacks[i], used | {i}, p)

    rec(0, S, frozenset(), 1.0)
    return out


class Stats:
    def __init__(self):
        self.decisions = 0
        self.fails = 0
        self.lat = []
        self.fail_ex = []


def play_table(bots, rng, track=None, stats=None, n_hands_cap=250, blinds=None, hands_per_level=20,
               start=2000, payouts=(50, 30, 20, 0, 0, 0, 0, 0), deal_seed=None):
    """bots: list of Agent objects (one per seat). track: set of seat indices whose latency/fails to record.
    Returns list of points per seat."""
    n = len(bots)
    blinds = blinds or DEFAULT_BLINDS
    stacks = [start] * n
    busted = [False] * n
    mem = [b""] * n
    ptr = [0] * n
    events = []
    bust_groups = []
    tid = "t%d" % rng.randrange(10 ** 9)
    cfgs = [Config(table_id=tid, seat=i, variant="holdem", players=n, starting_stack=start, blinds=blinds,
                   hands_per_level=hands_per_level, hand_cap=n_hands_cap, payouts=list(payouts), decision_ms=1,
                   time_bank_ms=100, memory_bytes=65536) for i in range(n)]
    button = rng.randrange(n)
    hand_no = 0
    while hand_no < n_hands_cap and sum(1 for b in busted if not b) > 1:
        hand_no += 1
        level = min((hand_no - 1) // hands_per_level, len(blinds) - 1)
        sb_amt, bb_amt = blinds[level]
        alive = [i for i in range(n) if not busted[i]]
        # move button
        if hand_no > 1:
            j = (button + 1) % n
            while busted[j]:
                j = (j + 1) % n
            button = j
        elif busted[button]:
            button = alive[0]

        def nxt(i):
            j = (i + 1) % n
            while busted[j]:
                j = (j + 1) % n
            return j

        if len(alive) == 2:
            sb, bbs = button, nxt(button)
        else:
            sb = nxt(button)
            bbs = nxt(sb)
        start_stacks = stacks[:]
        deck = CARDS[:]
        if deal_seed is None:
            rng.shuffle(deck)
        else:
            random.Random(deal_seed * 7919 + hand_no).shuffle(deck)
        hole = {}
        for i in alive:
            hole[i] = [deck.pop(), deck.pop()]
        board_all = [deck.pop() for _ in range(5)]
        status = ["busted" if busted[i] else "active" for i in range(n)]
        bet = [0] * n
        contrib = [0] * n
        hand_start = len(events)
        events.append(Event("hand", None, hand_no, None))

        def post(i, amt, kind):
            a = min(amt, stacks[i])
            stacks[i] -= a
            bet[i] += a
            contrib[i] += a
            if stacks[i] == 0:
                status[i] = "all_in"
            events.append(Event(kind, i, a, None))

        post(sb, sb_amt, "blind")
        post(bbs, bb_amt, "blind")
        board = []
        winner_by_fold = None
        for street in range(4):
            if street > 0:
                new = board_all[len(board):(3 if street == 1 else len(board) + 1)]
                board.extend(new)
                events.append(Event("board", None, None, list(new)))
                bet = [0] * n
            in_hand = [i for i in alive if status[i] != "folded"]
            can_act = [i for i in in_hand if status[i] == "active"]
            if len(in_hand) <= 1:
                break
            cur = max(bet)
            last_raise = bb_amt
            if street == 0:
                first = nxt(bbs) if len(alive) > 2 else sb
            else:
                first = nxt(button)
            if len(can_act) <= 1 and (street > 0 or all(bet[i] >= cur for i in can_act)):
                continue
            acted = set()
            i = first
            safety = 0
            while True:
                safety += 1
                if safety > 100000:
                    raise RuntimeError("betting loop")
                in_hand = [k for k in alive if status[k] != "folded"]
                if len(in_hand) <= 1:
                    break
                can_act = [k for k in in_hand if status[k] == "active"]
                if not can_act:
                    break
                if all(k in acted and bet[k] >= cur for k in can_act):
                    break
                if status[i] != "active" or (i in acted and bet[i] >= cur):
                    i = (i + 1) % n
                    continue
                if len(can_act) == 1 and bet[i] >= cur:
                    break
                to_call = cur - bet[i]
                legal = []
                if to_call > 0:
                    legal.append(LegalAction(ActionKind.FOLD))
                    legal.append(LegalAction(ActionKind.CALL))
                else:
                    legal.append(LegalAction(ActionKind.CHECK))
                others_live = [k for k in can_act if k != i]
                if stacks[i] > to_call and others_live:
                    mn = min(cur + last_raise, bet[i] + stacks[i])
                    legal.append(LegalAction(ActionKind.RAISE, mn, bet[i] + stacks[i]))
                seats = [Seat(k, stacks[k], bet[k], status[k], None) for k in range(n)]
                st = State(seat=i, cards=list(hole[i]), board=list(board), pot=sum(contrib), to_call=to_call,
                           legal_actions=legal, history=events[hand_start:], phase="betting", variant="holdem",
                           seats=seats, button=button, blind_level=level + 1, blinds=[sb_amt, bb_amt],
                           hands_until_next_level=hands_per_level - (hand_no - 1) % hands_per_level,
                           hand_number=hand_no, players_remaining=len(alive),
                           bust_order=[x for g in bust_groups for x in g], config=cfgs[i], time_bank_ms=100,
                           events=events[ptr[i]:])
                ptr[i] = len(events)
                t0 = time.perf_counter_ns()
                ok = True
                try:
                    act, m2 = bots[i].act(st, mem[i])
                except Exception as ex:  # noqa: BLE001
                    act, m2, ok = None, None, False
                    if stats is not None and track is not None and i in track:
                        stats.fail_ex.append(repr(ex))
                dt = time.perf_counter_ns() - t0
                kind = getattr(act, "kind", None)
                amt = getattr(act, "amount", None)
                if ok:
                    offered = {la.kind: la for la in legal}
                    if kind not in offered:
                        ok = False
                    elif kind == ActionKind.RAISE:
                        la = offered[kind]
                        if not isinstance(amt, int) or amt < la.min_amount or amt > la.max_amount:
                            ok = False
                    if m2 is not None:
                        mem[i] = bytes(m2)[:65536]
                if stats is not None and track is not None and i in track:
                    stats.decisions += 1
                    stats.lat.append(dt)
                    if not ok:
                        stats.fails += 1
                        if len(stats.fail_ex) < 5:
                            stats.fail_ex.append("illegal %r legal=%r" % (act, legal))
                if not ok:
                    kind = ActionKind.CHECK if to_call == 0 else ActionKind.FOLD
                acted.add(i)
                if kind == ActionKind.FOLD:
                    status[i] = "folded"
                    events.append(Event("fold", i, None, None))
                elif kind == ActionKind.CHECK:
                    events.append(Event("check", i, None, None))
                elif kind == ActionKind.CALL:
                    a = min(to_call, stacks[i])
                    stacks[i] -= a
                    bet[i] += a
                    contrib[i] += a
                    if stacks[i] == 0:
                        status[i] = "all_in"
                    events.append(Event("call", i, a, None))
                else:
                    tot = amt
                    a = tot - bet[i]
                    stacks[i] -= a
                    bet[i] = tot
                    contrib[i] += a
                    if tot - cur >= last_raise:
                        last_raise = tot - cur
                    if tot > cur:
                        cur = tot
                        acted = {i}
                    if stacks[i] == 0:
                        status[i] = "all_in"
                    events.append(Event("raise", i, tot, None))
                i = (i + 1) % n
            in_hand = [k for k in alive if status[k] != "folded"]
            if len(in_hand) <= 1:
                break
        in_hand = [k for k in alive if status[k] != "folded"]
        if len(in_hand) == 1:
            w = in_hand[0]
            amt = sum(contrib)
            stacks[w] += amt
            events.append(Event("win", w, amt, None))
        else:
            while len(board) < 5:
                new = board_all[len(board):(3 if len(board) == 0 else len(board) + 1)]
                board.extend(new)
                events.append(Event("board", None, None, list(new)))
            bd = [E7[c] for c in board]
            val = {}
            for k in in_hand:
                events.append(Event("show", k, None, list(hole[k])))
                val[k] = eval7.evaluate([E7[c] for c in hole[k]] + bd)
            # side pots
            levels = sorted(set(contrib[k] for k in alive if contrib[k] > 0))
            prev = 0
            won = [0] * n
            for lv in levels:
                pot = sum(min(contrib[k], lv) - min(contrib[k], prev) for k in range(n))
                elig = [k for k in in_hand if contrib[k] >= lv]
                if not elig:
                    # uncalled remainder: return to the contributors
                    elig = [k for k in range(n) if contrib[k] >= lv]
                best = max(val.get(k, -1) for k in elig)
                ws = [k for k in elig if val.get(k, -1) == best]
                share, odd = divmod(pot, len(ws))
                for idx, k in enumerate(ws):
                    won[k] += share + (1 if idx < odd else 0)
                prev = lv
            for k in range(n):
                if won[k]:
                    stacks[k] += won[k]
                    events.append(Event("win", k, won[k], None))
        for k in alive:
            events.append(Event("stack", k, stacks[k], None))
        newly = [k for k in alive if stacks[k] == 0]
        if newly:
            for k in newly:
                busted[k] = True
            # more chips at the start of the hand places higher -> busts first are the smaller stacks
            newly.sort(key=lambda k: start_stacks[k])
            groups = {}
            for k in newly:
                groups.setdefault(start_stacks[k], []).append(k)
            for key in sorted(groups):
                bust_groups.append(groups[key])
    # points
    pts = [0.0] * n
    place = n
    pays = list(payouts) + [0] * n
    for g in bust_groups:
        # g busted together with equal start stacks: share the places
        val = sum(pays[place - len(g):place]) / len(g)
        for k in g:
            pts[k] = val
        place -= len(g)
    surv = [k for k in range(n) if not busted[k]]
    if len(surv) == 1:
        pts[surv[0]] = pays[0]
    else:
        vals = icm_all([stacks[k] for k in surv], pays[:len(surv)])
        for k, v in zip(surv, vals):
            pts[k] = v
    return pts, hand_no
