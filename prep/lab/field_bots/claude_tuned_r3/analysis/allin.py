"""Round-2 deep dive: open-then-fold by stack depth, all-in equity vs result, who 3-bets us, calls of our shoves."""
import gzip, json, collections, sys, os
import eval7
PATH = sys.argv[1]
H = [json.loads(l) for l in gzip.open(PATH, "rt")]
C = {r + s: eval7.Card(r + s) for r in "23456789TJQKA" for s in "shdc"}


def eq_hu(mine, theirs, board):
    """exact-ish all-in equity heads-up by enumerating remaining boards (sampled if many)."""
    import random
    used = set(mine + theirs + board)
    deck = [c for c in C if c not in used]
    need = 5 - len(board)
    w = t = 0.0
    rng = random.Random(1)
    for _ in range(400 if need >= 3 else 1):
        if need == 0:
            boards = [board]
        elif need <= 2:
            import itertools
            boards = [board + list(x) for x in itertools.combinations(deck, need)]
        else:
            boards = [board + rng.sample(deck, need)]
        for b in boards:
            bd = [C[x] for x in b]
            a = eval7.evaluate([C[x] for x in mine] + bd)
            o = eval7.evaluate([C[x] for x in theirs] + bd)
            w += 1.0 if a > o else (0.5 if a == o else 0.0)
            t += 1
        if need <= 2:
            break
    return w / t


ofold = collections.defaultdict(lambda: [0, 0.0])
opens = collections.defaultdict(int)
three_by = collections.Counter()
shove_calls = collections.defaultdict(lambda: [0, 0])
ai = collections.defaultdict(lambda: [0, 0.0, 0.0])  # n, sum equity, sum result(win=1)
for h in H:
    me = h["seat"]
    if str(me) not in h["stacks"]:
        continue
    bb = h["blinds"][1]
    st0 = h["stacks"][str(me)]
    stbb = st0 / bb
    ev = h["events"]
    nr = 0
    opened = False
    street = 0
    my_shove = False
    for i, (k, s, a, c) in enumerate(ev):
        if k == "board":
            street += 1
        if street > 0 or k not in ("raise", "call", "fold", "check"):
            continue
        if k == "raise":
            nr += 1
            if s == me and nr == 1:
                opened = True
                if a >= 0.95 * st0:
                    my_shove = True
                    shv_amt = a
            elif opened and nr == 2:
                three_by[h["names"][str(s)]] += 1
        if my_shove and s != me and k in ("call", "fold", "raise"):
            bucket = min(30, int(st0 / bb / 5) * 5)
            shove_calls[bucket][0] += 1
            shove_calls[bucket][1] += (k != "fold")
    if opened and not my_shove:
        b = "%d-%d" % (int(stbb // 10) * 10, int(stbb // 10) * 10 + 10) if stbb < 60 else "60+"
        opens[b] += 1
        mine = [m for m in ev if m[1] == me and m[0] in ("fold",)]
        if mine and not any(x[0] == "board" for x in ev[:ev.index(mine[0])]):
            st1 = [x[2] for x in ev if x[0] == "stack" and x[1] == me][0]
            ofold[b][0] += 1
            ofold[b][1] += (st1 - st0) / bb
    # all-in showdowns involving us: equity at the moment of the last action vs actual
    shows = {s: c for k, s, a, c in ev if k == "show"}
    if me in shows and len(shows) == 2:
        opp = [s for s in shows if s != me][0]
        board_at = []
        # board known when the last chips went in = boards before the last call/raise
        last_bet_idx = max(i for i, x in enumerate(ev) if x[0] in ("call", "raise"))
        for x in ev[:last_bet_idx]:
            if x[0] == "board":
                board_at += x[3]
        e = eq_hu(h["hole"], shows[opp], board_at)
        st1 = [x[2] for x in ev if x[0] == "stack" and x[1] == me][0]
        won = 1.0 if st1 > st0 else (0.5 if st1 == st0 else 0.0)
        key = "pre" if not board_at else "post"
        ai[key][0] += 1; ai[key][1] += e; ai[key][2] += won
print("opens (non-shove) by depth and opens folded to 3-bet:")
for b in sorted(opens):
    print("  %-6s opens %4d  open>fold %4d (%.0f%%) net %6.0f bb" % (b, opens[b], ofold[b][0], 100 * ofold[b][0] / opens[b], ofold[b][1]))
print("our open-shoves: calls per opponent decision by our depth (bb bucket):",
      {k: "%d/%d=%.2f" % (v[1], v[0], v[1] / v[0]) for k, v in sorted(shove_calls.items())})
print("who 3-bets our opens:", three_by.most_common(8))
for k, v in ai.items():
    print("HU showdowns (%s): n=%d mean equity at all-in %.3f  actual win %.3f" % (k, v[0], v[1] / v[0], v[2] / v[0]))
