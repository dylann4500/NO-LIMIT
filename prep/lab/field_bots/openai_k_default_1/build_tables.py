"""Offline builder. Runtime reads only preflop.json, never runs this script."""
import itertools
import json
import os
import time

import eval7

RANKS = "23456789TJQKA"
CARDS = {r + s: eval7.Card(r + s) for r in RANKS for s in "cdhs"}


def key(a, b):
    x, y = sorted((RANKS.index(a[0]), RANKS.index(b[0])), reverse=True)
    return RANKS[x] + RANKS[y] + ("" if x == y else "s" if a[1] == b[1] else "o")


def main():
    t = time.monotonic()
    combos = list(itertools.combinations(CARDS, 2))
    all_range = [((CARDS[a], CARDS[b]), 1.0) for a, b in combos]
    representatives = {}
    counts = {}
    for a, b in combos:
        k = key(a, b)
        representatives[k] = [CARDS[a], CARDS[b]]
        counts[k] = counts.get(k, 0) + 1
    random_eq = {
        k: eval7.py_hand_vs_range_monte_carlo(h, all_range, [], 100000)
        for k, h in representatives.items()
    }

    def score(k):
        a, b = RANKS.index(k[0]), RANKS.index(k[1])
        pair = a == b
        suited = k.endswith("s")
        gap = a - b
        return random_eq[k] + 0.045 * pair + 0.034 * suited + (
            0.014 if suited and gap == 1 else 0.007 if suited and gap == 2 else 0
        ) - (0.012 if k.endswith("o") and a == 12 and b < 7 else 0)

    # A raw heads-up equity ordering puts medium pairs ahead of AK and makes
    # premium raising ranges implausibly pair-heavy. Start with a conventional
    # playable-hand ordering, then sort the low-frequency tail by utility.
    first = ("AA KK QQ AKs JJ AKo AQs TT AJs KQs AQo 99 ATs KJs AJo KQo "
             "88 QJs KTs A9s ATo 77 QTs JTs KJo A8s K9s 66 A7s QJo KTo "
             "A5s A6s Q9s J9s A4s 55 A3s K8s T9s A2s QTo K7s 44 JTo "
             "A9o K6s 98s Q8s K5s J8s 33 A8o K9o T8s K4s Q7s K3s "
             "87s Q9o 22 K2s J7s Q6s 76s A7o A5o Q5s T7s 97s A6o "
             "K8o A4o J9o 65s Q4s 86s T9o A3o J6s A2o K7o Q8o 54s").split()
    ordered = first + sorted((k for k in representatives if k not in first), key=score, reverse=True)
    percentile = {}
    n = 0
    for k in ordered:
        percentile[k] = (n + counts[k] * 0.5) / 1326.0
        n += counts[k]
    fractions = [0.025, 0.04, 0.06, 0.09, 0.13, 0.18, 0.25, 0.35, 0.50, 0.70, 1.0]
    ranges = []
    equities = {k: [] for k in ordered}
    for f in fractions:
        rr = [((CARDS[a], CARDS[b]), 1.0) for a, b in combos if percentile[key(a, b)] <= f]
        ranges.append([list((a, b)) for a, b in combos if percentile[key(a, b)] <= f])
        for k in ordered:
            equities[k].append(round(eval7.py_hand_vs_range_monte_carlo(
                representatives[k], rr, [], 50000), 5))
        print(f, len(rr), [k for k in ordered if percentile[k] <= f], flush=True)
    data = {"fractions": fractions, "percentile": percentile, "equity": equities,
            "random_equity": random_eq, "ranges": ranges}
    path = os.path.join(os.path.dirname(__file__), "preflop.json")
    with open(path, "w") as out:
        json.dump(data, out, separators=(",", ":"))
    # All straight-draw tests for any board rank mask and two hole ranks.
    # This turns the per-combination runtime operation into one byte lookup.
    windows = [31 << i for i in range(9)] + [0x100F]
    draws = bytearray(8192 * 169)
    for boardmask in range(8192):
        if not 1 <= boardmask.bit_count() <= 4:
            continue
        for a in range(13):
            for b in range(13):
                whole = boardmask | (1 << a) | (1 << b)
                draws[boardmask * 169 + a * 13 + b] = any(
                    (boardmask & w).bit_count() < 4 and (whole & w).bit_count() == 4
                    for w in windows)
    with open(os.path.join(os.path.dirname(__file__), "draws.bin"), "wb") as out:
        out.write(draws)
    print("Wrote", path, "in", round(time.monotonic() - t, 2), "seconds")


if __name__ == "__main__":
    main()
