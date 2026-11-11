"""Own mini tournament engine for testing vs. custom opponents (uses the fake SDK's classes).
Not used by the bot. Simplified: any raise reopens action; no antes."""
import os
import random
import sys
import time

import eval7

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "fake_sdk"))
import poker_agent_sdk as sdk  # noqa: E402
from poker_agent_sdk import ActionKind, LegalAction, Event, Seat, Config, State  # noqa: E402

DECK = [r + s for r in "23456789TJQKA" for s in "shdc"]
EC = {c: eval7.Card(c) for c in DECK}
SCHED = [[10, 20], [15, 30], [25, 50], [40, 80], [60, 120], [100, 200], [150, 300], [250, 500]]


def icm_all(stacks, pay):
    n = len(stacks)
    res = [0.0] * n

    def rec(alive, prob, place):
        if place >= len(pay) or not alive:
            return
        tot = sum(stacks[i] for i in alive)
        for i in alive:
            p = prob * stacks[i] / tot
            res[i] += p * pay[place]
            rec([j for j in alive if j != i], p, place + 1)

    rec([i for i in range(n) if stacks[i] > 0], 1.0, 0)
    return res


class Player:
    def __init__(self, bot, name):
        self.bot, self.name = bot, name
        self.mem = b""
        self.cursor = 0
        self.fails = 0
        self.decisions = 0
        self.maxlat = 0.0
        self.lat = []


def play_table(bots, names, rng, hand_cap=250, start=2000, hpl=20, payouts=(50, 30, 20, 0, 0, 0, 0, 0)):
    n = len(bots)
    P = [Player(b, nm) for b, nm in zip(bots, names)]
    stacks = [start] * n
    log = []
    bust_groups = []
    button = rng.randrange(n)
    cfg_base = dict(variant="holdem", players=n, starting_stack=start, blinds=SCHED, hands_per_level=hpl,
                    hand_cap=hand_cap, payouts=list(payouts), decision_ms=1, time_bank_ms=100, memory_bytes=65536)
    tid = "t%d" % rng.randrange(10 ** 9)
    hand_no = 0
    while hand_no < hand_cap and sum(1 for s in stacks if s > 0) > 1:
        hand_no += 1
        lvl = min((hand_no - 1) // hpl, len(SCHED) - 1)
        sb, bb = SCHED[lvl]
        alive = [i for i in range(n) if stacks[i] > 0]
        # move button to next alive
        b = (button + 1) % n
        while stacks[b] <= 0:
            b = (b + 1) % n
        button = b

        def nxt(i):
            j = (i + 1) % n
            while stacks_start[j] <= 0:
                j = (j + 1) % n
            return j

        stacks_start = stacks[:]
        hist = []

        def ev(kind, seat=None, amount=None, cards=None):
            e = Event(kind, seat, amount, cards)
            log.append(e)
            hist.append(e)

        ev("hand", None, hand_no)
        if len(alive) == 2:
            sbs, bbs = button, nxt(button)
        else:
            sbs = nxt(button)
            bbs = nxt(sbs)
        bet = [0] * n
        contrib = [0] * n
        status = ["active" if stacks[i] > 0 else "busted" for i in range(n)]
        for s_, amt in ((sbs, sb), (bbs, bb)):
            a = min(amt, stacks[s_])
            stacks[s_] -= a
            bet[s_] += a
            contrib[s_] += a
            ev("blind", s_, a)
            if stacks[s_] == 0:
                status[s_] = "all_in"
        deck = DECK[:]
        rng.shuffle(deck)
        hole = {}
        for i in alive:
            hole[i] = [deck.pop(), deck.pop()]
        board_all = [deck.pop() for _ in range(5)]
        board = []
        cur_bet = max(bet)
        min_inc = bb
        for street in range(4):
            if street > 0:
                newc = board_all[len(board):(3 if street == 1 else len(board) + 1)]
                board += newc
                ev("board", None, None, list(newc))
                bet = [0] * n
                cur_bet = 0
                min_inc = bb
            in_hand = [i for i in alive if status[i] in ("active", "all_in")]
            if len(in_hand) <= 1:
                break
            can_act = [i for i in in_hand if status[i] == "active"]
            if len(can_act) <= 1 and (street > 0 or all(bet[i] >= cur_bet for i in can_act)):
                continue
            first = nxt(bbs) if street == 0 else nxt(button)
            acted = set()
            i = first
            guard = 0
            while True:
                guard += 1
                if guard > 500:
                    raise RuntimeError("loop")
                in_hand = [k for k in alive if status[k] in ("active", "all_in")]
                if len(in_hand) <= 1:
                    break
                actives = [k for k in in_hand if status[k] == "active"]
                if all((k in acted and bet[k] >= cur_bet) for k in actives):
                    break
                if status[i] != "active":
                    i = nxt(i)
                    continue
                if i in acted and bet[i] >= cur_bet:
                    i = nxt(i)
                    continue
                to_call = min(cur_bet - bet[i], stacks[i])
                legal = []
                if to_call > 0:
                    legal.append(LegalAction(ActionKind.FOLD, 0, 0))
                    legal.append(LegalAction(ActionKind.CALL, 0, 0))
                else:
                    legal.append(LegalAction(ActionKind.CHECK, 0, 0))
                others_can = any(status[k] == "active" and k != i for k in in_hand)
                if stacks[i] > cur_bet - bet[i] and (others_can or cur_bet > bet[i]):
                    lo = min(cur_bet + min_inc, bet[i] + stacks[i])
                    legal.append(LegalAction(ActionKind.RAISE, lo, bet[i] + stacks[i]))
                    if not others_can:
                        legal.pop()
                pl = P[i]
                new_events = log[pl.cursor:]
                pl.cursor = len(log)
                seats = [Seat(k, stacks[k], bet[k], status[k], []) for k in range(n)]
                st = State(seat=i, cards=list(hole[i]), board=list(board), pot=sum(contrib), to_call=to_call,
                           legal_actions=legal, history=list(hist), phase="betting", variant="holdem", seats=seats,
                           button=button, blind_level=lvl + 1, blinds=[sb, bb],
                           hands_until_next_level=hpl - (hand_no - 1) % hpl - 1, hand_number=hand_no,
                           players_remaining=len(alive), bust_order=[], config=Config(table_id=tid, seat=i, **cfg_base),
                           time_bank_ms=100, events=new_events)
                t0 = time.perf_counter()
                ok = False
                try:
                    act, mem = pl.bot.act(st, pl.mem)
                    kind = act.kind
                    amt = act.amount
                    la = next((x for x in legal if x.kind == kind), None)
                    if la is not None and (kind != ActionKind.RAISE or (isinstance(amt, int) and la.min_amount <= amt <= la.max_amount)):
                        ok = True
                        pl.mem = mem[:65536] if isinstance(mem, (bytes, bytearray)) else b""
                except Exception as ex:  # noqa
                    if os.environ.get("SIM_RAISE"):
                        raise
                dt = time.perf_counter() - t0
                pl.decisions += 1
                pl.lat.append(dt)
                if not ok:
                    pl.fails += 1
                    kind = ActionKind.CHECK if to_call == 0 else ActionKind.FOLD
                    amt = None
                acted.add(i)
                if kind == ActionKind.FOLD:
                    status[i] = "folded"
                    ev("fold", i)
                elif kind == ActionKind.CHECK:
                    ev("check", i)
                elif kind == ActionKind.CALL:
                    a = to_call
                    stacks[i] -= a
                    bet[i] += a
                    contrib[i] += a
                    ev("call", i, a)
                    if stacks[i] == 0:
                        status[i] = "all_in"
                else:
                    add = amt - bet[i]
                    inc = amt - cur_bet
                    if inc >= min_inc:
                        min_inc = inc
                    cur_bet = max(cur_bet, amt)
                    stacks[i] -= add
                    bet[i] = amt
                    contrib[i] += add
                    ev("raise", i, amt)
                    if stacks[i] == 0:
                        status[i] = "all_in"
                    acted = {i}
                i = nxt(i)
        # showdown / award
        in_hand = [i for i in alive if status[i] in ("active", "all_in")]
        if len(in_hand) == 1:
            w = in_hand[0]
            amt = sum(contrib)
            stacks[w] += amt
            ev("win", w, amt)
        else:
            while len(board) < 5:
                newc = board_all[len(board):(3 if len(board) == 0 else len(board) + 1)]
                board += newc
                ev("board", None, None, list(newc))
            for i in in_hand:
                ev("show", i, None, list(hole[i]))
            val = {i: eval7.evaluate([EC[c] for c in hole[i] + board]) for i in in_hand}
            levels = sorted(set(contrib[i] for i in alive if contrib[i] > 0))
            prev = 0
            for lv in levels:
                layer = sum(min(contrib[k], lv) - min(contrib[k], prev) for k in range(n))
                elig = [i for i in in_hand if contrib[i] >= lv]
                if not elig:
                    # return to those who contributed (uncalled)
                    elig = [i for i in alive if contrib[i] >= lv]
                best = max(val.get(i, -1) for i in elig)
                ws = [i for i in elig if val.get(i, -1) == best]
                share = layer // len(ws)
                rem = layer - share * len(ws)
                for j, w in enumerate(ws):
                    stacks[w] += share + (1 if j < rem else 0)
                    ev("win", w, share)
                prev = lv
        for i in alive:
            ev("stack", i, stacks[i])
        busted = [i for i in alive if stacks[i] <= 0]
        if busted:
            busted.sort(key=lambda i: stacks_start[i])  # fewer chips at start = lower place
            # group by equal start stacks
            bust_groups.append(busted)
    # points
    pts = [0.0] * n
    surv = [i for i in range(n) if stacks[i] > 0]
    place = n
    places = [0] * n
    for g in bust_groups:
        # within one hand: lower start stack -> worse place
        for i in g:
            places[i] = place
            pts[i] = payouts[place - 1] if place - 1 < len(payouts) else 0
            place -= 1
    if len(surv) == 1:
        places[surv[0]] = 1
        pts[surv[0]] = payouts[0]
    else:
        pay = list(payouts[:len(surv)])
        vals = icm_all([stacks[i] for i in surv], pay)
        for k, i in enumerate(surv):
            pts[i] = vals[k]
        for r, i in enumerate(sorted(surv, key=lambda x: -stacks[x])):
            places[i] = r + 1
    return pts, places, P, hand_no
