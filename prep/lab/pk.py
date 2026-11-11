"""Cards, fast pure-Python evaluator, Monte Carlo equity, preflop tables.

Cards are ints 0..51: rank = c >> 2 (0=2 .. 12=A), suit = c & 3.
Higher evaluator value = better hand.
"""
import json, os, random
from itertools import combinations

# Each card maps to: base-5 rank-count key (high bits) + 4-bit suit counters (low 16 bits).
_POW5 = [5 ** r for r in range(13)]
CARD_KEY = [(_POW5[c >> 2] << 16) + (1 << (4 * (c & 3))) for c in range(52)]
RANKBIT = [1 << (c >> 2) for c in range(52)]
_STRAIGHTS = [0b1111100000000 >> i for i in range(9)] + [0b1000000001111]  # A-high .. wheel


def _straight_high(mask):
    for i, s in enumerate(_STRAIGHTS):
        if mask & s == s:
            return 12 - i if i < 9 else 3
    return -1


_MASK_STRAIGHT = [_straight_high(m) for m in range(8192)]


def _top_bits(mask, n):
    out = 0
    for r in range(12, -1, -1):
        if mask >> r & 1:
            out = out * 13 + r
            n -= 1
            if n == 0:
                break
    while n > 0:
        out *= 13
        n -= 1
    return out


_FLUSH_VAL = [0] * 8192
for _m in range(8192):
    if bin(_m).count("1") >= 5:
        _s = _MASK_STRAIGHT[_m]
        _FLUSH_VAL[_m] = (8 << 20) + _s if _s >= 0 else (5 << 20) + _top_bits(_m, 5)


def _rank_value(key):
    """Value of a non-flush rank multiset encoded in base 5."""
    counts = [(key // _POW5[r]) % 5 for r in range(13)]
    mask = 0
    quads, trips, pairs = [], [], []
    for r in range(12, -1, -1):
        c = counts[r]
        if c:
            mask |= 1 << r
        if c == 4:
            quads.append(r)
        elif c == 3:
            trips.append(r)
        elif c == 2:
            pairs.append(r)
    if quads:
        k = _top_bits(mask & ~(1 << quads[0]), 1)
        return (7 << 20) + quads[0] * 13 + k
    if trips and (len(trips) > 1 or pairs):
        t = trips[0]
        p = max(trips[1:] + pairs)
        return (6 << 20) + t * 13 + p
    s = _MASK_STRAIGHT[mask]
    if s >= 0:
        return (4 << 20) + s
    if trips:
        return (3 << 20) + trips[0] * 169 + _top_bits(mask & ~(1 << trips[0]), 2)
    if len(pairs) >= 2:
        return (2 << 20) + pairs[0] * 169 + pairs[1] * 13 + _top_bits(mask & ~(1 << pairs[0]) & ~(1 << pairs[1]), 1)
    if pairs:
        return (1 << 20) + pairs[0] * 2197 + _top_bits(mask & ~(1 << pairs[0]), 3)
    return _top_bits(mask, 5)


_RANK_CACHE = {}


def evaluate(cards):
    """Evaluate 5-7 cards. About 1 microsecond on a modern laptop."""
    k = 0
    for c in cards:
        k += CARD_KEY[c]
    if (k + 0x3333) & 0x8888:
        low = k & 0xFFFF
        for s in range(4):
            if (low >> (4 * s)) & 15 >= 5:
                m = 0
                for c in cards:
                    if c & 3 == s:
                        m |= RANKBIT[c]
                return _FLUSH_VAL[m]
    rk = k >> 16
    v = _RANK_CACHE.get(rk)
    if v is None:
        v = _RANK_CACHE[rk] = _rank_value(rk)
    return v


def evaluate_omaha(hole, board):
    best = 0
    for h in combinations(hole, 2):
        for b in combinations(board, 3):
            v = evaluate(h + b)
            if v > best:
                best = v
    return best


def hand_class(a, b):
    """0..168 canonical index: pairs on diagonal, suited above, offsuit below."""
    ra, rb = a >> 2, b >> 2
    if ra < rb:
        ra, rb = rb, ra
    if ra == rb:
        return ra * 13 + rb
    return ra * 13 + rb if (a & 3) == (b & 3) else rb * 13 + ra


def class_name(idx):
    n = "23456789TJQKA"
    x, y = idx // 13, idx % 13
    if x == y:
        return n[x] * 2
    return n[x] + n[y] + "s" if x > y else n[y] + n[x] + "o"


# ---- variant layer (set POKER_VARIANT before import; subprocesses inherit it) --------------------
VARIANT = os.environ.get("POKER_VARIANT", "holdem")
TABLE_VARIANT = os.environ.get("POKER_TABLE_FROM", VARIANT)  # lets us test a stale table
N_HOLE = {"omaha": 4, "hole3": 3, "hole3discard": 3}.get(VARIANT, 2)
# Discard variant (MIT Pokerbots 2026, lab/variants/DISCARD.md): three hole cards; after a two-card flop every player
# still in the hand discards one, in postflop order, face up onto the board; then betting, turn, river. Showdown is the
# two kept cards plus the whole board. DISCARD_DEAD=1 makes discards revealed but dead (not community cards).
DISCARD = VARIANT == "hole3discard"
FLOP_N = 2 if DISCARD else 3  # cards dealt on the flop
DISCARD_TO_BOARD = os.environ.get("DISCARD_DEAD") != "1"
DECK = [c for c in range(52) if VARIANT != "shortdeck" or c >> 2 >= 4]
_SD_WHEEL = (1 << 12) | 0b11110000  # A + 6,7,8,9 with rank index 2=0


def _rerank(cards, wheel):
    """Flush beats full house; optionally the short-deck A-6-7-8-9 straight. Values are doubled."""
    v = evaluate(cards)
    c = v >> 20
    if c == 5:
        return v * 2 + (3 << 20)
    if wheel and c < 4:
        m = 0
        for x in cards:
            m |= RANKBIT[x]
        if m & _SD_WHEEL == _SD_WHEEL:
            return ((4 << 20) + 3) * 2
    return v * 2


if VARIANT == "shortdeck":
    def showdown(h, b):
        return _rerank(h + b, True)
elif VARIANT == "flushfh":
    def showdown(h, b):
        return _rerank(h + b, False)
elif VARIANT == "omaha":
    def showdown(h, b):
        return evaluate_omaha(h, b)
elif DISCARD:
    def showdown(h, b):
        """Two kept cards plus the board. A three-card hand (before its discard, or a villain in a range) counts as
        its best two: a stand-in for the discard it will make."""
        if len(h) == 2:
            return evaluate(h + b)
        x, y, z = h
        return max(evaluate([x, y] + b), evaluate([x, z] + b), evaluate([y, z] + b))
else:
    def showdown(h, b):
        return evaluate(h + b)


def canon(hole):
    """Canonical strategy class: ranks with suits relabelled in order of appearance."""
    cs = sorted(hole, key=lambda c: (-(c >> 2), c & 3))
    m, out = {}, []
    for c in cs:
        s = m.setdefault(c & 3, len(m))
        out.append((c >> 2) * 4 + s)
    return tuple(out)


_TABLE_PATH = os.path.join(os.path.dirname(__file__), f"table_{TABLE_VARIANT}.json")


def _mc_class(args):
    rep, rollouts, seed = args
    rng = random.Random(seed)
    rep = list(rep)
    rest = [c for c in DECK if c not in rep]
    w1 = w2 = 0.0
    for _ in range(rollouts):
        s = rng.sample(rest, 5 + 2 * N_HOLE)
        b = s[:5]
        me = showdown(rep, b)
        v1 = showdown(s[5 : 5 + N_HOLE], b)
        v2 = showdown(s[5 + N_HOLE : 5 + 2 * N_HOLE], b)
        if me > v1:
            w1 += 1
        elif me == v1:
            w1 += 0.5
        if me > v1 and me > v2:
            w2 += 1
        elif me >= v1 and me >= v2:
            w2 += 0.5
    return w1 / rollouts, w2 / rollouts


def build_table(rollouts=None, procs=10):
    """Full strategy table for the current variant. Returns seconds taken."""
    import time
    from multiprocessing import Pool
    t0 = time.time()
    if rollouts is None:
        rollouts = {2: 4000, 3: 1200, 4: 300}[N_HOLE]
    counts, rep = {}, {}
    for h in combinations(DECK, N_HOLE):
        k = canon(h)
        counts[k] = counts.get(k, 0) + 1
        rep.setdefault(k, h)
    keys = list(rep)
    with Pool(procs) as p:
        res = p.map(_mc_class, [(rep[k], rollouts, i) for i, k in enumerate(keys)], chunksize=32)
    score = {k: 0.6 * r[0] + 0.8 * r[1] for k, r in zip(keys, res)}
    order = sorted(keys, key=lambda k: -score[k])
    tot, cum, out = sum(counts.values()), 0, {}
    for k in order:
        cum += counts[k]
        i = keys.index(k) if False else None
        out[",".join(map(str, k))] = [round(cum / tot, 5)]
    eq = {k: r[0] for k, r in zip(keys, res)}
    for k in keys:
        out[",".join(map(str, k))].append(round(eq[k], 4))
    json.dump(out, open(_TABLE_PATH, "w"))
    return time.time() - t0, len(keys)


_T = None
_C = None
if os.path.exists(_TABLE_PATH):
    _T = {tuple(map(int, k.split(","))): v for k, v in json.load(open(_TABLE_PATH)).items()}


def _load_order():
    global COMBOS_SORTED
    def key(h):
        v = _T.get(canon(h))
        return v[0] if v else 1.0
    COMBOS_SORTED = sorted(combinations(DECK, N_HOLE), key=key)


COMBOS_SORTED = None
if _T is not None:
    _load_order()
_CACHE2 = {}


def pct(hole):
    """Fraction of starting hands at least this strong (0 best, 1 worst)."""
    if N_HOLE == 2:
        a, b = hole[0], hole[1]
        k = (a, b)
        v = _CACHE2.get(k)
        if v is None:
            e = _T.get(canon(hole))
            v = _CACHE2[k] = e[0] if e else 1.0
        return v
    e = _T.get(canon(hole))
    return e[0] if e else 1.0


def hu_eq(hole):
    e = _T.get(canon(hole))
    return e[1] if e else 0.5


def equity_vs_range(hole, board, width, rollouts, rng=random.random):
    """Heads-up equity vs. a villain drawn uniformly from the top `width` of starting hands."""
    combos = COMBOS_SORTED
    size = len(combos)
    k_limit = max(8, int(width * size))
    known = set(hole)
    known.update(board)
    nb = getattr(board, "to_come", None)
    if nb is None:
        nb = 5 - len(board)
    final = len(board) + nb
    nd = len(DECK)
    deck = DECK
    wins = 0.0
    n = 0
    bl = list(board)
    sd = showdown
    for _ in range(rollouts):
        v = combos[int(rng() * k_limit)]
        bad = False
        for c in v:
            if c in known:
                bad = True
                break
        if bad:
            continue
        runout = bl
        if nb:
            runout = bl[:]
            while len(runout) < final:
                c = deck[int(rng() * nd)]
                if c not in known and c not in v and c not in runout:
                    runout.append(c)
        n += 1
        v1 = sd(hole, runout)
        v2 = sd(list(v), runout)
        if v1 > v2:
            wins += 1
        elif v1 == v2:
            wins += 0.5
    return wins / n if n else 0.5


class Board(list):
    """A board that knows how many cards are still to be dealt (discard variant: discards make len(board) vary)."""
    __slots__ = ("to_come",)

    def __init__(self, cards=(), to_come=None):
        list.__init__(self, cards)
        self.to_come = to_come


_HOLDEM_T = None


def pair_pct(a, b):
    """Hold'em preflop percentile of two cards (0 best), from table_holdem.json."""
    global _HOLDEM_T
    if _HOLDEM_T is None:
        path = os.path.join(os.path.dirname(__file__), "table_holdem.json")
        _HOLDEM_T = {tuple(map(int, k.split(","))): v[0] for k, v in json.load(open(path)).items()}
    return _HOLDEM_T.get(canon((a, b)), 1.0)


def default_discard(hole, board=()):
    """Lab bots' discard: the index of the card to drop so the two kept cards are the best pair by preflop strength."""
    best, bi = 2.0, 0
    for i in range(len(hole)):
        keep = [c for j, c in enumerate(hole) if j != i]
        v = pair_pct(keep[0], keep[1])
        if v < best:
            best, bi = v, i
    return bi


def icm(stacks, payouts):
    """Malmuth-Harville ICM. stacks: list of chips, payouts: list best-first. Returns expected points."""
    n = len(stacks)
    total = float(sum(stacks))
    if total <= 0:
        return [0.0] * n
    pay = list(payouts[:n]) + [0.0] * max(0, n - len(payouts))
    memo = {}

    def rec(mask, place, remain):
        # Returns expected payout vector for players in mask, given places `place..` remain.
        key = mask
        if key in memo:
            return memo[key]
        res = [0.0] * n
        if place >= n or remain <= 0:
            memo[key] = res
            return res
        for i in range(n):
            if mask >> i & 1 and stacks[i] > 0:
                p = stacks[i] / remain
                res[i] += p * pay[place]
                sub = rec(mask & ~(1 << i), place + 1, remain - stacks[i])
                for j in range(n):
                    res[j] += p * sub[j]
        memo[key] = res
        return res

    return rec((1 << n) - 1, 0, total)
