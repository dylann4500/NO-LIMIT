"""Independent dev simulator (written from the kit README only) for testing against archetype opponents.

usage: .venv/bin/python lab/field_bots/claude_default_d/dev/sim.py --tables 400 --field tag,tag,lag,station,nit,maniac,flaky \
           --me lab/field_bots/claude_default_d [--me2 path_to_other_agent_dir] [--copies 1]

Plays 8-seat sit-and-gos (2000 chips, 10/20 rising every 20 hands, cap 250, 50/30/20) with the SDK
objects from lab/fake_sdk, reports mean points per bot type.
"""
import argparse, importlib.util, math, os, random, sys, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
BOT = os.path.dirname(HERE)
LAB = os.path.dirname(os.path.dirname(BOT))
sys.path.insert(0, os.path.join(LAB, "fake_sdk"))
sys.path.insert(0, HERE)
import eval7
import poker_agent_sdk as sdk
from poker_agent_sdk import ActionKind, LegalAction, Event, Seat, Config, State

SCHEDULE = [[10, 20], [15, 30], [25, 50], [40, 80], [60, 120], [100, 200], [150, 300], [250, 500]]
PAYOUTS = [50, 30, 20, 0, 0, 0, 0, 0]
DECK = [r + s for r in "23456789TJQKA" for s in "shdc"]
EC = {c: eval7.Card(c) for c in DECK}


def load_agent(path, name):
    path = os.path.abspath(path)
    spec = importlib.util.spec_from_file_location(name, os.path.join(path, "agent.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    sys.path.insert(0, path)
    spec.loader.exec_module(mod)
    sys.path.remove(path)
    return mod.Agent


def icm(stacks, pay):
    n = len(stacks)
    tot = float(sum(stacks))
    k = min(len([p for p in pay if p > 0]), n)
    out = [0.0] * n

    def rec(rem, used, p, prob):
        for i in range(n):
            if used >> i & 1 or stacks[i] <= 0:
                continue
            pi = prob * stacks[i] / rem
            out[i] += pi * pay[p]
            if p + 1 < k:
                rec(rem - stacks[i], used | (1 << i), p + 1, pi)

    rec(tot, 0, 0, 1.0)
    return out


class Table:
    def __init__(self, bots, rng, hand_cap=250, stats=None):
        self.bots = bots
        self.n = len(bots)
        self.rng = rng
        self.stacks = [2000] * self.n
        self.mem = [b""] * self.n
        self.log = []
        self.ptr = [0] * self.n
        self.hand_cap = hand_cap
        self.bust_groups = []
        self.button = rng.randrange(self.n)
        self.tid = "t%d" % rng.randrange(10 ** 9)
        self.stats = stats if stats is not None else {"dec": 0, "fail": 0, "lat": []}

    def ev(self, kind, seat=None, amount=None, cards=None):
        e = Event(kind, seat, amount, cards)
        self.log.append(e)
        self.hand_log.append(e)

    def next_alive(self, s):
        for d in range(1, self.n + 1):
            x = (s + d) % self.n
            if self.stacks[x] > 0 or self.bet_total.get(x, 0) > 0:
                return x
        return s

    def run(self):
        hand_no = 0
        while True:
            alive = [i for i in range(self.n) if self.stacks[i] > 0]
            if len(alive) <= 1 or hand_no >= self.hand_cap:
                break
            hand_no += 1
            self.play_hand(hand_no)
        alive = [i for i in range(self.n) if self.stacks[i] > 0]
        pts = [0.0] * self.n
        place = self.n
        for g in self.bust_groups:
            g2 = sorted(g, key=lambda x: x[1])  # fewer start chips -> lower place
            for s, _ in g2:
                pts[s] = PAYOUTS[place - 1]
                place -= 1
        if len(alive) == 1:
            pts[alive[0]] = PAYOUTS[0]
        elif alive:
            eq = icm([self.stacks[i] for i in alive], PAYOUTS[:len(alive)])
            for j, i in enumerate(alive):
                pts[i] = eq[j]
        return pts, hand_no

    def play_hand(self, hand_no):
        n = self.n
        self.hand_log = []
        lvl = min((hand_no - 1) // 20, len(SCHEDULE) - 1)
        sbv, bbv = SCHEDULE[lvl]
        self.blinds = (sbv, bbv, lvl + 1, 20 - (hand_no - 1) % 20)
        self.hand_no = hand_no
        alive = [i for i in range(n) if self.stacks[i] > 0]
        start = {i: self.stacks[i] for i in alive}
        self.bet_total = {}
        # button
        b = self.button
        for d in range(1, n + 1):
            x = (b + d) % n
            if self.stacks[x] > 0:
                b = x
                break
        if hand_no == 1:
            b = self.button if self.stacks[self.button] > 0 else b
        self.button = b
        if len(alive) == 2:
            sb = b
            bb = [x for x in alive if x != b][0]
        else:
            sb = self.nx(b, alive)
            bb = self.nx(sb, alive)
        self.status = {i: ("active" if i in alive else "busted") for i in range(n)}
        self.bets = {i: 0 for i in range(n)}
        self.contrib = {i: 0 for i in range(n)}
        deck = DECK[:]
        self.rng.shuffle(deck)
        self.hole = {}
        for i in alive:
            self.hole[i] = [deck.pop(), deck.pop()]
        self.board = []
        self.ev("hand", None, hand_no)
        self.post(sb, sbv)
        self.post(bb, bbv)
        # preflop
        first = self.nx(bb, alive) if len(alive) > 2 else sb
        done = self.betting(first, bbv, preflop=True)
        for street, cnt in ((1, 3), (2, 1), (3, 1)):
            if done:
                break
            new = [deck.pop() for _ in range(cnt)]
            self.board += new
            self.ev("board", None, None, new)
            self.bets = {i: 0 for i in range(n)}
            if sum(1 for i in alive if self.status[i] == "active") >= 2:
                done = self.betting(self.nx(b, alive), bbv, preflop=False)
        # run out the board if needed
        live = [i for i in alive if self.status[i] in ("active", "all_in")]
        if len(live) >= 2:
            while len(self.board) < 5:
                c = deck.pop()
                self.board.append(c)
                self.ev("board", None, None, [c])
        self.showdown(alive, live)
        busted = [(i, start[i]) for i in alive if self.stacks[i] <= 0]
        if busted:
            self.bust_groups.append(busted)
        for i in range(n):
            if i in alive:
                self.ev("stack", i, self.stacks[i])

    def nx(self, s, alive):
        for d in range(1, self.n + 1):
            x = (s + d) % self.n
            if x in alive:
                return x
        return s

    def post(self, s, amt):
        a = min(amt, self.stacks[s])
        self.stacks[s] -= a
        self.bets[s] += a
        self.contrib[s] += a
        if self.stacks[s] == 0:
            self.status[s] = "all_in"
        self.ev("blind", s, a)

    def pot(self):
        return sum(self.contrib.values())

    def betting(self, first, bbv, preflop):
        n = self.n
        order = [(first + d) % n for d in range(n)]
        curbet = max(self.bets.values())
        last_raise = bbv
        pending = [i for i in order if self.status[i] == "active"]
        if preflop:
            pass
        # if only one active and nobody to match, skip
        while pending:
            actives = [i for i in range(n) if self.status[i] == "active"]
            notfold = [i for i in range(n) if self.status[i] in ("active", "all_in")]
            if len(notfold) <= 1:
                return True
            p = pending.pop(0)
            if self.status[p] != "active":
                continue
            to_call = curbet - self.bets[p]
            if len(actives) == 1 and to_call <= 0:
                continue
            legal = []
            if to_call > 0:
                legal.append(LegalAction(ActionKind.FOLD))
                legal.append(LegalAction(ActionKind.CALL))
            else:
                legal.append(LegalAction(ActionKind.CHECK))
            others_can_act = any(self.status[i] == "active" for i in range(n) if i != p)
            if self.stacks[p] > to_call and others_can_act:
                mn = curbet + last_raise if curbet > 0 else bbv
                mx = self.bets[p] + self.stacks[p]
                mn = min(mn, mx)
                legal.append(LegalAction(ActionKind.RAISE, mn, mx))
            kind, amt = self.ask(p, legal, to_call)
            if kind == ActionKind.FOLD:
                self.status[p] = "folded"
                self.ev("fold", p)
            elif kind == ActionKind.CHECK:
                self.ev("check", p)
            elif kind == ActionKind.CALL:
                a = min(to_call, self.stacks[p])
                self.stacks[p] -= a
                self.bets[p] += a
                self.contrib[p] += a
                if self.stacks[p] == 0:
                    self.status[p] = "all_in"
                self.ev("call", p, a)
            else:
                t = amt
                add = t - self.bets[p]
                self.stacks[p] -= add
                self.bets[p] = t
                self.contrib[p] += add
                if t - curbet >= last_raise:
                    last_raise = t - curbet
                curbet = t
                if self.stacks[p] == 0:
                    self.status[p] = "all_in"
                self.ev("raise", p, t)
                idx = order.index(p)
                pending = [order[(idx + d) % n] for d in range(1, n) if self.status[order[(idx + d) % n]] == "active"]
        notfold = [i for i in range(n) if self.status[i] in ("active", "all_in")]
        return len(notfold) <= 1

    def ask(self, p, legal, to_call):
        bot = self.bots[p]
        seats = [Seat(i, self.stacks[i], self.bets[i], self.status[i], []) for i in range(self.n)]
        cfg = Config(table_id=self.tid, seat=p, variant="holdem", players=self.n, starting_stack=2000,
                     blinds=SCHEDULE, hands_per_level=20, hand_cap=self.hand_cap, payouts=PAYOUTS,
                     decision_ms=1, time_bank_ms=100, memory_bytes=65536)
        sbv, bbv, lvl, hun = self.blinds
        evs = self.log[self.ptr[p]:]
        st = State(seat=p, cards=list(self.hole[p]), board=list(self.board), pot=self.pot(), to_call=to_call,
                   legal_actions=legal, history=list(self.hand_log), phase="betting", seats=seats,
                   button=self.button, blind_level=lvl, blinds=[sbv, bbv], hands_until_next_level=hun,
                   hand_number=self.hand_no, players_remaining=sum(1 for i in range(self.n) if self.status[i] != "busted"),
                   bust_order=[], config=cfg, time_bank_ms=100, events=list(evs), variant="holdem")
        t0 = time.perf_counter()
        ok = True
        try:
            res = bot.act(st, self.mem[p])
            action, mem = res
        except Exception as e:
            ok = False
            action, mem = None, None
        dt = time.perf_counter() - t0
        if getattr(bot, "_track", False):
            self.stats["dec"] += 1
            self.stats["lat"].append(dt)
        kind = None
        amt = None
        if ok and action is not None:
            kind = action.kind
            amt = action.amount
            la = None
            for l in legal:
                if l.kind == kind:
                    la = l
            if la is None:
                ok = False
            elif kind == ActionKind.RAISE:
                if not isinstance(amt, int) or amt < la.min_amount or amt > la.max_amount:
                    ok = False
        if not ok:
            if getattr(bot, "_track", False):
                self.stats["fail"] += 1
            kind = ActionKind.CHECK if to_call <= 0 else ActionKind.FOLD
            amt = None
        else:
            self.ptr[p] = len(self.log)
            if mem is not None:
                self.mem[p] = bytes(mem)[:65536]
        return kind, amt

    def showdown(self, alive, live):
        n = self.n
        if len(live) == 1:
            w = live[0]
            tot = self.pot()
            self.stacks[w] += tot
            self.ev("win", w, tot)
            return
        vals = {}
        bc = [EC[c] for c in self.board]
        for i in live:
            vals[i] = eval7.evaluate([EC[self.hole[i][0]], EC[self.hole[i][1]]] + bc)
            self.ev("show", i, None, list(self.hole[i]))
        levels = sorted(set(self.contrib[i] for i in live if self.contrib[i] > 0))
        prev = 0
        contrib = dict(self.contrib)
        for lv in levels:
            layer = 0
            for i in range(n):
                c = min(contrib[i], lv) - min(contrib[i], prev)
                if c > 0:
                    layer += c
            elig = [i for i in live if self.contrib[i] >= lv]
            best = max(vals[i] for i in elig)
            winners = [i for i in elig if vals[i] == best]
            share = layer // len(winners)
            rem = layer - share * len(winners)
            for k, w in enumerate(winners):
                self.stacks[w] += share + (1 if k < rem else 0)
                self.ev("win", w, share)
            prev = lv
        # uncontested excess (folded players' contributions above all live levels)
        top = levels[-1] if levels else 0
        extra = sum(max(0, self.contrib[i] - top) for i in range(n))
        if extra:
            best = max(live, key=lambda i: vals[i])
            self.stacks[best] += extra


def make_bot(kind, me_cls, me2_cls, seed=None):
    import opponents
    if kind == "me":
        b = me_cls()
        b._track = True
        return b
    if kind == "me2":
        return me2_cls()
    return opponents.make(kind, seed)


def run_chunk(args):
    seed, ntab, field, me_path, me2_path, copies = args
    rng = random.Random(seed)
    me_cls = load_agent(me_path, "me_agent")
    me2_cls = load_agent(me2_path, "me2_agent") if me2_path else None
    res = {}
    stats = {"dec": 0, "fail": 0, "lat": []}
    hands = 0
    for t in range(ntab):
        kinds = ["me"] * copies + list(field)
        kinds = kinds[:8]
        rng.shuffle(kinds)
        bots = [make_bot(k, me_cls, me2_cls, rng.random()) for k in kinds]
        tab = Table(bots, rng, stats=stats)
        pts, h = tab.run()
        hands += h
        for k, p in zip(kinds, pts):
            res.setdefault(k, []).append(p)
    lat = sorted(stats["lat"])
    return res, stats["dec"], stats["fail"], lat[-200:] if lat else [], lat[len(lat) // 2] if lat else 0, hands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", type=int, default=200)
    ap.add_argument("--field", default="tag,tag,lag,station,nit,maniac,flaky")
    ap.add_argument("--me", default=BOT)
    ap.add_argument("--me2", default=None)
    ap.add_argument("--copies", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--procs", type=int, default=14)
    a = ap.parse_args()
    field = a.field.split(",")
    per = max(1, a.tables // a.procs)
    jobs = [(a.seed * 1000 + i, per, field, a.me, a.me2, a.copies) for i in range(a.procs)]
    t0 = time.time()
    with Pool(a.procs) as p:
        outs = p.map(run_chunk, jobs)
    res = {}
    dec = fail = hands = 0
    lat_top = []
    meds = []
    for r, d, f, lt, med, h in outs:
        for k, v in r.items():
            res.setdefault(k, []).extend(v)
        dec += d
        fail += f
        hands += h
        lat_top += lt
        meds.append(med)
    print("tables %d  time %.1fs  avg hands %.1f" % (per * a.procs, time.time() - t0, hands / (per * a.procs)))
    for k in sorted(res, key=lambda k: -sum(res[k]) / len(res[k])):
        v = res[k]
        m = sum(v) / len(v)
        sd = math.sqrt(max(0.0, sum(x * x for x in v) / len(v) - m * m) / len(v))
        print("  %-10s n=%5d  mean %6.2f  se %.2f" % (k, len(v), m, sd))
    lat_top.sort()
    print("me decisions %d fails %d  median %.0fus  max %.0fus" % (dec, fail, sorted(meds)[len(meds) // 2] * 1e6,
                                                                  (lat_top[-1] * 1e6 if lat_top else 0)))


if __name__ == "__main__":
    main()
