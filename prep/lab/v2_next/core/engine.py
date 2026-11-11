"""Variant engine for the v2 core: every call that depends on the poker variant, behind one small interface.

The core (agent.py) never touches card objects, hand ranks or equity code directly. It uses:
    VARIANT, N_HOLE, ENGINE           the variant, hole cards per player, and "eval7" or "stdlib"
    CARD[name]                        engine card object for a normalised card string such as "As"
    hand_class(names)                 preflop class of the hole cards (strings): an index into TABLE's per-class lists
    TABLE                             tables_<VARIANT>.json (see build_tables.py): classes, keys, ncomb, total, order,
                                      cum, grid, eq, ps
    range_lists(widths, order)        per width, a shuffled list of villain hands from the top `width` of all hands,
                                      as entries (names, cards, mc): a tuple of card strings, a list of card objects,
                                      and what equity() needs
    strength_key(board)               sort key on entries: the hand's made-hand strength on `board`, higher is better
    equity(my, board, entries, iters, deadline)
                                      heads-up equity of `my` vs. a villain hand drawn from `entries` (eval7's
                                      Monte Carlo for hold'em; stdlib Monte Carlo that stops at `deadline`, a
                                      time.perf_counter() value, or an exact count on the river)
    CAND_MAX                          most villain hands worth scoring per decision with this engine
    showdown(hole, board)             showdown value of stdlib card ints, higher wins (tables and tests use it)

The variant is POKER_VARIANT if set, else VARIANT below, which the build step sets. hold'em runs on eval7 exactly as the
core did before this module existed. Every other variant runs on the stdlib evaluator below, vendored from lab/pk.py and
lab/make_bot.py (pk is not in the upload), so the upload stays self-contained.

New variant at kickoff: give it a branch under RULES (N_HOLE, DECK, showdown), then run build_tables.py <variant>.
"""
import json
import os
import random
import time
from bisect import bisect_right
from itertools import combinations, combinations_with_replacement, permutations
from math import comb

VARIANT = "holdem"  # the build step sets this; POKER_VARIANT, when set, overrides it
VARIANT = (os.environ.get("POKER_VARIANT") or VARIANT).strip().lower()
FORCE_STDLIB = os.environ.get("V2_STDLIB") == "1"  # tests: run hold'em on the stdlib evaluator instead of eval7

HERE = os.path.dirname(os.path.abspath(__file__))
RANKS, SUITS = "23456789TJQKA", "shdc"
NAMES = [r + s for r in RANKS for s in SUITS]  # stdlib card int c: rank c >> 2 (2 = 0 .. A = 12), suit c & 3
INT = {n: i for i, n in enumerate(NAMES)}

# ---- base evaluator: 5 to 8 cards, standard ranks, higher is better (from lab/pk.py) ---------------------------------
_POW5 = [5 ** r for r in range(13)]
_KEY = [(_POW5[c >> 2] << 16) + (1 << (4 * (c & 3))) for c in range(52)]  # base-5 rank counts, 4-bit suit counters
_BIT = [1 << (c >> 2) for c in range(52)]
_STR = [0b1111100000000 >> i for i in range(9)] + [0b1000000001111]  # A-high .. wheel


def _sh(m):
    for i, s in enumerate(_STR):
        if m & s == s:
            return 12 - i if i < 9 else 3
    return -1


_MS = [_sh(m) for m in range(8192)]


def _top(m, n):
    o = 0
    for r in range(12, -1, -1):
        if m >> r & 1:
            o = o * 13 + r
            n -= 1
            if not n:
                break
    return o * 13 ** n


_FL = [0] * 8192
for _m in range(8192):
    if bin(_m).count("1") >= 5:
        _s = _MS[_m]
        _FL[_m] = (8 << 20) + _s if _s >= 0 else (5 << 20) + _top(_m, 5)


def _rv(key):
    """Value of a non-flush rank multiset, base-5 encoded."""
    cnt = [(key // _POW5[r]) % 5 for r in range(13)]
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
        return (7 << 20) + q[0] * 13 + _top(m & ~(1 << q[0]), 1)
    if t and (len(t) > 1 or p):
        return (6 << 20) + t[0] * 13 + max(t[1:] + p)
    s = _MS[m]
    if s >= 0:
        return (4 << 20) + s
    if t:
        return (3 << 20) + t[0] * 169 + _top(m & ~(1 << t[0]), 2)
    if len(p) >= 2:
        return (2 << 20) + p[0] * 169 + p[1] * 13 + _top(m & ~(1 << p[0]) & ~(1 << p[1]), 1)
    if p:
        return (1 << 20) + p[0] * 2197 + _top(m & ~(1 << p[0]), 3)
    return _top(m, 5)


_RC = {}  # rank-multiset values, filled on demand (a miss costs a few microseconds)
_RC_MAX = 40000  # resizing past ~44k entries stalls for 1-4 ms; beyond the cap, values are computed, not stored


def evaluate(cards):
    """Best five of 5 to 8 cards under standard ranks."""
    k = 0
    for c in cards:
        k += _KEY[c]
    if (k + 0x3333) & 0x8888:
        low = k & 0xFFFF
        for s in range(4):
            if (low >> (4 * s)) & 15 >= 5:
                m = 0
                for c in cards:
                    if c & 3 == s:
                        m |= _BIT[c]
                return _FL[m]
    r = k >> 16
    v = _RC.get(r)
    if v is None:
        v = _rv(r)
        if len(_RC) < _RC_MAX:
            _RC[r] = v
    return v


_SD_WHEEL = (1 << 12) | 0b11110000  # short deck A-6-7-8-9


def _rerank(cards, wheel):
    """Flush beats full house; optionally the short-deck A-6-7-8-9 straight. Values doubled (as lab/pk.py)."""
    v = evaluate(cards)
    c = v >> 20
    if c == 5:
        return v * 2 + (3 << 20)
    if wheel and c < 4:
        m = 0
        for x in cards:
            m |= _BIT[x]
        if m & _SD_WHEEL == _SD_WHEEL:
            return ((4 << 20) + 3) * 2
    return v * 2


def prep(board):
    """Per-board work shared by every hand evaluated on that board. Default: none."""
    return board


def val(hole, p):
    """Showdown value of `hole` on a board prepared by prep()."""
    return showdown(hole, p)


# ==== RULES: the only variant-specific code. A new variant needs N_HOLE, DECK and showdown(hole, board) here, where
# hole and board are lists of card ints and a higher value wins; then build its table with build_tables.py. =========
N_HOLE = 2
DECK = list(range(52))
DISCARD = False  # a discard variant: core/agent.py sends discard turns to discard.py and sets TO_COME on betting turns
TO_COME = None  # discard variants: board cards still to be dealt this decision (None: 5 - len(board), as before)
if VARIANT == "holdem":
    def showdown(hole, board):
        return evaluate(hole + board)
elif VARIANT == "flushfh":  # flush beats full house
    def showdown(hole, board):
        return _rerank(hole + board, False)
elif VARIANT == "shortdeck":  # 36 cards (6 to A), flush beats full house, A-6-7-8-9 is the lowest straight
    DECK = [c for c in range(52) if c >> 2 >= 4]

    def showdown(hole, board):
        return _rerank(hole + board, True)
elif VARIANT == "hole3":  # three hole cards, best five of all eight
    N_HOLE = 3

    def showdown(hole, board):
        return evaluate(hole + board)
elif VARIANT == "hole3discard":  # MIT 2026 (lab/variants/DISCARD.md): three hole cards, one discarded after the flop
    N_HOLE = 3  # preflop; two after the discard
    DISCARD = True

    def showdown(hole, board):
        """Two kept cards plus the board. Three cards (preflop tables, villain hands in a range) play their best two:
        a stand-in for the discard that hand will make."""
        if len(hole) == 2:
            return evaluate(hole + board)
        a, b, c = hole
        return max(evaluate([a, b] + board), evaluate([a, c] + board), evaluate([b, c] + board))
elif VARIANT == "omaha":  # four hole cards, exactly two of them with exactly three of the board
    N_HOLE = 4
    _R5 = [_POW5[c >> 2] for c in range(52)]
    _RV5 = {}  # every five-card rank multiset, built once: Omaha only ever evaluates five cards
    for _rs in combinations_with_replacement(range(13), 5):
        if _rs[0] != _rs[4]:
            _k = sum(_POW5[r] for r in _rs)
            _RV5[_k] = _rv(_k)

    def prep(board):
        tri = list(combinations(board, 3))
        return ([_R5[a] + _R5[b] + _R5[c] for a, b, c in tri],
                [(a & 3, _BIT[a] | _BIT[b] | _BIT[c]) for a, b, c in tri if a & 3 == b & 3 == c & 3])

    def val(hole, p):
        keys, fl = p
        R, RV = _R5, _RV5
        a, b, c, d = hole
        ps = (R[a] + R[b], R[a] + R[c], R[a] + R[d], R[b] + R[c], R[b] + R[d], R[c] + R[d])
        best = max([RV[x + y] for x in ps for y in keys])  # a flush counted as its ranks is never above its real value
        for s, m in fl:
            hs = [h for h in hole if h & 3 == s]
            if len(hs) >= 2:
                for x, y in combinations(hs, 2):
                    v = _FL[m | _BIT[x] | _BIT[y]]
                    if v > best:
                        best = v
        return best

    def showdown(hole, board):
        return val(hole, prep(board))
else:
    raise ValueError(f"engine.py: unknown variant {VARIANT!r}; add it under RULES")
# ==== end of RULES ====================================================================================================

TOTAL = comb(len(DECK), N_HOLE)  # starting hands


def canon(hole):
    """Strategy class key: ranks with suits relabelled in order of appearance (lab/pk.py's canon)."""
    cs = sorted(hole, key=lambda c: (-(c >> 2), c & 3))
    m, out = {}, []
    for c in cs:
        s = m.setdefault(c & 3, len(m))
        out.append((c >> 2) * 4 + s)
    return tuple(out)


TABLE_PATH = os.path.join(HERE, f"tables_{VARIANT}.json")
TABLE = None
if os.path.exists(TABLE_PATH):
    with open(TABLE_PATH) as _f:
        TABLE = json.load(_f)
    if TABLE.get("variant") != VARIANT or TABLE.get("total") != TOTAL:
        raise ValueError(f"{TABLE_PATH} is for {TABLE.get('variant')!r} ({TABLE.get('total')} hands), not {VARIANT!r}")

# ---- stdlib runtime ----------------------------------------------------------------------------------------------------
ENGINE = "stdlib"
CARD = INT
_rng = random.Random()
_R = _rng.random
_pc = time.perf_counter
CAND_MAX = {2: 96, 3: 64}.get(N_HOLE, 40)  # scoring a villain hand costs about 1 us here (3.5 us for Omaha's river)
PER_RUN = 3 if VARIANT == "omaha" else 4  # villain hands per Monte Carlo runout; measured best for precision per us
MIN_RUNS = 2  # runouts done even past the deadline, so equity is never a bare guess
SAMPLE = 1200  # villain hands kept per range width when the hand space is too big to list (3+ hole cards)
_PERMS = list(permutations(range(4)))
_CLS = {tuple(k): i for i, k in enumerate(TABLE["keys"])} if TABLE else {}


def hand_class(names):
    return _CLS[canon([INT[x] for x in names])]


def _entry(h):
    h = list(h)
    return (tuple(NAMES[c] for c in h), h, h)


def range_lists(widths, order, seed=12345):
    """For each width, a shuffled list of villain hands from the top `width` of all hands by `order`. Small hand spaces
    list every hand of the top classes (as the hold'em core does); bigger ones sample SAMPLE hands uniformly."""
    rng = random.Random(seed)
    keys, out = TABLE["keys"], []
    if TOTAL <= 5000:
        members = {}
        for h in combinations(DECK, N_HOLE):
            members.setdefault(_CLS[canon(h)], []).append(h)
        for w in widths:
            lst, n = [], int(round(w * TOTAL))
            for ci in order:
                lst.extend(_entry(h) for h in members[ci])
                if len(lst) >= n:
                    break
            rng.shuffle(lst)
            out.append(lst)
        return out
    cum, t = [], 0
    for ci in order:
        t += TABLE["ncomb"][ci]
        cum.append(t)
    for w in widths:
        n = max(1, int(round(w * TOTAL)))
        lst = []
        for _ in range(SAMPLE):
            ci = order[bisect_right(cum, int(rng.random() * n))]
            p = _PERMS[rng.randrange(24)]  # a random suit relabelling: uniform over the hands like this class's key
            lst.append(_entry([(c & ~3) | p[c & 3] for c in keys[ci]]))
        out.append(lst)
    return out


_SC = {}  # strength of villain hands on the current board, by card names; cleared when the board changes
_SCB = [None, None]


def _prepped(board):
    k = tuple(board)
    if _SCB[0] != k:
        _SC.clear()
        _SCB[0], _SCB[1] = k, prep(board)
    return _SCB[1]


def strength_key(board):
    p, sc = _prepped(board), _SC

    def key(t):
        v = sc.get(t[0])
        if v is None:
            v = sc[t[0]] = val(t[1], p)
        return v
    return key


def equity(my, board, cands, iters, deadline=None):
    """Heads-up equity vs. a villain hand drawn uniformly from `cands`. River: exact over cands. Earlier: Monte Carlo,
    PER_RUN villain hands per random runout (a hand that collides with the runout is skipped, which keeps the estimate
    unbiased because every runout checks the same number), until `iters` comparisons or `deadline`."""
    n = len(cands)
    if not n:
        return 0.5
    nb = 5 - len(board) if TO_COME is None else TO_COME
    if nb <= 0:
        key = strength_key(board)
        mv = val(my, _SCB[1])
        w = 0.0
        for t in cands:
            v = key(t)
            if mv > v:
                w += 1.0
            elif mv == v:
                w += 0.5
        return w / n
    if deadline is None:
        deadline = float("inf")
    known = set(my)
    known.update(board)
    rest = [c for c in DECK if c not in known]
    L, m, R, pc, pr, vl = len(rest), PER_RUN, _R, _pc, prep, val
    j = int(R() * n)
    wins, cnt, runs = 0.0, 0, 0
    while cnt < iters:
        if runs >= MIN_RUNS and pc() > deadline:
            break
        runs += 1
        a = rest[int(R() * L)]
        if nb == 1:
            add = [a]
        else:
            b = a
            while b == a:
                b = rest[int(R() * L)]
            add = [a, b]
        p = pr(board + add)
        mv = vl(my, p)
        for _ in range(m):
            h = cands[j][1]
            j += 1
            if j == n:
                j = 0
            if a in h or (nb == 2 and b in h):
                continue
            v = vl(h, p)
            cnt += 1
            if mv > v:
                wins += 1.0
            elif mv == v:
                wins += 0.5
    return wins / cnt if cnt else 0.5


# ---- hold'em on eval7: the original core's code paths, unchanged ------------------------------------------------------
if VARIANT == "holdem" and not FORCE_STDLIB:
    try:
        import eval7
    except ImportError:  # no eval7 on the host: hold'em still runs, on the stdlib evaluator above
        eval7 = None
    if eval7 is not None:
        ENGINE = "eval7"
        CARD = {r + s: eval7.Card(r + s) for r in RANKS for s in SUITS}
        _EV = eval7.evaluate
        _MC = eval7.py_hand_vs_range_monte_carlo
        CAND_MAX = 1 << 30
        _RV = {r: i for i, r in enumerate(RANKS)}
        _CL_IDX = {c: i for i, c in enumerate(TABLE["classes"])} if TABLE else {}

        def hand_class(names):
            c1, c2 = names[0], names[1]
            r1, r2 = c1[0], c2[0]
            if _RV[r1] < _RV[r2]:
                r1, r2, c1, c2 = r2, r1, c2, c1
            if r1 == r2:
                return _CL_IDX[r1 + r2]
            return _CL_IDX[r1 + r2 + ("s" if c1[1] == c2[1] else "o")]

        def _class_combos(name):
            a, b = name[0], name[1]
            out = []
            if len(name) == 2:
                for x in range(4):
                    for y in range(x + 1, 4):
                        out.append((a + SUITS[x], b + SUITS[y]))
            elif name[2] == "s":
                for x in range(4):
                    out.append((a + SUITS[x], b + SUITS[x]))
            else:
                for x in range(4):
                    for y in range(4):
                        if x != y:
                            out.append((a + SUITS[x], b + SUITS[y]))
            return out

        def range_lists(widths, order, seed=12345):
            r0, classes, out = random.Random(seed), TABLE["classes"], []
            for w in widths:
                lst, n = [], int(round(w * TOTAL))
                for ci in order:
                    for (x, y) in _class_combos(classes[ci]):
                        cx, cy = CARD[x], CARD[y]
                        lst.append(((x, y), [cx, cy], ((cx, cy), 1.0)))
                    if len(lst) >= n:
                        break
                r0.shuffle(lst)
                out.append(lst)
            return out

        def strength_key(board):
            return lambda t: _EV(board + t[1])

        def equity(my, board, cands, iters, deadline=None):
            return _MC(my, [t[2] for t in cands], board, iters)
