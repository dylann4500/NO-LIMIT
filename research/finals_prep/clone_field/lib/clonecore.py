"""Shared core of the clone bots: the hand tracker that names the situation a seat is in
(used identically by the fitter on hand histories and by the clone on GameState.history),
cheap hand-strength measures, and the generic clone policy driven by a parameter table."""
import bisect
import json
import os
import zlib

import eval7

HERE = os.path.dirname(os.path.abspath(__file__))
RANKS = "23456789TJQKA"
RI = {r: i for i, r in enumerate(RANKS)}
CARD = {r + s: eval7.Card(r + s) for r in RANKS for s in "cdhs"}
DECK = list(CARD.values())
ACT_I = {"F": 0, "C": 1, "R": 2, "J": 3}


def sbk(x):
    return 0 if x < 6 else 1 if x < 10 else 2 if x < 16 else 3 if x < 28 else 4 if x < 50 else 5


class Track:
    """Replays one hand's public events. key(seat) names the decision the seat faces now."""
    __slots__ = ("n", "left", "live", "com", "pot", "cur", "street", "folded", "raises",
                 "raised_pf", "vol", "jam_live", "aggr", "prev_aggr", "acted", "bb", "blind", "nlive")

    def __init__(self, stacks, bb):
        n = len(stacks)
        self.n = n
        self.left = list(stacks)
        self.live = [s > 0 for s in stacks]
        self.nlive = sum(self.live)
        self.com = [0] * n
        self.pot = 0
        self.cur = 0
        self.street = 0
        self.folded = [not x for x in self.live]
        self.raises = 0
        self.raised_pf = [False] * n
        self.vol = [False] * n
        self.jam_live = False
        self.aggr = None
        self.prev_aggr = None
        self.acted = [False] * n
        self.bb = bb or 1
        self.blind = [0] * n

    def apply(self, k, s, amt):
        if k == "fold":
            self.folded[s] = True
            self.acted[s] = True
        elif k == "check":
            self.acted[s] = True
        elif k == "call":
            self.left[s] -= amt
            self.com[s] += amt
            self.pot += amt
            self.acted[s] = True
            if self.street == 0:
                self.vol[s] = True
        elif k == "raise":
            inc = amt - self.com[s]
            self.left[s] -= inc
            self.pot += inc
            self.com[s] = amt
            self.acted[s] = True
            if amt > self.cur:
                self.cur = amt
                self.raises += 1
                self.jam_live = self.left[s] <= 0
                self.aggr = s
            if self.street == 0:
                self.raised_pf[s] = True
        elif k == "board":
            self.street += 1
            self.com = [0] * self.n
            self.cur = 0
            self.prev_aggr = self.aggr
            self.aggr = None
            self.raises = 0
            self.jam_live = False
            self.acted = [False] * self.n
        elif k == "blind":
            self.left[s] -= amt
            self.com[s] += amt
            self.pot += amt
            self.blind[s] = amt
            if self.com[s] > self.cur:
                self.cur = self.com[s]
        elif k == "ante":
            self.left[s] -= amt
            self.pot += amt

    def cls(self, k, s, amt):
        """Class of a betting action about to be applied: F, C (check/call), R (raise), J (all-in raise)."""
        if k == "fold":
            return "F"
        if k == "raise":
            return "J" if amt - self.com[s] >= self.left[s] else "R"
        return "C"

    def key(self, s):
        left = self.left[s]
        tc = self.cur - self.com[s]
        if tc > left:
            tc = left
        bb = self.bb
        if self.street == 0:
            al = 1 if self.nlive <= 4 else 0
            if self.raises == 0:
                behind = 0
                for t in range(self.n):
                    if t != s and not self.folded[t] and not self.acted[t]:
                        behind += 1
                pos = behind if behind < 4 else 4 if behind < 6 else 5
                return "U%d%d%d" % (pos, sbk((left + self.com[s]) / bb), al)
            if self.jam_live or tc >= 0.4 * left:
                x = tc / bb
                cb = 0 if x < 5 else 1 if x < 10 else 2 if x < 18 else 3 if x < 35 else 4
                return "A%d%d%d" % (cb, 1 if self.raised_pf[s] else 0, al)
            if self.raises == 1:
                role = 2 if self.vol[s] else 1 if self.blind[s] else 0
                return "O%d%d" % (role, sbk((left + self.com[s]) / bb))
            x = (left + self.com[s]) / bb
            return "T%d%d%d" % (1 if self.raised_pf[s] else 0, min(self.raises, 3) - 2,
                                0 if x < 16 else 1 if x < 40 else 2)
        nopp = 0
        for t in range(self.n):
            if t != s and not self.folded[t]:
                nopp += 1
        multi = 1 if nopp >= 2 else 0
        if tc <= 0:
            return "K%d%d%d%d" % (self.street, multi, 1 if self.prev_aggr == s else 0,
                                  1 if left < self.pot else 0)
        base = self.pot - tc
        frac = tc / base if base > 0 else 9.0
        sz = 0 if frac < 0.3 else 1 if frac < 0.6 else 2 if frac < 1.0 else 3
        return "B%d%d%d%d%d" % (self.street, multi, sz, 1 if self.com[s] > 0 else 0,
                                1 if tc >= 0.5 * left else 0)

    def size(self, key, amt, s):
        """(size kind, value) of a non-all-in raise about to be applied in situation `key`."""
        c = key[0]
        if c == "U":
            return "sU", amt / self.bb
        if c == "K":
            return "sK" + key[1], amt / (self.pot or 1)
        if c == "B":
            return "sB", amt / (self.cur or 1)
        return "sO", amt / (self.cur or 1)


# ---------------------------------------------------------------- hand strength
def pre_key(cards):
    """Class of a 3-card starting hand: ranks high to low + which pairs of cards are suited."""
    c = sorted(cards, key=lambda x: -RI[x[0]])
    r = [RI[x[0]] for x in c]
    s12, s13, s23 = c[0][1] == c[1][1], c[0][1] == c[2][1], c[1][1] == c[2][1]
    if r[0] == r[1] and r[1] == r[2]:
        s12 = s13 = s23 = False
    elif r[0] == r[1]:
        s13, s23 = (s13 or s23), False
    elif r[1] == r[2]:
        s12, s13 = (s12 or s13), False
    return "%s%s%s%d%d%d" % (c[0][0], c[1][0], c[2][0], s12, s13, s23)


try:
    with open(os.path.join(HERE, "pre3.json")) as _f:
        PRE3 = json.load(_f)
except OSError:
    PRE3 = {}


def draw_outs(cards):
    """Rough outs of a flush or straight draw in `cards` (strings), 0 if none."""
    suits = {}
    for c in cards:
        suits[c[1]] = suits.get(c[1], 0) + 1
    outs = 9 if max(suits.values()) == 4 else 0
    mask = 0
    for c in cards:
        mask |= 1 << (RI[c[0]] + 1)
    if mask & (1 << 13):
        mask |= 1
    need = set()
    for lo in range(0, 10):
        w = (mask >> lo) & 31
        if w == 31:
            return outs
        if bin(w).count("1") == 4:
            miss = (~w) & 31
            need.add(lo + miss.bit_length() - 1)
    if need:
        outs += 8 if len(need) >= 2 else 4
    return outs


def raw_strength(mine, board, exposed, dead):
    """P(currently ahead of every opponent), each opponent holding its exposed card plus a
    uniformly random unseen card, nudged up for flush/straight draws before the river."""
    seen = set(mine) | set(board) | set(exposed) | set(dead)
    unseen = [CARD[c] for c in CARD if c not in seen]
    b = [CARD[c] for c in board]
    ev = eval7.evaluate
    my = ev(b + [CARD[c] for c in mine])
    q = 1.0
    n2 = 2.0 * len(unseen)
    for x in exposed:
        bx = b + [CARD[x], None]
        w = 0
        for c in unseen:
            bx[-1] = c
            v = ev(bx)
            if my > v:
                w += 2
            elif my == v:
                w += 1
        q *= w / n2
    if len(board) < 5 and (my >> 24) < 4:
        o = draw_outs(list(mine) + list(board))
        if o:
            q += (1.0 - q) * o * (0.035 if len(board) == 3 else 0.02)
    return q


def keep_score(pair, flop):
    v = eval7.evaluate([CARD[c] for c in pair] + [CARD[c] for c in flop])
    if (v >> 24) < 4:
        o = draw_outs(list(pair) + list(flop))
        v += int(o * 0.1 * (1 << 24))
    return v


def hu(*parts):
    return zlib.crc32("|".join(map(str, parts)).encode()) / 4294967296.0


FALLBACK = [0.6, 0.4, 0.0, 0.0]
LOGDIR = os.environ.get("CLONE_QLOG")


_QH = {}


def qlog_handle():
    pid = os.getpid()
    if pid not in _QH:
        _QH[pid] = open(os.path.join(LOGDIR, "q_%d.txt" % pid), "a")
    return _QH[pid]


class Clone:
    """The generic clone policy. `params`: cells (situation -> [F, C, R, J] frequencies),
    sizes (kind -> quantile list), ex_low, and optional cdf (strength quantile maps), eps, beta."""

    def __init__(self, params, action_cls):
        self.P = params
        self.cells = params["cells"]
        self.sizes = params["sizes"]
        self.cdf = params.get("cdf") or {}
        self.eps = params.get("eps", 0.0)
        self.eps_pre = params.get("eps_pre", 0.0)
        self.beta = params.get("beta", [0, 0.0, 0.0, 0.0])
        self.ex_low = params.get("ex_low", 0.5)
        self.A = action_cls
        self.qlog = qlog_handle() if LOGDIR else None

    # -- selection: keep the best two with the flop, expose lower/higher at the fitted rate
    def select(self, state):
        cards = state.cards
        flop = state.board[:3]
        best, bi = -1, (0, 1)
        for i, j in ((0, 1), (0, 2), (1, 2)):
            sc = keep_score((cards[i], cards[j]), flop)
            if sc > best:
                best, bi = sc, (i, j)
        i, j = bi
        d = 3 - i - j
        lo, hi = (i, j) if RI[cards[i][0]] <= RI[cards[j][0]] else (j, i)
        r = lo if hu(cards, state.hand_number, state.config.table_id, "x") < self.ex_low else hi
        return self.A("select", cards=(d, r))

    def act(self, state, memory):
        if state.phase != "betting":
            if state.phase == "select":
                return self.select(state), memory
            first = state.legal_actions[0]
            return self.A(first.kind, first.min_amount), memory
        me = state.seat
        seats = state.seats
        t = Track([1 if s.status != "busted" else 0 for s in seats], state.blinds.big_blind)
        ap = t.apply
        for e in state.history:
            ap(e.kind, e.seat, e.amount)
        t.left = [s.stack for s in seats]
        if t.aggr is not None:
            t.jam_live = seats[t.aggr].status == "all_in"
        key = t.key(me)
        f = self.cells.get(key) or FALLBACK
        hn = state.hand_number
        tid = state.config.table_id
        cards = state.cards
        lo, hi, mst, mq = 0.0, 1.0, -1, 0.0
        if memory:
            try:
                p = memory.split(b",")
                if int(p[0]) == hn:
                    lo, hi, mst, mq = float(p[1]), float(p[2]), int(p[3]), float(p[4])
            except Exception:
                pass
        ndec = len(state.history)
        k0 = key[0]
        if t.street == 0:
            p3 = PRE3.get(pre_key(cards), 0.5)
            u = (p3 - lo) / (hi - lo) if hi > lo else 0.5
            u = 0.0 if u < 0.0 else 1.0 if u > 1.0 else u
            if self.eps_pre and hu(cards, hn, tid, ndec, "e") < self.eps_pre:
                u = hu(cards, hn, tid, ndec, "u")
            a1, a2 = ("J", "R") if (t.left[me] + t.com[me]) < 16 * t.bb else ("R", "J")
            top = 1.0
            if u >= top - f[ACT_I[a1]]:
                act, sl = a1, (top - f[ACT_I[a1]], top)
            elif u >= top - f[2] - f[3]:
                act, sl = a2, (top - f[2] - f[3], top - f[ACT_I[a1]])
            elif u >= f[0]:
                act, sl = "C", (f[0], top - f[2] - f[3])
            else:
                act, sl = "F", (0.0, f[0])
            w = hi - lo
            lo, hi = lo + w * sl[0], lo + w * sl[1]
        else:
            if mst != t.street:
                exposed = [s.shown_cards[0] for s in seats
                           if s.seat != me and s.status in ("active", "all_in") and s.shown_cards]
                mq = raw_strength(cards, state.board, exposed, state.variant.get("discarded") or ())
                mst = t.street
            ck = key[:3]
            if self.qlog:
                self.qlog.write("%s %.4f\n" % (ck, mq))
            tab = self.cdf.get(ck)
            if tab:
                i = bisect.bisect_right(tab, mq)
                j = bisect.bisect_left(tab, mq)
                u = (i + j) / (2.0 * len(tab))
            else:
                u = mq
            if self.eps and hu(cards, hn, tid, ndec, "e") < self.eps:
                u = hu(cards, hn, tid, ndec, "u")
            if k0 == "K":
                b = f[2] + f[3]
                bl = self.beta[t.street] * b
                if u >= 1.0 - (b - bl) or u < bl:
                    act = "J" if hu(cards, hn, tid, ndec, "j") * b < f[3] else "R"
                else:
                    act = "C"
            else:
                r = f[2] + f[3]
                if u >= 1.0 - r:
                    act = "J" if hu(cards, hn, tid, ndec, "j") * r < f[3] else "R"
                elif u >= f[0]:
                    act = "C"
                else:
                    act = "F"
        mem = b"%d,%.5f,%.5f,%d,%.5f" % (hn, lo, hi, mst, mq)
        return self.legal(state, t, key, act, hu(cards, hn, tid, ndec, "s")), mem

    def legal(self, state, t, key, act, us):
        A = self.A
        can = {l.kind: l for l in state.legal_actions}
        if act in ("R", "J") and "raise" in can:
            lg = can["raise"]
            if act == "J":
                return A("raise", lg.max_amount)
            me = state.seat
            k0 = key[0]
            if k0 == "U":
                q = self.sizes.get("sU")
                amt = pick(q, us, 2.5) * t.bb
            elif k0 == "K":
                q = self.sizes.get("sK" + key[1])
                amt = pick(q, us, 0.6) * t.pot
            elif k0 == "B":
                amt = pick(self.sizes.get("sB"), us, 3.0) * t.cur
            else:
                amt = pick(self.sizes.get("sO"), us, 3.0) * t.cur
            amt = int(amt)
            if amt < lg.min_amount:
                amt = lg.min_amount
            if amt >= lg.max_amount:
                amt = lg.max_amount if lg.max_amount <= lg.min_amount else max(lg.min_amount, lg.max_amount - 1)
            return A("raise", amt)
        if act == "F":
            if "check" in can:
                return A("check")
            return A("fold")
        if "check" in can:
            return A("check")
        if "call" in can:
            return A("call")
        return A("fold")


def pick(q, u, default):
    if not q:
        return default
    x = u * (len(q) - 1)
    i = int(x)
    if i >= len(q) - 1:
        return q[-1]
    return q[i] + (q[i + 1] - q[i]) * (x - i)
