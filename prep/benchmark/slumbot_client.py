"""Plays a generated reference bot against Slumbot's public API, one request at a time. stdlib only.
usage: slumbot_client.py <bot_dir> --hands N [--log hands.jsonl] [--delay 0.1]

Format differs from the tournament: heads-up cash, 50/100, 200 BB, stacks reset every hand.
Use this to find postflop and heads-up leaks, not to predict tournament score.
"""
import argparse, itertools, json, math, os, sys, time, urllib.request

URL = "https://slumbot.com/slumbot/api/"
SB, BB, STACK = 50, 100, 20000
RK, SU = "23456789TJQKA", "shdc"
CARD = {r + s: i * 4 + j for i, r in enumerate(RK) for j, s in enumerate(SU)}


def post(path, body):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "poker-benchmark-client"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def parse(action):
    """Returns one dict of current-street state plus an event list, from an action string like b200c/kb400."""
    streets = action.split("/")
    total = [0, 0]  # by order: 0 = small blind / first preflop, 1 = big blind
    events = []
    cur_st = {}
    for si, s in enumerate(streets):
        bets = [SB, BB] if si == 0 else [0, 0]
        cur, last = (BB, BB) if si == 0 else (0, BB)
        actor = 0 if si == 0 else 1
        raises, aggressor = 0, -1
        i = 0
        while i < len(s):
            ch = s[i]
            i += 1
            if ch == "b":
                j = i
                while j < len(s) and s[j].isdigit():
                    j += 1
                to = int(s[i:j]); i = j
                if to - cur > last:
                    last = to - cur
                cur = to; bets[actor] = to; raises += 1; aggressor = actor
                events.append((si, actor, 2))
            elif ch == "c":
                bets[actor] = cur; events.append((si, actor, 1))
            elif ch == "k":
                events.append((si, actor, 1))
            elif ch == "f":
                events.append((si, actor, 0))
            actor = 1 - actor
        cur_st = dict(street=si, bets=bets, cur=cur, last=last, actor=actor, raises=raises, aggressor=aggressor, prior=list(total))
        if si < len(streets) - 1:
            total = [total[0] + bets[0], total[1] + bets[1]]
    cur_st["total"] = total
    return cur_st, events


def seen_acts(action):
    return action.split("/")[-1]


def decide(ref, policy, r, n_seen):
    """Maps a Slumbot response to the policy's normalised State. In the policy's view we are seat 0, Slumbot seat 1."""
    action, pos = r["action"], r["client_pos"]
    me = 1 if pos == 0 else 0  # client_pos 0 means big blind; preflop index 1
    st, events = parse(action)
    for si, who, kind in events[n_seen:]:
        policy.observe(0 if who == me else 1, si, kind)
    n_seen = len(events)
    o = ref.State()
    bets = st["bets"]
    prior = st["total"]
    my_bet, op_bet = bets[me], bets[1 - me]
    my_stack = STACK - prior[me] - my_bet
    op_stack = STACK - prior[1 - me] - op_bet
    o.seat = 0
    o.hole = [CARD[c] for c in r["hole_cards"]]
    o.board = [CARD[c] for c in r["board"]]
    o.street = st["street"]
    o.pot = sum(prior) + sum(bets)
    o.to_call = min(st["cur"] - my_bet, my_stack)
    o.cur = st["cur"]
    o.stack, o.bet = my_stack, my_bet
    o.sb, o.bb = SB, BB
    o.stacks, o.bets = [my_stack, op_stack], [my_bet, op_bet]
    o.in_hand = [True, True]
    o.n_alive, o.n_live = 2, 2
    # On a new street, or facing no bet when first to act, the opponent acts behind us.
    o.n_behind = 1 if (o.to_call == 0 and st["raises"] == 0 and (st["actor"] == (0 if st["street"] == 0 else 1))) or (st["street"] == 0 and st["raises"] == 0 and me == 0) else 0
    o.raises = st["raises"]
    o.aggressor = -1 if st["aggressor"] < 0 else (0 if st["aggressor"] == me else 1)
    o.n_callers = 0
    o.max_raise_to = my_bet + my_stack
    o.min_raise_to = min(st["cur"] + st["last"], o.max_raise_to)
    o.can_raise = op_stack > 0 and my_stack > o.to_call
    k, a = policy.safe_decide(o)
    if k == 2:
        return f"b{int(a)}", n_seen
    if k == 1:
        return ("k" if o.to_call == 0 else "c"), n_seen
    return "f", n_seen


def allin_adjusted(ref, r, winnings):
    """If both players were all-in before the river and cards were shown, replace the result with expected chips."""
    bot = r.get("bot_hole_cards")
    act = r.get("action", "")
    if not bot or not act.endswith("/") or "f" in act.split("/")[-1]:
        return winnings
    hole = [CARD[c] for c in r["hole_cards"]]
    opp = [CARD[c] for c in bot]
    streets = act.split("/")
    known = {0: 0, 1: 3, 2: 4, 3: 5}
    idx = 0
    for i, s in enumerate(streets):
        if s:
            idx = i
    nb = known.get(idx, 5)
    board = [CARD[c] for c in r["board"]][:nb]
    if len(board) >= 5:
        return winnings
    deck = [c for c in range(52) if c not in hole and c not in opp and c not in board]
    w = t = 0.0
    for extra in itertools.combinations(deck, 5 - len(board)):
        b = board + list(extra)
        a, v = ref.evaluate(hole + b), ref.evaluate(opp + b)
        w += 1.0 if a > v else 0.5 if a == v else 0.0
        t += 1
    return (2 * w / t - 1) * abs(winnings) if winnings else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("bot_dir"); ap.add_argument("--hands", type=int, default=20)
    ap.add_argument("--log", default=None); ap.add_argument("--delay", type=float, default=0.1)
    a = ap.parse_args()
    sys.path.insert(0, a.bot_dir)
    import bot as ref
    token = None
    results = []
    logf = open(a.log, "a", buffering=1) if a.log else None
    err = 0
    for h in range(a.hands):
        try:
            body = {"token": token} if token else {}
            r = post("new_hand", body)
            token = r.get("token", token)
            policy = ref.Policy()
            n_seen = 0
            while "winnings" not in r:
                inc, n_seen = decide(ref, policy, r, n_seen)
                time.sleep(a.delay)
                body = {"token": token, "incr": inc}
                r2 = post("act", body)
                if "error_msg" in r2:
                    err += 1
                    print("API error:", r2["error_msg"], "after", r["action"], "sent", inc, file=sys.stderr, flush=True)
                    r2 = post("act", {"token": token, "incr": "k" if inc in ("k",) else "c"})
                    if "error_msg" in r2:
                        r2 = post("act", {"token": token, "incr": "f"})
                r = r2
                token = r.get("token", token)
            w = r["winnings"]
            adj = allin_adjusted(ref, r, w)
            results.append((w, adj))
            if logf:
                logf.write(json.dumps({"w": w, "adj": adj, "action": r["action"], "pos": r["client_pos"], "hole": r["hole_cards"], "board": r["board"], "bot": r.get("bot_hole_cards")}) + "\n")
        except Exception as e:
            err += 1
            print("error:", repr(e), file=sys.stderr, flush=True)
            time.sleep(5)
            token = None
        if (h + 1) % 100 == 0 or h + 1 == a.hands:
            n = len(results)
            for lab, i in (("raw", 0), ("allin-adj", 1)):
                m = sum(x[i] for x in results) / n
                sd = math.sqrt(sum((x[i] - m) ** 2 for x in results) / max(1, n - 1))
                print(f"{n} hands {lab}: {m/BB*100:+.1f} ± {sd/math.sqrt(n)/BB*100:.1f} bb/100", flush=True)
            print(f"errors so far: {err}", flush=True)
            time.sleep(0)
