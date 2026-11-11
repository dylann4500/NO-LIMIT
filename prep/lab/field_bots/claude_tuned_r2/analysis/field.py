"""Per-team tendencies and results from every seat in the round-1 histories."""
import gzip, json, collections, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "..", "claude_tuned", "round1", "hand_history.jsonl.gz")
H = [json.loads(l) for l in gzip.open(PATH, "rt")]
T = collections.defaultdict(lambda: collections.Counter())
for h in H:
    names = h["names"]
    bb = h["blinds"][1]
    st0 = {int(k): v for k, v in h["stacks"].items()}
    st1 = {}
    for k, s, a, c in h["events"]:
        if k == "stack":
            st1[s] = a
    street = 0
    nr = 0
    acted = set(); vp = set(); pr = set()
    pf_aggr = None
    cbet_chance = None
    flop_bet = False
    faced_open = set()
    for k, s, a, c in h["events"]:
        if k == "board":
            street += 1
            flop_bet = False
            continue
        if k not in ("fold", "check", "call", "raise"):
            continue
        n = names[str(s)]
        t = T[n]
        if street == 0:
            if s not in acted:
                acted.add(s); t["hands"] += 1
                if nr == 0: t["unopened_chance"] += 0
            if nr == 1 and s not in faced_open:
                faced_open.add(s); t["faced_open"] += 1
                if k == "raise": t["3bet"] += 1
                if k == "fold": t["fold_to_open"] += 1
                if k == "call": t["call_open"] += 1
            if nr == 2 and s == pf_aggr_first:
                t["faced_3bet"] += 1
                if k == "fold": t["fold_to_3bet"] += 1
                if k == "raise": t["4bet"] += 1
            if k in ("call", "raise") and s not in vp:
                vp.add(s); t["vpip"] += 1
            if k == "raise":
                if nr == 0:
                    pf_aggr_first = s
                    t["open"] += 1
                    t["open_size_bb"] += a / bb
                    if st0.get(s, 0) and a >= 0.95 * st0[s]:
                        t["open_shove"] += 1
                nr += 1
                pf_aggr = s
                if s not in pr:
                    pr.add(s); t["pfr"] += 1
        else:
            if street == 1 and s == pf_aggr and not flop_bet:
                t["cbet_chance"] += 1
                if k == "raise": t["cbet"] += 1
            if street >= 1 and flop_bet and k in ("fold", "call", "raise"):
                t["faced_bet"] += 1
                if k == "fold": t["fold_to_bet"] += 1
                if k == "raise": t["raise_vs_bet"] += 1
            if k == "raise":
                t["post_aggr"] += 1; flop_bet = True
            else:
                t["post_pass"] += 1
    for s, v in st0.items():
        if s in st1:
            T[names[str(s)]]["net_bb_x100"] += int(100 * (st1[s] - v) / bb)
            T[names[str(s)]]["seen"] += 1
    for k, s, a, c in h["events"]:
        if k == "show":
            T[names[str(s)]]["showdowns"] += 1
lb = {e["name"]: e["mean"] for e in json.load(open(os.path.join(HERE, "..", "..", "claude_tuned", "round1", "leaderboard.json")))["board"]}
print("%-20s %5s %6s %5s %5s %5s %6s %5s %5s %5s %5s %5s %5s %5s %6s" % ("team", "pts", "hands", "vpip", "pfr", "3bet", "ftOpen", "osz", "oshv", "ft3b", "cbet", "ftBet", "AF", "wtsd", "bb/h"))
for n, t in sorted(T.items(), key=lambda kv: -lb.get(kv[0], 0)):
    hh = max(1, t["hands"])
    print("%-20s %5.1f %6d %5.2f %5.2f %5.2f %6.2f %5.1f %5.2f %5.2f %5.2f %5.2f %5.2f %5.2f %6.2f" % (
        n, lb.get(n, 0), t["hands"], t["vpip"] / hh, t["pfr"] / hh, t["3bet"] / max(1, t["faced_open"]),
        t["fold_to_open"] / max(1, t["faced_open"]), t["open_size_bb"] / max(1, t["open"]), t["open_shove"] / max(1, t["open"]),
        t["fold_to_3bet"] / max(1, t["faced_3bet"]), t["cbet"] / max(1, t["cbet_chance"]), t["fold_to_bet"] / max(1, t["faced_bet"]),
        t["post_aggr"] / max(1, t["post_aggr"] + t["post_pass"]), t["showdowns"] / hh, t["net_bb_x100"] / 100 / max(1, t["seen"])))
