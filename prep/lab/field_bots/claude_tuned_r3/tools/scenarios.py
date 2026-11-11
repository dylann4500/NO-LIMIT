"""Hand-built decision scenarios: sanity checks of the agent's choices in key spots."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "fake_sdk"))
sys.path.insert(0, os.path.dirname(HERE))
from poker_agent_sdk import ActionKind, LegalAction, Event, Seat, Config, State
import agent as A


def mk(cards, stacks, bets, button, me, hist, board=(), status=None, blinds=(10, 20), pays=(50, 30, 20, 0, 0, 0, 0, 0)):
    n = len(stacks)
    status = status or ["active"] * n
    cur = max(bets)
    to_call = cur - bets[me]
    legal = []
    if to_call > 0:
        legal += [LegalAction(ActionKind.FOLD), LegalAction(ActionKind.CALL)]
    else:
        legal += [LegalAction(ActionKind.CHECK)]
    if stacks[me] > to_call:
        legal.append(LegalAction(ActionKind.RAISE, min(cur + blinds[1], bets[me] + stacks[me]), bets[me] + stacks[me]))
    seats = [Seat(i, stacks[i], bets[i], status[i]) for i in range(n)]
    ev = [Event(*h) for h in hist]
    pot = sum(bets) + (0 if not board else 0)
    cfg = Config(payouts=list(pays), players=n)
    return State(seat=me, cards=list(cards), board=list(board), pot=pot, to_call=to_call, legal_actions=legal,
                 history=ev, phase="betting", seats=seats, button=button, blinds=list(blinds), config=cfg, events=ev)


def run(name, st, n=200, params=None):
    a = A.Agent(params)
    from collections import Counter
    c = Counter()
    for _ in range(n):
        act, _ = a.act(st, b"")
        c[(act.kind.value, act.amount)] += 1
    print("%-58s %s" % (name, dict(c.most_common(3))))


def main(params=None):
    H = lambda *x: x
    # 8-handed, 100bb deep, UTG (seat 3) unopened; button 0, SB 1, BB 2
    base_hist = [("hand", None, 5), ("blind", 1, 10), ("blind", 2, 20)]
    stacks = [2000, 1990, 1980, 2000, 2000, 2000, 2000, 2000]
    bets = [0, 10, 20, 0, 0, 0, 0, 0]
    for cards in (["As", "Kd"], ["7h", "7c"], ["Kh", "9d"], ["8s", "7s"]):
        run("UTG 100bb unopened %s" % "".join(cards), mk(cards, stacks, bets, 0, 3, base_hist), 20, params)
    # button unopened after folds
    h = base_hist + [("fold", s, None) for s in (3, 4, 5, 6, 7)]
    st = [2000, 1990, 1980, 2000, 2000, 2000, 2000, 2000]
    for cards in (["Kh", "9d"], ["Qs", "5s"], ["9h", "4c"]):
        run("BTN 100bb folded to %s" % "".join(cards), mk(cards, st, bets, 0, 0, h, status=["active", "active", "active"] + ["folded"] * 5), 20, params)
    # short stack 9bb in the CO (seat 7) 6 alive, blinds 100/200
    h = [("hand", None, 120), ("blind", 1, 100), ("blind", 2, 200), ("fold", 3, None), ("fold", 4, None)]
    stk = [3000, 2900, 2800, 2500, 2500, 0, 0, 1800]
    bts = [0, 100, 200, 0, 0, 0, 0, 0]
    stat = ["active", "active", "active", "folded", "folded", "busted", "busted", "active"]
    for cards in (["Ah", "4c"], ["Kd", "Tc"], ["9s", "8s"], ["Qd", "3c"], ["7h", "2c"]):
        run("CO 9bb shove? %s (6 left)" % "".join(cards), mk(cards, stk, bts, 0, 7, h, status=stat, blinds=(100, 200)), 50, params)
    # facing a 12bb shove from the button with 4 left (bubble), we are BB with 15bb
    h = [("hand", None, 170), ("blind", 1, 150), ("blind", 2, 300), ("raise", 0, 3600)]
    stk = [0, 5000, 4200, 0, 0, 0, 0, 3200]
    bts = [3600, 150, 300, 0, 0, 0, 0, 0]
    stat = ["all_in", "active", "active", "busted", "busted", "busted", "busted", "active"]
    stk[7] = 3200
    for cards in (["Ah", "Kc"], ["Ad", "9c"], ["8s", "8d"], ["Kd", "Jc"], ["Qs", "Ts"]):
        run("BB vs 12bb BTN shove, bubble (4 left) %s" % "".join(cards), mk(cards, stk, bts, 0, 2, h, status=stat, blinds=(150, 300)), 50, params)
    # postflop: we raised preflop, BB called, flop checked to us
    h = [("hand", None, 30), ("blind", 1, 15), ("blind", 2, 30), ("raise", 0, 75), ("fold", 1, None), ("call", 2, 45), ("board", None, None)]
    stk = [1900, 1985, 1900, 2000, 0, 0, 0, 0]
    stat = ["active", "folded", "active", "folded", "busted", "busted", "busted", "busted"]
    for cards, board in ((["Ah", "Kc"], ["Ad", "7c", "2s"]), (["Ah", "Kc"], ["9d", "8d", "6s"]), (["5h", "5c"], ["Kd", "Qc", "2s"])):
        st = mk(cards, stk, [0] * 8, 0, 0, h + [("check", 2, None)], board=board, status=stat, blinds=(15, 30))
        st.pot = 165
        run("flop IP checked to %s on %s" % ("".join(cards), "".join(board)), st, 50, params)
    # facing a pot-size river bet with a medium hand
    h = [("hand", None, 30), ("blind", 1, 15), ("blind", 2, 30), ("raise", 0, 75), ("fold", 1, None), ("call", 2, 45),
         ("board", None, None), ("check", 2, None), ("check", 0, None), ("board", None, None), ("check", 2, None), ("check", 0, None),
         ("board", None, None), ("raise", 2, 165)]
    for cards, board in ((["Ah", "Kc"], ["Ad", "7c", "2s", "9h", "4d"]), (["Th", "Tc"], ["Jd", "7c", "2s", "9h", "4d"]),
                         (["Ah", "Kc"], ["Qd", "7c", "2s", "9h", "4d"])):
        bt = [0, 0, 165, 0, 0, 0, 0, 0]
        st = mk(cards, [1900, 1985, 1735, 2000, 0, 0, 0, 0], bt, 0, 0, h, board=board, status=stat, blinds=(15, 30))
        st.pot = 165 + 165
        run("river facing pot bet %s on %s" % ("".join(cards), "".join(board)), st, 50, params)


if __name__ == "__main__":
    import json
    main(json.load(open(sys.argv[1])) if len(sys.argv) > 1 else None)
