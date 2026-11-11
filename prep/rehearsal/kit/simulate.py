"""Rehearsal simulator. usage: python simulate.py path/to/my_bot.py MyAgent [tables] [field]
Set POKER_VARIANT (holdem, shortdeck, flushfh, hole3, omaha) before running to change the rules."""
import importlib.util, json, os, random, sys, time, math
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "..", "lab"))
sys.path.insert(0, ROOT)
from engine import play_table, points_for
from field import ARCHETYPES, FIELDS

RULES = json.load(open(os.path.join(ROOT, "rules_card.json")))
RK, SU = "23456789TJQKA", "shdc"
S = lambda c: RK[c >> 2] + SU[c & 3]
ST = ["preflop", "flop", "turn", "river"]
pc = time.perf_counter


class Bridge:
    """Presents the engine to a kit-style agent, and enforces rule 3.7 on it."""
    def __init__(self, agent):
        self.a, self.hist, self.hand, self.seat_known = agent, [], -1, False
        self.lat, self.err, self.illegal, self.over = [], 0, 0, 0
        self.cur_hand = 0

    def observe(self, seat, street, kind, amount):
        name = ("fold", "call", "raise")[kind]
        if kind == 1 and amount == 0:
            name = "check"
        self.hist.append({"street": ST[street], "seat": seat, "action": name, "amount": amount})

    def end_hand(self, n):
        # Normal: history is only ever delivered at decisions, so actions after our last decision are never seen.
        # KIT_FULL_HISTORY delivers them, by replaying the finished hand to an optional agent hook.
        if os.environ.get("KIT_FULL_HISTORY") and hasattr(self.a, "hand_over"):
            self.a.hand_over(self.hist)
        self.hist = []

    def act(self, o):
        if not self.seat_known:
            self.a.reset(o.seat, len(o.stacks))
            self.seat_known = True
        st = []
        for i in range(len(o.stacks)):
            s = "out" if o.stacks[i] + o.bets[i] <= 0 and not o.in_hand[i] else "folded" if not o.in_hand[i] else "allin" if o.stacks[i] == 0 else "active"
            st.append({"seat": i, "chips": o.stacks[i], "street_bet": o.bets[i], "status": s})
        rb = o.min_raise_to - o.cur if o.can_raise else None
        state = {
            "hand_id": o.hand_no, "street": ST[o.street], "my_seat": o.seat, "dealer_seat": o.button,
            "small_blind": o.sb, "big_blind": o.bb, "hole": [S(c) for c in o.hole], "community": [S(c) for c in o.board],
            "players": st, "pot": o.pot,
            "legal": {"can_check": o.to_call == 0, "call_cost": o.to_call, "raise_by_min": rb,
                      "raise_by_max": (o.max_raise_to - o.cur) if o.can_raise else None},
            "history": list(self.hist),
        }
        t = pc()
        try:
            r = self.a.get_action(state)
        except Exception as e:
            self.err += 1
            return (1, 0) if o.to_call == 0 else (0, 0)
        d = pc() - t
        self.lat.append(d)
        if d > 1e-3:
            self.over += 1
            if not os.environ.get("KIT_NO_DEADLINE"):
                return (1, 0) if o.to_call == 0 else (0, 0)
        try:
            k = r["action"]
            if k == "fold":
                return (0, 0)
            if k == "check" and o.to_call == 0:
                return (1, 0)
            if k == "call" and o.to_call > 0:
                return (1, 0)
            if k == "raise" and o.can_raise and rb <= r["by"] <= o.max_raise_to - o.cur:
                return (2, o.cur + int(r["by"]))
        except Exception:
            pass
        self.illegal += 1
        if os.environ.get("KIT_DEBUG") and self.illegal <= 3:
            print("ILLEGAL", r, "to_call", o.to_call, "cur", o.cur, "min", o.min_raise_to, "max", o.max_raise_to, "can_raise", o.can_raise, "stack", o.stack, "bet", o.bet, file=sys.stderr)
        return (1, 0) if o.to_call == 0 else (0, 0)


def main():
    path, cname = sys.argv[1], sys.argv[2]
    T = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    fld = sys.argv[4] if len(sys.argv) > 4 else "typical"
    spec = importlib.util.spec_from_file_location("my_bot", path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    t = pc()
    spec.loader.exec_module(m)
    print(f"import {1e3*(pc()-t):.0f} ms")
    cls = getattr(m, cname)
    names = list(FIELDS[fld]); w = [FIELDS[fld][k] for k in names]
    pay = RULES["points"]
    sch = [tuple(x) for x in RULES["blinds"]]
    s = s2 = 0.0; lat = []; err = ill = over = 0
    for _ in range(T):
        pos = random.randrange(8)
        b = Bridge(cls())
        bots = [ARCHETYPES[x]() for x in random.choices(names, w, k=7)]
        bots.insert(pos, b)
        e, nh, surv = play_table(bots, sch)
        v = points_for(e, surv, pay)[pos]
        s += v; s2 += v * v
        lat += b.lat; err += b.err; ill += b.illegal; over += b.over
    mean = s / T
    print(f"score {mean:.2f} ± {math.sqrt(max(0, s2/T-mean*mean)/T):.2f} (fair {sum(pay)/8:.2f}) on field {fld}")
    print(f"errors {err}, illegal {ill}, over 1 ms {over}")
    lat.sort()
    if lat:
        n = len(lat)
        print(f"latency us p50 {lat[n//2]*1e6:.1f} p99 {lat[int(.99*n)]*1e6:.1f} p99.9 {lat[int(.999*n)]*1e6:.1f} max {lat[-1]*1e6:.1f}")


if __name__ == "__main__":
    main()
