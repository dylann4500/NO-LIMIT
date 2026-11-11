"""Small model: postflop equity from a hand-feature lookup table built offline. No live Monte Carlo.
Features are cheap and variant-portable: rebuild the table with the variant's evaluator."""
import json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk
from pk import evaluate, equity_vs_range
from hero import Hero

WIDTHS = [0.08, 0.2, 0.4, 1.0]
_TP = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"strength_{pk.VARIANT}.json")


def feature(hole, board):
    all_ = hole + board
    # Features stay in the base ranking; each variant's table learns what they are worth under its own rules.
    v = pk.evaluate_omaha(hole, board) if pk.VARIANT == "omaha" else evaluate(all_)
    cat = v >> 20
    bv = evaluate(board)
    bcat = bv >> 20
    ranks = sorted((c >> 2 for c in board), reverse=True)
    top = ranks[0]
    sub = 0
    if cat == 1:
        pr = (v - (1 << 20)) // 2197
        hi = max(c >> 2 for c in hole)
        if bcat == 1:
            sub = 5 if hi >= 11 else 6 if hi >= 8 else 7  # board pair, kicker strength
        elif pr > top:
            sub = 0 if pr >= 8 else 1  # overpair
        elif pr == top:
            sub = 2 if hi >= 10 and hi != pr or pr >= 11 else 3  # top pair, kicker
        elif len(ranks) > 1 and pr >= ranks[1]:
            sub = 4
        else:
            sub = 8
    elif cat == 0:
        hi = max(c >> 2 for c in hole)
        sub = 0 if hi > top and hi == 12 else 1 if hi > top else 2
    else:
        sub = 1 if cat > bcat else 0  # does our hand actually use the hole cards
    fd = sd = 0
    if len(board) < 5:
        if pk.VARIANT == "omaha":
            # Must use exactly two hole cards, so a draw needs two of the suit in hand and two on board.
            hc, bc = [0, 0, 0, 0], [0, 0, 0, 0]
            for c in hole:
                hc[c & 3] += 1
            for c in board:
                bc[c & 3] += 1
            for i in range(4):
                if hc[i] >= 2 and bc[i] == 2:
                    fd = 1
        else:
            cnt = [0, 0, 0, 0]
            for c in all_:
                cnt[c & 3] += 1
            ms = cnt[0]
            s = 0
            for i in range(1, 4):
                if cnt[i] > ms:
                    ms, s = cnt[i], i
            if ms == 4 and any((c & 3) == s for c in hole):
                fd = 1
        m = 0
        for c in all_:
            m |= 1 << (c >> 2)
        m = (m << 1) | (m >> 12 & 1)
        for i in range(0, 10):
            b = (m >> i) & 31
            if b in (0b11110, 0b01111):
                sd = 2
                break
            if b in (0b11101, 0b11011, 0b10111):
                sd = max(sd, 1)
    bpair = 1 if bcat >= 1 else 0
    cnt2 = [0, 0, 0, 0]
    for c in board:
        cnt2[c & 3] += 1
    wet = max(cnt2)
    wet = 2 if wet >= 3 else 1 if wet == 2 else 0
    return (len(board), cat, sub, fd, sd, bpair, wet)


def _sample(args):
    n, rollouts, seed = args
    random.seed(seed)
    out = {}
    deck = pk.DECK
    for _ in range(n):
        st = random.choice((3, 4, 5))
        s = random.sample(deck, pk.N_HOLE + st)
        hole, board = s[:pk.N_HOLE], s[pk.N_HOLE:]
        k = feature(hole, board)
        row = out.setdefault(k, [0] + [0.0] * len(WIDTHS))
        row[0] += 1
        for i, w in enumerate(WIDTHS):
            row[i + 1] += equity_vs_range(hole, board, w, rollouts)
    return out


def build(n=150000, rollouts=24, procs=10):
    from multiprocessing import Pool
    t = time.time()
    with Pool(procs) as p:
        parts = p.map(_sample, [(n // procs, rollouts, 1000 + i) for i in range(procs)])
    tot = {}
    for part in parts:
        for k, r in part.items():
            row = tot.setdefault(k, [0] + [0.0] * len(WIDTHS))
            for i in range(len(row)):
                row[i] += r[i]
    tab = {",".join(map(str, k)): [round(x / r[0], 4) for x in r[1:]] + [r[0]] for k, r in tot.items()}
    json.dump(tab, open(_TP, "w"))
    return time.time() - t, len(tab)


_TAB = None


def _load():
    global _TAB
    d = json.load(open(_TP))
    _TAB = {tuple(map(int, k.split(","))): v for k, v in d.items()}


def table_equity(hole, board, width):
    if _TAB is None:
        _load()
    r = _TAB.get(feature(hole, board))
    if r is None or r[-1] < 5:
        k = feature(hole, board)
        # Back off: ignore texture when the exact cell is rare.
        for cand, v in _TAB.items():
            if cand[:5] == k[:5] and v[-1] >= 5:
                r = v
                break
        if r is None:
            return 0.5
    if width <= WIDTHS[0]:
        return r[0]
    for i in range(1, len(WIDTHS)):
        if width <= WIDTHS[i]:
            f = (width - WIDTHS[i - 1]) / (WIDTHS[i] - WIDTHS[i - 1])
            return r[i - 1] * (1 - f) + r[i] * f
    return r[3]


class HeroTable(Hero):
    """Same policy as the candidate; only the postflop equity source differs."""
    def eq(self, hole, board, width):
        return table_equity(hole, board, width)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150000
    ro = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    procs = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    secs, cells = build(n, ro, procs)
    print(f"{pk.VARIANT}: {cells} feature cells in {secs:.1f}s -> {os.path.getsize(_TP)} bytes")
    _load()
    import time as T
    a = [random.sample(pk.DECK, pk.N_HOLE + 5) for _ in range(5000)]
    t = T.perf_counter()
    for s in a:
        table_equity(s[:pk.N_HOLE], s[pk.N_HOLE:pk.N_HOLE + random.choice((3, 4, 5))], 0.3)
    print(f"lookup {(T.perf_counter()-t)/5000*1e6:.1f} us")
    err = []
    for _ in range(600):
        st = random.choice((3, 4, 5))
        s = random.sample(pk.DECK, pk.N_HOLE + st)
        w = random.choice([0.15, 0.3, 0.6])
        h, b = s[:pk.N_HOLE], s[pk.N_HOLE:]
        err.append(abs(table_equity(h, b, w) - equity_vs_range(h, b, w, 200)))
    err.sort()
    print(f"abs equity error vs 200-rollout MC: mean {sum(err)/len(err):.3f}, p90 {err[int(.9*len(err))]:.3f}")
