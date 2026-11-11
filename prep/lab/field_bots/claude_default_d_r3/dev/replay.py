"""Replay real hand-history decision points (facing a raise after our own postflop bet) through two agent
versions and estimate the chip difference where they disagree (fold = lose what was already invested)."""
import json, gzip, collections, sys, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(LAB, "fake_sdk"))
from poker_agent_sdk import ActionKind, LegalAction, Event, Seat, Config, State
SCHED = [[10, 20], [15, 30], [25, 50], [40, 80], [60, 120], [100, 200], [150, 300], [250, 500]]

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(path, "agent.py"))
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m.Agent

A = load(sys.argv[1], "agent_a"); B = load(sys.argv[2], "agent_b")
files = sys.argv[3:]
tot = collections.Counter(); diff_bb = 0.0; rows = []; seen = set()
for P in files:
    for l in gzip.open(P, "rt"):
        h = json.loads(l); me = h["seat"]; bb = h["blinds"][1]
        if str(me) not in h["stacks"]: continue
        start = {int(k): v for k, v in h["stacks"].items()}
        s1 = None
        for k, s, a, c in h["events"]:
            if k == "stack" and s == me: s1 = a
        if s1 is None: continue
        contrib = collections.Counter(); sb = collections.Counter(); folded = set(); board = []; street = 0
        curbet = 0; last_raise = bb; bet_here = False; hist = []
        for k, s, a, c in h["events"]:
            if s == me and k in ("call", "fold", "raise", "check") and street >= 1 and bet_here and curbet > sb[me]:
                to_call = curbet - sb[me]
                mystack = start[me] - contrib[me]
                legal = [LegalAction(ActionKind.FOLD), LegalAction(ActionKind.CALL)]
                if mystack > to_call:
                    legal.append(LegalAction(ActionKind.RAISE, min(curbet + last_raise, mystack + sb[me]), mystack + sb[me]))
                seats = []
                for x in sorted(start):
                    stx = start[x] - contrib[x]
                    status = "folded" if x in folded else ("all_in" if stx == 0 else "active")
                    seats.append(Seat(x, stx, sb[x], status))
                cfg = Config(table_id="r", seat=me, variant="holdem", players=8, starting_stack=2000, blinds=SCHED,
                             hands_per_level=20, hand_cap=250, payouts=[50, 30, 20, 0, 0, 0, 0, 0], decision_ms=1,
                             time_bank_ms=100, memory_bytes=65536)
                st = State(seat=me, cards=list(h["hole"]), board=list(board), pot=sum(contrib.values()), to_call=to_call,
                           legal_actions=legal, history=list(hist), phase="betting", seats=seats, button=h["button"],
                           blind_level=1, blinds=list(h["blinds"]), hands_until_next_level=10, hand_number=h["hand"],
                           players_remaining=len(start), bust_order=[], config=cfg, time_bank_ms=100, events=list(hist))
                ka = A().act(st, b"")[0].kind.value; kb = B().act(st, b"")[0].kind.value
                actual = k
                res = (s1 - start[me]) / bb
                inv = -contrib[me] / bb
                tot[(ka, kb)] += 1
                if ka != "fold" and kb == "fold" and actual in ("call", "raise") and (P, h["table"], h["hand"]) not in seen:
                    seen.add((P, h["table"], h["hand"]))
                    diff_bb += inv - res; rows.append((h["hand"], h["hole"], board[:], ka, kb, round(res, 1), round(inv, 1)))
                elif ka == "fold" and kb != "fold" and actual == "fold":
                    rows.append(("B continues where A folded (unknown outcome)", h["hand"], h["hole"], board[:]))
            # apply event
            e = Event(k, s, a, c); hist.append(e)
            if k == "board": board += c; street += 1; sb = collections.Counter(); curbet = 0; last_raise = bb; bet_here = False
            elif k in ("blind", "ante"): contrib[s] += a; sb[s] += a; curbet = max(curbet, sb[s])
            elif k == "call": contrib[s] += a; sb[s] += a
            elif k == "fold": folded.add(s)
            elif k == "raise":
                contrib[s] += a - sb[s]; sb[s] = a
                if a - curbet > last_raise: last_raise = a - curbet
                curbet = a
                if s == me and street >= 1: bet_here = True
print("decision pairs (A action, B action):", dict(tot))
print("estimated chips saved by B folding where A continued (and A's line was actually played): %.0f bb over %d spots" % (diff_bb, sum(1 for r in rows if not isinstance(r[0], str))))
for r in rows[:25]: print("  ", r)
