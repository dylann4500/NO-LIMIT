"""Discard variants (lab/variants/DISCARD.md): which hole card to drop, and how to say so to the platform.

Self-contained, stdlib only. v2 loads it from core/agent.py; make_bot.py inlines this file into the Plan B bot, so
every name here starts with `_d` or `discard`/`DISCARD` to stay clear of the bot's own globals.

    discard_choice(hole, board, to_come, n_after, villains, deadline)  index into hole of the card to drop
    discard_action(state, Action, deadline)                           the platform Action for a discard-like turn,
                                                                     or None when this turn is not one
    discard_to_come(board, history)                                   betting rounds: board cards still to be dealt

Cards are ints, rank * 4 + suit (2 = 0 .. A = 12, suits shdc), as in lab/pk.py and core/engine.py.

KIT: everything the real kit decides is in the constants below. Check them against RULES.md at kickoff.
"""
import random as _drandom
import time as _dtime

DISCARD_KINDS = ("discard",)  # KIT: legal action kind name(s) of a discard (enum value or name, case-insensitive)
DISCARD_INDEX = True  # KIT: True: Action(kind, i) drops state.cards[i]. False: Action(kind, "Ks") names the card.
DISCARD_TO_BOARD = True  # KIT: MIT 2026: a discard goes face up onto the board and plays for everyone
DISCARD_DEALT = 4  # KIT: board cards dealt in a hand, discards excluded (MIT 2026: 2-card flop, turn, river)
DISCARD_BUDGET_S = 0.0003  # time for one discard decision

# ---- evaluator on summed card keys (as lab/pk.py): base-5 rank counts above bit 16, 4-bit suit counters below ------
_DP5 = [5 ** r for r in range(13)]
_DKEY = [(_DP5[c >> 2] << 16) + (1 << (4 * (c & 3))) for c in range(52)]
_DBIT = [1 << (c >> 2) for c in range(52)]
_DSTR = [0b1111100000000 >> i for i in range(9)] + [0b1000000001111]


def _dsh(m):
    for i, s in enumerate(_DSTR):
        if m & s == s:
            return 12 - i if i < 9 else 3
    return -1


_DMS = [_dsh(m) for m in range(8192)]


def _dtop(m, n):
    o = 0
    for r in range(12, -1, -1):
        if m >> r & 1:
            o = o * 13 + r
            n -= 1
            if not n:
                break
    return o * 13 ** n


_DFL = [0] * 8192
for _dm in range(8192):
    if bin(_dm).count("1") >= 5:
        _ds = _DMS[_dm]
        _DFL[_dm] = (8 << 20) + _ds if _ds >= 0 else (5 << 20) + _dtop(_dm, 5)


def _drv(key):
    """Value of a non-flush rank multiset, base-5 encoded."""
    cnt = [(key // _DP5[r]) % 5 for r in range(13)]
    m, q, t, p = 0, [], [], []
    for r in range(12, -1, -1):
        c = cnt[r]
        if c:
            m |= 1 << r
        if c == 4:
            q.append(r)
        elif c == 3:
            t.append(r)
        elif c == 2:
            p.append(r)
    if q:
        return (7 << 20) + q[0] * 13 + _dtop(m & ~(1 << q[0]), 1)
    if t and (len(t) > 1 or p):
        return (6 << 20) + t[0] * 13 + max(t[1:] + p)
    s = _DMS[m]
    if s >= 0:
        return (4 << 20) + s
    if t:
        return (3 << 20) + t[0] * 169 + _dtop(m & ~(1 << t[0]), 2)
    if len(p) >= 2:
        return (2 << 20) + p[0] * 169 + p[1] * 13 + _dtop(m & ~(1 << p[0]) & ~(1 << p[1]), 1)
    if p:
        return (1 << 20) + p[0] * 2197 + _dtop(m & ~(1 << p[0]), 3)
    return _dtop(m, 5)


_DRC = {}
_DRC_MAX = 40000  # cache cap: 8-10 card rank sets are many, and each dict resize past ~44k entries stalls for a millisecond


def _dslow(k, a, b):
    """Value for a key whose suit counters may hold a flush; a and b are the cards (two lists, read only here)."""
    low = k & 0xFFFF
    for s in range(4):
        if (low >> (4 * s)) & 15 >= 5:
            m = 0
            for c in a:
                if c & 3 == s:
                    m |= _DBIT[c]
            for c in b:
                if c & 3 == s:
                    m |= _DBIT[c]
            return _DFL[m]
    return _dfill(k >> 16)


def _dfill(r):
    v = _drv(r)
    if len(_DRC) < _DRC_MAX:
        _DRC[r] = v
    return v


def _dval(k, a, b):
    """Best five of the cards whose keys sum to k (standard ranks); a and b hold those cards, read only for a flush."""
    if (k + 0x3333) & 0x8888:
        return _dslow(k, a, b)
    v = _DRC.get(k >> 16)
    if v is None:
        v = _dfill(k >> 16)
    return v


_DRNG = _drandom.Random(20261106)


def discard_choice(hole, board, to_come=2, n_after=0, villains=None, deadline=None, deck=None, to_board=None,
                   max_samples=600):
    """Index into `hole` of the card to drop: the one whose kept cards have the best heads-up showdown equity against
    a villain hand, by Monte Carlo with common random numbers (every option is scored on the same villain hands and
    runouts, so their differences are far less noisy than each estimate).

    hole, board   card ints; board holds everything public now (flop and earlier discards)
    to_come       board cards still to be dealt after the discards (MIT 2026: turn and river)
    n_after       players who discard after us; with discards on the board each adds an unknown board card
    villains      optional list of villain hands (tuples of card ints, any length: a longer hand plays its best two
                  with the board, standing in for the discard it makes); default uniform random two-card hands
    deadline      time.perf_counter() value to stop at (default now + DISCARD_BUDGET_S); at least 8 samples
    to_board      whether our discard goes on the board (default DISCARD_TO_BOARD)
    """
    n = len(hole)
    if n <= 1:
        return 0
    pc = _dtime.perf_counter
    if deadline is None:
        deadline = pc() + DISCARD_BUDGET_S
    if to_board is None:
        to_board = DISCARD_TO_BOARD
    K, V, R = _DKEY, _dval, _DRNG.random
    known = set(hole)
    known.update(board)
    rest = [c for c in (deck or range(52)) if c not in known]
    L = len(rest)
    keep = [[c for j, c in enumerate(hole) if j != i] for i in range(n)]
    drop = [hole[i] for i in range(n)]
    kk = [sum(K[c] for c in kp) for kp in keep]
    dk = [K[d] if to_board else 0 for d in drop]
    bk = sum(K[c] for c in board)
    extra = max(0, to_come) + (max(0, n_after) if to_board else 0)
    vl = None
    if villains:
        vl = [tuple(v) for v in villains if known.isdisjoint(v)]
        if not vl:
            vl = None
    nv = len(vl) if vl else 0
    wins = [0.0] * n
    cnt = 0
    bl = list(board)
    RC = _DRC
    hb = [keep[i] + ([drop[i]] if to_board else []) for i in range(n)]
    db = [[drop[i]] if to_board else [] for i in range(n)]
    pairs = None
    while cnt < max_samples:
        if cnt >= 8 and not cnt & 3 and pc() > deadline:  # a cold rank cache makes early samples slow
            break
        # villain hand, then the unknown board cards, all distinct
        if vl:
            v = vl[int(R() * nv)]
        else:
            a = rest[int(R() * L)]
            b = a
            while b == a:
                b = rest[int(R() * L)]
            v = (a, b)
        if extra:
            add = []
            while len(add) < extra:
                c = rest[int(R() * L)]
                if c not in v and c not in add:
                    add.append(c)
            rk = bk
            for c in add:
                rk += K[c]
            run = bl + add
        else:
            rk, run = bk, bl
        if len(v) == 2:
            vk = rk + K[v[0]] + K[v[1]]
            for i in range(n):
                k = rk + dk[i] + kk[i]
                if (k + 0x3333) & 0x8888:
                    h = _dslow(k, run, hb[i])
                else:
                    h = RC.get(k >> 16)
                    if h is None:
                        h = _dfill(k >> 16)
                k = vk + dk[i]
                if (k + 0x3333) & 0x8888:
                    x = _dslow(k, run, v + tuple(db[i]))
                else:
                    x = RC.get(k >> 16)
                    if x is None:
                        x = _dfill(k >> 16)
                if h > x:
                    wins[i] += 1.0
                elif h == x:
                    wins[i] += 0.5
        else:
            if pairs is None or pairs[0] is not v:
                pairs = (v, [(p, q) for j, p in enumerate(v) for q in v[j + 1:]])
            for i in range(n):
                h = _dval(rk + dk[i] + kk[i], run, hb[i])
                x = max(_dval(rk + dk[i] + K[p] + K[q], run, (p, q, *db[i])) for p, q in pairs[1])
                if h > x:
                    wins[i] += 1.0
                elif h == x:
                    wins[i] += 0.5
        cnt += 1
    # ties: keep the higher cards (drop the lowest rank)
    best = max(range(n), key=lambda i: (wins[i], -(drop[i] >> 2)))
    return best


def discard_naive(hole):
    """Baseline: drop the lowest card."""
    return min(range(len(hole)), key=lambda i: hole[i] >> 2)


# ---- platform side -----------------------------------------------------------------------------------------------
_DINT = {r + s: i * 4 + j for i, r in enumerate("23456789TJQKA") for j, s in enumerate("shdc")}


def _dcard(c):
    v = _DINT.get(c)
    if v is None:
        c = str(c).strip()
        r = c[:-1].upper()
        v = _DINT[("T" if r == "10" else r) + c[-1].lower()]
    return v


def _dkind(k):
    return str(getattr(k, "value", k)).lower().rsplit(".", 1)[-1]


def _dget(o, k, d=None):
    v = o.get(k) if isinstance(o, dict) else getattr(o, k, None)
    return d if v is None else v


def discard_legal(state):
    """The discard-like legal action of this turn, or None. Discard-like: its kind is in DISCARD_KINDS, or the phase is
    not betting and the one offered kind is neither a betting kind nor something we know."""
    legal = list(_dget(state, "legal_actions", ()) or ())
    for a in legal:
        if _dkind(a.kind) in DISCARD_KINDS:
            return a
    phase = _dkind(_dget(state, "phase", "betting"))
    if phase != "betting" and "discard" in phase and len(legal) == 1:
        a = legal[0]
        if _dkind(a.kind) not in ("fold", "check", "call", "raise", "raise_to", "bet"):
            return a
    return None


def discard_to_come(board, history):
    """Board cards still to be dealt in a discard variant: DISCARD_DEALT minus the dealt cards on the board (the board
    minus the discards on it, known from discard events in this hand's history)."""
    nd, dc = 0, set()
    for e in history or ():
        if _dkind(_dget(e, "kind", "")) in DISCARD_KINDS:
            nd += 1
            for c in _dget(e, "cards", ()) or ():
                dc.add(str(c))
    if dc:
        on = sum(1 for c in board if str(c) in dc)
    else:
        on = nd if DISCARD_TO_BOARD else 0
    return max(0, DISCARD_DEALT - (len(board) - on))


def discard_action(state, Action, deadline=None, villains=None):
    """The Action for a discard-like turn (None if this turn is not one). Never raises past a legal fallback."""
    la = discard_legal(state)
    if la is None:
        return None
    lo = int(_dget(la, "min_amount", 0) or 0)
    try:
        names = list(_dget(state, "cards", ()))
        hole = [_dcard(c) for c in names]
        bnames = list(_dget(state, "board", ()) or ())
        board = [_dcard(c) for c in bnames]
        hist = _dget(state, "history", ()) or ()
        seats = _dget(state, "seats", ()) or ()
        in_hand = sum(1 for s in seats if _dkind(_dget(s, "status", "active")) in ("active", "all_in", "allin"))
        done = sum(1 for e in hist if _dkind(_dget(e, "kind", "")) in DISCARD_KINDS)
        n_after = max(0, in_hand - 1 - done)
        to_come = max(0, DISCARD_DEALT - (len(board) - (done if DISCARD_TO_BOARD else 0)))
        i = discard_choice(hole, board, to_come, n_after, villains, deadline)
        if DISCARD_INDEX:
            hi = int(_dget(la, "max_amount", len(hole) - 1) or 0)
            if not lo <= i <= hi:
                i = lo
            return Action(la.kind, i)
        return Action(la.kind, names[i])
    except Exception:
        return Action(la.kind, lo)

